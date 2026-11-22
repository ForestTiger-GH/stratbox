"""Minfin page parsing, document-card dates, and source-asset qualification.

Publisher HTML is evidence: the captured page never proves global inventory coverage.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import date, datetime
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit
import re

from stratbox.shared.evidence import SourcePayload
from .contracts import Asset, PublicationIndex, SourceFamily
from .access import allowed_file, PAGE_MIMES

class _Anchors(HTMLParser):
    def __init__(self, max_links: int):
        super().__init__(convert_charrefs=True)
        self.max_links = max_links
        self.links: list[tuple[str, str]] = []
        self.current_href: str | None = None
        self.text: list[str] = []
        self.title: str = ""
        self.bad_base = False
        self.overflow = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag.lower() == "base":
            self.bad_base = True  # Do not allow untrusted HTML to change URL resolution.
        if tag.lower() == "a":
            self.current_href = values.get("href")
            self.text = []
            self.title = values.get("title") or ""

    def handle_data(self, data):
        if self.current_href is not None and sum(map(len, self.text)) < 4096:
            self.text.append(data[:4096])

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current_href is not None:
            if len(self.links) >= self.max_links:
                self.overflow = True
            else:
                self.links.append((self.current_href, (self.title.strip() or "".join(self.text).strip())[:2048]))
            self.current_href = None
            self.text = []
            self.title = ""


def discover_links(family: SourceFamily, index: SourcePayload, max_links: int = 2000) -> PublicationIndex:
    if type(max_links) is not int or not 1 <= max_links <= 5000:
        raise ValueError("minfin.index_limit_invalid")
    if index.media_type not in PAGE_MIMES or index.identity.size > 8 * 1024 * 1024:
        raise ValueError("minfin.index_invalid_media")
    if index.source_id not in {None, family.family_id + ".index"}:
        raise ValueError("minfin.index_wrong_source")
    try:
        html = index.data.decode(index.charset or "utf-8", errors="strict")
    except (UnicodeError, LookupError):
        raise ValueError("minfin.index_invalid_charset") from None
    if "\x00" in html or "\ufffd" in html:
        raise ValueError("minfin.index_invalid_charset")
    parser = _Anchors(max_links)
    parser.feed(html)
    parser.close()
    if parser.bad_base or parser.overflow:
        raise ValueError("minfin.index_untrusted_or_oversized")
    if not parser.links:
        raise ValueError("minfin.index_no_links")
    unique: dict[str, Asset] = {}
    rejected = 0
    for raw, label in parser.links:
        if not isinstance(raw, str) or len(raw) > 8192:
            rejected += 1
            continue
        url = urljoin(family.landing_url, unescape(raw.strip()))
        if not allowed_file(url):
            rejected += 1
            continue
        filename = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in family.formats:
            rejected += 1
            continue
        variants = tuple(v for v in family.variants if filename.casefold().startswith(v.prefix.casefold()) and filename.casefold().endswith(v.suffix.casefold()))
        if len(variants) > 1:
            raise ValueError("minfin.index_variant_overlap")
        variant = variants[0] if variants else None
        asset_id = variant.asset_id if variant else "file_" + sha256(urlsplit(url).path.encode()).hexdigest()[:24]
        asset = Asset(family.family_id, variant.source_id if variant else family.default_source_id,
                      asset_id, url, filename, ext, label,
                      "registered_variant" if variant else "unclassified", index.identity)
        unique[url] = asset
    assets = tuple(sorted(unique.values(), key=lambda x: (x.source_id, x.filename, x.url)))
    ambiguous_ids = tuple(sorted(asset_id for asset_id in {a.asset_id for a in assets}
                                 if sum(a.asset_id == asset_id for a in assets) > 1))
    # Keep ambiguous candidates visible; require explicit URL selection to acquire.
    return PublicationIndex(family.family_id, assets, index.identity, rejected_links=rejected,
                            ambiguous_asset_ids=ambiguous_ids)


def check_asset(asset: Asset, family: SourceFamily) -> None:
    if asset.family_id != family.family_id or not allowed_file(asset.url, extension=asset.format):
        raise ValueError("minfin.asset_forbidden")
    if unquote(urlsplit(asset.url).path.rsplit("/", 1)[-1]) != asset.filename:
        raise ValueError("minfin.asset_filename_mismatch")
    if asset.format not in family.formats or asset.index_identity.size <= 0:
        raise ValueError("minfin.asset_unqualified")
    matched = tuple(v for v in family.variants if asset.filename.casefold().startswith(v.prefix.casefold()) and asset.filename.casefold().endswith(v.suffix.casefold()))
    if len(matched) > 1:
        raise ValueError("minfin.asset_ambiguous")
    expected = matched[0] if matched else None
    if asset.source_id != (expected.source_id if expected else family.default_source_id):
        raise ValueError("minfin.asset_source_mismatch")
    expected_id = expected.asset_id if expected else "file_" + sha256(urlsplit(asset.url).path.encode()).hexdigest()[:24]
    if asset.asset_id != expected_id or asset.recognition != ("registered_variant" if expected else "unclassified"):
        raise ValueError("minfin.asset_identity_mismatch")


_DOCUMENT = re.compile(r"(?:[?&])id_(57|4)=([0-9]{1,16})(?:[^0-9]|$)")
_DATE = re.compile(r"^(Опубликовано|Изменено):\s*([0-3]?\d\.[01]?\d\.\d{4})$")


@dataclass(frozen=True, slots=True)
class CardAttachment:
    href: str
    label: str
    document_id: str | None
    published_on: date | None
    modified_on: date | None
    document_title: str


class _DocumentCards(HTMLParser):
    def __init__(self, maximum: int) -> None:
        super().__init__(convert_charrefs=True)
        self.maximum = maximum
        self.depth = 0
        self.card_depth: int | None = None
        self.card: dict | None = None
        self.text_target: str | None = None
        self.text_parts: list[str] = []
        self.results: list[CardAttachment] = []
        self.invalid_dates = False
        self.overflow = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        kind = tag.lower()
        if kind == "div":
            self.depth += 1
            if self.card is None and "document_card" in (attr.get("class") or "").split():
                self.card_depth = self.depth
                identifier = _DOCUMENT.search(attr.get("data-href") or "")
                self.card = {
                    "document_id": f"id_{identifier[1]}:{identifier[2]}" if identifier else None,
                    "published_on": None, "modified_on": None,
                    "document_title": "", "attachments": [],
                }
        if self.card is None:
            return
        classes = (attr.get("class") or "").split()
        if kind == "span" and "date" in classes:
            self.text_target, self.text_parts = "date", []
        elif kind == "a" and "document_title" in classes:
            self.card["document_title"] = (attr.get("title") or "").strip()[:2048]
        elif kind == "a" and "file_item" in classes:
            href = (attr.get("href") or "").strip()
            if href:
                self.card["attachments"].append((href, (attr.get("title") or "").strip()[:2048]))
                if len(self.card["attachments"]) > self.maximum:
                    self.overflow = True

    def handle_data(self, data: str) -> None:
        if self.text_target == "date" and sum(map(len, self.text_parts)) < 128:
            self.text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        kind = tag.lower()
        if kind == "span" and self.text_target == "date":
            raw = " ".join("".join(self.text_parts).split())
            if self.card is not None:
                match = _DATE.fullmatch(raw)
                if match:
                    try:
                        observed = datetime.strptime(match[2], "%d.%m.%Y").date()
                    except ValueError:
                        self.invalid_dates = True
                    else:
                        key = "published_on" if match[1] == "Опубликовано" else "modified_on"
                        previous = self.card[key]
                        if previous is not None and previous != observed:
                            self.invalid_dates = True
                        self.card[key] = observed
                elif raw.startswith(("Опубликовано:", "Изменено:")):
                    self.invalid_dates = True
            self.text_target, self.text_parts = None, []
        if kind == "div":
            if self.card is not None and self.depth == self.card_depth:
                for href, label in self.card["attachments"]:
                    self.results.append(CardAttachment(
                        href=href, label=label,
                        document_id=self.card["document_id"],
                        published_on=self.card["published_on"],
                        modified_on=self.card["modified_on"],
                        document_title=self.card["document_title"],
                    ))
                    if len(self.results) > self.maximum:
                        self.overflow = True
                self.card = None
                self.card_depth = None
                self.text_target = None
            self.depth = max(0, self.depth - 1)


def document_attachments(html: str, *, maximum: int = 2000) -> tuple[CardAttachment, ...]:
    """Recognize attachments with per-document date labels (not page-wide dates).

    A page may have other navigation anchors and an archive carousel. Items with
    no explicit 'Изменено' are returned with a nullable marker, never invented.
    """
    if not isinstance(html, str) or not 0 < maximum <= 5000:
        raise ValueError("minfin.document_cards.invalid_request")
    reader = _DocumentCards(maximum)
    reader.feed(html)
    reader.close()
    if reader.overflow:
        raise ValueError("minfin.document_cards.limit")
    if reader.invalid_dates:
        raise ValueError("minfin.document_cards.invalid_dates")
    return tuple(reader.results)


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
