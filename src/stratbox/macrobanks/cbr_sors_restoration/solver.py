from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from stratbox.macrobanks.cbr_sors_restoration.problem import LinearTarget, SorsProblem


class SorsSolverDependencyError(ImportError):
    pass


def _load_highs():
    try:
        from highspy import Highs, HighsLp, HighsSparseMatrix, MatrixFormat, ObjSense, HighsModelStatus
        return Highs, HighsLp, HighsSparseMatrix, MatrixFormat, ObjSense, HighsModelStatus, 'highspy'
    except Exception:
        try:
            from scipy.optimize._highspy._core import (
                _Highs as Highs,
                HighsLp,
                HighsSparseMatrix,
                MatrixFormat,
                ObjSense,
                HighsModelStatus,
            )
            return Highs, HighsLp, HighsSparseMatrix, MatrixFormat, ObjSense, HighsModelStatus, 'scipy-internal-highs'
        except Exception as exc:
            raise SorsSolverDependencyError(
                'SORS restoration solver backend is unavailable. Install stratbox with '
                'the sors-restoration extra or install highspy>=1.11.'
            ) from exc


@dataclass(frozen=True, slots=True)
class SolveResult:
    success: bool
    status: str
    objective_value: float | None
    values: np.ndarray | None
    runtime_seconds: float | None


class ReusableHighsModel:
    def __init__(self, problem: SorsProblem, *, time_limit: float | None, threads: int):
        Highs, HighsLp, HighsSparseMatrix, MatrixFormat, ObjSense, HighsModelStatus, backend = _load_highs()
        self._ObjSense = ObjSense
        self._HighsModelStatus = HighsModelStatus
        self.backend = backend
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
        lp.col_upper_ = np.where(np.isfinite(problem.col_upper), problem.col_upper, 1e30).astype(float)
        lp.row_lower_ = np.where(np.isfinite(problem.row_lower), problem.row_lower, -1e30).astype(float)
        lp.row_upper_ = np.where(np.isfinite(problem.row_upper), problem.row_upper, 1e30).astype(float)
        sparse = HighsSparseMatrix()
        sparse.num_col_ = problem.num_variables
        sparse.num_row_ = matrix.shape[0]
        sparse.format_ = MatrixFormat.kRowwise
        sparse.start_ = matrix.indptr.astype(np.int32)
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
        desired[np.asarray(indices, dtype=np.int64)] = np.asarray(coefficients, dtype=float)
        changed = np.flatnonzero(np.abs(desired - self.current_cost) > 0)
        if len(changed):
            self.highs.changeColsCost(
                int(len(changed)),
                changed.astype(np.int32),
                desired[changed].astype(float),
            )
        self.current_cost = desired

    def solve_vector(self, indices: np.ndarray, coefficients: np.ndarray, *, maximize: bool = False) -> SolveResult:
        coeff = -np.asarray(coefficients, dtype=float) if maximize else np.asarray(coefficients, dtype=float)
        self._set_cost(np.asarray(indices, dtype=np.int32), coeff)
        self.highs.changeObjectiveSense(self._ObjSense.kMinimize)
        self.highs.run()
        model_status = self.highs.getModelStatus()
        success = model_status == self._HighsModelStatus.kOptimal
        objective = float(self.highs.getObjectiveValue()) if success else None
        if success and maximize and objective is not None:
            objective = -objective
        values = np.asarray(self.highs.getSolution().col_value, dtype=float) if success else None
        runtime = float(self.highs.getRunTime())
        return SolveResult(success, str(model_status), objective, values, runtime)

    def solve_objective(self, objective: np.ndarray) -> SolveResult:
        ids = np.flatnonzero(np.asarray(objective) != 0).astype(np.int32)
        return self.solve_vector(ids, np.asarray(objective, dtype=float)[ids], maximize=False)

    def solve_feasibility(self) -> SolveResult:
        return self.solve_vector(np.asarray([], dtype=np.int32), np.asarray([], dtype=float))

    def add_objective_cap(self, objective: np.ndarray, upper: float) -> None:
        ids = np.flatnonzero(np.asarray(objective) != 0).astype(np.int32)
        values = np.asarray(objective, dtype=float)[ids]
        self.highs.addRow(-1e30, float(upper), int(len(ids)), ids, values)

    def minmax_target(self, target: LinearTarget) -> tuple[SolveResult, SolveResult]:
        lower = self.solve_vector(target.indices, target.coefficients, maximize=False)
        upper = self.solve_vector(target.indices, target.coefficients, maximize=True)
        return lower, upper

    def close(self) -> None:
        highs = getattr(self, 'highs', None)
        if highs is None:
            return
        try:
            highs.resetGlobalScheduler(True)
        except Exception:
            pass
        self.highs = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def _isolated_worker(problem, indices, coefficients, maximize, time_limit, threads, connection) -> None:
    try:
        model = ReusableHighsModel(problem, time_limit=time_limit, threads=threads)
        result = model.solve_vector(indices, coefficients, maximize=maximize)
        connection.send((result, model.backend, model.version, None))
    except BaseException as exc:  # pragma: no cover - defensive process boundary
        connection.send((None, None, None, repr(exc)))
    finally:
        connection.close()


