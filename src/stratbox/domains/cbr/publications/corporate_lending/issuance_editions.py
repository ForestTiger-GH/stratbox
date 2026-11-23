"""Publication filename and observation-period rules for the issuance source profile."""
from __future__ import annotations
import re
from datetime import date, datetime

SERIES_CODE = "01_04_A_New_loans_corp"


_FILENAME = re.compile(r"01_04_A_New_loans_corp_(\d{8})\.xlsx", re.I)


def report_date_from_filename(name: str) -> str:
    match = _FILENAME.fullmatch(name)
    if match is None:
        raise ValueError(f"Unknown issuance filename: {name!r}")
    day = datetime.strptime(match.group(1), "%Y%m%d").date()
    if day.day != 1:
        raise ValueError(f"Issuance release date is not the first day of a month: {name!r}")
    return day.isoformat()


def reference_period(report_date: str) -> str:
    day = date.fromisoformat(report_date)
    if day.day != 1:
        raise ValueError("Issuance report date must be the first day of a month")
    year, month = (day.year - 1, 12) if day.month == 1 else (day.year, day.month - 1)
    return f"{year:04d}-{month:02d}"
