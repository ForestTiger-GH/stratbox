"""Bounded interval accounting and independently qualified collection coverage.

Evidence only proves what the named observer actually saw.  Claimed producer
counts never attest the identity of a host, the reality of an external effect,
or the contents of a missing event.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from stratbox.system.execution.contracts import safe_token

MAX_SEQUENCE = 2**53 - 1
MAX_RANGES = 100_000
CoverageStatus = Literal["complete", "incomplete", "indeterminate"]


@dataclass(frozen=True, slots=True, order=True)
class SequenceRange:
    first: int
    last: int

    def __post_init__(self) -> None:
        if (type(self.first) is not int or type(self.last) is not int
                or not 1 <= self.first <= self.last <= MAX_SEQUENCE):
            raise ValueError("Invalid sequence interval")

    @property
    def count(self) -> int:
        return self.last - self.first + 1


def merge_ranges(ranges: Iterable[SequenceRange], *, max_ranges: int = MAX_RANGES) -> tuple[SequenceRange, ...]:
    if not 1 <= max_ranges <= MAX_RANGES:
        raise ValueError("Invalid interval budget")
    bounded: list[SequenceRange] = []
    for n, item in enumerate(ranges, 1):
        if n > MAX_RANGES:
            raise ValueError("journal.interval_input_limit")
        bounded.append(item)
    ordered = sorted(bounded)
    merged: list[SequenceRange] = []
    for item in ordered:
        if not isinstance(item, SequenceRange):
            raise TypeError("Expected sequence ranges")
        if merged and item.first <= merged[-1].last + 1:
            prior = merged[-1]
            merged[-1] = SequenceRange(prior.first, max(item.last, prior.last))
        else:
            if len(merged) >= max_ranges:
                raise ValueError("journal.interval_limit")
            merged.append(item)
    return tuple(merged)


def count_ranges(ranges: Iterable[SequenceRange]) -> int:
    return sum(r.count for r in merge_ranges(ranges))


def intersect_ranges(left: Iterable[SequenceRange], right: Iterable[SequenceRange]) -> tuple[SequenceRange, ...]:
    a, b = merge_ranges(left), merge_ranges(right)
    i = j = 0
    out: list[SequenceRange] = []
    while i < len(a) and j < len(b):
        lo, hi = max(a[i].first, b[j].first), min(a[i].last, b[j].last)
        if lo <= hi:
            out.append(SequenceRange(lo, hi))
        if a[i].last <= b[j].last:
            i += 1
        else:
            j += 1
    return merge_ranges(out)


def subtract_ranges(left: Iterable[SequenceRange], right: Iterable[SequenceRange]) -> tuple[SequenceRange, ...]:
    a, b = merge_ranges(left), merge_ranges(right)
    out: list[SequenceRange] = []
    j = 0
    for item in a:
        pos = item.first
        while j < len(b) and b[j].last < pos:
            j += 1
        k = j
        while k < len(b) and b[k].first <= item.last:
            if b[k].first > pos:
                out.append(SequenceRange(pos, b[k].first - 1))
            pos = max(pos, b[k].last + 1)
            if pos > item.last:
                break
            k += 1
        if pos <= item.last:
            out.append(SequenceRange(pos, item.last))
        if len(out) > MAX_RANGES:
            raise ValueError("journal.interval_limit")
    return tuple(out)


def find_gaps(sequences: Iterable[int], *, start: int = 1,
              expected_last: int | None = None, max_observations: int = 1_000_000) -> tuple[SequenceRange, ...]:
    if type(start) is not int or not 1 <= start <= MAX_SEQUENCE:
        raise ValueError("Invalid start sequence")
    if expected_last is not None and (type(expected_last) is not int or not 0 <= expected_last <= MAX_SEQUENCE):
        raise ValueError("Invalid last sequence")
    found: set[int] = set()
    for n, item in enumerate(sequences, 1):
        if n > max_observations:
            raise ValueError("journal.observation_limit")
        found.add(item)
    seen = sorted(found)
    if any(type(n) is not int or not 1 <= n <= MAX_SEQUENCE for n in seen):
        raise ValueError("Invalid observed sequence")
    out: list[SequenceRange] = []
    pos = start
    for number in seen:
        if number < pos:
            continue
        if number > pos:
            out.append(SequenceRange(pos, number - 1))
        pos = number + 1
        if len(out) > MAX_RANGES:
            raise ValueError("journal.interval_limit")
    if expected_last is not None and expected_last >= pos:
        out.append(SequenceRange(pos, expected_last))
    return tuple(out)


def _range_contains(ranges: tuple[SequenceRange, ...], number: int) -> bool:
    return any(item.first <= number <= item.last for item in ranges)


@dataclass(frozen=True, slots=True)
class CaptureCoverage:
    invocation_id: str
    scope_id: str
    producer_last_sequence: int | None
    seen_ranges: tuple[SequenceRange, ...]
    policy_excluded_ranges: tuple[SequenceRange, ...] = ()
    lost_ranges: tuple[SequenceRange, ...] = ()
    unknown_loss_count: int = 0
    producer_dropped_count: int | None = None
    terminal_seen: bool = False
    generation_id: str | None = None
    evidence_quality: Literal["collector_observed", "producer_attested", "claimed"] = "claimed"
    start_seen: bool = False

    def __post_init__(self) -> None:
        for token in (self.invocation_id, self.scope_id, self.generation_id):
            if token is not None:
                safe_token(token)
        if self.producer_last_sequence is not None and (type(self.producer_last_sequence) is not int
                or not 0 <= self.producer_last_sequence <= MAX_SEQUENCE):
            raise ValueError("Invalid producer sequence")
        for value in (self.unknown_loss_count, self.producer_dropped_count):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Invalid loss counter")
        if self.evidence_quality not in {"collector_observed", "producer_attested", "claimed"}:
            raise ValueError("Invalid evidence quality")
        seen, excluded, lost = map(merge_ranges, (self.seen_ranges, self.policy_excluded_ranges, self.lost_ranges))
        if subtract_ranges(excluded, seen):
            raise ValueError("Excluded sequences must have been observed by collector")
        if intersect_ranges(excluded, lost):
            raise ValueError("Filtered events cannot also be reported lost")
        object.__setattr__(self, "seen_ranges", seen)
        object.__setattr__(self, "policy_excluded_ranges", excluded)
        object.__setattr__(self, "lost_ranges", lost)


CoverageEvidence = CaptureCoverage


@dataclass(frozen=True, slots=True)
class CoverageAssessment:
    status: CoverageStatus
    scope_id: str
    missing_ranges: tuple[SequenceRange, ...]
    missing_total: int
    explained_filter_ranges: tuple[SequenceRange, ...]
    known_loss_ranges: tuple[SequenceRange, ...]
    unknown_loss_count: int
    reasons: tuple[str, ...]


def assess_coverage(accepted_sequences: Iterable[int], evidence: CaptureCoverage | None, *,
                    start_seen: bool, terminal_seen: bool) -> CoverageAssessment:
    accepted = tuple(sorted(set(accepted_sequences)))
    end = evidence.producer_last_sequence if evidence else None
    missing = find_gaps(accepted, expected_last=end)
    if evidence is None:
        return CoverageAssessment("indeterminate", "unspecified", missing, count_ranges(missing), (), (), 0,
                                  ("journal.coverage_unverified",))
    excluded = evidence.policy_excluded_ranges
    unexplained = subtract_ranges(missing, excluded)
    reasons: set[str] = set()
    if evidence.evidence_quality != "collector_observed":
        reasons.add("journal.coverage_unverified")
    if end is None:
        reasons.add("journal.producer_tail_unknown")
    if not start_seen or not evidence.start_seen:
        reasons.add("journal.start_missing")
    if not terminal_seen or not evidence.terminal_seen:
        reasons.add("journal.finish_missing")
    if subtract_ranges(excluded, evidence.seen_ranges):
        reasons.add("journal.exclusion_unverified")
    accepted_ranges = merge_ranges(SequenceRange(seq, seq) for seq in accepted)
    if subtract_ranges(accepted_ranges, evidence.seen_ranges) or intersect_ranges(accepted_ranges, excluded):
        reasons.add("journal.collector_inconsistent")
    if unexplained:
        reasons.add("journal.sequence_gap")
    if evidence.lost_ranges or evidence.unknown_loss_count or (evidence.producer_dropped_count or 0):
        reasons.add("journal.capture_loss")
    if end is not None and accepted and max(accepted) > end:
        reasons.add("journal.producer_counter_conflict")
    if end is not None and evidence.seen_ranges and evidence.seen_ranges[-1].last > end:
        reasons.add("journal.producer_counter_conflict")
    if any(x.startswith("journal.") and x not in {"journal.coverage_unverified", "journal.producer_tail_unknown"}
           for x in reasons):
        status: CoverageStatus = "incomplete"
    elif reasons:
        status = "indeterminate"
    else:
        status = "complete"
    return CoverageAssessment(status, evidence.scope_id, missing, count_ranges(missing),
                              excluded, evidence.lost_ranges, evidence.unknown_loss_count,
                              tuple(sorted(reasons)))


@dataclass(frozen=True, slots=True)
class GenerationCaptureAssessment:
    """Qualified aggregate: numerical gaps stay local to their invocation."""
    scope_id: str
    generation_id: str
    status: CoverageStatus
    invocation_count: int
    complete_count: int
    incomplete_count: int
    indeterminate_count: int
    total_missing_events: int
    total_unknown_losses: int
    assessments_digest: str
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        safe_token(self.scope_id)
        safe_token(self.generation_id)
        if self.status not in {"complete", "incomplete", "indeterminate"}:
            raise ValueError("journal.generation_status_invalid")
        for name in ("invocation_count", "complete_count", "incomplete_count",
                     "indeterminate_count", "total_missing_events", "total_unknown_losses"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError("journal.generation_count_invalid")
        if self.complete_count + self.incomplete_count + self.indeterminate_count != self.invocation_count:
            raise ValueError("journal.generation_counts_inconsistent")
        if len(self.assessments_digest) != 64 or any(x not in "0123456789abcdef" for x in self.assessments_digest):
            raise ValueError("journal.generation_digest_invalid")
        if len(self.reasons) > 32 or any(not isinstance(x, str) or len(x) > 128 for x in self.reasons):
            raise ValueError("journal.generation_reasons_invalid")
