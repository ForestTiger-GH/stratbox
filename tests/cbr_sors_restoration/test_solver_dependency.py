import sys
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import (
    CsrMatrixData,
    SorsLinearProblem,
)
from stratbox.macrobanks.cbr_sors_restoration.linear.highs import (
    SorsSolverDependencyError,
    _load_highs,
)


def test_solver_has_no_scipy_internal_fallback(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, 'highspy', None)
    with pytest.raises(SorsSolverDependencyError, match='official HiGHS'):
        _load_highs()


def test_crosswalk_solver_unavailable_returns_nonaccepted_result(
    monkeypatch,
    small_result,
) -> None:
    from stratbox.macrobanks.cbr_sors_restoration.contracts import (
        SorsCrosswalkConfig,
    )
    from stratbox.macrobanks.cbr_sors_restoration.crosswalk import operations
    from stratbox.macrobanks.cbr_sors_restoration.crosswalk.problem import (
        CrosswalkCompilation,
    )

    problem = SorsLinearProblem(
        model_layer='CROSSWALK',
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
    compilation = CrosswalkCompilation(
        problem=problem,
        target_catalog_grid=pd.DataFrame(),
        mapping_edges_grid=pd.DataFrame(),
        relations_grid=pd.DataFrame(),
    )
    scenario_grid = small_result.regional_okved2_grid.copy()
    scenario_grid['scenario_id'] = 'core'
    scenario_grid['bounds_certified'] = False
    scenario_grid['value_identified'] = False
    scenario_grid['is_final_accepted'] = False
    scenario_grid['is_benchmark_estimate'] = False
    scenario_grid['benchmark_value'] = None
    scenario_grid['value'] = None

    execution = operations._ScenarioExecution(
        scenario_id='core',
        status='SOLVER_UNAVAILABLE',
        grid=scenario_grid,
        compilation=compilation,
        derivations_grid=pd.DataFrame(),
        solver_runs_grid=pd.DataFrame(),
        conflicts_grid=pd.DataFrame(
            [
                {
                    'conflict_id': 'solver',
                    'conflict_status': 'SOLVER_UNAVAILABLE',
                }
            ]
        ),
        diagnostics_grid=pd.DataFrame(
            [{'key': 'scenario_id', 'value': 'core'}]
        ),
    )
    monkeypatch.setattr(
        operations,
        'read_crosswalk_scenarios',
        lambda *args: ('core',),
    )
    monkeypatch.setattr(operations, '_run_scenario', lambda *args: execution)

    result = operations.run_sors_crosswalk(
        replace(small_result, _source_bundle=object()),
        SorsCrosswalkConfig(mode='feasibility'),
    )
    assert result.status == 'SOLVER_UNAVAILABLE'
    assert not result.crosswalk_facts_grid.shape[0]
    assert int(result.regional_okved2_grid['is_final_accepted'].fillna(False).sum()) == int(
        small_result.regional_okved2_grid['is_strict_fact'].sum()
    )


def test_highs_session_applies_solver_options_and_refreshes_bounds(monkeypatch) -> None:
    from types import SimpleNamespace

    from stratbox.macrobanks.cbr_sors_restoration.linear import highs as highs_module

    calls: dict[str, object] = {}

    class FakeHighs:
        def __init__(self) -> None:
            calls['instance'] = self

        def setOptionValue(self, name, value):
            calls.setdefault('options', {})[name] = value
            return 'kOk'

        def passModel(self, model):
            calls['model'] = model
            return 'kOk'

        def version(self):
            return 'fake-1'

        def changeColsBounds(self, count, indices, lower, upper):
            calls['changed_bounds'] = (
                count,
                np.asarray(indices).copy(),
                np.asarray(lower).copy(),
                np.asarray(upper).copy(),
            )
            return 'kOk'

    class FakeLp:
        pass

    class FakeSparse:
        pass

    fake_obj_sense = SimpleNamespace(kMinimize='minimize')
    fake_matrix_format = SimpleNamespace(kRowwise='rowwise')
    monkeypatch.setattr(
        highs_module,
        '_load_highs',
        lambda: (
            FakeHighs,
            FakeLp,
            FakeSparse,
            fake_matrix_format,
            fake_obj_sense,
            object(),
        ),
    )
    problem = SorsLinearProblem(
        model_layer='TEST',
        matrix=CsrMatrixData(
            shape=(0, 2),
            indptr=np.asarray([0], dtype=np.int64),
            indices=np.asarray([], dtype=np.int32),
            data=np.asarray([], dtype=float),
        ),
        row_lower=np.asarray([], dtype=float),
        row_upper=np.asarray([], dtype=float),
        col_lower=np.asarray([0.0, -np.inf], dtype=float),
        col_upper=np.asarray([1.0, np.inf], dtype=float),
        objective=np.zeros(2, dtype=float),
        constraints_grid=pd.DataFrame(),
        variables_grid=pd.DataFrame(),
    )

    session = highs_module.HighsSession(
        problem,
        time_limit_seconds=12.0,
        threads=2,
        solver='ipm',
        run_crossover='choose',
    )
    session.update_column_bounds(
        np.asarray([0.1, -np.inf]),
        np.asarray([0.9, np.inf]),
    )

    assert calls['options']['solver'] == 'ipm'
    assert calls['options']['run_crossover'] == 'choose'
    assert calls['options']['threads'] == 2
    assert calls['options']['time_limit'] == 12.0
    count, indices, lower, upper = calls['changed_bounds']
    assert count == 2
    assert np.array_equal(indices, np.asarray([0, 1], dtype=np.int32))
    assert lower[0] == 0.1
    assert lower[1] == -1e30
    assert upper[0] == 0.9
    assert upper[1] == 1e30
