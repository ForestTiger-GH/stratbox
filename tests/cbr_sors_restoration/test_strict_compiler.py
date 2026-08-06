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
                    region_code,
                    class_code,
                    component,
                ),
                'quantity_kind': 'ATOMIC_COMPONENT',
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
        component_quantity_id(region_code, class_code, 'performing_rub')
    ]
    overdue_fx = variables.loc[
        component_quantity_id(region_code, class_code, 'overdue_fx')
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
