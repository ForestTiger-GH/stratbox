"""Real execution sessions feed the existing notification owner and quotas."""
from dataclasses import dataclass, replace
from threading import Event, Lock

from stratbox.composition import OperationStep, ScenarioDefinition, compile_workflow
from stratbox.core.execution import OperationDefinition, OperationSemantics, OutputPort, ProcessingStage, run
from stratbox.core.execution.session import ExecutionSession, ExecutionSettings
from stratbox.core.notifications import (
    AccessDecision, CheckpointKey, ConsumerBinding, MemoryNotificationState,
    SourceBinding, SubscriptionChange, configure_subscription,
)
from stratbox.operations import operation_catalog, OperationCatalog, OperationRef
from stratbox.shared.data.processing import DataContract


@dataclass(frozen=True)
class ComputeRequest:
    value: int = 1


COMPUTE = OperationDefinition("test.observed", "observed", ComputeRequest, int,
    processing=OperationSemantics((ProcessingStage.CALCULATE,), summary="Compute a fixture value.",
        parameters=("value",), outputs=(OutputPort("value", DataContract("test.number")),)))


def compute(request, *, context=None):
    return run(COMPUTE, request, lambda req, invocation: req.value * 2, context=context)


class AllLocalAuthority:
    def authorize(self, request):
        return AccessDecision("allow", frozenset({"run_id", "plan_id", "outcome", "counters",
                              "completed", "total", "reason"}),
                              frozenset({"event_ref", "occurred_at_utc", "correlation"}),
                              "local.grant", "local.route")


def setup_runtime(execution, old_runtime, old_spec, inbox, context):
    stream = execution.journal.stream
    runtime = replace(old_runtime, state=MemoryNotificationState(), authority=AllLocalAuthority(),
        sources=(SourceBinding(stream, "execution.session", "local_snapshot", execution.journal.source),),
        consumers=(ConsumerBinding(stream.scope_id, old_spec.route, "in_process", inbox),))
    spec = replace(old_spec, scope_id=stream.scope_id, subscription_id="runs", streams=(stream,),
                   topic_id="run.completed", projection_id="run_summary")
    configure_subscription(SubscriptionChange("create", spec), runtime=runtime, context=context)
    configure_subscription(SubscriptionChange("enable", spec, 1), runtime=runtime, context=context)
    return runtime, CheckpointKey(stream.scope_id, "runs", stream)


def catalog():
    base = operation_catalog()
    return OperationCatalog((*base.references, OperationRef("test.observed", __name__ + ":compute", definition=COMPUTE)), base.registrations)


def test_real_session_completion_preparation_delivery_and_quotas(session):
    old_runtime, _, context, _, inbox, spec = session
    operations = catalog()
    with ExecutionSession(operations, settings=ExecutionSettings(max_workers=2, notifications=1)) as execution:
        runtime, key = setup_runtime(execution, old_runtime, spec, inbox, context)
        execution.operation_options.update({name: {"runtime": runtime}
            for name in ("notifications.prepare", "notifications.deliver", "notifications.reconcile")})
        computation = compile_workflow(ScenarioDefinition("compute", (
            OperationStep("a", "test.observed", parameters={"value": 3}),
            OperationStep("b", "test.observed", parameters={"value": 5}),
        )), operations)
        handle = execution.submit(computation)
        result = handle.result(5)
        assert result.outcome == "succeeded"
        operation_events = [record for record in execution.journal.records
                            if record.record_type == "execution" and record.correlation.run_id == result.run_id]
        assert len({record.invocation_id for record in operation_events}) == 2
        assert len({record.correlation.task_id for record in operation_events}) == 2
        terminal = next(record for record in execution.journal.records
                        if record.kind == "run.finished" and record.correlation.run_id == result.run_id)
        assert terminal.payload["counters"]["succeeded"] == 2
        prep = compile_workflow(ScenarioDefinition("prepare", (
            OperationStep("prepare", "notifications.prepare", parameters={"key": key}),
        )), operations)
        prepared = execution.submit(prep).result(5)
        assert prepared.outcome == "succeeded", prepared.diagnostics
        dispatches = runtime.state.scan_dispatches(key.scope_id, key.subscription_id, limit=10)
        assert len(dispatches) == 1
        deliveries = compile_workflow(ScenarioDefinition("deliver", tuple(
            OperationStep(f"send{i}", "notifications.deliver", parameters={
                "scope_id": key.scope_id, "dispatch_id": row.intent.dispatch_id})
            for i, row in enumerate(dispatches))), operations)
        assert execution.submit(deliveries).result(5).outcome == "succeeded"
        assert len(inbox.calls) == 1
        capacity = execution.ledger.snapshot()
        assert capacity.peak["worker"] <= 2
        assert capacity.peak["notification"] == capacity.peak["network"] == 1
        # Notification service runs cannot trigger another summary notification.
        next_prepare = execution.submit(prep).result(5)
        assert next_prepare.outcome == "succeeded"
        assert len(runtime.state.scan_dispatches(key.scope_id, key.subscription_id, limit=10)) == 1


