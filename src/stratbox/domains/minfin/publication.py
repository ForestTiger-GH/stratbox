"""Read publisher *document cards* without using browser state or executable HTML.

This module owns only the source-specific HTML shape. It is deliberately separate
from transport, operation execution and durable update checkpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
import re


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