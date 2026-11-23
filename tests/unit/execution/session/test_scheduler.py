"""Shared execution capacity, graph outcomes and bounded expansion."""
from dataclasses import dataclass, replace
from threading import Event, Lock
from time import sleep

import pytest

from stratbox.composition import (OperationStep, ScenarioDefinition, ScenarioStep, CascadeDefinition,
    PlanOutputRef, InputRef, MapStep, CollectStep, CollectSpec, RetryPolicy, compile_workflow)
from stratbox.core.execution import (OperationDefinition, OperationSemantics, InputPort,
    OutputPort, ProcessingStage, run, Completion)
from stratbox.core.execution.session import ExecutionSession, ExecutionSettings
from stratbox.core.execution.handoff import prepare_input
from stratbox.operations.catalog import OperationCatalog, OperationRef
from stratbox.shared.data.processing import DataContract, DataRole

C = DataContract("test.scalar", role=DataRole.EXTRACTS)
GROUP = DataContract("test.scalars", role=DataRole.EXTRACTS)

@dataclass(frozen=True)
class Request:
    value: int = 1
    delay: float = 0
    fail: bool = False

DEFINITION = OperationDefinition("test.session", "test.session.method", Request, int,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        summary="Produce a scheduler test value.", parameters=("value", "delay", "fail"), outputs=(OutputPort("value", C),)))
_lock = Lock()
_active = _peak = _calls = 0
_gate = None


def operation(request, *, context=None):
    def work(req, inv):
        global _active, _peak, _calls
        with _lock:
            _active += 1
            _calls += 1
            _peak = max(_peak, _active)
        try:
            if _gate is not None:
                _gate.wait(2)
            sleep(req.delay)
            if req.fail:
                return Completion(None, "failed", "test.transient")
            inv.budget.charge("objects", 1)
            return req.value
        finally:
            with _lock:
                _active -= 1
    return run(DEFINITION, request, work, context=context)


def catalog():
    return OperationCatalog((OperationRef("test.session", __name__ + ":operation", definition=DEFINITION),))


def plan(count=3, **params):
    return compile_workflow(ScenarioDefinition("work", tuple(OperationStep(f"s{i}", "test.session",
        parameters={"value": i, **params}) for i in range(count)),
        outputs={"last": PlanOutputRef(f"s{count-1}")}), catalog())


def test_two_runs_share_worker_capacity_and_keep_distinct_calls():
    global _peak
    _peak = 0
    with ExecutionSession(catalog(), settings=ExecutionSettings(max_workers=2, cpu=2)) as session:
        a = session.submit(plan(4, delay=.02))
        b = session.submit(plan(4, delay=.02))
        assert a.result(5).output("last") == 3
        assert b.result(5).output("last") == 3
        assert len(a.result().results) == 4
        assert _peak == 2
        assert session.ledger.snapshot().peak["worker"] == 2
        assert session.ledger.snapshot().spent["objects"] == 8


def test_nested_scenarios_complete_with_one_worker_and_run_slot():
    inner = ScenarioDefinition("inner", (OperationStep("one", "test.session"),),
                               outputs={"value": PlanOutputRef("one")})
    definition = CascadeDefinition("outer", (ScenarioStep("left", inner), ScenarioStep("right", inner)),
                                   outputs={"value": PlanOutputRef("right")})
    with ExecutionSession(catalog(), settings=ExecutionSettings(max_workers=1, active_runs=1)) as session:
        result = session.run(compile_workflow(definition, catalog()))
        assert result.outcome == "succeeded"
        assert len(result.results) == 2


def test_map_window_runs_entire_local_chain_and_collects_in_input_order():
    body = ScenarioDefinition("body", (OperationStep("call", "test.session", parameters={"value": InputRef("item")}),),
        outputs={"value": PlanOutputRef("call")}, inputs={"item": None})
    definition = ScenarioDefinition("many", (MapStep("map", body, (4, 1, 9), window=1),
        CollectStep("join", CollectSpec((PlanOutputRef("map"),), GROUP, C))),
        outputs={"values": PlanOutputRef("join")})
    with ExecutionSession(catalog(), settings=ExecutionSettings(max_workers=1, map_window=1)) as session:
        result = session.submit(compile_workflow(definition, catalog())).result(5)
        assert result.outcome == "succeeded"
        assert result.output("values") == (4, 1, 9)


def test_retry_wait_releases_worker_and_deadline_wait_does_not_release_slot():
    global _gate
    _gate = Event()
    try:
        with ExecutionSession(catalog(), settings=ExecutionSettings(max_workers=1)) as session:
            handle = session.submit(plan(1))
            with pytest.raises(TimeoutError):
                handle.result(.03)
            assert session.ledger.snapshot().occupied["worker"] == 1
            handle.cancel()
            assert not handle.done()
            _gate.set()
            result = handle.result(5)
            assert result.results["work/s0"].outcome == "succeeded"
    finally:
        _gate = None


def test_cumulative_budget_applies_across_runs():
    with ExecutionSession(catalog(), settings=ExecutionSettings(max_workers=1, expenditure={"objects": 2})) as session:
        first = session.run(plan(2))
        second = session.run(plan(1))
        assert first.outcome == "succeeded"
        assert second.outcome == "failed"
        assert session.ledger.snapshot().spent["objects"] == 2


