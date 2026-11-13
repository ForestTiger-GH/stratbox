"""Explicit SORS input, restoration, crosswalk and representation operations."""

from dataclasses import dataclass, fields
from pathlib import PurePosixPath

from stratbox.base.filestore import FileStore
from stratbox.base.ioapi.bytes import read_bounded_bytes
from stratbox.base.utils.optional_deps import require_extra
from stratbox.data import SourcePayload
from stratbox.data.representation import XLSX
from stratbox.execution import (
    Completion,
    ExecutionContext,
    OperationDefinition,
    OperationFailure,
    OperationResult,
    run,
)
from stratbox.macrobanks._cbr import WORKBOOK_LIMIT, admit_workbook, validate_workbook

from .contracts import (
    SorsCrosswalkConfig,
    SorsPivotRequest,
    SorsRunConfig,
    SorsSourceBundle,
    SorsSourceFiles,
    SorsSourceInputs,
    SorsWorkbookRequest,
)
from .results import (
    SorsCrosswalkResult,
    SorsPivotResult,
    SorsRestorationResult,
    SorsWorkbookResult,
)


@dataclass(frozen=True, slots=True)
class LoadSorsRequest:
    sources: SorsSourceInputs
    config: SorsRunConfig


@dataclass(frozen=True, slots=True)
class RestoreSorsRequest:
    source: SorsSourceInputs | SorsSourceBundle
    config: SorsRunConfig


@dataclass(frozen=True, slots=True)
class CrosswalkSorsRequest:
    strict: SorsRestorationResult
    config: SorsCrosswalkConfig


@dataclass(frozen=True, slots=True)
class PivotSorsRequest:
    result: SorsRestorationResult | SorsCrosswalkResult
    pivot: SorsPivotRequest


@dataclass(frozen=True, slots=True)
class RenderSorsRequest:
    result: SorsRestorationResult | SorsCrosswalkResult
    workbook: SorsWorkbookRequest = SorsWorkbookRequest()


READ = OperationDefinition(
    "cbr.sors.read_source_files",
    1,
    "sors-file-read-1",
    SorsSourceFiles,
    SorsSourceInputs,
    frozenset({"filestore"}),
)
LOAD = OperationDefinition(
    "cbr.sors.load_sources",
    1,
    "sors-source-bundle-1",
    LoadSorsRequest,
    SorsSourceBundle,
)
RESTORE = OperationDefinition(
    "cbr.sors.restore",
    1,
    "sors-multiscope-rounding-dominance-2026.7",
    RestoreSorsRequest,
    SorsRestorationResult,
)
CROSSWALK = OperationDefinition(
    "cbr.sors.crosswalk",
    1,
    "sors-crosswalk-1",
    CrosswalkSorsRequest,
    SorsCrosswalkResult,
)
PIVOT = OperationDefinition(
    "cbr.sors.build_pivot", 1, "sors-pivot-1", PivotSorsRequest, SorsPivotResult
)
RENDER = OperationDefinition(
    "cbr.sors.render_workbook", 1, "sors-xlsx-1", RenderSorsRequest, SorsWorkbookResult
)


