"""
Реестр отчетных форм Банка России.

Задача модуля:
- хранить список доступных форм в одном месте;
- давать единый механизм выбора форм для API и CLI;
- не размножать ручные списки form101/form102/... по разным файлам.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from stratbox.macrobanks.cbr_forms.forms import form101, form102, form123, form135, form805


@dataclass(frozen=True)
class CbrFormEntry:
    """
    Описание отчетной формы в реестре.
    """

    code: str
    module: Any
    title: str


FORM_REGISTRY: dict[str, CbrFormEntry] = {
    "101": CbrFormEntry(code="101", module=form101, title="0409101"),
    "102": CbrFormEntry(code="102", module=form102, title="0409102"),
    "123": CbrFormEntry(code="123", module=form123, title="0409123"),
    "135": CbrFormEntry(code="135", module=form135, title="0409135"),
    "805": CbrFormEntry(code="805", module=form805, title="0409805"),
}


def resolve_forms(forms: list[str] | tuple[str, ...] | str | None = None) -> list[CbrFormEntry]:
    """
    Функция возвращает список форм для запуска.

    Поддерживаемые варианты:
    - None или "all": все доступные формы;
    - "101,102,805": список через запятую;
    - ["101", "805"]: список строк.
    """
    if forms is None:
        return list(FORM_REGISTRY.values())

    if isinstance(forms, str):
        raw = forms.strip()
        if not raw or raw.lower() == "all":
            return list(FORM_REGISTRY.values())
        codes = [x.strip() for x in raw.split(",") if x.strip()]
    else:
        codes = [str(x).strip() for x in forms if str(x).strip()]

    unknown = [x for x in codes if x not in FORM_REGISTRY]
    if unknown:
        raise ValueError(f"Unknown CBR forms: {unknown}. Available: {sorted(FORM_REGISTRY)}")

    return [FORM_REGISTRY[x] for x in codes]
