"""Independent receive, save, replay and reconciliation of exact source material."""

from __future__ import annotations

from dataclasses import (
    replace,
)
from hashlib import sha256

from stratbox.core.storage.filestore import (
    MutationRejected, SourceStore, StagedWriter,
)
from stratbox.core.storage.bytes import file_identity, read_bounded_bytes
from stratbox.core.storage.staging import (
    BoundedStage, WRITE_GUARANTEES, commit_staged, current_revision, storage_scope, store_identity, stream_identity,
)
from stratbox.core.network import (
    HttpTransport, StreamingHttpTransport,
)
from stratbox.shared.evidence import (
    AcquiredSource, MaterialReference, SourcePayload, UsedInputReceipt,
)
from stratbox.shared.identity import ByteIdentity

from stratbox.core.operations.source.acquisition import StreamBaseline, receive_source, receive_stream
from stratbox.core.execution.contracts import (
    EffectReceipt, ExecutionContext, OperationFailure,
)
from stratbox.core.execution.runner import Completion, run

from .original_definitions import (
    OriginalDestination, READ, RECEIVE, RECEIVE_TO_STORE, RECONCILE, ReadOriginalRequest, ReceiveOriginalRequest, ReceiveToStoreRequest, ReconcileOriginalRequest, SAVE, SaveOriginalRequest, StoredOriginal, _HTTP, _MATERIAL_LIMIT, _OUTPUT, _SOURCE, _WRITE,
)


def _receive_options(req, invocation):
    return dict(source_id=req.source_id, invocation=invocation, media_types=req.media_types,
                default_media_type=req.default_media_type, retry=req.retry, baseline=req.baseline)


