"""Independent receive, save, replay and reconciliation of exact source material."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256

from stratbox.base.filestore import MutationRejected, SourceStore, StagedWriter, WriteMode
from stratbox.base.ioapi.bytes import file_identity, read_bounded_bytes
from stratbox.base.ioapi.staging import (
    BoundedStage, WRITE_GUARANTEES, commit_staged, current_revision, storage_scope, store_identity, stream_identity,
)
from stratbox.base.limits import ExecutionBudget
from stratbox.base.net import HttpRequest, HttpTransport, RetryPolicy, StreamingHttpTransport
from stratbox.data import (
    AcquiredSource, AcquisitionReceipt, ByteIdentity, MaterialReference, SourcePayload, StoredBytesReceipt,
    UsedInputReceipt,
)

from .acquisition import StreamBaseline, receive_source, receive_stream
from .contracts import EffectReceipt, ExecutionContext, OperationDefinition, OperationFailure
from .runner import Completion, run

_HTTP = frozenset({"http"})
_OUTPUT = frozenset({"output_filestore"})
_SOURCE = frozenset({"filestore"})
_WRITE = frozenset({"storage.write"})
_MATERIAL_LIMIT = 512 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ReceiveOriginalRequest:
    request: HttpRequest
    source_id: str
    media_types: frozenset[str]
    retry: RetryPolicy = RetryPolicy()
    baseline: AcquiredSource | None = field(default=None, repr=False)
    default_media_type: str | None = None


@dataclass(frozen=True, slots=True)
class OriginalDestination:
    locator: str = field(repr=False)
    mode: WriteMode = "immutable"
    expected_revision: str | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class SaveOriginalRequest:
    source: SourcePayload | AcquiredSource
    destination: OriginalDestination


@dataclass(frozen=True, slots=True)
class ReceiveToStoreRequest:
    source: ReceiveOriginalRequest
    destination: OriginalDestination
    baseline: StoredOriginal | None = None


@dataclass(frozen=True, slots=True)
class ReadOriginalRequest:
    material: MaterialReference
    limit: int = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ReconcileOriginalRequest:
    receipt: StoredBytesReceipt


@dataclass(frozen=True, slots=True)
class StoredOriginal:
    storage: StoredBytesReceipt
    material: MaterialReference | None
    acquisition: AcquisitionReceipt | None = None


RECEIVE = OperationDefinition("source.receive_original", 1, "http-receive-1", ReceiveOriginalRequest,
                              AcquiredSource, _HTTP)
SAVE = OperationDefinition("source.save_original", 1, "original-storage-1", SaveOriginalRequest,
                           StoredOriginal, _OUTPUT, _WRITE,
                           limits=ExecutionBudget(input_bytes=_MATERIAL_LIMIT, output_bytes=_MATERIAL_LIMIT,
                                                  temporary_bytes=_MATERIAL_LIMIT))
RECEIVE_TO_STORE = OperationDefinition(
    "source.receive_to_store", 1, "original-stream-1", ReceiveToStoreRequest, StoredOriginal,
    _HTTP | _OUTPUT, _WRITE,
    optional_capabilities=_SOURCE,
    limits=ExecutionBudget(input_bytes=_MATERIAL_LIMIT, output_bytes=_MATERIAL_LIMIT,
                           temporary_bytes=_MATERIAL_LIMIT),
)
READ = OperationDefinition("source.read_original", 1, "original-replay-1", ReadOriginalRequest, SourcePayload, _SOURCE)
RECONCILE = OperationDefinition("source.reconcile_original", 1, "original-read-back-1", ReconcileOriginalRequest,
                               StoredBytesReceipt, _SOURCE)


def _receive_options(req, invocation):
    return dict(source_id=req.source_id, invocation=invocation, media_types=req.media_types,
                default_media_type=req.default_media_type, retry=req.retry, baseline=req.baseline)


def receive_original(request: ReceiveOriginalRequest, *, transport: HttpTransport,
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
            raise OperationFailure("provider.capability_missing" if error.capability_missing else "effect.rejected") from None
    except OSError:
        if result is None:
            raise OperationFailure("effect.staging_failed") from None
    return result


def _stored_completion(value):
    if value.material is not None:
        return value
    return Completion(value, value.storage.status, value.storage.diagnostic_code)


def save_original(request: SaveOriginalRequest, *, store: StagedWriter,
                  context: ExecutionContext | None = None):
    def work(req, invocation):
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


def receive_to_store(request: ReceiveToStoreRequest, *, transport: StreamingHttpTransport, store: StagedWriter,
                     baseline_store: SourceStore | None = None,
                     context: ExecutionContext | None = None):
    def work(req, invocation):
        return _stored_completion(receive_original_to_store(
            req, transport=transport, store=store, invocation=invocation, baseline_store=baseline_store,
        ))
    return run(RECEIVE_TO_STORE, request, work, context=context,
               providers={"http": transport, "output_filestore": store})


def _material_admission(material, store, invocation, limit):
    if not isinstance(material, MaterialReference):
        raise OperationFailure("input.material_required")
    if not 0 <= limit <= _MATERIAL_LIMIT or material.identity.size > limit:
        raise OperationFailure("source.size_limit")
    if store_identity(store) != material.store_id or (
        material.store_scope is not None and storage_scope(store, material.locator) != material.store_scope
    ):
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


def read_original(request: ReadOriginalRequest, *, store: SourceStore, context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("read_original")
        return read_material(req.material, store, invocation, limit=req.limit)
    return run(READ, request, work, context=context, providers={"filestore": store})


def reconcile_original(request: ReconcileOriginalRequest, *, store: SourceStore,
                       context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("verify_destination")
        prior = req.receipt
        if store_identity(store) != prior.store_id or prior.effect_id is None or (
            prior.store_scope is not None and storage_scope(store, prior.destination) != prior.store_scope
        ):
            raise OperationFailure("input.material_store_mismatch")
        invocation.budget.charge("input_bytes", prior.identity.size)
        try:
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
