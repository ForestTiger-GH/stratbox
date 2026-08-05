from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsCertificationConfig
from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import SorsLinearProblem
from stratbox.macrobanks.cbr_sors_restoration.linear.highs import (
    HighsSession,
    SolveResult,
    SorsSolverDependencyError,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import linear_target_from_row


@dataclass(frozen=True)
class StrictSolveExecution:
    feasibility: SolveResult
    target_results: dict[str, tuple[SolveResult, SolveResult]]
    solver_runs_grid: pd.DataFrame
    backend: str
    version: str
    status: str


@dataclass(frozen=True)
class StrictTargetBatchExecution:
    target_results: dict[str, tuple[SolveResult, SolveResult]]
    solver_runs_grid: pd.DataFrame
    backend: str
    version: str
    elapsed_seconds: float


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


def _run_record(
    *,
    solve_id: str,
    model_instance_id: str,
    batch_id: str,
    target_id: str | None,
    direction: str,
    attempt_number: int,
    result: SolveResult,
    time_limit_seconds: float | None,
    basis_reused: bool,
    backend: str,
    version: str,
    model_reset_reason: str | None = None,
) -> dict[str, object]:
    return {
        'solve_id': solve_id,
        'model_layer': 'STRICT',
        'batch_id': batch_id,
        'model_instance_id': model_instance_id,
        'target_id': target_id,
        'direction': direction,
        'attempt_number': attempt_number,
        'status': result.status,
        'raw_status': result.raw_status,
        'objective_value': result.objective_value,
        'runtime_seconds': result.runtime_seconds,
        'simplex_iterations': result.simplex_iterations,
        'ipm_iterations': result.ipm_iterations,
        'time_limit_seconds': time_limit_seconds,
        'basis_reused': basis_reused,
        'model_reset_reason': model_reset_reason,
        'solver_backend': backend,
        'solver_version': version,
    }


def run_strict_feasibility(
    problem: SorsLinearProblem,
    config: SorsCertificationConfig,
) -> StrictSolveExecution:
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
    record = _run_record(
        solve_id='strict:feasibility',
        model_instance_id='strict:model:feasibility',
        batch_id='feasibility',
        target_id=None,
        direction='FEASIBILITY',
        attempt_number=1,
        result=feasibility,
        time_limit_seconds=config.per_solve_time_limit_seconds,
        basis_reused=False,
        backend=backend,
        version=version,
    )
    return StrictSolveExecution(
        feasibility=feasibility,
        target_results={},
        solver_runs_grid=pd.DataFrame([record]),
        backend=backend,
        version=version,
        status=feasibility.status,
    )


def run_strict_target_batch(
    problem: SorsLinearProblem,
    target_catalog_grid: pd.DataFrame,
    selected_plan_grid: pd.DataFrame,
    config: SorsCertificationConfig,
    *,
    batch_sequence: int,
) -> StrictTargetBatchExecution:
    selected = selected_plan_grid.sort_values('selection_order', kind='stable')
    catalog = target_catalog_grid.set_index('target_id')
    target_results: dict[str, tuple[SolveResult, SolveResult]] = {}
    records: list[dict[str, object]] = []
    started = perf_counter()
    session: HighsSession | None = None
    session_target_count = 0
    model_sequence = 0
    backend = 'highspy'
    version = 'unknown'

    def new_session(reason: str | None) -> tuple[HighsSession, str]:
        nonlocal model_sequence, session_target_count, backend, version
        model_sequence += 1
        session_target_count = 0
        created = HighsSession(
            problem,
            time_limit_seconds=config.per_solve_time_limit_seconds,
            threads=config.threads,
        )
        backend = created.backend
        version = created.version
        return created, reason or 'BATCH_START'

    try:
        reset_reason: str | None = 'BATCH_START'
        for plan_row in selected.itertuples(index=False):
            if (
                config.batch_time_limit_seconds is not None
                and perf_counter() - started >= config.batch_time_limit_seconds
            ):
                break
            if session is None or session_target_count >= config.model_reset_interval:
                if session is not None:
                    session.close()
                session, reset_reason = new_session(
                    'RESET_INTERVAL' if model_sequence else 'BATCH_START'
                )
            target = linear_target_from_row(catalog.loc[str(plan_row.target_id)])
            model_id = f'strict:model:b{batch_sequence:04d}:m{model_sequence:04d}'
            batch_id = f'batch:{batch_sequence:04d}'
            lower = session.solve_target(target, maximize=False)
            records.append(
                _run_record(
                    solve_id=f'strict:min:{target.target_id}:attempt1',
                    model_instance_id=model_id,
                    batch_id=batch_id,
                    target_id=target.target_id,
                    direction='MIN',
                    attempt_number=1,
                    result=lower,
                    time_limit_seconds=config.per_solve_time_limit_seconds,
                    basis_reused=session_target_count > 0,
                    backend=backend,
                    version=version,
                    model_reset_reason=reset_reason,
                )
            )
            reset_reason = None
            upper = session.solve_target(target, maximize=True)
            records.append(
                _run_record(
                    solve_id=f'strict:max:{target.target_id}:attempt1',
                    model_instance_id=model_id,
                    batch_id=batch_id,
                    target_id=target.target_id,
                    direction='MAX',
                    attempt_number=1,
                    result=upper,
                    time_limit_seconds=config.per_solve_time_limit_seconds,
                    basis_reused=True,
                    backend=backend,
                    version=version,
                )
            )
            session_target_count += 1
            if config.retry_failed_solve and not (lower.success and upper.success):
                session.close()
                session, _ = new_session('FAILED_SOLVE_RETRY')
                model_id = f'strict:model:b{batch_sequence:04d}:m{model_sequence:04d}'
                lower = session.solve_target(target, maximize=False)
                records.append(
                    _run_record(
                        solve_id=f'strict:min:{target.target_id}:attempt2',
                        model_instance_id=model_id,
                        batch_id=batch_id,
                        target_id=target.target_id,
                        direction='MIN',
                        attempt_number=2,
                        result=lower,
                        time_limit_seconds=config.per_solve_time_limit_seconds,
                        basis_reused=False,
                        backend=backend,
                        version=version,
                        model_reset_reason='FAILED_SOLVE_RETRY',
                    )
                )
                upper = session.solve_target(target, maximize=True)
                records.append(
                    _run_record(
                        solve_id=f'strict:max:{target.target_id}:attempt2',
                        model_instance_id=model_id,
                        batch_id=batch_id,
                        target_id=target.target_id,
                        direction='MAX',
                        attempt_number=2,
                        result=upper,
                        time_limit_seconds=config.per_solve_time_limit_seconds,
                        basis_reused=True,
                        backend=backend,
                        version=version,
                    )
                )
                session_target_count = 1
            target_results[target.target_id] = (lower, upper)
    except SorsSolverDependencyError as exc:
        backend = 'highspy'
        version = 'unavailable'
        unavailable = _unavailable_result(exc)
        for plan_row in selected.itertuples(index=False):
            target_id = str(plan_row.target_id)
            if target_id not in target_results:
                target_results[target_id] = (unavailable, unavailable)
    finally:
        if session is not None:
            session.close()

    return StrictTargetBatchExecution(
        target_results=target_results,
        solver_runs_grid=pd.DataFrame(records),
        backend=backend,
        version=version,
        elapsed_seconds=perf_counter() - started,
    )


def run_strict_solver(
    problem: SorsLinearProblem,
    target_catalog_grid: pd.DataFrame,
    certification_plan_grid: pd.DataFrame,
    config: SorsCertificationConfig,
) -> StrictSolveExecution:
    """Convenience one-shot executor.

    Production orchestration uses ``run_strict_feasibility`` followed by bounded
    target batches and closure between batches. This helper remains useful for
    focused tests and small target scopes.
    """
    feasibility = run_strict_feasibility(problem, config)
    if not feasibility.feasibility.success:
        return feasibility
    selected = certification_plan_grid[
        certification_plan_grid['selected'].astype(bool)
    ].head(config.batch_size)
    batch = run_strict_target_batch(
        problem,
        target_catalog_grid,
        selected,
        config,
        batch_sequence=1,
    )
    return StrictSolveExecution(
        feasibility=feasibility.feasibility,
        target_results=batch.target_results,
        solver_runs_grid=pd.concat(
            [feasibility.solver_runs_grid, batch.solver_runs_grid],
            ignore_index=True,
            sort=False,
        ),
        backend=batch.backend,
        version=batch.version,
        status='OPTIMAL',
    )


def apply_lp_bounds(
    quantities_grid: pd.DataFrame,
    target_catalog_grid: pd.DataFrame,
    target_results: dict[str, tuple[SolveResult, SolveResult]],
    *,
    point_tolerance: float,
) -> pd.DataFrame:
    out = quantities_grid.copy()
    for column in ('lp_lower_solve_id', 'lp_upper_solve_id', 'lp_status'):
        if column not in out.columns:
            out[column] = None
    position = {
        quantity_id: index
        for index, quantity_id in enumerate(out['quantity_id'].astype(str))
    }
    catalog = target_catalog_grid.set_index('target_id')
    for target_id, (lower_result, upper_result) in target_results.items():
        target = catalog.loc[target_id]
        index = position[str(target.quantity_id)]
        if lower_result.success and lower_result.objective_value is not None:
            value = float(lower_result.objective_value)
            if value > float(out.at[index, 'lower_bound']) + point_tolerance:
                out.at[index, 'lower_bound'] = value
                out.at[index, 'lower_attained'] = False
            out.at[index, 'lp_lower_solve_id'] = f'strict:min:{target_id}'
        if upper_result.success and upper_result.objective_value is not None:
            value = float(upper_result.objective_value)
            if value < float(out.at[index, 'upper_bound']) - point_tolerance:
                out.at[index, 'upper_bound'] = value
                out.at[index, 'upper_attained'] = False
            out.at[index, 'lp_upper_solve_id'] = f'strict:max:{target_id}'
        if lower_result.success and upper_result.success:
            width = float(out.at[index, 'upper_bound']) - float(out.at[index, 'lower_bound'])
            if width <= point_tolerance:
                midpoint = (
                    float(out.at[index, 'upper_bound'])
                    + float(out.at[index, 'lower_bound'])
                ) / 2.0
                out.at[index, 'lower_bound'] = midpoint
                out.at[index, 'upper_bound'] = midpoint
                out.at[index, 'lower_attained'] = True
                out.at[index, 'upper_attained'] = True
                out.at[index, 'lp_status'] = 'POINT_IDENTIFIED'
            else:
                out.at[index, 'lp_status'] = 'BOUNDED'
        else:
            out.at[index, 'lp_status'] = 'SOLVER_INCOMPLETE'
    return out
