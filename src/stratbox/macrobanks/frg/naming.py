"""
Разбор имени файла поставщика FRG и внутренних имён библиотеки.

Задачи модуля:
- нормализовать имя файла;
- извлечь период из имени;
- определить семейство файла по реестру;
- поддержать как исходные имена поставщика FRG, так и внутренние имена,
  которые уже создала сама библиотека.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from stratbox.macrobanks.frg.filename_scheme import get_active_internal_name_scheme
from stratbox.macrobanks.frg.models import FrgFamilyRule
from stratbox.macrobanks.frg.registry import get_family_rules


_DATE_RE = re.compile(
    r"(?<!\d)(?P<year>20\d{2})[\s._/-]+(?P<month>\d{1,2})[\s._/-]+(?P<day>\d{1,2})(?!\d)"
)
_WEEK_PATTERNS = (
    re.compile(
        r"(?P<month>январ[ья]|феврал[ья]|март[а]?|апрел[ья]|ма[йя]|июн[ья]|июл[ья]|"
        r"август[а]?|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья])[\s._-]+"
        r"(?P<year>20\d{2})[\s._-]+(?P<week>\d+)[\s._-]+недел[ьяи]*",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"(?P<year>20\d{2})[\s._-]+"
        r"(?P<month>январ[ья]|феврал[ья]|март[а]?|апрел[ья]|ма[йя]|июн[ья]|июл[ья]|"
        r"август[а]?|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья])[\s._-]+"
        r"(?P<week>\d+)[\s._-]+недел[ьяи]*",
        flags=re.IGNORECASE,
    ),
)
_INTERNAL_DATE_PREFIX_RE = re.compile(r"^(?P<period>20\d{2}-\d{2}-\d{2})_(?P<label>.+)$")
_INTERNAL_WEEK_PREFIX_RE = re.compile(
    r"^(?P<year>20\d{2})-(?P<month>\d{2}) week (?P<week>\d+)_(?P<label>.+)$",
    flags=re.IGNORECASE,
)
_MONTHS = {
    "январь": (1, "Январь"),
    "января": (1, "Январь"),
    "февраль": (2, "Февраль"),
    "февраля": (2, "Февраль"),
    "март": (3, "Март"),
    "марта": (3, "Март"),
    "апрель": (4, "Апрель"),
    "апреля": (4, "Апрель"),
    "май": (5, "Май"),
    "мая": (5, "Май"),
    "июнь": (6, "Июнь"),
    "июня": (6, "Июнь"),
    "июль": (7, "Июль"),
    "июля": (7, "Июль"),
    "август": (8, "Август"),
    "августа": (8, "Август"),
    "сентябрь": (9, "Сентябрь"),
    "сентября": (9, "Сентябрь"),
    "октябрь": (10, "Октябрь"),
    "октября": (10, "Октябрь"),
    "ноябрь": (11, "Ноябрь"),
    "ноября": (11, "Ноябрь"),
    "декабрь": (12, "Декабрь"),
    "декабря": (12, "Декабрь"),
}
_Q_MARKER_RE = re.compile(r"(?<![a-zа-я])q(?![a-zа-я])", flags=re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ParsedName:
    """Результат разбора имени файла."""

    file_name: str
    extension: str
    normalized_name: str
    name_origin: str
    name_priority: int
    family_rule: FrgFamilyRule | None
    period_date: date | None
    period_date_text: str | None
    week_no: int | None
    has_week_marker: bool
    has_q_marker: bool


@dataclass(frozen=True, slots=True)
class InternalNameParseResult:
    """Результат распознавания внутреннего имени файла."""

    family_rule: FrgFamilyRule
    period_date: date
    period_date_text: str
    week_no: int | None
    has_week_marker: bool
    has_q_marker: bool


_NAME_ORIGIN_PRIORITY = {
    "unrecognized": 0,
    "source_raw": 10,
    "internal_standard": 20,
}


def _basename(path: str) -> str:
    """Возвращает имя файла из пути с любой формой слэшей."""
    return str(path).replace("\\", "/").rstrip("/").split("/")[-1]



def normalize_file_name(file_name: str) -> str:
    """Приводит имя файла к единому виду для распознавания."""
    text = str(file_name).strip().lower().replace("ё", "е")
    text = text.replace("—", "-").replace("–", "-")
    text = text.replace("_", " ")
    text = text.replace(",", " ")
    text = re.sub(r"\s+", " ", text)
    return text



def normalize_label_text(text: str) -> str:
    """Нормализует подпись семейства для сравнения внутренних имён."""
    value = str(text).strip().lower().replace("ё", "е")
    value = value.replace("—", "-").replace("–", "-")
    value = value.replace("_", " ")
    value = value.replace(".", " ")
    value = value.replace(",", " ")
    value = re.sub(r"\s*\-\s*", " - ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()



def extract_extension(file_name: str) -> str:
    """Извлекает расширение файла в нижнем регистре."""
    base = _basename(file_name)
    parts = base.rsplit(".", 1)
    if len(parts) == 2:
        return f".{parts[1].lower()}"
    return ""



def _stem_without_extension(file_name: str) -> str:
    """Возвращает имя файла без расширения."""
    base = _basename(file_name)
    extension = extract_extension(base)
    if extension:
        return base[: -len(extension)]
    return base


def _extract_supplier_prefix(file_name: str) -> str:
    """Возвращает префикс до первой точки для проверки поставщика."""
    stem = _stem_without_extension(file_name)
    return stem.split(".", 1)[0].strip()


def looks_like_frg_supplier_prefix(file_name: str) -> bool:
    """Проверяет, что до первой точки сигнатура поставщика равна FRG."""
    prefix = _extract_supplier_prefix(file_name)
    if not prefix:
        return False

    upper_latin_letters = "".join(ch for ch in prefix if "A" <= ch <= "Z")
    return upper_latin_letters == "FRG"



def _format_date_text(period_date: date) -> str:
    """Формирует стандартный текст календарного периода."""
    return period_date.isoformat()



def _format_week_text(*, year: int, month_no: int, week_no: int) -> str:
    """Формирует стандартный текст недельного периода."""
    return f"{year:04d}-{month_no:02d} week {week_no}"



def extract_date_period(normalized_name: str) -> tuple[date | None, str | None]:
    """Пытается извлечь календарную дату периода из имени."""
    match = _DATE_RE.search(normalized_name)
    if not match:
        return None, None

    try:
        period_date = date(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
        )
    except ValueError:
        return None, None
    return period_date, _format_date_text(period_date)



def extract_week_period(normalized_name: str) -> tuple[date | None, str | None, int | None]:
    """Пытается извлечь недельный период и нормализует его текст."""
    for pattern in _WEEK_PATTERNS:
        match = pattern.search(normalized_name)
        if not match:
            continue

        month_token = match.group("month").lower()
        month_info = _MONTHS.get(month_token)
        if month_info is None:
            return None, None, None

        month_no, _month_title = month_info

        try:
            period_year = int(match.group("year"))
            week_no = int(match.group("week"))
            period_date = date(period_year, month_no, 1)
        except ValueError:
            return None, None, None

        return period_date, _format_week_text(year=period_year, month_no=month_no, week_no=week_no), week_no

    return None, None, None



def _matches_rule(
    normalized_name: str,
    rule: FrgFamilyRule,
    *,
    has_week_marker: bool,
    has_q_marker: bool,
) -> bool:
    """Проверяет, подходит ли имя файла под правило семейства."""
    if rule.requires_week_marker and not has_week_marker:
        return False
    if rule.requires_q_marker and not has_q_marker:
        return False

    if any(token not in normalized_name for token in rule.tokens_all):
        return False

    if rule.tokens_any and not any(token in normalized_name for token in rule.tokens_any):
        return False

    if any(token in normalized_name for token in rule.tokens_none):
        return False

    return True



def resolve_family_rule(
    normalized_name: str,
    *,
    has_week_marker: bool,
    has_q_marker: bool,
) -> FrgFamilyRule | None:
    """Подбирает первое подходящее правило из реестра."""
    for rule in get_family_rules():
        if _matches_rule(
            normalized_name,
            rule,
            has_week_marker=has_week_marker,
            has_q_marker=has_q_marker,
        ):
            return rule
    return None



def _strip_internal_prefix(stem: str) -> str | None:
    """Убирает активный внутренний префикс, если он используется."""
    active_scheme = get_active_internal_name_scheme()
    prefix = active_scheme.prefix.strip()
    separator = active_scheme.separator

    if not prefix:
        return stem

    prefix_with_separator = f"{prefix}{separator}"
    if stem.startswith(prefix_with_separator):
        return stem[len(prefix_with_separator) :]
    return None



def _resolve_family_rule_by_file_label(label_text: str) -> FrgFamilyRule | None:
    """Подбирает семейство по точному совпадению внутренней файловой подписи."""
    normalized_label = normalize_label_text(label_text)
    for rule in get_family_rules():
        if normalize_label_text(rule.file_label) == normalized_label:
            return rule
    return None



def parse_internal_standard_name(file_name: str) -> InternalNameParseResult | None:
    """Пытается распознать имя, которое уже создала сама библиотека."""
    stem = _stem_without_extension(file_name)
    stem_wo_prefix = _strip_internal_prefix(stem)
    if stem_wo_prefix is None:
        return None

    match = _INTERNAL_DATE_PREFIX_RE.match(stem_wo_prefix)
    if match:
        try:
            period_date = date.fromisoformat(match.group("period"))
        except ValueError:
            return None

        family_rule = _resolve_family_rule_by_file_label(match.group("label"))
        if family_rule is None or family_rule.period_mode != "date":
            return None

        return InternalNameParseResult(
            family_rule=family_rule,
            period_date=period_date,
            period_date_text=_format_date_text(period_date),
            week_no=None,
            has_week_marker=False,
            has_q_marker=family_rule.requires_q_marker,
        )

    match = _INTERNAL_WEEK_PREFIX_RE.match(stem_wo_prefix)
    if match:
        try:
            period_year = int(match.group("year"))
            month_no = int(match.group("month"))
            week_no = int(match.group("week"))
            period_date = date(period_year, month_no, 1)
        except ValueError:
            return None

        family_rule = _resolve_family_rule_by_file_label(match.group("label"))
        if family_rule is None or family_rule.period_mode != "weekly":
            return None

        return InternalNameParseResult(
            family_rule=family_rule,
            period_date=period_date,
            period_date_text=_format_week_text(year=period_year, month_no=month_no, week_no=week_no),
            week_no=week_no,
            has_week_marker=True,
            has_q_marker=family_rule.requires_q_marker,
        )

    return None



def parse_file_name(file_path: str) -> ParsedName:
    """Разбирает имя файла и возвращает классификацию первого этапа."""
    file_name = _basename(file_path)
    normalized_name = normalize_file_name(file_name)
    extension = extract_extension(file_name)

    internal_result = parse_internal_standard_name(file_name)
    if internal_result is not None:
        return ParsedName(
            file_name=file_name,
            extension=extension,
            normalized_name=normalized_name,
            name_origin="internal_standard",
            name_priority=_NAME_ORIGIN_PRIORITY["internal_standard"],
            family_rule=internal_result.family_rule,
            period_date=internal_result.period_date,
            period_date_text=internal_result.period_date_text,
            week_no=internal_result.week_no,
            has_week_marker=internal_result.has_week_marker,
            has_q_marker=internal_result.has_q_marker,
        )

    weekly_date, weekly_text, week_no = extract_week_period(normalized_name)
    date_period, date_text = extract_date_period(normalized_name)

    has_week_marker = "недел" in normalized_name
    has_q_marker = bool(_Q_MARKER_RE.search(normalized_name))
    is_frg_source_name = looks_like_frg_supplier_prefix(file_name)

    family_rule = None
    if is_frg_source_name:
        family_rule = resolve_family_rule(
            normalized_name,
            has_week_marker=has_week_marker,
            has_q_marker=has_q_marker,
        )

    if family_rule is not None and family_rule.period_mode == "weekly":
        period_date = weekly_date
        period_text = weekly_text
    else:
        period_date = date_period
        period_text = date_text

    name_origin = "source_raw" if is_frg_source_name and family_rule is not None else "unrecognized"

    return ParsedName(
        file_name=file_name,
        extension=extension,
        normalized_name=normalized_name,
        name_origin=name_origin,
        name_priority=_NAME_ORIGIN_PRIORITY[name_origin],
        family_rule=family_rule,
        period_date=period_date,
        period_date_text=period_text,
        week_no=week_no if family_rule and family_rule.period_mode == "weekly" else None,
        has_week_marker=has_week_marker,
        has_q_marker=has_q_marker,
    )
