from dataclasses import replace
import json

from stratbox.core.execution import Correlation
from stratbox.core.notifications import (
    CheckpointKey, DeliverRequest, PrepareRequest, SourceBinding, SubscriptionChange,
    build_catalog, configure_subscription, deliver, prepare,
)
from stratbox.core.observability import OrchestrationJournal


def test_terminal_run_uses_existing_prepare_and_delivery_without_task_spam(session):
    runtime, _, context, _, inbox, old_spec = session
    journal = OrchestrationJournal("public", max_records=2)
    runtime = replace(runtime, sources=(SourceBinding(journal.stream, "execution.session",
                                                     "local_snapshot", journal.source),))
    spec = replace(old_spec, subscription_id="runs", streams=(journal.stream,),
                   topic_id="run.completed", projection_id="run_summary")
    runtime.authority.fields = frozenset({"run_id", "plan_id", "outcome", "counters", "completed", "total", "reason"})
    configure_subscription(SubscriptionChange("create", spec), runtime=runtime, context=context)
    configure_subscription(SubscriptionChange("enable", spec, 1), runtime=runtime, context=context)
    key = CheckpointKey("public", "runs", journal.stream)
    corr = Correlation(session_id="public", run_id="r", plan_id="p")
    journal.reserve_run("r")
    for _ in range(10):
        journal.emit("task.finished", replace(corr, task_id="t"), outcome="succeeded")
    journal.emit("run.finished", corr, outcome="partial", counters={"succeeded": 9, "failed": 1})
    result = prepare(PrepareRequest(key), runtime=runtime, context=context)
    assert result.outcome == "succeeded", result.diagnostics
    assert result.value.prepared == 1
    assert prepare(PrepareRequest(key), runtime=runtime, context=context).value.prepared == 0
    dispatch = runtime.state.scan_dispatches("public", "runs", limit=10)[0]
    envelope = json.loads(dispatch.intent.envelope_bytes)
    assert envelope["data"]["outcome"] == "partial"
    assert envelope["data"]["counters"] == {"failed": 1, "succeeded": 9}
    request = DeliverRequest("public", dispatch.intent.dispatch_id)
    sent = deliver(request, runtime=runtime, context=context)
    assert sent.outcome == "succeeded", sent.diagnostics
    assert len(inbox.calls) == 1
    again = deliver(request, runtime=runtime, context=context)
    assert again.outcome == "succeeded"
    assert len(inbox.calls) == 1
    # Delivery evidence remains retained until explicit owner acknowledgement.
    assert journal.source.pending == 1


def test_run_topic_rejects_mismatched_transition_envelope():
    import pytest
    journal = OrchestrationJournal("s")
    journal.reserve_run("r")
    record = journal.emit("run.finished", Correlation(session_id="s", run_id="r"), outcome="unknown")
    topic = next(t for t in build_catalog().definitions() if t.topic_id == "run.completed")
    schema = build_catalog().input_schema(topic, record)
    data = schema.validate(record)
    assert topic.eligible(record, data)
    with pytest.raises(ValueError, match="run_envelope_mismatch"):
        topic.eligible(replace(record, outcome="succeeded"), data)
