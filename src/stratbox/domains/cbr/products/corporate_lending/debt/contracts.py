"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.data.representation import Representation


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

    @property
    def ok(self) -> bool:
        return bool(self.items) and all(item.ok for item in self.items)
