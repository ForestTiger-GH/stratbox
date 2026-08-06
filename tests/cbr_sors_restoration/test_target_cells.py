from __future__ import annotations

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsCellResolutionConfig,
)
from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import (
    CsrMatrixData,
    LinearTarget,
    SorsLinearProblem,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.strict.closure import SorsClosureState
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
    SorsQuantityGraph,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.subsystem import (
    SorsTargetSubsystem,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.target_solver import (
    apply_cell_proof,
    prove_cell_uniqueness,
)


def _bounds_only_subsystem(lower: float, upper: float) -> SorsTargetSubsystem:
    variables = pd.DataFrame(
        [
            {
                'quantity_id': 'component:r1:01:overdue_rub',
                'solver_column': 0,
            }
        ]
    )
    problem = SorsLinearProblem(
        model_layer='STRICT_TARGET_SUBSYSTEM',
        matrix=CsrMatrixData(
            shape=(0, 1),
            indptr=np.asarray([0], dtype=np.int64),
            indices=np.asarray([], dtype=np.int32),
            data=np.asarray([], dtype=float),
        ),
        row_lower=np.asarray([], dtype=float),
        row_upper=np.asarray([], dtype=float),
        col_lower=np.asarray([lower], dtype=float),
        col_upper=np.asarray([upper], dtype=float),
        objective=np.zeros(1, dtype=float),
        constraints_grid=pd.DataFrame(),
        variables_grid=variables,
    )
    target = LinearTarget(
        target_id='r1:01:overdue_rub',
        quantity_id='component:r1:01:overdue_rub',
        region_code='r1',
        region_name='Регион 1',
        class_code='01',
        metric='overdue_rub',
        indices=np.asarray([0], dtype=np.int32),
        coefficients=np.asarray([1.0], dtype=float),
    )
    return SorsTargetSubsystem(
        subsystem_id='attempt:cell',
        target_id=target.target_id,
        horizon='CELL',
        problem=problem,
        target=target,
        original_solver_rows=(),
        original_solver_columns=(0,),
        supporting_constraint_ids=(),
    )


def _quantity_grid(lower: float, upper: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                'quantity_id': 'component:r1:01:overdue_rub',
                'quantity_kind': 'ATOMIC_COMPONENT',
                'lower_bound': lower,
                'upper_bound': upper,
                'lower_attained': True,
                'upper_attained': True,
            }
        ]
    )


def test_bounds_only_target_is_promoted_as_exact_unique_value() -> None:
    subsystem = _bounds_only_subsystem(7.0, 7.0)
    proof = prove_cell_uniqueness(
        subsystem,
        SorsCellResolutionConfig(),
        RoundingPolicy(step=1.0),
        point_tolerance=1e-9,
        attempt_id='attempt:1',
    )

    assert proof.status == 'UNIQUE_FEASIBLE_VALUE'
    assert proof.unique_value == 7.0
    assert proof.value_precision == 'EXACT'
    assert tuple(proof.solver_runs_grid['solve_id']) == proof.proof_ids

    updated, changed = apply_cell_proof(
        _quantity_grid(0.0, 10.0),
        proof,
        point_tolerance=1e-9,
        attempt_id='attempt:1',
    )
    row = updated.iloc[0]
    assert changed
    assert row.lower_bound == 7.0
    assert row.upper_bound == 7.0
    assert row.lower_attained and row.upper_attained


def test_publication_bucket_uniqueness_does_not_become_false_exact_point() -> None:
    subsystem = _bounds_only_subsystem(10.6, 11.4)
    proof = prove_cell_uniqueness(
        subsystem,
        SorsCellResolutionConfig(accept_published_bucket=True),
        RoundingPolicy(step=1.0),
        point_tolerance=1e-9,
        attempt_id='attempt:2',
    )

    assert proof.status == 'UNIQUE_AT_PUBLISHED_PRECISION'
    assert proof.unique_value == 11.0
    assert proof.value_precision == 'PUBLISHED'

    updated, changed = apply_cell_proof(
        _quantity_grid(0.0, 20.0),
        proof,
        point_tolerance=1e-9,
        attempt_id='attempt:2',
    )
    row = updated.iloc[0]
    assert changed
    assert row.lower_bound == 10.6
    assert row.upper_bound == 11.4
    assert row.lower_bound != row.upper_bound


