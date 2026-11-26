"""Small adapters shared by bounded physical encoders."""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO

from stratbox.shared.data.values import ConvertedMaterial, IdentifiedMaterial, Material, EncodedProduct
from stratbox.shared.identity import ByteIdentity


def physical_material(value):
    while isinstance(value, (IdentifiedMaterial, ConvertedMaterial)):
        value = value.material
    if isinstance(value, bytes):
        return Material(value)
    if not hasattr(value, "identity"):
        raise ValueError("material.readable_required")
    return value


def material_properties(value):
    material = physical_material(value)
    properties = {"source_id": getattr(value, "source_id", getattr(material, "source_id", None)),
        "metadata": dict(getattr(material, "metadata", {})),
        "lineage": tuple(getattr(material, "lineage", ())), "source_uses": ()}
    uses = []
    for owner in (material, value):
        for use in getattr(owner, "source_uses", ()):
            if use not in uses:
                uses.append(use)
    properties["source_uses"] = tuple(uses)
    if isinstance(value, IdentifiedMaterial):
        properties["metadata"].setdefault("issue_id", value.claim.issue_id)
        properties["metadata"].setdefault("asset_id", value.claim.asset_id)
    return properties


@contextmanager
def open_material(value, context):
    opener = getattr(context, "open_material", None)
    if callable(opener):
        with opener(value) as stream:
            yield stream
    else:
        material = physical_material(value)
        if not isinstance(material, (Material, EncodedProduct)):
            raise ValueError("material.reader_context_required")
        with BytesIO(material.data) as stream:
            yield stream


def bounded_material_bytes(value, context, *, max_bytes):
    """Explicit bounded materialization for formats requiring a complete buffer."""
    material = physical_material(value)
    if type(max_bytes) is not int or max_bytes < 1 or material.identity.size > max_bytes:
        raise ValueError("material.materialization_limit")
    budget = getattr(context, "budget", None)
    if isinstance(material, (Material, EncodedProduct)):
        if budget is not None:
            budget.charge("decoded_bytes", material.identity.size)
        return material.data
    chunks, length, digest = [], 0, sha256()
    with open_material(value, context) as stream:
        while True:
            context.checkpoint()
            chunk = stream.read(min(65536, max_bytes - length + 1))
            if not chunk:
                break
            length += len(chunk)
            if length > max_bytes:
                raise ValueError("material.materialization_limit")
            if budget is not None:
                budget.charge("decoded_bytes", len(chunk))
            digest.update(chunk)
            chunks.append(chunk)
    if ByteIdentity(digest.hexdigest(), length) != material.identity:
        raise ValueError("material.identity_mismatch")
    return b"".join(chunks)


class LimitedStream:
    """Seekable sink limit, applied before each allocation or physical write."""

    def __init__(self, stream, limit, budget=None):
        if type(limit) is not int or limit < 0:
            raise ValueError("material.output_limit_invalid")
        self.stream, self.limit, self.budget = stream, limit, budget

    def write(self, data):
        end = self.stream.tell() + len(data)
        if end > self.limit:
            raise ValueError("material.output_limit")
        if self.budget is not None:
            self.budget.check("output_bytes", end)
        written = self.stream.write(data)
        if written != len(data):
            raise ValueError("material.short_write")
        return written

    def __getattr__(self, name):
        return getattr(self.stream, name)


class _RepresentationWriter:
    def __init__(self, stream, properties, *, staged=None, limit, budget):
        self.stream = LimitedStream(stream, limit, budget)
        self.properties, self.staged, self.sealed = properties, staged, None

    def seal(self, **properties):
        if self.sealed is not None:
            raise ValueError("material.already_sealed")
        self.properties.update(properties)
        if self.staged is not None:
            self.sealed = self.staged.seal(**properties)
        else:
            self.sealed = Material(self.stream.getvalue(), **self.properties)
        return self.sealed


@contextmanager
def representation_writer(context, *, placement, max_bytes, **properties):
    budget = getattr(context, "budget", None)
    if placement == "staged":
        stage = getattr(context, "stage", None)
        if not callable(stage):
            raise ValueError("material.staging_context_required")
        with stage(**properties) as builder:
            yield _RepresentationWriter(builder.stream, properties, staged=builder,
                                        limit=max_bytes, budget=budget)
    elif placement == "buffered":
        with BytesIO() as stream:
            yield _RepresentationWriter(stream, properties, limit=max_bytes, budget=budget)
    else:
        raise ValueError("material.placement_invalid")