def test_fair_rounds_allow_small_run_before_large_run_finishes():
    with ExecutionSession(catalog(), settings=ExecutionSettings(max_workers=1)) as session:
        large = session.submit(plan(20, delay=.015))
        small = session.submit(plan(1, delay=.001))
        assert small.result(5).outcome == "succeeded"
        assert not large.done()
        assert large.result(5).outcome == "succeeded"


def test_retained_value_quota_fails_without_waiting_forever():
    with ExecutionSession(catalog(), settings=ExecutionSettings(retained_bytes=1)) as session:
        result = session.submit(plan(2)).result(5)
        assert result.outcome == "failed"
        assert any(d.code == "resource.retained_bytes" for item in result.results.values() for d in item.diagnostics)
        assert session.ledger.snapshot().reservations == 0


def test_retry_releases_slot_during_delay():
    failing = ScenarioDefinition("retry", (OperationStep("one", "test.session", parameters={"fail": True},
        retry=RetryPolicy(max_attempts=3, delay=.1, retry_codes=("test.transient",))),))
    with ExecutionSession(catalog(), settings=ExecutionSettings(max_workers=1)) as session:
        retrying = session.submit(compile_workflow(failing, catalog()))
        quick = session.submit(plan(1))
        assert quick.result(5).outcome == "succeeded"
        assert not retrying.done()
        result = retrying.result(5)
        assert result.outcome == "failed"
        assert result.tasks[0].attempts == 3


def test_nested_maps_and_external_parameters_complete_with_small_windows():
    leaf = ScenarioDefinition("leaf", (OperationStep("call", "test.session", parameters={
        "value": InputRef("item"), "delay": InputRef("delay")}),),
        outputs={"value": PlanOutputRef("call")}, inputs={"item": None, "delay": None})
    branch = ScenarioDefinition("branch", (MapStep("inner", leaf, InputRef("items"), window=1,
        inputs={"delay": InputRef("delay")}), CollectStep("join", CollectSpec((PlanOutputRef("inner"),), GROUP, C))),
        outputs={"value": PlanOutputRef("join")}, inputs={"items": None, "delay": None})
    nested = ScenarioDefinition("nested", (MapStep("outer", branch, ((1,2), (3,4)), item_input="items", window=1,
        inputs={"delay": 0.0}),), outputs={"value": PlanOutputRef("outer")})
    with ExecutionSession(catalog(), settings=ExecutionSettings(max_workers=1, map_window=1)) as session:
        result = session.submit(compile_workflow(nested, catalog())).result(5)
        assert result.outcome == "succeeded"
        assert tuple(item.value for _, item in result.output("value").items) == ((1, 2), (3, 4))


def test_inflight_map_expansion_is_bounded_while_handler_is_slow():
    global _gate
    _gate = Event()
    body = ScenarioDefinition("body", (OperationStep("call", "test.session", parameters={"value": InputRef("item")}),),
        outputs={"value": PlanOutputRef("call")}, inputs={"item": None})
    workflow = ScenarioDefinition("bounded", (MapStep("map", body, tuple(range(100)), window=2),),
        outputs={"value": PlanOutputRef("map")})
    try:
        with ExecutionSession(catalog(), settings=ExecutionSettings(max_workers=2, cpu=2, map_window=2)) as session:
            handle = session.submit(compile_workflow(workflow, catalog()))
            sleep(.04)
            snapshot = handle.snapshot()
            assert sum(task.operation_id is not None for task in snapshot.tasks) <= 2
            assert not snapshot.total_known
            _gate.set()
            assert handle.result(10).outcome == "succeeded"
    finally:
        _gate = None


def test_nested_scope_expenditure_is_shared_by_siblings_not_independent_calls():
    limited = ScenarioDefinition("limited", tuple(OperationStep(f"s{i}", "test.session") for i in range(3)),
                                 expenditure={"objects": 2})
    other = ScenarioDefinition("other", (OperationStep("okay", "test.session"),))
    workflow = CascadeDefinition("budget", (ScenarioStep("limited", limited), ScenarioStep("other", other)))
    with ExecutionSession(catalog(), settings=ExecutionSettings(max_workers=1)) as session:
        result = session.submit(compile_workflow(workflow, catalog())).result(5)
        assert result.outcome == "failed"
        assert result.results["budget/other/okay"].outcome == "succeeded"
        assert session.ledger.snapshot().spent["objects"] == 3


def test_completed_payload_is_owned_by_handle_not_session_registry():
    with ExecutionSession(catalog()) as session:
        handle = session.submit(plan(2))
        result = handle.result(5)
        assert handle.run_id not in session._runs
        assert handle.snapshot().state == "succeeded"
        assert session.snapshot(handle.run_id).state == "succeeded"
        assert result.output("last") == 1
        assert handle.cancel() is False


def test_capacity_held_by_final_output_cannot_deadlock_later_admission():
    workflow = ScenarioDefinition("capacity", (
        OperationStep("first", "test.session"),
        OperationStep("second", "test.session", depends_on=("first",), resources={"retained_bytes": 8}),
    ), outputs={"first": PlanOutputRef("first"), "second": PlanOutputRef("second")})
    with ExecutionSession(catalog(), settings=ExecutionSettings(max_workers=1, retained_bytes=8)) as session:
        result = session.submit(compile_workflow(workflow, catalog())).result(5)
        assert result.outcome == "failed"
        assert "resource.unavailable" in result.diagnostics
