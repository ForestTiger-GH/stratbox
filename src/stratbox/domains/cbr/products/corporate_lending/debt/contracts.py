"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.data.representation import Representation
from stratbox.shared.data.source_context import SourceUse
from stratbox.domains.cbr.tables.corporate_lending.industry.sources import merge_source_uses


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpPivotWorkbookRequest:
    """Запрос на сохранение готового набора pivot-таблиц в одну книгу Excel."""

    freeze_headers: bool = True
    enable_auto_filter: bool = True
    adjust_column_widths: bool = True
    include_metadata_sheet: bool = False


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpPivotWorkbookResult:
    """Результат отдельной операции сохранения Excel-книги."""

    representation: Representation
    sheet_names: tuple[str, ...]
    sheet_count: int
    source_uses: tuple[SourceUse, ...] = ()

    @property
    def ok(self) -> bool:
        return self.sheet_count > 0


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpIndustryWorkbookRequest:
    """Запрос на CBR-подобную книгу динамики одной отрасли по регионам."""

    industry_code: str = "apk"
    calculate_apk_if_missing: bool = True
    include_metadata_sheet: bool = False


@dataclass(frozen=True, slots=True)
class Cbr0105ADebtCorpIndustryWorkbookResult:
    """Результат экспорта одной отрасли в шестилистовую CBR-подобную книгу."""

    representation: Representation
    industry_code: str
    industry_name_ru: str
    sheet_names: tuple[str, ...]
    sheet_count: int
    dates: tuple[str, ...]
    rows_per_sheet: int
    source_uses: tuple[SourceUse, ...] = ()

    @property
    def ok(self) -> bool:
        return (
            bool(self.industry_code)
            and self.sheet_count == 6
            and self.rows_per_sheet > 0
        )


@dataclass(frozen=True)
class IndustryWorkbooksResult:
    items: tuple[Cbr0105ADebtCorpIndustryWorkbookResult, ...]
    source_uses: tuple[SourceUse, ...] = ()

    def __post_init__(self):
        actual = merge_source_uses(*(item.source_uses for item in self.items))
        if self.source_uses and self.source_uses != actual:
            raise ValueError("industry.workbook_sources_invalid")
        object.__setattr__(self, "source_uses", actual)

    @property
    def ok(self) -> bool:
        return bool(self.items) and all(item.ok for item in self.items)
