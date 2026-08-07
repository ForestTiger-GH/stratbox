from __future__ import annotations

from dataclasses import dataclass, replace
from math import inf
import hashlib

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsSourceBundle
from stratbox.macrobanks.cbr_sors_restoration.metrics import METRIC_COMPONENTS
from stratbox.macrobanks.cbr_sors_restoration.portfolio import (
    PORTFOLIO_PARENT_SCOPE,
    PORTFOLIO_SCOPES,
    validate_portfolio_scopes,
)
from stratbox.macrobanks.cbr_sors_restoration.schema import COMPONENTS, TARGET_METRICS


@dataclass(frozen=True)
class SorsQuantityGraph:
    quantities_grid: pd.DataFrame
    relations_grid: pd.DataFrame
    observation_bindings_grid: pd.DataFrame


def component_quantity_id(
    portfolio_scope: str,
    region_code: str,
    class_code: str,
    component: str,
) -> str:
    return f'component:{portfolio_scope}:{region_code}:{class_code}:{component}'


def metric_quantity_id(
    portfolio_scope: str,
    region_code: str,
    class_code: str,
    metric: str,
) -> str:
    return f'metric:{portfolio_scope}:{region_code}:{class_code}:{metric}'


def _publication_quantity(row, country_node_id: str) -> tuple[str, str] | None:
    series = str(row.source_series)
    scope = str(row.portfolio_scope)
    metric = str(row.metric)
    if series in {'01_05_A', '01_05_D', '01_13_F', '01_13_I'}:
        if str(row.activity_code) != 'total':
            return None
        if str(row.geography_node_id) == country_node_id:
            return f'publication:{scope}:national_total:{metric}', 'NATIONAL_TOTAL'
        return (
            f'publication:{scope}:geography:{row.geography_node_id}:{metric}',
            'GEOGRAPHY_TOTAL',
        )
    if series in {'01_02_A', '01_11'}:
        if str(row.activity_code) != 'total':
            return None
        return f'publication:{scope}:national_total:{metric}', 'NATIONAL_TOTAL'
    if series in {'01_02_C', '01_11_F', '01_11_I'}:
        return (
            f'publication:{scope}:national_class:{row.activity_code}:{metric}',
            'NATIONAL_CLASS',
        )
    if series in {'01_03_C', '01_12_A'}:
        return (
            f'publication:{scope}:fd_section:{row.geography_node_id}:{row.activity_code}:{metric}',
            'FD_SECTION',
        )
    return None


def _intersection(records: pd.DataFrame) -> tuple[float, float, bool, bool]:
    lower = float(records['published_lower'].max())
    upper = float(records['published_upper'].min())
    lower_rows = records[records['published_lower'].astype(float).eq(lower)]
    upper_rows = records[records['published_upper'].astype(float).eq(upper)]
    lower_attained = bool(lower_rows['published_lower_attained'].astype(bool).all())
    upper_attained = bool(upper_rows['published_upper_attained'].astype(bool).all())
    if lower > upper or (lower == upper and not (lower_attained and upper_attained)):
        raise ValueError(
            'Conflicting publication intervals for observations '
            f'{tuple(records["observation_id"].astype(str))}'
        )
    return lower, upper, lower_attained, upper_attained


def _base_quantity_row(
    *,
    quantity_id: str,
    quantity_kind: str,
    portfolio_scope: str,
    region_code: str | None,
    class_code: str | None,
    component: str | None,
    metric: str | None,
    support_region_codes: tuple[str, ...],
    support_class_codes: tuple[str, ...],
    lower_bound: float = 0.0,
    upper_bound: float = inf,
    lower_attained: bool = True,
    upper_attained: bool = False,
) -> dict[str, object]:
    return {
        'quantity_id': quantity_id,
        'quantity_kind': quantity_kind,
        'portfolio_scope': portfolio_scope,
        'region_code': region_code,
        'class_code': class_code,
        'component': component,
        'metric': metric,
        'support_region_codes': support_region_codes,
        'support_class_codes': support_class_codes,
        'lower_bound': lower_bound,
        'upper_bound': upper_bound,
        'lower_attained': lower_attained,
        'upper_attained': upper_attained,
        'initial_lower_bound': lower_bound,
        'initial_upper_bound': upper_bound,
        'initial_lower_attained': lower_attained,
        'initial_upper_attained': upper_attained,
    }




def _stable_key(value: object) -> str:
    return hashlib.sha256(repr(value).encode('utf-8')).hexdigest()[:16]

