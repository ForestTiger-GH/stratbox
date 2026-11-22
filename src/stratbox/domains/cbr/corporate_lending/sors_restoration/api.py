"""Explicit SORS input, restoration, crosswalk and representation operations."""

from dataclasses import (
    asdict, fields, replace,
)
from pathlib import PurePosixPath
from decimal import Decimal

from stratbox.core.storage.filestore import FileStore
from stratbox.core.storage.bytes import read_bounded_bytes
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.data.lineage import input_value
from stratbox.shared.data.representation import XLSX
from stratbox.core.execution import (
    Completion, ExecutionContext, OperationFailure, OperationResult, run,
)
from stratbox.core.operations.tables import record_tables, use_tables
from stratbox.domains.cbr._source import WORKBOOK_LIMIT, admit_workbook

from .contracts import (
    SorsSourceBundle, SorsSourceFiles, SorsSourceInputs,
)
from .results import (
    SorsCrosswalkResult,
    SorsPivotResult,
    SorsRestorationResult,
    SorsWorkbookResult,
)

from .definitions import (
    CROSSWALK, CrosswalkSorsRequest, LOAD, LoadSorsRequest, PIVOT, PivotSorsRequest, READ, RENDER, RESTORE, RenderSorsRequest, RestoreSorsRequest, _TABLES,
)


