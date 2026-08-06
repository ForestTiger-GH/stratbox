import pytest

from stratbox.macrobanks.cbr_sors_restoration.crosswalk.mapping import (
    read_atom_class_edges,
    read_crosswalk_manifest,
    read_crosswalk_scenarios,
    read_legacy_atoms,
    validate_mapping_version,
)
from stratbox.macrobanks.cbr_sors_restoration.registries.okved2 import (
    read_okved2_classes,
)


MAPPING_VERSION = 'cbr-legacy-okved2-crosswalk-2026.3'


def test_crosswalk_resources_are_packaged_and_versioned() -> None:
    manifest = read_crosswalk_manifest()
    assert manifest['mapping_version'] == MAPPING_VERSION
    assert read_crosswalk_scenarios(MAPPING_VERSION) == ('core', 'broad')
    validate_mapping_version(MAPPING_VERSION)
    with pytest.raises(ValueError, match='crosswalk version mismatch'):
        validate_mapping_version('invented')


def test_core_crosswalk_is_complete_and_contains_no_economic_universal_fallback() -> None:
    classes = read_okved2_classes()
    atoms = read_legacy_atoms()
    edges = read_atom_class_edges(classes, MAPPING_VERSION, 'core')
    assert edges['atom_code'].nunique() == len(atoms)
    assert edges['class_code'].nunique() == len(classes)
    economic = edges[~edges['atom_type'].eq('technical_use_category')]
    assert economic.groupby('atom_code').size().max() < len(classes)


def test_core_crosswalk_derives_residual_atoms_instead_of_intersecting_parent_sets() -> None:
    edges = read_atom_class_edges(
        read_okved2_classes(), MAPPING_VERSION, 'core'
    )

    def targets(atom: str) -> set[str]:
        return set(edges.loc[edges['atom_code'].eq(atom), 'class_code'].astype(str))

    assert targets('agriculture_hunting_services') == {'01'}
    assert targets('forestry') == {'02'}
    assert targets('mining_other') == {'08'}
    assert targets('construction_other') == {'43'}
    assert targets('manufacturing_machinery_other') == {'26', '27'}
    assert targets('manufacturing_transport_equipment_other') == {'30'}
    assert targets('transport_communications_other') == {
        '49', '50', '52', '53', '61'
    }


def test_publishing_class_is_not_lost_through_manufacturing_parent_intersection() -> None:
    edges = read_atom_class_edges(
        read_okved2_classes(), MAPPING_VERSION, 'core'
    )
    targets = set(
        edges.loc[
            edges['atom_code'].eq(
                'manufacturing_pulp_paper_publishing_printing'
            ),
            'class_code',
        ].astype(str)
    )
    assert targets == {'17', '18', '58'}


def test_technical_category_is_explicitly_visible_as_uncertainty() -> None:
    classes = read_okved2_classes()
    edges = read_atom_class_edges(classes, MAPPING_VERSION, 'core')
    technical = edges[
        edges['atom_code'].eq('completion_of_settlements')
    ]
    assert set(technical['class_code'].astype(str)) == set(
        classes['class_code'].astype(str)
    )
    assert set(technical['edge_kind']) == {'TECHNICAL_UNALLOCATED'}


def test_relation_ids_are_scenario_scoped() -> None:
    from stratbox.macrobanks.cbr_sors_restoration.crosswalk.mapping import (
        build_crosswalk_relations_grid,
    )

    edges = read_atom_class_edges(
        read_okved2_classes(),
        MAPPING_VERSION,
        'core',
    )
    relations = build_crosswalk_relations_grid(edges)
    assert relations['relation_id'].astype(str).str.startswith('crosswalk:core:').all()
    assert not relations['relation_id'].duplicated().any()
