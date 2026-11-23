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
from stratbox.domains.cbr.publications.access import WORKBOOK_LIMIT, admit_workbook

from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceBundle
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceFiles
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceInputs
from stratbox.domains.cbr.analytics.corporate_lending.sors.results import SorsCrosswalkResult
from stratbox.domains.cbr.products.corporate_lending.sors.results import SorsPivotResult
from stratbox.domains.cbr.analytics.corporate_lending.sors.results import SorsRestorationResult
from stratbox.domains.cbr.products.corporate_lending.sors.results import SorsWorkbookResult

from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import CROSSWALK
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import CrosswalkSorsRequest
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import LOAD
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import PrepareSorsOriginalsRequest
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import PIVOT
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import PivotSorsRequest
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import READ
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import RENDER
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import RESTORE
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import RenderSorsRequest
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import RestoreSorsRequest
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import _TABLES


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
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.loader import parse_source_inputs

    invocation.stage("prepare_inputs")
    from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake
    from stratbox.domains.cbr.tables.corporate_lending.observations import CorporateSourceDataset
    admitted = {}
    for field in fields(SorsSourceInputs):
        invocation.check_cancelled()
        payload = getattr(sources, field.name)
        if isinstance(payload, SourcePayload):
            require_extra("openpyxl", "excel")
            invocation.budget.charge("input_bytes", payload.identity.size)
            admit_workbook(payload.data, invocation)
        elif isinstance(payload, WorkbookFlake):
            invocation.use(UsedInputReceipt(field.name + "_flake", payload.identity,
                "application/vnd.stratbox.dataset+json", "reference_only", payload.series_id))
        elif isinstance(payload, CorporateSourceDataset):
            from stratbox.domains.cbr.operations.corporate_lending.source_operations import use_observations
            admitted[field.name] = use_observations(payload, invocation, role=field.name + "_observations")
        elif payload is not None and getattr(payload, "evidence", None) is not None:
            # The shared 0105a extractor is a declared computational parent.
            # No original workbook is reopened when a sealed flake is supplied.
            invocation.parents.append((field.name + "_flake", payload.evidence))
            invocation.use(UsedInputReceipt(field.name + "_flake", payload.evidence.output,
                                            "application/vnd.stratbox.table-manifest+json", "reference_only"))
    try:
        bundle = parse_source_inputs(
            replace(sources, **admitted), config.as_of_date, publication_step=config.publication_step
        )
    except (ValueError, KeyError, OSError):
        raise OperationFailure("source.sors_bundle_invalid") from None
    for receipt in bundle.lineage:
        invocation.use(receipt)
    supplied = dict(invocation.context.input_source_contexts).get("sources")
    if supplied is not None:
        uses = []
        for use in bundle.source_uses:
            matches = [item for item in supplied.uses if item.coordinate.source_id == use.coordinate.source_id
                       and item.coordinate.material_identity == use.coordinate.material_identity
                       and item.input_role in {use.input_role, "sources." + use.input_role}]
            if len(matches) > 1:
                raise OperationFailure("sors.source_context_ambiguous")
            if matches:
                supplied_use = matches[0]
                coordinate = replace(use.coordinate,
                    issue_id=supplied_use.coordinate.issue_id or use.coordinate.issue_id,
                    asset_id=supplied_use.coordinate.asset_id or use.coordinate.asset_id)
                uses.append(replace(use, coordinate=coordinate, qualification=supplied_use.qualification))
            else:
                uses.append(use)
        bundle = replace(bundle, source_uses=tuple(uses))
    return bundle


from stratbox.domains.cbr.analytics.corporate_lending.sors.identity import (
    grid_tables as _grid_tables, grid_metadata as _grid_metadata, parameters as _parameters,
)


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


