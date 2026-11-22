"""Independent report operations executed by the shared core runner."""
from __future__ import annotations

from stratbox.core.execution import OperationFailure, run
from stratbox.shared.evidence import UsedInputReceipt

from . import definitions as D
from .bindings import bind_family, bind_source
from ..publications.catalog import families
from ..publications.contracts import (
    AcquiredReport, AcquireRequest, AssessMaterialRequest, CaptureRequest, Catalog,
    DiscoveryRequest, InspectionRequest, Inventory, PreparedFile, PrepareFileRequest,
    SelectionRequest, SourceIndex, SourceCheckpoint, UpdateRequest,
)
from ..publications.discovery import index_identity, validate_index
from ..publications.materials import (
    MAX_MATERIAL_BYTES, MEDIA_TYPES, acquire_material, capture_material, validate_period,
)
from ..publications.naming import build_internal_file_name, identify_index
from ..publications.updates import assess_material as compare_material, assess_updates


def _error(error: Exception, fallback="frg.source.invalid") -> OperationFailure:
    code = str(error)
    if code.startswith("frg.") and len(code) <= 95 and all(c.isascii() and (c.isalnum() or c in "_.") for c in code):
        return OperationFailure(code)
    return OperationFailure(fallback)


def _bound_families(family_ids=()):
    if (not isinstance(family_ids, tuple) or any(not isinstance(x, str) for x in family_ids)
            or len(set(family_ids)) != len(family_ids)):
        raise ValueError("frg.discovery.families_invalid")
    return tuple(bind_family(key) for key in (family_ids or tuple(x.family_id for x in families())))


def _discover(request, store, invocation):
    bound = _bound_families(request.family_ids)
    if len({x.discovery.profile_id for x in bound}) != 1:
        raise ValueError("frg.profile.discovery_scope_mismatch")
    invocation.stage("discover_files")
    index = bound[0].discovery.discover(request, store, invocation=invocation)
    validate_index(index)
    return index


def _inspect(index, invocation):
    validate_index(index)
    bound = _bound_families(index.family_ids)
    invocation.stage("identify_reports")
    invocation.budget.charge("objects", len(index.entries))
    invocation.use(UsedInputReceipt("directory_index", index.identity,
                                    "application/json", "inline", "frg.directory_index"))
    return identify_index(index, sources=tuple((x.source, x.identification) for x in bound))


def _inventory(inventory, invocation):
    if not isinstance(inventory, Inventory) or _inspect(inventory.index, invocation) != inventory:
        raise ValueError("frg.inventory.identity_mismatch")
    return inventory


def _select(request, invocation):
    inventory = _inventory(request.inventory, invocation)
    bound = _bound_families(inventory.index.family_ids)
    available = tuple(item.source_id for parent in bound for item in parent.source.series)
    requested = request.selected_sources or available
    if (not isinstance(request.selected_sources, tuple)
            or any(not isinstance(x, str) for x in requested)
            or len(set(requested)) != len(requested) or set(requested) - set(available)):
        raise ValueError("frg.selection.sources_invalid")
    invocation.stage("select_latest_periods")
    selections = []
    for parent in bound:
        selected = tuple(x for x in requested if x in {s.source_id for s in parent.source.series})
        if selected:
            selections.extend(parent.selection.select(inventory, source_ids=selected))
    by_source = {item.source_id: item for item in selections}
    if len(by_source) != len(requested) or set(by_source) != set(requested):
        raise ValueError("frg.selection.profile_result_invalid")
    return tuple(by_source[key] for key in requested)


def _asset(asset):
    if asset.source_id is None or asset.family_id is None:
        raise ValueError("frg.material.asset_invalid")
    bound = bind_source(asset.source_id)
    request = DiscoveryRequest(".", family_ids=(bound.parent.source.family_id,))
    entries = (asset.entry,)
    index = SourceIndex(".", entries, index_identity(request, entries), request.family_ids)
    expected = identify_index(index, sources=((bound.parent.source, bound.parent.identification),)).assets[0]
    if not asset.valid or asset != expected:
        raise ValueError("frg.material.asset_mismatch")
    return bound


def _report(report):
    if not isinstance(report, AcquiredReport):
        raise ValueError("frg.material.report_required")
    bound = bind_source(report.source_id)
    if (report.format not in bound.parent.identification.admitted_formats
            or report.payload.media_type != MEDIA_TYPES.get(report.format)
            or report.payload.source_id != report.source_id
            or not 0 < report.payload.identity.size <= MAX_MATERIAL_BYTES):
        raise ValueError("frg.material.report_invalid")
    validate_period(report.period, periodicity=bound.series.periodicity,
                    min_period_date=bound.rule.min_period_date)
    if report.route == "filestore":
        if (report.entry is None or report.file_version is None
                or report.entry.path != report.file_version.path
                or report.payload.identity != report.file_version.identity):
            raise ValueError("frg.material.file_evidence_invalid")
        request = DiscoveryRequest(".", family_ids=(bound.parent.source.family_id,))
        entries = (report.entry,)
        index = SourceIndex(".", entries, index_identity(request, entries), request.family_ids)
        asset = identify_index(index, sources=((bound.parent.source, bound.parent.identification),)).assets[0]
        if not asset.valid or (asset.source_id, asset.period, asset.format) != (report.source_id, report.period, report.format):
            raise ValueError("frg.material.file_evidence_invalid")
    return bound


