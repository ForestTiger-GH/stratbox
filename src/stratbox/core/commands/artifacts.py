"""Retain exact encoded bytes and reconcile uncertain immutable writes."""
from __future__ import annotations
from pathlib import Path
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import Assessment, ByteIdentity, ImmutableMaterialRef, fingerprint
from ._settings import _option
from ._storage import _provider_scope, _read


def artifact_commit(inputs, settings, context):
    value = inputs["material"]
    data = value if isinstance(value, bytes) else value.data
    identity, store = ByteIdentity.of(data), context.provider("filestore")
    destination = inputs.get("destination") or _option(context, settings, "destination")
    if destination is None: raise ExecutionFailure("storage.destination_required")
    if getattr(context, "budget", None):
        context.budget.account_output(fingerprint(("artifact", str(destination))), identity)
    # Content members always receive digest addressing. A mutable publication pointer is separate.
    path = str(Path(str(destination)) / identity.sha256)
    scope = _provider_scope(store, path)
    accepted = context.accepted_input("material")
    effect_id = fingerprint(("storage.write", scope, path, identity))
    reference = ImmutableMaterialRef(path, identity, str(getattr(store, "provider_id", "filestore")),
        accepted["basis"] if accepted else (), accepted_value_id=accepted["id"] if accepted else None,
        effect_id=effect_id, provider_scope=scope, source_uses=accepted["source_uses"] if accepted else ())
    def action():
        if getattr(store, "immutable_content", False) and hasattr(store, "create_immutable"):
            store.create_immutable(path, data)
        else:
            raise ExecutionFailure("storage.immutable_provider_required")
        actual = _read(store, path, identity.size)
        if ByteIdentity.of(actual) != identity: raise ExecutionFailure("storage.identity_mismatch")
        return reference
    receipt = context.effect("storage.write", effect_id, action, resource=path, intent=reference)
    if receipt.status != "confirmed": raise ExecutionFailure("storage.unknown", outcome="unknown")
    return {"reference": receipt.value, "receipt": receipt}


def artifact_reconcile(inputs, settings, context):
    receipt = inputs["effect"]
    provider = context.provider("filestore")
    def lookup(effect_id):
        known = context.service.lookup_effect(effect_id)
        expected = known.intent if known is not None else None
        if not isinstance(expected, ImmutableMaterialRef) or not getattr(provider, "immutable_content", False): return None
        if expected.provider_scope != _provider_scope(provider, expected.location): return None
        try:
            actual = ByteIdentity.of(_read(provider, expected.location, expected.identity.size))
        except (OSError, ExecutionFailure):
            return None
        return expected if actual == expected.identity else None
    recovered = context.service.reconcile_effect(receipt.effect_id, lookup, context=context)
    return {"assessment": Assessment("complete" if recovered.status == "confirmed" else "indeterminate",
        qualifications=frozenset({"exact_immutable_readback"}) if recovered.status == "confirmed" else frozenset())}