def _two_relation_graph() -> SorsQuantityGraph:
    quantities = pd.DataFrame(
        [
            {
                'quantity_id': 'p1',
                'quantity_kind': 'TEST',
                'lower_bound': 100.0,
                'upper_bound': 100.0,
                'lower_attained': True,
                'upper_attained': True,
            },
            {
                'quantity_id': 'p2',
                'quantity_kind': 'TEST',
                'lower_bound': 0.0,
                'upper_bound': float('inf'),
                'lower_attained': True,
                'upper_attained': False,
            },
            {
                'quantity_id': 'a',
                'quantity_kind': 'TEST',
                'lower_bound': 30.0,
                'upper_bound': 30.0,
                'lower_attained': True,
                'upper_attained': True,
            },
            {
                'quantity_id': 'b',
                'quantity_kind': 'TEST',
                'lower_bound': 0.0,
                'upper_bound': float('inf'),
                'lower_attained': True,
                'upper_attained': False,
            },
            {
                'quantity_id': 'c',
                'quantity_kind': 'TEST',
                'lower_bound': 0.0,
                'upper_bound': float('inf'),
                'lower_attained': True,
                'upper_attained': False,
            },
        ]
    )
    relations = pd.DataFrame(
        [
            {
                'relation_id': 'r1',
                'relation_kind': 'SUM',
                'parent_quantity_id': 'p1',
                'child_quantity_ids': ('a', 'b'),
                'source_observation_ids': (),
            },
            {
                'relation_id': 'r2',
                'relation_kind': 'SUM',
                'parent_quantity_id': 'p2',
                'child_quantity_ids': ('b', 'c'),
                'source_observation_ids': (),
            },
        ]
    )
    return SorsQuantityGraph(quantities, relations, pd.DataFrame())


def test_persistent_closure_assigns_unique_derivation_ids_across_cascade_runs() -> None:
    state = SorsClosureState(_two_relation_graph())
    first = state.run()
    assert first.quantities_grid.set_index('quantity_id').loc['b', 'lower_bound'] == 70.0

    updated = state.quantities_grid.copy()
    p2 = updated['quantity_id'].eq('p2')
    updated.loc[p2, ['lower_bound', 'upper_bound']] = 90.0
    updated.loc[p2, ['lower_attained', 'upper_attained']] = True
    state.replace_quantities(updated)
    second = state.run(seed_quantity_ids=('p2',))

    assert second.quantities_grid.set_index('quantity_id').loc['c', 'lower_bound'] == 20.0
    ids = tuple(state.derivations_grid['derivation_id'].astype(str))
    assert len(ids) == len(set(ids))
    assert ids[0] == 'derivation:00000001'
    assert ids[-1] == f'derivation:{len(ids):08d}'


