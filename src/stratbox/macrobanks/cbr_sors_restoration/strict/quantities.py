from __future__ import annotations

from dataclasses import dataclass, replace
from math import inf

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsSourceBundle
from stratbox.macrobanks.cbr_sors_restoration.metrics import METRIC_COMPONENTS
from stratbox.macrobanks.cbr_sors_restoration.schema import COMPONENTS, TARGET_METRICS


@dataclass(frozen=True)
class SorsQuantityGraph:
    quantities_grid: pd.DataFrame
    relations_grid: pd.DataFrame
    observation_bindings_grid: pd.DataFrame


def component_quantity_id(region_code: str, class_code: str, component: str) -> str:
    return f'component:{region_code}:{class_code}:{component}'


def metric_quantity_id(region_code: str, class_code: str, metric: str) -> str:
    return f'metric:{region_code}:{class_code}:{metric}'


def _publication_quantity_id(row, country_node_id: str) -> str | None:
    series = str(row.source_series)
    metric = str(row.metric)
    if series in {'01_05_A', '01_05_D'}:
        if str(row.activity_code) != 'total':
            return None
        if str(row.geography_node_id) == country_node_id:
            return f'publication:national_total:{metric}'
        return f'publication:geography:{row.geography_node_id}:{metric}'
    if series == '01_02_A':
        if str(row.activity_code) != 'total':
            return None
        return f'publication:national_total:{metric}'
    if series == '01_02_C':
        return f'publication:national_class:{row.activity_code}:{metric}'
    if series == '01_03_C':
        return (
            f'publication:fd_section:{row.geography_node_id}:'
            f'{row.activity_code}:{metric}'
        )
    return None


def _intersection(records: pd.DataFrame) -> tuple[float, float, bool, bool]:
    lower = float(records['published_lower'].max())
    upper = float(records['published_upper'].min())
    lower_rows = records[records['published_lower'].astype(float).eq(lower)]
    upper_rows = records[records['published_upper'].astype(float).eq(upper)]
    lower_attained = bool(lower_rows['published_lower_attained'].astype(bool).all())
    upper_attained = bool(upper_rows['published_upper_attained'].astype(bool).all())
    if lower > upper or (
        lower == upper and not (lower_attained and upper_attained)
    ):
        raise ValueError(
            'Conflicting publication intervals for observations '
            f'{tuple(records["observation_id"].astype(str))}'
        )
    return lower, upper, lower_attained, upper_attained


