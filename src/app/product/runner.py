"""Compatibility facade for product execution."""

from app.product.execution.runner import run_product_operation, run_product_operation_by_id

__all__ = ['run_product_operation', 'run_product_operation_by_id']
