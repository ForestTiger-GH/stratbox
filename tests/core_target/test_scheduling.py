"""Shared work, deadlines, fair admission and bounded retained state."""
from concurrent.futures import TimeoutError
from dataclasses import dataclass, field, replace
from threading import Event, Lock
from time import monotonic, sleep

import pytest

from stratbox.capabilities.model import MethodRef, PortContract, ReuseContract
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, MapTask, PreparedPlan, TemplateInput, ValueRef
from stratbox.core.execution.service import ExecutionFailure, ExecutionService, ExecutionSettings
from stratbox.core.limits import ExecutionBudget
from stratbox.core.observability.journal.stream import MemoryJournal
from stratbox.shared.data.values import Material, RequestSpec


@dataclass
class Probe:
    entered: Event = field(default_factory=Event)
    release: Event = field(default_factory=Event)
    calls: int = 0
    active: int = 0
    peak: int = 0


PROBES = {}
ORDER = []
LOCK = Lock()


@pytest.fixture(autouse=True)
def isolated_probes():
    PROBES.clear()
    ORDER.clear()
    yield
    for probe in PROBES.values():
        probe.release.set()


def probe(name):
    return PROBES.setdefault(name, Probe())


def blocked(inputs, settings, context):
    state = probe(settings["probe"])
    with LOCK:
        state.calls += 1
        state.active += 1
        state.peak = max(state.peak, state.active)
    state.entered.set()
    try:
        while not state.release.wait(.002):
            if settings.get("cooperative", True):
                context.checkpoint()
        return {"value": inputs["value"]}
    finally:
        with LOCK:
            state.active -= 1


def echo(inputs, settings, context):
    with LOCK:
        ORDER.append(inputs["value"])
    sleep(settings.get("delay", 0))
    return {"value": inputs["value"]}


def budgeted(inputs, settings, context):
    context.spend("objects", 1)
    with LOCK:
        ORDER.append(inputs["value"])
    return {"value": inputs["value"]}


def bytes_result(inputs, settings, context):
    return {"value": b"x" * settings["size"]}


def command(method="echo", *, settings=None, resources=None, reuse=None, outputs=None):
    return BoundCommand("command.test." + method, MethodRef(__name__ + ":" + method), settings or {},
        {"value": PortContract("number", int)}, outputs or {"value": PortContract("number", int)},
        resources=resources or {"cpu": 1}, reuse=reuse or ReuseContract(shareable=False))


def plan(tasks, outputs=None):
    return PreparedPlan("scheduler.regression", tuple(tasks), (), outputs or {"value": ValueRef(tasks[-1].task_id)},
        "scheduler.regression", "test-build")


def one(name, *, value=1, method="blocked", resources=None, cooperative=True, reusable=False):
    settings = {"probe": name, "cooperative": cooperative} if method == "blocked" else {}
    work = command(method, settings=settings, resources=resources,
        reuse=ReuseContract(shareable=reusable, completed=False))
    return plan((CommandTask(name, work, {"value": value}),))


def eventually(predicate, seconds=2):
    deadline = monotonic() + seconds
    while monotonic() < deadline:
        if predicate():
            return
        sleep(.002)
    assert predicate()


def wait_ticket(handle, task_id):
    return handle._run.tasks[task_id].wait_ticket


def facts(service, run_id=None):
    return service.journal.read(limit=min(1000, getattr(service.journal, "capacity", 1000)), run_id=run_id)


def test_wait_timeout_does_not_cancel_work_or_release_its_occupied_worker():
    state = probe("held")
    with ExecutionService(settings=ExecutionSettings(max_workers=1)) as service:
        try:
            held = service.submit(one("held"))
            assert state.entered.wait(2)
            with pytest.raises(TimeoutError):
                held.result(.01)
            queued = service.submit(one("quick", value=2, method="echo"))
            sleep(.03)
            assert not held.done() and not queued.done()
            assert state.active == 1
        finally:
            state.release.set()
        assert held.result(2).output() == 1
        assert queued.result(2).output() == 2


def test_cooperative_execution_deadline_cancels_without_a_subscriber():
    state = probe("deadline")
    with ExecutionService(settings=ExecutionSettings(max_workers=1)) as service:
        handle = service.submit(one("deadline"), timeout=.05)
        assert state.entered.wait(2)
        result = handle.result(2)
        assert result.outcome == "cancelled" and not result.outputs
        assert state.active == 0
        assert service.run(one("next", method="echo"), timeout=2).outcome == "succeeded"


def test_deadline_keeps_the_worker_owned_until_noncooperative_physical_work_returns():
    state = probe("physical")
    with ExecutionService(settings=ExecutionSettings(max_workers=1)) as service:
        try:
            handle = service.submit(one("physical", cooperative=False), timeout=.03)
            assert state.entered.wait(2)
            queued = service.submit(one("next", method="echo"))
            sleep(.07)
            assert not handle.done() and not queued.done()
            assert state.active == 1
        finally:
            state.release.set()
        assert handle.result(2).outcome == "cancelled"
        assert queued.result(2).outcome == "succeeded"


