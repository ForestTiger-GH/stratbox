"""Every shared or cached consumer retains its own logical byte obligations."""
from dataclasses import replace
from threading import Event
from time import monotonic, sleep

import pytest

from stratbox.capabilities.model import MethodRef, PortContract, ReuseContract
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, PreparedPlan, ValueRef
from stratbox.core.execution.service import ExecutionService, ExecutionSettings
from stratbox.core.limits import ExecutionBudget
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.materials import StagedMaterialRef
from stratbox.shared.data.values import ImmutableMaterialRef, Material


ENTERED, RELEASE = Event(), Event()
CALLS = []
PAYLOAD_SIZE = 32768


@pytest.fixture(autouse=True)
def isolated_gate():
    ENTERED.clear()
    RELEASE.clear()
    CALLS.clear()
    yield
    RELEASE.set()


def boundary_value(inputs, settings, context):
    CALLS.append(settings["kind"])
    if settings.get("gated"):
        ENTERED.set()
        while not RELEASE.wait(.002):
            context.checkpoint()
    if settings["kind"] in {"read", "buffered_read", "retained_read"}:
        with context.open_material(inputs["material"]) as stream:
            return {"value": len(stream.read(1))}
    if settings["kind"] == "stage":
        with context.stage() as writer:
            writer.write(b"x" * PAYLOAD_SIZE)
            return {"value": writer.seal()}
    return {"value": b"x" * PAYLOAD_SIZE}


def prefix(inputs, settings, context):
    return {"value": b"p" * settings.get("size", 0)}


def command(kind, *, gated=False):
    return BoundCommand("command.test.reused_boundary", MethodRef(__name__ + ":boundary_value"),
        {"kind": kind, "gated": gated},
        {"material": PortContract("retained", ImmutableMaterialRef),
         "alias": PortContract("retained", ImmutableMaterialRef, required=False)} if kind == "retained_read" else
        {"material": PortContract("staged", StagedMaterialRef)} if kind == "read" else
        {"material": PortContract("material", Material)} if kind == "buffered_read" else {},
        {"value": PortContract("value")}, reuse=ReuseContract(), resources={"cpu": 1},
        required_providers=frozenset({"filestore"}) if kind == "retained_read" else frozenset())


def plan(tasks, outputs=None):
    return PreparedPlan("reused.boundary", tuple(tasks), (),
        outputs or {"value": ValueRef(tasks[-1].task_id)}, "reused.boundary", "test")


def prefix_task(resource):
    work = BoundCommand("command.test.boundary_prefix", MethodRef(__name__ + ":prefix"),
        {"size": 50000 if resource == "output_bytes" else 0},
        {"payload": PortContract("bytes", bytes)} if resource == "input_bytes" else {},
        {"value": PortContract("bytes", bytes)}, reuse=ReuseContract(shareable=False), resources={"cpu": 1})
    return CommandTask("prefix", work, {"payload": b"p" * 50000} if resource == "input_bytes" else {})


def wait_for_shared(handle, task_id="work"):
    until = monotonic() + 3
    while monotonic() < until:
        if handle.snapshot()["tasks"].get(task_id) == "waiting_shared":
            return
        if handle.done():
            pytest.fail("Consumer settled before joining the controlled producer")
        sleep(.002)
    pytest.fail("Consumer did not join the controlled producer")


@pytest.mark.parametrize("resource", ["input_bytes", "output_bytes"])
def test_shared_stage_consumer_cannot_bypass_its_cumulative_boundary_limit(resource):
    limits = ExecutionBudget(**{resource: 80000})
    with ExecutionService(settings=ExecutionSettings(run_limits=limits)) as service:
        original = None
        if resource == "input_bytes":
            original = service.run(plan((CommandTask("original", command("stage"), {}),)))
            assert original.outcome == "succeeded"
            inputs = {"material": original.output()}
            work = command("read", gated=True)
        else:
            inputs, work = {}, command("stage", gated=True)
        first = service.submit(plan((CommandTask("work", work, inputs),)))
        try:
            assert ENTERED.wait(3)
            second = service.submit(plan((prefix_task(resource),
                CommandTask("work", work, inputs, deps=("prefix",)))))
            wait_for_shared(second)
        finally:
            RELEASE.set()
        with first.result(3) as producer, second.result(3) as consumer:
            assert producer.outcome == "succeeded", producer.diagnostics
            assert consumer.outcome == "failed"
            assert "budget." + resource in consumer.diagnostics
            assert "execution.coordinator_failed" not in consumer.diagnostics
            assert not consumer.outputs
            assert consumer.resources.get("temporary_bytes", 0) == 0
        if original is not None:
            original.close()
        assert service.staging.status()["objects"] == 0


