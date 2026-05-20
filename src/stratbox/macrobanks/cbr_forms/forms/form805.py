"""
Форма 805.

Форма 0409805 содержит показатели банковской группы.
Для раздела с обязательными нормативами используется DBF PN805ГГMM.dbf.

Ключевые поля DBF:
- REGN_GKO: регистрационный номер головной кредитной организации;
- NAME_NORM: код норматива;
- FAKT_ZN: фактическое значение.

Модуль является тонкой настройкой общего движка metric_form.py.
"""

from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_forms.common.dbf_picker import LayoutCandidates
from stratbox.macrobanks.cbr_forms.common.metric_form import MetricFormSpec, run_metric_form
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig


FORM = "805"

DEFAULT_CANDIDATES = LayoutCandidates(
    regn_candidates=["REGN_GKO", "REGN"],
    a_candidates=["NAME_NORM", "C1_3"],
    b_candidates=["FAKT_ZN", "C2_3"],
)
DEFAULT_PREFER = "PN805"

DEFAULT_CODE_ALIASES = {
    "H20.2": "H20_2",
    "H20.4": "H20_4",
    "Н20.2": "H20_2",
    "Н20.4": "H20_4",
}


def build_url(d: pd.Timestamp) -> str:
    """
    Функция формирует ссылку на архив формы 805 за дату.
    """
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/805-{ymd}.rar"


def run(
    *,
    dates: list[pd.Timestamp],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
    candidates: LayoutCandidates | None = None,
    prefer_stem_contains: str | None = None,
    cfg: RunnerConfig | None = None,
    show_progress: bool = True,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    """
    Функция запускает обработку формы 805 и возвращает long-таблицу.
    """
    spec = MetricFormSpec(
        form=FORM,
        progress_desc="CBR 805",
        candidates=candidates or DEFAULT_CANDIDATES,
        prefer_stem_contains=prefer_stem_contains or DEFAULT_PREFER,
        build_url=build_url,
        code_aliases=DEFAULT_CODE_ALIASES,
    )
    return run_metric_form(
        dates=dates,
        banks_df=banks_df,
        formulas_df=formulas_df,
        spec=spec,
        cfg=cfg,
        show_progress=show_progress,
    )
