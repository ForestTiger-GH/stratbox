from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsOptimizationConfig
from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import CsrMatrixData, SorsLinearProblem
from stratbox.macrobanks.cbr_sors_restoration.linear.highs import (
    HighsSession,
    SolveResult,
    SorsSolverDependencyError,
)


@dataclass(frozen=True)
class SorsRoundingProfile:
    problem: SorsLinearProblem
    tau_objective: np.ndarray
    l1_objective: np.ndarray
    tau_star: float | None
    l1_star: float | None
    benchmark_values: np.ndarray | None
    solver_runs_grid: pd.DataFrame
    backend: str | None
    version: str | None
    status: str


def _csr_rows(matrix: CsrMatrixData) -> list[list[tuple[int, float]]]:
    rows: list[list[tuple[int, float]]] = []
    for row in range(matrix.shape[0]):
        start, end = int(matrix.indptr[row]), int(matrix.indptr[row + 1])
        rows.append(
            [
                (int(column), float(value))
                for column, value in zip(matrix.indices[start:end], matrix.data[start:end], strict=True)
            ]
        )
    return rows


def _to_csr(rows: list[list[tuple[int, float]]], n_columns: int) -> CsrMatrixData:
    indptr = [0]
    indices: list[int] = []
    data: list[float] = []
    for row in rows:
        for column, coefficient in sorted(row):
            if coefficient == 0:
                continue
            indices.append(int(column))
            data.append(float(coefficient))
        indptr.append(len(indices))
    return CsrMatrixData(
        shape=(len(rows), n_columns),
        indptr=np.asarray(indptr, dtype=np.int64),
        indices=np.asarray(indices, dtype=np.int32),
        data=np.asarray(data, dtype=float),
    )


def build_rounding_distortion_problem(strict_problem: SorsLinearProblem) -> tuple[SorsLinearProblem, np.ndarray, np.ndarray]:
    constraints = strict_problem.constraints_grid
    eligible = constraints[
        constraints['published_center'].notna()
        & constraints['published_representative_status'].astype(str).eq('STABLE')
    ].copy()
    n = strict_problem.num_variables
    k = len(eligible)
    tau_index = n + k
    total_columns = n + k + 1

    rows = _csr_rows(strict_problem.matrix)
    row_lower = list(strict_problem.row_lower.astype(float))
    row_upper = list(strict_problem.row_upper.astype(float))
    meta: list[dict[str, object]] = [
        {'constraint_kind': 'STRICT_BASE', 'base_solver_row': i}
        for i in range(strict_problem.num_constraints)
    ]

    for local, item in enumerate(eligible.itertuples(index=False)):
        d_index = n + local
        indices = np.asarray(item.expression_indices, dtype=np.int32)
        coefficients = np.asarray(item.expression_coefficients, dtype=float)
        center = float(item.published_center)
        expression = [(int(i), float(c)) for i, c in zip(indices, coefficients, strict=True)]

        # A x - d <= center
        rows.append([*expression, (d_index, -1.0)])
        row_lower.append(-np.inf)
        row_upper.append(center)
        meta.append({'constraint_kind': 'ABS_POS', 'source_constraint_id': item.constraint_id})

        # -A x - d <= -center
        rows.append([*((int(i), -float(c)) for i, c in zip(indices, coefficients, strict=True)), (d_index, -1.0)])
        row_lower.append(-np.inf)
        row_upper.append(-center)
        meta.append({'constraint_kind': 'ABS_NEG', 'source_constraint_id': item.constraint_id})

        # d <= tau
        rows.append([(d_index, 1.0), (tau_index, -1.0)])
        row_lower.append(-np.inf)
        row_upper.append(0.0)
        meta.append({'constraint_kind': 'LINF_ENVELOPE', 'source_constraint_id': item.constraint_id})

    col_lower = np.concatenate([
        strict_problem.col_lower.astype(float),
        np.zeros(k + 1, dtype=float),
    ])
    col_upper = np.concatenate([
        strict_problem.col_upper.astype(float),
        np.full(k + 1, np.inf, dtype=float),
    ])
    tau_objective = np.zeros(total_columns, dtype=float)
    tau_objective[tau_index] = 1.0
    l1_objective = np.zeros(total_columns, dtype=float)
    if k:
        l1_objective[n:n+k] = 1.0
    problem = SorsLinearProblem(
        model_layer='ROUNDING_DISTORTION',
        matrix=_to_csr(rows, total_columns),
        row_lower=np.asarray(row_lower, dtype=float),
        row_upper=np.asarray(row_upper, dtype=float),
        col_lower=col_lower,
        col_upper=col_upper,
        objective=tau_objective,
        constraints_grid=pd.DataFrame(meta),
        variables_grid=strict_problem.variables_grid.copy(),
        metadata={
            **strict_problem.metadata,
            'base_variable_count': n,
            'distortion_variable_count': k,
            'tau_index': tau_index,
            'eligible_constraint_ids': tuple(eligible['constraint_id'].astype(str)),
        },
    )
    return problem, tau_objective, l1_objective


