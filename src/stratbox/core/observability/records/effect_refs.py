"""Portable identifiers for invocation-local qualified effect observations.

A qualified reference separates kinds sharing a raw provider-supplied ID.
The hash is an identity label, not proof of authority or inter-attempt
physical equivalence. The journal record retains its invocation scope.
"""
from __future__ import annotations

from hashlib import sha256

from stratbox.core.execution.contracts import EffectKey
from stratbox.core.observability.records.contracts import ObjectRef
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes


def effect_ref_id(key: EffectKey) -> str:
    if not isinstance(key, EffectKey):
        raise TypeError("Qualified EffectKey required")
    payload = canonical_manifest_bytes({
        "kind": key.kind, "effect_id": key.effect_id,
    })
    return sha256(b"stratbox.effect-ref.v1:\0" + payload).hexdigest()


def effect_reference(
    key: EffectKey, *, identity: ByteIdentity | None = None,
) -> ObjectRef:
    return ObjectRef("effect", effect_ref_id(key), "receipt", identity=identity)
