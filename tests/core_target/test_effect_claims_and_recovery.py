"""Durable revisions fence stale writers; restored history fences unseen work."""
from dataclasses import dataclass, replace
import sqlite3

import pytest

from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.execution.service import EffectReceipt, ExecutionService


def proposed(effect_id='one'):
    return EffectReceipt(effect_id, 'test.write', 'unknown', resource='destination', intent={'bytes': 'exact'})


def test_stale_revision_and_forged_claim_cannot_overwrite_new_observations(tmp_path):
    first, second = FileEffectState(tmp_path), FileEffectState(tmp_path)
    claimed, owned = first.begin(proposed())
    assert owned and claimed.revision == 1 and claimed.claim_id
    before = first.recovery_metadata()
    updated = first.put(replace(claimed, intent={**claimed.intent, 'observed': 'revision-a'}))
    assert updated.revision == 2 and updated.claim_id == claimed.claim_id
    after = second.recovery_metadata()
    assert before['unknown_count'] == after['unknown_count'] == 1
    assert after['revision_sum'] == before['revision_sum'] + 1
    with pytest.raises(ValueError, match='stale_revision_or_claim'):
        second.put(replace(claimed, status='confirmed', value={'status': 'confirmed'}))
    with pytest.raises(ValueError, match='stale_revision_or_claim'):
        second.put(replace(updated, claim_id='another-owner', status='confirmed'))
    with pytest.raises(ValueError, match='intent_conflict'):
        second.put(replace(updated, intent={'bytes': 'changed'}))
    final = second.put(replace(updated, status='confirmed', value={'status': 'confirmed'}))
    assert final.revision == 3 and first.get('one') == final


def test_rejected_retry_has_a_new_claim_but_cannot_rebind_its_intent(tmp_path):
    state = FileEffectState(tmp_path)
    claim, _ = state.begin(proposed())
    rejected = state.put(replace(claim, status='rejected'))
    with pytest.raises(ValueError, match='intent_conflict'):
        state.begin(replace(proposed(), intent={'bytes': 'different'}))
    fresh, owned = state.begin(proposed())
    assert owned and fresh.claim_id != rejected.claim_id and fresh.revision == rejected.revision + 1
    with pytest.raises(ValueError, match='stale_revision_or_claim'):
        state.put(replace(rejected, status='unknown'))


def test_unknown_claim_reserves_settlement_growth_before_external_action(tmp_path):
    first = FileEffectState(tmp_path, max_receipt_bytes=1200, max_hot_bytes=1500)
    second = FileEffectState(tmp_path, max_receipt_bytes=1200, max_hot_bytes=1500)
    current, _ = first.begin(proposed())
    assert first.usage()['effective_hot_bytes'] == 1200
    with pytest.raises(RuntimeError, match='hot_capacity_exhausted'):
        second.begin(proposed('another'))
    assert second.get('another') is None
    # A qualified bounded acknowledgement can grow within its reserved room.
    settled = second.put(replace(current, status='confirmed', value={'proof': 'x' * 700}))
    assert settled.status == 'confirmed' and first.usage()['reserved_bytes'] == 0
    first.archive(['one'])
    assert second.begin(proposed('another'))[1]


def test_nonterminal_cache_observes_shared_confirmation_without_redundant_lookup(tmp_path):
    state, other = FileEffectState(tmp_path), FileEffectState(tmp_path)
    current, _ = state.begin(proposed())
    with ExecutionService(providers={'effect_state': state}) as service:
        assert service.lookup_effect('one').status == 'unknown'
        final = other.put(replace(current, status='confirmed', value={'status': 'confirmed'}))
        assert service.lookup_effect('one') == final


def test_disappeared_durable_unknown_authority_fails_closed(tmp_path):
    state = FileEffectState(tmp_path)
    state.begin(proposed())
    with ExecutionService(providers={'effect_state': state}) as service:
        assert service.lookup_effect('one').status == 'unknown'
        with sqlite3.connect(tmp_path / 'effects.sqlite') as db:
            db.execute('DELETE FROM receipts')
        with pytest.raises(Exception, match='effect.authority_disappeared'):
            service.lookup_effect('one')


@pytest.mark.parametrize('replacement', ('different_scope', 'removed'))
def test_confirmed_cache_cannot_outlive_its_bound_durable_authority(tmp_path, replacement):
    state = FileEffectState(tmp_path / 'original')
    current, _ = state.begin(proposed())
    settled = state.put(replace(current, status='confirmed', value={'status': 'confirmed'}))
    with ExecutionService(providers={'effect_state': state}) as service:
        assert service.lookup_effect('one') == settled
        if replacement == 'removed':
            del service.providers['effect_state']
        else:
            service.providers['effect_state'] = FileEffectState(tmp_path / 'another')
        with pytest.raises(Exception, match='effect.authority_changed'):
            service.lookup_effect('one')


def test_same_scope_replacement_rechecks_even_a_confirmed_cache_hit(tmp_path, monkeypatch):
    state = FileEffectState(tmp_path)
    current, _ = state.begin(proposed())
    settled = state.put(replace(current, status='confirmed', value={'status': 'confirmed'}))
    with ExecutionService(providers={'effect_state': state}) as service:
        assert service.lookup_effect('one') == settled
        other, lookups = FileEffectState(tmp_path), []
        get = other.get
        def observed(identity):
            lookups.append(identity)
            return get(identity)
        monkeypatch.setattr(other, 'get', observed)
        service.providers['effect_state'] = other
        assert service.lookup_effect('one') == settled
        assert lookups == ['one']


