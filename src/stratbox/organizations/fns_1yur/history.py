"""Historical Form 1-YUR published fields, geography and cross-checks."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import io
import json
import re

from . import parser as modern
from .source import SourceError


class HistoryError(SourceError):
    pass


class XlsxSheetAdapter:
    """Cached cell values with xlrd-like read-only access; no formula evaluation."""

    def __init__(self, sheet):
        self.name = sheet.title
        sheet.reset_dimensions()
        self._rows = [
            tuple("" if value is None else value for value in row)
            for row in sheet.iter_rows(values_only=True)
        ]
        self.nrows = len(self._rows)
        self.ncols = max((len(row) for row in self._rows), default=0)

    def cell_value(self, row, col):
        if row < 0 or col < 0 or row >= self.nrows or col >= len(self._rows[row]):
            return ""
        return self._rows[row][col]


class XlsxBookAdapter:
    def __init__(self, file_bytes):
        from stratbox.base.utils.optional_deps import require_extra

        openpyxl = require_extra("openpyxl", "excel")
        try:
            self._book = openpyxl.load_workbook(
                io.BytesIO(file_bytes), read_only=True, data_only=True, keep_links=False
            )
        except Exception as exc:
            raise HistoryError("OOXML_WORKBOOK_UNREADABLE") from exc
        self._sheets = {}

    def sheet_names(self):
        return self._book.sheetnames

    def sheet_by_name(self, name):
        if name not in self._sheets:
            if name not in self._book.sheetnames:
                raise HistoryError("OOXML_SHEET_NOT_FOUND:" + name)
            self._sheets[name] = XlsxSheetAdapter(self._book[name])
        return self._sheets[name]

    def release_resources(self):
        self._book.close()


def open_source_workbook(file_bytes):
    if file_bytes.startswith(modern.OLE):
        from stratbox.base.utils.optional_deps import require_extra

        xlrd = require_extra("xlrd", "excel-legacy")
        try:
            return xlrd.open_workbook(file_contents=file_bytes, on_demand=True)
        except Exception as exc:
            raise HistoryError("XLS_UNREADABLE") from exc
    from .archive import check_workbook_xml, is_spreadsheet_ooxml

    if is_spreadsheet_ooxml(file_bytes):
        check_workbook_xml(file_bytes)
        return XlsxBookAdapter(file_bytes)
    raise HistoryError("SOURCE_WORKBOOK_TYPE_UNSUPPORTED")


def _header_row(sheet):
    """Require both printed alphabetic column labels and source indicator 1."""
    matches = [
        row
        for row in range(min(22, sheet.nrows))
        if str(sheet.cell_value(row, 0)).strip().upper() in ("А", "A")
        and str(sheet.cell_value(row, 1)).strip().upper() in ("Б", "B")
        and modern.code(sheet.cell_value(row, 2), 2) == "01"
    ]
    if len(matches) != 1:
        raise HistoryError("INDICATOR_NUMBER_ROW_UNRESOLVED")
    return matches[0]


def indicator_plan(sheet):
    """Select constructs from the publisher's column captions and numbers.

    Older editions move or omit bankruptcy states. The raw source indicator
    number, not the present-day equivalent, becomes the CSV prefix.
    """
    header_row = _header_row(sheet)
    captions = {}
    for col in range(2, sheet.ncols):
        text = " ".join(
            str(sheet.cell_value(row, col)).replace("\n", " ").lower()
            for row in range(4, header_row)
        )
        captions[col] = re.sub(r"\s+", " ", text).strip()
    proceedings = [
        col
        for col, text in captions.items()
        if re.search(r"процедур\w*.*банкротств", text)
    ]
    ceased = [col for col, text in captions.items() if "в порядке банкротства" in text]
    if len(ceased) != 1 or len(proceedings) > 1:
        raise HistoryError("BANKRUPTCY_CAPTION_AMBIGUOUS")
    loc = {"total": 2, "ceased_bankruptcy": ceased[0]}
    if proceedings:
        loc["in_bankruptcy_procedure"] = proceedings[0]
    result = {}
    for meaning, col in loc.items():
        number = modern.code(sheet.cell_value(header_row, col), 2)
        if number is None:
            raise HistoryError("SOURCE_INDICATOR_CODE_MISSING")
        result[meaning] = (col, "c" + number, str(int(number)))
    if len({value[0] for value in result.values()}) != len(result):
        raise HistoryError("SOURCE_SELECTED_COLUMNS_OVERLAP")
    return header_row, result


def _geography(sheet, row):
    """Return the original geographic key without guessing a district code."""
    name = sheet.cell_value(row, 1)
    if not isinstance(name, str) or not name.strip():
        return None
    name_lower = name.strip().casefold()
    number = modern.code(sheet.cell_value(row, 0), 2)
    if name_lower == "российская федерация" or "федеральный округ" in name_lower:
        if number is not None:
            raise HistoryError("AGGREGATE_HAS_UNEXPECTED_NUMERIC_CODE")
        return ("", name)
    if number is not None and modern.REGION_RE.fullmatch(number):
        return (number, name)
    return None


def _kind_control(book, geography, kinds, mappings_by_kind, expected):
    """Cross-check each *reported* observation against its transposed sheet."""
    code, name = geography
    candidates = [code] if code else [name, name.strip()]
    sheet_name = next((n for n in candidates if n in book.sheet_names()), None)
    if sheet_name is None and not code:
        return 0, []
    if sheet_name is None:
        raise HistoryError("REGION_CONTROL_SHEET_MISSING:" + code)
    sheet = book.sheet_by_name(sheet_name)
    found = {}
    for row in range(sheet.nrows):
        if sheet.ncols < 3:
            continue
        kind = modern.code(sheet.cell_value(row, 1), 4)
        if kind not in kinds:
            continue
        if kind in found:
            raise HistoryError("DUPLICATE_CONTROL_KIND:" + str(geography))
        found[kind] = {}
        for meaning, (col, _, _) in mappings_by_kind[kind].items():
            if col >= sheet.ncols:
                raise HistoryError("CONTROL_MEASURE_COLUMN_MISSING")
            found[kind][meaning] = modern.integer(
                sheet.cell_value(row, col), "CONTROL_VALUE_NOT_INTEGER"
            )
    # The transposed region view can itself omit publisher categories.
    # Such omissions are recorded as source inconsistencies. They do not
    # erase values present on the selected legal-kind worksheets.
    disagreements = []
    for missing_kind in sorted(set(kinds) - set(found)):
        disagreements.append(
            {
                "territory_code": code,
                "territory_name": name,
                "kind": missing_kind,
                "issue": "REGION_CONTROL_KIND_NOT_PUBLISHED",
                "kind_sheet_values": expected[missing_kind],
            }
        )
    checked = 0
    for kind in sorted(set(kinds) & set(found)):
        for meaning in mappings_by_kind[kind]:
            checked += 1
            if found[kind][meaning] != expected[kind][meaning]:
                disagreements.append(
                    {
                        "territory_code": code,
                        "territory_name": name,
                        "kind": kind,
                        "meaning": meaning,
                        "issue": "REGION_CONTROL_VALUE_DIFFERS",
                        "kind_sheet_value": expected[kind][meaning],
                        "region_sheet_value": found[kind][meaning],
                    }
                )
    return checked, disagreements


def is_registration_record_label(label):
    """Exclude a count of registration *records*, not a legal-entity kind.

    This is based exclusively on the current release's national-summary label.
    It does not exclude legal entities merely described as specially registered.
    """
    if not isinstance(label, str):
        return False
    words = " ".join(label.casefold().split())
    return bool(
        re.search(r"запис\w*\s+(?:о\s+)?(?:государственн\w*\s+)?регистрац\w*", words)
        or re.search(r"регистрационн\w*\s+запис\w*", words)
    )


def extract_observations(xls, reference_date, *, checkpoint=None):
    """Preserve the complete printed geographic order and source metric coverage."""
    book = open_source_workbook(xls)
    try:
        sheet_names = set(book.sheet_names())
        candidate_codes = sorted(
            name
            for name in sheet_names
            if re.fullmatch(r"1[0-2][0-9]{2}", name) and name != "1300"
        )
        if not candidate_codes and "Российская Федерация" in sheet_names:
            national_title = str(
                book.sheet_by_name("Российская Федерация").cell_value(0, 0)
            ).casefold()
            if "раздел 2" in national_title:
                raise HistoryError("SOURCE_SECTION_ONE_NOT_PUBLISHED")
        if not (
            12 <= len(candidate_codes) <= 90 and "Российская Федерация" in sheet_names
        ):
            raise HistoryError("LEGAL_KIND_SHEETS_UNEXPECTED")
        nation = book.sheet_by_name("Российская Федерация")
        kind_labels_all = {}
        for row in range(nation.nrows):
            number = (
                modern.code(nation.cell_value(row, 1), 4) if nation.ncols >= 2 else None
            )
            if number in candidate_codes:
                label = nation.cell_value(row, 0)
                if not isinstance(label, str) or not label.strip():
                    raise HistoryError("SOURCE_KIND_DESCRIPTION_MISSING:" + number)
                if number in kind_labels_all and kind_labels_all[number] != label:
                    raise HistoryError("SOURCE_KIND_DESCRIPTION_CONFLICT:" + number)
                kind_labels_all[number] = label
        if set(kind_labels_all) != set(candidate_codes):
            raise HistoryError("SOURCE_NATIONAL_KIND_SUMMARY_INCOMPLETE")
        excluded_non_entity_sheets = {
            code: label
            for code, label in kind_labels_all.items()
            if is_registration_record_label(label)
        }
        kinds = [
            code for code in candidate_codes if code not in excluded_non_entity_sheets
        ]
        if not 12 <= len(kinds) <= 90:
            raise HistoryError("LEGAL_ENTITY_KIND_COUNT_UNEXPECTED")
        kind_labels = {code: kind_labels_all[code] for code in kinds}
        master_order = None
        order_disagreements = []
        excluded_incomplete_kind_sheets = {}
        records = {}
        common_mapping = None
        mappings_by_kind = {}
        for kind in kinds:
            if checkpoint is not None:
                checkpoint()
            sheet = book.sheet_by_name(kind)
            header_row = _header_row(sheet)
            if sheet.ncols == 3:
                # Publisher prints only indicator 1 for this legal-kind sheet.
                if modern.code(sheet.cell_value(header_row, 2), 2) != "01":
                    raise HistoryError("TOTAL_ONLY_SHEET_NUMBER_UNEXPECTED:" + kind)
                mapping = {"total": (2, "c01", "1")}
            else:
                if common_mapping is None:
                    header_row, mapping = indicator_plan(sheet)
                    common_mapping = dict(mapping)
                else:
                    mapping = common_mapping
                    for meaning, (col, _, number) in mapping.items():
                        if sheet.ncols <= col or modern.code(
                            sheet.cell_value(header_row, col), 2
                        ) != str(number).zfill(2):
                            raise HistoryError(
                                "INDICATOR_CODE_DIFFERS_BETWEEN_KINDS:"
                                + kind
                                + ":"
                                + meaning
                            )
            mappings_by_kind[kind] = mapping
            order = []
            for row in range(header_row + 1, sheet.nrows):
                geo = _geography(sheet, row)
                if geo is None:
                    continue
                counts = {
                    meaning: modern.integer(
                        sheet.cell_value(row, col), "SOURCE_COUNT_NOT_INTEGER"
                    )
                    for meaning, (col, _, _) in mapping.items()
                }
                if geo in order:
                    raise HistoryError("DUPLICATE_GEOGRAPHY_ROW")
                order.append(geo)
                records.setdefault(geo, {})[kind] = counts
            if master_order is None:
                master_order = order
            elif order != master_order:
                if set(order) != set(master_order):
                    excluded_incomplete_kind_sheets[kind] = {
                        "reason": "SOURCE_KIND_WORKSHEET_GEOGRAPHIC_COVERAGE_DIFFERS",
                        "missing_geographies": [
                            list(geo) for geo in master_order if geo not in order
                        ],
                        "extra_geographies": [
                            list(geo) for geo in order if geo not in master_order
                        ],
                    }
                else:
                    first = next(
                        (
                            i
                            for i, (left, right) in enumerate(zip(master_order, order))
                            if left != right
                        ),
                        None,
                    )
                    order_disagreements.append(
                        {
                            "kind_code": kind,
                            "first_different_source_row_index": first,
                            "canonical_source_kind_code": kinds[0],
                            "issue": "SAME_PUBLISHED_TERRITORIES_DIFFERENT_ORDER",
                        }
                    )
        if excluded_incomplete_kind_sheets:
            retained = [k for k in kinds if k not in excluded_incomplete_kind_sheets]
            reviewed_2019_sparse_release = (
                reference_date == date(2019, 6, 1)
                and retained == ["1000"]
                and len(excluded_incomplete_kind_sheets) == 32
                and all(
                    [
                        list(geo)
                        for geo in master_order
                        if geo == ("53", "Новгородская область")
                    ]
                    == detail["missing_geographies"]
                    and not detail["extra_geographies"]
                    for detail in excluded_incomplete_kind_sheets.values()
                )
            )
            if (
                len(excluded_incomplete_kind_sheets) > 8
                and not reviewed_2019_sparse_release
            ):
                raise HistoryError(
                    "TOO_MANY_INCOMPLETE_SOURCE_KIND_SHEETS:"
                    + str(len(excluded_incomplete_kind_sheets))
                )
            kinds = retained
            kind_labels = {k: kind_labels[k] for k in kinds}
            for geo in list(records):
                if geo not in master_order:
                    del records[geo]
                    continue
                for ignored in excluded_incomplete_kind_sheets:
                    records[geo].pop(ignored, None)
        if not (
            12 <= len(kinds) <= 90
            or (reference_date == date(2019, 6, 1) and kinds == ["1000"])
        ):
            raise HistoryError("TOO_FEW_GEOGRAPHICALLY_COMPLETE_KINDS")
        if common_mapping is None:
            raise HistoryError("SOURCE_BANKRUPTCY_COLUMNS_NOT_PUBLISHED")
        if (
            not master_order
            or master_order[0][0] != ""
            or master_order[0][1].strip().casefold() != "российская федерация"
        ):
            raise HistoryError("SOURCE_RUSSIA_ROW_NOT_FIRST")
        districts = [
            x
            for x in master_order
            if not x[0] and "федеральный округ" in x[1].casefold()
        ]
        subjects = [x for x in master_order if x[0]]
        if (
            not 6 <= len(districts) <= 9
            or not 60 <= len(subjects) <= 110
            or len(master_order) != 1 + len(districts) + len(subjects)
        ):
            raise HistoryError("SOURCE_GEOGRAPHY_PERIMETER_UNEXPECTED")
        repeated = {
            code: [name for k, name in subjects if k == code]
            for code, _ in subjects
            if sum(1 for k, _ in subjects if k == code) > 1
        }
        if any(set(records[geo]) != set(kinds) for geo in master_order):
            raise HistoryError("KIND_COVERAGE_INCOMPLETE")
        source_differences = []
        for kind in kinds:
            for meaning in mappings_by_kind[kind]:
                total = int(records[master_order[0]][kind][meaning])
                territorial = sum(int(records[geo][kind][meaning]) for geo in subjects)
                if total != territorial:
                    source_differences.append(
                        {
                            "kind_code": kind,
                            "meaning": meaning,
                            "reported_russia": total,
                            "sum_territorial_rows": territorial,
                            "difference": total - territorial,
                        }
                    )
        crosschecked = 0
        orientation_differences = []
        for geo in master_order:
            if geo[0] in repeated:
                # A single code does not identify which of the source's
                # overlapping territories a transposed sheet represents.
                # Both rows remain in the evidence; do not double-match them.
                continue
            cells, disagreements = _kind_control(
                book, geo, kinds, mappings_by_kind, records[geo]
            )
            crosschecked += cells
            orientation_differences.extend(disagreements)
            if len(orientation_differences) > 5000:
                raise HistoryError("SOURCE_ORIENTATION_CONFLICT_TOO_BROAD")
        result_columns = ["region_code", "region_name"]
        coverage = {}
        metric_order = ("total", "in_bankruptcy_procedure", "ceased_bankruptcy")
        for meaning in metric_order:
            matching = [kind for kind in kinds if meaning in mappings_by_kind[kind]]
            if not matching:
                continue
            prefixes = {mappings_by_kind[kind][meaning][1] for kind in matching}
            if len(prefixes) != 1:
                raise HistoryError("SOURCE_METRIC_CODE_INCONSISTENT")
            prefix = next(iter(prefixes))
            result_columns.extend(prefix + "_" + kind for kind in matching)
            coverage[meaning] = matching
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(result_columns)
        for geo in master_order:
            line = [geo[0], geo[1]]
            for meaning in metric_order:
                for kind in coverage.get(meaning, []):
                    line.append(records[geo][kind][meaning])
            writer.writerow(line)
        source_map = {
            meaning: {
                "source_column_index_0based": column,
                "source_indicator": number,
                "csv_prefix": prefix,
            }
            for meaning, (column, prefix, number) in (
                common_mapping or {"total": (2, "c01", "1")}
            ).items()
        }
        return output.getvalue().encode("utf-8"), {
            "rows": len(master_order),
            "regions": len(subjects),
            "federal_districts": len(districts),
            "legal_kinds": len(kinds),
            "source_indicator_map": source_map,
            "source_kind_metric_coverage": coverage,
            "crosschecked_values": crosschecked,
            "kind_codes": kinds,
            "national_territorial_differences": source_differences,
            "overlapping_territory_codes": repeated,
            "geographic_order": "canonical_first_legal_kind_sheet",
            "source_sheet_order_disagreements": order_disagreements,
            "orientation_disagreements_count": len(orientation_differences),
            "orientation_disagreements_sha256": (
                hashlib.sha256(
                    json.dumps(
                        orientation_differences,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                if orientation_differences
                else None
            ),
            "orientation_disagreements": orientation_differences[:50],
            "kind_labels": kind_labels,
            "excluded_source_non_entity_sheets": excluded_non_entity_sheets,
            "excluded_incomplete_kind_sheets": excluded_incomplete_kind_sheets,
        }
    finally:
        book.release_resources()
