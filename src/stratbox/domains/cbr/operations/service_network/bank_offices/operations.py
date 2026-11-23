"""Daily office capture, independent of storage and publication."""

from datetime import date, tzinfo

from stratbox.core.network import HttpRequest, HttpTransport, HttpsEndpoint, RetryPolicy
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.domains.cbr.tables.service_network.context import source_uses
from stratbox.shared.data.releases import (
    CompareReleaseRequest,
    ParsedRelease,
    build_release,
    csv_rows,
)
from stratbox.core.execution import (
    ExecutionContext, OperationFailure, OperationResult, run,
)
from stratbox.core.operations.source.acquisition import receive_source
from stratbox.core.operations.source.comparison import compare_release_inputs, explain_comparison
from stratbox.core.operations.source.validation import (
    decode_html,
    source_failure,
    use_payload,
)

from stratbox.domains.cbr.tables.service_network.bank_offices.contracts import AcquiredOffices, AcquireOfficesRequest, ParseOfficesRequest, ReadOfficesRequest
from stratbox.domains.cbr.tables.service_network.bank_offices.parser import CaptureError, MAX_CSV, MAX_HTML, KNOWN_CONTEXT, extract_records
from stratbox.domains.cbr.tables.service_network.bank_offices.representation import serialize_csv, validate_csv_bytes

from stratbox.domains.cbr.operations.service_network.bank_offices.definitions import ACQUIRE, CAPTURE, COMPARE, DATASET, METHOD, PARSE, READ

from stratbox.domains.cbr.tables.service_network.bank_offices.observations import _observations

PROFILE = "cbr.offices.wide-csv"
_PATH = "/banking_sector/credit/cstat/"
from stratbox.domains.cbr.publications.profiles import acquisition_profile
_URL = acquisition_profile("cbr.route.bank_offices").default_url
_ENDPOINTS = tuple(HttpsEndpoint(host, _PATH) for host in ("www.cbr.ru", "cbr.ru"))


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
        source_uses=source_uses(DATASET, request.payload, request.captured_on, METHOD),
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
    request: ReadOfficesRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedRelease]:
    def work(req, invocation):
        invocation.stage("validate")
        if type(req.captured_on) is not date or (req.official_as_of is not None and type(req.official_as_of) is not date):
            raise OperationFailure("request.invalid_date")
        basis = req.period_basis or ("as_of" if req.official_as_of is not None else "unknown")
        if basis not in {"capture", "as_of", "unknown"} or (basis == "as_of") != (req.official_as_of is not None):
            raise OperationFailure("request.observation_period_invalid")
        use_payload(req.payload, invocation, role="csv_representation", limit=MAX_CSV)
        try:
            count, _ = validate_csv_bytes(req.payload.data)
        except CaptureError as error:
            raise source_failure(error) from None
        rows = csv_rows(req.payload.data)
        return build_release(
            DATASET,
            PROFILE,
            READ.method_id,
            req.captured_on,
            req.payload.data,
            count,
            invocation.used_inputs,
            facts_method=METHOD,
            observations=_observations(rows, req.captured_on, req.official_as_of) if basis != "unknown" else None,
            source_uses=source_uses(DATASET, req.payload, req.captured_on, METHOD),
            parameters={"official_as_of": req.official_as_of, "period_basis": basis},
            source_details={"captured_on": req.captured_on, "official_as_of": req.official_as_of,
                            "period_basis": basis},
        )

    return run(READ, request, work, context=context)


def compare(
    request: CompareReleaseRequest, *, context: ExecutionContext | None = None
) -> OperationResult[Comparison]:
    def evaluate(req, invocation):
        decision = compare_release_inputs(req, invocation, DATASET, PROFILE)
        if decision is not None and decision.state != "new_release":
            return decision
        old, new = req.baseline, req.candidate
        old_official = (old.source_details or {}).get("official_as_of")
        new_official = (new.source_details or {}).get("official_as_of")
        if old_official is not None and new_official is not None and old_official != new_official:
            return Comparison("new_release", "comparison.official_reference_date_changed")
        if (old_official is None) != (new_official is None):
            return Comparison("indeterminate", "comparison.observation_date_qualification_changed")
        if (old.facts_method or old.dataset_version.method_version) != (new.facts_method or new.dataset_version.method_version):
            return Comparison("indeterminate", "comparison.method_changed")
        if old_official is None and old.as_of != new.as_of:
            if (old.representation.identity == new.representation.identity
                    and old.dataset_version.method_version == new.dataset_version.method_version):
                return Comparison("unchanged", "comparison.capture_bytes_unchanged_official_date_unknown")
            return Comparison("revised", "comparison.capture_content_changed_official_date_unknown")
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
        result = evaluate(req, invocation)
        same_issue = None
        if isinstance(req.baseline, ParsedRelease) and req.baseline_state == "available":
            old_official = (req.baseline.source_details or {}).get("official_as_of")
            new_official = (req.candidate.source_details or {}).get("official_as_of")
            if old_official is not None or new_official is not None:
                same_issue = old_official is not None and old_official == new_official
        return explain_comparison(result, req, invocation, same_issue=same_issue)

    return run(COMPARE, request, work, context=context)
