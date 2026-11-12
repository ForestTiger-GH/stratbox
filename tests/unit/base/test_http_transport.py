from gzip import compress
from io import BytesIO

import pytest
import requests
from requests.structures import CaseInsensitiveDict

from stratbox.base.net import (
    HttpFailure,
    HttpRequest,
    HttpResponse,
    HttpsEndpoint,
    RequestsTransport,
    RetryPolicy,
    exchange,
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
