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

    result = run(OP, "ok", worker, context=ExecutionContext(
        clock=clock, sink=InMemorySink(),
    ))
    record = record_from_result(result)
    assert record.payload["observability"]["timing_degraded"] is True
    assert record.payload["observability"]["degraded"] is True


def test_invalid_progress_args_are_rejected_before_deadline_clock_use():
    from stratbox.core.execution import runner
    class BrokenOnProgressClock:
        calls = 0
        def monotonic(self):
            self.calls += 1
            if self.calls > 3:
                raise OSError("clock should not be touched for invalid progress")
            return 0.0
        def now(self):
            return datetime(2026, 11, 19, tzinfo=timezone.utc)
    clock = BrokenOnProgressClock()
    op = OperationDefinition("test.invalid_progress_early", 1, "m-1", int, int)
    def work(request, invocation):
        invocation.progress(True, True)
        return request
    result = run(op, 1, work, context=ExecutionContext(
        clock=clock, budget=ExecutionBudget(seconds=30),
    ))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "internal.error"
    # One shared admission origin + admission checkpoint + terminal checkpoint.
    # No event sink means no optional final timing measurement.
    assert clock.calls == 3


@pytest.mark.parametrize("bad", [float("inf"), float("-inf"), float("nan"), True, "bad"])
def test_invalid_monotonic_origin_rejected_before_execution(bad):
    from stratbox.core.limits import BudgetClockError, BudgetMeter
    with pytest.raises(BudgetClockError):
        BudgetMeter(ExecutionBudget(seconds=1), now=lambda: bad)


def test_nonfinite_monotonic_after_handler_cannot_claim_timed_success():
    class NaNClock(ControlledClock):
        def monotonic(self):
            return float("nan") if self.bad_monotonic else self.t

    clock = NaNClock()

    def work(req, inv):
        inv.effect(EffectReceipt("storage.write", "confirmed", effect_id="write"))
        clock.bad_monotonic = True
        return req

    result = run(OP, "ok", work, context=ExecutionContext(
        clock=clock, budget=ExecutionBudget(seconds=1),
    ))
    assert result.outcome == "failed"
    assert any(d.code == "budget.clock_unavailable" for d in result.diagnostics)
    assert result.effects[0].state == "confirmed"


@pytest.mark.parametrize("feature", ("stage", "progress"))
@pytest.mark.parametrize("sink_enabled", (False, True))
@pytest.mark.parametrize("failure", ("exception", "nan"))
def test_optional_stage_progress_clock_failure_does_not_change_work(
    feature, sink_enabled, failure,
):
    clock = ControlledClock()
    sink = InMemorySink() if sink_enabled else None

    def work(value, invocation):
        if failure == "exception":
            clock.bad_monotonic = True
        else:
            clock.t = float("nan")
        if feature == "stage":
            invocation.stage("load")
        else:
            invocation.progress(1, 2)
        return value

    result = run(OP, "ok", work, context=ExecutionContext(clock=clock, sink=sink))
    assert result.outcome == "succeeded"
    assert result.observability.timing_degraded is sink_enabled
    if sink_enabled and feature == "progress":
        assert not any(event.kind == "operation.progress" for event in sink.events)


def test_many_used_input_receipts_keep_order_and_deduplicate():
    from stratbox.shared.evidence import UsedInputReceipt
    from stratbox.shared.identity import ByteIdentity
    def worker(value, invocation):
        for index in range(10_000):
            item = UsedInputReceipt(
                "source", ByteIdentity.of(str(index).encode()),
                "text/plain", "inline",
            )
            invocation.use(item)
            invocation.use(item)
        return value
    result = run(OP, "ok", worker)
    assert result.outcome == "succeeded"
    assert len(result.used_inputs) == 10_000
    assert result.used_inputs[0].identity == ByteIdentity.of(b"0")
    assert result.used_inputs[-1].identity == ByteIdentity.of(b"9999")


class _TickSequence:
    def __init__(self, ticks):
        self._ticks = iter(ticks)
    def __call__(self):
        return next(self._ticks)


@pytest.mark.parametrize("ticks", [
    (100, 99), (100, float("nan")), (100, float("inf")),
    (100, True), (100, "invalid"),
])
def test_strict_budget_rejects_reversing_or_invalid_monotonic(ticks):
    from stratbox.core.limits import BudgetClockError, BudgetMeter
    meter = BudgetMeter(ExecutionBudget(seconds=10), now=_TickSequence(ticks))
    with pytest.raises(BudgetClockError, match="budget.clock_unavailable"):
        meter.checkpoint()


