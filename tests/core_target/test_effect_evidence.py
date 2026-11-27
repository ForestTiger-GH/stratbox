"""Every effect entrance admits the same exact provider evidence."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from stratbox.core.execution.effect_evidence import admit_evidence
from stratbox.core.execution.service import EffectReceipt
from stratbox.core.notifications import MemoryNotificationState
from stratbox.core.observability.journal import MemoryJournal
from stratbox.sdk import StrategyBox
from stratbox.shared.data.materials import NamedEffectIntent, NamedMaterialReceipt
from stratbox.shared.identity import ByteIdentity


@pytest.mark.parametrize('route', ('action', 'retry', 'explicit'))
@pytest.mark.parametrize('as_object', (False, True))
@pytest.mark.parametrize('conflict', ('intent_id', 'kind', 'both_id_aliases', 'both_kind_aliases',
                                    'provider_scope', 'payload', 'route', 'status_aliases'))
def test_conflicting_notification_evidence_never_retires_pending_or_resends(route, as_object, conflict):
    state, journal = MemoryNotificationState(), MemoryJournal()
    journal.append(kind='output.accepted', run_id='source', data={'value': 'authoritative'})
    intent, = state.prepare(journal.read(), route='channel')
    value = {'status': 'confirmed'}
    if conflict == 'both_id_aliases':
        value.update(effect_id=intent['id'], intent_id='foreign')
    elif conflict == 'both_kind_aliases':
        value.update(effect_kind='notification.deliver', kind='storage.write')
    elif conflict == 'status_aliases':
        value['confirmation'] = 'rejected'
    else:
        value[conflict] = {'text': 'foreign'} if conflict == 'payload' else 'foreign'
    observation = SimpleNamespace(**value) if as_object else value

    class Channel:
        scope_id = 'fixture.channel'
        calls = 0
        def deliver(self, supplied):
            self.calls += 1
            if route != 'action':
                raise OSError('Lost acknowledgement')
            return observation
        def lookup(self, effect_id):
            return observation

    channel = Channel()
    with StrategyBox(providers={'notification': channel, 'notification_state': state}) as box:
        first = box.invoke('command.notification.deliver', inputs={'intent': intent})
        if route == 'retry':
            result = box.invoke('command.notification.deliver', inputs={'intent': intent})
            assert result.outcome == 'unknown'
        elif route == 'explicit':
            receipt = first.effects[intent['id']]
            result = box.invoke('command.notification.reconcile', inputs={'receipt': receipt})
            assert result.output('assessment').status == 'unknown'
        else:
            assert first.outcome == 'unknown'
        assert box.session.lookup_effect(intent['id']).status == 'unknown'
        assert channel.calls == 1 and state.pending() == (intent,)


@pytest.mark.parametrize('field', ('destination', 'identity', 'provider_scope', 'operation'))
@pytest.mark.parametrize('source', ('action', 'lookup'))
def test_named_storage_payload_is_validated_after_status_and_identity(field, source):
    identity = ByteIdentity.of(b'expected')
    intent = NamedEffectIntent('copy', 'scope', 'destination', identity)
    expected = EffectReceipt('effect', 'storage.write', 'unknown', resource='destination', intent=intent)
    receipt = NamedMaterialReceipt('destination', identity, 'scope', guarantee='atomic_create')
    wrong = ByteIdentity.of(b'other') if field == 'identity' else 'move' if field == 'operation' else 'foreign'
    admitted = admit_evidence(expected, replace(receipt, **{field: wrong}), source=source)
    assert admitted.outcome == 'conflict'


def test_current_bytes_cannot_prove_a_conditional_replacement_or_its_precondition():
    intent = NamedEffectIntent('copy', 'scope', 'named', ByteIdentity.of(b'new'),
        expected_destination=ByteIdentity.of(b'old'), policy='replace_if_matches',
        expected_destination_revision='observed-revision')
    expected = EffectReceipt('effect', 'storage.write', 'unknown', resource='named', intent=intent)
    current = NamedMaterialReceipt('named', intent.identity, 'scope', guarantee='verified_current_postcondition')
    assert admit_evidence(expected, current, source='lookup').outcome == 'unknown'
    wrong = {'status': 'confirmed', 'effect_id': 'effect', 'expected_destination_revision': 'foreign'}
    assert admit_evidence(expected, wrong, source='action').outcome == 'conflict'


@pytest.mark.parametrize('provider_id, outcome', (('qualified.files', 'confirmed'), ('foreign.files', 'conflict')))
def test_publication_provider_identity_echo_must_match_the_sealed_owner(provider_id, outcome):
    intent = {'provider_id': 'qualified.files', 'provider_scope': 'scope', 'destination': 'release.json',
        'expected_token': 'old-token', 'identity': 'new-token'}
    expected = EffectReceipt('publish', 'publication.write', 'unknown', resource='release.json', intent=intent)
    observed = {'status': 'confirmed', 'provider_id': provider_id, 'token': 'new-token'}
    assert admit_evidence(expected, observed).outcome == outcome


def test_typed_evidence_cannot_be_rebound_to_another_occurrence():
    intent = {'id': 'one', 'payload': {'text': 'message'}}
    expected = EffectReceipt('one', 'notification.deliver', 'unknown', resource='channel', intent=intent)
    admitted = admit_evidence(expected, {'status': 'accepted', 'intent_id': 'one'})
    assert admitted.outcome == 'confirmed'
    assert admitted.evidence.acknowledgement_level == 'accepted'
    assert admit_evidence(replace(expected, effect_id='two'), admitted.evidence).outcome == 'conflict'


@pytest.mark.parametrize('source', ('action', 'lookup'))
@pytest.mark.parametrize('wrapper', ('evidence', 'receipt'))
@pytest.mark.parametrize('outer,inner', (('confirmed', 'rejected'), ('confirmed', 'unknown'),
                                      ('rejected', 'confirmed'), ('unknown', 'confirmed')))
def test_nested_acknowledgement_status_cannot_be_promoted_by_a_wrapper(source, wrapper, outer, inner):
    expected = EffectReceipt('one', 'notification.deliver', 'unknown', resource='channel',
        intent={'id': 'one', 'payload': {'message': 'exact'}})
    payload = {'status': inner, 'intent_id': 'one'}
    if wrapper == 'receipt':
        observed = replace(expected, status=outer, value=payload)
    else:
        admitted = admit_evidence(expected, {'status': 'confirmed', 'intent_id': 'one'})
        from stratbox.shared.data.values import fingerprint
        observed = replace(admitted.evidence, outcome=outer, payload=payload,
            evidence_identity=fingerprint(payload), acknowledgement_level=None)
    result = admit_evidence(expected, observed, source=source)
    assert result.outcome == 'conflict' and result.finding == 'effect.evidence_status_conflict'


def test_nested_receipt_payload_aliases_remain_bound_to_the_same_intent():
    expected = EffectReceipt('one', 'notification.deliver', 'unknown', resource='channel', intent={'id': 'one'})
    observed = replace(expected, status='confirmed', value={'status': 'confirmed', 'intent_id': 'different'})
    assert admit_evidence(expected, observed, source='lookup').outcome == 'conflict'
