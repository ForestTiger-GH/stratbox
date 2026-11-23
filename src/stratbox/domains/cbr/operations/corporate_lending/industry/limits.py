"""Shared resource declarations for independent industry-series operations."""

from stratbox.core.limits import ExecutionBudget

TABLE_LIMITS = ExecutionBudget(cells=50_000_000, output_bytes=128 * 1024 * 1024)
