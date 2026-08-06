import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.crosswalk.closure import (
    close_crosswalk_bounds,
)
from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import (
    CsrMatrixData,
    SorsLinearProblem,
)


def _problem() -> SorsLinearProblem:
    # x + y = 100; y = 60; x + z = 75.
    matrix = CsrMatrixData(
        shape=(3, 3),
        indptr=np.asarray([0, 2, 3, 5], dtype=np.int64),
        indices=np.asarray([0, 1, 1, 0, 2], dtype=np.int32),
        data=np.ones(5, dtype=float),
    )
    constraints = pd.DataFrame(
        [
            {'constraint_id': 'sum_xy'},
            {'constraint_id': 'y'},
            {'constraint_id': 'sum_xz'},
        ]
    )
    variables = pd.DataFrame(
        {
            'solver_column': [0, 1, 2],
            'lower_bound': [0.0, 0.0, 0.0],
            'upper_bound': [np.inf, np.inf, np.inf],
        }
    )
    return SorsLinearProblem(
        model_layer='CROSSWALK',
        matrix=matrix,
        row_lower=np.asarray([100.0, 60.0, 75.0]),
        row_upper=np.asarray([100.0, 60.0, 75.0]),
        col_lower=np.zeros(3, dtype=float),
        col_upper=np.full(3, np.inf, dtype=float),
        objective=np.zeros(3, dtype=float),
        constraints_grid=constraints,
        variables_grid=variables,
    )


def test_crosswalk_closure_cascades_residual_equations() -> None:
    result = close_crosswalk_bounds(_problem(), tolerance=1e-9)
    assert result.passes >= 2
    assert np.allclose(result.problem.col_lower, [40.0, 60.0, 35.0])
    assert np.allclose(result.problem.col_upper, [40.0, 60.0, 35.0])
    assert set(result.derivations_grid['rule_id']) == {
        'SUM_UPPER_TO_VARIABLE_UPPER',
        'SUM_LOWER_RESIDUAL_TO_VARIABLE_LOWER',
    }