def test_cancelled_producer_consumer_preserves_shared_follower_and_spare_worker():
    state = probe("shared")
    with ExecutionService(settings=ExecutionSettings(max_workers=2, capacities={"cpu": 1, "network": 1})) as service:
        try:
            producer = service.submit(one("shared", reusable=True))
            assert state.entered.wait(2)
            follower = service.submit(one("shared", reusable=True))
            eventually(lambda: "waiting_shared" in follower.snapshot()["tasks"].values())
            independent = service.submit(one("independent", method="echo", resources={"network": 1}))
            assert independent.result(1).outcome == "succeeded"
            assert producer.cancel()
            assert state.calls == 1
        finally:
            state.release.set()
        assert producer.result(2).outcome == "cancelled"
        assert follower.result(2).output() == 1
        assert state.calls == 1
        starts = [fact for fact in facts(service) if fact.kind == "work.started" and fact.command_id == "command.test.blocked"]
        joined = [fact for fact in facts(service) if fact.kind == "work.joined"]
        assert len(starts) == len(joined) == 1
        assert starts[0].physical_work_id == joined[0].physical_work_id


def test_deadline_of_one_shared_consumer_does_not_cancel_another_consumer():
    state = probe("shared_deadline")
    with ExecutionService(settings=ExecutionSettings(max_workers=1)) as service:
        try:
            producer = service.submit(one("shared_deadline", reusable=True), timeout=.06)
            assert state.entered.wait(2)
            follower = service.submit(one("shared_deadline", reusable=True))
            eventually(lambda: "waiting_shared" in follower.snapshot()["tasks"].values())
            sleep(.09)
            assert not follower.done(), "A different consumer's deadline cancelled the shared producer"
        finally:
            state.release.set()
        assert producer.result(2).outcome == "cancelled"
        assert follower.result(2).outcome == "succeeded"
        assert state.calls == 1


def test_oldest_conflicting_claim_keeps_priority_while_independent_capacity_is_useful():
    occupying, large, independent = probe("occupying"), probe("large"), probe("independent")
    with ExecutionService(settings=ExecutionSettings(max_workers=3, capacities={"cpu": 2, "network": 1})) as service:
        try:
            occupied = service.submit(one("occupying", resources={"cpu": 1}))
            assert occupying.entered.wait(2)
            older = service.submit(one("large", resources={"cpu": 2}))
            eventually(lambda: wait_ticket(older, "large") is not None)
            younger = service.submit(one("younger", method="echo", resources={"cpu": 1}))
            preview = service.submit(one("independent", resources={"network": 1}))
            assert independent.entered.wait(.5), "A queued CPU claim blocked free network/worker capacity"
            assert not large.entered.is_set()
            independent.release.set()
            assert preview.result(2).outcome == "succeeded"
            occupying.release.set()
            assert large.entered.wait(2)
            assert not younger.done()
        finally:
            occupying.release.set()
            large.release.set()
            independent.release.set()
        assert occupied.result(2).outcome == older.result(2).outcome == younger.result(2).outcome == "succeeded"


def test_cancellation_releases_a_waiters_reservation_for_a_younger_claim():
    occupying, large, small = probe("occupying"), probe("large"), probe("small")
    with ExecutionService(settings=ExecutionSettings(max_workers=3, capacities={"cpu": 2})) as service:
        try:
            occupied = service.submit(one("occupying", resources={"cpu": 1}))
            assert occupying.entered.wait(2)
            older = service.submit(one("large", resources={"cpu": 2}))
            eventually(lambda: wait_ticket(older, "large") is not None)
            younger = service.submit(one("small", resources={"cpu": 1}))
            eventually(lambda: wait_ticket(younger, "small") is not None)
            assert older.cancel()
            assert small.entered.wait(1)
            assert not large.entered.is_set()
        finally:
            occupying.release.set()
            small.release.set()
            large.release.set()
        assert older.result(2).outcome == "cancelled"
        assert occupied.result(2).outcome == younger.result(2).outcome == "succeeded"


def test_two_waiters_make_progress_in_ticket_order_after_capacity_frees():
    occupying, large, small = probe("occupying"), probe("large"), probe("small")
    with ExecutionService(settings=ExecutionSettings(max_workers=3, capacities={"cpu": 2})) as service:
        try:
            occupied = service.submit(one("occupying", resources={"cpu": 1}))
            assert occupying.entered.wait(2)
            older = service.submit(one("large", resources={"cpu": 2}))
            eventually(lambda: wait_ticket(older, "large") is not None)
            younger = service.submit(one("small", resources={"cpu": 1}))
            eventually(lambda: wait_ticket(younger, "small") is not None)
            occupying.release.set()
            assert large.entered.wait(1)
            assert not small.entered.is_set()
            large.release.set()
            assert small.entered.wait(1)
        finally:
            occupying.release.set()
            large.release.set()
            small.release.set()
        assert occupied.result(2).outcome == older.result(2).outcome == younger.result(2).outcome == "succeeded"


