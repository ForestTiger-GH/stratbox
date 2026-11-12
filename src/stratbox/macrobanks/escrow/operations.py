"""Source discovery, history, views and workbook representation for escrow accounts."""

from datetime import date
from pathlib import PurePosixPath

from stratbox.base.ioapi.workbook_bytes import openpyxl_bytes
from stratbox.base.net import HttpTransport
from stratbox.base.utils.optional_deps import require_extra
from stratbox.data import AcquiredSource, Representation
from stratbox.data.representation import XLSX
from stratbox.execution import (
    Completion,
    ExecutionContext,
    OperationDefinition,
    OperationFailure,
    OperationResult,
    run,
)
from stratbox.execution.source_validation import use_payload
from stratbox.macrobanks._cbr import (
    HTML_TYPES,
    WORKBOOK_LIMIT,
    XLSX_TYPES,
    official_url,
    receive_cbr,
    validate_workbook,
)

from .contracts import (
    BuildEscrowViewsRequest,
    DiscoverEscrowRequest,
    EscrowHistoryBuildRequest,
    EscrowHistoryResult,
    EscrowPivotPack,
    EscrowSourceFailure,
    EscrowSourceLink,
    ParseEscrowRequest,
    ParsedEscrowFile,
)

_ROOTS = ("/vfs/", "/content/document/file/")
DISCOVER = OperationDefinition(
    "cbr.escrow.discover", 1, "cbr-escrow-index-1", DiscoverEscrowRequest, tuple
)
ACQUIRE = OperationDefinition(
    "cbr.escrow.acquire",
    1,
    "cbr-escrow-source-1",
    EscrowSourceLink,
    AcquiredSource,
    frozenset({"http"}),
)
PARSE = OperationDefinition(
    "cbr.escrow.parse", 1, "cbr-escrow-layout-1", ParseEscrowRequest, ParsedEscrowFile
)
HISTORY = OperationDefinition(
    "cbr.escrow.build_history",
    1,
    "cbr-escrow-history-1",
    EscrowHistoryBuildRequest,
    EscrowHistoryResult,
    partial_allowed=True,
)
VIEWS = OperationDefinition(
    "cbr.escrow.build_views",
    1,
    "cbr-escrow-views-1",
    BuildEscrowViewsRequest,
    EscrowPivotPack,
)
RENDER = OperationDefinition(
    "cbr.escrow.render_workbook",
    1,
    "cbr-escrow-xlsx-1",
    EscrowPivotPack,
    Representation,
)


