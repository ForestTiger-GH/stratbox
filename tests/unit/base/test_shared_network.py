from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO
from threading import Event
from time import monotonic, sleep

import pytest

from stratbox.core.network import (
    AccessScope, AccessScopes, HttpFailure, HttpRequest, HttpResponse, HttpsEndpoint,
    RequestsTransport, RetryPolicy, SessionNetwork, SharedMaterial,
    SharedWorkRegistry, acquisition_key, exchange, exchange_into,
)
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.identity import ByteIdentity

ENDPOINT = HttpsEndpoint("fixture.example", "/", subtree=True, allow_query=True)
REQUEST = HttpRequest("GET", "https://fixture.example/workbook", (ENDPOINT,))


def response(body=b"workbook", status=200):
    return HttpResponse(status, body, {}, datetime.now(timezone.utc), "https://fixture.example")


def eventually(check, seconds=2):
    deadline = monotonic() + seconds
    while monotonic() < deadline:
        if check():
            return
        sleep(0.005)
    assert check()


class CountingTransport:
    def __init__(self):
        self.calls = 0
        self.closed = False

    def exchange(self, request, *, cancelled=None):
        self.calls += 1
        return response()

    def close(self):
        self.closed = True


def test_observation_generation_and_body_are_exact_boundaries():
    scope = AccessScope()
    key = acquisition_key(REQUEST, scope, "run-a")
    assert key != acquisition_key(REQUEST, scope, "run-b")
    assert key != acquisition_key(REQUEST, replace(scope, generation=1), "run-a")
    assert key != acquisition_key(REQUEST, replace(scope, scope_id="other"), "run-a")
    for changed in (
        replace(REQUEST, url="https://fixture.example/workbook?b=2&a=1"),
        replace(REQUEST, headers={"accept": "text/csv"}),
        replace(REQUEST, deadline_seconds=10),
        replace(REQUEST, max_response_bytes=123),
    ):
        assert acquisition_key(changed, scope, "run-a") != key
    a = HttpRequest("POST", REQUEST.url, (ENDPOINT,), body=b"A", read_only_post=True)
    b = replace(a, body=b"B")
    assert acquisition_key(a, scope, "run-a") != acquisition_key(b, scope, "run-a")
    pinned = ByteIdentity.of(b"workbook")
    assert acquisition_key(REQUEST, scope, "run-a", immutable_identity=pinned) == acquisition_key(
        REQUEST, scope, "run-b", immutable_identity=pinned)


def test_one_observation_shares_bytes_but_fresh_runs_fetch_again():
    backend = CountingTransport()
    with SessionNetwork(backend) as network:
        first, second = network.transport_for("run-a"), network.transport_for("run-a")
        assert exchange(REQUEST, transport=first).body == b"workbook"
        assert exchange(REQUEST, transport=second).body == b"workbook"
        assert backend.calls == 1
        assert exchange(REQUEST, transport=network.transport_for("run-b")).body == b"workbook"
        assert backend.calls == 2
        scope = network.scopes.invalidate(AccessScope())
        assert scope.generation == 1
        exchange(REQUEST, transport=first)
        assert backend.calls == 3
    assert not backend.closed
    owned = CountingTransport()
    with SessionNetwork(owned, owned=True):
        pass
    assert owned.closed


def test_cancelled_first_consumer_cannot_abort_other_consumers():
    entered, release, cancelled = Event(), Event(), Event()

    class Blocking(CountingTransport):
        def exchange(self, request, *, cancelled=None):
            self.calls += 1
            entered.set()
            while not release.wait(0.005):
                if cancelled and cancelled():
                    return HttpFailure("cancelled", "body")
            return response()

    backend = Blocking()
    with SessionNetwork(backend) as network, ThreadPoolExecutor(2) as pool:
        transport = network.transport_for("run-a")
        first = pool.submit(transport.exchange, REQUEST, cancelled=cancelled.is_set)
        assert entered.wait(2)
        second = pool.submit(transport.exchange, REQUEST)
        eventually(lambda: network.acquisitions.snapshot()["consumers"] == 2)
        cancelled.set()
        # Keep the producer alive until it observes the first consumer's
        # cancellation while the second still needs the response.
        eventually(lambda: network.acquisitions.snapshot()["consumers"] == 1)
        release.set()
        assert first.result(2).reason == "cancelled"
        assert second.result(2).body == b"workbook"
        assert backend.calls == 1


def test_cancelled_follower_detaches_without_cancelling_shared_future():
    registry = SharedWorkRegistry()
    leader = registry.claim("request", "leader")
    follower = registry.claim("request", "follower")
    registry.detach(follower)
    assert not registry.should_cancel(leader)
    registry.complete(leader, "result")
    assert leader.future.result() == follower.future.result() == "result"
    registry.detach(leader)


