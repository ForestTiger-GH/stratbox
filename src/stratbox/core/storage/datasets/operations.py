"""Execution-qualified read, immutable publication and catalog operations."""

from __future__ import annotations

from stratbox.core.execution.contracts import EffectReceipt, ExecutionContext, OperationFailure
from stratbox.core.execution.runner import Completion, run
from stratbox.core.limits import BudgetError
from stratbox.core.runtime.capabilities import ProviderSelection
from stratbox.shared.data.snapshots import DatasetAssembly, DatasetSnapshot, SnapshotReference, identity_value
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from .codec import SNAPSHOT_MEDIA_TYPE, TABLE_MEDIA_TYPE
from .ports import DatasetReadControls, DatasetStorageError, DatasetWriteControls, DatasetWriteResult, selected_components, validate_scope, validate_snapshot

from .definitions import READ, WRITE, LIST, ReadSnapshotRequest, WriteSnapshotRequest, ListVersionsRequest, DatasetVersions


def _selection(request, role, provider, *, reference=False):
    selected = getattr(request, "selection", None)
    if selected is None and reference and provider is None and isinstance(request, ReadSnapshotRequest):
        ref = request.reference
        if isinstance(ref, SnapshotReference):
            selected = ProviderSelection(ref.provider_id, ref.scope_id)
    return {role: selected} if selected is not None else {}


def _error(error):
    code = str(error)
    if not code.startswith("dataset.") or not all(c.isalnum() or c in "._" for c in code):
        code = "dataset.value_invalid"
    return OperationFailure(code)


def read_snapshot(request: ReadSnapshotRequest, *, store=None, context: ExecutionContext | None = None):
    def work(req, invocation):
        reader = invocation.provider("dataset_reader", store)
        invocation.stage("read_snapshot")
        try:
            validate_scope(reader, req.reference)
            value = reader.read_snapshot(req.reference, req.components, controls=DatasetReadControls(
                budget=invocation.budget, checkpoint=invocation.check_cancelled))
            if not isinstance(value, DatasetSnapshot) or value.identity != req.reference.identity:
                raise DatasetStorageError("dataset.snapshot_mismatch")
            names = selected_components(value.manifest, req.components)
            if tuple(name for name, _ in value.tables) != names:
                raise DatasetStorageError("dataset.component_selection_mismatch")
        except (ValueError, TypeError) as error:
            raise _error(error) from None
        invocation.use(UsedInputReceipt("dataset_snapshot", value.identity, SNAPSHOT_MEDIA_TYPE, "reference_only",
                                        value.manifest.dataset_id, version=value.identity))
        for name, table in value.tables:
            invocation.use(UsedInputReceipt("dataset_component", table.identity, TABLE_MEDIA_TYPE, "inline",
                                            value.manifest.dataset_id, version=value.identity))
            invocation.account_output(table.identity, key=f"component:{name}")
        invocation.account_output(value.manifest.identity, key="manifest")
        identity = ByteIdentity.of(canonical_manifest_bytes({"manifest": identity_value(value.identity), "selected": names}))
        invocation.record(identity, parameters={"components": names})
        return value
    return run(READ, request, work, context=context, providers={"dataset_reader": store},
               provider_selections=_selection(request, "dataset_reader", store, reference=True))