def build_quantity_graph(bundle: SorsSourceBundle) -> SorsQuantityGraph:
    regions = bundle.atomic_regions_grid.sort_values('region_order')
    classes = bundle.okved2_classes_grid.sort_values('class_order')
    quantity_rows: list[dict[str, object]] = []
    relation_rows: list[dict[str, object]] = []

    for region in regions.itertuples(index=False):
        for activity in classes.itertuples(index=False):
            for component in COMPONENTS:
                quantity_rows.append(
                    {
                        'quantity_id': component_quantity_id(
                            str(region.region_code), str(activity.class_code), component
                        ),
                        'quantity_kind': 'ATOMIC_COMPONENT',
                        'region_code': str(region.region_code),
                        'class_code': str(activity.class_code),
                        'component': component,
                        'metric': None,
                        'lower_bound': 0.0,
                        'upper_bound': inf,
                        'lower_attained': True,
                        'upper_attained': False,
                        'initial_lower_bound': 0.0,
                        'initial_upper_bound': inf,
                        'initial_lower_attained': True,
                        'initial_upper_attained': False,
                    }
                )
            for metric in TARGET_METRICS:
                parent = metric_quantity_id(
                    str(region.region_code), str(activity.class_code), metric
                )
                quantity_rows.append(
                    {
                        'quantity_id': parent,
                        'quantity_kind': 'REGIONAL_CLASS_METRIC',
                        'region_code': str(region.region_code),
                        'class_code': str(activity.class_code),
                        'component': None,
                        'metric': metric,
                        'lower_bound': 0.0,
                        'upper_bound': inf,
                        'lower_attained': True,
                        'upper_attained': False,
                        'initial_lower_bound': 0.0,
                        'initial_upper_bound': inf,
                        'initial_lower_attained': True,
                        'initial_upper_attained': False,
                    }
                )
                children = tuple(
                    component_quantity_id(
                        str(region.region_code), str(activity.class_code), component
                    )
                    for component in METRIC_COMPONENTS[metric]
                )
                relation_rows.append(
                    {
                        'relation_id': f'relation:{parent}',
                        'relation_kind': 'METRIC_COMPONENT_SUM',
                        'parent_quantity_id': parent,
                        'child_quantity_ids': children,
                        'source_observation_ids': (),
                    }
                )

    country_node = bundle.geography_nodes_grid.loc[
        bundle.geography_nodes_grid['geography_kind'].eq('country_total'),
        'geography_node_id',
    ].iloc[0]
    binding_rows: list[dict[str, object]] = []
    # 01_05_D is a validation/history source. It is intentionally excluded
    # from strict bounds so that an optional source cannot silently narrow the
    # official four-book identification model.
    source = bundle.source_grid[
        ~bundle.source_grid['source_series'].eq('01_05_D')
    ].copy()
    source['_publication_quantity_id'] = [
        _publication_quantity_id(row, str(country_node))
        for row in source.itertuples(index=False)
    ]
    bound_source = source[source['_publication_quantity_id'].notna()].copy()
    for quantity_id, group in bound_source.groupby('_publication_quantity_id', sort=True):
        lower, upper, lower_attained, upper_attained = _intersection(group)
        first = group.iloc[0]
        quantity_rows.append(
            {
                'quantity_id': str(quantity_id),
                'quantity_kind': 'PUBLISHED_AGGREGATE',
                'region_code': None,
                'class_code': None,
                'component': None,
                'metric': str(first.metric),
                'lower_bound': lower,
                'upper_bound': upper,
                'lower_attained': lower_attained,
                'upper_attained': upper_attained,
                'initial_lower_bound': lower,
                'initial_upper_bound': upper,
                'initial_lower_attained': lower_attained,
                'initial_upper_attained': upper_attained,
            }
        )
        for row in group.itertuples(index=False):
            binding_rows.append(
                {
                    'observation_id': str(row.observation_id),
                    'quantity_id': str(quantity_id),
                    'source_series': str(row.source_series),
                }
            )

    all_regions = tuple(regions['region_code'].astype(str))
    all_classes = tuple(classes['class_code'].astype(str))
    geo_members = {
        str(row.geography_node_id): tuple(row.atomic_region_codes)
        for row in bundle.geography_nodes_grid.itertuples(index=False)
    }
    national_category_members = {
        str(code): tuple(group['member_class_code'].astype(str))
        for code, group in bundle.publication_categories_grid[
            bundle.publication_categories_grid['publication_level'].eq(
                'NATIONAL_CLASS'
            )
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
    binding_grouped = pd.DataFrame(binding_rows).groupby('quantity_id', sort=False)[
        'observation_id'
    ].agg(tuple).to_dict()
    publication_ids = [
        row['quantity_id']
        for row in quantity_rows
        if row['quantity_kind'] == 'PUBLISHED_AGGREGATE'
    ]
    for quantity_id in sorted(publication_ids):
        parts = quantity_id.split(':')
        metric = parts[-1]
        if parts[1] == 'national_total':
            region_codes, class_codes = all_regions, all_classes
            kind = 'NATIONAL_TOTAL'
        elif parts[1] == 'geography':
            region_codes = geo_members[parts[2]]
            class_codes = all_classes
            kind = 'GEOGRAPHY_TOTAL'
        elif parts[1] == 'national_class':
            region_codes = all_regions
            class_codes = national_category_members[parts[2]]
            kind = 'NATIONAL_CLASS'
        elif parts[1] == 'fd_section':
            region_codes = fd_region_members[parts[2]]
            class_codes = fd_category_members[parts[3]]
            metric = parts[4]
            kind = 'FD_SECTION'
        else:
            raise AssertionError(quantity_id)
        children = tuple(
            metric_quantity_id(region_code, class_code, metric)
            for region_code in region_codes
            for class_code in class_codes
        )
        relation_rows.append(
            {
                'relation_id': f'relation:{quantity_id}',
                'relation_kind': kind,
                'parent_quantity_id': quantity_id,
                'child_quantity_ids': children,
                'source_observation_ids': binding_grouped.get(quantity_id, ()),
            }
        )

    quantities = pd.DataFrame(quantity_rows).sort_values('quantity_id').reset_index(drop=True)
    relations = pd.DataFrame(relation_rows).sort_values('relation_id').reset_index(drop=True)
    bindings = pd.DataFrame(binding_rows).sort_values(
        ['quantity_id', 'observation_id']
    ).reset_index(drop=True)
    if quantities['quantity_id'].duplicated().any():
        raise ValueError('Quantity graph contains duplicate quantity IDs')
    if relations['relation_id'].duplicated().any():
        raise ValueError('Quantity graph contains duplicate relation IDs')
    return SorsQuantityGraph(quantities, relations, bindings)


def attach_observation_bindings(
    bundle: SorsSourceBundle,
    graph: SorsQuantityGraph,
) -> SorsSourceBundle:
    return replace(bundle, observation_bindings_grid=graph.observation_bindings_grid)
