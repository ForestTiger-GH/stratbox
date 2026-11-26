"""Bounded verified readers shared by physical commands and persistence."""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO

from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.materials import StagedMaterialRef
from stratbox.shared.data.values import IdentifiedMaterial, Material, EncodedProduct, ImmutableMaterialRef


def carrier(value):
    return value.material if isinstance(value, IdentifiedMaterial) else value


def scan_identity(stream, *, limit=None, checkpoint=lambda: None, budget=None,
                  resource=None, chunk_size=1024 * 1024):
    digest, size = sha256(), 0
    while True:
        checkpoint()
        chunk = stream.read(chunk_size if limit is None else min(chunk_size, max(1, limit - size + 1)))
        if not chunk:
            break
        size += len(chunk)
        if limit is not None and size > limit:
            raise ValueError("storage.read_limit")
        if budget is not None and resource:
            budget.charge(resource, len(chunk))
        digest.update(chunk)
    return ByteIdentity(digest.hexdigest(), size)


def copy_stream(source, destination, *, limit=None, expected=None,
                checkpoint=lambda: None, budget=None, resource=None):
    digest, size = sha256(), 0
    while True:
        checkpoint()
        chunk = source.read(1024 * 1024 if limit is None else min(1024 * 1024, max(1, limit - size + 1)))
        if not chunk:
            break
        size += len(chunk)
        if limit is not None and size > limit:
            raise ValueError("storage.read_limit")
        if budget is not None and resource:
            budget.charge(resource, len(chunk))
        written = destination.write(chunk)
        if written != len(chunk):
            raise ValueError("storage.short_write")
        digest.update(chunk)
    identity = ByteIdentity(digest.hexdigest(), size)
    if expected is not None and expected != identity:
        raise ValueError("storage.identity_mismatch")
    return identity


@contextmanager
def open_provider(store, location):
    opener = getattr(store, "open", None)
    if callable(opener):
        with opener(str(location), "rb") as stream:
            yield stream
    elif callable(getattr(store, "open_read", None)):
        with store.open_read(str(location)) as stream:
            yield stream
    else:
        raise ValueError("storage.streaming_read_required")


@contextmanager
def open_material(value, context):
    value = carrier(value)
    if isinstance(value, (Material, EncodedProduct)):
        with BytesIO(value.data) as stream:
            yield stream
    elif isinstance(value, bytes):
        with BytesIO(value) as stream:
            yield stream
    elif isinstance(value, StagedMaterialRef):
        with context.service.staging.open(value) as stream:
            yield stream
    elif isinstance(value, ImmutableMaterialRef):
        from stratbox.core.commands._storage import _provider_scope, _same_physical_reference
        store = context.provider("filestore")
        if value.guarantee != "immutable_content" or not getattr(store, "immutable_content", False):
            raise ValueError("storage.immutable_provider_required")
        if not value.provider_scope or value.provider_scope != _provider_scope(store, value.location):
            raise ValueError("storage.provider_scope_conflict")
        known = context.service.lookup_effect(value.effect_id) if value.effect_id else None
        if known is None or known.status != "confirmed" or not _same_physical_reference(known.value, value):
            raise ValueError("storage.confirmed_retention_required")
        with open_provider(store, value.location) as stream:
            if not stream.seekable():
                raise ValueError("storage.seekable_reader_required")
            actual = scan_identity(stream, limit=value.identity.size, checkpoint=context.checkpoint)
            if actual != value.identity:
                raise ValueError("storage.identity_mismatch")
            stream.seek(0)
            yield stream
    else:
        raise TypeError("material.readable_carrier_required")
