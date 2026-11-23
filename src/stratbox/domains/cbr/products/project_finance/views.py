"""Build prepared products solely from an admitted integrated dataset."""
from stratbox.core.execution import OperationFailure
from stratbox.domains.cbr.integration.project_finance.evidence import use_dataset
from stratbox.domains.cbr.integration.project_finance.snapshots import dataset_snapshot, _release_input
from .contracts import EscrowPivotPack
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse

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
    available = {item.code for item in dataset.indicator_specs}
    specs = tuple(item for item in sorted(options.profile.indicators, key=lambda item: (item.order, item.code)) if item.code in available)
    if not specs:
        raise OperationFailure("request.empty_views")
    invocation.budget.check("cells", len(regions) * len(dates) * len(specs))
    pivots = {spec.code: pd.DataFrame(None, index=pd.Index(regions, name="Регион"),
                                      columns=pd.Index(dates, name="Дата"), dtype=object) for spec in specs}
    for period, region, kind, code, value, token, status, name, sheet, row, column in dataset.observations.itertuples(index=False, name=None):
        if region in regions and code in pivots:
            pivots[code].at[region, period] = value if status == "numeric" else token if options.missing_display == "source_token" and status != "blank" else None
    return EscrowPivotPack(pivots, specs, regions, dates,
                            source_dataset=dataset_snapshot(dataset).identity, coverage=dataset.coverage,
                            missing_display=options.missing_display, row_metadata=tuple(row_lookup[region] for region in regions),
                            product_profile_id=options.profile.profile_id, product_profile_version=options.profile.version,
                            input_versions=tuple(_release_input(release) for release in dataset.releases),
                            source_uses=tuple(SourceUse(SourceCoordinate("cbr.project_finance.escrow", "cbr.project_finance",
                                "project_finance_statistics", release.period, material_identity=release.original_identity),
                                "releases", "domain_validated") for release in dataset.releases))
