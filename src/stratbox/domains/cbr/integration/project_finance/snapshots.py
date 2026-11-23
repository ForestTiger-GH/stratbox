"""Complete integrated dataset interchange and input-version validation."""
from __future__ import annotations
from datetime import date
import json
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import TypedTable
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from .contracts import EscrowDataset, EscrowRelease
from stratbox.domains.cbr.tables.project_finance.codec import (_schema, T, I, D, B, _json, _string_tuple, _specs, _read_specs, _frame, frame_table, _check, _check_lineage, _build, SPECS)

DATASET = DataContract("cbr.escrow.dataset.snapshot", 2, DataRole.INTEGRATED)
ROW_FIELDS = (("display_order", I, False), ("row_kind", T, False), ("Регион", T, False), ("federal_district_name", T, True), ("region_number", I, True))
OBS_FIELDS = (("period", T, False), ("region", T, False), ("row_kind", T, False), ("indicator_code", T, False),
              ("value", D, True), ("raw_token", T, True), ("status", T, False), ("source_name", T, False),
              ("sheet_name", T, False), ("source_row", I, False), ("source_column", I, False))
OBSERVATIONS = _schema("dataset.observations", OBS_FIELDS, role=DataRole.INTEGRATED,
                       key=("period", "region", "row_kind", "indicator_code"))
ROWS = _schema("dataset.rows", (("period", T, False), *ROW_FIELDS), role=DataRole.INTEGRATED, key=("period", "row_kind", "Регион"))
RELEASES = _schema("dataset.releases", (("period", T, False), ("source_name", T, False), ("source_id", T, True),
                                      ("original_sha256", T, False), ("original_size", I, False), ("sheet_name", T, False),
                                      ("method_version", T, False), ("unmapped_headers", T, False)), role=DataRole.INTEGRATED, key=("period",))
SELECTION = _schema("dataset.selection", (("complete", B, False), ("failures", T, False), ("stop_reason", T, True), ("integration_profile", T, False)), role=DataRole.INTEGRATED)


def _release_input(release):
    return UsedInputReceipt("source_workbook", release.original_identity,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only", release.source_id)


def dataset_tables(dataset):
    from stratbox.domains.cbr.tables.project_finance.parser import decode_cell
    if not isinstance(dataset, EscrowDataset) or not dataset.releases or type(dataset.selection_complete) is not bool:
        raise ValueError("escrow.dataset_invalid")
    if (dataset.integration_profile != "cbr-escrow-integration-2"
            or not isinstance(dataset.failures, tuple)
            or any(not isinstance(item, tuple) or len(item) != 2 or not all(type(value) is str and value for value in item) for item in dataset.failures)
            or dataset.stop_reason is not None and (type(dataset.stop_reason) is not str or not dataset.stop_reason)
            or dataset.selection_complete and (dataset.failures or dataset.stop_reason)
            or any(release.method_version != "cbr-escrow-xlsx-flake-2" for release in dataset.releases)):
        raise ValueError("escrow.dataset_selection_invalid")
    periods = tuple(release.period for release in dataset.releases)
    if periods != tuple(sorted(set(periods))):
        raise ValueError("escrow.duplicate_release")
    for period in periods:
        date.fromisoformat(period)
    observations = frame_table(dataset.observations, OBSERVATIONS)
    rows = frame_table(dataset.rows, ROWS)
    specs = _specs(dataset.indicator_specs)
    codes = {spec.code for spec in dataset.indicator_specs}
    region_keys = {(row[0], row[2], row[3]) for row in rows.rows}
    if {row[0] for row in rows.rows} != set(periods):
        raise ValueError("escrow.dataset_period_mismatch")
    for period in periods:
        period_rows = [row for row in rows.rows if row[0] == period]
        if ([row[1] for row in period_rows] != list(range(1, len(period_rows) + 1))
                or any(row[2] not in {"region", "federal_district", "rf_total"} for row in period_rows)
                or len({row[3] for row in period_rows}) != len(period_rows)):
            raise ValueError("escrow.dataset_rows_invalid")
    release_by_period = {release.period: release for release in dataset.releases}
    for period, region, row_kind, code, value, token, status, source_name, sheet, source_row, source_column in observations.rows:
        release = release_by_period.get(period)
        if (release is None or (period, row_kind, region) not in region_keys or code not in codes
                or (source_name, sheet) != (release.source_name, release.sheet_name)
                or source_row < 1 or source_column < 1 or (status == "numeric") != (value is not None)
                or status not in {"numeric", "blank", "marker", "unparsed", "formula_unresolved"}
                or (status == "numeric" and (token is None or decode_cell(token)[3] != value))):
            raise ValueError("escrow.dataset_observation_invalid")
    releases = TypedTable(RELEASES, tuple((r.period, r.source_name, r.source_id, r.original_identity.sha256,
                                          r.original_identity.size, r.sheet_name, r.method_version, _json(list(r.unmapped_headers))) for r in dataset.releases))
    return (("selection", TypedTable(SELECTION, ((dataset.selection_complete, _json(list(dataset.failures)), dataset.stop_reason, dataset.integration_profile),))), ("releases", releases),
            ("indicators", specs), ("rows", rows), ("observations", observations))


def dataset_snapshot(dataset, *, dataset_id="cbr.escrow.integrated", version_id=None):
    return _build(dataset_id, version_id, DATASET, dataset_tables(dataset), coverage=dataset.coverage,
                  inputs=tuple(_release_input(release) for release in dataset.releases))


def dataset_from_snapshot(snapshot):
    components = {"selection": SELECTION, "releases": RELEASES, "indicators": SPECS, "rows": ROWS, "observations": OBSERVATIONS}
    _check(snapshot, DATASET, components)
    selection = snapshot.table("selection")
    if len(selection.rows) != 1:
        raise ValueError("escrow.snapshot_selection_invalid")
    releases = tuple(EscrowRelease(p, n, sid, ByteIdentity(sha, size), sheet, method, _string_tuple(unknown))
                     for p, n, sid, sha, size, sheet, method, unknown in snapshot.table("releases").rows)
    value = EscrowDataset(_frame(snapshot.table("observations")), _frame(snapshot.table("rows")), releases,
                          _read_specs(snapshot.table("indicators")), snapshot.manifest.coverage, selection.rows[0][0],
                          failures=tuple(tuple(item) for item in json.loads(selection.rows[0][1])),
                          stop_reason=selection.rows[0][2], integration_profile=selection.rows[0][3])
    dataset_tables(value)
    _check_lineage(snapshot, tuple(_release_input(release) for release in releases))
    return value
