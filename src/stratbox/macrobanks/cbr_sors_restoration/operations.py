from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pandas as pd

from stratbox import __version__ as STRATBOX_VERSION
from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsRunConfig,
    SorsSourceBundle,
    SorsSourceFiles,
)
from stratbox.macrobanks.cbr_sors_restoration.linear.elastic import diagnose_infeasibility
from stratbox.macrobanks.cbr_sors_restoration.optimization import run_optimization_fixed_point
from stratbox.macrobanks.cbr_sors_restoration.portfolio import (
    PORTFOLIO_SCOPES,
    PRIMARY_PORTFOLIO_SCOPE,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    RoundingPolicy,
    SorsPublicationLedger,
    build_publication_graph,
    run_publication_fixed_point,
)
from stratbox.macrobanks.cbr_sors_restoration.result_grid import (
    build_components_grid,
    build_regional_okved2_grid,
)
from stratbox.macrobanks.cbr_sors_restoration.results import (
    SorsRestorationResult,
    SorsRunSummary,
)
from stratbox.macrobanks.cbr_sors_restoration.sources import load_sors_sources
from stratbox.macrobanks.cbr_sors_restoration.strict.interval_closure import SorsIntervalClosureState
from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import (
    compile_strict_problem,
    refresh_strict_problem_bounds,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
    attach_observation_bindings,
    build_quantity_graph,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.solver import run_strict_feasibility


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
    strict_manifest = manifest[
        manifest['source_series'].isin(
            [
                '01_05_A', '01_02_A', '01_02_C', '01_03_C',
                '01_11', '01_11_F', '01_11_I', '01_12_A', '01_13_F', '01_13_I',
            ]
        )
    ]
    strict_model_id = _hash_payload(
        {
            'dataset_sources': strict_manifest[['source_series', 'sha256']].to_dict('records'),
            'publication_step': config.publication_step,
            'rules_version': config.rules_version,
            'primary_portfolio_scope': config.primary_portfolio_scope,
            'portfolio_scopes': PORTFOLIO_SCOPES,
            'regions': tuple(bundle.atomic_regions_grid['region_code'].astype(str)),
            'classes': tuple(bundle.okved2_classes_grid['class_code'].astype(str)),
        }
    )
    execution_run_id = _hash_payload(
        {
            'strict_model_id': strict_model_id,
            'deterministic': config.deterministic,
            'optimization': config.optimization,
            'package_version': _package_version(),
        }
    )
    return dataset_id, strict_model_id, execution_run_id


def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    usable = [frame.dropna(axis=1, how='all') for frame in frames if frame is not None and not frame.empty]
    return pd.concat(usable, ignore_index=True, sort=False) if usable else pd.DataFrame()


def run_sors_restoration(
    source: SorsSourceFiles | SorsSourceBundle,
    config: SorsRunConfig,
) -> SorsRestorationResult:
    """Restore one CBR SORS publication slice.

    Execution order is deliberate and methodologically significant:

    1. latent interval graph;
    2. zero/bucket + value-inheritance publication fixed point to exhaustion;
    3. one global latent feasibility gate;
    4. optimization waves, each returning new publication facts to the same
       deterministic fixed point before another optimization wave starts.
    """

    bundle = (
        source
        if isinstance(source, SorsSourceBundle)
        else load_sors_sources(
            source,
            config.as_of_date,
            publication_step=config.publication_step,
        )
    )
    if 'portfolio_scope' not in bundle.source_grid:
        raise ValueError(
            'SORS source bundle must carry portfolio_scope in source provenance'
        )
    source_scopes = tuple(
        sorted(set(bundle.source_grid['portfolio_scope'].dropna().astype(str)))
    )
    if config.primary_portfolio_scope != PRIMARY_PORTFOLIO_SCOPE:
        raise ValueError(
            'SORS outward restoration target is fixed to CORPORATE_TOTAL; '
            'SME and SME_IE are auxiliary constraint scopes only.'
        )
    if set(source_scopes) != set(PORTFOLIO_SCOPES):
        raise ValueError(
            'SORS multi-scope source bundle is incomplete: '
            f'expected={PORTFOLIO_SCOPES}, source={source_scopes}'
        )

    dataset_id, strict_model_id, execution_run_id = _identities(bundle, config)
    policy = RoundingPolicy(step=config.publication_step)

    graph = build_quantity_graph(bundle)
    bundle = attach_observation_bindings(bundle, graph)
    publication_graph = build_publication_graph(graph)
    ledger = SorsPublicationLedger()
    closure_state = SorsIntervalClosureState(
        graph,
        tolerance=config.point_tolerance / 10.0,
        max_passes=config.deterministic.interval_closure_max_passes,
    )

    deterministic = run_publication_fixed_point(
        closure_state,
        publication_graph,
        ledger,
        policy=policy,
        point_tolerance=config.point_tolerance,
        max_passes=config.deterministic.max_fixed_point_passes,
        inheritance_enabled=config.deterministic.inheritance_enabled,
    )

    compilation = compile_strict_problem(
        bundle,
        graph,
        closure_state.quantities_grid,
        point_tolerance=config.point_tolerance,
    )
    feasibility = run_strict_feasibility(compilation.problem, config.optimization)
    strict_status = feasibility.feasibility.status
    conflicts = pd.DataFrame()
    solver_frames = [feasibility.solver_runs_grid]

    optimization = None
    if feasibility.feasibility.success:
        strict_status = 'OPTIMAL'
        ledger.confirm_feasibility(True)
        optimization = run_optimization_fixed_point(
            bundle,
            publication_graph,
            closure_state,
            ledger,
            compilation,
            config.optimization,
            policy=policy,
            point_tolerance=config.point_tolerance,
            deterministic_max_passes=config.deterministic.max_fixed_point_passes,
            inheritance_enabled=config.deterministic.inheritance_enabled,
        )
        if not optimization.solver_runs_grid.empty:
            solver_frames.append(optimization.solver_runs_grid)
        if optimization.status == 'PUBLICATION_FEASIBILITY_CONFLICT':
            strict_status = 'PUBLICATION_FEASIBILITY_CONFLICT'
            conflicts = pd.DataFrame([
                {
                    'conflict_id': 'publication:optimization:latent_infeasible',
                    'conflict_status': 'PUBLICATION_FEASIBILITY_CONFLICT',
                    'message': (
                        'A publication fact promoted during optimization made the latent '
                        'model infeasible. All publication facts were withdrawn from the '
                        'accepted result surface.'
                    ),
                }
            ])
    else:
        ledger.confirm_feasibility(False)
        if strict_status == 'INFEASIBLE':
            try:
                conflicts, conflict_runs = diagnose_infeasibility(
                    compilation.problem,
                    time_limit_seconds=config.optimization.per_solve_time_limit_seconds,
                    threads=config.optimization.threads,
                )
                solver_frames.append(conflict_runs)
            except Exception as exc:
                conflicts = pd.DataFrame([
                    {
                        'conflict_id': 'publication_fixed_point:latent_infeasible',
                        'conflict_status': 'INFEASIBLE',
                        'message': (
                            'The latent model became infeasible after publication-level '
                            'promotion. Conflict localization could not complete.'
                        ),
                        'details': str(exc),
                    }
                ])
        else:
            conflicts = pd.DataFrame([
                {
                    'conflict_id': 'strict:feasibility:incomplete',
                    'conflict_status': strict_status,
                    'message': (
                        'Global latent feasibility was not confirmed. Publication facts '
                        'remain provisional and are not emitted as accepted values.'
                    ),
                }
            ])

    final_problem = refresh_strict_problem_bounds(
        compilation.problem, closure_state.quantities_grid
    )
    current_facts = ledger.facts_grid(current_only=True)
    primary_grid = build_regional_okved2_grid(
        bundle,
        closure_state.quantities_grid,
        ledger.facts_grid(),
        as_of_date=config.as_of_date,
        dataset_id=dataset_id,
        strict_model_id=strict_model_id,
        execution_run_id=execution_run_id,
        feasibility_confirmed=bool(ledger.feasibility_confirmed),
        rules_version=config.rules_version,
        solver_backend=feasibility.backend,
        solver_version=feasibility.version,
    )
    components_grid = build_components_grid(
        bundle,
        closure_state.quantities_grid,
        ledger.facts_grid(),
        as_of_date=config.as_of_date,
        dataset_id=dataset_id,
        strict_model_id=strict_model_id,
        execution_run_id=execution_run_id,
    )
    restored_facts = primary_grid[primary_grid['is_primary_fact'].astype(bool)].copy()
    component_facts = (
        current_facts[current_facts['quantity_kind'].astype(str).eq('ATOMIC_COMPONENT')].copy()
        if not current_facts.empty
        else pd.DataFrame()
    )

    accepted_current = (
        current_facts[current_facts['is_accepted_fact'].astype(bool)]
        if not current_facts.empty
        else pd.DataFrame()
    )
    primary_accepted = (
        accepted_current[
            accepted_current['portfolio_scope'].astype(str).eq(PRIMARY_PORTFOLIO_SCOPE)
        ]
        if not accepted_current.empty
        else pd.DataFrame()
    )
    auxiliary_accepted = (
        accepted_current[
            ~accepted_current['portfolio_scope'].astype(str).eq(PRIMARY_PORTFOLIO_SCOPE)
        ]
        if not accepted_current.empty
        else pd.DataFrame()
    )
    method_counts = (
        primary_accepted['evidence_method'].value_counts().to_dict()
        if not primary_accepted.empty
        else {}
    )
    publication_zero_facts = (
        int(primary_accepted['published_value'].astype(float).eq(0.0).sum())
        if not primary_accepted.empty
        else 0
    )
    deterministic_passes = deterministic.passes
    deterministic_bound_updates = deterministic.bound_updates
    fixed_point_frames = [deterministic.passes_grid]
    inheritance_frames = [deterministic.inheritance_events_grid]
    token_frames = [deterministic.tokens_grid]
    optimization_status = 'DISABLED'
    optimization_rounds = 0
    optimization_targets = 0
    rounding_profiles = pd.DataFrame()
    optimization_rounds_grid = pd.DataFrame()
    target_bounds_grid = pd.DataFrame()
    selection_attempts_grid = pd.DataFrame()
    if optimization is not None:
        optimization_status = optimization.status
        optimization_rounds = optimization.rounds
        optimization_targets = optimization.targets_attempted
        fixed_point_frames.append(optimization.deterministic_passes_grid)
        inheritance_frames.append(optimization.inheritance_events_grid)
        token_frames.append(optimization.tokens_grid)
        rounding_profiles = optimization.rounding_profiles_grid
        optimization_rounds_grid = optimization.optimization_rounds_grid
        target_bounds_grid = optimization.target_bounds_grid
        selection_attempts_grid = optimization.selection_attempts_grid
    all_fixed_point_passes = _concat(fixed_point_frames)
    all_inheritance = _concat(inheritance_frames)
    all_tokens = _concat(token_frames)
    if not all_tokens.empty and 'token_id' in all_tokens:
        all_tokens = all_tokens.drop_duplicates('token_id', keep='last').reset_index(drop=True)
    solver_runs = _concat(solver_frames)
    if not all_fixed_point_passes.empty:
        deterministic_passes = len(all_fixed_point_passes)
        deterministic_bound_updates = int(
            all_fixed_point_passes.get('interval_bound_updates', pd.Series(dtype=float)).fillna(0).sum()
        )

    tau_star = None
    l1_star = None
    relaxed_l1_star = None
    relaxed_linf_at_l1 = None
    if not rounding_profiles.empty:
        optimal_profiles = rounding_profiles[rounding_profiles['status'].eq('OPTIMAL')]
        if not optimal_profiles.empty:
            profile_row = optimal_profiles.iloc[-1]
            tau_star = float(profile_row.tau_star_mln)
            l1_star = float(profile_row.l1_star_mln)
            relaxed_l1_value = getattr(profile_row, 'relaxed_l1_star_mln', None)
            relaxed_linf_value = getattr(profile_row, 'relaxed_linf_at_l1_mln', None)
            if relaxed_l1_value is not None and not pd.isna(relaxed_l1_value):
                relaxed_l1_star = float(relaxed_l1_value)
            if relaxed_linf_value is not None and not pd.isna(relaxed_linf_value):
                relaxed_linf_at_l1 = float(relaxed_linf_value)

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
        portfolio_scopes=PORTFOLIO_SCOPES,
        primary_component_quantities=int(
            (
                closure_state.quantities_grid['quantity_kind'].eq('ATOMIC_COMPONENT')
                & closure_state.quantities_grid['portfolio_scope'].astype(str).eq(PRIMARY_PORTFOLIO_SCOPE)
            ).sum()
        ),
        auxiliary_component_quantities=int(
            (
                closure_state.quantities_grid['quantity_kind'].eq('ATOMIC_COMPONENT')
                & ~closure_state.quantities_grid['portfolio_scope'].astype(str).eq(PRIMARY_PORTFOLIO_SCOPE)
            ).sum()
        ),
        latent_component_quantities=int(
            closure_state.quantities_grid['quantity_kind'].eq('ATOMIC_COMPONENT').sum()
        ),
        regional_metric_rows=len(primary_grid),
        raw_publication_observations=len(graph.observation_bindings_grid),
        unique_publication_constraints=int(
            compilation.problem.constraints_grid['model_layer'].astype(str).eq('STRICT').sum()
        ),
        deterministic_status=deterministic.status,
        deterministic_passes=deterministic_passes,
        deterministic_bound_updates=deterministic_bound_updates,
        publication_facts=len(primary_accepted),
        publication_zero_facts=publication_zero_facts,
        inherited_facts=int(method_counts.get('PUBLISHED_VALUE_INHERITED', 0)),
        strict_identified_facts=int(
            method_counts.get('LATENT_POINT_IDENTIFIED', 0)
            + method_counts.get('PUBLISHED_BUCKET_IDENTIFIED', 0)
        ),
        rounding_optimal_facts=int(method_counts.get('ROUNDING_OPTIMUM_IDENTIFIED', 0)),
        rounding_preferred_facts=int(
            method_counts.get('ROUNDING_PREFERRED', 0)
            + method_counts.get('ROUNDING_PREFERRED_CLOSURE', 0)
        ),
        rounding_selected_facts=int(
            method_counts.get('ROUNDING_SELECTED', 0)
            + method_counts.get('ROUNDING_SELECTED_CLOSURE', 0)
        ),
        auxiliary_publication_facts=len(auxiliary_accepted),
        optimization_status=optimization_status,
        optimization_rounds=optimization_rounds,
        optimization_targets_attempted=optimization_targets,
        tau_star_mln=tau_star,
        l1_star_mln=l1_star,
        relaxed_l1_star_mln=relaxed_l1_star,
        relaxed_linf_at_l1_mln=relaxed_linf_at_l1,
    )

    audit = pd.DataFrame([
        {'key': 'created_at_utc', 'value': datetime.now(timezone.utc).isoformat()},
        {'key': 'strategy_box_version', 'value': _package_version()},
        {'key': 'dataset_id', 'value': dataset_id},
        {'key': 'strict_model_id', 'value': strict_model_id},
        {'key': 'execution_run_id', 'value': execution_run_id},
        {'key': 'rules_version', 'value': config.rules_version},
        {'key': 'primary_portfolio_scope', 'value': config.primary_portfolio_scope},
        {'key': 'auxiliary_portfolio_scopes', 'value': ('SME', 'SME_IE')},
        {'key': 'strict_status', 'value': strict_status},
        {'key': 'deterministic_status', 'value': deterministic.status},
        {'key': 'optimization_status', 'value': optimization_status},
        {'key': 'publication_step', 'value': config.publication_step},
        {'key': 'strict_variables', 'value': final_problem.num_variables},
        {'key': 'solver_constraints', 'value': final_problem.num_constraints},
        {
            'key': 'official_publication_constraints',
            'value': int(
                final_problem.constraints_grid['model_layer'].astype(str).eq('STRICT').sum()
            ),
        },
        {'key': 'strict_nnz', 'value': final_problem.matrix.nnz},
        {'key': 'portfolio_scopes', 'value': PORTFOLIO_SCOPES},
        {'key': 'primary_component_quantities', 'value': summary.primary_component_quantities},
        {'key': 'auxiliary_component_quantities', 'value': summary.auxiliary_component_quantities},
        {'key': 'latent_component_quantities', 'value': summary.latent_component_quantities},
        {'key': 'publication_partitions', 'value': len(publication_graph.partitions_grid)},
        {'key': 'publication_facts', 'value': summary.publication_facts},
        {'key': 'auxiliary_publication_facts', 'value': summary.auxiliary_publication_facts},
        {'key': 'publication_zero_facts', 'value': summary.publication_zero_facts},
        {'key': 'inherited_facts', 'value': summary.inherited_facts},
        {'key': 'rounding_tau_star_mln', 'value': tau_star},
        {'key': 'rounding_l1_star_mln', 'value': l1_star},
        {'key': 'rounding_relaxed_l1_star_mln', 'value': relaxed_l1_star},
        {'key': 'rounding_relaxed_linf_at_l1_mln', 'value': relaxed_linf_at_l1},
        {
            'key': 'restoration_architecture',
            'value': (
                'latent interval graph → deterministic publication fixed point '
                '(zero/bucket ↔ inheritance) → global feasibility → strict min/max '
                '→ deterministic fixed point → minimum rounding distortion → '
                'optimal-face certification/selection → deterministic fixed point'
            ),
        },
        {
            'key': 'crosswalk_relation_system',
            'value': 'separate conditional evidence layer after the official publication fixed point',
        },
    ])

    return SorsRestorationResult(
        source_grid=bundle.source_grid,
        source_manifest_grid=bundle.source_manifest_grid,
        validation_grid=bundle.validation_grid,
        regional_okved2_grid=primary_grid,
        components_grid=components_grid,
        restored_facts_grid=restored_facts,
        derivations_grid=closure_state.derivations_grid,
        constraints_grid=final_problem.constraints_grid,
        variables_grid=final_problem.variables_grid,
        solver_runs_grid=solver_runs,
        conflicts_grid=conflicts,
        audit_grid=audit,
        summary=summary,
        facts_ledger_grid=ledger.facts_grid(),
        current_component_facts_grid=component_facts,
        publication_partitions_grid=publication_graph.partitions_grid,
        inheritance_events_grid=all_inheritance,
        publication_tokens_grid=all_tokens,
        promotion_events_grid=ledger.promotion_events_grid(),
        fixed_point_passes_grid=all_fixed_point_passes,
        optimization_rounds_grid=optimization_rounds_grid,
        target_bounds_grid=target_bounds_grid,
        rounding_profiles_grid=rounding_profiles,
        selection_attempts_grid=selection_attempts_grid,
        _source_bundle=bundle,
        _strict_problem=final_problem,
    )
