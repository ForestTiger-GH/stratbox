"""Composite requests crossing publisher materials and extracted tables."""
from __future__ import annotations
from dataclasses import dataclass
from ..publications.contracts import Asset, AcquiredAsset
from ..tables.contracts import TableExtract


@dataclass(frozen=True, slots=True)
class CaptureRequest:
    asset: Asset
    max_bytes: int = 64 * 1024 * 1024
    max_cells: int = 150_000
    member: str | None = None
    selected_sheets: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CaptureResult:
    acquired: AcquiredAsset
    extracted: TableExtract
