"""Discovered escrow source instances."""
from dataclasses import dataclass
@dataclass(frozen=True, slots=True)
class EscrowSourceLink:
    """One discovered monthly publication instance."""

    source_id: str
    url: str
    source_name: str
    file_date_hint: str | None = None
    format: str = "xlsx"
    extraction_status: str = "supported"
    profile_id: str = "cbr-escrow-xlsx-flake-2"
