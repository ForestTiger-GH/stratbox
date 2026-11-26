"""Reviewed publisher layouts with source-native geography and exact periods.

Population editions 2022/2023 have names but no territorial codes. Edition 2024
adds TERSON-MO codes; these are retained as publisher codes, without asserting
an OKTMO crosswalk. Regional industrial indices preserve monthly and cumulative
comparison bases separately. Other layouts require explicit reviewed mappings.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
import re

from stratbox.shared.data.coverage import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import canonical_manifest_bytes
from .types import SourceTable, SourceValue, RowDecision, SectionEvidence
from .kep2 import numeric_token, _raw

POPULATION_EDITIONS = {
    2022: ("Таб_27", 9, 1, (2, 3, 4), None),
    2023: ("Численность_по_МО", 9, 1, (2, 3, 4), None),
    2024: ("Численность_по_МО", 8, 2, (3, 4, 5), 1),
}
_MONTHS = ("январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь")
_INDEX_SHEETS = (
    (" к соотв. месяцу", "В % к соответствующему месяцу предыдущего года", "year_on_year_index", "monthly", "same_month_previous_year"),
    ("к соотв. периоду", "В % к соответствующему периоду предыдущего года", "year_on_year_index", "ytd", "same_year_to_date_previous_year"),
    ("к пред. месяцу", "В % к предыдущему месяцу", "previous_period_index", "monthly", "previous_month"),
)


def _cells(sheet):
    return {(cell.row, cell.column): cell for cell in sheet.cells}


def _text(cell):
    return str(cell.value or "").strip() if cell is not None else ""


def _lineage(workbook):
    return (*workbook.lineage, UsedInputReceipt("physical_workbook", workbook.identity, "application/vnd.stratbox.dataset", "inline"))


def extract_population(workbook, *, selected_rows=(), checkpoint=None):
    """Read the three actual annual bulletin layouts under their native edition."""
    if workbook.series_id != "rosstat.population_municipalities":
        raise ValueError("rosstat.population_series_mismatch")
    title = next((sheet for sheet in workbook.sheets if sheet.name == "Титул"), None)
    if title is None:
        raise ValueError("rosstat.population_title_missing")
    label = _text(_cells(title).get((14, 2)))
    match = re.fullmatch(r"НА 1 ЯНВАРЯ\s+(\d{4}) года", label)
    if match is None or int(match[1]) not in POPULATION_EDITIONS:
        raise ValueError("rosstat.population_layout_unsupported")
    year = int(match[1])
    if workbook.issue_id != str(year):
        raise ValueError("rosstat.population_issue_date_mismatch")
    name, first_row, label_column, columns, code_column = POPULATION_EDITIONS[year]
    sheet = next((sheet for sheet in workbook.sheets if sheet.name == name), None)
    if sheet is None:
        raise ValueError("rosstat.population_table_missing")
    cells = _cells(sheet)
    title_row, title_column = (3, 2) if year == 2024 else (4, 1)
    if _text(cells.get((title_row, title_column))) != "ПО МУНИЦИПАЛЬНЫМ ОБРАЗОВАНИЯМ на 1 января " + str(year) + " года":
        raise ValueError("rosstat.population_stock_date_unreviewed")
    header = 6 if year == 2024 else 7
    if tuple(_text(cells.get((header, column))) for column in columns) != ("население", "городское", "сельское"):
        raise ValueError("rosstat.population_columns_unreviewed")
    if _text(cells.get((header + 1, columns[0]))) != "(человек)":
        raise ValueError("rosstat.population_units_unreviewed")
    if year == 2024 and (_text(cells.get((6, 1))), _text(cells.get((7, 1)))) != ("Коды территорий", "ТЕРСОН-МО"):
        raise ValueError("rosstat.population_code_system_unreviewed")
    if (not isinstance(selected_rows, tuple) or len(set(selected_rows)) != len(selected_rows)
            or any(type(row) is not int or not first_row <= row <= sheet.rows for row in selected_rows)):
        raise ValueError("rosstat.population_selection_invalid")
    rows = selected_rows or tuple(sorted({row for row, column in cells if column == label_column and row >= first_row}))
    if checkpoint is not None:
        checkpoint()
    values, decisions, diagnostics = [], [], []
    edition = "rosstat.population." + str(year)
    for row in rows:
        if checkpoint is not None:
            checkpoint()
        literal = _text(cells.get((row, label_column)))
        if not literal:
            if selected_rows:
                raise ValueError("rosstat.population_selected_row_missing")
            continue
        source_cells = {str(column): _raw(cells.get((row, column))) for column in (label_column, *columns, *((code_column,) if code_column else ()))}
        code = _raw(cells.get((row, code_column))) if code_column else None
        # Row membership remains part of source-native identity: actual 2024
        # originals contain repeated/annotated TERSON-MO codes.
        namespace = "rosstat.terson-mo" if code_column else "rosstat.population.row"
        identifier = code or (str(year) + ":" + str(row))
        scope = "publisher.population." + str(year) + ".row." + str(row)
        dimensions = (("geography_edition", edition), ("source_geography_label", literal),
            ("source_geography_code", code or ""), ("source_row", str(row)))
        for column, category in zip(columns, ("total", "urban", "rural")):
            cell = cells.get((row, column))
            raw = _raw(cell)
            value, status, footnotes = numeric_token(raw, formula_without_cache=bool(cell and cell.formula and cell.value is None))
            if status == "unparsed":
                diagnostics.append("rosstat.population.unparsed:" + str(row) + ":" + str(column))
            if value is not None and (value < 0 or value != value.to_integral_value()):
                raise ValueError("rosstat.population_count_invalid")
            values.append(SourceValue("population", "Permanent population", category, "annual",
                date(year, 1, 1), date(year, 1, 1), date(year, 1, 1), value, status, raw,
                "(человек)", "person", Decimal(1), "count", namespace, identifier,
                sheet.name + "!" + (cell.coordinate if cell else "R" + str(row) + "C" + str(column)),
                sheet.name, row, column, footnotes, dimensions, scope, "as_of",
                cell.kind if cell else "absent", cell.number_format if cell else "General", cell.formula if cell else None,
                str(year), label))
        decisions.append(RowDecision("population", "total_urban_rural", sheet.name, row, year, True,
            "explicit_source_rows" if selected_rows else "published_population_row", canonical_manifest_bytes(source_cells).decode()))
    if not values:
        raise ValueError("rosstat.population_values_required")
    if selected_rows and len(decisions) != len(selected_rows):
        raise ValueError("rosstat.population_selection_incomplete")
    coverage = "complete" if not diagnostics and (selected_rows or workbook.coverage.status == "complete") else "partial"
    publisher_notes = tuple(_text(cell) for source_sheet in workbook.sheets if source_sheet.name == "Предисловие"
        for cell in source_sheet.cells if cell.value is not None and cell.row >= 4)
    section = SectionEvidence("population", "total_urban_rural", sheet.name, title_row, None, first_row, sheet.rows,
        label, tuple(_text(cells.get((header, column))) for column in columns), "(человек)",
        (*publisher_notes, "Nested publisher territorial rows are separate source facts; totals and descendants must not be summed together.",
         "TERSON-MO codes and names-only editions require an explicit reviewed crosswalk for canonical municipal geography."))
    return SourceTable(workbook.series_id, workbook.issue_id, workbook.asset_id,
        workbook.source_identity, workbook.identity, "rosstat.population.bulletin", tuple(values), (section,),
        tuple(decisions), _lineage(workbook), SnapshotCoverage(coverage,
            "Exact total, urban and rural stock counts from the explicitly selected source rows; territorial edition " + edition + "."), tuple(diagnostics))


def extract_regional_industrial_indices(workbook, *, selected_rows=(), selected_years=(), checkpoint=None):
    """Interpret the reviewed three-sheet regional industrial index workbook."""
    if workbook.series_id not in {"rosstat.socioeconomic_regions", "rosstat.socioeconomic_regions.industrial_production"}:
        raise ValueError("rosstat.regional_series_mismatch")
    if not re.fullmatch(r"2026-(06|08)", workbook.issue_id):
        raise ValueError("rosstat.regional_index_edition_unsupported")
    if tuple(sheet.name for sheet in workbook.sheets) != tuple(item[0] for item in _INDEX_SHEETS):
        raise ValueError("rosstat.regional_index_sheets_unreviewed")
    for selection in (selected_rows, selected_years):
        if not isinstance(selection, tuple) or len(set(selection)) != len(selection) or any(type(value) is not int for value in selection):
            raise ValueError("rosstat.regional_index_selection_invalid")
    values, sections, diagnostics = [], [], []
    for ordinal, (sheet, (name, basis, measure, frequency, comparison)) in enumerate(zip(workbook.sheets, _INDEX_SHEETS)):
        cells = _cells(sheet)
        title = _text(cells.get((1, 1)))
        if ((ordinal == 0 and title != "Индекс промышленного производства1")
                or (ordinal > 0 and title != "продолжение")):
            raise ValueError("rosstat.regional_index_title_unreviewed")
        if _text(cells.get((2, 1))) != basis:
            raise ValueError("rosstat.regional_index_basis_unreviewed")
        notes = tuple(_text(cell) for (row, column), cell in cells.items() if column == 1 and row > 100 and _text(cell))
        periods = []
        year = None
        for column in range(2, sheet.columns + 1):
            value = _text(cells.get((3, column)))
            if value:
                match = re.fullmatch(r"(\d{4}) год", value)
                if match is None:
                    raise ValueError("rosstat.regional_index_year_unreviewed")
                year = int(match[1])
            if year is None or not 2016 <= year <= 2026:
                raise ValueError("rosstat.regional_index_year_unreviewed")
            month = (column - 2) % 12 + 1
            literal = _text(cells.get((4, column)))
            expected = _MONTHS[month - 1] if frequency == "monthly" or month == 1 else "январь-" + _MONTHS[month - 1]
            if literal != expected:
                raise ValueError("rosstat.regional_index_period_unreviewed")
            if not selected_years or year in selected_years:
                periods.append((column, year, month, literal))
        if selected_years and set(selected_years) - {year for _, year, _, _ in periods}:
            raise ValueError("rosstat.regional_index_year_missing")
        rows = selected_rows or tuple(range(5, 101))
        if any(not 5 <= row <= 100 for row in rows):
            raise ValueError("rosstat.regional_index_row_unreviewed")
        if checkpoint is not None:
            checkpoint()
        for row in rows:
            if checkpoint is not None:
                checkpoint()
            literal_label = _text(cells.get((row, 1)))
            if not literal_label:
                raise ValueError("rosstat.regional_index_geography_missing")
            label = re.sub(r"[12]$", "", literal_label).strip()
            for column, year, month, literal in periods:
                cell = cells.get((row, column))
                raw = _raw(cell)
                value, status, footnotes = numeric_token(raw, formula_without_cache=bool(cell and cell.formula and cell.value is None))
                if status == "unparsed":
                    diagnostics.append("rosstat.regional_index.unparsed:" + sheet.name + ":" + str(row) + ":" + str(column))
                start = date(year, 1 if frequency == "ytd" else month, 1)
                end = date(year, month, monthrange(year, month)[1])
                dimensions = (("comparison_basis", comparison), ("geography_edition", "rosstat.regional-industrial.2026"),
                    ("source_geography_label", literal_label), ("source_period_label", literal))
                values.append(SourceValue("industrial_production", "Industrial production index", measure, frequency,
                    start, end, end, value, status, raw, basis, "percent", Decimal(1), "index",
                    "rosstat.region.label", label, sheet.name + "!" + (cell.coordinate if cell else "R" + str(row) + "C" + str(column)),
                    sheet.name, row, column, (*footnotes, *notes), dimensions, "publisher.regional-industrial." + label,
                    "interval", cell.kind if cell else "absent", cell.number_format if cell else "General", cell.formula if cell else None,
                    str(year), literal))
        sections.append(SectionEvidence("industrial_production", measure, sheet.name, 1, 2, 5, 100, title,
            tuple(period[3] for period in periods), basis, notes))
    if not values:
        raise ValueError("rosstat.regional_index_values_required")
    coverage = "complete" if not diagnostics and (workbook.coverage.status == "complete" or selected_rows and selected_years) else "partial"
    return SourceTable(workbook.series_id, workbook.issue_id, workbook.asset_id,
        workbook.source_identity, workbook.identity, "rosstat.regional.industrial_indices", tuple(values), tuple(sections), (),
        _lineage(workbook), SnapshotCoverage(coverage,
            "Reviewed three-sheet industrial index layout; monthly and YTD bases remain distinct; source labels retain publisher geography."), tuple(diagnostics))
