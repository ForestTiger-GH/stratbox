"""The regional SME register as independent index, source, parse and comparison operations."""

from dataclasses import dataclass
from datetime import date

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
    build_release,
)
from stratbox.execution import (
    ExecutionContext,
    OperationDefinition,
    OperationFailure,
    OperationResult,
    run,
)
from stratbox.execution.acquisition import receive_source
from stratbox.execution.comparison import compare_release_inputs
from stratbox.execution.source_validation import source_failure, use_payload

from .parser import (
    COLUMNS,
    LIMIT_HTML,
    LIMIT_JSON,
    FnsError,
    decode_snapshot,
    discover_dates,
    format_source_date,
)
from .representation import read_csv, write_csv

DATASET = "fns.sme"
PROFILE = "fns.sme.regional-csv"
METHOD = "fns-sme-regional-json-1"
_HOST = "rmsp.nalog.ru"
_PAGE = HttpsEndpoint(_HOST, "/statistics.html")
_API = HttpsEndpoint(_HOST, "/statistics-proc.json")
_HTTP = frozenset({"http"})


@dataclass(frozen=True, slots=True)
class DiscoverSmeRequest:
    index: SourcePayload | None = None


@dataclass(frozen=True, slots=True)
class AcquireSmeRequest:
    as_of: date


@dataclass(frozen=True, slots=True)
class ParseSmeRequest:
    payload: SourcePayload
    as_of: date


DISCOVER = OperationDefinition(
    f"{DATASET}.discover", 1, "fns-sme-index-1", DiscoverSmeRequest, tuple,
    optional_capabilities=frozenset({"http"}),
)
ACQUIRE = OperationDefinition(
    f"{DATASET}.acquire",
    1,
    "fns-sme-regional-post-1",
    AcquireSmeRequest,
    AcquiredSource,
    _HTTP,
)
PARSE = OperationDefinition(
    f"{DATASET}.parse", 1, METHOD, ParseSmeRequest, ParsedRelease
)
CAPTURE = OperationDefinition(
    f"{DATASET}.capture", 1, METHOD, AcquireSmeRequest, ParsedRelease, _HTTP
)
READ = OperationDefinition(
    f"{DATASET}.read_representation",
    1,
    "fns-sme-csv-1",
    ReadReleaseRequest,
    ParsedRelease,
)
COMPARE = OperationDefinition(
    f"{DATASET}.compare", 1, "fns-sme-compare-1", CompareReleaseRequest, Comparison
)


def discover(
    request: DiscoverSmeRequest,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[tuple[date, ...]]:
    def work(req, invocation):
        payload = req.index
        if payload is None:
            invocation.stage("acquire_index")
            if transport is None:
                raise OperationFailure("provider.capability_missing")
            payload = receive_source(
                HttpRequest(
                    "GET",
                    f"https://{_HOST}{_PAGE.path}",
                    (_PAGE,),
                    max_response_bytes=LIMIT_HTML,
                ),
                transport=transport,
                invocation=invocation,
                source_id=f"{DATASET}.index",
                media_types=frozenset({"text/html", "application/xhtml+xml"}),
                retry=RetryPolicy(),
            ).payload
        invocation.stage("discover")
        use_payload(payload, invocation, role="source_index", limit=LIMIT_HTML)
        try:
            return tuple(discover_dates(payload.data))
        except (FnsError, ValueError) as error:
            raise source_failure(error) from None

    return run(DISCOVER, request, work, context=context)


def _check_date(value):
    if type(value) is not date or not date(2016, 8, 1) <= value <= date(2099, 12, 31):
        raise OperationFailure("request.invalid_release_date")


def _acquire(req, invocation, transport):
    invocation.stage("acquire")
    _check_date(req.as_of)
    source = receive_source(
        HttpRequest(
            "POST",
            f"https://{_HOST}{_API.path}",
            (_API,),
            {"accept": "application/json"},
            form_fields={"statDate": format_source_date(req.as_of)},
            max_response_bytes=LIMIT_JSON,
            read_only_post=True,
        ),
        transport=transport,
        invocation=invocation,
        source_id=DATASET,
        media_types=frozenset({"application/json", "text/json", "text/plain"}),
        retry=RetryPolicy(),
    )
    if not source.payload.data.lstrip().startswith(b"["):
        raise OperationFailure("source.json_signature_invalid")
    return source


def acquire(
    request: AcquireSmeRequest,
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


def _release(day, rows, data, invocation, *, method=METHOD, acquisition=None):
    period = PeriodRef("as_of", day)
    observations = tuple(
        Observation(
            SubjectRef("fns.ssrf", code),
            MetricRef(metric, "count"),
            period,
            (("region_label", row[1]),),
            "published_sme_register",
            int(token),
            "reported",
            f"region:{code}",
            token,
        )
        for code, row in sorted(rows.items())
        for metric, token in zip(COLUMNS[2:], row[2:])
    )
    return build_release(
        DATASET,
        PROFILE,
        method,
        day,
        data,
        len(rows),
        invocation.used_inputs,
        observations=observations,
        acquisition=acquisition,
    )


def _parse(req, invocation, acquisition=None):
    invocation.stage("parse")
    _check_date(req.as_of)
    use_payload(req.payload, invocation, role="source_json", limit=LIMIT_JSON)
    try:
        rows = decode_snapshot(req.payload.data, req.as_of)
        data = write_csv(rows)
        read_csv(data)
    except FnsError as error:
        raise source_failure(error) from None
    invocation.stage("validate")
    return _release(req.as_of, rows, data, invocation, acquisition=acquisition)


def parse(
    request: ParseSmeRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedRelease]:
    return run(PARSE, request, _parse, context=context)


def capture(
    request: AcquireSmeRequest,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[ParsedRelease]:
    def work(req, invocation):
        acquired = _acquire(req, invocation, transport)
        return _parse(
            ParseSmeRequest(acquired.payload, req.as_of), invocation, acquired.receipt
        )

    return run(CAPTURE, request, work, providers={"http": transport}, context=context)


def read_representation(
    request: ReadReleaseRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedRelease]:
    def work(req, invocation):
        invocation.stage("validate")
        _check_date(req.as_of)
        use_payload(
            req.payload, invocation, role="csv_representation", limit=LIMIT_JSON
        )
        try:
            rows = read_csv(req.payload.data)
        except FnsError as error:
            raise source_failure(error) from None
        return _release(
            req.as_of, rows, req.payload.data, invocation, method=READ.method_version
        )

    return run(READ, request, work, context=context)


def compare(
    request: CompareReleaseRequest, *, context: ExecutionContext | None = None
) -> OperationResult[Comparison]:
    def work(req, invocation):
        decision = compare_release_inputs(req, invocation, DATASET, PROFILE)
        if decision is not None:
            return decision
        try:
            older = read_csv(req.baseline.representation.data)
            newer = read_csv(req.candidate.representation.data)
        except FnsError:
            return Comparison("indeterminate", "comparison.invalid_representation")
        if len(newer) * 10 < len(older) * 9:
            return Comparison("indeterminate", "source.coverage_drop")
        changed = tuple(
            sorted(
                key
                for key in older.keys() | newer.keys()
                if older.get(key) != newer.get(key)
            )
        )
        return Comparison(
            "revised" if changed else "unchanged", "source.regional_rows", changed
        )

    return run(COMPARE, request, work, context=context)
