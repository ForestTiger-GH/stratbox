"""Pure interpretation of supplier names and canonical report filenames."""
from __future__ import annotations

from datetime import date
import re

from .contracts import Asset, Inventory, ReportPeriod, SourceFamily, SourceIndex
from .profiles import IdentificationProfile, NamingProfile, RecognitionRule

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


def identify_index(index: SourceIndex, *, sources: tuple[tuple[SourceFamily, IdentificationProfile], ...]) -> Inventory:
    """Identify observed names without reading, selecting or mutating files."""
    if len({item[0].family_id for item in sources}) != len(sources):
        raise ValueError("frg.profile.duplicate_family")
    if index.family_ids and set(index.family_ids) != {item[0].family_id for item in sources}:
        raise ValueError("frg.index.family_scope_mismatch")
    if len({item.path for item in index.entries}) != len(index.entries):
        raise ValueError("frg.index.duplicate_path")
    rules = []
    for family, profile in sources:
        if {item.slot for item in family.series} != {item.slot for item in profile.rules}:
            raise ValueError("frg.profile.series_slots_incomplete")
        rules.extend((family, family.slot(rule.slot), rule, profile) for rule in profile.rules)
    assets = []
    for entry in index.entries:
        if (not isinstance(entry.filename, str) or not entry.filename
                or entry.path.replace("\\", "/").rsplit("/", 1)[-1] != entry.filename):
            raise ValueError("frg.index.filename_mismatch")
        stem, dot, extension = entry.filename.rpartition(".")
        format = extension.lower() if dot else ""
        stem = stem if dot else entry.filename
        canonical = _canonical_period(stem)
        period = None
        matched = []
        recognition = "unclassified"
        if canonical:
            label, periodicity, period = canonical
            matched = [item for item in rules if item[2].periodicity == periodicity
                       and normalize_label_text(item[2].canonical_label) == normalize_label_text(label)]
            recognition = "canonical" if matched else "unclassified"
        elif _supplier_name(stem):
            normalized = normalize_file_name(stem)
            matched = [item for item in rules if _matches(normalized, item[2])]
            if matched:
                priority = min(item[2].priority for item in matched)
                matched = [item for item in matched if item[2].priority == priority]
                recognition = "supplier"
                period = (_week_period(normalized) if matched[0][2].periodicity == "month_week"
                          else _date_period(normalized))
        if len(matched) != 1:
            conflicted = len(matched) > 1
            assets.append(Asset(entry, None, None, None, format, period,
                                "conflicted" if conflicted else "unclassified", False,
                                "frg.file.identity_conflict" if conflicted else "frg.file.unclassified"))
            continue
        family, source, rule, profile = matched[0]
        diagnostic = "frg.file.recognized"
        if format not in profile.admitted_formats:
            diagnostic = "frg.file.unsupported_format"
        elif period is None:
            diagnostic = "frg.file.period_invalid"
        elif rule.min_period_date is not None and period.snapshot_date < rule.min_period_date:
            diagnostic = "frg.file.period_before_minimum"
        assets.append(Asset(entry, family.family_id, source.source_id, source.slot, format, period,
                            recognition, diagnostic == "frg.file.recognized", diagnostic))
    return Inventory(index, tuple(assets))


def _canonical_filename(period: ReportPeriod, rule: RecognitionRule, *, format: str, profile: NamingProfile) -> str:
    label = _FORBIDDEN.sub(" ", rule.canonical_label).strip(" .")
    label = re.sub(r"\s+", " ", label)
    if not label:
        raise ValueError("frg.naming.empty_label")
    return f"{period.text}{profile.separator}{label}.{format}"


def build_internal_file_name(period: ReportPeriod, rule: RecognitionRule, *, format: str, profile: NamingProfile) -> str:
    """Apply the registered canonical naming method to a logical report."""
    if not isinstance(period, ReportPeriod) or not isinstance(rule, RecognitionRule):
        raise ValueError("frg.naming.invalid_report")
    if (period.week_no is not None) != (rule.periodicity == "month_week"):
        raise ValueError("frg.naming.periodicity_mismatch")
    if format not in {"xlsx", "xlsm", "xls", "xlsb"}:
        raise ValueError("frg.naming.unsupported_format")
    return profile.build(period, rule, format=format, profile=profile)


__all__ = ("identify_index", "build_internal_file_name", "normalize_file_name", "normalize_label_text")
