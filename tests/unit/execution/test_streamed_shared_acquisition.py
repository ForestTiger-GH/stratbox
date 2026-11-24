"""Large shared transfers stage on disk and keep independent reader offsets."""
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import tracemalloc

from stratbox.core.execution.resources import ResourceLedger
from stratbox.core.network import HttpFailure, HttpRequest, HttpResponse, HttpStreamResponse, HttpsEndpoint, SessionNetwork
from stratbox.shared.identity import ByteIdentity


CHUNK = b"abcdefgh" * 8192
REQUEST = HttpRequest("GET", "https://fixture.example/data", (HttpsEndpoint("fixture.example", "/data"),))


class StreamingProvider:
    def __init__(self, chunks):
        self.chunks, self.calls = chunks, 0

    def exchange(self, request, *, cancelled=None):
        raise AssertionError("the streaming path must not request a full body")

    def exchange_into(self, request, sink, *, cancelled=None):
        self.calls += 1
        digest = sha256()
        for _ in range(self.chunks):
            assert sink.write(CHUNK) == len(CHUNK)
            digest.update(CHUNK)
        response = HttpResponse(200, b"", {}, datetime.now(timezone.utc), "https://fixture.example")
        return HttpStreamResponse(response, ByteIdentity(digest.hexdigest(), len(CHUNK) * self.chunks))


class DigestSink:
    def __init__(self):
        self.digest, self.size, self.largest_write = sha256(), 0, 0

    def write(self, chunk):
        self.digest.update(chunk)
        self.size += len(chunk)
        self.largest_write = max(self.largest_write, len(chunk))
        return len(chunk)


def test_large_transfer_uses_bounded_heap_and_one_physical_stream_for_independent_readers():
    size = len(CHUNK) * 128
    ledger = ResourceLedger({"staging_bytes": size * 2})
    backend = StreamingProvider(128)
    tracemalloc.start()
    try:
        with SessionNetwork(backend, max_bytes=size * 2, max_staging_bytes=size * 2,
                            staging_ledger=ledger) as network:
            transport = network.transport_for("frozen-observation")
            one, two = DigestSink(), DigestSink()
            first = transport.exchange_into(REQUEST, one)
            second = transport.exchange_into(REQUEST, two)
            assert first.identity == second.identity
            assert first.identity.size == one.size == two.size == size
            assert first.identity.sha256 == one.digest.hexdigest() == two.digest.hexdigest()
            assert second.response.shared_reused and second.response.wire_size == 0
            assert backend.calls == 1
            assert one.largest_write <= 65536 and two.largest_write <= 65536
            assert ledger.snapshot().occupied["staging_bytes"] == size
            assert tracemalloc.get_traced_memory()[1] < size // 2
        assert ledger.snapshot().occupied["staging_bytes"] == 0
    finally:
        tracemalloc.stop()


def test_staging_ceiling_discards_partial_transfer_and_cannot_leave_claimed_bytes():
    backend = StreamingProvider(10)
    ledger = ResourceLedger({"staging_bytes": len(CHUNK) * 2})
    with SessionNetwork(backend, max_bytes=len(CHUNK) * 2,
                        max_staging_bytes=len(CHUNK) * 2, staging_ledger=ledger) as network:
        sink = BytesIO()
        result = network.transport_for("observation").exchange_into(REQUEST, sink)
        assert isinstance(result, HttpFailure) and result.reason == "staging_failed"
        assert sink.getvalue() == b""
        assert ledger.snapshot().occupied["staging_bytes"] == 0
        assert network.staging.snapshot()["entries"] == 0
