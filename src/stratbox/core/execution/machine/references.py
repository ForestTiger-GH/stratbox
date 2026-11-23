"""Portable invocation using host-owned typed references and explicit effect grants.

The host constructs or restores typed requests, owns reference lifetimes and
provides runtime bindings. This boundary does not evaluate Python, deserialize
arbitrary classes, resolve paths or infer provider authority from a reference.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import json
import re
from typing import Protocol
from uuid import uuid4

from stratbox.core.execution.contracts import OperationResult
from stratbox.core.execution.machine.contracts import WireRequestError
from stratbox.shared.identity import ByteIdentity

_REF = re.compile(r"[A-Za-z0-9_-]{1,256}\Z")


class TypedValueResolver(Protocol):
    def resolve(self, reference: str, expected_type: type) -> object: ...
    def retain(self, value: object) -> str: ...


class MemoryValueResolver:
    """An explicit local host vault; handles are valid only in this instance."""
    def __init__(self, *, max_values=1000):
        if type(max_values) is not int or not 1 <= max_values <= 100_000:
            raise ValueError("reference.capacity_invalid")
        self.max_values = max_values
        self._values = {}

    def retain(self, value):
        if len(self._values) >= self.max_values:
            raise WireRequestError("reference.capacity_exhausted")
        key = "value_" + uuid4().hex
        self._values[key] = value
        return key

    def resolve(self, reference, expected_type):
        if type(reference) is not str or not _REF.fullmatch(reference):
            raise WireRequestError("reference.invalid")
        value = self._values.get(reference)
        if not isinstance(value, expected_type):
            raise WireRequestError("reference.type_or_scope_mismatch")
        return value

    def discard(self, reference):
        self._values.pop(reference, None)

    def clear(self):
        self._values.clear()


def _safe(value, *, remaining, depth=0, max_rows=20):
    if depth > 5 or remaining[0] <= 0:
        return {"truncated": True}
    remaining[0] -= 1
    if value is None or type(value) in {int, bool}:
        return value
    if isinstance(value, Enum):
        return value.value
    if type(value) is str:
        return value if len(value) <= 1000 else value[:1000] + "…"
    if isinstance(value, Decimal):
        return {"type": "decimal", "value": str(value)}
    if type(value) in {date, datetime}:
        return value.isoformat()
    if isinstance(value, bytes):
        identity = ByteIdentity.of(value)
        return {"sha256": identity.sha256, "size": identity.size, "bytes_omitted": True}
    if isinstance(value, (tuple, list)):
        return {"items": [_safe(v, remaining=remaining, depth=depth+1, max_rows=max_rows)
                          for v in value[:max_rows]], "count": len(value), "truncated": len(value) > max_rows}
    if isinstance(value, dict):
        selected = list(value.items())[:max_rows]
        return {str(k): _safe(v, remaining=remaining, depth=depth+1, max_rows=max_rows) for k, v in selected}
    if is_dataclass(value):
        return {f.name: _safe(getattr(value, f.name), remaining=remaining, depth=depth+1, max_rows=max_rows)
                for f in fields(value) if f.repr and not f.name.startswith("_")}
    return {"type": type(value).__name__, "preview_unavailable": True}


def preview_value(value, *, max_rows=20, max_bytes=32_768):
    if (type(max_rows) is not int or not 1 <= max_rows <= 100
            or type(max_bytes) is not int or not 256 <= max_bytes <= 131_072):
        raise WireRequestError("reference.preview_limit_invalid")
    projected = _safe(value, remaining=[1000], max_rows=max_rows)
    raw = json.dumps(projected, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode()
    if len(raw) > max_bytes:
        return {"type": type(value).__name__, "preview_omitted": "byte_limit", "bounded": True}
    return projected


def reference_schemas(operation_id, contract_version, *, catalog):
    op = catalog.get(operation_id, contract_version)
    fields_in = {"operation_id": {"const": op.operation_id}, "contract_version": {"const": op.contract_version},
        "request_ref": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,256}$"},
        "preview_rows": {"type": "integer", "minimum": 1, "maximum": 100},
        "preview_bytes": {"type": "integer", "minimum": 256, "maximum": 131072}}
    request = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
        "additionalProperties": False, "properties": fields_in,
        "required": ["operation_id", "contract_version", "request_ref"],
        "x-request-type": op.request_type.__module__+"."+op.request_type.__qualname__,
        "x-effects-requiring-host-grant": sorted(op.possible_effects)}
    response = {"type": "object", "properties": {
        "operation_id": {"const": op.operation_id}, "contract_version": {"const": op.contract_version},
        "method_version": {"const": op.method_version}, "outcome": {"type": "string"},
        "result_ref": {"type": "string"}, "value_ref": {"type": ["string", "null"]},
        "preview": {}, "diagnostics": {"type": "array"}, "effects": {"type": "array"}},
        "required": ["operation_id", "contract_version", "method_version", "outcome", "result_ref", "value_ref",
                     "preview", "diagnostics", "effects"], "additionalProperties": False}
    return request, response


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise WireRequestError("reference.duplicate_field")
        result[key] = value
    return result


def invoke_reference(raw: bytes, *, catalog, values: TypedValueResolver, context=None,
                     authorized_effects=frozenset()) -> bytes:
    if type(raw) is not bytes or len(raw) > 16_384:
        raise WireRequestError("reference.request_size_invalid")
    try:
        request = json.loads(raw, object_pairs_hook=_object)
    except (ValueError, UnicodeError, RecursionError):
        raise WireRequestError("reference.invalid_json") from None
    required = {"operation_id", "contract_version", "request_ref"}
    if not isinstance(request, dict) or not required <= set(request) or set(request) - required - {"preview_rows", "preview_bytes"}:
        raise WireRequestError("reference.request_shape_invalid")
    if type(request["operation_id"]) is not str or type(request["contract_version"]) is not int:
        raise WireRequestError("reference.operation_invalid")
    if type(request["request_ref"]) is not str or not _REF.fullmatch(request["request_ref"]):
        raise WireRequestError("reference.invalid")
    max_rows, max_bytes = request.get("preview_rows", 20), request.get("preview_bytes", 32768)
    preview_value(None, max_rows=max_rows, max_bytes=max_bytes)
    definition = catalog.get(request["operation_id"], request["contract_version"])
    if not isinstance(authorized_effects, frozenset) or not definition.possible_effects <= authorized_effects:
        raise WireRequestError("reference.effects_not_granted")
    typed = values.resolve(request["request_ref"], definition.request_type)
    if not isinstance(typed, definition.request_type):
        raise WireRequestError("reference.request_type_mismatch")
    _, handler, _ = catalog.resolve(definition.operation_id, definition.contract_version)
    result = handler(typed, context=context)
    if not isinstance(result, OperationResult) or result.definition != definition:
        raise WireRequestError("reference.result_mismatch")
    result_ref = values.retain(result)
    value_ref = values.retain(result.value) if result.value is not None else None
    response = {"operation_id": definition.operation_id, "contract_version": definition.contract_version,
        "method_version": definition.method_version, "outcome": result.outcome,
        "result_ref": result_ref, "value_ref": value_ref,
        "preview": preview_value(result.value, max_rows=max_rows, max_bytes=max_bytes),
        "diagnostics": [{"code": d.code, "stage": d.stage, "retry_disposition": d.retry_disposition} for d in result.diagnostics[:128]],
        "effects": [{"kind": e.kind, "state": e.state, "effect_id": e.effect_id} for e in result.effects[:128]]}
    return json.dumps(response, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("utf-8")
