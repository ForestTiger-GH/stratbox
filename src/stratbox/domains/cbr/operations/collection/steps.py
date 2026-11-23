"""One-item collection boundaries with explicit cumulative byte admission."""
from __future__ import annotations

from dataclasses import dataclass, replace

from stratbox.core.execution import Completion, OperationFailure, run
from stratbox.core.limits import BudgetError
from stratbox.core.runtime.capabilities import BindingError
from stratbox.operations.declarations import definition
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import SnapshotCoverage, identifier
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.material_collections import CollectionDisposition, CollectionManifest, CollectionMember
from stratbox.domains.cbr.publications.collection.contracts import Collection, CollectFilesRequest, CollectToStoreRequest
from stratbox.domains.cbr.publications.contracts import IdentifyRequest
from .material_definitions import CollectMaterial, MaterialCollection


@dataclass(frozen=True, slots=True)
class CollectMaterialStepRequest:
    item: CollectMaterial
    previous: MaterialCollection | None = None
    max_batch_bytes: int = 256 * 1024**2
    continue_on_error: bool = True
    final: bool = True


@dataclass(frozen=True, slots=True)
class CollectStoredStepRequest:
    request: CollectToStoreRequest
    previous: Collection | None = None
    max_batch_bytes: int = 256 * 1024**2
    continue_on_error: bool = True
    final: bool = True


@dataclass(frozen=True, slots=True)
class CollectRawStepRequest:
    request: CollectFilesRequest
    previous: Collection | None = None
    max_batch_bytes: int = 256 * 1024**2
    continue_on_error: bool = True
    final: bool = True


def _validate(maximum, continue_on_error, final):
    if type(maximum) is not int or not 0 < maximum <= 256 * 1024**2:
        raise OperationFailure("cbr.collection.selection_invalid")
    if type(continue_on_error) is not bool or type(final) is not bool:
        raise OperationFailure("cbr.collection.selection_invalid")


def collect_material_step(request, *, transport=None, store=None, context=None):
    def work(req, invocation):
        from .materials import _receive
        from stratbox.domains.cbr.publications.catalog import source
        from stratbox.domains.cbr.publications.admission import identify_value
        _validate(req.max_batch_bytes, req.continue_on_error, req.final)
        item = req.item
        if not isinstance(item, CollectMaterial):
            raise OperationFailure("cbr.collection.selection_invalid")
        identifier(item.key)
        if item.format not in source(item.series_id).formats:
            raise OperationFailure("cbr.publication.format_unsupported")
        previous = req.previous
        originals = [] if previous is None else list(previous.originals)
        members = [] if previous is None else list(previous.manifest.members)
        dispositions = [] if previous is None else list(previous.manifest.dispositions)
        inputs = [] if previous is None else list(previous.manifest.inputs)
        if item.key in {member.key for member in dispositions}:
            raise OperationFailure("cbr.collection.selection_invalid")
        remaining = req.max_batch_bytes - sum(member.identity.size for member in members)
        reason = None
        if previous is not None and not previous.manifest.complete and not req.continue_on_error:
            reason = "cbr.collection.previous_failure"
        elif remaining <= 0:
            reason = "budget.batch_bytes"
        if reason is not None:
            dispositions.append(CollectionDisposition(item.key, "not_attempted", reason))
        else:
            try:
                invocation.check_cancelled()
                payload = _receive(item, invocation, transport, store, remaining)
                if payload.identity.size > remaining:
                    raise OperationFailure("budget.batch_bytes")
                value = identify_value(IdentifyRequest(item.series_id, item.issue_id, payload,
                    item.format, item.asset_id), invocation)
                name = item.name or f"{item.series_id}/{item.issue_id}/{item.asset_id}.{item.format}"
                member = CollectionMember(item.key, name,
                    DataContract("cbr.publication.original", role=DataRole.ORIGINALS), payload.identity,
                    payload.media_type, value.asset, value.artifact.identity)
                # Enforce duplicate destination/name rules before accepting this item.
                CollectionManifest("cbr.originals", "validation", tuple(members) + (member,),
                    tuple(dispositions) + (CollectionDisposition(item.key, "completed"),), SnapshotCoverage("unknown"))
                originals.append((item.key, value))
                members.append(member)
                dispositions.append(CollectionDisposition(item.key, "completed"))
                inputs.append(UsedInputReceipt("original", payload.identity, payload.media_type,
                    "reference_only" if item.material is not None else "inline", item.series_id))
                invocation.account_output(payload.identity)
            except (OperationFailure, BudgetError, BindingError) as error:
                reason = error.diagnostic.code if isinstance(error, OperationFailure) else error.code
                dispositions.append(CollectionDisposition(item.key, "failed", reason))
            except ValueError as error:
                reason = str(error) if str(error).startswith(("cbr.", "collection.", "source.")) else "cbr.collection.invalid_material"
                dispositions.append(CollectionDisposition(item.key, "failed", reason))
        manifest = CollectionManifest("cbr.originals", "content", tuple(members), tuple(dispositions),
            SnapshotCoverage("unknown", "Explicit selection; publisher historical coverage is unspecified."), tuple(inputs))
        manifest = replace(manifest, version_id=manifest.identity.sha256)
        value = MaterialCollection(tuple(originals), manifest)
        invocation.record(manifest.identity)
        if manifest.complete:
            return value
        reason = reason or next(item.diagnostic for item in dispositions if item.status != "completed")
        return Completion(value, "failed" if req.final and not originals else "partial", reason)
    return run(definition("cbr.file_collector.collect_material_step"), request, work,
               context=context, providers={"http": transport, "filestore": store})


