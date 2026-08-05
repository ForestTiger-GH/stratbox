from __future__ import annotations

import sys

import pandas as pd
import pytest

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsRestorationResult,
    SorsRunConfig,
)
from stratbox.macrobanks.cbr_sors_restoration.mapping import (
    build_atom_class_edges,
    read_legacy_atoms,
    read_mapping_manifest,
    validate_mapping_version,
)
from stratbox.macrobanks.cbr_sors_restoration.metrics import source_metric
from stratbox.macrobanks.cbr_sors_restoration.okved2 import read_okved2_classes
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    RoundingPolicy,
    publication_interval,
    published_bucket,
)
from stratbox.macrobanks.cbr_sors_restoration.solver import (
    SorsSolverDependencyError,
    _load_highs,
)


def test_publication_zero_is_an_interval_not_exact_zero() -> None:
    assert publication_interval(0.0) == (0.0, 0.5)
    assert published_bucket(0.0, 0.499999) == 0.0


def test_publication_rounding_is_explicit_half_up() -> None:
    policy = RoundingPolicy(step=1.0)
    assert policy.bucket(2.5) == 3.0
    assert policy.single_bucket(10.01, 10.49) == 10.0
    assert policy.single_bucket(10.49, 10.51) is None


def test_source_metrics_cover_all_six_publications() -> None:
    assert source_metric('debt', 'rub') == 'debt_rub'
    assert source_metric('debt', 'fx') == 'debt_fx'
    assert source_metric('debt', 'total') == 'debt_total'
    assert source_metric('overdue', 'rub') == 'overdue_rub'
    assert source_metric('overdue', 'fx') == 'overdue_fx'
    assert source_metric('overdue', 'total') == 'overdue_total'


def test_okved2_registry_drives_classes_and_sections() -> None:
    classes = read_okved2_classes()
    assert len(classes) == 88
    assert classes.set_index('class_code').loc['01', 'section_code'] == 'A'
    assert classes.set_index('class_code').loc['35', 'section_code'] == 'D'
    assert classes.set_index('class_code').loc['68', 'section_code'] == 'L'
    assert classes.set_index('class_code').loc['85', 'section_code'] == 'P'


def test_mapping_version_is_packaged_and_strictly_validated() -> None:
    manifest = read_mapping_manifest()
    assert manifest['mapping_version'] == 'cbr-legacy-okved2-bridge-2026.2'
    validate_mapping_version('cbr-legacy-okved2-bridge-2026.2')
    with pytest.raises(ValueError, match='mapping version mismatch'):
        validate_mapping_version('invented-version')


def test_atom_graph_is_complete_and_preferred_edges_are_separate() -> None:
    classes = read_okved2_classes()
    atoms = read_legacy_atoms()
    edges = build_atom_class_edges(
        classes, 'cbr-legacy-okved2-bridge-2026.2'
    )
    assert len(edges) == len(atoms) * len(classes)
    wood = edges[
        edges['atom_code'].eq('manufacturing_wood_products')
        & edges['is_preferred'].astype(bool)
    ]
    assert tuple(wood['class_code']) == ('16',)
    completion = edges[
        edges['atom_code'].eq('completion_of_settlements')
        & edges['is_preferred'].astype(bool)
    ]
    assert len(completion) == len(classes)
    assert set(edges['reclassification_penalty'].astype(float)) == {0.0, 1.0}


def test_conditional_bridge_is_disabled_only_explicitly() -> None:
    config = SorsRunConfig(as_of_date='2026-06-01')
    assert config.include_conditional_bridge is True
    assert config.bridge_objective_tolerance > 0


def test_result_contract_separates_facts_and_estimates() -> None:
    result = SorsRestorationResult(
        canonical_grid=pd.DataFrame(),
        facts_grid=pd.DataFrame(),
        estimates_grid=pd.DataFrame(),
        bounds_grid=pd.DataFrame(),
        bridge_bounds_grid=pd.DataFrame(),
        bridge_diagnostics_grid=pd.DataFrame(),
        constraints_grid=pd.DataFrame(),
        mapping_edges_grid=pd.DataFrame(),
        conflicts_grid=pd.DataFrame(),
        audit={},
    )
    assert result.facts_grid is not result.estimates_grid


def test_solver_has_no_scipy_internal_fallback(monkeypatch) -> None:
    # The environment used for unit tests may or may not contain highspy. Force
    # the import to fail and verify that the domain raises its own clear error.
    monkeypatch.setitem(sys.modules, 'highspy', None)
    with pytest.raises(SorsSolverDependencyError, match='official HiGHS'):
        _load_highs()
