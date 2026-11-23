"""Historical Part I selection from retained cells, with explicit source omissions."""
import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.snapshots import CoverageDimension, SnapshotCoverage
from stratbox.shared.identity import canonical_manifest_bytes

from ...publications.legal_entities.source import DATE_RE
from ...publications.legal_entities.source_history import MIN_DATE
from ..contracts import FieldDisposition, SourceProjection, ValidationFinding, ValidationReport
from .archive import member_name
from .history import HistoryError, _geography, _header_row, project_book
from .parser import code

PROFILE = "fns.1yur.part-i-reported.v1"


class CellSheet:
    """Sparse retained cells with the historical selector's zero-based interface."""
    def __init__(self, sheet):
        self.name, self.nrows, self.ncols = sheet.name, sheet.rows, sheet.columns
        self._cells = {(cell.row - 1, cell.column - 1): cell for cell in sheet.cells}

    def cell_value(self, row, column):
        cell = self._cells.get((row, column))
        return "" if cell is None or cell.value is None else cell.value

    def cell(self, row, column):
        return self._cells.get((row, column))


class CellBook:
    def __init__(self, workbook):
        self._sheets = {sheet.name: CellSheet(sheet) for sheet in workbook.sheets}

    def sheet_names(self):
        return tuple(self._sheets)

    def sheet_by_name(self, name):
        return self._sheets[name]


def select_part_i(flake):
    selected = "main" if flake.container_format == "standalone" else member_name(
        tuple(item.name for item in flake.inventory))
    for name, workbook in flake.members:
        if name != selected:
            continue
        printed = DATE_RE.search(name.rsplit("/", 1)[-1])
        if printed is not None and date(int(printed[3]), int(printed[2]), int(printed[1])) != flake.context.observation_date:
            raise HistoryError("SOURCE_MEMBER_DATE_MISMATCH")
        return name, workbook
    raise HistoryError("SELECTED_PART_I_NOT_ADMITTED")