def collect_stored_step(request, *, transport=None, store=None, context=None):
    def work(req, invocation):
        from .handlers import _collect
        _validate(req.max_batch_bytes, req.continue_on_error, req.final)
        if len(req.request.selection.source_ids) != 1:
            raise OperationFailure("cbr.collection.single_item_required")
        key = req.request.selection.source_ids[0]
        previous = req.previous
        if previous is not None and key in previous.selected:
            raise OperationFailure("request.source_selection_invalid")
        consumed = 0 if previous is None else sum(item.source.storage.identity.size for item in previous.completed)
        remaining = req.max_batch_bytes - consumed
        if remaining <= 0 or previous is not None and previous.failed and not req.continue_on_error:
            current = Collection((key,), (), (), (), (key,), stop_reason="budget.batch_bytes" if remaining <= 0 else "cbr.collection.previous_failure")
        else:
            current = _collect(replace(req.request.selection, max_batch_bytes=remaining), invocation,
                invocation.provider("http", transport), destinations=dict(req.request.destinations),
                store=invocation.provider("output_filestore", store))
            if isinstance(current, Completion):
                current = current.value
        value = current if previous is None else Collection(
            previous.selected + current.selected, previous.attempted + current.attempted,
            previous.completed + current.completed, previous.failed + current.failed,
            previous.not_attempted + current.not_attempted, current.interrupted or previous.interrupted,
            current.stop_reason or previous.stop_reason, current.unresolved or previous.unresolved)
        if value.unresolved is not None:
            return Completion(value, "unknown", value.stop_reason or "storage.commit_unknown")
        if value.failed or value.not_attempted or value.interrupted:
            return Completion(value, "failed" if req.final and not value.completed else "partial",
                              current.stop_reason or (current.failed[0].code if current.failed else None)
                              or value.stop_reason or "source.selection_incomplete")
        return value
    return run(definition("cbr.file_collector.collect_stored_step"), request, work,
               context=context, providers={"http": transport, "output_filestore": store})


def collect_raw_step(request, *, transport=None, context=None):
    def work(req, invocation):
        from .handlers import _collect
        _validate(req.max_batch_bytes, req.continue_on_error, req.final)
        if len(req.request.source_ids) != 1:
            raise OperationFailure("cbr.collection.single_item_required")
        key = req.request.source_ids[0]
        previous = req.previous
        if previous is not None and key in previous.selected:
            raise OperationFailure("request.source_selection_invalid")
        consumed = 0 if previous is None else sum(item.source.payload.identity.size for item in previous.completed)
        remaining = req.max_batch_bytes - consumed
        if remaining <= 0 or previous is not None and previous.failed and not req.continue_on_error:
            current = Collection((key,), (), (), (), (key,), stop_reason="budget.batch_bytes" if remaining <= 0 else "cbr.collection.previous_failure")
        else:
            current = _collect(replace(req.request, max_batch_bytes=remaining), invocation,
                               invocation.provider("http", transport))
            if isinstance(current, Completion):
                current = current.value
        value = current if previous is None else Collection(
            previous.selected + current.selected, previous.attempted + current.attempted,
            previous.completed + current.completed, previous.failed + current.failed,
            previous.not_attempted + current.not_attempted, current.interrupted or previous.interrupted,
            current.stop_reason or previous.stop_reason, None)
        if value.failed or value.not_attempted or value.interrupted:
            return Completion(value, "failed" if req.final and not value.completed else "partial",
                              current.stop_reason or (current.failed[0].code if current.failed else None)
                              or value.stop_reason or "source.selection_incomplete")
        return value
    return run(definition("cbr.file_collector.collect_raw_step"), request, work,
               context=context, providers={"http": transport})
