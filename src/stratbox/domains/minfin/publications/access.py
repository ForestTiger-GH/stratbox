"""Minfin HTTPS policy and HTTP request contracts; transport stays in core.network."""
from __future__ import annotations
from urllib.parse import unquote, urlsplit
from stratbox.core.network import HttpRequest, HttpsEndpoint
from stratbox.core.network.contracts import public_https_parts

_HOSTS = ("minfin.gov.ru", "www.minfin.gov.ru")
_STORAGE = ("/common/upload/library/", "/upload/")
_FORM = {"xlsx", "xls", "xlsm", "csv", "zip", "pdf", "doc", "docx"}
PAGE_MIMES = frozenset({"text/html", "application/xhtml+xml"})
FILE_MIMES = frozenset({
    "application/octet-stream", "application/force-download", "application/x-binary",
    "application/zip", "application/x-zip-compressed", "application/pdf",
    "application/vnd.ms-excel", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel.sheet.macroenabled.12",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "text/csv", "text/plain",
})


def allowed_page(url: str) -> bool:
    try:
        p = public_https_parts(url)
    except (ValueError, TypeError):
        return False
    return p.hostname in _HOSTS and p.path.startswith("/ru/") and not p.query


def allowed_file(url: str, *, extension: str | None = None) -> bool:
    try:
        p = public_https_parts(url)
        path = unquote(p.path, errors="strict")
    except (ValueError, TypeError):
        return False
    ext = path.rsplit("/", 1)[-1].rsplit(".", 1)[-1].lower()
    return (
        p.hostname in _HOSTS and any(path.startswith(root) for root in _STORAGE)
        and ext in _FORM and (extension is None or ext == extension)
        and not p.query
    )


def page_request(url: str, *, limit: int = 8 * 1024 * 1024) -> HttpRequest:
    if not allowed_page(url):
        raise ValueError("minfin.page_forbidden")
    return HttpRequest(
        "GET", url,
        tuple(HttpsEndpoint(host, urlsplit(url).path) for host in _HOSTS),
        headers={"Accept": "text/html,application/xhtml+xml"},
        deadline_seconds=60, max_response_bytes=limit,
    )


def file_request(url: str, *, limit: int, deadline: int) -> HttpRequest:
    if not allowed_file(url):
        raise ValueError("minfin.asset_url_forbidden")
    return HttpRequest(
        "GET", url,
        tuple(HttpsEndpoint(host, root, subtree=True) for host in _HOSTS for root in _STORAGE),
        headers={"Accept": "application/octet-stream,*/*"},
        deadline_seconds=deadline, max_response_bytes=limit,
    )
