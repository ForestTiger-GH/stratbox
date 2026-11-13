"""Independent acquisition, normalization, calculation and rendering for 01_05_A_Debt_corp."""

from dataclasses import asdict, replace
from pathlib import PurePosixPath

from stratbox.base.limits import ExecutionBudget
from stratbox.base.net import HttpTransport
from stratbox.base.utils.optional_deps import require_extra
from stratbox.data import AcquiredSource, ByteIdentity, canonical_manifest_bytes
from stratbox.execution import (
    Completion,
    ExecutionContext,
    OperationDefinition,
    OperationFailure,
    OperationResult,
    run,
)
from stratbox.execution.batch import attempt_batch, require_batch_values
from stratbox.execution.source_validation import use_payload
from stratbox.execution.tables import record_tables, seal_stream, use_stream, use_tables
from stratbox.macrobanks._cbr import (
    HTML_TYPES,
    WORKBOOK_LIMIT,
    XLSX_TYPES,
    official_url,
    receive_cbr,
    admit_workbook,
    validate_workbook,
)

from .selection import resolve_industry_codes, selection_parameters
from .contracts import (
    BuildIndustryStreamRequest,
    CalculateApkRequest,
    Cbr0105ADebtCorpApkCalculationResult,
    Cbr0105ADebtCorpIndustryWorkbookResult,
    Cbr0105ADebtCorpPivotRequest,
    Cbr0105ADebtCorpPivotSetResult,
    Cbr0105ADebtCorpPivotWorkbookResult,
    Cbr0105ADebtCorpSourceFailure,
    Cbr0105ADebtCorpSourceLink,
    Cbr0105ADebtCorpStreamResult,
    DiscoverIndustriesRequest,
    ParseIndustryRequest,
    IndustrySelection,
    ParsedCbr0105ADebtCorpFile,
    PivotInput,
    RenderIndustryRequest,
    RenderIndustriesRequest,
    IndustryWorkbooksResult,
    RenderPivotRequest,
)

_DATASET = "cbr.industries.0105a"
_ROOTS = ("/vfs/statistics/", "/content/document/file/")
_METHOD = "cbr-0105a-workbook-2"
_HTTP = frozenset({"http"})
_TABLE_LIMITS = ExecutionBudget(cells=50_000_000, output_bytes=128 * 1024 * 1024)
DISCOVER = OperationDefinition(
    f"{_DATASET}.discover", 1, "cbr-0105a-index-1", DiscoverIndustriesRequest, tuple,
    optional_capabilities=frozenset({"http"}),
)
ACQUIRE = OperationDefinition(
    f"{_DATASET}.acquire",
    1,
    "cbr-0105a-source-1",
    Cbr0105ADebtCorpSourceLink,
    AcquiredSource,
    _HTTP,
)
PARSE = OperationDefinition(
    f"{_DATASET}.parse", 3, _METHOD + "-selective", ParseIndustryRequest, ParsedCbr0105ADebtCorpFile,
    limits=_TABLE_LIMITS,
)
BUILD_STREAM = OperationDefinition(
    f"{_DATASET}.build_stream",
    3,
    "cbr-0105a-stream-3",
    BuildIndustryStreamRequest,
    Cbr0105ADebtCorpStreamResult,
    partial_allowed=True,
    limits=_TABLE_LIMITS,
)
CALCULATE_APK = OperationDefinition(
    f"{_DATASET}.calculate_apk",
    2,
    "cbr-0105a-derived-apk-1",
    CalculateApkRequest,
    Cbr0105ADebtCorpApkCalculationResult,
    limits=_TABLE_LIMITS,
)
PIVOT = OperationDefinition(
    f"{_DATASET}.build_pivots",
    2,
    "cbr-0105a-pivots-1",
    PivotInput,
    Cbr0105ADebtCorpPivotSetResult,
    limits=_TABLE_LIMITS,
)
RENDER_PIVOTS = OperationDefinition(
    f"{_DATASET}.render_pivots",
    2,
    "cbr-0105a-pivot-xlsx-1",
    RenderPivotRequest,
    Cbr0105ADebtCorpPivotWorkbookResult,
    limits=_TABLE_LIMITS,
)
RENDER_INDUSTRY = OperationDefinition(
    f"{_DATASET}.render_industry",
    2,
    "cbr-0105a-industry-xlsx-1",
    RenderIndustryRequest,
    Cbr0105ADebtCorpIndustryWorkbookResult,
    limits=_TABLE_LIMITS,
)