def test_preparation_is_once_per_scope_generation_and_failures_are_retryable():
    scopes = AccessScopes()
    scope, first = scopes.claim(AccessScope(), "prepare", {"region": "a"}, "one")
    same_scope, second = scopes.claim(AccessScope(), "prepare", {"region": "a"}, "two")
    assert first.producer and not second.producer and same_scope == scope
    scopes.complete(scope, first, "access-ready", ttl_seconds=20)
    assert second.future.result() == "access-ready"
    scopes.preparations.detach(first)
    scopes.preparations.detach(second)
    scopes.invalidate(scope)
    updated, third = scopes.claim(scope, "prepare", {"region": "a"}, "three")
    assert updated.generation == 1 and third.producer
    scopes.preparations.fail(third, RuntimeError("temporary"))
    with pytest.raises(RuntimeError, match="temporary"):
        third.future.result()
    scopes.preparations.detach(third)
    _, fourth = scopes.claim(scope, "prepare", {"region": "a"}, "four")
    assert fourth.producer


def test_independent_source_uses_do_not_rename_the_physical_material():
    result = response()
    material = SharedMaterial("physical-one", "a" * 64, result)
    a = SourceUse(SourceCoordinate("series-a", source_group_id="sheet-a", material_identity=material.identity))
    b = SourceUse(SourceCoordinate("series-b", source_group_id="sheet-b", material_identity=material.identity))
    combined = material.with_use(a).with_use(b)
    assert combined.response is material.response
    assert combined.acquisition_id == "physical-one"
    assert [use.coordinate.source_id for use in combined.uses] == ["series-a", "series-b"]
    with pytest.raises(ValueError, match="material_identity"):
        material.with_use(SourceUse(SourceCoordinate("series-c", material_identity=ByteIdentity.of(b"other"))))


def test_failed_work_is_not_cached_and_scheduler_owns_retry_budget():
    class Failing(CountingTransport):
        def exchange(self, request, *, cancelled=None):
            self.calls += 1
            return response(status=503)

    backend = Failing()
    with SessionNetwork(backend) as network:
        transport = network.transport_for("run-a")
        retry = RetryPolicy(attempts=3, initial_delay_seconds=0, max_delay_seconds=0)
        assert exchange(REQUEST, transport=transport, retry=retry).status_code == 503
        assert backend.calls == 1
        exchange(REQUEST, transport=transport, retry=retry)
        assert backend.calls == 2


def test_pinned_identity_is_verified_and_writes_are_independent():
    backend = CountingTransport()
    with SessionNetwork(backend) as network:
        bad = network.transport_for("run-a", immutable_identity=ByteIdentity.of(b"other"))
        assert exchange(REQUEST, transport=bad).reason == "invalid_http"
        transport = network.transport_for("run-b")
        first, second = BytesIO(), BytesIO()
        one = exchange_into(REQUEST, first, transport=transport)
        two = exchange_into(REQUEST, second, transport=transport)
        assert one.identity == two.identity == ByteIdentity.of(b"workbook")
        assert first.getvalue() == second.getvalue() == b"workbook"
        assert backend.calls == 2


def test_stream_failure_removes_partial_staging():
    class ShortWrite(BytesIO):
        def write(self, value):
            super().write(value[:2])
            return 2

    with SessionNetwork(CountingTransport()) as network:
        sink = ShortWrite()
        result = exchange_into(REQUEST, sink, transport=network.transport_for("run-a"))
        assert result.reason == "staging_failed"
        assert sink.getvalue() == b""


def test_shared_cache_releases_evicted_bytes():
    registry = SharedWorkRegistry(max_entries=2, max_bytes=10)
    for index in range(5):
        claim = registry.claim(str(index), "consumer")
        registry.complete(claim, b"12345", size=5)
        registry.detach(claim)
    assert registry.snapshot() == {"entries": 2, "retained_bytes": 10, "running": 0, "consumers": 0}
    registry.close()
    assert registry.snapshot()["retained_bytes"] == 0


def test_pool_close_waits_for_active_response_and_preserves_borrowed_session():
    import requests
    from requests.structures import CaseInsensitiveDict
    entered, release = Event(), Event()

    class Wire:
        status_code = 200
        headers = CaseInsensitiveDict({"content-length": "2"})
        def __init__(self):
            self.raw = self
            self.body = BytesIO(b"ok")
        def __enter__(self):
            entered.set()
            assert release.wait(2)
            return self
        def __exit__(self, *exc):
            self.body.close()
        def read1(self, size, *, decode_content):
            return self.body.read(size)

    class Session:
        def __init__(self):
            self.closed = False
        def get_adapter(self, url):
            return self
        def send(self, *args, **kwargs):
            return Wire()
        def close(self):
            self.closed = True

    session = Session()
    transport = RequestsTransport(session=session, own_session=True)
    with ThreadPoolExecutor(2) as pool:
        running = pool.submit(transport.exchange, REQUEST)
        assert entered.wait(2)
        closing = pool.submit(transport.close)
        eventually(lambda: transport._closing)
        assert not closing.done() and not session.closed
        release.set()
        assert running.result(2).body == b"ok"
        closing.result(2)
    assert session.closed
    assert transport.exchange(REQUEST).reason == "capability_missing"
    borrowed = Session()
    RequestsTransport(session=borrowed).close()
    assert not borrowed.closed


