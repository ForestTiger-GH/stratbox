"""
Служебные типы для единообразной сигнатуры модулей форм Банка России.
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig


class FormModule(Protocol):
    """Описывает минимальный контракт модуля формы, используемый общим API."""

    FORM: str

    def build_url(self, d: pd.Timestamp) -> str: ...

    def run(
        self,
        *,
        dates: list[pd.Timestamp],
        banks_df: pd.DataFrame,
        model_df: pd.DataFrame,
        cfg: RunnerConfig | None = None,
        show_progress: bool = True,
        **kwargs,
    ) -> tuple[pd.DataFrame, dict[str, int] | None]: ...
