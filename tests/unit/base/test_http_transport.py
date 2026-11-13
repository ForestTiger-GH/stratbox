from gzip import compress
from hashlib import sha256
from io import BytesIO

import pytest
import requests
from requests.structures import CaseInsensitiveDict

from stratbox.base.net import (
    HttpFailure,
    HttpRequest,
    HttpResponse,
    HttpsEndpoint,
    HttpsRoute,
    RequestsTransport,
    RetryPolicy,
    RoutedTransport,
    exchange,
    exchange_into,
)

HOST = "example.org"
URL = "https://example.org/public/file"
ENDPOINT = HttpsEndpoint(HOST, "/public/", subtree=True)


class Response:
    def __init__(self, status, headers, body=b""):
        self.status_code = status
        self.headers = CaseInsensitiveDict(headers)
        self.raw = self
        self._body = BytesIO(body)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._body.close()

    def read1(self, size, *, decode_content):
        assert not decode_content
        return self._body.read(size)


def install_responses(monkeypatch, *responses):
    calls = []

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def get_adapter(self, url):
            return self

        def send(self, prepared, **options):
            calls.append(prepared)
            return responses[len(calls) - 1]

    monkeypatch.setattr(requests, "Session", Session)
    return calls


def test_fixed_gateway_keeps_source_and_transport_evidence(monkeypatch):
    source = "https://example.org/public/Keep%20Case?date=2026-11-13"
    wire = "https://relay.example/source/public/Keep%20Case?date=2026-11-13"
    endpoint = HttpsEndpoint(HOST, "/public/", subtree=True, allow_query=True)
    req = HttpRequest("GET", source, (endpoint,))
    route = HttpsRoute("relay", (HOST,), "https://relay.example/source/")
    transport = RoutedTransport(RequestsTransport(), (route,))
    calls = install_responses(monkeypatch, Response(200, {}, b"data"), Response(200, {}, b"data"))
    result = exchange(req, transport=transport)
    assert result.effective_locator_safe == "https://relay.example"
    assert result.route_id == "relay"
    assert result.logical_target_sha256 == sha256(source.encode()).hexdigest()
    assert result.target_sha256 == sha256(wire.encode()).hexdigest()
    assert result.origin_assurance == "provider_reported"
    assert result.transport_assurance == "tls_host"
    sink = BytesIO()
    streamed = exchange_into(req, sink, transport=transport)
    assert sink.getvalue() == result.body == b"data"
    assert streamed.response.target_sha256 == result.target_sha256
    assert [call.url for call in calls] == [wire, wire]


def test_gateway_rejects_sensitive_headers_and_unqualified_redirect(monkeypatch):
    route = HttpsRoute("relay", (HOST,), "https://relay.example/source/")
    transport = RoutedTransport(RequestsTransport(), (route,))
    calls = install_responses(monkeypatch, Response(302, {"Location": "/elsewhere"}))
    req = HttpRequest("GET", URL, (ENDPOINT,), {"Authorization": "synthetic"})
    assert exchange(req, transport=transport) == HttpFailure("destination_forbidden", "admission")
    assert not calls
    req = HttpRequest("GET", URL, (ENDPOINT,))
    assert exchange(req, transport=transport).reason == "redirect_forbidden"
    assert len(calls) == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org/public/file",
        "https://example.org/public/%2e%2e/private",
        "https://example.org/public/file?secret=1",
        "https://127.0.0.1/public/file",
        "https://user:secret@example.org/public/file",
    ],
)
def test_admission_rejects_before_provider_call(url):
    class MustNotRun:
        def exchange(self, *args, **kwargs):
            pytest.fail("destination reached the provider")

    result = exchange(HttpRequest("GET", url, (ENDPOINT,)), transport=MustNotRun())
    assert result == HttpFailure("destination_forbidden", "admission")


