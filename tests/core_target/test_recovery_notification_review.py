"""Recovery keeps subscription progress, pending work and delivery truth together."""
import sqlite3

import pytest

from stratbox.core.recovery import restore_recovery_package
from stratbox.sdk import StrategyBox
from stratbox.sdk.profile import LocalProfile


SUBSCRIPTION = 'review'
SELECTOR = {'kind': 'fixture.notice'}
ROUTE = 'review-channel'


class Channel:
    scope_id = 'fixture.notification-recovery'

    def __init__(self, *, uncertain=False):
        self.calls = []
        self.lookups = []
        self.uncertain = uncertain

    def deliver(self, intent):
        self.calls.append(intent)
        if self.uncertain:
            raise OSError('fixture.transport_accepted_but_acknowledgement_lost')
        return {'status': 'confirmed', 'effect_id': intent['id']}

    def lookup(self, identity):
        self.lookups.append(identity)
        return {'status': 'confirmed', 'effect_id': identity}


def register(profile):
    return profile.providers['notification_state'].register(SUBSCRIPTION,
        stream_id=profile.journal.stream_id, selector=SELECTOR, route=ROUTE)


def prepare_notice(profile, value='later'):
    before = profile.journal.checkpoint().tail
    profile.journal.append(kind='fixture.notice', run_id='source', data={'value': value})
    page = profile.journal.read_page(after=before)
    with profile.box.invoke('command.notification.prepare', inputs={'page': page}, parameters={
            'subscription_id': SUBSCRIPTION, 'selector': SELECTOR, 'route': ROUTE}) as result:
        assert result.outcome == 'succeeded', result.diagnostics
        return result.output('intents')[-1]


def close_restored(restored):
    if restored is not None:
        restored['providers']['source_state'].close()
        restored['journal'].close()


def test_restore_keeps_post_cut_pending_intent_and_its_consumption_checkpoint(tmp_path):
    package = tmp_path / 'backup'
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        register(profile)
        profile.export_recovery(package)
        intent = prepare_notice(profile)
        expected = profile.providers['notification_state'].checkpoint(SUBSCRIPTION)
    restored = None
    try:
        restored = restore_recovery_package(package, tmp_path / 'restored')
        state = restored['providers']['notification_state']
        assert state.checkpoint(SUBSCRIPTION) == expected
        assert state.pending(SUBSCRIPTION) == (intent,)
        assert restored['journal'].checkpoint().tail >= expected['sequence']
    finally:
        close_restored(restored)


def test_restore_keeps_post_cut_subscription_and_host_named_retention_consumer(tmp_path):
    package, consumer = tmp_path / 'backup', 'host-notification-review'
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        profile.export_recovery(package)
        register(profile)
        profile.journal.register_consumer(consumer, after=0)
        intent = prepare_notice(profile)
        expected = profile.providers['notification_state'].checkpoint(SUBSCRIPTION)
        # Cursor acknowledgement may lag committed queue preparation. Its
        # explicit host identity remains a retention barrier after restoration.
        assert profile.journal.checkpoint().consumers[consumer] == 0
    restored = None
    try:
        restored = restore_recovery_package(package, tmp_path / 'restored')
        state = restored['providers']['notification_state']
        assert state.checkpoint(SUBSCRIPTION) == expected
        assert state.pending(SUBSCRIPTION) == (intent,)
        assert restored['journal'].checkpoint().consumers[consumer] == 0
    finally:
        close_restored(restored)


def test_restore_keeps_post_cut_acknowledgement_without_replaying_transport(tmp_path):
    package, channel = tmp_path / 'backup', Channel()
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files',
                      providers={'notification': channel}) as profile:
        register(profile)
        intent = prepare_notice(profile, 'before cut')
        profile.export_recovery(package)
        with profile.box.invoke('command.notification.deliver', inputs={'intent': intent}) as delivered:
            assert delivered.outcome == 'succeeded', delivered.diagnostics
        assert not profile.providers['notification_state'].pending(SUBSCRIPTION)
        assert len(channel.calls) == 1
    restored = None
    try:
        restored = restore_recovery_package(package, tmp_path / 'restored', providers={'notification': channel})
        state = restored['providers']['notification_state']
        with StrategyBox(providers=restored['providers'], journal=restored['journal']) as box:
            with box.invoke('command.notification.deliver', inputs={'intent': intent}) as repeated:
                assert repeated.outcome == 'succeeded', repeated.diagnostics
        assert len(channel.calls) == 1
        assert state.pending(SUBSCRIPTION) == ()
    finally:
        close_restored(restored)


def test_missing_post_cut_notification_queue_blocks_transfer_despite_retained_effect_receipt(tmp_path):
    package = tmp_path / 'backup'
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        register(profile)
        profile.export_recovery(package)
        prepare_notice(profile)
    (tmp_path / 'profile' / 'notifications' / 'dispatch.sqlite').unlink()
    restored = None
    try:
        with pytest.raises(ValueError, match='notification'):
            restored = restore_recovery_package(package, tmp_path / 'restored')
        assert not (tmp_path / 'profile' / 'journal' / 'writer-closed.json').exists()
        assert not (tmp_path / 'restored' / 'recovery.json').exists()
    finally:
        close_restored(restored)


