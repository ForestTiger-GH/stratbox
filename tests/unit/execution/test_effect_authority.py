from dataclasses import replace
from threading import Event, Thread

import pytest

from stratbox.core.execution import Correlation, ExecutionContext, OperationDefinition, run
from stratbox.core.execution.contracts import EffectReceipt
from stratbox.core.execution.effects import EffectAuthority, EffectAuthorityError, EffectIntent, ExactCurrentRevisionPolicy
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
        authority.commit(replace(intent(), input_basis='another'), 'new', confirmed)


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
    assert record.destination_current is True
    assert record.attempt_authorized is False
    assert record.current is False


def test_later_run_cannot_publish_older_opaque_source_revision():
    authority = EffectAuthority()
    admitted(authority, 'first')
    admitted(authority, 'later')
    # The source owner admits opaque edition Q as current. Its spelling carries
    # no ordering: a later invocation carrying Z must still be rejected.
    policy = ExactCurrentRevisionPolicy('source.editions', source_revision='Q', input_basis='basis')
    authority.register_revision_policy('destination/product.csv', policy)
    authority.commit(intent('first', source_revision='Q'), 'attempt', confirmed)
    writes = []
    with pytest.raises(EffectAuthorityError, match='source_revision_rejected'):
        authority.commit(intent('later', effect_id='old-save', source_revision='Z'),
                         'attempt', lambda: writes.append(1))
    assert writes == []


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
    authority.release_run('run')
    assert authority.retention_snapshot().runs == 0
    assert authority.retention_snapshot().attempts == 0
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


def test_revisioned_publication_requires_an_explicit_source_policy():
    authority = EffectAuthority()
    admitted(authority)
    with pytest.raises(EffectAuthorityError, match='source_policy_required'):
        authority.commit(intent(source_revision='opaque'), 'attempt', confirmed)
    assert authority.snapshot() == ()


def test_closed_results_release_known_receipts_but_live_cache_pin_survives():
    authority = EffectAuthority(max_records=1, history_limit=0)
    admitted(authority)
    authority.commit(intent(), 'attempt', confirmed)
    authority.retain_run('run', 'cache.accepted')
    authority.finish_run('run')
    assert authority.retention_snapshot().attempts == 0
    authority.release_run('run')
    assert authority.lookup_effect('destination/product.csv', 'save') is not None
    assert authority.retention_snapshot().pins == 1
    authority.release_owner('cache.accepted')
    assert authority.retention_snapshot().records == 0
    assert authority.retention_snapshot().runs == 0


def test_unknown_survives_closed_result_then_reconciliation_releases_obligation():
    authority = EffectAuthority(max_records=1, history_limit=0)
    admitted(authority)
    authority.commit(intent(), 'attempt', lambda: (_ for _ in ()).throw(OSError()))
    authority.release_run('run')
    record = authority.lookup('run', 'scope', 'save')
    assert record is not None and record.receipt.state == 'unknown'
    assert authority.retention_snapshot().runs == authority.retention_snapshot().pins == 0
    authority.reconcile('run', 'scope', 'save', confirmed(), expected_revision=record.revision)
    assert authority.retention_snapshot().records == 0


def test_completed_attempt_and_receipt_history_stay_bounded_over_many_runs():
    authority = EffectAuthority(max_records=2, history_limit=3, attempt_limit=1)
    for i in range(100):
        run_id = 'run.' + str(i)
        effect_id = 'write.' + str(i)
        admitted(authority, run_id)
        authority.commit(intent(run_id, effect_id=effect_id), 'attempt', lambda: confirmed(effect_id))
        authority.finish_run(run_id)
        authority.release_run(run_id)
        snapshot = authority.retention_snapshot()
        assert snapshot.records == snapshot.attempts == snapshot.runs == snapshot.pins == 0
        assert snapshot.history <= 3
    assert authority.retention_snapshot().history == 3