def test_forbidden_redirect_and_post_redirect_admission(monkeypatch):
    calls = install_responses(
        monkeypatch, Response(302, {"Location": "https://other.example/public/file"})
    )
    result = exchange(
        HttpRequest("GET", URL, (ENDPOINT,)), transport=RequestsTransport()
    )
    assert result.reason == "redirect_forbidden" and len(calls) == 1
    calls = install_responses(monkeypatch, Response(302, {"Location": "/public/next"}))
    result = exchange(
        HttpRequest("POST", URL, (ENDPOINT,), form_fields={"date": "x"}),
        transport=RequestsTransport(),
    )
    assert result.reason == "redirect_forbidden" and len(calls) == 1


def test_bounded_gzip_and_truncated_length(monkeypatch):
    body = b"source bytes"
    compressed = compress(body)
    install_responses(
        monkeypatch,
        Response(
            200,
            {"Content-Encoding": "gzip", "Content-Length": str(len(compressed))},
            compressed,
        ),
    )
    result = exchange(
        HttpRequest("GET", URL, (ENDPOINT,), max_response_bytes=80),
        transport=RequestsTransport(),
    )
    assert isinstance(result, HttpResponse) and result.body == body
    install_responses(
        monkeypatch, Response(200, {"Content-Encoding": "gzip"}, compress(b"x" * 2000))
    )
    result = exchange(
        HttpRequest("GET", URL, (ENDPOINT,), max_response_bytes=80),
        transport=RequestsTransport(),
    )
    assert result.reason == "response_too_large"
    install_responses(monkeypatch, Response(200, {"Content-Length": "80"}, b"short"))
    result = exchange(
        HttpRequest("GET", URL, (ENDPOINT,)), transport=RequestsTransport()
    )
    assert result.reason == "truncated"


def test_status_and_retry_after_preserve_http_response(monkeypatch):
    calls = install_responses(
        monkeypatch, Response(429, {"Retry-After": "600"}, b"wait")
    )
    result = exchange(
        HttpRequest("GET", URL, (ENDPOINT,)),
        transport=RequestsTransport(),
        retry=RetryPolicy(),
    )
    assert result.status_code == 429 and len(calls) == 1
    calls = install_responses(
        monkeypatch, Response(503, {}), Response(200, {}, b"complete")
    )
    result = exchange(
        HttpRequest("GET", URL, (ENDPOINT,)),
        transport=RequestsTransport(),
        retry=RetryPolicy(attempts=2, initial_delay_seconds=0, max_delay_seconds=0),
    )
    assert result.status_code == 200 and result.body == b"complete" and len(calls) == 2
    install_responses(monkeypatch, Response(304, {"Content-Length": "2048"}))
    result = exchange(
        HttpRequest("GET", URL, (ENDPOINT,)), transport=RequestsTransport()
    )
    assert result.status_code == 304 and result.body == b""


def test_budget_covers_retries_and_redirects_before_next_connection(monkeypatch):
    from stratbox.base.limits import BudgetExceeded, BudgetMeter, ExecutionBudget

    retry = RetryPolicy(attempts=2, initial_delay_seconds=0, max_delay_seconds=0)
    for first in (Response(503, {}), Response(302, {"Location": "/public/next"})):
        calls = install_responses(monkeypatch, first)
        budget = BudgetMeter(ExecutionBudget(requests=1))
        with pytest.raises(BudgetExceeded, match="budget.requests"):
            exchange(HttpRequest("GET", URL, (ENDPOINT,)), transport=RequestsTransport(),
                     retry=retry, budget=budget)
        assert len(calls) == budget.used("requests") == 1


