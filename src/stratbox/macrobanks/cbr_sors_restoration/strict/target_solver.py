from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsCellResolutionConfig
from stratbox.macrobanks.cbr_sors_restoration.linear.highs import (
    HighsSession,
    SolveResult,
    SorsSolverDependencyError,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.strict.subsystem import (
    SorsTargetSubsystem,
)


@dataclass(frozen=True)
class SorsCellProof:
    target_id: str
    quantity_id: str
    subsystem_id: str
    horizon: str
    status: str
    lower_result: SolveResult
    upper_result: SolveResult
    lower_bound: float | None
    upper_bound: float | None
    unique_value: float | None
    value_precision: str
    proof_ids: tuple[str, ...]
    supporting_constraint_ids: tuple[str, ...]
    solver_runs_grid: pd.DataFrame

    @property
    def complete(self) -> bool:
        return self.lower_result.success and self.upper_result.success

    @property
    def identified(self) -> bool:
        return self.unique_value is not None


def _result_from_bound(value: float, direction: str) -> SolveResult:
    return SolveResult(
        success=True,
        status='BOUNDS_ONLY',
        raw_status=direction,
        objective_value=float(value),
        values=None,
        runtime_seconds=0.0,
        simplex_iterations=0,
        ipm_iterations=0,
    )


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
    attempt_id: str,
    subsystem: SorsTargetSubsystem,
    direction: str,
    result: SolveResult,
    attempt_number: int,
    backend: str,
    version: str,
    basis_reused: bool,
    time_limit_seconds: float | None,
) -> dict[str, object]:
    return {
        'solve_id': solve_id,
        'model_layer': 'STRICT_CELL',
        'attempt_id': attempt_id,
        'subsystem_id': subsystem.subsystem_id,
        'target_id': subsystem.target_id,
        'quantity_id': subsystem.target.quantity_id,
        'horizon': subsystem.horizon,
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
        'solver_backend': backend,
        'solver_version': version,
        'subsystem_variables': subsystem.problem.num_variables,
        'subsystem_constraints': subsystem.problem.num_constraints,
        'subsystem_nnz': subsystem.problem.matrix.nnz,
    }


