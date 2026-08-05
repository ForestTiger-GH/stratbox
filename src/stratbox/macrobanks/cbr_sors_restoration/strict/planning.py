from __future__ import annotations

from math import floor, isfinite

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsCertificationConfig,
    SorsSourceBundle,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    PublicationInterval,
    RoundingPolicy,
)


def _resolve_scope(
    bundle: SorsSourceBundle,
    config: SorsCertificationConfig,
) -> tuple[set[str], set[str], set[str]]:
    scope = config.scope
    regions = bundle.atomic_regions_grid
    selected_codes = set(scope.region_codes)
    if scope.region_names:
        by_name = regions.set_index('region_name')['region_code'].astype(str).to_dict()
        missing = sorted(set(scope.region_names) - set(by_name))
        if missing:
            raise ValueError(f'Unknown SORS region names: {missing}')
        selected_codes.update(by_name[name] for name in scope.region_names)
    known_region_codes = set(regions['region_code'].astype(str))
    missing_codes = sorted(selected_codes - known_region_codes)
    if missing_codes:
        raise ValueError(f'Unknown SORS region codes: {missing_codes}')
    if not selected_codes:
        selected_codes = known_region_codes

    known_classes = set(bundle.okved2_classes_grid['class_code'].astype(str))
    selected_classes = set(scope.class_codes) or known_classes
    missing_classes = sorted(selected_classes - known_classes)
    if missing_classes:
        raise ValueError(f'Unknown SORS class codes: {missing_classes}')
    return selected_codes, selected_classes, set(scope.metrics)


def build_certification_plan(
    bundle: SorsSourceBundle,
    target_catalog_grid: pd.DataFrame,
    quantities_grid: pd.DataFrame,
    config: SorsCertificationConfig,
    policy: RoundingPolicy,
) -> pd.DataFrame:
    quantity_bounds = quantities_grid.set_index('quantity_id')[
        ['lower_bound', 'upper_bound', 'lower_attained', 'upper_attained']
    ]
    plan = target_catalog_grid.merge(
        quantity_bounds,
        left_on='quantity_id',
        right_index=True,
        how='left',
        validate='one_to_one',
    )
    plan['initial_bucket'] = [
        policy.single_bucket_interval(
            PublicationInterval(
                float(row.lower_bound),
                float(row.upper_bound),
                bool(row.lower_attained),
                bool(row.upper_attained),
            )
        )
        for row in plan.itertuples(index=False)
    ]
    plan['already_identified'] = plan['initial_bucket'].notna()
    plan['selected'] = False
    plan['skip_reason'] = None
    plan['priority'] = 999999.0
    plan['priority_reason'] = None
    plan['batch_number'] = None

    if config.mode == 'closure':
        plan['skip_reason'] = 'CLOSURE_ONLY_MODE'
        return plan

    region_codes, class_codes, metrics = _resolve_scope(bundle, config)
    in_scope = (
        plan['region_code'].astype(str).isin(region_codes)
        & plan['class_code'].astype(str).isin(class_codes)
        & plan['metric'].astype(str).isin(metrics)
    )
    unresolved = ~plan['already_identified'].astype(bool)
    candidates = plan[in_scope & unresolved].copy()
    plan.loc[~in_scope, 'skip_reason'] = 'OUTSIDE_SCOPE'
    plan.loc[in_scope & ~unresolved, 'skip_reason'] = 'ALREADY_IDENTIFIED_BY_CLOSURE'

    if config.mode in {'targets', 'all'}:
        candidates['priority'] = 0.0
        candidates['priority_reason'] = 'EXPLICIT_SCOPE' if config.mode == 'targets' else 'EXHAUSTIVE'
    else:
        def score(row) -> tuple[float, str]:
            lower = float(row.lower_bound)
            upper = float(row.upper_bound)
            if not isfinite(upper):
                return 1e12, 'UNBOUNDED_UPPER'
            lower_bucket = floor(lower / policy.step + 0.5)
            upper_bucket = floor(upper / policy.step + 0.5)
            bucket_count = max(1, upper_bucket - lower_bucket + 1)
            positive_bonus = -1000.0 if lower > 0 else 0.0
            return bucket_count + positive_bonus, 'NARROW_INTERVAL'
        scored = [score(row) for row in candidates.itertuples(index=False)]
        candidates['priority'] = [item[0] for item in scored]
        candidates['priority_reason'] = [item[1] for item in scored]

    candidates = candidates.sort_values(
        ['priority', 'region_code', 'class_code', 'metric'],
        kind='stable',
    )
    if config.max_targets is not None:
        candidates = candidates.head(config.max_targets)
    selected_ids = set(candidates['target_id'].astype(str))
    plan.loc[plan['target_id'].astype(str).isin(selected_ids), 'selected'] = True
    plan.loc[
        in_scope & unresolved & ~plan['target_id'].astype(str).isin(selected_ids),
        'skip_reason',
    ] = 'BUDGET_LIMIT'
    plan = plan.merge(
        candidates[['target_id', 'priority', 'priority_reason']],
        on='target_id',
        how='left',
        suffixes=('', '_selected'),
    )
    plan['priority'] = plan['priority_selected'].fillna(plan['priority'])
    plan['priority_reason'] = plan['priority_reason_selected'].fillna(
        plan['priority_reason']
    )
    plan = plan.drop(columns=['priority_selected', 'priority_reason_selected'])
    selected_order = {
        target_id: position
        for position, target_id in enumerate(candidates['target_id'].astype(str))
    }
    plan['selection_order'] = plan['target_id'].map(selected_order)
    plan['batch_number'] = plan['selection_order'].map(
        lambda value: None
        if pd.isna(value)
        else int(value) // config.batch_size + 1
    )
    return plan.sort_values(
        ['selected', 'selection_order', 'target_id'],
        ascending=[False, True, True],
        kind='stable',
    ).reset_index(drop=True)