def project_reported(flake, *, checkpoint=None):
    if flake.context.observation_date.day != 1 or not MIN_DATE <= flake.context.observation_date <= date(2099, 12, 31):
        raise HistoryError("SOURCE_REFERENCE_DATE_INVALID")
    member, workbook = select_part_i(flake)
    book = CellBook(workbook)
    original, facts = project_book(book, flake.context.observation_date, checkpoint=checkpoint)
    rows = list(csv.reader(StringIO(original.decode("utf-8"), newline="")))
    header = rows[0]
    lookups = {}
    for field in header[2:]:
        indicator, kind = field.split("_", 1)
        sheet = book.sheet_by_name(kind)
        number_row = _header_row(sheet)
        columns = [column for column in range(2, sheet.ncols)
                   if code(sheet.cell_value(number_row, column), 2) == indicator[1:]]
        if len(columns) != 1:
            raise HistoryError("SOURCE_INDICATOR_COLUMN_AMBIGUOUS")
        geography = {}
        for row in range(number_row + 1, sheet.nrows):
            geo = _geography(sheet, row)
            if geo is not None:
                if geo in geography:
                    raise HistoryError("SOURCE_GEOGRAPHY_DUPLICATE")
                geography[geo] = row
        lookups[field] = sheet, columns[0], geography
    observations = []
    for values in rows[1:]:
        region_code, label = values[:2]
        perimeter = "published_territory" if region_code else (
            "published_national" if label.strip().casefold() == "российская федерация" else "published_district")
        for field, token in zip(header[2:], values[2:]):
            sheet, column, geography = lookups[field]
            row = geography[(region_code, label)]
            cell = sheet.cell(row, column)
            if cell is None:
                raise HistoryError("SOURCE_SELECTED_CELL_MISSING")
            indicator, kind = field.split("_", 1)
            evidence = f"member:{member}:sheet:{kind}:cell:{cell.coordinate}"
            # The published issue date locates the observation. A particular source
            # indicator's stock/flow interpretation is assigned in integration.
            observations.append(Observation(
                SubjectRef("fns.1yur.geography", region_code + ":" + label if region_code else label),
                MetricRef(field, "count", "count", PROFILE, Decimal(1)),
                PeriodRef("as_of", flake.context.observation_date),
                (("source_indicator", indicator), ("source_legal_kind", kind),
                 ("region_code", region_code), ("published_label", label)),
                perimeter, int(token), "reported", evidence, cell.raw_token))
    dispositions = [FieldDisposition(field, field, "reported_field_selected") for field in header[2:]]
    source_fields = set(header[2:])
    for kind in (*facts["kind_codes"], *facts["excluded_incomplete_kind_sheets"]):
        sheet = book.sheet_by_name(kind)
        number_row = _header_row(sheet)
        for column in range(2, sheet.ncols):
            number = code(sheet.cell_value(number_row, column), 2)
            if number is not None:
                source_fields.add("c" + number + "_" + kind)
    omitted_source_fields = sorted(source_fields - set(header[2:]))
    dispositions.extend(FieldDisposition(field, None, "outside_reviewed_reported_projection")
                        for field in omitted_source_fields)
    for kind in facts["excluded_source_non_entity_sheets"]:
        dispositions.append(FieldDisposition("sheet:" + kind, None, "registration_record_category_outside_entity_projection"))
    for kind in facts["excluded_incomplete_kind_sheets"]:
        dispositions.append(FieldDisposition("sheet:" + kind, None, "geographically_incomplete_kind_preserved_in_flake"))
    for name, _ in flake.members:
        if name != member:
            dispositions.append(FieldDisposition("member:" + name, None, "outside_reviewed_part_i_projection"))
    qualifications = ["source.selected_part_i_fields", *flake.qualifications]
    if facts["excluded_incomplete_kind_sheets"]:
        qualifications.append("source.incomplete_legal_kind_projection")
    if facts["national_territorial_differences"]:
        qualifications.append("source.national_territorial_disagreement")
    if facts["orientation_disagreements_count"]:
        qualifications.append("source.orientation_disagreement")
    if facts["overlapping_territory_codes"]:
        qualifications.append("source.overlapping_territory_codes")
    facts["selected_member"] = member
    batch = ObservationBatch("fns.1yur.reported", 1, "source-" + flake.source_identity.sha256,
        tuple(observations), flake.lineage, (SourceUse(SourceCoordinate(flake.context.series_id,
            source_group_id="registration_statistics", issue_id=flake.context.issue_id, asset_id=flake.context.asset_id,
            material_identity=flake.source_identity, semantic_profile_edition=PROFILE), "flake", "domain_validated"),))
    requested_kinds = tuple(sorted(set(facts["kind_codes"]) | set(facts["excluded_incomplete_kind_sheets"])))
    missing_kinds = tuple(sorted(facts["excluded_incomplete_kind_sheets"]))
    return SourceProjection(flake.context, flake.identity, batch, PROFILE,
        SnapshotCoverage("partial", "Reviewed Part I indicators and geographically complete entity sheets; every omitted source cell remains in the workbook flake.", (
            CoverageDimension("source_fields", requested=tuple(sorted(source_fields)), materialized=tuple(sorted(source_fields)),
                validated=tuple(header[2:]), output=tuple(header[2:]), missing=tuple(omitted_source_fields)),
            CoverageDimension("legal_kinds", requested=requested_kinds, materialized=requested_kinds,
                validated=tuple(facts["kind_codes"]), output=tuple(facts["kind_codes"]), missing=missing_kinds),
        )),
        tuple(dict.fromkeys(qualifications)), tuple(dispositions), canonical_manifest_bytes(facts).decode("utf-8"))


def validate(flake):
    findings = [ValidationFinding("source." + item.disposition, "warning", "member:" + item.name)
                for item in flake.inventory if item.disposition != "extracted"]
    try:
        projection = project_reported(flake)
        findings.extend(ValidationFinding(code, "warning", "part_i") for code in projection.qualifications
                        if code.startswith("source."))
    except HistoryError as error:
        findings.append(ValidationFinding("source." + str(error).lower().split(":")[0], "error", "part_i"))
    return ValidationReport(PROFILE, flake.identity, tuple(findings))