def _checkpoint(value):
    if not isinstance(value, SourceCheckpoint):
        raise ValueError("frg.update.checkpoint_invalid")
    bound = bind_source(value.source_id)
    validate_period(value.period, periodicity=bound.series.periodicity,
                    min_period_date=bound.rule.min_period_date)


def discover(request: DiscoveryRequest, *, store=None, selection=None, context=None):
    def work(req, invocation):
        try:
            return _discover(req, invocation.provider("filestore", store), invocation)
        except ValueError as error:
            raise _error(error) from None
        except OSError:
            raise OperationFailure("frg.discovery.storage_unavailable") from None
    return run(D.DISCOVER, request, work, context=context, providers={"filestore": store},
               provider_selections={"filestore": selection} if selection is not None else None)


def inspect(request: InspectionRequest, *, context=None):
    def work(req, invocation):
        try:
            return _inspect(req.index, invocation)
        except ValueError as error:
            raise _error(error) from None
    return run(D.INSPECT, request, work, context=context)


def select(request: SelectionRequest, *, context=None):
    def work(req, invocation):
        try:
            return _select(req, invocation)
        except ValueError as error:
            raise _error(error) from None
    return run(D.SELECT, request, work, context=context)


def scan(request: DiscoveryRequest, *, store=None, selection=None, context=None):
    def work(req, invocation):
        try:
            index = _discover(req, invocation.provider("filestore", store), invocation)
            inventory = _inspect(index, invocation)
            return Catalog(inventory, _select(SelectionRequest(inventory), invocation))
        except ValueError as error:
            raise _error(error) from None
        except OSError:
            raise OperationFailure("frg.discovery.storage_unavailable") from None
    return run(D.SCAN, request, work, context=context, providers={"filestore": store},
               provider_selections={"filestore": selection} if selection is not None else None)


def acquire(request: AcquireRequest, *, store=None, selection=None, context=None):
    def work(req, invocation):
        try:
            _asset(req.asset)
            invocation.stage("acquire_file")
            report = acquire_material(req, invocation.provider("filestore", store), invocation)
            invocation.account_output(report.payload.identity)
            return report
        except ValueError as error:
            raise _error(error) from None
        except OSError:
            raise OperationFailure("frg.material.storage_unavailable") from None
    return run(D.ACQUIRE, request, work, context=context, providers={"filestore": store},
               provider_selections={"filestore": selection} if selection is not None else None)


def capture(request: CaptureRequest, *, context=None):
    def work(req, invocation):
        try:
            bound = bind_source(req.source_id)
            invocation.stage("admit_supplied_original")
            report = capture_material(req, admitted_formats=bound.parent.identification.admitted_formats,
                                      periodicity=bound.series.periodicity,
                                      min_period_date=bound.rule.min_period_date, invocation=invocation)
            invocation.account_output(report.payload.identity)
            return report
        except ValueError as error:
            raise _error(error) from None
    return run(D.CAPTURE, request, work, context=context)


def prepare_file(request: PrepareFileRequest, *, context=None):
    def work(req, invocation):
        try:
            bound = _report(req.report)
            invocation.stage("prepare_standard_filename")
            invocation.budget.charge("input_bytes", req.report.payload.identity.size)
            invocation.use(UsedInputReceipt.for_payload(req.report.payload, "original"))
            profile = bound.parent.naming
            filename = build_internal_file_name(req.report.period, bound.rule,
                                                format=req.report.format, profile=profile)
            invocation.account_output(req.report.payload.identity)
            invocation.record(req.report.payload.identity, parameters={
                "source_id": req.report.source_id, "filename": filename,
                "format": req.report.format, "naming_profile": profile.profile_id,
                "naming_method": str(profile.method_version),
            })
            return PreparedFile(req.report.source_id, req.report.period, filename,
                                req.report.payload, profile.profile_id, str(profile.method_version))
        except ValueError as error:
            raise _error(error) from None
    return run(D.PREPARE_FILE, request, work, context=context)


def plan_updates(request: UpdateRequest, *, context=None):
    def work(req, invocation):
        try:
            expected = _select(SelectionRequest(req.catalog.inventory,
                               tuple(x.source_id for x in req.catalog.selections)), invocation)
            if expected != req.catalog.selections:
                raise ValueError("frg.update.catalog_mismatch")
            for checkpoint in req.checkpoints:
                _checkpoint(checkpoint)
            invocation.stage("assess_file_metadata")
            return assess_updates(req)
        except ValueError as error:
            raise _error(error) from None
    return run(D.PLAN_UPDATES, request, work, context=context)


def assess_material(request: AssessMaterialRequest, *, context=None):
    def work(req, invocation):
        try:
            _report(req.report)
            if req.checkpoint is not None:
                _checkpoint(req.checkpoint)
            invocation.stage("compare_original_bytes")
            invocation.use(UsedInputReceipt.for_payload(req.report.payload, "current_original"))
            return compare_material(req)
        except ValueError as error:
            raise _error(error) from None
    return run(D.ASSESS_MATERIAL, request, work, context=context)
