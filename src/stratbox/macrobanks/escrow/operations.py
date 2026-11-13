"""Source discovery, history, views and workbook representation for escrow accounts."""

from dataclasses import asdict, replace
from datetime import date
from pathlib import PurePosixPath

from stratbox.base.ioapi.workbook_bytes import openpyxl_bytes
from stratbox.base.net import HttpTransport
from stratbox.base.limits import ExecutionBudget
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
from stratbox.execution.batch import attempt_batch, require_batch_values
from stratbox.execution.tables import record_tables, use_tables
from stratbox.macrobanks._cbr import (
    HTML_TYPES,
    WORKBOOK_LIMIT,
    XLSX_TYPES,
    official_url,
    receive_cbr,
    admit_workbook,
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

from .sources import ESCROW_SOURCE_ROOTS

_ROOTS = ESCROW_SOURCE_ROOTS
_TABLES = ExecutionBudget(cells=50_000_000, output_bytes=128 * 1024 * 1024)
DISCOVER = OperationDefinition(
    "cbr.escrow.discover", 1, "cbr-escrow-index-1", DiscoverEscrowRequest, tuple,
    optional_capabilities=frozenset({"http"}),
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
    "cbr.escrow.parse", 2, "cbr-escrow-layout-2", ParseEscrowRequest, ParsedEscrowFile, limits=_TABLES
)
HISTORY = OperationDefinition(
    "cbr.escrow.build_history",
    2,
    "cbr-escrow-history-2",
    EscrowHistoryBuildRequest,
    EscrowHistoryResult,
    partial_allowed=True,
    limits=_TABLES,
)
VIEWS = OperationDefinition(
    "cbr.escrow.build_views",
    2,
    "cbr-escrow-views-1",
    BuildEscrowViewsRequest,
    EscrowPivotPack,
    limits=_TABLES,
)
RENDER = OperationDefinition(
    "cbr.escrow.render_workbook",
    2,
    "cbr-escrow-xlsx-1",
    EscrowPivotPack,
    Representation,
    limits=_TABLES,
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
        validate_workbook(acquired.payload.data, budget=invocation.budget)
        return acquired

    return run(ACQUIRE, request, work, context=context, providers={"http": transport})


def _parse(req, invocation):
    require_extra("pandas", "dataframe")
    require_extra("openpyxl", "excel")
    from .parser import extract_date_from_filename, parse_escrow_excel_bytes

    use_payload(req.payload, invocation, role="source_workbook", limit=WORKBOOK_LIMIT)
    admit_workbook(req.payload.data, invocation)
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
    except ValueError:
        raise OperationFailure("source.workbook_layout_unresolved") from None
    except (KeyError, OSError):
        raise OperationFailure("source.workbook_invalid") from None
    if value.df_long.empty:
        raise OperationFailure("source.observations_empty")
    return value


def parse(
    request: ParseEscrowRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedEscrowFile]:
    def work(req, invocation):
        invocation.stage("parse")
        value = _parse(req, invocation)
        evidence = record_tables(invocation, (("rows", value.df_rows), ("observations", value.df_long)),
                                 parameters={"date": value.file_date, "sheet": value.sheet_name,
                                             "unmapped_headers": value.unmapped_headers})
        return replace(value, evidence=evidence)

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
        batch = attempt_batch(req.sources, lambda source: _parse(source, invocation), invocation,
                              continue_on_error=req.continue_on_error)
        require_batch_values(batch, "source.no_valid_workbooks")
        failures = [
            EscrowSourceFailure(source.payload.source_id or source.source_name, "", source.source_name, diagnostic.code)
            for source, diagnostic in batch.failed
        ]
        parsed = sorted(batch.values, key=lambda item: item.file_date)
        dates = tuple(item.file_date for item in parsed)
        if len(set(dates)) != len(dates):
            raise OperationFailure("source.duplicate_release")
        checkpoint = (lambda: None) if batch.stopped is not None else None
        if checkpoint is None:
            invocation.stage("build_history")
        invocation.budget.check("cells", sum(item.df_long.size for item in parsed), completed=checkpoint is not None)
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
            dates,
            indicators,
            len(long),
            stop_reason=batch.stopped.code if batch.stopped else None,
        )
        tables, metadata = _history_tables(result)
        result = replace(result, evidence=record_tables(
            invocation, tables, metadata=metadata, checkpoint=checkpoint, parameters={
                "coverage": "complete" if result.ok else "subset",
                "unmapped_headers": [item.unmapped_headers for item in parsed],
                "not_started": [item.source_name for item in batch.remaining],
                "interrupted": batch.interrupted.source_name if batch.interrupted else None,
            },
        ))
        if not result.ok:
            return Completion(result, "partial", batch.stopped or "source.selection_incomplete")
        return result

    return run(HISTORY, request, work, context=context)


def _history_tables(result):
    tables = (("observations", result.df_long),) + tuple(
        (item.file_date, item.df_rows) for item in result.parsed_files
    )
    return tables, {"dates": result.dates, "failed": bool(result.failures), "stop_reason": result.stop_reason}


def _pivot_metadata(result):
    return {"indicators": [asdict(spec) for spec in result.indicator_specs],
            "regions": result.region_order, "dates": result.date_order}


def build_views(
    request: BuildEscrowViewsRequest, *, context: ExecutionContext | None = None
) -> OperationResult[EscrowPivotPack]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        from .pivots import build_escrow_pivots

        invocation.stage("build_views")
        if req.view.regions_mode not in {"latest", "custom"}:
            raise OperationFailure("request.region_order_invalid")
        if not req.history.ok and req.view.require_complete_history:
            raise OperationFailure("source.history_incomplete")
        tables, metadata = _history_tables(req.history)
        long, *rows = use_tables(invocation, tables, receipt=req.history.evidence,
                                 role="escrow_history", metadata=metadata)
        files = tuple(replace(item, df_rows=frame) for item, frame in zip(req.history.parsed_files, rows, strict=True))
        try:
            pivots, indicators, regions, dates = build_escrow_pivots(
                long, parsed_files=files, regions_mode=req.view.regions_mode,
                custom_regions=req.view.custom_regions, budget=invocation.budget,
            )
        except ValueError:
            raise OperationFailure("request.escrow_view_invalid") from None
        value = EscrowPivotPack(pivots, tuple(indicators), tuple(regions), tuple(dates))
        return replace(value, evidence=record_tables(invocation, tuple(pivots.items()),
                                                    metadata=_pivot_metadata(value), parameters=asdict(req.view)))

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
        tables = tuple(req.pivots.items())
        frames = use_tables(invocation, tables, receipt=req.evidence, role="escrow_views", metadata=_pivot_metadata(req))
        pivots = dict(zip((name for name, _ in tables), frames, strict=True))
        workbook = build_escrow_workbook(
            pivots, list(req.indicator_specs), checkpoint=invocation.check_cancelled
        )
        try:
            return Representation(
                "cbr.escrow.workbook",
                1,
                XLSX,
                openpyxl_bytes(workbook, literal_text=True, budget=invocation.budget),
            )
        finally:
            workbook.close()

    return run(RENDER, request, work, context=context)
