from __future__ import annotations

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.mapping import read_bridge_targets
from stratbox.macrobanks.cbr_sors_restoration.metrics import source_metric
from stratbox.macrobanks.cbr_sors_restoration.okved2 import read_okved2_classes
from stratbox.macrobanks.cbr_sors_restoration.problem import (
    CsrMatrixData,
    SorsProblem,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    RoundingPolicy,
    publication_interval,
    published_bucket,
)
from stratbox.macrobanks.cbr_sors_restoration.solver import solve_cold_minmax


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


def test_bridge_keeps_singleton_and_group_edges_separate() -> None:
    classes = read_okved2_classes()
    edges = read_bridge_targets(classes, 'test-mapping')
    wood = edges[edges['legacy_node_code'].eq('manufacturing_wood_products')]
    assert tuple(wood['class_code']) == ('16',)
    food = edges[
        edges['legacy_node_code'].eq('manufacturing_food_beverages_tobacco')
    ]
    assert set(food['class_code']) == {'10', '11', '12'}
    assert set(edges['evidence_type']) == {'METHODOLOGY_DERIVED'}


def test_solver_certifies_a_linear_target_on_tiny_problem() -> None:
    # x + y = 10, 0 <= x <= 4, y >= 0. Therefore x is in [0, 4].
    problem = SorsProblem(
        matrix=CsrMatrixData(
            shape=(1, 2),
            indptr=np.asarray([0, 2], dtype=np.int64),
            indices=np.asarray([0, 1], dtype=np.int32),
            data=np.asarray([1.0, 1.0]),
        ),
        row_lower=np.asarray([10.0]),
        row_upper=np.asarray([10.0]),
        col_lower=np.asarray([0.0, 0.0]),
        col_upper=np.asarray([4.0, np.inf]),
        bridge_objective=np.zeros(2),
        variable_grid=pd.DataFrame({'variable_id': [0, 1]}),
        constraints_grid=pd.DataFrame({'constraint_id': ['sum']}),
        region_positions={},
        class_positions={},
        component_positions={},
        n_primary_variables=2,
    )
    lower, upper, _, _ = solve_cold_minmax(
        problem,
        np.asarray([0], dtype=np.int32),
        np.asarray([1.0]),
        time_limit=30.0,
        threads=1,
    )
    assert lower.success and upper.success
    assert lower.objective_value == 0.0
    assert upper.objective_value == 4.0
