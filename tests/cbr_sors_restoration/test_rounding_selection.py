from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsOptimizationConfig,
    SorsSelectionPolicy,
)
from stratbox.macrobanks.cbr_sors_restoration.optimization import selection as selection_module
from stratbox.macrobanks.cbr_sors_restoration.optimization.selection import (
    _connected_candidate_clusters,
    validate_selection_clusters,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy


def _candidate(target_id: str, components: tuple[str, ...]) -> dict[str, object]:
    return {
        'target_id': target_id,
        'connected_component_ids': components,
        'selected_bucket': 1.0,
        'indices': (),
        'coefficients': (),
        'constant': 1.0,
    }




def test_selection_defaults_allow_relaxed_linf_but_protect_zero_bucket() -> None:
    policy = SorsSelectionPolicy()
    assert policy.max_linf_degradation_mln is None
    assert policy.allow_zero_selection is False


def test_selection_clusters_follow_connected_components() -> None:
    candidates = pd.DataFrame([
        _candidate('a', ('cc:1',)),
        _candidate('b', ('cc:1', 'cc:2')),
        _candidate('c', ('cc:2',)),
        _candidate('d', ('cc:9',)),
        _candidate('e', ()),
    ])
    clusters = _connected_candidate_clusters(candidates)
    assert [tuple(frame['target_id']) for frame in clusters] == [
        ('a', 'b', 'c'),
        ('d',),
        ('e',),
    ]


def test_rejected_cluster_does_not_block_independent_cluster(monkeypatch) -> None:
    candidates = pd.DataFrame([
        _candidate('bad-a', ('cc:bad',)),
        _candidate('bad-b', ('cc:bad',)),
        _candidate('good', ('cc:good',)),
    ])
    calls: list[tuple[str, ...]] = []

    def fake_validate(batch, profile, config, policy):
        ids = tuple(batch['target_id'].astype(str))
        calls.append(ids)
        ok = ids == ('good',)
        return ok, {
            'status': 'OPTIMAL' if ok else 'INFEASIBLE',
            'raw_status': 'TEST',
            'runtime_seconds': 0.0,
            'solver_backend': 'test',
            'solver_version': 'test',
        }

    monkeypatch.setattr(selection_module, '_validate_joint_batch', fake_validate)
    config = SorsOptimizationConfig(
        mode='priority',
        max_targets=10,
        selection=SorsSelectionPolicy(max_joint_selection_targets=10),
    )
    execution = validate_selection_clusters(
        candidates,
        profile=object(),
        config=config,
        policy=RoundingPolicy(),
    )

    assert calls == [('bad-a', 'bad-b'), ('good',)]
    assert tuple(execution.accepted_grid['target_id']) == ('good',)
    assert tuple(execution.accepted_grid['selection_attempt_id']) == ('selection:benchmark:000002',)
    assert execution.status == 'PARTIAL'
    assert len(execution.attempts_grid) == 2


def test_large_connected_cluster_is_chunked_without_greedy_premises(monkeypatch) -> None:
    candidates = pd.DataFrame([
        _candidate('a', ('cc:1',)),
        _candidate('b', ('cc:1',)),
        _candidate('c', ('cc:1',)),
    ])
    calls: list[tuple[str, ...]] = []

    def fake_validate(batch, profile, config, policy):
        ids = tuple(batch['target_id'].astype(str))
        calls.append(ids)
        return True, {
            'status': 'OPTIMAL',
            'raw_status': 'TEST',
            'runtime_seconds': 0.0,
            'solver_backend': 'test',
            'solver_version': 'test',
        }

    monkeypatch.setattr(selection_module, '_validate_joint_batch', fake_validate)
    config = SorsOptimizationConfig(
        mode='priority',
        max_targets=10,
        selection=SorsSelectionPolicy(max_joint_selection_targets=2),
    )
    execution = validate_selection_clusters(
        candidates,
        profile=object(),
        config=config,
        policy=RoundingPolicy(),
    )

    assert calls == [('a', 'b'), ('c',)]
    assert tuple(execution.accepted_grid['target_id']) == ('a', 'b', 'c')
    assert tuple(execution.accepted_grid['selection_attempt_id']) == (
        'selection:benchmark:000001',
        'selection:benchmark:000001',
        'selection:benchmark:000002',
    )
    assert execution.status == 'ACCEPTED'
    assert tuple(execution.attempts_grid['validation_mode']) == (
        'COMMON_BENCHMARK_ATOMIC_BATCH',
        'COMMON_BENCHMARK_ATOMIC_BATCH',
    )


def _one_target_bounds(lower: float, upper: float):
    targets = pd.DataFrame(
        [
            {
                'target_id': 't1',
                'target_kind': 'METRIC',
                'quantity_id': 'q1',
                'region_code': 'r1',
                'region_name': 'Регион 1',
                'class_code': '01',
                'class_name': 'Класс 01',
                'metric': 'debt_rub',
                'indices': __import__('numpy').asarray([0], dtype='int32'),
                'coefficients': __import__('numpy').asarray([1.0]),
                'constant': 0.0,
                'connected_component_ids': ('cc:1',),
                'target_kind_rank': 0,
                'current_width': upper - lower,
            }
        ]
    )
    bounds = pd.DataFrame(
        [
            {
                'target_id': 't1',
                'quantity_id': 'q1',
                'lower_bound': lower,
                'upper_bound': upper,
            }
        ]
    )
    return targets, bounds


def test_weak_rounding_never_selects_when_zero_bucket_remains_possible() -> None:
    from types import SimpleNamespace
    import numpy as np
    from stratbox.macrobanks.cbr_sors_restoration.optimization.selection import (
        build_selection_candidates,
    )

    targets, bounds = _one_target_bounds(0.0, 1.2)
    profile = SimpleNamespace(benchmark_values=np.asarray([0.9]))
    config = SorsOptimizationConfig(
        mode='priority',
        max_targets=10,
        selection=SorsSelectionPolicy(
            max_relative_interval_width=None,
            allow_zero_selection=False,
        ),
    )
    candidates = build_selection_candidates(
        targets, bounds, profile, config, RoundingPolicy()
    )
    assert candidates.empty


def test_bucket_competition_prefers_lower_global_rounding_cost(monkeypatch) -> None:
    from types import SimpleNamespace
    import numpy as np
    from stratbox.macrobanks.cbr_sors_restoration.optimization.selection import (
        build_selection_candidates,
        score_bucket_competition,
    )

    targets, bounds = _one_target_bounds(10.0, 12.0)
    profile = SimpleNamespace(
        benchmark_values=np.asarray([11.0]),
        l1_star=97.0,
        relaxed_l1_star=97.0,
    )
    config = SorsOptimizationConfig(
        mode='priority',
        max_targets=10,
        selection=SorsSelectionPolicy(
            max_relative_interval_width=0.25,
            max_l1_degradation_mln=1.0,
            min_preference_l1_gap_mln=0.01,
        ),
    )
    candidates = build_selection_candidates(
        targets, bounds, profile, config, RoundingPolicy()
    )
    assert tuple(candidates.iloc[0].candidate_buckets) == (10.0, 11.0, 12.0)

    def fake_score(item, bucket, profile, config, policy):
        costs = {10.0: 97.4, 11.0: 97.0, 12.0: 97.7}
        return {
            'status': 'OPTIMAL',
            'raw_status': 'TEST',
            'l1_cost_mln': costs[bucket],
            'linf_cost_mln': {10.0: 0.40, 11.0: 0.35, 12.0: 0.45}[bucket],
            'runtime_seconds': 0.0,
            'solver_backend': 'test',
            'solver_version': 'test',
        }

    monkeypatch.setattr(selection_module, '_score_bucket', fake_score)
    preferred, attempts, runs = score_bucket_competition(
        candidates, profile, config, RoundingPolicy()
    )
    assert tuple(preferred['selected_bucket']) == (11.0,)
    assert tuple(preferred['selection_evidence_method']) == ('ROUNDING_PREFERRED',)
    assert abs(float(attempts.iloc[0].preference_l1_gap_mln) - 0.4) < 1e-9
    assert len(runs) == 3
