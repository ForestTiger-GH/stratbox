"""KEP2 selected tables: source row decisions and all published frequencies.

The review scope is the supplied reviewed method's eleven indicators. Full workbook
cells remain a separate physical extract. No filename implies an observation
period; no published index is converted into a growth rate here.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import re

from stratbox.shared.data.coverage import SnapshotCoverage, CoverageDimension
from stratbox.shared.identity import canonical_manifest_bytes
from .types import Kep2Settings, SourceTable, RowDecision, SectionEvidence, SourceValue
from ..common.kep2 import KEP2_INDICATORS, KEP2_MEASURES, KEP2_RULES_ID


class Kep2Error(ValueError):
    pass


def normalized(value: object) -> str:
    text = str(value or "").replace("ё", "е").replace("Ё", "Е")
    text = text.translate(str.maketrans({"«": '"', "»": '"', "“": '"', "”": '"', "\u00a0": " ", "\n": " "}))
    text = re.sub(r"^\s*\d+(?:\.\d+)*\.?(?:\s+|$)", "", text)
    return re.sub(r"\s+", " ", text).strip(" .:").casefold()


def strip_footnotes(token: str) -> tuple[str, tuple[str, ...]]:
    match = re.search(r"\s+(\d{1,3}\))\s*$", token)
    if match is None:
        match = re.search(r"(?<=[\d….\-–—])(\d\))\s*$", token)
    if match:
        return token[:match.start()].strip(), (match.group(1),)
    match = re.search(r"(\*{1,3})\s*$", token)
    if match:
        return token[:match.start()].strip(), (match.group(1),)
    return token.strip(), ()


def numeric_token(raw: str | None, *, formula_without_cache: bool = False) -> tuple[Decimal | None, str, tuple[str, ...]]:
    if formula_without_cache:
        return None, "unparsed", ()
    if raw is None or not raw.strip():
        return None, "blank", ()
    token, notes = strip_footnotes(raw)
    token = token.replace("\u00a0", " ").replace("\u202f", " ").strip()
    if token in {"-", "–", "—"}:
        return None, "dash", notes
    if token in {"…", "...", "..", "н/д", "н.д.", "N/A"}:
        return None, "missing", notes
    if token.casefold() in {"x", "х"}:
        return None, "not_applicable", notes
    token = token.replace(" ", "").replace(",", ".").replace("−", "-")
    if token.endswith("%"):
        token = token[:-1]
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", token):
        return None, "unparsed", notes
    try:
        value = Decimal(token)
    except InvalidOperation:
        return None, "unparsed", notes
    return (value, "reported", notes) if value.is_finite() else (None, "unparsed", notes)


def period(year: int, column: int) -> tuple[str, date, date, date]:
    if column == 2:
        start, stop, frequency = date(year, 1, 1), date(year + 1, 1, 1), "annual"
    elif 3 <= column <= 6:
        month = 1 + (column - 3) * 3
        start = date(year, month, 1)
        stop = date(year + 1, 1, 1) if month == 10 else date(year, month + 3, 1)
        frequency = "quarterly"
    elif 7 <= column <= 18:
        month = column - 6
        start = date(year, month, 1)
        stop = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        frequency = "monthly"
    else:
        raise Kep2Error("rosstat.kep2.column_outside_layout")
    return frequency, start, stop - timedelta(days=1), stop


def _unit(text: str) -> tuple[str | None, Decimal]:
    value = normalized(re.sub(r"(?<=[А-Яа-яA-Za-z])\d{1,3}\)", "", text))
    if re.search(r"млрд\.?\s*(?:т[.\s-]*км|тонно?-км|тонн[оа-]*километр)", value):
        return "tonne_km", Decimal(10) ** 9
    if re.search(r"млн\.?\s*(?:т[.\s-]*км|тонно?-км|тонн[оа-]*километр)", value):
        return "tonne_km", Decimal(10) ** 6
    if re.search(r"млрд\.?\s*руб", value):
        return "RUB", Decimal(10) ** 9
    if re.search(r"млн\.?\s*руб", value):
        return "RUB", Decimal(10) ** 6
    if re.search(r"тыс\.?\s*руб", value):
        return "RUB", Decimal(10) ** 3
    if re.search(r"руб(?:\.|лей|ля|ль)?(?:\b|$)", value):
        return "RUB", Decimal(1)
    return None, Decimal(1)


def _matches(text: str, titles: tuple[str, ...]) -> bool:
    candidate = normalized(re.sub(r"(?<=[А-Яа-яA-Za-z])\d{1,3}\)", "", text))
    for title in titles:
        exact = normalized(title)
        if candidate == exact:
            return True
        # A unit may be appended to a complete title. Arbitrary title prefixes
        # (the reviewed method's first 30 characters) are deliberately not admitted.
        if candidate.startswith(exact):
            tail = candidate[len(exact):].strip(" ,;()")
            if _unit(tail)[0] is not None:
                return True
    return False


def _sheet_name(value: str, sheets) -> str:
    def key(name):
        return str(name).strip().rstrip(".").casefold()
    candidates = [sheet.name for sheet in sheets if key(sheet.name) == key(value)]
    if len(candidates) != 1:
        raise Kep2Error("rosstat.kep2.sheet_unresolved" if not candidates else "rosstat.kep2.sheet_ambiguous")
    return candidates[0]


def _raw(cell) -> str | None:
    if cell is None:
        return None
    if cell.raw_token is not None and cell.kind in {"n", "e"}:
        return cell.raw_token
    return None if cell.value is None else str(cell.value)


def _row_evidence(cells, row):
    return canonical_manifest_bytes({"cells":[{
        "column":col,"raw_token":_raw(cells.get((row,col))),
        "kind":cells[(row,col)].kind if (row,col) in cells else "absent",
        "number_format":cells[(row,col)].number_format if (row,col) in cells else "General",
        "formula":cells[(row,col)].formula if (row,col) in cells else None,
    } for col in range(1,19)]}).decode("utf-8")


def extract_kep2(request: Kep2Settings, *, budget=None, checkpoint=None) -> SourceTable:
    if checkpoint is not None:
        checkpoint()
    workbook = request.workbook
    if workbook.series_id != "rosstat.short_term_indicators":
        raise Kep2Error("rosstat.kep2.series_mismatch")
    if request.duplicate_year_policy not in {"last_source_row", "reject"}:
        raise Kep2Error("rosstat.kep2.duplicate_year_policy_invalid")
    known = {item.id: item for item in KEP2_INDICATORS}
    required = request.required_indicators or tuple(known)
    if len(set(required)) != len(required) or not set(required) <= set(known):
        raise Kep2Error("rosstat.kep2.indicators_invalid")
    if any(key not in known or not alias.strip() for key, alias in request.title_aliases):
        raise Kep2Error("rosstat.kep2.alias_invalid")
    aliases = {key: known[key].titles + tuple(v for k, v in request.title_aliases if k == key) for key in known}
    override = {}
    for key, literal, unit, scale in request.unit_overrides:
        if key not in known or key in override or not literal or not unit or not isinstance(scale, Decimal) or not scale.is_finite() or scale <= 0:
            raise Kep2Error("rosstat.kep2.unit_override_invalid")
        override[key] = (literal, unit, scale)
    contents = [sheet for sheet in workbook.sheets if normalized(sheet.name) == "содержание"]
    if len(contents) != 1:
        raise Kep2Error("rosstat.kep2.contents_required")
    table = contents[0]
    lookup = {(cell.row, cell.column): cell for cell in table.cells}
    entries = []
    for row in range(1, table.rows + 1):
        for sc, tc in ((1, 2), (5, 6)):
            sheet, title = _raw(lookup.get((row, sc))), _raw(lookup.get((row, tc)))
            if sheet and title and normalized(sheet) not in {"лист", "листы"} and normalized(title) not in {"раздел", "разделы"}:
                entries.append((sheet, title))
    if not entries:
        raise Kep2Error("rosstat.kep2.contents_empty")
    assignments = {}
    for indicator in KEP2_INDICATORS:
        matched = {(sheet, title) for sheet, title in entries if _matches(title, aliases[indicator.id])}
        if len(matched) > 1:
            raise Kep2Error("rosstat.kep2.contents_ambiguous")
        if matched:
            sheet, _ = next(iter(matched))
            assignments[indicator.id] = _sheet_name(sheet, workbook.sheets)
        elif indicator.parent in assignments:
            assignments[indicator.id] = assignments[indicator.parent]
    by_sheet = {sheet.name: sheet for sheet in workbook.sheets}
    values, sections, decisions, diagnostics = [], [], [], []
    all_titles = tuple(title for _, title in entries) + tuple(title for group in aliases.values() for title in group)
    for indicator in KEP2_INDICATORS:
        if checkpoint is not None:
            checkpoint()
        if indicator.id not in required:
            continue
        if indicator.id not in assignments:
            diagnostics.append("rosstat.kep2.indicator_missing:" + indicator.id)
            continue
        sheet = by_sheet[assignments[indicator.id]]
        cells = {(cell.row, cell.column): cell for cell in sheet.cells}
        first = {row: _raw(cells.get((row, 1))) or "" for row in range(1, sheet.rows + 1)}
        # The reviewed method's A:R positions are a reviewed layout, not a universal
        # calendar guess. Admit that layout only when source headers agree.
        year_header = normalized(re.sub(r"\d+\)", "", _raw(cells.get((1, 2))) or ""))
        quarter_headers = tuple(normalized(_raw(cells.get((2, col))) or "") for col in range(3, 7))
        months = ({"янв","январь"},{"фев","февр","февраль"},{"март"},{"апр","апрель"},{"май"},{"июнь"},
            {"июль"},{"авг","август"},{"сент","сен","сентябрь"},{"окт","октябрь"},{"нояб","ноябрь"},{"дек","декабрь"})
        month_headers=tuple(normalized(re.sub(r"\d+\)","",_raw(cells.get((1,col))) or "")) for col in range(7,19))
        if (year_header not in {"год", "год / year", "year"} or quarter_headers != ("i", "ii", "iii", "iv")
                or any(header not in accepted for header,accepted in zip(month_headers,months))):
            raise Kep2Error("rosstat.kep2.period_layout_unreviewed")
        section_aliases = aliases[indicator.id]
        if indicator.id == "wages":
            nominal = tuple(title for title in section_aliases if "номинальная" in title)
            if any(_matches(text, nominal) for text in first.values()):
                section_aliases = nominal
        candidates = [row for row, text in first.items() if _matches(text, section_aliases)]
        if len(candidates) != 1:
            if not candidates:
                diagnostics.append("rosstat.kep2.section_missing:" + indicator.id)
                continue
            raise Kep2Error("rosstat.kep2.section_ambiguous")
        title_row = candidates[0]
        boundary = sheet.rows + 1
        for row in range(title_row + 1, sheet.rows + 1):
            text = first[row]
            # Full named sections and unit-bearing category headers bound the
            # target. In particular freight transport totals stop before cargo
            # transportation, rather than stealing another category's markers.
            new_quantity = bool(re.search(r",\s*(?:млн|млрд|тыс)\.?\s*(?:тонн|пассаж|руб)", text.casefold()))
            if _matches(text, all_titles) or re.match(r"^\s*\d+\.\d+(?:\.\d+)*\.?\s+[А-Яа-яA-Za-z]", text) or new_quantity:
                boundary = row
                break
        markers = {}
        for measure, _, marker in KEP2_MEASURES[1:]:
            found = [row for row in range(title_row + 1, boundary)
                     if normalized(first[row]).startswith(normalized(marker))]
            if len(found) > 1:
                raise Kep2Error("rosstat.kep2.marker_ambiguous")
            if found:
                markers[measure] = found[0]
        for measure, _, marker in KEP2_MEASURES:
            if measure == "absolute" and not indicator.absolute:
                continue
            if marker and measure not in markers:
                if indicator.id == "agriculture" and measure == "previous_period_index":
                    continue  # The reviewed KEP2 agriculture block publishes year-on-year only.
                diagnostics.append("rosstat.kep2.marker_missing:" + indicator.id + ":" + measure)
                continue
            anchor = markers.get(measure, title_row)
            stop = min([boundary, *(r for r in markers.values() if r > anchor)])
            candidates_by_year = {}
            current_year = None
            current_year_literal = ""
            row_year_literals = {}
            finished = False
            headers = [" | ".join(_raw(cells.get((row, col))) or "" for col in range(1, 19)).rstrip(" |") for row in (1, 2)]
            notes = [text for text in first.values() if re.match(r"^\s*\d{1,3}\)", text)]
            for row in range(anchor + 1, stop):
                head, _ = strip_footnotes(first[row])
                if finished:
                    if head:
                        notes.append(first[row])
                    if re.fullmatch(r"(?:18|19|20|21)\d{2}(?:\.0)?",head):
                        diagnostics.append("rosstat.kep2.unreviewed_data_run:" + indicator.id + ":" + measure)
                        decisions.append(RowDecision(indicator.id,measure,sheet.name,row,int(float(head)),False,
                            "unreviewed_data_run",_row_evidence(cells,row)))
                    continue
                if re.fullmatch(r"(?:18|19|20|21)\d{2}(?:\.0)?", head):
                    current_year = int(float(head))
                    current_year_literal = first[row]
                elif head:
                    if current_year is not None:
                        notes.append(first[row])
                        finished = True
                    else:
                        headers.append(" | ".join(_raw(cells.get((row, col))) or "" for col in range(1, 19)).rstrip(" |"))
                    current_year = None
                    continue
                elif current_year is None:
                    line = " | ".join(_raw(cells.get((row, col))) or "" for col in range(1, 19)).rstrip(" |")
                    if line:
                        headers.append(line)
                    continue
                if current_year is not None and (head or any(_raw(cells.get((row, col))) not in {None, ""} for col in range(2, 19))):
                    candidates_by_year.setdefault(current_year, []).append(row)
                    row_year_literals[row] = current_year_literal
            if not candidates_by_year:
                diagnostics.append("rosstat.kep2.block_empty:" + indicator.id + ":" + measure)
                continue
            if request.duplicate_year_policy == "reject" and any(len(rows) > 1 for rows in candidates_by_year.values()):
                raise Kep2Error("rosstat.kep2.duplicate_year")
            unit_literal = " | ".join((first[title_row], *headers))
            if marker:
                unit_literal, unit, scale = first[anchor], "percent", Decimal(1)
            else:
                unit, scale = _unit(unit_literal)
                if indicator.id in override:
                    unit_literal, unit, scale = override[indicator.id]
                if unit is None:
                    diagnostics.append("rosstat.kep2.unit_unresolved:" + indicator.id)
            sections.append(SectionEvidence(indicator.id, measure, sheet.name, title_row,
                anchor if marker else None, anchor + 1, stop - 1, first[title_row], tuple(headers), unit_literal, tuple(notes)))
            for year, rows in candidates_by_year.items():
                chosen = rows[-1]
                if budget is not None:
                    budget.charge("cells",17)
                if checkpoint is not None:
                    checkpoint()
                for row in rows:
                    decisions.append(RowDecision(indicator.id, measure, sheet.name, row, year,
                        row == chosen, "last_source_row" if len(rows) > 1 else "single_source_row",
                        _row_evidence(cells,row)))
                for col in range(2, 19):
                    cell = cells.get((chosen, col))
                    raw = _raw(cell)
                    value, status, footnotes = numeric_token(raw, formula_without_cache=bool(cell and cell.formula and cell.value is None))
                    _,year_notes=strip_footnotes(row_year_literals[chosen])
                    footnotes=tuple(dict.fromkeys((*year_notes,*footnotes)))
                    frequency, start, end, display = period(year, col)
                    locator = f"{sheet.name}!R{chosen}C{col}"
                    if status == "unparsed":
                        diagnostics.append("rosstat.kep2.unparsed:" + locator)
                    values.append(SourceValue(indicator.id, indicator.label, measure, frequency, start, end,
                        display, value, status, raw, unit_literal, unit, scale,
                        "index" if marker else indicator.quantity_kind, "iso3166-1", "RU",
                        locator, sheet.name, chosen, col, footnotes,
                        (("comparison_basis", "same_period_previous_year" if measure == "year_on_year_index" else "previous_period"),) if marker else (),
                        "russia_publisher_scope", "interval",
                        cell.kind if cell else "absent", cell.number_format if cell else "General",
                        cell.formula if cell else None, row_year_literals[chosen],
                        " | ".join(filter(None, (_raw(cells.get((r, col))) for r in (1, 2))))))
    status = "partial" if diagnostics else "complete"
    materialized=tuple(key for key in required if any(value.indicator_id==key for value in values))
    interpreted=tuple(key for key in materialized if all(value.unit is not None and value.value_status!="unparsed" for value in values if value.indicator_id==key))
    dimensions=(CoverageDimension("indicators",required,materialized,materialized,interpreted,materialized,
        tuple(key for key in required if key not in materialized)),
        CoverageDimension("frequencies",("annual","quarterly","monthly"),
            ("annual","quarterly","monthly"),("annual","quarterly","monthly"),("annual","quarterly","monthly"),("annual","quarterly","monthly")))
    return SourceTable(workbook.series_id, workbook.issue_id, workbook.asset_id,
        workbook.source_identity, workbook.identity, KEP2_RULES_ID, tuple(values),
        tuple(sections), tuple(decisions), workbook.lineage,
        SnapshotCoverage(status, "Selected KEP2 indicators: " + ", ".join(required) + "; all annual, quarterly and monthly cells; not the whole workbook.",dimensions),
        tuple(dict.fromkeys(diagnostics)))
