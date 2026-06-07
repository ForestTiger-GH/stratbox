from __future__ import annotations

from .artifacts import build_primary_output_actions, detect_operation_log
from .requests import ProductResult


def finalize_product_result(result: ProductResult) -> ProductResult:
    outputs = build_primary_output_actions(result.outputs)
    details = dict(result.details)
    details.setdefault('operation_log', detect_operation_log(outputs))
    return ProductResult(ok=result.ok, message=result.message, outputs=outputs, details=details)
