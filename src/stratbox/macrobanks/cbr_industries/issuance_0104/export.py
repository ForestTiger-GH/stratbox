"""Three-sheet monthly issuance workbooks reusing the shared CBR region renderer."""

from __future__ import annotations

from openpyxl import Workbook
from openpyxl.styles import Font

from stratbox.base.ioapi.workbook_bytes import openpyxl_bytes
from stratbox.data import Representation
from stratbox.data.representation import XLSX
from stratbox.macrobanks.cbr_industries.export import (
    _industry_table_dates, _write_cbr_industry_sheet,
)

from .contracts import IssuanceWorkbookResult
from .parser import _SHEETS
from .sources import reference_period


def render_issuance_workbook(pivots, *, industry_code: str, industry_name_ru: str,
                             reference_periods: tuple[str, ...],
                             include_metadata_sheet: bool = False) -> IssuanceWorkbookResult:
    if (pivots.row_dimension != "region_code" or pivots.column_dimension != "report_date"
        or pivots.value_columns != ("value",)
        or set(pivots.sheet_dimensions) != {"measure", "currency_scope"}
        or pivots.table_count != 3):
        raise ValueError("Issuance workbook requires exactly three region-by-report-date tables")
    keyed = {tuple(dict(t.sheet_key).get(k) for k in ("measure", "currency_scope")): t
             for t in pivots.tables}
    expected = {("new_loans", item.currency_scope) for item in _SHEETS}
    if set(keyed) != expected:
        raise ValueError("Issuance sheets do not match the three published indicators")
    dates = _industry_table_dates(pivots.tables[0])
    if any(_industry_table_dates(table) != dates for table in pivots.tables):
        raise ValueError("Issuance sheets disagree on dates")
    actual_periods = tuple(reference_period(x) for x in dates)
    if actual_periods != reference_periods:
        raise ValueError("Reference periods disagree with source dates")
    workbook = Workbook()
    workbook.remove(workbook.active)
    try:
        if include_metadata_sheet:
            metadata = workbook.create_sheet("_Параметры")
            metadata.append(("Параметр", "Значение"))
            metadata.append(("Серия", "01_04_A_New_loans_corp"))
            metadata.append(("Отрасль", industry_name_ru))
            metadata.append(("Код отрасли", industry_code))
            metadata.append(("Первый отчетный месяц", actual_periods[0]))
            metadata.append(("Последний отчетный месяц", actual_periods[-1]))
            metadata.append(("Количество периодов", len(actual_periods)))
            metadata.append(("Единица измерения", "млн руб."))
            metadata.append(("Дата публикации", "Первое число следующего месяца"))
            metadata.column_dimensions["A"].width = 30
            metadata.column_dimensions["B"].width = 54
            metadata.freeze_panes = "A2"
            metadata.sheet_view.showGridLines = False
            for cell in metadata[1]:
                cell.font = Font(bold=True)
        label = ("расчетному отраслевому агрегату АПК" if industry_code == "apk"
                 else "всем видам деятельности" if industry_code == "total"
                 else f"отрасли «{industry_name_ru}»")
        subtitle = (f"Выдачи за отчетные месяцы {actual_periods[0]} — {actual_periods[-1]}; "
                    "дата исходного файла — первое число следующего месяца")
        for spec in _SHEETS:
            table = keyed[("new_loans", spec.currency_scope)]
            _write_cbr_industry_sheet(
                workbook, table=table, sheet_name=spec.workbook_sheet_name,
                title=("Объем кредитов, предоставленных юридическим лицам-резидентам "
                       f"и ИП, по {label}, {spec.currency_scope_name_ru.lower()}, "
                       "в региональном разрезе, млн руб."),
                subtitle=subtitle, dates=dates,
            )
            sheet = workbook[spec.workbook_sheet_name]
            for index, month in enumerate(actual_periods, start=2):
                yyyy, mm = month.split("-")
                sheet.cell(3, index, f"{mm}.{yyyy}")
        data = openpyxl_bytes(workbook, literal_text=True)
    finally:
        workbook.close()
    names = tuple(("_Параметры",) if include_metadata_sheet else ()) + tuple(
        item.workbook_sheet_name for item in _SHEETS)
    return IssuanceWorkbookResult(
        Representation("cbr.industries.0104a.industry-xlsx", 1, XLSX, data),
        industry_code, industry_name_ru, names, dates, actual_periods,
        pivots.tables[0].rows,
    )
