"""Prepare a selected national source slice for the SORS model."""
from .common import canonicalize_observations, source_records


def parse_national_book(source, as_of_date, *, classifier_id, source_series, source_role, policy):
    out = source_records(source, as_of_date, source_series)
    out["classifier_id"] = classifier_id
    out["geography_node_id"] = "RF"
    out["geography_name"] = "РОССИЙСКАЯ ФЕДЕРАЦИЯ"
    out["geography_raw"] = "РОССИЙСКАЯ ФЕДЕРАЦИЯ"
    out["geography_kind"] = "country_total"
    return canonicalize_observations(out, policy, source_role=source_role)
