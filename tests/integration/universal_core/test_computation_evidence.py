from dataclasses import replace
from decimal import Decimal
from threading import Event

import pandas as pd
import pytest

from stratbox.data import ByteIdentity, table_identity
from stratbox.execution import EffectReceipt, ExecutionContext, InMemorySink, OperationDefinition, run


def test_table_identity_keeps_scalar_types_missing_states_order_and_index():
    frame = pd.DataFrame({"x": pd.Series([None, "", 0, Decimal("0"), False, -0.0, pd.NA], dtype=object)})
    identity = table_identity((("observations", frame),))
    assert identity == table_identity((("observations", frame.copy()),))
    assert identity != table_identity((("presentation", frame),))
    assert identity != table_identity((("observations", frame.iloc[::-1]),))
    assert identity != table_identity((("observations", frame.rename(index={0: 20})),))
    for row, value in ((0, pd.NA), (2, False), (3, 0), (5, 0.0)):
        edited = frame.copy()
        edited.iloc[row, 0] = value
        assert table_identity((("observations", edited),)) != identity
    edited = frame.copy()
    edited.at[0, "x"] = ["mutable"]
    with pytest.raises(TypeError, match="Unsupported table value"):
        table_identity((("observations", edited),))


def test_closed_incident_and_failed_event_sink_preserve_uncertain_effect():
    class IncidentSink:
        def __init__(self):
            self.incidents = []

        def emit(self, event):
            self.incidents.append(event)
            raise RuntimeError("closed sink unavailable")

    class EventSink(InMemorySink):
        def emit(self, event):
            super().emit(event)
            raise RuntimeError("public sink unavailable")

    def fail(_, invocation):
        invocation.stage("commit")
        invocation.effect(EffectReceipt("storage.write", "unknown", effect_id="logical-key"))
        raise RuntimeError("secret_value")

    definition = OperationDefinition("test.effect", 1, "test-1", str, str,
                                     possible_effects=frozenset({"storage.write"}))
    public, private = EventSink(), IncidentSink()
    outcome = run(definition, "value", fail, context=ExecutionContext(sink=public, incident_sink=private))
    assert outcome.outcome == "unknown"
    diagnostic = outcome.diagnostics[0]
    assert diagnostic.code == "internal.error" and diagnostic.evidence_ref == "logical-key"
    assert public.events[-1].incident_id == private.incidents[0].incident_id == diagnostic.incident_id
    assert private.incidents[0].exception_type == "RuntimeError"
    assert "secret_value" not in public.events[-1].to_json()
    assert "secret_value" not in repr(private.incidents[0])
    assert outcome.observability.dropped == len(public.events)
    assert outcome.observability.incidents_dropped == 1


def test_cancellation_after_known_acceptance_keeps_success():
    token = Event()
    definition = OperationDefinition("test.effect", 1, "test-1", str, str,
                                     possible_effects=frozenset({"storage.write"}))

    def completed(value, invocation):
        receipt = EffectReceipt("storage.write", "unknown", effect_id="logical-key",
                                identity=ByteIdentity.of(value.encode()))
        invocation.effect(receipt)
        token.set()
        invocation.effect(replace(receipt, state="confirmed"))
        return value

    result = run(definition, "value", completed, context=ExecutionContext(cancellation=token))
    assert result.outcome == "succeeded" and len(result.effects) == 1
    assert result.effects[0].state == "confirmed"
