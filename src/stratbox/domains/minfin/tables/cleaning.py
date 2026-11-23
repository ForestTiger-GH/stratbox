"""Deterministic source-table cleaning, parameterized by a registered table profile.

No catalogue lookup, network, consumer storage or operation runner occurs here.
"""
from __future__ import annotations
import re
from .periods import normalize_period
from .contracts import BuildFlakeRequest, FlakeColumn, FlakeRow, FlakeTable
from .profiles import TableProfile

def _scalar(cell):
    if cell is None:
        return None
    if cell.kind == "formula":
        return cell.cached
    if cell.kind in {"number", "date", "date_serial", "text", "blank", "error", "boolean"}:
        return cell.value
    return None


def _text(cell) -> str:
    value = _scalar(cell)
    return " ".join(str(value or "").split())


def _periods(cells: dict[tuple[int, int], object], width: int, frequency: str, profile: TableProfile) -> tuple[FlakeColumn, ...]:
    options = []
    for row in range(1, min(profile.max_header_rows + 2, max(4, max((r for r, _ in cells), default=0))) + 1):
        candidate = []
        for col in range(profile.first_period_column, width + 1):
            cell = cells.get((row, col))
            if cell is None:
                continue
            try:
                period = normalize_period(_text(cell), frequency)
            except ValueError:
                continue
            candidate.append(FlakeColumn(col, _text(cell), period))
        if candidate:
            options.append((len(candidate), row, candidate))
    if not options:
        raise ValueError("minfin.flake.no_period_header")
    _, header_row, selected = max(options, key=lambda x: (x[0], -x[1]))
    if not 1 <= header_row <= profile.max_header_rows or len(selected) < profile.minimum_periods:
        raise ValueError("minfin.flake.period_header_unsupported")
    if len({c.period_id for c in selected}) != len(selected):
        raise ValueError("minfin.flake.duplicate_period")
    normalized = [c.period_id for c in selected]
    if normalized != sorted(normalized):
        raise ValueError("minfin.flake.period_order_invalid")
    return tuple(selected)


def build_flake(request: BuildFlakeRequest, *, profile: TableProfile, frequency: str, basis: str) -> FlakeTable:
    extract = request.extract
    if extract.source_id != request.source_id:
        raise ValueError("minfin.flake.source_mismatch")
    if extract.format not in profile.admitted_formats:
        raise ValueError("minfin.flake.format_unsupported")
    if frequency not in {"monthly", "quarterly", "annual"} or basis not in {"ytd", "annual", "stock"}:
        raise ValueError("minfin.flake.source_unsupported")
    if len(extract.sheets) != 1:
        raise ValueError("minfin.flake.one_sheet_required")
    sheet = extract.sheets[0]
    if request.selected_sheet is not None and sheet.name != request.selected_sheet:
        raise ValueError("minfin.flake.sheet_mismatch")
    if sheet.rows > profile.max_rows or sheet.columns > 20_000:
        raise ValueError("minfin.flake.geometry_unsupported")
    cells = {(c.row, c.column): c for c in sheet.cells}
    periods = _periods(cells, sheet.columns, frequency, profile)
    header_row = min((r for r, c in cells if c == periods[0].source_column
                      and _text(cells[(r, c)]) == periods[0].original_header), default=None)
    if header_row is None:
        raise ValueError("minfin.flake.header_missing")
    cleaned = []
    for row in range(header_row + 1, sheet.rows + 1):
        code = _text(cells.get((row, profile.code_column))).strip()
        indicator = _text(cells.get((row, profile.indicator_column))).strip()
        if not indicator or indicator.upper().startswith("РАЗДЕЛ"):
            continue
        # A heading or footnote that is not accompanied by data is not a table row.
        values = tuple(_scalar(cells.get((row, period.source_column))) for period in periods)
        if not any(v is not None and str(v).strip() != "" for v in values):
            continue
        if code and not re.fullmatch(profile.code_pattern, code):
            # Any prefixed footnote or textual decoration belongs outside the table.
            continue
        indicator = re.sub(profile.notes_pattern, "", indicator).strip()
        if not indicator:
            continue
        monetary = profile.unit_hint == "billion_rub" or (
            profile.profile_id == "minfin.nwf_table.v1" and code.rstrip(".") in {"2", "5"})
        cleaned.append(FlakeRow(row, code, indicator,
                                 tuple(str(value) if value is not None else None
                                       for value in values),
                                 "RUB" if monetary else None, "1000000000" if monetary else None,
                                 basis if profile.unit_hint == "billion_rub" else ("stock" if monetary else None)))
    if not cleaned:
        raise ValueError("minfin.flake.no_table_rows")
    return FlakeTable(extract.family_id, extract.source_id, extract.source_identity,
                      sheet.name, frequency, basis, periods, tuple(cleaned),
                      method_version=profile.method_version, unit_hint=profile.unit_hint, publication=extract.publication)