def test_fair_rounds_run_a_small_call_before_a_large_call_finishes():
    work = command(settings={"delay": .005})
    large_plan = plan(tuple(CommandTask("item" + str(i), work, {"value": i}) for i in range(30)))
    with ExecutionService(settings=ExecutionSettings(max_workers=1)) as service:
        large = service.submit(large_plan)
        small = service.submit(one("quick", value=100, method="echo"))
        assert small.result(2).output() == 100
        assert not large.done()
        assert large.result(3).outcome == "succeeded"


def test_map_window_bounds_live_chains_and_keeps_input_order_with_one_worker():
    state = probe("mapped")
    first = command("blocked", settings={"probe": "mapped"})
    template = plan((CommandTask("first", first, {"value": TemplateInput("item")}),
        CommandTask("second", command(), {"value": ValueRef("first")}, ("first",))))
    mapped = MapTask("map", template, tuple(range(20)), window=2, item_output="value")
    with ExecutionService(settings=ExecutionSettings(max_workers=1, active_runs=1)) as service:
        try:
            handle = service.submit(plan((mapped,), {"values": ValueRef("map", "items")}))
            assert state.entered.wait(2)
            eventually(lambda: len(handle.snapshot()["tasks"]) >= 5)
            assert len(handle.snapshot()["tasks"]) == 5
            assert state.calls == 1
        finally:
            state.release.set()
        result = handle.result(3)
        assert result.outcome == "succeeded" and result.output("values") == tuple(range(20))


def test_nested_maps_share_one_worker_without_recursive_deadlock():
    leaf = plan((CommandTask("echo", command(), {"value": TemplateInput("item")}),))
    inner = MapTask("inner", leaf, TemplateInput("group"), window=1, item_output="value")
    branch = plan((inner,), {"value": ValueRef("inner", "items")})
    outer = MapTask("outer", branch, ((1, 2), (3, 4)), item_input="group", item_output="value", window=1)
    with ExecutionService(settings=ExecutionSettings(max_workers=1, active_runs=1)) as service:
        result = service.run(plan((outer,), {"values": ValueRef("outer", "items")}), timeout=3)
        assert result.outcome == "succeeded", result.diagnostics
        assert result.output("values") == ((1, 2), (3, 4))


def test_run_budget_is_shared_by_sibling_work_and_a_new_run_has_its_own_budget():
    work = command("budgeted")
    three = plan(tuple(CommandTask("item" + str(i), work, {"value": i}) for i in range(3)))
    with ExecutionService(settings=ExecutionSettings(max_workers=1, run_limits=ExecutionBudget(objects=2))) as service:
        first = service.run(three, timeout=3)
        assert first.outcome == "failed" and "budget.objects" in first.diagnostics
        assert ORDER == [0, 1]
        second = service.run(plan((CommandTask("new", work, {"value": 9}),)), timeout=3)
        assert second.outcome == "succeeded" and second.output() == 9


def test_live_retained_output_fails_new_admission_promptly_then_close_releases_capacity():
    work = command("bytes_result", settings={"size": 600}, outputs={"value": PortContract("bytes", bytes)})
    task = plan((CommandTask("bytes", work, {"value": 1}),))
    with ExecutionService(settings=ExecutionSettings(max_workers=1, max_retained_bytes=1100)) as service:
        first = service.run(task, timeout=2)
        assert first.outcome == "succeeded", first.diagnostics
        retained_value = first.output()
        second = service.run(task, timeout=2)
        assert second.outcome == "failed" and "value.retention_capacity_exhausted" in second.diagnostics
        first.close()
        assert retained_value == b"x" * 600
        with pytest.raises(ExecutionFailure, match="result_closed"):
            first.output()
        third = service.run(task, timeout=2)
        assert third.outcome == "succeeded", third.diagnostics


def test_completed_reuse_has_its_own_owner_after_a_callers_result_is_closed():
    state = probe("cached")
    state.release.set()
    work = command("blocked", settings={"probe": "cached"}, reuse=ReuseContract())
    request = plan((CommandTask("cached", work, {"value": 7}),))
    with ExecutionService() as service:
        first = service.run(request, timeout=2)
        assert first.output() == 7 and state.calls == 1
        first.close()
        assert service._retained_bytes == 0 and service._cache_bytes > 0
        second = service.run(request, timeout=2)
        assert second.output() == 7 and state.calls == 1
        assert any(fact.kind == "work.reused" for fact in facts(service, second.run_id))
        second.close()
        assert service._retained_bytes == 0 and service._cache_bytes > 0
    assert service._cache_bytes == 0


