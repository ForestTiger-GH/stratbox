"""Standalone prepared-view snapshots retain style and exact input versions."""
from __future__ import annotations
from datetime import date
from dataclasses import asdict
from decimal import Decimal
import json
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import TypedTable
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.domains.cbr.tables.project_finance.codec import (_schema, T, I, D, _json, _check, _check_lineage, _build)
from .contracts import EscrowPivotPack
from .profiles import EscrowProductIndicator, EscrowProductProfile

VIEW = DataContract("cbr.escrow.view.snapshot", 2, DataRole.PRODUCTS)
PRESENTATION = _schema("view.presentation", (("indicator_code", T, False), ("specification", T, False)), role=DataRole.PRODUCTS, key=("indicator_code",))
INPUTS = _schema("view.input_versions", (("sha256", T, False), ("size", I, False), ("source_id", T, True)), role=DataRole.PRODUCTS)

VIEW_META = _schema("view.metadata", (("source_sha256", T, True), ("source_size", I, True), ("missing_display", T, False), ("profile_id", T, False), ("profile_version", I, False)), role=DataRole.PRODUCTS)
VIEW_ROWS = _schema("view.rows", (("region", T, False), ("row_kind", T, False), ("federal_district_name", T, True)), role=DataRole.PRODUCTS, key=("region",))
VIEW_DATES = _schema("view.dates", (("period", T, False),), role=DataRole.PRODUCTS, key=("period",))
VIEW_VALUES = _schema("view.values", (("indicator_code", T, False), ("region", T, False), ("period", T, False),
                                     ("number", D, True), ("text", T, True)), role=DataRole.PRODUCTS, key=("indicator_code", "region", "period"))


def _specs(values):
    return TypedTable(PRESENTATION, tuple((spec.code, _json(asdict(spec))) for spec in values))

def _read_specs(table):
    values = tuple(EscrowProductIndicator(**json.loads(payload)) for code, payload in table.rows)
    if tuple(spec.code for spec in values) != tuple(code for code, payload in table.rows):
        raise ValueError("escrow.snapshot_indicators_invalid")
    return values

def _inputs(value):
    for item in value.input_versions:
        if (item.role != "source_workbook" or item.media_type != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                or item.availability != "reference_only" or item.container or item.member or item.version):
            raise ValueError("escrow.view_input_versions_invalid")
    return TypedTable(INPUTS, tuple((item.identity.sha256, item.identity.size, item.source_id) for item in value.input_versions))

def _lineage(value):
    return (UsedInputReceipt("integrated_dataset", value.source_dataset, "application/json", "reference_only"),) + value.input_versions if value.source_dataset else value.input_versions

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
    EscrowProductProfile(view.product_profile_id, view.product_profile_version, view.indicator_specs)
    identity = view.source_dataset
    return (("metadata", TypedTable(VIEW_META, ((identity.sha256 if identity else None, identity.size if identity else None, view.missing_display, view.product_profile_id, view.product_profile_version),))),
            ("indicators", _specs(view.indicator_specs)), ("rows", TypedTable(VIEW_ROWS, row_metadata)),
            ("periods", TypedTable(VIEW_DATES, tuple((period,) for period in view.date_order))),
            ("values", TypedTable(VIEW_VALUES, tuple(values))), ("input_versions", _inputs(view)))


def view_snapshot(view, *, dataset_id="cbr.escrow.prepared_view", version_id=None):
    return _build(dataset_id, version_id, VIEW, view_tables(view), coverage=view.coverage,
                  inputs=_lineage(view))


def view_from_snapshot(snapshot):
    import pandas as pd
    components = {"metadata": VIEW_META, "indicators": PRESENTATION, "rows": VIEW_ROWS, "periods": VIEW_DATES, "values": VIEW_VALUES, "input_versions": INPUTS}
    _check(snapshot, VIEW, components)
    if len(snapshot.table("metadata").rows) != 1:
        raise ValueError("escrow.snapshot_metadata_invalid")
    sha, size, missing, profile_id, profile_version = snapshot.table("metadata").rows[0]
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
                            coverage=snapshot.manifest.coverage, missing_display=missing, row_metadata=rows, product_profile_id=profile_id, product_profile_version=profile_version,
                            input_versions=tuple(UsedInputReceipt("source_workbook", ByteIdentity(sha, size),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only", source_id)
                                for sha, size, source_id in snapshot.table("input_versions").rows))
    view_tables(value)
    _check_lineage(snapshot, _lineage(value))
    return value