def test_network_observations_distinguish_physical_work_and_consumers():
    from stratbox.core.observability import OrchestrationJournal

    with closing(OrchestrationJournal("session-test")) as journal, SessionNetwork(
            CountingTransport(), journal=journal) as network:
        first = network.transport_for("observation", run_id="run-one", task_id="task-one")
        second = network.transport_for("observation", run_id="run-two", task_id="task-two")
        exchange(REQUEST, transport=first)
        exchange(REQUEST, transport=second)
        records = journal.records
        assert sum(item.kind == "shared_work.started" for item in records) == 1
        assert sum(item.kind == "shared_work.attached" for item in records) == 2
        assert sum(item.kind == "shared_work.reused" for item in records) == 1
        assert len({item.correlation.shared_work_id for item in records}) == 1
        assert {item.correlation.run_id for item in records} == {"run-one", "run-two"}
        assert "fixture.example" not in repr(records)


def test_redirect_moves_actual_origin_reservation_before_sending():
    from requests.structures import CaseInsensitiveDict
    from stratbox.core.execution.resources import ResourceLedger

    ledger = ResourceLedger({"worker": 1, "network": 1}, per_origin=1)
    initial = {"worker": 1, "network": 1, "origin:https://fixture.example": 1}
    assert ledger.reserve("task", initial)
    seen = []

    class Wire:
        def __init__(self, status, headers, body=b""):
            self.status_code, self.headers = status, CaseInsensitiveDict(headers)
            self.raw = self
            self.body = BytesIO(body)
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            self.body.close()
        def read1(self, size, *, decode_content):
            return self.body.read(size)

    class Session:
        def get_adapter(self, url):
            return self
        def send(self, prepared, **options):
            seen.append((prepared.url, ledger.requirements("task")))
            if len(seen) == 1:
                return Wire(302, {"location": "https://other.example/workbook"})
            return Wire(200, {}, b"ok")

    request = replace(REQUEST, endpoints=(ENDPOINT, HttpsEndpoint("other.example", "/", subtree=True)))
    backend = RequestsTransport(session=Session(), per_origin=1)
    with SessionNetwork(backend) as network:
        transport = network.transport_for("run-a", reservation_owner="task", ledger=ledger)
        result = exchange(request, transport=transport)
    assert result.body == b"ok"
    assert seen[0][1] == initial
    assert seen[1][1] == {"worker": 1, "network": 1, "origin:https://other.example": 1}
    ledger.release("task")
    assert all(value == 0 for value in ledger.snapshot().occupied.values())


def test_requests_pool_reuses_a_live_https_connection(tmp_path, monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from shutil import which
    import socket
    import ssl
    import subprocess
    from threading import Thread

    openssl = which("openssl")
    if openssl is None:
        pytest.skip("OpenSSL is needed for a local HTTPS fixture")
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    subprocess.run([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
        "-subj", "/CN=fixture.example", "-addext", "subjectAltName=DNS:fixture.example",
        "-keyout", str(key), "-out", str(cert)], check=True, capture_output=True, timeout=30)
    received, connections = [], []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def do_GET(self):
            received.append(self.path)
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")
        def log_message(self, *_):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(str(cert), str(key))
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        serving = Thread(target=server.serve_forever, daemon=True)
        serving.start()
        real_socket, real_lookup = socket.socket, socket.getaddrinfo
        class FixtureSocket(real_socket):
            def connect(self, address):
                if address == ("127.0.0.1", 443):
                    connections.append(address)
                    address = server.server_address
                return super().connect(address)
        def lookup(host, port, *args, **kwargs):
            if host == "fixture.example":
                return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))]
            return real_lookup(host, port, *args, **kwargs)
        monkeypatch.setattr(socket, "socket", FixtureSocket)
        monkeypatch.setattr(socket, "getaddrinfo", lookup)
        try:
            with RequestsTransport(ca_bundle=str(cert)) as transport:
                assert exchange(REQUEST, transport=transport).body == b"ok"
                assert exchange(replace(REQUEST, url="https://fixture.example/second"), transport=transport).body == b"ok"
            assert received == ["/workbook", "/second"]
            assert len(connections) == 1
        finally:
            server.shutdown()
            serving.join(3)


