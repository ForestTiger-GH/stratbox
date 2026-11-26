"""Service shutdown drains physical work before reporting its final effect truth."""
from dataclasses import dataclass, field, replace
from pathlib import Path
import subprocess
import sys
from threading import Event
from time import monotonic, sleep

import pytest

from stratbox.capabilities.model import MethodRef, PortContract, ReuseContract
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, PreparedPlan, ValueRef
from stratbox.core.execution.service import ExecutionFailure, ExecutionService, ExecutionSettings
from stratbox.core.observability.journal import MemoryJournal


@dataclass
class Probe:
    entered: Event = field(default_factory=Event)
    release: Event = field(default_factory=Event)
    worker_close_returned: Event = field(default_factory=Event)
    calls: list = field(default_factory=list)
    blocked_starts: int = 0


PROBE = Probe()


@pytest.fixture(autouse=True)
def fresh_probe():
    global PROBE
    PROBE = Probe()
    yield
    PROBE.release.set()


def echo(inputs, settings, context):
    PROBE.calls.append(("echo", inputs["value"]))
    return {"value": inputs["value"]}


def blocked(inputs, settings, context):
    PROBE.blocked_starts += 1
    PROBE.entered.set()
    assert PROBE.release.wait(2), "test.release_timeout"
    return {"value": inputs["value"]}


def write_after_release(inputs, settings, context):
    def action():
        PROBE.entered.set()
        assert PROBE.release.wait(2), "test.release_timeout"
        PROBE.calls.append(("committed", inputs["value"]))
        if settings.get("lose_acknowledgement"):
            raise OSError("Acknowledgement was lost after physical mutation")
        return "stored"
    context.effect("storage.write", "blocked-write", action, resource="fixture.file")
    return {"value": inputs["value"]}


def close_from_worker(inputs, settings, context):
    context.service.close(wait=True)
    PROBE.worker_close_returned.set()
    return {"value": inputs["value"]}


def command(method="echo", *, effects=(), settings=None):
    return BoundCommand("command.test.drain." + method, MethodRef(__name__ + ":" + method),
        settings or {}, {"value": PortContract("number", int)},
        {"value": PortContract("number", int)}, resources={"cpu": 1},
        effects=frozenset(effects), reuse=ReuseContract(shareable=False, completed=False))


def plan(*tasks):
    return PreparedPlan("service.drain.regression", tuple(tasks), (),
        {"value": ValueRef(tasks[-1].task_id)}, "service.drain.regression", "test-build")


def one(name="work", value=1):
    return plan(CommandTask(name, command(), {"value": value}))


def eventually(predicate, timeout=1):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if predicate():
            return
        sleep(.002)
    assert predicate()


def stop(service):
    """Every test releases fixture IO before waiting for service termination."""
    PROBE.release.set()
    service.close(wait=False)
    assert service.wait_closed(2), "test.service_did_not_close"


def test_idle_service_closes_idempotently_and_rejects_new_admission():
    journal = MemoryJournal()
    service = ExecutionService(journal=journal)
    try:
        assert service.state == "running"
        service.close(wait=False)
        assert service.wait_closed(1)
        assert service.state == "closed"
        before = journal.read()
        with pytest.raises(ExecutionFailure, match="service_closed"):
            service.submit(one())
        assert journal.read() == before
        service.close(wait=False)
        service.close(wait=True)
        assert service.state == "closed"
    finally:
        stop(service)


def test_nonblocking_close_drains_an_accepted_dependency_chain():
    first = CommandTask("first", command("blocked"), {"value": 7})
    second = CommandTask("second", command(), {"value": ValueRef("first")}, ("first",))
    service = ExecutionService(settings=ExecutionSettings(max_workers=1))
    try:
        handle = service.submit(plan(first, second))
        assert PROBE.entered.wait(1)
        service.close(wait=False)
        assert service.state == "draining"
        assert not service.wait_closed(.02)
        assert not handle.done()
        with pytest.raises(ExecutionFailure, match="service_closed"):
            service.submit(one("late"))
        # Repeated close does not shut the executor down ahead of the dependency.
        service.close(wait=False)
        PROBE.release.set()
        result = handle.result(2)
        assert result.outcome == "succeeded", result.diagnostics
        assert result.output() == 7
        assert PROBE.calls == [("echo", 7)]
        assert service.wait_closed(1) and service.state == "closed"
        assert handle.snapshot()["tasks"] == {"first": "succeeded", "second": "succeeded"}
    finally:
        stop(service)


def exercise_worker_close():
    """Run in a subprocess so a regressed self-join cannot strand pytest itself."""
    service = ExecutionService(settings=ExecutionSettings(max_workers=1))
    try:
        first = CommandTask("close", command("close_from_worker"), {"value": 11})
        second = CommandTask("dependent", command(), {"value": ValueRef("close")}, ("close",))
        result = service.submit(plan(first, second)).result(2)
        assert PROBE.worker_close_returned.is_set()
        assert result.outcome == "succeeded", result.diagnostics
        assert result.output() == 11
        assert PROBE.calls == [("echo", 11)]
        assert service.wait_closed(1) and service.state == "closed"
    finally:
        service.close(wait=False)


def test_close_wait_from_a_worker_requests_drain_without_self_deadlock():
    code = ("import sys; sys.path.insert(0, " + repr(str(Path(__file__).parent)) + "); "
        "from test_service_failure_drain import exercise_worker_close; exercise_worker_close()")
    completed = subprocess.run([sys.executable, "-c", code], capture_output=True,
        text=True, timeout=3)
    assert completed.returncode == 0, completed.stdout + completed.stderr


class FailingStartJournal(MemoryJournal):
    fail_next_start = False

    def append(self, **kwargs):
        if kwargs["kind"] == "run.started" and self.fail_next_start:
            self.fail_next_start = False
            raise RuntimeError("Injected coordinator journal failure")
        return super().append(**kwargs)


