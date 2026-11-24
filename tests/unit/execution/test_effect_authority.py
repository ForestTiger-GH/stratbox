from dataclasses import replace
from threading import Event, Thread

import pytest

from stratbox.core.execution import Correlation, ExecutionContext, OperationDefinition, run
from stratbox.core.execution.contracts import EffectReceipt
from stratbox.core.execution.effects import EffectAuthority, EffectAuthorityError, EffectIntent
from stratbox.shared.identity import ByteIdentity


def intent(run_id='run', effect_id='save', **options):
    return EffectIntent(run_id, 'scope', 'work', 'storage.write', effect_id,
                        'destination/product.csv', input_basis='basis', **options)


def admitted(authority, run_id='run', attempt='attempt'):
    authority.begin_attempt(run_id, 'scope', 'work', attempt)


def confirmed(effect_id='save', identity=None):
    return EffectReceipt('storage.write', 'confirmed', effect_id=effect_id, identity=identity)


def test_lost_commit_reply_is_addressable_and_requires_reconciliation_before_retry():
    authority = EffectAuthority()
    admitted(authority)
    writes = []
    def lost_reply():
        writes.append(b'accepted')
        raise ConnectionError('reply lost after store commit')
    receipt = authority.commit(intent(), 'attempt', lost_reply)
    assert receipt.state == 'unknown'
    saved = authority.lookup('run', 'scope', 'save')
    assert saved.receipt == receipt
    with pytest.raises(EffectAuthorityError, match='reconciliation_required'):
        authority.commit(intent(), 'attempt', lost_reply)
    assert writes == [b'accepted']
    authority.reconcile('run', 'scope', 'save', confirmed(), expected_revision=saved.revision)
    assert authority.commit(intent(), 'attempt', lost_reply) == confirmed()
    assert writes == [b'accepted']


def test_superseded_attempt_cannot_start_a_write_or_change_pinned_inputs():
    authority = EffectAuthority()
    admitted(authority, attempt='old')
    admitted(authority, attempt='new')
    writes = []
    with pytest.raises(EffectAuthorityError, match='stale_attempt'):
        authority.commit(intent(), 'old', lambda: writes.append(1))
    assert writes == []
    authority.commit(intent(), 'new', confirmed)
    with pytest.raises(EffectAuthorityError, match='identity_conflict'):
        authority.commit(replace(intent(), source_revision='another'), 'new', confirmed)


def test_cancel_after_physical_start_retains_fact_but_revokes_current_promotion():
    authority = EffectAuthority()
    admitted(authority)
    started, finish = Event(), Event()
    def commit():
        started.set()
        assert finish.wait(2)
        return confirmed()
    worker = Thread(target=lambda: authority.commit(intent(), 'attempt', commit))
    worker.start()
    assert started.wait(1)
    authority.invalidate_attempt('run', 'scope', 'work', 'attempt')
    finish.set()
    worker.join(2)
    assert not worker.is_alive()
    record = authority.lookup('run', 'scope', 'save')
    assert record.receipt.state == 'confirmed'
    assert record.current is False


def test_newer_run_resource_commit_fences_late_older_run():
    authority = EffectAuthority()
    admitted(authority, 'old')
    admitted(authority, 'new')
    authority.commit(intent('new'), 'attempt', confirmed)
    with pytest.raises(EffectAuthorityError, match='stale_attempt'):
        authority.commit(intent('old', effect_id='old-save'), 'attempt', lambda: confirmed('old-save'))


def test_invocation_exposes_unknown_save_without_losing_computation_or_blind_retry():
    authority = EffectAuthority()
    admitted(authority)
    correlation = Correlation(run_id='run', workflow_scope_id='scope', task_id='work', attempt_id='attempt')
    context = ExecutionContext(correlation=correlation, effect_authority=authority)
    definition = OperationDefinition('test.save', 'save', bytes, bytes,
                                    possible_effects=frozenset({'storage.write'}))
    def handler(value, invocation):
        invocation.commit_effect('storage.write', 'save', lambda: (_ for _ in ()).throw(OSError()),
                                 resource='destination/product.csv', identity=ByteIdentity.of(value),
                                 input_basis='basis')
        return value
    result = run(definition, b'calculated', handler, context=context)
    assert result.outcome == 'unknown'
    assert result.effects[0].effect_id == 'save'
    assert result.effects[0].state == 'unknown'
    assert result.diagnostics[0].evidence_ref == 'save'
    assert authority.snapshot()[0].intent.input_basis == 'basis'


def test_unknown_effect_in_another_run_still_requires_reconciliation():
    authority = EffectAuthority()
    admitted(authority, 'first')
    admitted(authority, 'resume')
    authority.commit(intent('first'), 'attempt', lambda: (_ for _ in ()).throw(OSError()))
    with pytest.raises(EffectAuthorityError, match='reconciliation_required'):
        authority.commit(intent('resume'), 'attempt', confirmed)
    assert len(authority.snapshot()) == 1
    assert authority.lookup_effect('destination/product.csv', 'save').intent.run_id == 'first'


def test_effect_capacity_preserves_unknown_recovery_obligation():
    authority = EffectAuthority(max_records=1)
    admitted(authority)
    authority.commit(intent(), 'attempt', lambda: (_ for _ in ()).throw(OSError()))
    with pytest.raises(EffectAuthorityError, match='retention_capacity'):
        authority.commit(intent(effect_id='another'), 'attempt', lambda: confirmed('another'))
    with pytest.raises(EffectAuthorityError, match='unresolved_obligation'):
        authority.release_run('run')
    assert authority.snapshot()[0].receipt.state == 'unknown'


def test_authority_effect_identity_is_kind_qualified():
    authority = EffectAuthority()
    admitted(authority)
    authority.commit(intent(), 'attempt', confirmed)
    other = replace(intent(), kind='publication.commit')
    authority.commit(other, 'attempt', lambda: EffectReceipt('publication.commit', 'confirmed', effect_id='save'))
    assert len(authority.snapshot()) == 2
    assert authority.lookup('run', 'scope', 'save', kind='storage.write').receipt.kind == 'storage.write'
    assert authority.lookup('run', 'scope', 'save', kind='publication.commit').receipt.kind == 'publication.commit'
    with pytest.raises(EffectAuthorityError, match='kind_required'):
        authority.lookup('run', 'scope', 'save')
