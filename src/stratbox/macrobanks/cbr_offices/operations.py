"""Daily office capture, independent of storage and publication."""

from datetime import date, tzinfo
import re

from stratbox.base.net import HttpRequest, HttpTransport, HttpsEndpoint, RetryPolicy
from stratbox.data import Comparison, MetricRef, Observation, PeriodRef, SubjectRef, UsedInputReceipt
from stratbox.data.releases import (
    CompareReleaseRequest,
    ParsedRelease,
    ReadReleaseRequest,
    build_release,
    csv_rows,
)
from stratbox.execution import (
    ExecutionContext,
    OperationDefinition,
    OperationFailure,
    OperationResult,
    run,
)
from stratbox.execution.acquisition import receive_source
from stratbox.execution.comparison import compare_release_inputs, explain_comparison
from stratbox.execution.source_validation import (
    decode_html,
    source_failure,
    use_payload,
)

from .contracts import AcquiredOffices, AcquireOfficesRequest, ParseOfficesRequest
from .parser import CaptureError, MAX_CSV, MAX_HTML, KNOWN_CONTEXT, extract_records
from .representation import serialize_csv, validate_csv_bytes

DATASET = "cbr.offices"
PROFILE = "cbr.offices.wide-csv"
METHOD = "cbr-offices-html-1"
_PATH = "/banking_sector/credit/cstat/"
_URL = "https://www.cbr.ru" + _PATH
_ENDPOINTS = tuple(HttpsEndpoint(host, _PATH) for host in ("www.cbr.ru", "cbr.ru"))
_HTTP = frozenset({"http"})
PARSE = OperationDefinition(
    f"{DATASET}.parse", 1, METHOD, ParseOfficesRequest, ParsedRelease
)
ACQUIRE = OperationDefinition(
    f"{DATASET}.acquire",
    2,
    "cbr-offices-http-2",
    AcquireOfficesRequest,
    AcquiredOffices,
    _HTTP,
)
CAPTURE = OperationDefinition(
    f"{DATASET}.capture", 2, METHOD, AcquireOfficesRequest, ParsedRelease, _HTTP
)
READ = OperationDefinition(
    f"{DATASET}.read_representation",
    1,
    "cbr-offices-csv-1",
    ReadReleaseRequest,
    ParsedRelease,
)
COMPARE = OperationDefinition(
    f"{DATASET}.compare", 2, "cbr-offices-compare-1", CompareReleaseRequest, Comparison
)


def _acquire(request, invocation, transport):
    invocation.stage("acquire")
    if request.capture_zone is None or not isinstance(request.capture_zone, tzinfo):
        raise OperationFailure("request.capture_zone_required")
    source = receive_source(
        HttpRequest(
            "GET",
            _URL,
            _ENDPOINTS,
            {"accept": "text/html"},
            max_response_bytes=MAX_HTML,
        ),
        transport=transport,
        source_id=DATASET,
        invocation=invocation,
        media_types=frozenset({"text/html", "application/xhtml+xml"}),
        retry=RetryPolicy(),
        baseline=request.baseline,
    )
    # Retain the received-byte evidence even if the page is for a different series.
    if KNOWN_CONTEXT not in " ".join(decode_html(source.payload).split()):
        invocation.use(UsedInputReceipt.for_payload(source.payload, "unqualified_response"))
        raise OperationFailure("source.context_changed")
    return AcquiredOffices(
        source, source.receipt.observed_at_utc.astimezone(request.capture_zone).date()
    )



