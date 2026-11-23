"""Geography alignment of independently extracted regional source histories."""
from stratbox.domains.cbr.analytics.corporate_lending.sors.schema import normalize_key
from .common import canonicalize_observations, source_records


def align_regional_records(frame, geography_nodes):
    by_name = {normalize_key(row.geography_name): row for row in geography_nodes.itertuples(index=False)}
    nodes = [by_name.get(normalize_key(name)) for name in frame["geography_raw"]]
    if any(node is None for node in nodes):
        raise ValueError("sors.source_geography_unmapped")
    out = frame.copy()
    out["classifier_id"] = "total_only"
    out["activity_code"] = "total"
    out["activity_name"] = "ВСЕГО"
    out["activity_raw"] = "ВСЕГО"
    out["geography_node_id"] = [str(node.geography_node_id) for node in nodes]
    out["geography_name"] = [str(node.geography_name) for node in nodes]
    out["geography_kind"] = [str(node.geography_kind) for node in nodes]
    return out


def parse_regional_totals_history(source, as_of_date, policy, geography_nodes):
    out = align_regional_records(source_records(source, as_of_date, "01_05_D"), geography_nodes)
    if len(out) != 576:
        raise ValueError(f"Expected 576 01_05_D observations, got {len(out)}")
    return canonicalize_observations(out, policy, source_role="OPTIONAL_VALIDATION_AND_HISTORY")