def test_expired_access_refresh_advances_one_shared_generation(monkeypatch):
    import stratbox.core.network.shared as shared
    clock = [100.0]
    monkeypatch.setattr(shared, "monotonic", lambda: clock[0])
    scopes = AccessScopes()
    scope, claim = scopes.claim(AccessScope(), "prepare", {}, "first")
    scopes.complete(scope, claim, "ready", ttl_seconds=10)
    scopes.preparations.detach(claim)
    clock[0] = 111.0
    next_scope, refresh = scopes.claim(scope, "prepare", {}, "second")
    same_scope, follower = scopes.claim(scope, "prepare", {}, "third")
    assert next_scope.generation == same_scope.generation == 1
    assert refresh.producer and not follower.producer
    assert refresh.future is follower.future


def test_shared_request_counts_one_physical_receive_and_each_consumer_processing():
    from stratbox.core.execution.resources import ResourceLedger, SharedBudgetMeter
    from stratbox.core.limits import ExecutionBudget

    class Metered(CountingTransport):
        accounts_http_budget = True
        def exchange(self, request, *, cancelled=None):
            self.calls += 1
            request.budget.charge("requests", 1)
            request.budget.charge("wire_bytes", 8)
            request.budget.charge("decoded_bytes", 8)
            return response()

    ledger = ResourceLedger(expenditure={"requests": 1, "wire_bytes": 8})
    first = SharedBudgetMeter(ExecutionBudget(), ledger)
    second = SharedBudgetMeter(ExecutionBudget(), ledger)
    with SessionNetwork(Metered()) as network:
        transport = network.transport_for("run")
        assert exchange(REQUEST, transport=transport, budget=first).body == b"workbook"
        assert exchange(REQUEST, transport=transport, budget=second).body == b"workbook"
    spent = ledger.snapshot().spent
    assert spent["requests"] == 1 and spent["wire_bytes"] == 8
    assert spent["decoded_bytes"] == 16


def test_closing_during_shared_work_cannot_repopulate_cache():
    registry = SharedWorkRegistry()
    claim = registry.claim("request", "consumer")
    registry.close()
    assert registry.should_cancel(claim)
    registry.complete(claim, b"late", size=4)
    registry.detach(claim)
    assert registry.snapshot() == {"entries": 0, "retained_bytes": 0, "running": 0, "consumers": 0}


def test_provider_scope_generation_and_configuration_survive_session_wrapping():
    backend = CountingTransport()
    backend.scope = AccessScope("provider", "account", 4, "managed", "route-one", "tls-one")
    with SessionNetwork(backend) as network:
        transport = network.transport_for("run", scope=AccessScope("binding", profile="local"))
        assert transport.scope == AccessScope("binding", "account", 4, "local", "route-one", "tls-one")
        exchange(REQUEST, transport=transport)
        exchange(REQUEST, transport=transport)
        assert backend.calls == 1
        backend.scope = replace(backend.scope, generation=5)
        exchange(REQUEST, transport=transport)
        assert backend.calls == 2
        assert transport.scope.generation == 5


def test_two_source_receipts_share_physical_id_without_double_wire_claim():
    from types import SimpleNamespace
    from stratbox.core.execution.values import argument_value
    from stratbox.core.limits import BudgetMeter, ExecutionBudget
    from stratbox.core.operations.source.acquisition import receive_source

    class Backend(CountingTransport):
        def exchange(self, request, *, cancelled=None):
            return replace(super().exchange(request, cancelled=cancelled), wire_size=8)

    backend = Backend()
    with SessionNetwork(backend) as network:
        transport = network.transport_for("run")
        invocation = SimpleNamespace(context=SimpleNamespace(profile="local", bindings=()),
            provider=lambda role, provider: provider, budget=BudgetMeter(ExecutionBudget()), cancelled=lambda: False)
        options = dict(transport=transport, invocation=invocation,
            media_types=frozenset({"application/octet-stream"}), default_media_type="application/octet-stream")
        first = receive_source(REQUEST, source_id="series-a", **options)
        second = receive_source(REQUEST, source_id="series-b", **options)
    assert backend.calls == 1
    assert first.receipt.shared_work_id == second.receipt.shared_work_id
    assert first.receipt.shared_work_id is not None
    assert first.receipt.wire_size == 8 and not first.receipt.reused
    assert second.receipt.wire_size == 0 and second.receipt.reused
    assert first.receipt.observed_at_utc == second.receipt.observed_at_utc
    assert first.payload.identity == second.payload.identity == ByteIdentity.of(b"workbook")
    assert first.receipt.source_id == "series-a" and second.receipt.source_id == "series-b"
    assert argument_value(first.receipt) == argument_value(replace(first.receipt, shared_work_id="another-work"))
