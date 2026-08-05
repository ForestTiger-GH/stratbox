from __future__ import annotations

from pathlib import Path

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.schema import normalize_class_code
from stratbox.macrobanks.cbr_sors_restoration.sources.national_common import (
    parse_national_book,
)


def parse_national_okved2(
    path: str | Path,
    as_of_date: str,
    policy: RoundingPolicy,
) -> pd.DataFrame:
    out = parse_national_book(
        path,
        as_of_date,
        classifier_id='okved2',
        source_series='01_02_C',
        source_role='STRICT_NATIONAL_OKVED2',
        policy=policy,
    )
    out['activity_code'] = out['activity_raw'].map(normalize_class_code)
    out = out[
        out['activity_code'].eq('PUBLISHED_OTHER')
        | out['activity_code'].str.fullmatch(r'\d{2}')
    ].copy()
    out['activity_name'] = out['activity_raw']
    return out.reset_index(drop=True)
