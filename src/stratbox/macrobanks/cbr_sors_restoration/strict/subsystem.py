from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsSourceBundle
from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import (
    CsrMatrixData,
    LinearTarget,
    SorsLinearProblem,
)

_COMPONENT_PRIMARY_METRICS = {
    'performing_rub': frozenset({'debt_rub', 'overdue_rub'}),
    'overdue_rub': frozenset({'overdue_rub'}),
    'performing_fx': frozenset({'debt_fx', 'overdue_fx'}),
    'overdue_fx': frozenset({'overdue_fx'}),
}


@dataclass(frozen=True)
class SorsTargetSubsystem:
    subsystem_id: str
    target_id: str
    horizon: str
    problem: SorsLinearProblem
    target: LinearTarget
    original_solver_rows: tuple[int, ...]
    original_solver_columns: tuple[int, ...]
    supporting_constraint_ids: tuple[str, ...]


def _row_columns(matrix: CsrMatrixData, row: int) -> np.ndarray:
    start = int(matrix.indptr[row])
    end = int(matrix.indptr[row + 1])
    return matrix.indices[start:end]


def _build_csr_projection(
    matrix: CsrMatrixData,
    rows: tuple[int, ...],
    columns: tuple[int, ...],
) -> CsrMatrixData:
    local_by_original = {column: position for position, column in enumerate(columns)}
    indptr = [0]
    indices: list[int] = []
    data: list[float] = []
    for row in rows:
        start = int(matrix.indptr[row])
        end = int(matrix.indptr[row + 1])
        for original, value in zip(
            matrix.indices[start:end], matrix.data[start:end], strict=True
        ):
            local = local_by_original.get(int(original))
            if local is None:
                continue
            indices.append(local)
            data.append(float(value))
        indptr.append(len(indices))
    return CsrMatrixData(
        shape=(len(rows), len(columns)),
        indptr=np.asarray(indptr, dtype=np.int64),
        indices=np.asarray(indices, dtype=np.int32),
        data=np.asarray(data, dtype=float),
    )


