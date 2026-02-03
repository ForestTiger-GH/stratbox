"""
banks.py — утилиты для работы с названиями банков.

Цель normalize_bank_name:
- привести входные "кривые" названия к предсказуемому виду (чистка + OPF + спецкейсы)
- затем выполнить финальную канонизацию через реестр replacements:
  _resources/cbr_replacements/cbr_replacements.csv (canon, alias)

Важно:
- по умолчанию внутри компании используется CAPS LOCK (case_mode='upper')
- "брендовые" и любые "как нам надо" замены НЕ хранятся в коде; они хранятся в CSV
"""

from __future__ import annotations

from functools import lru_cache
from io import StringIO
import csv
import re


@lru_cache(maxsize=1)
def _load_cbr_replacements_alias_to_canon() -> dict[str, str]:
    """
    Загружает реестр замен из ресурсов пакета и возвращает словарь:
      ALIAS (upper) -> CANON (upper)

    Файл:
      stratbox.registries/_resources/cbr_replacements/cbr_replacements.csv

    Если файла нет или он некорректный — возвращается пустой словарь.
    """
    try:
        from stratbox.registries._loader import pick_latest_by_prefix, read_resource_bytes

        package = "stratbox.registries"
        rel_dir = "_resources/cbr_replacements"

        rf = pick_latest_by_prefix(package, rel_dir, prefix="cbr_replacements", suffix=".csv")
        raw = read_resource_bytes(package, rf.path)
        text = raw.decode("utf-8-sig")

        rdr = csv.DictReader(StringIO(text))
        out: dict[str, str] = {}

        for row in rdr:
            canon = (row.get("canon") or "").strip().upper()
            alias = (row.get("alias") or "").strip().upper()
            if canon and alias:
                out[alias] = canon

        return out
    except Exception:
        return {}