def prove_cell_uniqueness(
    subsystem: SorsTargetSubsystem,
    config: SorsCellResolutionConfig,
    policy: RoundingPolicy,
    *,
    point_tolerance: float,
    attempt_id: str,
) -> SorsCellProof:
    records: list[dict[str, object]] = []
    backend = 'column_bounds'
    version = 'n/a'
    lower_solve_id = f'{attempt_id}:{subsystem.horizon}:min:bounds'
    upper_solve_id = f'{attempt_id}:{subsystem.horizon}:max:bounds'
    if subsystem.problem.num_constraints == 0:
        index = int(subsystem.target.indices[0])
        lower = _result_from_bound(
            float(subsystem.problem.col_lower[index]), 'LOWER_BOUND'
        )
        upper = _result_from_bound(
            float(subsystem.problem.col_upper[index]), 'UPPER_BOUND'
        )
        records.extend(
            [
                _run_record(
                    solve_id=lower_solve_id,
                    attempt_id=attempt_id,
                    subsystem=subsystem,
                    direction='MIN_INTERNAL_UNIQUENESS',
                    result=lower,
                    attempt_number=0,
                    backend=backend,
                    version=version,
                    basis_reused=False,
                    time_limit_seconds=None,
                ),
                _run_record(
                    solve_id=upper_solve_id,
                    attempt_id=attempt_id,
                    subsystem=subsystem,
                    direction='MAX_INTERNAL_UNIQUENESS',
                    result=upper,
                    attempt_number=0,
                    backend=backend,
                    version=version,
                    basis_reused=False,
                    time_limit_seconds=None,
                ),
            ]
        )
    else:
        session: HighsSession | None = None
        try:
            session = HighsSession(
                subsystem.problem,
                time_limit_seconds=config.per_solve_time_limit_seconds,
                threads=config.threads,
            )
            backend = session.backend
            version = session.version
            lower_solve_id = f'{attempt_id}:{subsystem.horizon}:min:attempt1'
            upper_solve_id = f'{attempt_id}:{subsystem.horizon}:max:attempt1'
            lower = session.solve_target(subsystem.target, maximize=False)
            records.append(
                _run_record(
                    solve_id=lower_solve_id,
                    attempt_id=attempt_id,
                    subsystem=subsystem,
                    direction='MIN_INTERNAL_UNIQUENESS',
                    result=lower,
                    attempt_number=1,
                    backend=backend,
                    version=version,
                    basis_reused=False,
                    time_limit_seconds=config.per_solve_time_limit_seconds,
                )
            )
            upper = session.solve_target(subsystem.target, maximize=True)
            records.append(
                _run_record(
                    solve_id=upper_solve_id,
                    attempt_id=attempt_id,
                    subsystem=subsystem,
                    direction='MAX_INTERNAL_UNIQUENESS',
                    result=upper,
                    attempt_number=1,
                    backend=backend,
                    version=version,
                    basis_reused=True,
                    time_limit_seconds=config.per_solve_time_limit_seconds,
                )
            )
            if config.retry_failed_solve and not (lower.success and upper.success):
                session.close()
                session = HighsSession(
                    subsystem.problem,
                    time_limit_seconds=config.per_solve_time_limit_seconds,
                    threads=config.threads,
                )
                backend = session.backend
                version = session.version
                lower_solve_id = f'{attempt_id}:{subsystem.horizon}:min:attempt2'
                upper_solve_id = f'{attempt_id}:{subsystem.horizon}:max:attempt2'
                lower = session.solve_target(subsystem.target, maximize=False)
                records.append(
                    _run_record(
                        solve_id=lower_solve_id,
                        attempt_id=attempt_id,
                        subsystem=subsystem,
                        direction='MIN_INTERNAL_UNIQUENESS',
                        result=lower,
                        attempt_number=2,
                        backend=backend,
                        version=version,
                        basis_reused=False,
                        time_limit_seconds=config.per_solve_time_limit_seconds,
                    )
                )
                upper = session.solve_target(subsystem.target, maximize=True)
                records.append(
                    _run_record(
                        solve_id=upper_solve_id,
                        attempt_id=attempt_id,
                        subsystem=subsystem,
                        direction='MAX_INTERNAL_UNIQUENESS',
                        result=upper,
                        attempt_number=2,
                        backend=backend,
                        version=version,
                        basis_reused=True,
                        time_limit_seconds=config.per_solve_time_limit_seconds,
                    )
                )
        except SorsSolverDependencyError as exc:
            backend = 'highspy'
            version = 'unavailable'
            lower_solve_id = f'{attempt_id}:{subsystem.horizon}:min:unavailable'
            upper_solve_id = f'{attempt_id}:{subsystem.horizon}:max:unavailable'
            lower = _unavailable_result(exc)
            upper = _unavailable_result(exc)
            records.extend(
                [
                    _run_record(
                        solve_id=lower_solve_id,
                        attempt_id=attempt_id,
                        subsystem=subsystem,
                        direction='MIN_INTERNAL_UNIQUENESS',
                        result=lower,
                        attempt_number=0,
                        backend=backend,
                        version=version,
                        basis_reused=False,
                        time_limit_seconds=config.per_solve_time_limit_seconds,
                    ),
                    _run_record(
                        solve_id=upper_solve_id,
                        attempt_id=attempt_id,
                        subsystem=subsystem,
                        direction='MAX_INTERNAL_UNIQUENESS',
                        result=upper,
                        attempt_number=0,
                        backend=backend,
                        version=version,
                        basis_reused=False,
                        time_limit_seconds=config.per_solve_time_limit_seconds,
                    ),
                ]
            )
        finally:
            if session is not None:
                session.close()

    lower_value = lower.objective_value if lower.success else None
    upper_value = upper.objective_value if upper.success else None
    unique_value: float | None = None
    value_precision = 'NONE'
    status = 'SOLVER_INCOMPLETE'
    if lower_value is not None and upper_value is not None:
        lower_value = float(lower_value)
        upper_value = float(upper_value)
        if upper_value - lower_value <= point_tolerance:
            unique_value = (lower_value + upper_value) / 2.0
            value_precision = 'EXACT'
            status = 'UNIQUE_FEASIBLE_VALUE'
        elif config.accept_published_bucket:
            bucket = policy.single_bucket(
                lower_value,
                upper_value,
                lower_attained=True,
                upper_attained=True,
            )
            if bucket is not None:
                unique_value = bucket
                value_precision = 'PUBLISHED'
                status = 'UNIQUE_AT_PUBLISHED_PRECISION'
            else:
                status = 'MULTIPLE_FEASIBLE_VALUES'
        else:
            status = 'MULTIPLE_FEASIBLE_VALUES'
    return SorsCellProof(
        target_id=subsystem.target_id,
        quantity_id=subsystem.target.quantity_id,
        subsystem_id=subsystem.subsystem_id,
        horizon=subsystem.horizon,
        status=status,
        lower_result=lower,
        upper_result=upper,
        lower_bound=lower_value,
        upper_bound=upper_value,
        unique_value=unique_value,
        value_precision=value_precision,
        proof_ids=(lower_solve_id, upper_solve_id),
        supporting_constraint_ids=subsystem.supporting_constraint_ids,
        solver_runs_grid=pd.DataFrame(records),
    )