def test_invalid_resource_claim_is_rejected_without_mutating_existing_runs_or_facts():
    state = probe("active")
    with ExecutionService(settings=ExecutionSettings(max_workers=1, capacities={"cpu": 1})) as service:
        try:
            active = service.submit(one("active"))
            assert state.entered.wait(2)
            before_runs = tuple(service._runs)
            before_facts = tuple(facts(service))
            invalid = one("impossible", method="echo", resources={"cpu": 999})
            with pytest.raises(ExecutionFailure, match="impossible_claim"):
                service.submit(invalid)
            assert tuple(service._runs) == before_runs
            assert tuple(facts(service)) == before_facts
        finally:
            state.release.set()
        assert active.result(2).outcome == "succeeded"


def test_full_journal_fails_boundedly_and_does_not_leak_a_worker_reservation():
    journal = MemoryJournal(capacity=2)
    with ExecutionService(settings=ExecutionSettings(max_workers=1), journal=journal) as service:
        handle = service.submit(one("never_started", method="echo"))
        result=handle.result(2)
        assert result.outcome=='failed' and not result.outputs
        assert 'execution.coordinator_failed' in result.diagnostics
        assert [fact.kind for fact in journal.read(limit=2)] == ["run.admitted", "run.started"]
        assert ORDER == []
        assert all(amount == 0 for amount in service._used.values())


def test_full_journal_rejects_admission_without_adding_an_unreported_run():
    journal = MemoryJournal(capacity=1)
    journal.append(kind="retained.fact", run_id="previous")
    with ExecutionService(settings=ExecutionSettings(max_workers=1), journal=journal) as service:
        with pytest.raises(RuntimeError, match="journal.capacity_exhausted"):
            service.submit(one("unreported", method="echo"))
        assert not service._runs and not service._order
        assert [fact.kind for fact in journal.read(limit=1)] == ["retained.fact"]
        assert ORDER == []


class ControlledHTTP:
    def __init__(self, data):
        self.data, self.calls, self.entered, self.release = data, 0, Event(), Event()

    def fetch(self, request):
        self.calls += 1
        self.entered.set()
        assert self.release.wait(2)
        return Material(self.data, source_id=request.source_id)


def http_plan(request):
    work = BoundCommand("command.material.fetch", MethodRef("stratbox.core.commands.materials:material_fetch"), None,
        {"request": PortContract("request", RequestSpec)}, {"material": PortContract("material", Material),
        "evidence": PortContract("evidence"),"request":PortContract("request",RequestSpec)}, resources={"network": 1}, effects=frozenset({"network.read"}),
        required_providers=frozenset({"http"}),
        reuse=ReuseContract(deterministic=False, completed=False, observation_scoped=True))
    return plan((CommandTask("fetch", work, {"request": request}),), {"material": ValueRef("fetch", "material")})


def test_shared_http_has_one_physical_transfer_and_budget_charge_with_distinct_consumer_context():
    data = b"abcdefgh" * 65536
    provider = ControlledHTTP(data)
    first_request = RequestSpec("https://fixture.example/data", source_id="source.A", observation_id="same-observation", max_bytes=len(data))
    second_request = replace(first_request, source_id="source.B")
    settings = ExecutionSettings(max_workers=2, run_limits=ExecutionBudget(requests=1, wire_bytes=len(data)))
    with ExecutionService(settings=settings, providers={"http": provider}) as service:
        try:
            first = service.submit(http_plan(first_request))
            assert provider.entered.wait(2)
            second = service.submit(http_plan(second_request))
            eventually(lambda: "waiting_shared" in second.snapshot()["tasks"].values())
        finally:
            provider.release.set()
        left, right = first.result(2), second.result(2)
        assert left.outcome == right.outcome == "succeeded"
        assert left.output("material").data == right.output("material").data == data
        assert left.output("material").source_id == "source.A"
        assert right.output("material").source_id == "source.B"
        assert provider.calls == 1
        assert sum(handle._run.meter.used("requests") for handle in (first, second)) == 1
        assert sum(handle._run.meter.used("wire_bytes") for handle in (first, second)) == len(data)


def test_response_over_byte_limit_is_never_admitted_as_partial_material():
    provider = ControlledHTTP(b"exceeds")
    provider.release.set()
    request = RequestSpec("https://fixture.example/data", max_bytes=3)
    with ExecutionService(providers={"http": provider}) as service:
        result = service.run(http_plan(request), timeout=2)
        assert result.outcome == "failed" and "http.response_limit" in result.diagnostics
        assert not result.outputs and provider.calls == 1
