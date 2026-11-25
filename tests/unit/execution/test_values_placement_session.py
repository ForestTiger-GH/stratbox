"""Completed operation scopes retain managed projections after actual spill."""
from dataclasses import dataclass
import gc
from threading import Event
import weakref

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import (
    Call, CommandDefinition, GraphBody, InputRef, OperationDefinition,
    OutputRef, PortContract, ReuseContract, ScenarioDefinition,
)
from stratbox.composition import prepare_invocation
from stratbox.core.execution.session import ExecutionSession, ExecutionSettings
from stratbox.core.execution.values.placement import ManagedProjection, ManagedResult
from stratbox.sdk.bootstrap import CapabilityRuntimeCatalog
from stratbox.shared.data.processing import DataContract

_entered = Event()
_release = Event()
SIZE = 2 * 1024 * 1024


@dataclass
class Payload:
    data: bytearray


def produce(values, invocation):
    return Payload(bytearray(b"x" * SIZE))


def summarize(values, invocation):
    return len(values["payload"].data)


def wait(values, invocation):
    import sys
    state = sys.modules[__name__]
    state._entered.set()
    if not state._release.wait(10):
        raise ValueError("test.gate_timeout")
    return values["number"]


def runtime():
    payload = PortContract(DataContract("test.placement-payload"), Payload)
    number = PortContract(DataContract("test.placement-number"), int)
    no_reuse = ReuseContract(shareable=False, completed=False)
    commands = (
        CommandDefinition("placement.produce", __name__ + ":produce", outputs={"value": payload}, reuse=no_reuse),
        CommandDefinition("placement.summarize", __name__ + ":summarize", inputs={"payload": payload}, outputs={"value": number}, reuse=no_reuse),
        CommandDefinition("placement.wait", __name__ + ":wait", inputs={"number": number}, outputs={"value": number}, reuse=no_reuse),
    )
    operations = (
        OperationDefinition("placement.original", GraphBody((Call("produce", "placement.produce"),),
            {"value": OutputRef("produce")}), outputs={"value": payload}),
        OperationDefinition("placement.summary", GraphBody((Call("summarize", "placement.summarize", {"payload": InputRef("payload")}),),
            {"value": OutputRef("summarize")}), inputs={"payload": payload}, outputs={"value": number}),
        OperationDefinition("placement.gate", GraphBody((Call("wait", "placement.wait", {"number": InputRef("number")}),),
            {"value": OutputRef("wait")}), inputs={"number": number}, outputs={"value": number}),
    )
    scenario = ScenarioDefinition("placement.chain", GraphBody((Call("original", "placement.original"),
        Call("summary", "placement.summary", {"payload": OutputRef("original")}),
        Call("gate", "placement.gate", {"number": OutputRef("summary")})), {"value": OutputRef("gate")}), outputs={"value": number})
    snapshot = CatalogSnapshot((*commands, *operations, scenario))
    return snapshot, CapabilityRuntimeCatalog(snapshot)


def test_completed_scope_follows_spill_and_drops_actual_payload_before_run_finishes(monkeypatch):
    _entered.clear()
    _release.clear()
    captured = []
    original_init = ManagedResult.__init__

    def capture(self, result, **options):
        original_init(self, result, **options)
        if result.operation_id == "placement.produce":
            captured.append((weakref.ref(result.value), weakref.ref(self)))

    monkeypatch.setattr(ManagedResult, "__init__", capture)
    snapshot, catalog = runtime()
    plan = prepare_invocation("placement.chain", snapshot, catalog)
    settings = ExecutionSettings(max_workers=1, retained_bytes=16 * SIZE, staging_bytes=16 * SIZE)
    with ExecutionSession(catalog, settings=settings) as session:
        handle = session.submit(plan)
        try:
            assert _entered.wait(8)
            assert captured, "The actual command result must enter the common placement owner."
            gc.collect()
            assert all(payload() is None for payload, _ in captured)
            assert all(owner().placement == "temporary" for _, owner in captured)
            with session._condition:
                completed = handle._run.scope_outputs["placement.chain/original"]
                assert isinstance(completed["value"], ManagedProjection)
            assert session.ledger.snapshot().occupied["retained_bytes"] < SIZE
        finally:
            _release.set()
        result = handle.result(8)
        assert result.outcome == "succeeded"
        assert result.output("value") == SIZE
        restored = result.scope_outputs["placement.chain/original"]["value"]
        assert len(restored.data) == SIZE
        result.close()
        # Explicit caller-owned output remains usable after internal release.
        assert restored.data[0] == ord("x")
        assert session.ledger.snapshot().occupied["retained_bytes"] == 0
