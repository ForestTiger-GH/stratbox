"""Resolve reviewed source axes while retaining measurement qualifications.

Source-label identities remain local to their series, sheet and source section.
A semantic binding identifies an existing measure; it never converts its value.
Unknown periods, units and layout cells remain diagnostics backed by the flake.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import calendar
import re

from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import canonical_manifest_bytes
from stratbox.domains.cbr.publications.catalog import source
from stratbox.domains.cbr.tables.statistics.contracts import TableDiagnostic
from stratbox.domains.cbr.tables.statistics.profiles import table_profile, sheet_variant
from .contracts import ColumnPeriodBinding, InputVersion, RowBinding, StatisticsDataset

_MONTHS = {name: index for index, name in enumerate(
    ("янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"), 1)}
_MONTH_TOKEN = r"(?:янв(?:арь|аря)?|фев(?:раль|раля)?|мар(?:т|та)?|апр(?:ель|еля)?|ма[йя]|июн[ья]?|июл[ья]?|авг(?:уст|уста)?|сен(?:тябрь|тября)?|окт(?:ябрь|ября)?|ноя(?:брь|бря)?|дек(?:абрь|абря)?)\.?"
_SCALES = {"тыс": Decimal(1000), "млн": Decimal(1_000_000), "млрд": Decimal(1_000_000_000)}
_CURRENCY = r"(?:руб(?:\.|лей|ля|ль)?|долл(?:\.|аров|ара|ар)?|\$|usd|rub)"


def _text(value):
    return " ".join(str(value).lower().replace("\xa0", " ").split())


def _date(value):
    if type(value) is datetime:
        return value.date()
    if type(value) is date:
        return value
    if isinstance(value, str):
        for pattern in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(value.strip(), pattern).date()
            except ValueError:
                pass
    return None


def _month_period(year, month, frequency="month", *, start_month=None):
    end_month = month + 2 if frequency == "quarter" else 12 if frequency == "year" else month
    return PeriodRef("interval", start=date(year, start_month or month, 1),
                     end=date(year, end_month, calendar.monthrange(year, end_month)[1]))


def _month(token):
    text = _text(token)
    if re.fullmatch(_MONTH_TOKEN, text):
        return 5 if text.rstrip(".") in {"май", "мая"} else _MONTHS.get(text[:3])
    return None


def _year(value):
    if type(value) in {int, Decimal} and value == int(value) and 1900 <= value <= 2200:
        return int(value)
    match = re.fullmatch(r"((?:19|20|21)\d{2}|2200)(?:\s*г\.?)?", _text(value))
    return int(match[1]) if match else None


def _direct_period(value):
    value = re.sub(r"\*+$", "", value.strip()).strip() if isinstance(value, str) else value
    parsed = _date(value)
    if parsed is not None:
        return PeriodRef("as_of", as_of=parsed)
    if not isinstance(value, str):
        return None
    match = re.fullmatch(rf"({_MONTH_TOKEN})[\s\-–]*((?:19|20|21)\d{{2}}|2200)(?:\s*г\.?)?", _text(value))
    if match:
        return _month_period(int(match[2]), _month(match[1]))
    return None


def _display_period(cell, variant):
    period = _direct_period(cell.value)
    if (period is not None and period.kind == "as_of" and variant.period_basis == "source_interval"
            and type(cell.value) in {date, datetime}):
        # OOXML dates rendered as month/year are explicit monthly labels. A
        # full-date display retains the point date and its flow qualification.
        display = re.sub(r'"[^"]*"', "", cell.number_format.lower())
        if "m" in display and "y" in display and "d" not in display:
            return _month_period(period.as_of.year, period.as_of.month)
    return period


def _short_month_period(value, known):
    if not isinstance(value, str):
        return None
    text = re.sub(r"\*+$", "", _text(value)).strip()
    match = re.fullmatch(rf"({_MONTH_TOKEN})[\s.\-–]*(\d{{2}})", text)
    if not match or not known:
        return None
    years = [(period.as_of or period.end).year for period in known]
    candidates = [year for year in range(min(years) - 1, max(years) + 2) if year % 100 == int(match[2])]
    return _month_period(candidates[0], _month(match[1])) if len(candidates) == 1 else None


def _year_period(year, token, frequency):
    if frequency == "year":
        return _month_period(year, 1, "year")
    text = _text(token)
    if frequency == "month":
        month = _month(text)
        if month is not None:
            return _month_period(year, month)
        match = re.fullmatch(rf"({_MONTH_TOKEN})\s*[-–—]\s*({_MONTH_TOKEN})", text)
        if match:
            first, last = _month(match[1]), _month(match[2])
            if first <= last:
                return _month_period(year, last, start_month=first)
    if frequency == "quarter":
        match = re.fullmatch(r"([1-4])\s*(?:кварт\.?|квартал)", text)
        if match:
            return _month_period(year, (int(match[1]) - 1) * 3 + 1, "quarter")
        if re.fullmatch(r"1\s*полугод(?:\.|ие)?", text):
            return _month_period(year, 6, start_month=1)
        if re.fullmatch(r"9\s*мес(?:\.|яцев)?", text):
            return _month_period(year, 9, start_month=1)
        if text in {"год", "за год"}:
            return _month_period(year, 1, "year")
    return None


def _point(token):
    match = re.fullmatch(r"([A-Z]+)([1-9]\d*)", token)
    column = 0
    for letter in match[1]:
        column = column * 26 + ord(letter) - 64
    return int(match[2]), column


def _merges(sheet):
    return tuple((*_point(value.split(":")[0]), *_point(value.split(":")[-1]))
                 for value in sheet.merged_ranges)


def _cell_value(cell):
    if cell is None or cell.value is None:
        return None, "missing" if cell is not None and cell.formula is not None else "blank", None if cell is None else cell.raw_token
    value = cell.value
    token = cell.raw_token if type(value) in {int, Decimal} else str(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("\xa0", " ")
        if not cleaned:
            return None, "blank", value
        cleaned = re.sub(r"\*+$", "", cleaned).strip()
        if cleaned in {"-", "–", "—"}:
            return None, "dash", value
        if cleaned.lower() in {"...", "…", "н/д", "н.д.", "н.д", "н/д*"}:
            return None, "missing", value
        if cleaned in {"x", "X", "х", "Х"}:
            return None, "withheld", value
        try:
            numeric = Decimal(cleaned.replace(" ", "").replace(",", "."))
            if numeric.is_finite():
                return numeric, "reported", value
        except InvalidOperation:
            pass
        raise ValueError("cbr.statistics.non_numeric_token")
    if type(value) not in {int, Decimal}:
        raise ValueError("cbr.statistics.non_numeric_token")
    return value, "reported", token


def _fact(cell):
    try:
        return _cell_value(cell)[1] != "blank"
    except ValueError:
        return False


@dataclass
class _Axis:
    start: int
    header: int
    periods: dict
    unresolved: set


def _period_axes(sheet, variant, explicit=()):
    """Bind every physical axis, including repeated sections and merged years."""
    grid = {(cell.row, cell.column): cell for cell in sheet.cells}
    rows = defaultdict(list)
    for cell in sheet.cells:
        rows[cell.row].append(cell)
    merged = _merges(sheet)
    axes = {}
    for row, cells in rows.items():
        periods = {cell.column: period for cell in cells if cell.column > 1
                   and (period := _display_period(cell, variant)) is not None}
        if periods:
            for cell in cells:
                if cell.column > 1 and cell.column not in periods:
                    period = _short_month_period(cell.value, tuple(periods.values()))
                    if period is not None:
                        periods[cell.column] = period
        if periods:
            axes[row] = _Axis(row, row, periods, set())
    if variant.period_basis in {"month", "quarter", "year"}:
        for row, cells in rows.items():
            years = {cell.column: year for cell in cells if cell.column > 1
                     and (year := _year(cell.value)) is not None}
            if not years:
                continue
            for first_row, first_col, last_row, last_col in merged:
                if first_row == last_row == row and first_col in years:
                    for column in range(first_col, last_col + 1):
                        years.setdefault(column, years[first_col])
            if variant.period_basis == "year":
                # The annual header contains years only; values resembling years
                # inside a numeric data row are never a second axis.
                if any(cell.column > 1 and cell.value not in (None, "") and _year(cell.value) is None for cell in cells):
                    continue
                axes[row] = _Axis(row, row, {column: _month_period(year, 1, "year")
                                            for column, year in years.items()}, set())
                continue
            next_cells = {cell.column: cell for cell in rows.get(row + 1, ()) if cell.column > 1}
            recognized = {column for column, cell in next_cells.items()
                          if _year_period(2000, cell.value, variant.period_basis) is not None}
            if not recognized:
                continue
            periods = {column: period for column, year in years.items() if column in next_cells
                       and (period := _year_period(year, next_cells[column].value, variant.period_basis)) is not None}
            unknown = (recognized | set(years)) - set(periods)
            axes[row + 1] = _Axis(row, row + 1, periods, unknown)
    ordered = sorted(axes.values(), key=lambda item: item.header)
    explicit_map = {item.column: item.period for item in explicit}
    if any(type(column) is not int or not 1 < column <= sheet.columns for column in explicit_map):
        raise ValueError("cbr.statistics.period_binding_column_invalid")
    combined = []
    for axis in ordered:
        if combined:
            previous = combined[-1]
            first_column = min(previous.periods or previous.unresolved)
            facts_between = any(
                any(cell.column < first_column and isinstance(cell.value, str) and cell.value.strip() for cell in rows[row])
                and any(cell.column >= first_column and _fact(cell) for cell in rows[row])
                for row in range(previous.header + 1, axis.start))
            if not facts_between:
                conflicts = {column for column in previous.periods.keys() & axis.periods.keys()
                             if previous.periods[column] != axis.periods[column]}
                if conflicts - explicit_map.keys():
                    raise ValueError("cbr.statistics.period_axis_ambiguous")
                combined[-1] = _Axis(previous.start, axis.header,
                                     {**previous.periods, **axis.periods}, previous.unresolved | axis.unresolved)
                continue
        combined.append(axis)
    if not combined and explicit_map:
        combined = [_Axis(0, 0, {}, set())]
    # Column-only overrides cannot express different meanings in two blocks.
    for column in explicit_map:
        published = {axis.periods[column] for axis in combined if column in axis.periods}
        if len(published) > 1:
            raise ValueError("cbr.statistics.period_binding_scope_ambiguous")
    for axis in combined:
        axis.periods.update(explicit_map)
        axis.periods = dict(sorted(axis.periods.items()))
        axis.unresolved.difference_update(axis.periods)
    return tuple(combined)


def period_axis(sheet, variant, explicit=()):
    """Expose a single axis; multi-section sheets require the full aligner."""
    axes = _period_axes(sheet, variant, explicit)
    if len(axes) > 1:
        raise ValueError("cbr.statistics.period_axis_ambiguous")
    if not axes:
        return 0, {}
    if axes[0].unresolved:
        raise ValueError("cbr.statistics.period_column_unresolved")
    return axes[0].header, axes[0].periods


def _units(text):
    """Read explicit measurement phrases, not currency/rate words in labels."""
    text = _text(text)
    units = set()
    if "рублей за единицу иностранной валюты" in text:
        return {("RUB_per_foreign_currency", Decimal(1))}
    scaled = list(re.finditer(rf"\b(тыс|млн|млрд)\.?\s*({_CURRENCY}|ед\.?|единиц\w*)", text))
    for match in scaled:
        token = match[2]
        currency = "RUB" if token.startswith("руб") or token == "rub" else "count" if token.startswith("ед") else "USD"
        units.add((currency, _SCALES[match[1]]))
    # Remove matched phrases before looking for unscaled units. Otherwise a
    # published million-ruble unit would conflict with its own 'rubles' token.
    remainder = re.sub(rf"\b(тыс|млн|млрд)\.?\s*({_CURRENCY}|ед\.?|единиц\w*)", " ", text)
    if "%" in text or re.search(r"(?:^|[,;(])\s*процент(?:ов|ы|ах)?(?:\s+годовых)?(?:\W|$)|\bв процентах\b", text):
        units.add(("percent", Decimal(1)))
    if re.search(r"\bмесяцев\b", text):
        units.add(("month", Decimal(1)))
    if re.search(r"(?<!\w)ед\.(?!\w)|\bединиц(?:а|ах|ы)?\b", remainder):
        units.add(("count", Decimal(1)))
    for match in re.finditer(rf"(?:^|[,;(])\s*({_CURRENCY})(?:\s+сша)?(?=$|[,;)*\s])", remainder):
        units.add(("RUB" if match[1].startswith("руб") or match[1] == "rub" else "USD", Decimal(1)))
    return units


def _unit(text):
    candidates = _units(text)
    return next(iter(candidates)) if len(candidates) == 1 else None


def _kind(label, variant, unit):
    lower = _text(label)
    if "индекс" in lower:
        return "index"
    if unit == "percent":
        return "ratio"
    if unit == "count":
        return "count"
    if unit == "month" or unit.startswith("RUB_per_"):
        return None
    if variant.variant_id.startswith("reported_"):
        return variant.quantity_kind
    if "за месяц" in lower or "в течение месяца" in lower:
        return "flow"
    if "задолженност" in lower or "остатк" in lower:
        return "stock"
    return variant.quantity_kind


def _period(period, label, variant):
    lower = _text(label)
    if period.kind == "as_of" and ("за месяц" in lower or "в течение месяца" in lower):
        if period.as_of.day != 1:
            raise ValueError("cbr.statistics.month_reference_invalid")
        end = period.as_of - timedelta(days=1)
        return PeriodRef("interval", start=end.replace(day=1), end=end)
    if period.kind == "interval" and "на конец периода" in lower:
        return PeriodRef("as_of", as_of=period.end)
    if period.kind == "interval" and "с начала года" in lower:
        return PeriodRef("interval", start=date(period.end.year, 1, 1), end=period.end)
    return period


def _basis(variant, section):
    text = _text(section)
    if "прироста к декабрю предыдущего года" in text:
        return "reported_growth_ytd"
    if "прироста к предыдущему периоду" in text:
        return "reported_growth_period"
    if "прироста к соответствующему периоду предыдущего года" in text:
        return "reported_growth_comparable_year_period"
    return variant.variant_id if variant.variant_id.startswith("reported_") else "published_level"


def _note(label):
    text = _text(label)
    return text.startswith(("*", "примечани", "источник", "комментари", "дата обновления", "дата последнего обновления")) or bool(re.match(r"(?:\d+\)|[¹²³⁴⁵⁶⁷⁸⁹⁰]+)\s", text))


def _label_cells(row, columns, grid, merged):
    result = []
    for column in columns:
        cell = grid.get((row, column))
        if cell is None or cell.value in (None, ""):
            for first_row, first_col, last_row, last_col in merged:
                if first_row <= row <= last_row and first_col <= column <= last_col and last_col < columns.stop:
                    cell = grid.get((first_row, first_col))
                    break
        if cell is not None and cell.value not in (None, "") and cell not in result:
            result.append(cell)
    return result if any(isinstance(cell.value, str) and cell.value.strip() for cell in result) else []


def _section_title(row, first_column, cells, merged):
    values = [cell for cell in cells if cell.value not in (None, "") and str(cell.value).strip()]
    if len(values) != 1 or not isinstance(values[0].value, str):
        return None
    cell = values[0]
    if cell.column >= first_column and any(r1 == r2 == row and c1 == cell.column and c2 > c1 for r1, c1, r2, c2 in merged):
        return cell.value.strip()
    return None


def _validate_bindings(row_bindings, period_bindings):
    if any(not isinstance(item, RowBinding) or type(item.source_row) is not int or item.source_row < 1
           or not isinstance(item.metric, MetricRef) or not isinstance(item.subject, SubjectRef)
           or not item.subject.namespace or not item.subject.id
           or len(dict(item.dimensions)) != len(item.dimensions)
           or any(type(key) is not str or type(value) is not str or not key for key, value in item.dimensions)
           for item in row_bindings):
        raise ValueError("cbr.statistics.row_bindings_invalid")
    if any(not isinstance(item, ColumnPeriodBinding) or not isinstance(item.period, PeriodRef)
           for item in period_bindings):
        raise ValueError("cbr.statistics.period_bindings_invalid")
    row_map = {(item.series_id, item.sheet, item.source_row): item for item in row_bindings}
    period_map = {(item.series_id, item.sheet, item.column): item for item in period_bindings}
    if len(row_map) != len(row_bindings) or len(period_map) != len(period_bindings):
        raise ValueError("cbr.statistics.duplicate_semantic_binding")
    return row_map, period_map


def align_statistics(flakes, *, row_bindings=(), period_bindings=(), mapping_version="cbr.source_labels.v1", strict=False):
    if not flakes or type(strict) is not bool or not isinstance(mapping_version, str) or not mapping_version.strip():
        raise ValueError("cbr.statistics.alignment_request_invalid")
    row_map, period_map = _validate_bindings(row_bindings, period_bindings)
    batches, versions, diagnostics, used_rows, used_periods = [], [], [], set(), set()
    for flake in flakes:
        descriptor = source(flake.series_id)
        profile = table_profile(flake.profile_id)
        if profile.series_id != flake.series_id or profile.version != flake.profile_version:
            raise ValueError("cbr.statistics.profile_mismatch")
        identity = flake.identity
        versions.append(InputVersion(flake.series_id, flake.issue_id, flake.source_identity, identity,
                                     flake.profile_id, flake.profile_version, flake.asset_id))
        observations = []
        for sheet in flake.sheets:
            variant = sheet_variant(profile, sheet.name)
            if variant is None:
                diagnostics.append(TableDiagnostic("cbr.statistics.layout_unrecognized", sheet.name))
                continue
            if variant.role == "metadata":
                continue
            explicit = tuple(item for key, item in period_map.items() if key[:2] == (flake.series_id, sheet.name))
            try:
                axes = _period_axes(sheet, variant, explicit)
            except ValueError as error:
                diagnostics.append(TableDiagnostic(str(error), sheet.name))
                continue
            if not axes:
                diagnostics.append(TableDiagnostic("cbr.statistics.period_axis_unresolved", sheet.name))
                continue
            used_periods.update((item.series_id, item.sheet, item.column) for item in explicit)
            grid = {(cell.row, cell.column): cell for cell in sheet.cells}
            rows = defaultdict(list)
            for cell in sheet.cells:
                rows[cell.row].append(cell)
            merged = _merges(sheet)
            occurrences = defaultdict(int)
            for index, axis in enumerate(axes):
                periods = axis.periods
                if not periods:
                    diagnostics.append(TableDiagnostic("cbr.statistics.period_axis_unresolved", sheet.name))
                    continue
                first_column = min(periods.keys() | axis.unresolved)
                label_columns = range(1, first_column)
                end = axes[index + 1].start - 1 if index + 1 < len(axes) else sheet.rows
                context_start = 1
                if index:
                    previous = axes[index - 1]
                    prior_facts = [row for row in range(previous.header + 1, axis.start)
                                   if _label_cells(row, label_columns, grid, merged)
                                   and any(cell.column in previous.periods and _fact(cell) for cell in rows[row])]
                    context_start = max(prior_facts, default=previous.header) + 1
                header_text = " ".join(str(cell.value) for row in range(context_start, axis.header + 1)
                                       for cell in rows[row] if isinstance(cell.value, str)
                                       and _direct_period(cell.value) is None)
                table_units = _units(header_text)
                anchor = getattr(variant, "unit_anchor", None)
                if anchor is not None:
                    anchor_cell = grid.get(_point(anchor))
                    anchor_units = _units(anchor_cell.value) if anchor_cell is not None else set()
                    if not anchor_units:
                        diagnostics.append(TableDiagnostic("cbr.statistics.unit_anchor_unresolved", sheet.name, anchor))
                    table_units.update(anchor_units)
                section = header_text.strip() if len(axes) > 1 else ""
                section_units = set()
                hierarchy = []
                missing_columns = set(axis.unresolved)
                last_fact_row = max((row for row in range(axis.header + 1, end + 1)
                    if _label_cells(row, label_columns, grid, merged)
                    and any(cell.column in periods and _fact(cell) for cell in rows[row])), default=axis.header)
                for column in sorted(axis.unresolved):
                    diagnostics.append(TableDiagnostic("cbr.statistics.period_column_unresolved", sheet.name,
                                                       f"row{axis.header}.column{column}"))
                for row in range(axis.header + 1, end + 1):
                    section_title = _section_title(row, first_column, rows[row], merged)
                    if section_title:
                        section, section_units, hierarchy = section_title, _units(section_title), []
                        continue
                    labels = _label_cells(row, label_columns, grid, merged)
                    if not labels:
                        continue
                    label = " | ".join(str(cell.value) for cell in labels)
                    if _note(label):
                        if any(cell.column in periods and _fact(cell) for cell in rows[row]):
                            diagnostics.append(TableDiagnostic("cbr.statistics.source_note_contains_values", sheet.name, labels[-1].coordinate))
                        if row > last_fact_row:
                            break
                        continue
                    data_cells = tuple(grid.get((row, column)) for column in periods)
                    has_facts = any(_fact(cell) for cell in data_cells)
                    binding_key = (flake.series_id, sheet.name, row)
                    binding = row_map.get(binding_key)
                    if binding:
                        used_rows.add(binding_key)
                    for cell in rows[row]:
                        if cell.column >= first_column and cell.column not in periods and _fact(cell) and cell.column not in missing_columns:
                            diagnostics.append(TableDiagnostic("cbr.statistics.period_column_unresolved", sheet.name, cell.coordinate))
                            missing_columns.add(cell.column)
                    merged_heading = any(r1 == r2 == row and c1 < c2 < first_column
                                         and any(cell.row == row and cell.column == c1 for cell in labels)
                                         for r1, c1, r2, c2 in merged)
                    if not binding and not has_facts and (label.strip().isupper() or merged_heading):
                        section, section_units, hierarchy = label.strip(), set(), []
                        continue
                    last_label = str(labels[-1].value)
                    leading = len(last_label) - len(last_label.lstrip())
                    level = labels[-1].indent * 100 + leading
                    while hierarchy and hierarchy[-1][0] >= level:
                        hierarchy.pop()
                    local_units = _units(label)
                    parent_units = next((entry[2] for entry in reversed(hierarchy) if entry[2]), set())
                    path = tuple(item[1] for item in hierarchy) + (label.strip(),)
                    hierarchy.append((level, label.strip(), local_units))
                    # A fully populated physical matrix row can publish blanks.
                    # Sparse label-only headings and footnotes are not measures.
                    blank_row = all(cell is not None for cell in data_cells) and any(
                        cell.number_format != "General" for cell in data_cells if cell is not None)
                    if not binding and not has_facts and not blank_row:
                        continue
                    if not has_facts and _text(label).rstrip(":") in {"в том числе", "из них"}:
                        continue
                    row_path = " / ".join(((section,) if section else ()) + path)
                    occurrences[row_path] += 1
                    if occurrences[row_path] > 1:
                        row_path += f" [occurrence {occurrences[row_path]}]"
                    candidates = local_units or parent_units or section_units or table_units
                    unit, scale = next(iter(candidates)) if len(candidates) == 1 else ("source_unspecified", None)
                    if unit == "RUB_per_foreign_currency":
                        for word, currency in (("доллар", "USD"), ("евро", "EUR"), ("юан", "CNY")):
                            if word in _text(label):
                                unit = "RUB_per_" + currency
                                break
                    if (flake.series_id.endswith(".mortgage_ihc") and "на приобретение" in _text(label)
                            and unit == "count" and any("объем" in _text(item[1]) for item in hierarchy[:-1])):
                        diagnostics.append(TableDiagnostic("cbr.statistics.source_unit_conflict", sheet.name, labels[-1].coordinate))
                        unit, scale = "source_conflicting", None
                    if binding:
                        if unit not in {"source_unspecified", "source_conflicting"} and (binding.metric.unit != unit or binding.metric.scale != scale):
                            raise ValueError("cbr.statistics.binding_measurement_mismatch")
                    elif unit == "source_unspecified":
                        code = "cbr.statistics.unit_ambiguous" if len(candidates) > 1 else "cbr.statistics.unit_unresolved"
                        diagnostics.append(TableDiagnostic(code, sheet.name, labels[-1].coordinate))
                    metric_id = flake.series_id + ".m." + sha256(canonical_manifest_bytes([flake.asset_id, sheet.name, row_path])).hexdigest()[:16]
                    semantic_label = " / ".join(path)
                    metric = binding.metric if binding else MetricRef(metric_id, unit, _kind(semantic_label, variant, unit), profile.edition, scale)
                    source_row_id = sha256(canonical_manifest_bytes([flake.series_id, flake.asset_id, sheet.name, row_path])).hexdigest()[:24]
                    subject = binding.subject if binding else SubjectRef("cbr.source_row", source_row_id)
                    dimensions = {"source_series": flake.series_id, "source_asset_id": flake.asset_id, "source_sheet": sheet.name,
                                  "source_hierarchy": row_path, "measure_basis": _basis(variant, section),
                                  "seasonal_adjustment": "adjusted" if "с.к" in sheet.name.lower() else "unadjusted",
                                  "mapping_status": "explicit" if binding else "source_identity"}
                    if section:
                        dimensions["source_section"] = section
                    if "средневзвешенн" in _text(label):
                        dimensions["source_aggregation"] = "weighted_average"
                    if binding:
                        if any(key in dimensions and dimensions[key] != value for key, value in binding.dimensions):
                            raise ValueError("cbr.statistics.binding_source_dimension_conflict")
                        dimensions.update(binding.dimensions)
                    for column, period in periods.items():
                        cell = grid.get((row, column))
                        try:
                            value, status, token = _cell_value(cell)
                            actual_period = period if (flake.series_id, sheet.name, column) in period_map else _period(period, semantic_label, variant)
                        except ValueError as error:
                            diagnostics.append(TableDiagnostic(str(error), sheet.name, cell.coordinate if cell else None))
                            continue
                        cell_dimensions = dict(dimensions)
                        period_cell = grid.get((axis.header, column))
                        if period_cell is not None and isinstance(period_cell.value, str) and period_cell.value.strip().endswith("*"):
                            cell_dimensions["source_period_label"] = period_cell.value
                        if isinstance(token, str) and token.strip().endswith("*"):
                            cell_dimensions["source_value_qualification"] = "annotated"
                        if metric.quantity_kind == "flow" and actual_period.kind == "as_of":
                            cell_dimensions["period_qualification"] = "reported_date_interval_unresolved"
                        coordinate = cell.coordinate if cell else f"row{row}.column{column}"
                        observations.append(Observation(subject, metric, actual_period, tuple(sorted(cell_dimensions.items())),
                            binding.perimeter if binding and binding.perimeter else descriptor.series_id,
                            value, status, flake.source_identity.sha256 + ":" + sheet.name + "!" + coordinate, token))
        if not observations:
            codes = ", ".join(sorted({item.code for item in diagnostics}))
            raise ValueError("cbr.statistics.no_admitted_observations: " + codes)
        lineage = (*flake.lineage, UsedInputReceipt("source_flake", identity, "application/vnd.stratbox.dataset+json",
                                                   "inline", flake.series_id, version=identity))
        from stratbox.core.registry.sources import source_cards
        card = next(card for card in source_cards("cbr") if card.series_id == flake.series_id)
        group = card.source_groups[0].group_id if len(card.source_groups) == 1 else None
        uses = (SourceUse(SourceCoordinate(flake.series_id, source_group_id=group, issue_id=flake.issue_id,
            asset_id=flake.asset_id, material_identity=flake.source_identity,
            layout_edition=profile.edition, semantic_profile_edition=mapping_version), "flakes", "domain_validated"),)
        batches.append(ObservationBatch(flake.series_id, 1, identity.sha256, tuple(observations), lineage, uses))
    if set(row_map) != used_rows or set(period_map) != used_periods:
        raise ValueError("cbr.statistics.unused_semantic_binding")
    if strict and diagnostics:
        raise ValueError("cbr.statistics.unresolved_semantics")
    if len({(item.series_id, item.flake) for item in versions}) != len(versions):
        raise ValueError("cbr.statistics.duplicate_input_version")
    return StatisticsDataset(tuple(batches), tuple(versions), mapping_version, tuple(diagnostics))
