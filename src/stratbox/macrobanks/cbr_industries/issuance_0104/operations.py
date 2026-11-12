"""Independent typed operations for monthly 01_04_A corporate loan issuance."""

from __future__ import annotations

from dataclasses import replace
from pathlib import PurePosixPath

from stratbox.base.net import HttpTransport
from stratbox.base.utils.optional_deps import require_extra
from stratbox.data import AcquiredSource
from stratbox.execution import (
    Completion, ExecutionContext, OperationDefinition, OperationFailure,
    OperationResult, run,
)
from stratbox.execution.source_validation import use_payload
from stratbox.macrobanks._cbr import (
    HTML_TYPES, WORKBOOK_LIMIT, XLSX_TYPES, official_url, receive_cbr,
    validate_workbook,
)

from .contracts import (
    BuildIssuanceStreamRequest, CalculateIssuanceApkRequest, DiscoverIssuanceRequest,
    IssuanceSourceFailure, IssuanceSourceLink, IssuanceStreamResult,
    IssuanceWorkbookRequest, IssuanceWorkbookResult, ParseIssuanceRequest, ParsedIssuanceFile,
    PivotIssuanceRequest,
)
from stratbox.macrobanks.cbr_industries.contracts import (
    Cbr0105ADebtCorpApkCalculationResult, Cbr0105ADebtCorpPivotSetResult,
)
from .sources import CBR_SORS_INDEX_URL, SERIES_CODE, discover_links, reference_period, report_date_from_filename

_DATASET = "cbr.industries.0104a"
_ROOTS = ("/vfs/statistics/", "/content/document/file/")
DISCOVER = OperationDefinition(f"{_DATASET}.discover", 1, "cbr-0104a-index-1", DiscoverIssuanceRequest, tuple)
ACQUIRE = OperationDefinition(f"{_DATASET}.acquire", 1, "cbr-0104a-source-1", IssuanceSourceLink,
                              AcquiredSource, frozenset({"http"}))
PARSE = OperationDefinition(f"{_DATASET}.parse", 1, "cbr-0104a-workbook-1", ParseIssuanceRequest,
                            ParsedIssuanceFile)
BUILD_STREAM = OperationDefinition(f"{_DATASET}.build_stream", 1, "cbr-0104a-stream-1",
                                   BuildIssuanceStreamRequest, IssuanceStreamResult, partial_allowed=True)
CALCULATE_APK = OperationDefinition(f"{_DATASET}.calculate_apk", 1, "cbr-industry-apk-1",
                                    CalculateIssuanceApkRequest, Cbr0105ADebtCorpApkCalculationResult)
PIVOT = OperationDefinition(f"{_DATASET}.build_pivots", 1, "cbr-industry-pivot-1",
                            PivotIssuanceRequest, Cbr0105ADebtCorpPivotSetResult)
RENDER_INDUSTRY = OperationDefinition(f"{_DATASET}.render_industry", 1, "cbr-0104a-xlsx-1",
                                      IssuanceWorkbookRequest, IssuanceWorkbookResult)


def _check_source(source: IssuanceSourceLink) -> None:
    path = official_url(source.url, roots=_ROOTS)
    try:
        day = report_date_from_filename(source.source_name)
    except ValueError:
        raise OperationFailure("request.source_filename_invalid") from None
    if (PurePosixPath(path).name != source.source_name
        or source.report_date != day
        or source.reference_period != reference_period(day)
        or source.source_id != f"{SERIES_CODE}_{day.replace('-', '')}"):
        raise OperationFailure("request.source_identity_mismatch")


def discover(request: DiscoverIssuanceRequest, *, transport: HttpTransport | None = None,
             context: ExecutionContext | None = None) -> OperationResult[tuple[IssuanceSourceLink, ...]]:
    def work(req, invocation):
        invocation.stage("discover")
        index = req.index
        if index is None:
            index = receive_cbr(CBR_SORS_INDEX_URL, roots=("/statistics/",),
                                media_types=HTML_TYPES, limit=5_000_000,
                                source_id=f"{_DATASET}.index", transport=transport,
                                invocation=invocation).payload
        use_payload(index, invocation, role="source_index", limit=5_000_000)
        try:
            sources = discover_links(index.data, date_from=req.date_from, date_to=req.date_to)
        except ValueError:
            raise OperationFailure("source.index_invalid") from None
        if not sources:
            raise OperationFailure("source.index_empty")
        for source in sources:
            _check_source(source)
        return sources
    return run(DISCOVER, request, work, context=context)