RENDER_INDUSTRIES = OperationDefinition(
    f"{_DATASET}.render_industries", 1, "cbr-0105a-industry-batch-1",
    RenderIndustriesRequest, IndustryWorkbooksResult, limits=_TABLE_LIMITS,
)


def discover(
    request: DiscoverIndustriesRequest,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[tuple[Cbr0105ADebtCorpSourceLink, ...]]:
    def work(req, invocation):
        from .sources import (
            CBR_SORS_INDEX_URL,
            discover_cbr_0105a_debt_corp_links_from_html,
        )

        invocation.stage("discover")
        payload = req.index
        if payload is None:
            payload = receive_cbr(
                CBR_SORS_INDEX_URL,
                roots=("/statistics/",),
                media_types=HTML_TYPES,
                limit=5_000_000,
                source_id=f"{_DATASET}.index",
                transport=transport,
                invocation=invocation,
            ).payload
        use_payload(payload, invocation, role="source_index", limit=5_000_000)
        try:
            found = discover_cbr_0105a_debt_corp_links_from_html(payload.data)
        except ValueError:
            raise OperationFailure("source.index_invalid") from None
        if not found:
            raise OperationFailure("source.index_empty")
        for source in found:
            official_url(source.url, roots=_ROOTS)
        return found

    return run(DISCOVER, request, work, context=context)


def _validate_link(source):
    from .sources import report_date_from_cbr_0105a_filename

    path = official_url(source.url, roots=_ROOTS)
    try:
        day = report_date_from_cbr_0105a_filename(source.source_name)
    except ValueError:
        raise OperationFailure("request.source_filename_invalid") from None
    if (
        PurePosixPath(path).name != source.source_name
        or day != source.report_date
        or source.source_id != f"01_05_A_Debt_corp_{day.replace('-', '')}"
    ):
        raise OperationFailure("request.source_identity_mismatch")


def acquire(
    request: Cbr0105ADebtCorpSourceLink,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[AcquiredSource]:
    def work(req, invocation):
        invocation.stage("acquire")
        _validate_link(req)
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


def _parse(req, invocation, *, selection: IndustrySelection | None = None):
    require_extra("pandas", "dataframe")
    require_extra("openpyxl", "excel")
    from .parser import parse_cbr_0105a_debt_corp_excel_bytes

    chosen = req.selection if selection is None else selection
    try:
        resolve_industry_codes(chosen)
    except ValueError:
        raise OperationFailure("request.industry_selection_invalid") from None
    use_payload(req.payload, invocation, role="source_workbook", limit=WORKBOOK_LIMIT)
    if req.source is not None:
        _validate_link(req.source)
        if req.source.source_name != req.source_name:
            raise OperationFailure("request.source_identity_mismatch")
    admit_workbook(req.payload.data, invocation)
    try:
        return parse_cbr_0105a_debt_corp_excel_bytes(
            req.payload.data,
            source_name=req.source_name,
            source_sha256=req.payload.identity.sha256,
            source_url=req.source.url if req.source is not None else None,
            checkpoint=invocation.check_cancelled,
            selection=chosen,
        )
    except (ValueError, KeyError, OSError):
        raise OperationFailure("source.workbook_layout_unresolved") from None


def parse(
    request: ParseIndustryRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedCbr0105ADebtCorpFile]:
    def work(req, invocation):
        invocation.stage("parse")
        value = _parse(req, invocation)
        value = seal_stream(invocation, value, parameters={
            "report_date": value.report_date, "unmapped_headers": value.unmapped_headers,
            **selection_parameters(value.selection),
        })
        if any(issue.severity == "error" for issue in value.validation_issues):
            return Completion(value, "failed", "source.validation_failed")
        return value

    return run(PARSE, request, work, context=context)


def build_stream(
    request: BuildIndustryStreamRequest, *, context: ExecutionContext | None = None
) -> OperationResult[Cbr0105ADebtCorpStreamResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from .parser import concat_cbr_0105a_debt_corp_streams
        from .regions import normalize_cbr_0105a_debt_corp_regions_to_latest
        from .sources import report_date_from_cbr_0105a_filename

        invocation.stage("parse")
        if not req.sources:
            raise OperationFailure("request.source_selection_empty")
        try:
            resolve_industry_codes(req.selection)
        except ValueError:
            raise OperationFailure("request.industry_selection_invalid") from None
        try:
            selected = tuple(
                report_date_from_cbr_0105a_filename(item.source_name)
                for item in req.sources
            )
        except ValueError:
            raise OperationFailure("request.source_filename_invalid") from None
        if len(set(selected)) != len(selected):
            raise OperationFailure("request.duplicate_release")
        batch = attempt_batch(tuple(zip(req.sources, selected, strict=True)),
                              lambda pair: _parse(pair[0], invocation, selection=req.selection), invocation,
                              continue_on_error=req.continue_on_error)
        require_batch_values(batch, "source.no_valid_workbooks")
        failures = [
            Cbr0105ADebtCorpSourceFailure(
                "parse", item.source.source_id if item.source else item.source_name,
                item.source.url if item.source else "", item.source_name, day, diagnostic.code,
            )
            for (item, day), diagnostic in batch.failed
        ]
        checkpoint = (lambda: None) if batch.stopped is not None else None
        if checkpoint is None:
            invocation.stage("normalize_geography")
        invocation.budget.check("cells", sum(item.df_stream.size for item in batch.values),
                                completed=checkpoint is not None)
        files = normalize_cbr_0105a_debt_corp_regions_to_latest(batch.values)
        stream = concat_cbr_0105a_debt_corp_streams(item.df_stream for item in files)
        stream = stream.sort_values(
            ["report_date", "sheet_order", "region_order", "industry_order"],
            kind="stable",
        ).reset_index(drop=True)
        dates = tuple(sorted(item.report_date for item in files))
        latest = max(files, key=lambda item: item.report_date)
        value = Cbr0105ADebtCorpStreamResult(
            tuple(item.source for item in req.sources if item.source is not None),
            tuple(failures),
            files,
            tuple(issue for item in files for issue in item.validation_issues),
            stream,
            dates,
            latest.report_date,
            max(selected),
            latest.report_date,
            latest.report_date == max(selected),
            latest.regions,
            latest.industries,
            len(stream), stop_reason=batch.stopped.code if batch.stopped else None,
            selection=req.selection,
        )
        value = seal_stream(invocation, value, parameters={
            "selected": selected, "accepted": dates,
            **selection_parameters(req.selection),
            "quantity_kind": "stock", "period_basis": "as_of", "unit": "million_rubles",
            "geography_anchor": latest.report_date, "geography_method": value.geography_method_version,
            "coverage": "subset" if failures or batch.stopped else "complete",
            "not_started": [item[0].source_name if isinstance(item, tuple) else item.source_name for item in batch.remaining],
            "interrupted": batch.interrupted[0].source_name if batch.interrupted else None,
            "unmapped_headers": [pair for item in files for pair in item.unmapped_headers],
        }, checkpoint=checkpoint)
        if not value.validation_ok:
            return Completion(value, "failed", "source.validation_failed")
        if batch.stopped or failures:
            return Completion(value, "partial", batch.stopped or "source.selection_incomplete")
        return value

    return run(BUILD_STREAM, request, work, context=context)


def calculate_apk(
    request: CalculateApkRequest, *, context: ExecutionContext | None = None
) -> OperationResult[Cbr0105ADebtCorpApkCalculationResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from .derived import (
            Cbr0105ADebtCorpDerivedIndustryError,
            calculate_cbr_0105a_debt_corp_apk_industry,
        )

        invocation.stage("calculate_derived")
        if isinstance(req.stream, Cbr0105ADebtCorpStreamResult) and not req.stream.ok:
            raise OperationFailure("source.stream_incomplete")
        if isinstance(req.stream, ParsedCbr0105ADebtCorpFile) and any(
            item.severity == "error" for item in req.stream.validation_issues
        ):
            raise OperationFailure("source.validation_failed")
        stream = use_stream(invocation, req.stream)
        try:
            value = calculate_cbr_0105a_debt_corp_apk_industry(stream, budget=invocation.budget)
        except Cbr0105ADebtCorpDerivedIndustryError as error:
            raise OperationFailure(f"derived.{error.code.lower()}") from None
        return seal_stream(invocation, value, parameters={
            "components": value.source_industry_codes, "apk": value.apk_formula_ru, "lpk": value.lpk_formula_ru,
        })

    return run(CALCULATE_APK, request, work, context=context)


def build_pivots(
    request: PivotInput, *, context: ExecutionContext | None = None
) -> OperationResult[Cbr0105ADebtCorpPivotSetResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from .pivots import (
            Cbr0105ADebtCorpPivotError,
            build_cbr_0105a_debt_corp_pivot_set,
        )

        invocation.stage("build_views")
        stream = use_stream(invocation, req.stream, source=req.source)
        stream = _select_industry(stream, req.industry_code)
        try:
            result = build_cbr_0105a_debt_corp_pivot_set(
                stream, req.pivot, stream_result=_stream_metadata(req), budget=invocation.budget,
            )
        except Cbr0105ADebtCorpPivotError as error:
            raise OperationFailure(f"pivot.{error.code.lower()}") from None
        return _seal_pivots(invocation, result, req.pivot, industry_code=req.industry_code)

    return run(PIVOT, request, work, context=context)


def _stream_metadata(request):
    if request.source is not None:
        return request.source
    return request.stream if hasattr(request.stream, "validation_issues") else None


def _select_industry(stream, code):
    if code is None:
        return stream
    if "industry_code" not in stream:
        raise OperationFailure("request.industry_unresolved")
    selected = stream.loc[stream["industry_code"].eq(code)]
    if selected.empty:
        raise OperationFailure("request.industry_unresolved")
    return selected


def _pivot_tables(result):
    return tuple((table.suggested_sheet_name, table.df_table) for table in result.tables)


def _pivot_metadata(result):
    return {
        "row_dimension": result.row_dimension, "column_dimension": result.column_dimension,
        "value_columns": result.value_columns, "sheet_dimensions": result.sheet_dimensions,
        "fixed_dimensions": result.fixed_dimensions, "source_rows": result.source_rows,
        "partial": result.is_partial, "sheets": [
            (table.sheet_key, table.rows, table.data_columns) for table in result.tables
        ],
    }


def _seal_pivots(invocation, result, request, *, industry_code=None):
    return replace(result, evidence=record_tables(invocation, _pivot_tables(result),
                                                   parameters={**asdict(request), "industry": industry_code},
                                                   metadata=_pivot_metadata(result)))


def render_pivots(
    request: RenderPivotRequest, *, context: ExecutionContext | None = None
) -> OperationResult[Cbr0105ADebtCorpPivotWorkbookResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from .export import render_cbr_0105a_debt_corp_pivot_workbook

        invocation.stage("render")
        if not req.tables.tables:
            raise OperationFailure("request.empty_views")
        frames = use_tables(invocation, _pivot_tables(req.tables), receipt=req.tables.evidence,
                            role="pivots", metadata=_pivot_metadata(req.tables))
        tables = replace(req.tables, tables=tuple(
            replace(table, df_table=frame) for table, frame in zip(req.tables.tables, frames, strict=True)
        ))
        value = render_cbr_0105a_debt_corp_pivot_workbook(tables, req.format, budget=invocation.budget)
        invocation.record(value.representation.identity, parameters={
            "profile": value.representation.profile_id, **asdict(req.format),
        })
        return value

    return run(RENDER_PIVOTS, request, work, context=context)


def _render_one_industry(source, private_stream, fmt, invocation):
    """Reuse the exact economic calculation and Excel exporter for one or many books."""
    from .derived import (
        Cbr0105ADebtCorpDerivedIndustryError,
        calculate_cbr_0105a_debt_corp_apk_industry,
    )
    from .export import render_cbr_0105a_debt_corp_industry_workbook
    from .pivots import (
        Cbr0105ADebtCorpPivotError, build_cbr_0105a_debt_corp_pivot_set,
    )

    derived = False
    try:
        frame = private_stream
        if (fmt.industry_code == "apk" and not frame["industry_code"].eq("apk").any()
                and fmt.calculate_apk_if_missing):
            frame = calculate_cbr_0105a_debt_corp_apk_industry(
                frame, budget=invocation.budget,
            ).df_stream
            derived = True
        selected = frame.loc[frame["industry_code"].eq(fmt.industry_code)]
        names = selected["industry_name_ru"].dropna().unique()
        if len(names) != 1:
            raise OperationFailure("request.industry_unresolved")
        pivot = build_cbr_0105a_debt_corp_pivot_set(
            selected,
            Cbr0105ADebtCorpPivotRequest(
                "region_code", "report_date",
                sheet_dimensions=("currency_scope", "measure"), max_sheet_count=6,
            ),
            stream_result=source, budget=invocation.budget,
        )
        invocation.stage("render")
        value = render_cbr_0105a_debt_corp_industry_workbook(
            pivot, fmt, industry_name_ru=str(names[0]), budget=invocation.budget,
        )
        return value, derived
    except Cbr0105ADebtCorpDerivedIndustryError as error:
        raise OperationFailure(f"derived.{error.code.lower()}") from None
    except (Cbr0105ADebtCorpPivotError, ValueError):
        raise OperationFailure("source.industry_views_invalid") from None


def render_industry(
    request: RenderIndustryRequest, *, context: ExecutionContext | None = None
) -> OperationResult[Cbr0105ADebtCorpIndustryWorkbookResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        if not req.stream.ok:
            raise OperationFailure("source.stream_incomplete")
        invocation.stage("select_industry")
        private_stream = use_stream(invocation, req.stream)
        value, derived = _render_one_industry(req.stream, private_stream, req.format, invocation)
        invocation.record(value.representation.identity, parameters={
            "profile": value.representation.profile_id, **asdict(req.format),
            "derived_method": CALCULATE_APK.method_version if derived else None,
        })
        return value

    return run(RENDER_INDUSTRY, request, work, context=context)


def render_industries(
    request: RenderIndustriesRequest, *, context: ExecutionContext | None = None
) -> OperationResult[IndustryWorkbooksResult]:
    """Admit a caller-owned DataFrame once; return distinct verified output identities."""
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        try:
            resolve_industry_codes(IndustrySelection(req.industry_codes))
        except ValueError:
            raise OperationFailure("request.industry_selection_invalid") from None
        if not req.stream.ok:
            raise OperationFailure("source.stream_incomplete")
        invocation.stage("admit_stream")
        private_stream = use_stream(invocation, req.stream)
        items = []
        for code in req.industry_codes:
            invocation.check_cancelled()
            fmt = Cbr0105ADebtCorpIndustryWorkbookRequest(
                industry_code=code, include_metadata_sheet=req.include_metadata_sheet,
            )
            value, _ = _render_one_industry(req.stream, private_stream, fmt, invocation)
            invocation.budget.charge("output_bytes", value.representation.identity.size)
            items.append(value)
        result = IndustryWorkbooksResult(tuple(items))
        if not result.ok:
            raise OperationFailure("source.industry_views_invalid")
        manifest = [
            {"industry": item.industry_code, "profile": item.representation.profile_id,
             "sha256": item.representation.identity.sha256, "size": item.representation.identity.size}
            for item in items
        ]
        invocation.record(ByteIdentity.of(canonical_manifest_bytes(manifest)), parameters={
            "industries": req.industry_codes,
            "include_metadata_sheet": req.include_metadata_sheet,
            "derived_method": CALCULATE_APK.method_version if "apk" in req.industry_codes else None,
        })
        return result

    return run(RENDER_INDUSTRIES, request, work, context=context)