def test_real_session_keeps_result_when_terminal_source_temporarily_fails(monkeypatch):
    operations = catalog()
    with ExecutionSession(operations) as execution:
        append = execution.journal.source.append_terminal
        blocked = Event()
        def unavailable(record):
            if not blocked.is_set():
                raise OSError("temporary source failure")
            return append(record)
        monkeypatch.setattr(execution.journal.source, "append_terminal", unavailable)
        definition = compile_workflow(ScenarioDefinition("compute", (OperationStep("a", "test.observed"),)), operations)
        result = execution.submit(definition).result(5)
        assert result.outcome == "succeeded"
        assert execution.journal.health_snapshot().unpublished_transitions == 1
        blocked.set()
        execution.journal.flush_transitions()
        assert execution.journal.health_snapshot().unpublished_transitions == 0
        assert execution.journal.source.pending == 1


def test_snapshot_cursor_reconnect_matches_public_task_correlation():
    operations = catalog()
    with ExecutionSession(operations) as execution:
        definition = compile_workflow(ScenarioDefinition("compute", (OperationStep("a", "test.observed"),)), operations)
        handle = execution.submit(definition)
        snapshot = handle.snapshot()
        result = handle.result(5)
        updates = handle.events(after=snapshot.event_cursor)
        assert all(record.record_type == "orchestration" for record in updates)
        assert all(record.sequence > snapshot.event_cursor for record in updates)
        final = handle.snapshot()
        identities = {task.correlation_id for task in final.tasks}
        task_events = [record for record in handle.events() if record.kind.startswith("task.")]
        assert {record.correlation.task_id for record in task_events} <= identities
        assert final.state == result.outcome == "succeeded"


def test_observation_disabled_or_failed_preserves_real_session_result():
    operations = catalog()
    definition = compile_workflow(ScenarioDefinition("compute", (OperationStep("a", "test.observed"),)), operations)
    def failed_observer(record):
        raise OSError("consumer unavailable")
    for observer in (None, failed_observer):
        with ExecutionSession(operations, observer=observer) as execution:
            result = execution.submit(definition).result(5)
            assert result.outcome == "succeeded"
        health = execution.journal.health_snapshot()
        assert health.observer_failed > 0 if observer else health.observer_failed == 0
        assert execution.journal.source.pending == 1


def test_caller_operation_sinks_are_preserved_and_isolated_by_run():
    from stratbox.core.execution import ExecutionContext, InMemorySink
    operations = catalog()
    definition = compile_workflow(ScenarioDefinition("compute", (OperationStep("a", "test.observed"),)), operations)
    first, second = InMemorySink(), InMemorySink()
    with ExecutionSession(operations, context=ExecutionContext(sink=first)) as execution:
        a = execution.submit(definition)
        b = execution.submit(definition, context=ExecutionContext(sink=second))
        assert a.result(5).outcome == b.result(5).outcome == "succeeded"
    for handle, sink in ((a, first), (b, second)):
        assert sink.events[0].kind == "operation.started"
        assert sink.events[-1].kind == "operation.finished"
        assert {event.correlation.run_id for event in sink.events} == {handle.run_id}
        assert len({event.event_id for event in sink.events}) == len(sink.events)
    assert execution.journal.health_snapshot().observer_failed == 0


def test_slow_and_failed_caller_operation_sink_never_blocks_execution():
    from stratbox.core.execution import ExecutionContext
    operations = catalog()
    definition = compile_workflow(ScenarioDefinition("compute", (OperationStep("a", "test.observed"),)), operations)
    entered, release = Event(), Event()
    class SlowFailingSink:
        def emit(self, event):
            entered.set()
            release.wait(3)
            raise OSError("optional caller sink failed")
    with ExecutionSession(operations, context=ExecutionContext(sink=SlowFailingSink())) as execution:
        handle = execution.submit(definition)
        assert entered.wait(1)
        assert handle.result(1).outcome == "succeeded"
        release.set()
    assert execution.journal.health_snapshot().observer_failed > 0
