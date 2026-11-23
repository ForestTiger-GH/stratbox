"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.data.representation import Representation


@dataclass(frozen=True)
class IssuanceWorkbookResult:
    representation: Representation
    industry_code: str
    industry_name_ru: str
    sheet_names: tuple[str, ...]
    dates: tuple[str, ...]
    reference_periods: tuple[str, ...]
    rows_per_sheet: int

    @property
    def sheet_count(self) -> int:
        return sum(name != "_Параметры" for name in self.sheet_names)

    @property
    def ok(self) -> bool:
        return self.sheet_count == 3 and self.rows_per_sheet > 0


@dataclass(frozen=True)
class IssuanceWorkbooksResult:
    items: tuple[IssuanceWorkbookResult, ...]

    @property
    def ok(self) -> bool:
        return bool(self.items) and all(item.ok for item in self.items)