def test_explicit_source_policy_rejects_older_source_with_real_valid_destination_cas(tmp_path):
    from stratbox.core.capabilities.materials import store_commit
    from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding
    from stratbox.core.storage.filestore import LocalFileStore
    from stratbox.core.storage.staging import storage_scope
    from stratbox.shared.data.representation import Representation
    from stratbox.shared.evidence import StoredBytesReceipt
    store = LocalFileStore(str(tmp_path))
    authority = EffectAuthority()
    resource = storage_scope(store, 'current.csv') + ':current.csv'
    policy = ExactCurrentRevisionPolicy('official.editions', source_revision='Q', input_basis='basis')
    authority.register_revision_policy(resource, policy)
    definition = OperationDefinition('test.publish_source', 'publish', dict, StoredBytesReceipt,
        required_capabilities=frozenset({'output_filestore'}), possible_effects=frozenset({'storage.write'}))
    def context(run_id):
        admitted(authority, run_id)
        return ExecutionContext(correlation=Correlation(run_id=run_id, workflow_scope_id='scope', task_id='work', attempt_id='attempt'),
            effect_authority=authority, bindings=(ProviderBinding('output', CapabilityRequirement('output_filestore'), 'ready', store),))
    current = Representation('csv', 1, 'text/csv', b'Q\ncurrent')
    first = run(definition, dict(material=current, destination='current.csv', source_revision='Q', input_basis='basis'),
                store_commit, context=context('first'))
    assert first.outcome == 'succeeded', first.diagnostics
    revision = store.current_revision('current.csv')
    old = Representation('csv', 1, 'text/csv', b'Z\nolder')
    later = run(definition, dict(material=old, destination='current.csv', mode='replace_expected_revision',
        expected_revision=revision, source_revision='Z', input_basis='older'), store_commit, context=context('later'))
    assert later.outcome == 'failed'
    assert any(d.code == 'effect.source_revision_rejected' for d in later.diagnostics)
    assert store.current_revision('current.csv') == revision
    assert (tmp_path / 'current.csv').read_bytes() == current.data


def test_policy_admission_uses_owner_cas_and_stale_receipt_cannot_become_current():
    authority = EffectAuthority()
    policy = ExactCurrentRevisionPolicy('source.editions', source_revision='opaque-Z', input_basis='basis')
    authority.register_revision_policy('destination/product.csv', policy)
    admitted(authority)
    original = intent(source_revision='opaque-Z')
    authority.commit(original, 'attempt', confirmed)
    record = authority.lookup('run', 'scope', 'save')
    assert record.publication_policy_id == policy.policy_id
    assert record.publication_policy_revision == policy.revision
    revision = policy.revision
    # Owner metadata supplies the successor even though its label sorts first.
    policy.admit_current('opaque-A', 'basis-next', expected_revision=revision)
    with pytest.raises(EffectAuthorityError, match='source_policy_conflict'):
        policy.admit_current('opaque-Z', 'basis', expected_revision=revision)
    assert authority.lookup('run', 'scope', 'save').current is False
    admitted(authority, 'resume')
    with pytest.raises(EffectAuthorityError, match='source_revision_rejected'):
        authority.commit(replace(original, run_id='resume'), 'attempt', confirmed)


def test_publication_credit_is_admitted_before_each_distinct_commit():
    authority = EffectAuthority()
    admitted(authority)
    writes = []
    def admit_effect(kind, effect_id):
        if effect_id == 'second':
            raise ValueError('orchestration.publication_capacity')
    context = ExecutionContext(correlation=Correlation(run_id='run', workflow_scope_id='scope', task_id='work', attempt_id='attempt'),
        effect_authority=authority, effect_admitter=admit_effect)
    definition = OperationDefinition('test.variable_effects', 'commit', int, int,
                                    possible_effects=frozenset({'storage.write'}))
    def work(value, invocation):
        for effect_id in ('first', 'second'):
            def action(effect_id=effect_id):
                writes.append(effect_id)
                return confirmed(effect_id)
            invocation.commit_effect('storage.write', effect_id, action, resource='resource.' + effect_id)
        return value
    result = run(definition, 1, work, context=context)
    assert result.outcome == 'failed'
    assert writes == ['first']
    assert [receipt.effect_id for receipt in result.effects] == ['first']
    assert any(d.code == 'orchestration.publication_capacity' and d.stage == 'admission' for d in result.diagnostics)


def test_new_confirmed_attempt_supersedes_failed_history_and_pins_receipt_for_new_consumer():
    authority = EffectAuthority(max_records=2, history_limit=2)
    admitted(authority, 'failed')
    authority.commit(intent('failed'), 'attempt', lambda: EffectReceipt('storage.write', 'failed', effect_id='save'))
    authority.release_run('failed')
    admitted(authority, 'confirmed')
    authority.commit(intent('confirmed'), 'attempt', confirmed)
    assert authority.lookup_effect('destination/product.csv', 'save', kind='storage.write').receipt.state == 'confirmed'
    admitted(authority, 'consumer')
    authority.commit(intent('consumer'), 'attempt', lambda: (_ for _ in ()).throw(AssertionError('physical write repeated')))
    authority.release_run('confirmed')
    assert authority.retention_snapshot().records == 1
    authority.release_run('consumer')
    assert authority.retention_snapshot().records == 0
