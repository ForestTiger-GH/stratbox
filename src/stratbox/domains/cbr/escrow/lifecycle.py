"""Independent flake replay, semantic integration and prepared-view operations."""
from __future__ import annotations

from dataclasses import asdict, replace

from stratbox.core.execution import OperationFailure
from stratbox.core.execution.runner import run
from stratbox.core.operations.tables import record_tables, use_tables
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from .contracts import EscrowDataset, EscrowPivotPack, EscrowRelease
from . import snapshots


def flake_evidence(value):
    tables = (("rows", value.df_rows), ("observations", value.df_long), ("cells", value.df_cells))
    metadata = {"source_name": value.source_name, "period": value.file_date, "sheet": value.sheet_name,
                "header_row": value.header_row_index, "source_id": value.source_id,
                "original": asdict(value.original_identity) if value.original_identity else None,
                "method": value.method_version, "unmapped_headers": value.unmapped_headers,
                "columns": [asdict(column) for column in value.resolved_columns], "rows": [asdict(row) for row in value.rows]}
    return tables, metadata


def seal_flake(value, invocation):
    snapshots.flake_tables(value)
    tables, metadata = flake_evidence(value)
    return replace(value, evidence=record_tables(invocation, tables, metadata=metadata))


def use_flake(value, invocation):
    tables, metadata = flake_evidence(value)
    frames = use_tables(invocation, tables, receipt=value.evidence, metadata=metadata, role="escrow_flake")
    copied = replace(value, df_rows=frames[0], df_long=frames[1], df_cells=frames[2])
    snapshots.flake_tables(copied)
    return copied


def dataset_evidence(value):
    return (("observations", value.observations), ("rows", value.rows)), {
        "releases": [asdict(release) for release in value.releases],
        "indicators": [asdict(spec) for spec in value.indicator_specs],
        "coverage": asdict(value.coverage), "selection_complete": value.selection_complete,
    }


def seal_dataset(value, invocation):
    snapshots.dataset_tables(value)
    tables, metadata = dataset_evidence(value)
    return replace(value, evidence=record_tables(invocation, tables, metadata=metadata))


def use_dataset(value, invocation):
    tables, metadata = dataset_evidence(value)
    observations, rows = use_tables(invocation, tables, receipt=value.evidence, metadata=metadata, role="escrow_dataset")
    copied = replace(value, observations=observations, rows=rows)
    snapshots.dataset_tables(copied)
    return copied


def integrate_values(flakes, coverage, *, selection_complete=True):
    import pandas as pd
    if not flakes:
        raise ValueError("escrow.source_selection_empty")
    ordered = sorted(flakes, key=lambda flake: flake.file_date)
    periods = tuple(flake.file_date for flake in ordered)
    if len(periods) != len(set(periods)):
        raise ValueError("escrow.duplicate_release")
    specs, observations, dimensions, releases = {}, [], [], []
    for flake in ordered:
        snapshots.flake_tables(flake)
        for column in flake.resolved_columns:
            previous = specs.get(column.spec.code)
            if previous is not None and previous != column.spec:
                raise ValueError("escrow.indicator_edition_conflict")
            specs[column.spec.code] = column.spec
        releases.append(EscrowRelease(flake.file_date, flake.source_name, flake.source_id, flake.original_identity,
                                      flake.sheet_name, flake.method_version, flake.unmapped_headers))
        for row in flake.df_rows.itertuples(index=False, name=None):
            dimensions.append((flake.file_date, *row))
        for source_row, source_column, header, code, token, kind, status, value, row_kind, region, display in flake.df_cells.itertuples(index=False, name=None):
            if code is not None:
                observations.append((flake.file_date, region, row_kind, code, value, token, status,
                                     flake.source_name, flake.sheet_name, source_row, source_column))
    result = EscrowDataset(
        pd.DataFrame(observations, columns=[c.name for c in snapshots.OBSERVATIONS.columns], dtype=object),
        pd.DataFrame(dimensions, columns=[c.name for c in snapshots.ROWS.columns], dtype=object),
        tuple(releases), tuple(sorted(specs.values(), key=lambda spec: (spec.order, spec.code))), coverage, selection_complete,
    )
    snapshots.dataset_tables(result)
    return result


def integrate_flakes(request, *, context=None):
    from .definitions import INTEGRATE
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        invocation.stage("integrate")
        try:
            flakes = tuple(use_flake(flake, invocation) for flake in req.flakes)
            return seal_dataset(integrate_values(flakes, req.coverage), invocation)
        except (TypeError, ValueError, KeyError) as error:
            raise OperationFailure(_error_code(error, "escrow.integration_invalid")) from None
    return run(INTEGRATE, request, work, context=context)