@pytest.mark.parametrize("lose_acknowledgement", [False, True])
@pytest.mark.parametrize("failure_source", ["journal", "readiness"])
def test_failure_rejects_new_work_but_waits_for_physical_mutation_truth(
        monkeypatch, lose_acknowledgement, failure_source):
    journal = FailingStartJournal()
    service = ExecutionService(settings=ExecutionSettings(max_workers=2), journal=journal)
    try:
        writer = command("write_after_release", effects=("storage.write",),
            settings={"lose_acknowledgement": lose_acknowledgement})
        writing = service.submit(plan(CommandTask("write", writer, {"value": 23})))
        assert PROBE.entered.wait(1)
        if failure_source == "journal":
            journal.fail_next_start = True
        else:
            ready = service._ready
            def failed_ready(run, task):
                if task.spec.task_id == "coordinator-fault":
                    raise RuntimeError("Injected coordinator readiness failure")
                return ready(run, task)
            monkeypatch.setattr(service, "_ready", failed_ready)
        failing = service.submit(one("coordinator-fault"))
        eventually(lambda: service.state == "failed")
        assert service.failure is not None
        assert not writing.done(), "Physical work was finalized before its acknowledgement"
        assert not service.wait_closed(.02)
        before = journal.read()
        with pytest.raises(ExecutionFailure, match="service_failed"):
            service.submit(one("rejected-after-failure"))
        assert journal.read() == before
        service.close(wait=False)
        service.close(wait=False)
        assert service.state == "failed"
        PROBE.release.set()
        result = writing.result(2)
        expected = "unknown" if lose_acknowledgement else "failed"
        assert result.outcome == expected, result.diagnostics
        assert not result.outputs
        receipt = result.effects["blocked-write"]
        assert receipt.status == ("unknown" if lose_acknowledgement else "confirmed")
        assert service.lookup_effect(receipt.effect_id) == receipt
        assert PROBE.calls == [("committed", 23)]
        assert failing.result(2).outcome == "failed"
        assert service.wait_closed(1) and service.state == "failed"
        # Resource occupancy is an internal invariant after every physical future settles.
        assert all(amount == 0 for amount in service._used.values())
        assert all(state not in {"pending", "running", "waiting_shared", "expanding"}
            for state in writing.snapshot()["tasks"].values())
        service.close(wait=True)
    finally:
        stop(service)


def test_failure_before_dispatch_is_structured_and_admission_stays_closed():
    journal = FailingStartJournal()
    journal.fail_next_start = True
    service = ExecutionService(journal=journal)
    try:
        result = service.submit(one()).result(2)
        assert result.outcome == "failed" and not result.effects
        assert not PROBE.calls
        assert service.wait_closed(1) and service.state == "failed"
        assert "execution.coordinator_failed" in result.diagnostics
        with pytest.raises(ExecutionFailure, match="service_failed"):
            service.submit(one("after-failure"))
    finally:
        stop(service)


def test_async_cancel_keeps_the_worker_owned_until_noncooperative_work_returns():
    first = CommandTask("blocked", command("blocked"), {"value": 31})
    second = CommandTask("never-started", command(), {"value": ValueRef("blocked")}, ("blocked",))
    service = ExecutionService(settings=ExecutionSettings(max_workers=1))
    try:
        handle = service.submit(plan(first, second))
        assert PROBE.entered.wait(1)
        service.close(wait=False, cancel=True)
        assert service.state == "draining" and not service.wait_closed(.02)
        assert not handle.done()
        PROBE.release.set()
        result = handle.result(2)
        assert result.outcome == "cancelled", result.diagnostics
        assert not PROBE.calls and not result.effects
        assert service.wait_closed(1) and service.state == "closed"
        assert all(amount == 0 for amount in service._used.values())
    finally:
        stop(service)


def test_failed_service_preserves_a_previously_completed_result_owner():
    journal = FailingStartJournal()
    service = ExecutionService(journal=journal)
    try:
        completed = service.run(one("completed", 41))
        assert completed.outcome == "succeeded" and completed.output() == 41
        journal.fail_next_start = True
        failed = service.submit(one("fault")).result(2)
        assert failed.outcome == "failed"
        assert service.wait_closed(1) and service.state == "failed"
        assert completed.outcome == "succeeded" and completed.output() == 41
        completed.close()
        assert not completed.outputs
    finally:
        stop(service)


def test_failure_drains_a_shared_physical_future_and_releases_its_claim_once(monkeypatch):
    service = ExecutionService(settings=ExecutionSettings(max_workers=1))
    try:
        shared = replace(command("blocked"), reuse=ReuseContract(shareable=True, completed=False))
        shared_plan = plan(CommandTask("shared", shared, {"value": 53}))
        first = service.submit(shared_plan)
        assert PROBE.entered.wait(1)
        second = service.submit(shared_plan)
        eventually(lambda: any(fact.kind == "work.joined" and fact.run_id == second.run_id
            for fact in service.journal.read()))
        ready = service._ready
        def failed_ready(run, task):
            if task.spec.task_id == "coordinator-fault":
                raise RuntimeError("Injected coordinator readiness failure")
            return ready(run, task)
        monkeypatch.setattr(service, "_ready", failed_ready)
        failing = service.submit(one("coordinator-fault"))
        eventually(lambda: service.state == "failed")
        assert not first.done() and not second.done()
        PROBE.release.set()
        assert first.result(2).outcome == second.result(2).outcome == "failed"
        assert failing.result(2).outcome == "failed"
        assert service.wait_closed(1) and PROBE.blocked_starts == 1
        assert all(amount == 0 for amount in service._used.values())
    finally:
        stop(service)
