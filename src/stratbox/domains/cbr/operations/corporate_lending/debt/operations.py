"""Independent acquisition, normalization, calculation and rendering for 01_05_A_Debt_corp."""

from dataclasses import asdict, replace
from pathlib import PurePosixPath

from stratbox.core.network import HttpTransport
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.evidence import AcquiredSource
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.core.execution import (
    Completion, ExecutionContext, OperationFailure, OperationResult, run,
)
from stratbox.core.execution.batch import attempt_batch, require_batch_values
from stratbox.core.operations.source.validation import use_payload
from stratbox.core.operations.tables import (
    seal_stream, use_stream, use_tables,
)
from stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers import _stream_metadata
from stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers import _select_industry
from stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers import _pivot_tables
from stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers import _pivot_metadata
from stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers import _seal_pivots
from stratbox.domains.cbr.operations.corporate_lending.industry.extraction import record_flakes
from stratbox.domains.cbr.operations.corporate_lending.industry.extraction import seal_flake
from stratbox.domains.cbr.tables.corporate_lending.industry.sources import industry_source_uses
from stratbox.domains.cbr.integration.corporate_lending.industry.integration import assemble_flakes
from stratbox.domains.cbr.publications.access import (
    HTML_TYPES,
    WORKBOOK_LIMIT,
    XLSX_TYPES,
    official_url,
    receive_cbr,
    admit_workbook,
    validate_workbook,
)

from stratbox.domains.cbr.tables.corporate_lending.debt.selection import resolve_industry_codes
from stratbox.domains.cbr.tables.corporate_lending.debt.selection import selection_parameters
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import BuildIndustryStreamRequest
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import CalculateApkRequest
from stratbox.domains.cbr.analytics.corporate_lending.industry.contracts import IndustryApkCalculationResult as Cbr0105ADebtCorpApkCalculationResult
from stratbox.domains.cbr.products.corporate_lending.debt.contracts import Cbr0105ADebtCorpIndustryWorkbookRequest
from stratbox.domains.cbr.products.corporate_lending.debt.contracts import Cbr0105ADebtCorpIndustryWorkbookResult
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotRequest as Cbr0105ADebtCorpPivotRequest
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotSetResult as Cbr0105ADebtCorpPivotSetResult
from stratbox.domains.cbr.products.corporate_lending.debt.contracts import Cbr0105ADebtCorpPivotWorkbookResult
from stratbox.domains.cbr.tables.corporate_lending.debt.contracts import Cbr0105ADebtCorpSourceFailure
from stratbox.domains.cbr.publications.corporate_lending.contracts import Cbr0105ADebtCorpSourceLink
from stratbox.domains.cbr.integration.corporate_lending.debt.contracts import Cbr0105ADebtCorpStreamResult
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import DiscoverIndustriesRequest
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import ParseIndustryRequest
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySelection
from stratbox.domains.cbr.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import PivotInput
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import RenderIndustryRequest
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import RenderIndustriesRequest
from stratbox.domains.cbr.products.corporate_lending.debt.contracts import IndustryWorkbooksResult
from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import RenderPivotRequest

from stratbox.domains.cbr.operations.corporate_lending.debt.definitions import ACQUIRE
from stratbox.domains.cbr.operations.corporate_lending.debt.definitions import BUILD_STREAM
from stratbox.domains.cbr.operations.corporate_lending.debt.definitions import CALCULATE_APK
from stratbox.domains.cbr.operations.corporate_lending.debt.definitions import DISCOVER
from stratbox.domains.cbr.operations.corporate_lending.debt.definitions import PARSE
from stratbox.domains.cbr.operations.corporate_lending.debt.definitions import PIVOT
from stratbox.domains.cbr.operations.corporate_lending.debt.definitions import RENDER_INDUSTRIES
from stratbox.domains.cbr.operations.corporate_lending.debt.definitions import RENDER_INDUSTRY
from stratbox.domains.cbr.operations.corporate_lending.debt.definitions import RENDER_PIVOTS
from stratbox.domains.cbr.operations.corporate_lending.debt.definitions import _DATASET
from stratbox.domains.cbr.operations.corporate_lending.debt.definitions import _HTTP
from stratbox.domains.cbr.operations.corporate_lending.debt.definitions import _METHOD

_ROOTS = ("/vfs/statistics/", "/content/document/file/")


