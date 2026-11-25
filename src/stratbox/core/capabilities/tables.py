"""Physical selection and explicitly profiled observation interpretation."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Mapping

from stratbox.core.execution.contracts import OperationFailure
from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.workbook_cells import WorkbookCells, WorkbookCell
from stratbox.shared.data.scalars import encode_scalar
from stratbox.shared.data.assessment import CoverageCoordinate, CoverageAssessment, ProcessingFinding, ValueEvidence, observation_coordinate
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.evidence import UsedInputReceipt


@dataclass(frozen=True, slots=True)
class CellSelection:
    """A physical rectangle with source coordinates and original cell tokens."""
    source_identity: ByteIdentity
    sheet: str
    first_row: int
    first_column: int
    rows: tuple[tuple[WorkbookCell | None, ...], ...]

    @property
    def identity(self):
        return ByteIdentity.of(canonical_manifest_bytes({
            "source": self.source_identity.sha256, "sheet": self.sheet,
            "first_row": self.first_row, "first_column": self.first_column,
            "rows": [[None if c is None else (c.coordinate, *encode_scalar(c.value), c.raw_token, c.kind)
                      for c in row] for row in self.rows]}))


def table_select(request: Mapping, invocation):
    request = {**dict(request.get("profile", {})), **dict(request)}
    workbook = request["workbook"]
    if not isinstance(workbook, WorkbookCells):
        raise OperationFailure("table.workbook_required")
    name = request.get("sheet", workbook.sheets[0].name if workbook.sheets else "")
    matches = [sheet for sheet in workbook.sheets if sheet.name == name]
    if len(matches) != 1:
        raise OperationFailure("table.member_missing")
    sheet = matches[0]
    first_row, first_column = request.get("first_row", 1), request.get("first_column", 1)
    last_row, last_column = request.get("last_row", sheet.rows), request.get("last_column", sheet.columns)
    if any(type(n) is not int for n in (first_row, first_column, last_row, last_column)) or not (
        1 <= first_row <= last_row <= sheet.rows and 1 <= first_column <= last_column <= sheet.columns
    ):
        raise OperationFailure("table.selection_invalid")
    count = (last_row - first_row + 1) * (last_column - first_column + 1)
    if count > request.get("max_cells", 1_000_000):
        raise OperationFailure("table.selection_limit")
    invocation.budget.charge("cells", count)
    cells = {(cell.row, cell.column): cell for cell in sheet.cells}
    rows = []
    for row in range(first_row, last_row + 1):
        invocation.check_cancelled()
        rows.append(tuple(cells.get((row, column)) for column in range(first_column, last_column + 1)))
    return CellSelection(workbook.identity, sheet.name, first_row, first_column, tuple(rows))


def table_reshape(request: Mapping, invocation):
    selected = request["table"]
    if not isinstance(selected, CellSelection):
        raise OperationFailure("table.selection_required")
    if request.get("transpose", False):
        return replace(selected, rows=tuple(tuple(row) for row in zip(*selected.rows)))
    return selected


def _date(value):
    return value if type(value) is date else date.fromisoformat(value)


def fields_interpret(request: Mapping, invocation):
    """Interpret a declared rectangle; no date, unit or subject is guessed."""
    selected = request["table"]
    if not isinstance(selected, CellSelection):
        raise OperationFailure("interpret.selection_required")
    profile = dict(request.get("profile", {}))
    profile.update({name: value for name, value in request.items() if name not in {"table", "profile"}})
    required = {"dataset_id", "release_id", "subject_column", "value_column", "metric_id", "unit", "period_kind", "perimeter"}
    if required - profile.keys():
        raise OperationFailure("interpret.profile_incomplete")
    subject_column, value_column = profile["subject_column"], profile["value_column"]
    columns = len(selected.rows[0]) if selected.rows else 0
    if (any(type(c) is not int or not 0 <= c < columns for c in (subject_column, value_column))
            or type(profile.get("header_rows", 1)) is not int or profile.get("header_rows", 1) < 0):
        raise OperationFailure("interpret.column_invalid")
    expected_headers = profile.get("expected_headers", {})
    for column, expected in expected_headers.items():
        cell = selected.rows[0][int(column)] if selected.rows else None
        if cell is None or cell.value != expected:
            raise OperationFailure("interpret.header_mismatch")
    try:
        period = (PeriodRef("interval", start=_date(profile["start"]), end=_date(profile["end"]))
                  if profile["period_kind"] == "interval" else
                  PeriodRef(profile["period_kind"], as_of=_date(profile["as_of"])))
        metric = MetricRef(profile["metric_id"], profile["unit"], profile.get("quantity_kind"),
                           profile.get("definition_version"), Decimal(str(profile["scale"])) if "scale" in profile else None)
    except (KeyError, TypeError, ValueError, InvalidOperation):
        raise OperationFailure("interpret.semantics_invalid") from None
    observations = []
    for row in selected.rows[profile.get("header_rows", 1):]:
        invocation.check_cancelled()
        subject, cell = row[subject_column], row[value_column]
        if subject is None or subject.value in (None, ""):
            if any(c is not None and c.value is not None for c in row):
                raise OperationFailure("interpret.subject_missing")
            continue
        raw, value = (None, None) if cell is None else (
            cell.raw_token if cell.raw_token is not None else cell.value if isinstance(cell.value, str) else None, cell.value)
        if value is None:
            status = "missing" if cell is None else "blank"
        elif isinstance(value, str) and value in profile.get("status_tokens", {}):
            status = profile["status_tokens"][value]
            if status not in {"blank", "dash", "missing", "not_applicable", "withheld"}:
                raise OperationFailure("interpret.status_token_invalid")
            value = None
        elif value in profile.get("missing_tokens", ("-", "—")):
            value, status = None, "dash"
        else:
            try:
                if type(value) not in (int, Decimal):
                    value = Decimal(str(value).replace(" ", "").replace(",", "."))
                if not Decimal(value).is_finite():
                    raise InvalidOperation()
                status = "reported"
            except (ValueError, TypeError, InvalidOperation):
                raise OperationFailure("interpret.number_invalid") from None
        dimensions = tuple((key, str(row[int(column)].value)) for key, column in
                           sorted(profile.get("dimension_columns", {}).items()) if row[int(column)] is not None)
        coordinate = cell.coordinate if cell else f"row-{selected.first_row + len(observations)}"
        observations.append(Observation(SubjectRef(profile.get("subject_namespace", "source"), str(subject.value)),
            metric, period, dimensions, profile["perimeter"], value, status,
            f"{selected.source_identity.sha256}:{selected.sheet}:{coordinate}", raw))
    if not observations and not profile.get("allow_empty", False):
        raise OperationFailure("interpret.observations_missing")
    lineage = (UsedInputReceipt("source", selected.source_identity,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only"),)
    return ObservationBatch(profile["dataset_id"], 1, profile["release_id"], tuple(observations), lineage)


def schema_check(request: Mapping, invocation):
    value = request["value"]
    if isinstance(value, ObservationBatch):
        if len(value.observations) < request.get("min_rows", 1):
            raise OperationFailure("schema.observations_missing")
        identities = [(o.subject, o.metric.id, o.period, o.dimensions, o.perimeter) for o in value.observations]
        if len(identities) != len(set(identities)):
            raise OperationFailure("schema.duplicate_observation")
        for observation in value.observations:
            observation.__post_init__()
            if request.get("require_reported", False) and observation.value_status != "reported":
                raise OperationFailure("schema.reported_value_required")
    return value


def extraction_assess(request: Mapping, invocation):
    """Accept observations with their measured scope and substantive findings."""
    batch, selected = request["observations"], request["table"]
    profile = request.get("profile", {})
    if not isinstance(batch, ObservationBatch) or not isinstance(selected, CellSelection):
        raise OperationFailure("extraction.assessment_inputs_required")
    observed, members, statuses = set(), [], {}
    for item in batch.observations:
        period = item.period.as_of.isoformat() if item.period.as_of is not None else f"{item.period.start}/{item.period.end}"
        observed.update((f"subject:{item.subject.namespace}:{item.subject.id}", f"metric:{item.metric.id}", f"period:{period}"))
        members.append(observation_coordinate(item).identity)
        statuses.setdefault(item.value_status, []).append(item.evidence_ref)
    expected = None
    if any(name in profile for name in ("expected_subjects", "expected_metrics", "expected_periods")):
        namespaces = {item.subject.namespace for item in batch.observations}
        namespace = profile.get("subject_namespace")
        if namespace is None and len(namespaces) == 1:
            namespace = next(iter(namespaces))
        if namespace is None and profile.get("expected_subjects"):
            raise OperationFailure("extraction.expected_subject_namespace_required")
        expected = tuple(sorted({
            *(f"subject:{namespace}:{value}" for value in profile.get("expected_subjects", ())),
            *(f"metric:{value}" for value in profile.get("expected_metrics", ())),
            *(f"period:{value}" for value in profile.get("expected_periods", ())),
        }))
    expected_coordinates = None
    if "expected_coordinates" in profile:
        declared = profile["expected_coordinates"]
        limit = profile.get("max_expected_coordinates", 100_000)
        if (not isinstance(declared, (tuple, list)) or type(limit) is not int or limit < 1
                or len(declared) > limit):
            raise OperationFailure("extraction.expected_coordinate_limit")
        invocation.budget.charge("objects", len(declared))
        coordinates = []
        try:
            for item in declared:
                if not isinstance(item, Mapping):
                    raise ValueError
                data = dict(item)
                data["dimensions"] = tuple(tuple(pair) for pair in data.get("dimensions", ()))
                coordinates.append(CoverageCoordinate(**data))
        except (TypeError, ValueError):
            raise OperationFailure("extraction.expected_coordinates_invalid") from None
        expected_coordinates = tuple(coordinates)
        if len({coordinate.identity for coordinate in expected_coordinates}) != len(expected_coordinates):
            raise OperationFailure("extraction.expected_coordinates_invalid")
    coverage = CoverageAssessment(batch.dataset_id + ":" + batch.release_id, tuple(members), True,
        tuple(sorted(observed)), expected, selected.source_identity,
        (selected.sheet, selected.first_row, selected.first_column, len(selected.rows), len(selected.rows[0])),
        expected_coordinates)
    findings = []
    for status in ("missing", "blank", "dash", "withheld", "not_applicable"):
        references = statuses.get(status, ())
        if references:
            findings.append(ProcessingFinding("extraction.values." + status, "warning", len(references),
                "Source values retain their distinct unavailable-value status.", tuple(references[:8]), scope_id=coverage.scope_id))
    absent = sorted(set(expected or ()) - observed)
    if absent:
        findings.append(ProcessingFinding("extraction.expected_coverage_missing", "warning", len(absent),
            "Declared axis members are absent from the observed selection.", tuple(absent[:8]), scope_id=coverage.scope_id))
    observed_members = set(members)
    missing_coordinates = tuple(coordinate for coordinate in (expected_coordinates or ()) if coordinate.identity not in observed_members)
    if missing_coordinates:
        findings.append(ProcessingFinding("extraction.expected_coordinates_missing", "warning", len(missing_coordinates),
            "Exact required observation coordinates are absent despite any matching axis marginals.",
            tuple(coordinate.identity for coordinate in missing_coordinates[:8]), scope_id=coverage.scope_id))
    if coverage.status == "unknown":
        findings.append(ProcessingFinding("extraction.coverage_unspecified", "information", 1,
            "No exact observation-coordinate expectation is supplied; axis coverage is recorded separately.", scope_id=coverage.scope_id))
    actual = dict(getattr(invocation.context, "binding_identities", ()))
    methods = tuple(sorted({value for key, value in actual.items() if key == "method" or key.startswith(("method:", "implementation:"))}))
    profiles = tuple(sorted({value for key, value in actual.items() if key == "profile" or key.startswith("profile:")}))
    if not profiles:
        # An inline profile is consumed data, rather than a registered profile
        # edition. Its exact content remains identifiable on the same boundary.
        profiles = (ByteIdentity.of(canonical_manifest_bytes(profile)).sha256,)
    references = tuple(sorted({value for key, value in actual.items() if key.startswith("reference:")}))
    evidence = ValueEvidence(frozenset({"extraction.validated", *statuses}), coverage, tuple(findings),
        method_fingerprints=methods, profile_fingerprints=profiles, reference_fingerprints=references)
    source_uses = batch.source_uses
    if not source_uses:
        actual_sources = {receipt.source_id for receipt in invocation.context.input_receipts
            if receipt.identity == selected.source_identity and receipt.source_id is not None}
        declared = profile.get("source_id") or batch.dataset_id
        source_uses = tuple(SourceUse(SourceCoordinate(source_id=source, issue_id=batch.release_id,
            material_identity=selected.source_identity, layout_edition=profile.get("layout_edition"),
            semantic_profile_edition=profiles[0] if profiles else None), qualification="observed" if actual_sources else "declared",
            evidence_ref=selected.source_identity.sha256) for source in sorted(actual_sources or {declared}))
    value = replace(batch, source_uses=source_uses, evidence=evidence)
    return {"observations": value, "coverage": coverage, "findings": tuple(findings)}


def numbers_evaluate(request: Mapping, invocation):
    """An aligned two-input ratio; unmatched keys and zero denominators fail."""
    numerator, denominator = request["numerator"], request["denominator"]
    if not isinstance(numerator, ObservationBatch) or not isinstance(denominator, ObservationBatch):
        raise OperationFailure("calculation.observations_required")
    def keyed(batch):
        pairs = [((o.subject, o.period, o.dimensions, o.perimeter), o) for o in batch.observations]
        result = dict(pairs)
        if len(result) != len(pairs):
            raise OperationFailure("calculation.duplicate_key")
        return result
    left, right = keyed(numerator), keyed(denominator)
    if left.keys() != right.keys() or not left:
        raise OperationFailure("calculation.coverage_mismatch")
    rows = []
    metric = MetricRef(request.get("metric_id", "ratio"), request.get("unit", "ratio"), "ratio", "1")
    multiplier = Decimal(str(request.get("multiplier", 1)))
    for key, item in left.items():
        invocation.check_cancelled()
        other = right[key]
        if (item.metric.unit != other.metric.unit or item.metric.scale != other.metric.scale
                or item.metric.quantity_kind != other.metric.quantity_kind):
            raise OperationFailure("calculation.unit_mismatch")
        if item.value is None or other.value is None:
            raise OperationFailure("calculation.value_unavailable")
        if Decimal(other.value) == 0:
            raise OperationFailure("calculation.zero_denominator")
        value = Decimal(item.value) / Decimal(other.value) * multiplier
        rows.append(replace(item, metric=metric, value=value, value_status="derived", raw_token=None,
                            evidence_ref=f"ratio:{item.evidence_ref}:{other.evidence_ref}"))
    return ObservationBatch((request.get("dataset_id") or numerator.dataset_id + ".ratio"), 1,
        numerator.release_id, tuple(rows), tuple(dict.fromkeys((*numerator.lineage, *denominator.lineage))),
        tuple(dict.fromkeys((*numerator.source_uses, *denominator.source_uses))))
