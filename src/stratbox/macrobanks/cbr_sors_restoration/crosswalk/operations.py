from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from time import perf_counter

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsCrosswalkConfig
from stratbox.macrobanks.cbr_sors_restoration.crosswalk.closure import (
    CrosswalkClosureConflictError,
    close_crosswalk_bounds,
)
from stratbox.macrobanks.cbr_sors_restoration.crosswalk.mapping import (
    read_crosswalk_scenarios,
)
from stratbox.macrobanks.cbr_sors_restoration.crosswalk.problem import (
    CrosswalkCompilation,
    compile_crosswalk_problem,
    crosswalk_target,
)
from stratbox.macrobanks.cbr_sors_restoration.linear.highs import (
    HighsSession,
    SolveResult,
    SorsSolverDependencyError,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    PublicationInterval,
    RoundingPolicy,
)
from stratbox.macrobanks.cbr_sors_restoration.results import (
    SorsCrosswalkResult,
    SorsRestorationResult,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.certification import (
    certify_interval,
)


@dataclass(frozen=True)
class _ScenarioExecution:
    scenario_id: str
    status: str
    grid: pd.DataFrame
    compilation: CrosswalkCompilation
    derivations_grid: pd.DataFrame
    solver_runs_grid: pd.DataFrame
    conflicts_grid: pd.DataFrame
    diagnostics_grid: pd.DataFrame


def _overall_crosswalk_status(statuses: set[str]) -> str:
    resolved_statuses = {'OPTIMAL', 'INFEASIBLE', 'INFEASIBLE_BY_CLOSURE'}
    if statuses == {'OPTIMAL'}:
        return 'OPTIMAL'
    if 'OPTIMAL' in statuses and statuses <= resolved_statuses:
        # Every configured scenario is resolved. Proven-infeasible scenarios do
        # not weaken the envelope over the remaining feasible scenarios.
        return 'OPTIMAL_WITH_REJECTED_SCENARIOS'
    if 'OPTIMAL' in statuses:
        return 'PARTIAL'
    if statuses and statuses <= {'INFEASIBLE', 'INFEASIBLE_BY_CLOSURE'}:
        return 'INFEASIBLE'
    if 'SOLVER_UNAVAILABLE' in statuses:
        return 'SOLVER_UNAVAILABLE'
    return 'INCOMPLETE'


def _crosswalk_id(strict_model_id: str, config: SorsCrosswalkConfig) -> str:
    payload = json.dumps(
        {'strict_model_id': strict_model_id, 'config': config},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]


def _solve_record(
    solve_id: str,
    direction: str,
    result: SolveResult,
    *,
    scenario_id: str,
    target_id: str | None = None,
    attempt: int = 1,
    model_id: str = 'crosswalk:model:0001',
) -> dict[str, object]:
    return {
        'solve_id': solve_id,
        'model_layer': 'CROSSWALK',
        'scenario_id': scenario_id,
        'model_instance_id': model_id,
        'target_id': target_id,
        'direction': direction,
        'attempt_number': attempt,
        'status': result.status,
        'raw_status': result.raw_status,
        'objective_value': result.objective_value,
        'runtime_seconds': result.runtime_seconds,
        'simplex_iterations': result.simplex_iterations,
        'ipm_iterations': result.ipm_iterations,
        'solver_backend': 'highspy',
    }


def _target_outer_bounds(
    compilation: CrosswalkCompilation,
) -> pd.DataFrame:
    problem = compilation.problem
    records: list[dict[str, object]] = []
    for row in compilation.target_catalog_grid.itertuples(index=False):
        indices = np.asarray(row.indices, dtype=np.int32)
        coefficients = np.asarray(row.coefficients, dtype=float)
        lower = float(np.dot(coefficients, problem.col_lower[indices]))
        upper_values = problem.col_upper[indices]
        upper = (
            float('inf')
            if np.isinf(upper_values).any()
            else float(np.dot(coefficients, upper_values))
        )
        records.append(
            {
                'target_id': str(row.target_id),
                'region_code': str(row.region_code),
                'region_name': str(row.region_name),
                'class_code': str(row.class_code),
                'metric': str(row.metric),
                'lower_bound': lower + float(row.constant),
                'upper_bound': upper + float(row.constant),
            }
        )
    return pd.DataFrame(records)


def _scope_targets(
    strict_result: SorsRestorationResult,
    catalog: pd.DataFrame,
    scenario_grid: pd.DataFrame,
    config: SorsCrosswalkConfig,
) -> pd.DataFrame:
    selected = catalog.copy()
    scope = config.scope
    if config.mode == 'targets':
        if scope.region_codes:
            selected = selected[
                selected['region_code'].astype(str).isin(scope.region_codes)
            ]
        if scope.region_names:
            selected = selected[
                selected['region_name'].astype(str).isin(scope.region_names)
            ]
        if scope.class_codes:
            selected = selected[
                selected['class_code'].astype(str).isin(scope.class_codes)
            ]
        selected = selected[
            selected['metric'].astype(str).isin(scope.metrics)
        ]
    strict_keys = set(
        strict_result.regional_okved2_grid.loc[
            strict_result.regional_okved2_grid['is_strict_fact'].astype(bool),
            ['region_code', 'class_code', 'metric'],
        ]
        .astype(str)
        .agg(':'.join, axis=1)
    )
    closure_keys = set(
        scenario_grid.loc[
            scenario_grid['value_identified'].astype(bool),
            ['region_code', 'class_code', 'metric'],
        ]
        .astype(str)
        .agg(':'.join, axis=1)
    )
    selected['_key'] = (
        selected[['region_code', 'class_code', 'metric']]
        .astype(str)
        .agg(':'.join, axis=1)
    )
    selected = selected[
        ~selected['_key'].isin(strict_keys | closure_keys)
    ].drop(columns='_key')
    selected = selected.sort_values(
        ['region_code', 'class_code', 'metric'], kind='stable'
    )
    if config.max_targets is not None:
        selected = selected.head(config.max_targets)
    return selected.reset_index(drop=True)


def _supporting_relation_ids(
    compilation: CrosswalkCompilation,
) -> dict[str, tuple[str, ...]]:
    relations = compilation.relations_grid
    atom_relations = {
        str(row.legacy_atom_code): str(row.relation_id)
        for row in relations.itertuples(index=False)
        if str(row.relation_kind) == 'LEGACY_ATOM_FLOW_CONSERVATION'
    }
    out: dict[str, tuple[str, ...]] = {}
    for row in relations.itertuples(index=False):
        if str(row.relation_kind) != 'OKVED2_CLASS_FLOW_CONSERVATION':
            continue
        class_code = str(tuple(row.okved2_class_codes)[0])
        incoming = tuple(str(value) for value in row.incoming_legacy_atoms)
        out[class_code] = tuple(
            [str(row.relation_id)]
            + [atom_relations[atom] for atom in incoming if atom in atom_relations]
        )
    return out


def _base_scenario_grid(
    strict_result: SorsRestorationResult,
    compilation: CrosswalkCompilation,
    *,
    scenario_id: str,
    policy: RoundingPolicy,
    point_tolerance: float,
    feasibility_confirmed: bool,
) -> pd.DataFrame:
    outer = _target_outer_bounds(compilation).set_index(
        ['region_code', 'class_code', 'metric']
    )
    grid = strict_result.regional_okved2_grid.copy()
    already_strict = grid['is_strict_fact'].astype(bool).copy()
    relation_ids = _supporting_relation_ids(compilation)
    grid['scenario_id'] = scenario_id
    grid['scenario_ids'] = [(scenario_id,)] * len(grid)
    grid['scenario_coverage_complete'] = bool(feasibility_confirmed)
    grid['mapping_version'] = str(
        compilation.problem.metadata.get('mapping_version', 'UNKNOWN')
    )
    grid['supporting_relation_ids'] = grid['class_code'].astype(str).map(
        lambda value: relation_ids.get(value, tuple())
    )
    grid['evidence_layer'] = 'CROSSWALK'
    grid['evidence_profile'] = scenario_id
    grid['already_strict_fact'] = already_strict
    grid['is_strict_fact'] = False
    grid['is_reconstructed'] = False
    grid['is_estimate'] = False
    grid['is_benchmark_estimate'] = False
    grid['benchmark_value'] = None
    grid['bounds_certified'] = bool(feasibility_confirmed)
    grid['value_identified'] = False
    grid['is_final_accepted'] = False
    grid['is_lp_certified'] = False
    grid['lp_lower_certified'] = False
    grid['lp_upper_certified'] = False
    grid['derivation_method'] = 'CROSSWALK_CLOSURE'
    grid['identification_status'] = (
        'CROSSWALK_BOUNDED' if feasibility_confirmed else 'PROVISIONAL_CROSSWALK_BOUNDED'
    )
    grid['value_precision'] = 'NONE'
    grid['value'] = None
    grid['identified_value'] = None
    grid['identified_value_precision'] = 'NONE'
    grid['exact_value'] = None
    grid['published_value'] = None
    grid['lower_solve_id'] = None
    grid['upper_solve_id'] = None
    grid['proof_id'] = None
    grid['feasibility_confirmed'] = bool(feasibility_confirmed)

    for index, row in grid.iterrows():
        key = (str(row.region_code), str(row.class_code), str(row.metric))
        bounds = outer.loc[key]
        outer_lower = float(bounds.lower_bound)
        outer_upper = float(bounds.upper_bound)
        strict_lower = float(row.lower_bound)
        strict_upper = float(row.upper_bound)
        lower = max(outer_lower, strict_lower)
        upper = min(outer_upper, strict_upper)
        if lower > upper + point_tolerance:
            raise ValueError(
                'Crosswalk closure and strict bounds have an empty target interval: '
                f'{key} -> [{lower}, {upper}]'
            )
        lower_attained = (
            True
            if outer_lower > strict_lower + point_tolerance
            else bool(row.lower_attained)
        )
        upper_attained = (
            True
            if outer_upper < strict_upper - point_tolerance
            else bool(row.upper_attained)
        )
        grid.at[index, 'lower_bound'] = lower
        grid.at[index, 'upper_bound'] = upper
        grid.at[index, 'lower_attained'] = lower_attained
        grid.at[index, 'upper_attained'] = upper_attained
        grid.at[index, 'interval_width'] = upper - lower
        interval = PublicationInterval(
            lower,
            upper,
            lower_attained,
            upper_attained,
        )
        certification = certify_interval(
            interval,
            policy=policy,
            point_tolerance=point_tolerance,
        )
        identified = certification.value is not None
        if identified:
            grid.at[index, 'identified_value'] = certification.value
            grid.at[index, 'identified_value_precision'] = (
                certification.value_precision
            )
            grid.at[index, 'value_identified'] = bool(feasibility_confirmed)
            if feasibility_confirmed and not bool(already_strict.at[index]):
                grid.at[index, 'value'] = certification.value
                grid.at[index, 'value_precision'] = certification.value_precision
                grid.at[index, 'exact_value'] = certification.exact_value
                grid.at[index, 'published_value'] = certification.published_value
                grid.at[index, 'is_final_accepted'] = True
                grid.at[index, 'is_reconstructed'] = True
                grid.at[index, 'identification_status'] = (
                    f'CROSSWALK_{certification.identification_status}'
                )
                grid.at[index, 'proof_id'] = (
                    f'crosswalk:{scenario_id}:closure:'
                    f'{row.region_code}:{row.class_code}:{row.metric}'
                )
            elif feasibility_confirmed:
                grid.at[index, 'identification_status'] = (
                    'CROSSWALK_REDUNDANT_WITH_STRICT_'
                    f'{certification.identification_status}'
                )
            else:
                grid.at[index, 'identification_status'] = (
                    f'PROVISIONAL_CROSSWALK_{certification.identification_status}'
                )
        grid.at[index, 'is_zero_at_published_precision'] = bool(
            certification.is_zero_at_published_precision
        )
        grid.at[index, 'is_exact_zero'] = bool(certification.is_exact_zero)
    return grid


def _apply_target_results(
    grid: pd.DataFrame,
    catalog: pd.DataFrame,
    target_results: dict[str, tuple[SolveResult, SolveResult]],
    *,
    policy: RoundingPolicy,
    point_tolerance: float,
    scenario_id: str,
) -> pd.DataFrame:
    """Apply any successful min/max side to already certified closure bounds.

    A failed LP side does not invalidate the deterministic outer bound already
    confirmed by feasibility. Therefore one successful side may safely tighten
    the interval and can identify a publication bucket. `is_lp_certified` means
    that both exact extrema were solved; side-specific flags preserve the finer
    proof state.
    """
    out = grid.copy()
    if 'lp_lower_certified' not in out:
        out['lp_lower_certified'] = False
    if 'lp_upper_certified' not in out:
        out['lp_upper_certified'] = False
    positions = {
        (str(row.region_code), str(row.class_code), str(row.metric)): index
        for index, row in out.iterrows()
    }
    catalog_index = catalog.set_index('target_id')
    for target_id, (lower_result, upper_result) in target_results.items():
        row = catalog_index.loc[target_id]
        index = positions[
            (str(row.region_code), str(row.class_code), str(row.metric))
        ]
        lower_success = (
            lower_result.success and lower_result.objective_value is not None
        )
        upper_success = (
            upper_result.success and upper_result.objective_value is not None
        )
        if lower_success:
            solved_lower = float(lower_result.objective_value)
            if solved_lower > float(out.at[index, 'lower_bound']):
                out.at[index, 'lower_bound'] = solved_lower
                out.at[index, 'lower_attained'] = True
            out.at[index, 'lower_solve_id'] = f'crosswalk:min:{target_id}'
            out.at[index, 'lp_lower_certified'] = True
        if upper_success:
            solved_upper = float(upper_result.objective_value)
            if solved_upper < float(out.at[index, 'upper_bound']):
                out.at[index, 'upper_bound'] = solved_upper
                out.at[index, 'upper_attained'] = True
            out.at[index, 'upper_solve_id'] = f'crosswalk:max:{target_id}'
            out.at[index, 'lp_upper_certified'] = True
        if not (lower_success or upper_success):
            out.at[index, 'identification_status'] = (
                'CROSSWALK_SOLVER_INCOMPLETE_USING_CLOSURE_BOUNDS'
            )
            continue

        lower_value = float(out.at[index, 'lower_bound'])
        upper_value = float(out.at[index, 'upper_bound'])
        if lower_value > upper_value + point_tolerance:
            raise ValueError(
                'Crosswalk min/max produced an empty interval for '
                f'{target_id}: [{lower_value}, {upper_value}]'
            )
        out.at[index, 'interval_width'] = upper_value - lower_value
        interval = PublicationInterval(
            lower_value,
            upper_value,
            bool(out.at[index, 'lower_attained']),
            bool(out.at[index, 'upper_attained']),
        )
        certification = certify_interval(
            interval,
            policy=policy,
            point_tolerance=point_tolerance,
        )
        both_sides = bool(lower_success and upper_success)
        out.at[index, 'is_lp_certified'] = both_sides
        out.at[index, 'derivation_method'] = (
            'CROSSWALK_MINMAX' if both_sides else 'CROSSWALK_PARTIAL_MINMAX'
        )
        status_prefix = (
            'CROSSWALK_' if both_sides else 'CROSSWALK_PARTIAL_MINMAX_'
        )
        out.at[index, 'identification_status'] = (
            f'{status_prefix}{certification.identification_status}'
        )
        out.at[index, 'proof_id'] = (
            f'crosswalk:{scenario_id}:'
            f'{"minmax" if both_sides else "partial-minmax"}:{target_id}'
        )
        out.at[index, 'is_zero_at_published_precision'] = bool(
            certification.is_zero_at_published_precision
        )
        out.at[index, 'is_exact_zero'] = bool(certification.is_exact_zero)
        out.at[index, 'value'] = None
        out.at[index, 'value_precision'] = 'NONE'
        out.at[index, 'exact_value'] = None
        out.at[index, 'published_value'] = None
        out.at[index, 'identified_value'] = certification.value
        out.at[index, 'identified_value_precision'] = (
            certification.value_precision
            if certification.value is not None
            else 'NONE'
        )
        out.at[index, 'value_identified'] = certification.value is not None
        out.at[index, 'is_final_accepted'] = False
        out.at[index, 'is_reconstructed'] = False
        if (
            certification.value is not None
            and bool(out.at[index, 'bounds_certified'])
            and not bool(out.at[index, 'already_strict_fact'])
        ):
            out.at[index, 'value'] = certification.value
            out.at[index, 'value_precision'] = certification.value_precision
            out.at[index, 'exact_value'] = certification.exact_value
            out.at[index, 'published_value'] = certification.published_value
            out.at[index, 'is_final_accepted'] = True
            out.at[index, 'is_reconstructed'] = True
        elif certification.value is not None and bool(
            out.at[index, 'already_strict_fact']
        ):
            out.at[index, 'identification_status'] = (
                f'{status_prefix}REDUNDANT_WITH_STRICT_'
                f'{certification.identification_status}'
            )
    return out


def _run_scenario(
    strict_result: SorsRestorationResult,
    config: SorsCrosswalkConfig,
    scenario_id: str,
) -> _ScenarioExecution:
    assert strict_result._source_bundle is not None
    compilation = compile_crosswalk_problem(
        strict_result._source_bundle,
        strict_result.strict_components_grid,
        config,
        scenario_id,
    )
    conflicts = pd.DataFrame()
    try:
        closure = close_crosswalk_bounds(
            compilation.problem,
            tolerance=config.point_tolerance,
            max_passes=config.closure_max_passes,
        )
        compilation = CrosswalkCompilation(
            problem=closure.problem,
            target_catalog_grid=compilation.target_catalog_grid,
            mapping_edges_grid=compilation.mapping_edges_grid,
            relations_grid=compilation.relations_grid,
        )
        derivations = closure.derivations_grid
        closure_passes = closure.passes
        closure_updates = closure.bound_updates
        closure_converged = closure.converged
    except CrosswalkClosureConflictError as exc:
        conflicts = exc.conflicts_grid.copy()
        grid = _base_scenario_grid(
            strict_result,
            compilation,
            scenario_id=scenario_id,
            policy=RoundingPolicy(step=strict_result.summary.publication_step),
            point_tolerance=config.point_tolerance,
            feasibility_confirmed=False,
        )
        return _ScenarioExecution(
            scenario_id=scenario_id,
            status='INFEASIBLE_BY_CLOSURE',
            grid=grid,
            compilation=compilation,
            derivations_grid=pd.DataFrame(),
            solver_runs_grid=pd.DataFrame(),
            conflicts_grid=conflicts,
            diagnostics_grid=pd.DataFrame(
                [
                    {'key': 'scenario_id', 'value': scenario_id},
                    {'key': 'status', 'value': 'INFEASIBLE_BY_CLOSURE'},
                ]
            ),
        )

    records: list[dict[str, object]] = []
    target_results: dict[str, tuple[SolveResult, SolveResult]] = {}
    selected = pd.DataFrame()
    status = 'UNKNOWN'
    target_time_limit_reached = False
    solver_version: str | None = None
    feasibility_confirmed = False
    try:
        with HighsSession(
            compilation.problem,
            time_limit_seconds=config.per_solve_time_limit_seconds,
            threads=config.threads,
        ) as session:
            solver_version = session.version
            feasibility = session.solve_feasibility()
            records.append(
                _solve_record(
                    f'crosswalk:{scenario_id}:feasibility',
                    'FEASIBILITY',
                    feasibility,
                    scenario_id=scenario_id,
                )
            )
            status = feasibility.status
            feasibility_confirmed = feasibility.success
        if status == 'INFEASIBLE':
            conflicts = pd.DataFrame(
                [
                    {
                        'conflict_id': f'crosswalk:{scenario_id}:infeasible',
                        'scenario_id': scenario_id,
                        'conflict_status': 'INFEASIBLE',
                        'message': (
                            'The official publications and this crosswalk scenario '
                            'have no common feasible flow table.'
                        ),
                    }
                ]
            )
    except SorsSolverDependencyError as exc:
        status = 'SOLVER_UNAVAILABLE'
        conflicts = pd.DataFrame(
            [
                {
                    'conflict_id': f'crosswalk:{scenario_id}:solver-unavailable',
                    'scenario_id': scenario_id,
                    'conflict_status': status,
                    'message': str(exc),
                }
            ]
        )

    policy = RoundingPolicy(step=strict_result.summary.publication_step)
    grid = _base_scenario_grid(
        strict_result,
        compilation,
        scenario_id=scenario_id,
        policy=policy,
        point_tolerance=config.point_tolerance,
        feasibility_confirmed=feasibility_confirmed,
    )

    if feasibility_confirmed and config.mode in {'targets', 'all'}:
        selected = _scope_targets(
            strict_result,
            compilation.target_catalog_grid,
            grid,
            config,
        )
        catalog = compilation.target_catalog_grid.set_index('target_id')
        started = perf_counter()
        for chunk_start in range(0, len(selected), config.model_reset_interval):
            if (
                config.batch_time_limit_seconds is not None
                and perf_counter() - started >= config.batch_time_limit_seconds
            ):
                target_time_limit_reached = True
                break
            chunk = selected.iloc[
                chunk_start : chunk_start + config.model_reset_interval
            ]
            model_number = chunk_start // config.model_reset_interval + 1
            with HighsSession(
                compilation.problem,
                time_limit_seconds=config.per_solve_time_limit_seconds,
                threads=config.threads,
            ) as session:
                for position, row in enumerate(chunk.itertuples(index=False)):
                    if (
                        config.batch_time_limit_seconds is not None
                        and perf_counter() - started
                        >= config.batch_time_limit_seconds
                    ):
                        target_time_limit_reached = True
                        break
                    target = crosswalk_target(catalog.loc[str(row.target_id)])
                    model_id = (
                        f'crosswalk:{scenario_id}:model:{model_number:04d}'
                    )
                    lower = session.solve_target(target, maximize=False)
                    upper = session.solve_target(target, maximize=True)
                    records.append(
                        _solve_record(
                            f'crosswalk:{scenario_id}:min:{target.target_id}:attempt1',
                            'MIN',
                            lower,
                            scenario_id=scenario_id,
                            target_id=target.target_id,
                            model_id=model_id,
                        )
                    )
                    records.append(
                        _solve_record(
                            f'crosswalk:{scenario_id}:max:{target.target_id}:attempt1',
                            'MAX',
                            upper,
                            scenario_id=scenario_id,
                            target_id=target.target_id,
                            model_id=model_id,
                        )
                    )
                    if config.retry_failed_solve and not (
                        lower.success and upper.success
                    ):
                        with HighsSession(
                            compilation.problem,
                            time_limit_seconds=config.per_solve_time_limit_seconds,
                            threads=config.threads,
                        ) as retry:
                            lower = retry.solve_target(target, maximize=False)
                            upper = retry.solve_target(target, maximize=True)
                            retry_model = (
                                f'{model_id}:retry:{position + 1:04d}'
                            )
                            records.append(
                                _solve_record(
                                    f'crosswalk:{scenario_id}:min:'
                                    f'{target.target_id}:attempt2',
                                    'MIN',
                                    lower,
                                    scenario_id=scenario_id,
                                    target_id=target.target_id,
                                    attempt=2,
                                    model_id=retry_model,
                                )
                            )
                            records.append(
                                _solve_record(
                                    f'crosswalk:{scenario_id}:max:'
                                    f'{target.target_id}:attempt2',
                                    'MAX',
                                    upper,
                                    scenario_id=scenario_id,
                                    target_id=target.target_id,
                                    attempt=2,
                                    model_id=retry_model,
                                )
                            )
                    target_results[target.target_id] = (lower, upper)
        grid = _apply_target_results(
            grid,
            compilation.target_catalog_grid,
            target_results,
            policy=policy,
            point_tolerance=config.point_tolerance,
            scenario_id=scenario_id,
        )

    diagnostics = pd.DataFrame(
        [
            {'key': 'scenario_id', 'value': scenario_id},
            {'key': 'status', 'value': status},
            {'key': 'variables', 'value': compilation.problem.num_variables},
            {'key': 'constraints', 'value': compilation.problem.num_constraints},
            {
                'key': 'nonzero_coefficients',
                'value': compilation.problem.matrix.nnz,
            },
            {'key': 'closure_passes', 'value': closure_passes},
            {'key': 'closure_bound_updates', 'value': closure_updates},
            {'key': 'closure_converged', 'value': closure_converged},
            {'key': 'targets_selected', 'value': len(selected)},
            {'key': 'targets_attempted', 'value': len(target_results)},
            {
                'key': 'targets_completed',
                'value': sum(
                    lower.success and upper.success
                    for lower, upper in target_results.values()
                ),
            },
            {
                'key': 'target_time_limit_reached',
                'value': target_time_limit_reached,
            },
            {'key': 'solver_version', 'value': solver_version},
        ]
    )
    return _ScenarioExecution(
        scenario_id=scenario_id,
        status=status,
        grid=grid,
        compilation=compilation,
        derivations_grid=derivations,
        solver_runs_grid=pd.DataFrame(records),
        conflicts_grid=conflicts,
        diagnostics_grid=diagnostics,
    )


def _robust_envelope(
    strict_result: SorsRestorationResult,
    executions: list[_ScenarioExecution],
    *,
    policy: RoundingPolicy,
    point_tolerance: float,
) -> pd.DataFrame:
    resolved_statuses = {'OPTIMAL', 'INFEASIBLE', 'INFEASIBLE_BY_CLOSURE'}
    scenario_coverage_complete = all(
        execution.status in resolved_statuses for execution in executions
    )
    feasible = [execution for execution in executions if execution.status == 'OPTIMAL']
    if not feasible:
        empty = strict_result.regional_okved2_grid.copy()
        empty['evidence_layer'] = 'CROSSWALK'
        empty['evidence_profile'] = None
        empty['scenario_ids'] = [tuple()] * len(empty)
        empty['mapping_version'] = None
        empty['supporting_relation_ids'] = [tuple()] * len(empty)
        empty['bounds_certified'] = False
        empty['scenario_coverage_complete'] = scenario_coverage_complete
        empty['value_identified'] = False
        empty['is_final_accepted'] = False
        empty['is_benchmark_estimate'] = False
        empty['benchmark_value'] = None
        empty['already_strict_fact'] = empty['is_strict_fact'].astype(bool)
        empty['is_strict_fact'] = False
        empty['is_reconstructed'] = False
        empty['value'] = None
        empty['identification_status'] = 'CROSSWALK_NOT_FEASIBLE'
        return empty

    keys = ['region_code', 'class_code', 'metric']
    stacked = pd.concat(
        [execution.grid for execution in feasible], ignore_index=True
    )
    records: list[dict[str, object]] = []
    template = feasible[0].grid.set_index(keys)
    for key, group in stacked.groupby(keys, sort=False):
        row = template.loc[key].to_dict()
        lower_values = group['lower_bound'].astype(float)
        upper_values = group['upper_bound'].astype(float)
        lower = float(lower_values.min())
        upper = float(upper_values.max())
        lower_attained = bool(
            group.loc[
                (lower_values - lower).abs() <= point_tolerance,
                'lower_attained',
            ].astype(bool).any()
        )
        upper_attained = bool(
            group.loc[
                (upper_values - upper).abs() <= point_tolerance,
                'upper_attained',
            ].astype(bool).any()
        )
        scenarios = tuple(sorted(group['scenario_id'].astype(str).unique()))
        mapping_versions = tuple(
            sorted(group['mapping_version'].dropna().astype(str).unique())
        )
        supporting_relations = tuple(
            sorted(
                {
                    relation
                    for values in group['supporting_relation_ids']
                    for relation in (values if isinstance(values, tuple) else tuple())
                }
            )
        )
        bounds_certified = bool(
            scenario_coverage_complete
            and group['bounds_certified'].astype(bool).all()
        )
        interval = PublicationInterval(
            lower,
            upper,
            lower_attained,
            upper_attained,
        )
        certification = certify_interval(
            interval,
            policy=policy,
            point_tolerance=point_tolerance,
        )
        value_identified = bounds_certified and certification.value is not None
        already_strict_fact = bool(group['already_strict_fact'].astype(bool).all())
        identified = value_identified and not already_strict_fact
        row.update(
            {
                'region_code': key[0],
                'class_code': key[1],
                'metric': key[2],
                'scenario_id': None,
                'scenario_ids': scenarios,
                'evidence_layer': 'CROSSWALK',
                'evidence_profile': '|'.join(scenarios),
                'mapping_version': (
                    mapping_versions[0]
                    if len(mapping_versions) == 1
                    else '|'.join(mapping_versions)
                ),
                'supporting_relation_ids': supporting_relations,
                'lower_bound': lower,
                'upper_bound': upper,
                'lower_attained': lower_attained,
                'upper_attained': upper_attained,
                'interval_width': upper - lower,
                'bounds_certified': bounds_certified,
                'scenario_coverage_complete': scenario_coverage_complete,
                'already_strict_fact': already_strict_fact,
                'value_identified': value_identified,
                'is_final_accepted': identified,
                'is_reconstructed': identified,
                'is_strict_fact': False,
                'is_estimate': False,
                'is_benchmark_estimate': False,
                'benchmark_value': None,
                'value': certification.value if identified else None,
                'identified_value': certification.value if identified else None,
                'value_precision': (
                    certification.value_precision if identified else 'NONE'
                ),
                'identified_value_precision': (
                    certification.value_precision if identified else 'NONE'
                ),
                'exact_value': certification.exact_value if identified else None,
                'published_value': (
                    certification.published_value if identified else None
                ),
                'identification_status': (
                    (
                        'CROSSWALK_SCENARIO_ROBUST_REDUNDANT_WITH_STRICT_'
                        f'{certification.identification_status}'
                    )
                    if value_identified and already_strict_fact
                    else (
                        f'CROSSWALK_SCENARIO_ROBUST_'
                        f'{certification.identification_status}'
                        if identified
                        else (
                            'CROSSWALK_SCENARIO_ROBUST_BOUNDED'
                            if bounds_certified
                            else 'CROSSWALK_SCENARIO_BOUNDS_INCOMPLETE'
                        )
                    )
                ),
                'derivation_method': (
                    'CROSSWALK_SCENARIO_ENVELOPE'
                    if len(scenarios) > 1
                    else str(group['derivation_method'].iloc[0])
                ),
                'is_lp_certified': bool(
                    bounds_certified
                    and group['is_lp_certified'].astype(bool).all()
                ),
                'is_zero_at_published_precision': bool(
                    certification.is_zero_at_published_precision
                ),
                'is_exact_zero': bool(certification.is_exact_zero),
                'proof_id': (
                    'crosswalk:scenario-envelope:'
                    f'{key[0]}:{key[1]}:{key[2]}'
                    if bounds_certified
                    else None
                ),
            }
        )
        records.append(row)
    frame = pd.DataFrame(records)
    order_columns = [
        column
        for column in ('region_order', 'class_order', 'metric_order')
        if column in frame
    ]
    if order_columns:
        frame = frame.sort_values(order_columns, kind='stable')
    return frame.reset_index(drop=True)


def _primary_grid(
    strict_result: SorsRestorationResult,
    crosswalk_grid: pd.DataFrame,
) -> pd.DataFrame:
    strict = strict_result.regional_okved2_grid.copy()
    if 'feasibility_confirmed' in strict.columns:
        strict['bounds_certified'] = strict['feasibility_confirmed'].astype(bool)
    else:
        strict['bounds_certified'] = (
            strict_result.summary.strict_status == 'OPTIMAL'
        )
    strict['value_identified'] = strict['value'].notna()
    strict['is_final_accepted'] = strict['value'].notna()
    strict['is_estimate'] = False
    strict['is_benchmark_estimate'] = False
    strict['benchmark_value'] = None
    strict['evidence_profile'] = strict['rules_version'].astype(str)
    strict['scenario_ids'] = [tuple()] * len(strict)

    crosswalk_index = crosswalk_grid.set_index(
        ['region_code', 'class_code', 'metric']
    )
    for index, row in strict.iterrows():
        if bool(row.is_strict_fact):
            continue
        key = (str(row.region_code), str(row.class_code), str(row.metric))
        if key not in crosswalk_index.index:
            continue
        replacement = crosswalk_index.loc[key]
        for column in crosswalk_grid.columns:
            if column in {'region_code', 'class_code', 'metric'}:
                continue
            if column not in strict.columns:
                strict[column] = None
            strict.at[index, column] = replacement[column]
    return strict


def run_sors_crosswalk(
    strict_result: SorsRestorationResult,
    config: SorsCrosswalkConfig,
) -> SorsCrosswalkResult:
    if config.mode == 'disabled':
        raise ValueError(
            'Crosswalk mode is disabled; choose feasibility, targets or all'
        )
    if strict_result._source_bundle is None:
        raise ValueError('Strict result does not contain its source bundle')
    known = set(read_crosswalk_scenarios(config.mapping_version))
    unknown = sorted(set(config.scenario_ids) - known)
    if unknown:
        raise ValueError(f'Unknown crosswalk scenarios: {unknown}')

    crosswalk_run_id = _crosswalk_id(
        strict_result.summary.strict_model_id,
        config,
    )
    executions = [
        _run_scenario(strict_result, config, scenario_id)
        for scenario_id in config.scenario_ids
    ]
    policy = RoundingPolicy(step=strict_result.summary.publication_step)
    robust = _robust_envelope(
        strict_result,
        executions,
        policy=policy,
        point_tolerance=config.point_tolerance,
    )
    robust['crosswalk_run_id'] = crosswalk_run_id
    primary = _primary_grid(strict_result, robust)
    primary['crosswalk_run_id'] = crosswalk_run_id
    facts = robust[robust['is_final_accepted'].astype(bool)].copy()

    def concat(attribute: str) -> pd.DataFrame:
        frames = [getattr(execution, attribute) for execution in executions]
        frames = [frame for frame in frames if not frame.empty]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    scenario_grid = pd.concat(
        [execution.grid for execution in executions], ignore_index=True
    )
    mapping = pd.concat(
        [execution.compilation.mapping_edges_grid for execution in executions],
        ignore_index=True,
    ).drop_duplicates()
    relations = pd.concat(
        [execution.compilation.relations_grid for execution in executions],
        ignore_index=True,
    ).drop_duplicates()
    constraints = pd.concat(
        [execution.compilation.problem.constraints_grid for execution in executions],
        ignore_index=True,
    )
    variables = pd.concat(
        [execution.compilation.problem.variables_grid for execution in executions],
        ignore_index=True,
    )
    diagnostics = concat('diagnostics_grid')
    diagnostics = pd.concat(
        [
            pd.DataFrame(
                [
                    {'key': 'crosswalk_run_id', 'value': crosswalk_run_id},
                    {'key': 'mapping_version', 'value': config.mapping_version},
                    {'key': 'scenario_policy', 'value': config.scenario_policy},
                    {
                        'key': 'configured_scenarios',
                        'value': tuple(config.scenario_ids),
                    },
                    {
                        'key': 'feasible_scenarios',
                        'value': tuple(
                            execution.scenario_id
                            for execution in executions
                            if execution.status == 'OPTIMAL'
                        ),
                    },
                    {'key': 'crosswalk_facts', 'value': len(facts)},
                ]
            ),
            diagnostics,
        ],
        ignore_index=True,
    )
    statuses = {execution.status for execution in executions}
    status = _overall_crosswalk_status(statuses)

    audit = pd.DataFrame(
        [
            {
                'key': 'strict_model_id',
                'value': strict_result.summary.strict_model_id,
            },
            {'key': 'crosswalk_run_id', 'value': crosswalk_run_id},
            {'key': 'mapping_version', 'value': config.mapping_version},
            {'key': 'status', 'value': status},
            {
                'key': 'acceptance_rule',
                'value': (
                    'value is populated only when the feasible min/max envelope '
                    'is a point or one publication bucket'
                ),
            },
        ]
    )
    return SorsCrosswalkResult(
        regional_okved2_grid=primary,
        crosswalk_bounds_grid=robust,
        crosswalk_facts_grid=facts,
        scenario_bounds_grid=scenario_grid,
        mapping_edges_grid=mapping,
        relations_grid=relations,
        constraints_grid=constraints,
        variables_grid=variables,
        derivations_grid=concat('derivations_grid'),
        diagnostics_grid=diagnostics,
        solver_runs_grid=concat('solver_runs_grid'),
        conflicts_grid=concat('conflicts_grid'),
        audit_grid=audit,
        crosswalk_run_id=crosswalk_run_id,
        status=status,
        _strict_result=strict_result,
    )
