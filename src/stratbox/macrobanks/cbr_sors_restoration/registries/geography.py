from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.schema import (
    FD_NAME_TO_CODE,
    FD_ORDER,
)

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


def build_geography_registry(region_specs) -> tuple[pd.DataFrame, pd.DataFrame]:
    parent_names = set(_PARENT_MEMBERS)
    atomic_rows: list[dict[str, object]] = []
    for spec in region_specs:
        if spec.region_kind in {'country_total', 'federal_district_total'}:
            continue
        if spec.canonical_name in parent_names:
            continue
        fd_name = str(spec.federal_district_name or '')
        fd_code = FD_NAME_TO_CODE.get(fd_name)
        if not fd_code:
            raise ValueError(
                f'Unknown federal district for atomic region {spec.canonical_name!r}: '
                f'{fd_name!r}'
            )
        atomic_rows.append(
            {
                'region_code': str(spec.code),
                'region_name': str(spec.canonical_name),
                'region_kind': str(spec.region_kind),
                'region_order': int(spec.order),
                'federal_district_code': fd_code,
                'federal_district_name': fd_name,
                'federal_district_order': FD_ORDER[fd_code],
            }
        )
    atomic = pd.DataFrame(atomic_rows).sort_values('region_order').reset_index(drop=True)
    if len(atomic) != 85:
        raise ValueError(f'Expected 85 atomic SORS territories, got {len(atomic)}')
    if atomic['region_code'].duplicated().any() or atomic['region_name'].duplicated().any():
        raise ValueError('Atomic SORS geography contains duplicate code or name')

    by_name = atomic.set_index('region_name')['region_code'].astype(str).to_dict()
    all_codes = tuple(atomic['region_code'].astype(str))
    node_rows: list[dict[str, object]] = []
    for spec in region_specs:
        fd_name = str(spec.federal_district_name or '') or None
        fd_code = FD_NAME_TO_CODE.get(fd_name or '')
        if spec.region_kind == 'country_total':
            members = all_codes
        elif spec.region_kind == 'federal_district_total':
            members = tuple(
                atomic.loc[
                    atomic['federal_district_name'].eq(fd_name), 'region_code'
                ].astype(str)
            )
        elif spec.canonical_name in _PARENT_MEMBERS:
            members = tuple(by_name[name] for name in _PARENT_MEMBERS[spec.canonical_name])
        else:
            members = (by_name[str(spec.canonical_name)],)
        node_rows.append(
            {
                'geography_node_id': str(spec.code),
                'geography_name': str(spec.canonical_name),
                'geography_kind': str(spec.region_kind),
                'geography_order': int(spec.order),
                'federal_district_code': fd_code,
                'federal_district_name': fd_name,
                'federal_district_order': None if fd_code is None else FD_ORDER[fd_code],
                'atomic_region_codes': members,
            }
        )
    nodes = pd.DataFrame(node_rows).sort_values('geography_order').reset_index(drop=True)
    if len(nodes) != 96:
        raise ValueError(f'Expected 96 published geography nodes, got {len(nodes)}')
    if nodes['geography_node_id'].duplicated().any():
        raise ValueError('Published SORS geography contains duplicate node IDs')

    seen: set[str] = set()
    for fd_code, group in atomic.groupby('federal_district_code', sort=False):
        current = set(group['region_code'].astype(str))
        if seen & current:
            raise ValueError(f'Federal district {fd_code} overlaps another district')
        seen.update(current)
    if seen != set(all_codes):
        raise ValueError('Federal districts do not form a complete atomic partition')
    return nodes, atomic
