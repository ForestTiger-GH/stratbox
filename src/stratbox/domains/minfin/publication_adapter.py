"""Attach publisher document-card evidence to registered source candidates."""
from __future__ import annotations

from dataclasses import replace
from html import unescape
from urllib.parse import urljoin

from .models import PublicationIndex
from .publication import document_attachments


def enrich_index(index: PublicationIndex, html: str, landing_url: str) -> PublicationIndex:
    links = document_attachments(html)
    if not links:
        # Non-card/synthetic page: keep discovered links but leave all dates unknown.
        return index
    by_url = {}
    for link in links:
        uri = urljoin(landing_url, unescape(link.href.strip()))
        previous = by_url.get(uri)
        if previous is not None and previous != link:
            raise ValueError("minfin.index.conflicting_document_evidence")
        by_url[uri] = link
    found = []
    for asset in index.assets:
        card = by_url.get(asset.url)
        found.append(asset if card is None else replace(
            asset, document_id=card.document_id,
            published_on=card.published_on,
            modified_on=card.modified_on,
            document_title=card.document_title,
        ))
    return replace(index, assets=tuple(found))