"""Publication evidence retained independently of original bytes and tables."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from hashlib import sha256

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .contracts import Asset


@dataclass(frozen=True, slots=True)
class PublicationContext:
    series_id: str
    issue_id: str
    asset_id: str
    published_on: date | None = None
    modified_on: date | None = None
    document_id: str | None = None
    source_url: str | None = None

    def __post_init__(self):
        if any(not isinstance(x, str) or not x.strip() or len(x) > 2048
               for x in (self.series_id, self.issue_id, self.asset_id)):
            raise ValueError("minfin.publication_context_invalid")
        if any(x is not None and type(x) is not date for x in (self.published_on, self.modified_on)):
            raise ValueError("minfin.publication_context_invalid")
        if any(x is not None and (not isinstance(x, str) or not x or len(x) > 8192)
               for x in (self.document_id, self.source_url)):
            raise ValueError("minfin.publication_context_invalid")


def context_for(asset: Asset) -> PublicationContext:
    # An undated attachment remains an explicitly undated publication, rather
    # than acquiring a fabricated reporting period from the acquisition clock.
    issue = ("document-" + sha256(asset.document_id.encode("utf-8")).hexdigest()) if asset.document_id else (
        asset.published_on.isoformat() if asset.published_on is not None else "undated-" + asset.asset_id)
    return PublicationContext(asset.source_id, issue, asset.asset_id, asset.published_on,
                              asset.modified_on, asset.document_id, asset.url)


def context_document(value: PublicationContext | None):
    if value is None:
        return None
    return {key: item.isoformat() if isinstance(item, date) else item for key, item in asdict(value).items()}


def context_from_document(value) -> PublicationContext | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {
        "series_id", "issue_id", "asset_id", "published_on", "modified_on", "document_id", "source_url",
    }:
        raise ValueError("minfin.publication_context_invalid")
    fields = dict(value)
    for key in ("published_on", "modified_on"):
        if fields[key] is not None:
            fields[key] = date.fromisoformat(fields[key])
    return PublicationContext(**fields)
