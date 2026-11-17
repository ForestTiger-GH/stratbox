"""Explicit, independent capture, storage batching and presentation policies."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from stratbox.core.observability.records.contracts import JournalRecord


@dataclass(frozen=True, slots=True)
class CapturePolicy:
    record_types: frozenset[str] | None = None
    kinds: frozenset[str] | None = None
    progress: bool = False
    max_records: int = 10_000
    max_bytes: int = 16 * 1024 * 1024

    def __post_init__(self):
        if not 1 <= self.max_records <= 1_000_000 or not 1024 <= self.max_bytes <= 1024**3:
            raise ValueError("Invalid capture limits")

    def classify(self, record: JournalRecord) -> str:
        if self.record_types is not None and record.record_type not in self.record_types:
            return "filtered_by_record_type"
        if self.kinds is not None and record.kind not in self.kinds:
            return "filtered_by_kind"
        if not self.progress and record.kind == "operation.progress":
            return "filtered_by_progress"
        return "accepted"

    def accepts(self, record: JournalRecord) -> bool:
        return self.classify(record) == "accepted"


@dataclass(frozen=True, slots=True)
class ObserverLimits:
    """Hard caps on collection metadata independent from captured byte limits."""
    max_tracked_invocations: int = 10_000
    max_total_sequence_ranges: int = 100_000
    max_ranges_per_invocation: int = 5_000

    def __post_init__(self):
        if not 1 <= self.max_tracked_invocations <= 1_000_000:
            raise ValueError("journal.invocation_budget_invalid")
        if not 1 <= self.max_total_sequence_ranges <= 1_000_000:
            raise ValueError("journal.range_budget_invalid")
        if not 1 <= self.max_ranges_per_invocation <= self.max_total_sequence_ranges:
            raise ValueError("journal.local_range_budget_invalid")