def test_uncertain_post_cut_delivery_retains_pending_intent_and_uses_lookup_only(tmp_path):
    package, channel = tmp_path / 'backup', Channel(uncertain=True)
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files',
                      providers={'notification': channel}) as profile:
        register(profile)
        intent = prepare_notice(profile, 'before cut')
        profile.export_recovery(package)
        with profile.box.invoke('command.notification.deliver', inputs={'intent': intent}) as delivered:
            assert delivered.outcome == 'unknown'
            receipt = delivered.effects[intent['id']]
        assert len(channel.calls) == 1
    restored = None
    try:
        restored = restore_recovery_package(package, tmp_path / 'restored', providers={'notification': channel})
        assert restored['providers']['notification_state'].pending(SUBSCRIPTION) == (intent,)
        assert restored['providers']['effect_state'].get(intent['id']).status == 'unknown'
        with StrategyBox(providers=restored['providers'], journal=restored['journal']) as box:
            with box.invoke('command.notification.reconcile', inputs={'receipt': receipt}) as reconciled:
                assert reconciled.outcome == 'succeeded', reconciled.diagnostics
                assert reconciled.output('assessment').status == 'confirmed'
        assert len(channel.calls) == 1 and channel.lookups == [intent['id']]
        # Reconciliation establishes transport truth; acknowledgement remains
        # a separate state transition and no pending work disappears here.
        assert restored['providers']['notification_state'].pending(SUBSCRIPTION) == (intent,)
    finally:
        close_restored(restored)


@pytest.mark.parametrize('delivery', ('not_attempted', 'unknown'))
def test_missing_saved_pending_intent_requires_exact_confirmed_delivery_authority(tmp_path, delivery):
    package, channel = tmp_path / 'backup', Channel(uncertain=True)
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files',
                      providers={'notification': channel}) as profile:
        register(profile)
        intent = prepare_notice(profile, 'pending at cut')
        profile.export_recovery(package)
        if delivery == 'unknown':
            with profile.box.invoke('command.notification.deliver', inputs={'intent': intent}) as result:
                assert result.outcome == 'unknown'
    # Inject loss of a row without its required acknowledgement transaction.
    with sqlite3.connect(tmp_path / 'profile' / 'notifications' / 'dispatch.sqlite') as db:
        db.execute('DELETE FROM intents WHERE id=?', (intent['id'],))
    restored = None
    try:
        with pytest.raises(ValueError, match='notification_delivery_authority_missing'):
            restored = restore_recovery_package(package, tmp_path / 'restored')
        assert not (tmp_path / 'profile' / 'journal' / 'writer-closed.json').exists()
    finally:
        close_restored(restored)


@pytest.mark.parametrize('altered', ('policy', 'consumed_identity'))
def test_surviving_notification_overlap_must_agree_with_saved_authority(tmp_path, altered):
    package = tmp_path / 'backup'
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        register(profile)
        prepare_notice(profile, 'at cut')
        profile.export_recovery(package)
    with sqlite3.connect(tmp_path / 'profile' / 'notifications' / 'dispatch.sqlite') as db:
        if altered == 'policy':
            db.execute('UPDATE subscriptions SET policy=? WHERE id=?', ('changed-policy', SUBSCRIPTION))
        else:
            db.execute('UPDATE consumed SET identity=? WHERE subscription=?', ('changed-fact', SUBSCRIPTION))
    restored = None
    try:
        code = 'notification_subscription_regressed' if altered == 'policy' else 'notification_consumption_conflict'
        with pytest.raises(ValueError, match=code):
            restored = restore_recovery_package(package, tmp_path / 'restored')
        assert not (tmp_path / 'profile' / 'journal' / 'writer-closed.json').exists()
    finally:
        close_restored(restored)


def test_notification_capture_detects_same_count_commit_before_transfer(tmp_path, monkeypatch):
    from stratbox.core.notifications.state import FileNotificationState
    package, original_state = tmp_path / 'backup', tmp_path / 'profile' / 'notifications'
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        register(profile)
        prepare_notice(profile, 'at cut')
        profile.export_recovery(package)
    export = FileNotificationState.export_checkpoint

    def interrupted_cut(state, destination, **kwargs):
        result = export(state, destination, **kwargs)
        if state.directory == original_state:
            # Fault injection within the capture boundary: all counts and
            # subscription cursor metadata remain unchanged by this commit.
            with sqlite3.connect(state.directory / 'dispatch.sqlite') as db:
                db.execute('UPDATE consumed SET identity=? WHERE subscription=?', ('changed-during-copy', SUBSCRIPTION))
        return result

    monkeypatch.setattr(FileNotificationState, 'export_checkpoint', interrupted_cut)
    restored = None
    try:
        with pytest.raises(ValueError, match='notification_owner_changed_during_capture'):
            restored = restore_recovery_package(package, tmp_path / 'restored')
        assert not (tmp_path / 'profile' / 'journal' / 'writer-closed.json').exists()
    finally:
        close_restored(restored)
