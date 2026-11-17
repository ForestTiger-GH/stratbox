"""Bounded JSON decoding and structural machine-input admission."""

from __future__ import annotations

import json
import re

from .contracts import WireRequestError

MAX_JSON = 16_384
JSON_STRUCTURE = re.compile(r'"(?:[^"\\]|\\.)*"|[{}\[\]]', re.DOTALL)


def _unique(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise WireRequestError("request.duplicate_field")
        fields[key] = value
    return fields


def _shape(value, allowed, required):
    if not isinstance(value, dict) or not set(required) <= set(value) <= set(allowed):
        raise WireRequestError("request.invalid_fields")


def decode_request(raw: bytes, catalog):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_JSON:
        raise WireRequestError("request.size_limit")
    try:
        encoded = raw.decode("utf-8")
        depth = 0
        for match in JSON_STRUCTURE.finditer(encoded):
            if match[0] in ("{", "["):
                depth += 1
                if depth > 2:
                    raise WireRequestError("request.depth_limit")
            elif match[0] in ("}", "]"):
                depth -= 1
        body = json.loads(encoded, object_pairs_hook=_unique)
    except WireRequestError:
        raise
    except (UnicodeError, ValueError, RecursionError):
        raise WireRequestError("request.invalid_json") from None
    fields = ("operation_id", "contract_version", "input")
    _shape(body, fields, fields)
    operation_id, version = body["operation_id"], body["contract_version"]
    if not isinstance(operation_id, str) or type(version) is not int:
        raise WireRequestError("request.invalid_type")
    _, _, allowed = catalog.resolve(operation_id, version)
    if allowed is None:
        raise WireRequestError("operation.wire_unavailable")
    data = body["input"]
    _shape(data, allowed.input_fields, allowed.required_fields)
    for name, value in data.items():
        rule = allowed.input_fields[name]
        if rule["type"] == "boolean":
            if type(value) is not bool:
                raise WireRequestError("request.invalid_type")
        elif not isinstance(value, str):
            raise WireRequestError("request.invalid_value")
        elif "pattern" in rule and not re.fullmatch(rule["pattern"], value, re.ASCII):
            raise WireRequestError("request.invalid_value")
    return allowed, data