def test_post_retry_and_cross_origin_headers_are_admitted_separately(monkeypatch):
    retry = RetryPolicy(attempts=2, initial_delay_seconds=0, max_delay_seconds=0)
    for safe in (False, True):
        calls = install_responses(monkeypatch, Response(503, {}), Response(200, {}, b"ok"))
        result = exchange(HttpRequest("POST", URL, (ENDPOINT,), form_fields={"date": "x"},
                                      read_only_post=safe), transport=RequestsTransport(), retry=retry)
        assert result.status_code == (200 if safe else 503)
        assert len(calls) == (2 if safe else 1)
    next_url = "https://fixture.example/public/next"
    calls = install_responses(monkeypatch, Response(302, {"Location": next_url}),
                              Response(200, {}, b"ok"))
    request = HttpRequest("GET", URL, (ENDPOINT, HttpsEndpoint("fixture.example", "/public/next")),
                          headers={"authorization": "private", "if-none-match": '"source"'})
    assert exchange(request, transport=RequestsTransport()).body == b"ok"
    assert calls[0].headers["authorization"] == "private"
    assert "authorization" not in calls[1].headers and "if-none-match" not in calls[1].headers


def test_peer_admission_and_tls_use_actual_connection(tmp_path, monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from shutil import which
    import socket
    import ssl
    import subprocess
    from threading import Thread

    from stratbox.base.net import PeerBoundTransport, exchange_into

    openssl = which("openssl")
    if openssl is None:
        pytest.skip("OpenSSL command required to generate a loopback fixture certificate")
    cert, key = tmp_path / "cert.pem", tmp_path / "key.pem"
    subprocess.run(
        [openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
         "-subj", "/CN=fixture.example", "-addext", "subjectAltName=DNS:fixture.example",
         "-keyout", str(key), "-out", str(cert)],
        check=True, capture_output=True, timeout=30,
    )
    requests_seen = []
    names = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):
            requests_seen.append((self.path, self.headers["Host"]))
            self.send_response(200)
            if self.path == "/chunked":
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                self.wfile.write(b"2\r\nok\r\n3\r\n123\r\n0\r\n\r\n")
                return
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *_):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(str(cert), str(key))
        tls.set_servername_callback(lambda _, name, __: names.append(name))
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        serving = Thread(target=server.serve_forever, daemon=True)
        serving.start()
        try:
            connections = []
            lookups = []

            def resolver(host, port):
                lookups.append((host, port))
                return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", port))]

            real_socket = socket.socket

            class FixtureSocket(real_socket):
                def connect(self, address):
                    connections.append(address)
                    assert address == ("127.0.0.1", 443)
                    return super().connect(server.server_address)

            monkeypatch.setattr(socket, "socket", FixtureSocket)
            client = ssl.create_default_context(cafile=str(cert))
            req = HttpRequest("GET", "https://fixture.example/public", (HttpsEndpoint("fixture.example", "/public"),))
            denied = exchange(req, transport=PeerBoundTransport(resolver=resolver, tls_context=client))
            assert denied.reason == "destination_forbidden" and not connections
            transport = PeerBoundTransport(resolver=resolver, tls_context=client, allow_peer=lambda peer: peer.is_loopback)
            allowed = exchange(req, transport=transport)
            assert isinstance(allowed, HttpResponse), (allowed, names, connections, requests_seen)
            assert allowed.origin_assurance == "peer_bound" and allowed.body == b"ok"
            mismatch = HttpRequest("GET", "https://different.example/public",
                                   (HttpsEndpoint("different.example", "/public"),))
            rejected = exchange(mismatch, transport=transport)
            assert rejected.reason == "destination_forbidden"
            assert len(connections) == 2
            assert names == ["fixture.example", "different.example"]
            assert [name for name, _ in lookups] == ["fixture.example", "fixture.example", "different.example"]
            assert requests_seen == [("/public", "fixture.example")]
            chunked = HttpRequest("GET", "https://fixture.example/chunked",
                                  (HttpsEndpoint("fixture.example", "/chunked"),))
            sink = BytesIO()
            streamed = exchange_into(chunked, sink, transport=transport)
            assert streamed.response.origin_assurance == "peer_bound"
            assert streamed.response.wire_size == streamed.identity.size == 5
            assert sink.getvalue() == b"ok123"
        finally:
            server.shutdown()
            serving.join(3)
