"""Independent typed operations for monthly 01_04_A corporate loan issuance."""

from __future__ import annotations

from dataclasses import replace
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
from stratbox.core.operations.tables import seal_stream, use_stream
from stratbox.domains.cbr.publications.access import (
    HTML_TYPES, WORKBOOK_LIMIT, XLSX_TYPES, official_url, receive_cbr,
    admit_workbook,
    validate_workbook,
)

from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import BuildIssuanceStreamRequest
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import CalculateIssuanceApkRequest
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import DiscoverIssuanceRequest
from stratbox.domains.cbr.tables.corporate_lending.issuance.contracts import IssuanceSourceFailure
from stratbox.domains.cbr.publications.corporate_lending.contracts import IssuanceSourceLink
from stratbox.domains.cbr.integration.corporate_lending.issuance.contracts import IssuanceStreamResult
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import IssuanceWorkbookRequest
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import RenderIssuanceIndustriesRequest
from stratbox.domains.cbr.products.corporate_lending.issuance.contracts import IssuanceWorkbooksResult
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import ParseIssuanceRequest
from stratbox.domains.cbr.tables.corporate_lending.issuance.contracts import ParsedIssuanceFile
from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import PivotIssuanceRequest
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotRequest
from stratbox.domains.cbr.tables.corporate_lending.issuance.selection import resolve_industry_codes
from stratbox.domains.cbr.tables.corporate_lending.issuance.selection import selection_parameters
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySelection
from stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers import _seal_pivots
from stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers import _select_industry
from stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers import _stream_metadata
from stratbox.domains.cbr.operations.corporate_lending.industry.extraction import record_flakes
from stratbox.domains.cbr.operations.corporate_lending.industry.extraction import seal_flake
from stratbox.domains.cbr.tables.corporate_lending.industry.sources import industry_source_uses
from stratbox.domains.cbr.integration.corporate_lending.industry.integration import assemble_flakes
from stratbox.domains.cbr.publications.corporate_lending.issuance import CBR_SORS_INDEX_URL
from stratbox.domains.cbr.publications.corporate_lending.issuance_editions import SERIES_CODE
from stratbox.domains.cbr.publications.corporate_lending.issuance import discover_links
from stratbox.domains.cbr.publications.corporate_lending.issuance_editions import reference_period
from stratbox.domains.cbr.publications.corporate_lending.issuance_editions import report_date_from_filename

from stratbox.domains.cbr.operations.corporate_lending.issuance.definitions import ACQUIRE
from stratbox.domains.cbr.operations.corporate_lending.issuance.definitions import BUILD_STREAM
from stratbox.domains.cbr.operations.corporate_lending.issuance.definitions import CALCULATE_APK
from stratbox.domains.cbr.operations.corporate_lending.issuance.definitions import DISCOVER
from stratbox.domains.cbr.operations.corporate_lending.issuance.definitions import PARSE
from stratbox.domains.cbr.operations.corporate_lending.issuance.definitions import PIVOT
from stratbox.domains.cbr.operations.corporate_lending.issuance.definitions import RENDER_INDUSTRIES
from stratbox.domains.cbr.operations.corporate_lending.issuance.definitions import RENDER_INDUSTRY
from stratbox.domains.cbr.operations.corporate_lending.issuance.definitions import _DATASET

_ROOTS = ("/vfs/statistics/", "/content/document/file/")


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
    return run(DISCOVER, request, work, context=context, providers={"http": transport})


def acquire(request: IssuanceSourceLink, *, transport: HttpTransport | None = None,
            context: ExecutionContext | None = None) -> OperationResult[AcquiredSource]:
    def work(req, invocation):
        invocation.stage("acquire")
        _check_source(req)
        received = receive_cbr(req.url, roots=_ROOTS, media_types=XLSX_TYPES,
                               limit=WORKBOOK_LIMIT, source_id=req.source_id,
                               transport=transport, invocation=invocation)
        validate_workbook(received.payload.data, budget=invocation.budget)
        return received
    return run(ACQUIRE, request, work, context=context, providers={"http": transport})