def solve_cold(
    problem: SorsProblem,
    indices: np.ndarray,
    coefficients: np.ndarray,
    *,
    maximize: bool,
    time_limit: float | None,
    threads: int,
) -> tuple[SolveResult, str, str]:
    """Solve one objective in a clean backend state."""
    try:
        import highspy  # noqa: F401
    except Exception:
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory(prefix='stratbox-sors-highs-') as tmp:
            source = Path(tmp) / 'problem.npz'
            target = Path(tmp) / 'result.npz'
            np.savez(
                source,
                n_rows=np.asarray(problem.matrix.shape[0], dtype=np.int64),
                n_cols=np.asarray(problem.matrix.shape[1], dtype=np.int64),
                indptr=problem.matrix.indptr,
                indices=problem.matrix.indices,
                matrix_data=problem.matrix.data,
                row_lower=problem.row_lower,
                row_upper=problem.row_upper,
                col_lower=problem.col_lower,
                col_upper=problem.col_upper,
                objective_indices=np.asarray(indices, dtype=np.int32),
                objective_coefficients=np.asarray(coefficients, dtype=float),
            )
            command = [
                sys.executable,
                '-m',
                'stratbox.macrobanks.cbr_sors_restoration.solver_worker',
                str(source),
                str(target),
                '1' if maximize else '0',
                'none' if time_limit is None else str(float(time_limit)),
                str(int(threads)),
            ]
            hard_timeout = None if time_limit is None else max(float(time_limit) + 30.0, 60.0)
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=hard_timeout,
                check=False,
            )
            if completed.returncode != 0 or not target.exists():
                stderr = completed.stderr.decode(errors='replace')[-4000:]
                raise RuntimeError(
                    f'Isolated SORS HiGHS worker failed with code '
                    f'{completed.returncode}: {stderr}'
                )
            with np.load(target, allow_pickle=False) as data:
                success = bool(int(data['success'][0]))
                objective = float(data['objective'][0])
                runtime = float(data['runtime'][0])
                values = np.asarray(data['values'], dtype=float)
                result = SolveResult(
                    success=success,
                    status=str(data['status'][0]),
                    objective_value=None if np.isnan(objective) else objective,
                    values=None if values.size == 0 else values,
                    runtime_seconds=None if np.isnan(runtime) else runtime,
                )
                return result, str(data['backend'][0]), str(data['version'][0])
    model = ReusableHighsModel(problem, time_limit=time_limit, threads=threads)
    result = model.solve_vector(indices, coefficients, maximize=maximize)
    backend = model.backend
    version = model.version
    model.close()
    return result, backend, version


