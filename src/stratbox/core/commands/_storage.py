"""Provider scope and retained-content checks shared by persistence actions."""
from dataclasses import replace
from stratbox.shared.data.values import ImmutableMaterialRef, fingerprint
from stratbox.shared.identity import ByteIdentity
from stratbox.core.execution.service import ExecutionFailure
from stratbox.core.storage.readable import open_provider, scan_identity


def _read(store, location, limit):
    if type(limit) is not int or limit < 0:
        raise ExecutionFailure("storage.read_limit_invalid")
    chunks, size = [], 0
    with open_provider(store, location) as stream:
        while True:
            chunk = stream.read(min(65536, limit - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                raise ExecutionFailure("storage.read_limit")
            chunks.append(chunk)
    return b"".join(chunks)


def _read_identity(store, location, identity, *, checkpoint=lambda: None):
    with open_provider(store, location) as stream:
        return scan_identity(stream, limit=identity.size, checkpoint=checkpoint)


def _same_physical_reference(left, right):
    if not isinstance(left, ImmutableMaterialRef) or not isinstance(right, ImmutableMaterialRef):
        return False
    return all(getattr(left, name) == getattr(right, name) for name in (
        "location", "identity", "provider_id", "guarantee", "effect_id", "provider_scope", "accepted_value_id"))


def _compact_reference(reference):
    return replace(reference, lineage=(), source_uses=(), metadata={})


def _confirmed_reference(reference, context):
    if not isinstance(reference, ImmutableMaterialRef) or not reference.effect_id:
        raise ExecutionFailure("storage.confirmed_retention_required")
    known = context.service.lookup_effect(reference.effect_id)
    if known is None or known.status != "confirmed" or not _same_physical_reference(reference, known.value):
        raise ExecutionFailure("storage.confirmed_retention_required")
    store = context.provider("filestore")
    if not getattr(store, "immutable_content", False) or reference.provider_scope != _provider_scope(store, reference.location):
        raise ExecutionFailure("storage.immutable_provider_required")
    if _read_identity(store, reference.location, reference.identity, checkpoint=context.checkpoint) != reference.identity:
        raise ExecutionFailure("storage.identity_mismatch")
    return known.value


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
    if receipt is None or receipt.status != "confirmed" or not _same_physical_reference(receipt.value, reference):
        raise ExecutionFailure("release.confirmed_retention_required")
    if (reference.lineage, reference.source_uses) != (receipt.value.lineage, receipt.value.source_uses):
        raise ExecutionFailure("release.logical_lineage_conflict")
    if reference.assessment != receipt.value.assessment:
        raise ExecutionFailure("release.assessment_conflict")
    store = context.provider("filestore")
    if not getattr(store, "immutable_content", False) or reference.provider_scope != _provider_scope(store, reference.location):
        raise ExecutionFailure("release.immutable_provider_required")
    if _read_identity(store, reference.location, reference.identity, checkpoint=context.checkpoint) != reference.identity:
        raise ExecutionFailure("release.member_identity_mismatch")
