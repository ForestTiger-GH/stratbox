"""Shared immutable publication-family selection contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndustrySelection:
    """Published industry codes to materialize; None requests all published codes."""
    industry_codes: tuple[str, ...] | None = None
