"""
Форма 0409135: текущий direct-dataset обязательных нормативов банка.

Физическая структура раздела 3 задается в этом модуле, а семантический набор
показателей — в ``models/form135.csv``. Архитектура допускает последующее
добавление ``control_value``/``note`` и других dataset без изменения CSV-schema.
"""

from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_forms.common.direct_form import (
    DirectDatasetSpec,
    normalize_code_metric,
    run_direct_form,
)
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig


FORM = "135"


def build_url(d: pd.Timestamp) -> str:
    """
    Функция формирует ссылку на архив формы 135 за отчетную дату.
    """
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/135-{ymd}.rar"


DEFAULT_SPEC = DirectDatasetSpec(
    form=FORM,
    dataset="section3",
    progress_desc="CBR 135",
    build_url=build_url,
    bank_fields=("REGN",),
    code_fields=("C1_3",),
    measure_fields={"actual": ("C2_3",)},
    prefer_stem_contains="135_3",
    code_normalizer=normalize_code_metric,
)


def run(
    *,
    dates: list[pd.Timestamp],
    banks_df: pd.DataFrame,
    model_df: pd.DataFrame,
    cfg: RunnerConfig | None = None,
    show_progress: bool = True,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Функция запускает текущий direct-dataset формы 135.
    """
    return run_direct_form(
        dates=dates,
        banks_df=banks_df,
        model_df=model_df,
        spec=DEFAULT_SPEC,
        cfg=cfg,
        show_progress=show_progress,
    )
