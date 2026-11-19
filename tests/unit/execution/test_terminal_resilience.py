"""Deadline and faulty-clock behavior at operation finalization."""
from datetime import datetime, timezone
from threading import Event

import pytest

from stratbox.core.execution import (
    Completion, EffectReceipt, ExecutionBudget, ExecutionContext,
    InMemorySink, OperationDefinition, run,
)


OP = OperationDefinition("test.terminal", 1, "m-1", str, str,
    possible_effects=frozenset({"storage.write"}), partial_allowed=True,
)


class ControlledClock:
    def __init__(self):
        self.t = 0.0
        self.bad_monotonic = False
        self.bad_now = False

    def monotonic(self):
        if self.bad_monotonic:
            raise RuntimeError("monotonic clock unavailable")
        return self.t

    def now(self):
        if self.bad_now:
            raise RuntimeError("utc clock unavailable")
        return datetime(2026, 11, 19, tzinfo=timezone.utc)


@pytest.mark.parametrize(("state", "expected"), [
    (None, "failed"), ("confirmed", "failed"), ("unknown", "unknown"),
])
def test_deadline_after_handler_preserves_effect_truth(state, expected):
    clock = ControlledClock()
    sink = InMemorySink()

    def work(req, inv):
        if state is not None:
            inv.effect(EffectReceipt("storage.write", state, effect_id="x"))
        clock.t = 2
        return req

    result = run(OP, "ok", work, context=ExecutionContext(
        clock=clock, sink=sink, budget=ExecutionBudget(seconds=1),
    ))
    assert result.outcome == expected
    assert len(result.effects) == (state is not None)
    assert any(d.code == "budget.deadline" for d in result.diagnostics)
    assert sink.events[-1].outcome == result.outcome


def test_explicit_partial_retains_value_and_deadline_diagnostic():
    clock = ControlledClock()

    def work(req, inv):
        clock.t = 2
        return Completion(req, "partial", "domain.partial_coverage")

    result = run(OP, "ok", work, context=ExecutionContext(
        clock=clock, budget=ExecutionBudget(seconds=1),
    ))
    assert result.outcome == "partial"
    assert {d.code for d in result.diagnostics} >= {"domain.partial_coverage", "budget.deadline"}


def test_late_cancellation_does_not_reclassify_success():
    clock = ControlledClock()
    cancel = Event()

    def work(req, inv):
        cancel.set()
        return req

    result = run(OP, "ok", work, context=ExecutionContext(
        clock=clock, cancellation=cancel,
    ))
    assert result.outcome == "succeeded"


def test_faulty_monotonic_only_degrades_optional_timing():
    clock = ControlledClock()
    sink = InMemorySink()

    def work(req, inv):
        inv.stage("compute")
        inv.effect(EffectReceipt("storage.write", "confirmed", effect_id="write"))
        clock.bad_monotonic = True
        return req

    result = run(OP, "ok", work, context=ExecutionContext(
        clock=clock, sink=sink,
    ))
    assert result.outcome == "succeeded"
    assert result.effects[0].state == "confirmed"
    assert result.observability.timing_degraded
    assert result.observability.dropped == 0
    assert sink.events[-1].duration_ms is None
    assert sink.events[-1].stage_elapsed_ms is None


def test_faulty_utc_timestamp_drops_only_terminal_event():
    clock = ControlledClock()
    sink = InMemorySink()

    def work(req, inv):
        inv.effect(EffectReceipt("storage.write", "confirmed", effect_id="write"))
        clock.bad_now = True
        return req

    result = run(OP, "ok", work, context=ExecutionContext(clock=clock, sink=sink))
    assert result.outcome == "succeeded"
    assert result.effects[0].state == "confirmed"
    assert result.observability.timing_degraded
    assert result.observability.dropped == 1
    assert not any(event.kind == "operation.finished" for event in sink.events)