def read_source_files(
    request: SorsSourceFiles,
    *,
    store: FileStore | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[SorsSourceInputs]:
    def work(req, invocation, given_store=store):
        store = invocation.provider("filestore", given_store)
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
            payload = SourcePayload(data, XLSX, PurePosixPath(path.replace("\\", "/")).name)
            invocation.use(UsedInputReceipt.for_payload(payload, field.name))
            loaded[field.name] = payload
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
        if isinstance(payload, SourcePayload):
            invocation.budget.charge("input_bytes", payload.identity.size)
            admit_workbook(payload.data, invocation)
        elif payload is not None and getattr(payload, "evidence", None) is not None:
            # The shared 0105a extractor is a declared computational parent.
            # No original workbook is reopened when a sealed flake is supplied.
            invocation.parents.append((field.name + "_flake", payload.evidence))
            invocation.use(UsedInputReceipt(field.name + "_flake", payload.evidence.output,
                                            "application/vnd.stratbox.table-manifest+json", "reference_only"))
    try:
        bundle = parse_source_inputs(
            sources, config.as_of_date, publication_step=config.publication_step
        )
    except (ValueError, KeyError, OSError):
        raise OperationFailure("source.sors_bundle_invalid") from None
    for receipt in bundle.lineage:
        invocation.use(receipt)
    return bundle


def _grid_tables(value):
    return tuple((item.name, getattr(value, item.name)) for item in fields(value) if item.name.endswith("_grid"))


def _parameters(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {name: _parameters(item) for name, item in value.items()}
    if isinstance(value, (tuple, list)):
        return tuple(_parameters(item) for item in value)
    return value


def _grid_metadata(value):
    if isinstance(value, SorsSourceBundle):
        return {
            "as_of_date": value.as_of_date, "publication_step": _parameters(value.publication_step),
            "coverage": asdict(value.coverage), "method_version": value.method_version,
            "lineage": [input_value(item) for item in value.lineage],
        }
    if isinstance(value, SorsRestorationResult):
        return {"summary": _parameters(asdict(value.summary)),
                "run_config": _parameters(asdict(value.run_config)) if value.run_config else None,
                "source_context": asdict(value.source_bundle.evidence.output) if value.source_bundle is not None and value.source_bundle.evidence else None}
    if isinstance(value, SorsCrosswalkResult):
        return {"status": value.status, "crosswalk_run_id": value.crosswalk_run_id,
                "crosswalk_config": _parameters(asdict(value.crosswalk_config)) if value.crosswalk_config else None,
                "strict_context": asdict(value.strict_result.evidence.output) if value.strict_result is not None and value.strict_result.evidence else None}
    return None


def _seal_grids(invocation, value, *, parameters=None):
    return replace(value, evidence=record_tables(
        invocation, _grid_tables(value), metadata=_grid_metadata(value), parameters=parameters,
        allow_infinite=True,
    ))


def _use_grids(invocation, value, role):
    # A separately supplied source bundle needs a sealed computation receipt.
    # Raw tables and a caller-written lineage do not prove a loaded source snapshot.
    if isinstance(value, SorsSourceBundle) and value.evidence is None:
        raise OperationFailure("input.snapshot_required")
    tables = _grid_tables(value)
    frames = use_tables(invocation, tables, receipt=value.evidence, role=role,
                        metadata=_grid_metadata(value), allow_infinite=True)
    if value.evidence is not None:
        for receipt in value.evidence.inputs:
            invocation.use(receipt)
    return replace(value, **{name: frame for (name, _), frame in zip(tables, frames, strict=True)})


def load_sources(
    request: LoadSorsRequest, *, context: ExecutionContext | None = None
) -> OperationResult[SorsSourceBundle]:
    def work(req, invocation):
        bundle = _load(req.sources, req.config, invocation)
        return _seal_grids(invocation, bundle, parameters={
            "as_of": req.config.as_of_date, "publication_step": Decimal(str(req.config.publication_step)),
        })

    return run(LOAD, request, work, context=context)


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
            _use_grids(invocation, req.source, "sors_source_bundle")
            if isinstance(req.source, SorsSourceBundle)
            else _load(req.source, req.config, invocation)
        )
        if bundle.as_of_date is not None and bundle.as_of_date != req.config.as_of_date:
            raise OperationFailure("sors.source_period_mismatch")
        if bundle.publication_step is not None and bundle.publication_step != req.config.publication_step:
            raise OperationFailure("sors.source_publication_step_mismatch")
        regions, classes = len(bundle.atomic_regions_grid), len(bundle.okved2_classes_grid)
        invocation.budget.check("cells", regions * classes * 6 * 30)
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
        if result.source_bundle is not None:
            # The solver attaches observation bindings. Seal the resulting bundle
            # before handing it to a separately invoked crosswalk.
            result = replace(result, source_bundle=_seal_grids(invocation, result.source_bundle))
        result = _seal_grids(invocation, result, parameters=_parameters(asdict(req.config)))
        if result.summary.strict_status == "SOLVER_UNAVAILABLE":
            return Completion(result, "failed", "provider.capability_missing")
        if result.summary.strict_status != "OPTIMAL":
            return Completion(result, "failed", "sors.feasibility_unconfirmed")
        return result

    return run(RESTORE, request, work, context=context)


def run_crosswalk(
    request: CrosswalkSorsRequest, *, context: ExecutionContext | None = None
) -> OperationResult[SorsCrosswalkResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        from .crosswalk.operations import run_sors_crosswalk
        from .linear.highs import solver_budget

        invocation.stage("crosswalk")
        strict = _use_grids(invocation, req.strict, "sors_restoration")
        if strict.source_bundle is not None:
            strict = replace(strict, source_bundle=_use_grids(invocation, strict.source_bundle, "sors_source_bundle"))
        from .crosswalk.mapping import capture_mapping_inputs

        try:
            with solver_budget(lambda: _solver_time_left(invocation)), capture_mapping_inputs(invocation.use):
                value = run_sors_crosswalk(
                    strict, req.config, checkpoint=invocation.check_cancelled
                )
        except ValueError:
            raise OperationFailure("sors.crosswalk_request_invalid") from None
        value = _seal_grids(invocation, value, parameters=_parameters(asdict(req.config)))
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
        result = _use_grids(invocation, req.result, "sors_result")
        try:
            value = build_sors_pivot(result, req.pivot, budget=invocation.budget)
        except (ValueError, KeyError):
            raise OperationFailure("sors.pivot_request_invalid") from None
        evidence = record_tables(invocation, (("pivot", value.table),), parameters=asdict(req.pivot),
                                 allow_infinite=True)
        return replace(value, evidence=evidence)

    return run(PIVOT, request, work, context=context)


def render_workbook(
    request: RenderSorsRequest, *, context: ExecutionContext | None = None
) -> OperationResult[SorsWorkbookResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("xlsxwriter", "excel")
        from .export import render_sors_workbook

        invocation.stage("render")
        result = _use_grids(invocation, req.result, "sors_result")
        if isinstance(result, SorsCrosswalkResult) and result.strict_result is not None:
            result = replace(result, strict_result=_use_grids(invocation, result.strict_result, "sors_restoration"))
        value = render_sors_workbook(
            result, req.workbook, checkpoint=invocation.check_cancelled, budget=invocation.budget,
        )
        invocation.record(value.representation.identity, parameters={
            "profile": value.representation.profile_id, **asdict(req.workbook),
        })
        return value

    return run(RENDER, request, work, context=context)
