"""Verify retained member lineage and publish a conditional release manifest."""
from __future__ import annotations
from typing import Mapping
import json
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import ImmutableMaterialRef, canonical_tree, fingerprint
from ._settings import _get, _option
from ._storage import _provider_scope, _read_identity, _verify_member
from stratbox.shared.identity import ByteIdentity


def release_assemble(inputs, settings, context):
    members = inputs["members"]
    if not members: raise ExecutionFailure("release.empty_members")
    basis = _option(context, settings, "basis")
    records = []
    for member in members:
        reference = _get(member, "reference", member if isinstance(member, ImmutableMaterialRef) else None)
        derivation = _get(member, "derivation", getattr(reference, "lineage", ()))
        _verify_member(reference, context)
        if tuple(derivation) != reference.lineage:
            raise ExecutionFailure("release.caller_derivation_conflict")
        requested = set(basis.values()) if isinstance(basis, Mapping) else set(basis) if isinstance(basis, (tuple, list, set, frozenset)) else {basis} if basis is not None else set()
        if requested and not {fingerprint(item) for item in requested} <= {fingerprint(item) for item in reference.lineage}:
            raise ExecutionFailure("release.member_basis_mismatch")
        records.append({"reference": reference, "derivation": derivation})
    return {"manifest": {"members": tuple(records), "basis": basis, "identity": fingerprint(records)}}


def release_publish(inputs, settings, context):
    store, manifest = context.provider("filestore"), inputs["manifest"]
    publish = getattr(store, "compare_and_set", None)
    if publish is None: raise ExecutionFailure("publication.conditional_provider_required")
    destination = _option(context, settings, "destination")
    if not isinstance(destination, str) or not destination:
        raise ExecutionFailure("publication.destination_required")
    for member in manifest["members"]:
        _verify_member(member["reference"], context)
    data = json.dumps(canonical_tree(manifest), sort_keys=True, separators=(",", ":")).encode()
    expected = inputs.get("expected_token")
    identity = ByteIdentity.of(data)
    intent = {'destination': destination, 'expected_token': expected, 'identity': identity.sha256,
        'provider_id': str(getattr(store, 'provider_id', type(store).__qualname__)),
        'provider_scope': _provider_scope(store, destination)}
    occurrence = _option(context, settings, 'publication_id', None)
    if occurrence is not None and (not isinstance(occurrence, str) or not occurrence or len(occurrence) > 1024):
        raise ExecutionFailure('publication.occurrence_identity_invalid')
    receipt = context.effect("publication.write", fingerprint(('publication.write', intent, occurrence)),
        lambda: publish(destination, expected, data), resource=str(destination), intent=intent)
    if receipt.status != "confirmed": raise ExecutionFailure("publication.unknown", outcome="unknown")
    if _read_identity(store, destination, identity, checkpoint=context.checkpoint) != identity:
        raise ExecutionFailure('publication.current_postcondition_changed')
    return {"receipt": receipt}
