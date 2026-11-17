"""One bounded lifecycle validator for in-memory and recovered executions.

Only execution envelopes constitute lifecycle evidence. Sequence ordering is local
within an invocation; time ordering and storage digests are not substitutes.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Iterable, Mapping

from .contracts import JournalRecord


@dataclass(frozen=True, slots=True)
class ExecutionLifecycleAssessment:
    invocation_id: str
    operation_id: str | None
    accepted_sequences: tuple[int, ...]
    start_seen: bool
    terminal_seen: bool
    start_sequence: int | None
    terminal_sequence: int | None
    problems: tuple[str, ...]

    @property
    def structurally_valid(self) -> bool:
        return not self.problems


def inspect_execution_lifecycle(
    records: Iterable[JournalRecord], invocation_id: str, *,
    max_records: int = 100_000,
) -> ExecutionLifecycleAssessment:
    """Detect structure conflicts before numeric coverage collapses duplicate sequence IDs."""
    if not 1 <= max_records <= 1_000_000:
        raise ValueError("journal.lifecycle_limit_invalid")
    by_id: dict[str, JournalRecord] = {}
    sequences: dict[int, str] = {}
    operations: set[str] = set()
    starts: list[int] = []
    finishes: list[int] = []
    problems: set[str] = set()
    count = 0
    for record in records:
        if record.record_type != "execution" or record.invocation_id != invocation_id:
            continue
        count += 1
        if count > max_records:
            problems.add("journal.lifecycle_truncated")
            break
        previous = by_id.get(record.record_id)
        if previous is not None:
            if previous != record:
                problems.add("journal.record_identity_conflict")
            continue
        by_id[record.record_id] = record
        seq = record.sequence
        if seq is None:
            problems.add("journal.sequence_invalid")
            continue
        if seq in sequences and sequences[seq] != record.record_id:
            problems.add("journal.sequence_conflict")
        sequences[seq] = record.record_id
        if record.operation_id:
            operations.add(record.operation_id)
        if record.kind == "operation.started":
            starts.append(seq)
        elif record.kind == "operation.finished":
            finishes.append(seq)
        elif record.kind not in {"operation.stage", "operation.progress"}:
            problems.add("journal.execution_kind_invalid")
        payload = record.payload
        if isinstance(payload, Mapping):
            for name, expected in (("invocation_id", invocation_id),
                                   ("operation_id", record.operation_id),
                                   ("sequence", seq), ("kind", record.kind)):
                if name in payload and payload[name] != expected:
                    problems.add("journal.execution_envelope_mismatch")
    if len(operations) > 1:
        problems.add("journal.operation_identity_conflict")
    if not starts:
        problems.add("journal.start_missing")
    if not finishes:
        problems.add("journal.finish_missing")
    if len(starts) > 1 or len(finishes) > 1:
        problems.add("journal.lifecycle_conflict")
    if starts and starts[0] != 1:
        problems.add("journal.start_position_invalid")
    if finishes and sequences and finishes[0] != max(sequences):
        problems.add("journal.finish_position_invalid")
    return ExecutionLifecycleAssessment(
        invocation_id, next(iter(operations)) if len(operations) == 1 else None,
        tuple(sorted(sequences)), len(starts) == 1, len(finishes) == 1,
        starts[0] if len(starts) == 1 else None,
        finishes[0] if len(finishes) == 1 else None, tuple(sorted(problems)),
    )


def assess_invocation_lifecycle(records: Iterable[JournalRecord], invocation_id: str, coverage=None):
    """Combine structural and numerical proof, without granting completeness on a mere claim."""
    from .coverage import assess_coverage
    lifecycle = inspect_execution_lifecycle(records, invocation_id)
    numeric = assess_coverage(lifecycle.accepted_sequences, coverage,
                              start_seen=lifecycle.start_seen, terminal_seen=lifecycle.terminal_seen)
    structural = set(lifecycle.problems) - {"journal.start_missing", "journal.finish_missing"}
    if (coverage is not None and coverage.producer_last_sequence is not None
            and lifecycle.terminal_sequence is not None
            and lifecycle.terminal_sequence != coverage.producer_last_sequence):
        structural.add("journal.producer_tail_after_finish")
    if structural:
        status = "incomplete"
    elif numeric.status == "complete" and not lifecycle.problems:
        status = "complete"
    else:
        status = numeric.status
    if structural != set(lifecycle.problems) - {"journal.start_missing", "journal.finish_missing"}:
        from dataclasses import replace
        lifecycle = replace(lifecycle, problems=tuple(sorted(set(lifecycle.problems) | structural)))
    return lifecycle, numeric, status


def assess_generation_coverage(records: Iterable[JournalRecord], evidence, *, scope_id: str,
                               generation_id: str, max_records: int = 100_000,
                               max_invocations: int = 10_000):
    """Single record index; strict invocation set equality; deterministic scoped digest."""
    from collections import defaultdict
    from hashlib import sha256
    import json
    from .coverage import GenerationCaptureAssessment

    index = defaultdict(list)
    for n, rec in enumerate(records, 1):
        if n > max_records:
            raise ValueError("journal.generation_record_limit")
        if rec.record_type == "execution" and rec.invocation_id:
            index[rec.invocation_id].append(rec)
            if len(index) > max_invocations:
                raise ValueError("journal.generation_invocation_limit")
    expected = {}
    reasons: set[str] = set()
    for item in evidence:
        if item.invocation_id in expected:
            reasons.add("journal.coverage_duplicate_invocation")
        expected[item.invocation_id] = item
        if len(expected) > max_invocations:
            raise ValueError("journal.generation_invocation_limit")
        if item.scope_id != scope_id:
            reasons.add("journal.coverage_scope_mismatch")
        if item.generation_id != generation_id:
            reasons.add("journal.generation_unbound" if item.generation_id is None else "journal.generation_mismatch")
    unexpected = set(index) - set(expected)
    absent = set(expected) - set(index)
    if unexpected:
        reasons.add("journal.uncovered_invocation")
    if absent:
        reasons.add("journal.unobserved_invocation")
    details = []
    counts = {"complete": 0, "incomplete": 0, "indeterminate": 0}
    missing = unknown = 0
    for invocation in sorted(set(index) | set(expected)):
        items = expected.get(invocation)
        if invocation not in index or items is None:
            status = "incomplete"
            local_reasons = ("journal.invocation_set_mismatch",)
            lost = unknown_loss = 0
        else:
            lc, numerical, status = assess_invocation_lifecycle(index[invocation], invocation, items)
            lost = numerical.missing_total
            unknown_loss = numerical.unknown_loss_count
            local_reasons = tuple(sorted(set(lc.problems) | set(numerical.reasons)))
        counts[status] += 1
        missing += lost
        unknown += unknown_loss
        details.append((invocation, status, local_reasons, lost, unknown_loss))
        reasons.update(local_reasons)
    if not details:
        status = "indeterminate"
        reasons.add("journal.capture_scope_empty")
    elif counts["incomplete"] or reasons.intersection({
        "journal.uncovered_invocation", "journal.unobserved_invocation",
        "journal.coverage_duplicate_invocation", "journal.generation_mismatch",
        "journal.coverage_scope_mismatch"}):
        status = "incomplete"
    elif counts["indeterminate"] or reasons:
        status = "indeterminate"
    else:
        status = "complete"
    digest = sha256(json.dumps(details, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    return GenerationCaptureAssessment(scope_id, generation_id, status, len(details),
                                       counts["complete"], counts["incomplete"],
                                       counts["indeterminate"], missing, unknown,
                                       digest, tuple(sorted(reasons))[:32])
