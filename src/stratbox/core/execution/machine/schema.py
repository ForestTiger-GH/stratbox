"""Construct JSON schemas from explicitly admitted machine codecs."""

from __future__ import annotations

from copy import deepcopy

from stratbox.core.execution.machine.contracts import WireRequestError

SCHEMA = "https://json-schema.org/draft/2020-12/schema"


def _obj(properties, required):
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(required)}


def wire_schemas(operation_id: str, *, catalog):
    definition = catalog.get(operation_id)
    codec = catalog.wire_contract(operation_id)
    if codec is None:
        raise WireRequestError("operation.wire_unavailable")
    identity = {"operation_id": {"const": operation_id}}
    request = {"$schema": SCHEMA, **_obj(
        {**identity, "input": _obj(codec.input_fields, codec.required_fields)},
        (*identity, "input"),
    )}
    string = {"type": "string"}
    nullable_string = {"type": ["string", "null"]}
    digest = _obj({"sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                   "size": {"type": "integer", "minimum": 0}}, ("sha256", "size"))
    fields = {
        **identity,
        "method_id": {"const": definition.method_id},
        "outcome": {"enum": ["succeeded", "partial", "failed", "cancelled", "unknown"]},
        "value": {"anyOf": [_obj(codec.output_fields, codec.output_fields), {"type": "null"}]},
        "computation": {"anyOf": [_obj({
            "id": digest, "output": digest,
            "method_fingerprint": {"anyOf": [digest, {"type": "null"}]},
            "argument_coverage": {"enum": ["declared", "whole_request", "unqualified"]},
            "qualifications": {"type": "array", "items": {"type": "string"}},
        }, ("id", "output", "method_fingerprint", "argument_coverage", "qualifications")), {"type": "null"}]},
        "diagnostics": {"type": "array", "items": _obj(
            {"code": string, "stage": nullable_string, "component": nullable_string,
             "reason_class": nullable_string, "retry_disposition": string,
             "evidence_ref": nullable_string, "reconciliation_owner": nullable_string},
            ("code", "stage", "component", "reason_class", "retry_disposition",
             "evidence_ref", "reconciliation_owner"),
        )},
    }
    return deepcopy((request, {"$schema": SCHEMA, **_obj(fields, fields)}))
