from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import numpy as np

from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import (
    LinearTarget,
    SorsLinearProblem,
)


class SorsSolverDependencyError(ImportError):
    pass


def _load_highs():
    try:
        from highspy import (
            Highs,
            HighsLp,
            HighsModelStatus,
            HighsSparseMatrix,
            MatrixFormat,
            ObjSense,
        )
    except Exception as exc:
        raise SorsSolverDependencyError(
            'SORS restoration requires the official HiGHS Python package. '
            'Install stratbox with the sors-restoration extra or install '
            'highspy>=1.11,<2. SciPy internal HiGHS bindings are intentionally '
            'unsupported.'
        ) from exc
    return Highs, HighsLp, HighsSparseMatrix, MatrixFormat, ObjSense, HighsModelStatus


def normalize_highs_status(raw_status: object) -> str:
    text = str(raw_status)
    if 'kOptimal' in text:
        return 'OPTIMAL'
    if 'kInfeasible' in text:
        return 'INFEASIBLE'
    if 'kTimeLimit' in text:
        return 'TIME_LIMIT'
    if 'kIterationLimit' in text:
        return 'ITERATION_LIMIT'
    if 'kUnboundedOrInfeasible' in text:
        return 'UNBOUNDED_OR_INFEASIBLE'
    if 'kUnbounded' in text:
        return 'UNBOUNDED'
    if 'kObjectiveBound' in text or 'kObjectiveTarget' in text:
        return 'OBJECTIVE_LIMIT'
    if 'kModelError' in text or 'kSolveError' in text:
        return 'ERROR'
    return 'UNKNOWN'


@dataclass(frozen=True, slots=True)
class SolveResult:
    success: bool
    status: str
    raw_status: str
    objective_value: float | None
    values: np.ndarray | None
    runtime_seconds: float
    simplex_iterations: int | None
    ipm_iterations: int | None


class HighsSession:
    def __init__(
        self,
        problem: SorsLinearProblem,
        *,
        time_limit_seconds: float | None,
        threads: int,
    ) -> None:
        (
            Highs,
            HighsLp,
            HighsSparseMatrix,
            MatrixFormat,
            ObjSense,
            HighsModelStatus,
        ) = _load_highs()
        self._ObjSense = ObjSense
        self._HighsModelStatus = HighsModelStatus
        self.backend = 'highspy'
        self.highs = Highs()
        self.highs.setOptionValue('output_flag', False)
        self.highs.setOptionValue('threads', int(threads))
        self.highs.setOptionValue('presolve', 'on')
        self.highs.setOptionValue('solver', 'simplex')
        self.highs.setOptionValue('random_seed', 0)
        if time_limit_seconds is not None:
            self.highs.setOptionValue('time_limit', float(time_limit_seconds))
        matrix = problem.matrix
        lp = HighsLp()
        lp.num_col_ = problem.num_variables
        lp.num_row_ = problem.num_constraints
        lp.col_cost_ = np.zeros(problem.num_variables, dtype=float)
        lp.col_lower_ = problem.col_lower.astype(float)
        lp.col_upper_ = np.where(
            np.isfinite(problem.col_upper), problem.col_upper, 1e30
        ).astype(float)
        lp.row_lower_ = np.where(
            np.isfinite(problem.row_lower), problem.row_lower, -1e30
        ).astype(float)
        lp.row_upper_ = np.where(
            np.isfinite(problem.row_upper), problem.row_upper, 1e30
        ).astype(float)
        sparse = HighsSparseMatrix()
        sparse.num_col_ = problem.num_variables
        sparse.num_row_ = problem.num_constraints
        sparse.format_ = MatrixFormat.kRowwise
        sparse.start_ = matrix.indptr.astype(np.int64)
        sparse.index_ = matrix.indices.astype(np.int32)
        sparse.value_ = matrix.data.astype(float)
        lp.a_matrix_ = sparse
        lp.sense_ = ObjSense.kMinimize
        status = self.highs.passModel(lp)
        if 'kOk' not in str(status):
            raise RuntimeError(f'HiGHS rejected SORS model: {status}')
        self.version = str(self.highs.version())
        self._current_indices = np.asarray([], dtype=np.int32)

    def _set_cost(self, indices: np.ndarray, coefficients: np.ndarray) -> None:
        indices = np.asarray(indices, dtype=np.int32)
        coefficients = np.asarray(coefficients, dtype=float)
        if len(self._current_indices):
            self.highs.changeColsCost(
                int(len(self._current_indices)),
                self._current_indices,
                np.zeros(len(self._current_indices), dtype=float),
            )
        if len(indices):
            self.highs.changeColsCost(int(len(indices)), indices, coefficients)
        self._current_indices = indices.copy()

    def solve_vector(
        self,
        indices: np.ndarray,
        coefficients: np.ndarray,
        *,
        maximize: bool = False,
        constant: float = 0.0,
        include_values: bool = False,
    ) -> SolveResult:
        coefficients = np.asarray(coefficients, dtype=float)
        effective = -coefficients if maximize else coefficients
        self._set_cost(np.asarray(indices, dtype=np.int32), effective)
        self.highs.changeObjectiveSense(self._ObjSense.kMinimize)
        started = perf_counter()
        self.highs.run()
        runtime = perf_counter() - started
        raw_status = self.highs.getModelStatus()
        status = normalize_highs_status(raw_status)
        success = status == 'OPTIMAL'
        objective = float(self.highs.getObjectiveValue()) if success else None
        if objective is not None:
            if maximize:
                objective = -objective
            objective += float(constant)
        values = None
        if success and include_values:
            values = np.asarray(self.highs.getSolution().col_value, dtype=float)
        simplex_iterations = None
        ipm_iterations = None
        try:
            info = self.highs.getInfo()
            simplex_iterations = int(getattr(info, 'simplex_iteration_count', 0))
            ipm_iterations = int(getattr(info, 'ipm_iteration_count', 0))
        except Exception:
            pass
        return SolveResult(
            success=success,
            status=status,
            raw_status=str(raw_status),
            objective_value=objective,
            values=values,
            runtime_seconds=float(runtime),
            simplex_iterations=simplex_iterations,
            ipm_iterations=ipm_iterations,
        )

    def solve_target(
        self,
        target: LinearTarget,
        *,
        maximize: bool,
        include_values: bool = False,
    ) -> SolveResult:
        return self.solve_vector(
            target.indices,
            target.coefficients,
            maximize=maximize,
            constant=target.constant,
            include_values=include_values,
        )

    def solve_objective(
        self,
        objective: np.ndarray,
        *,
        include_values: bool = False,
    ) -> SolveResult:
        objective = np.asarray(objective, dtype=float)
        indices = np.flatnonzero(objective != 0).astype(np.int32)
        return self.solve_vector(
            indices,
            objective[indices],
            include_values=include_values,
        )

    def solve_feasibility(self) -> SolveResult:
        return self.solve_vector(
            np.asarray([], dtype=np.int32),
            np.asarray([], dtype=float),
        )

    def add_objective_cap(self, objective: np.ndarray, upper: float) -> None:
        objective = np.asarray(objective, dtype=float)
        indices = np.flatnonzero(objective != 0).astype(np.int32)
        values = objective[indices]
        status = self.highs.addRow(-1e30, float(upper), len(indices), indices, values)
        if 'kOk' not in str(status):
            raise RuntimeError(f'HiGHS rejected objective cap: {status}')

    def close(self) -> None:
        self.highs = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
