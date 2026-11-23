"""Typed values owned by this processing boundary."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, TYPE_CHECKING
from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.data.source_context import SourceUse
if TYPE_CHECKING:
    from pandas import DataFrame

@dataclass(frozen=True, slots=True)
class FormViews:
    form: str
    profile: str
    sheets: Mapping[str, DataFrame]
    lineage: tuple[UsedInputReceipt, ...]
    evidence: ComputationReceipt | None = None
    source_uses: tuple[SourceUse, ...] = ()
