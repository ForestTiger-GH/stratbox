"""Bounded Ministry of Finance HTML discovery and evidence-based identification.

Parser extracts the publisher's document ID and date for each exact attachment.
A separate identification profile resolves series without the YAML knowing any
actual filename. Conflicts remain unresolved; they cannot trigger downloads.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import date, datetime
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import re
from urllib.parse import unquote, urljoin, urlsplit
from stratbox.shared.evidence import SourcePayload
from .contracts import Asset, PublicationIndex, SourceFamily
from .access import PAGE_MIMES, allowed_file
from .profiles import IdentificationProfile, PublicationProfile

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
            self.bad_base = True
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


def _unclassified_id(url: str) -> str:
    return "file_" + sha256(urlsplit(url).path.encode()).hexdigest()[:24]


def discover_links(family: SourceFamily, index: SourcePayload, max_links: int = 2000) -> PublicationIndex:
    """Discover exact publisher URLs without interpreting filenames prematurely."""
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
    found: dict[str, Asset] = {}
    rejected = 0
    for href, label in parser.links:
        if not isinstance(href, str) or len(href) > 8192:
            rejected += 1
            continue
        url = urljoin(family.landing_url, unescape(href.strip()))
        if not allowed_file(url):
            rejected += 1
            continue
        filename = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
        fmt = filename.rsplit(".", 1)[-1].lower()
        found[url] = Asset(family.family_id, family.default_source_id, _unclassified_id(url),
                           url, filename, fmt, label, "unclassified", index.identity)
    return PublicationIndex(family.family_id,
                            tuple(sorted(found.values(), key=lambda item: (item.filename, item.url))),
                            index.identity, rejected_links=rejected)


def enrich_index(index: PublicationIndex, html: str, landing_url: str, *,
                 profile: PublicationProfile) -> PublicationIndex:
    """Associate document-card evidence with its own attachment, never page-wide."""
    links = profile.parse_cards(html)
    if not links:
        return index
    by_url = {}
    for link in links:
        uri = urljoin(landing_url, unescape(link.href.strip()))
        previous = by_url.get(uri)
        if previous is not None and previous != link:
            raise ValueError("minfin.index.conflicting_document_evidence")
        by_url[uri] = link
    return replace(index, assets=tuple(
        item if (card := by_url.get(item.url)) is None else replace(
            item, document_id=card.document_id, published_on=card.published_on,
            modified_on=card.modified_on, document_title=card.document_title)
        for item in index.assets
    ))


def identify_asset(asset: Asset, family: SourceFamily, profile: IdentificationProfile) -> Asset:
    if asset.family_id != family.family_id or not allowed_file(asset.url, extension=asset.format):
        raise ValueError("minfin.asset_forbidden")
    if unquote(urlsplit(asset.url).path.rsplit("/", 1)[-1]) != asset.filename:
        raise ValueError("minfin.asset_filename_mismatch")
    slot, recognition = profile.identify(asset.document_id, asset.filename, asset.format)
    if slot is None:
        return replace(asset, source_id=family.default_source_id,
                       asset_id=_unclassified_id(asset.url), recognition=recognition)
    series = family.slot(slot)
    rule = profile.rule(slot)
    if series.kind == "table" and series.periodicity == "unknown":
        raise ValueError("minfin.profile.invalid_series")
    return replace(asset, source_id=series.source_id, asset_id=rule.asset_id,
                   recognition=recognition)


def identify_index(index: PublicationIndex, family: SourceFamily,
                   profile: IdentificationProfile) -> PublicationIndex:
    if index.family_id != family.family_id:
        raise ValueError("minfin.index_family_mismatch")
    assets = tuple(identify_asset(asset, family, profile) for asset in index.assets)
    duplicates: dict[str, int] = {}
    for asset in assets:
        if asset.recognition == "registered_variant":
            duplicates[asset.asset_id] = duplicates.get(asset.asset_id, 0) + 1
    ambiguous = set(asset_id for asset_id, count in duplicates.items() if count > 1)
    for asset in assets:
        if asset.recognition == "conflicted":
            for rule in profile.rules:
                if rule.document_id == asset.document_id or rule.matches_filename(asset.filename):
                    ambiguous.add(rule.asset_id)
    return replace(index, assets=tuple(sorted(assets, key=lambda x: (x.source_id, x.filename, x.url))),
                   ambiguous_asset_ids=tuple(sorted(ambiguous)))


def check_asset(asset: Asset, family: SourceFamily, profile: IdentificationProfile) -> None:
    if asset.index_identity.size <= 0 or asset.recognition == "conflicted":
        raise ValueError("minfin.asset_ambiguous")
    expected = identify_asset(asset, family, profile)
    if (expected.source_id, expected.asset_id, expected.recognition) != (
        asset.source_id, asset.asset_id, asset.recognition
    ):
        raise ValueError("minfin.asset_identity_mismatch")


__all__ = ("discover_links", "enrich_index", "identify_asset", "identify_index",
           "check_asset", "document_attachments", "CardAttachment")