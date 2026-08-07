from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.publication import (
    solver_lower_bound,
    solver_upper_bound,
)
from stratbox.macrobanks.cbr_sors_restoration.schema import COMPONENTS
from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import (
    compile_strict_problem,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
    SorsQuantityGraph,
    component_quantity_id,
)


def test_initial_strict_problem_uses_solver_safe_open_column_bounds() -> None:
    region_code = 'r1'
    class_code = '01'
    rows = []
    for component in COMPONENTS:
        open_lower = component == 'performing_rub'
        open_upper = component == 'overdue_fx'
        rows.append(
            {
                'quantity_id': component_quantity_id(
                    'CORPORATE_TOTAL',
                    region_code,
                    class_code,
                    component,
                ),
                'quantity_kind': 'ATOMIC_COMPONENT',
                'portfolio_scope': 'CORPORATE_TOTAL',
                'region_code': region_code,
                'class_code': class_code,
                'component': component,
                'lower_bound': 0.0,
                'upper_bound': 0.5,
                'lower_attained': not open_lower,
                'upper_attained': not open_upper,
            }
        )
    quantities = pd.DataFrame(rows)
    graph = SorsQuantityGraph(
        quantities_grid=quantities,
        relations_grid=pd.DataFrame(
            columns=[
                'relation_id',
                'relation_kind',
                'parent_quantity_id',
                'child_quantity_ids',
            ]
        ),
        observation_bindings_grid=pd.DataFrame(
            columns=['quantity_id', 'observation_id', 'source_series']
        ),
    )
    bundle = SimpleNamespace(
        atomic_regions_grid=pd.DataFrame(
            [
                {
                    'region_code': region_code,
                    'region_name': 'Регион 1',
                    'region_order': 1,
                    'federal_district_code': 'fd1',
                    'federal_district_name': 'Округ 1',
                    'federal_district_order': 1,
                }
            ]
        ),
        okved2_classes_grid=pd.DataFrame(
            [
                {
                    'class_code': class_code,
                    'class_name': 'Класс 01',
                    'class_order': 1,
                    'section_code': 'A',
                    'section_name': 'Раздел A',
                    'section_order': 1,
                    'publication_category_code': class_code,
                }
            ]
        ),
    )

    compilation = compile_strict_problem(
        bundle,
        graph,
        quantities,
        point_tolerance=1e-9,
    )
    variables = compilation.problem.variables_grid.set_index('quantity_id')

    performing_rub = variables.loc[
        component_quantity_id('CORPORATE_TOTAL', region_code, class_code, 'performing_rub')
    ]
    overdue_fx = variables.loc[
        component_quantity_id('CORPORATE_TOTAL', region_code, class_code, 'overdue_fx')
    ]
    performing_rub_col = int(performing_rub.solver_column)
    overdue_fx_col = int(overdue_fx.solver_column)

    assert compilation.problem.col_lower[performing_rub_col] == solver_lower_bound(
        0.0,
        False,
        open_margin=1e-9,
    )
    assert compilation.problem.col_lower[performing_rub_col] > 0.0
    assert compilation.problem.col_upper[overdue_fx_col] == solver_upper_bound(
        0.5,
        False,
        open_margin=1e-9,
    )
    assert compilation.problem.col_upper[overdue_fx_col] < 0.5

    # Semantic source bounds remain unchanged for reporting and derivations.
    assert float(overdue_fx.upper_bound) == 0.5
    assert not bool(overdue_fx.upper_attained)
    assert np.isfinite(compilation.problem.col_upper).all()