def prepare_from_originals(
    request: PrepareSorsOriginalsRequest, *, context: ExecutionContext | None = None
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


def _restore_bundle(bundle, config, invocation):
    require_extra("pandas", "dataframe")
    from stratbox.domains.cbr.analytics.corporate_lending.sors.operations import restore_bundle
    from stratbox.domains.cbr.analytics.corporate_lending.sors.linear.highs import solver_budget
    from stratbox.domains.cbr.analytics.corporate_lending.sors.optimization import SorsOptimizationFixedPointLimitError
    from stratbox.domains.cbr.analytics.corporate_lending.sors.publication import SorsPublicationFixedPointLimitError


    if bundle.as_of_date is not None and bundle.as_of_date != config.as_of_date:
        raise OperationFailure("sors.source_period_mismatch")
    if bundle.publication_step is not None and bundle.publication_step != config.publication_step:
        raise OperationFailure("sors.source_publication_step_mismatch")
    regions, classes = len(bundle.atomic_regions_grid), len(bundle.okved2_classes_grid)
    invocation.budget.check("cells", regions * classes * 6 * 30)
    try:
        with solver_budget(lambda: _solver_time_left(invocation)):
            result = restore_bundle(bundle, config, stage=invocation.stage)
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
    result = _seal_grids(invocation, result, parameters=_parameters(asdict(config)))
    if result.summary.strict_status == "SOLVER_UNAVAILABLE":
        return Completion(result, "failed", "provider.capability_missing")
    if result.summary.strict_status != "OPTIMAL":
        return Completion(result, "failed", "sors.feasibility_unconfirmed")
    return result


def restore(request: RestoreSorsRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        if not isinstance(req.source, SorsSourceBundle):
            raise OperationFailure("sors.prepared_bundle_required")
        return _restore_bundle(_use_grids(invocation, req.source, "sors_source_bundle"), req.config, invocation)
    return run(RESTORE, request, work, context=context)


def restore_from_originals(request, *, context=None):
    from .definitions import RESTORE_FROM_ORIGINALS
    def work(req, invocation):
        return _restore_bundle(_load(req.sources, req.config, invocation), req.config, invocation)
    return run(RESTORE_FROM_ORIGINALS, request, work, context=context)


def _prepare_retained(req, invocation, *, interpret):
    from stratbox.domains.cbr.tables.corporate_lending.observations import CorporateSourceDataset
    from stratbox.domains.cbr.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile
    from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake
    for item in fields(req.sources):
        value = getattr(req.sources, item.name)
        if value is None:
            continue
        accepted = (ParsedCbr0105ADebtCorpFile,) if item.name == "regional_traditional" else (
            (CorporateSourceDataset, WorkbookFlake) if interpret else (CorporateSourceDataset,))
        if not isinstance(value, accepted):
            raise OperationFailure("sors.source_flakes_required" if interpret else "sors.source_observations_required")
    bundle = _load(req.sources, req.config, invocation)
    return _seal_grids(invocation, bundle, parameters={"as_of": req.config.as_of_date,
        "publication_step": Decimal(str(req.config.publication_step))})


def prepare_inputs(request, *, context=None):
    from .definitions import PREPARE
    return run(PREPARE, request, lambda req, invocation: _prepare_retained(req, invocation, interpret=False), context=context)


def prepare_from_flakes(request, *, context=None):
    from .definitions import PREPARE_FROM_FLAKES
    return run(PREPARE_FROM_FLAKES, request, lambda req, invocation: _prepare_retained(req, invocation, interpret=True), context=context)


def run_crosswalk(
    request: CrosswalkSorsRequest, *, context: ExecutionContext | None = None
) -> OperationResult[SorsCrosswalkResult]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        from stratbox.domains.cbr.analytics.corporate_lending.sors.crosswalk.operations import run_sors_crosswalk
        from stratbox.domains.cbr.analytics.corporate_lending.sors.linear.highs import solver_budget

        invocation.stage("crosswalk")
        strict = _use_grids(invocation, req.strict, "sors_restoration")
        if strict.source_bundle is not None:
            strict = replace(strict, source_bundle=_use_grids(invocation, strict.source_bundle, "sors_source_bundle"))
        from stratbox.domains.cbr.analytics.corporate_lending.sors.crosswalk.mapping import capture_mapping_inputs

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
        from stratbox.domains.cbr.products.corporate_lending.sors.views import build_sors_pivot

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


def build_views(request, *, context=None):
    from .definitions import VIEWS
    from stratbox.domains.cbr.products.corporate_lending.sors.pack import build_sors_views
    from stratbox.domains.cbr.products.corporate_lending.sors.snapshots import view_metadata
    def work(req, invocation):
        invocation.stage("build_views")
        source = _use_grids(invocation, req.result, "sors_result")
        if isinstance(source, SorsCrosswalkResult) and source.strict_result is not None:
            source = replace(source, strict_result=_use_grids(invocation, source.strict_result, "sors_strict_result"))
        try:
            value = build_sors_views(source, req.workbook, checkpoint=invocation.check_cancelled, budget=invocation.budget)
        except (ValueError, KeyError, TypeError):
            raise OperationFailure("sors.view_request_invalid") from None
        return replace(value, evidence=record_tables(invocation, value.tables, metadata=view_metadata(value),
            parameters=asdict(req.workbook), allow_infinite=True))
    return run(VIEWS, request, work, context=context)


def _use_views(value, invocation):
    from stratbox.domains.cbr.products.corporate_lending.sors.snapshots import validate_view_pack, view_metadata
    try:
        validate_view_pack(value, require_seal=True)
    except ValueError as error:
        raise OperationFailure(str(error)) from None
    frames = use_tables(invocation, value.tables, receipt=value.evidence, role="sors_views",
                        metadata=view_metadata(value), allow_infinite=True)
    return replace(value, tables=tuple((name, frame) for (name, _), frame in zip(value.tables, frames, strict=True)))


def render_views(request: RenderSorsRequest, *, context=None):
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("xlsxwriter", "excel")
        from stratbox.domains.cbr.products.corporate_lending.sors.rendering import render_sors_views
        invocation.stage("render")
        value = render_sors_views(_use_views(req.views, invocation), checkpoint=invocation.check_cancelled,
                                  budget=invocation.budget)
        invocation.record(value.representation.identity, parameters={"profile": value.representation.profile_id})
        return value
    return run(RENDER, request, work, context=context)
