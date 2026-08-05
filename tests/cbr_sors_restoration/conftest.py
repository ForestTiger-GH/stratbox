from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from stratbox.macrobanks.cbr_sors_restoration.results import (
    SorsRestorationResult,
    SorsRunSummary,
)


@pytest.fixture
def small_result() -> SorsRestorationResult:
    records = []
    regions = [
        ('r1', 'Регион 1', 1, 'fd1', 'Округ 1', 1),
        ('r2', 'Регион 2', 2, 'fd1', 'Округ 1', 1),
    ]
    classes = [
        ('01', 'Класс 01', 1, 'A', 'Раздел A', 1),
        ('16', 'Класс 16', 2, 'C', 'Раздел C', 2),
    ]
    metrics = ('debt_rub', 'debt_fx')
    for region_code, region_name, region_order, fd_code, fd_name, fd_order in regions:
        for class_code, class_name, class_order, section_code, section_name, section_order in classes:
            for metric_order, metric in enumerate(metrics, start=1):
                identified = region_code == 'r1' and class_code == '01'
                records.append(
                    {
                        'dataset_id': 'dataset',
                        'strict_model_id': 'model',
                        'execution_run_id': 'run',
                        'as_of_date': '2026-06-01',
                        'region_code': region_code,
                        'region_name': region_name,
                        'region_order': region_order,
                        'federal_district_code': fd_code,
                        'federal_district_name': fd_name,
                        'federal_district_order': fd_order,
                        'section_code': section_code,
                        'section_name': section_name,
                        'section_order': section_order,
                        'class_code': class_code,
                        'class_name': class_name,
                        'class_order': class_order,
                        'publication_category_code': class_code,
                        'is_individually_published': True,
                        'metric': metric,
                        'metric_name': metric,
                        'metric_order': metric_order,
                        'unit': 'million_rubles',
                        'value': 0.0 if identified else None,
                        'value_precision': 'PUBLISHED' if identified else 'NONE',
                        'exact_value': None,
                        'published_value': 0.0 if identified else None,
                        'lower_bound': 0.0,
                        'upper_bound': 0.5 if identified else 10.0,
                        'lower_attained': True,
                        'upper_attained': False,
                        'interval_width': 0.5 if identified else 10.0,
                        'evidence_layer': 'STRICT',
                        'identification_status': 'PUBLISHED_BUCKET_IDENTIFIED' if identified else 'BOUNDED',
                        'derivation_method': 'DETERMINISTIC_CLOSURE' if identified else 'NONE',
                        'is_strict_fact': identified,
                        'is_reconstructed': identified,
                        'is_zero_at_published_precision': identified,
                        'is_exact_zero': False,
                        'is_lp_certified': False,
                        'proof_id': 'd1' if identified else None,
                        'closure_pass': 1 if identified else None,
                        'lower_solve_id': None,
                        'upper_solve_id': None,
                        'rules_version': 'test',
                        'solver_backend': 'highspy',
                        'solver_version': 'test',
                    }
                )
    grid = pd.DataFrame(records)
    summary = SorsRunSummary(
        dataset_id='dataset', strict_model_id='model', execution_run_id='run',
        as_of_date='2026-06-01', publication_step=1.0, strict_status='OPTIMAL', solver_backend='highspy',
        solver_version='test', source_rows=0, atomic_regions=2, okved2_classes=2,
        component_quantities=16, regional_metric_rows=len(grid),
        raw_publication_observations=0, unique_publication_constraints=0,
        closure_passes=1, closure_identified_facts=2, lp_identified_facts=0,
        strict_facts=2, certification_targets_attempted=0,
        certification_targets_completed=0,
    )
    empty = pd.DataFrame()
    return SorsRestorationResult(
        source_grid=empty, source_manifest_grid=empty, validation_grid=empty,
        regional_okved2_grid=grid,
        strict_components_grid=empty,
        strict_facts_grid=grid[grid['is_strict_fact']].copy(),
        derivations_grid=empty, constraints_grid=empty, variables_grid=empty,
        certification_plan_grid=empty, solver_runs_grid=empty,
        conflicts_grid=empty, audit_grid=pd.DataFrame([{'key': 'x', 'value': 'y'}]),
        summary=summary,
    )
