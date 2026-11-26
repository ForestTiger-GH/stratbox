"""Publication filename and observation-period rules for the debt source profile."""
from __future__ import annotations
import re
from datetime import date, datetime

CBR_0105A_DEBT_CORP_SERIES_CODE = "01_05_A_Debt_corp"

CBR_0105A_DEBT_CORP_FILENAME_RE = re.compile(
    r"^01_05_A_Debt_corp_(\d{8})\.xlsx$",
    flags=re.I,
)


def report_date_from_cbr_0105a_filename(source_name: str) -> str:
    """Resolve the observation date from an admitted canonical publication name."""
    match = CBR_0105A_DEBT_CORP_FILENAME_RE.fullmatch(str(source_name).strip())
    if not match:
        raise ValueError(f"Unsupported 01_05_A_Debt_corp source name: {source_name!r}")
    parsed = datetime.strptime(match.group(1), "%Y%m%d").date()
    return parsed.isoformat()
