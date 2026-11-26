from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CsrMatrixData:
    shape: tuple[int, int]
    indptr: np.ndarray
    indices: np.ndarray
    data: np.ndarray

    @property
    def nnz(self) -> int:
        return int(len(self.data))


@dataclass(frozen=True, slots=True)
class LinearTarget:
    target_id: str
    quantity_id: str
    region_code: str
    region_name: str
    class_code: str
    metric: str
    indices: np.ndarray
    coefficients: np.ndarray
    constant: float = 0.0


@dataclass(frozen=True)
class SorsLinearProblem:
    model_layer: str
    matrix: CsrMatrixData
    row_lower: np.ndarray
    row_upper: np.ndarray
    col_lower: np.ndarray
    col_upper: np.ndarray
    objective: np.ndarray
    constraints_grid: pd.DataFrame
    variables_grid: pd.DataFrame
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def num_variables(self) -> int:
        return int(len(self.col_lower))

    @property
    def num_constraints(self) -> int:
        return int(len(self.row_lower))
