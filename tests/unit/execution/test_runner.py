from dataclasses import dataclass
from threading import Event

from stratbox.execution import (
    Completion,
    Correlation,
    ExecutionContext,
    InMemorySink,
    OperationDefinition,
    run,
)


@dataclass(frozen=True)
class Request:
    sensitive: str


OP = OperationDefinition("test.calculate", 1, "test-calculation-1", Request, str)


def test_events_have_invocation_correlation_sequences_and_safe_diagnostics():
    sink = InMemorySink()
    context = ExecutionContext(
        correlation=Correlation(run_id="consumer-123"), sink=sink
    )
    request = Request("credential=NEVER_SERIALIZE")

    def work(req, invocation):
        invocation.stage("validate")
        raise RuntimeError(req.sensitive)

    result = run(OP, request, work, context=context)
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "internal.error"
    assert [event.sequence for event in sink.events] == [1, 2, 3]
    assert sink.events[-1].outcome == "failed"
    assert sink.events[-1].duration_ms >= 0
    assert all(event.invocation_id == result.invocation_id for event in sink.events)
    assert all(
        event.occurred_at_utc.utcoffset().total_seconds() == 0 for event in sink.events
    )
    assert all("NEVER_SERIALIZE" not in event.to_json() for event in sink.events)
    assert run(OP, request, lambda req, inv: "ok").invocation_id != result.invocation_id


def test_sink_failure_and_cooperative_cancellation_are_independent():
    class Broken:
        def emit(self, event):
            raise OSError("sink offline")

    operation = run(
        OP,
        Request("input"),
        lambda req, inv: "ok",
        context=ExecutionContext(sink=Broken()),
    )
    assert operation.outcome == "succeeded"
    assert operation.observability.dropped == 2
    token = Event()
    token.set()
    cancelled = run(
        OP,
        Request("input"),
        lambda req, inv: "unreachable",
        context=ExecutionContext(cancellation=token),
    )
    assert cancelled.outcome == "cancelled"
    invalid = run(
        OP,
        Request("input"),
        lambda req, inv: Completion("value", "partial", "source.incomplete"),
    )
    assert invalid.diagnostics[0].code == "internal.error"
