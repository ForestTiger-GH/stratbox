from __future__ import annotations

from dataclasses import dataclass
from math import floor, isfinite

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsCellResolutionConfig,
    SorsSourceBundle,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.schema import COMPONENTS
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
    component_quantity_id,
)

COMPONENT_NAMES_RU = {
    'performing_rub': 'Рубли без просрочки',
    'overdue_rub': 'Рубли просроченные',
    'performing_fx': 'Валюта без просрочки',
    'overdue_fx': 'Валюта просроченная',
}
COMPONENT_ORDER = {component: index for index, component in enumerate(COMPONENTS)}


@dataclass(frozen=True, slots=True)
class SorsCellSelection:
    region_codes: frozenset[str]
    class_codes: frozenset[str]
    components: frozenset[str]


def resolve_cell_scope(
    bundle: SorsSourceBundle,
    config: SorsCellResolutionConfig,
) -> SorsCellSelection:
    scope = config.scope
    regions = bundle.atomic_regions_grid
    selected_regions = set(scope.region_codes)
    if scope.region_names:
        by_name = regions.set_index('region_name')['region_code'].astype(str).to_dict()
        missing = sorted(set(scope.region_names) - set(by_name))
        if missing:
            raise ValueError(f'Unknown SORS region names: {missing}')
        selected_regions.update(by_name[name] for name in scope.region_names)
    known_regions = set(regions['region_code'].astype(str))
    missing_regions = sorted(selected_regions - known_regions)
    if missing_regions:
        raise ValueError(f'Unknown SORS region codes: {missing_regions}')
    if not selected_regions:
        selected_regions = known_regions

    known_classes = set(bundle.okved2_classes_grid['class_code'].astype(str))
    selected_classes = set(scope.class_codes) or known_classes
    missing_classes = sorted(selected_classes - known_classes)
    if missing_classes:
        raise ValueError(f'Unknown SORS class codes: {missing_classes}')
    return SorsCellSelection(
        region_codes=frozenset(selected_regions),
        class_codes=frozenset(selected_classes),
        components=frozenset(scope.components),
    )


def build_cell_target_catalog(
    bundle: SorsSourceBundle,
    quantities_grid: pd.DataFrame,
    variables_grid: pd.DataFrame,
) -> pd.DataFrame:
    quantities = quantities_grid.set_index('quantity_id', drop=False)
    variable_lookup = variables_grid.set_index('quantity_id')[
        ['solver_column', 'connected_component_id', 'is_fixed', 'fixed_value']
    ]
    rows: list[dict[str, object]] = []
    regions = bundle.atomic_regions_grid.sort_values('region_order')
    classes = bundle.okved2_classes_grid.sort_values('class_order')
    for region in regions.itertuples(index=False):
        for activity in classes.itertuples(index=False):
            for component in COMPONENTS:
                quantity_id = component_quantity_id(
                    str(region.region_code), str(activity.class_code), component
                )
                quantity = quantities.loc[quantity_id]
                variable = variable_lookup.loc[quantity_id]
                rows.append(
                    {
                        'target_id': (
                            f'{region.region_code}:{activity.class_code}:{component}'
                        ),
                        'quantity_id': quantity_id,
                        'region_code': str(region.region_code),
                        'region_name': str(region.region_name),
                        'region_order': int(region.region_order),
                        'federal_district_code': str(region.federal_district_code),
                        'federal_district_name': str(region.federal_district_name),
                        'federal_district_order': int(region.federal_district_order),
                        'class_code': str(activity.class_code),
                        'class_name': str(activity.class_name),
                        'class_order': int(activity.class_order),
                        'section_code': str(activity.section_code),
                        'section_name': str(activity.section_name),
                        'section_order': int(activity.section_order),
                        'publication_category_code': str(
                            activity.publication_category_code
                        ),
                        'component': component,
                        'component_name': COMPONENT_NAMES_RU[component],
                        'component_order': COMPONENT_ORDER[component],
                        'solver_column': variable.solver_column,
                        'connected_component_id': variable.connected_component_id,
                        'initially_fixed': bool(variable.is_fixed),
                        'initial_fixed_value': variable.fixed_value,
                        'lower_bound': float(quantity.lower_bound),
                        'upper_bound': float(quantity.upper_bound),
                        'lower_attained': bool(quantity.lower_attained),
                        'upper_attained': bool(quantity.upper_attained),
                    }
                )
    return pd.DataFrame(rows).sort_values(
        ['region_order', 'class_order', 'component_order'], kind='stable'
    ).reset_index(drop=True)


