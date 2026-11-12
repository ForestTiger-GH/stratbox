"""Territorial office releases published in the Bank of Russia workbook."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re
from urllib.parse import unquote, urlsplit
from xml.etree.ElementTree import ParseError

from stratbox.base.ioapi.archive_bytes import ArchiveError
from stratbox.base.net import HttpRequest, HttpTransport, HttpsEndpoint, RetryPolicy
from stratbox.data import (
    AcquiredSource,
    Comparison,
    MetricRef,
    Observation,
    PeriodRef,
    SourcePayload,
    SubjectRef,
)
from stratbox.data.releases import (
    CompareReleaseRequest,
    ParsedRelease,
    ReadReleaseRequest,
    ReleaseLink,
    build_release,
    csv_rows,
)
from stratbox.data.representation import XLSX
from stratbox.execution import (
    ExecutionContext,
    OperationDefinition,
    OperationFailure,
    OperationResult,
    run,
)
from stratbox.execution.acquisition import receive_source
from stratbox.execution.comparison import compare_release_inputs
from stratbox.execution.source_validation import (
    decode_html,
    source_failure,
    use_payload,
)

from .parser import CaptureError, LIMIT_XLSX, convert_xlsx
from .representation import validate_csv
from .source import LIMIT_HTML, SOURCE_PAGE, discover as discover_links, url_date

DATASET = "cbr.offices_reg"
PROFILE = "cbr.offices_reg.wide-csv"
METHOD = "cbr-offices-reg-xlsx-1"
_HOSTS = ("www.cbr.ru", "cbr.ru")
_HTTP = frozenset({"http"})
_HTML = frozenset({"text/html", "application/xhtml+xml"})


@dataclass(frozen=True, slots=True)
class DiscoverOfficesRegRequest:
    index: SourcePayload | None = None


@dataclass(frozen=True, slots=True)
class ParseOfficesRegRequest:
    payload: SourcePayload
    as_of: date


DISCOVER = OperationDefinition(
    f"{DATASET}.discover",
    1,
    "cbr-offices-reg-index-1",
    DiscoverOfficesRegRequest,
    tuple,
)
ACQUIRE = OperationDefinition(
    f"{DATASET}.acquire", 1, METHOD, ReleaseLink, AcquiredSource, _HTTP
)
PARSE = OperationDefinition(
    f"{DATASET}.parse", 1, METHOD, ParseOfficesRegRequest, ParsedRelease
)
CAPTURE = OperationDefinition(
    f"{DATASET}.capture", 1, METHOD, ReleaseLink, ParsedRelease, _HTTP
)
READ = OperationDefinition(
    f"{DATASET}.read_representation",
    1,
    "cbr-offices-reg-csv-1",
    ReadReleaseRequest,
    ParsedRelease,
)
COMPARE = OperationDefinition(
    f"{DATASET}.compare",
    1,
    "cbr-offices-reg-compare-1",
    CompareReleaseRequest,
    Comparison,
)


def discover(
    request: DiscoverOfficesRegRequest,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[tuple[ReleaseLink, ...]]:
    def work(req, invocation):
        payload = req.index
        if payload is None:
            invocation.stage("acquire_index")
            if transport is None:
                raise OperationFailure("provider.capability_missing")
            endpoints = tuple(
                HttpsEndpoint(host, urlsplit(SOURCE_PAGE).path) for host in _HOSTS
            )
            payload = receive_source(
                HttpRequest(
                    "GET", SOURCE_PAGE, endpoints, max_response_bytes=LIMIT_HTML
                ),
                transport=transport,
                invocation=invocation,
                source_id=f"{DATASET}.index",
                media_types=_HTML,
                retry=RetryPolicy(),
            ).payload
        invocation.stage("discover")
        use_payload(payload, invocation, role="source_index", limit=LIMIT_HTML)
        try:
            return tuple(
                ReleaseLink(day, url)
                for day, url in discover_links(decode_html(payload)).items()
            )
        except (CaptureError, ValueError) as error:
            raise source_failure(error) from None

    return run(DISCOVER, request, work, context=context)


def _acquire(req, invocation, transport):
    invocation.stage("acquire")
    try:
        official_date = url_date(req.url)
    except (CaptureError, ValueError):
        raise OperationFailure("request.release_link_invalid") from None
    if official_date != req.as_of:
        raise OperationFailure("request.release_date_mismatch")
    endpoints = tuple(
        HttpsEndpoint(host, unquote(urlsplit(req.url).path)) for host in _HOSTS
    )
    source = receive_source(
        HttpRequest("GET", req.url, endpoints, max_response_bytes=LIMIT_XLSX),
        transport=transport,
        invocation=invocation,
        source_id=DATASET,
        media_types=frozenset(
            {
                XLSX,
                "application/octet-stream",
                "application/zip",
                "application/vnd.ms-excel",
            }
        ),
        retry=RetryPolicy(),
    )
    if not source.payload.data.startswith(b"PK\x03\x04"):
        raise OperationFailure("source.xlsx_signature_invalid")
    return source


def acquire(
    request: ReleaseLink,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[AcquiredSource]:
    return run(
        ACQUIRE,
        request,
        lambda req, inv: _acquire(req, inv, transport),
        providers={"http": transport},
        context=context,
    )


def _check_date(as_of):
    if type(as_of) is not date or as_of.day != 1 or as_of.year < 2019:
        raise OperationFailure("request.invalid_release_date")


def _observations(data: bytes, as_of: date) -> tuple[Observation, ...] | None:
    rows = csv_rows(data)
    header = rows[0]
    territories = [
        i
        for i, name in enumerate(header[2:], 2)
        if any(
            part.casefold() in {"регион", "территория", "наименование территории"}
            for part in name.split(" / ")
        )
    ]
    if len(territories) != 1:
        return None
    column = territories[0]
    period = PeriodRef("as_of", as_of)
    result = []
    for row in rows[1:]:
        territory = row[column]
        if not territory:
            return None
        perimeter = (
            "national"
            if "российская федерация" in territory.casefold()
            else "territorial"
        )
        for metric, token in zip(header[column + 1 :], row[column + 1 :]):
            if token in {"", "-", "–", "—"}:
                value, status = None, ("blank" if not token else "dash")
            elif re.fullmatch(r"[0-9]{1,18}(?:[.,][0-9]{1,10})?", token):
                value, status = Decimal(token.replace(",", ".")), "reported"
            else:
                # Keep a literal projection when the source adds an unclassified column.
                return None
            result.append(
                Observation(
                    SubjectRef("cbr.published_territory", territory),
                    MetricRef(metric, "count"),
                    period,
                    (("section", row[1]),),
                    perimeter,
                    value,
                    status,
                    f"row:{row[0]}",
                    token,
                )
            )
    return tuple(result)


def _parse(req, invocation, acquisition=None):
    invocation.stage("parse")
    _check_date(req.as_of)
    use_payload(req.payload, invocation, role="source_workbook", limit=LIMIT_XLSX)
    try:
        data, formulas = convert_xlsx(
            req.payload.data, return_formula_lineage=True, expected_date=req.as_of
        )
        count = validate_csv(data)
    except (ArchiveError, CaptureError, ParseError, ValueError) as error:
        raise source_failure(error) from None
    invocation.stage("validate")
    return build_release(
        DATASET,
        PROFILE,
        METHOD,
        req.as_of,
        data,
        count,
        invocation.used_inputs,
        observations=_observations(data, req.as_of),
        acquisition=acquisition,
        source_details={"formula_lineage": formulas},
    )


def parse(
    request: ParseOfficesRegRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedRelease]:
    return run(PARSE, request, _parse, context=context)


def capture(
    request: ReleaseLink,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[ParsedRelease]:
    def work(req, invocation):
        original = _acquire(req, invocation, transport)
        return _parse(
            ParseOfficesRegRequest(original.payload, req.as_of),
            invocation,
            original.receipt,
        )

    return run(CAPTURE, request, work, providers={"http": transport}, context=context)


def read_representation(
    request: ReadReleaseRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedRelease]:
    def work(req, invocation):
        invocation.stage("validate")
        _check_date(req.as_of)
        use_payload(
            req.payload, invocation, role="csv_representation", limit=LIMIT_XLSX
        )
        try:
            count = validate_csv(req.payload.data)
        except (CaptureError, ValueError) as error:
            raise source_failure(error) from None
        return build_release(
            DATASET,
            PROFILE,
            READ.method_version,
            req.as_of,
            req.payload.data,
            count,
            invocation.used_inputs,
            observations=_observations(req.payload.data, req.as_of),
        )

    return run(READ, request, work, context=context)


def compare(
    request: CompareReleaseRequest, *, context: ExecutionContext | None = None
) -> OperationResult[Comparison]:
    def work(req, invocation):
        decision = compare_release_inputs(req, invocation, DATASET, PROFILE)
        if decision is not None:
            return decision
        old, new = req.baseline.representation.data, req.candidate.representation.data
        return Comparison(
            "unchanged" if old == new else "revised",
            "representation.literal_comparison",
        )

    return run(COMPARE, request, work, context=context)
