from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsRunConfig, SorsSourceBundle
from stratbox.macrobanks.cbr_sors_restoration.mapping import (
    build_atom_class_edges,
    read_legacy_atoms,
    read_legacy_membership,
)
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
    model_layer: str
    matrix: CsrMatrixData
    row_lower: np.ndarray
    row_upper: np.ndarray
    col_lower: np.ndarray
    col_upper: np.ndarray
    objective: np.ndarray
    constraints_grid: pd.DataFrame
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def num_variables(self) -> int:
        return int(len(self.col_lower))


class _SparseProblemBuilder:
    def __init__(self) -> None:
        self.rows: list[list[tuple[int, float]]] = []
        self.row_lower: list[float] = []
        self.row_upper: list[float] = []
        self.row_meta: list[dict[str, object]] = []

    def add_row(
        self,
        items,
        *,
        lower: float,
        upper: float,
        constraint_id: str,
        constraint_kind: str,
        source_observation_id: str | None = None,
        source_series: str | None = None,
        model_layer: str,
    ) -> None:
        combined: dict[int, float] = {}
        for column, coefficient in items:
            column = int(column)
            combined[column] = combined.get(column, 0.0) + float(coefficient)
        row = [(column, coefficient) for column, coefficient in combined.items() if coefficient]
        if not row:
            raise ValueError(f'Constraint {constraint_id!r} has no variables')
        self.rows.append(row)
        self.row_lower.append(float(lower))
        self.row_upper.append(float(upper))
        self.row_meta.append({
            'constraint_id': constraint_id,
            'constraint_kind': constraint_kind,
            'model_layer': model_layer,
            'source_observation_id': source_observation_id,
            'source_series': source_series,
            'lower_bound': float(lower),
            'upper_bound': float(upper),
        })

    def matrix(self, n_columns: int) -> CsrMatrixData:
        indptr = [0]
        indices: list[int] = []
        data: list[float] = []
        for row in self.rows:
            for column, coefficient in sorted(row):
                indices.append(column)
                data.append(coefficient)
            indptr.append(len(indices))
        return CsrMatrixData(
            shape=(len(self.rows), n_columns),
            indptr=np.asarray(indptr, dtype=np.int64),
            indices=np.asarray(indices, dtype=np.int32),
            data=np.asarray(data, dtype=float),
        )


class _PublicationMixin:
    bundle: SorsSourceBundle
    regions: pd.DataFrame
    classes: pd.DataFrame
    geo_members: dict[str, tuple[str, ...]]

    def _class_codes_for_publication(self, code: str, *, fd: bool = False) -> tuple[str, ...]:
        if code == 'PUBLISHED_OTHER':
            if not fd:
                return self.bundle.published_other_classes
            published_sections = (
                set(self.bundle.fd_okved2_grid['activity_code'].astype(str))
                - {'PUBLISHED_OTHER'}
            )
            return tuple(
                self.classes.loc[
                    ~self.classes['section_code'].astype(str).isin(published_sections),
                    'class_code',
                ].astype(str)
            )
        if fd:
            return tuple(
                self.classes.loc[
                    self.classes['section_code'].astype(str).eq(code), 'class_code'
                ].astype(str)
            )
        return (code,)


