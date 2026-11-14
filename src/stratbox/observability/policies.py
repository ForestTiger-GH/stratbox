"""Selection, persistence and presentation policies are independent choices."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from .contracts import JournalRecord, Reliability


@dataclass(frozen=True, slots=True)
class CapturePolicy:
    record_types: frozenset[str] | None = None
    kinds: frozenset[str] | None = None
    progress: bool = False
    max_records: int = 10000

    def __post_init__(self):
        if self.max_records < 1:
            raise ValueError("max_records must be positive")

    def accepts(self, record: JournalRecord) -> bool:
        return (self.record_types is None or record.record_type in self.record_types) and (
            self.kinds is None or record.kind in self.kinds) and (
            self.progress or record.kind != "operation.progress")


@dataclass(frozen=True, slots=True)
class PersistencePolicy:
    reliability: Reliability = "durable"
    format: Literal["jsonl", "json"] = "jsonl"
    max_buffer_records: int = 256
    max_buffer_bytes: int = 1024 * 1024

    def __post_init__(self):
        if self.reliability not in {"best_effort", "durable", "required"} or self.format not in {"jsonl", "json"}:
            raise ValueError("Invalid persistence policy")
        if self.max_buffer_records <= 0 or self.max_buffer_bytes < 4096:
            raise ValueError("Invalid journal buffer limits")


@dataclass(frozen=True, slots=True)
class PresentationPolicy:
    include_progress: bool = False
    include_diagnostics: bool = True