def write_snapshot(request: WriteSnapshotRequest, *, store=None, context: ExecutionContext | None = None):
    def work(req, invocation):
        writer = invocation.provider("dataset_writer", store)
        invocation.stage("publish_snapshot")
        try:
            validate_snapshot(req.snapshot)
        except (ValueError, TypeError) as error:
            raise _error(error) from None
        snapshot = req.snapshot
        invocation.use(UsedInputReceipt("dataset_snapshot", snapshot.identity, SNAPSHOT_MEDIA_TYPE, "inline",
                                        snapshot.manifest.dataset_id, version=snapshot.identity))
        invocation.budget.charge("input_bytes", snapshot.identity.size)
        for receipt in snapshot.manifest.inputs:
            invocation.use(receipt)
        if isinstance(snapshot, DatasetSnapshot):
            for _, table in snapshot.tables:
                invocation.budget.charge("input_bytes", table.identity.size)
                invocation.budget.charge("cells", len(table.rows) * max(1, len(table.schema.columns)))
        effect_id = ByteIdentity.of(canonical_manifest_bytes({"provider": writer.provider_id, "scope": writer.scope_id,
            "dataset": snapshot.manifest.dataset_id, "version": snapshot.manifest.version_id,
            "identity": identity_value(snapshot.identity)})).sha256

        def publication(receipt):
            state = {"stored": "confirmed", "already_present": "confirmed", "failed": "failed", "unknown": "unknown"}[receipt.status]
            invocation.effect(EffectReceipt("dataset.write", state, snapshot.manifest.dataset_id, effect_id,
                "publish_snapshot", snapshot.identity, "immutable_version", "dataset_store"))

        def physical(receipt):
            state = {"stored": "confirmed", "already_present": "confirmed", "failed": "failed", "unknown": "unknown"}[receipt.status]
            invocation.effect(EffectReceipt("storage.write", state, receipt.destination, receipt.effect_id,
                receipt.stage, receipt.identity, receipt.guarantee, "store"))

        controls = DatasetWriteControls(invocation.budget, invocation.check_cancelled,
            invocation.context.profile == "managed", invocation.definition.operation_id, physical, publication)
        try:
            value = writer.write_snapshot(snapshot, controls=controls)
        except DatasetStorageError as error:
            publication(DatasetWriteResult(None, "failed", error.code))
            raise _error(error) from None
        except (BudgetError, OperationFailure):
            # The provider announces the actual commit boundary. A budget or
            # cancellation before that boundary has no uncertain logical write.
            raise
        except Exception:
            publication(DatasetWriteResult(None, "unknown", "effect.outcome_unknown"))
            raise
        if not isinstance(value, DatasetWriteResult):
            publication(DatasetWriteResult(None, "unknown", "dataset.write_receipt_invalid"))
            raise OperationFailure("dataset.write_receipt_invalid", outcome="unknown")
        if value.reference is not None:
            try:
                validate_scope(writer, value.reference)
                if (value.reference.dataset_id, value.reference.version_id, value.reference.identity) != (
                    snapshot.manifest.dataset_id, snapshot.manifest.version_id, snapshot.identity):
                    raise DatasetStorageError("dataset.snapshot_mismatch")
            except (ValueError, TypeError) as error:
                publication(DatasetWriteResult(None, "unknown", "dataset.write_receipt_invalid"))
                raise _error(error) from None
        publication(value)
        invocation.record(snapshot.identity, parameters={"dataset_id": snapshot.manifest.dataset_id,
                                                        "version_id": snapshot.manifest.version_id})
        if value.status not in {"stored", "already_present"}:
            return Completion(value, value.status, value.diagnostic_code or "dataset.publication_failed")
        return value
    return run(WRITE, request, work, context=context, providers={"dataset_writer": store},
               provider_selections=_selection(request, "dataset_writer", store))


def list_versions(request: ListVersionsRequest, *, store=None, context: ExecutionContext | None = None):
    def work(req, invocation):
        catalog = invocation.provider("dataset_catalog", store)
        invocation.stage("list_versions")
        try:
            references = catalog.versions(req.dataset_id, controls=DatasetReadControls(
                budget=invocation.budget, checkpoint=invocation.check_cancelled))
            if not isinstance(references, tuple):
                raise DatasetStorageError("dataset.catalog_invalid")
            versions = set()
            for ref in references:
                validate_scope(catalog, ref)
                if ref.dataset_id != req.dataset_id or ref.version_id in versions:
                    raise DatasetStorageError("dataset.catalog_mismatch")
                versions.add(ref.version_id)
        except (ValueError, TypeError) as error:
            raise _error(error) from None
        return DatasetVersions(req.dataset_id, references)
    return run(LIST, request, work, context=context, providers={"dataset_catalog": store},
               provider_selections=_selection(request, "dataset_catalog", store))
