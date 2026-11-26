"""One execution service shares HTTP work while retaining each consumer's evidence."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO
from threading import Event, Lock
from time import monotonic, sleep

import pytest

from stratbox.core.network import HttpFailure,HttpRequest,HttpResponse,HttpsEndpoint,RequestsTransport,RetryPolicy,exchange,exchange_into
from stratbox.core.observability import MemoryJournal
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material,RequestSpec,request_identity
from stratbox.shared.identity import ByteIdentity

ENDPOINT=HttpsEndpoint("fixture.example","/",subtree=True,allow_query=True)
REQUEST=HttpRequest("GET","https://fixture.example/workbook",(ENDPOINT,))


def response(body=b"workbook",status=200):
    return HttpResponse(status,body,{},datetime.now(timezone.utc),"https://fixture.example")

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


class Fetcher:
    def __init__(self):self.calls=0;self.lock=Lock()
    def fetch(self,request):
        with self.lock:self.calls+=1
        return Material(b"workbook")


def checked(result):
    assert result.outcome=="succeeded",result.diagnostics
    return result


def fetch(box,request):
    return box.invoke("command.material.fetch",inputs={"request":request})


def test_request_body_observation_access_scope_and_limits_are_exact_work_boundaries():
    backend=Fetcher();base=RequestSpec(REQUEST.url,observation_id="observation-a")
    with StrategyBox(providers={"http":backend}) as box:
        results=[checked(fetch(box,base)),checked(fetch(box,base))]
        assert backend.calls==2
        changed=(replace(base,observation_id="observation-b"),replace(base,headers={"accept":"text/csv"}),
            replace(base,timeout=10),replace(base,max_bytes=123),replace(base,metadata={"access_scope":"different"}),
            replace(base,method="POST",body=b"A"),replace(base,method="POST",body=b"B"))
        for item in changed:results.append(checked(fetch(box,item)))
        assert backend.calls==2+len(changed)
        assert len({request_identity(item) for item in changed})==len(changed)


def test_completed_mutable_observations_fetch_again_with_explicit_freshness():
    backend=Fetcher()
    with StrategyBox(providers={"http":backend}) as box:
        a=checked(fetch(box,RequestSpec(REQUEST.url)))
        b=checked(fetch(box,RequestSpec(REQUEST.url)))
        assert backend.calls==2
        request=RequestSpec(REQUEST.url,observation_id="same")
        c=checked(fetch(box,request));d=checked(fetch(box,request))
        assert backend.calls==4 and c.output("material").identity==d.output("material").identity
        checked(fetch(box,replace(request,freshness="fresh")))
        checked(fetch(box,replace(request,freshness="fresh")))
        assert backend.calls==6


@pytest.mark.parametrize("cancel_first",(True,False))
def test_cancelling_one_consumer_preserves_another_consumer_of_the_shared_body(cancel_first):
    entered,release=Event(),Event()
    class Blocked(Fetcher):
        def fetch(self,request):
            self.calls+=1;entered.set()
            assert release.wait(3)
            return Material(b"workbook")
    backend=Blocked();journal=MemoryJournal()
    with StrategyBox(providers={"http":backend},journal=journal) as box:
        request=RequestSpec(REQUEST.url,observation_id="same")
        first=box.submit("command.material.fetch",inputs={"request":request})
        assert entered.wait(2)
        second=box.submit("command.material.fetch",inputs={"request":request})
        eventually(lambda:any(f.kind=="work.joined" for f in journal.read()))
        cancelled,remaining=(first,second) if cancel_first else (second,first)
        cancelled.cancel();release.set()
        assert cancelled.result(3).outcome=="cancelled"
        assert checked(remaining.result(3)).output("material").data==b"workbook"
        assert backend.calls==1


def test_failed_http_work_is_not_cached_and_each_retry_remains_explicit():
    class Failed(Fetcher):
        def fetch(self,request):self.calls+=1;return response(status=503)
    backend=Failed();request=RequestSpec(REQUEST.url,observation_id="same")
    with StrategyBox(providers={"http":backend}) as box:
        assert fetch(box,request).outcome=="failed"
        assert fetch(box,request).outcome=="failed"
        assert backend.calls==2


def test_two_sources_share_physical_receive_with_independent_logical_materials_and_receipts():
    entered,release=Event(),Event()
    class Blocked(Fetcher):
        def fetch(self,request):
            self.calls+=1;entered.set()
            assert release.wait(3)
            return Material(b"workbook")
    backend=Blocked();journal=MemoryJournal();base=RequestSpec(REQUEST.url,observation_id="same")
    with StrategyBox(providers={"http":backend},journal=journal) as box:
        first=box.submit("command.material.fetch",inputs={"request":replace(base,source_id="series-a")})
        assert entered.wait(2)
        second=box.submit("command.material.fetch",inputs={"request":replace(base,source_id="series-b")})
        eventually(lambda:any(f.kind=="work.joined" for f in journal.read()))
        release.set()
        a,b=checked(first.result(3)),checked(second.result(3))
        assert backend.calls==1
        assert a.output("material").source_id=="series-a" and b.output("material").source_id=="series-b"
        assert a.output("material").identity==b.output("material").identity==ByteIdentity.of(b"workbook")
        assert a.output("evidence")==b.output("evidence")
        assert sum(result.resources.get("requests",0) for result in (a,b))==1
        assert sum(result.resources.get("wire_bytes",0) for result in (a,b))==8
        facts=journal.read()
        assert sum(f.kind=="work.started" for f in facts)==1
        assert sum(f.kind=="work.joined" for f in facts)==1
        assert len({f.physical_work_id for f in facts if f.physical_work_id})==1
        assert "fixture.example" not in repr(facts)


def test_stream_failure_removes_partial_staging():
    from requests.structures import CaseInsensitiveDict
    class ShortWrite(BytesIO):
        def write(self,value):super().write(value[:2]);return 2
    class Wire:
        status_code=200
        headers=CaseInsensitiveDict({"content-length":"8"})
        def __init__(self):self.raw=self;self.body=BytesIO(b"workbook")
        def __enter__(self):return self
        def __exit__(self,*exc):self.body.close()
        def read1(self,size,*,decode_content):return self.body.read(size)
    class Session:
        def get_adapter(self,url):return self
        def send(self,*args,**kwargs):return Wire()
    sink=ShortWrite()
    result=exchange_into(REQUEST,sink,transport=RequestsTransport(session=Session()))
    assert result.reason=="staging_failed" and sink.getvalue()==b""
