from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from stratbox.macrobanks.cbr_sors_restoration.problem import LinearTarget, SorsProblem


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
            'unsupported because they are binary-version dependent.'
        ) from exc
    return Highs, HighsLp, HighsSparseMatrix, MatrixFormat, ObjSense, HighsModelStatus


@dataclass(frozen=True, slots=True)
class SolveResult:
    success: bool
    status: str
    objective_value: float | None
    values: np.ndarray | None
    runtime_seconds: float | None


@dataclass(frozen=True)
class RestorationSolveBatch:
    backend: str
    version: str
    strict_feasibility: SolveResult
    strict_targets: dict[str, tuple[SolveResult, SolveResult]]
    bridge_optimum: SolveResult | None
    bridge_targets: dict[str, tuple[SolveResult, SolveResult]]


class ReusableHighsModel:
    def __init__(self, problem: SorsProblem, *, time_limit: float | None, threads: int):
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
        if time_limit is not None:
            self.highs.setOptionValue('time_limit', float(time_limit))
        matrix = problem.matrix
        lp = HighsLp()
        lp.num_col_ = problem.num_variables
        lp.num_row_ = matrix.shape[0]
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
        sparse.num_row_ = matrix.shape[0]
        sparse.format_ = MatrixFormat.kRowwise
        sparse.start_ = matrix.indptr.astype(np.int64)
        sparse.index_ = matrix.indices.astype(np.int32)
        sparse.value_ = matrix.data.astype(float)
        lp.a_matrix_ = sparse
        lp.sense_ = ObjSense.kMinimize
        status = self.highs.passModel(lp)
        if 'kOk' not in str(status):
            raise RuntimeError(f'HiGHS rejected SORS model: {status}')
        self.n = problem.num_variables
        self.current_cost = np.zeros(self.n, dtype=float)
        self.version = str(self.highs.version())

    def _set_cost(self, indices: np.ndarray, coefficients: np.ndarray) -> None:
        desired = np.zeros(self.n, dtype=float)
        desired[np.asarray(indices, dtype=np.int64)] = np.asarray(
            coefficients, dtype=float
        )
        changed = np.flatnonzero(np.abs(desired - self.current_cost) > 0)
        if len(changed):
            self.highs.changeColsCost(
                int(len(changed)),
                changed.astype(np.int32),
                desired[changed].astype(float),
            )
        self.current_cost = desired

    def solve_vector(
        self,
        indices: np.ndarray,
        coefficients: np.ndarray,
        *,
        maximize: bool = False,
    ) -> SolveResult:
        coefficients = np.asarray(coefficients, dtype=float)
        effective = -coefficients if maximize else coefficients
        self._set_cost(np.asarray(indices, dtype=np.int32), effective)
        self.highs.changeObjectiveSense(self._ObjSense.kMinimize)
        self.highs.run()
        model_status = self.highs.getModelStatus()
        success = model_status == self._HighsModelStatus.kOptimal
        objective = float(self.highs.getObjectiveValue()) if success else None
        if success and maximize and objective is not None:
            objective = -objective
        values = (
            np.asarray(self.highs.getSolution().col_value, dtype=float)
            if success else None
        )
        return SolveResult(
            success=success,
            status=str(model_status),
            objective_value=objective,
            values=values,
            runtime_seconds=float(self.highs.getRunTime()),
        )

    def solve_objective(self, objective: np.ndarray) -> SolveResult:
        ids = np.flatnonzero(np.asarray(objective) != 0).astype(np.int32)
        return self.solve_vector(ids, np.asarray(objective, dtype=float)[ids])

    def solve_feasibility(self) -> SolveResult:
        return self.solve_vector(
            np.asarray([], dtype=np.int32), np.asarray([], dtype=float)
        )

    def add_objective_cap(self, objective: np.ndarray, upper: float) -> None:
        ids = np.flatnonzero(np.asarray(objective) != 0).astype(np.int32)
        values = np.asarray(objective, dtype=float)[ids]
        status = self.highs.addRow(
            -1e30, float(upper), int(len(ids)), ids, values
        )
        if 'kOk' not in str(status):
            raise RuntimeError(f'HiGHS rejected bridge objective cap: {status}')

    def minmax_target(self, target: LinearTarget) -> tuple[SolveResult, SolveResult]:
        lower = self.solve_vector(
            target.indices, target.coefficients, maximize=False
        )
        upper = self.solve_vector(
            target.indices, target.coefficients, maximize=True
        )
        return lower, upper

    def close(self) -> None:
        self.highs = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def _solve_targets(
    model: ReusableHighsModel,
    targets: list[LinearTarget],
) -> dict[str, tuple[SolveResult, SolveResult]]:
    results: dict[str, tuple[SolveResult, SolveResult]] = {}
    for target in targets:
        results[target.target_id] = model.minmax_target(target)
    return results


def solve_restoration_batch(
    strict_problem: SorsProblem,
    strict_targets: list[LinearTarget],
    *,
    bridge_problem: SorsProblem | None,
    bridge_targets: list[LinearTarget],
    bridge_objective_tolerance: float,
    time_limit: float | None,
    threads: int,
) -> RestorationSolveBatch:
    """Run strict and conditional certification in one deterministic process.

    Bridge target bounds are calculated over *all* solutions whose total
    off-preferred-edge mass is within ``bridge_objective_tolerance`` of the
    global minimum. No selected bridge profile is fixed and no shortcut is used.
    """
    with ReusableHighsModel(
        strict_problem, time_limit=time_limit, threads=threads
    ) as strict_model:
        strict_feasibility = strict_model.solve_feasibility()
        strict_results = (
            _solve_targets(strict_model, strict_targets)
            if strict_feasibility.success else {}
        )
        backend = strict_model.backend
        version = strict_model.version

    bridge_optimum: SolveResult | None = None
    bridge_results: dict[str, tuple[SolveResult, SolveResult]] = {}
    if bridge_problem is not None:
        with ReusableHighsModel(
            bridge_problem, time_limit=time_limit, threads=threads
        ) as bridge_model:
            bridge_optimum = bridge_model.solve_objective(bridge_problem.objective)
            backend = bridge_model.backend
            version = bridge_model.version
            if bridge_optimum.success and bridge_optimum.objective_value is not None:
                cap = (
                    float(bridge_optimum.objective_value)
                    + float(bridge_objective_tolerance)
                )
                bridge_model.add_objective_cap(bridge_problem.objective, cap)
                bridge_results = _solve_targets(bridge_model, bridge_targets)

    return RestorationSolveBatch(
        backend=backend,
        version=version,
        strict_feasibility=strict_feasibility,
        strict_targets=strict_results,
        bridge_optimum=bridge_optimum,
        bridge_targets=bridge_results,
    )
