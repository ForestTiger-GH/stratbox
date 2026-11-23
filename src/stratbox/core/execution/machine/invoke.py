"""Invoke only expressly enabled read-only operations through a supplied catalog."""

from __future__ import annotations

import json

from stratbox.core.execution import ExecutionContext, OperationResult
from stratbox.core.execution.machine.codec import decode_request
from stratbox.core.execution.machine.contracts import MaterialResolver, WireRequestError
from stratbox.core.execution.machine.projections import computation_projection, diagnostic_projection


def invoke_read_only(
    raw: bytes, *, catalog, materials: MaterialResolver,
    context: ExecutionContext | None = None,
) -> bytes:
    codec, data = decode_request(raw, catalog)
    try:
        result = codec.resolve_and_invoke(data, materials, context)
        if (not isinstance(result, OperationResult)
                or result.definition != catalog.get(codec.operation_id)):
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
        "method_id": result.definition.method_id,
        "outcome": result.outcome,
        "value": value,
        "computation": computation_projection(result),
        "diagnostics": [diagnostic_projection(item) for item in result.diagnostics[:128]],
    }, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
