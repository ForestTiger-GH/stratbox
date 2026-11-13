"""Decode the publisher's cached workbook values and territorial structure."""

from __future__ import annotations

from datetime import date

import re

from stratbox.base.ioapi.archive_bytes import ArchiveLimits, open_zip
from stratbox.base.ioapi.xml import XmlError, parse_xml
from .representation import serialize


XML = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


PKGREL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


LIMIT_XLSX = 8_000_000


LIMIT_UNPACKED = 30_000_000


LIMIT_CELLS = 80_000


MAX_WIDTH = 16_384
MAX_ROW = 1_048_576


class CaptureError(Exception):
    pass


class AmbiguousBlock(CaptureError):
    def __init__(self, candidates: tuple[tuple[str, int, int], ...]):
        self.candidates = candidates
        super().__init__("XLSX_NATIONAL_TOTAL_AMBIGUOUS")


def require(ok, reason):
    if not ok:
        raise CaptureError(reason)


def clean(value):
    result = re.sub(r"\s+", " ", value).strip()
    require(
        "\ufffd" not in result
        and not any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in result),
        "INVALID_TEXT",
    )
    return result


def colnum(ref):
    letters = re.fullmatch(r"([A-Z]{1,3})[1-9][0-9]{0,6}", ref)
    require(letters is not None, "XLSX_CELL_REFERENCE")
    n = 0
    for ch in letters[1]:
        n = n * 26 + ord(ch) - 64
    require(1 <= n <= MAX_WIDTH, "XLSX_COLUMN_LIMIT")
    return n


def xlsx_rows(blob, *, budget=None, checkpoint=None):
    require(len(blob) <= LIMIT_XLSX and blob[:2] == b"PK", "XLSX_NOT_ZIP")
    limits = ArchiveLimits(250, LIMIT_UNPACKED, LIMIT_UNPACKED, LIMIT_XLSX)
    with open_zip(blob, limits, budget=budget) as archive:
        return _xlsx_rows(archive, budget=budget, checkpoint=checkpoint)


def _xml(archive, name, budget):
    if budget is not None:
        budget.check("decoded_bytes", archive.getinfo(name).file_size)
    try:
        return parse_xml(archive.read(name), budget=budget)
    except XmlError as error:
        code = "XLSX_DTD_UNSUPPORTED" if str(error) == "xml.dtd_forbidden" else "XLSX_XML_INVALID"
        raise CaptureError(code) from None


def _header_columns(tree, previous, candidates, columns, territory_column):
    groups = {}
    for item in tree.iter(XML + "mergeCell"):
        ref = item.get("ref", "")
        match = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,6}):([A-Z]{1,3})([1-9][0-9]{0,6})", ref)
        require(match is not None, "XLSX_BAD_MERGE_RANGE")
        first_col = colnum(match[1] + match[2])
        last_col = colnum(match[3] + match[4])
        first_row, last_row = int(match[2]), int(match[4])
        require(first_col <= last_col and first_row <= last_row <= MAX_ROW, "XLSX_BAD_MERGE_RANGE")
        anchor = previous.get(first_row, {}).get(first_col)
        if not anchor or first_col <= territory_column <= last_col:
            continue
        selected = [col for col in columns if first_col <= col <= last_col]
        if len(selected) < 2:
            continue
        candidates.setdefault(first_row, previous[first_row])
        for col in selected:
            require((first_row, col) not in groups, "XLSX_OVERLAPPING_HEADERS")
            groups[first_row, col] = anchor
    return groups


