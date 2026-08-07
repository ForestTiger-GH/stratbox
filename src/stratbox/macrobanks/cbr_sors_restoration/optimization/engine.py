from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.evidence import (
    ROUNDING_OPTIMAL_TIER,
    ROUNDING_PREFERRED_TIER,
    ROUNDING_SELECTED_TIER,
)
from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsOptimizationConfig,
    SorsSourceBundle,
)
from stratbox.macrobanks.cbr_sors_restoration.optimization.distortion import (
    configure_optimal_face_session,
    solve_rounding_profile,
)
from stratbox.macrobanks.cbr_sors_restoration.optimization.selection import (
    run_controlled_selection,
)
from stratbox.macrobanks.cbr_sors_restoration.optimization.targets import (
    apply_strict_minmax_bounds,
    select_optimization_targets,
    solve_target_minmax,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    RoundingPolicy,
    SorsPublicationGraph,
    SorsPublicationLedger,
    run_publication_fixed_point,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.interval_closure import SorsIntervalClosureState
from stratbox.macrobanks.cbr_sors_restoration.strict.solver import run_strict_feasibility
from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import (
    StrictCompilation,
    refresh_strict_problem_bounds,
)


class SorsOptimizationFixedPointLimitError(RuntimeError):
    """Optimization kept producing facts beyond the configured safety fuse."""


@dataclass(frozen=True)
class SorsOptimizationExecution:
    quantities_grid: pd.DataFrame
    facts_ledger_grid: pd.DataFrame
    current_facts_grid: pd.DataFrame
    derivations_grid: pd.DataFrame
    solver_runs_grid: pd.DataFrame
    target_bounds_grid: pd.DataFrame
    rounding_profiles_grid: pd.DataFrame
    selection_attempts_grid: pd.DataFrame
    optimization_rounds_grid: pd.DataFrame
    deterministic_passes_grid: pd.DataFrame
    inheritance_events_grid: pd.DataFrame
    tokens_grid: pd.DataFrame
    status: str
    rounds: int
    targets_attempted: int
    new_facts: int


def _model_assumption_tier(quantities_grid: pd.DataFrame) -> int:
    lower = (
        int(quantities_grid['lower_assumption_tier'].fillna(0).astype(int).max())
        if 'lower_assumption_tier' in quantities_grid and not quantities_grid.empty
        else 0
    )
    upper = (
        int(quantities_grid['upper_assumption_tier'].fillna(0).astype(int).max())
        if 'upper_assumption_tier' in quantities_grid and not quantities_grid.empty
        else 0
    )
    return max(lower, upper)


def _promote_rounding_optimal_buckets(
    optimal_bounds: pd.DataFrame,
    quantities_grid: pd.DataFrame,
    ledger: SorsPublicationLedger,
    policy: RoundingPolicy,
    *,
    optimization_round: int,
    model_assumption_tier: int,
) -> set[str]:
    if optimal_bounds.empty:
        return set()
    lookup = quantities_grid.set_index('quantity_id', drop=False)
    promoted: set[str] = set()
    for row in optimal_bounds.itertuples(index=False):
        if row.lower_bound is None or row.upper_bound is None:
            continue
        bucket = policy.single_bucket(
            float(row.lower_bound),
            float(row.upper_bound),
            lower_attained=True,
            upper_attained=True,
        )
        if bucket is None:
            continue
        quantity_id = str(row.quantity_id)
        if quantity_id not in lookup.index:
            continue
        quantity = lookup.loc[quantity_id]
        fact_tier = max(ROUNDING_OPTIMAL_TIER, int(model_assumption_tier))
        if fact_tier <= ROUNDING_OPTIMAL_TIER:
            method = 'ROUNDING_OPTIMUM_IDENTIFIED'
        elif fact_tier == ROUNDING_PREFERRED_TIER:
            method = 'ROUNDING_PREFERRED_CLOSURE'
        else:
            method = 'ROUNDING_SELECTED_CLOSURE'
        changed = ledger.promote_external_bucket(
            quantity,
            published_value=float(bucket),
            evidence_method=method,
            restoration_pass=0,
            optimization_round=optimization_round,
            proof_ids=(str(row.lower_solve_id), str(row.upper_solve_id)),
            details='One publication bucket across the minimum-rounding-distortion optimal face.',
            assumption_tier=fact_tier,
        )
        if changed:
            promoted.add(quantity_id)
    return promoted


def _promote_selected(
    accepted: pd.DataFrame,
    quantities_grid: pd.DataFrame,
    ledger: SorsPublicationLedger,
    *,
    optimization_round: int,
) -> set[str]:
    if accepted.empty:
        return set()
    lookup = quantities_grid.set_index('quantity_id', drop=False)
    promoted: set[str] = set()
    for row in accepted.itertuples(index=False):
        quantity_id = str(row.quantity_id)
        if quantity_id not in lookup.index:
            continue
        evidence_method = str(
            getattr(row, 'selection_evidence_method', 'ROUNDING_SELECTED')
        )
        preferred = evidence_method == 'ROUNDING_PREFERRED'
        proof_ids = tuple(
            str(value)
            for value in (
                getattr(row, 'competition_attempt_id', None),
                getattr(row, 'selection_attempt_id', None),
            )
            if value is not None and str(value) != 'nan'
        )
        changed = ledger.promote_external_bucket(
            lookup.loc[quantity_id],
            published_value=float(row.selected_bucket),
            evidence_method=evidence_method,
            restoration_pass=0,
            optimization_round=optimization_round,
            proof_ids=proof_ids,
            details=(
                'Publication bucket is decisively cheaper than alternative buckets by global '
                'L1 source-rounding cost inside the hard official publication '
                'intervals and is jointly validated inside the configured budget.'
                if preferred
                else
                'Common-benchmark publication bucket jointly validated without exceeding the '
                'configured relaxed-L1 budget and any optional L∞ cap.'
            ),
            assumption_tier=(
                ROUNDING_PREFERRED_TIER if preferred else ROUNDING_SELECTED_TIER
            ),
        )
        if changed:
            promoted.add(quantity_id)
    return promoted


def run_optimization_fixed_point(
    bundle: SorsSourceBundle,
    publication_graph: SorsPublicationGraph,
    closure_state: SorsIntervalClosureState,
    ledger: SorsPublicationLedger,
    compilation: StrictCompilation,
    config: SorsOptimizationConfig,
    *,
    policy: RoundingPolicy,
    point_tolerance: float,
    deterministic_max_passes: int,
    inheritance_enabled: bool = True,
) -> SorsOptimizationExecution:
    if config.mode == 'none':
        return SorsOptimizationExecution(
            quantities_grid=closure_state.quantities_grid.copy(),
            facts_ledger_grid=ledger.facts_grid(),
            current_facts_grid=ledger.facts_grid(current_only=True),
            derivations_grid=closure_state.derivations_grid.copy(),
            solver_runs_grid=pd.DataFrame(),
            target_bounds_grid=pd.DataFrame(),
            rounding_profiles_grid=pd.DataFrame(),
            selection_attempts_grid=pd.DataFrame(),
            optimization_rounds_grid=pd.DataFrame(),
            deterministic_passes_grid=pd.DataFrame(),
            inheritance_events_grid=pd.DataFrame(),
            tokens_grid=pd.DataFrame(),
            status='DISABLED',
            rounds=0,
            targets_attempted=0,
            new_facts=0,
        )

    initial_facts = len(ledger.current_quantity_ids)
    solver_frames: list[pd.DataFrame] = []
    bound_frames: list[pd.DataFrame] = []
    profile_rows: list[dict[str, object]] = []
    selection_frames: list[pd.DataFrame] = []
    round_rows: list[dict[str, object]] = []
    deterministic_frames: list[pd.DataFrame] = []
    inheritance_frames: list[pd.DataFrame] = []
    token_frames: list[pd.DataFrame] = []
    total_targets = 0
    status = 'FIXED_POINT'

    def revalidate_latent_feasibility(optimization_round: int, trigger: str) -> bool:
        current_problem = refresh_strict_problem_bounds(
            compilation.problem, closure_state.quantities_grid
        )
        check = run_strict_feasibility(current_problem, config)
        if not check.solver_runs_grid.empty:
            frame = check.solver_runs_grid.copy()
            frame['solve_id'] = frame['solve_id'].map(
                lambda value: f'optimization:{optimization_round}:{trigger}:{value}'
            )
            frame['model_layer'] = 'PUBLICATION_FEASIBILITY_GATE'
            frame['optimization_round'] = optimization_round
            frame['trigger'] = trigger
            solver_frames.append(frame)
        ledger.confirm_feasibility(bool(check.feasibility.success))
        return bool(check.feasibility.success)

    for optimization_round in range(1, config.max_fixed_point_rounds + 1):
        started = perf_counter()
        facts_before = len(ledger.current_quantity_ids)
        round_new_facts = 0
        strict_bound_updates = 0
        strict_attempts = 0
        rounding_attempts = 0
        selected_count = 0
        model_assumption_tier = _model_assumption_tier(closure_state.quantities_grid)

        current_problem = refresh_strict_problem_bounds(
            compilation.problem, closure_state.quantities_grid
        )
        targets = select_optimization_targets(
            bundle,
            compilation,
            closure_state.quantities_grid,
            config,
            already_fact_quantity_ids=ledger.current_quantity_ids,
        )
        if targets.empty:
            status = 'NO_TARGETS'
            round_rows.append({
                'optimization_round': optimization_round,
                'new_facts': 0,
                'strict_target_attempts': 0,
                'rounding_target_attempts': 0,
                'selected_facts': 0,
                'runtime_seconds': perf_counter() - started,
                'stop_reason': 'NO_TARGETS',
            })
            break

        if config.strict_minmax_enabled:
            strict_exec = solve_target_minmax(
                current_problem,
                targets,
                config,
                model_layer='STRICT_MINMAX',
            )
            strict_attempts = len(strict_exec.bounds_grid)
            total_targets += strict_attempts
            if not strict_exec.solver_runs_grid.empty:
                solver_frames.append(strict_exec.solver_runs_grid)
            if strict_exec.status == 'SOLVER_UNAVAILABLE':
                status = 'SOLVER_UNAVAILABLE'
                round_rows.append({
                    'optimization_round': optimization_round,
                    'new_facts': 0,
                    'strict_target_attempts': 0,
                    'rounding_target_attempts': 0,
                    'selected_facts': 0,
                    'runtime_seconds': perf_counter() - started,
                    'stop_reason': 'SOLVER_UNAVAILABLE',
                })
                break
            strict_bounds = strict_exec.bounds_grid.copy()
            if not strict_bounds.empty:
                strict_bounds['optimization_round'] = optimization_round
                strict_bounds['assumption_tier'] = model_assumption_tier
                strict_bounds['evidence_surface'] = (
                    'STRICT_OFFICIAL_FEASIBLE_SET'
                    if model_assumption_tier == 0
                    else 'PUBLICATION_CONSTRAINED_FEASIBLE_SET'
                )
                bound_frames.append(strict_bounds)
            updated, changed_bounds, proof_ids = apply_strict_minmax_bounds(
                closure_state.quantities_grid,
                strict_exec.bounds_grid,
                tolerance=point_tolerance,
                assumption_tier=model_assumption_tier,
            )
            strict_bound_updates = len(changed_bounds)
            if changed_bounds:
                closure_state.replace_quantities(updated)
            ledger.promote_interval_facts(
                closure_state.quantities_grid,
                policy=policy,
                point_tolerance=point_tolerance,
                restoration_pass=0,
                optimization_round=optimization_round,
                proof_ids_by_quantity=proof_ids,
            )
            det = run_publication_fixed_point(
                closure_state,
                publication_graph,
                ledger,
                policy=policy,
                point_tolerance=point_tolerance,
                max_passes=deterministic_max_passes,
                optimization_round=optimization_round,
                inheritance_enabled=inheritance_enabled,
            )
            if not det.passes_grid.empty:
                frame = det.passes_grid.copy()
                frame['trigger'] = 'STRICT_MINMAX'
                deterministic_frames.append(frame)
            if not det.inheritance_events_grid.empty:
                inheritance_frames.append(det.inheritance_events_grid)
            if not det.tokens_grid.empty:
                token_frames.append(det.tokens_grid)
            if det.new_facts > 0 and not revalidate_latent_feasibility(
                optimization_round, 'STRICT_MINMAX_DETERMINISTIC_CASCADE'
            ):
                status = 'PUBLICATION_FEASIBILITY_CONFLICT'
                round_rows.append({
                    'optimization_round': optimization_round,
                    'new_facts': len(ledger.current_quantity_ids) - facts_before,
                    'strict_bound_updates': strict_bound_updates,
                    'strict_target_attempts': strict_attempts,
                    'rounding_target_attempts': 0,
                    'selected_facts': 0,
                    'runtime_seconds': perf_counter() - started,
                    'stop_reason': 'PUBLICATION_FEASIBILITY_CONFLICT',
                })
                break
            round_new_facts = len(ledger.current_quantity_ids) - facts_before
            if round_new_facts > 0:
                round_rows.append({
                    'optimization_round': optimization_round,
                    'new_facts': round_new_facts,
                    'strict_bound_updates': strict_bound_updates,
                    'strict_target_attempts': strict_attempts,
                    'rounding_target_attempts': 0,
                    'selected_facts': 0,
                    'runtime_seconds': perf_counter() - started,
                    'stop_reason': 'NEW_STRICT_FACTS_RESTART',
                })
                continue

        if config.rounding_optimal_enabled:
            model_assumption_tier = _model_assumption_tier(closure_state.quantities_grid)
            current_problem = refresh_strict_problem_bounds(
                compilation.problem, closure_state.quantities_grid
            )
            profile = solve_rounding_profile(
                current_problem,
                config,
                point_tolerance=point_tolerance,
            )
            if not profile.solver_runs_grid.empty:
                solver_frames.append(profile.solver_runs_grid)
            profile_rows.append({
                'optimization_round': optimization_round,
                'status': profile.status,
                'tau_star_mln': profile.tau_star,
                'l1_star_mln': profile.l1_star,
                'relaxed_l1_star_mln': profile.relaxed_l1_star,
                'relaxed_linf_at_l1_mln': profile.relaxed_linf_at_l1,
                'distortion_constraints': int(profile.problem.metadata.get('distortion_variable_count', 0)),
                'scope_linf_mln': profile.scope_linf_mln,
                'scope_l1_mln': profile.scope_l1_mln,
                'assumption_tier': model_assumption_tier,
            })
            if profile.status == 'SOLVER_UNAVAILABLE':
                status = 'SOLVER_UNAVAILABLE'
                round_rows.append({
                    'optimization_round': optimization_round,
                    'new_facts': 0,
                    'strict_bound_updates': strict_bound_updates,
                    'strict_target_attempts': strict_attempts,
                    'rounding_target_attempts': 0,
                    'selected_facts': 0,
                    'runtime_seconds': perf_counter() - started,
                    'stop_reason': 'SOLVER_UNAVAILABLE',
                })
                break
            if profile.status == 'OPTIMAL':
                unresolved_targets = select_optimization_targets(
                    bundle,
                    compilation,
                    closure_state.quantities_grid,
                    config,
                    already_fact_quantity_ids=ledger.current_quantity_ids,
                )

                def setup(session):
                    configure_optimal_face_session(
                        session,
                        profile,
                        linf_extra=point_tolerance,
                        l1_extra=point_tolerance,
                    )

                optimal_exec = solve_target_minmax(
                    profile.problem,
                    unresolved_targets,
                    config,
                    model_layer='ROUNDING_OPTIMAL_MINMAX',
                    session_setup=setup,
                )
                rounding_attempts = len(optimal_exec.bounds_grid)
                total_targets += rounding_attempts
                if not optimal_exec.solver_runs_grid.empty:
                    solver_frames.append(optimal_exec.solver_runs_grid)
                optimal_bounds = optimal_exec.bounds_grid.copy()
                if not optimal_bounds.empty:
                    optimal_bounds['optimization_round'] = optimization_round
                    optimal_bounds['assumption_tier'] = max(
                        ROUNDING_OPTIMAL_TIER, model_assumption_tier
                    )
                    optimal_bounds['evidence_surface'] = 'ROUNDING_OPTIMAL_FACE'
                    bound_frames.append(optimal_bounds)
                promoted_optimal = _promote_rounding_optimal_buckets(
                    optimal_exec.bounds_grid,
                    closure_state.quantities_grid,
                    ledger,
                    policy,
                    optimization_round=optimization_round,
                    model_assumption_tier=model_assumption_tier,
                )
                if promoted_optimal:
                    updated, _ = ledger.apply_current_facts_to_quantities(
                        closure_state.quantities_grid,
                        policy=policy,
                        tolerance=point_tolerance,
                    )
                    closure_state.replace_quantities(updated)
                    det = run_publication_fixed_point(
                        closure_state,
                        publication_graph,
                        ledger,
                        policy=policy,
                        point_tolerance=point_tolerance,
                        max_passes=deterministic_max_passes,
                        optimization_round=optimization_round,
                        inheritance_enabled=inheritance_enabled,
                    )
                    if not det.passes_grid.empty:
                        frame = det.passes_grid.copy()
                        frame['trigger'] = 'ROUNDING_OPTIMUM_IDENTIFIED'
                        deterministic_frames.append(frame)
                    if not det.inheritance_events_grid.empty:
                        inheritance_frames.append(det.inheritance_events_grid)
                    if not det.tokens_grid.empty:
                        token_frames.append(det.tokens_grid)
                    if det.new_facts > 0 and not revalidate_latent_feasibility(
                        optimization_round, 'ROUNDING_OPTIMUM_DETERMINISTIC_CASCADE'
                    ):
                        status = 'PUBLICATION_FEASIBILITY_CONFLICT'
                        round_rows.append({
                            'optimization_round': optimization_round,
                            'new_facts': len(ledger.current_quantity_ids) - facts_before,
                            'strict_bound_updates': strict_bound_updates,
                            'strict_target_attempts': strict_attempts,
                            'rounding_target_attempts': rounding_attempts,
                            'selected_facts': 0,
                            'runtime_seconds': perf_counter() - started,
                            'stop_reason': 'PUBLICATION_FEASIBILITY_CONFLICT',
                        })
                        break
                    round_new_facts = len(ledger.current_quantity_ids) - facts_before
                    round_rows.append({
                        'optimization_round': optimization_round,
                        'new_facts': round_new_facts,
                        'strict_bound_updates': strict_bound_updates,
                        'strict_target_attempts': strict_attempts,
                        'rounding_target_attempts': rounding_attempts,
                        'selected_facts': 0,
                        'runtime_seconds': perf_counter() - started,
                        'stop_reason': 'NEW_ROUNDING_OPTIMAL_FACTS_RESTART',
                    })
                    continue

                selection = run_controlled_selection(
                    unresolved_targets,
                    optimal_exec.bounds_grid,
                    profile,
                    config,
                    policy,
                )
                if not selection.attempts_grid.empty:
                    frame = selection.attempts_grid.copy()
                    frame['optimization_round'] = optimization_round
                    selection_frames.append(frame)
                if not selection.solver_runs_grid.empty:
                    solver_frames.append(selection.solver_runs_grid)
                selected_methods = set(
                    selection.accepted_grid.get(
                        'selection_evidence_method', pd.Series(dtype=str)
                    ).dropna().astype(str)
                ) if not selection.accepted_grid.empty else set()
                promoted_selected = _promote_selected(
                    selection.accepted_grid,
                    closure_state.quantities_grid,
                    ledger,
                    optimization_round=optimization_round,
                )
                selected_count = len(promoted_selected)
                if promoted_selected:
                    updated, _ = ledger.apply_current_facts_to_quantities(
                        closure_state.quantities_grid,
                        policy=policy,
                        tolerance=point_tolerance,
                    )
                    closure_state.replace_quantities(updated)
                    det = run_publication_fixed_point(
                        closure_state,
                        publication_graph,
                        ledger,
                        policy=policy,
                        point_tolerance=point_tolerance,
                        max_passes=deterministic_max_passes,
                        optimization_round=optimization_round,
                        inheritance_enabled=inheritance_enabled,
                    )
                    if not det.passes_grid.empty:
                        frame = det.passes_grid.copy()
                        frame['trigger'] = (
                            'ROUNDING_PREFERRED'
                            if selected_methods == {'ROUNDING_PREFERRED'}
                            else 'ROUNDING_SELECTED'
                        )
                        deterministic_frames.append(frame)
                    if not det.inheritance_events_grid.empty:
                        inheritance_frames.append(det.inheritance_events_grid)
                    if not det.tokens_grid.empty:
                        token_frames.append(det.tokens_grid)
                    if det.new_facts > 0 and not revalidate_latent_feasibility(
                        optimization_round, 'ROUNDING_SELECTION_DETERMINISTIC_CASCADE'
                    ):
                        status = 'PUBLICATION_FEASIBILITY_CONFLICT'
                        round_rows.append({
                            'optimization_round': optimization_round,
                            'new_facts': len(ledger.current_quantity_ids) - facts_before,
                            'strict_bound_updates': strict_bound_updates,
                            'strict_target_attempts': strict_attempts,
                            'rounding_target_attempts': rounding_attempts,
                            'selected_facts': selected_count,
                            'runtime_seconds': perf_counter() - started,
                            'stop_reason': 'PUBLICATION_FEASIBILITY_CONFLICT',
                        })
                        break
                    round_new_facts = len(ledger.current_quantity_ids) - facts_before
                    round_rows.append({
                        'optimization_round': optimization_round,
                        'new_facts': round_new_facts,
                        'strict_bound_updates': strict_bound_updates,
                        'strict_target_attempts': strict_attempts,
                        'rounding_target_attempts': rounding_attempts,
                        'selected_facts': selected_count,
                        'runtime_seconds': perf_counter() - started,
                        'stop_reason': 'NEW_SELECTED_FACTS_RESTART',
                    })
                    continue

        round_rows.append({
            'optimization_round': optimization_round,
            'new_facts': 0,
            'strict_bound_updates': strict_bound_updates,
            'strict_target_attempts': strict_attempts,
            'rounding_target_attempts': rounding_attempts,
            'selected_facts': selected_count,
            'runtime_seconds': perf_counter() - started,
            'stop_reason': 'NO_NEW_FACTS',
        })
        status = 'FIXED_POINT'
        break
    else:
        raise SorsOptimizationFixedPointLimitError(
            'SORS optimization did not reach a fixed point within '
            f'{config.max_fixed_point_rounds} rounds. The round limit is a safety '
            'fuse; a partially closed optimization state is not a final result.'
        )

    return SorsOptimizationExecution(
        quantities_grid=closure_state.quantities_grid.copy(),
        facts_ledger_grid=ledger.facts_grid(),
        current_facts_grid=ledger.facts_grid(current_only=True),
        derivations_grid=closure_state.derivations_grid.copy(),
        solver_runs_grid=(pd.concat(solver_frames, ignore_index=True, sort=False) if solver_frames else pd.DataFrame()),
        target_bounds_grid=(pd.concat(bound_frames, ignore_index=True, sort=False) if bound_frames else pd.DataFrame()),
        rounding_profiles_grid=pd.DataFrame(profile_rows),
        selection_attempts_grid=(pd.concat(selection_frames, ignore_index=True, sort=False) if selection_frames else pd.DataFrame()),
        optimization_rounds_grid=pd.DataFrame(round_rows),
        deterministic_passes_grid=(pd.concat(deterministic_frames, ignore_index=True, sort=False) if deterministic_frames else pd.DataFrame()),
        inheritance_events_grid=(pd.concat(inheritance_frames, ignore_index=True, sort=False) if inheritance_frames else pd.DataFrame()),
        tokens_grid=(
            pd.concat(token_frames, ignore_index=True, sort=False)
            .drop_duplicates('token_id', keep='last')
            .reset_index(drop=True)
            if token_frames else pd.DataFrame()
        ),
        status=status,
        rounds=len(round_rows),
        targets_attempted=total_targets,
        new_facts=len(ledger.current_quantity_ids) - initial_facts,
    )