def acquire(request: IssuanceSourceLink, *, transport: HttpTransport | None = None,
            context: ExecutionContext | None = None) -> OperationResult[AcquiredSource]:
    def work(req, invocation):
        invocation.stage("acquire")
        _check_source(req)
        received = receive_cbr(req.url, roots=_ROOTS, media_types=XLSX_TYPES,
                               limit=WORKBOOK_LIMIT, source_id=req.source_id,
                               transport=transport, invocation=invocation)
        validate_workbook(received.payload.data)
        return received
    return run(ACQUIRE, request, work, context=context, providers={"http": transport})


def _parse(req: ParseIssuanceRequest, invocation) -> ParsedIssuanceFile:
    require_extra("pandas", "dataframe")
    require_extra("openpyxl", "excel")
    from .parser import parse_workbook

    use_payload(req.payload, invocation, role="source_workbook", limit=WORKBOOK_LIMIT)
    if req.source is not None:
        _check_source(req.source)
        if req.source.source_name != req.source_name:
            raise OperationFailure("request.source_identity_mismatch")
    validate_workbook(req.payload.data)
    try:
        return parse_workbook(req.payload.data, source_name=req.source_name,
                              source_url=req.source.url if req.source else None,
                              source_sha256=req.payload.identity.sha256,
                              checkpoint=invocation.check_cancelled)
    except (ValueError, KeyError, OSError, IndexError, TypeError):
        raise OperationFailure("source.workbook_invalid") from None


def parse(request: ParseIssuanceRequest, *, context: ExecutionContext | None = None
          ) -> OperationResult[ParsedIssuanceFile]:
    def work(req, invocation):
        invocation.stage("parse")
        parsed = _parse(req, invocation)
        if any(issue.severity == "error" for issue in parsed.validation_issues):
            return Completion(parsed, "failed", "source.validation_failed")
        return parsed
    return run(PARSE, request, work, context=context)


