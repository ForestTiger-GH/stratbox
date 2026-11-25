"""Competing provider callbacks keep physical and analytical truth separate."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from stratbox.core.execution.contracts import EffectReceipt
from stratbox.core.execution.effects import EffectAuthority, EffectIntent, ExactCurrentRevisionPolicy
from stratbox.core.storage.bytes import write_verified_bytes
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.identity import ByteIdentity


def _intent(label, resource='report.csv', **fields):
    return EffectIntent('run.' + label, 'scope', 'work.' + label, 'storage.write', label, resource, **fields)


def _admit(authority, intent):
    attempt = 'attempt.' + intent.effect_id
    authority.begin_attempt(intent.run_id, intent.scope_id, intent.work_id, attempt)
    return attempt


def test_confirmed_writer_restores_current_after_overlapping_writer_loses_actual_store_cas(tmp_path):
    entered_a, entered_b, release_a, release_b = (Event() for _ in range(4))
    class CompetingStore(LocalFileStore):
        def replace_if_revision(self, path, data, expected_revision):
            entered, release = (entered_a, release_a) if data == b'A' else (entered_b, release_b)
            entered.set()
            assert release.wait(5)
            return super().replace_if_revision(path, data, expected_revision)
    store = CompetingStore(str(tmp_path))
    assert store.create_if_absent('report.csv', b'baseline')
    revision = store.current_revision('report.csv')
    authority = EffectAuthority()
    a = _intent('A', expected_revision=revision, identity=ByteIdentity.of(b'A'))
    b = _intent('B', expected_revision=revision, identity=ByteIdentity.of(b'B'))
    def callback(intent, data):
        stored = write_verified_bytes('report.csv', data, store=store, expected_sha256=intent.identity.sha256,
                                      mode='replace_expected_revision', expected_revision=revision)
        state = 'confirmed' if stored.status in {'stored', 'already_present'} else stored.status
        return EffectReceipt(intent.kind, state, effect_id=intent.effect_id, identity=stored.identity,
                             guarantee=stored.guarantee, stage=stored.stage)
    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(authority.commit, a, _admit(authority, a), lambda: callback(a, b'A'))
        assert entered_a.wait(2)
        second = workers.submit(authority.commit, b, _admit(authority, b), lambda: callback(b, b'B'))
        try:
            assert entered_b.wait(2)
            release_a.set()
            assert first.result(3).state == 'confirmed'
            assert store.read_bytes('report.csv') == b'A'
            pending_a = authority.lookup(a.run_id, a.scope_id, a.effect_id)
            pending_b = authority.lookup(b.run_id, b.scope_id, b.effect_id)
            assert pending_a.contender is False and pending_a.destination_current is None
            assert pending_b.contender is True and pending_b.receipt.state == 'unknown'
        finally:
            release_a.set()
            release_b.set()
        assert second.result(3).state == 'failed'
    assert store.read_bytes('report.csv') == b'A'
    observed_a = authority.lookup(a.run_id, a.scope_id, a.effect_id)
    observed_b = authority.lookup(b.run_id, b.scope_id, b.effect_id)
    assert observed_a.destination_current is True and observed_a.current is True
    assert observed_a.basis_current is None and observed_a.attempt_authorized is True
    assert observed_b.destination_current is False and observed_b.current is False
    assert observed_a.contender is observed_b.contender is False


def test_confirmed_destination_and_source_current_basis_are_independent(tmp_path):
    store = LocalFileStore(str(tmp_path))
    authority = EffectAuthority()
    material = b'reported edition Q'
    a = _intent('A', source_revision='opaque-Q', input_basis='basis-Q', identity=ByteIdentity.of(material))
    policy = ExactCurrentRevisionPolicy('source.editions', source_revision='opaque-Q', input_basis='basis-Q')
    authority.register_revision_policy(a.resource, policy)
    def write():
        stored = write_verified_bytes('report.csv', material, store=store, expected_sha256=a.identity.sha256)
        assert stored.status == 'stored'
        return EffectReceipt(a.kind, 'confirmed', effect_id=a.effect_id, identity=stored.identity)
    authority.commit(a, _admit(authority, a), write)
    before = authority.lookup(a.run_id, a.scope_id, a.effect_id)
    assert before.destination_current is True and before.basis_current is True and before.current is True
    policy.admit_current('opaque-A', 'basis-next', expected_revision=policy.revision)
    after = authority.lookup(a.run_id, a.scope_id, a.effect_id)
    assert store.read_bytes('report.csv') == material
    assert after.receipt.state == 'confirmed'
    assert after.destination_current is True
    assert after.basis_current is False
    assert after.current is False


def test_overlapping_confirmations_need_fresh_destination_observation_not_callback_order(tmp_path):
    store = LocalFileStore(str(tmp_path))
    assert store.create_if_absent('report.csv', b'baseline')
    authority = EffectAuthority()
    a = _intent('A', identity=ByteIdentity.of(b'A'))
    a_written, finish_a = Event(), Event()
    def first_write():
        stored = write_verified_bytes('report.csv', b'A', store=store, expected_sha256=a.identity.sha256,
            mode='replace_expected_revision', expected_revision=store.current_revision('report.csv'))
        assert stored.status == 'stored'
        a_written.set()
        assert finish_a.wait(5)
        return EffectReceipt(a.kind, 'confirmed', effect_id='A', identity=a.identity)
    with ThreadPoolExecutor(max_workers=1) as worker:
        first = worker.submit(authority.commit, a, _admit(authority, a), first_write)
        try:
            assert a_written.wait(2)
            b = _intent('B', expected_revision=store.current_revision('report.csv'), identity=ByteIdentity.of(b'B'))
            def second_write():
                stored = write_verified_bytes('report.csv', b'B', store=store, expected_sha256=b.identity.sha256,
                    mode='replace_expected_revision', expected_revision=b.expected_revision)
                assert stored.status == 'stored'
                return EffectReceipt(b.kind, 'confirmed', effect_id='B', identity=b.identity)
            authority.commit(b, _admit(authority, b), second_write)
        finally:
            finish_a.set()
        assert first.result(3).state == 'confirmed'
    assert store.read_bytes('report.csv') == b'B'
    assert authority.lookup(a.run_id, a.scope_id, 'A').destination_current is None
    observed_b = authority.lookup(b.run_id, b.scope_id, 'B')
    assert observed_b.destination_current is None
    # The provider supplies a new read-back, independent of callback arrival.
    assert ByteIdentity.of(store.read_bytes('report.csv')) == b.identity
    authority.reconcile(b.run_id, b.scope_id, 'B', observed_b.receipt, expected_revision=observed_b.revision)
    assert authority.lookup(b.run_id, b.scope_id, 'B').destination_current is True
    assert authority.lookup(a.run_id, a.scope_id, 'A').destination_current is False


def test_unknown_competitor_retains_destination_evidence_until_known_reconciliation(tmp_path):
    store = LocalFileStore(str(tmp_path))
    authority = EffectAuthority(max_records=2, history_limit=0)
    a = _intent('A', identity=ByteIdentity.of(b'A'))
    def write_a():
        stored = write_verified_bytes('report.csv', b'A', store=store, expected_sha256=a.identity.sha256)
        assert stored.status == 'stored'
        return EffectReceipt(a.kind, 'confirmed', effect_id='A', identity=a.identity)
    authority.commit(a, _admit(authority, a), write_a)
    b = _intent('B', identity=ByteIdentity.of(b'B'))
    authority.commit(b, _admit(authority, b), lambda: (_ for _ in ()).throw(OSError('reply unavailable')))
    authority.release_run(a.run_id)
    authority.release_run(b.run_id)
    held_a = authority.lookup(a.run_id, a.scope_id, 'A')
    held_b = authority.lookup(b.run_id, b.scope_id, 'B')
    assert held_a is not None and held_a.receipt.state == 'confirmed'
    assert held_a.destination_current is None
    assert held_b.receipt.state == 'unknown'
    assert authority.retention_snapshot().records == 2
    assert store.read_bytes('report.csv') == b'A'
    authority.reconcile(b.run_id, b.scope_id, 'B',
        EffectReceipt(b.kind, 'failed', effect_id='B', identity=b.identity), expected_revision=held_b.revision)
    assert authority.retention_snapshot().records == 0
