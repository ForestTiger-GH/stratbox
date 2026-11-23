"""Align the selected published federal-district slice for model preparation."""
from stratbox.domains.cbr.analytics.corporate_lending.sors.schema import FD_NAME_TO_CODE
from .common import canonicalize_observations, source_records


def parse_federal_district_okved2(source, as_of_date, policy, *, source_series="01_03_C",
                                 source_role="STRICT_FD_OKVED2", portfolio_scope="CORPORATE_TOTAL"):
    out = source_records(source, as_of_date, source_series)
    out["classifier_id"] = "okved2_section"
    out["activity_code"] = out["activity_raw"].map(lambda name: "PUBLISHED_OTHER" if name.lower().startswith("проч") else name.split(".", 1)[0].strip())
    out["activity_name"] = out["activity_raw"]
    out["geography_node_id"] = out["geography_raw"].map(FD_NAME_TO_CODE)
    if out["geography_node_id"].isna().any():
        raise ValueError("sors.federal_district_unmapped")
    out["geography_name"] = out["geography_raw"]
    out["geography_kind"] = "federal_district_total"
    out["currency"] = "total"
    out["portfolio_scope"] = portfolio_scope
    if len(out) != 256:
        raise ValueError(f"Expected 256 {source_series} observations, got {len(out)}")
    return canonicalize_observations(out, policy, source_role=source_role)
