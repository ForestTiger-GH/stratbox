"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.data.datasets import ComputationReceipt

from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySpec

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True)
class IndustryApkCalculationResult:
    """Результат добавления расчетной отрасли ``АПК`` в поток."""

    industry: IndustrySpec
    source_industry_codes: tuple[str, ...]
    lpk_formula_ru: str
    apk_formula_ru: str
    df_apk: pd.DataFrame
    df_stream: pd.DataFrame
    source_rows_used: int
    groups_calculated: int
    rows_added: int
    evidence: ComputationReceipt | None = None

    @property
    def ok(self) -> bool:
        return self.rows_added > 0 and self.rows_added == len(self.df_apk)
