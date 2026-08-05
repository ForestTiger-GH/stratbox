from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsRunConfig, SorsSourceBundle
from stratbox.macrobanks.cbr_sors_restoration.mapping import bridge_groups, bridge_weights
from stratbox.macrobanks.cbr_sors_restoration.metrics import METRIC_COMPONENTS, source_metric
from stratbox.macrobanks.cbr_sors_restoration.schema import COMPONENTS


@dataclass(frozen=True, slots=True)
class LinearTarget:
    target_id: str
    region_name: str
    region_code: str
    class_code: str
    metric: str
    indices: np.ndarray
    coefficients: np.ndarray


@dataclass(frozen=True)
class CsrMatrixData:
    shape: tuple[int, int]
    indptr: np.ndarray
    indices: np.ndarray
    data: np.ndarray

    @property
    def nnz(self) -> int:
        return int(len(self.data))


@dataclass(frozen=True)
class SorsProblem:
    matrix: CsrMatrixData
    row_lower: np.ndarray
    row_upper: np.ndarray
    col_lower: np.ndarray
    col_upper: np.ndarray
    bridge_objective: np.ndarray
    variable_grid: pd.DataFrame
    constraints_grid: pd.DataFrame
    region_positions: dict[str, int]
    class_positions: dict[str, int]
    component_positions: dict[str, int]
    n_primary_variables: int

    @property
    def num_variables(self) -> int:
        return int(len(self.col_lower))


def _project_problem(
    problem: SorsProblem,
    *,
    row_positions: np.ndarray,
    row_lower: np.ndarray,
    row_upper: np.ndarray,
    constraints_grid: pd.DataFrame,
) -> SorsProblem:
    n_columns = problem.n_primary_variables
    indptr = [0]
    indices: list[int] = []
    data: list[float] = []
    for row_position in row_positions.astype(int):
        start = int(problem.matrix.indptr[row_position])
        end = int(problem.matrix.indptr[row_position + 1])
        row_indices = problem.matrix.indices[start:end]
        row_data = problem.matrix.data[start:end]
        mask = row_indices < n_columns
        indices.extend(row_indices[mask].astype(int).tolist())
        data.extend(row_data[mask].astype(float).tolist())
        indptr.append(len(indices))
    matrix = CsrMatrixData(
        shape=(len(row_positions), n_columns),
        indptr=np.asarray(indptr, dtype=np.int64),
        indices=np.asarray(indices, dtype=np.int32),
        data=np.asarray(data, dtype=float),
    )
    variable_grid = problem.variable_grid.iloc[:n_columns].copy().reset_index(drop=True)
    return SorsProblem(
        matrix=matrix,
        row_lower=np.asarray(row_lower, dtype=float),
        row_upper=np.asarray(row_upper, dtype=float),
        col_lower=problem.col_lower[:n_columns].copy(),
        col_upper=problem.col_upper[:n_columns].copy(),
        bridge_objective=np.zeros(n_columns, dtype=float),
        variable_grid=variable_grid,
        constraints_grid=constraints_grid.reset_index(drop=True),
        region_positions=problem.region_positions,
        class_positions=problem.class_positions,
        component_positions=problem.component_positions,
        n_primary_variables=n_columns,
    )


def strict_publication_problem(problem: SorsProblem) -> SorsProblem:
    mask = problem.constraints_grid['hardness'].astype(str).eq('HARD_PUBLICATION').to_numpy()
    positions = np.flatnonzero(mask)
    return _project_problem(
        problem,
        row_positions=positions,
        row_lower=problem.row_lower[positions],
        row_upper=problem.row_upper[positions],
        constraints_grid=problem.constraints_grid.iloc[positions].copy(),
    )


