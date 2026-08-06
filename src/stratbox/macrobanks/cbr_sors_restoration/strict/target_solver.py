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


@dataclass(frozen=True)
class _SessionLease:
    session: HighsSession
    reused: bool
    pooled: bool
    solver: str


class SorsCellSolverPool:
    """Reuse structurally identical global RKVS models across target proofs.

    Local horizons remain short-lived because their projected matrices vary by
    target. GLOBAL_CONNECTED subsystems usually share one connected-component
    matrix; retaining that model avoids repeated matrix loading and lets HiGHS
    reuse its internal state when only objective coefficients and bounds change.
    """

    def __init__(self, config: SorsCellResolutionConfig) -> None:
        self.config = config
        self._global_sessions: dict[
            tuple[str, tuple[int, ...], tuple[int, ...]], HighsSession
        ] = {}

    def _new_session(self, subsystem: SorsTargetSubsystem, solver: str) -> HighsSession:
        return HighsSession(
            subsystem.problem,
            time_limit_seconds=self.config.per_solve_time_limit_seconds,
            threads=self.config.threads,
            solver=solver,
            run_crossover=self.config.run_crossover,
        )

    @staticmethod
    def _session_key(
        subsystem: SorsTargetSubsystem,
        solver: str,
    ) -> tuple[str, tuple[int, ...], tuple[int, ...]]:
        return (
            solver,
            subsystem.original_solver_rows,
            subsystem.original_solver_columns,
        )

    def acquire_primary(self, subsystem: SorsTargetSubsystem) -> _SessionLease:
        solver = (
            self.config.global_solver
            if subsystem.horizon == 'GLOBAL_CONNECTED'
            else self.config.local_solver
        )
        pooled = bool(
            self.config.reuse_global_session
            and subsystem.horizon == 'GLOBAL_CONNECTED'
        )
        if not pooled:
            return _SessionLease(
                session=self._new_session(subsystem, solver),
                reused=False,
                pooled=False,
                solver=solver,
            )
        key = self._session_key(subsystem, solver)
        session = self._global_sessions.get(key)
        if session is None:
            session = self._new_session(subsystem, solver)
            self._global_sessions[key] = session
            reused = False
        else:
            try:
                session.update_column_bounds(
                    subsystem.problem.col_lower,
                    subsystem.problem.col_upper,
                )
                reused = True
            except Exception:
                session.close()
                session = self._new_session(subsystem, solver)
                self._global_sessions[key] = session
                reused = False
        return _SessionLease(
            session=session,
            reused=reused,
            pooled=True,
            solver=solver,
        )

    def invalidate_primary(
        self,
        subsystem: SorsTargetSubsystem,
        solver: str,
    ) -> None:
        key = self._session_key(subsystem, solver)
        session = self._global_sessions.pop(key, None)
        if session is not None:
            session.close()

    def new_retry_session(self, subsystem: SorsTargetSubsystem) -> _SessionLease:
        return _SessionLease(
            session=self._new_session(subsystem, self.config.retry_solver),
            reused=False,
            pooled=False,
            solver=self.config.retry_solver,
        )

    def close(self) -> None:
        for session in self._global_sessions.values():
            session.close()
        self._global_sessions.clear()

    def __enter__(self) -> 'SorsCellSolverPool':
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.close()
        return False


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
    session_reused: bool,
    solver_algorithm: str,
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
        'session_reused': session_reused,
        'solver_algorithm': solver_algorithm,
        'solver_backend': backend,
        'solver_version': version,
        'subsystem_variables': subsystem.problem.num_variables,
        'subsystem_constraints': subsystem.problem.num_constraints,
        'subsystem_nnz': subsystem.problem.matrix.nnz,
    }


def _solve_direction(
    lease: _SessionLease,
    subsystem: SorsTargetSubsystem,
    *,
    maximize: bool,
) -> SolveResult:
    return lease.session.solve_target(subsystem.target, maximize=maximize)


