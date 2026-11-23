"""Dated official 1-YUR transport routes; physical parsing belongs to tables."""
from datetime import date
from urllib.parse import unquote, urlsplit
from stratbox.core.network import HttpRequest, HttpsEndpoint, RetryPolicy
from stratbox.core.execution import OperationFailure
from stratbox.core.operations.source.acquisition import receive_source
from stratbox.shared.data.representation import XLSX
from .source import SourceError, allowed_url, MAX_HTML
from .source_history import MAX_SOURCE, MIN_DATE

DATASET = "fns.1yur"
OLE = bytes.fromhex("D0CF11E0A1B11AE1")
_HOSTS = ("www.nalog.gov.ru", "www.nalog.ru")
_HTML = frozenset({"text/html", "application/xhtml+xml"})


def _check_date(value):
    if (
        type(value) is not date
        or not MIN_DATE <= value <= date(2099, 12, 31)
        or value.day != 1
    ):
        raise OperationFailure("request.invalid_release_date")


def _http_request(url, limit):
    endpoints = tuple(
        HttpsEndpoint(host, unquote(urlsplit(url).path)) for host in _HOSTS
    )
    return HttpRequest("GET", url, endpoints, max_response_bytes=limit)


def _index(url, transport, invocation):
    return receive_source(
        _http_request(url, MAX_HTML),
        transport=transport,
        invocation=invocation,
        source_id=f"{DATASET}.index",
        media_types=_HTML,
        retry=RetryPolicy(),
    ).payload

def acquire_source(req, invocation, transport):
    invocation.stage("acquire")
    _check_date(req.as_of)
    try:
        allowed_url(req.url, "source")
    except SourceError:
        raise OperationFailure("request.release_link_invalid") from None
    source = receive_source(
        _http_request(req.url, MAX_SOURCE),
        transport=transport,
        invocation=invocation,
        source_id=DATASET,
        media_types=frozenset(
            {
                XLSX,
                "application/vnd.ms-excel",
                "application/octet-stream",
                "application/zip",
                "application/x-zip-compressed",
                "application/vnd.rar",
                "application/x-rar-compressed",
                "application/x-rar",
                "application/force-download",
            }
        ),
        retry=RetryPolicy(),
    )
    if not source.payload.data.startswith((b"PK\x03\x04", b"Rar!", OLE)):
        raise OperationFailure("source.asset_signature_invalid")
    return source
