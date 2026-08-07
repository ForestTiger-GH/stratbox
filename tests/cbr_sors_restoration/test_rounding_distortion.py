from __future__ import annotations

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import (
    CsrMatrixData,
    SorsLinearProblem,
)
from stratbox.macrobanks.cbr_sors_restoration.optimization.distortion import (
    build_rounding_distortion_problem,
)


def _csr(rows: list[list[tuple[int, float]]], n_columns: int) -> CsrMatrixData:
    indptr = [0]
    indices: list[int] = []
    data: list[float] = []
    for row in rows:
        for column, coefficient in row:
            indices.append(column)
            data.append(coefficient)
        indptr.append(len(indices))
    return CsrMatrixData(
        shape=(len(rows), n_columns),
        indptr=np.asarray(indptr, dtype=np.int64),
        indices=np.asarray(indices, dtype=np.int32),
        data=np.asarray(data, dtype=float),
    )


def _toy_problem() -> SorsLinearProblem:
    # Three independently rounded publications:
    # x -> 6, y -> 5, x+y -> 10.  Their integer representatives do not add up,
    # although the publication intervals are mutually feasible.
    rows = [[(0, 1.0)], [(1, 1.0)], [(0, 1.0), (1, 1.0)]]
    centers = [6.0, 5.0, 10.0]
    expressions = [
        (np.asarray([0], dtype=np.int32), np.asarray([1.0])),
        (np.asarray([1], dtype=np.int32), np.asarray([1.0])),
        (np.asarray([0, 1], dtype=np.int32), np.asarray([1.0, 1.0])),
    ]
    constraints = []
    for index, (center, (indices, coefficients)) in enumerate(zip(centers, expressions, strict=True)):
        constraints.append(
            {
                'constraint_id': f'c{index}',
                'published_center': center,
                'published_representative_status': 'STABLE',
                'expression_indices': indices,
                'expression_coefficients': coefficients,
            }
        )
    return SorsLinearProblem(
        model_layer='STRICT',
        matrix=_csr(rows, 2),
        row_lower=np.asarray([5.5, 4.5, 9.5]),
        row_upper=np.asarray([6.5, 5.5, 10.5]),
        col_lower=np.asarray([0.0, 0.0]),
        col_upper=np.asarray([np.inf, np.inf]),
        objective=np.zeros(2),
        constraints_grid=pd.DataFrame(constraints),
        variables_grid=pd.DataFrame({'quantity_id': ['x', 'y']}),
    )


def test_rounding_distortion_builds_linf_model_and_recovers_one_third_million() -> None:
    strict = _toy_problem()
    distortion, tau_objective, l1_objective = build_rounding_distortion_problem(strict)

    assert distortion.num_variables == 6  # x, y, 3 abs residuals, tau
    assert distortion.num_constraints == 12  # 3 strict + 3 constraints per residual
    assert distortion.metadata['distortion_variable_count'] == 3
    assert np.count_nonzero(tau_objective) == 1
    assert np.count_nonzero(l1_objective) == 3

    # Analytic optimum for the toy system.  Let e1=x-6, e2=y-5 and
    # e3=x+y-10.  Then e1+e2-e3=-1, so if |ei|<=tau we must have
    # 3*tau>=1.  The witness x=17/3, y=14/3 gives residuals
    # (-1/3, -1/3, +1/3), hence tau*=1/3 exactly.
    tau_star = 1.0 / 3.0
    witness = np.asarray([17.0 / 3.0, 14.0 / 3.0])
    residuals = np.asarray([
        witness[0] - 6.0,
        witness[1] - 5.0,
        witness.sum() - 10.0,
    ])
    assert np.max(np.abs(residuals)) == pytest.approx(tau_star, abs=1e-12)
    assert abs(float(residuals[0] + residuals[1] - residuals[2])) == pytest.approx(1.0)

    # Independently solve the augmented matrix through SciPy HiGHS.  Production
    # code intentionally uses highspy directly; this test is only a second
    # implementation of the toy mathematics so matrix-sign mistakes are caught.
    from scipy.optimize import linprog
    from scipy.sparse import csr_matrix, vstack

    matrix = csr_matrix(
        (distortion.matrix.data, distortion.matrix.indices, distortion.matrix.indptr),
        shape=distortion.matrix.shape,
    )
    a_ub = []
    b_ub = []
    for row in range(distortion.num_constraints):
        vector = matrix.getrow(row)
        if np.isfinite(distortion.row_upper[row]):
            a_ub.append(vector)
            b_ub.append(float(distortion.row_upper[row]))
        if np.isfinite(distortion.row_lower[row]):
            a_ub.append(-vector)
            b_ub.append(float(-distortion.row_lower[row]))
    result = linprog(
        tau_objective,
        A_ub=vstack(a_ub),
        b_ub=np.asarray(b_ub),
        bounds=list(zip(distortion.col_lower, distortion.col_upper, strict=True)),
        method='highs',
    )
    assert result.success
    assert float(result.fun) == pytest.approx(tau_star, abs=1e-9)


# Imported late to keep the fixture focused on model construction above.
import pytest