def test_refresh_updates_dynamic_metric_row_after_publication_fact() -> None:
    from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import (
        refresh_strict_problem_bounds,
    )
    from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
        metric_quantity_id,
    )

    region_code = 'r1'
    class_code = '01'
    rows: list[dict[str, object]] = []
    for component in COMPONENTS:
        rows.append(
            {
                'quantity_id': component_quantity_id('CORPORATE_TOTAL', region_code, class_code, component),
                'quantity_kind': 'ATOMIC_COMPONENT',
                'portfolio_scope': 'CORPORATE_TOTAL',
                'region_code': region_code,
                'class_code': class_code,
                'component': component,
                'metric': None,
                'lower_bound': 0.0,
                'upper_bound': np.inf,
                'lower_attained': True,
                'upper_attained': False,
            }
        )
    metric_id = metric_quantity_id('CORPORATE_TOTAL', region_code, class_code, 'debt_rub')
    rows.append(
        {
            'quantity_id': metric_id,
            'quantity_kind': 'REGIONAL_CLASS_METRIC',
                'portfolio_scope': 'CORPORATE_TOTAL',
            'region_code': region_code,
            'class_code': class_code,
            'component': None,
            'metric': 'debt_rub',
            'lower_bound': 0.0,
            'upper_bound': np.inf,
            'lower_attained': True,
            'upper_attained': False,
        }
    )
    quantities = pd.DataFrame(rows)
    graph = SorsQuantityGraph(
        quantities_grid=quantities,
        relations_grid=pd.DataFrame(
            columns=[
                'relation_id',
                'relation_kind',
                'parent_quantity_id',
                'child_quantity_ids',
            ]
        ),
        observation_bindings_grid=pd.DataFrame(
            columns=['quantity_id', 'observation_id', 'source_series']
        ),
    )
    bundle = SimpleNamespace(
        atomic_regions_grid=pd.DataFrame(
            [
                {
                    'region_code': region_code,
                    'region_name': 'Регион 1',
                    'region_order': 1,
                    'federal_district_code': 'fd1',
                    'federal_district_name': 'Округ 1',
                    'federal_district_order': 1,
                }
            ]
        ),
        okved2_classes_grid=pd.DataFrame(
            [
                {
                    'class_code': class_code,
                    'class_name': 'Класс 01',
                    'class_order': 1,
                    'section_code': 'A',
                    'section_name': 'Раздел A',
                    'section_order': 1,
                    'publication_category_code': class_code,
                }
            ]
        ),
    )

    compilation = compile_strict_problem(
        bundle, graph, quantities, point_tolerance=1e-9
    )
    dynamic = compilation.problem.constraints_grid[
        compilation.problem.constraints_grid['constraint_id'].eq(
            f'dynamic_metric:{metric_id}'
        )
    ].iloc[0]
    solver_row = int(dynamic.solver_row)
    assert compilation.problem.row_lower[solver_row] == 0.0
    assert np.isposinf(compilation.problem.row_upper[solver_row])

    changed = quantities.copy()
    index = changed.index[changed['quantity_id'].eq(metric_id)][0]
    changed.at[index, 'lower_bound'] = 5.5
    changed.at[index, 'upper_bound'] = 6.5
    changed.at[index, 'lower_attained'] = True
    changed.at[index, 'upper_attained'] = False
    refreshed = refresh_strict_problem_bounds(compilation.problem, changed)

    debt_components = {'performing_rub', 'overdue_rub'}
    variable_lookup = compilation.problem.variables_grid.set_index('quantity_id')
    expected_columns = {
        int(variable_lookup.loc[component_quantity_id('CORPORATE_TOTAL', region_code, class_code, c)].solver_column)
        for c in debt_components
    }
    assert set(dynamic.expression_indices.tolist()) == expected_columns
    assert refreshed.row_lower[solver_row] == 5.5
    assert refreshed.row_upper[solver_row] == solver_upper_bound(
        6.5, False, open_margin=1e-9
    )