def _relation_unknown_counts(
    quantities_grid: pd.DataFrame,
    relations_grid: pd.DataFrame,
    *,
    point_tolerance: float,
) -> tuple[dict[str, int], dict[str, float], dict[str, int]]:
    bounds = quantities_grid.set_index('quantity_id')[['lower_bound', 'upper_bound']]
    fixed = (
        bounds['upper_bound'].astype(float) - bounds['lower_bound'].astype(float)
    ).abs().le(point_tolerance)
    fixed_map = fixed.to_dict()
    unknown_min: dict[str, int] = {}
    cascade_score: dict[str, float] = {}
    adjacent_count: dict[str, int] = {}
    for relation in relations_grid.itertuples(index=False):
        members = (
            str(relation.parent_quantity_id),
            *tuple(str(value) for value in relation.child_quantity_ids),
        )
        unresolved = sum(not bool(fixed_map.get(member, False)) for member in members)
        score = 1.0 / max(unresolved, 1)
        for member in members:
            adjacent_count[member] = adjacent_count.get(member, 0) + 1
            unknown_min[member] = min(unknown_min.get(member, 10**9), unresolved)
            cascade_score[member] = cascade_score.get(member, 0.0) + score
    return unknown_min, cascade_score, adjacent_count


def build_cell_work_plan(
    bundle: SorsSourceBundle,
    target_catalog_grid: pd.DataFrame,
    quantities_grid: pd.DataFrame,
    relations_grid: pd.DataFrame,
    config: SorsCellResolutionConfig,
    policy: RoundingPolicy,
    *,
    attempted_counts: dict[str, int] | None = None,
    completed_ids: set[str] | None = None,
    point_tolerance: float = 1e-9,
) -> pd.DataFrame:
    attempted_counts = attempted_counts or {}
    completed_ids = completed_ids or set()
    selection = resolve_cell_scope(bundle, config)
    bounds = quantities_grid.set_index('quantity_id')[
        ['lower_bound', 'upper_bound', 'lower_attained', 'upper_attained']
    ]
    plan = target_catalog_grid.drop(
        columns=['lower_bound', 'upper_bound', 'lower_attained', 'upper_attained'],
        errors='ignore',
    ).merge(
        bounds,
        left_on='quantity_id',
        right_index=True,
        how='left',
        validate='one_to_one',
    )
    plan['published_bucket'] = [
        policy.single_bucket(
            float(row.lower_bound),
            float(row.upper_bound),
            lower_attained=bool(row.lower_attained),
            upper_attained=bool(row.upper_attained),
        )
        for row in plan.itertuples(index=False)
    ]
    plan['already_identified'] = plan['published_bucket'].notna()
    plan['attempt_count'] = plan['target_id'].map(attempted_counts).fillna(0).astype(int)
    plan['completed'] = plan['target_id'].astype(str).isin(completed_ids)
    in_scope = (
        plan['region_code'].astype(str).isin(selection.region_codes)
        & plan['class_code'].astype(str).isin(selection.class_codes)
        & plan['component'].astype(str).isin(selection.components)
    )
    eligible = (
        in_scope
        & ~plan['already_identified'].astype(bool)
        & ~plan['completed'].astype(bool)
        & plan['attempt_count'].lt(config.max_attempts_per_target)
    )
    unknown_min, cascade_score, adjacent_count = _relation_unknown_counts(
        quantities_grid,
        relations_grid,
        point_tolerance=point_tolerance,
    )
    plan['minimum_relation_unknowns'] = plan['quantity_id'].map(unknown_min).fillna(10**9)
    plan['cascade_score'] = plan['quantity_id'].map(cascade_score).fillna(0.0)
    plan['adjacent_relation_count'] = plan['quantity_id'].map(adjacent_count).fillna(0)

    def interval_bucket_count(row) -> int:
        lower = float(row.lower_bound)
        upper = float(row.upper_bound)
        if not isfinite(upper):
            return 10**12
        lower_bucket = floor(lower / policy.step + 0.5)
        upper_bucket = floor(upper / policy.step + 0.5)
        return max(1, upper_bucket - lower_bucket + 1)

    plan['bucket_count'] = [interval_bucket_count(row) for row in plan.itertuples(index=False)]
    plan['priority'] = (
        plan['minimum_relation_unknowns'].astype(float) * 1_000_000.0
        + plan['bucket_count'].astype(float)
        - plan['cascade_score'].astype(float) * 1_000.0
        - plan['adjacent_relation_count'].astype(float)
    )
    plan['selected'] = eligible
    plan['skip_reason'] = None
    plan.loc[~in_scope, 'skip_reason'] = 'OUTSIDE_SCOPE'
    plan.loc[in_scope & plan['already_identified'].astype(bool), 'skip_reason'] = (
        'ALREADY_IDENTIFIED'
    )
    plan.loc[
        in_scope & plan['attempt_count'].ge(config.max_attempts_per_target),
        'skip_reason',
    ] = 'TARGET_ATTEMPT_LIMIT'
    plan.loc[plan['completed'].astype(bool), 'skip_reason'] = 'COMPLETED'
    if config.mode == 'closure':
        plan['selected'] = False
        plan.loc[plan['skip_reason'].isna(), 'skip_reason'] = 'CLOSURE_ONLY_MODE'
    ordered = plan.sort_values(
        ['selected', 'priority', 'region_order', 'class_order', 'component_order'],
        ascending=[False, True, True, True, True],
        kind='stable',
    ).reset_index(drop=True)
    ordered['selection_order'] = None
    selected_index = ordered.index[ordered['selected'].astype(bool)]
    ordered.loc[selected_index, 'selection_order'] = range(len(selected_index))
    return ordered
