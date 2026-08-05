from __future__ import annotations

from pathlib import Path

import pandas as pd

from stratbox.macrobanks.cbr_industries.schema import (
    CBR_0105A_DEBT_CORP_INDUSTRY_SPECS,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.schema import normalize_key
from stratbox.macrobanks.cbr_sors_restoration.sources.national_common import (
    parse_national_book,
)


def _label_is_compatible(raw: str, canonical: str) -> bool:
    left = normalize_key(raw.replace('из них', '').replace('в том числе', ''))
    right = normalize_key(canonical)
    if left == right:
        return True
    left_words = {word for word in left.split() if len(word) >= 5}
    right_words = {word for word in right.split() if len(word) >= 5}
    if not right_words:
        return bool(left)
    return len(left_words & right_words) >= max(1, min(2, len(right_words)))


def parse_national_traditional(
    path: str | Path,
    as_of_date: str,
    policy: RoundingPolicy,
) -> pd.DataFrame:
    out = parse_national_book(
        path,
        as_of_date,
        classifier_id='cbr_traditional',
        source_series='01_02_A',
        source_role='STRICT_NATIONAL_TOTAL_AND_BRIDGE_LEGACY',
        policy=policy,
    )
    specs = list(CBR_0105A_DEBT_CORP_INDUSTRY_SPECS)
    chunks: list[pd.DataFrame] = []
    for sheet, group in out.groupby('source_sheet', sort=False):
        if len(group) != len(specs):
            raise ValueError(
                f'National traditional sheet {sheet!r} has {len(group)} rows, '
                f'expected {len(specs)}'
            )
        part = group.sort_values('source_row').copy().reset_index(drop=True)
        incompatible: list[str] = []
        for row, spec in zip(part.itertuples(index=False), specs, strict=True):
            if not _label_is_compatible(str(row.activity_raw), spec.canonical_name_ru):
                incompatible.append(
                    f'row {row.source_row}: {row.activity_raw!r} != '
                    f'{spec.canonical_name_ru!r}'
                )
        if incompatible:
            raise ValueError(
                'National traditional activity layout changed: '
                + '; '.join(incompatible[:5])
            )
        part['activity_code'] = [spec.code for spec in specs]
        part['activity_name'] = [spec.canonical_name_ru for spec in specs]
        chunks.append(part)
    return pd.concat(chunks, ignore_index=True)
