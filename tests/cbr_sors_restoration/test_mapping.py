import pytest

from stratbox.macrobanks.cbr_sors_restoration.bridge.mapping import (
    build_atom_class_edges,
    read_legacy_atoms,
    read_mapping_manifest,
    validate_mapping_version,
)
from stratbox.macrobanks.cbr_sors_restoration.registries.okved2 import read_okved2_classes


def test_mapping_resources_are_packaged_and_versioned() -> None:
    manifest = read_mapping_manifest()
    assert manifest['mapping_version'] == 'cbr-legacy-okved2-bridge-2026.2'
    validate_mapping_version('cbr-legacy-okved2-bridge-2026.2')
    with pytest.raises(ValueError, match='mapping version mismatch'):
        validate_mapping_version('invented')


def test_complete_conditional_edge_registry() -> None:
    classes = read_okved2_classes()
    atoms = read_legacy_atoms()
    edges = build_atom_class_edges(classes, 'cbr-legacy-okved2-bridge-2026.2')
    assert len(edges) == len(classes) * len(atoms)
    assert set(edges['reclassification_penalty'].astype(float)) == {0.0, 1.0}
