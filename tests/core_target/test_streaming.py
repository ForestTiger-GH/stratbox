"""Large original retention uses bounded staging and a separately visible read."""
from dataclasses import replace
from datetime import datetime, timezone

from stratbox.core.execution.service import ExecutionSettings
from stratbox.core.limits import ExecutionBudget
from stratbox.core.network.contracts import HttpResponse, HttpStreamResponse
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import RequestSpec
from stratbox.shared.identity import ByteIdentity
from stratbox.core.execution.effect_state import FileEffectState
from contextlib import contextmanager


class StreamingTransport:
    def __init__(self, data): self.data, self.calls = data, 0
    def exchange(self, request): raise AssertionError("Buffered exchange was used")
    def exchange_into(self, request, sink, *, cancelled=None):
        self.calls += 1
        for offset in range(0, len(self.data), 4096):
            assert cancelled is None or not cancelled()
            sink.write(self.data[offset:offset+4096])
        response = HttpResponse(200, b"", {"content-type":"text/csv"}, datetime.now(timezone.utc),
            "https://example.test", wire_size=len(self.data))
        return HttpStreamResponse(response, ByteIdentity.of(self.data))


def test_receive_retains_stream_without_a_buffered_body_then_reads_exact_bytes(tmp_path):
    data = b"source original\n" * 32768
    transport, store = StreamingTransport(data), LocalFileStore(str(tmp_path))
    request = RequestSpec("https://example.test/original.csv", max_bytes=len(data)+1,
        source_id="fixture.source", observation_id="capture", metadata={"issue_id":"2026-11"})
    settings = ExecutionSettings(max_retained_bytes=32768,
        run_limits=ExecutionBudget(requests=1, wire_bytes=len(data), temporary_bytes=len(data)))
    with StrategyBox(providers={"http":transport,"filestore":store},settings=settings) as box:
        received = box.invoke("command.material.receive",inputs={"request":request,"destination":"originals"})
        assert received.outcome == "succeeded", received.diagnostics
        reference = received.output("reference")
        assert reference.identity == ByteIdentity.of(data)
        assert (tmp_path/reference.location).read_bytes() == data
        assert received.resources["requests"] == 1 and received.resources["wire_bytes"] == len(data)
        assert received.resources["temporary_bytes"] == len(data)
        assert received.output("evidence").material_identity == reference.identity
    with StrategyBox(providers={"filestore":store}) as box:
        read = box.invoke("command.material.read",inputs={"location":reference})
        assert read.outcome == "succeeded", read.diagnostics
        assert read.output("material").data == data
        assert read.output("material").metadata["issue_id"] == "2026-11"
        assert read.output("material").metadata["filename"] == "original.csv"
    assert transport.calls == 1


def test_stream_response_limit_rejects_before_immutable_commit(tmp_path):
    transport, store = StreamingTransport(b"x"*10000), LocalFileStore(str(tmp_path))
    with StrategyBox(providers={"http":transport,"filestore":store}) as box:
        result = box.invoke("command.material.receive",inputs={
            "request":RequestSpec("https://example.test/original.csv", max_bytes=9000),"destination":"originals"})
        assert result.outcome != "succeeded" and not result.outputs
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def test_lost_staged_commit_ack_reconciles_after_restart_without_redownload(tmp_path):
    class LostStageAcknowledgement(LocalFileStore):
        @contextmanager
        def stage_content(self, directory):
            with super().stage_content(directory) as stage:
                class Lost:
                    stream = stage.stream
                    location = stage.location
                    def commit(self, identity, **kwargs):
                        stage.commit(identity, **kwargs)
                        raise OSError("Acknowledgement was lost after immutable creation")
                yield Lost()
    transport = StreamingTransport(b"exact streamed source\n"*1000)
    request = RequestSpec("https://example.test/original.csv", observation_id="one-closed-capture")
    def providers():
        return {"http":transport,"filestore":LostStageAcknowledgement(str(tmp_path/"files")),
            "effect_state":FileEffectState(tmp_path/"effects")}
    with StrategyBox(providers=providers()) as box:
        first = box.invoke("command.material.receive",inputs={"request":request,"destination":"originals"})
        assert first.outcome == "unknown"
        receipt, = first.effects.values()
        assert receipt.intent.identity == ByteIdentity.of(transport.data)
    with StrategyBox(providers=providers()) as box:
        again = box.invoke("command.material.receive",inputs={"request":request,"destination":"originals"})
        assert again.outcome == "unknown" and transport.calls == 1
        recovered = box.invoke("command.artifact.reconcile",inputs={"effect":receipt})
        assert recovered.outcome == "succeeded", recovered.diagnostics
        assert box.session.lookup_effect(receipt.effect_id).status == "confirmed"
        assert transport.calls == 1
