"""
Форма 0409802 «Консолидированный балансовый отчет».

Модуль отвечает только за физическую структуру публичного DBF Банка России:
``REGN_GKO``, ``STR``, ``KORR_P``, ``KORR_M``, ``KORR_GR`` и ``VSEGO``.
Номенклатура 86 строк основного баланса хранится в ``models/form802.csv``.

Стандартный long использует ``measure=total`` (поле ``VSEGO``), а ``run_raw``
сохраняет все четыре физически доступных канала значений.
"""

from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_forms.common.direct_form import (
    DirectDatasetSpec,
    run_direct_dataset_raw,
    run_direct_form,
)
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig


FORM = "802"


def build_url(d: pd.Timestamp) -> str:
    """
    Функция формирует ссылку на архив формы 802 за отчетную дату.
    """
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/802-{ymd}.rar"


DEFAULT_SPEC = DirectDatasetSpec(
    form=FORM,
    dataset="main",
    progress_desc="CBR 802",
    build_url=build_url,
    bank_fields=("REGN_GKO",),
    code_fields=("STR",),
    measure_fields={
        "total": ("VSEGO",),
        "consolidation_plus": ("KORR_P",),
        "consolidation_minus": ("KORR_M",),
        "intragroup_adjustment": ("KORR_GR",),
    },
    prefer_stem_contains="PK802",
)


def run_raw(
    *,
    dates: list[pd.Timestamp],
    cfg: RunnerConfig | None = None,
    show_progress: bool = True,
) -> list[tuple[str, pd.DataFrame]]:
    """
    Функция возвращает normalized raw 802 со всеми полями корректировок и total.
    """
    return run_direct_dataset_raw(
        dates=dates,
        spec=DEFAULT_SPEC,
        cfg=cfg,
        show_progress=show_progress,
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
    Функция загружает 802 и формирует canonical long по 86 официальным строкам.
    """
    return run_direct_form(
        dates=dates,
        banks_df=banks_df,
        model_df=model_df,
        spec=DEFAULT_SPEC,
        cfg=cfg,
        show_progress=show_progress,
    )