def _parse(req: ParseIssuanceRequest, invocation, *, selection: IndustrySelection | None = None) -> ParsedIssuanceFile:
    require_extra("pandas", "dataframe")
    require_extra("openpyxl", "excel")
    from stratbox.domains.cbr.tables.corporate_lending.issuance.parser import parse_workbook

    chosen = req.selection if selection is None else selection
    try:
        resolve_industry_codes(chosen)
    except ValueError:
        raise OperationFailure("request.industry_selection_invalid") from None
    use_payload(req.payload, invocation, role="source_workbook", limit=WORKBOOK_LIMIT)
    if req.source is not None:
        _check_source(req.source)
        if req.source.source_name != req.source_name:
            raise OperationFailure("request.source_identity_mismatch")
    admit_workbook(req.payload.data, invocation)
    try:
        return parse_workbook(req.payload.data, source_name=req.source_name,
                              source_url=req.source.url if req.source else None,
                              source_sha256=req.payload.identity.sha256,
                              checkpoint=invocation.check_cancelled, selection=chosen)
    except (ValueError, KeyError, OSError, IndexError, TypeError):
        raise OperationFailure("source.workbook_layout_unresolved") from None


def _parse_flake(req, invocation, *, selection=None):
    parsed = _parse(req, invocation, selection=selection)
    return seal_flake(parsed, req, PARSE, invocation, parameters={
        "report_date": parsed.report_date, "reference_period": parsed.reference_period,
        "unmapped_headers": parsed.unmapped_headers,
        **selection_parameters(parsed.selection),
    })


def parse(request: ParseIssuanceRequest, *, context: ExecutionContext | None = None
          ) -> OperationResult[ParsedIssuanceFile]:
    def work(req, invocation):
        invocation.stage("parse")
        parsed = _parse_flake(req, invocation)
        if any(issue.severity == "error" for issue in parsed.validation_issues):
            return Completion(parsed, "failed", "source.validation_failed")
        return parsed
    return run(PARSE, request, work, context=context)


