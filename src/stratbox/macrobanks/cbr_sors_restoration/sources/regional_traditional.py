from __future__ import annotations

from pathlib import Path

import pandas as pd

from stratbox.macrobanks.cbr_industries import parse_cbr_0105a_debt_corp_excel_bytes
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.registries.geography import (
    build_geography_registry,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.common import (
    canonicalize_observations,
    sha256_file,
)


def parse_regional_traditional(
    path: str | Path,
    as_of_date: str,
    policy: RoundingPolicy,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    actual = Path(path)
    logical_name = f'01_05_A_Debt_corp_{as_of_date.replace("-", "")}.xlsx'
    parsed = parse_cbr_0105a_debt_corp_excel_bytes(
        actual.read_bytes(),
        source_name=logical_name,
        source_id=f'local:{actual.name}',
        source_sha256=sha256_file(actual),
    )
    if parsed.report_date != as_of_date:
        raise ValueError(
            f'Regional workbook date {parsed.report_date} differs from {as_of_date}'
        )
    frame = parsed.df_stream.copy()
    frame['source_series'] = '01_05_A'
    frame['source_file_actual'] = actual.name
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
        source_role='STRICT_REGIONAL_TOTALS_AND_BRIDGE_LEGACY',
    )
    return out, geography, atomic
