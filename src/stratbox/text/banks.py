"""
banks.py — утилиты для работы с названиями банков.

Здесь хранится функция нормализации названий банков, которая:
- приводит разные варианты юр.формы к тегам (АО/ПАО/ООО/НКО и т.п.)
- исправляет "традиционные" варианты написания (например, Россельхозбанк -> РСХБ)
- выдаёт короткое и единообразное имя, удобное для таблиц и графиков

Важно:
- по умолчанию используется CAPS LOCK (case_mode='upper'), как принято внутри компании
- функция поддерживает строку, list/tuple, а также pandas.Series / pandas.Index
"""

from __future__ import annotations


def normalize_bank_name(
    name,
    placement: str = "omit",     # 'left' | 'right' | 'omit'
    case_mode: str = "upper",    # 'upper' | 'preserve'
    drop_bank: str = "left"      # 'keep' | 'left' | 'right' | 'both'
):
    import re

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

    # --- OPF-замены (неупорядоченный список) ---
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
    # Авто-приоритизация: длиннее результат → раньше; при равенстве — длиннее шаблон раньше
    OPF = sorted(OPF, key=lambda pr: (len(pr[1]), len(pr[0])), reverse=True)

    # Спец-кейсы
    SPECIAL = [
        (re.compile(r"\b(нац(иональн\w*)?\s+рас[чш]е?тн\w*\s+центр|нрц|нац\s*рц)\b", re.I),
         (["НКО", "АО"], "НАЦИОНАЛЬНЫЙ РАСЧЕТНЫЙ ЦЕНТР")),
        (re.compile(r"\b(нац(иональн\w*)?\s+рас[чш]е?тн\w*\s+депозитар\w*|нрд)\b", re.I),
         (["НКО", "АО"], "НАЦИОНАЛЬНЫЙ РАСЧЕТНЫЙ ДЕПОЗИТАРИЙ")),
        (re.compile(r"\b(петербургск\w*\s+рас[чш]е?тн\w*\s+центр|прц|спб\s*рц)\b", re.I),
         (["НКО", "АО"], "ПЕТЕРБУРГСКИЙ РАСЧЕТНЫЙ ЦЕНТР")),
    ]

    # Пост-нормализационные правки — «традиционные ошибки»
    ERR_FIX = {
        "Россельхозбанк": "РСХБ",
        "Россельхоз банк": "РСХБ",
        "Тинькофф Банк": "Т-Банк",
        "Тинькофф-Банк": "Т-Банк",
        "Т Банк": "Т-Банк",
        "Тинькофф": "Т-Банк",
        "ТБанк": "Т-Банк",
        "Райффайзен банк": "Райффайзенбанк",
        "Сбербанк России": "Сбербанк",
        "Сбер": "Сбербанк",
        "МТС Банк": "МТС-Банк",
    }

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

    def _apply_err_fix(s: str) -> str:
        # Самые длинные ключи — первыми, чтобы не срабатывали укороченные варианты раньше
        for old in sorted(ERR_FIX.keys(), key=len, reverse=True):
            s = re.sub(rf"(?<!\w){re.escape(old)}(?!\w)", ERR_FIX[old], s, flags=re.I)
        return s

    def _apply_opf(s: str) -> str:
        for p, r in OPF:
            s = re.sub(p, r, s, flags=re.I)
        return s

    # Извлечение тегов без перекрытий: одно общее regex, длинные сначала
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
        out = re.sub(r"^\s*-\s*", "", out)  # убрать «висячий» дефис
        return re.sub(r"\s+", " ", out).strip()

    def _one(x):
        if x is None or str(x).strip() == "":
            return None

        # 1) Предобработка
        s = _std(x)

        # 2) Сначала традиционные правки (длинные -> короткие)
        s = _apply_err_fix(s)

        # 3) Затем OPF-замены (НКО-ЦК, АО, ПАО и т.п.)
        s = _apply_opf(s)

        up = s.upper()

        # 4) Спец-кейсы или общий путь
        tags, rem = None, None
        for pat, (tg, canon) in SPECIAL:
            if pat.search(up):
                tags = [t for t in ORDERED_TAGS if t in tg]
                rem = canon if case_mode == "upper" else canon.title()
                break

        if tags is None:
            tags = _collect_tags_longest_first(up)
            rem = _strip(up if case_mode == "upper" else s, tags, ci=(case_mode != "upper"))

        # 5) Сборка по placement
        if placement == "omit":
            res = rem
        elif placement == "right":
            res = f"{rem} ({' '.join(tags)})" if tags and rem else (f"({' '.join(tags)})" if tags else rem)
        else:  # left
            res = (" ".join([*tags, rem]).strip() if tags and rem else (rem or " ".join(tags).strip()))

        # 6) Удаление ОТДЕЛЬНОГО слова «Банк» на краях (склейки/дефисы не трогаем)
        if drop_bank in {"left", "both"}:
            res = re.sub(r"^\s*БАНК\s+(?=\S)", "", res, flags=re.I)
        if drop_bank in {"right", "both"}:
            res = re.sub(r"(?<=\S)\s+БАНК\s*$", "", res, flags=re.I)

        # Страховка от дубликата вида «…-БАНК БАНК»
        res = re.sub(r"(?i)(\b\S+-БАНК)\s+БАНК\b", r"\1", res or "")

        # 7) Финальная чистка
        res = re.sub(r"\s*-\s*", "-", res or "")
        res = re.sub(r"\s+", " ", res).strip()

        return (res.upper() if case_mode == "upper" else res) or None

    # Коллекции/pandas
    if HAS_PD and isinstance(name, pd.Series):
        return name.map(_one)
    if HAS_PD and isinstance(name, pd.Index):
        return pd.Index([_one(v) for v in name], name=name.name)
    if isinstance(name, (list, tuple)):
        return [_one(v) for v in name]
    return _one(name)
