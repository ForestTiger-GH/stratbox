"""Extract literal anchors before applying any publisher-specific qualification."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin


@dataclass(frozen=True, slots=True)
class PageLink:
    raw_href: str
    url: str
    label_literal: str
    position: int


class _Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active: list[object] | None = None
        self.links: list[tuple[str, str]] = []
        self.base: str | None = None

    def handle_starttag(self, tag, attrs):
        pairs = dict(attrs)
        if tag.lower() == "base" and self.base is None:
            self.base = pairs.get("href")
        if tag.lower() == "a" and self.active is None and pairs.get("href"):
            self.active = [pairs["href"], []]

    def handle_data(self, data):
        if self.active is not None:
            self.active[1].append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.active is not None:
            href, pieces = self.active
            self.links.append((href, "".join(pieces)))
            self.active = None


def parse_page_links(html: str, page_url: str, allow_base) -> tuple[PageLink, ...]:
    if not isinstance(html, str) or len(html) > 10 * 1024 * 1024:
        raise ValueError("rosstat.html_limit")
    parser = _Anchors()
    parser.feed(html)
    parser.close()
    base = page_url
    if parser.base is not None:
        candidate = urljoin(page_url, parser.base)
        if not allow_base(candidate):
            raise ValueError("rosstat.html_base_forbidden")
        base = candidate
    return tuple(
        PageLink(href, urljoin(base, href), label, index)
        for index, (href, label) in enumerate(parser.links)
    )
