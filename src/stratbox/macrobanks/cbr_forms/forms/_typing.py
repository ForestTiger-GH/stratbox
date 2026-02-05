"""
forms/_typing.py

Служебные типы для единообразной сигнатуры форм.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import pandas as pd

from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig
from stratbox.macrobanks.cbr_forms.common.dbf_picker import LayoutCandidates


class FormModule(Protocol):
    FORM: str

    def build_url(self, d: pd.Timestamp) -> str: ...

    def run(
        self,
        *,
        dates: list[pd.Timestamp],
        banks_df: pd.DataFrame,
        formulas_df: pd.DataFrame,
        candidates: LayoutCandidates | None = None,
        prefer_stem_contains: str | None = None,
        cfg: RunnerConfig | None = None,
        **kwargs,
    ) -> tuple[pd.DataFrame, dict[str, int] | None]: ...


ValueResolver = Callable[[pd.DataFrame, str, str, dict], str]
"""
ValueResolver(df_dbf, regn_str, code_str, ctx) -> value_str

Используется в 101/102:
- df_dbf: таблица DBF (как отдаёт runner/read_dbf_to_df: REGN/A/B или расширенный DF)
- regn_str: номер банка
- code_str: код строки/показателя/счёта из формулы
- ctx: словарь с доп. параметрами (например, a_p=1/2 или нужные поля)

Должен вернуть строку-значение ("" или "0" если нет).
"""
