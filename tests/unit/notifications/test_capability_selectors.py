"""Exact selectors never broaden missing capability coordinates."""
from dataclasses import replace
import pytest

from stratbox.core.notifications import CapabilitySelector
from stratbox.core.notifications.contracts import DispatchSelectionEvidence
from stratbox.core.notifications.state.codec import decode_state_mutation, encode_state_mutation
from stratbox.core.notifications.state.contracts import StateMutation


def test_selector_uses_exact_kind_scope_and_output_coordinates():
    selector = CapabilitySelector('extract.observations', 'operation', 'monthly/item-1/extract', 'observations')
    exact = dict(capability_id='extract.observations', capability_kind='operation',
        scope_id='monthly/item-1/extract', output_name='observations')
    assert selector.matches(exact)
    for name in selector.fields:
        missing = dict(exact)
        del missing[name]
        assert not selector.matches(missing)
        different = {**exact, name: 'other'}
        assert not selector.matches(different)
    assert not DispatchSelectionEvidence('value.accepted').matches(selector)
    with pytest.raises(ValueError, match='selector_kind_invalid'):
        CapabilitySelector(capability_kind='run')
    with pytest.raises(ValueError, match='selector_empty'):
        CapabilitySelector()


def test_subscription_selector_survives_the_transaction_codec(session):
    runtime, key, _, _, _, _ = session
    sub = runtime.state.get_subscription(key.scope_id, key.subscription_id)
    selector = CapabilitySelector('sample.command', 'command', output_name='value')
    changed = replace(sub, revision=sub.revision + 1, spec=replace(sub.spec, selector=selector))
    mutation = StateMutation(key.scope_id, key.subscription_id, sub.revision, subscription=changed)
    assert decode_state_mutation(encode_state_mutation(mutation)) == mutation