def bridge_profile_problem(
    problem: SorsProblem,
    optimum_values: np.ndarray,
    *,
    tolerance: float,
    geography_node_id: str | None = None,
) -> SorsProblem:
    meta = problem.constraints_grid.copy()
    hard_mask = meta['hardness'].astype(str).eq('HARD_PUBLICATION').to_numpy()
    bridge_mask = meta['hardness'].astype(str).eq('BRIDGE_OBJECTIVE').to_numpy()
    if geography_node_id is not None:
        geography = meta.get('geography_node_id', pd.Series(index=meta.index, dtype=object)).astype(str)
        bridge_mask &= geography.eq(str(geography_node_id)).to_numpy()
    selected_mask = hard_mask | bridge_mask
    positions = np.flatnonzero(selected_mask)
    lower = problem.row_lower[positions].copy()
    upper = problem.row_upper[positions].copy()
    selected_meta = meta.iloc[positions].copy()
    primary_values = np.asarray(optimum_values[:problem.n_primary_variables], dtype=float)
    for local_position, row_position in enumerate(positions):
        if not bridge_mask[row_position]:
            continue
        start = int(problem.matrix.indptr[row_position])
        end = int(problem.matrix.indptr[row_position + 1])
        row_indices = problem.matrix.indices[start:end]
        row_data = problem.matrix.data[start:end]
        mask = row_indices < problem.n_primary_variables
        fitted = float(np.dot(row_data[mask], primary_values[row_indices[mask]]))
        lower[local_position] = max(0.0, fitted - tolerance)
        upper[local_position] = fitted + tolerance
    selected_meta.loc[selected_meta['hardness'].astype(str).eq('BRIDGE_OBJECTIVE'), 'hardness'] = 'BRIDGE_PROFILE'
    selected_meta.loc[selected_meta['constraint_kind'].astype(str).eq('legacy_bridge_fit'), 'constraint_kind'] = 'legacy_bridge_profile'
    return _project_problem(
        problem,
        row_positions=positions,
        row_lower=lower,
        row_upper=upper,
        constraints_grid=selected_meta,
    )


