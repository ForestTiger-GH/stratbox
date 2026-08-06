from __future__ import annotations

import importlib.resources as resources
import json
import re

import pandas as pd

_RESOURCE_PACKAGE = 'stratbox.macrobanks.cbr_sors_restoration.crosswalk'
_RESOURCE_DIR = '_resources'


def _resource(name: str):
    return resources.files(_RESOURCE_PACKAGE).joinpath(_RESOURCE_DIR, name)


def _read_csv(name: str) -> pd.DataFrame:
    ref = _resource(name)
    with resources.as_file(ref) as path:
        return pd.read_csv(path, dtype=str).fillna('')


def read_crosswalk_manifest() -> dict[str, object]:
    ref = _resource('crosswalk_manifest.json')
    with ref.open('r', encoding='utf-8') as stream:
        return json.load(stream)


def validate_mapping_version(mapping_version: str) -> dict[str, object]:
    manifest = read_crosswalk_manifest()
    actual = str(manifest.get('mapping_version', ''))
    if mapping_version != actual:
        raise ValueError(
            f'SORS crosswalk version mismatch: requested {mapping_version!r}, '
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
    atoms = set(read_legacy_atoms()['atom_code'].astype(str))
    unknown = sorted(set(out['atom_code'].astype(str)) - atoms)
    if unknown:
        raise ValueError(f'Legacy membership contains unknown atoms: {unknown}')
    return out


def _expand_codes(spec: str, valid: set[str]) -> tuple[str, ...]:
    result: list[str] = []
    for token in str(spec).split():
        match = re.fullmatch(r'(\d{2})-(\d{2})', token)
        if match:
            lo, hi = map(int, match.groups())
            if lo > hi:
                raise ValueError(f'Invalid OKVED2 range: {token!r}')
            result.extend(
                f'{value:02d}'
                for value in range(lo, hi + 1)
                if f'{value:02d}' in valid
            )
        elif token in valid:
            result.append(token)
        else:
            raise ValueError(f'Unknown OKVED2 class in crosswalk mapping: {token!r}')
    expanded = tuple(dict.fromkeys(result))
    if not expanded:
        raise ValueError(f'Crosswalk class specification is empty: {spec!r}')
    return expanded


def read_crosswalk_scenarios(mapping_version: str) -> tuple[str, ...]:
    manifest = validate_mapping_version(mapping_version)
    scenarios = tuple(str(value) for value in manifest.get('scenario_ids', ()))
    if not scenarios:
        raise ValueError('Crosswalk manifest contains no scenarios')
    return scenarios


def read_atom_class_edges(
    okved2_classes: pd.DataFrame,
    mapping_version: str,
    scenario_id: str,
) -> pd.DataFrame:
    manifest = validate_mapping_version(mapping_version)
    known_scenarios = set(str(value) for value in manifest.get('scenario_ids', ()))
    if scenario_id not in known_scenarios:
        raise ValueError(
            f'Unknown SORS crosswalk scenario {scenario_id!r}; '
            f'expected one of {sorted(known_scenarios)}'
        )

    source = _read_csv('atom_class_edges.csv')
    source = source[source['scenario_id'].astype(str).eq(scenario_id)].copy()
    if source.empty:
        raise ValueError(f'Crosswalk scenario {scenario_id!r} contains no edges')

    atoms = read_legacy_atoms()
    atom_types = atoms.set_index('atom_code')['atom_type'].astype(str).to_dict()
    unknown_atoms = sorted(set(source['atom_code'].astype(str)) - set(atom_types))
    if unknown_atoms:
        raise ValueError(f'Crosswalk contains unknown legacy atoms: {unknown_atoms}')
    duplicate_atoms = source['atom_code'].astype(str).duplicated()
    if duplicate_atoms.any():
        values = sorted(source.loc[duplicate_atoms, 'atom_code'].astype(str).unique())
        raise ValueError(f'Crosswalk scenario has duplicate atom specifications: {values}')

    valid_classes = set(okved2_classes['class_code'].astype(str))
    records: list[dict[str, object]] = []
    for row in source.itertuples(index=False):
        atom_code = str(row.atom_code)
        classes = _expand_codes(str(row.okved2_classes), valid_classes)
        for class_code in classes:
            records.append(
                {
                    'mapping_version': mapping_version,
                    'scenario_id': scenario_id,
                    'atom_code': atom_code,
                    'atom_type': atom_types[atom_code],
                    'class_code': class_code,
                    'edge_kind': str(row.edge_kind),
                    'evidence_type': str(row.evidence_type),
                    'comment': str(row.comment),
                }
            )
    out = pd.DataFrame(records)
    if out.duplicated(['atom_code', 'class_code']).any():
        raise ValueError('Crosswalk scenario contains duplicate atom/class edges')

    represented_atoms = set(out['atom_code'].astype(str))
    missing_atoms = sorted(set(atom_types) - represented_atoms)
    if missing_atoms:
        raise ValueError(f'Crosswalk scenario omits legacy atoms: {missing_atoms}')
    represented_classes = set(out['class_code'].astype(str))
    missing_classes = sorted(valid_classes - represented_classes)
    if missing_classes:
        raise ValueError(f'Crosswalk scenario omits OKVED2 classes: {missing_classes}')

    technical = out[out['atom_type'].eq('technical_use_category')]
    economic = out[~out['atom_type'].eq('technical_use_category')]
    for atom_code, group in economic.groupby('atom_code', sort=False):
        if len(group) == len(valid_classes):
            raise ValueError(
                f'Economic atom {atom_code!r} is an unrestricted universal fallback'
            )
    if technical.empty:
        raise ValueError('Crosswalk scenario must explicitly represent technical mass')

    atom_order = {
        code: position
        for position, code in enumerate(atoms['atom_code'].astype(str), start=1)
    }
    class_order = okved2_classes.set_index('class_code')['class_order'].astype(int).to_dict()
    out['atom_order'] = out['atom_code'].map(atom_order)
    out['class_order'] = out['class_code'].map(class_order)
    return out.sort_values(['atom_order', 'class_order'], kind='stable').reset_index(
        drop=True
    )


def build_crosswalk_relations_grid(edges: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    mapping_version = str(edges['mapping_version'].iloc[0])
    scenario_id = str(edges['scenario_id'].iloc[0])
    for atom_code, group in edges.groupby('atom_code', sort=False):
        records.append(
            {
                'mapping_version': mapping_version,
                'scenario_id': scenario_id,
                'relation_id': f'crosswalk:{scenario_id}:atom:{atom_code}',
                'relation_kind': 'LEGACY_ATOM_FLOW_CONSERVATION',
                'legacy_atom_code': str(atom_code),
                'okved2_class_codes': tuple(group['class_code'].astype(str)),
                'evidence_type': '|'.join(
                    sorted(set(group['evidence_type'].astype(str)))
                ),
                'comment': str(group['comment'].iloc[0]),
            }
        )
    for class_code, group in edges.groupby('class_code', sort=False):
        records.append(
            {
                'mapping_version': mapping_version,
                'scenario_id': scenario_id,
                'relation_id': f'crosswalk:{scenario_id}:class:{class_code}',
                'relation_kind': 'OKVED2_CLASS_FLOW_CONSERVATION',
                'legacy_atom_code': None,
                'okved2_class_codes': (str(class_code),),
                'incoming_legacy_atoms': tuple(group['atom_code'].astype(str)),
                'evidence_type': '|'.join(
                    sorted(set(group['evidence_type'].astype(str)))
                ),
                'comment': 'OKVED2 class equals the sum of incoming allowed atom flows.',
            }
        )
    return pd.DataFrame(records)
