from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsCellResolutionConfig
from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import SorsLinearProblem
from stratbox.macrobanks.cbr_sors_restoration.linear.highs import (
    HighsSession,
    SolveResult,
    SorsSolverDependencyError,
)


@dataclass(frozen=True)
class StrictFeasibilityExecution:
    feasibility: SolveResult
    solver_runs_grid: pd.DataFrame
    backend: str
    version: str
    status: str


def _unavailable_result(exc: Exception) -> SolveResult:
    return SolveResult(
        success=False,
        status='SOLVER_UNAVAILABLE',
        raw_status=str(exc),
        objective_value=None,
        values=None,
        runtime_seconds=0.0,
        simplex_iterations=None,
        ipm_iterations=None,
    )


def run_strict_feasibility(
    problem: SorsLinearProblem,
    config: SorsCellResolutionConfig,
) -> StrictFeasibilityExecution:
    try:
        with HighsSession(
            problem,
            time_limit_seconds=config.per_solve_time_limit_seconds,
            threads=config.threads,
        ) as session:
            feasibility = session.solve_feasibility()
            backend = session.backend
            version = session.version
    except SorsSolverDependencyError as exc:
        feasibility = _unavailable_result(exc)
        backend = 'highspy'
        version = 'unavailable'
    record = {
        'solve_id': 'strict:feasibility',
        'model_layer': 'STRICT',
        'target_id': None,
        'direction': 'FEASIBILITY',
        'attempt_number': 1,
        'status': feasibility.status,
        'raw_status': feasibility.raw_status,
        'objective_value': feasibility.objective_value,
        'runtime_seconds': feasibility.runtime_seconds,
        'simplex_iterations': feasibility.simplex_iterations,
        'ipm_iterations': feasibility.ipm_iterations,
        'time_limit_seconds': config.per_solve_time_limit_seconds,
        'basis_reused': False,
        'solver_backend': backend,
        'solver_version': version,
        'subsystem_variables': problem.num_variables,
        'subsystem_constraints': problem.num_constraints,
        'subsystem_nnz': problem.matrix.nnz,
    }
    return StrictFeasibilityExecution(
        feasibility=feasibility,
        solver_runs_grid=pd.DataFrame([record]),
        backend=backend,
        version=version,
        status=feasibility.status,
    )
