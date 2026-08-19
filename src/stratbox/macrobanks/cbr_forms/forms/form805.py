"""
Форма 0409805: текущий direct-dataset обязательных нормативов банковской группы.

Сейчас модуль сохраняет прежний аналитический охват нормативов. Новый общий
контракт моделей и direct-dataset позволяет далее добавлять остальные разделы
0409805 как отдельные dataset без возврата к выражениям вида ``FIELD -> VALUE``.
"""

from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_forms.common.direct_form import (
    DirectDatasetSpec,
    normalize_code_metric,
    run_direct_form,
)
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig


FORM = "805"


def build_url(d: pd.Timestamp) -> str:
    """
    Функция формирует ссылку на архив формы 805 за отчетную дату.
    """
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/805-{ymd}.rar"


DEFAULT_SPEC = DirectDatasetSpec(
    form=FORM,
    dataset="normatives",
    progress_desc="CBR 805",
    build_url=build_url,
    bank_fields=("REGN_GKO", "REGN"),
    code_fields=("NAME_NORM", "C1_3"),
    measure_fields={"actual": ("FAKT_ZN", "C2_3")},
    prefer_stem_contains="PN805",
    code_normalizer=normalize_code_metric,
    code_aliases={
        "H20.2": "H20_2",
        "H20.4": "H20_4",
        "Н20.2": "H20_2",
        "Н20.4": "H20_4",
    },
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
    Функция запускает текущий direct-dataset формы 805.
    """
    return run_direct_form(
        dates=dates,
        banks_df=banks_df,
        model_df=model_df,
        spec=DEFAULT_SPEC,
        cfg=cfg,
        show_progress=show_progress,
    )
