"""Publication backpressure is visible and autonomous waits have a finite end."""
from concurrent.futures import TimeoutError
from threading import Event
from time import monotonic, sleep

import pytest

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import (
    Call, CommandDefinition, GraphBody, InputRef, MapCall, OperationDefinition,
    OutputRef, PortContract, ReuseContract, ScenarioDefinition,
)
from stratbox.core.execution.session import ExecutionSettings
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import DataContract

NUMBER = PortContract(DataContract("wait.number"), int)


class Probe:
    entered, release = Event(), Event()


def emit(request, invocation):
    return request["number"]


def blocked(request, invocation):
    Probe.entered.set()
    while not Probe.release.wait(.002):
        invocation.check_cancelled()
    return request["number"]


def snapshot():
    command = CommandDefinition("wait.emit", __name__ + ":emit", inputs={"number": NUMBER}, outputs={"value": NUMBER},
        reuse=ReuseContract(shareable=False))
    wait = CommandDefinition("wait.blocked", __name__ + ":blocked", parameters={"number": 1}, outputs={"value": NUMBER},
        reuse=ReuseContract(shareable=False))
    operation = OperationDefinition("wait.operation", GraphBody((Call("emit", command.capability_id,
        {"number": InputRef("number")}),), {"value": OutputRef("emit")}), inputs={"number": NUMBER}, outputs={"value": NUMBER})
    item = ScenarioDefinition("wait.item", GraphBody((Call("op", operation.capability_id,
        {"number": InputRef("item")}),), {"value": OutputRef("op")}), inputs={"item": NUMBER}, outputs={"value": NUMBER})
    scenario = ScenarioDefinition("wait.map", GraphBody((MapCall("items", item.capability_id, tuple(range(8)), window=1),),
        {"values": OutputRef("items")}), outputs={"values": PortContract(NUMBER.schema, collection=True)})
    return CatalogSnapshot(definitions=(command, wait, operation, item, scenario))


def eventually(predicate, seconds=3):
    until = monotonic() + seconds
    while monotonic() < until:
        if predicate(): return
        sleep(.003)
    assert predicate()


def test_autonomous_full_outbox_finishes_with_a_diagnostic_and_preserved_prior_facts():
    settings = ExecutionSettings(max_workers=1, publication_capacity=8, external_wait_seconds=.03)
    with StrategyBox(capabilities=snapshot(), settings=settings) as box:
        result = box.invoke("wait.map", timeout=3)
        assert result.outcome == "failed"
        assert "execution.publication_ack_timeout" in result.diagnostics
        assert any(state == "succeeded" for scope, state in result.scopes.items() if "/items/" in scope)
        assert box.session.journal.facts_source.pending > 0
        assert box.session.ledger.snapshot().occupied["worker"] == 0
        result.close()


def test_managed_wait_is_visible_and_acknowledgement_resumes_without_redoing_items():
    settings = ExecutionSettings(max_workers=1, publication_capacity=8, publication_wait_policy="managed")
    with StrategyBox(capabilities=snapshot(), settings=settings) as box:
        handle = box.submit(box.prepare("wait.map"), execution_timeout=3)
        eventually(lambda: handle.snapshot().waiting_for_ack)
        snapshot_state = handle.snapshot()
        assert snapshot_state.state == "waiting_ack"
        assert snapshot_state.waiting_reason == "publication_ack" and snapshot_state.waiting_since is not None
        assert snapshot_state.wait_policy == "managed" and snapshot_state.execution_deadline is not None
        while not handle.done():
            journal = box.session.journal
            head = journal.facts_source.head(journal.facts_stream)
            journal.facts_source.acknowledge(head.tail_offset)
            journal.flush_transitions()
            sleep(.003)
        result = handle.result(1)
        assert result.outcome == "succeeded", result.diagnostics
        assert handle.snapshot().physical_work_count == 8
        result.close()


def test_execution_deadline_cancels_managed_ack_wait_without_a_subscriber():
    settings = ExecutionSettings(max_workers=1, publication_capacity=8, publication_wait_policy="managed")
    with StrategyBox(capabilities=snapshot(), settings=settings) as box:
        handle = box.submit(box.prepare("wait.map"), execution_timeout=.08)
        result = handle.result(2)
        assert result.outcome == "cancelled"
        assert "execution.deadline" in result.diagnostics
        assert box.session.journal.facts_source.pending > 0
        result.close()


def test_wait_timeout_and_execution_timeout_are_independent_sdk_options():
    Probe.entered.clear(); Probe.release.clear()
    with StrategyBox(capabilities=snapshot()) as box:
        handle = box.submit(box.prepare("wait.blocked"))
        try:
            assert Probe.entered.wait(2)
            with pytest.raises(TimeoutError): handle.result(.01)
            assert not handle.done() and handle.snapshot().execution_deadline is None
        finally:
            Probe.release.set()
        result = handle.result(2)
        assert result.outcome == "succeeded"
        result.close()
        Probe.release.clear()
        try:
            with pytest.raises(TimeoutError):
                box.run("wait.blocked", timeout=.005, execution_timeout=.04)
            eventually(lambda: not box.session._runs)
        finally:
            Probe.release.set()


def test_fragment_admission_failure_leaves_tasks_scopes_bindings_and_fact_credits_unchanged():
    from dataclasses import replace
    from stratbox.composition.compiler import plan_identity
    Probe.entered.clear(); Probe.release.clear()
    with StrategyBox(capabilities=snapshot()) as box:
        handle = box.submit(box.prepare("wait.blocked"))
        try:
            assert Probe.entered.wait(2)
            fragment = box.prepare("wait.operation", inputs={"number": 1})
            changed = tuple(replace(task, resources={"cpu": 999}) if task.operation_id else task for task in fragment.tasks)
            fragment = replace(fragment, tasks=changed)
            fragment = replace(fragment, plan_id=plan_identity(fragment.definition_id, fragment.tasks,
                fragment.outputs, fragment.scopes, fragment.policy, fragment.root_kind, fragment.selected_bindings))
            with box.session._condition:
                run = handle._run
                before = (tuple(run.tasks), tuple(run.scope_specs), dict(run.admitted_bindings),
                          dict(box.session.journal._publication_credits))
                with pytest.raises(ValueError, match="resource.unsatisfiable"):
                    box.session._admit_plan(run, fragment)
                after = (tuple(run.tasks), tuple(run.scope_specs), dict(run.admitted_bindings),
                         dict(box.session.journal._publication_credits))
                assert after == before
        finally:
            Probe.release.set()
        result = handle.result(2)
        assert result.outcome == "succeeded"
        result.close()
