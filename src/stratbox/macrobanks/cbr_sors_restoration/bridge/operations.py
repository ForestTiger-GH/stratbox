from __future__ import annotations

import hashlib
import json
from time import perf_counter

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.bridge.problem import (
    bridge_target,
    compile_bridge_problem,
)
from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsBridgeConfig
from stratbox.macrobanks.cbr_sors_restoration.linear.highs import (
    HighsSession,
    SorsSolverDependencyError,
    SolveResult,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    PublicationInterval,
    RoundingPolicy,
)
from stratbox.macrobanks.cbr_sors_restoration.results import (
    SorsBridgeResult,
    SorsRestorationResult,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.certification import certify_interval


def _bridge_id(strict_model_id: str, config: SorsBridgeConfig) -> str:
    payload = json.dumps(
        {'strict_model_id': strict_model_id, 'config': config},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]


def _record(solve_id: str, direction: str, result: SolveResult, *, target_id: str | None = None, attempt: int = 1, model_id: str = 'bridge:model:0001') -> dict[str, object]:
    return {
        'solve_id': solve_id,
        'model_layer': 'CONDITIONAL_BRIDGE',
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


def _scope_targets(result: SorsRestorationResult, catalog: pd.DataFrame, config: SorsBridgeConfig) -> pd.DataFrame:
    scope = config.scope
    selected = catalog.copy()
    if scope.region_codes:
        selected = selected[selected['region_code'].astype(str).isin(scope.region_codes)]
    if scope.region_names:
        selected = selected[selected['region_name'].astype(str).isin(scope.region_names)]
    if scope.class_codes:
        selected = selected[selected['class_code'].astype(str).isin(scope.class_codes)]
    selected = selected[selected['metric'].astype(str).isin(scope.metrics)]
    strict_ids = set(
        result.regional_okved2_grid.loc[
            result.regional_okved2_grid['is_strict_fact'].astype(bool),
            ['region_code', 'class_code', 'metric'],
        ].astype(str).agg(':'.join, axis=1)
    )
    selected['_key'] = selected[['region_code', 'class_code', 'metric']].astype(str).agg(':'.join, axis=1)
    selected = selected[~selected['_key'].isin(strict_ids)].drop(columns='_key')
    selected = selected.sort_values(['region_code', 'class_code', 'metric'], kind='stable')
    if config.max_targets is not None:
        selected = selected.head(config.max_targets)
    return selected.reset_index(drop=True)


def _conditional_grid(
    strict_result: SorsRestorationResult,
    catalog: pd.DataFrame,
    optimum_values: np.ndarray | None,
    target_results: dict[str, tuple[SolveResult, SolveResult]],
    *,
    policy: RoundingPolicy,
) -> pd.DataFrame:
    grid = strict_result.regional_okved2_grid.copy()
    grid['evidence_layer'] = 'CONDITIONAL_BRIDGE'
    grid['is_strict_fact'] = False
    grid['is_reconstructed'] = False
    grid['is_lp_certified'] = False
    grid['is_estimate'] = optimum_values is not None
    grid['derivation_method'] = 'CONDITIONAL_BRIDGE'
    grid['identification_status'] = 'BRIDGE_NOT_CERTIFIED'
    grid['value_precision'] = 'NONE'
    grid['value'] = None
    grid['exact_value'] = None
    grid['published_value'] = None
    grid['lower_solve_id'] = None
    grid['upper_solve_id'] = None
    grid['bridge_objective_value'] = None
    positions = {
        (str(row.region_code), str(row.class_code), str(row.metric)): index
        for index, row in grid.iterrows()
    }
    catalog_index = catalog.set_index('target_id')
    if optimum_values is not None:
        for row in catalog.itertuples(index=False):
            index = positions[(str(row.region_code), str(row.class_code), str(row.metric))]
            value = float(np.dot(optimum_values[np.asarray(row.indices, dtype=np.int32)], np.asarray(row.coefficients, dtype=float)) + float(row.constant))
            grid.at[index, 'value'] = value
            grid.at[index, 'value_precision'] = 'MODEL_ESTIMATE'
            grid.at[index, 'identification_status'] = 'BENCHMARK_ESTIMATE'
    for target_id, (lower, upper) in target_results.items():
        row = catalog_index.loc[target_id]
        index = positions[(str(row.region_code), str(row.class_code), str(row.metric))]
        if lower.success and lower.objective_value is not None:
            grid.at[index, 'lower_bound'] = float(lower.objective_value)
            grid.at[index, 'lower_solve_id'] = f'bridge:min:{target_id}'
        if upper.success and upper.objective_value is not None:
            grid.at[index, 'upper_bound'] = float(upper.objective_value)
            grid.at[index, 'upper_solve_id'] = f'bridge:max:{target_id}'
        if lower.success and upper.success:
            interval = PublicationInterval(float(grid.at[index, 'lower_bound']), float(grid.at[index, 'upper_bound']), False, False)
            certification = certify_interval(interval, policy=policy, point_tolerance=1e-6)
            grid.at[index, 'identification_status'] = f'CONDITIONAL_{certification.identification_status}'
            grid.at[index, 'is_lp_certified'] = True
        else:
            grid.at[index, 'identification_status'] = 'BRIDGE_SOLVER_INCOMPLETE'
    return grid


def run_sors_bridge(
    strict_result: SorsRestorationResult,
    config: SorsBridgeConfig,
) -> SorsBridgeResult:
    if config.mode == 'disabled':
        raise ValueError('Bridge mode is disabled; choose optimum_only or targets')
    if strict_result._source_bundle is None:
        raise ValueError('Strict result does not contain its source bundle')
    bridge_run_id = _bridge_id(strict_result.summary.strict_model_id, config)
    compilation = compile_bridge_problem(
        strict_result._source_bundle,
        strict_result.strict_components_grid,
        config,
    )
    records: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = [
        {'key': 'bridge_run_id', 'value': bridge_run_id},
        {'key': 'mapping_version', 'value': config.mapping_version},
        {'key': 'variables', 'value': compilation.problem.num_variables},
        {'key': 'constraints', 'value': compilation.problem.num_constraints},
        {'key': 'nonzero_coefficients', 'value': compilation.problem.matrix.nnz},
    ]
    target_results: dict[str, tuple[SolveResult, SolveResult]] = {}
    optimum_values: np.ndarray | None = None
    conflicts = pd.DataFrame()
    status = 'UNKNOWN'
    optimum_value: float | None = None
    cap: float | None = None
    selected = pd.DataFrame()
    target_time_limit_reached = False
    try:
        with HighsSession(
            compilation.problem,
            time_limit_seconds=config.per_solve_time_limit_seconds,
            threads=config.threads,
        ) as session:
            optimum = session.solve_objective(
                compilation.problem.objective,
                include_values=True,
            )
            records.append(_record('bridge:optimum', 'OBJECTIVE', optimum))
            status = optimum.status
            if optimum.success and optimum.objective_value is not None:
                optimum_value = float(optimum.objective_value)
                optimum_values = optimum.values
                cap = optimum_value + float(config.objective_tolerance)
                diagnostics.extend(
                    [
                        {'key': 'minimum_reclassification_mass', 'value': optimum_value},
                        {'key': 'objective_cap', 'value': cap},
                    ]
                )
            elif optimum.status == 'INFEASIBLE':
                conflicts = pd.DataFrame(
                    [
                        {
                            'conflict_id': 'bridge:infeasible',
                            'conflict_status': 'INFEASIBLE',
                            'message': 'Conditional bridge model is infeasible.',
                        }
                    ]
                )
            else:
                conflicts = pd.DataFrame(
                    [
                        {
                            'conflict_id': 'bridge:incomplete',
                            'conflict_status': optimum.status,
                            'message': (
                                'Conditional bridge optimum was not confirmed; '
                                'this is not proof of infeasibility.'
                            ),
                        }
                    ]
                )

        if config.mode == 'targets' and cap is not None:
            selected = _scope_targets(
                strict_result,
                compilation.target_catalog_grid,
                config,
            )
            catalog = compilation.target_catalog_grid.set_index('target_id')
            target_started = perf_counter()
            for chunk_start in range(0, len(selected), config.model_reset_interval):
                if (
                    config.batch_time_limit_seconds is not None
                    and perf_counter() - target_started
                    >= config.batch_time_limit_seconds
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
                    session.add_objective_cap(compilation.problem.objective, cap)
                    for position, row in enumerate(chunk.itertuples(index=False)):
                        if (
                            config.batch_time_limit_seconds is not None
                            and perf_counter() - target_started
                            >= config.batch_time_limit_seconds
                        ):
                            target_time_limit_reached = True
                            break
                        target = bridge_target(catalog.loc[str(row.target_id)])
                        model_id = f'bridge:model:{model_number:04d}'
                        lower = session.solve_target(target, maximize=False)
                        upper = session.solve_target(target, maximize=True)
                        records.append(
                            _record(
                                f'bridge:min:{target.target_id}:attempt1',
                                'MIN',
                                lower,
                                target_id=target.target_id,
                                model_id=model_id,
                            )
                        )
                        records.append(
                            _record(
                                f'bridge:max:{target.target_id}:attempt1',
                                'MAX',
                                upper,
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
                                retry.add_objective_cap(
                                    compilation.problem.objective,
                                    cap,
                                )
                                lower = retry.solve_target(target, maximize=False)
                                upper = retry.solve_target(target, maximize=True)
                                retry_model = f'{model_id}:retry:{position + 1:04d}'
                                records.append(
                                    _record(
                                        f'bridge:min:{target.target_id}:attempt2',
                                        'MIN',
                                        lower,
                                        target_id=target.target_id,
                                        attempt=2,
                                        model_id=retry_model,
                                    )
                                )
                                records.append(
                                    _record(
                                        f'bridge:max:{target.target_id}:attempt2',
                                        'MAX',
                                        upper,
                                        target_id=target.target_id,
                                        attempt=2,
                                        model_id=retry_model,
                                    )
                                )
                        target_results[target.target_id] = (lower, upper)
    except SorsSolverDependencyError as exc:
        status = 'SOLVER_UNAVAILABLE'
        conflicts = pd.DataFrame(
            [
                {
                    'conflict_id': 'bridge:solver-unavailable',
                    'conflict_status': status,
                    'message': str(exc),
                }
            ]
        )

    policy = RoundingPolicy(step=strict_result.summary.publication_step)
    grid = _conditional_grid(
        strict_result,
        compilation.target_catalog_grid,
        optimum_values,
        target_results,
        policy=policy,
    )
    grid['bridge_run_id'] = bridge_run_id
    grid['bridge_objective_value'] = optimum_value
    diagnostics.extend(
        [
            {'key': 'status', 'value': status},
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
        ]
    )
    return SorsBridgeResult(
        regional_okved2_grid=grid,
        mapping_edges_grid=compilation.mapping_edges_grid,
        diagnostics_grid=pd.DataFrame(diagnostics),
        solver_runs_grid=pd.DataFrame(records),
        conflicts_grid=conflicts,
        audit_grid=pd.DataFrame(
            [
                {
                    'key': 'strict_model_id',
                    'value': strict_result.summary.strict_model_id,
                },
                {'key': 'bridge_run_id', 'value': bridge_run_id},
            ]
        ),
        bridge_run_id=bridge_run_id,
        status=status,
    )
