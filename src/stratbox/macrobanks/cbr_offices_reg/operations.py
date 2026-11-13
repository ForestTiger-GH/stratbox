"""Territorial office releases published in the Bank of Russia workbook."""

from collections import Counter
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
    ByteIdentity,
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
    Completion,
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

from .parser import AmbiguousBlock, CaptureError, LIMIT_XLSX, convert_xlsx
from .representation import count_label, validate_csv
from .source import LIMIT_HTML, SOURCE_PAGE, discover as discover_links, url_date

DATASET = "cbr.offices_reg"
PROFILE = "cbr.offices_reg.wide-csv"
METHOD = "cbr-offices-reg-xlsx-3"
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
    sheet: str | None = None
    national_row: int | None = None


@dataclass(frozen=True, slots=True)
class OfficesRegCandidates:
    source_identity: ByteIdentity
    blocks: tuple[tuple[str, int, int], ...]


DISCOVER = OperationDefinition(
    f"{DATASET}.discover",
    1,
    "cbr-offices-reg-index-1",
    DiscoverOfficesRegRequest,
    tuple,
    optional_capabilities=frozenset({"http"}),
)
ACQUIRE = OperationDefinition(
    f"{DATASET}.acquire", 1, METHOD, ReleaseLink, AcquiredSource, _HTTP
)
PARSE = OperationDefinition(
    f"{DATASET}.parse", 2, METHOD, ParseOfficesRegRequest,
    (ParsedRelease, OfficesRegCandidates), partial_allowed=True,
)
CAPTURE = OperationDefinition(
    f"{DATASET}.capture", 2, METHOD, ReleaseLink,
    (ParsedRelease, OfficesRegCandidates), _HTTP, partial_allowed=True,
)
READ = OperationDefinition(
    f"{DATASET}.read_representation",
    1,
    "cbr-offices-reg-csv-2",
    ReadReleaseRequest,
    ParsedRelease,
)
COMPARE = OperationDefinition(
    f"{DATASET}.compare",
    1,
    "cbr-offices-reg-compare-2",
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


_MISSING = frozenset({"", "-", "–", "—"})


def _count_token(token: str) -> bool:
    return token in _MISSING or re.fullmatch(r"[0-9]{1,18}(?:[.,]0{1,10})?", token) is not None


def _observations(data: bytes, as_of: date) -> tuple[tuple[Observation, ...] | None, tuple[str, ...]]:
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
        return None, tuple(header[2:])
    column = territories[0]
    period = PeriodRef("as_of", as_of)
    metrics = [count_label(heading) for heading in header[column + 1:]]
    duplicates = Counter(metrics)
    fields = []
    excluded = list(header[2:column])
    for index, (heading, metric) in enumerate(zip(header[column + 1:], metrics), column + 1):
        if (metric is None or duplicates[metric] != 1
                or any(not _count_token(row[index]) for row in rows[1:])):
            excluded.append(heading)
        else:
            fields.append((index, metric))
    if not fields:
        return None, tuple(excluded)
    result = []
    for row in rows[1:]:
        territory = row[column]
        if not territory:
            return None, tuple(header[2:])
        perimeter = (
            "national"
            if "российская федерация" in territory.casefold()
            else "territorial"
        )
        for index, metric in fields:
            token = row[index]
            if token in _MISSING:
                value, status = None, ("blank" if not token else "dash")
            else:
                value, status = Decimal(token.replace(",", ".")), "reported"
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
    return tuple(result), tuple(excluded)


def _parse(req, invocation, acquisition=None):
    invocation.stage("parse")
    _check_date(req.as_of)
    if req.sheet is not None and (not isinstance(req.sheet, str) or not 1 <= len(req.sheet) <= 255):
        raise OperationFailure("request.workbook_sheet_invalid")
    if req.national_row is not None and (
        type(req.national_row) is not int or not 1 <= req.national_row <= 1_048_576
    ):
        raise OperationFailure("request.workbook_row_invalid")
    use_payload(req.payload, invocation, role="source_workbook", limit=LIMIT_XLSX)
    evidence = {}
    try:
        data, formulas = convert_xlsx(
            req.payload.data, return_formula_lineage=True, expected_date=req.as_of,
            sheet_name=req.sheet, national_row=req.national_row, budget=invocation.budget,
            checkpoint=invocation.check_cancelled, evidence=evidence,
        )
        count = validate_csv(data)
    except AmbiguousBlock as error:
        return Completion(
            OfficesRegCandidates(req.payload.identity, error.candidates),
            "partial", "source.xlsx_national_total_ambiguous",
        )
    except (ArchiveError, CaptureError, ParseError, ValueError) as error:
        raise source_failure(error) from None
    invocation.stage("validate")
    observations, excluded = _observations(data, req.as_of)
    parameters = {
        key: value for key, value in {"sheet": req.sheet, "national_row": req.national_row}.items()
        if value is not None
    }
    return build_release(
        DATASET,
        PROFILE,
        METHOD,
        req.as_of,
        data,
        count,
        invocation.used_inputs,
        observations=observations, excluded_fields=excluded,
        acquisition=acquisition,
        parameters=parameters,
        source_details={"formula_lineage": formulas, "selection": evidence},
    )


def parse(
    request: ParseOfficesRegRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedRelease | OfficesRegCandidates]:
    return run(PARSE, request, _parse, context=context)


def capture(
    request: ReleaseLink,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[ParsedRelease | OfficesRegCandidates]:
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
        observations, excluded = _observations(req.payload.data, req.as_of)
        return build_release(
            DATASET,
            PROFILE,
            READ.method_version,
            req.as_of,
            req.payload.data,
            count,
            invocation.used_inputs,
            observations=observations, excluded_fields=excluded,
        )

    return run(READ, request, work, context=context)


def compare(
    request: CompareReleaseRequest, *, context: ExecutionContext | None = None
) -> OperationResult[Comparison]:
    def work(req, invocation):
        decision = compare_release_inputs(req, invocation, DATASET, PROFILE)
        if decision is not None:
            return decision
        old, new = req.baseline, req.candidate
        if (old.facts_identity is not None and new.facts_identity is not None
                and old.batch is not None and new.batch is not None):
            old_metrics = {item.metric for item in old.batch.observations}
            new_metrics = {item.metric for item in new.batch.observations}
            if old_metrics != new_metrics:
                return Comparison("indeterminate", "comparison.indicator_scope_changed")
            old_geography = {item.subject for item in old.batch.observations}
            new_geography = {item.subject for item in new.batch.observations}
            if not old_geography <= new_geography:
                return Comparison("indeterminate", "comparison.geographic_coverage_dropped")
            return Comparison(
                "unchanged" if old.facts_identity == new.facts_identity else "revised",
                "comparison.territorial_observations",
            )
        if (old.representation.identity == new.representation.identity
                and old.dataset_version.method_version == new.dataset_version.method_version
                and old.qualification == new.qualification):
            return Comparison("unchanged", "representation.literal_comparison")
        return Comparison("indeterminate", "comparison.qualification_missing")

    return run(COMPARE, request, work, context=context)
