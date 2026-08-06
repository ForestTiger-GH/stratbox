from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsCellResolutionConfig,
    SorsSourceBundle,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.strict.cells import build_cell_work_plan
from stratbox.macrobanks.cbr_sors_restoration.strict.closure import SorsClosureState
from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import (
    StrictCompilation,
    refresh_strict_problem_bounds,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.ledger import SorsFactLedger
from stratbox.macrobanks.cbr_sors_restoration.strict.subsystem import SorsSubsystemBuilder
from stratbox.macrobanks.cbr_sors_restoration.strict.target_solver import (
    SorsCellSolverPool,
    apply_cell_proof,
    prove_cell_uniqueness,
)


@dataclass(frozen=True)
class SorsCellResolutionExecution:
    quantities_grid: pd.DataFrame
    derivations_grid: pd.DataFrame
    facts_ledger_grid: pd.DataFrame
    current_facts_grid: pd.DataFrame
    cell_target_plan_grid: pd.DataFrame
    cell_attempts_grid: pd.DataFrame
    cell_subsystems_grid: pd.DataFrame
    promotion_events_grid: pd.DataFrame
    fixed_point_passes_grid: pd.DataFrame
    solver_runs_grid: pd.DataFrame
    attempted_counts: dict[str, int]
    completed_target_ids: frozenset[str]
    status: str
    fixed_point_passes: int
    target_attempts: int
    target_values_resolved: int
    target_values_resolved_by_local_system: int


def _target_is_identified(
    quantities_grid: pd.DataFrame,
    quantity_id: str,
    policy: RoundingPolicy,
) -> bool:
    row = quantities_grid.set_index('quantity_id').loc[quantity_id]
    return policy.single_bucket(
        float(row.lower_bound),
        float(row.upper_bound),
        lower_attained=bool(row.lower_attained),
        upper_attained=bool(row.upper_attained),
    ) is not None


def run_cell_resolution(
    bundle: SorsSourceBundle,
    graph,
    compilation: StrictCompilation,
    closure_state: SorsClosureState,
    config: SorsCellResolutionConfig,
    policy: RoundingPolicy,
    *,
    point_tolerance: float,
    feasibility_confirmed: bool = True,
) -> SorsCellResolutionExecution:
    target_catalog = compilation.cell_target_catalog_grid
    ledger = SorsFactLedger()
    if feasibility_confirmed:
        initial_promoted, _ = ledger.promote_from_quantities(
            closure_state.quantities_grid,
            target_catalog,
            closure_state.derivations_grid,
            policy=policy,
            point_tolerance=point_tolerance,
            restoration_pass=0,
        )
    else:
        initial_promoted = set()
    attempted_counts: dict[str, int] = {}
    completed_ids: set[str] = set(
        target_catalog.loc[
            target_catalog['quantity_id'].astype(str).isin(initial_promoted),
            'target_id',
        ].astype(str)
    )
    attempts: list[dict[str, object]] = []
    subsystems: list[dict[str, object]] = []
    fixed_point_rows: list[dict[str, object]] = []
    solver_runs: list[pd.DataFrame] = []
    total_attempts = 0
    started = perf_counter()

    if config.mode == 'closure':
        plan = build_cell_work_plan(
            bundle,
            target_catalog,
            closure_state.quantities_grid,
            graph.relations_grid,
            config,
            policy,
            attempted_counts=attempted_counts,
            completed_ids=completed_ids,
            point_tolerance=point_tolerance,
        )
        return SorsCellResolutionExecution(
            quantities_grid=closure_state.quantities_grid,
            derivations_grid=closure_state.derivations_grid,
            facts_ledger_grid=ledger.facts_grid(),
            current_facts_grid=ledger.facts_grid(current_only=True),
            cell_target_plan_grid=plan,
            cell_attempts_grid=pd.DataFrame(),
            cell_subsystems_grid=pd.DataFrame(),
            promotion_events_grid=ledger.promotion_events_grid(),
            fixed_point_passes_grid=pd.DataFrame(),
            solver_runs_grid=pd.DataFrame(),
            attempted_counts=attempted_counts,
            completed_target_ids=frozenset(completed_ids),
            status='CLOSURE_COMPLETE',
            fixed_point_passes=0,
            target_attempts=0,
            target_values_resolved=len(completed_ids),
            target_values_resolved_by_local_system=0,
        )

    problem = refresh_strict_problem_bounds(
        compilation.problem, closure_state.quantities_grid
    )
    builder = SorsSubsystemBuilder(bundle, problem, target_catalog)
    status = 'FIXED_POINT'
    last_plan = pd.DataFrame()
    with SorsCellSolverPool(config) as solver_pool:
        for fixed_point_pass in range(1, config.max_fixed_point_passes + 1):
            if (
                config.run_time_limit_seconds is not None
                and perf_counter() - started >= config.run_time_limit_seconds
            ):
                status = 'RUN_TIME_LIMIT'
                break
            plan = build_cell_work_plan(
                bundle,
                target_catalog,
                closure_state.quantities_grid,
                graph.relations_grid,
                config,
                policy,
                attempted_counts=attempted_counts,
                completed_ids=completed_ids,
                point_tolerance=point_tolerance,
            )
            last_plan = plan
            candidates = plan[plan['selected'].astype(bool)].copy()
            if config.max_target_attempts is not None:
                remaining = config.max_target_attempts - total_attempts
                if remaining <= 0:
                    status = 'TARGET_BUDGET_EXHAUSTED'
                    break
                candidates = candidates.head(remaining)
            if candidates.empty:
                status = 'FIXED_POINT'
                break

            pass_started = perf_counter()
            pass_attempts = 0
            pass_bound_updates = 0
            pass_new_facts = 0
            pass_resolved_targets = 0
            for target_row in candidates.itertuples(index=False):
                if (
                    config.run_time_limit_seconds is not None
                    and perf_counter() - started >= config.run_time_limit_seconds
                ):
                    status = 'RUN_TIME_LIMIT'
                    break
                target_id = str(target_row.target_id)
                quantity_id = str(target_row.quantity_id)
                if _target_is_identified(
                    closure_state.quantities_grid, quantity_id, policy
                ):
                    completed_ids.add(target_id)
                    continue
                attempted_counts[target_id] = attempted_counts.get(target_id, 0) + 1
                total_attempts += 1
                pass_attempts += 1
                attempt_id = (
                    f'cell-attempt:{total_attempts:08d}:{target_id}:'
                    f'r{attempted_counts[target_id]}'
                )
                attempt_started = perf_counter()
                cumulative_rows: set[int] = set()
                attempt_status = 'UNRESOLVED_GLOBAL'
                largest_horizon: str | None = None
                bound_changed_in_attempt = False
                facts_before = len(ledger.current_quantity_ids)
                proof_ids: tuple[str, ...] = ()
                previous_subsystem = None
                for horizon_index, horizon in enumerate(config.horizon_order, start=1):
                    largest_horizon = horizon
                    before_rows = len(cumulative_rows)
                    cumulative_rows.update(builder.rows_for_horizon(target_id, horizon))
                    new_constraint_count = len(cumulative_rows) - before_rows
                    if (
                        horizon != 'CELL'
                        and new_constraint_count == 0
                        and previous_subsystem is not None
                    ):
                        subsystems.append(
                            {
                                'subsystem_id': f'{attempt_id}:{horizon.lower()}',
                                'attempt_id': attempt_id,
                                'target_id': target_id,
                                'quantity_id': quantity_id,
                                'horizon': horizon,
                                'horizon_order': horizon_index,
                                'new_constraint_count': 0,
                                'cumulative_constraint_count': (
                                    previous_subsystem.problem.num_constraints
                                ),
                                'cumulative_variable_count': (
                                    previous_subsystem.problem.num_variables
                                ),
                                'cumulative_nnz': previous_subsystem.problem.matrix.nnz,
                                'supporting_constraint_ids': (
                                    previous_subsystem.supporting_constraint_ids
                                ),
                                'original_solver_rows': (
                                    previous_subsystem.original_solver_rows
                                ),
                                'original_solver_columns': (
                                    previous_subsystem.original_solver_columns
                                ),
                                'solver_skipped': True,
                                'skip_reason': 'NO_NEW_CONSTRAINTS',
                            }
                        )
                        continue
                    subsystem = builder.build(
                        target_id, horizon, cumulative_rows, attempt_id=attempt_id
                    )
                    if subsystem is None:
                        attempt_status = 'IDENTIFIED_BEFORE_SOLVER'
                        completed_ids.add(target_id)
                        break
                    subsystems.append(
                        {
                            'subsystem_id': subsystem.subsystem_id,
                            'attempt_id': attempt_id,
                            'target_id': target_id,
                            'quantity_id': quantity_id,
                            'horizon': horizon,
                            'horizon_order': horizon_index,
                            'new_constraint_count': new_constraint_count,
                            'cumulative_constraint_count': subsystem.problem.num_constraints,
                            'cumulative_variable_count': subsystem.problem.num_variables,
                            'cumulative_nnz': subsystem.problem.matrix.nnz,
                            'solver_skipped': False,
                            'skip_reason': None,
                            'supporting_constraint_ids': subsystem.supporting_constraint_ids,
                            'original_solver_rows': subsystem.original_solver_rows,
                            'original_solver_columns': subsystem.original_solver_columns,
                        }
                    )
                    previous_subsystem = subsystem
                    proof = prove_cell_uniqueness(
                        subsystem,
                        config,
                        policy,
                        point_tolerance=point_tolerance,
                        attempt_id=attempt_id,
                        solver_pool=solver_pool,
                    )
                    proof_ids = proof.proof_ids
                    if not proof.solver_runs_grid.empty:
                        solver_runs.append(proof.solver_runs_grid)
                    updated, changed = apply_cell_proof(
                        closure_state.quantities_grid,
                        proof,
                        point_tolerance=point_tolerance,
                        attempt_id=attempt_id,
                    )
                    if changed:
                        bound_changed_in_attempt = True
                        pass_bound_updates += 1
                        closure_state.replace_quantities(updated)
                        closure_state.run(seed_quantity_ids=(quantity_id,))
                        problem = refresh_strict_problem_bounds(
                            problem, closure_state.quantities_grid
                        )
                        builder.problem = problem
                        promoted: set[str] = set()
                        if proof.identified:
                            direct, _ = ledger.promote_from_quantities(
                                closure_state.quantities_grid,
                                target_catalog,
                                closure_state.derivations_grid,
                                policy=policy,
                                point_tolerance=point_tolerance,
                                restoration_pass=fixed_point_pass,
                                uniqueness_basis='LOCAL_TARGET_SYSTEM',
                                largest_horizon=horizon,
                                attempt_id=attempt_id,
                                proof_ids=proof.proof_ids,
                                quantity_ids={quantity_id},
                            )
                            promoted.update(direct)
                        cascade, _ = ledger.promote_from_quantities(
                            closure_state.quantities_grid,
                            target_catalog,
                            closure_state.derivations_grid,
                            policy=policy,
                            point_tolerance=point_tolerance,
                            restoration_pass=fixed_point_pass,
                        )
                        promoted.update(cascade)
                        pass_new_facts += len(promoted)
                        promoted_targets = target_catalog[
                            target_catalog['quantity_id'].astype(str).isin(promoted)
                        ]['target_id'].astype(str)
                        completed_ids.update(promoted_targets)
                    if proof.identified or target_id in completed_ids:
                        attempt_status = proof.status
                        pass_resolved_targets += 1
                        break
                    attempt_status = (
                        'SOLVER_INCOMPLETE'
                        if proof.status == 'SOLVER_INCOMPLETE'
                        else 'UNRESOLVED_AT_HORIZON'
                    )
                facts_after = len(ledger.current_quantity_ids)
                attempts.append(
                    {
                        'attempt_id': attempt_id,
                        'fixed_point_pass': fixed_point_pass,
                        'target_id': target_id,
                        'quantity_id': quantity_id,
                        'region_code': str(target_row.region_code),
                        'region_name': str(target_row.region_name),
                        'class_code': str(target_row.class_code),
                        'component': str(target_row.component),
                        'attempt_number_for_target': attempted_counts[target_id],
                        'status': attempt_status,
                        'largest_horizon': largest_horizon,
                        'bound_changed': bound_changed_in_attempt,
                        'new_fact_count': facts_after - facts_before,
                        'target_identified': target_id in completed_ids,
                        'proof_ids': proof_ids,
                        'runtime_seconds': perf_counter() - attempt_started,
                    }
                )
            fixed_point_rows.append(
                {
                    'fixed_point_pass': fixed_point_pass,
                    'target_attempts': pass_attempts,
                    'bound_updates': pass_bound_updates,
                    'new_facts': pass_new_facts,
                    'resolved_targets': pass_resolved_targets,
                    'total_current_facts': len(ledger.current_quantity_ids),
                    'total_target_attempts': total_attempts,
                    'runtime_seconds': perf_counter() - pass_started,
                    'stop_reason': None,
                }
            )
            if status == 'RUN_TIME_LIMIT':
                fixed_point_rows[-1]['stop_reason'] = status
                break
            if pass_bound_updates == 0 and pass_new_facts == 0:
                fixed_point_rows[-1]['stop_reason'] = 'NO_NEW_BOUNDS_OR_FACTS'
                status = 'FIXED_POINT'
                break
        else:
            status = 'FIXED_POINT_PASS_LIMIT'

    final_plan = build_cell_work_plan(
        bundle,
        target_catalog,
        closure_state.quantities_grid,
        graph.relations_grid,
        config,
        policy,
        attempted_counts=attempted_counts,
        completed_ids=completed_ids,
        point_tolerance=point_tolerance,
    )
    if final_plan.empty and not last_plan.empty:
        final_plan = last_plan
    attempts_grid = pd.DataFrame(attempts)
    resolved_by_local_system = int(
        attempts_grid.get('target_identified', pd.Series(dtype=bool))
        .fillna(False)
        .astype(bool)
        .sum()
    )
    return SorsCellResolutionExecution(
        quantities_grid=closure_state.quantities_grid,
        derivations_grid=closure_state.derivations_grid,
        facts_ledger_grid=ledger.facts_grid(),
        current_facts_grid=ledger.facts_grid(current_only=True),
        cell_target_plan_grid=final_plan,
        cell_attempts_grid=attempts_grid,
        cell_subsystems_grid=pd.DataFrame(subsystems),
        promotion_events_grid=ledger.promotion_events_grid(),
        fixed_point_passes_grid=pd.DataFrame(fixed_point_rows),
        solver_runs_grid=(
            pd.concat(
                [frame.dropna(axis=1, how='all') for frame in solver_runs],
                ignore_index=True,
                sort=False,
            )
            if solver_runs
            else pd.DataFrame()
        ),
        attempted_counts=attempted_counts,
        completed_target_ids=frozenset(completed_ids),
        status=status,
        fixed_point_passes=len(fixed_point_rows),
        target_attempts=total_attempts,
        target_values_resolved=len(completed_ids),
        target_values_resolved_by_local_system=resolved_by_local_system,
    )
