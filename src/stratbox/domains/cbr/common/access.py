"""Shared publisher request scope; HTTP execution belongs to the core."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PublisherAccess:
    hosts: tuple[str, ...]
    source_roots: tuple[str, ...]
    max_response_bytes: int
    deadline_seconds: int


CBR_ACCESS = PublisherAccess(
    ("www.cbr.ru", "cbr.ru"),
    ("/vfs/", "/content/document/file/", "/collection/collection/file/", "/statistics/", "/banking_sector/", "/analytics/"),
    64 * 1024 * 1024,
    60,
)
