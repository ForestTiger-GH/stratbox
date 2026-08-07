from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsOptimizationConfig
from stratbox.macrobanks.cbr_sors_restoration.linear.highs import (
    HighsSession,
    SorsSolverDependencyError,
)
from stratbox.macrobanks.cbr_sors_restoration.optimization.distortion import (
    SorsRoundingProfile,
    configure_linf_face_session,
    distortion_linf_from_values,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    RoundingPolicy,
    solver_lower_bound,
    solver_upper_bound,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import linear_target_from_row


@dataclass(frozen=True)
class SorsSelectionExecution:
    accepted_grid: pd.DataFrame
    attempts_grid: pd.DataFrame
    solver_runs_grid: pd.DataFrame
    status: str


_TARGET_COLUMNS = [
    'target_id',
    'target_kind',
    'quantity_id',
    'region_code',
    'region_name',
    'class_code',
    'class_name',
    'metric',
    'indices',
    'coefficients',
    'constant',
    'connected_component_ids',
    'target_kind_rank',
    'current_width',
]


def _target_benchmark(row, profile: SorsRoundingProfile) -> float | None:
    if profile.benchmark_values is None:
        return None
    target = linear_target_from_row(row)
    if len(target.indices) == 0:
        return float(target.constant)
    return float(
        np.dot(target.coefficients, profile.benchmark_values[target.indices])
        + target.constant
    )


def _benchmark_in_bucket(value: float, bucket: float, policy: RoundingPolicy) -> bool:
    interval = policy.interval(float(bucket))
    if value < interval.lower - policy.tolerance:
        return False
    if value > interval.upper + policy.tolerance:
        return False
    if abs(value - interval.lower) <= policy.tolerance and not interval.lower_attained:
        return False
    if abs(value - interval.upper) <= policy.tolerance and not interval.upper_attained:
        return False
    return True


def build_selection_candidates(
    targets_grid: pd.DataFrame,
    optimal_bounds_grid: pd.DataFrame,
    profile: SorsRoundingProfile,
    config: SorsOptimizationConfig,
    policy: RoundingPolicy,
) -> pd.DataFrame:
    """Build weak-rounding candidates from accumulated target uncertainty.

    The target interval is the result of the *whole* latent model, so it already
    contains rounding uncertainty accumulated through every independent aggregate
    and residual path.  We therefore gate by feasible publication buckets rather
    than multiplying +/-0.5 by a graph-path length.

    A target for which zero is still feasible is deliberately excluded from weak
    selection by default.  Tiny positive cells must not disappear merely because
    one benchmark happens to sit below half a publication step.
    """

    if not config.selection.enabled or optimal_bounds_grid.empty:
        return pd.DataFrame()
    # Min/max output already carries target identity fields such as quantity_id.
    # Merge only metadata absent from that output to avoid Pandas _x/_y suffixes;
    # a suffixed quantity_id would silently break target reconstruction during
    # controlled rounding on real Solver output.
    metadata_columns = [
        column
        for column in _TARGET_COLUMNS
        if column == 'target_id'
        or (
            column in targets_grid.columns
            and column not in optimal_bounds_grid.columns
        )
    ]
    merged = optimal_bounds_grid.merge(
        targets_grid[metadata_columns],
        on='target_id',
        how='left',
        validate='one_to_one',
    )
    rows: list[dict[str, object]] = []
    for row in merged.itertuples(index=False):
        if row.lower_bound is None or row.upper_bound is None:
            continue
        lower, upper = float(row.lower_bound), float(row.upper_bound)
        if not (isfinite(lower) and isfinite(upper)):
            continue
        width = upper - lower
        if width <= policy.tolerance:
            continue
        if (
            config.selection.max_interval_width_mln is not None
            and width > config.selection.max_interval_width_mln
        ):
            continue
        denominator = max(abs(lower), abs(upper), policy.step)
        if (
            config.selection.max_relative_interval_width is not None
            and width / denominator > config.selection.max_relative_interval_width
        ):
            continue
        buckets = policy.candidate_buckets(
            lower,
            upper,
            lower_attained=True,
            upper_attained=True,
            max_buckets=config.selection.max_candidate_buckets,
        )
        if len(buckets) <= 1 or len(buckets) > config.selection.max_candidate_buckets:
            continue
        if not config.selection.allow_zero_selection and 0.0 in buckets:
            # Protection against swallowing economically real tiny positions.
            continue
        benchmark = _target_benchmark(row, profile)
        if benchmark is None:
            continue
        benchmark_bucket = policy.bucket(benchmark)
        if benchmark_bucket not in buckets or not _benchmark_in_bucket(
            benchmark, benchmark_bucket, policy
        ):
            continue
        rows.append(
            {
                **row._asdict(),
                'interval_width': width,
                'relative_interval_width': width / denominator,
                'benchmark_value': benchmark,
                'benchmark_bucket': benchmark_bucket,
                'candidate_buckets': tuple(float(value) for value in buckets),
                'candidate_bucket_count': len(buckets),
                'zero_bucket_feasible': 0.0 in buckets,
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        [
            'candidate_bucket_count',
            'relative_interval_width',
            'target_kind_rank',
            'interval_width',
            'current_width',
            'target_id',
        ],
        ascending=[True, True, True, True, True, True],
        kind='stable',
    ).reset_index(drop=True)


def _add_bucket_constraint(
    session: HighsSession,
    item: dict[str, object],
    bucket: float,
    policy: RoundingPolicy,
) -> None:
    indices = np.asarray(item['indices'], dtype=np.int32)
    coefficients = np.asarray(item['coefficients'], dtype=float)
    constant = float(item['constant'])
    interval = policy.interval(float(bucket))
    lower = solver_lower_bound(
        interval.lower - constant,
        interval.lower_attained,
        open_margin=1e-9,
    )
    upper = solver_upper_bound(
        interval.upper - constant,
        interval.upper_attained,
        open_margin=1e-9,
    )
    session.add_linear_constraint(indices, coefficients, lower=lower, upper=upper)


def _score_bucket(
    item: dict[str, object],
    bucket: float,
    profile: SorsRoundingProfile,
    config: SorsOptimizationConfig,
    policy: RoundingPolicy,
) -> dict[str, object]:
    """Return minimum global L1 distortion compatible with one bucket.

    By default the weak tier may use the full hard official publication intervals.
    An optional ``max_linf_degradation_mln`` can deliberately keep it close to the
    strong minimum-L∞ face.
    """

    try:
        with HighsSession(
            profile.problem,
            time_limit_seconds=config.per_solve_time_limit_seconds,
            threads=config.threads,
            solver=config.rounding_solver,
            run_crossover=config.run_crossover,
        ) as session:
            if config.selection.max_linf_degradation_mln is not None:
                configure_linf_face_session(
                    session,
                    profile,
                    linf_extra=config.selection.max_linf_degradation_mln,
                )
            _add_bucket_constraint(session, item, bucket, policy)
            result = session.solve_objective(profile.l1_objective, include_values=True)
            linf_cost = distortion_linf_from_values(
                profile.problem, result.values
            )
            return {
                'status': result.status,
                'raw_status': result.raw_status,
                'l1_cost_mln': result.objective_value,
                'linf_cost_mln': linf_cost,
                'runtime_seconds': result.runtime_seconds,
                'solver_backend': session.backend,
                'solver_version': session.version,
            }
    except SorsSolverDependencyError as exc:
        return {
            'status': 'SOLVER_UNAVAILABLE',
            'raw_status': str(exc),
            'l1_cost_mln': None,
            'linf_cost_mln': None,
            'runtime_seconds': None,
            'solver_backend': 'highspy',
            'solver_version': 'unavailable',
        }


def score_bucket_competition(
    candidates: pd.DataFrame,
    profile: SorsRoundingProfile,
    config: SorsOptimizationConfig,
    policy: RoundingPolicy,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compare feasible publication buckets by their whole-model rounding cost."""

    if candidates.empty or not config.selection.bucket_competition_enabled:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    preferred: list[dict[str, object]] = []
    attempts: list[dict[str, object]] = []
    solver_rows: list[dict[str, object]] = []
    competition_number = 0
    for item in candidates.to_dict('records'):
        competition_number += 1
        competition_id = f'rounding:competition:{competition_number:06d}'
        scores: list[tuple[float, float, float]] = []
        unavailable = False
        for bucket_index, bucket in enumerate(item['candidate_buckets'], start=1):
            result = _score_bucket(item, float(bucket), profile, config, policy)
            solve_id = f'{competition_id}:bucket:{bucket_index:02d}'
            solver_rows.append(
                {
                    'solve_id': solve_id,
                    'model_layer': 'ROUNDING_BUCKET_COMPETITION',
                    'target_id': item['target_id'],
                    'candidate_bucket': float(bucket),
                    **result,
                }
            )
            if result['status'] == 'SOLVER_UNAVAILABLE':
                unavailable = True
                break
            if result['status'] == 'OPTIMAL' and result['l1_cost_mln'] is not None:
                scores.append((
                    float(result['l1_cost_mln']),
                    float(bucket),
                    float(result['linf_cost_mln']) if result.get('linf_cost_mln') is not None else float('inf'),
                ))
        if unavailable:
            attempts.append(
                {
                    'selection_attempt_id': competition_id,
                    'target_id': item['target_id'],
                    'validation_mode': 'BUCKET_COMPETITION',
                    'status': 'SOLVER_UNAVAILABLE',
                    'accepted': False,
                    'candidate_buckets': item['candidate_buckets'],
                }
            )
            break
        scores.sort(key=lambda pair: (pair[0], pair[1]))
        if not scores:
            attempts.append(
                {
                    'selection_attempt_id': competition_id,
                    'target_id': item['target_id'],
                    'validation_mode': 'BUCKET_COMPETITION',
                    'status': 'NO_FEASIBLE_BUCKET',
                    'accepted': False,
                    'candidate_buckets': item['candidate_buckets'],
                }
            )
            continue
        best_cost, best_bucket, best_linf = scores[0]
        second_cost = scores[1][0] if len(scores) > 1 else float('inf')
        preference_gap = second_cost - best_cost
        global_budget_ok = bool(
            profile.relaxed_l1_star is not None
            and best_cost <= profile.relaxed_l1_star + config.selection.max_l1_degradation_mln + 1e-9
        )
        decisive = bool(
            len(scores) > 1
            and preference_gap + 1e-9 >= config.selection.min_preference_l1_gap_mln
        )
        accepted = bool(global_budget_ok and decisive)
        attempts.append(
            {
                'selection_attempt_id': competition_id,
                'target_id': item['target_id'],
                'validation_mode': 'BUCKET_COMPETITION',
                'status': 'PREFERRED' if accepted else 'AMBIGUOUS',
                'accepted': accepted,
                'candidate_buckets': item['candidate_buckets'],
                'feasible_bucket_count': len(scores),
                'selected_bucket': best_bucket if accepted else None,
                'best_l1_cost_mln': best_cost,
                'best_linf_cost_mln': None if not isfinite(best_linf) else best_linf,
                'relaxed_l1_baseline_mln': profile.relaxed_l1_star,
                'second_best_l1_cost_mln': None if not isfinite(second_cost) else second_cost,
                'preference_l1_gap_mln': None if not isfinite(second_cost) else preference_gap,
                'global_l1_budget_ok': global_budget_ok,
            }
        )
        if accepted:
            preferred.append(
                {
                    **item,
                    'selected_bucket': best_bucket,
                    'bucket_l1_cost_mln': best_cost,
                    'bucket_linf_cost_mln': best_linf,
                    'second_best_l1_cost_mln': second_cost,
                    'preference_l1_gap_mln': preference_gap,
                    'selection_evidence_method': 'ROUNDING_PREFERRED',
                    'competition_attempt_id': competition_id,
                }
            )
    return (
        pd.DataFrame(preferred),
        pd.DataFrame(attempts),
        pd.DataFrame(solver_rows),
    )


def _connected_candidate_clusters(candidates: pd.DataFrame) -> list[pd.DataFrame]:
    if candidates.empty:
        return []
    rows = candidates.reset_index(drop=True)
    parent = list(range(len(rows)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    owner_by_component: dict[str, int] = {}
    for index, value in enumerate(rows['connected_component_ids']):
        components = tuple(str(item) for item in (value or ()))
        for component in components:
            owner = owner_by_component.get(component)
            if owner is None:
                owner_by_component[component] = index
            else:
                union(index, owner)
    groups: dict[int, list[int]] = {}
    for index in range(len(rows)):
        groups.setdefault(find(index), []).append(index)
    return [
        rows.iloc[indices].reset_index(drop=True)
        for indices in sorted(groups.values(), key=lambda values: min(values))
    ]


def _validate_joint_batch(
    candidates: pd.DataFrame,
    profile: SorsRoundingProfile,
    config: SorsOptimizationConfig,
    policy: RoundingPolicy,
) -> tuple[bool, dict[str, object]]:
    try:
        with HighsSession(
            profile.problem,
            time_limit_seconds=config.per_solve_time_limit_seconds,
            threads=config.threads,
            solver=config.rounding_solver,
            run_crossover=config.run_crossover,
        ) as session:
            if profile.relaxed_l1_star is None:
                return False, {
                    'status': 'NO_RELAXED_L1_BASELINE',
                    'raw_status': 'Relaxed L1 rounding baseline is unavailable',
                    'solver_backend': session.backend,
                    'solver_version': session.version,
                }
            if config.selection.max_linf_degradation_mln is not None:
                configure_linf_face_session(
                    session,
                    profile,
                    linf_extra=config.selection.max_linf_degradation_mln,
                )
            session.add_objective_cap(
                profile.l1_objective,
                profile.relaxed_l1_star + config.selection.max_l1_degradation_mln,
            )
            for item in candidates.to_dict('records'):
                _add_bucket_constraint(
                    session,
                    item,
                    float(item['selected_bucket']),
                    policy,
                )
            result = session.solve_feasibility()
            return result.success, {
                'status': result.status,
                'raw_status': result.raw_status,
                'runtime_seconds': result.runtime_seconds,
                'solver_backend': session.backend,
                'solver_version': session.version,
            }
    except SorsSolverDependencyError as exc:
        return False, {
            'status': 'SOLVER_UNAVAILABLE',
            'raw_status': str(exc),
            'solver_backend': 'highspy',
            'solver_version': 'unavailable',
        }


def _validate_candidate_clusters(
    candidates: pd.DataFrame,
    profile: SorsRoundingProfile,
    config: SorsOptimizationConfig,
    policy: RoundingPolicy,
    *,
    preferred_mode: bool,
) -> SorsSelectionExecution:
    if candidates.empty:
        return SorsSelectionExecution(
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 'NO_CANDIDATES'
        )
    accepted_frames: list[pd.DataFrame] = []
    attempt_rows: list[dict[str, object]] = []
    solver_rows: list[dict[str, object]] = []
    unavailable = False
    rejected = 0
    attempt_number = 0
    for cluster_number, cluster in enumerate(
        _connected_candidate_clusters(candidates), start=1
    ):
        if preferred_mode:
            # Preferred buckets need an actual common witness. Unlike benchmark
            # buckets, they do not necessarily share the profile benchmark, so a
            # connected cluster is indivisible. Skip an oversized cluster rather
            # than greedily legitimising a subset in target-order.
            batches = [cluster] if len(cluster) <= config.selection.max_joint_selection_targets else []
            if not batches:
                attempt_number += 1
                attempt_id = f'selection:preferred:{attempt_number:06d}'
                attempt_rows.append(
                    {
                        'selection_attempt_id': attempt_id,
                        'cluster_number': cluster_number,
                        'cluster_candidate_count': len(cluster),
                        'target_ids': tuple(cluster['target_id'].astype(str)),
                        'target_count': len(cluster),
                        'status': 'CLUSTER_TOO_LARGE',
                        'accepted': False,
                        'validation_mode': 'PREFERRED_CONNECTED_CLUSTER',
                    }
                )
                rejected += 1
                continue
        else:
            size = config.selection.max_joint_selection_targets
            batches = [
                cluster.iloc[start:start + size].copy()
                for start in range(0, len(cluster), size)
            ]
        for chunk_number, batch in enumerate(batches, start=1):
            ok, result = _validate_joint_batch(batch, profile, config, policy)
            attempt_number += 1
            prefix = 'preferred' if preferred_mode else 'benchmark'
            attempt_id = f'selection:{prefix}:{attempt_number:06d}'
            status = str(result.get('status', 'REJECTED'))
            if status == 'SOLVER_UNAVAILABLE':
                unavailable = True
            if ok:
                accepted = batch.copy()
                accepted['selection_attempt_id'] = attempt_id
                accepted_frames.append(accepted)
            else:
                rejected += 1
            attempt_rows.append(
                {
                    'selection_attempt_id': attempt_id,
                    'cluster_number': cluster_number,
                    'cluster_candidate_count': len(cluster),
                    'chunk_number': chunk_number,
                    'target_ids': tuple(batch['target_id'].astype(str)),
                    'target_count': len(batch),
                    'status': status,
                    'accepted': bool(ok),
                    'validation_mode': (
                        'PREFERRED_CONNECTED_CLUSTER'
                        if preferred_mode
                        else 'COMMON_BENCHMARK_ATOMIC_BATCH'
                    ),
                }
            )
            solver_rows.append(
                {'solve_id': attempt_id, 'model_layer': 'ROUNDING_SELECTION', **result}
            )
    accepted = (
        pd.concat(accepted_frames, ignore_index=True, sort=False)
        if accepted_frames
        else pd.DataFrame()
    )
    if unavailable:
        status = 'SOLVER_UNAVAILABLE'
    elif accepted_frames and rejected:
        status = 'PARTIAL'
    elif accepted_frames:
        status = 'ACCEPTED'
    else:
        status = 'REJECTED'
    return SorsSelectionExecution(
        accepted,
        pd.DataFrame(attempt_rows),
        pd.DataFrame(solver_rows),
        status,
    )


def run_controlled_selection(
    targets_grid: pd.DataFrame,
    optimal_bounds_grid: pd.DataFrame,
    profile: SorsRoundingProfile,
    config: SorsOptimizationConfig,
    policy: RoundingPolicy,
) -> SorsSelectionExecution:
    """Select publication buckets using strongest available weak evidence.

    Tier 1 compares every feasible bucket by minimum whole-model L1 rounding cost
    inside the hard official publication intervals.  Unlike the strong optimal-face
    tier, it may relax L∞ above ``tau_star`` when policy permits; this is how
    accumulated target uncertainty becomes practically usable without widening any
    source interval. A decisively cheaper bucket is ROUNDING_PREFERRED.
    Tier 2 is the older common-benchmark selection and is reached only when no
    preferred bucket can be jointly validated. Zero is protected in both tiers by
    the candidate builder unless explicitly enabled in policy.
    """

    candidates = build_selection_candidates(
        targets_grid, optimal_bounds_grid, profile, config, policy
    )
    if candidates.empty:
        return SorsSelectionExecution(
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 'NO_CANDIDATES'
        )
    attempt_frames: list[pd.DataFrame] = []
    solver_frames: list[pd.DataFrame] = []

    preferred, competition_attempts, competition_runs = score_bucket_competition(
        candidates, profile, config, policy
    )
    if not competition_attempts.empty:
        attempt_frames.append(competition_attempts)
    if not competition_runs.empty:
        solver_frames.append(competition_runs)
    if not preferred.empty:
        validated = _validate_candidate_clusters(
            preferred,
            profile,
            config,
            policy,
            preferred_mode=True,
        )
        if not validated.attempts_grid.empty:
            attempt_frames.append(validated.attempts_grid)
        if not validated.solver_runs_grid.empty:
            solver_frames.append(validated.solver_runs_grid)
        if not validated.accepted_grid.empty or validated.status == 'SOLVER_UNAVAILABLE':
            return SorsSelectionExecution(
                validated.accepted_grid,
                pd.concat(attempt_frames, ignore_index=True, sort=False),
                pd.concat(solver_frames, ignore_index=True, sort=False),
                validated.status,
            )

    if not config.selection.fallback_benchmark_selection_enabled:
        return SorsSelectionExecution(
            pd.DataFrame(),
            pd.concat(attempt_frames, ignore_index=True, sort=False)
            if attempt_frames else pd.DataFrame(),
            pd.concat(solver_frames, ignore_index=True, sort=False)
            if solver_frames else pd.DataFrame(),
            'NO_PREFERRED_BUCKET',
        )

    fallback = candidates.copy()
    fallback['selected_bucket'] = fallback['benchmark_bucket'].astype(float)
    fallback['selection_evidence_method'] = 'ROUNDING_SELECTED'
    fallback_validated = _validate_candidate_clusters(
        fallback,
        profile,
        config,
        policy,
        preferred_mode=False,
    )
    if not fallback_validated.attempts_grid.empty:
        attempt_frames.append(fallback_validated.attempts_grid)
    if not fallback_validated.solver_runs_grid.empty:
        solver_frames.append(fallback_validated.solver_runs_grid)
    return SorsSelectionExecution(
        fallback_validated.accepted_grid,
        pd.concat(attempt_frames, ignore_index=True, sort=False)
        if attempt_frames else pd.DataFrame(),
        pd.concat(solver_frames, ignore_index=True, sort=False)
        if solver_frames else pd.DataFrame(),
        fallback_validated.status,
    )


# Conceptual validator for already-built benchmark candidates.
def validate_selection_clusters(
    candidates: pd.DataFrame,
    profile: SorsRoundingProfile,
    config: SorsOptimizationConfig,
    policy: RoundingPolicy,
) -> SorsSelectionExecution:
    return _validate_candidate_clusters(
        candidates,
        profile,
        config,
        policy,
        preferred_mode=False,
    )
