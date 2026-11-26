"""Prepare requests, acquire and inspect supplied materials through explicit providers."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import Assessment, FetchEvidence, IdentifiedMaterial, ImmutableMaterialRef, Material, PublicationAsset, ReadEvidence, RequestSpec, SourceClaim, fingerprint, request_identity
from ._settings import _get, _option
from ._values import _material
from ._storage import _provider_scope, _read


def request_prepare(inputs, settings, context):
    locator = inputs.get("locator") or _option(context, settings, "url")
    if hasattr(locator, "locator"):
        locator = locator.locator
    if isinstance(locator, Mapping):
        locator = locator.get("url", locator.get("locator"))
    if not isinstance(locator, str):
        raise ExecutionFailure("request.locator_required")
    return {"request": RequestSpec(locator, _option(context, settings, "method", "GET"),
        _get(settings, "headers", {}), _get(settings, "body"), _get(settings, "form"),
        _option(context, settings, "max_bytes", 16 * 1024 * 1024), _option(context, settings, "timeout", 60),
        source_id=_get(settings, "source_id"), observation_id=context.run_id)}


def material_fetch(inputs, settings, context):
    request = inputs["request"]
    if request.method not in {"GET", "POST"} or request.method == "POST" and not request.read_only:
        raise ExecutionFailure("http.read_only_request_required")
    provider = context.provider("http")
    context.checkpoint()
    budget = getattr(context, "budget", None)
    before = dict(budget.usage()) if budget else {}
    metered = bool(getattr(provider, "accounts_http_budget", False))
    if budget and not metered: budget.charge("requests", 1)
    if hasattr(provider, "fetch"):
        response = provider.fetch(request)
    elif callable(provider):
        response = provider(request)
    else:
        # Adapt a neutral provider's HTTP contract; no publisher dispatch occurs.
        from stratbox.core.network.contracts import HttpRequest, HttpsEndpoint
        from urllib.parse import urlsplit
        parts = urlsplit(request.url)
        exchange = HttpRequest(request.method, request.url,
            (HttpsEndpoint(parts.hostname, parts.path or "/", allow_query=True),), headers=request.headers,
            body=request.body, form_fields=request.form, deadline_seconds=request.timeout,
            max_response_bytes=request.max_bytes, read_only_post=request.method == "POST" and request.read_only,
            budget=budget)
        send = getattr(provider, "exchange", None) or getattr(provider, "request", None) or getattr(provider, "send", None)
        if send is None:
            raise ExecutionFailure("http.provider_protocol")
        response = send(exchange)
    if isinstance(response, Material):
        material, status, headers = response, 200, {}
    else:
        body = response if isinstance(response, bytes) else getattr(response, "body", getattr(response, "content", None))
        status, headers = getattr(response, "status_code", 200), getattr(response, "headers", {})
        if status == 304:
            retained = _option(context, settings, "retained_material")
            if retained is None:
                raise ExecutionFailure("http.retained_body_required")
            material = _material(retained)
        elif not 200 <= status < 300 or not isinstance(body, bytes):
            raise ExecutionFailure("http.response_failed:" + str(status))
        else:
            material = Material(body, headers.get("content-type", "application/octet-stream").split(";")[0],
                request.source_id, metadata={"url": request.url, **dict(request.metadata)})
    if len(material.data) > request.max_bytes:
        raise ExecutionFailure("http.response_limit")
    if budget:
        for resource, amount in (("wire_bytes", getattr(response, "wire_size", None) or len(material.data)),
                                  ("decoded_bytes", len(material.data))):
            already = budget.used(resource) - before.get(resource, 0)
            if amount > already: budget.charge(resource, amount - already)
    evidence = FetchEvidence(_request_identity(request), getattr(response, "observed_at_utc", datetime.now(timezone.utc)), status,
        material.identity, headers, request.observation_id or context.run_id,
        getattr(response, "effective_locator_safe", request.url), getattr(response, "origin_assurance", "provider_reported"),
        getattr(response, "transport_assurance", None), getattr(response, "route_id", None),
        getattr(response, "target_sha256", None), getattr(response, "logical_target_sha256", None))
    from dataclasses import replace
    material = replace(material, lineage=(*material.lineage, evidence))
    return {"material": material, "evidence": evidence}


def _request_identity(request):
    return request_identity(request)


def material_receive(inputs, settings, context):
    """Receive an original into bounded staging without materializing its body."""
    from stratbox.core.network.contracts import HttpRequest, HttpsEndpoint, HttpStreamResponse
    from urllib.parse import urlsplit
    request, destination = inputs["request"], inputs["destination"]
    if request.method not in {"GET", "POST"} or request.method == "POST" and not request.read_only:
        raise ExecutionFailure("http.read_only_request_required")
    if not isinstance(destination, str) or not destination: raise ExecutionFailure("storage.destination_required")
    transport, store = context.provider("http"), context.provider("filestore")
    if not callable(getattr(transport, "exchange_into", None)) or not callable(getattr(store, "stage_content", None)) or not getattr(store, "immutable_content", False):
        raise ExecutionFailure("streaming.provider_capability_required")
    parts = urlsplit(request.url)
    exchange = HttpRequest(request.method, request.url,
        (HttpsEndpoint(parts.hostname, parts.path or "/", allow_query=True),), headers=request.headers,
        form_fields=request.form, body=request.body, deadline_seconds=min(request.timeout, context.remaining_seconds()),
        max_response_bytes=request.max_bytes, read_only_post=request.method == "POST", budget=context.budget)
    scope = _provider_scope(store, destination)
    effect_id = fingerprint(("material.receive", scope, destination, request_identity(request), request.observation_id or context.run_id))
    accepted = context.accepted_input("request")
    def action():
        before = dict(context.budget.usage())
        if not getattr(transport, "accounts_http_budget", False): context.budget.charge("requests", 1)
        with store.stage_content(destination) as stage:
            class BoundedSink:
                def __init__(self): self.size = 0
                def write(self, data):
                    context.checkpoint()
                    if self.size + len(data) > request.max_bytes: raise ExecutionFailure("http.response_limit")
                    context.budget.charge("temporary_bytes", len(data))
                    result = stage.stream.write(data); self.size += len(data); return result
                def seek(self, *args): return stage.stream.seek(*args)
                def tell(self): return stage.stream.tell()
                def truncate(self, *args): return stage.stream.truncate(*args)
                def flush(self): return stage.stream.flush()
            response = transport.exchange_into(exchange, BoundedSink(), cancelled=lambda: bool(context.run.cancel.is_set() and not context.service._producer_needed(context.task)))
            if not isinstance(response, HttpStreamResponse) or not 200 <= response.response.status_code < 300:
                from stratbox.core.storage.filestore import MutationRejected
                raise MutationRejected("No accepted streamed response", code="http.streaming_response_failed")
            identity, observed = response.identity, response.response
            for resource, amount in (("wire_bytes", observed.wire_size or identity.size), ("decoded_bytes", identity.size)):
                spent = context.budget.used(resource) - before.get(resource, 0)
                if amount > spent: context.budget.charge(resource, amount - spent)
            evidence = FetchEvidence(request_identity(request), observed.observed_at_utc, observed.status_code, identity,
                observed.headers, request.observation_id or context.run_id, observed.effective_locator_safe,
                observed.origin_assurance, observed.transport_assurance, observed.route_id, observed.target_sha256, observed.logical_target_sha256)
            context.budget.account_output(effect_id, identity)
            if not callable(getattr(stage, "location", None)):
                raise ExecutionFailure("streaming.exact_stage_location_required")
            location = stage.location(identity)
            uses = ()
            if request.source_id:
                from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
                uses = (SourceUse(SourceCoordinate(request.source_id, issue_id=request.metadata.get("issue_id"),
                    asset_id=request.metadata.get("asset_id"), material_identity=identity), "material", "identified"),)
            reference = ImmutableMaterialRef(location, identity, str(getattr(store, "provider_id", "filestore")),
                (*(accepted["basis"] if accepted else ()), request_identity(request), evidence),
                accepted_value_id=accepted["id"] if accepted else None, effect_id=effect_id,
                provider_scope=_provider_scope(store, location), source_uses=uses,
                metadata={**dict(request.metadata), "url":request.url, "filename":Path(parts.path).name,
                    "media_type":observed.headers.get("content-type","application/octet-stream").split(";")[0], "source_id":request.source_id})
            context.update_effect_intent(effect_id, reference)
            if stage.commit(identity, checkpoint=context.checkpoint) != location:
                raise ExecutionFailure("streaming.retained_location_conflict")
            return reference
    receipt = context.effect("storage.write", effect_id, action, resource=str(destination),
        intent={"request_identity":request_identity(request),"provider_scope":scope,"destination":destination})
    if receipt.status != "confirmed": raise ExecutionFailure("streaming."+receipt.status, outcome="unknown" if receipt.status == "unknown" else "failed")
    evidence = next(item for item in reversed(receipt.value.lineage) if isinstance(item, FetchEvidence))
    return {"reference": receipt.value, "evidence": evidence, "receipt": receipt}


def material_read(inputs, settings, context):
    location = inputs["location"]
    expected = getattr(location, "identity", None)
    path = getattr(location, "location", getattr(location, "locator", location))
    data = _read(context.provider("filestore"), path, _option(context, settings, "max_bytes", 128 * 1024 * 1024))
    if getattr(context, "budget", None): context.budget.charge("input_bytes", len(data))
    source_id = getattr(location, "source_id", _get(settings, "source_id", getattr(location, "metadata", {}).get("source_id")))
    metadata = {**dict(getattr(location, "metadata", {})), "location": str(path)}
    metadata.setdefault("filename", Path(str(path)).name)
    if isinstance(location, PublicationAsset):
        metadata.update(dict(location.metadata), issue_id=location.issue_id, asset_id=location.asset_id, format=location.format)
    value = Material(data, _get(settings, "media_type", metadata.get("media_type", "application/octet-stream")), source_id, metadata=metadata,
        lineage=tuple(getattr(location, "lineage", ())))
    if expected is not None and expected != value.identity:
        raise ExecutionFailure("storage.identity_mismatch")
    evidence = ReadEvidence(str(path), value.identity, datetime.now(timezone.utc), _provider_scope(context.provider("filestore"), path))
    from dataclasses import replace
    return {"material": replace(value, lineage=(*value.lineage, evidence)), "evidence": evidence}


def material_list(inputs, settings, context):
    store, location = context.provider("filestore"), inputs["location"]
    limit = _option(context, settings, "max_items", 10000)
    listing = getattr(store, "list", None) or getattr(store, "listdir", None)
    if listing is None:
        raise ExecutionFailure("storage.list_protocol")
    result = []
    for item in listing(str(location)):
        context.checkpoint()
        if len(result) == limit:
            raise ExecutionFailure("storage.inventory_limit")
        if isinstance(item, Mapping):
            result.append(dict(item))
        else:
            candidate = str(item)
            path = candidate if Path(candidate).is_absolute() or str(location) in Path(candidate).parents else str(Path(str(location)) / candidate)
            metadata = {"path": path, "filename": Path(candidate).name}
            stat = getattr(store, "stat", None)
            if stat:
                state = stat(path)
                metadata.update(size=state.st_size, mtime=state.st_mtime_ns)
            result.append(metadata)
    return {"inventory": tuple(sorted(result, key=lambda item: item["path"]))}


def material_identify(inputs, settings, context):
    original, claim = inputs["material"], inputs.get("claim") or _get(settings, "claim")
    if isinstance(original, IdentifiedMaterial):
        if claim and original.claim.source_id != claim.source_id:
            raise ExecutionFailure("source.context_conflict")
        return {"material": original, "assessment": original.assessment}
    original = _material(original)
    if claim is None and inputs.get("request") is not None:
        request, evidence, asset = inputs["request"], inputs.get("evidence"), inputs.get("asset")
        if (not isinstance(request, RequestSpec) or not isinstance(evidence, FetchEvidence)
                or evidence.material_identity != original.identity or evidence.request_identity != _request_identity(request)):
            raise ExecutionFailure("source.acquisition_evidence_conflict")
        if isinstance(asset, PublicationAsset):
            if asset.locator != request.url or request.source_id not in {None, asset.source_id}:
                raise ExecutionFailure("source.selected_asset_conflict")
            claim = SourceClaim(asset.source_id, asset.issue_id, asset.asset_id, "recognized")
        elif request.source_id:
            claim = SourceClaim(request.source_id, str(request.metadata.get("issue_id", "")), str(request.metadata.get("asset_id", "main")), "recognized")
    if claim is None and isinstance(inputs.get("evidence"), ReadEvidence) and isinstance(inputs.get("asset"), PublicationAsset):
        evidence, asset = inputs["evidence"], inputs["asset"]
        if evidence.location != asset.locator or evidence.material_identity != original.identity or original.source_id not in {None, asset.source_id}:
            raise ExecutionFailure("source.selected_asset_conflict")
        claim = SourceClaim(asset.source_id, asset.issue_id, asset.asset_id, "recognized")
    if claim is None:
        raise ExecutionFailure("source.claim_required")
    if original.source_id is not None and original.source_id != claim.source_id:
        raise ExecutionFailure("source.context_conflict")
    assessment = Assessment(qualifications=frozenset({"source." + claim.attribution}))
    if inputs.get("evidence") is not None:
        from dataclasses import replace
        original = replace(original, lineage=(*original.lineage, inputs["evidence"]))
    return {"material": IdentifiedMaterial(original, claim, assessment), "assessment": assessment}


def material_select(inputs, settings, context):
    formats = frozenset(_option(context, settings, "formats", ()))
    names = frozenset(_option(context, settings, "names", ()))
    accepted, findings, observed, expected = [], [], [], []
    for index, value in enumerate(inputs["materials"]):
        material = _material(value)
        name = str(material.metadata.get("member", material.metadata.get("filename", index)))
        expected.append(name)
        suffix = name.rsplit(".", 1)[-1].lower()
        if names and name not in names or formats and suffix not in formats:
            findings.append("material.excluded:" + name)
        else:
            accepted.append(value); observed.append(name)
    return {"materials": tuple(accepted), "assessment": Assessment("complete" if len(accepted) == len(expected) else "partial",
        tuple(findings), tuple(expected), tuple(observed))}