def normalize_bank_name(
    name,
    placement: str = "omit",     # 'left' | 'right' | 'omit'
    case_mode: str = "upper",    # 'upper' | 'preserve'
    drop_bank: str = "left"      # 'keep' | 'left' | 'right' | 'both'
):
    """
    Нормализует наименование банка.

    Стратегия:
    1) техническая чистка строки (пробелы/тире/кавычки/мусор)
    2) приведение полных юр.форм к тегам (ПАО/АО/ООО/НКО/...)
    3) спец-кейсы (НРД/НРЦ/ПРЦ)
    4) сборка результата по placement
    5) (опционально) удаление слова "БАНК" по краям
    6) финальная канонизация через replacements (alias -> canon)

    Реестр replacements должен содержать "как нам надо видеть" итоговые имена:
    - например: canon=СБЕР, alias=СБЕРБАНК
    - canon=ТБАНК, alias=Т-БАНК
    и т.п.
    """
    # pandas поддерживается опционально (если установлен)
    try:
        import pandas as pd
        HAS_PD = True
    except Exception:
        HAS_PD = False
        pd = None

    if placement not in {"left", "right", "omit"}:
        raise ValueError("placement: 'left' | 'right' | 'omit'")
    if case_mode not in {"upper", "preserve"}:
        raise ValueError("case_mode: 'upper' | 'preserve'")
    if drop_bank not in {"keep", "left", "right", "both"}:
        raise ValueError("drop_bank: 'keep' | 'left' | 'right' | 'both'")

    # Порядок отображения тегов при сборке результата
    ORDERED_TAGS = ["ПАО", "АО", "ОАО", "ООО", "ЗАО", "НКО-ЦК", "НКО", "АКБ", "КБ", "КИНБ", "АБ", "МАБ", "МБО", "МБ"]

    DASHES = r"\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uFE58\uFE63\uFF0D"
    SPACES = r"\u00A0\u2000-\u200B\u202F\u205F\u3000"

    # --- OPF-замены ---
    OPF = [
        # Специфичные НКО-ЦК
        (r"\bнебанковская\s+кредитная\s+организация\b(?:\s*[-—–]\s*|\s*\(\s*|\s+)\s*центральный\s+контрагент\b\)?", "НКО-ЦК"),
        (r"\bнко\b(?:\s*[-—–]\s*|\s*\(\s*|\s+)\s*центральный\s+контрагент\b\)?", "НКО-ЦК"),

        # Общие формы
        (r"\bне\s*публичное\s+акционерное\s+общество\b", "АО"),
        (r"\bпубличное\s+акционерное\s+общество\b", "ПАО"),
        (r"\bакционерное\s+общество\b", "АО"),
        (r"\bоткрытое\s+акционерное\s+общество\b", "ОАО"),
        (r"\bзакрытое\s+акционерное\s+общество\b", "ЗАО"),
        (r"\bобщество\s+с\s+ограниченной\s+ответственностью\b", "ООО"),
        (r"\bнебанковская\s+кредитная\s+организация\b", "НКО"),
        (r"\bакционерный\s+коммерческий\s+банк\b", "АКБ"),
        (r"\bкоммерческий\s+банк\b", "КБ"),
        (r"\bкоммерческий\s+инвестиционный\s+народный\s+банк\b", "КИНБ"),
        (r"\bакционерный\s+банк\b", "АБ"),
        (r"\bмежрегиональный\s+акционерный\s+банк\b", "МАБ"),
        (r"\bмежбанковское\s+объединение\b", "МБО"),
        (r"\bмеждународный\s+банк\b", "МБ"),
    ]
    # Приоритизация: длиннее результат → раньше; при равенстве — длиннее шаблон раньше
    OPF = sorted(OPF, key=lambda pr: (len(pr[1]), len(pr[0])), reverse=True)

    # Спец-кейсы (каноническое имя задаётся сразу)
    SPECIAL = [
        (re.compile(r"\b(нац(иональн\w*)?\s+рас[чш]е?тн\w*\s+центр|нрц|нац\s*рц)\b", re.I),
         (["НКО", "АО"], "НАЦИОНАЛЬНЫЙ РАСЧЕТНЫЙ ЦЕНТР")),
        (re.compile(r"\b(нац(иональн\w*)?\s+рас[чш]е?тн\w*\s+депозитар\w*|нрд)\b", re.I),
         (["НКО", "АО"], "НАЦИОНАЛЬНЫЙ РАСЧЕТНЫЙ ДЕПОЗИТАРИЙ")),
        (re.compile(r"\b(петербургск\w*\s+рас[чш]е?тн\w*\s+центр|прц|спб\s*рц)\b", re.I),
         (["НКО", "АО"], "ПЕТЕРБУРГСКИЙ РАСЧЕТНЫЙ ЦЕНТР")),
    ]

    # --- Утилиты ---
    def _std(s: str) -> str:
        # Нормализация пробелов/тире/кавычек + очистка от мусора
        s = "" if s is None else str(s)
        s = s.replace("Ё", "Е").replace("ё", "е")
        s = re.sub(f"[{SPACES}]", " ", s)
        s = re.sub(f"[{DASHES}]", "-", s)
        s = s.translate(str.maketrans({"«": "", "»": "", "“": "", "”": "", '"': "", "'": "", "_": " "}))
        s = re.sub(r"\.{2,}", ".", s)
        s = re.sub(r"[^\w\.\-\s\(\)]", " ", s, flags=re.U)
        return re.sub(r"\s+", " ", s).strip()

    def _apply_opf(s: str) -> str:
        for p, r in OPF:
            s = re.sub(p, r, s, flags=re.I)
        return s

    # Извлечение тегов: одно regex, длинные сначала
    TAG_ALTS = sorted(ORDERED_TAGS, key=len, reverse=True)
    TAG_RE = re.compile(r"\b(?:" + "|".join(map(re.escape, TAG_ALTS)) + r")\b")

    def _collect_tags_longest_first(upper: str):
        found = [m.group(0) for m in TAG_RE.finditer(upper)]
        seen, out = set(), []
        for t in ORDERED_TAGS:
            if t in found and t not in seen:
                out.append(t)
                seen.add(t)
        return out

    def _strip(base: str, tags, ci=True):
        out = base
        for t in tags:
            out = re.sub(rf"\b{re.escape(t)}\b", " ", out, flags=re.I if ci else 0)
        out = out.replace("(", " ").replace(")", " ")
        out = re.sub(r"[^\w\.\-\s]", " ", out, flags=re.U)
        out = re.sub(r"\s*-\s*", "-", out)
        out = re.sub(r"^\s*-\s*", "", out)
        return re.sub(r"\s+", " ", out).strip()

    def _final_replace(res: str) -> str:
        # Финальная канонизация через replacements применяется только в upper-режиме
        if not res:
            return res
        if case_mode != "upper":
            return res

        rep = _load_cbr_replacements_alias_to_canon()
        key = res.strip().upper()
        return rep.get(key, key)

    def _one(x):
        if x is None or str(x).strip() == "":
            return None

        # 1) Предобработка
        s = _std(x)

        # 2) OPF-замены (НКО-ЦК, АО, ПАО и т.п.)
        s = _apply_opf(s)

        up = s.upper()

        # 3) Спец-кейсы или общий путь
        tags, rem = None, None
        for pat, (tg, canon) in SPECIAL:
            if pat.search(up):
                tags = [t for t in ORDERED_TAGS if t in tg]
                rem = canon if case_mode == "upper" else canon.title()
                break

        if tags is None:
            tags = _collect_tags_longest_first(up)
            rem = _strip(up if case_mode == "upper" else s, tags, ci=(case_mode != "upper"))

        # 4) Сборка по placement
        if placement == "omit":
            res = rem
        elif placement == "right":
            res = f"{rem} ({' '.join(tags)})" if tags and rem else (f"({' '.join(tags)})" if tags else rem)
        else:  # left
            res = (" ".join([*tags, rem]).strip() if tags and rem else (rem or " ".join(tags).strip()))

        # 5) Удаление отдельного слова «Банк» по краям (склейки/дефисы не трогаем)
        if drop_bank in {"left", "both"}:
            res = re.sub(r"^\s*БАНК\s+(?=\S)", "", res or "", flags=re.I)
        if drop_bank in {"right", "both"}:
            res = re.sub(r"(?<=\S)\s+БАНК\s*$", "", res or "", flags=re.I)

        # Страховка от дубликата вида «…-БАНК БАНК»
        res = re.sub(r"(?i)(\b\S+-БАНК)\s+БАНК\b", r"\1", res or "")

        # 6) Финальная чистка
        res = re.sub(r"\s*-\s*", "-", res or "")
        res = re.sub(r"\s+", " ", res).strip()

        # 7) Финальная канонизация по replacements
        res = _final_replace(res)

        # 8) Возврат с учётом case_mode
        return (res.upper() if case_mode == "upper" else res) or None

    # Коллекции/pandas
    if HAS_PD and isinstance(name, pd.Series):
        return name.map(_one)
    if HAS_PD and isinstance(name, pd.Index):
        return pd.Index([_one(v) for v in name], name=name.name)
    if isinstance(name, (list, tuple)):
        return [_one(v) for v in name]
    return _one(name)
