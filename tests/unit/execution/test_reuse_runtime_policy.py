"""The real executor honors completed reuse and each consumer's ancestry."""
from threading import Event
from time import monotonic, sleep

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import CommandDefinition, PortContract, ReuseContract
from stratbox.core.execution.handoff import PreparedInput
from stratbox.core.execution.session import ExecutionSettings
from stratbox.sdk import StrategyBox
from stratbox.shared.data.processing import DataContract
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity


class Probe:
    calls = 0
    entered = Event()
    release = Event()


def produce(request, invocation):
    Probe.calls += 1
    Probe.entered.set()
    while not Probe.release.wait(.002):
        invocation.check_cancelled()
    return request.get("material", request.get("value", 3))


def catalog(*, completed=True, supplied=False):
    contract = DataContract("reuse.material")
    return CatalogSnapshot(definitions=(CommandDefinition("reuse.produce", __name__ + ":produce",
        inputs={"material": PortContract(contract, bytes)} if supplied else {},
        parameters={} if supplied else {"value": 3},
        outputs={"value": PortContract(contract if supplied else DataContract("reuse.number"), bytes if supplied else int)},
        reuse=ReuseContract(completed=completed)),))


def reset(*, blocked=False):
    Probe.calls = 0
    Probe.entered.clear()
    Probe.release.clear() if blocked else Probe.release.set()


def test_completed_false_executes_again_after_the_first_producer_is_done():
    reset()
    with StrategyBox(capabilities=catalog(completed=False)) as box:
        first = box.invoke("reuse.produce")
        second = box.invoke("reuse.produce")
        assert Probe.calls == 2
        assert first.output("value") == second.output("value") == 3
        first.close(); second.close()


def test_completed_false_still_joins_an_inflight_producer_with_one_worker():
    reset(blocked=True)
    with StrategyBox(capabilities=catalog(completed=False),
                     settings=ExecutionSettings(max_workers=1, active_runs=2)) as box:
        first = box.submit(box.prepare("reuse.produce"))
        try:
            assert Probe.entered.wait(3)
            second = box.submit(box.prepare("reuse.produce"))
            until = monotonic() + 3
            while monotonic() < until and second.snapshot().tasks[0].state != "shared_wait":
                sleep(.002)
            assert second.snapshot().tasks[0].state == "shared_wait"
        finally:
            Probe.release.set()
        a, b = first.result(3), second.result(3)
        assert a.output("value") == b.output("value") == 3
        assert Probe.calls == 1
        a.close(); b.close()


def test_same_bytes_do_not_reuse_another_consumers_source_evidence():
    reset()
    content = b"equal bytes"
    contract = DataContract("reuse.material")
    def supplied(source):
        return PreparedInput(contract, content, used_inputs=(UsedInputReceipt(
            "source", ByteIdentity.of(content), "application/octet-stream", "inline", source),))
    with StrategyBox(capabilities=catalog(supplied=True)) as box:
        first = box.invoke("reuse.produce", inputs={"material": supplied("source.a")})
        second = box.invoke("reuse.produce", inputs={"material": supplied("source.b")})
        assert Probe.calls == 2
        assert first.output("value") == second.output("value") == content
        receipts = {receipt.source_id for result in second.results.values() for receipt in result.used_inputs}
        assert "source.b" in receipts and "source.a" not in receipts
        first.close(); second.close()
