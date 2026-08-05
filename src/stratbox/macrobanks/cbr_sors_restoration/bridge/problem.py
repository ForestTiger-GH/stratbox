from __future__ import annotations

from dataclasses import dataclass
from math import inf, isfinite

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.bridge.mapping import (
    build_atom_class_edges,
    read_legacy_atoms,
    read_legacy_membership,
)
from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsBridgeConfig,
    SorsSourceBundle,
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
class BridgeCompilation:
    problem: SorsLinearProblem
    target_catalog_grid: pd.DataFrame
    mapping_edges_grid: pd.DataFrame


class _SparseBuilder:
    def __init__(self) -> None:
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
        lower = solver_lower_bound(semantic_lower, lower_attained)
        upper = solver_upper_bound(semantic_upper, upper_attained)
        combined: dict[int, float] = {}
        for column, coefficient in items:
            combined[int(column)] = combined.get(int(column), 0.0) + float(coefficient)
        row = sorted((column, value) for column, value in combined.items() if value)
        if not row:
            if lower <= 0 <= upper:
                return
            raise ValueError(f'Empty bridge constraint is inconsistent: {meta}')
        self.rows.append(row)
        self.lower.append(float(lower))
        self.upper.append(float(upper))
        self.meta.append(
            dict(
                meta,
                lower_bound=semantic_lower,
                upper_bound=semantic_upper,
                lower_attained=bool(lower_attained),
                upper_attained=bool(upper_attained),
                solver_lower_bound=float(lower),
                solver_upper_bound=float(upper),
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


class BridgeProblemBuilder(_SparseBuilder):
    def __init__(
        self,
        bundle: SorsSourceBundle,
        strict_components_grid: pd.DataFrame,
        config: SorsBridgeConfig,
    ) -> None:
        super().__init__()
        self.bundle = bundle
        self.config = config
        self.regions = bundle.atomic_regions_grid.sort_values('region_order').reset_index(drop=True)
        self.classes = bundle.okved2_classes_grid.sort_values('class_order').reset_index(drop=True)
        self.atoms = read_legacy_atoms().reset_index(drop=True)
        self.membership = read_legacy_membership()
        self.mapping_edges = build_atom_class_edges(self.classes, config.mapping_version)
        preferred = self.mapping_edges[self.mapping_edges['is_preferred'].astype(bool)].copy()
        atom_order = {code: i for i, code in enumerate(self.atoms['atom_code'].astype(str))}
        class_order = {code: i for i, code in enumerate(self.classes['class_code'].astype(str))}
        preferred['_a'] = preferred['atom_code'].astype(str).map(atom_order)
        preferred['_c'] = preferred['class_code'].astype(str).map(class_order)
        preferred = preferred.sort_values(['_a', '_c'], kind='stable')
        self.preferred_pairs = tuple(zip(preferred['atom_code'].astype(str), preferred['class_code'].astype(str), strict=True))
        self.pair_positions = {pair: i for i, pair in enumerate(self.preferred_pairs)}
        self.pairs_by_atom: dict[str, list[tuple[str, str]]] = {}
        self.pairs_by_class: dict[str, list[tuple[str, str]]] = {}
        for pair in self.preferred_pairs:
            self.pairs_by_atom.setdefault(pair[0], []).append(pair)
            self.pairs_by_class.setdefault(pair[1], []).append(pair)
        self.region_positions = {code: i for i, code in enumerate(self.regions['region_code'].astype(str))}
        self.atom_positions = {code: i for i, code in enumerate(self.atoms['atom_code'].astype(str))}
        self.class_positions = {code: i for i, code in enumerate(self.classes['class_code'].astype(str))}
        self.component_positions = {name: i for i, name in enumerate(COMPONENTS)}
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
            for code, group in self.regions.groupby('federal_district_code', sort=False)
        }
        self.strict_bounds = strict_components_grid.set_index(['region_code', 'class_code', 'component'])
        self.n_regions = len(self.regions)
        self.n_atoms = len(self.atoms)
        self.n_classes = len(self.classes)
        self.n_components = len(COMPONENTS)
        self.n_pairs = len(self.preferred_pairs)
        self.y_offset = 0
        self.preferred_offset = self.n_regions * self.n_atoms * self.n_components
        self.atom_residual_offset = self.preferred_offset + self.n_regions * self.n_pairs * self.n_components
        self.class_residual_offset = self.atom_residual_offset + self.n_regions * self.n_atoms * self.n_components
        self.n = self.class_residual_offset + self.n_regions * self.n_classes * self.n_components

    def y(self, region: str, atom: str, component: str) -> int:
        return ((self.region_positions[region] * self.n_atoms + self.atom_positions[atom]) * self.n_components + self.component_positions[component])

    def preferred(self, region: str, atom: str, class_code: str, component: str) -> int:
        return self.preferred_offset + ((self.region_positions[region] * self.n_pairs + self.pair_positions[(atom, class_code)]) * self.n_components + self.component_positions[component])

    def atom_residual(self, region: str, atom: str, component: str) -> int:
        return self.atom_residual_offset + ((self.region_positions[region] * self.n_atoms + self.atom_positions[atom]) * self.n_components + self.component_positions[component])

    def class_residual(self, region: str, class_code: str, component: str) -> int:
        return self.class_residual_offset + ((self.region_positions[region] * self.n_classes + self.class_positions[class_code]) * self.n_components + self.component_positions[component])

    def class_component_expression(self, region: str, class_code: str, component: str):
        items = [
            (self.preferred(region, atom, class_code, component), 1.0)
            for atom, _ in self.pairs_by_class.get(class_code, ())
        ]
        items.append((self.class_residual(region, class_code, component), 1.0))
        return items

    def class_expression(self, region: str, class_code: str, metric: str):
        return [item for component in METRIC_COMPONENTS[metric] for item in self.class_component_expression(region, class_code, component)]

    def legacy_expression(self, regions, atoms, metric: str):
        return [(self.y(region, atom, component), 1.0) for region in regions for atom in atoms for component in METRIC_COMPONENTS[metric]]

    def okved_expression(self, regions, classes, metric: str):
        return [item for region in regions for class_code in classes for item in self.class_expression(region, class_code, metric)]

    def publication_classes(self, code: str, *, fd: bool = False) -> tuple[str, ...]:
        if code == 'PUBLISHED_OTHER':
            if not fd:
                return tuple(PUBLISHED_OTHER_CLASSES)
            published = set(self.bundle.federal_district_okved2_grid['activity_code'].astype(str)) - {'PUBLISHED_OTHER'}
            return tuple(self.classes.loc[~self.classes['section_code'].astype(str).isin(published), 'class_code'].astype(str))
        if fd:
            return tuple(self.classes.loc[self.classes['section_code'].astype(str).eq(code), 'class_code'].astype(str))
        return (code,)

    def _flow_rows(self) -> None:
        for region in self.regions['region_code'].astype(str):
            for atom in self.atoms['atom_code'].astype(str):
                for component in COMPONENTS:
                    items = [(self.y(region, atom, component), 1.0)]
                    items.extend((self.preferred(region, a, c, component), -1.0) for a, c in self.pairs_by_atom.get(atom, ()))
                    items.append((self.atom_residual(region, atom, component), -1.0))
                    self.add(items, lower=0.0, upper=0.0, constraint_id=f'bridge:flow:{region}:{atom}:{component}', constraint_kind='ATOM_FLOW', model_layer='CONDITIONAL_BRIDGE')
            for component in COMPONENTS:
                items = [(self.atom_residual(region, atom, component), 1.0) for atom in self.atoms['atom_code'].astype(str)]
                items.extend((self.class_residual(region, class_code, component), -1.0) for class_code in self.classes['class_code'].astype(str))
                self.add(items, lower=0.0, upper=0.0, constraint_id=f'bridge:residual:{region}:{component}', constraint_kind='RESIDUAL_BALANCE', model_layer='CONDITIONAL_BRIDGE')

    def _legacy_rows(self) -> None:
        for frame in (self.bundle.regional_traditional_grid, self.bundle.national_traditional_grid):
            for row in frame.itertuples(index=False):
                regions = self.geo_members[str(row.geography_node_id)] if str(row.source_series) == '01_05_A' else tuple(self.regions['region_code'].astype(str))
                atoms = self.node_atoms[str(row.activity_code)]
                self.add(self.legacy_expression(regions, atoms, str(row.metric)), lower=float(row.published_lower), upper=float(row.published_upper), lower_attained=bool(row.published_lower_attained), upper_attained=bool(row.published_upper_attained), constraint_id=f'bridge:publication:{row.observation_id}', constraint_kind='LEGACY_PUBLICATION', source_observation_ids=(str(row.observation_id),), source_series=(str(row.source_series),), model_layer='CONDITIONAL_BRIDGE')

    def _okved_rows(self) -> None:
        all_regions = tuple(self.regions['region_code'].astype(str))
        for row in self.bundle.national_okved2_grid.itertuples(index=False):
            self.add(self.okved_expression(all_regions, self.publication_classes(str(row.activity_code)), str(row.metric)), lower=float(row.published_lower), upper=float(row.published_upper), lower_attained=bool(row.published_lower_attained), upper_attained=bool(row.published_upper_attained), constraint_id=f'bridge:publication:{row.observation_id}', constraint_kind='NATIONAL_OKVED2', source_observation_ids=(str(row.observation_id),), source_series=(str(row.source_series),), model_layer='CONDITIONAL_BRIDGE')
        for row in self.bundle.federal_district_okved2_grid.itertuples(index=False):
            self.add(self.okved_expression(self.fd_members[str(row.geography_node_id)], self.publication_classes(str(row.activity_code), fd=True), str(row.metric)), lower=float(row.published_lower), upper=float(row.published_upper), lower_attained=bool(row.published_lower_attained), upper_attained=bool(row.published_upper_attained), constraint_id=f'bridge:publication:{row.observation_id}', constraint_kind='FD_OKVED2', source_observation_ids=(str(row.observation_id),), source_series=(str(row.source_series),), model_layer='CONDITIONAL_BRIDGE')

    def _strict_component_rows(self) -> None:
        for key, row in self.strict_bounds.iterrows():
            region, class_code, component = map(str, key)
            lower = float(row.lower_bound)
            upper = float(row.upper_bound)
            if lower <= 0.0 and not isfinite(upper):
                continue
            self.add(self.class_component_expression(region, class_code, component), lower=lower, upper=upper, lower_attained=bool(row.lower_attained), upper_attained=bool(row.upper_attained), constraint_id=f'bridge:strict-bound:{region}:{class_code}:{component}', constraint_kind='STRICT_COMPONENT_BOUND', source_observation_ids=(), source_series=(), model_layer='CONDITIONAL_BRIDGE')

    def _variables_grid(self, col_upper: np.ndarray) -> pd.DataFrame:
        records: list[dict[str, object]] = []
        for region in self.regions['region_code'].astype(str):
            for atom in self.atoms['atom_code'].astype(str):
                for component in COMPONENTS:
                    records.append({'solver_column': self.y(region, atom, component), 'variable_kind': 'LEGACY_ATOM', 'region_code': region, 'atom_code': atom, 'class_code': None, 'component': component})
            for atom, class_code in self.preferred_pairs:
                for component in COMPONENTS:
                    records.append({'solver_column': self.preferred(region, atom, class_code, component), 'variable_kind': 'PREFERRED_FLOW', 'region_code': region, 'atom_code': atom, 'class_code': class_code, 'component': component})
            for atom in self.atoms['atom_code'].astype(str):
                for component in COMPONENTS:
                    records.append({'solver_column': self.atom_residual(region, atom, component), 'variable_kind': 'ATOM_RESIDUAL', 'region_code': region, 'atom_code': atom, 'class_code': None, 'component': component})
            for class_code in self.classes['class_code'].astype(str):
                for component in COMPONENTS:
                    records.append({'solver_column': self.class_residual(region, class_code, component), 'variable_kind': 'CLASS_RESIDUAL', 'region_code': region, 'atom_code': None, 'class_code': class_code, 'component': component})
        out = pd.DataFrame(records).sort_values('solver_column').reset_index(drop=True)
        out['lower_bound'] = 0.0
        out['upper_bound'] = col_upper
        return out

    def build(self) -> BridgeCompilation:
        self._flow_rows()
        self._legacy_rows()
        self._okved_rows()
        self._strict_component_rows()
        objective = np.zeros(self.n, dtype=float)
        objective[self.atom_residual_offset:self.class_residual_offset] = 1.0
        col_upper = np.full(self.n, inf, dtype=float)
        # Each non-negative class-side term cannot exceed the strict class/component upper bound.
        for (region, class_code, component), row in self.strict_bounds.iterrows():
            upper = solver_upper_bound(
                float(row.upper_bound), bool(row.upper_attained)
            )
            if isfinite(upper):
                for atom, _ in self.pairs_by_class.get(str(class_code), ()):
                    col_upper[self.preferred(str(region), atom, str(class_code), str(component))] = min(col_upper[self.preferred(str(region), atom, str(class_code), str(component))], upper)
                col_upper[self.class_residual(str(region), str(class_code), str(component))] = min(col_upper[self.class_residual(str(region), str(class_code), str(component))], upper)
        variables = self._variables_grid(col_upper)
        problem = SorsLinearProblem(model_layer='CONDITIONAL_BRIDGE', matrix=self.matrix(self.n), row_lower=np.asarray(self.lower, dtype=float), row_upper=np.asarray(self.upper, dtype=float), col_lower=np.zeros(self.n, dtype=float), col_upper=col_upper, objective=objective, constraints_grid=pd.DataFrame(self.meta), variables_grid=variables, metadata={'mapping_version': self.config.mapping_version, 'preferred_pairs': self.preferred_pairs})
        targets: list[dict[str, object]] = []
        region_names = self.regions.set_index('region_code')['region_name'].astype(str).to_dict()
        for region in self.regions['region_code'].astype(str):
            for class_code in self.classes['class_code'].astype(str):
                for metric in METRIC_COMPONENTS:
                    items = self.class_expression(region, class_code, metric)
                    targets.append({'target_id': f'bridge:{region}:{class_code}:{metric}', 'quantity_id': f'metric:{region}:{class_code}:{metric}', 'region_code': region, 'region_name': region_names[region], 'class_code': class_code, 'metric': metric, 'indices': np.asarray([i for i, _ in items], dtype=np.int32), 'coefficients': np.asarray([v for _, v in items], dtype=float), 'constant': 0.0})
        return BridgeCompilation(problem=problem, target_catalog_grid=pd.DataFrame(targets), mapping_edges_grid=self.mapping_edges)


def compile_bridge_problem(bundle: SorsSourceBundle, strict_components_grid: pd.DataFrame, config: SorsBridgeConfig) -> BridgeCompilation:
    return BridgeProblemBuilder(bundle, strict_components_grid, config).build()


def bridge_target(row: pd.Series) -> LinearTarget:
    return LinearTarget(target_id=str(row.target_id), quantity_id=str(row.quantity_id), region_code=str(row.region_code), region_name=str(row.region_name), class_code=str(row.class_code), metric=str(row.metric), indices=np.asarray(row.indices, dtype=np.int32), coefficients=np.asarray(row.coefficients, dtype=float), constant=float(row.constant))
