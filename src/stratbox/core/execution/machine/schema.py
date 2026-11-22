"""Construct JSON schemas from explicitly admitted machine codecs."""

from __future__ import annotations

from copy import deepcopy

from stratbox.core.execution.machine.contracts import WireRequestError

SCHEMA = "https://json-schema.org/draft/2020-12/schema"


def _obj(properties, required):
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(required)}


def wire_schemas(operation_id: str, contract_version: int, *, catalog):
    definition = catalog.get(operation_id, contract_version)
    codec = catalog.wire_contract(operation_id, contract_version)
    if codec is None:
        raise WireRequestError("operation.wire_unavailable")
    identity = {"operation_id": {"const": operation_id},
                "contract_version": {"const": contract_version}}
    request = {"$schema": SCHEMA, **_obj(
        {**identity, "input": _obj(codec.input_fields, codec.required_fields)},
        (*identity, "input"),
    )}
    string = {"type": "string"}
    nullable_string = {"type": ["string", "null"]}
    fields = {
        **identity,
        "method_version": {"const": definition.method_version},
        "outcome": {"enum": ["succeeded", "partial", "failed", "cancelled", "unknown"]},
        "value": {"anyOf": [_obj(codec.output_fields, codec.output_fields), {"type": "null"}]},
        "diagnostics": {"type": "array", "items": _obj(
            {"code": string, "stage": nullable_string, "component": nullable_string,
             "retry_disposition": string},
            ("code", "stage", "component", "retry_disposition"),
        )},
    }
    return deepcopy((request, {"$schema": SCHEMA, **_obj(fields, fields)}))
