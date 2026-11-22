from __future__ import annotations

from math import isfinite

from stratbox.shared.evidence import SourcePayload
from stratbox.shared.data.tables import table_identity

import pandas as pd

from stratbox.domains.cbr.corporate_lending.industries.debt_0105a.parser import parse_cbr_0105a_debt_corp_excel_bytes
from stratbox.domains.cbr.corporate_lending.industries.debt_0105a.contracts import ParsedCbr0105ADebtCorpFile
from stratbox.domains.cbr.corporate_lending.industries.debt_0105a.schema import CBR_0105A_DEBT_CORP_INDUSTRY_SPECS
from stratbox.domains.cbr.corporate_lending.sors_restoration.publication import RoundingPolicy
from stratbox.domains.cbr.corporate_lending.sors_restoration.registries.geography import (
    build_geography_registry,
)
from stratbox.domains.cbr.corporate_lending.sors_restoration.sources.common import (
    canonicalize_observations,

)


def parse_regional_traditional(
    path: SourcePayload,
    as_of_date: str,
    policy: RoundingPolicy,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    actual_name = path.source_id or "source.xlsx"
    logical_name = f'01_05_A_Debt_corp_{as_of_date.replace("-", "")}.xlsx'
    parsed = parse_cbr_0105a_debt_corp_excel_bytes(
        path.data,
        source_name=logical_name,
        source_id=actual_name,
        source_sha256=path.identity.sha256,
    )
    return _project_regional_traditional(parsed, as_of_date, policy, actual_name)


def regional_traditional_from_flake(
    parsed: ParsedCbr0105ADebtCorpFile,
    as_of_date: str,
    policy: RoundingPolicy,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Admit a complete retained 0105a flake as a SORS input without XLSX bytes.

    The source receipt and SHA-256 remain the original publication evidence.
    ``policy`` explicitly supplies the publication interval step; the adapter
    never infers it from float spelling or from a retained file's location.
    """
    if not isinstance(parsed, ParsedCbr0105ADebtCorpFile) or parsed.evidence is None:
        raise ValueError("sors.regional_flake_unqualified")
    if table_identity((("stream", parsed.df_stream),)) != parsed.evidence.output:
        raise ValueError("sors.regional_flake_identity_mismatch")
    if any(issue.severity == "error" for issue in parsed.validation_issues):
        raise ValueError("sors.regional_flake_invalid")
    if (parsed.source_validation_scope != "full" or
            parsed.geography_reference_version != "cbr-industry-geography-2026-06-01"):
        raise ValueError("sors.regional_flake_scope_unsupported")
    expected_industries = {spec.code for spec in CBR_0105A_DEBT_CORP_INDUSTRY_SPECS}
    if set(parsed.df_stream["industry_code"].astype(str)) != expected_industries:
        raise ValueError("sors.regional_flake_incomplete")
    dimensions = ["measure", "currency_scope", "region_code", "industry_code"]
    if (len(parsed.sheets) != 6 or parsed.rows_stream != len(parsed.df_stream)
            or len(parsed.df_stream) != 6 * len(parsed.regions) * len(expected_industries)
            or parsed.df_stream.duplicated(dimensions).any()):
        raise ValueError("sors.regional_flake_incomplete")
    if (parsed.source_sha256 is None or
            set(parsed.df_stream["source_sha256"].dropna().astype(str)) != {parsed.source_sha256}):
        raise ValueError("sors.regional_flake_source_mismatch")
    return _project_regional_traditional(parsed, as_of_date, policy, parsed.source_id)


def _project_regional_traditional(parsed, as_of_date, policy, actual_name):
    if not isinstance(policy, RoundingPolicy) or not isfinite(policy.step) or not isfinite(policy.tolerance):
        raise ValueError("sors.publication_policy_invalid")
    if parsed.report_date != as_of_date:
        raise ValueError(
            f'Regional workbook date {parsed.report_date} differs from {as_of_date}'
        )
    if set(parsed.df_stream["report_date"].dropna().astype(str)) != {as_of_date}:
        raise ValueError("sors.regional_flake_date_mismatch")
    logical_name = f'01_05_A_Debt_corp_{as_of_date.replace("-", "")}.xlsx'
    frame = parsed.df_stream.copy()
    frame['source_series'] = '01_05_A'
    frame['source_file_actual'] = actual_name
    frame['source_file_logical'] = logical_name
    frame['source_sheet'] = frame['source_sheet_name'].astype(str)
    frame['as_of_date'] = as_of_date
    frame['activity_code'] = frame['industry_code'].astype(str)
    frame['activity_name'] = frame['industry_name_ru'].astype(str)
    frame['activity_raw'] = frame['industry_source_name'].astype(str)
    frame['classifier_id'] = 'cbr_traditional'
    frame['geography_node_id'] = frame['region_code'].astype(str)
    frame['geography_name'] = frame['region_name'].astype(str)
    frame['geography_raw'] = frame['region_source_name'].astype(str)
    frame['geography_kind'] = frame['region_kind'].astype(str)
    frame['currency'] = frame['currency_scope'].map(
        {
            'rubles': 'rub',
            'foreign_currency_and_precious_metals': 'fx',
            'total': 'total',
        }
    )
    frame['measure'] = frame['measure'].map(
        {'overdue_debt': 'overdue', 'debt': 'debt'}
    )
    geography, atomic = build_geography_registry(parsed.regions)
    out = canonicalize_observations(
        frame,
        policy,
        source_role='STRICT_REGIONAL_TOTALS_AND_CROSSWALK_LEGACY',
    )
    return out, geography, atomic