def read_source_files(
    request: SorsSourceFiles,
    *,
    store: FileStore | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[SorsSourceInputs]:
    def work(req, invocation):
        invocation.stage("read_sources")
        loaded = {}
        for field in fields(SorsSourceFiles):
            invocation.check_cancelled()
            location = getattr(req, field.name)
            if location is None:
                continue
            path = str(location)
            try:
                data = read_bounded_bytes(
                    path, store=store, limit=WORKBOOK_LIMIT, budget=invocation.budget,
                    checkpoint=invocation.check_cancelled,
                )
            except ValueError:
                raise OperationFailure("source.size_limit") from None
            except OSError:
                raise OperationFailure("storage.source_unreadable") from None
            if not 0 < len(data) <= WORKBOOK_LIMIT:
                raise OperationFailure("source.size_limit")
            loaded[field.name] = SourcePayload(
                data, XLSX, PurePosixPath(path.replace("\\", "/")).name
            )
        return SorsSourceInputs(**loaded)

    return run(READ, request, work, context=context, providers={"filestore": store})


def _load(sources, config, invocation):
    require_extra("pandas", "dataframe")
    require_extra("openpyxl", "excel")
    from .sources.loader import parse_source_inputs

    invocation.stage("load_sources")
    for field in fields(SorsSourceInputs):
        invocation.check_cancelled()
        payload = getattr(sources, field.name)
        if payload is not None:
            invocation.budget.charge("input_bytes", payload.identity.size)
            admit_workbook(payload.data, invocation)
    try:
        bundle = parse_source_inputs(
            sources, config.as_of_date, publication_step=config.publication_step
        )
    except (ValueError, KeyError, OSError):
        raise OperationFailure("source.sors_bundle_invalid") from None
    for receipt in bundle.lineage:
        invocation.use(receipt)
    return bundle


def load_sources(
    request: LoadSorsRequest, *, context: ExecutionContext | None = None
) -> OperationResult[SorsSourceBundle]:
    return run(
        LOAD,
        request,
        lambda req, inv: _load(req.sources, req.config, inv),
        context=context,
    )


def _solver_time_left(invocation) -> float:
    invocation.check_cancelled()
    return invocation.budget.seconds_left()


def restore(
    request: RestoreSorsRequest, *, context: ExecutionContext | None = None
) -> OperationResult[SorsRestorationResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        from .operations import restore_bundle
        from .linear.highs import solver_budget
        from .optimization import SorsOptimizationFixedPointLimitError
        from .publication import SorsPublicationFixedPointLimitError

        bundle = (
            req.source
            if isinstance(req.source, SorsSourceBundle)
            else _load(req.source, req.config, invocation)
        )
        for receipt in bundle.lineage:
            invocation.use(receipt)
        try:
            with solver_budget(lambda: _solver_time_left(invocation)):
                result = restore_bundle(bundle, req.config, stage=invocation.stage)
        except (
            SorsOptimizationFixedPointLimitError,
            SorsPublicationFixedPointLimitError,
        ):
            raise OperationFailure("sors.fixed_point_limit") from None
        except ValueError:
            raise OperationFailure("sors.model_invalid") from None
        if result.summary.strict_status == "SOLVER_UNAVAILABLE":
            return Completion(result, "failed", "provider.capability_missing")
        if result.summary.strict_status != "OPTIMAL":
            return Completion(result, "failed", "sors.feasibility_unconfirmed")
        return result

    return run(RESTORE, request, work, context=context)


def crosswalk(
    request: CrosswalkSorsRequest, *, context: ExecutionContext | None = None
) -> OperationResult[SorsCrosswalkResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        from .crosswalk.operations import run_sors_crosswalk
        from .linear.highs import solver_budget

        invocation.stage("crosswalk")
        if req.strict._source_bundle is not None:
            for receipt in req.strict._source_bundle.lineage:
                invocation.use(receipt)
        try:
            with solver_budget(lambda: _solver_time_left(invocation)):
                value = run_sors_crosswalk(
                    req.strict, req.config, checkpoint=invocation.check_cancelled
                )
        except ValueError:
            raise OperationFailure("sors.crosswalk_request_invalid") from None
        if value.status == "SOLVER_UNAVAILABLE":
            return Completion(value, "failed", "provider.capability_missing")
        return value

    return run(CROSSWALK, request, work, context=context)


def build_pivot(
    request: PivotSorsRequest, *, context: ExecutionContext | None = None
) -> OperationResult[SorsPivotResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        from .pivots import build_sors_pivot

        invocation.stage("build_pivot")
        try:
            return build_sors_pivot(req.result, req.pivot)
        except (ValueError, KeyError):
            raise OperationFailure("sors.pivot_request_invalid") from None

    return run(PIVOT, request, work, context=context)


def render_workbook(
    request: RenderSorsRequest, *, context: ExecutionContext | None = None
) -> OperationResult[SorsWorkbookResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("xlsxwriter", "excel")
        from .export import render_sors_workbook

        invocation.stage("render")
        return render_sors_workbook(
            req.result, req.workbook, checkpoint=invocation.check_cancelled
        )

    return run(RENDER, request, work, context=context)
