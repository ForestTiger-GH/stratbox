"""Publisher-specific period labels normalized to stable economic periods.

No conversion of cumulative budget values into monthly or quarterly flows takes
place here. A header date's *day* is incidental for these monthly tables.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import re

_MONTHS = {
    "янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5,
    "мая": 5, "июн": 6, "июл": 7, "авг": 8, "сен": 9,
    "сент": 9, "окт": 10, "ноя": 11, "дек": 12,
}
_SUPERSCRIPTS = str.maketrans("", "", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def _year(token: str) -> int:
    year = int(token)
    year = year + 2000 if year < 100 else year
    if not 1900 <= year <= 2100:
        raise ValueError("minfin.period.year_out_of_range")
    return year


def normalize_period(header: str, frequency: str) -> str:
    """Return YYYY, YYYY-Qn or YYYY-MM; raise on ambiguous/unknown labels."""
    if frequency not in {"monthly", "quarterly", "annual"}:
        raise ValueError("minfin.period.frequency_invalid")
    if not isinstance(header, str) or len(header) > 128:
        raise ValueError("minfin.period.invalid_header")
    raw = header.strip().translate(_SUPERSCRIPTS)
    raw = re.sub(r"\s*\*+\s*$", "", raw).strip()
    if frequency == "annual":
        if re.fullmatch(r"(?:19|20)\d{2}", raw):
            return raw
    if frequency == "quarterly":
        m = re.fullmatch(r"([1-4])\s*кв\.?\s*(\d{2,4})\.?", raw, flags=re.I)
        if m:
            return f"{_year(m[2])}-Q{int(m[1])}"
    if frequency == "monthly":
        # Dates are often stored in XLSX as datetime values, and their day can
        # be the first or last day of the month. Both map to the same period.
        m = re.fullmatch(r"(\d{4})-(\d{1,2})(?:-(\d{1,2})(?:[T ].*)?)?", raw)
        if m:
            year, month = int(m[1]), int(m[2])
            if 1900 <= year <= 2100 and 1 <= month <= 12:
                return f"{year:04d}-{month:02d}"
        m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", raw)
        if m:
            return f"{_year(m[3]):04d}-{int(m[2]):02d}" if 1 <= int(m[2]) <= 12 else _bad()
        m = re.fullmatch(r"([А-Яа-яЁё]+)\.?\s*(\d{2,4})\.?", raw)
        if m:
            key = m[1].casefold()
            number = _MONTHS.get(key, _MONTHS.get(key[:3]))
            if number is not None:
                return f"{_year(m[2]):04d}-{number:02d}"
        # Excel serial dates, as emitted from cell.value when a source uses
        # an ordinary numeric cell rather than a date number format.
        if re.fullmatch(r"[0-9]{5}(?:\.0+)?", raw):
            serial = int(raw.split(".")[0])
            if 30_000 <= serial <= 90_000:
                observed = date(1899, 12, 30) + timedelta(days=serial)
                return f"{observed.year:04d}-{observed.month:02d}"
    raise ValueError("minfin.period.unrecognized_header")


def _bad():
    raise ValueError("minfin.period.unrecognized_header")


def preceding_year(period: str) -> str:
    if re.fullmatch(r"\d{4}(?:-Q[1-4]|-(?:0[1-9]|1[0-2]))?", period):
        return f"{int(period[:4]) - 1:04d}{period[4:]}"
    raise ValueError("minfin.period.invalid_identity")