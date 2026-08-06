from __future__ import annotations

from dataclasses import dataclass
from math import inf, isfinite

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsCrosswalkConfig,
    SorsSourceBundle,
)
from stratbox.macrobanks.cbr_sors_restoration.crosswalk.mapping import (
    build_crosswalk_relations_grid,
    read_atom_class_edges,
    read_legacy_atoms,
    read_legacy_membership,
)
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
from stratbox.macrobanks.cbr_sors_restoration.registries.publication_categories import (
    PUBLISHED_OTHER_CLASSES,
)
from stratbox.macrobanks.cbr_sors_restoration.schema import COMPONENTS


@dataclass(frozen=True)
class CrosswalkCompilation:
    problem: SorsLinearProblem
    target_catalog_grid: pd.DataFrame
    mapping_edges_grid: pd.DataFrame
    relations_grid: pd.DataFrame


class _SparseBuilder:
    def __init__(self, *, open_bound_margin: float = 0.0) -> None:
        self.open_bound_margin = float(open_bound_margin)
        self.rows: list[list[tuple[int, float]]] = []
        self.lower: list[float] = []
        self.upper: list[float] = []
        self.meta: list[dict[str, object]] = []

    def add(
        self,
        items,
        *,
        lower: float,
        upper: float,
        lower_attained: bool = True,
        upper_attained: bool = True,
        **meta: object,
    ) -> None:
        semantic_lower = float(lower)
        semantic_upper = float(upper)
        solver_lower = solver_lower_bound(
            semantic_lower,
            lower_attained,
            open_margin=self.open_bound_margin,
        )
        solver_upper = solver_upper_bound(
            semantic_upper,
            upper_attained,
            open_margin=self.open_bound_margin,
        )
        combined: dict[int, float] = {}
        for column, coefficient in items:
            combined[int(column)] = combined.get(int(column), 0.0) + float(
                coefficient
            )
        row = sorted(
            (column, value) for column, value in combined.items() if value != 0.0
        )
        if not row:
            if solver_lower <= 0.0 <= solver_upper:
                return
            raise ValueError(f'Empty crosswalk constraint is inconsistent: {meta}')
        self.rows.append(row)
        self.lower.append(float(solver_lower))
        self.upper.append(float(solver_upper))
        self.meta.append(
            dict(
                meta,
                lower_bound=semantic_lower,
                upper_bound=semantic_upper,
                lower_attained=bool(lower_attained),
                upper_attained=bool(upper_attained),
                solver_lower_bound=float(solver_lower),
                solver_upper_bound=float(solver_upper),
            )
        )

    def matrix(self, columns: int) -> CsrMatrixData:
        indptr = [0]
        indices: list[int] = []
        values: list[float] = []
        for row in self.rows:
            indices.extend(column for column, _ in row)
            values.extend(value for _, value in row)
            indptr.append(len(indices))
        return CsrMatrixData(
            shape=(len(self.rows), columns),
            indptr=np.asarray(indptr, dtype=np.int64),
            indices=np.asarray(indices, dtype=np.int32),
            data=np.asarray(values, dtype=float),
        )


