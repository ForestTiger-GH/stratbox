"""Bounded material commands using explicit runtime provider ports."""
from __future__ import annotations

from dataclasses import replace
from tempfile import TemporaryFile
from typing import Mapping
from urllib.parse import urlsplit

from stratbox.core.execution.contracts import EffectReceipt, OperationFailure
from stratbox.core.network.contracts import HttpFailure, HttpRequest, HttpsEndpoint
from stratbox.core.storage.bytes import file_identity, read_bounded_bytes, write_verified_bytes
from stratbox.core.storage.staging import current_revision, storage_scope, store_identity
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import SourcePayload, StoredBytesReceipt, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes


def material_read(request: Mapping, invocation):
    supplied = request.get("material")
    limit = request.get("max_bytes", 16 * 1024 * 1024)
    if type(limit) is not int or limit < 1:
        raise OperationFailure("material.limit_invalid")
    if isinstance(supplied, SourcePayload):
        payload = supplied
    elif isinstance(supplied, Representation):
        payload = SourcePayload(supplied.data, supplied.media_type)
    elif isinstance(supplied, bytes):
        payload = SourcePayload(supplied, request.get("media_type", "application/octet-stream"))
    elif "path" in request:
        store = invocation.provider("filestore")
        data = read_bounded_bytes(request["path"], store=store, limit=limit,
                                  checkpoint=invocation.check_cancelled)
        payload = SourcePayload(data, request.get("media_type", "application/octet-stream"))
    else:
        raise OperationFailure("material.supplied_required")
    if payload.identity.size > limit:
        raise OperationFailure("material.size_limit")
    invocation.budget.charge("input_bytes", payload.identity.size)
    invocation.use(UsedInputReceipt.for_payload(payload, "source"))
    return payload


def material_attribute(request: Mapping, invocation):
    """Attach a logical source use after physical representation acquisition."""
    material = request["material"]
    if not isinstance(material, SourcePayload):
        raise OperationFailure("material.source_payload_required")
    source_id = request.get("source_id")
    if source_id is not None and (not isinstance(source_id, str) or not source_id):
        raise OperationFailure("material.source_identity_invalid")
    payload = replace(material, source_id=source_id)
    invocation.use(UsedInputReceipt.for_payload(payload, "source"))
    return payload


def http_acquire(request: Mapping, invocation):
    """Stream when the provider supports it; all materialization is size bound."""
    if not request.get("allow_network", True):
        raise OperationFailure("source.network_forbidden")
    provider = invocation.provider("http")
    limit = request.get("max_bytes", 16 * 1024 * 1024)
    if type(limit) is not int or not 1 <= limit <= 512 * 1024 * 1024:
        raise OperationFailure("material.limit_invalid")
    exchange = request.get("request")
    if exchange is None:
        url = request["url"]
        parts = urlsplit(url)
        exchange = HttpRequest("GET", url,
            (HttpsEndpoint(parts.hostname or "", parts.path or "/", allow_query=bool(parts.query)),),
            max_response_bytes=limit, budget=invocation.budget,
            headers=request.get("headers", {}))
    elif isinstance(exchange, HttpRequest):
        exchange = replace(exchange, max_response_bytes=min(exchange.max_response_bytes, limit), budget=invocation.budget)
    else:
        raise OperationFailure("material.http_request_required")
    into = getattr(provider, "exchange_into", None)
    if callable(into):
        class BoundedSink:
            size = 0
            def __init__(self, stream): self.stream = stream
            def write(self, data):
                invocation.check_cancelled()
                if self.size + len(data) > exchange.max_response_bytes:
                    raise OperationFailure("material.size_limit")
                invocation.budget.charge("temporary_bytes", len(data))
                count = self.stream.write(data)
                if count != len(data):
                    raise OperationFailure("material.staging_short_write")
                self.size += count
                return count
            def __getattr__(self, name): return getattr(self.stream, name)
        with TemporaryFile(mode="w+b") as stage:
            bounded = BoundedSink(stage)
            received = into(exchange, bounded, cancelled=invocation.cancelled)
            if isinstance(received, HttpFailure):
                raise OperationFailure("http." + received.reason)
            response = received.response
            stage.seek(0)
            data = stage.read(exchange.max_response_bytes + 1)
            if ByteIdentity.of(data) != received.identity:
                raise OperationFailure("material.stream_identity_mismatch")
    else:
        response = provider.exchange(exchange, cancelled=invocation.cancelled)
        if isinstance(response, HttpFailure):
            raise OperationFailure("http." + response.reason)
        data = response.body
    if not 200 <= response.status_code < 300:
        raise OperationFailure(f"http.status_{response.status_code}")
    if len(data) > exchange.max_response_bytes:
        raise OperationFailure("material.size_limit")
    media = request.get("media_type", response.headers.get("content-type", "application/octet-stream").split(";", 1)[0])
    payload = SourcePayload(data, media)
    invocation.use(UsedInputReceipt.for_payload(payload, "source"))
    if "network.receive" in invocation.definition.possible_effects:
        effect_id = ByteIdentity.of(canonical_manifest_bytes({"url": exchange.url, "content": payload.identity.sha256})).sha256
        invocation.effect(EffectReceipt("network.receive", "confirmed", effect_id=effect_id,
            identity=payload.identity, guarantee="acquisition_receipt"))
    return payload


