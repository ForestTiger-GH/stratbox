"""The regional SME register as independent index, source, parse and comparison operations."""

from datetime import date
from decimal import Decimal

from stratbox.core.network import HttpRequest, HttpTransport, HttpsEndpoint, RetryPolicy
from stratbox.shared.evidence import (
    AcquiredSource,
)
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.observations import MetricRef, Observation, PeriodRef, SubjectRef
from stratbox.shared.data.releases import (
    CompareReleaseRequest,
    ParsedRelease,
    ReadReleaseRequest,
    build_release,
)
from stratbox.core.execution import (
    ExecutionContext, OperationFailure, OperationResult, run,
)
from stratbox.core.operations.source.acquisition import receive_source
from stratbox.core.operations.source.comparison import compare_release_inputs, explain_comparison
from stratbox.core.operations.source.validation import source_failure, use_payload

from ...tables.sme.parser import (
    COLUMNS,
    LIMIT_HTML,
    LIMIT_JSON,
    FnsError,
    decode_snapshot,
    discover_dates,
    format_source_date,
)
from ...products.sme.regional_csv import read_csv, write_csv
from ..receipts import record_acquired, record_control

from .definitions import (
    ACQUIRE, AcquireSmeRequest, CAPTURE, COMPARE, DATASET, DISCOVER, DiscoverSmeRequest, METHOD, PARSE, ParseSmeRequest, READ, _HTTP,
)

PROFILE = "fns.sme.regional-csv"
from ...publications.sme.access import _check_date, acquire_source, discover_dates_from_source


def discover(request: DiscoverSmeRequest, *, transport=None, context=None):
    return run(DISCOVER, request,
        lambda req, inv: record_control(discover_dates_from_source(req.index, inv, transport), inv),
        providers={"http": transport}, context=context)


def _acquire(req, invocation, transport):
    return acquire_source(req.as_of, invocation, transport)


def acquire(
    request: AcquireSmeRequest,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[AcquiredSource]:
    return run(
        ACQUIRE,
        request,
        lambda req, inv: record_acquired(_acquire(req, inv, transport), inv, req.as_of),
        providers={"http": transport},
        context=context,
    )


def _release(day, rows, data, invocation, *, method=METHOD, acquisition=None):
    period = PeriodRef("as_of", day)
    observations = tuple(
        Observation(
            SubjectRef("fns.ssrf", code),
            MetricRef(metric, "count", "stock", "fns.sme.regional-counts.v1", Decimal(1)),
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
        facts_method=METHOD if method != METHOD else None,
        acquisition=acquisition,
        excluded_fields=("country_rows", "federal_district_rows", "cnt_ul_total", "cnt_ip_total"),
        scope="fns.sme.regional_counts",
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
    def evaluate(req, invocation):
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

    def work(req, invocation):
        return record_control(explain_comparison(evaluate(req, invocation), req, invocation), invocation)

    return run(COMPARE, request, work, context=context)
