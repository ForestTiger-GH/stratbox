"""Shared admission rules for official Bank of Russia resources."""

from urllib.parse import unquote

from stratbox.base.ioapi.archive_bytes import ArchiveError, ArchiveLimits, open_zip
from stratbox.base.net import HttpRequest, HttpsEndpoint, RetryPolicy
from stratbox.base.net.contracts import public_https_parts
from stratbox.data.representation import XLSX
from stratbox.execution import OperationFailure
from stratbox.execution.acquisition import receive_source

HOSTS = ("www.cbr.ru", "cbr.ru")
HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
XLSX_TYPES = frozenset(
    {
        XLSX,
        "application/vnd.ms-excel",
        "application/octet-stream",
        "application/zip",
        "application/x-zip-compressed",
    }
)
ARCHIVE_TYPES = frozenset(
    {
        "application/octet-stream",
        "application/zip",
        "application/x-zip-compressed",
        "application/vnd.rar",
        "application/rar",
        "application/x-rar-compressed",
        "application/x-rar",
    }
)
WORKBOOK_LIMIT = 64 * 1024 * 1024
WORKBOOK_ARCHIVE_LIMITS = ArchiveLimits(
    500, 256 * 1024 * 1024, 128 * 1024 * 1024, WORKBOOK_LIMIT
)


def official_url(url: str, *, roots: tuple[str, ...] = ()) -> str:
    try:
        parts = public_https_parts(url)
    except (TypeError, ValueError):
        raise OperationFailure("request.source_url_invalid") from None
    path = unquote(parts.path)
    if (
        parts.hostname not in HOSTS
        or "?" in url
        or (roots and not path.casefold().startswith(roots))
    ):
        raise OperationFailure("request.source_url_invalid")
    return path


def receive_cbr(
    url,
    *,
    roots,
    media_types,
    limit,
    source_id,
    transport,
    invocation,
    retry=None,
    deadline=60,
):
    path = official_url(url, roots=roots)
    endpoints = tuple(HttpsEndpoint(host, path) for host in HOSTS)
    request = HttpRequest(
        "GET",
        url,
        endpoints,
        {"accept": ", ".join(sorted(media_types))},
        max_response_bytes=limit,
        deadline_seconds=deadline,
    )
    return receive_source(
        request,
        transport=transport,
        invocation=invocation,
        source_id=source_id,
        media_types=media_types,
        default_media_type="application/octet-stream",
        retry=retry if retry is not None else RetryPolicy(),
    )


def validate_workbook(data: bytes) -> None:
    try:
        with open_zip(data, WORKBOOK_ARCHIVE_LIMITS) as archive:
            names = set(archive.namelist())
            if not {"[Content_Types].xml", "xl/workbook.xml"}.issubset(names):
                raise OperationFailure("source.xlsx_signature_invalid")
    except ArchiveError:
        raise OperationFailure("source.xlsx_signature_invalid") from None