def test_strict_budget_accepts_equal_forward_and_expires():
    from stratbox.core.limits import BudgetMeter
    meter = BudgetMeter(ExecutionBudget(seconds=10),
                        now=_TickSequence((100, 100, 101, 110)))
    assert meter.seconds_left() == 10
    assert meter.seconds_left() == 9
    with pytest.raises(Exception, match="budget.deadline"):
        meter.checkpoint()


@pytest.mark.parametrize("feature", ("stage", "progress"))
def test_strict_clock_fault_at_work_checkpoint_is_qualified(feature):
    clock = ControlledClock()
    def work(value, invocation):
        clock.bad_monotonic = True
        if feature == "stage":
            invocation.stage("parse")
        else:
            invocation.progress(1, 2)
        return value
    result = run(OP, "ok", work, context=ExecutionContext(
        clock=clock, budget=ExecutionBudget(seconds=10),
    ))
    assert result.outcome == "failed"
    assert any(d.code == "budget.clock_unavailable" for d in result.diagnostics)


def test_strict_clock_fault_with_unknown_effect_dominates_outcome():
    clock = ControlledClock()
    def work(value, invocation):
        invocation.effect(EffectReceipt("storage.write", "unknown", effect_id="write"))
        clock.bad_monotonic = True
        return value
    result = run(OP, "ok", work, context=ExecutionContext(
        clock=clock, budget=ExecutionBudget(seconds=10),
    ))
    assert result.outcome == "unknown"
    assert {d.code for d in result.diagnostics} >= {
        "budget.clock_unavailable", "effect.outcome_unknown",
    }


def test_zip_reader_propagates_clock_fault_without_falsely_marking_corruption():
    from io import BytesIO
    from zipfile import ZipFile
    from stratbox.core.formats.archives.members import open_zip
    from stratbox.core.limits import BudgetClockError, BudgetMeter
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("valid.txt", "valid")
    # First budget checkpoint is before ZIP parsing; second occurs in
    # its try block and must not be reclassified as archive.invalid_zip.
    meter = BudgetMeter(
        ExecutionBudget(seconds=10), now=_TickSequence((100, 100, 99)),
    )
    with pytest.raises(BudgetClockError, match="budget.clock_unavailable"):
        with open_zip(stream.getvalue(), budget=meter):
            pass


def test_budget_measures_from_initial_invocation_tick():
    class ReverseImmediately(ControlledClock):
        def __init__(self):
            super().__init__()
            self.times = iter((100, 99, 100))
        def monotonic(self):
            return next(self.times)
    clock = ReverseImmediately()
    result = run(OP, "ok", lambda req, invocation: req, context=ExecutionContext(
        clock=clock, budget=ExecutionBudget(seconds=10),
    ))
    assert result.outcome == "failed"
    assert any(d.code == "budget.clock_unavailable" for d in result.diagnostics)


def test_batch_keeps_clock_diagnostic_instead_of_internal_error():
    from stratbox.core.execution.batch import attempt_batch
    clock = ControlledClock()
    ticks = iter((100, 100, 99, 100))
    clock.monotonic = lambda: next(ticks)
    definition = OperationDefinition(
        "test.batch_budget_clock", 1, "v1", str, tuple, partial_allowed=True,
    )
    def worker(value, invocation):
        batch = attempt_batch((1, 2), lambda item: item, invocation, continue_on_error=True)
        assert batch.stopped is not None
        return Completion(batch.values, "failed", batch.stopped)
    result = run(definition, "input", worker, context=ExecutionContext(
        clock=clock, budget=ExecutionBudget(seconds=10),
    ))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "budget.clock_unavailable"
    assert not any(d.code == "internal.error" for d in result.diagnostics)


def test_optional_progress_backward_tick_only_degrades_telemetry():
    clock = ControlledClock()
    sink = InMemorySink()
    def worker(value, invocation):
        clock.t = 5.0
        invocation.stage("export")
        invocation.progress(1, 10)
        clock.t = 4.0
        invocation.progress(2, 10)
        clock.t = 6.0
        return value
    result = run(OP, "value", worker, context=ExecutionContext(
        clock=clock, sink=sink,
    ))
    assert result.outcome == "succeeded"
    assert result.observability.timing_degraded
    assert len([e for e in sink.events if e.kind == "operation.progress"]) == 1