def test_refresh_updates_official_aggregate_row_after_deterministic_tightening() -> None:
    from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import (
        refresh_strict_problem_bounds,
    )
    from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
        metric_quantity_id,
    )

    region_code = 'r1'
    class_code = '01'
    metric_id = metric_quantity_id('CORPORATE_TOTAL', region_code, class_code, 'debt_rub')
    publication_id = 'publication:national_total:debt_rub'
    rows: list[dict[str, object]] = []
    for component in COMPONENTS:
        rows.append(
            {
                'quantity_id': component_quantity_id('CORPORATE_TOTAL', region_code, class_code, component),
                'quantity_kind': 'ATOMIC_COMPONENT',
                'portfolio_scope': 'CORPORATE_TOTAL',
                'region_code': region_code,
                'class_code': class_code,
                'component': component,
                'metric': None,
                'lower_bound': 0.0,
                'upper_bound': np.inf,
                'lower_attained': True,
                'upper_attained': False,
            }
        )
    rows.extend(
        [
            {
                'quantity_id': metric_id,
                'quantity_kind': 'REGIONAL_CLASS_METRIC',
                'portfolio_scope': 'CORPORATE_TOTAL',
                'region_code': region_code,
                'class_code': class_code,
                'component': None,
                'metric': 'debt_rub',
                'lower_bound': 0.0,
                'upper_bound': np.inf,
                'lower_attained': True,
                'upper_attained': False,
            },
            {
                'quantity_id': publication_id,
                'quantity_kind': 'PUBLISHED_AGGREGATE',
                'portfolio_scope': 'CORPORATE_TOTAL',
                'region_code': None,
                'class_code': None,
                'component': None,
                'metric': 'debt_rub',
                'lower_bound': 9.5,
                'upper_bound': 10.5,
                'lower_attained': True,
                'upper_attained': False,
                'published_representative': 10.0,
                'published_representative_status': 'STABLE',
            },
        ]
    )
    quantities = pd.DataFrame(rows)
    graph = SorsQuantityGraph(
        quantities_grid=quantities,
        relations_grid=pd.DataFrame(
            [
                {
                    'relation_id': 'r:pub',
                    'relation_kind': 'NATIONAL_TOTAL',
                    'parent_quantity_id': publication_id,
                    'child_quantity_ids': (metric_id,),
                    'source_observation_ids': ('obs:pub',),
                }
            ]
        ),
        observation_bindings_grid=pd.DataFrame(
            [
                {
                    'quantity_id': publication_id,
                    'observation_id': 'obs:pub',
                    'source_series': 'TEST',
                }
            ]
        ),
    )
    bundle = SimpleNamespace(
        atomic_regions_grid=pd.DataFrame(
            [
                {
                    'region_code': region_code,
                    'region_name': 'Регион 1',
                    'region_order': 1,
                    'federal_district_code': 'fd1',
                    'federal_district_name': 'Округ 1',
                    'federal_district_order': 1,
                }
            ]
        ),
        okved2_classes_grid=pd.DataFrame(
            [
                {
                    'class_code': class_code,
                    'class_name': 'Класс 01',
                    'class_order': 1,
                    'section_code': 'A',
                    'section_name': 'Раздел A',
                    'section_order': 1,
                    'publication_category_code': class_code,
                }
            ]
        ),
    )

    compilation = compile_strict_problem(
        bundle, graph, quantities, point_tolerance=1e-9
    )
    row = compilation.problem.constraints_grid[
        compilation.problem.constraints_grid['constraint_id'].eq(
            f'strict:{publication_id}'
        )
    ].iloc[0]
    solver_row = int(row.solver_row)
    assert compilation.problem.row_lower[solver_row] == 9.5
    assert compilation.problem.row_upper[solver_row] == solver_upper_bound(
        10.5, False, open_margin=1e-9
    )

    tightened = quantities.copy()
    index = tightened.index[tightened['quantity_id'].eq(publication_id)][0]
    tightened.at[index, 'lower_bound'] = 9.8
    tightened.at[index, 'upper_bound'] = 10.2
    tightened.at[index, 'lower_attained'] = True
    tightened.at[index, 'upper_attained'] = False
    refreshed = refresh_strict_problem_bounds(compilation.problem, tightened)

    assert refreshed.row_lower[solver_row] == 9.8
    assert refreshed.row_upper[solver_row] == solver_upper_bound(
        10.2, False, open_margin=1e-9
    )
    refreshed_meta = refreshed.constraints_grid[
        refreshed.constraints_grid['constraint_id'].eq(f'strict:{publication_id}')
    ].iloc[0]
    assert float(refreshed_meta.lower_bound) == 9.8
    assert float(refreshed_meta.upper_bound) == 10.2