@pytest.mark.parametrize('limits', ({'max_bytes': 1}, {'max_files': 2}, {'max_file_bytes': 1}))
def test_effect_checkpoint_budget_does_not_publish_partial_authority(tmp_path, limits):
    state = FileEffectState(tmp_path / 'live')
    claimed, _ = state.begin(proposed())
    state.put(replace(claimed, status='confirmed', value={'receipt': b'proof'}))
    state.archive(['one'])
    with pytest.raises(ValueError, match='checkpoint_capacity_exhausted'):
        state.export_checkpoint(tmp_path / 'rejected', **limits)
    assert not (tmp_path / 'rejected').exists()
    assert not tuple(tmp_path.glob('stratbox-effects-checkpoint-*'))
    state.export_checkpoint(tmp_path / 'accepted', max_files=4, max_bytes=1024**2, max_file_bytes=1024**2)
    assert FileEffectState.checkpoint_view(tmp_path / 'accepted').get('one') == state.get('one')


def test_checkpoint_restores_cold_and_unknown_evidence_but_fences_new_claims(tmp_path):
    state = FileEffectState(tmp_path / 'live', archive_directory=tmp_path / 'external-cold')
    unknown, _ = state.begin(proposed('unknown'))
    terminal, _ = state.begin(proposed('confirmed'))
    terminal = state.put(replace(terminal, status='confirmed', value={'receipt': b'exact evidence'}))
    rejected, _ = state.begin(proposed('rejected'))
    rejected = state.put(replace(rejected, status='rejected'))
    state.archive(['confirmed', 'rejected'])
    exported = state.export_checkpoint(tmp_path / 'checkpoint')
    # This external occurrence happened after the cut and is absent on restore.
    after, _ = state.begin(proposed('after-checkpoint'))
    state.put(replace(after, status='confirmed', value={'sent': True}))
    restored = FileEffectState.restore_checkpoint(tmp_path / 'checkpoint', tmp_path / 'restored',
        recovery_manifest_id='manifest-one')
    assert exported['cold_count'] == 2
    assert restored.scope_id == state.scope_id
    assert restored.get('confirmed') == terminal and restored.get('unknown') == unknown
    assert restored.recovery_metadata()['namespace_state'] == 'closed'
    assert restored.recovery_metadata()['recovery_manifest_id'] == 'manifest-one'
    assert restored.get('after-checkpoint') is None
    for effect_id in ('after-checkpoint', 'entirely-new', 'rejected'):
        with pytest.raises(ValueError, match='recovery_namespace_closed'):
            restored.begin(proposed(effect_id))
    assert restored.begin(proposed('unknown')) == (unknown, False)
    settled = restored.put(replace(unknown, status='confirmed', value={'authoritative_lookup': True}))
    assert settled.status == 'confirmed'
    assert FileEffectState(tmp_path / 'restored').recovery_metadata()['namespace_state'] == 'closed'


@pytest.mark.parametrize('damage', ('database', 'cold-index', 'cold-body'))
def test_checkpoint_dependency_damage_is_rejected_before_opening_action_authority(tmp_path, damage):
    state = FileEffectState(tmp_path / 'live')
    current, _ = state.begin(proposed())
    state.put(replace(current, status='confirmed', value={'receipt': b'original'}))
    state.archive(['one'])
    state.export_checkpoint(tmp_path / 'checkpoint')
    if damage == 'database':
        target = tmp_path / 'checkpoint' / 'effects.sqlite'
    elif damage == 'cold-index':
        target = tmp_path / 'checkpoint' / 'cold-index.jsonl'
    else:
        target = next(path for path in (tmp_path / 'checkpoint' / 'archive').rglob('*') if path.is_file())
    target.write_bytes(b'corrupted')
    with pytest.raises(ValueError, match='checkpoint_'):
        FileEffectState.restore_checkpoint(tmp_path / 'checkpoint', tmp_path / 'restored')
    assert not (tmp_path / 'restored').exists()


@dataclass(frozen=True)
class CustomAcknowledgement:
    token: str


def test_checkpoint_rejects_missing_admitted_codec_before_publishing_destination(tmp_path):
    types = {__name__ + ':CustomAcknowledgement': CustomAcknowledgement}
    state = FileEffectState(tmp_path / 'live', admitted_types=types)
    current, _ = state.begin(proposed())
    state.put(replace(current, status='confirmed', value=CustomAcknowledgement('exact')))
    state.archive(['one'])
    state.export_checkpoint(tmp_path / 'checkpoint')
    with pytest.raises(ValueError, match='type_not_admitted'):
        FileEffectState.restore_checkpoint(tmp_path / 'checkpoint', tmp_path / 'restored')
    assert not (tmp_path / 'restored').exists()
    restored = FileEffectState.restore_checkpoint(tmp_path / 'checkpoint', tmp_path / 'restored', admitted_types=types)
    assert restored.get('one').value == CustomAcknowledgement('exact')
