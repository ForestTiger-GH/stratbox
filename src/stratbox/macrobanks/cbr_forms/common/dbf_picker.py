"""
Модуль отвечает за выбор "правильного" DBF внутри распакованного архива.

Идея:
- После распаковки в папке может быть несколько DBF.
- Нужный выбирается по наличию требуемых полей (кандидаты задаёт форма).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dbfread import DBF

from stratbox.macrobanks.cbr_forms.common.dbf import CBRFieldParser, DBFLayout


@dataclass(frozen=True)
class LayoutCandidates:
    """
    Кандидаты имён полей (в UPPER).

    Требование:
- regn_candidates: варианты поля REGN
- a_candidates: варианты поля A (например C1_3 / C1 / ...)
- b_candidates: варианты поля B (например C2_3 / C3 / ...)
    """
    regn_candidates: list[str]
    a_candidates: list[str]
    b_candidates: list[str]


def list_dbf_files(root: Path) -> list[Path]:
    """
    Находит все DBF в каталоге рекурсивно.
    """
    return sorted(list(root.rglob("*.dbf")) + list(root.rglob("*.DBF")))


def pick_dbf_and_layout(
    extracted_dir: Path,
    candidates: LayoutCandidates,
    prefer_stem_contains: str | None = None,
) -> tuple[Path, DBFLayout]:
    """
    Выбирает DBF и возвращает:
      (path_to_dbf, DBFLayout(regn, a, b))

    prefer_stem_contains:
      - необязательный "бонус" к скорингу, если имя файла содержит строку (например "123" или "135").
    """
    dbfs = list_dbf_files(extracted_dir)
    if not dbfs:
        raise FileNotFoundError("No DBF found after extracting archive.")

    best = None  # (score, path, layout)

    for p in dbfs:
        try:
            tmp = DBF(str(p), parserclass=CBRFieldParser, load=False)
            fn = {f.upper(): f for f in tmp.field_names}  # upper -> real
        except Exception:
            continue

        regn_real = next((fn[c] for c in candidates.regn_candidates if c in fn), None)
        a_real = next((fn[c] for c in candidates.a_candidates if c in fn), None)
        b_real = next((fn[c] for c in candidates.b_candidates if c in fn), None)

        if not (regn_real and a_real and b_real):
            continue

        score = 0
        if prefer_stem_contains and prefer_stem_contains.lower() in p.stem.lower():
            score += 10

        # бонус “классическим” именам
        if a_real.upper() in ("C1", "C_1", "C1_3"):
            score += 3
        if b_real.upper() in ("C3", "C_3", "C2_3"):
            score += 3

        cand = (score, p, DBFLayout(regn=regn_real, a=a_real, b=b_real))
        if best is None or cand[0] > best[0]:
            best = cand

    if best is None:
        # диагностика: покажем поля первого файла
        sample = dbfs[0]
        tmp = DBF(str(sample), parserclass=CBRFieldParser, load=False)
        raise RuntimeError(f"Could not pick suitable DBF layout. Sample='{sample.name}', fields={tmp.field_names}")

    _, chosen, layout = best
    return chosen, layout