def _xlsx_rows(z, *, budget=None, checkpoint=None):
    files = set(z.namelist())
    require(
        "xl/workbook.xml" in files and "xl/_rels/workbook.xml.rels" in files,
        "XLSX_MISSING_WORKBOOK",
    )
    shared = []
    if "xl/sharedStrings.xml" in files:
        ss = _xml(z, "xl/sharedStrings.xml", budget)
        for item in ss.findall(XML + "si"):
            shared.append("".join(n.text or "" for n in item.iter(XML + "t")))
    relations = _xml(z, "xl/_rels/workbook.xml.rels", budget)
    relmap = {}
    relation_ids = set()
    for relationship in relations.findall(PKGREL + "Relationship"):
        key = relationship.get("Id")
        target = relationship.get("Target")
        require(key and key not in relation_ids and target, "XLSX_BAD_RELATION_ID")
        relation_ids.add(key)
        if relationship.get("TargetMode") != "External":
            relmap[key] = target
    wb = _xml(z, "xl/workbook.xml", budget)
    sheets = wb.find(XML + "sheets")
    require(sheets is not None, "XLSX_NO_SHEETS")
    out = []
    count = 0
    for sh in sheets.findall(XML + "sheet"):
        name = clean(sh.get("name") or "")
        require(name and "\n" not in name, "XLSX_BAD_SHEET_NAME")
        relation = relmap.get(sh.get(REL + "id"), "")
        require(
            relation
            and not relation.startswith(("http:", "https:"))
            and ".." not in relation.split("/"),
            "XLSX_BAD_SHEET_RELATION",
        )
        target = relation.lstrip("/") if relation.startswith("/") else "xl/" + relation
        require(target in files, "XLSX_MISSING_SHEET")
        if checkpoint is not None:
            checkpoint()
        tree = _xml(z, target, budget)
        sheetdata = tree.find(XML + "sheetData")
        if sheetdata is None:
            continue
        data = []
        formulas = {}
        seen_rows = set()
        for r in sheetdata.findall(XML + "row"):
            rid = int(r.get("r", "0"))
            require(1 <= rid <= MAX_ROW, "XLSX_ROW_LIMIT")
            require(rid not in seen_rows, "XLSX_DUPLICATE_ROW")
            seen_rows.add(rid)
            if checkpoint is not None:
                checkpoint()
            cells = {}
            seen_cols = set()
            for c in r.findall(XML + "c"):
                count += 1
                if budget is not None:
                    budget.charge("cells", 1)
                require(count <= LIMIT_CELLS, "XLSX_CELL_LIMIT")
                ref = c.get("r", "")
                column = colnum(ref)
                require(int(ref.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")) == rid, "XLSX_CELL_REFERENCE")
                require(column not in seen_cols, "XLSX_DUPLICATE_CELL")
                seen_cols.add(column)
                kind = c.get("t", "n")
                v = c.find(XML + "v")
                formula = c.find(XML + "f")
                if formula is not None:
                    # Preserve the publisher's cached value, NEVER evaluate the formula.
                    formulas[(rid, column)] = {
                        "formula": formula.text or "",
                        "attributes": dict(sorted(formula.attrib.items())),
                        **({"cache_missing": True} if v is None or v.text is None else {}),
                    }
                if kind == "inlineStr":
                    x = c.find(XML + "is")
                    value = (
                        ""
                        if x is None
                        else "".join(t.text or "" for t in x.iter(XML + "t"))
                    )
                elif kind == "s":
                    require(v is not None and v.text is not None, "XLSX_BAD_STRING_ID")
                    index = int(v.text)
                    require(0 <= index < len(shared), "XLSX_BAD_STRING_ID")
                    value = shared[index]
                elif kind in ("n", "str", "d"):
                    value = "" if v is None or v.text is None else v.text
                elif kind == "b":
                    require(v is not None and v.text in ("0", "1"), "XLSX_BAD_BOOLEAN")
                    value = "TRUE" if v.text == "1" else "FALSE"
                elif kind == "e":
                    value = ""
                    formulas.setdefault((rid, column), {})["error_value"] = True
                else:
                    raise CaptureError("XLSX_UNSUPPORTED_TYPE")
                value = clean(value)
                if value:
                    cells[column] = value
            if cells:
                data.append((rid, cells))
        if data:
            out.append((name, data, formulas, tree))
    return out


def is_quantitative(value):
    return re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?", value) is not None


def is_district_label(value):
    # The source's generic grouping label, not a hardcoded district name list.
    return "федеральный округ" in value.casefold()


def last_district_boundary(data, district_index, territory_col, indicator_cols):
    """Resolve the end of the last district without assigning trailing regions to it.

    The publication may append territories outside the preceding federal district.
    Reconcile the published district subtotal against its following rows. This
    only determines extraction grouping; it does not alter any published value.
    """
    district = data[district_index][1]
    following = data[district_index + 1 :]
    require(following, "XLSX_FINAL_DISTRICT_EMPTY")
    comparable = [
        c
        for c in indicator_cols
        if district.get(c, "").isascii()
        and district.get(c, "").isdecimal()
        and all(
            cells.get(c, "").isascii() and cells.get(c, "").isdecimal()
            for _, cells in following
        )
    ]
    require(len(comparable) >= 2, "XLSX_FINAL_DISTRICT_BALANCE_UNKNOWN")
    targets = {c: int(district[c]) for c in comparable}
    totals = {c: 0 for c in comparable}
    matches = []
    for offset, (_, cells) in enumerate(following, start=1):
        for c in comparable:
            totals[c] += int(cells[c])
        if totals == targets:
            matches.append(district_index + offset)
    require(len(matches) == 1, "XLSX_FINAL_DISTRICT_BALANCE_AMBIGUOUS")
    return matches[0]


def is_column_number_guide(cells):
    """Recognize Excel's technical column numbering, even when codes skip values.

    Official publications sometimes number their final visible column as 9
    after 1..5, because former office categories were consolidated. Those
    technical ordinals must never be appended to published CSV headings.
    """
    if len(cells) < 3:
        return False
    numbered = [v for _, v in sorted(cells.items())]
    if not all(v.isascii() and v.isdecimal() for v in numbered):
        return False
    codes = [int(v) for v in numbered]
    return codes[0] == 1 and all(a < b for a, b in zip(codes, codes[1:]))


def convert_xlsx(
    blob, *, return_formula_lineage=False, expected_date: date | None = None,
    sheet_name: str | None = None, budget=None, checkpoint=None, evidence=None,
):
    """Keep only the published table and attach source-derived district context."""
    sheets = xlsx_rows(blob, budget=budget, checkpoint=checkpoint)
    starts = [
        (sheet, rows, formulas, tree, i, k)
        for sheet, rows, formulas, tree in sheets
        if sheet_name is None or sheet == sheet_name
        for i, (_, cells) in enumerate(rows)
        for k, value in cells.items()
        if "российская федерация" in value.casefold()
        and sum(is_quantitative(v) for v in cells.values()) >= 2
    ]
    if len(starts) > 1:
        raise AmbiguousBlock(tuple((sheet, rows[i][0], col) for sheet, rows, _, _, i, col in starts[:32]))
    require(len(starts) == 1, "XLSX_NATIONAL_TOTAL_AMBIGUOUS")
    sheet, rows, formulas, tree, idx, territory_col = starts[0]
    require(
        "российская федерация" in rows[idx][1].get(territory_col, "").casefold(),
        "XLSX_NATIONAL_TOTAL_POSITION",
    )

    if expected_date is not None:
        printed_dates = {
            date(int(year), int(month), int(day))
            for _, cells in rows[:idx]
            for text in cells.values()
            for day, month, year in re.findall(
                r"\b(?:на|по состоянию на)\s+(\d{1,2})\.(\d{1,2})\.(20\d{2})\b",
                text, flags=re.I,
            )
        }
        require(
            not printed_dates or printed_dates == {expected_date},
            "XLSX_REPORT_DATE_MISMATCH",
        )

    previous = rows[max(0, idx - 6) : idx]
    # The title is not a table heading. Numbered column guides (1, 2, 3...)
    # are not source indicator names, even when adjacent to the heading row.
    header_candidates = {
        row: cells
        for row, cells in previous
        if len(cells) > 1 and not is_column_number_guide(cells)
    }
    require(header_candidates, "XLSX_HEADER_ABSENT")

    data = []
    footer_started = False
    for rid, cells in rows[idx:]:
        name = cells.get(territory_col, "")
        number_count = sum(
            is_quantitative(v) for k, v in cells.items() if k != territory_col
        )
        if number_count >= 2:
            require(not footer_started, "XLSX_DATA_AFTER_FOOTER")
            require(name, "XLSX_UNLABELLED_DATA_ROW")
            data.append((rid, cells))
        else:
            require(not number_count, "XLSX_AMBIGUOUS_NON_DATA_ROW")
            footer_started = True
    require(
        len(data) >= 30 and len({r for r, _ in data}) == len(data),
        "XLSX_TOO_FEW_REGIONS",
    )
    cols = sorted({k for _, cells in data for k in cells})
    require(territory_col in cols and len(cols) >= 4, "XLSX_FEW_INDICATORS")
    indicator_cols = [k for k in cols if k != territory_col]
    used_rows = {rid for rid, _ in data}
    groups = _header_columns(tree, dict(previous), header_candidates, cols, territory_col)
    for (rid, column), formula in formulas.items():
        if column not in cols:
            continue
        require(rid not in header_candidates, "XLSX_FORMULA_IN_HEADER")
        if rid in used_rows:
            require(not formula.get("cache_missing"), "XLSX_FORMULA_CACHE_MISSING")
            require(not formula.get("error_value"), "XLSX_SOURCE_ERROR_VALUE")
    header_candidates = dict(sorted(header_candidates.items()))
    cols = [territory_col, *indicator_cols]
    if evidence is not None:
        evidence.update(
            sheet=sheet, header_rows=tuple(header_candidates), first_row=data[0][0],
            last_row=data[-1][0], territory_column=territory_col,
            column_order=tuple(cols), date_basis="printed" if expected_date is not None and printed_dates else "release",
        )

    header = []
    for k in cols:
        parts = []
        for row, candidate in header_candidates.items():
            value = candidate.get(k) or groups.get((row, k))
            if value and (not parts or parts[-1] != value):
                parts.append(value)
        if not parts:
            parts = [f"source_column_{k}"]
        header.append(" / ".join(parts))
    require(len(set(header)) == len(header), "XLSX_DUPLICATE_HEADER")

    districts = [
        i
        for i, (_, cells) in enumerate(data)
        if is_district_label(cells[territory_col])
    ]
    final_boundary = (
        last_district_boundary(data, districts[-1], territory_col, indicator_cols)
        if districts
        else None
    )
    last_section = ""
    records = [["source_row", "section_label", *header]]
    formula_lineage = {}
    formulas_by_row = {}
    for (rid, column), formula in formulas.items():
        formulas_by_row.setdefault(rid, {})[str(column)] = formula
    for i, (rid, cells) in enumerate(data):
        name = cells[territory_col]
        if i in districts:
            # The source's district subtotal row supplies a structural section
            # label; do not duplicate its aggregate numeric values in the CSV.
            last_section = name
            continue
        if final_boundary is not None and i > final_boundary:
            section = ""  # These territories have no published district heading.
        else:
            section = last_section
        source_formulas = formulas_by_row.get(rid)
        if source_formulas:
            formula_lineage[str(rid)] = source_formulas
        records.append([str(rid), section, *(cells.get(k, "") for k in cols)])
    result = serialize(records)
    return (result, formula_lineage) if return_formula_lineage else result