def _dominance_relation(
    *,
    relation_id: str,
    parent_quantity_id: str,
    child_quantity_id: str,
    dominance_kind: str,
) -> dict[str, object]:
    """Represent ``child <= parent`` in the common relation graph."""
    return {
        'relation_id': relation_id,
        'relation_kind': 'DOMINANCE',
        'dominance_kind': dominance_kind,
        'parent_quantity_id': parent_quantity_id,
        'child_quantity_ids': (child_quantity_id,),
        'source_observation_ids': (),
    }


_METRIC_DOMINANCE = (
    ('debt_rub', 'overdue_rub'),
    ('debt_fx', 'overdue_fx'),
    ('debt_total', 'overdue_total'),
    ('debt_total', 'debt_rub'),
    ('debt_total', 'debt_fx'),
    ('overdue_total', 'overdue_rub'),
    ('overdue_total', 'overdue_fx'),
)


def build_quantity_graph(bundle: SorsSourceBundle) -> SorsQuantityGraph:
    regions = bundle.atomic_regions_grid.sort_values('region_order')
    classes = bundle.okved2_classes_grid.sort_values('class_order')
    scopes = validate_portfolio_scopes(
        set(bundle.source_grid['portfolio_scope'].dropna().astype(str))
    )
    quantity_rows: list[dict[str, object]] = []
    relation_rows: list[dict[str, object]] = []

    # All three hidden scopes use the same region × real-OKVED2 lattice.  SME and
    # SME_IE remain auxiliary: only CORPORATE_TOTAL becomes a user-facing target.
    for scope in scopes:
        for region in regions.itertuples(index=False):
            region_code = str(region.region_code)
            for activity in classes.itertuples(index=False):
                class_code = str(activity.class_code)
                for component in COMPONENTS:
                    quantity_rows.append(
                        _base_quantity_row(
                            quantity_id=component_quantity_id(scope, region_code, class_code, component),
                            quantity_kind='ATOMIC_COMPONENT',
                            portfolio_scope=scope,
                            region_code=region_code,
                            class_code=class_code,
                            component=component,
                            metric=None,
                            support_region_codes=(region_code,),
                            support_class_codes=(class_code,),
                        )
                    )
                for metric in TARGET_METRICS:
                    parent = metric_quantity_id(scope, region_code, class_code, metric)
                    quantity_rows.append(
                        _base_quantity_row(
                            quantity_id=parent,
                            quantity_kind='REGIONAL_CLASS_METRIC',
                            portfolio_scope=scope,
                            region_code=region_code,
                            class_code=class_code,
                            component=None,
                            metric=metric,
                            support_region_codes=(region_code,),
                            support_class_codes=(class_code,),
                        )
                    )
                    children = tuple(
                        component_quantity_id(scope, region_code, class_code, component)
                        for component in METRIC_COMPONENTS[metric]
                    )
                    relation_rows.append(
                        {
                            'relation_id': f'relation:{parent}',
                            'relation_kind': 'METRIC_COMPONENT_SUM',
                            'dominance_kind': None,
                            'parent_quantity_id': parent,
                            'child_quantity_ids': children,
                            'source_observation_ids': (),
                        }
                    )
                for parent_metric, child_metric in _METRIC_DOMINANCE:
                    relation_rows.append(
                        _dominance_relation(
                            relation_id=(
                                f'dominance:metric:{scope}:{region_code}:{class_code}:'
                                f'{child_metric}<={parent_metric}'
                            ),
                            parent_quantity_id=metric_quantity_id(scope, region_code, class_code, parent_metric),
                            child_quantity_id=metric_quantity_id(scope, region_code, class_code, child_metric),
                            dominance_kind='METRIC_MONOTONICITY',
                        )
                    )

    # Portfolio nesting is exact on every hidden component and therefore on every
    # regional/class metric.  Explicit metric inequalities accelerate deterministic
    # propagation; component inequalities are also compiled into the LP.
    for child_scope, parent_scope in PORTFOLIO_PARENT_SCOPE.items():
        for region in regions.itertuples(index=False):
            region_code = str(region.region_code)
            for activity in classes.itertuples(index=False):
                class_code = str(activity.class_code)
                for component in COMPONENTS:
                    relation_rows.append(
                        _dominance_relation(
                            relation_id=(
                                f'dominance:scope_component:{child_scope}<={parent_scope}:'
                                f'{region_code}:{class_code}:{component}'
                            ),
                            parent_quantity_id=component_quantity_id(parent_scope, region_code, class_code, component),
                            child_quantity_id=component_quantity_id(child_scope, region_code, class_code, component),
                            dominance_kind='PORTFOLIO_SCOPE_COMPONENT',
                        )
                    )
                for metric in TARGET_METRICS:
                    relation_rows.append(
                        _dominance_relation(
                            relation_id=(
                                f'dominance:scope_metric:{child_scope}<={parent_scope}:'
                                f'{region_code}:{class_code}:{metric}'
                            ),
                            parent_quantity_id=metric_quantity_id(parent_scope, region_code, class_code, metric),
                            child_quantity_id=metric_quantity_id(child_scope, region_code, class_code, metric),
                            dominance_kind='PORTFOLIO_SCOPE_METRIC',
                        )
                    )

    country_node = str(bundle.geography_nodes_grid.loc[
        bundle.geography_nodes_grid['geography_kind'].eq('country_total'),
        'geography_node_id',
    ].iloc[0])
    binding_rows: list[dict[str, object]] = []
    source = bundle.source_grid[~bundle.source_grid['source_series'].eq('01_05_D')].copy()
    publication_meta = [_publication_quantity(row, country_node) for row in source.itertuples(index=False)]
    source['_publication_quantity_id'] = [item[0] if item else None for item in publication_meta]
    source['_publication_axis'] = [item[1] if item else None for item in publication_meta]
    bound_source = source[source['_publication_quantity_id'].notna()].copy()

    for quantity_id, group in bound_source.groupby('_publication_quantity_id', sort=True):
        lower, upper, lower_attained, upper_attained = _intersection(group)
        first = group.iloc[0]
        representatives = tuple(sorted(set(group['value'].astype(float))))
        representative = representatives[0] if len(representatives) == 1 else None
        representative_status = 'STABLE' if representative is not None else 'MULTI_SOURCE_CONFLICT'
        quantity_rows.append({
            **_base_quantity_row(
                quantity_id=str(quantity_id),
                quantity_kind='PUBLISHED_AGGREGATE',
                portfolio_scope=str(first.portfolio_scope),
                region_code=None,
                class_code=None,
                component=None,
                metric=str(first.metric),
                support_region_codes=(),
                support_class_codes=(),
                lower_bound=lower,
                upper_bound=upper,
                lower_attained=lower_attained,
                upper_attained=upper_attained,
            ),
            'publication_axis': str(first._publication_axis),
            'publication_geography_node_id': str(first.geography_node_id),
            'publication_activity_code': str(first.activity_code),
            'published_representative': representative,
            'published_representative_status': representative_status,
            'published_representatives': representatives,
            'source_observation_ids': tuple(group['observation_id'].astype(str)),
            'source_series': tuple(group['source_series'].astype(str)),
        })
        for row in group.itertuples(index=False):
            binding_rows.append({
                'observation_id': str(row.observation_id),
                'quantity_id': str(quantity_id),
                'source_series': str(row.source_series),
                'portfolio_scope': str(row.portfolio_scope),
            })

    all_regions = tuple(regions['region_code'].astype(str))
    all_classes = tuple(classes['class_code'].astype(str))
    geo_members = {
        str(row.geography_node_id): tuple(str(v) for v in row.atomic_region_codes)
        for row in bundle.geography_nodes_grid.itertuples(index=False)
    }
    national_category_members = {
        str(code): tuple(group['member_class_code'].astype(str))
        for code, group in bundle.publication_categories_grid[
            bundle.publication_categories_grid['publication_level'].eq('NATIONAL_CLASS')
        ].groupby('publication_category_code', sort=False)
    }
    fd_category_members = {
        str(code): tuple(group['member_class_code'].astype(str))
        for code, group in bundle.publication_categories_grid[
            bundle.publication_categories_grid['publication_level'].eq('FD_SECTION')
        ].groupby('publication_category_code', sort=False)
    }
    fd_region_members = {
        str(code): tuple(group['region_code'].astype(str))
        for code, group in regions.groupby('federal_district_code', sort=False)
    }
    bindings = pd.DataFrame(binding_rows)
    binding_grouped = (
        bindings.groupby('quantity_id', sort=False)['observation_id'].agg(tuple).to_dict()
        if not bindings.empty else {}
    )

    # Give every publication aggregate its exact latent support and exact relation
    # to region×class metric quantities in the SAME portfolio scope.
    for item in quantity_rows:
        if item['quantity_kind'] != 'PUBLISHED_AGGREGATE':
            continue
        axis = str(item['publication_axis'])
        geo = str(item['publication_geography_node_id'])
        activity = str(item['publication_activity_code'])
        if axis == 'NATIONAL_TOTAL':
            region_codes, class_codes, kind = all_regions, all_classes, 'NATIONAL_TOTAL'
        elif axis == 'GEOGRAPHY_TOTAL':
            region_codes, class_codes, kind = geo_members[geo], all_classes, 'GEOGRAPHY_TOTAL'
        elif axis == 'NATIONAL_CLASS':
            region_codes, class_codes, kind = all_regions, national_category_members[activity], 'NATIONAL_CLASS'
        elif axis == 'FD_SECTION':
            region_codes, class_codes, kind = fd_region_members[geo], fd_category_members[activity], 'FD_SECTION'
        else:  # pragma: no cover - source adapter contract
            raise AssertionError(axis)
        item['support_region_codes'] = tuple(region_codes)
        item['support_class_codes'] = tuple(class_codes)
        scope = str(item['portfolio_scope'])
        metric = str(item['metric'])
        children = tuple(
            metric_quantity_id(scope, region_code, class_code, metric)
            for region_code in region_codes
            for class_code in class_codes
        )
        relation_rows.append({
            'relation_id': f'relation:{item["quantity_id"]}',
            'relation_kind': kind,
            'dominance_kind': None,
            'parent_quantity_id': str(item['quantity_id']),
            'child_quantity_ids': children,
            'source_observation_ids': binding_grouped.get(str(item['quantity_id']), ()),
        })

    quantities = pd.DataFrame(quantity_rows).sort_values('quantity_id', kind='stable').reset_index(drop=True)

    # Direct dominance between published aggregates gives the cheap closure engine
    # the same obvious inequalities available to the latent LP.  Supports, not raw
    # table names, define comparability.
    published = quantities[quantities['quantity_kind'].eq('PUBLISHED_AGGREGATE')].copy()
    if not published.empty:
        published['_support_key'] = [
            (tuple(r), tuple(c))
            for r, c in zip(published['support_region_codes'], published['support_class_codes'], strict=True)
        ]
        by_scope_support = {
            (str(scope), support): group.set_index('metric')['quantity_id'].astype(str).to_dict()
            for (scope, support), group in published.groupby(['portfolio_scope', '_support_key'], sort=False)
        }
        for (scope, support), metric_ids in by_scope_support.items():
            for parent_metric, child_metric in _METRIC_DOMINANCE:
                if parent_metric in metric_ids and child_metric in metric_ids:
                    relation_rows.append(_dominance_relation(
                        relation_id=f'dominance:published_metric:{scope}:{_stable_key(support)}:{child_metric}<={parent_metric}',
                        parent_quantity_id=metric_ids[parent_metric],
                        child_quantity_id=metric_ids[child_metric],
                        dominance_kind='PUBLISHED_METRIC_MONOTONICITY',
                    ))
        by_support_metric = {
            (support, str(metric)): group.set_index('portfolio_scope')['quantity_id'].astype(str).to_dict()
            for (support, metric), group in published.groupby(['_support_key', 'metric'], sort=False)
        }
        for (support, metric), scope_ids in by_support_metric.items():
            for child_scope, parent_scope in PORTFOLIO_PARENT_SCOPE.items():
                if child_scope in scope_ids and parent_scope in scope_ids:
                    relation_rows.append(_dominance_relation(
                        relation_id=f'dominance:published_scope:{child_scope}<={parent_scope}:{_stable_key((support, metric))}',
                        parent_quantity_id=scope_ids[parent_scope],
                        child_quantity_id=scope_ids[child_scope],
                        dominance_kind='PUBLISHED_PORTFOLIO_SCOPE',
                    ))

    quantities['lower_assumption_tier'] = 0
    quantities['upper_assumption_tier'] = 0
    relations = pd.DataFrame(relation_rows).drop_duplicates('relation_id').sort_values(
        'relation_id', kind='stable'
    ).reset_index(drop=True)
    bindings = bindings.sort_values(['quantity_id','observation_id'], kind='stable').reset_index(drop=True)
    if quantities['quantity_id'].duplicated().any():
        duplicates = tuple(quantities.loc[quantities['quantity_id'].duplicated(False), 'quantity_id'].astype(str).head(10))
        raise ValueError(f'Quantity graph contains duplicate quantity IDs: {duplicates}')
    if relations['relation_id'].duplicated().any():
        raise ValueError('Quantity graph contains duplicate relation IDs')
    if tuple(scopes) != PORTFOLIO_SCOPES:
        raise ValueError(f'Unexpected portfolio scope order: {scopes}')
    return SorsQuantityGraph(quantities, relations, bindings)


def attach_observation_bindings(bundle: SorsSourceBundle, graph: SorsQuantityGraph) -> SorsSourceBundle:
    return replace(bundle, observation_bindings_grid=graph.observation_bindings_grid)