def apply_cell_proof(
    quantities_grid: pd.DataFrame,
    proof: SorsCellProof,
    *,
    point_tolerance: float,
    attempt_id: str,
) -> tuple[pd.DataFrame, bool]:
    out = quantities_grid.copy()
    for column in (
        'cell_lower_solve_id',
        'cell_upper_solve_id',
        'cell_resolution_status',
        'cell_largest_horizon',
        'cell_attempt_id',
        'cell_subsystem_id',
    ):
        if column not in out:
            out[column] = None
    matches = out['quantity_id'].astype(str).eq(proof.quantity_id)
    if matches.sum() != 1:
        raise ValueError(f'Unknown or duplicate RKVS quantity {proof.quantity_id!r}')
    index = int(out.index[matches][0])
    previous = (
        float(out.at[index, 'lower_bound']),
        float(out.at[index, 'upper_bound']),
    )
    if proof.lower_bound is not None:
        out.at[index, 'lower_bound'] = max(previous[0], float(proof.lower_bound))
        out.at[index, 'lower_attained'] = True
        out.at[index, 'cell_lower_solve_id'] = proof.proof_ids[0]
    if proof.upper_bound is not None:
        out.at[index, 'upper_bound'] = min(previous[1], float(proof.upper_bound))
        out.at[index, 'upper_attained'] = True
        out.at[index, 'cell_upper_solve_id'] = proof.proof_ids[1]
    if proof.status == 'UNIQUE_FEASIBLE_VALUE' and proof.unique_value is not None:
        value = float(proof.unique_value)
        out.at[index, 'lower_bound'] = value
        out.at[index, 'upper_bound'] = value
        out.at[index, 'lower_attained'] = True
        out.at[index, 'upper_attained'] = True
    out.at[index, 'cell_resolution_status'] = proof.status
    out.at[index, 'cell_largest_horizon'] = proof.horizon
    out.at[index, 'cell_attempt_id'] = attempt_id
    out.at[index, 'cell_subsystem_id'] = proof.subsystem_id
    changed = (
        float(out.at[index, 'lower_bound']) > previous[0] + point_tolerance
        or float(out.at[index, 'upper_bound']) < previous[1] - point_tolerance
        or proof.identified
    )
    return out, bool(changed)