class ProblemBuilder:
    def __init__(self, bundle: SorsSourceBundle, config: SorsRunConfig, mapping_edges: pd.DataFrame):
        self.bundle = bundle
        self.config = config
        self.mapping_edges = mapping_edges
        self.regions = bundle.atomic_regions.reset_index(drop=True)
        self.classes = bundle.okved2_classes.reset_index(drop=True)
        self.region_positions = {name: i for i, name in enumerate(self.regions['region_name'].astype(str))}
        self.region_code_positions = {code: i for i, code in enumerate(self.regions['region_code'].astype(str))}
        self.class_positions = {code: i for i, code in enumerate(self.classes['class_code'].astype(str))}
        self.component_positions = {name: i for i, name in enumerate(COMPONENTS)}
        self.n_primary = len(self.regions) * len(self.classes) * len(COMPONENTS)
        self.rows: list[list[tuple[int, float]]] = []
        self.row_lower: list[float] = []
        self.row_upper: list[float] = []
        self.row_meta: list[dict[str, object]] = []
        self.bridge_objective: list[float] = [0.0] * self.n_primary
        self.col_meta: list[dict[str, object]] = []
        for r, region in self.regions.iterrows():
            for c, cls in self.classes.iterrows():
                for k, component in enumerate(COMPONENTS):
                    self.col_meta.append({
                        'variable_id': self.x_index(r, c, component),
                        'variable_kind': 'regional_okved2_component',
                        'region_code': region['region_code'],
                        'region_name': region['region_name'],
                        'federal_district_name': region['federal_district_name'],
                        'class_code': cls['class_code'],
                        'class_name': cls['class_name'],
                        'section_code': cls['section_code'],
                        'component': component,
                    })
        self.geo_members = {
            row.geography_node_id: tuple(row.atomic_region_codes)
            for row in bundle.geography_nodes.itertuples(index=False)
        }
        self.bridge_groups = bridge_groups(mapping_edges)
        self.bridge_weights = bridge_weights(mapping_edges)

    def x_index(self, region_pos: int, class_pos: int, component: str) -> int:
        return (region_pos * len(self.classes) + class_pos) * len(COMPONENTS) + self.component_positions[component]

    def expression(self, region_codes, class_codes, metric: str) -> list[tuple[int, float]]:
        components = METRIC_COMPONENTS[metric]
        return [
            (self.x_index(self.region_code_positions[region], self.class_positions[class_code], component), 1.0)
            for region in region_codes
            for class_code in class_codes
            for component in components
        ]

    def add_hard(self, *, constraint_id: str, items, lower: float, upper: float, source_observation_id: str, source_series: str, kind: str) -> None:
        values = list(items)
        if not values:
            raise ValueError(f'Constraint {constraint_id} has no variables')
        self.rows.append(values)
        self.row_lower.append(float(lower))
        self.row_upper.append(float(upper))
        self.row_meta.append({
            'constraint_id': constraint_id,
            'constraint_kind': kind,
            'hardness': 'HARD_PUBLICATION',
            'source_observation_id': source_observation_id,
            'source_series': source_series,
            'published_lower': lower,
            'published_upper': upper,
            'bridge_weight': 0.0,
        })

    def add_soft_bridge(self, *, constraint_id: str, items, value: float, observation, base_weight: float, geography_weight: float) -> None:
        expression = list(items)
        if not expression:
            return
        positive = len(self.bridge_objective)
        negative = positive + 1
        self.bridge_objective.extend([0.0, 0.0])
        self.col_meta.extend([
            {'variable_id': positive, 'variable_kind': 'bridge_positive_deviation', 'bridge_constraint_id': constraint_id},
            {'variable_id': negative, 'variable_kind': 'bridge_negative_deviation', 'bridge_constraint_id': constraint_id},
        ])
        expression.extend([(positive, -1.0), (negative, 1.0)])
        weight = float(base_weight) * float(geography_weight) / sqrt(max(abs(float(value)), 100.0))
        self.bridge_objective[positive] = weight
        self.bridge_objective[negative] = weight
        self.rows.append(expression)
        self.row_lower.append(float(value))
        self.row_upper.append(float(value))
        self.row_meta.append({
            'constraint_id': constraint_id,
            'constraint_kind': 'legacy_bridge_fit',
            'hardness': 'BRIDGE_OBJECTIVE',
            'source_observation_id': observation.observation_id,
            'source_series': observation.source_series,
            'published_lower': observation.published_lower,
            'published_upper': observation.published_upper,
            'bridge_weight': weight,
            'geography_node_id': getattr(observation, 'geography_node_id', None),
            'geography_name': getattr(observation, 'geography_name', None),
            'geography_kind': getattr(observation, 'geography_kind', None),
            'activity_code': getattr(observation, 'activity_code', None),
            'measure': getattr(observation, 'measure', None),
            'currency': getattr(observation, 'currency', None),
        })

    def _class_codes_for_publication(self, code: str, *, fd: bool = False) -> tuple[str, ...]:
        if code == 'PUBLISHED_OTHER':
            if not fd:
                return self.bundle.published_other_classes
            published_sections = set(self.bundle.fd_okved2_grid['activity_code'].astype(str)) - {'PUBLISHED_OTHER'}
            return tuple(self.classes.loc[~self.classes['section_code'].isin(published_sections), 'class_code'].astype(str))
        if fd:
            return tuple(self.classes.loc[self.classes['section_code'].astype(str) == code, 'class_code'].astype(str))
        return (code,)

    def add_publication_constraints(self) -> None:
        all_regions = tuple(self.regions['region_code'].astype(str))
        all_classes = tuple(self.classes['class_code'].astype(str))
        regional_total = self.bundle.regional_traditional_grid[self.bundle.regional_traditional_grid['activity_code'].astype(str) == 'total']
        for row in regional_total.itertuples(index=False):
            metric = source_metric(row.measure, row.currency)
            members = self.geo_members[str(row.geography_node_id)]
            self.add_hard(
                constraint_id=f'hard:{row.observation_id}',
                items=self.expression(members, all_classes, metric),
                lower=row.published_lower,
                upper=row.published_upper,
                source_observation_id=row.observation_id,
                source_series=row.source_series,
                kind='regional_total',
            )
        national_old_total = self.bundle.national_traditional_grid[self.bundle.national_traditional_grid['activity_code'].astype(str) == 'total']
        for row in national_old_total.itertuples(index=False):
            metric = source_metric(row.measure, row.currency)
            self.add_hard(
                constraint_id=f'hard:{row.observation_id}',
                items=self.expression(all_regions, all_classes, metric),
                lower=row.published_lower,
                upper=row.published_upper,
                source_observation_id=row.observation_id,
                source_series=row.source_series,
                kind='national_traditional_total',
            )
        for row in self.bundle.national_okved2_grid.itertuples(index=False):
            metric = source_metric(row.measure, row.currency)
            classes = self._class_codes_for_publication(str(row.activity_code))
            self.add_hard(
                constraint_id=f'hard:{row.observation_id}',
                items=self.expression(all_regions, classes, metric),
                lower=row.published_lower,
                upper=row.published_upper,
                source_observation_id=row.observation_id,
                source_series=row.source_series,
                kind='national_okved2',
            )
        fd_members = {
            name: tuple(group['region_code'].astype(str))
            for name, group in self.regions.groupby('federal_district_name', sort=False)
        }
        for row in self.bundle.fd_okved2_grid.itertuples(index=False):
            metric = source_metric(row.measure, 'total')
            classes = self._class_codes_for_publication(str(row.activity_code), fd=True)
            self.add_hard(
                constraint_id=f'hard:{row.observation_id}',
                items=self.expression(fd_members[str(row.geography_name)], classes, metric),
                lower=row.published_lower,
                upper=row.published_upper,
                source_observation_id=row.observation_id,
                source_series=row.source_series,
                kind='fd_okved2_section',
            )

    def add_bridge_constraints(self) -> None:
        def geography_weight(kind: str, member_count: int) -> float:
            if member_count == 1:
                return 1.0
            if kind == 'federal_district_total':
                return 0.25
            if kind == 'country_total':
                return 0.125
            return 0.5
        regional = self.bundle.regional_traditional_grid
        regional = regional[regional['activity_code'].astype(str).isin(self.bridge_groups)]
        for row in regional.itertuples(index=False):
            metric = source_metric(row.measure, row.currency)
            members = self.geo_members[str(row.geography_node_id)]
            classes = self.bridge_groups[str(row.activity_code)]
            self.add_soft_bridge(
                constraint_id=f'bridge:{row.observation_id}',
                items=self.expression(members, classes, metric),
                value=row.value,
                observation=row,
                base_weight=self.bridge_weights[str(row.activity_code)],
                geography_weight=geography_weight(str(row.geography_kind), len(members)),
            )
        for row in self.bundle.national_traditional_grid.itertuples(index=False):
            if str(row.activity_code) not in self.bridge_groups:
                continue
            metric = source_metric(row.measure, row.currency)
            classes = self.bridge_groups[str(row.activity_code)]
            self.add_soft_bridge(
                constraint_id=f'bridge:{row.observation_id}',
                items=self.expression(tuple(self.regions['region_code'].astype(str)), classes, metric),
                value=row.value,
                observation=row,
                base_weight=self.bridge_weights[str(row.activity_code)],
                geography_weight=0.125,
            )

    def build(self) -> SorsProblem:
        self.add_publication_constraints()
        self.add_bridge_constraints()
        indptr = [0]
        indices: list[int] = []
        data: list[float] = []
        for items in self.rows:
            combined: dict[int, float] = {}
            for column, coefficient in items:
                combined[int(column)] = combined.get(int(column), 0.0) + float(coefficient)
            for column in sorted(combined):
                coefficient = combined[column]
                if coefficient != 0.0:
                    indices.append(column)
                    data.append(coefficient)
            indptr.append(len(indices))
        matrix = CsrMatrixData(
            shape=(len(self.rows), len(self.bridge_objective)),
            indptr=np.asarray(indptr, dtype=np.int64),
            indices=np.asarray(indices, dtype=np.int32),
            data=np.asarray(data, dtype=float),
        )
        col_lower = np.zeros(len(self.bridge_objective), dtype=float)
        col_upper = np.full(len(self.bridge_objective), np.inf, dtype=float)
        return SorsProblem(
            matrix=matrix,
            row_lower=np.asarray(self.row_lower, dtype=float),
            row_upper=np.asarray(self.row_upper, dtype=float),
            col_lower=col_lower,
            col_upper=col_upper,
            bridge_objective=np.asarray(self.bridge_objective, dtype=float),
            variable_grid=pd.DataFrame(self.col_meta),
            constraints_grid=pd.DataFrame(self.row_meta),
            region_positions=self.region_positions,
            class_positions=self.class_positions,
            component_positions=self.component_positions,
            n_primary_variables=self.n_primary,
        )


def make_target(problem: SorsProblem, bundle: SorsSourceBundle, region_name: str, class_code: str, metric: str) -> LinearTarget:
    r = problem.region_positions[region_name]
    c = problem.class_positions[class_code]
    indices = np.asarray([
        (r * len(bundle.okved2_classes) + c) * len(COMPONENTS) + problem.component_positions[component]
        for component in METRIC_COMPONENTS[metric]
    ], dtype=np.int32)
    coefficients = np.ones(len(indices), dtype=float)
    region_row = bundle.atomic_regions.loc[bundle.atomic_regions['region_name'].astype(str) == region_name].iloc[0]
    return LinearTarget(
        target_id=f'{region_row.region_code}:{class_code}:{metric}',
        region_name=region_name,
        region_code=str(region_row.region_code),
        class_code=class_code,
        metric=metric,
        indices=indices,
        coefficients=coefficients,
    )