def _run_row(solve_id: str, direction: str, result: SolveResult, backend: str, version: str) -> dict[str, object]:
    return {
        'solve_id': solve_id,
        'model_layer': 'ROUNDING_DISTORTION',
        'direction': direction,
        'status': result.status,
        'raw_status': result.raw_status,
        'objective_value': result.objective_value,
        'runtime_seconds': result.runtime_seconds,
        'simplex_iterations': result.simplex_iterations,
        'ipm_iterations': result.ipm_iterations,
        'solver_backend': backend,
        'solver_version': version,
    }


def solve_rounding_profile(
    strict_problem: SorsLinearProblem,
    config: SorsOptimizationConfig,
    *,
    point_tolerance: float,
) -> SorsRoundingProfile:
    problem, tau_objective, l1_objective = build_rounding_distortion_problem(strict_problem)
    records: list[dict[str, object]] = []
    try:
        with HighsSession(
            problem,
            time_limit_seconds=config.per_solve_time_limit_seconds,
            threads=config.threads,
            solver=config.rounding_solver,
            run_crossover=config.run_crossover,
        ) as session:
            backend, version = session.backend, session.version
            tau = session.solve_objective(tau_objective)
            records.append(_run_row('rounding:linf', 'MIN_LINF', tau, backend, version))
            if not tau.success or tau.objective_value is None:
                return SorsRoundingProfile(problem, tau_objective, l1_objective, None, None, None, pd.DataFrame(records), backend, version, tau.status)
            tau_star = float(tau.objective_value)
            session.add_objective_cap(tau_objective, tau_star + point_tolerance)
            l1 = session.solve_objective(l1_objective, include_values=True)
            records.append(_run_row('rounding:l1', 'MIN_L1_GIVEN_LINF', l1, backend, version))
            if not l1.success or l1.objective_value is None:
                return SorsRoundingProfile(problem, tau_objective, l1_objective, tau_star, None, None, pd.DataFrame(records), backend, version, l1.status)
            return SorsRoundingProfile(
                problem=problem,
                tau_objective=tau_objective,
                l1_objective=l1_objective,
                tau_star=tau_star,
                l1_star=float(l1.objective_value),
                benchmark_values=l1.values,
                solver_runs_grid=pd.DataFrame(records),
                backend=backend,
                version=version,
                status='OPTIMAL',
            )
    except SorsSolverDependencyError as exc:
        return SorsRoundingProfile(
            problem=problem,
            tau_objective=tau_objective,
            l1_objective=l1_objective,
            tau_star=None,
            l1_star=None,
            benchmark_values=None,
            solver_runs_grid=pd.DataFrame([{
                'solve_id': 'rounding:solver_unavailable',
                'model_layer': 'ROUNDING_DISTORTION',
                'status': 'SOLVER_UNAVAILABLE',
                'raw_status': str(exc),
            }]),
            backend='highspy',
            version='unavailable',
            status='SOLVER_UNAVAILABLE',
        )


def configure_optimal_face_session(
    session: HighsSession,
    profile: SorsRoundingProfile,
    *,
    linf_extra: float,
    l1_extra: float,
) -> None:
    if profile.tau_star is None or profile.l1_star is None:
        raise ValueError('Rounding profile is not optimal')
    session.add_objective_cap(profile.tau_objective, profile.tau_star + float(linf_extra))
    session.add_objective_cap(profile.l1_objective, profile.l1_star + float(l1_extra))
