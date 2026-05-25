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
    text = text.replace("_", " ")
    text = text.replace(",", " ")
    text = re.sub(r"\s+", " ", text)
    return text



def extract_extension(file_name: str) -> str:
    """Извлекает расширение файла в нижнем регистре."""
    base = _basename(file_name)
    parts = base.rsplit(".", 1)
    if len(parts) == 2:
        return f".{parts[1].lower()}"
    return ""



def _format_date_text(period_date: date) -> str:
    """Формирует стандартный текст календарного периода."""
    return period_date.isoformat()



def _format_week_text(*, year: int, month_title: str, week_no: int) -> str:
    """Формирует стандартный текст недельного периода."""
    return f"{year:04d} {month_title} {week_no} неделя"



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

        month_no, month_title = month_info

        try:
            period_year = int(match.group("year"))
            week_no = int(match.group("week"))
            period_date = date(period_year, month_no, 1)
        except ValueError:
            return None, None, None

        return period_date, _format_week_text(year=period_year, month_title=month_title, week_no=week_no), week_no

    return None, None, None



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
    has_q_marker = bool(_Q_MARKER_RE.search(normalized_name))

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
