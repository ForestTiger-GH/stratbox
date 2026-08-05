from __future__ import annotations

import pandas as pd

_PARENT_MEMBERS = {
    'Архангельская область': (
        'в том числе Ненецкий автономный округ',
        'Архангельская область без данных по Ненецкому автономному округу',
    ),
    'Тюменская область': (
        'в том числе Ханты-Мансийский автономный округ - Югра',
        'в том числе Ямало-Ненецкий автономный округ',
        'Тюменская область без данных по Ханты-Мансийскому автономному округу - Югре и Ямало-Ненецкому автономному округу',
    ),
}


def build_geography_frames(region_specs) -> tuple[pd.DataFrame, pd.DataFrame]:
    parent_names = set(_PARENT_MEMBERS)
    atomic_rows = [
        {
            'region_code': r.code,
            'region_name': r.canonical_name,
            'federal_district_name': r.federal_district_name,
            'region_kind': r.region_kind,
            'region_order': r.order,
        }
        for r in region_specs
        if r.region_kind not in {'country_total', 'federal_district_total'}
        and r.canonical_name not in parent_names
    ]
    atomic = pd.DataFrame(atomic_rows).sort_values('region_order').reset_index(drop=True)
    if len(atomic) != 85:
        raise ValueError(f'Expected 85 atomic SORS territories, got {len(atomic)}')
    by_name = {row.region_name: row.region_code for row in atomic.itertuples(index=False)}
    all_codes = tuple(atomic['region_code'].astype(str))
    nodes: list[dict[str, object]] = []
    for r in region_specs:
        if r.region_kind == 'country_total':
            members = all_codes
        elif r.region_kind == 'federal_district_total':
            members = tuple(atomic.loc[atomic['federal_district_name'] == r.federal_district_name, 'region_code'].astype(str))
        elif r.canonical_name in _PARENT_MEMBERS:
            members = tuple(by_name[name] for name in _PARENT_MEMBERS[r.canonical_name])
        else:
            members = (by_name[r.canonical_name],)
        nodes.append({
            'geography_node_id': r.code,
            'geography_name': r.canonical_name,
            'geography_kind': r.region_kind,
            'federal_district_name': r.federal_district_name,
            'geography_order': r.order,
            'atomic_region_codes': members,
        })
    return pd.DataFrame(nodes), atomic