class StrictProblemBuilder(_SparseProblemBuilder, _PublicationMixin):
    """Official-publication model without any legacy/OKVED2 mapping assumption."""

    def __init__(self, bundle: SorsSourceBundle):
        super().__init__()
        self.bundle = bundle
        self.regions = bundle.atomic_regions.reset_index(drop=True)
        self.classes = bundle.okved2_classes.reset_index(drop=True)
        self.region_positions = {
            code: i for i, code in enumerate(self.regions['region_code'].astype(str))
        }
        self.class_positions = {
            code: i for i, code in enumerate(self.classes['class_code'].astype(str))
        }
        self.component_positions = {name: i for i, name in enumerate(COMPONENTS)}
        self.geo_members = {
            row.geography_node_id: tuple(row.atomic_region_codes)
            for row in bundle.geography_nodes.itertuples(index=False)
        }
        self.n = len(self.regions) * len(self.classes) * len(COMPONENTS)

    def index(self, region_code: str, class_code: str, component: str) -> int:
        r = self.region_positions[region_code]
        c = self.class_positions[class_code]
        k = self.component_positions[component]
        return (r * len(self.classes) + c) * len(COMPONENTS) + k

    def expression(self, region_codes, class_codes, metric: str):
        return [
            (self.index(region, class_code, component), 1.0)
            for region in region_codes
            for class_code in class_codes
            for component in METRIC_COMPONENTS[metric]
        ]

    def _publication_rows(self) -> None:
        all_regions = tuple(self.regions['region_code'].astype(str))
        all_classes = tuple(self.classes['class_code'].astype(str))
        regional_total = self.bundle.regional_traditional_grid[
            self.bundle.regional_traditional_grid['activity_code'].astype(str).eq('total')
        ]
        for row in regional_total.itertuples(index=False):
            self.add_row(
                self.expression(
                    self.geo_members[str(row.geography_node_id)],
                    all_classes,
                    source_metric(row.measure, row.currency),
                ),
                lower=row.published_lower,
                upper=row.published_upper,
                constraint_id=f'strict:{row.observation_id}',
                constraint_kind='regional_total',
                source_observation_id=row.observation_id,
                source_series=row.source_series,
                model_layer='STRICT',
            )
        national_old_total = self.bundle.national_traditional_grid[
            self.bundle.national_traditional_grid['activity_code'].astype(str).eq('total')
        ]
        for row in national_old_total.itertuples(index=False):
            self.add_row(
                self.expression(
                    all_regions, all_classes, source_metric(row.measure, row.currency)
                ),
                lower=row.published_lower,
                upper=row.published_upper,
                constraint_id=f'strict:{row.observation_id}',
                constraint_kind='national_traditional_total',
                source_observation_id=row.observation_id,
                source_series=row.source_series,
                model_layer='STRICT',
            )
        for row in self.bundle.national_okved2_grid.itertuples(index=False):
            self.add_row(
                self.expression(
                    all_regions,
                    self._class_codes_for_publication(str(row.activity_code)),
                    source_metric(row.measure, row.currency),
                ),
                lower=row.published_lower,
                upper=row.published_upper,
                constraint_id=f'strict:{row.observation_id}',
                constraint_kind='national_okved2',
                source_observation_id=row.observation_id,
                source_series=row.source_series,
                model_layer='STRICT',
            )
        fd_members = {
            name: tuple(group['region_code'].astype(str))
            for name, group in self.regions.groupby('federal_district_name', sort=False)
        }
        for row in self.bundle.fd_okved2_grid.itertuples(index=False):
            self.add_row(
                self.expression(
                    fd_members[str(row.geography_name)],
                    self._class_codes_for_publication(str(row.activity_code), fd=True),
                    source_metric(row.measure, 'total'),
                ),
                lower=row.published_lower,
                upper=row.published_upper,
                constraint_id=f'strict:{row.observation_id}',
                constraint_kind='fd_okved2_section',
                source_observation_id=row.observation_id,
                source_series=row.source_series,
                model_layer='STRICT',
            )

    def build(self) -> SorsProblem:
        self._publication_rows()
        return SorsProblem(
            model_layer='STRICT',
            matrix=self.matrix(self.n),
            row_lower=np.asarray(self.row_lower, dtype=float),
            row_upper=np.asarray(self.row_upper, dtype=float),
            col_lower=np.zeros(self.n, dtype=float),
            col_upper=np.full(self.n, np.inf, dtype=float),
            objective=np.zeros(self.n, dtype=float),
            constraints_grid=pd.DataFrame(self.row_meta),
            metadata={
                'region_codes': tuple(self.regions['region_code'].astype(str)),
                'class_codes': tuple(self.classes['class_code'].astype(str)),
                'components': tuple(COMPONENTS),
            },
        )

    def target(self, region_name: str, class_code: str, metric: str) -> LinearTarget:
        region = self.regions.loc[
            self.regions['region_name'].astype(str).eq(region_name)
        ].iloc[0]
        indices = np.asarray([
            self.index(str(region.region_code), class_code, component)
            for component in METRIC_COMPONENTS[metric]
        ], dtype=np.int32)
        return LinearTarget(
            target_id=f'{region.region_code}:{class_code}:{metric}',
            region_name=region_name,
            region_code=str(region.region_code),
            class_code=class_code,
            metric=metric,
            indices=indices,
            coefficients=np.ones(len(indices), dtype=float),
        )


