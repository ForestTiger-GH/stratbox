"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.data.representation import Representation
from stratbox.shared.data.source_context import SourceUse
from stratbox.domains.cbr.tables.corporate_lending.industry.sources import merge_source_uses


@dataclass(frozen=True)
class IssuanceWorkbookResult:
    representation: Representation
    industry_code: str
    industry_name_ru: str
    sheet_names: tuple[str, ...]
    dates: tuple[str, ...]
    reference_periods: tuple[str, ...]
    rows_per_sheet: int
    source_uses: tuple[SourceUse, ...] = ()

    @property
    def sheet_count(self) -> int:
        return sum(name != "_Параметры" for name in self.sheet_names)

    @property
    def ok(self) -> bool:
        return self.sheet_count == 3 and self.rows_per_sheet > 0


@dataclass(frozen=True)
class IssuanceWorkbooksResult:
    items: tuple[IssuanceWorkbookResult, ...]
    source_uses: tuple[SourceUse, ...] = ()

    def __post_init__(self):
        actual = merge_source_uses(*(item.source_uses for item in self.items))
        if self.source_uses and self.source_uses != actual:
            raise ValueError("industry.workbook_sources_invalid")
        object.__setattr__(self, "source_uses", actual)

    @property
    def ok(self) -> bool:
        return bool(self.items) and all(item.ok for item in self.items)
