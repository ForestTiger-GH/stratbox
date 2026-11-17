"""Bounded, explicit evidence counters and sequence tracking."""
from __future__ import annotations
from dataclasses import dataclass
from stratbox.core.execution.contracts import ObservabilitySummary
from stratbox.core.observability.records.contracts import JournalRecord
from stratbox.core.observability.assessment.coverage import CaptureCoverage, SequenceRange, merge_ranges
from stratbox.core.observability.capture.policies import ObserverLimits

@dataclass(slots=True)
class _InvocationTracker:
    seen: list[SequenceRange]
    excluded: list[SequenceRange]
    lost: list[SequenceRange]
    start_seen: bool = False
    terminal_seen: bool = False
    overflowed: bool = False

class _Counter:
    def __init__(self, limits: ObserverLimits):
        self.limits = limits
        self.received = self.accepted = self.filtered = self.dropped_capacity = self.failed = 0
        self.metadata_overflow = 0
        self._invocations: dict[str, _InvocationTracker] = {}
        self._total_ranges = 0

    @property
    def tracked_ranges(self) -> int:
        return self._total_ranges

    @staticmethod
    def _merged_count(items: list[SequenceRange], seq: int) -> tuple[SequenceRange, ...]:
        # Existing intervals are bounded; duplicates and adjacent sequences cost no new slot.
        return merge_ranges((*items, SequenceRange(seq, seq)))

    def observe(self, rec: JournalRecord, *, filtered: bool = False) -> bool:
        if rec.record_type != "execution" or not rec.invocation_id or rec.sequence is None:
            return True
        key = rec.invocation_id
        tracker = self._invocations.get(key)
        if tracker is None:
            if len(self._invocations) >= self.limits.max_tracked_invocations:
                self.metadata_overflow += 1
                return False
            tracker = _InvocationTracker([], [], [])
            self._invocations[key] = tracker
        if tracker.overflowed:
            self.metadata_overflow += 1
            return False
        seen = self._merged_count(tracker.seen, rec.sequence)
        excluded = self._merged_count(tracker.excluded, rec.sequence) if filtered else tuple(tracker.excluded)
        old_count = len(tracker.seen) + len(tracker.excluded) + len(tracker.lost)
        new_count = len(seen) + len(excluded) + len(tracker.lost)
        if new_count > self.limits.max_ranges_per_invocation or (self._total_ranges - old_count + new_count) > self.limits.max_total_sequence_ranges:
            tracker.overflowed = True
            self.metadata_overflow += 1
            return False
        self._total_ranges += new_count - old_count
        tracker.seen = list(seen)
        tracker.excluded = list(excluded)
        tracker.start_seen |= rec.kind == "operation.started"
        tracker.terminal_seen |= rec.kind == "operation.finished"
        return True

    def lost(self, rec: JournalRecord) -> None:
        if rec.record_type != "execution" or not rec.invocation_id or rec.sequence is None:
            return
        tracker = self._invocations.get(rec.invocation_id)
        if tracker is None or tracker.overflowed:
            return
        updated = self._merged_count(tracker.lost, rec.sequence)
        growth = len(updated) - len(tracker.lost)
        if (len(tracker.seen) + len(tracker.excluded) + len(updated) > self.limits.max_ranges_per_invocation
                or self._total_ranges + growth > self.limits.max_total_sequence_ranges):
            tracker.overflowed = True
            self.metadata_overflow += 1
            return
        self._total_ranges += growth
        tracker.lost = list(updated)

    def coverage(self, invocation: str, *, producer: ObservabilitySummary | None,
                 scope_id: str, generation_id: str | None = None) -> CaptureCoverage:
        tracker = self._invocations.get(invocation)
        seen = tuple(tracker.seen) if tracker else ()
        last = producer.emitted + producer.dropped if producer else None
        unknown = int(tracker.overflowed) if tracker else (1 if self.metadata_overflow else 0)
        return CaptureCoverage(invocation, scope_id, last, seen,
                               tuple(tracker.excluded) if tracker else (),
                               tuple(tracker.lost) if tracker else (), unknown,
                               producer.dropped if producer else None,
                               tracker.terminal_seen if tracker else False, generation_id,
                               "collector_observed" if producer is not None and seen and not unknown else "claimed",
                               tracker.start_seen if tracker else False)
