"""Official FNS access facts; live transports belong to the core."""
from dataclasses import dataclass


@dataclass(frozen=True)
class AccessSettings:
    id: str
    hosts: frozenset[str]
    max_index_bytes: int = 3_000_000
    max_asset_bytes: int = 30_000_000


ACCESS = AccessSettings("fns.public_statistics", frozenset({
    "rmsp.nalog.ru", "www.nalog.gov.ru", "www.nalog.ru",
}))
SME_INDEX = "https://rmsp.nalog.ru/statistics.html"
SME_DATA = "https://rmsp.nalog.ru/statistics-proc.json"
LEGAL_INDEX = "https://www.nalog.gov.ru/rn77/related_activities/statistics_and_analytics/forms/"
