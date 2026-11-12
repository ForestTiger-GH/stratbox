"""Physical fields and source identity for Bank of Russia Form 135."""


from __future__ import annotations

from datetime import date

from stratbox.macrobanks.cbr_forms.common.direct_form import (
    DirectDatasetSpec,
    normalize_code_metric,
)


FORM = "135"


def build_url(d: date) -> str:
    """
    Функция формирует ссылку на архив формы 135 за отчетную дату.
    """
    ymd = d.strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/135-{ymd}.rar"


DEFAULT_SPEC = DirectDatasetSpec(
    form=FORM,
    dataset="section3",
    bank_fields=("REGN",),
    code_fields=("C1_3",),
    measure_fields={"actual": ("C2_3",)},
    prefer_stem_contains="135_3",
    code_normalizer=normalize_code_metric,
)
