"""Coordinator sharing, dynamic admission and real retained capacity."""
from dataclasses import dataclass, replace
from threading import Event
from time import monotonic, sleep

import pytest

from stratbox.composition import (
    InputRef, MapStep, OperationStep, PlanOutputRef, ScenarioDefinition, compile_workflow,
)
from stratbox.core.execution import (
    OperationDefinition, OperationSemantics, OutputPort, ProcessingStage, run,
)
from stratbox.core.execution.resources import ResourceLedger
from stratbox.core.execution.session import ExecutionSession, ExecutionSettings
from stratbox.operations.catalog import OperationCatalog, OperationRef
from stratbox.shared.data.processing import DataContract


@dataclass(frozen=True)
class NumberRequest:
    value: int = 3


NUMBER = DataContract("coordinator.number")
DEFINITION = OperationDefinition("coordinator.number", "coordinator.number", NumberRequest, int,
    processing=OperationSemantics((ProcessingStage.CALCULATE,), parameters=("value",),
        outputs=(OutputPort("value", NUMBER),), summary="Produce one controlled value."))
HTTP = replace(DEFINITION, operation_id="coordinator.http", required_capabilities=frozenset({"http"}))
ENTERED, RELEASE = Event(), Event()
CALLS = []


def number(request, *, context=None):
    def work(req, invocation):
        CALLS.append(req.value)
        ENTERED.set()
        while not RELEASE.wait(.002):
            invocation.check_cancelled()
        return req.value
    return run(DEFINITION, request, work, context=context)


def http(request, *, context=None):
    return run(HTTP, request, lambda req, invocation: req.value, context=context)


def eventually(predicate):
    deadline = monotonic() + 3
    while monotonic() < deadline:
        if predicate():
            return
        sleep(.002)
    assert predicate()


def catalog():
    return OperationCatalog((OperationRef(DEFINITION.operation_id, __name__ + ":number", definition=DEFINITION),
                             OperationRef(HTTP.operation_id, __name__ + ":http", definition=HTTP)))


def plan(operations, value=3):
    definition = ScenarioDefinition("one", (OperationStep("work", DEFINITION.operation_id,
        parameters={"value": value}),), {"answer": PlanOutputRef("work")})
    compiled = compile_workflow(definition, operations)
    from stratbox.composition.compiler import plan_identity
    compiled = replace(compiled, tasks=tuple(replace(task, capability_kind="command", reuse_eligible=True)
                                             for task in compiled.tasks))
    return replace(compiled, plan_id=plan_identity(compiled.definition_id, compiled.tasks, compiled.outputs,
        compiled.scopes, compiled.policy, compiled.root_kind, compiled.selected_bindings))


def test_shared_follower_never_occupies_worker_and_producer_cancel_preserves_other_use():
    ENTERED.clear(); RELEASE.clear(); CALLS.clear()
    operations = catalog()
    with ExecutionSession(operations, settings=ExecutionSettings(max_workers=1, active_runs=2)) as session:
        first = session.submit(plan(operations))
        assert ENTERED.wait(2)
        second = session.submit(plan(operations))
        eventually(lambda: second.snapshot().tasks[0].state == "shared_wait")
        assert session.ledger.snapshot().occupied["worker"] == 1
        first.cancel()
        RELEASE.set()
        a, b = first.result(3), second.result(3)
        assert a.outcome == "cancelled"
        assert b.outcome == "succeeded", b.diagnostics
        assert b.output("answer") == 3
        assert CALLS == [3]
        assert first.snapshot().physical_work_count == 1
        assert second.snapshot().physical_work_count == 0
        a.close(); b.close()


def test_completed_reuse_is_accounted_separately_from_all_live_result_bytes():
    ENTERED.clear(); RELEASE.set(); CALLS.clear()
    operations = catalog()
    with ExecutionSession(operations) as session:
        first = session.run(plan(operations))
        assert first.output("answer") == 3
        occupied = session.ledger.snapshot().occupied
        assert occupied["retained_bytes"] > 0 and occupied["cache_bytes"] > 0
        second = session.run(plan(operations))
        assert second.output("answer") == 3
        assert len(CALLS) == 1
        assert session.snapshot(second.run_id).physical_work_count == 0
        different = session.run(plan(operations, 7))
        assert different.output("answer") == 7 and CALLS == [3, 7]
        first.close(); second.close(); different.close()
        assert session.ledger.snapshot().occupied["retained_bytes"] == 0
        assert session.ledger.snapshot().occupied["cache_bytes"] > 0
    assert session.ledger.snapshot().occupied["cache_bytes"] == 0


def test_result_close_preserves_existing_reader_and_then_releases_capacity():
    RELEASE.set()
    operations = catalog()
    with ExecutionSession(operations) as session:
        result = session.run(plan(operations))
        reader = result.read("answer")
        result.close()
        assert reader.value == 3
        assert session.ledger.snapshot().occupied["retained_bytes"] > 0
        with pytest.raises(RuntimeError, match="result.closed"):
            result.output("answer")
        reader.close()
        assert session.ledger.snapshot().occupied["retained_bytes"] == 0


def test_only_dynamic_http_leaf_receives_same_network_preparation_as_static_leaf(monkeypatch):
    operations = catalog()
    item = ScenarioDefinition("item", (OperationStep("http", HTTP.operation_id,
        parameters={"value": InputRef("item")}),), {"value": PlanOutputRef("http")}, inputs={"item": None})
    definition = ScenarioDefinition("dynamic", (MapStep("items", item, (1, 2), window=1),),
        {"values": PlanOutputRef("items")})
    prepared = []
    original = ExecutionSession._prepare_network
    def prepare(self, context):
        prepared.append(True)
        return original(self, context)
    monkeypatch.setattr(ExecutionSession, "_prepare_network", prepare)
    with ExecutionSession(operations, settings=ExecutionSettings(max_workers=1)) as session:
        result = session.run(compile_workflow(definition, operations))
        assert result.outcome == "succeeded", result.diagnostics
        assert tuple(item.value for item in result.output("values").values) == (1, 2)
        assert len(prepared) == 2
        result.close()


def test_aged_large_claim_reserves_conflicting_units_without_blocking_independent_work(monkeypatch):
    import stratbox.core.execution.resources as resources
    clock = [0.0]
    monkeypatch.setattr(resources, "monotonic", lambda: clock[0])
    ledger = ResourceLedger({"worker": 3, "cpu": 2, "network": 1}, starvation_seconds=1)
    assert ledger.reserve("running", {"worker": 1, "cpu": 1})
    assert not ledger.reserve("large", {"worker": 1, "cpu": 2})
    clock[0] = 2
    assert not ledger.reserve("new-small", {"worker": 1, "cpu": 1})
    assert ledger.reserve("preview", {"worker": 1, "network": 1})
    ledger.release("running")
    assert ledger.reserve("large", {"worker": 1, "cpu": 2})
    assert ledger.snapshot().occupied["cpu"] == 2
