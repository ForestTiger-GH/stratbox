from __future__ import annotations

from dataclasses import dataclass, replace
from math import inf, isfinite

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsSourceBundle
from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import (
    CsrMatrixData,
    LinearTarget,
    SorsLinearProblem,
)
from stratbox.macrobanks.cbr_sors_restoration.metrics import METRIC_COMPONENTS
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    solver_lower_bound,
    solver_upper_bound,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.cells import (
    build_cell_target_catalog,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
    SorsQuantityGraph,
    component_quantity_id,
    metric_quantity_id,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.reduction import (
    assign_connected_components,
)


@dataclass(frozen=True)
class StrictCompilation:
    problem: SorsLinearProblem
    target_catalog_grid: pd.DataFrame
    cell_target_catalog_grid: pd.DataFrame


def _csr(rows: list[list[tuple[int, float]]], n_columns: int) -> CsrMatrixData:
    indptr = [0]
    indices: list[int] = []
    data: list[float] = []
    for row in rows:
        for column, coefficient in sorted(row):
            indices.append(int(column))
            data.append(float(coefficient))
        indptr.append(len(indices))
    return CsrMatrixData(
        shape=(len(rows), n_columns),
        indptr=np.asarray(indptr, dtype=np.int64),
        indices=np.asarray(indices, dtype=np.int32),
        data=np.asarray(data, dtype=float),
    )


def compile_strict_problem(
    bundle: SorsSourceBundle,
    graph: SorsQuantityGraph,
    quantities_grid: pd.DataFrame,
    *,
    point_tolerance: float,
) -> StrictCompilation:
    quantities = quantities_grid.set_index('quantity_id', drop=False)
    components = quantities[
        quantities['quantity_kind'].eq('ATOMIC_COMPONENT')
    ].sort_values(['region_code', 'class_code', 'component']).copy()
    fixed = (
        np.isfinite(components['upper_bound'].astype(float))
        & (
            components['upper_bound'].astype(float)
            - components['lower_bound'].astype(float)
        ).abs().le(point_tolerance)
        & components['lower_attained'].astype(bool)
        & components['upper_attained'].astype(bool)
    )
    components['is_fixed'] = fixed
    components['fixed_value'] = np.where(
        fixed,
        (
            components['lower_bound'].astype(float)
            + components['upper_bound'].astype(float)
        )
        / 2.0,
        np.nan,
    )
    active_ids = tuple(components.loc[~fixed, 'quantity_id'].astype(str))
    column_by_quantity = {quantity_id: i for i, quantity_id in enumerate(active_ids)}
    components['solver_column'] = components['quantity_id'].map(column_by_quantity)
    components['original_variable_id'] = components['quantity_id']

    relation_lookup = graph.relations_grid.set_index('parent_quantity_id')
    publication = quantities[
        quantities['quantity_kind'].eq('PUBLISHED_AGGREGATE')
    ].sort_index()
    binding_map = (
        graph.observation_bindings_grid.groupby('quantity_id', sort=False)[
            ['observation_id', 'source_series']
        ]
        .agg(tuple)
        .to_dict('index')
    )

    rows: list[list[tuple[int, float]]] = []
    row_lower: list[float] = []
    row_upper: list[float] = []
    row_meta: list[dict[str, object]] = []
    row_columns: list[np.ndarray] = []
    fixed_values = components.set_index('quantity_id')['fixed_value'].to_dict()
    active_rows = components.loc[~fixed]
    active_lower = np.asarray(
        [
            solver_lower_bound(row.lower_bound, bool(row.lower_attained))
            for row in active_rows.itertuples(index=False)
        ],
        dtype=float,
    )
    active_upper = np.asarray(
        [
            solver_upper_bound(row.upper_bound, bool(row.upper_attained))
            for row in active_rows.itertuples(index=False)
        ],
        dtype=float,
    )

    for pub in publication.itertuples(index=False):
        relation = relation_lookup.loc[str(pub.quantity_id)]
        if isinstance(relation, pd.DataFrame):
            relation = relation.iloc[0]
        coefficient_by_column: dict[int, float] = {}
        fixed_offset = 0.0
        for metric_quantity in relation.child_quantity_ids:
            _, region_code, class_code, metric = str(metric_quantity).split(':', 3)
            for component in METRIC_COMPONENTS[metric]:
                component_id = component_quantity_id(
                    region_code,
                    class_code,
                    component,
                )
                column = column_by_quantity.get(component_id)
                if column is None:
                    fixed_offset += float(fixed_values[component_id])
                else:
                    coefficient_by_column[column] = (
                        coefficient_by_column.get(column, 0.0) + 1.0
                    )
        semantic_lower = float(pub.lower_bound) - fixed_offset
        semantic_upper = float(pub.upper_bound) - fixed_offset
        lower = solver_lower_bound(semantic_lower, bool(pub.lower_attained))
        upper = solver_upper_bound(semantic_upper, bool(pub.upper_attained))
        items = [
            (column, coefficient)
            for column, coefficient in coefficient_by_column.items()
            if coefficient
        ]
        columns = np.asarray([item[0] for item in items], dtype=np.int32)
        coefficients = np.asarray([item[1] for item in items], dtype=float)
        if len(columns):
            expression_lower = float(
                np.dot(
                    coefficients,
                    np.where(coefficients >= 0, active_lower[columns], active_upper[columns]),
                )
            )
            expression_upper = float(
                np.dot(
                    coefficients,
                    np.where(coefficients >= 0, active_upper[columns], active_lower[columns]),
                )
            )
        else:
            expression_lower = expression_upper = 0.0
        redundant = (
            expression_lower >= lower - point_tolerance
            and expression_upper <= upper + point_tolerance
        )
        status = 'REDUNDANT_BY_COLUMN_BOUNDS' if redundant else 'ACTIVE'
        solver_row = None
        if not redundant:
            if not items:
                raise ValueError(
                    f'Publication constraint {pub.quantity_id} has no active variables '
                    'and is not satisfied by fixed values'
                )
            solver_row = len(rows)
            rows.append(items)
            row_lower.append(lower)
            row_upper.append(upper)
            row_columns.append(columns)
        binding = binding_map.get(str(pub.quantity_id), {})
        row_meta.append(
            {
                'constraint_id': f'strict:{pub.quantity_id}',
                'quantity_id': str(pub.quantity_id),
                'constraint_kind': str(relation.relation_kind),
                'model_layer': 'STRICT',
                'source_observation_ids': binding.get('observation_id', ()),
                'source_series': binding.get('source_series', ()),
                'lower_bound': semantic_lower,
                'upper_bound': semantic_upper,
                'lower_attained': bool(pub.lower_attained),
                'upper_attained': bool(pub.upper_attained),
                'solver_lower_bound': lower,
                'solver_upper_bound': upper,
                'fixed_offset': fixed_offset,
                'constraint_status': status,
                'solver_row': solver_row,
                'active_columns': len(items),
            }
        )

    variables_grid = components.reset_index(drop=True)
    variables_grid = assign_connected_components(variables_grid, row_columns)
    active = variables_grid[~variables_grid['is_fixed'].astype(bool)].sort_values(
        'solver_column'
    )
    problem = SorsLinearProblem(
        model_layer='STRICT',
        matrix=_csr(rows, len(active)),
        row_lower=np.asarray(row_lower, dtype=float),
        row_upper=np.asarray(row_upper, dtype=float),
        col_lower=active['lower_bound'].astype(float).to_numpy(),
        col_upper=active['upper_bound'].astype(float).to_numpy(),
        objective=np.zeros(len(active), dtype=float),
        constraints_grid=pd.DataFrame(row_meta),
        variables_grid=variables_grid,
        metadata={
            'quantity_to_column': column_by_quantity,
            'fixed_values': fixed_values,
            'point_tolerance': point_tolerance,
        },
    )

    region_names = bundle.atomic_regions_grid.set_index('region_code')[
        'region_name'
    ].astype(str).to_dict()
    target_rows: list[dict[str, object]] = []
    for region in bundle.atomic_regions_grid.sort_values('region_order').itertuples(index=False):
        for activity in bundle.okved2_classes_grid.sort_values('class_order').itertuples(index=False):
            for metric in METRIC_COMPONENTS:
                quantity_id = metric_quantity_id(
                    str(region.region_code), str(activity.class_code), metric
                )
                columns: list[int] = []
                coefficients: list[float] = []
                constant = 0.0
                for component in METRIC_COMPONENTS[metric]:
                    component_id = component_quantity_id(
                        str(region.region_code), str(activity.class_code), component
                    )
                    column = column_by_quantity.get(component_id)
                    if column is None:
                        constant += float(fixed_values[component_id])
                    else:
                        columns.append(column)
                        coefficients.append(1.0)
                target_rows.append(
                    {
                        'target_id': (
                            f'{region.region_code}:{activity.class_code}:{metric}'
                        ),
                        'quantity_id': quantity_id,
                        'region_code': str(region.region_code),
                        'region_name': region_names[str(region.region_code)],
                        'class_code': str(activity.class_code),
                        'metric': metric,
                        'indices': np.asarray(columns, dtype=np.int32),
                        'coefficients': np.asarray(coefficients, dtype=float),
                        'constant': constant,
                    }
                )
    cell_targets = build_cell_target_catalog(
        bundle, quantities_grid, variables_grid
    )
    return StrictCompilation(problem, pd.DataFrame(target_rows), cell_targets)


def linear_target_from_row(row) -> LinearTarget:
    return LinearTarget(
        target_id=str(row.target_id),
        quantity_id=str(row.quantity_id),
        region_code=str(row.region_code),
        region_name=str(row.region_name),
        class_code=str(row.class_code),
        metric=str(row.metric),
        indices=np.asarray(row.indices, dtype=np.int32),
        coefficients=np.asarray(row.coefficients, dtype=float),
        constant=float(row.constant),
    )


def refresh_strict_problem_bounds(
    problem: SorsLinearProblem,
    quantities_grid: pd.DataFrame,
) -> SorsLinearProblem:
    """Refresh active column bounds without rebuilding the sparse matrix."""

    quantities = quantities_grid.set_index('quantity_id')
    active = problem.variables_grid[
        problem.variables_grid['solver_column'].notna()
    ].copy()
    active['solver_column'] = active['solver_column'].astype(int)
    active = active.sort_values('solver_column')
    lower = np.asarray(
        [
            solver_lower_bound(
                float(quantities.loc[str(row.quantity_id), 'lower_bound']),
                bool(quantities.loc[str(row.quantity_id), 'lower_attained']),
            )
            for row in active.itertuples(index=False)
        ],
        dtype=float,
    )
    upper = np.asarray(
        [
            solver_upper_bound(
                float(quantities.loc[str(row.quantity_id), 'upper_bound']),
                bool(quantities.loc[str(row.quantity_id), 'upper_attained']),
            )
            for row in active.itertuples(index=False)
        ],
        dtype=float,
    )
    return replace(problem, col_lower=lower, col_upper=upper)
