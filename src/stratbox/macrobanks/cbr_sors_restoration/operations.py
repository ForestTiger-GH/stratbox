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
from stratbox.macrobanks.cbr_sors_restoration.linear.elastic import (
    diagnose_infeasibility,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.results import (
    SorsRestorationResult,
    SorsRunSummary,
)
from stratbox.macrobanks.cbr_sors_restoration.sources import load_sors_sources
from stratbox.macrobanks.cbr_sors_restoration.strict.closure import (
    run_deterministic_closure,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import (
    compile_strict_problem,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.planning import (
    build_certification_plan,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
    attach_observation_bindings,
    build_quantity_graph,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.result_grid import (
    build_components_grid,
    build_regional_okved2_grid,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.solver import (
    apply_lp_bounds,
    run_strict_feasibility,
    run_strict_target_batch,
)


def _package_version() -> str:
    return STRATBOX_VERSION


def _hash_payload(payload: object, length: int = 24) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode('utf-8')
    ).hexdigest()[:length]


def _identities(bundle: SorsSourceBundle, config: SorsRunConfig) -> tuple[str, str, str]:
    manifest = bundle.source_manifest_grid.sort_values('source_series')
    dataset_id = _hash_payload(
        {
            'as_of_date': config.as_of_date,
            'sources': manifest[['source_series', 'sha256']].to_dict('records'),
        }
    )
    strict_manifest = manifest[manifest['source_series'].isin(
        ['01_05_A', '01_02_A', '01_02_C', '01_03_C']
    )]
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
            'certification': config.strict_certification,
            'package_version': _package_version(),
        }
    )
    return dataset_id, strict_model_id, execution_run_id


def _offset_derivations(
    first: pd.DataFrame,
    second: pd.DataFrame,
    quantities: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if second.empty:
        return first, quantities
    second = second.copy()
    offset = len(first)
    pass_offset = (
        int(first['pass_number'].max())
        if not first.empty and 'pass_number' in first
        else 0
    )
    second['pass_number'] = second['pass_number'].astype(int) + pass_offset
    old_ids = tuple(second['derivation_id'].astype(str))
    new_ids = tuple(
        f'derivation:{offset + position:08d}'
        for position in range(1, len(second) + 1)
    )
    remap = dict(zip(old_ids, new_ids, strict=True))
    second['derivation_id'] = second['derivation_id'].astype(str).map(remap)
    quantities = quantities.copy()
    new_derivation = quantities['last_derivation_id'].astype(str).isin(remap)
    if 'last_derivation_pass' in quantities:
        quantities.loc[new_derivation, 'last_derivation_pass'] = quantities.loc[
            new_derivation, 'last_derivation_pass'
        ].map(
            lambda value: int(value) + pass_offset
            if value is not None and not pd.isna(value)
            else value
        )
    quantities['last_derivation_id'] = quantities['last_derivation_id'].map(
        lambda value: remap.get(str(value), value)
        if value is not None and not pd.isna(value)
        else value
    )
    return (
        pd.concat([first, second], ignore_index=True, sort=False),
        quantities,
    )


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
    initial_closure = run_deterministic_closure(
        graph,
        tolerance=config.point_tolerance / 10.0,
    )
    quantities = initial_closure.quantities_grid
    derivations = initial_closure.derivations_grid
    closure_passes = initial_closure.passes
    compilation = compile_strict_problem(
        bundle,
        graph,
        quantities,
        point_tolerance=config.point_tolerance,
    )

    feasibility = run_strict_feasibility(
        compilation.problem,
        config.strict_certification,
    )
    solver_runs = feasibility.solver_runs_grid
    conflicts = pd.DataFrame()
    attempted: set[str] = set()
    completed: set[str] = set()
    attempt_order: dict[str, int] = {}
    all_target_results: dict[str, object] = {}
    batch_sequence = 0
    total_budget = config.strict_certification.max_targets

    if feasibility.feasibility.success:
        strict_status = 'OPTIMAL'
        if config.strict_certification.mode != 'closure':
            planning_config = replace(
                config.strict_certification,
                max_targets=None,
            )
            while True:
                plan = build_certification_plan(
                    bundle,
                    compilation.target_catalog_grid,
                    quantities,
                    planning_config,
                    policy,
                )
                candidates = plan[
                    plan['selected'].astype(bool)
                    & ~plan['target_id'].astype(str).isin(attempted)
                ].sort_values('selection_order', kind='stable')
                if total_budget is not None:
                    remaining = total_budget - len(attempted)
                    if remaining <= 0:
                        break
                    candidates = candidates.head(remaining)
                candidates = candidates.head(config.strict_certification.batch_size)
                if candidates.empty:
                    break

                batch_sequence += 1
                batch = run_strict_target_batch(
                    compilation.problem,
                    compilation.target_catalog_grid,
                    candidates,
                    config.strict_certification,
                    batch_sequence=batch_sequence,
                )
                if not batch.solver_runs_grid.empty:
                    solver_runs = pd.concat(
                        [solver_runs, batch.solver_runs_grid],
                        ignore_index=True,
                        sort=False,
                    )
                before = quantities[
                    ['quantity_id', 'lower_bound', 'upper_bound']
                ].set_index('quantity_id')
                quantities = apply_lp_bounds(
                    quantities,
                    compilation.target_catalog_grid,
                    batch.target_results,
                    point_tolerance=config.point_tolerance,
                )
                for target_id, pair in batch.target_results.items():
                    target_id = str(target_id)
                    if target_id not in attempted:
                        attempt_order[target_id] = len(attempt_order)
                    attempted.add(target_id)
                    all_target_results[target_id] = pair
                    if pair[0].success and pair[1].success:
                        completed.add(target_id)

                graph_after_lp = replace(graph, quantities_grid=quantities)
                lp_closure = run_deterministic_closure(
                    graph_after_lp,
                    tolerance=config.point_tolerance / 10.0,
                )
                quantities = lp_closure.quantities_grid
                derivations, quantities = _offset_derivations(
                    derivations,
                    lp_closure.derivations_grid,
                    quantities,
                )
                closure_passes += lp_closure.passes
                after = quantities[
                    ['quantity_id', 'lower_bound', 'upper_bound']
                ].set_index('quantity_id')
                changed = bool(
                    (
                        (after['lower_bound'] - before['lower_bound']).abs()
                        > config.point_tolerance
                    ).any()
                    or (
                        (after['upper_bound'] - before['upper_bound']).abs()
                        > config.point_tolerance
                    ).any()
                )
                compilation = compile_strict_problem(
                    bundle,
                    graph,
                    quantities,
                    point_tolerance=config.point_tolerance,
                )
                if not changed and not batch.target_results:
                    break
    else:
        strict_status = feasibility.feasibility.status
        if strict_status == 'INFEASIBLE':
            conflicts, conflict_runs = diagnose_infeasibility(
                compilation.problem,
                time_limit_seconds=(
                    config.strict_certification.per_solve_time_limit_seconds
                ),
                threads=config.strict_certification.threads,
            )
            solver_runs = pd.concat(
                [solver_runs, conflict_runs],
                ignore_index=True,
                sort=False,
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

    final_plan_config = replace(config.strict_certification, max_targets=None)
    plan = build_certification_plan(
        bundle,
        compilation.target_catalog_grid,
        quantities,
        final_plan_config,
        policy,
    )
    plan['attempted'] = plan['target_id'].astype(str).isin(attempted)
    plan['completed'] = plan['target_id'].astype(str).isin(completed)
    plan['execution_order'] = plan['target_id'].astype(str).map(attempt_order)
    plan['selected'] = plan['attempted']
    plan.loc[plan['attempted'], 'skip_reason'] = None
    plan.loc[
        ~plan['attempted'] & plan['already_identified'].astype(bool),
        'skip_reason',
    ] = 'IDENTIFIED_WITHOUT_LP'
    if total_budget is not None and len(attempted) >= total_budget:
        plan.loc[
            ~plan['attempted'] & ~plan['already_identified'].astype(bool),
            'skip_reason',
        ] = 'TOTAL_BUDGET_EXHAUSTED'

    primary_grid = build_regional_okved2_grid(
        bundle,
        quantities,
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
        quantities,
        as_of_date=config.as_of_date,
        dataset_id=dataset_id,
        strict_model_id=strict_model_id,
        execution_run_id=execution_run_id,
    )
    strict_facts = primary_grid[primary_grid['is_strict_fact'].astype(bool)].copy()
    closure_fact_count = int(
        (
            primary_grid['derivation_method'].eq('DETERMINISTIC_CLOSURE')
            & primary_grid['identification_status'].astype(str).str.contains(
                'IDENTIFIED', regex=False
            )
        ).sum()
    )
    lp_identified = int(strict_facts['is_lp_certified'].astype(bool).sum())
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
            quantities['quantity_kind'].eq('ATOMIC_COMPONENT').sum()
        ),
        regional_metric_rows=len(primary_grid),
        raw_publication_observations=int(
            graph.observation_bindings_grid['source_series']
            .astype(str)
            .ne('01_05_D')
            .sum()
        ),
        unique_publication_constraints=len(
            compilation.problem.constraints_grid
        ),
        closure_passes=closure_passes,
        closure_identified_facts=closure_fact_count,
        lp_identified_facts=lp_identified,
        strict_facts=len(strict_facts),
        certification_targets_attempted=len(attempted),
        certification_targets_completed=len(completed),
    )
    audit = pd.DataFrame(
        [
            {'key': 'created_at_utc', 'value': datetime.now(timezone.utc).isoformat()},
            {'key': 'strategy_box_version', 'value': _package_version()},
            {'key': 'dataset_id', 'value': dataset_id},
            {'key': 'strict_model_id', 'value': strict_model_id},
            {'key': 'execution_run_id', 'value': execution_run_id},
            {'key': 'strict_status', 'value': strict_status},
            {'key': 'publication_step', 'value': config.publication_step},
            {'key': 'source_rows', 'value': len(bundle.source_grid)},
            {'key': 'component_quantities', 'value': summary.component_quantities},
            {'key': 'regional_metric_rows', 'value': len(primary_grid)},
            {'key': 'strict_variables', 'value': compilation.problem.num_variables},
            {'key': 'strict_constraints', 'value': compilation.problem.num_constraints},
            {'key': 'strict_nnz', 'value': compilation.problem.matrix.nnz},
            {'key': 'closure_passes', 'value': closure_passes},
            {'key': 'strict_facts', 'value': len(strict_facts)},
            {'key': 'targets_attempted', 'value': len(attempted)},
            {'key': 'targets_completed', 'value': len(completed)},
            {
                'key': 'conditional_bridge',
                'value': 'separate operation; never executed inside strict run',
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
        derivations_grid=derivations,
        constraints_grid=compilation.problem.constraints_grid,
        variables_grid=compilation.problem.variables_grid,
        certification_plan_grid=plan,
        solver_runs_grid=solver_runs,
        conflicts_grid=conflicts,
        audit_grid=audit,
        summary=summary,
        _source_bundle=bundle,
        _strict_problem=compilation.problem,
    )