def discover(
    request: DiscoverEscrowRequest,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[tuple[EscrowSourceLink, ...]]:
    def work(req, invocation):
        from .sources import CBR_ESCROW_INDEX_URL, discover_escrow_source_links

        invocation.stage("discover")
        index = req.index
        if index is None:
            index = receive_cbr(
                CBR_ESCROW_INDEX_URL,
                roots=("/statistics/",),
                media_types=HTML_TYPES,
                limit=5_000_000,
                source_id="cbr.escrow.index",
                transport=transport,
                invocation=invocation,
            ).payload
        use_payload(index, invocation, role="source_index", limit=5_000_000)
        links = discover_escrow_source_links(index.data)
        if not links:
            raise OperationFailure("source.index_empty")
        return links

    return run(DISCOVER, request, work, context=context)


def acquire(
    request: EscrowSourceLink,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[AcquiredSource]:
    def work(req, invocation):
        from .sources import _source_id_from_absolute_url

        invocation.stage("acquire")
        path = official_url(req.url, roots=_ROOTS)
        if (
            not path.casefold().endswith(".xlsx")
            or PurePosixPath(path).name != req.source_name
            or req.source_id != _source_id_from_absolute_url(req.url)
        ):
            raise OperationFailure("request.source_identity_mismatch")
        acquired = receive_cbr(
            req.url,
            roots=_ROOTS,
            media_types=XLSX_TYPES,
            limit=WORKBOOK_LIMIT,
            source_id=req.source_id,
            transport=transport,
            invocation=invocation,
        )
        validate_workbook(acquired.payload.data)
        return acquired

    return run(ACQUIRE, request, work, context=context, providers={"http": transport})


def _parse(req, invocation):
    require_extra("pandas", "dataframe")
    require_extra("openpyxl", "excel")
    from .parser import extract_date_from_filename, parse_escrow_excel_bytes

    use_payload(req.payload, invocation, role="source_workbook", limit=WORKBOOK_LIMIT)
    validate_workbook(req.payload.data)
    named_date = extract_date_from_filename(req.source_name)
    try:
        day = date.fromisoformat(named_date) if named_date is not None else req.as_of
    except ValueError:
        raise OperationFailure("source.date_invalid") from None
    if type(day) is not date:
        raise OperationFailure("request.release_date_required")
    if req.as_of is not None and req.as_of != day:
        raise OperationFailure("source.date_mismatch")
    try:
        value = parse_escrow_excel_bytes(
            req.payload.data, source_name=req.source_name, as_of=day.isoformat()
        )
    except (ValueError, KeyError, OSError):
        raise OperationFailure("source.workbook_invalid") from None
    if value.df_long.empty:
        raise OperationFailure("source.observations_empty")
    return value


def parse(
    request: ParseEscrowRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedEscrowFile]:
    def work(req, invocation):
        invocation.stage("parse")
        return _parse(req, invocation)

    return run(PARSE, request, work, context=context)


def build_history(
    request: EscrowHistoryBuildRequest, *, context: ExecutionContext | None = None
) -> OperationResult[EscrowHistoryResult]:
    def work(req, invocation):
        pd = require_extra("pandas", "dataframe")

        from .columns import get_output_indicator_specs

        invocation.stage("parse")
        if not req.sources:
            raise OperationFailure("request.source_selection_empty")
        parsed, failures = [], []
        dates = set()
        for index, source in enumerate(req.sources):
            invocation.progress(index, len(req.sources))
            try:
                item = _parse(source, invocation)
            except OperationFailure as error:
                if not req.continue_on_error or error.outcome == "cancelled":
                    raise
                failures.append(
                    EscrowSourceFailure(
                        source.payload.source_id or source.source_name,
                        "",
                        source.source_name,
                        error.diagnostic.code,
                    )
                )
                continue
            if item.file_date in dates:
                raise OperationFailure("source.duplicate_release")
            dates.add(item.file_date)
            parsed.append(item)
        if not parsed:
            raise OperationFailure("source.no_valid_workbooks")
        invocation.stage("build_history")
        parsed.sort(key=lambda item: item.file_date)
        long = pd.concat([item.df_long for item in parsed], ignore_index=True)
        present = set(long["Показатель"].dropna())
        indicators = tuple(
            spec.canonical_name
            for spec in get_output_indicator_specs()
            if spec.canonical_name in present
        )
        result = EscrowHistoryResult(
            tuple(failures),
            tuple(parsed),
            long,
            tuple(sorted(dates)),
            indicators,
            len(long),
        )
        if failures:
            return Completion(result, "partial", "source.selection_incomplete")
        return result

    return run(HISTORY, request, work, context=context)


def build_views(
    request: BuildEscrowViewsRequest, *, context: ExecutionContext | None = None
) -> OperationResult[EscrowPivotPack]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        from .pivots import build_escrow_pivots

        invocation.stage("build_views")
        if req.view.regions_mode not in {"latest", "custom"}:
            raise OperationFailure("request.region_order_invalid")
        if not req.history.ok:
            raise OperationFailure("source.history_incomplete")
        pivots, indicators, regions, dates = build_escrow_pivots(
            req.history.df_long,
            parsed_files=req.history.parsed_files,
            regions_mode=req.view.regions_mode,
            custom_regions=req.view.custom_regions,
        )
        return EscrowPivotPack(pivots, tuple(indicators), tuple(regions), tuple(dates))

    return run(VIEWS, request, work, context=context)


def render_workbook(
    request: EscrowPivotPack, *, context: ExecutionContext | None = None
) -> OperationResult[Representation]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from .workbook import build_escrow_workbook

        invocation.stage("render")
        if not req.indicator_specs:
            raise OperationFailure("request.empty_views")
        workbook = build_escrow_workbook(
            req.pivots, list(req.indicator_specs), checkpoint=invocation.check_cancelled
        )
        try:
            return Representation(
                "cbr.escrow.workbook",
                1,
                XLSX,
                openpyxl_bytes(workbook, literal_text=True),
            )
        finally:
            workbook.close()

    return run(RENDER, request, work, context=context)
