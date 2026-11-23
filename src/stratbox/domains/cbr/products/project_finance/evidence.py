"""Prepared-view evidence includes presentation and exact input versions."""
from dataclasses import asdict, replace
from stratbox.core.operations.tables import record_tables, use_tables

def view_metadata(value):
    return {"indicators": [asdict(spec) for spec in value.indicator_specs],
            "regions": value.region_order, "dates": value.date_order,
            "source_dataset": asdict(value.source_dataset) if value.source_dataset else None,
            "coverage": asdict(value.coverage), "missing_display": value.missing_display,
            "row_metadata": value.row_metadata,
            "product_profile": [value.product_profile_id, value.product_profile_version],
            "input_versions": [asdict(item) for item in value.input_versions]}

def use_view(value, invocation):
    from .snapshots import view_tables
    tables = tuple(value.pivots.items())
    frames = use_tables(invocation, tables, receipt=value.evidence, role="escrow_views", metadata=view_metadata(value))
    result = replace(value, pivots=dict(zip((name for name, _ in tables), frames, strict=True)))
    view_tables(result)
    return result

def seal_view(value, invocation):
    from .snapshots import view_tables
    view_tables(value)
    return replace(value, evidence=record_tables(invocation, tuple(value.pivots.items()), metadata=view_metadata(value)))
