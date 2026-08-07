from __future__ import annotations

from dataclasses import dataclass
from math import inf, isfinite

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsOptimizationConfig,
    SorsSourceBundle,
)
from stratbox.macrobanks.cbr_sors_restoration.linear.highs import (
    HighsSession,
    SolveResult,
    SorsSolverDependencyError,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import (
    StrictCompilation,
    linear_target_from_row,
)


@dataclass(frozen=True)
class SorsMinMaxExecution:
    bounds_grid: pd.DataFrame
    solver_runs_grid: pd.DataFrame
    backend: str | None
    version: str | None
    status: str


def _scope_region_codes(bundle: SorsSourceBundle, config: SorsOptimizationConfig) -> set[str]:
    scope = config.scope
    regions = bundle.atomic_regions_grid
    selected = set(str(v) for v in scope.region_codes)
    if scope.region_names:
        by_name = regions.set_index('region_name')['region_code'].astype(str).to_dict()
        missing = sorted(set(scope.region_names) - set(by_name))
        if missing:
            raise ValueError(f'Unknown SORS region names: {missing}')
        selected.update(by_name[name] for name in scope.region_names)
    return selected


def select_optimization_targets(
    bundle: SorsSourceBundle,
    compilation: StrictCompilation,
    quantities_grid: pd.DataFrame,
    config: SorsOptimizationConfig,
    *,
    already_fact_quantity_ids: set[str],
) -> pd.DataFrame:
    if config.mode == 'none':
        return pd.DataFrame()
    targets = compilation.target_catalog_grid.copy()
    targets = targets[~targets['quantity_id'].astype(str).isin(already_fact_quantity_ids)]
    if not config.include_internal_components:
        targets = targets[targets['target_kind'].eq('METRIC')]

    selected_regions = _scope_region_codes(bundle, config)
    if config.mode == 'targets':
        if selected_regions:
            targets = targets[targets['region_code'].astype(str).isin(selected_regions)]
        if config.scope.class_codes:
            targets = targets[targets['class_code'].astype(str).isin(config.scope.class_codes)]
        metric_mask = targets['target_kind'].eq('COMPONENT') | targets['metric'].astype(str).isin(
            config.scope.metrics
        )
        targets = targets[metric_mask]

    q = quantities_grid.set_index('quantity_id')
    target_lower: list[float] = []
    target_upper: list[float] = []
    for row in targets.itertuples(index=False):
        quantity_id = str(row.quantity_id)
        if quantity_id in q.index:
            item = q.loc[quantity_id]
            target_lower.append(float(item.lower_bound))
            target_upper.append(float(item.upper_bound))
        else:
            target_lower.append(0.0)
            target_upper.append(inf)
    targets['current_lower_bound'] = target_lower
    targets['current_upper_bound'] = target_upper
    targets['current_width'] = targets['current_upper_bound'] - targets['current_lower_bound']
    targets['finite_width'] = targets['current_width'].map(isfinite)
    targets['target_kind_rank'] = targets['target_kind'].map({'METRIC': 0, 'COMPONENT': 1}).fillna(2)
    targets['absolute_midpoint'] = (
        targets['current_lower_bound'].clip(lower=0)
        + targets['current_upper_bound'].where(targets['finite_width'], targets['current_lower_bound'])
    ) / 2.0
    # Narrow finite ranges first; user-facing metrics win ties.  This makes the
    # priority mode useful without changing the mathematical result of any proof.
    targets = targets.sort_values(
        ['finite_width', 'current_width', 'target_kind_rank', 'region_code', 'class_code', 'metric'],
        ascending=[False, True, True, True, True, True],
        kind='stable',
    )
    if config.mode in {'priority', 'targets'} and config.max_targets is not None:
        targets = targets.head(config.max_targets)
    return targets.reset_index(drop=True)


def _solve_record(
    *,
    solve_id: str,
    target_id: str,
    direction: str,
    result: SolveResult,
    backend: str,
    version: str,
    solver: str,
    model_layer: str,
) -> dict[str, object]:
    return {
        'solve_id': solve_id,
        'model_layer': model_layer,
        'target_id': target_id,
        'direction': direction,
        'status': result.status,
        'raw_status': result.raw_status,
        'objective_value': result.objective_value,
        'runtime_seconds': result.runtime_seconds,
        'simplex_iterations': result.simplex_iterations,
        'ipm_iterations': result.ipm_iterations,
        'solver_algorithm': solver,
        'solver_backend': backend,
        'solver_version': version,
    }


def _constant_result(value: float) -> SolveResult:
    return SolveResult(
        success=True,
        status='OPTIMAL',
        raw_status='BOUNDS_ONLY',
        objective_value=float(value),
        values=None,
        runtime_seconds=0.0,
        simplex_iterations=0,
        ipm_iterations=0,
    )


def solve_target_minmax(
    problem,
    targets_grid: pd.DataFrame,
    config: SorsOptimizationConfig,
    *,
    model_layer: str = 'STRICT_MINMAX',
    session_setup=None,
) -> SorsMinMaxExecution:
    if targets_grid.empty:
        return SorsMinMaxExecution(pd.DataFrame(), pd.DataFrame(), None, None, 'NO_TARGETS')
    records: list[dict[str, object]] = []
    bounds: list[dict[str, object]] = []
    backend: str | None = None
    version: str | None = None
    try:
        with HighsSession(
            problem,
            time_limit_seconds=config.per_solve_time_limit_seconds,
            threads=config.threads,
            solver=config.solver if model_layer == 'STRICT_MINMAX' else config.rounding_solver,
            run_crossover=config.run_crossover,
        ) as session:
            if session_setup is not None:
                session_setup(session)
            backend = session.backend
            version = session.version
            for position, row in enumerate(targets_grid.itertuples(index=False), start=1):
                target = linear_target_from_row(row)
                if len(target.indices) == 0:
                    lower = upper = _constant_result(target.constant)
                else:
                    lower = session.solve_target(target, maximize=False)
                    upper = session.solve_target(target, maximize=True)
                min_id = f'{model_layer.lower()}:{position:06d}:min'
                max_id = f'{model_layer.lower()}:{position:06d}:max'
                records.append(
                    _solve_record(
                        solve_id=min_id,
                        target_id=target.target_id,
                        direction='MIN',
                        result=lower,
                        backend=backend,
                        version=version,
                        solver=(config.solver if model_layer == 'STRICT_MINMAX' else config.rounding_solver),
                        model_layer=model_layer,
                    )
                )
                records.append(
                    _solve_record(
                        solve_id=max_id,
                        target_id=target.target_id,
                        direction='MAX',
                        result=upper,
                        backend=backend,
                        version=version,
                        solver=(config.solver if model_layer == 'STRICT_MINMAX' else config.rounding_solver),
                        model_layer=model_layer,
                    )
                )
                bounds.append(
                    {
                        'target_id': target.target_id,
                        'target_kind': str(row.target_kind),
                        'quantity_id': target.quantity_id,
                        'region_code': target.region_code,
                        'region_name': target.region_name,
                        'class_code': target.class_code,
                        'metric': target.metric,
                        'component': getattr(row, 'component', None),
                        'lower_bound': lower.objective_value if lower.success else None,
                        'upper_bound': upper.objective_value if upper.success else None,
                        'lower_solve_id': min_id,
                        'upper_solve_id': max_id,
                        'lower_status': lower.status,
                        'upper_status': upper.status,
                        'connected_component_ids': getattr(row, 'connected_component_ids', ()),
                    }
                )
    except SorsSolverDependencyError as exc:
        return SorsMinMaxExecution(
            pd.DataFrame(),
            pd.DataFrame([
                {
                    'solve_id': f'{model_layer.lower()}:solver_unavailable',
                    'model_layer': model_layer,
                    'status': 'SOLVER_UNAVAILABLE',
                    'raw_status': str(exc),
                }
            ]),
            'highspy',
            'unavailable',
            'SOLVER_UNAVAILABLE',
        )
    frame = pd.DataFrame(bounds)
    complete = (
        frame['lower_bound'].notna() & frame['upper_bound'].notna()
        if not frame.empty
        else pd.Series(dtype=bool)
    )
    status = 'OPTIMAL' if frame.empty or bool(complete.all()) else 'PARTIAL'
    return SorsMinMaxExecution(frame, pd.DataFrame(records), backend, version, status)


def apply_strict_minmax_bounds(
    quantities_grid: pd.DataFrame,
    bounds_grid: pd.DataFrame,
    *,
    tolerance: float,
    assumption_tier: int = 0,
) -> tuple[pd.DataFrame, set[str], dict[str, tuple[str, ...]]]:
    if bounds_grid.empty:
        return quantities_grid.copy(), set(), {}
    out = quantities_grid.copy()
    if 'lower_assumption_tier' not in out:
        out['lower_assumption_tier'] = 0
    if 'upper_assumption_tier' not in out:
        out['upper_assumption_tier'] = 0
    model_tier = int(assumption_tier)
    positions = {str(q): i for i, q in zip(out.index, out['quantity_id'], strict=True)}
    changed: set[str] = set()
    proofs: dict[str, tuple[str, ...]] = {}
    for row in bounds_grid.itertuples(index=False):
        if row.lower_bound is None or row.upper_bound is None:
            continue
        quantity_id = str(row.quantity_id)
        if quantity_id not in positions:
            continue
        index = positions[quantity_id]
        old_lower = float(out.at[index, 'lower_bound'])
        old_upper = float(out.at[index, 'upper_bound'])
        new_lower = max(old_lower, float(row.lower_bound))
        new_upper = min(old_upper, float(row.upper_bound))
        if new_lower > old_lower + tolerance:
            out.at[index, 'lower_bound'] = new_lower
            out.at[index, 'lower_attained'] = True
            out.at[index, 'lower_assumption_tier'] = model_tier
            changed.add(quantity_id)
        elif abs(new_lower - old_lower) <= tolerance and model_tier < int(out.at[index, 'lower_assumption_tier']):
            out.at[index, 'lower_assumption_tier'] = model_tier
            changed.add(quantity_id)
        if new_upper < old_upper - tolerance:
            out.at[index, 'upper_bound'] = new_upper
            out.at[index, 'upper_attained'] = True
            out.at[index, 'upper_assumption_tier'] = model_tier
            changed.add(quantity_id)
        elif abs(new_upper - old_upper) <= tolerance and model_tier < int(out.at[index, 'upper_assumption_tier']):
            out.at[index, 'upper_assumption_tier'] = model_tier
            changed.add(quantity_id)
        proofs[quantity_id] = (str(row.lower_solve_id), str(row.upper_solve_id))
    return out, changed, proofs
