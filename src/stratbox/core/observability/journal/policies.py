"""Bounded persistence and batching policies for journal writers."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True, slots=True)
class PersistencePolicy:
    format: Literal["jsonl", "json"] = "jsonl"
    max_buffer_records: int = 256
    max_buffer_bytes: int = 1024 * 1024

    def __post_init__(self):
        if self.format not in {"jsonl", "json"} or not 1 <= self.max_buffer_records <= 100_000 or not 4096 <= self.max_buffer_bytes <= 128 * 1024**2:
            raise ValueError("Invalid journal buffer policy")


