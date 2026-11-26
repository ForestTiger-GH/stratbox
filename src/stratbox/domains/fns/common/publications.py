"""Publication facts are independent of file decoding and storage."""
from dataclasses import dataclass
from datetime import date
from .access import SME_INDEX, SME_DATA, LEGAL_INDEX


@dataclass(frozen=True)
class PublicationRules:
    source_id: str
    index_url: str
    data_url: str | None
    method: str
    earliest: date
    first_day: bool = False
    max_bytes: int = 30_000_000
    archive_mode: str = "single"


SME_PUBLICATION = PublicationRules("fns.sme", SME_INDEX, SME_DATA, "POST",
                                   date(2016, 8, 1), max_bytes=4_000_000)
LEGAL_PUBLICATION = PublicationRules("fns.1yur", LEGAL_INDEX, None, "GET",
                                     date(2012, 1, 1), first_day=True, archive_mode="workbook_collection")
