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
    assert execution.status == 'ACCEPTED'
    assert tuple(execution.attempts_grid['validation_mode']) == (
        'COMMON_WITNESS_ATOMIC_BATCH',
        'COMMON_WITNESS_ATOMIC_BATCH',
    )
