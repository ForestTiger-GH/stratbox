from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsSourceBundle


def validate_source_bundle(bundle: SorsSourceBundle) -> None:
    dates = set(bundle.canonical_grid['as_of_date'].dropna().astype(str))
    if len(dates) != 1:
        raise ValueError(f'SORS sources must contain one common date, got {sorted(dates)}')
    expected_rows = {'01_05_A': 14976, '01_02_A': 156, '01_02_C': 486, '01_03_C': 256}
    actual = bundle.source_manifest.set_index('source_series')['rows'].astype(int).to_dict()
    for series, expected in expected_rows.items():
        if actual.get(series) != expected:
            raise ValueError(f'{series} completeness failure: expected {expected}, got {actual.get(series)}')
    if len(bundle.atomic_regions) != 85:
        raise ValueError('Atomic geography must contain 85 territories')
    if len(bundle.geography_nodes) != 96:
        raise ValueError('Regional publication geography must contain 96 nodes')
    if len(bundle.okved2_classes) != 88:
        raise ValueError('OKVED2 class registry must contain 88 classes')
    for frame, keys, label in (
        (bundle.regional_traditional_grid, ['as_of_date', 'geography_node_id', 'activity_code', 'measure', 'currency'], '01_05_A'),
        (bundle.national_traditional_grid, ['as_of_date', 'activity_code', 'measure', 'currency'], '01_02_A'),
        (bundle.national_okved2_grid, ['as_of_date', 'activity_code', 'measure', 'currency'], '01_02_C'),
        (bundle.fd_okved2_grid, ['as_of_date', 'geography_node_id', 'activity_code', 'measure'], '01_03_C'),
    ):
        duplicates = int(frame.duplicated(keys, keep=False).sum())
        if duplicates:
            raise ValueError(f'{label} contains {duplicates} duplicate observations')
    expected_metrics = {
        ('debt', 'rub'), ('overdue', 'rub'), ('debt', 'fx'), ('overdue', 'fx'),
        ('debt', 'total'), ('overdue', 'total'),
    }
    for frame, label in (
        (bundle.regional_traditional_grid, '01_05_A'),
        (bundle.national_traditional_grid, '01_02_A'),
        (bundle.national_okved2_grid, '01_02_C'),
    ):
        got = set(zip(frame['measure'].astype(str), frame['currency'].astype(str)))
        if got != expected_metrics:
            raise ValueError(f'{label} metric sheets changed: {sorted(got)}')
