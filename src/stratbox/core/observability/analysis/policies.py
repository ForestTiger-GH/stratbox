"""Human-facing projection and CSV presentation policies."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True, slots=True)
class PresentationPolicy:
    include_progress: bool = False
    include_diagnostics: bool = True
    audience: Literal["summary", "technical"] = "summary"
    csv_mode: Literal["spreadsheet_safe", "machine"] = "spreadsheet_safe"
    permitted_columns: tuple[str, ...] = ()

    def __post_init__(self):
        if self.audience not in {"summary", "technical"} or self.csv_mode not in {"spreadsheet_safe", "machine"}:
            raise ValueError("Invalid presentation mode")
        if len(set(self.permitted_columns)) != len(self.permitted_columns):
            raise ValueError("Duplicate export columns")


