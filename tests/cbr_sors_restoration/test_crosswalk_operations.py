from __future__ import annotations

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsCrosswalkConfig,
    SorsSourceBundle,
)
from stratbox.macrobanks.cbr_sors_restoration.crosswalk import operations
from stratbox.macrobanks.cbr_sors_restoration.linear.highs import SolveResult
from stratbox.macrobanks.cbr_sors_restoration.metrics import (
    METRIC_NAMES_RU,
    METRIC_ORDER,
)
from stratbox.macrobanks.cbr_sors_restoration.registries.okved2 import (
    read_okved2_classes,
)
from stratbox.macrobanks.cbr_sors_restoration.registries.publication_categories import (
    build_publication_categories,
    enrich_okved2_classes,
)
from stratbox.macrobanks.cbr_sors_restoration.results import (
    SorsRestorationResult,
    SorsRunSummary,
)
from stratbox.macrobanks.cbr_sors_restoration.schema import TARGET_METRICS


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


def _strict_with_bundle() -> SorsRestorationResult:
    classes = read_okved2_classes()
    publication_categories = build_publication_categories(classes)
    classes = enrich_okved2_classes(classes, publication_categories)
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
        [{'geography_node_id': 'r1', 'atomic_region_codes': ('r1',)}]
    )
    regional = pd.DataFrame(
        [
            _published_row('narrow', 'agriculture_hunting_services', 90.0),
            _published_row('broad', 'agriculture_hunting_forestry', 100.0),
            _published_row('technical', 'completion_of_settlements', 0.0),
        ]
    )
    empty = pd.DataFrame()
    bundle = SorsSourceBundle(
        source_grid=regional,
        regional_traditional_grid=regional,
        national_traditional_grid=empty,
        national_okved2_grid=empty,
        federal_district_okved2_grid=empty,
        regional_totals_history_grid=empty,
        geography_nodes_grid=geography,
        atomic_regions_grid=region,
        okved2_classes_grid=classes,
        publication_categories_grid=publication_categories,
        observation_bindings_grid=empty,
        source_manifest_grid=empty,
        validation_grid=empty,
    )
    records: list[dict[str, object]] = []
    region_row = region.iloc[0]
    for class_row in classes.itertuples(index=False):
        for metric in TARGET_METRICS:
            records.append(
                {
                    'dataset_id': 'dataset',
                    'strict_model_id': 'strict-model',
                    'execution_run_id': 'strict-run',
                    'as_of_date': '2026-06-01',
                    **region_row.to_dict(),
                    'section_code': str(class_row.section_code),
                    'section_name': str(class_row.section_name),
                    'section_order': int(class_row.section_order),
                    'class_code': str(class_row.class_code),
                    'class_name': str(class_row.class_name),
                    'class_order': int(class_row.class_order),
                    'publication_category_code': str(
                        class_row.publication_category_code
                    ),
                    'is_individually_published': bool(
                        class_row.is_individually_published
                    ),
                    'metric': metric,
                    'metric_name': METRIC_NAMES_RU[metric],
                    'metric_order': METRIC_ORDER[metric],
                    'unit': 'million_rubles',
                    'value': None,
                    'value_precision': 'NONE',
                    'exact_value': None,
                    'published_value': None,
                    'lower_bound': 0.0,
                    'upper_bound': float('inf'),
                    'lower_attained': True,
                    'upper_attained': False,
                    'interval_width': float('inf'),
                    'evidence_layer': 'STRICT',
                    'identification_status': 'BOUNDED',
                    'derivation_method': 'NONE',
                    'is_strict_fact': False,
                    'is_reconstructed': False,
                    'is_zero_at_published_precision': False,
                    'is_exact_zero': False,
                    'is_lp_certified': False,
                    'proof_id': None,
                    'closure_pass': None,
                    'lower_solve_id': None,
                    'upper_solve_id': None,
                    'rules_version': 'test',
                    'solver_backend': 'test',
                    'solver_version': 'test',
                }
            )
    grid = pd.DataFrame(records)
    summary = SorsRunSummary(
        dataset_id='dataset',
        strict_model_id='strict-model',
        execution_run_id='strict-run',
        as_of_date='2026-06-01',
        publication_step=1.0,
        strict_status='OPTIMAL',
        solver_backend='test',
        solver_version='test',
        source_rows=len(regional),
        atomic_regions=1,
        okved2_classes=len(classes),
        component_quantities=len(classes) * 4,
        regional_metric_rows=len(grid),
        raw_publication_observations=len(regional),
        unique_publication_constraints=len(regional),
        closure_passes=1,
        closure_identified_facts=0,
        lp_identified_facts=0,
        strict_facts=0,
    )
    return SorsRestorationResult(
        source_grid=regional,
        source_manifest_grid=empty,
        validation_grid=empty,
        regional_okved2_grid=grid,
        strict_components_grid=empty,
        strict_facts_grid=empty,
        derivations_grid=empty,
        constraints_grid=empty,
        variables_grid=empty,
        solver_runs_grid=empty,
        conflicts_grid=empty,
        audit_grid=empty,
        summary=summary,
        _source_bundle=bundle,
    )


class _FeasibilitySession:
    def __init__(self, problem, *, time_limit_seconds, threads):
        self.problem = problem
        self.version = 'test-highs'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def solve_feasibility(self) -> SolveResult:
        return SolveResult(
            success=True,
            status='OPTIMAL',
            raw_status='kOptimal',
            objective_value=0.0,
            values=np.zeros(self.problem.num_variables),
            runtime_seconds=0.0,
            simplex_iterations=0,
            ipm_iterations=0,
        )


def test_full_crosswalk_orchestration_accepts_only_equation_identified_values(
    monkeypatch,
) -> None:
    monkeypatch.setattr(operations, 'HighsSession', _FeasibilitySession)
    result = operations.run_sors_crosswalk(
        _strict_with_bundle(),
        SorsCrosswalkConfig(
            mode='feasibility',
            scenario_ids=('core',),
            scenario_policy='single',
        ),
    )

    assert result.status == 'OPTIMAL'
    facts = result.crosswalk_facts_grid.set_index(['class_code', 'metric'])
    assert facts.loc[('01', 'overdue_rub'), 'value'] == 90.0
    assert facts.loc[('02', 'overdue_rub'), 'value'] == 10.0
    assert facts['value'].notna().all()
    assert not facts['is_benchmark_estimate'].astype(bool).any()
    assert facts['mapping_version'].eq(
        'cbr-legacy-okved2-crosswalk-2026.3'
    ).all()
    assert facts['scenario_coverage_complete'].astype(bool).all()
    assert facts['supporting_relation_ids'].map(bool).all()

    unresolved = result.crosswalk_bounds_grid[
        ~result.crosswalk_bounds_grid['is_final_accepted'].astype(bool)
    ]
    assert unresolved['value'].isna().all()


def test_overall_crosswalk_status_treats_proven_infeasible_scenario_as_resolved() -> None:
    assert operations._overall_crosswalk_status(
        {'OPTIMAL', 'INFEASIBLE'}
    ) == 'OPTIMAL_WITH_REJECTED_SCENARIOS'
    assert operations._overall_crosswalk_status(
        {'OPTIMAL', 'SOLVER_UNAVAILABLE'}
    ) == 'PARTIAL'
    assert operations._overall_crosswalk_status(
        {'INFEASIBLE', 'INFEASIBLE_BY_CLOSURE'}
    ) == 'INFEASIBLE'
