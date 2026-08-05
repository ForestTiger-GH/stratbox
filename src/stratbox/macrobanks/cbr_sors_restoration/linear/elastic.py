from __future__ import annotations

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import (
    CsrMatrixData,
    SorsLinearProblem,
)
from stratbox.macrobanks.cbr_sors_restoration.linear.highs import HighsSession


def _rows_from_csr(problem: SorsLinearProblem) -> list[list[tuple[int, float]]]:
    rows: list[list[tuple[int, float]]] = []
    matrix = problem.matrix
    for row in range(matrix.shape[0]):
        start, end = int(matrix.indptr[row]), int(matrix.indptr[row + 1])
        rows.append(
            [
                (int(column), float(value))
                for column, value in zip(
                    matrix.indices[start:end], matrix.data[start:end], strict=True
                )
            ]
        )
    return rows


def _csr(rows: list[list[tuple[int, float]]], n_columns: int) -> CsrMatrixData:
    starts = [0]
    indices: list[int] = []
    data: list[float] = []
    for row in rows:
        for column, value in sorted(row):
            indices.append(column)
            data.append(value)
        starts.append(len(indices))
    return CsrMatrixData(
        shape=(len(rows), n_columns),
        indptr=np.asarray(starts, dtype=np.int64),
        indices=np.asarray(indices, dtype=np.int32),
        data=np.asarray(data, dtype=float),
    )


def diagnose_infeasibility(
    problem: SorsLinearProblem,
    *,
    time_limit_seconds: float | None,
    threads: int,
    tolerance: float = 1e-7,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    base_rows = _rows_from_csr(problem)
    n, m = problem.num_variables, problem.num_constraints

    epsilon_column = n
    common_rows: list[list[tuple[int, float]]] = []
    common_lower: list[float] = []
    common_upper: list[float] = []
    for row, lower, upper in zip(
        base_rows, problem.row_lower, problem.row_upper, strict=True
    ):
        common_rows.append(row + [(epsilon_column, 1.0)])
        common_lower.append(float(lower))
        common_upper.append(np.inf)
        common_rows.append(row + [(epsilon_column, -1.0)])
        common_lower.append(-np.inf)
        common_upper.append(float(upper))
    common_objective = np.zeros(n + 1, dtype=float)
    common_objective[epsilon_column] = 1.0
    common_problem = SorsLinearProblem(
        model_layer='STRICT_CONFLICT_COMMON_EPSILON',
        matrix=_csr(common_rows, n + 1),
        row_lower=np.asarray(common_lower, dtype=float),
        row_upper=np.asarray(common_upper, dtype=float),
        col_lower=np.concatenate((problem.col_lower, [0.0])),
        col_upper=np.concatenate((problem.col_upper, [np.inf])),
        objective=common_objective,
        constraints_grid=pd.DataFrame(),
        variables_grid=pd.DataFrame(),
    )
    solve_rows: list[dict[str, object]] = []
    with HighsSession(
        common_problem,
        time_limit_seconds=time_limit_seconds,
        threads=threads,
    ) as session:
        common = session.solve_objective(common_objective, include_values=True)
        solve_rows.append(
            {
                'solve_id': 'strict:conflict:common_epsilon',
                'model_layer': common_problem.model_layer,
                'status': common.status,
                'objective_value': common.objective_value,
                'runtime_seconds': common.runtime_seconds,
                'solver_backend': session.backend,
                'solver_version': session.version,
            }
        )
    if not common.success or common.objective_value is None:
        return pd.DataFrame(), pd.DataFrame(solve_rows)
    epsilon = float(common.objective_value)

    local_rows: list[list[tuple[int, float]]] = []
    local_lower: list[float] = []
    local_upper: list[float] = []
    for row_number, (row, lower, upper) in enumerate(
        zip(base_rows, problem.row_lower, problem.row_upper, strict=True)
    ):
        lower_slack = n + row_number
        upper_slack = n + m + row_number
        local_rows.append(row + [(lower_slack, 1.0)])
        local_lower.append(float(lower))
        local_upper.append(np.inf)
        local_rows.append(row + [(upper_slack, -1.0)])
        local_lower.append(-np.inf)
        local_upper.append(float(upper))
    local_objective = np.zeros(n + 2 * m, dtype=float)
    local_objective[n:] = 1.0
    local_problem = SorsLinearProblem(
        model_layer='STRICT_CONFLICT_LOCAL_SLACK',
        matrix=_csr(local_rows, n + 2 * m),
        row_lower=np.asarray(local_lower, dtype=float),
        row_upper=np.asarray(local_upper, dtype=float),
        col_lower=np.concatenate((problem.col_lower, np.zeros(2 * m))),
        col_upper=np.concatenate(
            (
                problem.col_upper,
                np.full(2 * m, epsilon + tolerance, dtype=float),
            )
        ),
        objective=local_objective,
        constraints_grid=pd.DataFrame(),
        variables_grid=pd.DataFrame(),
    )
    with HighsSession(
        local_problem,
        time_limit_seconds=time_limit_seconds,
        threads=threads,
    ) as session:
        local = session.solve_objective(local_objective, include_values=True)
        solve_rows.append(
            {
                'solve_id': 'strict:conflict:local_slacks',
                'model_layer': local_problem.model_layer,
                'status': local.status,
                'objective_value': local.objective_value,
                'runtime_seconds': local.runtime_seconds,
                'solver_backend': session.backend,
                'solver_version': session.version,
            }
        )
    if not local.success or local.values is None:
        return pd.DataFrame(), pd.DataFrame(solve_rows)
    lower_slacks = local.values[n : n + m]
    upper_slacks = local.values[n + m :]
    constraints = problem.constraints_grid[
        problem.constraints_grid['constraint_status'].eq('ACTIVE')
    ].sort_values('solver_row')
    conflict_rows: list[dict[str, object]] = []
    for position, row in enumerate(constraints.itertuples(index=False)):
        lower_slack = float(lower_slacks[position])
        upper_slack = float(upper_slacks[position])
        if lower_slack <= tolerance and upper_slack <= tolerance:
            continue
        conflict_rows.append(
            {
                'conflict_id': f'strict:conflict:{row.constraint_id}',
                'constraint_id': row.constraint_id,
                'quantity_id': row.quantity_id,
                'source_observation_ids': row.source_observation_ids,
                'source_series': row.source_series,
                'original_lower': row.lower_bound,
                'original_upper': row.upper_bound,
                'minimum_common_epsilon': epsilon,
                'required_lower_expansion': lower_slack,
                'required_upper_expansion': upper_slack,
                'total_violation': lower_slack + upper_slack,
                'conflict_status': 'ACTIVE_CONFLICT',
                'message': 'Official interval requires expansion for global feasibility',
            }
        )
    return pd.DataFrame(conflict_rows), pd.DataFrame(solve_rows)