def receive_original(request: ReceiveOriginalRequest, *, transport: HttpTransport | None = None,
                     context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("receive")
        value = receive_source(req.request, transport=transport, **_receive_options(req, invocation))
        invocation.use(UsedInputReceipt.for_payload(value.payload, "original"))
        return value
    return run(RECEIVE, request, work, context=context, providers={"http": transport})


def storage_effect(invocation, storage):
    state = {"stored": "confirmed", "already_present": "confirmed", "failed": "failed", "unknown": "unknown"}
    invocation.effect(EffectReceipt(
        "storage.write", state[storage.status], storage.destination, storage.effect_id,
        storage.stage, storage.identity, storage.guarantee, "store",
    ))


def _destination(target, store, invocation):
    if not target.locator or target.locator in {".", ".."} or "\x00" in target.locator:
        raise OperationFailure("effect.destination_invalid")
    if target.mode not in WRITE_GUARANTEES:
        raise OperationFailure("effect.mode_invalid")
    if target.mode == "replace_expected_revision" and not target.expected_revision:
        raise OperationFailure("effect.revision_required")
    if invocation.context.profile == "managed" and target.mode == "best_effort_verified":
        raise OperationFailure("effect.mode_forbidden")
    if not callable(getattr(store, "stage_write", None)) or not callable(getattr(store, "open_read", None)):
        raise OperationFailure("provider.capability_missing")


def _store(invocation, target, store, produce):
    _destination(target, store, invocation)
    result = None
    try:
        with store.stage_write(target.locator) as stage:
            invocation.stage("stage_original")
            bounded = BoundedStage(stage.stream, invocation.budget)
            identity, mime, source_id, charset, acquisition = produce(bounded)
            bounded.flush()
            try:
                verified = stream_identity(stage.stream, invocation.check_cancelled, limit=identity.size)
            except ValueError:
                raise OperationFailure("input.identity_mismatch") from None
            if verified != identity:
                raise OperationFailure("input.identity_mismatch")
            invocation.stage("commit_original")
            storage = commit_staged(
                stage, target.locator, identity, store=store, budget=invocation.budget,
                checkpoint=invocation.check_cancelled, mode=target.mode,
                expected_revision=target.expected_revision, plan_identity=identity,
                operation_id=invocation.definition.operation_id,
                require_admission=invocation.context.profile == "managed",
                on_effect=lambda receipt: storage_effect(invocation, receipt),
            )
            material = None
            if storage.status in {"stored", "already_present"}:
                material = MaterialReference(
                    target.locator, storage.store_id, identity, mime, source_id,
                    storage.observed_revision, charset, storage.store_scope,
                )
            result = StoredOriginal(storage, material, acquisition)
    except MutationRejected as error:
        if result is None:
            raise OperationFailure(error.code) from None
    except OSError:
        if result is None:
            raise OperationFailure("effect.staging_failed") from None
    return result


def _stored_completion(value):
    if value.material is not None:
        return value
    return Completion(value, value.storage.status, value.storage.diagnostic_code)


def save_original(request: SaveOriginalRequest, *, store: StagedWriter | None = None,
                  context: ExecutionContext | None = None):
    def work(req, invocation, given_store=store):
        store = invocation.provider("output_filestore", given_store)
        acquired = req.source if isinstance(req.source, AcquiredSource) else None
        payload = acquired.payload if acquired else req.source
        if not isinstance(payload, SourcePayload):
            raise OperationFailure("input.payload_required")
        invocation.budget.charge("input_bytes", payload.identity.size)
        invocation.use(UsedInputReceipt.for_payload(payload, "original"))

        def produce(sink):
            for offset in range(0, payload.identity.size, 65536):
                invocation.check_cancelled()
                sink.write(payload.data[offset:offset + 65536])
            return payload.identity, payload.media_type, payload.source_id, payload.charset, acquired.receipt if acquired else None

        return _stored_completion(_store(invocation, req.destination, store, produce))

    return run(SAVE, request, work, context=context, providers={"output_filestore": store})


def receive_original_to_store(req, *, transport, store, invocation, validate=None, baseline_store=None):
    """Stage one admitted HTTP source under the caller's existing operation and budget."""
    if not callable(getattr(transport, "exchange_into", None)):
        raise OperationFailure("provider.capability_missing")
    invocation.require_provider("output_filestore", store)
    options = _receive_options(req.source, invocation)
    prior = req.baseline
    if prior is not None:
        if req.source.baseline is not None or prior.material is None or prior.acquisition is None:
            raise OperationFailure("request.baseline_invalid")
        if prior.acquisition.identity != prior.material.identity:
            raise OperationFailure("input.identity_mismatch")
        reader = baseline_store if baseline_store is not None else store
        invocation.require_provider("filestore", reader)
        options["baseline"] = StreamBaseline(
            prior.acquisition, prior.material.charset,
            lambda sink: _copy_material(prior.material, reader, invocation, sink),
        )

    def produce(sink):
        receipt, charset = receive_stream(req.source.request, sink, transport=transport,
                                          **options)
        if validate is not None:
            validate(sink.stream, receipt.identity.size)
        invocation.use(UsedInputReceipt(
            "original", receipt.identity, receipt.media_type, "reference_only", receipt.source_id,
        ))
        return receipt.identity, receipt.media_type, receipt.source_id, charset, receipt

    return _store(invocation, req.destination, store, produce)


def receive_to_store(request: ReceiveToStoreRequest, *, transport: StreamingHttpTransport | None = None,
                     store: StagedWriter | None = None,
                     baseline_store: SourceStore | None = None,
                     context: ExecutionContext | None = None):
    def work(req, invocation, given_store=store):
        store = invocation.provider("output_filestore", given_store)
        return _stored_completion(receive_original_to_store(
            req, transport=invocation.provider("http", transport), store=store,
            invocation=invocation, baseline_store=baseline_store,
        ))
    return run(RECEIVE_TO_STORE, request, work, context=context,
               providers={"http": transport, "output_filestore": store})


def _material_admission(material, store, invocation, limit):
    if not isinstance(material, MaterialReference):
        raise OperationFailure("input.material_required")
    if not 0 <= limit <= _MATERIAL_LIMIT or material.identity.size > limit:
        raise OperationFailure("source.size_limit")
    try:
        matches = store_identity(store) == material.store_id and (
            material.store_scope is None or storage_scope(store, material.locator) == material.store_scope
        )
    except OSError:
        raise OperationFailure("input.material_unavailable") from None
    if not matches:
        raise OperationFailure("input.material_store_mismatch")
    invocation.budget.check("input_bytes", material.identity.size)


def _copy_material(material, store, invocation, sink):
    _material_admission(material, store, invocation, _MATERIAL_LIMIT)
    digest = sha256()
    size = 0
    try:
        revision = current_revision(store, material.locator)
        if material.revision is not None and revision != material.revision:
            raise OperationFailure("input.material_version_changed")
        with store.open_read(material.locator) as stream:
            while True:
                invocation.check_cancelled()
                chunk = stream.read(min(65536, material.identity.size - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                invocation.budget.charge("input_bytes", len(chunk))
                if size > material.identity.size:
                    raise OperationFailure("input.identity_mismatch")
                digest.update(chunk)
                if sink.write(chunk) != len(chunk):
                    raise OperationFailure("effect.staging_failed")
        if revision != current_revision(store, material.locator):
            raise OperationFailure("input.material_version_changed")
    except OSError:
        raise OperationFailure("input.material_unavailable") from None
    if ByteIdentity(digest.hexdigest(), size) != material.identity:
        raise OperationFailure("input.identity_mismatch")


def read_material(material, store, invocation, *, limit):
    _material_admission(material, store, invocation, limit)
    try:
        revision = current_revision(store, material.locator)
        if material.revision is not None and material.revision != revision:
            raise OperationFailure("input.material_version_changed")
        data = read_bounded_bytes(
            material.locator, store=store, limit=material.identity.size, budget=invocation.budget,
            checkpoint=invocation.check_cancelled,
        )
        if revision != current_revision(store, material.locator):
            raise OperationFailure("input.material_version_changed")
        payload = SourcePayload(data, material.media_type, material.source_id, charset=material.charset)
        if payload.identity != material.identity:
            raise OperationFailure("input.identity_mismatch")
    except ValueError:
        raise OperationFailure("input.identity_mismatch") from None
    except OSError:
        raise OperationFailure("input.material_unavailable") from None
    invocation.use(UsedInputReceipt.for_payload(payload, "original"))
    return payload


def read_original(request: ReadOriginalRequest, *, store: SourceStore | None = None, context: ExecutionContext | None = None):
    def work(req, invocation, given_store=store):
        store = invocation.provider("filestore", given_store)
        invocation.stage("read_original")
        return read_material(req.material, store, invocation, limit=req.limit)
    return run(READ, request, work, context=context, providers={"filestore": store})


def reconcile_original(request: ReconcileOriginalRequest, *, store: SourceStore | None = None,
                       context: ExecutionContext | None = None):
    def work(req, invocation, given_store=store):
        store = invocation.provider("filestore", given_store)
        invocation.stage("verify_destination")
        prior = req.receipt
        if store_identity(store) != prior.store_id or prior.effect_id is None:
            raise OperationFailure("input.material_store_mismatch")
        invocation.budget.charge("input_bytes", prior.identity.size)
        try:
            if prior.store_scope is not None and storage_scope(store, prior.destination) != prior.store_scope:
                raise OperationFailure("input.material_store_mismatch")
            revision = current_revision(store, prior.destination)
            actual = file_identity(prior.destination, store=store, limit=prior.identity.size,
                                   checkpoint=invocation.check_cancelled)
            if revision != current_revision(store, prior.destination):
                actual = None
        except (OSError, ValueError):
            revision, actual = None, None
        if actual == prior.identity:
            return replace(prior, status="already_present", stage="verify", diagnostic_code=None,
                           observed_identity=actual, observed_revision=revision)
        code = "effect.read_back_mismatch" if actual is not None else "effect.read_back_unavailable"
        value = replace(prior, status="unknown", stage="verify", diagnostic_code=code, observed_identity=actual)
        return Completion(value, "unknown", code)
    return run(RECONCILE, request, work, context=context, providers={"filestore": store})
