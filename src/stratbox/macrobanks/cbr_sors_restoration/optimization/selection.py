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
    configure_optimal_face_session,
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


def build_selection_candidates(
    targets_grid: pd.DataFrame,
    optimal_bounds_grid: pd.DataFrame,
    profile: SorsRoundingProfile,
    config: SorsOptimizationConfig,
    policy: RoundingPolicy,
) -> pd.DataFrame:
    """Build narrow publication-bucket candidates from one common L1 optimum.

    Every selected bucket is derived from the *same* feasible benchmark vector.
    Therefore the candidate set has a common witness by construction.  The final
    validation below still re-solves the augmented model with all chosen buckets
    imposed simultaneously so numerical/open-bound issues cannot silently pass.
    """

    if not config.selection.enabled or optimal_bounds_grid.empty:
        return pd.DataFrame()
    merged = optimal_bounds_grid.merge(
        targets_grid[
            [
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
        ],
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
        if width <= 0 or width > config.selection.max_selection_width_mln:
            continue
        benchmark = _target_benchmark(row, profile)
        if benchmark is None:
            continue
        bucket = policy.bucket(benchmark)
        if config.selection.max_selection_width_ratio is not None:
            denominator = max(abs(bucket), policy.step)
            if width / denominator > config.selection.max_selection_width_ratio:
                continue
        interval = policy.interval(float(bucket))
        # The common benchmark must itself witness the proposed publication bucket.
        if benchmark < interval.lower or benchmark > interval.upper:
            continue
        if benchmark == interval.lower and not interval.lower_attained:
            continue
        if benchmark == interval.upper and not interval.upper_attained:
            continue
        rows.append(
            {
                **row._asdict(),
                'interval_width': width,
                'benchmark_value': benchmark,
                'selected_bucket': bucket,
            }
        )
    if not rows:
        return pd.DataFrame()
    candidates = pd.DataFrame(rows)
    # Keep the full eligible set here.  Atomic batches are formed later per
    # connected Solver component so one unrelated rejected cluster cannot block
    # valid selections elsewhere in the cube.
    return candidates.sort_values(
        ['target_kind_rank', 'interval_width', 'current_width', 'target_id'],
        ascending=[True, True, True, True],
        kind='stable',
    ).reset_index(drop=True)


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
            configure_optimal_face_session(
                session,
                profile,
                linf_extra=config.selection.max_linf_degradation_mln,
                l1_extra=config.selection.max_l1_degradation_mln,
            )
            for item in candidates.to_dict('records'):
                indices = np.asarray(item['indices'], dtype=np.int32)
                coefficients = np.asarray(item['coefficients'], dtype=float)
                constant = float(item['constant'])
                interval = policy.interval(float(item['selected_bucket']))
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
                session.add_linear_constraint(
                    indices,
                    coefficients,
                    lower=lower,
                    upper=upper,
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
        return False, {'status': 'SOLVER_UNAVAILABLE', 'raw_status': str(exc)}


def _connected_candidate_clusters(candidates: pd.DataFrame) -> list[pd.DataFrame]:
    """Group selection candidates by overlapping latent connected components.

    Targets that do not share any Solver-connected component are mathematically
    independent in the compiled latent model.  They must therefore be validated
    independently: a problematic candidate in one component must never suppress a
    sound batch in another.  Within one connected cluster we keep atomic semantics
    and never greedily accept a subset after a failed joint validation.
    """

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
        if not components:
            # A constant/disconnected target has no coupling to another target and
            # therefore forms its own atomic cluster.
            continue
        for component in components:
            owner = owner_by_component.get(component)
            if owner is None:
                owner_by_component[component] = index
            else:
                union(index, owner)

    groups: dict[int, list[int]] = {}
    for index in range(len(rows)):
        groups.setdefault(find(index), []).append(index)
    ordered = sorted(groups.values(), key=lambda indices: min(indices))
    return [rows.iloc[indices].reset_index(drop=True) for indices in ordered]


def validate_selection_clusters(
    candidates: pd.DataFrame,
    profile: SorsRoundingProfile,
    config: SorsOptimizationConfig,
    policy: RoundingPolicy,
) -> SorsSelectionExecution:
    """Validate benchmark buckets in bounded atomic batches.

    All candidates come from one common L1-optimal benchmark vector and
    ``build_selection_candidates`` verifies that this very vector lies inside
    every proposed publication bucket.  Consequently *all* candidate buckets
    have a common global witness by construction and are mutually compatible on
    the configured rounding-optimal face.

    We still re-solve bounded batches to protect against endpoint/numerical issues
    and to keep HiGHS model mutations small.  Batches are independent checks
    against the same original optimal-face problem; acceptance of one batch is
    never used as a premise for validating another.  Splitting a large connected
    cluster is therefore a performance operation, not greedy mathematical
    selection.
    """

    if candidates.empty:
        return SorsSelectionExecution(
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 'NO_CANDIDATES'
        )

    accepted_frames: list[pd.DataFrame] = []
    attempt_rows: list[dict[str, object]] = []
    solver_rows: list[dict[str, object]] = []
    unavailable = False
    rejected = 0
    clusters = _connected_candidate_clusters(candidates)
    attempt_number = 0

    for cluster_number, cluster in enumerate(clusters, start=1):
        chunk_size = config.selection.max_joint_selection_targets
        for chunk_number, start in enumerate(range(0, len(cluster), chunk_size), start=1):
            batch = cluster.iloc[start:start + chunk_size].copy()
            ok, result = _validate_joint_batch(batch, profile, config, policy)
            attempt_number += 1
            attempt_id = f'selection:batch:{attempt_number:06d}'
            status = str(result.get('status', 'REJECTED'))
            if status == 'SOLVER_UNAVAILABLE':
                unavailable = True
            if ok:
                accepted_frames.append(batch)
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
                    'validation_mode': 'COMMON_WITNESS_ATOMIC_BATCH',
                }
            )
            solver_rows.append(
                {
                    'solve_id': attempt_id,
                    'model_layer': 'ROUNDING_SELECTION',
                    **result,
                }
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
        accepted_grid=accepted,
        attempts_grid=pd.DataFrame(attempt_rows),
        solver_runs_grid=pd.DataFrame(solver_rows),
        status=status,
    )