def build_stream(request: BuildIssuanceStreamRequest, *, context: ExecutionContext | None = None
                 ) -> OperationResult[IssuanceStreamResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from stratbox.domains.cbr.integration.corporate_lending.industry.geography import normalize_cbr_0105a_debt_corp_regions_to_latest
        from stratbox.domains.cbr.operations.corporate_lending.issuance.snapshot_operations import _result

        invocation.stage("parse")
        if not req.sources:
            raise OperationFailure("request.source_selection_empty")
        try:
            resolve_industry_codes(req.selection)
        except ValueError:
            raise OperationFailure("request.industry_selection_invalid") from None
        try:
            selected = tuple(report_date_from_filename(x.source_name) for x in req.sources)
        except ValueError:
            raise OperationFailure("request.source_filename_invalid") from None
        if len(set(selected)) != len(selected):
            raise OperationFailure("request.duplicate_release")
        batch = attempt_batch(req.sources, lambda item: _parse_flake(item, invocation, selection=req.selection), invocation,
                              continue_on_error=req.continue_on_error)
        require_batch_values(batch, "source.no_valid_workbooks")
        failures = [
            IssuanceSourceFailure("parse", item.source.source_id if item.source else item.source_name,
                                  item.source_name, diagnostic.code)
            for item, diagnostic in batch.failed
        ]
        checkpoint = (lambda: None) if batch.stopped is not None else None
        if checkpoint is None:
            invocation.stage("normalize_geography")
        invocation.budget.check("cells", sum(item.df_stream.size for item in batch.values),
                                completed=checkpoint is not None)
        record_flakes(batch.values, invocation)
        result, parameters = assemble_flakes(batch.values, selected, family="0104a",
            normalize_geography=normalize_cbr_0105a_debt_corp_regions_to_latest,
            result_factory=_result, failures=tuple(failures),
            stop_reason=batch.stopped.code if batch.stopped else None)
        result = seal_stream(invocation, result, parameters={
            **parameters,
            **selection_parameters(req.selection),
            "reference_periods": result.reference_periods, "geography_anchor": result.latest_report_date,
            "geography_method": "cbr-0105a-geography-1", "coverage": "subset" if failures or batch.stopped else "complete",
            "not_started": [item[0].source_name if isinstance(item, tuple) else item.source_name for item in batch.remaining],
            "interrupted": batch.interrupted.source_name if batch.interrupted else None,
            "unmapped_headers": [pair for item in batch.values for pair in item.unmapped_headers],
        }, checkpoint=checkpoint)
        if any(x.severity == "error" for x in result.validation_issues):
            return Completion(result, "failed", "source.validation_failed")
        if batch.stopped or failures:
            return Completion(result, "partial", batch.stopped or "source.selection_incomplete")
        return result
    return run(BUILD_STREAM, request, work, context=context)


def _apk(stream, *, budget, source_uses=()):
    from stratbox.domains.cbr.analytics.corporate_lending.industry.apk import Cbr0105ADebtCorpDerivedIndustryError
    from stratbox.domains.cbr.analytics.corporate_lending.industry.apk import calculate_cbr_0105a_debt_corp_apk_industry
    try:
        result = calculate_cbr_0105a_debt_corp_apk_industry(stream, budget=budget, source_uses=source_uses)
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
        if isinstance(req.stream, IssuanceStreamResult) and not req.stream.ok:
            raise OperationFailure("source.stream_incomplete")
        if isinstance(req.stream, ParsedIssuanceFile) and any(
            item.severity == "error" for item in req.stream.validation_issues
        ):
            raise OperationFailure("source.validation_failed")
        stream = use_stream(invocation, req.stream)
        result = _apk(stream, budget=invocation.budget,
            source_uses=industry_source_uses(req.stream, frame=stream))
        return seal_stream(invocation, result, parameters={
            "components": result.source_industry_codes, "apk": result.apk_formula_ru, "lpk": result.lpk_formula_ru,
        })
    return run(CALCULATE_APK, request, work, context=context)


def build_pivots(request: PivotIssuanceRequest, *, context: ExecutionContext | None = None):
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
        except Cbr0105ADebtCorpPivotError as exc:
            raise OperationFailure(f"pivot.{exc.code.lower()}") from None
        return _seal_pivots(invocation, result, req.pivot, industry_code=req.industry_code)
    return run(PIVOT, request, work, context=context)


def _render_one_issuance(source, private_stream, industry_code, include_metadata_sheet, invocation, periods):
    """Build from an admitted private snapshot; one implementation for one or many books."""
    from stratbox.domains.cbr.products.corporate_lending.industry.views import Cbr0105ADebtCorpPivotError
    from stratbox.domains.cbr.products.corporate_lending.industry.views import build_cbr_0105a_debt_corp_pivot_set
    from stratbox.domains.cbr.products.corporate_lending.issuance.rendering import render_issuance_workbook

    derived = (industry_code == "apk"
               and not private_stream["industry_code"].astype("object").eq("apk").any())
    frame = _apk(private_stream, budget=invocation.budget).df_stream if derived else private_stream
    selected = frame.loc[frame["industry_code"].astype("object").eq(industry_code)]
    names = selected["industry_name_ru"].dropna().unique()
    if len(names) != 1:
        raise OperationFailure("request.industry_unresolved")
    invocation.stage("build_views")
    try:
        tables = build_cbr_0105a_debt_corp_pivot_set(
            selected,
            IndustryPivotRequest(
                "region_code", "report_date",
                sheet_dimensions=("measure", "currency_scope"), max_sheet_count=3,
            ),
            stream_result=source, budget=invocation.budget,
        )
        invocation.stage("render")
        value = render_issuance_workbook(
            tables, industry_code=industry_code, industry_name_ru=str(names[0]),
            reference_periods=periods, include_metadata_sheet=include_metadata_sheet,
            budget=invocation.budget,
        )
        return value, derived
    except (Cbr0105ADebtCorpPivotError, ValueError):
        raise OperationFailure("source.industry_views_invalid") from None


def render_industry(request: IssuanceWorkbookRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        if not req.stream.ok:
            raise OperationFailure("source.stream_incomplete")
        invocation.stage("select_industry")
        frame = use_stream(invocation, req.stream)
        periods = tuple(sorted(frame["reference_period"].dropna().unique()))
        if (req.industry_code == "apk" and not req.calculate_apk_if_missing
                and not frame["industry_code"].astype("object").eq("apk").any()):
            raise OperationFailure("request.industry_unresolved")
        value, derived = _render_one_issuance(
            req.stream, frame, req.industry_code, req.include_metadata_sheet, invocation, periods,
        )
        invocation.record(value.representation.identity, parameters={
            "profile": value.representation.profile_id, "industry": req.industry_code,
            "metadata_sheet": req.include_metadata_sheet, "reference_periods": periods,
            "derived_method": CALCULATE_APK.method_id if derived else None,
        })
        return value
    return run(RENDER_INDUSTRY, request, work, context=context)


def render_industries(
    request: RenderIssuanceIndustriesRequest, *, context: ExecutionContext | None = None
) -> OperationResult[IssuanceWorkbooksResult]:
    """Create multiple source-equivalent issuance workbooks with one input verification."""
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
        frame = use_stream(invocation, req.stream)
        periods = tuple(sorted(frame["reference_period"].dropna().unique()))
        items = []
        for code in req.industry_codes:
            invocation.check_cancelled()
            value, _ = _render_one_issuance(
                req.stream, frame, code, req.include_metadata_sheet, invocation, periods,
            )
            invocation.account_output(value.representation.identity, key=f"render:{code}")
            items.append(value)
        result = IssuanceWorkbooksResult(tuple(items))
        if not result.ok:
            raise OperationFailure("source.industry_views_invalid")
        manifest = [{"industry": item.industry_code, "profile": item.representation.profile_id,
                     "sha256": item.representation.identity.sha256, "size": item.representation.identity.size}
                    for item in items]
        invocation.record(ByteIdentity.of(canonical_manifest_bytes(manifest)), parameters={
            "industries": req.industry_codes, "reference_periods": periods,
            "include_metadata_sheet": req.include_metadata_sheet,
            "derived_method": CALCULATE_APK.method_id if "apk" in req.industry_codes else None,
        })
        return result
    return run(RENDER_INDUSTRIES, request, work, context=context)


def render_pivots(request, *, context: ExecutionContext | None = None):
    """Format a complete prepared view, including one restored from a snapshot."""
    from stratbox.domains.cbr.operations.corporate_lending.issuance.definitions import RENDER_PIVOTS

    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from stratbox.core.operations.tables import use_tables
        from stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers import _pivot_tables
        from stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers import _pivot_metadata
        from stratbox.domains.cbr.products.corporate_lending.issuance.rendering import render_issuance_workbook

        invocation.stage("render")
        if not req.tables.tables or req.tables.is_partial:
            raise OperationFailure("request.incomplete_views")
        frames = use_tables(invocation, _pivot_tables(req.tables), receipt=req.tables.evidence,
                            role="pivots", metadata=_pivot_metadata(req.tables))
        tables = replace(req.tables, tables=tuple(replace(table, df_table=frame)
            for table, frame in zip(req.tables.tables, frames, strict=True)))
        try:
            value = render_issuance_workbook(tables, industry_code=req.industry_code,
                industry_name_ru=req.industry_name_ru, reference_periods=req.reference_periods,
                include_metadata_sheet=req.include_metadata_sheet, budget=invocation.budget)
        except ValueError:
            raise OperationFailure("source.industry_views_invalid") from None
        invocation.record(value.representation.identity, parameters={
            "profile": value.representation.profile_id, "industry": req.industry_code,
            "industry_name": req.industry_name_ru, "reference_periods": req.reference_periods,
            "metadata_sheet": req.include_metadata_sheet,
        })
        return value
    return run(RENDER_PIVOTS, request, work, context=context)
