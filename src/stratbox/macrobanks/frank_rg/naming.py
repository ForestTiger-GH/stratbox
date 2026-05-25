"""
Разбор имени файла Frank RG.

Задачи модуля:
- нормализовать имя файла;
- извлечь период из имени;
- определить семейство файла по реестру.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from stratbox.macrobanks.frank_rg.models import FrankFamilyRule
from stratbox.macrobanks.frank_rg.registry import get_family_rules


_DATE_RE = re.compile(r"(?P<year>20\d{2})[.-](?P<month>\d{2})[.-](?P<day>\d{2})")
_WEEK_RE = re.compile(
    r"(?P<month>январ[ья]|феврал[ья]|март[а]?|апрел[ья]|ма[йя]|июн[ья]|июл[ья]|"
    r"август[а]?|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья])\s+"
    r"(?P<year>20\d{2})\s+(?P<week>\d+)\s+недел",
    flags=re.IGNORECASE,
)
_MONTHS = {
    "январь": 1,
    "января": 1,
    "февраль": 2,
    "февраля": 2,
    "март": 3,
    "марта": 3,
    "апрель": 4,
    "апреля": 4,
    "май": 5,
    "мая": 5,
    "июнь": 6,
    "июня": 6,
    "июль": 7,
    "июля": 7,
    "август": 8,
    "августа": 8,
    "сентябрь": 9,
    "сентября": 9,
    "октябрь": 10,
    "октября": 10,
    "ноябрь": 11,
    "ноября": 11,
    "декабрь": 12,
    "декабря": 12,
}


@dataclass(frozen=True, slots=True)
class ParsedName:
    """Результат разбора имени файла."""

    file_name: str
    extension: str
    normalized_name: str
    family_rule: FrankFamilyRule | None
    period_date: date | None
    period_date_text: str | None
    week_no: int | None
    has_week_marker: bool
    has_q_marker: bool


def _basename(path: str) -> str:
    """Возвращает имя файла из пути с любой формой слэшей."""
    return str(path).replace("\\", "/").rstrip("/").split("/")[-1]


def normalize_file_name(file_name: str) -> str:
    """Приводит имя файла к единому виду для распознавания."""
    text = str(file_name).strip().lower().replace("ё", "е")
    text = text.replace("—", "-").replace("–", "-")
    text = re.sub(r"\s+", " ", text)
    return text


def extract_extension(file_name: str) -> str:
    """Извлекает расширение файла в нижнем регистре."""
    base = _basename(file_name)
    parts = base.rsplit(".", 1)
    if len(parts) == 2:
        return f".{parts[1].lower()}"
    return ""


def extract_date_period(normalized_name: str) -> tuple[date | None, str | None]:
    """Пытается извлечь календарную дату периода из имени файла."""
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
    return period_date, match.group(0)


def extract_week_period(normalized_name: str) -> tuple[date | None, str | None, int | None]:
    """Пытается извлечь текстовый период вида 'Май 2026 2 недели'."""
    match = _WEEK_RE.search(normalized_name)
    if not match:
        return None, None, None

    month_token = match.group("month").lower()
    month_no = _MONTHS.get(month_token)
    if month_no is None:
        return None, None, None

    try:
        period_date = date(int(match.group("year")), month_no, 1)
        week_no = int(match.group("week"))
    except ValueError:
        return None, None, None

    return period_date, match.group(0), week_no


def _matches_rule(
    normalized_name: str,
    rule: FrankFamilyRule,
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
) -> FrankFamilyRule | None:
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


def parse_file_name(file_path: str) -> ParsedName:
    """Разбирает имя файла и возвращает классификацию первого этапа."""
    file_name = _basename(file_path)
    normalized_name = normalize_file_name(file_name)
    extension = extract_extension(file_name)

    weekly_date, weekly_text, week_no = extract_week_period(normalized_name)
    date_period, date_text = extract_date_period(normalized_name)

    has_week_marker = "недел" in normalized_name
    has_q_marker = "(q)" in normalized_name or normalized_name.endswith(" q") or " q " in normalized_name

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

    return ParsedName(
        file_name=file_name,
        extension=extension,
        normalized_name=normalized_name,
        family_rule=family_rule,
        period_date=period_date,
        period_date_text=period_text,
        week_no=week_no if family_rule and family_rule.period_mode == "weekly" else None,
        has_week_marker=has_week_marker,
        has_q_marker=has_q_marker,
    )