class CrosswalkProblemBuilder(_SparseBuilder):
    """Compile one conditional crosswalk scenario as a pure flow system.

    A solver variable is a non-negative flow from one legacy atom to one allowed
    OKVED2 class for one atomic region and one disjoint monetary component.
    Legacy publications sum the same flows by source atom; OKVED2 publications
    sum them by destination class. Thus the crosswalk graph itself is the system
    of conditional equations. No preferred solution or fallback objective is used.
    """

    def __init__(
        self,
        bundle: SorsSourceBundle,
        strict_components_grid: pd.DataFrame,
        config: SorsCrosswalkConfig,
        scenario_id: str,
    ) -> None:
        super().__init__(open_bound_margin=config.point_tolerance)
        self.bundle = bundle
        self.config = config
        self.scenario_id = scenario_id
        self.regions = bundle.atomic_regions_grid.sort_values(
            'region_order'
        ).reset_index(drop=True)
        self.classes = bundle.okved2_classes_grid.sort_values(
            'class_order'
        ).reset_index(drop=True)
        self.atoms = read_legacy_atoms().reset_index(drop=True)
        self.membership = read_legacy_membership()
        self.mapping_edges = read_atom_class_edges(
            self.classes,
            config.mapping_version,
            scenario_id,
        )
        self.relations = build_crosswalk_relations_grid(self.mapping_edges)

        atom_order = {
            code: position
            for position, code in enumerate(self.atoms['atom_code'].astype(str))
        }
        class_order = {
            code: position
            for position, code in enumerate(self.classes['class_code'].astype(str))
        }
        ordered = self.mapping_edges.copy()
        ordered['_atom_order'] = ordered['atom_code'].astype(str).map(atom_order)
        ordered['_class_order'] = ordered['class_code'].astype(str).map(class_order)
        ordered = ordered.sort_values(
            ['_atom_order', '_class_order'], kind='stable'
        )
        self.allowed_pairs = tuple(
            zip(
                ordered['atom_code'].astype(str),
                ordered['class_code'].astype(str),
                strict=True,
            )
        )
        self.pair_positions = {
            pair: position for position, pair in enumerate(self.allowed_pairs)
        }
        self.pairs_by_atom: dict[str, tuple[tuple[str, str], ...]] = {
            str(atom): tuple(
                zip(
                    group['atom_code'].astype(str),
                    group['class_code'].astype(str),
                    strict=True,
                )
            )
            for atom, group in ordered.groupby('atom_code', sort=False)
        }
        self.pairs_by_class: dict[str, tuple[tuple[str, str], ...]] = {
            str(class_code): tuple(
                zip(
                    group['atom_code'].astype(str),
                    group['class_code'].astype(str),
                    strict=True,
                )
            )
            for class_code, group in ordered.groupby('class_code', sort=False)
        }
        self.region_positions = {
            code: position
            for position, code in enumerate(self.regions['region_code'].astype(str))
        }
        self.component_positions = {
            name: position for position, name in enumerate(COMPONENTS)
        }
        self.n_regions = len(self.regions)
        self.n_pairs = len(self.allowed_pairs)
        self.n_components = len(COMPONENTS)
        self.n = self.n_regions * self.n_pairs * self.n_components

        self.geo_members = {
            str(row.geography_node_id): tuple(row.atomic_region_codes)
            for row in bundle.geography_nodes_grid.itertuples(index=False)
        }
        self.node_atoms = {
            str(node): tuple(group['atom_code'].astype(str))
            for node, group in self.membership.groupby('node_code', sort=False)
        }
        self.node_atoms['total'] = tuple(self.atoms['atom_code'].astype(str))
        self.fd_members = {
            str(code): tuple(group['region_code'].astype(str))
            for code, group in self.regions.groupby(
                'federal_district_code', sort=False
            )
        }
        if strict_components_grid.empty:
            self.strict_bounds = pd.DataFrame()
        else:
            required = {'region_code', 'class_code', 'component'}
            missing = required - set(strict_components_grid.columns)
            if missing:
                raise ValueError(
                    f'Strict component grid is missing columns: {sorted(missing)}'
                )
            self.strict_bounds = strict_components_grid.set_index(
                ['region_code', 'class_code', 'component']
            )

    def flow(
        self,
        region: str,
        atom: str,
        class_code: str,
        component: str,
    ) -> int:
        pair = self.pair_positions[(atom, class_code)]
        return (
            (
                self.region_positions[region] * self.n_pairs
                + pair
            )
            * self.n_components
            + self.component_positions[component]
        )

    def atom_component_expression(
        self,
        region: str,
        atom: str,
        component: str,
    ) -> list[tuple[int, float]]:
        return [
            (self.flow(region, source, target, component), 1.0)
            for source, target in self.pairs_by_atom[atom]
        ]

    def class_component_expression(
        self,
        region: str,
        class_code: str,
        component: str,
    ) -> list[tuple[int, float]]:
        return [
            (self.flow(region, source, target, component), 1.0)
            for source, target in self.pairs_by_class[class_code]
        ]

    def legacy_expression(
        self,
        regions: tuple[str, ...],
        atoms: tuple[str, ...],
        metric: str,
    ) -> list[tuple[int, float]]:
        return [
            item
            for region in regions
            for atom in atoms
            for component in METRIC_COMPONENTS[metric]
            for item in self.atom_component_expression(region, atom, component)
        ]

    def okved_expression(
        self,
        regions: tuple[str, ...],
        classes: tuple[str, ...],
        metric: str,
    ) -> list[tuple[int, float]]:
        return [
            item
            for region in regions
            for class_code in classes
            for component in METRIC_COMPONENTS[metric]
            for item in self.class_component_expression(
                region, class_code, component
            )
        ]

    def class_expression(
        self,
        region: str,
        class_code: str,
        metric: str,
    ) -> list[tuple[int, float]]:
        return [
            item
            for component in METRIC_COMPONENTS[metric]
            for item in self.class_component_expression(
                region, class_code, component
            )
        ]

    def publication_classes(
        self,
        code: str,
        *,
        federal_district: bool = False,
    ) -> tuple[str, ...]:
        if code == 'PUBLISHED_OTHER':
            if not federal_district:
                return tuple(PUBLISHED_OTHER_CLASSES)
            published = set(
                self.bundle.federal_district_okved2_grid[
                    'activity_code'
                ].astype(str)
            ) - {'PUBLISHED_OTHER'}
            return tuple(
                self.classes.loc[
                    ~self.classes['section_code'].astype(str).isin(published),
                    'class_code',
                ].astype(str)
            )
        if federal_district:
            return tuple(
                self.classes.loc[
                    self.classes['section_code'].astype(str).eq(code),
                    'class_code',
                ].astype(str)
            )
        return (code,)

    def _legacy_rows(self) -> None:
        all_regions = tuple(self.regions['region_code'].astype(str))
        for frame in (
            self.bundle.regional_traditional_grid,
            self.bundle.national_traditional_grid,
        ):
            for row in frame.itertuples(index=False):
                activity_code = str(row.activity_code)
                if activity_code not in self.node_atoms:
                    raise ValueError(
                        f'Legacy publication node {activity_code!r} is absent from '
                        'the atom membership registry'
                    )
                if str(row.source_series) == '01_05_A':
                    regions = self.geo_members[str(row.geography_node_id)]
                else:
                    regions = all_regions
                self.add(
                    self.legacy_expression(
                        regions,
                        self.node_atoms[activity_code],
                        str(row.metric),
                    ),
                    lower=float(row.published_lower),
                    upper=float(row.published_upper),
                    lower_attained=bool(row.published_lower_attained),
                    upper_attained=bool(row.published_upper_attained),
                    constraint_id=(
                        f'crosswalk:{self.scenario_id}:publication:'
                        f'{row.observation_id}'
                    ),
                    constraint_kind='LEGACY_PUBLICATION',
                    source_observation_ids=(str(row.observation_id),),
                    source_series=(str(row.source_series),),
                    model_layer='CROSSWALK',
                    scenario_id=self.scenario_id,
                    activity_code=activity_code,
                )

    def _okved_rows(self) -> None:
        all_regions = tuple(self.regions['region_code'].astype(str))
        for row in self.bundle.national_okved2_grid.itertuples(index=False):
            self.add(
                self.okved_expression(
                    all_regions,
                    self.publication_classes(str(row.activity_code)),
                    str(row.metric),
                ),
                lower=float(row.published_lower),
                upper=float(row.published_upper),
                lower_attained=bool(row.published_lower_attained),
                upper_attained=bool(row.published_upper_attained),
                constraint_id=(
                    f'crosswalk:{self.scenario_id}:publication:'
                    f'{row.observation_id}'
                ),
                constraint_kind='NATIONAL_OKVED2',
                source_observation_ids=(str(row.observation_id),),
                source_series=(str(row.source_series),),
                model_layer='CROSSWALK',
                scenario_id=self.scenario_id,
            )
        for row in self.bundle.federal_district_okved2_grid.itertuples(index=False):
            self.add(
                self.okved_expression(
                    self.fd_members[str(row.geography_node_id)],
                    self.publication_classes(
                        str(row.activity_code), federal_district=True
                    ),
                    str(row.metric),
                ),
                lower=float(row.published_lower),
                upper=float(row.published_upper),
                lower_attained=bool(row.published_lower_attained),
                upper_attained=bool(row.published_upper_attained),
                constraint_id=(
                    f'crosswalk:{self.scenario_id}:publication:'
                    f'{row.observation_id}'
                ),
                constraint_kind='FD_OKVED2',
                source_observation_ids=(str(row.observation_id),),
                source_series=(str(row.source_series),),
                model_layer='CROSSWALK',
                scenario_id=self.scenario_id,
            )

    def _strict_component_rows(self) -> None:
        if self.strict_bounds.empty:
            return
        for key, row in self.strict_bounds.iterrows():
            region, class_code, component = map(str, key)
            lower = float(row.lower_bound)
            upper = float(row.upper_bound)
            if lower <= 0.0 and not isfinite(upper):
                continue
            self.add(
                self.class_component_expression(region, class_code, component),
                lower=lower,
                upper=upper,
                lower_attained=bool(row.lower_attained),
                upper_attained=bool(row.upper_attained),
                constraint_id=(
                    f'crosswalk:{self.scenario_id}:strict-bound:'
                    f'{region}:{class_code}:{component}'
                ),
                constraint_kind='STRICT_COMPONENT_BOUND',
                source_observation_ids=(),
                source_series=(),
                model_layer='CROSSWALK',
                scenario_id=self.scenario_id,
            )

    def _column_upper_bounds(self) -> np.ndarray:
        upper = np.full(self.n, inf, dtype=float)
        if self.strict_bounds.empty:
            return upper
        for (region, class_code, component), row in self.strict_bounds.iterrows():
            semantic_upper = solver_upper_bound(
                float(row.upper_bound),
                bool(row.upper_attained),
                open_margin=self.config.point_tolerance,
            )
            if not isfinite(semantic_upper):
                continue
            for atom, target in self.pairs_by_class[str(class_code)]:
                column = self.flow(
                    str(region), atom, target, str(component)
                )
                upper[column] = min(upper[column], semantic_upper)
        return upper

    def _variables_grid(self, column_upper: np.ndarray) -> pd.DataFrame:
        edge_lookup = self.mapping_edges.set_index(
            ['atom_code', 'class_code']
        ).to_dict('index')
        records: list[dict[str, object]] = []
        for region in self.regions['region_code'].astype(str):
            for atom, class_code in self.allowed_pairs:
                edge = edge_lookup[(atom, class_code)]
                for component in COMPONENTS:
                    column = self.flow(region, atom, class_code, component)
                    records.append(
                        {
                            'solver_column': column,
                            'variable_kind': 'CROSSWALK_FLOW',
                            'scenario_id': self.scenario_id,
                            'region_code': region,
                            'atom_code': atom,
                            'class_code': class_code,
                            'component': component,
                            'edge_kind': edge['edge_kind'],
                            'evidence_type': edge['evidence_type'],
                            'lower_bound': 0.0,
                            'upper_bound': column_upper[column],
                        }
                    )
        return pd.DataFrame(records).sort_values('solver_column').reset_index(drop=True)

    def _target_catalog(self) -> pd.DataFrame:
        region_names = self.regions.set_index('region_code')[
            'region_name'
        ].astype(str).to_dict()
        records: list[dict[str, object]] = []
        for region in self.regions['region_code'].astype(str):
            for class_code in self.classes['class_code'].astype(str):
                for metric in METRIC_COMPONENTS:
                    items = self.class_expression(region, class_code, metric)
                    records.append(
                        {
                            'target_id': (
                                f'crosswalk:{self.scenario_id}:'
                                f'{region}:{class_code}:{metric}'
                            ),
                            'quantity_id': f'metric:{region}:{class_code}:{metric}',
                            'scenario_id': self.scenario_id,
                            'region_code': region,
                            'region_name': region_names[region],
                            'class_code': class_code,
                            'metric': metric,
                            'indices': np.asarray(
                                [column for column, _ in items], dtype=np.int32
                            ),
                            'coefficients': np.asarray(
                                [coefficient for _, coefficient in items], dtype=float
                            ),
                            'constant': 0.0,
                        }
                    )
        return pd.DataFrame(records)

    def build(self) -> CrosswalkCompilation:
        self._legacy_rows()
        self._okved_rows()
        self._strict_component_rows()
        column_upper = self._column_upper_bounds()
        problem = SorsLinearProblem(
            model_layer='CROSSWALK',
            matrix=self.matrix(self.n),
            row_lower=np.asarray(self.lower, dtype=float),
            row_upper=np.asarray(self.upper, dtype=float),
            col_lower=np.zeros(self.n, dtype=float),
            col_upper=column_upper,
            objective=np.zeros(self.n, dtype=float),
            constraints_grid=pd.DataFrame(self.meta),
            variables_grid=self._variables_grid(column_upper),
            metadata={
                'mapping_version': self.config.mapping_version,
                'scenario_id': self.scenario_id,
                'allowed_pairs': self.allowed_pairs,
                'point_tolerance': self.config.point_tolerance,
            },
        )
        return CrosswalkCompilation(
            problem=problem,
            target_catalog_grid=self._target_catalog(),
            mapping_edges_grid=self.mapping_edges,
            relations_grid=self.relations,
        )


def compile_crosswalk_problem(
    bundle: SorsSourceBundle,
    strict_components_grid: pd.DataFrame,
    config: SorsCrosswalkConfig,
    scenario_id: str,
) -> CrosswalkCompilation:
    return CrosswalkProblemBuilder(
        bundle,
        strict_components_grid,
        config,
        scenario_id,
    ).build()


def crosswalk_target(row: pd.Series) -> LinearTarget:
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
