"""Durable idempotency survives concurrent claims and terminal-body archiving."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from threading import Barrier
import sqlite3

import pytest

from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.execution.service import EffectReceipt


def claim(identity='effect', **kwargs):
    return EffectReceipt(identity, 'store', 'unknown', resource='destination', intent={'source': ('exact', 1)}, **kwargs)


def confirmed(identity='effect', value=None):
    return replace(claim(identity), status='confirmed', value={'ack': 'received'} if value is None else value)


def test_atomic_begin_across_instances_grants_exactly_one_action_authority(tmp_path):
    first, second = FileEffectState(tmp_path), FileEffectState(tmp_path)
    assert first.scope_id == second.scope_id
    barrier = Barrier(2)
    def begin(state):
        barrier.wait(timeout=2)
        return state.begin(claim())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(begin, (first, second)))
    assert sum(owned for _, owned in results) == 1
    assert all(receipt.status == 'unknown' for receipt, _ in results)
    assert FileEffectState(tmp_path).get('effect').intent == {'source': ('exact', 1)}


def test_unknown_effect_cannot_be_archived_or_forgotten_after_restart(tmp_path):
    state = FileEffectState(tmp_path)
    state.begin(claim())
    with pytest.raises(ValueError, match='unknown_retention_required'):
        state.archive(['effect'])
    restarted = FileEffectState(tmp_path)
    receipt, owned = restarted.begin(claim())
    assert not owned and receipt.status == 'unknown'
    assert restarted.page(status='unknown')[0]['effect_id'] == 'effect'
    assert not restarted.page(archived=True)


def test_terminal_archive_moves_body_and_retains_complete_exact_receipt(tmp_path):
    state = FileEffectState(tmp_path)
    state.begin(claim())
    state.put(confirmed(value={'ack': 'received', 'evidence': b'actual receipt'}))
    before = state.get('effect')
    assert state.archive(['effect']) == ('effect',)
    with sqlite3.connect(tmp_path / 'effects.sqlite') as db:
        body, locator = db.execute('SELECT body,archive_locator FROM receipts').fetchone()
    assert body is None and locator
    assert (tmp_path / 'archive' / locator).is_file()
    restarted = FileEffectState(tmp_path)
    assert restarted.get('effect') == before
    assert restarted.begin(claim()) == (before, False)
    assert restarted.archive(['effect']) == ('effect',)
    assert restarted.page(archived=True)[0]['body_identity'] == sha256((tmp_path / 'archive' / locator).read_bytes()).hexdigest()


def test_archived_rejected_effect_can_be_atomically_retried_with_new_evidence(tmp_path):
    state = FileEffectState(tmp_path)
    state.begin(claim())
    state.put(replace(claim(), status='rejected', finding='storage.create_rejected'))
    state.archive(['effect'])
    old_files = set((tmp_path / 'archive').rglob('*'))
    retry = replace(claim(), intent={'source': ('exact', 2)})
    assert state.begin(retry) == (retry, True)
    state.put(replace(retry, status='confirmed', value={'ack': 'second attempt'}))
    state.archive(['effect'])
    assert set((tmp_path / 'archive').rglob('*')) > old_files
    assert FileEffectState(tmp_path).get('effect').value == {'ack': 'second attempt'}


@pytest.mark.parametrize('damage', ['missing', 'corrupt'])
def test_missing_or_corrupt_cold_evidence_never_makes_an_effect_unseen(tmp_path, damage):
    state = FileEffectState(tmp_path)
    state.put(confirmed())
    state.archive(['effect'])
    path = next(path for path in (tmp_path / 'archive').rglob('*') if path.is_file() and len(path.name) == 64)
    if damage == 'missing': path.unlink()
    else: path.write_bytes(b'forged receipt')
    restarted = FileEffectState(tmp_path)
    with pytest.raises((FileNotFoundError, ValueError)):
        restarted.get('effect')
    with pytest.raises((FileNotFoundError, ValueError)):
        restarted.begin(claim())
    assert restarted.page()[0]['effect_id'] == 'effect'


def test_confirmation_is_monotonic_and_identity_conflicts_are_rejected(tmp_path):
    state = FileEffectState(tmp_path)
    state.put(confirmed())
    state.archive(['effect'])
    state.put(confirmed())
    with pytest.raises(ValueError, match='confirmed_conflict'):
        state.put(claim())
    with pytest.raises(ValueError, match='confirmed_conflict'):
        state.put(confirmed(value={'different': True}))
    with pytest.raises(ValueError, match='identity_conflict'):
        state.begin(replace(claim(), resource='other destination'))
    assert state.get('effect') == confirmed()


def test_intent_enrichment_is_durable_and_rejected_retry_requires_atomic_claim(tmp_path):
    state = FileEffectState(tmp_path)
    state.begin(claim())
    enriched = replace(claim(), intent={'source': ('exact', 1), 'observed_bytes': b'bytes'})
    state.put(enriched)
    assert FileEffectState(tmp_path).get('effect') == enriched
    state.put(replace(enriched, status='rejected'))
    with pytest.raises(ValueError, match='atomic_begin_required'):
        state.put(claim())
    assert state.begin(claim())[1]


def test_archive_validates_all_selected_states_before_moving_terminal_bodies(tmp_path):
    state = FileEffectState(tmp_path)
    state.put(confirmed('a')); state.begin(claim('b'))
    with pytest.raises(ValueError, match='unknown_retention_required'):
        state.archive(['a', 'b'])
    assert not state.page(archived=True)
    assert len(state.page(archived=False)) == 2


def test_cold_write_failure_keeps_complete_hot_body_and_all_identity_rows(tmp_path, monkeypatch):
    state = FileEffectState(tmp_path)
    state.put(confirmed())
    monkeypatch.setattr(state.store, 'create_immutable', lambda *args: (_ for _ in ()).throw(OSError('cold storage unavailable')))
    with pytest.raises(OSError, match='cold storage unavailable'):
        state.archive(['effect'])
    assert FileEffectState(tmp_path).get('effect') == confirmed()
    assert state.page(archived=False)[0]['effect_id'] == 'effect'


def test_compaction_releases_hot_storage_without_deleting_idempotency_rows(tmp_path):
    state = FileEffectState(tmp_path)
    for index in range(4):
        state.put(confirmed(str(index), value=b'x' * 100000))
    state.begin(claim('uncertain'))
    state.archive(['0', '1', '2', '3'])
    with sqlite3.connect(tmp_path / 'effects.sqlite') as db:
        assert db.execute('PRAGMA auto_vacuum').fetchone()[0] == 2
        initial_pages = db.execute('PRAGMA page_count').fetchone()[0]
    for _ in range(10): state.compact(pages=100)
    assert state.compact()['page_count'] < initial_pages
    restarted = FileEffectState(tmp_path)
    assert len(restarted.page()) == 5
    assert restarted.get('3').value == b'x' * 100000
    assert restarted.get('uncertain').status == 'unknown'


@pytest.mark.parametrize('kwargs', [{'max_receipt_bytes': True}, {'max_receipt_bytes': 0}])
def test_receipt_capacity_requires_positive_integer(tmp_path, kwargs):
    with pytest.raises(ValueError, match='receipt_limit_invalid'):
        FileEffectState(tmp_path, **kwargs)


def test_receipt_limit_and_page_limits_fail_before_persistence(tmp_path):
    state = FileEffectState(tmp_path, max_receipt_bytes=500)
    with pytest.raises(ValueError, match='receipt_size_limit'):
        state.put(confirmed(value=b'x' * 1000))
    assert not state.page()
    with pytest.raises(ValueError): state.page(limit=True)
    with pytest.raises(ValueError): state.page(limit=10001)
    with pytest.raises(ValueError): state.archive('effect')
    with pytest.raises(ValueError): state.begin(confirmed())


def test_hot_count_quota_pins_unknown_and_terminal_archive_releases_capacity(tmp_path):
    first = FileEffectState(tmp_path, max_hot_receipts=2)
    second = FileEffectState(tmp_path, max_hot_receipts=2)
    first.begin(claim('unknown'))
    first.begin(claim('terminal'))
    with pytest.raises(RuntimeError, match='hot_capacity_exhausted'):
        second.begin(claim('blocked'))
    assert second.get('blocked') is None
    first.put(confirmed('terminal'))
    first.archive(['terminal'])
    assert second.begin(claim('new'))[1]
    assert first.get('unknown').status == 'unknown'
    assert first.usage()['hot_receipts'] == 2
    assert len(first.page()) == 3


def test_hot_byte_quota_checks_intent_enrichment_and_survives_restart(tmp_path):
    state = FileEffectState(tmp_path, max_hot_bytes=1000)
    state.begin(claim())
    original = state.get('effect')
    with pytest.raises(RuntimeError, match='hot_capacity_exhausted'):
        state.put(replace(original, intent={'large': b'x' * 2000}))
    restarted = FileEffectState(tmp_path, max_hot_bytes=1000)
    assert restarted.get('effect') == original
    assert restarted.usage()['hot_receipts'] == 1
    assert restarted.usage()['hot_bytes'] < 1000


_ACTION = {}


def atomic_external_action(inputs, settings, context):
    def mutate():
        with _ACTION['lock']:
            _ACTION['calls'] += 1
        _ACTION['entered'].set()
        assert _ACTION['release'].wait(3)
        return {'ack': 'actual external mutation'}
    receipt = context.effect('store', 'one-shared-effect', mutate, resource='shared-destination')
    return {'status': receipt.status}


def test_two_execution_services_claim_one_external_action_and_reuse_archived_ack(tmp_path):
    from threading import Event, Lock
    from time import monotonic, sleep
    from stratbox.capabilities.model import MethodRef, PortContract
    from stratbox.capabilities.plan.models import BoundCommand, CommandTask, PreparedPlan, ValueRef
    from stratbox.core.execution.service import ExecutionService

    barrier = Barrier(2)
    class RacingState(FileEffectState):
        def __init__(self, directory):
            super().__init__(directory)
            self.first = True
        def get(self, effect_id):
            receipt = super().get(effect_id)
            if self.first:
                self.first = False
                barrier.wait(timeout=3)
            return receipt
    _ACTION.update(lock=Lock(), entered=Event(), release=Event(), calls=0)
    command = BoundCommand('command.test.atomic_effect', MethodRef(__name__ + ':atomic_external_action'), {},
        {}, {'status': PortContract('status', str)}, effects=frozenset({'store'}))
    plan = PreparedPlan('atomic.claim.regression', (CommandTask('mutate', command, {}),), (),
        {'status': ValueRef('mutate', 'status')}, 'atomic.claim.regression', 'test-build')
    states = RacingState(tmp_path), RacingState(tmp_path)
    with ExecutionService(providers={'effect_state': states[0]}) as first, ExecutionService(providers={'effect_state': states[1]}) as second:
        handles = first.submit(plan), second.submit(plan)
        try:
            assert _ACTION['entered'].wait(3)
            deadline = monotonic() + 3
            while not any(handle.done() for handle in handles) and monotonic() < deadline:
                sleep(.002)
            assert any(handle.done() for handle in handles)
            assert _ACTION['calls'] == 1
        finally:
            _ACTION['release'].set()
        results = tuple(handle.result(3) for handle in handles)
        assert sorted(result.outcome for result in results) == ['succeeded', 'unknown']
        for result in results: result.close()
    state = FileEffectState(tmp_path)
    state.archive(['one-shared-effect'])
    with ExecutionService(providers={'effect_state': FileEffectState(tmp_path)}) as restarted:
        result = restarted.run(plan, timeout=3)
        assert result.outcome == 'succeeded' and result.output('status') == 'confirmed'
        assert _ACTION['calls'] == 1
        result.close()


def test_effect_lookup_cache_is_bounded_while_archived_receipts_remain_authoritative(tmp_path):
    from stratbox.core.execution.service import ExecutionService, ExecutionSettings
    state = FileEffectState(tmp_path)
    for index in range(20): state.put(confirmed(f'confirmed-{index:02d}'))
    state.archive([f'confirmed-{index:02d}' for index in range(20)])
    with ExecutionService(providers={'effect_state': state}, settings=ExecutionSettings(effect_capacity=3)) as service:
        for index in range(20):
            assert service.lookup_effect(f'confirmed-{index:02d}') == confirmed(f'confirmed-{index:02d}')
            assert len(service._effects) <= 3
        assert tuple(service._effects) == ('confirmed-17', 'confirmed-18', 'confirmed-19')
        assert service.lookup_effect('confirmed-00') == confirmed('confirmed-00')
        assert len(service._effects) == 3 and 'confirmed-17' not in service._effects
    assert state.get('confirmed-00') == confirmed('confirmed-00')


def test_unknown_receipts_pin_cache_and_terminal_lookup_can_return_uncached(tmp_path):
    from stratbox.core.execution.service import ExecutionService, ExecutionSettings
    state = FileEffectState(tmp_path)
    for index in range(3): state.begin(claim(f'unknown-{index}'))
    state.put(confirmed()); state.archive(['effect'])
    with ExecutionService(providers={'effect_state': state}, settings=ExecutionSettings(effect_capacity=3)) as service:
        for index in range(3): assert service.lookup_effect(f'unknown-{index}').status == 'unknown'
        for _ in range(3):
            assert service.lookup_effect('effect') == confirmed()
            assert len(service._effects) == 3 and 'effect' not in service._effects
            assert all(receipt.status == 'unknown' for receipt in service._effects.values())