def prepare_dataset_view(dataset, options, invocation):
    import pandas as pd
    dataset = use_dataset(dataset, invocation)
    if options.require_complete_history and not dataset.selection_complete:
        raise OperationFailure("source.history_incomplete")
    if options.regions_mode not in {"latest", "custom"} or options.missing_display not in {"source_token", "blank"}:
        raise OperationFailure("request.escrow_view_invalid")
    dates = tuple(release.period for release in dataset.releases)
    latest = dataset.rows.loc[dataset.rows["period"].eq(dates[-1])].sort_values("display_order")
    if options.regions_mode == "latest":
        regions = tuple(latest["Регион"])
    else:
        regions = tuple(options.custom_regions)
        if not regions or len(set(regions)) != len(regions):
            raise OperationFailure("request.region_order_invalid")
        if not set(regions).issubset(set(dataset.rows["Регион"])):
            raise OperationFailure("request.region_unknown")
    # Last known row metadata is used only for display. Every historical edition
    # remains in dataset.rows and in the logical dataset identity.
    row_lookup = {}
    for period, order, kind, region, district, number in dataset.rows.itertuples(index=False, name=None):
        row_lookup[region] = (region, kind, district)
    invocation.budget.check("cells", len(regions) * len(dates) * len(dataset.indicator_specs))
    pivots = {spec.code: pd.DataFrame(None, index=pd.Index(regions, name="Регион"),
                                      columns=pd.Index(dates, name="Дата"), dtype=object) for spec in dataset.indicator_specs}
    for period, region, kind, code, value, token, status, name, sheet, row, column in dataset.observations.itertuples(index=False, name=None):
        if region in regions:
            pivots[code].at[region, period] = value if status == "numeric" else token if options.missing_display == "source_token" and status != "blank" else None
    return EscrowPivotPack(pivots, dataset.indicator_specs, regions, dates,
                            source_dataset=snapshots.dataset_snapshot(dataset).identity, coverage=dataset.coverage,
                            missing_display=options.missing_display, row_metadata=tuple(row_lookup[region] for region in regions))


def _error_code(error, fallback):
    code = str(error)
    return code if code.startswith("escrow.") and " " not in code else fallback


def _encode(definition, request, get_value, encode, consume, *, context):
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        invocation.stage("encode_snapshot")
        try:
            value = consume(get_value(req), invocation)
            snapshot = encode(value, dataset_id=req.dataset_id, version_id=req.version_id)
        except (TypeError, ValueError, KeyError) as error:
            raise OperationFailure(_error_code(error, "escrow.snapshot_invalid")) from None
        invocation.record(snapshot.identity, parameters={"dataset_id": snapshot.manifest.dataset_id, "version_id": snapshot.manifest.version_id})
        return snapshot
    return run(definition, request, work, context=context)


def _decode(definition, request, decode, seal, *, context):
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        invocation.stage("decode_snapshot")
        invocation.use(UsedInputReceipt("snapshot", req.snapshot.identity, "application/json", "inline"))
        invocation.budget.check("cells", sum(len(table.rows) * len(table.schema.columns) for _, table in req.snapshot.tables))
        try:
            value = decode(req.snapshot)
            return seal(value, invocation)
        except (TypeError, ValueError, KeyError) as error:
            raise OperationFailure(_error_code(error, "escrow.snapshot_invalid")) from None
    return run(definition, request, work, context=context)


def build_flake_snapshot(request, *, context=None):
    from .definitions import FLAKE_SNAPSHOT
    return _encode(FLAKE_SNAPSHOT, request, lambda req: req.flake, snapshots.flake_snapshot, use_flake, context=context)


def read_flake_snapshot(request, *, context=None):
    from .definitions import READ_FLAKE_SNAPSHOT
    return _decode(READ_FLAKE_SNAPSHOT, request, snapshots.flake_from_snapshot, seal_flake, context=context)


def build_dataset_snapshot(request, *, context=None):
    from .definitions import DATASET_SNAPSHOT
    return _encode(DATASET_SNAPSHOT, request, lambda req: req.dataset, snapshots.dataset_snapshot, use_dataset, context=context)


def read_dataset_snapshot(request, *, context=None):
    from .definitions import READ_DATASET_SNAPSHOT
    return _decode(READ_DATASET_SNAPSHOT, request, snapshots.dataset_from_snapshot, seal_dataset, context=context)


def _use_view(value, invocation):
    from .operations import _pivot_metadata
    tables = tuple(value.pivots.items())
    frames = use_tables(invocation, tables, receipt=value.evidence, role="escrow_views", metadata=_pivot_metadata(value))
    return replace(value, pivots=dict(zip((name for name, _ in tables), frames, strict=True)))


def _seal_view(value, invocation):
    from .operations import _pivot_metadata
    return replace(value, evidence=record_tables(invocation, tuple(value.pivots.items()), metadata=_pivot_metadata(value)))


def build_view_snapshot(request, *, context=None):
    from .definitions import VIEW_SNAPSHOT
    return _encode(VIEW_SNAPSHOT, request, lambda req: req.view, snapshots.view_snapshot, _use_view, context=context)


def read_view_snapshot(request, *, context=None):
    from .definitions import READ_VIEW_SNAPSHOT
    return _decode(READ_VIEW_SNAPSHOT, request, snapshots.view_from_snapshot, _seal_view, context=context)