def test_unconfirmed_global_feasibility_never_populates_accepted_fact_ledger() -> None:
    from types import SimpleNamespace

    from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import (
        StrictCompilation,
    )
    from stratbox.macrobanks.cbr_sors_restoration.strict.engine import (
        run_cell_resolution,
    )

    quantity_id = 'component:r1:01:overdue_rub'
    quantities = pd.DataFrame(
        [
            {
                'quantity_id': quantity_id,
                'quantity_kind': 'ATOMIC_COMPONENT',
                'region_code': 'r1',
                'class_code': '01',
                'component': 'overdue_rub',
                'metric': None,
                'lower_bound': 0.0,
                'upper_bound': 0.5,
                'lower_attained': True,
                'upper_attained': False,
            }
        ]
    )
    graph = SorsQuantityGraph(quantities, pd.DataFrame(), pd.DataFrame())
    state = SorsClosureState(graph)
    target_catalog = pd.DataFrame(
        [
            {
                'target_id': 'r1:01:overdue_rub',
                'quantity_id': quantity_id,
                'region_code': 'r1',
                'region_name': 'Регион 1',
                'region_order': 1,
                'federal_district_code': 'fd1',
                'federal_district_name': 'Округ 1',
                'federal_district_order': 1,
                'class_code': '01',
                'class_name': 'Класс 01',
                'class_order': 1,
                'section_code': 'A',
                'section_name': 'Раздел A',
                'section_order': 1,
                'publication_category_code': '01',
                'component': 'overdue_rub',
                'component_name': 'Рубли просроченные',
                'component_order': 1,
                'solver_column': None,
                'connected_component_id': None,
                'initially_fixed': False,
                'initial_fixed_value': None,
                'lower_bound': 0.0,
                'upper_bound': 0.5,
                'lower_attained': True,
                'upper_attained': False,
            }
        ]
    )
    empty_problem = SorsLinearProblem(
        model_layer='STRICT',
        matrix=CsrMatrixData(
            shape=(0, 0),
            indptr=np.asarray([0], dtype=np.int64),
            indices=np.asarray([], dtype=np.int32),
            data=np.asarray([], dtype=float),
        ),
        row_lower=np.asarray([], dtype=float),
        row_upper=np.asarray([], dtype=float),
        col_lower=np.asarray([], dtype=float),
        col_upper=np.asarray([], dtype=float),
        objective=np.asarray([], dtype=float),
        constraints_grid=pd.DataFrame(),
        variables_grid=pd.DataFrame(),
    )
    compilation = StrictCompilation(
        problem=empty_problem,
        target_catalog_grid=pd.DataFrame(),
        cell_target_catalog_grid=target_catalog,
    )
    bundle = SimpleNamespace(
        atomic_regions_grid=pd.DataFrame(
            [
                {
                    'region_code': 'r1',
                    'region_name': 'Регион 1',
                    'region_order': 1,
                }
            ]
        ),
        okved2_classes_grid=pd.DataFrame(
            [{'class_code': '01', 'class_order': 1}]
        ),
    )

    result = run_cell_resolution(
        bundle,
        graph,
        compilation,
        state,
        SorsCellResolutionConfig(mode='closure'),
        RoundingPolicy(step=1.0),
        point_tolerance=1e-9,
        feasibility_confirmed=False,
    )

    assert result.facts_ledger_grid.empty
    assert result.current_facts_grid.empty


def test_solver_dependency_failure_has_auditable_proof_records(monkeypatch) -> None:
    from stratbox.macrobanks.cbr_sors_restoration.linear.highs import (
        SorsSolverDependencyError,
    )
    from stratbox.macrobanks.cbr_sors_restoration.strict import target_solver

    subsystem = _bounds_only_subsystem(0.0, 10.0)
    constrained_problem = SorsLinearProblem(
        model_layer=subsystem.problem.model_layer,
        matrix=CsrMatrixData(
            shape=(1, 1),
            indptr=np.asarray([0, 1], dtype=np.int64),
            indices=np.asarray([0], dtype=np.int32),
            data=np.asarray([1.0], dtype=float),
        ),
        row_lower=np.asarray([0.0], dtype=float),
        row_upper=np.asarray([10.0], dtype=float),
        col_lower=subsystem.problem.col_lower,
        col_upper=subsystem.problem.col_upper,
        objective=subsystem.problem.objective,
        constraints_grid=pd.DataFrame(
            [{'constraint_id': 'c1', 'solver_row': 0}]
        ),
        variables_grid=subsystem.problem.variables_grid,
    )
    constrained = SorsTargetSubsystem(
        subsystem_id=subsystem.subsystem_id,
        target_id=subsystem.target_id,
        horizon='REGION_COMPONENT',
        problem=constrained_problem,
        target=subsystem.target,
        original_solver_rows=(0,),
        original_solver_columns=(0,),
        supporting_constraint_ids=('c1',),
    )

    class UnavailableSession:
        def __init__(self, *args, **kwargs) -> None:
            raise SorsSolverDependencyError('highspy missing')

    monkeypatch.setattr(target_solver, 'HighsSession', UnavailableSession)
    proof = prove_cell_uniqueness(
        constrained,
        SorsCellResolutionConfig(),
        RoundingPolicy(step=1.0),
        point_tolerance=1e-9,
        attempt_id='attempt:unavailable',
    )

    assert proof.status == 'SOLVER_INCOMPLETE'
    assert tuple(proof.solver_runs_grid['solve_id']) == proof.proof_ids
    assert set(proof.solver_runs_grid['status']) == {'SOLVER_UNAVAILABLE'}
    assert all(value.endswith(':unavailable') for value in proof.proof_ids)