def store_commit(request: Mapping, invocation):
    """Commit exact encoded bytes using provider CAS and attempt authority."""
    material = request["material"]
    if isinstance(material, (SourcePayload, Representation)):
        data, identity = material.data, material.identity
    elif isinstance(material, bytes):
        data, identity = material, ByteIdentity.of(material)
    else:
        raise OperationFailure("store.encoded_material_required")
    store = invocation.provider("output_filestore")
    destination = request["destination"]
    mode = request.get("mode", "immutable")
    expected = request.get("expected_revision")
    if mode not in {"immutable", "replace_expected_revision"}:
        raise OperationFailure("store.conditional_commit_required")
    resource = storage_scope(store, destination) + ":" + destination
    effect_id = ByteIdentity.of(canonical_manifest_bytes({"resource": resource,
        "payload": identity.sha256, "mode": mode, "revision": expected,
        "source_revision": request.get("source_revision"), "input_basis": request.get("input_basis")})).sha256
    stored = []
    def action():
        receipt = write_verified_bytes(destination, data, store=store, expected_sha256=identity.sha256,
            mode=mode, expected_revision=expected, cancelled=invocation.cancelled)
        receipt = replace(receipt, effect_id=effect_id, store_scope=storage_scope(store, destination),
            observed_revision=current_revision(store, destination) if receipt.status in {"stored", "already_present"} else None)
        stored.append(receipt)
        state = "confirmed" if receipt.status in {"stored", "already_present"} else receipt.status
        return EffectReceipt("storage.write", state, reference=destination, effect_id=effect_id,
            identity=identity, guarantee=receipt.guarantee, stage=receipt.stage, reconciliation_owner="output_filestore")
    invocation.account_output(identity, key="commit:" + effect_id)
    effect = invocation.commit_effect("storage.write", effect_id, action, resource=resource, identity=identity,
        expected_revision=expected, input_basis=request.get("input_basis"), source_revision=request.get("source_revision"))
    if stored:
        return stored[0]
    # A confirmed authority replay has no second provider mutation. Availability
    # at this destination is checked separately from the historical receipt.
    observed = file_identity(destination, store=store, limit=identity.size, checkpoint=invocation.check_cancelled)
    if observed != identity:
        raise OperationFailure("effect.replay_resource_changed")
    return StoredBytesReceipt(destination, identity, "already_present", effect.guarantee,
        store_identity(store), observed_identity=observed, expected_revision=expected,
        effect_id=effect_id, observed_revision=current_revision(store, destination),
        store_scope=storage_scope(store, destination))
