"""Territorial office releases published in the Bank of Russia workbook."""

from datetime import date
import re
from urllib.parse import unquote, urlsplit
from xml.etree.ElementTree import ParseError

from stratbox.core.formats.archives.members import ArchiveError
from stratbox.core.network import HttpRequest, HttpTransport, HttpsEndpoint, RetryPolicy
from stratbox.shared.evidence import (
    AcquiredSource,
)
from stratbox.shared.data.comparison import Comparison
from stratbox.domains.cbr.tables.service_network.context import source_uses
from stratbox.shared.data.releases import CompareReleaseRequest, ParsedRelease, ReleaseLink, build_release
from stratbox.shared.data.representation import XLSX
from stratbox.core.execution import (
    Completion, ExecutionContext, OperationFailure, OperationResult, run,
)
from stratbox.core.operations.source.acquisition import receive_source
from stratbox.core.operations.source.comparison import compare_release_inputs, explain_comparison
from stratbox.core.operations.source.validation import (
    decode_html,
    source_failure,
    use_payload,
)

from stratbox.domains.cbr.tables.service_network.territorial_offices.parser import AmbiguousBlock, CaptureError, LIMIT_XLSX, convert_xlsx
from stratbox.domains.cbr.tables.service_network.territorial_offices.representation import validate_csv, validate_source_details
from stratbox.domains.cbr.tables.service_network.territorial_offices.source import LIMIT_HTML, SOURCE_PAGE, discover as discover_links, url_date

from stratbox.domains.cbr.operations.service_network.territorial_offices.definitions import ACQUIRE, CAPTURE, COMPARE, DATASET, DISCOVER, DiscoverOfficesRegRequest, METHOD, OfficesRegCandidates, PARSE, ParseOfficesRegRequest, READ, ReadOfficesRegRequest

from stratbox.domains.cbr.tables.service_network.territorial_offices.observations import _observations

PROFILE = "cbr.offices_reg.wide-csv"
_HOSTS = ("www.cbr.ru", "cbr.ru")
_HTML = frozenset({"text/html", "application/xhtml+xml"})


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

    return run(DISCOVER, request, work, providers={"http": transport}, context=context)


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


def _parse(req, invocation, acquisition=None):
    invocation.stage("parse")
    _check_date(req.as_of)
    if req.sheet is not None and (not isinstance(req.sheet, str) or not 1 <= len(req.sheet) <= 255):
        raise OperationFailure("request.workbook_sheet_invalid")
    for row in (req.national_row, req.last_row):
        if row is not None and (type(row) is not int or not 1 <= row <= 1_048_576):
            raise OperationFailure("request.workbook_row_invalid")
    use_payload(req.payload, invocation, role="source_workbook", limit=LIMIT_XLSX)
    evidence = {}
    try:
        data, formulas = convert_xlsx(
            req.payload.data, return_formula_lineage=True, expected_date=req.as_of,
            sheet_name=req.sheet, national_row=req.national_row, budget=invocation.budget,
            last_row=req.last_row, checkpoint=invocation.check_cancelled, evidence=evidence,
        )
        count = validate_csv(data, minimum_rows=1 if req.last_row is not None else 30)
    except AmbiguousBlock as error:
        return Completion(
            OfficesRegCandidates(req.payload.identity, error.candidates, req.as_of,
                req.sheet, req.national_row, req.last_row, tuple(invocation.used_inputs), acquisition),
            "partial", "source.xlsx_national_total_ambiguous",
        )
    except (ArchiveError, CaptureError, ParseError, ValueError) as error:
        raise source_failure(error) from None
    invocation.stage("validate")
    observations, excluded = _observations(data, req.as_of, unresolved=evidence["unresolved_fields"])
    parameters = {
        key: value for key, value in {"sheet": req.sheet, "national_row": req.national_row,
                                      "last_row": req.last_row}.items()
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
        source_uses=source_uses(DATASET, req.payload, req.as_of, METHOD),
        acquisition=acquisition,
        parameters=parameters,
        source_details={"formula_lineage": formulas, "selection": evidence},
        scope="selected_fragment" if req.last_row is not None else None,
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
    request: ReadOfficesRegRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedRelease]:
    def work(req, invocation):
        invocation.stage("validate")
        _check_date(req.as_of)
        use_payload(
            req.payload, invocation, role="csv_representation", limit=LIMIT_XLSX
        )
        try:
            selection = req.source_details.get("selection") if req.source_details is not None else None
            fragment = selection is not None and selection["scope"] == "selected_fragment"
            count = validate_csv(req.payload.data, minimum_rows=1 if fragment or req.source_details is None else 30)
            if req.source_details is not None:
                selection = validate_source_details(req.source_details, req.payload.data)
        except (CaptureError, ValueError, TypeError, KeyError, AttributeError) as error:
            raise source_failure(error) from None
        observations, excluded = (_observations(req.payload.data, req.as_of, unresolved=selection["unresolved_fields"])
                                  if selection is not None else (None, ()))
        return build_release(
            DATASET,
            PROFILE,
            READ.method_id,
            req.as_of,
            req.payload.data,
            count,
            invocation.used_inputs,
            facts_method=METHOD,
            observations=observations, excluded_fields=excluded,
        source_uses=source_uses(DATASET, req.payload, req.as_of, METHOD),
            source_details=req.source_details,
            scope="unqualified_csv" if selection is None else "selected_fragment" if fragment else None,
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

    def work(req, invocation):
        return explain_comparison(evaluate(req, invocation), req, invocation)

    return run(COMPARE, request, work, context=context)
