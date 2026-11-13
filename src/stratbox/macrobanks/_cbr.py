"""Shared admission rules for official Bank of Russia resources."""

from urllib.parse import unquote

from io import BytesIO

from stratbox.base.ioapi.archive_bytes import ArchiveError, ArchiveLimits, open_zip_stream
from stratbox.base.ioapi.workbook_input import WorkbookError, workbook_profile
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
    request = cbr_request(url, roots=roots, media_types=media_types, limit=limit, deadline=deadline)
    return receive_source(
        request,
        transport=transport,
        invocation=invocation,
        source_id=source_id,
        media_types=media_types,
        default_media_type="application/octet-stream",
        retry=retry if retry is not None else RetryPolicy(),
    )


def cbr_request(url, *, roots, media_types, limit, deadline):
    path = official_url(url, roots=roots)
    endpoints = tuple(HttpsEndpoint(host, path) for host in HOSTS)
    return HttpRequest(
        "GET",
        url,
        endpoints,
        {"accept": ", ".join(sorted(media_types))},
        max_response_bytes=limit,
        deadline_seconds=deadline,
    )


def validate_workbook(data: bytes, *, budget=None) -> None:
    validate_workbook_stream(BytesIO(data), len(data), budget=budget)


def validate_workbook_stream(stream, size, *, budget=None) -> None:
    try:
        with open_zip_stream(stream, size, WORKBOOK_ARCHIVE_LIMITS, budget=budget) as archive:
            names = set(archive.namelist())
            if not {"[Content_Types].xml", "xl/workbook.xml"}.issubset(names):
                raise OperationFailure("source.xlsx_signature_invalid")
    except ArchiveError:
        raise OperationFailure("source.xlsx_signature_invalid") from None


def admit_workbook(data: bytes, invocation) -> None:
    if len(data) > WORKBOOK_LIMIT:
        raise OperationFailure("source.size_limit")
    token = invocation.context.cancellation
    try:
        profile = workbook_profile(
            data, budget=invocation.budget,
            cancelled=token.is_set if token is not None else None,
        )
    except (ArchiveError, WorkbookError) as error:
        if str(error) == "operation.cancelled":
            raise OperationFailure("operation.cancelled", outcome="cancelled") from None
        reason = str(error)
        code = "source.workbook_limit" if reason.endswith("_limit") else "source.workbook_invalid"
        raise OperationFailure(code) from None
    if profile.kind != "xlsx":
        raise OperationFailure("source.xlsx_signature_invalid")
    try:
        profile.check_materialization(invocation.budget)
    except WorkbookError:
        raise OperationFailure("source.workbook_materialization_limit") from None
