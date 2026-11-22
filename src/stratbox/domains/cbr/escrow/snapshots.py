"""Complete escrow interchange through typed logical dataset snapshots.

Physical storage is chosen by the caller. Decoders require every component and
validate domain structure before reconstructing a value for subsequent work.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import date
from decimal import Decimal
import json

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from .contracts import EscrowDataset, EscrowIndicatorSpec, EscrowParsedRow, EscrowPivotPack, EscrowRelease, ParsedEscrowFile, ResolvedEscrowColumn

FLAKE = DataContract("cbr.escrow.flake.snapshot", 1, DataRole.EXTRACTS)
DATASET = DataContract("cbr.escrow.dataset.snapshot", 1, DataRole.INTEGRATED)
VIEW = DataContract("cbr.escrow.view.snapshot", 1, DataRole.PRODUCTS)
T, I, D, B = ScalarType.TEXT, ScalarType.INT64, ScalarType.DECIMAL, ScalarType.BOOLEAN


def _schema(name, fields, *, role=DataRole.EXTRACTS, key=()):
    return TableSchema(DataContract(f"cbr.escrow.{name}", 1, role),
                       tuple(ColumnSchema(n, t, nullable) for n, t, nullable in fields), key)


METADATA = _schema("flake.metadata", (
    ("source_name", T, False), ("period", T, False), ("sheet_name", T, False), ("header_row", I, False),
    ("original_sha256", T, False), ("original_size", I, False), ("source_id", T, True), ("method_version", T, False),
    ("unmapped_headers", T, False),
))
COLUMNS = _schema("flake.columns", (("source_index", I, False), ("source_name", T, False), ("indicator_code", T, False)), key=("source_index",))
SPECS = _schema("indicators", (("indicator_code", T, False), ("specification", T, False)), key=("indicator_code",))
PARSED_ROWS = _schema("flake.rows", (("source_row_index", I, False), ("display_order", I, False), ("row_kind", T, False),
                                   ("entity_name", T, False), ("federal_district_name", T, True), ("region_number", I, True)), key=("source_row_index",))
CELLS = _schema("flake.cells", (
    ("source_row", I, False), ("source_column", I, False), ("source_header", T, False), ("indicator_code", T, True),
    ("raw_token", T, True), ("raw_kind", T, False), ("status", T, False), ("value", D, True),
    ("row_kind", T, False), ("region", T, False), ("display_order", I, False),
), key=("source_row", "source_column"))
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
SELECTION = _schema("dataset.selection", (("complete", B, False),), role=DataRole.INTEGRATED)
VIEW_META = _schema("view.metadata", (("source_sha256", T, True), ("source_size", I, True), ("missing_display", T, False)), role=DataRole.PRODUCTS)
VIEW_ROWS = _schema("view.rows", (("region", T, False), ("row_kind", T, False), ("federal_district_name", T, True)), role=DataRole.PRODUCTS, key=("region",))
VIEW_DATES = _schema("view.dates", (("period", T, False),), role=DataRole.PRODUCTS, key=("period",))
VIEW_VALUES = _schema("view.values", (("indicator_code", T, False), ("region", T, False), ("period", T, False),
                                     ("number", D, True), ("text", T, True)), role=DataRole.PRODUCTS, key=("indicator_code", "region", "period"))


def _json(value):
    return canonical_manifest_bytes(value).decode("utf-8")


def _string_tuple(value):
    result = json.loads(value)
    if not isinstance(result, list) or any(type(item) is not str for item in result):
        raise ValueError("escrow.snapshot_text_list_invalid")
    return tuple(result)


def _specs(values):
    return TypedTable(SPECS, tuple((spec.code, _json(asdict(spec))) for spec in values))


def _read_specs(table):
    if table.schema != SPECS:
        raise ValueError("escrow.snapshot_schema_invalid")
    output = []
    for code, payload in table.rows:
        fields = json.loads(payload)
        if not isinstance(fields, dict):
            raise ValueError("escrow.snapshot_indicators_invalid")
        fields["required_tokens"] = tuple(fields["required_tokens"])
        fields["forbidden_tokens"] = tuple(fields["forbidden_tokens"])
        item = EscrowIndicatorSpec(**fields)
        if (item.code != code or any(type(value) is not str or not value for value in (item.code, item.canonical_name, item.sheet_code))
                or item.value_kind not in {"number", "percent"} or type(item.order) is not int or item.order < 0
                or type(item.is_required) is not bool or type(item.is_output) is not bool
                or any(type(token) is not str or not token for token in (*item.required_tokens, *item.forbidden_tokens))):
            raise ValueError("escrow.snapshot_indicators_invalid")
        output.append(item)
    return tuple(output)


def _frame(table):
    import pandas as pd
    return pd.DataFrame(list(table.rows), columns=[column.name for column in table.schema.columns], dtype=object)


def frame_table(frame, schema):
    if tuple(frame.columns) != tuple(column.name for column in schema.columns):
        raise ValueError("escrow.snapshot_columns_invalid")
    return TypedTable(schema, tuple(tuple(row) for row in frame.itertuples(index=False, name=None)))


def _check(snapshot, contract, components):
    if (not isinstance(snapshot, DatasetSnapshot) or not snapshot.complete or snapshot.manifest.contract != contract
            or tuple(name for name, _ in snapshot.tables) != tuple(components)):
        raise ValueError("escrow.snapshot_invalid")
    for name, schema in components.items():
        if snapshot.table(name).schema != schema:
            raise ValueError("escrow.snapshot_schema_invalid")


def _check_lineage(snapshot, expected):
    observed = tuple(replace(item, availability="reference_only") for item in snapshot.manifest.inputs)
    if observed != expected or snapshot.manifest.parents:
        raise ValueError("escrow.snapshot_lineage_mismatch")


def _release_input(release):
    return UsedInputReceipt("source_workbook", release.original_identity,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only", release.source_id)


def _build(dataset_id, version_id, contract, tables, *, coverage, inputs=()):
    version = version_id or ByteIdentity.of(canonical_manifest_bytes(
        {"contract": contract.schema_id, "coverage": asdict(coverage),
         "tables": [[name, table.identity.sha256, table.identity.size] for name, table in tables],
         "inputs": [[item.role, item.identity.sha256, item.identity.size, item.source_id] for item in inputs]}
    )).sha256
    return DatasetSnapshot.build(dataset_id, version, contract, tables, coverage=coverage, inputs=inputs)


def flake_tables(flake):
    from .parser import CELL_COLUMNS, LONG_COLUMNS, ROW_COLUMNS
    if (not isinstance(flake, ParsedEscrowFile) or flake.original_identity is None or flake.df_cells is None
            or flake.method_version != "cbr-escrow-xlsx-flake-1" or type(flake.file_date) is not str):
        raise ValueError("escrow.flake_incomplete")
    date.fromisoformat(flake.file_date)
    if flake.header_row_index < 0 or not flake.rows or not flake.resolved_columns:
        raise ValueError("escrow.flake_structure_invalid")
    metadata = TypedTable(METADATA, ((flake.source_name, flake.file_date, flake.sheet_name, flake.header_row_index,
                                    flake.original_identity.sha256, flake.original_identity.size, flake.source_id,
                                    flake.method_version, _json(list(flake.unmapped_headers))),))
    specs = tuple(column.spec for column in flake.resolved_columns)
    rows = TypedTable(PARSED_ROWS, tuple((row.source_row_index, row.display_order, row.row_kind, row.entity_name,
                                        row.federal_district_name, row.region_number) for row in flake.rows))
    cells = frame_table(flake.df_cells, CELLS)
    column_table = TypedTable(COLUMNS, tuple((column.source_index, column.source_name, column.spec.code) for column in flake.resolved_columns))
    reconstructed = _restore_flake(metadata, column_table, _specs(specs), rows, cells)
    if (tuple(flake.df_rows.columns) != ROW_COLUMNS or tuple(flake.df_long.columns) != LONG_COLUMNS
            or not flake.df_rows.equals(reconstructed.df_rows) or not flake.df_long.equals(reconstructed.df_long)):
        raise ValueError("escrow.flake_projection_mismatch")
    return (("metadata", metadata), ("columns", column_table), ("indicators", _specs(specs)), ("rows", rows), ("cells", cells))


def _restore_flake(metadata, columns, specs_table, rows_table, cells):
    from .parser import LONG_COLUMNS, _build_rows_frame, decode_cell
    import pandas as pd
    if len(metadata.rows) != 1:
        raise ValueError("escrow.snapshot_metadata_invalid")
    name, period, sheet, header, sha, size, source_id, method, unknown = metadata.rows[0]
    date.fromisoformat(period)
    if header < 0 or method != "cbr-escrow-xlsx-flake-1":
        raise ValueError("escrow.snapshot_profile_invalid")
    specs = {spec.code: spec for spec in _read_specs(specs_table)}
    resolved = [ResolvedEscrowColumn(label, index, specs[code]) for index, label, code in columns.rows]
    rows = [EscrowParsedRow(*row) for row in rows_table.rows]
    by_row = {header + row.source_row_index + 2: row for row in rows}
    by_column = {column.source_index + 1: column for column in resolved}
    if not rows or any(row.source_row_index < 0 or row.display_order != i + 1 for i, row in enumerate(rows)):
        raise ValueError("escrow.snapshot_rows_invalid")
    if len({row.entity_name for row in rows}) != len(rows):
        raise ValueError("escrow.duplicate_region")
    if any(row.row_kind not in {"region", "federal_district", "rf_total"} for row in rows):
        raise ValueError("escrow.snapshot_rows_invalid")
    records = []
    mapped_coordinates = set()
    for source_row, source_column, label, code, token, kind, status, value, row_kind, region, display in cells.rows:
        row = by_row.get(source_row)
        if row is None or (row.row_kind, row.entity_name, row.display_order) != (row_kind, region, display) or source_column < 3:
            raise ValueError("escrow.snapshot_cell_coordinates_invalid")
        if status not in {"numeric", "blank", "marker", "unparsed", "formula_unresolved"} or kind not in {"blank", "number", "text", "boolean", "datetime", "formula"}:
            raise ValueError("escrow.snapshot_cell_status_invalid")
        if (status == "numeric") != (value is not None):
            raise ValueError("escrow.snapshot_cell_value_invalid")
        if status == "numeric" and (token is None or decode_cell(token)[3] != value):
            raise ValueError("escrow.snapshot_cell_value_invalid")
        if code is None:
            if source_column in by_column:
                raise ValueError("escrow.snapshot_cell_indicator_invalid")
            continue
        column = by_column.get(source_column)
        if column is None or column.spec.code != code or column.source_name != label:
            raise ValueError("escrow.snapshot_cell_indicator_invalid")
        mapped_coordinates.add((source_row, source_column))
        if value is not None:
            records.append((row.entity_name, column.spec.canonical_name, value, period, row.row_kind, row.display_order,
                            row.federal_district_name, row.region_number, code, column.spec.sheet_code, column.spec.value_kind, name))
    if mapped_coordinates != {(row, column) for row in by_row for column in by_column}:
        raise ValueError("escrow.snapshot_cells_incomplete")
    # Parser records follow source-column order; the same order survives replay.
    return ParsedEscrowFile(name, period, sheet, header, resolved, rows, _build_rows_frame(rows),
                            pd.DataFrame(records, columns=LONG_COLUMNS, dtype=object), unmapped_headers=_string_tuple(unknown),
                            df_cells=_frame(cells), original_identity=ByteIdentity(sha, size), source_id=source_id, method_version=method)


def flake_snapshot(flake, *, dataset_id="cbr.escrow.flake", version_id=None):
    tables = flake_tables(flake)
    receipt = UsedInputReceipt("source_workbook", flake.original_identity,
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only", flake.source_id)
    return _build(dataset_id, version_id, FLAKE, tables,
                  coverage=SnapshotCoverage("unknown", "One publication-local XLSX table; publisher historical coverage is unspecified."), inputs=(receipt,))


def flake_from_snapshot(snapshot):
    components = {"metadata": METADATA, "columns": COLUMNS, "indicators": SPECS, "rows": PARSED_ROWS, "cells": CELLS}
    _check(snapshot, FLAKE, components)
    value = _restore_flake(*(snapshot.table(name) for name in components))
    flake_tables(value)
    _check_lineage(snapshot, (UsedInputReceipt("source_workbook", value.original_identity,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only", value.source_id),))
    return value


def dataset_tables(dataset):
    from .parser import decode_cell
    if not isinstance(dataset, EscrowDataset) or not dataset.releases or type(dataset.selection_complete) is not bool:
        raise ValueError("escrow.dataset_invalid")
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
    return (("selection", TypedTable(SELECTION, ((dataset.selection_complete,),))), ("releases", releases),
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
                          _read_specs(snapshot.table("indicators")), snapshot.manifest.coverage, selection.rows[0][0])
    dataset_tables(value)
    _check_lineage(snapshot, tuple(_release_input(release) for release in releases))
    return value


def view_tables(view):
    if not isinstance(view, EscrowPivotPack) or not view.indicator_specs or view.missing_display not in {"blank", "source_token"}:
        raise ValueError("escrow.view_invalid")
    if tuple(view.pivots) != tuple(spec.code for spec in view.indicator_specs):
        raise ValueError("escrow.view_indicator_mismatch")
    if not view.region_order or not view.date_order or tuple(sorted(set(view.date_order))) != view.date_order:
        raise ValueError("escrow.view_dimensions_mismatch")
    for period in view.date_order:
        date.fromisoformat(period)
    row_metadata = view.row_metadata or tuple((region, "unspecified", None) for region in view.region_order)
    if tuple(item[0] for item in row_metadata) != view.region_order:
        raise ValueError("escrow.view_rows_mismatch")
    values = []
    for code, frame in view.pivots.items():
        if tuple(frame.index) != view.region_order or tuple(frame.columns) != view.date_order:
            raise ValueError("escrow.view_dimensions_mismatch")
        for region in view.region_order:
            for period in view.date_order:
                value = frame.at[region, period]
                number, token = None, None
                if isinstance(value, str):
                    token = value
                elif value is not None:
                    import pandas as pd
                    if not pd.isna(value):
                        number = value if isinstance(value, Decimal) else Decimal(str(value))
                values.append((code, region, period, number, token))
    identity = view.source_dataset
    return (("metadata", TypedTable(VIEW_META, ((identity.sha256 if identity else None, identity.size if identity else None, view.missing_display),))),
            ("indicators", _specs(view.indicator_specs)), ("rows", TypedTable(VIEW_ROWS, row_metadata)),
            ("periods", TypedTable(VIEW_DATES, tuple((period,) for period in view.date_order))),
            ("values", TypedTable(VIEW_VALUES, tuple(values))))


def view_snapshot(view, *, dataset_id="cbr.escrow.prepared_view", version_id=None):
    return _build(dataset_id, version_id, VIEW, view_tables(view), coverage=view.coverage,
                  inputs=(UsedInputReceipt("integrated_dataset", view.source_dataset, "application/json", "reference_only"),) if view.source_dataset else ())


def view_from_snapshot(snapshot):
    import pandas as pd
    components = {"metadata": VIEW_META, "indicators": SPECS, "rows": VIEW_ROWS, "periods": VIEW_DATES, "values": VIEW_VALUES}
    _check(snapshot, VIEW, components)
    if len(snapshot.table("metadata").rows) != 1:
        raise ValueError("escrow.snapshot_metadata_invalid")
    sha, size, missing = snapshot.table("metadata").rows[0]
    if (sha is None) != (size is None):
        raise ValueError("escrow.snapshot_identity_invalid")
    specs = _read_specs(snapshot.table("indicators"))
    rows = snapshot.table("rows").rows
    regions = tuple(row[0] for row in rows)
    periods = tuple(row[0] for row in snapshot.table("periods").rows)
    pivots = {spec.code: pd.DataFrame(None, index=pd.Index(regions, name="Регион"), columns=pd.Index(periods, name="Дата"), dtype=object) for spec in specs}
    seen = set()
    for code, region, period, number, token in snapshot.table("values").rows:
        if code not in pivots or region not in regions or period not in periods or (number is not None and token is not None):
            raise ValueError("escrow.snapshot_view_cell_invalid")
        pivots[code].at[region, period] = number if number is not None else token
        seen.add((code, region, period))
    if len(seen) != len(specs) * len(regions) * len(periods):
        raise ValueError("escrow.snapshot_view_incomplete")
    value = EscrowPivotPack(pivots, specs, regions, periods, source_dataset=ByteIdentity(sha, size) if sha else None,
                            coverage=snapshot.manifest.coverage, missing_display=missing, row_metadata=rows)
    view_tables(value)
    _check_lineage(snapshot, (UsedInputReceipt("integrated_dataset", value.source_dataset, "application/json", "reference_only"),) if value.source_dataset else ())
    return value
