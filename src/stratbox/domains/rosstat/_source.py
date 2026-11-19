"""Narrow publisher URLs; discovered links never expand the trust boundary."""

from __future__ import annotations

from urllib.parse import unquote, urlsplit

from stratbox.core.network import HttpRequest, HttpsEndpoint, RetryPolicy
from stratbox.core.network.contracts import public_https_parts

PUBLISHER_HOSTS = ("rosstat.gov.ru", "www.rosstat.gov.ru")
MEDIA_TYPES = frozenset({
    "text/html", "application/xhtml+xml",
    "application/octet-stream", "application/pdf", "application/zip",
    "application/x-zip-compressed", "application/x-rar-compressed",
    "application/vnd.rar", "application/x-rar", "application/x-binary",
    "application/force-download", "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
})
FILE_PREFIXES = ("/storage/mediabank/", "/upload/")


def allowed_rosstat_base(url: str) -> bool:
    """An HTML base may be the publisher root, not necessarily the landing page."""
    try:
        p = public_https_parts(url)
    except (TypeError, ValueError):
        return False
    return p.hostname in PUBLISHER_HOSTS and not p.query and p.port in (None, 443)


def allowed_page_url(url: str, canonical: str) -> bool:
    try:
        p = public_https_parts(url)
        expected = public_https_parts(canonical)
    except (TypeError, ValueError):
        return False
    return (
        p.hostname in PUBLISHER_HOSTS and p.path == expected.path
        and not p.query and p.port in (None, 443)
    )


def allowed_file_url(url: str) -> bool:
    try:
        p = public_https_parts(url)
        path = unquote(p.path, errors="strict")
    except (ValueError, TypeError):
        return False
    return (
        p.hostname in PUBLISHER_HOSTS
        and any(path.startswith(prefix) for prefix in FILE_PREFIXES)
        and p.query == "" and p.port in (None, 443)
    )


def page_request(url: str, canonical: str, limit: int = 10 * 1024 * 1024) -> HttpRequest:
    if not allowed_page_url(url, canonical):
        raise ValueError("rosstat.page_url_forbidden")
    path = urlsplit(canonical).path
    return HttpRequest(
        "GET", url,
        tuple(HttpsEndpoint(host, path) for host in PUBLISHER_HOSTS),
        headers={"Accept": "text/html,application/xhtml+xml"},
        deadline_seconds=60, max_response_bytes=limit,
    )


def file_request(url: str, limit: int, deadline: float) -> HttpRequest:
    if not allowed_file_url(url):
        raise ValueError("rosstat.file_url_forbidden")
    # Redirects may move between official media-bank objects but never escape
    # the explicit publisher-host and vetted storage/upload path boundaries.
    return HttpRequest(
        "GET", url,
        tuple(HttpsEndpoint(host, prefix, subtree=True)
              for host in PUBLISHER_HOSTS for prefix in FILE_PREFIXES),
        headers={"Accept": "application/octet-stream,*/*"},
        deadline_seconds=deadline, max_response_bytes=limit,
    )