class BridgeFlowProblemBuilder(_SparseProblemBuilder, _PublicationMixin):
    """Conditional minimum-reclassification model in factorized form.

    Preferred atom/class flows are explicit. Mass that cannot use a preferred
    edge is represented by an atom-side residual and a class-side residual,
    balanced for every region and monetary component. This is mathematically
    equivalent, for the objective and all class totals, to a complete fallback
    atom/class transportation graph with unit penalty, while avoiding hundreds
    of thousands of explicit fallback variables.
    """

    def __init__(
        self,
        bundle: SorsSourceBundle,
        config: SorsRunConfig,
        mapping_edges: pd.DataFrame | None = None,
    ):
        super().__init__()
        self.bundle = bundle
        self.config = config
        self.regions = bundle.atomic_regions.reset_index(drop=True)
        self.classes = bundle.okved2_classes.reset_index(drop=True)
        self.atoms = read_legacy_atoms().reset_index(drop=True)
        self.membership = read_legacy_membership()
        self.mapping_edges = (
            build_atom_class_edges(bundle.okved2_classes, config.mapping_version)
            if mapping_edges is None else mapping_edges.copy()
        )
        preferred = self.mapping_edges[
            self.mapping_edges['is_preferred'].astype(bool)
        ].copy()
        atom_order = {
            code: i for i, code in enumerate(self.atoms['atom_code'].astype(str))
        }
        class_order = {
            code: i for i, code in enumerate(self.classes['class_code'].astype(str))
        }
        preferred['_atom_order'] = preferred['atom_code'].astype(str).map(atom_order)
        preferred['_class_order'] = preferred['class_code'].astype(str).map(class_order)
        preferred = preferred.sort_values(['_atom_order', '_class_order'])
        self.preferred_pairs = tuple(
            zip(
                preferred['atom_code'].astype(str),
                preferred['class_code'].astype(str),
                strict=True,
            )
        )
        self.pair_positions = {
            pair: i for i, pair in enumerate(self.preferred_pairs)
        }
        self.pairs_by_atom: dict[str, tuple[tuple[str, str], ...]] = {}
        self.pairs_by_class: dict[str, tuple[tuple[str, str], ...]] = {}
        for pair in self.preferred_pairs:
            self.pairs_by_atom.setdefault(pair[0], []).append(pair)
            self.pairs_by_class.setdefault(pair[1], []).append(pair)
        self.pairs_by_atom = {
            key: tuple(value) for key, value in self.pairs_by_atom.items()
        }
        self.pairs_by_class = {
            key: tuple(value) for key, value in self.pairs_by_class.items()
        }
        self.region_positions = {
            code: i for i, code in enumerate(self.regions['region_code'].astype(str))
        }
        self.atom_positions = {
            code: i for i, code in enumerate(self.atoms['atom_code'].astype(str))
        }
        self.class_positions = {
            code: i for i, code in enumerate(self.classes['class_code'].astype(str))
        }
        self.component_positions = {name: i for i, name in enumerate(COMPONENTS)}
        self.geo_members = {
            row.geography_node_id: tuple(row.atomic_region_codes)
            for row in bundle.geography_nodes.itertuples(index=False)
        }
        self.node_atoms = {
            node: tuple(group['atom_code'].astype(str))
            for node, group in self.membership.groupby('node_code', sort=False)
        }
        self.node_atoms['total'] = tuple(self.atoms['atom_code'].astype(str))
        self.n_regions = len(self.regions)
        self.n_atoms = len(self.atoms)
        self.n_classes = len(self.classes)
        self.n_components = len(COMPONENTS)
        self.n_pairs = len(self.preferred_pairs)
        self.atom_offset = 0
        self.preferred_offset = self.n_regions * self.n_atoms * self.n_components
        self.atom_residual_offset = (
            self.preferred_offset
            + self.n_regions * self.n_pairs * self.n_components
        )
        self.class_residual_offset = (
            self.atom_residual_offset
            + self.n_regions * self.n_atoms * self.n_components
        )
        self.n = (
            self.class_residual_offset
            + self.n_regions * self.n_classes * self.n_components
        )

    def y_index(self, region_code: str, atom_code: str, component: str) -> int:
        r = self.region_positions[region_code]
        a = self.atom_positions[atom_code]
        k = self.component_positions[component]
        return (r * self.n_atoms + a) * self.n_components + k

    def preferred_index(
        self,
        region_code: str,
        atom_code: str,
        class_code: str,
        component: str,
    ) -> int:
        r = self.region_positions[region_code]
        pair = self.pair_positions[(atom_code, class_code)]
        k = self.component_positions[component]
        return self.preferred_offset + (
            (r * self.n_pairs + pair) * self.n_components + k
        )

    def atom_residual_index(
        self, region_code: str, atom_code: str, component: str
    ) -> int:
        r = self.region_positions[region_code]
        a = self.atom_positions[atom_code]
        k = self.component_positions[component]
        return self.atom_residual_offset + (
            (r * self.n_atoms + a) * self.n_components + k
        )

    def class_residual_index(
        self, region_code: str, class_code: str, component: str
    ) -> int:
        r = self.region_positions[region_code]
        c = self.class_positions[class_code]
        k = self.component_positions[component]
        return self.class_residual_offset + (
            (r * self.n_classes + c) * self.n_components + k
        )

    def legacy_expression(self, region_codes, atom_codes, metric: str):
        return [
            (self.y_index(region, atom, component), 1.0)
            for region in region_codes
            for atom in atom_codes
            for component in METRIC_COMPONENTS[metric]
        ]

    def class_expression(self, region_code: str, class_code: str, metric: str):
        items = [
            (
                self.preferred_index(region_code, atom, class_code, component),
                1.0,
            )
            for atom, _ in self.pairs_by_class.get(class_code, ())
            for component in METRIC_COMPONENTS[metric]
        ]
        items.extend(
            (
                self.class_residual_index(region_code, class_code, component),
                1.0,
            )
            for component in METRIC_COMPONENTS[metric]
        )
        return items

    def okved_expression(self, region_codes, class_codes, metric: str):
        return [
            item
            for region in region_codes
            for class_code in class_codes
            for item in self.class_expression(region, class_code, metric)
        ]

    def _flow_rows(self) -> None:
        for region in self.regions['region_code'].astype(str):
            for atom in self.atoms['atom_code'].astype(str):
                pairs = self.pairs_by_atom.get(atom, ())
                for component in COMPONENTS:
                    items = [(self.y_index(region, atom, component), 1.0)]
                    items.extend(
                        (
                            self.preferred_index(
                                region, pair[0], pair[1], component
                            ),
                            -1.0,
                        )
                        for pair in pairs
                    )
                    items.append(
                        (
                            self.atom_residual_index(region, atom, component),
                            -1.0,
                        )
                    )
                    self.add_row(
                        items,
                        lower=0.0,
                        upper=0.0,
                        constraint_id=f'bridge-link:{region}:{atom}:{component}',
                        constraint_kind='atom_preferred_flow_conservation',
                        model_layer='CONDITIONAL_BRIDGE',
                    )
            for component in COMPONENTS:
                items = [
                    (
                        self.atom_residual_index(region, atom, component),
                        1.0,
                    )
                    for atom in self.atoms['atom_code'].astype(str)
                ]
                items.extend(
                    (
                        self.class_residual_index(region, class_code, component),
                        -1.0,
                    )
                    for class_code in self.classes['class_code'].astype(str)
                )
                self.add_row(
                    items,
                    lower=0.0,
                    upper=0.0,
                    constraint_id=f'bridge-residual-balance:{region}:{component}',
                    constraint_kind='fallback_mass_balance',
                    model_layer='CONDITIONAL_BRIDGE',
                )

    def _legacy_rows(self) -> None:
        for frame in (
            self.bundle.regional_traditional_grid,
            self.bundle.national_traditional_grid,
        ):
            for row in frame.itertuples(index=False):
                region_codes = (
                    self.geo_members[str(row.geography_node_id)]
                    if row.source_series == '01_05_A'
                    else tuple(self.regions['region_code'].astype(str))
                )
                atom_codes = self.node_atoms[str(row.activity_code)]
                self.add_row(
                    self.legacy_expression(
                        region_codes,
                        atom_codes,
                        source_metric(row.measure, row.currency),
                    ),
                    lower=row.published_lower,
                    upper=row.published_upper,
                    constraint_id=f'bridge-hard:{row.observation_id}',
                    constraint_kind='legacy_publication',
                    source_observation_id=row.observation_id,
                    source_series=row.source_series,
                    model_layer='CONDITIONAL_BRIDGE',
                )

    def _okved_rows(self) -> None:
        all_regions = tuple(self.regions['region_code'].astype(str))
        for row in self.bundle.national_okved2_grid.itertuples(index=False):
            self.add_row(
                self.okved_expression(
                    all_regions,
                    self._class_codes_for_publication(str(row.activity_code)),
                    source_metric(row.measure, row.currency),
                ),
                lower=row.published_lower,
                upper=row.published_upper,
                constraint_id=f'bridge-hard:{row.observation_id}',
                constraint_kind='national_okved2',
                source_observation_id=row.observation_id,
                source_series=row.source_series,
                model_layer='CONDITIONAL_BRIDGE',
            )
        fd_members = {
            name: tuple(group['region_code'].astype(str))
            for name, group in self.regions.groupby('federal_district_name', sort=False)
        }
        for row in self.bundle.fd_okved2_grid.itertuples(index=False):
            self.add_row(
                self.okved_expression(
                    fd_members[str(row.geography_name)],
                    self._class_codes_for_publication(str(row.activity_code), fd=True),
                    source_metric(row.measure, 'total'),
                ),
                lower=row.published_lower,
                upper=row.published_upper,
                constraint_id=f'bridge-hard:{row.observation_id}',
                constraint_kind='fd_okved2_section',
                source_observation_id=row.observation_id,
                source_series=row.source_series,
                model_layer='CONDITIONAL_BRIDGE',
            )

    def build(self) -> SorsProblem:
        self._flow_rows()
        self._legacy_rows()
        self._okved_rows()
        objective = np.zeros(self.n, dtype=float)
        objective[
            self.atom_residual_offset:self.class_residual_offset
        ] = 1.0
        return SorsProblem(
            model_layer='CONDITIONAL_BRIDGE',
            matrix=self.matrix(self.n),
            row_lower=np.asarray(self.row_lower, dtype=float),
            row_upper=np.asarray(self.row_upper, dtype=float),
            col_lower=np.zeros(self.n, dtype=float),
            col_upper=np.full(self.n, np.inf, dtype=float),
            objective=objective,
            constraints_grid=pd.DataFrame(self.row_meta),
            metadata={
                'region_codes': tuple(self.regions['region_code'].astype(str)),
                'atom_codes': tuple(self.atoms['atom_code'].astype(str)),
                'class_codes': tuple(self.classes['class_code'].astype(str)),
                'components': tuple(COMPONENTS),
                'preferred_pairs': self.preferred_pairs,
                'atom_offset': self.atom_offset,
                'preferred_offset': self.preferred_offset,
                'atom_residual_offset': self.atom_residual_offset,
                'class_residual_offset': self.class_residual_offset,
            },
        )

    def target(self, region_name: str, class_code: str, metric: str) -> LinearTarget:
        region = self.regions.loc[
            self.regions['region_name'].astype(str).eq(region_name)
        ].iloc[0]
        items = self.class_expression(
            str(region.region_code), class_code, metric
        )
        return LinearTarget(
            target_id=f'{region.region_code}:{class_code}:{metric}',
            region_name=region_name,
            region_code=str(region.region_code),
            class_code=class_code,
            metric=metric,
            indices=np.asarray([item[0] for item in items], dtype=np.int32),
            coefficients=np.asarray([item[1] for item in items], dtype=float),
        )


def build_strict_problem(bundle: SorsSourceBundle) -> tuple[SorsProblem, StrictProblemBuilder]:
    builder = StrictProblemBuilder(bundle)
    return builder.build(), builder


def build_bridge_flow_problem(
    bundle: SorsSourceBundle,
    config: SorsRunConfig,
    mapping_edges: pd.DataFrame | None = None,
) -> tuple[SorsProblem, BridgeFlowProblemBuilder]:
    builder = BridgeFlowProblemBuilder(bundle, config, mapping_edges)
    return builder.build(), builder
