"""Volatile observer snapshot, without implicit persistence assurance."""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from stratbox.core.observability.records.contracts import JournalRecord
if TYPE_CHECKING:
    from stratbox.core.observability.capture.health import ObserverHealthSnapshot

@dataclass(frozen=True, slots=True)
class ObserverGenerationSnapshot:
    records: tuple[JournalRecord, ...]
    health: ObserverHealthSnapshot
    invocation_ids: tuple[str, ...]
    generation_id: str | None
    # An in-memory snapshot is volatile, never automatically storage-confirmed.