@pytest.mark.parametrize("resource", ["input_bytes", "output_bytes"])
def test_cached_boundary_is_charged_again_and_cannot_bypass_consumer_budget(resource):
    with ExecutionService(settings=ExecutionSettings(run_limits=ExecutionBudget(**{resource: 80000}))) as service:
        kind = "buffered_read" if resource == "input_bytes" else "buffered"
        inputs = {"material": Material(b"x" * PAYLOAD_SIZE)} if resource == "input_bytes" else {}
        work = command(kind)
        with service.run(plan((CommandTask("work", work, inputs),))) as initial:
            assert initial.outcome == "succeeded"
        with service.run(plan((prefix_task(resource),
                CommandTask("work", work, inputs, deps=("prefix",))))) as reused:
            assert reused.outcome == "failed"
            assert "budget." + resource in reused.diagnostics
            assert not reused.outputs
        assert CALLS == [kind]
        with service.run(plan((CommandTask("work", work, inputs),))) as fresh_run:
            assert fresh_run.outcome == "succeeded"
            assert fresh_run.resources[resource] >= PAYLOAD_SIZE


@pytest.mark.parametrize("reuse", ["producer", "shared", "cached"])
def test_retained_body_size_counts_for_every_logical_input_boundary(tmp_path, reuse):
    settings = ExecutionSettings(run_limits=ExecutionBudget(input_bytes=80000))
    with StrategyBox(providers={"filestore": LocalFileStore(tmp_path)}, settings=settings) as box:
        with box.invoke("command.artifact.commit", inputs={"material": Material(b"x" * PAYLOAD_SIZE),
                "destination": "objects"}) as retained:
            assert retained.outcome == "succeeded", retained.diagnostics
            reference = retained.output("reference")
        service = box.session
        work = command("retained_read", gated=reuse == "shared")
        inputs = {"material": reference}
        first = None
        if reuse != "producer":
            first = service.submit(plan((CommandTask("work", work, inputs),)))
            if reuse == "shared":
                assert ENTERED.wait(3)
            else:
                with first.result(3) as result:
                    assert result.outcome == "succeeded", result.diagnostics
                    assert result.resources["input_bytes"] >= PAYLOAD_SIZE
        try:
            second = service.submit(plan((prefix_task("input_bytes"),
                CommandTask("work", work, inputs, deps=("prefix",)))))
            if reuse == "shared":
                wait_for_shared(second)
        finally:
            RELEASE.set()
        with second.result(3) as rejected:
            assert rejected.outcome == "failed"
            assert "budget.input_bytes" in rejected.diagnostics
            assert not rejected.outputs
        if reuse == "shared":
            with first.result(3) as result:
                assert result.outcome == "succeeded", result.diagnostics
        assert CALLS == ([] if reuse == "producer" else ["retained_read"])


def test_compact_aliases_of_one_retained_body_count_once_per_input_boundary(tmp_path):
    with StrategyBox(providers={"filestore": LocalFileStore(tmp_path)}) as box:
        with box.invoke("command.artifact.commit", inputs={"material": Material(b"x" * PAYLOAD_SIZE,
                metadata={"filename": "source.dat"}), "destination": "objects"}) as retained:
            assert retained.outcome == "succeeded", retained.diagnostics
            reference = retained.output("reference")
        alias = replace(reference, metadata={}, lineage=(), source_uses=())
        with box.session.run(plan((CommandTask("work", command("retained_read"),
                {"material": reference, "alias": alias}),))) as result:
            assert result.outcome == "succeeded", result.diagnostics
            assert PAYLOAD_SIZE <= result.resources["input_bytes"] < 2 * PAYLOAD_SIZE
            assert result.resources["output_bytes"] < PAYLOAD_SIZE


def test_two_shared_tasks_in_one_run_charge_two_logical_stage_outputs():
    work = command("stage", gated=True)
    with ExecutionService() as service:
        handle = service.submit(plan((CommandTask("left", work, {}), CommandTask("right", work, {})),
            {"left": ValueRef("left"), "right": ValueRef("right")}))
        try:
            assert ENTERED.wait(3)
            wait_for_shared(handle, "right")
        finally:
            RELEASE.set()
        with handle.result(3) as result:
            assert result.outcome == "succeeded", result.diagnostics
            assert result.output("left") == result.output("right")
            assert result.resources["output_bytes"] >= 2 * PAYLOAD_SIZE
            assert result.resources["temporary_bytes"] == PAYLOAD_SIZE
            assert CALLS == ["stage"]
            assert service.staging.status()["objects"] == 1
        assert service.staging.status()["objects"] == 0


def test_cancelled_producer_releases_its_pins_after_surviving_consumer_accepts_stage():
    work = command("stage", gated=True)
    with ExecutionService() as service:
        first = service.submit(plan((CommandTask("work", work, {}),)))
        try:
            assert ENTERED.wait(3)
            second = service.submit(plan((CommandTask("work", work, {}),)))
            wait_for_shared(second)
            assert first.cancel()
        finally:
            RELEASE.set()
        with first.result(3) as cancelled, second.result(3) as accepted:
            assert cancelled.outcome == "cancelled" and not cancelled.outputs
            assert accepted.outcome == "succeeded", accepted.diagnostics
            assert accepted.resources["output_bytes"] >= PAYLOAD_SIZE
            assert accepted.resources.get("temporary_bytes", 0) == 0
            with service.staging.open(accepted.output()) as stream:
                assert stream.read(4) == b"xxxx"
            assert service.staging.status()["objects"] == 1
        assert service.staging.status()["objects"] == 0
