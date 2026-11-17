"""Read-only counters for observer degradation; never self-log into a failed sink."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ObserverHealthSnapshot:
    producer_emitted: int | None = None
    producer_dropped: int | None = None
    collector_received: int = 0
    collector_accepted: int = 0
    policy_filtered: int = 0
    collector_dropped: int = 0
    pending_records: int = 0
    pending_bytes: int = 0
    flush_confirmed: int = 0
    flush_failed: int = 0
    flush_unknown: int = 0
    last_confirmed_at_utc: datetime | None = None
    known_gap_count: int = 0
    unknown_gap_count: int = 0
    degraded: bool = False
    tracked_invocations: int = 0
    tracked_sequence_ranges: int = 0
    metadata_overflow_events: int = 0
    retained_receipts: int = 0
    generation_finalized: bool = False

    def __post_init__(self):
        for key in ("producer_emitted", "producer_dropped", "collector_received", "collector_accepted",
                    "policy_filtered", "collector_dropped", "pending_records", "pending_bytes",
                    "flush_confirmed", "flush_failed", "flush_unknown", "known_gap_count", "unknown_gap_count",
                    "tracked_invocations", "tracked_sequence_ranges", "metadata_overflow_events", "retained_receipts"):
            value = getattr(self, key)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Invalid observer health counter")
