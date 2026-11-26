"""Exact delivered-report name conventions, separate from economic periods."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import re

@dataclass(frozen=True, order=True)
class ReportPeriod:
    snapshot_date: date
    week_no: int | None = None

    def __post_init__(self):
        if self.week_no is not None and (type(self.week_no) is not int or not 1 <= self.week_no <= 6):
            raise ValueError("frg.publication_week_invalid")

    @property
    def text(self):
        return self.snapshot_date.isoformat() if self.week_no is None else f"{self.snapshot_date:%Y-%m} week {self.week_no}"

@dataclass(frozen=True)
class RecognitionRule:
    source_id: str
    canonical_label: str
    periodicity: str
    priority: int
    tokens_all: tuple[str, ...]
    tokens_any: tuple[str, ...] = ()
    tokens_none: tuple[str, ...] = ()
    requires_q_marker: bool = False
    min_period_date: date | None = None

_DATE = re.compile(r"(?<!\d)(20\d{2})[\s._/-]+(\d{1,2})[\s._/-]+(\d{1,2})(?!\d)")
_MONTH_TOKEN = (r"январ[ья]|феврал[ья]|март[а]?|апрел[ья]|ма[йя]|июн[ья]|июл[ья]|"
                r"август[а]?|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья]")
_WEEKS = (
    re.compile(rf"(?P<month>{_MONTH_TOKEN})[\s._-]+(?P<year>20\d{{2}})[\s._-]+(?P<week>\d+)[\s._-]+недел[ьяи]*", re.I),
    re.compile(rf"(?P<year>20\d{{2}})[\s._-]+(?P<month>{_MONTH_TOKEN})[\s._-]+(?P<week>\d+)[\s._-]+недел[ьяи]*", re.I),
)
_MONTHS = {
    "январь": 1, "января": 1, "февраль": 2, "февраля": 2,
    "март": 3, "марта": 3, "апрель": 4, "апреля": 4, "май": 5, "мая": 5,
    "июнь": 6, "июня": 6, "июль": 7, "июля": 7, "август": 8, "августа": 8,
    "сентябрь": 9, "сентября": 9, "октябрь": 10, "октября": 10,
    "ноябрь": 11, "ноября": 11, "декабрь": 12, "декабря": 12,
}
_CANONICAL_DATE = re.compile(r"^(?P<date>20\d{2}-\d{2}-\d{2})_(?P<label>.+)$")
_CANONICAL_WEEK = re.compile(r"^(?P<year>20\d{2})-(?P<month>\d{2}) week (?P<week>\d+)_(?P<label>.+)$", re.I)
_Q = re.compile(r"(?<![a-zа-я])q(?![a-zа-я])", re.I)
_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def normalize_file_name(value: str) -> str:
    value = value.strip().lower().replace("ё", "е")
    value = value.replace("—", "-").replace("–", "-").replace("_", " ").replace(",", " ")
    return re.sub(r"\s+", " ", value)


def normalize_label_text(value: str) -> str:
    value = value.strip().lower().replace("ё", "е")
    value = re.sub(r"[—–_.,-]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _supplier_name(stem: str) -> bool:
    prefix = stem.split(".", 1)[0].strip()
    return "".join(letter for letter in prefix if "A" <= letter <= "Z") == "FRG"


def _date_period(name: str) -> ReportPeriod | None:
    try:
        periods = {date(*(int(value) for value in match.groups())) for match in _DATE.finditer(name)}
        return ReportPeriod(periods.pop()) if len(periods) == 1 else None
    except ValueError:
        return None


def _week_period(name: str) -> ReportPeriod | None:
    try:
        periods = {
            ReportPeriod(date(int(match["year"]), _MONTHS[match["month"].lower()], 1), int(match["week"]))
            for pattern in _WEEKS for match in pattern.finditer(name)
        }
        return periods.pop() if len(periods) == 1 else None
    except (ValueError, KeyError):
        return None


def _canonical_period(stem: str):
    match = _CANONICAL_DATE.fullmatch(stem)
    if match:
        try:
            period = ReportPeriod(date.fromisoformat(match["date"]))
        except ValueError:
            period = None
        return match["label"], "snapshot", period
    match = _CANONICAL_WEEK.fullmatch(stem)
    if match:
        try:
            period = ReportPeriod(date(int(match["year"]), int(match["month"]), 1), int(match["week"]))
        except ValueError:
            period = None
        return match["label"], "month_week", period
    return None


def _matches(name: str, rule: RecognitionRule) -> bool:
    if rule.periodicity == "month_week" and "недел" not in name:
        return False
    if rule.requires_q_marker and not _Q.search(name):
        return False
    return (all(token in name for token in rule.tokens_all)
            and (not rule.tokens_any or any(token in name for token in rule.tokens_any))
            and not any(token in name for token in rule.tokens_none))



def canonical_filename(period: ReportPeriod, rule: RecognitionRule, format: str):
    if format not in {"xlsx", "xlsm", "xls", "xlsb"}:
        raise ValueError("frg.unsupported_format")
    if (period.week_no is not None) != (rule.periodicity == "month_week"):
        raise ValueError("frg.publication_period_mismatch")
    label = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", " ", rule.canonical_label).strip(" .")
    return period.text + "_" + re.sub(r"\s+", " ", label) + "." + format
