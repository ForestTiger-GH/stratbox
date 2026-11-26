"""Provider scope and retained-content checks shared by persistence actions."""
from stratbox.shared.data.values import ImmutableMaterialRef, fingerprint
from stratbox.shared.identity import ByteIdentity
from stratbox.core.execution.service import ExecutionFailure


def _read(store, location, limit):
    if hasattr(store, "open"):
        with store.open(str(location), "rb") as stream:
            data = stream.read(limit + 1)
    elif hasattr(store, "read_bytes"):
        data = store.read_bytes(str(location))
    else:
        raise ExecutionFailure("storage.read_protocol")
    if len(data) > limit:
        raise ExecutionFailure("storage.read_limit")
    return data


def _provider_scope(provider, destination):
    scope = getattr(provider, "storage_scope", None)
    location = scope(str(destination)) if callable(scope) else getattr(provider, "scope_id", None)
    if location is None:
        root = getattr(provider, "directory", getattr(provider, "_root", None))
        location = str(root) if root is not None else str(getattr(provider, "provider_id", type(provider).__module__ + ":" + type(provider).__qualname__))
    return fingerprint((str(getattr(provider, "provider_id", type(provider).__qualname__)), str(location)))


def _verify_member(reference, context):
    if not isinstance(reference, ImmutableMaterialRef) or not reference.accepted_value_id or not reference.effect_id:
        raise ExecutionFailure("release.accepted_lineage_required")
    receipt = context.service.lookup_effect(reference.effect_id)
    if receipt is None or receipt.status != "confirmed" or receipt.value != reference:
        raise ExecutionFailure("release.confirmed_retention_required")
    store = context.provider("filestore")
    if not getattr(store, "immutable_content", False) or reference.provider_scope != _provider_scope(store, reference.location):
        raise ExecutionFailure("release.immutable_provider_required")
    if ByteIdentity.of(_read(store, reference.location, reference.identity.size)) != reference.identity:
        raise ExecutionFailure("release.member_identity_mismatch")
