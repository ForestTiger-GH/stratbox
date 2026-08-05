from __future__ import annotations

import importlib.resources as resources
import json
import re

import pandas as pd

_RESOURCE_PACKAGE = 'stratbox.macrobanks.cbr_sors_restoration.bridge'
_RESOURCE_DIR = '_resources'


def _resource(name: str):
    return resources.files(_RESOURCE_PACKAGE).joinpath(_RESOURCE_DIR, name)


def _read_csv(name: str) -> pd.DataFrame:
    ref = _resource(name)
    with resources.as_file(ref) as path:
        return pd.read_csv(path, dtype=str).fillna('')


def read_mapping_manifest() -> dict[str, object]:
    ref = _resource('mapping_manifest.json')
    with ref.open('r', encoding='utf-8') as stream:
        return json.load(stream)


def validate_mapping_version(mapping_version: str) -> dict[str, object]:
    manifest = read_mapping_manifest()
    actual = str(manifest.get('mapping_version', ''))
    if mapping_version != actual:
        raise ValueError(
            f'SORS mapping version mismatch: requested {mapping_version!r}, '
            f'packaged resource is {actual!r}'
        )
    return manifest


def read_legacy_atoms() -> pd.DataFrame:
    out = _read_csv('legacy_atoms.csv')
    if out['atom_code'].duplicated().any():
        raise ValueError('Duplicate legacy atom codes')
    return out


def read_legacy_membership() -> pd.DataFrame:
    out = _read_csv('legacy_node_membership.csv')
    if out.duplicated(['node_code', 'atom_code']).any():
        raise ValueError('Duplicate legacy node/atom memberships')
    return out


def _expand_codes(spec: str, valid: set[str]) -> tuple[str, ...]:
    result: list[str] = []
    for token in str(spec).split():
        match = re.fullmatch(r'(\d{2})-(\d{2})', token)
        if match:
            lo, hi = map(int, match.groups())
            result.extend(
                f'{value:02d}' for value in range(lo, hi + 1)
                if f'{value:02d}' in valid
            )
        elif token in valid:
            result.append(token)
        else:
            raise ValueError(f'Unknown OKVED2 class in bridge mapping: {token!r}')
    return tuple(dict.fromkeys(result))


def read_bridge_targets(okved2_classes: pd.DataFrame, mapping_version: str) -> pd.DataFrame:
    validate_mapping_version(mapping_version)
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


def build_atom_class_edges(
    okved2_classes: pd.DataFrame,
    mapping_version: str,
) -> pd.DataFrame:
    """Build the complete conditional atom/class graph.

    Every atom/class pair is represented so that all official legacy and OKVED2
    publications can remain hard constraints. Preferred edges have zero penalty;
    non-preferred edges carry unit reclassification penalty. The mapping remains
    methodology-derived and can therefore certify only conditional bridge facts.
    """
    targets = read_bridge_targets(okved2_classes, mapping_version)
    atoms = read_legacy_atoms()
    membership = read_legacy_membership()
    classes = tuple(okved2_classes['class_code'].astype(str))
    node_groups = {
        node: set(group['class_code'].astype(str))
        for node, group in targets.groupby('legacy_node_code', sort=False)
    }
    records: list[dict[str, object]] = []
    for atom in atoms.itertuples(index=False):
        atom_code = str(atom.atom_code)
        nodes = tuple(
            membership.loc[
                membership['atom_code'].astype(str).eq(atom_code), 'node_code'
            ].astype(str)
        )
        mapped_sets = [node_groups[node] for node in nodes if node in node_groups]
        if str(atom.atom_type) == 'technical_use_category':
            preferred = set(classes)
            derivation = 'TECHNICAL_CATEGORY_UNINFORMATIVE'
        elif mapped_sets:
            preferred = set.intersection(*mapped_sets)
            derivation = 'NODE_MAPPING_INTERSECTION'
        else:
            raise ValueError(f'Legacy atom {atom_code!r} has no bridge candidates')
        if not preferred:
            raise ValueError(f'Legacy atom {atom_code!r} has empty preferred bridge')
        for class_code in classes:
            is_preferred = class_code in preferred
            records.append({
                'mapping_version': mapping_version,
                'atom_code': atom_code,
                'atom_name_ru': str(atom.atom_name_ru),
                'atom_type': str(atom.atom_type),
                'class_code': class_code,
                'is_preferred': bool(is_preferred),
                'reclassification_penalty': 0.0 if is_preferred else 1.0,
                'evidence_type': (
                    'METHODOLOGY_DERIVED_PREFERRED'
                    if is_preferred else 'UNRESTRICTED_FALLBACK'
                ),
                'derivation': derivation,
                'source_nodes': ' '.join(nodes),
            })
    return pd.DataFrame(records)


def preferred_atom_classes(edges: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    preferred = edges[edges['is_preferred'].astype(bool)]
    return {
        atom: tuple(group['class_code'].astype(str))
        for atom, group in preferred.groupby('atom_code', sort=False)
    }
