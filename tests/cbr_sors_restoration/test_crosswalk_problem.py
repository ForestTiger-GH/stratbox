from __future__ import annotations

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsCrosswalkConfig,
    SorsSourceBundle,
)
from stratbox.macrobanks.cbr_sors_restoration.crosswalk.problem import (
    CrosswalkCompilation,
    compile_crosswalk_problem,
)
from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import (
    CsrMatrixData,
    SorsLinearProblem,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.registries.okved2 import (
    read_okved2_classes,
)
from stratbox.macrobanks.cbr_sors_restoration.crosswalk.operations import (
    _base_scenario_grid,
    _target_outer_bounds,
)


def _empty_bundle() -> SorsSourceBundle:
    classes = read_okved2_classes()
    region = pd.DataFrame(
        [
            {
                'region_code': 'r1',
                'region_name': 'Регион 1',
                'region_order': 1,
                'federal_district_code': 'fd1',
                'federal_district_name': 'Округ 1',
                'federal_district_order': 1,
            }
        ]
    )
    geography = pd.DataFrame(
        [
            {
                'geography_node_id': 'r1',
                'atomic_region_codes': ('r1',),
            }
        ]
    )
    empty = pd.DataFrame()
    return SorsSourceBundle(
        source_grid=empty,
        regional_traditional_grid=empty,
        national_traditional_grid=empty,
        national_okved2_grid=empty,
        federal_district_okved2_grid=empty,
        regional_totals_history_grid=empty,
        geography_nodes_grid=geography,
        atomic_regions_grid=region,
        okved2_classes_grid=classes,
        publication_categories_grid=empty,
        observation_bindings_grid=empty,
        source_manifest_grid=empty,
        validation_grid=empty,
    )


def test_crosswalk_problem_uses_only_explicit_allowed_flows() -> None:
    compilation = compile_crosswalk_problem(
        _empty_bundle(),
        pd.DataFrame(),
        SorsCrosswalkConfig(mode='feasibility'),
        'core',
    )
    variables = compilation.problem.variables_grid
    assert set(variables['variable_kind']) == {'CROSSWALK_FLOW'}
    assert not variables['variable_kind'].str.contains('RESIDUAL').any()
    assert np.count_nonzero(compilation.problem.objective) == 0

    class_01_atoms = set(
        variables.loc[variables['class_code'].eq('01'), 'atom_code'].astype(str)
    )
    class_02_atoms = set(
        variables.loc[variables['class_code'].eq('02'), 'atom_code'].astype(str)
    )
    assert 'agriculture_hunting_services' in class_01_atoms
    assert 'forestry' not in class_01_atoms
    assert 'forestry' in class_02_atoms
    assert 'completion_of_settlements' in class_01_atoms
    assert 'completion_of_settlements' in class_02_atoms


def _acceptance_compilation(small_result) -> CrosswalkCompilation:
    rows = small_result.regional_okved2_grid.reset_index(drop=True)
    size = len(rows)
    upper = np.full(size, 10.0, dtype=float)
    lower = np.zeros(size, dtype=float)
    exact_index = next(
        index
        for index, row in rows.iterrows()
        if not bool(row.is_strict_fact)
    )
    lower[exact_index] = upper[exact_index] = 5.0
    problem = SorsLinearProblem(
        model_layer='CROSSWALK',
        matrix=CsrMatrixData(
            shape=(0, size),
            indptr=np.asarray([0], dtype=np.int64),
            indices=np.asarray([], dtype=np.int32),
            data=np.asarray([], dtype=float),
        ),
        row_lower=np.asarray([], dtype=float),
        row_upper=np.asarray([], dtype=float),
        col_lower=lower,
        col_upper=upper,
        objective=np.zeros(size, dtype=float),
        constraints_grid=pd.DataFrame(),
        variables_grid=pd.DataFrame({'solver_column': range(size)}),
    )
    catalog = pd.DataFrame(
        [
            {
                'target_id': f't:{index}',
                'quantity_id': f'q:{index}',
                'scenario_id': 'core',
                'region_code': str(row.region_code),
                'region_name': str(row.region_name),
                'class_code': str(row.class_code),
                'metric': str(row.metric),
                'indices': np.asarray([index], dtype=np.int32),
                'coefficients': np.asarray([1.0], dtype=float),
                'constant': 0.0,
            }
            for index, row in enumerate(rows.itertuples(index=False))
        ]
    )
    return CrosswalkCompilation(
        problem=problem,
        target_catalog_grid=catalog,
        mapping_edges_grid=pd.DataFrame(),
        relations_grid=pd.DataFrame(),
    )


def test_crosswalk_value_is_populated_only_for_identified_interval(small_result) -> None:
    compilation = _acceptance_compilation(small_result)
    grid = _base_scenario_grid(
        small_result,
        compilation,
        scenario_id='core',
        policy=RoundingPolicy(step=1.0),
        point_tolerance=1e-6,
        feasibility_confirmed=True,
    )
    exact = grid[grid['value'].eq(5.0)]
    assert len(exact) == 1
    assert bool(exact.iloc[0]['is_final_accepted'])
    unresolved = grid.drop(index=exact.index)
    assert unresolved.loc[~unresolved['is_strict_fact'].astype(bool), 'value'].isna().all()
    assert not grid['is_benchmark_estimate'].astype(bool).any()


def test_crosswalk_closure_value_remains_provisional_without_feasibility(small_result) -> None:
    compilation = _acceptance_compilation(small_result)
    grid = _base_scenario_grid(
        small_result,
        compilation,
        scenario_id='core',
        policy=RoundingPolicy(step=1.0),
        point_tolerance=1e-6,
        feasibility_confirmed=False,
    )
    assert grid['value'].isna().all()
    assert not grid['is_final_accepted'].astype(bool).any()
    assert (grid['identified_value'] == 5.0).sum() == 1


def _published_row(
    observation_id: str,
    activity_code: str,
    value: float,
) -> dict[str, object]:
    return {
        'observation_id': observation_id,
        'source_series': '01_05_A',
        'geography_node_id': 'r1',
        'activity_code': activity_code,
        'metric': 'overdue_rub',
        'published_lower': value,
        'published_upper': value,
        'published_lower_attained': True,
        'published_upper_attained': True,
    }


def test_agriculture_crosswalk_equations_identify_01_and_02_by_residual() -> None:
    bundle = _empty_bundle()
    regional = pd.DataFrame(
        [
            _published_row('narrow', 'agriculture_hunting_services', 90.0),
            _published_row('broad', 'agriculture_hunting_forestry', 100.0),
            _published_row('technical', 'completion_of_settlements', 0.0),
        ]
    )
    bundle = SorsSourceBundle(
        source_grid=bundle.source_grid,
        regional_traditional_grid=regional,
        national_traditional_grid=bundle.national_traditional_grid,
        national_okved2_grid=bundle.national_okved2_grid,
        federal_district_okved2_grid=bundle.federal_district_okved2_grid,
        regional_totals_history_grid=bundle.regional_totals_history_grid,
        geography_nodes_grid=bundle.geography_nodes_grid,
        atomic_regions_grid=bundle.atomic_regions_grid,
        okved2_classes_grid=bundle.okved2_classes_grid,
        publication_categories_grid=bundle.publication_categories_grid,
        observation_bindings_grid=bundle.observation_bindings_grid,
        source_manifest_grid=bundle.source_manifest_grid,
        validation_grid=bundle.validation_grid,
    )
    compilation = compile_crosswalk_problem(
        bundle,
        pd.DataFrame(),
        SorsCrosswalkConfig(mode='feasibility'),
        'core',
    )
    from stratbox.macrobanks.cbr_sors_restoration.crosswalk.closure import (
        close_crosswalk_bounds,
    )

    closed = close_crosswalk_bounds(
        compilation.problem,
        tolerance=1e-9,
    )
    compilation = CrosswalkCompilation(
        problem=closed.problem,
        target_catalog_grid=compilation.target_catalog_grid,
        mapping_edges_grid=compilation.mapping_edges_grid,
        relations_grid=compilation.relations_grid,
    )
    bounds = {
        (row.class_code, row.metric): (row.lower_bound, row.upper_bound)
        for row in _target_outer_bounds(compilation).itertuples(index=False)
    }
    assert bounds[('01', 'overdue_rub')] == (90.0, 90.0)
    assert bounds[('02', 'overdue_rub')] == (10.0, 10.0)


def test_scenario_envelope_is_not_accepted_when_coverage_is_incomplete(
    small_result,
) -> None:
    from stratbox.macrobanks.cbr_sors_restoration.crosswalk.operations import (
        _ScenarioExecution,
        _robust_envelope,
    )

    compilation = _acceptance_compilation(small_result)
    optimal_grid = _base_scenario_grid(
        small_result,
        compilation,
        scenario_id='core',
        policy=RoundingPolicy(step=1.0),
        point_tolerance=1e-6,
        feasibility_confirmed=True,
    )
    unresolved_grid = optimal_grid.copy()
    unresolved_grid['scenario_id'] = 'broad'
    unresolved_grid['evidence_profile'] = 'broad'
    unresolved_grid['bounds_certified'] = False
    unresolved_grid['value_identified'] = False
    unresolved_grid['is_final_accepted'] = False
    unresolved_grid['value'] = None

    empty = pd.DataFrame()
    executions = [
        _ScenarioExecution(
            scenario_id='core',
            status='OPTIMAL',
            grid=optimal_grid,
            compilation=compilation,
            derivations_grid=empty,
            solver_runs_grid=empty,
            conflicts_grid=empty,
            diagnostics_grid=empty,
        ),
        _ScenarioExecution(
            scenario_id='broad',
            status='SOLVER_UNAVAILABLE',
            grid=unresolved_grid,
            compilation=compilation,
            derivations_grid=empty,
            solver_runs_grid=empty,
            conflicts_grid=empty,
            diagnostics_grid=empty,
        ),
    ]
    envelope = _robust_envelope(
        small_result,
        executions,
        policy=RoundingPolicy(step=1.0),
        point_tolerance=1e-6,
    )

    assert not envelope['scenario_coverage_complete'].astype(bool).any()
    assert not envelope['bounds_certified'].astype(bool).any()
    assert envelope['value'].isna().all()
    assert not envelope['is_final_accepted'].astype(bool).any()


def test_one_sided_lp_tightening_can_safely_identify_bucket(small_result) -> None:
    from stratbox.macrobanks.cbr_sors_restoration.crosswalk.operations import (
        _apply_target_results,
    )
    from stratbox.macrobanks.cbr_sors_restoration.linear.highs import SolveResult

    compilation = _acceptance_compilation(small_result)
    grid = _base_scenario_grid(
        small_result,
        compilation,
        scenario_id='core',
        policy=RoundingPolicy(step=1.0),
        point_tolerance=1e-6,
        feasibility_confirmed=True,
    )
    catalog = compilation.target_catalog_grid
    exact_target = catalog.loc[
        catalog['indices'].map(lambda values: int(values[0])).eq(
            int(np.flatnonzero(compilation.problem.col_lower == 5.0)[0])
        )
    ].iloc[0]
    candidate = catalog.loc[
        ~catalog['target_id'].eq(exact_target.target_id)
        & ~catalog.apply(
            lambda row: bool(
                small_result.regional_okved2_grid.loc[
                    (small_result.regional_okved2_grid['region_code'].eq(row.region_code))
                    & (small_result.regional_okved2_grid['class_code'].eq(row.class_code))
                    & (small_result.regional_okved2_grid['metric'].eq(row.metric)),
                    'is_strict_fact',
                ].iloc[0]
            ),
            axis=1,
        )
    ].iloc[0]
    lower = SolveResult(
        success=True,
        status='OPTIMAL',
        raw_status='kOptimal',
        objective_value=9.6,
        values=None,
        runtime_seconds=0.0,
        simplex_iterations=0,
        ipm_iterations=0,
    )
    upper = SolveResult(
        success=False,
        status='TIME_LIMIT',
        raw_status='kTimeLimit',
        objective_value=None,
        values=None,
        runtime_seconds=1.0,
        simplex_iterations=0,
        ipm_iterations=0,
    )
    out = _apply_target_results(
        grid,
        compilation.target_catalog_grid,
        {str(candidate.target_id): (lower, upper)},
        policy=RoundingPolicy(step=1.0),
        point_tolerance=1e-6,
        scenario_id='core',
    )
    row = out.loc[
        out['region_code'].eq(candidate.region_code)
        & out['class_code'].eq(candidate.class_code)
        & out['metric'].eq(candidate.metric)
    ].iloc[0]
    assert row.value == 10.0
    assert bool(row.is_final_accepted)
    assert bool(row.lp_lower_certified)
    assert not bool(row.lp_upper_certified)
    assert not bool(row.is_lp_certified)
    assert row.derivation_method == 'CROSSWALK_PARTIAL_MINMAX'


def test_broad_agriculture_scenario_preserves_mapping_uncertainty() -> None:
    bundle = _empty_bundle()
    regional = pd.DataFrame(
        [
            _published_row('narrow', 'agriculture_hunting_services', 90.0),
            _published_row('broad', 'agriculture_hunting_forestry', 100.0),
            _published_row('technical', 'completion_of_settlements', 0.0),
        ]
    )
    bundle = SorsSourceBundle(
        source_grid=bundle.source_grid,
        regional_traditional_grid=regional,
        national_traditional_grid=bundle.national_traditional_grid,
        national_okved2_grid=bundle.national_okved2_grid,
        federal_district_okved2_grid=bundle.federal_district_okved2_grid,
        regional_totals_history_grid=bundle.regional_totals_history_grid,
        geography_nodes_grid=bundle.geography_nodes_grid,
        atomic_regions_grid=bundle.atomic_regions_grid,
        okved2_classes_grid=bundle.okved2_classes_grid,
        publication_categories_grid=bundle.publication_categories_grid,
        observation_bindings_grid=bundle.observation_bindings_grid,
        source_manifest_grid=bundle.source_manifest_grid,
        validation_grid=bundle.validation_grid,
    )
    compilation = compile_crosswalk_problem(
        bundle,
        pd.DataFrame(),
        SorsCrosswalkConfig(mode='feasibility'),
        'broad',
    )
    from stratbox.macrobanks.cbr_sors_restoration.crosswalk.closure import (
        close_crosswalk_bounds,
    )

    closed = close_crosswalk_bounds(compilation.problem, tolerance=1e-9)
    compilation = CrosswalkCompilation(
        problem=closed.problem,
        target_catalog_grid=compilation.target_catalog_grid,
        mapping_edges_grid=compilation.mapping_edges_grid,
        relations_grid=compilation.relations_grid,
    )
    bounds = {
        (row.class_code, row.metric): (row.lower_bound, row.upper_bound)
        for row in _target_outer_bounds(compilation).itertuples(index=False)
    }
    assert bounds[('01', 'overdue_rub')] == (90.0, 100.0)
    assert bounds[('02', 'overdue_rub')] == (0.0, 10.0)
