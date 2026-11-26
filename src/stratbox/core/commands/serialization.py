"""Bounded portable encoding and restoration of admitted scientific values."""
from __future__ import annotations
import json
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import EncodedProduct, canonical_tree, fingerprint, restore_tree, validate_portable_tree
from ._settings import _option


def value_encode(inputs, settings, context):
    return {"representation": encode_value(inputs["value"],context=context,
        max_bytes=_option(context,settings,"max_bytes",256*1024*1024))}


def encode_value(value, *, context, admitted_types=None, max_bytes=256 * 1024 * 1024):
    """Bounded shared serializer with an explicit trusted scientific vocabulary."""
    limit = max_bytes
    budget = getattr(context, "budget", None)
    if budget and budget.remaining("output_bytes") is not None: limit = min(limit, budget.remaining("output_bytes"))
    data = bytearray()
    for chunk in json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(",", ":")).iterencode(validate_portable_tree(canonical_tree(value),admitted_types=admitted_types)):
        context.checkpoint()
        raw = chunk.encode()
        if len(data) + len(raw) > limit:
            if budget and budget.remaining("output_bytes") is not None: budget.check("output_bytes", len(data) + len(raw))
            raise ExecutionFailure("codec.output_limit")
        data.extend(raw)
    data = bytes(data)
    identity = fingerprint(value)
    return EncodedProduct(data, "application/json", (identity,),
        descriptor={"encoding": "canonical_tree", "value_identity": identity},
        source_uses=getattr(value, "source_uses", ()))


def value_decode(inputs, settings, context):
    encoded = inputs["representation"]
    data = encoded if isinstance(encoded, bytes) else encoded.data
    value = restore_tree(json.loads(data))
    expected = getattr(encoded, "descriptor", {}).get("value_identity")
    if expected is not None and fingerprint(value) != expected: raise ExecutionFailure("codec.value_identity_mismatch")
    return {"value": value}
