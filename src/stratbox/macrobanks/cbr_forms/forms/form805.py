"""Physical fields and source identity for Bank of Russia Form 805."""


from __future__ import annotations

from datetime import date

from stratbox.macrobanks.cbr_forms.common.direct_form import (
    DirectDatasetSpec,
    normalize_code_metric,
)


FORM = "805"


def build_url(d: date) -> str:
    """
    Функция формирует ссылку на архив формы 805 за отчетную дату.
    """
    ymd = d.strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/805-{ymd}.rar"


DEFAULT_SPEC = DirectDatasetSpec(
    form=FORM,
    dataset="normatives",
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
