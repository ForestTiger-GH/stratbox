"""Model projections of reusable national and regional SME source observations."""
from stratbox.shared.evidence import SourcePayload
import pandas as pd
from stratbox.domains.cbr.calculations.sors.publication import RoundingPolicy
from stratbox.domains.cbr.calculations.sors.schema import normalize_class_code, normalize_key
from stratbox.domains.cbr.calculations.sors.inputs.common import canonicalize_observations, source_records
from stratbox.domains.cbr.calculations.sors.inputs.national_common import parse_national_book


def parse_sme_national_totals(source, as_of_date, policy):
    out = source_records(source, as_of_date, "01_11")
    out["classifier_id"] = "total_only"
    out["activity_code"] = "total"
    out["activity_name"] = "ВСЕГО"
    out["activity_raw"] = out["row_label"]
    out["geography_node_id"] = "RF"
    out["geography_name"] = "РОССИЙСКАЯ ФЕДЕРАЦИЯ"
    out["geography_raw"] = "РОССИЙСКАЯ ФЕДЕРАЦИЯ"
    out["geography_kind"] = "country_total"
    if len(out) != 12 or set(out["portfolio_scope"]) != {"SME", "SME_IE"}:
        raise ValueError("sors.sme_national_scope_invalid")
    return canonicalize_observations(out, policy, source_role="STRICT_NATIONAL_SME_TOTALS")


def parse_sme_national_okved2(
    path: SourcePayload,
    as_of_date: str,
    policy: RoundingPolicy,
    *,
    portfolio_scope: str,
    source_series: str,
) -> pd.DataFrame:
    if portfolio_scope not in {'SME', 'SME_IE'}:
        raise ValueError(f'Unsupported SME national scope {portfolio_scope!r}')
    out = parse_national_book(
        path,
        as_of_date,
        classifier_id='okved2',
        source_series=source_series,
        source_role=f'STRICT_NATIONAL_OKVED2_{portfolio_scope}',
        policy=policy,
    )
    out['activity_code'] = out['activity_raw'].map(normalize_class_code)
    out = out[
        out['activity_code'].eq('PUBLISHED_OTHER')
        | out['activity_code'].str.fullmatch(r'\d{2}')
    ].copy()
    out['activity_name'] = out['activity_raw']
    out['portfolio_scope'] = portfolio_scope
    if len(out) != 486:
        raise ValueError(f'Expected 486 {source_series} observations, got {len(out)}')
    return out.reset_index(drop=True)



def parse_sme_regional_totals(source, as_of_date, policy, geography_nodes, *, portfolio_scope, source_series):
    if portfolio_scope not in {"SME", "SME_IE"}:
        raise ValueError("sors.sme_scope_invalid")
    from stratbox.domains.cbr.calculations.sors.inputs.regional_totals import align_regional_records
    out = align_regional_records(source_records(source, as_of_date, source_series), geography_nodes)
    out["portfolio_scope"] = portfolio_scope
    if len(out) != 576:
        raise ValueError(f"Expected 576 {source_series} observations, got {len(out)}")
    return canonicalize_observations(out, policy, source_role=f"STRICT_REGIONAL_TOTALS_{portfolio_scope}")
