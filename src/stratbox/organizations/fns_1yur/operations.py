"""Dated 1-YUR acquisition, workbook evidence and identity-only CSV."""

from dataclasses import dataclass
from datetime import date
from urllib.parse import unquote, urlsplit
from xml.etree.ElementTree import ParseError

from stratbox.base.ioapi.archive_bytes import ArchiveError, ArchiveReader
from stratbox.base.net import HttpRequest, HttpTransport, HttpsEndpoint, RetryPolicy
from stratbox.base.utils.optional_deps import MissingExtra
from stratbox.data import (
    AcquiredSource,
    Comparison,
    MetricRef,
    Observation,
    PeriodRef,
    SourcePayload,
    SubjectRef,
    UsedInputReceipt,
)
from stratbox.data.releases import (
    CompareReleaseRequest,
    ParsedRelease,
    ReadReleaseRequest,
    ReleaseLink,
    build_release,
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
from stratbox.execution.comparison import compare_release_inputs, explain_comparison
from stratbox.execution.source_validation import source_failure, use_payload

from .archive import select_workbook
from .history import extract_observations
from .parser import OLE
from .representation import read_canonical
from .semantics import MAP_VERSION, SchemaError, convert, epoch
from .source import (
    BASE,
    MAX_HTML,
    PAGES,
    SourceError,
    allowed_url,
    discover_year_pages,
    extract_releases,
)
from .source_history import MAX_SOURCE, MIN_DATE, releases_from_page

DATASET = "fns.1yur"
PROFILE = "fns.1yur.identity-csv"
METHOD = "fns-1yur-part-i-1"
_HOSTS = ("www.nalog.gov.ru", "www.nalog.ru")
_HTTP = frozenset({"http"})
_HTML = frozenset({"text/html", "application/xhtml+xml"})


@dataclass(frozen=True, slots=True)
class Discover1YurRequest:
    year: int
    index: SourcePayload | None = None
    index_url: str | None = None


@dataclass(frozen=True, slots=True)
class ReleaseIndex:
    releases: tuple[ReleaseLink, ...]
    missing_assets: tuple[date, ...]


@dataclass(frozen=True, slots=True)
class Parse1YurRequest:
    payload: SourcePayload
    as_of: date


DISCOVER = OperationDefinition(
    f"{DATASET}.discover", 1, "fns-1yur-index-1", Discover1YurRequest, ReleaseIndex,
    optional_capabilities=frozenset({"http"}),
)
ACQUIRE = OperationDefinition(
    f"{DATASET}.acquire", 1, METHOD, ReleaseLink, AcquiredSource, _HTTP
)
_RAR = frozenset({"archive_decoder"})
PARSE = OperationDefinition(
    f"{DATASET}.parse", 1, METHOD, Parse1YurRequest, ParsedRelease, optional_capabilities=_RAR,
)
CAPTURE = OperationDefinition(
    f"{DATASET}.capture", 1, METHOD, ReleaseLink, ParsedRelease, _HTTP, optional_capabilities=_RAR,
)
READ = OperationDefinition(
    f"{DATASET}.read_representation",
    1,
    "fns-1yur-csv-1",
    ReadReleaseRequest,
    ParsedRelease,
)
COMPARE = OperationDefinition(
    f"{DATASET}.compare", 2, "fns-1yur-compare-1", CompareReleaseRequest, Comparison
)


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


def discover(
    request: Discover1YurRequest,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[ReleaseIndex]:
    def work(req, invocation):
        if type(req.year) is not int or not MIN_DATE.year <= req.year <= 2099:
            raise OperationFailure("request.invalid_year")
        page = req.index_url or (
            f"{BASE}{PAGES[req.year]}/" if req.year in PAGES else None
        )
        if req.index is None and transport is None:
            raise OperationFailure("provider.capability_missing")
        try:
            if page is None:
                if req.index is not None:
                    raise OperationFailure("request.index_url_required")
                invocation.stage("discover_year")
                index = _index(BASE, transport, invocation)
                use_payload(index, invocation, role="forms_index", limit=MAX_HTML)
                page = discover_year_pages(index.data).get(req.year)
                if page is None:
                    raise OperationFailure("source.year_unavailable")
            allowed_url(page, "page")
            if page == BASE:
                raise OperationFailure("request.release_index_required")
            invocation.stage("discover_releases")
            payload = (
                req.index
                if req.index is not None
                else _index(page, transport, invocation)
            )
            use_payload(payload, invocation, role="source_index", limit=MAX_HTML)
            missing = set()
            found = releases_from_page(
                payload.data, page, missing=missing, require_releases=False
            )
            if not found and not missing:
                found = extract_releases(payload.data, page)
            releases = tuple(
                ReleaseLink(day, url)
                for day, url in sorted(found.items())
                if day.year == req.year
            )
            gaps = tuple(
                sorted(day for day in missing - found.keys() if day.year == req.year)
            )
            if not releases and not gaps:
                raise OperationFailure("source.year_unavailable")
            return ReleaseIndex(releases, gaps)
        except (SourceError, ValueError) as error:
            raise source_failure(error) from None

    return run(DISCOVER, request, work, context=context)


def _acquire(req, invocation, transport):
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


def _build(as_of, data, invocation, *, method, acquisition=None, details=None):
    fields, rows = read_canonical(data)
    period = PeriodRef("as_of", as_of)
    observations = []
    for index, ((code, label), row) in enumerate(rows.items(), 2):
        perimeter = (
            "published_territory"
            if code
            else ("published_national" if index == 2 else "published_district")
        )
        for field, token in zip(fields[2:], row[2:]):
            measure, kind = field[3:].split("__", 1)
            observations.append(
                Observation(
                    SubjectRef("fns.1yur.geography", code or label),
                    MetricRef(measure, "count"),
                    period,
                    (("legal_kind", kind), ("published_label", label)),
                    perimeter,
                    int(token),
                    "reported",
                    f"csv-row:{index}",
                    token,
                )
            )
    return build_release(
        DATASET,
        PROFILE,
        method,
        as_of,
        data,
        len(rows),
        invocation.used_inputs,
        observations=tuple(observations),
        parameters={"epoch": epoch(as_of)},
        resources={"field_map": MAP_VERSION},
        facts_method=METHOD if method != METHOD else None,
        acquisition=acquisition,
        source_details=details,
    )


def _parse(req, invocation, rar_reader, acquisition=None):
    _check_date(req.as_of)
    invocation.stage("identify_workbook")
    use_payload(req.payload, invocation, role="source_asset", limit=MAX_SOURCE)
    try:
        if req.payload.data.startswith(b"Rar!") and invocation.context.profile == "managed":
            invocation.require_provider("archive_decoder", rar_reader)
        workbook = select_workbook(
            req.payload, req.as_of, rar_reader=rar_reader, budget=invocation.budget,
            checkpoint=invocation.check_cancelled,
        )
        invocation.stage("parse_workbook")
        if workbook.member is not None:
            invocation.use(
                UsedInputReceipt.for_payload(
                    workbook.payload,
                    "workbook_member",
                    container=req.payload.identity,
                    member=workbook.member,
                )
            )
        original, workbook_facts = extract_observations(
            workbook.payload.data, req.as_of, checkpoint=invocation.check_cancelled,
            budget=invocation.budget, depth=2 if workbook.member is not None else 1,
        )
        invocation.stage("map_source_fields")
        canonical, mapping_facts = convert(req.as_of, original)
        return _build(
            req.as_of,
            canonical,
            invocation,
            method=METHOD,
            acquisition=acquisition,
            details={
                "container_format": workbook.container_format,
                "member": workbook.member,
                "workbook": workbook_facts,
                "mapping": mapping_facts,
            },
        )
    except MissingExtra:
        raise OperationFailure("provider.capability_missing") from None
    except (ArchiveError, SourceError, SchemaError, ParseError, ValueError) as error:
        raise source_failure(error) from None


def parse(
    request: Parse1YurRequest,
    *,
    rar_reader: ArchiveReader | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[ParsedRelease]:
    return run(
        PARSE, request, lambda req, inv: _parse(req, inv, rar_reader), context=context
    )


def capture(
    request: ReleaseLink,
    *,
    transport: HttpTransport | None = None,
    rar_reader: ArchiveReader | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[ParsedRelease]:
    def work(req, invocation):
        source = _acquire(req, invocation, transport)
        return _parse(
            Parse1YurRequest(source.payload, req.as_of),
            invocation,
            rar_reader,
            source.receipt,
        )

    return run(CAPTURE, request, work, providers={"http": transport}, context=context)


def read_representation(
    request: ReadReleaseRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedRelease]:
    def work(req, invocation):
        invocation.stage("validate")
        _check_date(req.as_of)
        use_payload(
            req.payload, invocation, role="csv_representation", limit=MAX_SOURCE
        )
        try:
            return _build(
                req.as_of, req.payload.data, invocation, method=READ.method_version
            )
        except (SchemaError, ValueError) as error:
            raise source_failure(error) from None

    return run(READ, request, work, context=context)


def compare(
    request: CompareReleaseRequest, *, context: ExecutionContext | None = None
) -> OperationResult[Comparison]:
    def evaluate(req, invocation):
        decision = compare_release_inputs(req, invocation, DATASET, PROFILE)
        if decision is not None:
            return decision
        try:
            old_fields, old = read_canonical(req.baseline.representation.data)
            new_fields, new = read_canonical(req.candidate.representation.data)
        except SchemaError:
            return Comparison("indeterminate", "comparison.invalid_representation")
        if old_fields != new_fields:
            return Comparison("indeterminate", "source.schema_changed")
        changed = tuple(
            f"{code}:{label}"
            for code, label in sorted(old.keys() | new.keys())
            if old.get((code, label)) != new.get((code, label))
        )
        return Comparison(
            "revised" if changed else "unchanged", "source.geography_rows", changed
        )

    def work(req, invocation):
        return explain_comparison(evaluate(req, invocation), req, invocation)

    return run(COMPARE, request, work, context=context)