def acquire(
    request: AcquireOfficesRequest,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[AcquiredOffices]:
    return run(
        ACQUIRE,
        request,
        lambda req, inv: _acquire(req, inv, transport),
        providers={"http": transport},
        context=context,
    )


def _observations(rows, captured_on, official_as_of):
    period = (
        PeriodRef("as_of", official_as_of)
        if official_as_of is not None
        else PeriodRef("capture", captured_on)
    )
    observations = []
    for source_row, section, region, _bank, registration, *tokens in rows[1:]:
        for header, token in zip(rows[0][5:], tokens):
            value = (
                int(token)
                if re.fullmatch(r"[0-9]{1,18}", token, re.ASCII)
                else token or None
            )
            status = "reported"
            if token in {"", "-", "–", "—"}:
                status = "blank" if not token else "dash"
                value = None
            observations.append(
                Observation(
                    SubjectRef("cbr.bank.registration", registration),
                    MetricRef(header, "count"),
                    period,
                    (("region", region), ("section", section)),
                    "published_bank_region",
                    value,
                    status,
                    f"row:{source_row}",
                    token,
                )
            )
    return tuple(observations)


def _parse(request, invocation, acquisition=None):
    invocation.stage("parse")
    if type(request.captured_on) is not date or (
        request.official_as_of is not None and type(request.official_as_of) is not date
    ):
        raise OperationFailure("request.invalid_date")
    use_payload(request.payload, invocation, role="source_html", limit=MAX_HTML)
    try:
        rows, count = extract_records(decode_html(request.payload))
        data = serialize_csv(rows)
        validate_csv_bytes(data)
    except (CaptureError, UnicodeError, ValueError) as error:
        raise source_failure(error) from None
    invocation.stage("validate")
    return build_release(
        DATASET,
        PROFILE,
        METHOD,
        request.captured_on,
        data,
        count,
        invocation.used_inputs,
        observations=_observations(rows, request.captured_on, request.official_as_of),
        parameters={"official_as_of": request.official_as_of},
        acquisition=acquisition,
        source_details={
            "captured_on": request.captured_on,
            "official_as_of": request.official_as_of,
        },
    )


def parse(
    request: ParseOfficesRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedRelease]:
    return run(PARSE, request, _parse, context=context)


def capture(
    request: AcquireOfficesRequest,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[ParsedRelease]:
    def work(req, invocation):
        acquired = _acquire(req, invocation, transport)
        return _parse(
            ParseOfficesRequest(acquired.payload, acquired.capture_date),
            invocation,
            acquired.source.receipt,
        )

    return run(CAPTURE, request, work, providers={"http": transport}, context=context)


def read_representation(
    request: ReadReleaseRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedRelease]:
    def work(req, invocation):
        invocation.stage("validate")
        use_payload(req.payload, invocation, role="csv_representation", limit=MAX_CSV)
        try:
            count, _ = validate_csv_bytes(req.payload.data)
        except CaptureError as error:
            raise source_failure(error) from None
        rows = csv_rows(req.payload.data)
        return build_release(
            DATASET,
            PROFILE,
            READ.method_version,
            req.as_of,
            req.payload.data,
            count,
            invocation.used_inputs,
            facts_method=METHOD,
            observations=_observations(rows, req.as_of, None),
        )

    return run(READ, request, work, context=context)


def compare(
    request: CompareReleaseRequest, *, context: ExecutionContext | None = None
) -> OperationResult[Comparison]:
    def evaluate(req, invocation):
        decision = compare_release_inputs(req, invocation, DATASET, PROFILE)
        if decision is not None:
            return decision
        old, new = req.baseline, req.candidate
        old_periods = {item.period for item in old.batch.observations} if old.batch else set()
        new_periods = {item.period for item in new.batch.observations} if new.batch else set()
        if old_periods != new_periods or old.facts_identity is None or new.facts_identity is None:
            return Comparison("indeterminate", "comparison.qualification_missing")
        if old.facts_identity == new.facts_identity:
            return Comparison("unchanged", "comparison.offices_observations")
        old_metrics = {item.metric for item in old.batch.observations}
        new_metrics = {item.metric for item in new.batch.observations}
        if old_metrics != new_metrics:
            return Comparison("indeterminate", "comparison.indicator_scope_changed")
        return Comparison(
            "revised",
            "comparison.offices_observations",
        )

    def work(req, invocation):
        return explain_comparison(evaluate(req, invocation), req, invocation)

    return run(COMPARE, request, work, context=context)
