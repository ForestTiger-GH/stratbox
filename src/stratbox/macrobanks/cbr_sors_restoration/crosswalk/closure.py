from __future__ import annotations

from dataclasses import dataclass, replace
from math import inf

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import SorsLinearProblem


class CrosswalkClosureConflictError(ValueError):
    def __init__(self, conflicts_grid: pd.DataFrame):
        super().__init__('Crosswalk interval closure found an empty feasible interval')
        self.conflicts_grid = conflicts_grid


@dataclass(frozen=True)
class CrosswalkClosureResult:
    problem: SorsLinearProblem
    derivations_grid: pd.DataFrame
    passes: int
    bound_updates: int
    converged: bool


def close_crosswalk_bounds(
    problem: SorsLinearProblem,
    *,
    tolerance: float,
    max_passes: int = 50,
) -> CrosswalkClosureResult:
    """Propagate non-negative sum constraints into variable bounds.

    Crosswalk rows contain only positive coefficients. For every row
    ``L <= sum(a_i*x_i) <= U`` the function applies residual lower/upper rules
    until a fixed point. The result is an outer bound: accepting a target from
    these bounds is safe, while a wide bound remains unresolved.
    """
    matrix = problem.matrix
    lower = problem.col_lower.astype(float).copy()
    upper = problem.col_upper.astype(float).copy()
    derivations: list[dict[str, object]] = []
    updates = 0
    conflicts: list[dict[str, object]] = []
    constraints = problem.constraints_grid.reset_index(drop=True)
    for pass_number in range(1, max_passes + 1):
        changed = False
        for row_index in range(problem.num_constraints):
            start = int(matrix.indptr[row_index])
            stop = int(matrix.indptr[row_index + 1])
            columns = matrix.indices[start:stop]
            coefficients = matrix.data[start:stop]
            if len(columns) == 0:
                continue
            if np.any(coefficients <= 0):
                raise ValueError(
                    'Crosswalk closure supports positive sum constraints only'
                )
            row_lower = float(problem.row_lower[row_index])
            row_upper = float(problem.row_upper[row_index])
            current_lower = lower[columns]
            current_upper = upper[columns]
            weighted_lower = coefficients * current_lower
            expression_lower = float(weighted_lower.sum())
            finite_upper = np.isfinite(current_upper)
            weighted_upper = coefficients[finite_upper] * current_upper[finite_upper]
            upper_inf_count = int((~finite_upper).sum())
            expression_upper = (
                inf if upper_inf_count else float(weighted_upper.sum())
            )
            constraint_id = (
                str(constraints.iloc[row_index].get('constraint_id', row_index))
                if row_index < len(constraints)
                else str(row_index)
            )
            if expression_lower > row_upper + tolerance or (
                np.isfinite(expression_upper)
                and expression_upper < row_lower - tolerance
            ):
                conflicts.append(
                    {
                        'conflict_id': f'crosswalk:closure:{constraint_id}',
                        'constraint_id': constraint_id,
                        'expression_lower': expression_lower,
                        'expression_upper': expression_upper,
                        'row_lower': row_lower,
                        'row_upper': row_upper,
                        'message': 'Constraint interval is empty under current bounds.',
                    }
                )
                continue

            if np.isfinite(row_upper):
                other_lower = expression_lower - weighted_lower
                candidates = np.maximum(
                    0.0,
                    (row_upper - other_lower) / coefficients,
                )
                improve = candidates < current_upper - tolerance
                if np.any(improve):
                    for local in np.flatnonzero(improve):
                        column = int(columns[local])
                        previous = float(upper[column])
                        upper[column] = float(candidates[local])
                        updates += 1
                        derivations.append(
                            {
                                'derivation_id': f'crosswalk-derivation:{updates:09d}',
                                'pass_number': pass_number,
                                'rule_id': 'SUM_UPPER_TO_VARIABLE_UPPER',
                                'constraint_id': constraint_id,
                                'solver_column': column,
                                'previous_lower': float(lower[column]),
                                'previous_upper': previous,
                                'new_lower': float(lower[column]),
                                'new_upper': float(upper[column]),
                            }
                        )
                    changed = True

            current_upper = upper[columns]
            finite_upper = np.isfinite(current_upper)
            upper_inf_count = int((~finite_upper).sum())
            if np.isfinite(row_lower):
                candidate_positions: np.ndarray
                if upper_inf_count == 0:
                    candidate_positions = np.arange(len(columns), dtype=np.int32)
                    expression_upper = float(
                        np.dot(coefficients, current_upper)
                    )
                elif upper_inf_count == 1:
                    candidate_positions = np.flatnonzero(~finite_upper).astype(np.int32)
                    expression_upper = inf
                else:
                    candidate_positions = np.asarray([], dtype=np.int32)
                    expression_upper = inf
                for local_raw in candidate_positions:
                    local = int(local_raw)
                    if upper_inf_count == 0:
                        other_upper = (
                            expression_upper
                            - float(coefficients[local] * current_upper[local])
                        )
                    else:
                        mask = np.ones(len(columns), dtype=bool)
                        mask[local] = False
                        other_upper = float(
                            np.dot(coefficients[mask], current_upper[mask])
                        )
                    candidate = max(
                        0.0,
                        (row_lower - other_upper) / float(coefficients[local]),
                    )
                    column = int(columns[local])
                    if candidate > lower[column] + tolerance:
                        previous = float(lower[column])
                        lower[column] = candidate
                        updates += 1
                        derivations.append(
                            {
                                'derivation_id': f'crosswalk-derivation:{updates:09d}',
                                'pass_number': pass_number,
                                'rule_id': 'SUM_LOWER_RESIDUAL_TO_VARIABLE_LOWER',
                                'constraint_id': constraint_id,
                                'solver_column': column,
                                'previous_lower': previous,
                                'previous_upper': float(upper[column]),
                                'new_lower': float(lower[column]),
                                'new_upper': float(upper[column]),
                            }
                        )
                        changed = True

            invalid = lower[columns] > upper[columns] + tolerance
            if np.any(invalid):
                for local in np.flatnonzero(invalid):
                    column = int(columns[int(local)])
                    conflicts.append(
                        {
                            'conflict_id': (
                                f'crosswalk:closure:{constraint_id}:{column}'
                            ),
                            'constraint_id': constraint_id,
                            'solver_column': column,
                            'lower_bound': float(lower[column]),
                            'upper_bound': float(upper[column]),
                            'message': 'Variable interval became empty during closure.',
                        }
                    )

        if conflicts:
            raise CrosswalkClosureConflictError(
                pd.DataFrame(conflicts).drop_duplicates('conflict_id')
            )
        if not changed:
            variables = problem.variables_grid.copy()
            variables['lower_bound'] = lower
            variables['upper_bound'] = upper
            return CrosswalkClosureResult(
                problem=replace(
                    problem,
                    col_lower=lower,
                    col_upper=upper,
                    variables_grid=variables,
                ),
                derivations_grid=pd.DataFrame(derivations),
                passes=pass_number,
                bound_updates=updates,
                converged=True,
            )
    raise RuntimeError(
        f'Crosswalk deterministic closure did not converge in {max_passes} passes'
    )