def discover(
    request: DiscoverIndustriesRequest,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[tuple[Cbr0105ADebtCorpSourceLink, ...]]:
    def work(req, invocation):
        from stratbox.domains.cbr.publications.corporate_lending.debt import CBR_SORS_INDEX_URL
        from stratbox.domains.cbr.publications.corporate_lending.debt import discover_cbr_0105a_debt_corp_links_from_html

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

    return run(DISCOVER, request, work, context=context, providers={"http": transport})


def _validate_link(source):
    from stratbox.domains.cbr.publications.corporate_lending.debt_editions import report_date_from_cbr_0105a_filename

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
    from stratbox.domains.cbr.tables.corporate_lending.debt.parser import parse_cbr_0105a_debt_corp_excel_bytes

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


def _parse_flake(req, invocation, *, selection=None):
    value = _parse(req, invocation, selection=selection)
    return seal_flake(value, req, PARSE, invocation, parameters={
        "report_date": value.report_date, "unmapped_headers": value.unmapped_headers,
        **selection_parameters(value.selection),
    })


def parse(
    request: ParseIndustryRequest, *, context: ExecutionContext | None = None
) -> OperationResult[ParsedCbr0105ADebtCorpFile]:
    def work(req, invocation):
        invocation.stage("parse")
        value = _parse_flake(req, invocation)
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
        from stratbox.domains.cbr.integration.corporate_lending.industry.geography import normalize_cbr_0105a_debt_corp_regions_to_latest
        from stratbox.domains.cbr.publications.corporate_lending.debt_editions import report_date_from_cbr_0105a_filename
        from stratbox.domains.cbr.operations.corporate_lending.debt.snapshot_operations import _result

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
                              lambda pair: _parse_flake(pair[0], invocation, selection=req.selection), invocation,
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
        record_flakes(batch.values, invocation)
        value, parameters = assemble_flakes(batch.values, selected, family="0105a",
            normalize_geography=normalize_cbr_0105a_debt_corp_regions_to_latest,
            result_factory=_result, failures=tuple(failures),
            stop_reason=batch.stopped.code if batch.stopped else None)
        value = seal_stream(invocation, value, parameters={
            **parameters,
            **selection_parameters(req.selection),
            "geography_anchor": value.latest_report_date, "geography_method": value.geography_method_version,
            "coverage": "subset" if failures or batch.stopped else "complete",
            "not_started": [item[0].source_name if isinstance(item, tuple) else item.source_name for item in batch.remaining],
            "interrupted": batch.interrupted[0].source_name if batch.interrupted else None,
            "unmapped_headers": [pair for item in batch.values for pair in item.unmapped_headers],
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
        from stratbox.domains.cbr.analytics.corporate_lending.industry.apk import Cbr0105ADebtCorpDerivedIndustryError
        from stratbox.domains.cbr.analytics.corporate_lending.industry.apk import calculate_cbr_0105a_debt_corp_apk_industry

        invocation.stage("calculate_derived")
        if isinstance(req.stream, Cbr0105ADebtCorpStreamResult) and not req.stream.ok:
            raise OperationFailure("source.stream_incomplete")
        if isinstance(req.stream, ParsedCbr0105ADebtCorpFile) and any(
            item.severity == "error" for item in req.stream.validation_issues
        ):
            raise OperationFailure("source.validation_failed")
        stream = use_stream(invocation, req.stream)
        try:
            value = calculate_cbr_0105a_debt_corp_apk_industry(stream, budget=invocation.budget,
                source_uses=industry_source_uses(req.stream, frame=stream))
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
        from stratbox.domains.cbr.products.corporate_lending.industry.views import Cbr0105ADebtCorpPivotError
        from stratbox.domains.cbr.products.corporate_lending.industry.views import build_cbr_0105a_debt_corp_pivot_set

        invocation.stage("build_views")
        stream = use_stream(invocation, req.stream, source=req.source)
        stream = _select_industry(stream, req.industry_code)
        try:
            result = build_cbr_0105a_debt_corp_pivot_set(
                stream, req.pivot, stream_result=_stream_metadata(req), budget=invocation.budget,
                source_uses=industry_source_uses(req.stream, frame=stream),
            )
        except Cbr0105ADebtCorpPivotError as error:
            raise OperationFailure(f"pivot.{error.code.lower()}") from None
        return _seal_pivots(invocation, result, req.pivot, industry_code=req.industry_code)

    return run(PIVOT, request, work, context=context)


def render_pivots(
    request: RenderPivotRequest, *, context: ExecutionContext | None = None
) -> OperationResult[Cbr0105ADebtCorpPivotWorkbookResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from stratbox.domains.cbr.products.corporate_lending.debt.rendering import render_cbr_0105a_debt_corp_pivot_workbook

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
    from stratbox.domains.cbr.analytics.corporate_lending.industry.apk import Cbr0105ADebtCorpDerivedIndustryError
    from stratbox.domains.cbr.analytics.corporate_lending.industry.apk import calculate_cbr_0105a_debt_corp_apk_industry
    from stratbox.domains.cbr.products.corporate_lending.debt.rendering import render_cbr_0105a_debt_corp_industry_workbook
    from stratbox.domains.cbr.products.corporate_lending.industry.views import Cbr0105ADebtCorpPivotError
    from stratbox.domains.cbr.products.corporate_lending.industry.views import build_cbr_0105a_debt_corp_pivot_set

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
            "derived_method": CALCULATE_APK.method_id if derived else None,
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
            invocation.account_output(value.representation.identity, key=f"render:{code}")
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
            "derived_method": CALCULATE_APK.method_id if "apk" in req.industry_codes else None,
        })
        return result

    return run(RENDER_INDUSTRIES, request, work, context=context)