class SorsSubsystemBuilder:
    """Build cumulative safe outer systems around one RKVS target.

    A local subsystem drops rows from the globally feasible strict model and
    keeps every variable used by selected rows. Its feasible set is therefore
    an outer approximation of the global feasible set.
    """

    def __init__(
        self,
        bundle: SorsSourceBundle,
        problem: SorsLinearProblem,
        target_catalog_grid: pd.DataFrame,
    ) -> None:
        self.bundle = bundle
        self.problem = problem
        self.targets = target_catalog_grid.set_index('target_id', drop=False)
        constraints = problem.constraints_grid.copy()
        constraints = constraints[constraints['solver_row'].notna()].copy()
        constraints['solver_row'] = constraints['solver_row'].astype(int)
        self.constraints = constraints.set_index('solver_row', drop=False).sort_index()

        nodes = bundle.geography_nodes_grid.copy()
        self.node_kind = nodes.set_index('geography_node_id')['geography_kind'].astype(str).to_dict()
        self.node_members = {
            str(row.geography_node_id): tuple(str(v) for v in row.atomic_region_codes)
            for row in nodes.itertuples(index=False)
        }
        self.singleton_node_by_region: dict[str, str] = {}
        self.parent_nodes_by_region: dict[str, tuple[str, ...]] = {}
        for node_id, members in self.node_members.items():
            kind = self.node_kind.get(node_id, '')
            if len(members) == 1 and kind not in {'country_total', 'federal_district_total'}:
                self.singleton_node_by_region[members[0]] = node_id
        for region in bundle.atomic_regions_grid['region_code'].astype(str):
            parents = [
                node_id
                for node_id, members in self.node_members.items()
                if region in members
                and len(members) > 1
                and self.node_kind.get(node_id, '') not in {
                    'country_total', 'federal_district_total'
                }
            ]
            self.parent_nodes_by_region[region] = tuple(sorted(parents))
        self.fd_node_by_code = {
            str(row.federal_district_code): str(row.geography_node_id)
            for row in nodes[nodes['geography_kind'].eq('federal_district_total')].itertuples(index=False)
        }
        self.country_node_ids = frozenset(
            nodes.loc[nodes['geography_kind'].eq('country_total'), 'geography_node_id'].astype(str)
        )

        national = bundle.publication_categories_grid[
            bundle.publication_categories_grid['publication_level'].eq('NATIONAL_CLASS')
        ]
        self.national_category_by_class = {
            str(row.member_class_code): str(row.publication_category_code)
            for row in national.itertuples(index=False)
        }
        fd = bundle.publication_categories_grid[
            bundle.publication_categories_grid['publication_level'].eq('FD_SECTION')
        ]
        self.fd_category_by_class = {
            str(row.member_class_code): str(row.publication_category_code)
            for row in fd.itertuples(index=False)
        }

        active_variables = problem.variables_grid[
            problem.variables_grid['solver_column'].notna()
        ].copy()
        active_variables['solver_column'] = active_variables['solver_column'].astype(int)
        self.variable_by_column = active_variables.set_index('solver_column').sort_index()
        self.component_columns: dict[str, frozenset[int]] = {
            str(component_id): frozenset(group['solver_column'].astype(int))
            for component_id, group in active_variables.groupby(
                'connected_component_id', dropna=True, sort=False
            )
        }
        self.rows_by_connected_component: dict[str, tuple[int, ...]] = {}
        row_column_sets = [
            set(int(value) for value in _row_columns(problem.matrix, solver_row))
            for solver_row in range(problem.num_constraints)
        ]
        for component_id, columns in self.component_columns.items():
            column_set = set(columns)
            self.rows_by_connected_component[component_id] = tuple(
                row for row, row_columns in enumerate(row_column_sets)
                if column_set.intersection(row_columns)
            )

    @staticmethod
    def _parse_quantity_id(quantity_id: str) -> tuple[str, ...]:
        return tuple(str(quantity_id).split(':'))

    def _rows_matching(self, predicate) -> set[int]:
        return {
            int(row.solver_row)
            for row in self.constraints.itertuples(index=False)
            if predicate(row)
        }

    def rows_for_horizon(self, target_id: str, horizon: str) -> set[int]:
        target = self.targets.loc[target_id]
        region = str(target.region_code)
        class_code = str(target.class_code)
        component = str(target.component)
        fd_code = str(target.federal_district_code)
        if horizon == 'CELL':
            return set()
        if horizon == 'REGION_COMPONENT':
            node = self.singleton_node_by_region.get(region)
            metrics = _COMPONENT_PRIMARY_METRICS[component]
            return self._rows_matching(
                lambda row: (
                    self._parse_quantity_id(str(row.quantity_id))[:3]
                    == ('publication', 'geography', str(node))
                    and self._parse_quantity_id(str(row.quantity_id))[-1] in metrics
                )
            )
        if horizon == 'REGION_CROSS_METRIC':
            node = self.singleton_node_by_region.get(region)
            return self._rows_matching(
                lambda row: self._parse_quantity_id(str(row.quantity_id))[:3]
                == ('publication', 'geography', str(node))
            )
        if horizon == 'REGION_PARENT':
            nodes = set(self.parent_nodes_by_region.get(region, ()))
            return self._rows_matching(
                lambda row: (
                    len(self._parse_quantity_id(str(row.quantity_id))) >= 3
                    and self._parse_quantity_id(str(row.quantity_id))[1] == 'geography'
                    and self._parse_quantity_id(str(row.quantity_id))[2] in nodes
                )
            )
        if horizon == 'FD_SECTION':
            category = self.fd_category_by_class[class_code]
            return self._rows_matching(
                lambda row: self._parse_quantity_id(str(row.quantity_id))[:4]
                == ('publication', 'fd_section', fd_code, category)
            )
        if horizon == 'FEDERAL_DISTRICT_TOTAL':
            node = self.fd_node_by_code.get(fd_code)
            return self._rows_matching(
                lambda row: self._parse_quantity_id(str(row.quantity_id))[:3]
                == ('publication', 'geography', str(node))
            )
        if horizon == 'NATIONAL_CLASS':
            category = self.national_category_by_class[class_code]
            return self._rows_matching(
                lambda row: self._parse_quantity_id(str(row.quantity_id))[:3]
                == ('publication', 'national_class', category)
            )
        if horizon == 'NATIONAL_TOTAL':
            return self._rows_matching(
                lambda row: (
                    len(self._parse_quantity_id(str(row.quantity_id))) > 1
                    and (
                        self._parse_quantity_id(str(row.quantity_id))[1] == 'national_total'
                        or (
                            self._parse_quantity_id(str(row.quantity_id))[1] == 'geography'
                            and self._parse_quantity_id(str(row.quantity_id))[2]
                            in self.country_node_ids
                        )
                    )
                )
            )
        if horizon == 'GLOBAL_CONNECTED':
            component_id = target.connected_component_id
            if component_id is None or pd.isna(component_id):
                return set()
            return set(self.rows_by_connected_component.get(str(component_id), ()))
        raise ValueError(f'Unsupported RKVS horizon: {horizon}')

    def build(
        self,
        target_id: str,
        horizon: str,
        cumulative_rows: set[int],
        *,
        attempt_id: str,
    ) -> SorsTargetSubsystem | None:
        target_row = self.targets.loc[target_id]
        original_target_column = target_row.solver_column
        if original_target_column is None or pd.isna(original_target_column):
            return None
        target_column = int(original_target_column)
        rows = tuple(sorted(cumulative_rows))
        columns: set[int] = {target_column}
        for row in rows:
            columns.update(int(value) for value in _row_columns(self.problem.matrix, row))
        ordered_columns = tuple(sorted(columns))
        local_by_original = {original: local for local, original in enumerate(ordered_columns)}
        local_target_column = local_by_original[target_column]
        matrix = _build_csr_projection(self.problem.matrix, rows, ordered_columns)
        variables = self.variable_by_column.loc[list(ordered_columns)].copy()
        variables['original_solver_column'] = variables.index.astype(int)
        variables['solver_column'] = range(len(variables))
        variables = variables.reset_index(drop=True)
        if rows:
            constraints = self.constraints.loc[list(rows)].copy()
            constraints['original_solver_row'] = constraints['solver_row'].astype(int)
            constraints['solver_row'] = range(len(constraints))
            constraints = constraints.reset_index(drop=True)
        else:
            constraints = pd.DataFrame(columns=self.problem.constraints_grid.columns)
        subsystem_id = f'{attempt_id}:{horizon.lower()}'
        local_problem = SorsLinearProblem(
            model_layer='STRICT_TARGET_SUBSYSTEM',
            matrix=matrix,
            row_lower=self.problem.row_lower[list(rows)].copy() if rows else np.asarray([], dtype=float),
            row_upper=self.problem.row_upper[list(rows)].copy() if rows else np.asarray([], dtype=float),
            col_lower=self.problem.col_lower[list(ordered_columns)].copy(),
            col_upper=self.problem.col_upper[list(ordered_columns)].copy(),
            objective=np.zeros(len(ordered_columns), dtype=float),
            constraints_grid=constraints,
            variables_grid=variables,
            metadata={
                'subsystem_id': subsystem_id,
                'target_id': target_id,
                'horizon': horizon,
                'original_solver_rows': rows,
                'original_solver_columns': ordered_columns,
            },
        )
        target = LinearTarget(
            target_id=target_id,
            quantity_id=str(target_row.quantity_id),
            region_code=str(target_row.region_code),
            region_name=str(target_row.region_name),
            class_code=str(target_row.class_code),
            metric=str(target_row.component),
            indices=np.asarray([local_target_column], dtype=np.int32),
            coefficients=np.asarray([1.0], dtype=float),
            constant=0.0,
        )
        supporting = tuple(constraints['constraint_id'].astype(str)) if not constraints.empty else ()
        return SorsTargetSubsystem(
            subsystem_id=subsystem_id,
            target_id=target_id,
            horizon=horizon,
            problem=local_problem,
            target=target,
            original_solver_rows=rows,
            original_solver_columns=ordered_columns,
            supporting_constraint_ids=supporting,
        )