def prove_cell_uniqueness(
    subsystem: SorsTargetSubsystem,
    config: SorsCellResolutionConfig,
    policy: RoundingPolicy,
    *,
    point_tolerance: float,
    attempt_id: str,
    solver_pool: SorsCellSolverPool | None = None,
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
        for solve_id, direction, result in (
            (lower_solve_id, 'MIN_INTERNAL_UNIQUENESS', lower),
            (upper_solve_id, 'MAX_INTERNAL_UNIQUENESS', upper),
        ):
            records.append(
                _run_record(
                    solve_id=solve_id,
                    attempt_id=attempt_id,
                    subsystem=subsystem,
                    direction=direction,
                    result=result,
                    attempt_number=0,
                    backend=backend,
                    version=version,
                    basis_reused=False,
                    session_reused=False,
                    solver_algorithm='bounds',
                    time_limit_seconds=None,
                )
            )
    else:
        owned_pool = solver_pool is None
        pool = solver_pool or SorsCellSolverPool(config)
        primary: _SessionLease | None = None
        try:
            primary = pool.acquire_primary(subsystem)
            backend = primary.session.backend
            version = primary.session.version
            lower_solve_id = f'{attempt_id}:{subsystem.horizon}:min:attempt1'
            upper_solve_id = f'{attempt_id}:{subsystem.horizon}:max:attempt1'
            lower = _solve_direction(primary, subsystem, maximize=False)
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
                    basis_reused=primary.reused,
                    session_reused=primary.reused,
                    solver_algorithm=primary.solver,
                    time_limit_seconds=config.per_solve_time_limit_seconds,
                )
            )
            upper = _solve_direction(primary, subsystem, maximize=True)
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
                    basis_reused=lower.success,
                    session_reused=True,
                    solver_algorithm=primary.solver,
                    time_limit_seconds=config.per_solve_time_limit_seconds,
                )
            )

            if not (lower.success and upper.success) and primary.pooled:
                pool.invalidate_primary(subsystem, primary.solver)

            if config.retry_failed_solve and not (lower.success and upper.success):
                retry = pool.new_retry_session(subsystem)
                retry_lower_solved = False
                try:
                    backend = retry.session.backend
                    version = retry.session.version
                    if not lower.success:
                        lower_solve_id = (
                            f'{attempt_id}:{subsystem.horizon}:min:attempt2'
                        )
                        lower = _solve_direction(retry, subsystem, maximize=False)
                        retry_lower_solved = lower.success
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
                                session_reused=False,
                                solver_algorithm=retry.solver,
                                time_limit_seconds=config.per_solve_time_limit_seconds,
                            )
                        )
                    if not upper.success:
                        upper_solve_id = (
                            f'{attempt_id}:{subsystem.horizon}:max:attempt2'
                        )
                        upper = _solve_direction(retry, subsystem, maximize=True)
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
                                basis_reused=retry_lower_solved,
                                session_reused=retry_lower_solved,
                                solver_algorithm=retry.solver,
                                time_limit_seconds=config.per_solve_time_limit_seconds,
                            )
                        )
                finally:
                    retry.session.close()
        except SorsSolverDependencyError as exc:
            backend = 'highspy'
            version = 'unavailable'
            lower_solve_id = f'{attempt_id}:{subsystem.horizon}:min:unavailable'
            upper_solve_id = f'{attempt_id}:{subsystem.horizon}:max:unavailable'
            lower = _unavailable_result(exc)
            upper = _unavailable_result(exc)
            for solve_id, direction, result in (
                (lower_solve_id, 'MIN_INTERNAL_UNIQUENESS', lower),
                (upper_solve_id, 'MAX_INTERNAL_UNIQUENESS', upper),
            ):
                records.append(
                    _run_record(
                        solve_id=solve_id,
                        attempt_id=attempt_id,
                        subsystem=subsystem,
                        direction=direction,
                        result=result,
                        attempt_number=0,
                        backend=backend,
                        version=version,
                        basis_reused=False,
                        session_reused=False,
                        solver_algorithm='unavailable',
                        time_limit_seconds=config.per_solve_time_limit_seconds,
                    )
                )
        finally:
            if primary is not None and not primary.pooled:
                primary.session.close()
            if owned_pool:
                pool.close()

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
