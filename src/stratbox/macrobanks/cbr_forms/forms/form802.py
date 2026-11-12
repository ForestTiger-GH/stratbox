"""Physical fields and source identity for Bank of Russia Form 802."""


from __future__ import annotations

from datetime import date

from stratbox.macrobanks.cbr_forms.common.direct_form import (
    DirectDatasetSpec,
)


FORM = "802"


def build_url(d: date) -> str:
    """
    Функция формирует ссылку на архив формы 802 за отчетную дату.
    """
    ymd = d.strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/802-{ymd}.rar"


DEFAULT_SPEC = DirectDatasetSpec(
    form=FORM,
    dataset="main",
    bank_fields=("REGN_GKO",),
    code_fields=("STR",),
    measure_fields={
        "total": ("VSEGO",),
    },
    optional_measure_fields={
        "consolidation_plus": ("KORR_P",),
        "consolidation_minus": ("KORR_M",),
        "intragroup_adjustment": ("KORR_GR",),
    },
    prefer_stem_contains="PK802",
)