def solve_cold_objective(
    problem: SorsProblem,
    objective: np.ndarray,
    *,
    time_limit: float | None,
    threads: int,
) -> tuple[SolveResult, str, str]:
    ids = np.flatnonzero(np.asarray(objective) != 0).astype(np.int32)
    return solve_cold(
        problem,
        ids,
        np.asarray(objective, dtype=float)[ids],
        maximize=False,
        time_limit=time_limit,
        threads=threads,
    )


def solve_cold_feasibility(
    problem: SorsProblem,
    *,
    time_limit: float | None,
    threads: int,
) -> tuple[SolveResult, str, str]:
    return solve_cold(
        problem,
        np.asarray([], dtype=np.int32),
        np.asarray([], dtype=float),
        maximize=False,
        time_limit=time_limit,
        threads=threads,
    )


def _isolated_minmax_worker(problem, indices, coefficients, time_limit, threads, connection) -> None:
    try:
        model = ReusableHighsModel(problem, time_limit=time_limit, threads=threads)
        lower = model.solve_vector(indices, coefficients, maximize=False)
        backend = model.backend
        version = model.version
        model = ReusableHighsModel(problem, time_limit=time_limit, threads=threads)
        upper = model.solve_vector(indices, coefficients, maximize=True)
        connection.send((lower, upper, backend, version, None))
    except BaseException as exc:  # pragma: no cover - process boundary
        connection.send((None, None, None, None, repr(exc)))
    finally:
        connection.close()


def solve_cold_minmax(
    problem: SorsProblem,
    indices: np.ndarray,
    coefficients: np.ndarray,
    *,
    time_limit: float | None,
    threads: int,
) -> tuple[SolveResult, SolveResult, str, str]:
    lower, backend, version = solve_cold(
        problem,
        indices,
        coefficients,
        maximize=False,
        time_limit=time_limit,
        threads=threads,
    )
    upper, _, _ = solve_cold(
        problem,
        indices,
        coefficients,
        maximize=True,
        time_limit=time_limit,
        threads=threads,
    )
    return lower, upper, backend, version



def solve_restoration_batch(
    problem: SorsProblem,
    targets: list[LinearTarget],
    *,
    profile_targets: list[LinearTarget] | None = None,
    profile_tolerance: float,
    time_limit: float | None,
    threads: int,
):
    """Solve the complete one-pass certification batch.

    The external highspy backend can operate in-process, but this batch worker is
    also used as the deterministic compatibility path for notebook environments.
    """
    import os
    import pickle
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory(prefix='stratbox-sors-batch-') as tmp:
        source = Path(tmp) / 'batch.pkl'
        target = Path(tmp) / 'result.pkl'
        with source.open('wb') as stream:
            pickle.dump(
                {
                    'problem': problem,
                    'targets': targets,
                    'profile_targets': targets if profile_targets is None else profile_targets,
                    'profile_tolerance': float(profile_tolerance),
                    'time_limit': time_limit,
                    'threads': int(threads),
                },
                stream,
                protocol=pickle.HIGHEST_PROTOCOL,
            )
        command = [
            sys.executable,
            '-m',
            'stratbox.macrobanks.cbr_sors_restoration.solver_batch_worker',
            str(source),
            str(target),
        ]
        # One bridge solve plus four solves per target.
        per_solve = 300.0 if time_limit is None else float(time_limit)
        hard_timeout = max(per_solve * (1 + 4 * max(len(targets), 1)) + 60.0, 180.0)
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=hard_timeout,
            check=False,
            env=os.environ.copy(),
        )
        if completed.returncode != 0 or not target.exists():
            stderr = completed.stderr.decode(errors='replace')[-6000:]
            raise RuntimeError(
                f'SORS batch solver failed with code {completed.returncode}: {stderr}'
            )
        with target.open('rb') as stream:
            return pickle.load(stream)
