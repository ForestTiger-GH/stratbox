"""Invoke only expressly enabled read-only operations through a supplied catalog."""

from __future__ import annotations

import json

from stratbox.core.execution import ExecutionContext, OperationResult
from stratbox.core.execution.machine.codec import decode_request
from stratbox.core.execution.machine.contracts import MaterialResolver, WireRequestError


def invoke_read_only(
    raw: bytes, *, catalog, materials: MaterialResolver,
    context: ExecutionContext | None = None,
) -> bytes:
    codec, data = decode_request(raw, catalog)
    try:
        result = codec.resolve_and_invoke(data, materials, context)
        if not isinstance(result, OperationResult) or (
            result.operation_id != codec.operation_id
            or result.definition.contract_version != codec.contract_version
        ):
            raise WireRequestError("operation.result_mismatch")
        value = codec.project(result)
        if value is not None and set(value) != set(codec.output_fields):
            raise WireRequestError("operation.projection_mismatch")
    except WireRequestError:
        raise
    except Exception:
        raise WireRequestError("material.unavailable") from None
    return json.dumps({
        "operation_id": codec.operation_id,
        "contract_version": codec.contract_version,
        "method_version": result.definition.method_version,
        "outcome": result.outcome,
        "value": value,
        "diagnostics": [
            {"code": item.code, "stage": item.stage, "component": item.component,
             "retry_disposition": item.retry_disposition}
            for item in result.diagnostics
        ],
    }, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
