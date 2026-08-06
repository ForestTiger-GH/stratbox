from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone

import pandas as pd

from stratbox import __version__ as STRATBOX_VERSION
from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsRunConfig,
    SorsSourceBundle,
    SorsSourceFiles,
)
from stratbox.macrobanks.cbr_sors_restoration.linear.elastic import diagnose_infeasibility
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.results import (
    SorsRestorationResult,
    SorsRunSummary,
)
from stratbox.macrobanks.cbr_sors_restoration.sources import load_sors_sources
from stratbox.macrobanks.cbr_sors_restoration.strict.closure import SorsClosureState
from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import (
    compile_strict_problem,
    refresh_strict_problem_bounds,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.engine import run_cell_resolution
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
    attach_observation_bindings,
    build_quantity_graph,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.result_grid import (
    build_components_grid,
    build_regional_okved2_grid,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.solver import run_strict_feasibility


def _package_version() -> str:
    return STRATBOX_VERSION


def _hash_payload(payload: object, length: int = 24) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode('utf-8')
    ).hexdigest()[:length]


def _identities(
    bundle: SorsSourceBundle,
    config: SorsRunConfig,
) -> tuple[str, str, str]:
    manifest = bundle.source_manifest_grid.sort_values('source_series')
    dataset_id = _hash_payload(
        {
            'as_of_date': config.as_of_date,
            'sources': manifest[['source_series', 'sha256']].to_dict('records'),
        }
    )
    strict_manifest = manifest[
        manifest['source_series'].isin(['01_05_A', '01_02_A', '01_02_C', '01_03_C'])
    ]
    strict_model_id = _hash_payload(
        {
            'dataset_sources': strict_manifest[
                ['source_series', 'sha256']
            ].to_dict('records'),
            'publication_step': config.publication_step,
            'rules_version': config.rules_version,
            'regions': tuple(bundle.atomic_regions_grid['region_code'].astype(str)),
            'classes': tuple(bundle.okved2_classes_grid['class_code'].astype(str)),
        }
    )
    execution_run_id = _hash_payload(
        {
            'strict_model_id': strict_model_id,
            'cell_resolution': config.cell_resolution,
            'package_version': _package_version(),
        }
    )
    return dataset_id, strict_model_id, execution_run_id


def run_sors_restoration(
    source: SorsSourceFiles | SorsSourceBundle,
    config: SorsRunConfig,
) -> SorsRestorationResult:
    bundle = (
        source
        if isinstance(source, SorsSourceBundle)
        else load_sors_sources(
            source,
            config.as_of_date,
            publication_step=config.publication_step,
        )
    )
    dataset_id, strict_model_id, execution_run_id = _identities(bundle, config)
    policy = RoundingPolicy(step=config.publication_step)

    graph = build_quantity_graph(bundle)
    bundle = attach_observation_bindings(bundle, graph)
    closure_state = SorsClosureState(
        graph, tolerance=config.point_tolerance / 10.0
    )
    closure_state.run()
    compilation = compile_strict_problem(
        bundle,
        graph,
        closure_state.quantities_grid,
        point_tolerance=config.point_tolerance,
    )
    feasibility = run_strict_feasibility(
        compilation.problem, config.cell_resolution
    )
    solver_runs = feasibility.solver_runs_grid
    conflicts = pd.DataFrame()
    strict_status = feasibility.feasibility.status

    if feasibility.feasibility.success:
        cell_execution = run_cell_resolution(
            bundle,
            graph,
            compilation,
            closure_state,
            config.cell_resolution,
            policy,
            point_tolerance=config.point_tolerance,
            feasibility_confirmed=True,
        )
        if not cell_execution.solver_runs_grid.empty:
            solver_runs = pd.concat(
                [
                    solver_runs.dropna(axis=1, how='all'),
                    cell_execution.solver_runs_grid.dropna(axis=1, how='all'),
                ],
                ignore_index=True,
                sort=False,
            )
        strict_status = 'OPTIMAL'
    else:
        provisional_config = replace(config.cell_resolution, mode='closure')
        cell_execution = run_cell_resolution(
            bundle,
            graph,
            compilation,
            closure_state,
            provisional_config,
            policy,
            point_tolerance=config.point_tolerance,
            feasibility_confirmed=False,
        )
        if strict_status == 'INFEASIBLE':
            conflicts, conflict_runs = diagnose_infeasibility(
                compilation.problem,
                time_limit_seconds=config.cell_resolution.per_solve_time_limit_seconds,
                threads=config.cell_resolution.threads,
            )
            solver_runs = pd.concat(
                [solver_runs, conflict_runs], ignore_index=True, sort=False
            )
        else:
            conflicts = pd.DataFrame(
                [
                    {
                        'conflict_id': 'strict:feasibility:incomplete',
                        'constraint_id': None,
                        'conflict_status': strict_status,
                        'message': (
                            'Strict feasibility was not confirmed; this is not '
                            'proof of infeasibility.'
                        ),
                    }
                ]
            )

    final_problem = refresh_strict_problem_bounds(
        compilation.problem, cell_execution.quantities_grid
    )
    primary_grid = build_regional_okved2_grid(
        bundle,
        cell_execution.quantities_grid,
        as_of_date=config.as_of_date,
        dataset_id=dataset_id,
        strict_model_id=strict_model_id,
        execution_run_id=execution_run_id,
        policy=policy,
        point_tolerance=config.point_tolerance,
        feasibility_confirmed=feasibility.feasibility.success,
        rules_version=config.rules_version,
        solver_backend=feasibility.backend,
        solver_version=feasibility.version,
    )
    components_grid = build_components_grid(
        bundle,
        cell_execution.quantities_grid,
        as_of_date=config.as_of_date,
        dataset_id=dataset_id,
        strict_model_id=strict_model_id,
        execution_run_id=execution_run_id,
    )
    strict_facts = primary_grid[primary_grid['is_strict_fact'].astype(bool)].copy()
    component_facts = cell_execution.current_facts_grid
    exact_components = (
        int(component_facts['value_precision'].eq('EXACT').sum())
        if not component_facts.empty
        else 0
    )
    published_components = (
        int(component_facts['value_precision'].eq('PUBLISHED').sum())
        if not component_facts.empty
        else 0
    )
    closure_fact_count = int(
        (
            primary_grid['derivation_method'].eq('DETERMINISTIC_CLOSURE')
            & primary_grid['identification_status'].astype(str).str.contains(
                'IDENTIFIED', regex=False
            )
        ).sum()
    )
    solver_identified = int(
        component_facts['uniqueness_basis'].eq('LOCAL_TARGET_SYSTEM').sum()
        if not component_facts.empty
        else 0
    )
    summary = SorsRunSummary(
        dataset_id=dataset_id,
        strict_model_id=strict_model_id,
        execution_run_id=execution_run_id,
        as_of_date=config.as_of_date,
        publication_step=config.publication_step,
        strict_status=strict_status,
        solver_backend=feasibility.backend,
        solver_version=feasibility.version,
        source_rows=len(bundle.source_grid),
        atomic_regions=len(bundle.atomic_regions_grid),
        okved2_classes=len(bundle.okved2_classes_grid),
        component_quantities=int(
            cell_execution.quantities_grid['quantity_kind'].eq('ATOMIC_COMPONENT').sum()
        ),
        regional_metric_rows=len(primary_grid),
        raw_publication_observations=int(
            graph.observation_bindings_grid['source_series'].astype(str).ne('01_05_D').sum()
        ),
        unique_publication_constraints=len(compilation.problem.constraints_grid),
        closure_passes=closure_state.total_passes,
        closure_identified_facts=closure_fact_count,
        lp_identified_facts=solver_identified,
        strict_facts=len(strict_facts),
        cell_resolution_status=cell_execution.status,
        fixed_point_passes=cell_execution.fixed_point_passes,
        cell_targets_attempted=cell_execution.target_attempts,
        cell_targets_resolved=cell_execution.target_values_resolved,
        cell_targets_resolved_by_local_system=(
            cell_execution.target_values_resolved_by_local_system
        ),
        component_facts=len(component_facts),
        exact_component_facts=exact_components,
        published_component_facts=published_components,
    )
    audit = pd.DataFrame(
        [
            {'key': 'created_at_utc', 'value': datetime.now(timezone.utc).isoformat()},
            {'key': 'strategy_box_version', 'value': _package_version()},
            {'key': 'dataset_id', 'value': dataset_id},
            {'key': 'strict_model_id', 'value': strict_model_id},
            {'key': 'execution_run_id', 'value': execution_run_id},
            {'key': 'strict_status', 'value': strict_status},
            {'key': 'cell_resolution_status', 'value': cell_execution.status},
            {'key': 'publication_step', 'value': config.publication_step},
            {'key': 'source_rows', 'value': len(bundle.source_grid)},
            {'key': 'component_quantities', 'value': summary.component_quantities},
            {'key': 'strict_variables', 'value': final_problem.num_variables},
            {'key': 'strict_constraints', 'value': final_problem.num_constraints},
            {'key': 'strict_nnz', 'value': final_problem.matrix.nnz},
            {'key': 'closure_passes', 'value': closure_state.total_passes},
            {'key': 'component_facts', 'value': len(component_facts)},
            {'key': 'strict_metric_facts', 'value': len(strict_facts)},
            {'key': 'cell_target_attempts', 'value': cell_execution.target_attempts},
            {'key': 'cell_targets_resolved', 'value': cell_execution.target_values_resolved},
            {
                'key': 'cell_targets_resolved_by_local_system',
                'value': cell_execution.target_values_resolved_by_local_system,
            },
            {
                'key': 'target_architecture',
                'value': (
                    'persistent constraint graph → local RKVS horizons → '
                    'internal uniqueness proof → fact ledger → affected closure'
                ),
            },
            {
                'key': 'crosswalk_relation_system',
                'value': (
                    'separate evidence layer; not injected into STRICT until '
                    'its scenario is globally feasible'
                ),
            },
        ]
    )
    return SorsRestorationResult(
        source_grid=bundle.source_grid,
        source_manifest_grid=bundle.source_manifest_grid,
        validation_grid=bundle.validation_grid,
        regional_okved2_grid=primary_grid,
        strict_components_grid=components_grid,
        strict_facts_grid=strict_facts,
        derivations_grid=cell_execution.derivations_grid,
        constraints_grid=final_problem.constraints_grid,
        variables_grid=final_problem.variables_grid,
        solver_runs_grid=solver_runs,
        conflicts_grid=conflicts,
        audit_grid=audit,
        summary=summary,
        facts_ledger_grid=cell_execution.facts_ledger_grid,
        current_component_facts_grid=cell_execution.current_facts_grid,
        cell_target_plan_grid=cell_execution.cell_target_plan_grid,
        cell_attempts_grid=cell_execution.cell_attempts_grid,
        cell_subsystems_grid=cell_execution.cell_subsystems_grid,
        promotion_events_grid=cell_execution.promotion_events_grid,
        fixed_point_passes_grid=cell_execution.fixed_point_passes_grid,
        _source_bundle=bundle,
        _strict_problem=final_problem,
    )
