from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from stratbox.macrobanks.cbr_sors_restoration.problem import CsrMatrixData
from stratbox.macrobanks.cbr_sors_restoration.solver import ReusableHighsModel


@dataclass(frozen=True)
class WorkerProblem:
    matrix: CsrMatrixData
    row_lower: np.ndarray
    row_upper: np.ndarray
    col_lower: np.ndarray
    col_upper: np.ndarray

    @property
    def num_variables(self) -> int:
        return int(len(self.col_lower))


def main() -> None:
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    maximize = sys.argv[3] == '1'
    time_limit = None if sys.argv[4] == 'none' else float(sys.argv[4])
    threads = int(sys.argv[5])
    with np.load(source, allow_pickle=False) as data:
        problem = WorkerProblem(
            matrix=CsrMatrixData(
                shape=(int(data['n_rows']), int(data['n_cols'])),
                indptr=data['indptr'],
                indices=data['indices'],
                data=data['matrix_data'],
            ),
            row_lower=data['row_lower'],
            row_upper=data['row_upper'],
            col_lower=data['col_lower'],
            col_upper=data['col_upper'],
        )
        indices = data['objective_indices']
        coefficients = data['objective_coefficients']
    model = ReusableHighsModel(problem, time_limit=time_limit, threads=threads)
    result = model.solve_vector(indices, coefficients, maximize=maximize)
    np.savez(
        target,
        success=np.asarray([1 if result.success else 0], dtype=np.int8),
        status=np.asarray([result.status]),
        objective=np.asarray([
            np.nan if result.objective_value is None else result.objective_value
        ], dtype=float),
        values=(
            np.asarray([], dtype=float)
            if result.values is None
            else np.asarray(result.values, dtype=float)
        ),
        runtime=np.asarray([
            np.nan if result.runtime_seconds is None else result.runtime_seconds
        ], dtype=float),
        backend=np.asarray([model.backend]),
        version=np.asarray([model.version]),
    )
    # The SciPy-internal HiGHS wrapper may deadlock during interpreter shutdown.
    # Files are closed at this point; hard exit is intentional for this worker only.
    os._exit(0)


if __name__ == '__main__':
    main()
