"""Independent acquisition, normalization, calculation and rendering for 01_05_A_Debt_corp."""

from pathlib import PurePosixPath

from stratbox.base.net import HttpTransport
from stratbox.base.utils.optional_deps import require_extra
from stratbox.data import AcquiredSource
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
    admit_workbook,
    validate_workbook,
)

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
    ParsedCbr0105ADebtCorpFile,
    PivotInput,
    RenderIndustryRequest,
    RenderPivotRequest,
)

_DATASET = "cbr.industries.0105a"
_ROOTS = ("/vfs/statistics/", "/content/document/file/")
_METHOD = "cbr-0105a-workbook-1"
_HTTP = frozenset({"http"})
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
    f"{_DATASET}.parse", 1, _METHOD, ParseIndustryRequest, ParsedCbr0105ADebtCorpFile
)
BUILD_STREAM = OperationDefinition(
    f"{_DATASET}.build_stream",
    1,
    "cbr-0105a-stream-1",
    BuildIndustryStreamRequest,
    Cbr0105ADebtCorpStreamResult,
    partial_allowed=True,
)
CALCULATE_APK = OperationDefinition(
    f"{_DATASET}.calculate_apk",
    1,
    "cbr-0105a-derived-apk-1",
    CalculateApkRequest,
    Cbr0105ADebtCorpApkCalculationResult,
)
PIVOT = OperationDefinition(
    f"{_DATASET}.build_pivots",
    1,
    "cbr-0105a-pivots-1",
    PivotInput,
    Cbr0105ADebtCorpPivotSetResult,
)
RENDER_PIVOTS = OperationDefinition(
    f"{_DATASET}.render_pivots",
    1,
    "cbr-0105a-pivot-xlsx-1",
    RenderPivotRequest,
    Cbr0105ADebtCorpPivotWorkbookResult,
)
RENDER_INDUSTRY = OperationDefinition(
    f"{_DATASET}.render_industry",
    1,
    "cbr-0105a-industry-xlsx-1",
    RenderIndustryRequest,
    Cbr0105ADebtCorpIndustryWorkbookResult,
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


def _parse(req, invocation):
    require_extra("pandas", "dataframe")
    require_extra("openpyxl", "excel")
    from .parser import parse_cbr_0105a_debt_corp_excel_bytes

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
        )
    except (ValueError, KeyError, OSError):
        raise OperationFailure("source.workbook_invalid") from None


def parse(
    request: ParseIndustryRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedCbr0105ADebtCorpFile]:
    def work(req, invocation):
        invocation.stage("parse")
        value = _parse(req, invocation)
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
            selected = tuple(
                report_date_from_cbr_0105a_filename(item.source_name)
                for item in req.sources
            )
        except ValueError:
            raise OperationFailure("request.source_filename_invalid") from None
        if len(set(selected)) != len(selected):
            raise OperationFailure("request.duplicate_release")
        parsed, failures = [], []
        for index, (item, day) in enumerate(zip(req.sources, selected), 1):
            invocation.progress(index - 1, len(selected))
            try:
                parsed.append(_parse(item, invocation))
            except OperationFailure as error:
                if not req.continue_on_error or error.outcome == "cancelled":
                    raise
                source = item.source
                failures.append(
                    Cbr0105ADebtCorpSourceFailure(
                        "parse",
                        source.source_id if source else item.source_name,
                        source.url if source else "",
                        item.source_name,
                        day,
                        error.diagnostic.code,
                    )
                )
        if not parsed:
            raise OperationFailure("source.no_valid_workbooks")
        invocation.stage("normalize_geography")
        files = normalize_cbr_0105a_debt_corp_regions_to_latest(parsed)
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
            len(stream),
        )
        if not value.validation_ok:
            return Completion(value, "failed", "source.validation_failed")
        if failures:
            return Completion(value, "partial", "source.selection_incomplete")
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
        try:
            return calculate_cbr_0105a_debt_corp_apk_industry(req.stream)
        except Cbr0105ADebtCorpDerivedIndustryError as error:
            raise OperationFailure(f"derived.{error.code.lower()}") from None

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
        try:
            return build_cbr_0105a_debt_corp_pivot_set(
                req.stream, req.pivot, stream_result=req.source
            )
        except Cbr0105ADebtCorpPivotError as error:
            raise OperationFailure(f"pivot.{error.code.lower()}") from None

    return run(PIVOT, request, work, context=context)


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
        return render_cbr_0105a_debt_corp_pivot_workbook(req.tables, req.format)

    return run(RENDER_PIVOTS, request, work, context=context)


def render_industry(
    request: RenderIndustryRequest, *, context: ExecutionContext | None = None
) -> OperationResult[Cbr0105ADebtCorpIndustryWorkbookResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from .derived import (
            Cbr0105ADebtCorpDerivedIndustryError,
            calculate_cbr_0105a_debt_corp_apk_industry,
        )
        from .export import render_cbr_0105a_debt_corp_industry_workbook
        from .pivots import (
            Cbr0105ADebtCorpPivotError,
            build_cbr_0105a_debt_corp_pivot_set,
        )

        if not req.stream.ok:
            raise OperationFailure("source.stream_incomplete")
        invocation.stage("select_industry")
        stream = req.stream.df_stream
        code = req.format.industry_code
        try:
            if (
                code == "apk"
                and not stream["industry_code"].eq(code).any()
                and req.format.calculate_apk_if_missing
            ):
                stream = calculate_cbr_0105a_debt_corp_apk_industry(stream).df_stream
            filtered = stream.loc[stream["industry_code"].eq(code)]
            names = filtered["industry_name_ru"].dropna().unique()
            if len(names) != 1:
                raise OperationFailure("request.industry_unresolved")
            pivot = build_cbr_0105a_debt_corp_pivot_set(
                filtered,
                Cbr0105ADebtCorpPivotRequest(
                    "region_code",
                    "report_date",
                    sheet_dimensions=("currency_scope", "measure"),
                    max_sheet_count=6,
                ),
                stream_result=req.stream,
            )
            invocation.stage("render")
            return render_cbr_0105a_debt_corp_industry_workbook(
                pivot, req.format, industry_name_ru=str(names[0])
            )
        except Cbr0105ADebtCorpDerivedIndustryError as error:
            raise OperationFailure(f"derived.{error.code.lower()}") from None
        except (Cbr0105ADebtCorpPivotError, ValueError):
            raise OperationFailure("source.industry_views_invalid") from None

    return run(RENDER_INDUSTRY, request, work, context=context)