def test_failed_deadline_clock_cannot_assert_success():
    clock = ControlledClock()

    def work(req, inv):
        inv.effect(EffectReceipt("storage.write", "confirmed", effect_id="write"))
        clock.bad_monotonic = True
        return req

    result = run(OP, "ok", work, context=ExecutionContext(
        clock=clock, budget=ExecutionBudget(seconds=10),
    ))
    assert result.outcome == "failed"
    assert result.effects[0].state == "confirmed"
    assert any(d.code == "budget.clock_unavailable" for d in result.diagnostics)


def test_public_handler_seal_is_not_supported():
    def work(req, inv):
        inv.effect(EffectReceipt("storage.write", "unknown", effect_id="x"))
        inv.seal()
        return req

    result = run(OP, "ok", work)
    assert result.outcome == "unknown"
    assert result.effects[0].state == "unknown"
    assert any(d.code == "internal.error" for d in result.diagnostics)


def test_private_early_seal_does_not_escape_with_confirmed_effect():
    def work(req, inv):
        inv.effect(EffectReceipt("storage.write", "confirmed", effect_id="x"))
        inv._seal()
        return req

    result = run(OP, "ok", work)
    assert result.outcome == "failed"
    assert result.effects[0].state == "confirmed"
    assert any(d.code == "internal.error" for d in result.diagnostics)


def test_resolver_fault_returns_conservative_result_with_receipts(monkeypatch):
    from stratbox.core.execution import runner
    monkeypatch.setattr(runner, "_resolve_completion",
                        lambda *args: (_ for _ in ()).throw(RuntimeError("resolver bug")))
    sink = InMemorySink()

    def work(req, inv):
        inv.effect(EffectReceipt("storage.write", "unknown", effect_id="x"))
        return req

    result = run(OP, "ok", work, context=ExecutionContext(sink=sink))
    assert result.outcome == "unknown"
    assert any(d.code == "internal.error" for d in result.diagnostics)
    assert result.effects[0].state == "unknown"
    assert sink.events[-1].outcome == "unknown"


def test_failed_and_unknown_progress_is_validated_before_telemetry():
    op = OperationDefinition("test.progress", 1, "m-1", int, int)
    for completed, total in ((1.0, 2.0), (True, True), (1, False), (2, 1), (-1, 2)):
        sink = InMemorySink()
        def work(req, inv):
            inv.progress(completed, total)
            return req
        result = run(op, 1, work, context=ExecutionContext(sink=sink))
        assert result.outcome == "failed"
        assert result.diagnostics[0].code == "internal.error"
        assert sink.events[-1].outcome == "failed"
        assert result.observability.dropped == 0


def test_no_deadline_does_not_depend_on_budget_clock():
    from stratbox.core.limits import BudgetMeter, ExecutionBudget
    now = lambda: (_ for _ in ()).throw(RuntimeError("should never read clock"))
    meter = BudgetMeter(ExecutionBudget(), now=now)
    meter.checkpoint()
    assert meter.seconds_left() == float("inf")


def test_second_constructor_fault_keeps_effect_receipts(monkeypatch):
    from stratbox.core.execution import runner
    original = runner.OperationResult
    monkeypatch.setattr(runner, "OperationResult",
                        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("constructor broken")))

    def worker(request, invocation):
        invocation.effect(EffectReceipt("storage.write", "confirmed", effect_id="write"))
        return request

    result = run(OP, "ok", worker)
    assert isinstance(result, original)
    assert result.outcome == "failed"
    assert result.effects[0].state == "confirmed"
    assert result.diagnostics[-1].code == "internal.error"


def test_elapsed_clock_failure_after_effect_is_visible_in_result_summary():
    from stratbox.core.observability.capture.adapters import record_from_result
    clock = ControlledClock()

    def worker(request, invocation):
        invocation.stage("work")
        invocation.effect(EffectReceipt("storage.write", "confirmed", effect_id="write"))
        clock.bad_monotonic = True
        return request

    result = run(OP, "ok", worker, context=ExecutionContext(clock=clock))
    record = record_from_result(result)
    assert record.payload["observability"]["timing_degraded"] is True
    assert record.payload["observability"]["degraded"] is True
