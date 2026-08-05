from __future__ import annotations

import importlib.resources as resources
import re

import pandas as pd

_RESOURCE_PACKAGE = 'stratbox.macrobanks.cbr_sors_restoration'
_RESOURCE_DIR = '_resources'


def _read_csv(name: str) -> pd.DataFrame:
    ref = resources.files(_RESOURCE_PACKAGE).joinpath(_RESOURCE_DIR, name)
    with resources.as_file(ref) as path:
        return pd.read_csv(path, dtype=str).fillna('')


def read_legacy_atoms() -> pd.DataFrame:
    out = _read_csv('legacy_atoms.csv')
    if out['atom_code'].duplicated().any():
        raise ValueError('Duplicate legacy atom codes')
    return out


def read_legacy_membership() -> pd.DataFrame:
    return _read_csv('legacy_node_membership.csv')


def _expand_codes(spec: str, valid: set[str]) -> tuple[str, ...]:
    result: list[str] = []
    for token in str(spec).split():
        match = re.fullmatch(r'(\d{2})-(\d{2})', token)
        if match:
            lo, hi = map(int, match.groups())
            result.extend(f'{value:02d}' for value in range(lo, hi + 1) if f'{value:02d}' in valid)
        elif token in valid:
            result.append(token)
        else:
            raise ValueError(f'Unknown OKVED2 class in bridge mapping: {token!r}')
    return tuple(dict.fromkeys(result))


def read_bridge_targets(okved2_classes: pd.DataFrame, mapping_version: str) -> pd.DataFrame:
    source = _read_csv('bridge_targets.csv')
    membership = read_legacy_membership()
    known_nodes = set(membership['node_code'].astype(str))
    unknown_nodes = sorted(set(source['node_code'].astype(str)) - known_nodes)
    if unknown_nodes:
        raise ValueError(f'Bridge contains unknown legacy nodes: {unknown_nodes}')
    valid = set(okved2_classes['class_code'].astype(str))
    records: list[dict[str, object]] = []
    for row in source.itertuples(index=False):
        for class_code in _expand_codes(row.okved2_classes, valid):
            records.append({
                'mapping_version': mapping_version,
                'legacy_node_code': row.node_code,
                'class_code': class_code,
                'relation_type': row.relation_type,
                'evidence_type': row.evidence_type,
                'base_weight': float(row.base_weight),
                'comment': row.comment,
            })
    out = pd.DataFrame(records)
    if out.empty:
        raise ValueError('Bridge target registry is empty')
    return out


def bridge_groups(edges: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    return {
        node: tuple(group['class_code'].astype(str))
        for node, group in edges.groupby('legacy_node_code', sort=False)
    }


def bridge_weights(edges: pd.DataFrame) -> dict[str, float]:
    return edges.groupby('legacy_node_code')['base_weight'].first().astype(float).to_dict()