def build_stream(request: BuildIssuanceStreamRequest, *, context: ExecutionContext | None = None
                 ) -> OperationResult[IssuanceStreamResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from stratbox.macrobanks.cbr_industries.parser import concat_cbr_0105a_debt_corp_streams
        from stratbox.macrobanks.cbr_industries.regions import normalize_cbr_0105a_debt_corp_regions_to_latest

        invocation.stage("parse")
        if not req.sources:
            raise OperationFailure("request.source_selection_empty")
        try:
            selected = tuple(report_date_from_filename(x.source_name) for x in req.sources)
        except ValueError:
            raise OperationFailure("request.source_filename_invalid") from None
        if len(set(selected)) != len(selected):
            raise OperationFailure("request.duplicate_release")
        parsed, failures = [], []
        for number, item in enumerate(req.sources, start=1):
            invocation.progress(number - 1, len(req.sources))
            try:
                parsed.append(_parse(item, invocation))
            except OperationFailure as error:
                if not req.continue_on_error or error.outcome == "cancelled":
                    raise
                failures.append(IssuanceSourceFailure(
                    "parse", item.source.source_id if item.source else item.source_name,
                    item.source_name, error.diagnostic.code))
        if not parsed:
            raise OperationFailure("source.no_valid_workbooks")
        invocation.stage("normalize_geography")
        files = normalize_cbr_0105a_debt_corp_regions_to_latest(parsed)
        stream = concat_cbr_0105a_debt_corp_streams(x.df_stream for x in files)
        stream = stream.sort_values(["report_date", "sheet_order", "region_order", "industry_order"],
                                    kind="stable").reset_index(drop=True)
        latest = max(files, key=lambda x: x.report_date)
        result = IssuanceStreamResult(
            tuple(x.source for x in req.sources if x.source is not None), tuple(failures),
            files, tuple(issue for x in files for issue in x.validation_issues),
            stream, tuple(x.report_date for x in files),
            tuple(x.reference_period for x in files), latest.report_date, max(selected),
            latest.report_date, latest.report_date == max(selected),
            latest.regions, latest.industries, len(stream),
        )
        if any(x.severity == "error" for x in result.validation_issues):
            return Completion(result, "failed", "source.validation_failed")
        if failures:
            return Completion(result, "partial", "source.selection_incomplete")
        return result
    return run(BUILD_STREAM, request, work, context=context)


def _apk(stream):
    from stratbox.macrobanks.cbr_industries.derived import (
        Cbr0105ADebtCorpDerivedIndustryError, calculate_cbr_0105a_debt_corp_apk_industry,
    )
    try:
        result = calculate_cbr_0105a_debt_corp_apk_industry(stream)
    except Cbr0105ADebtCorpDerivedIndustryError as exc:
        raise OperationFailure(f"derived.{exc.code.lower()}") from None
    # The shared formula keeps the 01_05 stream schema; restore the issuance
    # reference-month dimension for the computed APK observations as well.
    if "reference_period" in stream.columns:
        lookup = stream[["report_date", "reference_period"]].drop_duplicates()
        if lookup["report_date"].duplicated().any():
            raise OperationFailure("source.reference_period_conflict")
        periods = dict(lookup.itertuples(index=False, name=None))
        frame = result.df_stream.copy()
        frame["reference_period"] = frame["report_date"].astype("object").map(periods)
        if frame["reference_period"].isna().any():
            raise OperationFailure("source.reference_period_missing")
        apk_rows = frame.loc[frame["industry_code"].astype("object").eq("apk")].copy()
        return replace(result, df_stream=frame, df_apk=apk_rows)
    return result


def calculate_apk(request: CalculateIssuanceApkRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        invocation.stage("calculate_derived")
        return _apk(req.stream)
    return run(CALCULATE_APK, request, work, context=context)


def build_pivots(request: PivotIssuanceRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        from stratbox.macrobanks.cbr_industries.pivots import (
            Cbr0105ADebtCorpPivotError, build_cbr_0105a_debt_corp_pivot_set,
        )
        invocation.stage("build_views")
        try:
            return build_cbr_0105a_debt_corp_pivot_set(req.stream, req.pivot, stream_result=req.source)
        except Cbr0105ADebtCorpPivotError as exc:
            raise OperationFailure(f"pivot.{exc.code.lower()}") from None
    return run(PIVOT, request, work, context=context)


def render_industry(request: IssuanceWorkbookRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from stratbox.macrobanks.cbr_industries.contracts import Cbr0105ADebtCorpPivotRequest
        from stratbox.macrobanks.cbr_industries.pivots import (
            Cbr0105ADebtCorpPivotError, build_cbr_0105a_debt_corp_pivot_set,
        )
        from .export import render_issuance_workbook

        if not req.stream.ok:
            raise OperationFailure("source.stream_incomplete")
        invocation.stage("select_industry")
        frame = req.stream.df_stream
        if (req.industry_code == "apk" and req.calculate_apk_if_missing
            and not frame["industry_code"].astype("object").eq("apk").any()):
            frame = _apk(frame).df_stream
        subset = frame.loc[frame["industry_code"].astype("object").eq(req.industry_code)]
        names = subset["industry_name_ru"].dropna().unique()
        if len(names) != 1:
            raise OperationFailure("request.industry_unresolved")
        invocation.stage("build_views")
        try:
            tables = build_cbr_0105a_debt_corp_pivot_set(
                subset,
                Cbr0105ADebtCorpPivotRequest("region_code", "report_date",
                                               sheet_dimensions=("measure", "currency_scope"),
                                               max_sheet_count=3),
                stream_result=req.stream,
            )
            invocation.stage("render")
            return render_issuance_workbook(
                tables, industry_code=req.industry_code, industry_name_ru=str(names[0]),
                reference_periods=req.stream.reference_periods,
                include_metadata_sheet=req.include_metadata_sheet,
            )
        except (Cbr0105ADebtCorpPivotError, ValueError):
            raise OperationFailure("source.industry_views_invalid") from None
    return run(RENDER_INDUSTRY, request, work, context=context)
