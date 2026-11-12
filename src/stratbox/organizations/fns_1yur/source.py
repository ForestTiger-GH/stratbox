"""Official publication pages and report links."""

from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, unquote

from stratbox.base.net.contracts import public_https_parts


PAGES = {
    2026: "16601803",
    2025: "15764462",
    2024: "14414858",
    2023: "13134463",
    2022: "11892431",
    2021: "10553558",
    2020: "9558929",
    2019: "8376083",
    2018: "7243238",
    2017: "6427754",
    2016: "5953348",
    2015: "5404042",
    2014: "4558837",
    2013: "4161934",
    2012: "4171842",
}


BASE = (
    "https://www.nalog.gov.ru/rn77/related_activities/statistics_and_analytics/forms/"
)


DATE_RE = re.compile(
    r"(?<!\d)(0[1-9]|[12]\d|3[01])[./](0[1-9]|1[0-2])[./](20\d{2})(?!\d)"
)


MAX_HTML = 4_000_000


class SourceError(Exception):
    """Publisher, archive, schema, or evidence inconsistency."""


def check(value, reason):
    if not value:
        raise SourceError(reason)


def page_url(year):
    check(year in PAGES, "YEAR_PAGE_NOT_REVIEWED")
    return BASE + PAGES[year] + "/"


def allowed_url(url, kind):
    from .source_history import PATHS

    try:
        parts = public_https_parts(url)
    except (TypeError, ValueError):
        raise SourceError("SOURCE_HOST_INVALID") from None
    check(
        parts.hostname in ("www.nalog.gov.ru", "www.nalog.ru") and "?" not in url,
        "SOURCE_HOST_INVALID",
    )
    path = unquote(parts.path)
    if kind == "page":
        check(
            re.fullmatch(
                r"/rn77/related_activities/statistics_and_analytics/forms/(?:[0-9]+/)?",
                path,
            ),
            "SOURCE_PAGE_PATH_INVALID",
        )
    else:
        check(
            path.lower().endswith((".zip", ".rar", ".xls", ".xlsx"))
            and (
                any(path.startswith(prefix) for prefix in PATHS)
                or path.startswith(
                    "/rn77/related_activities/statistics_and_analytics/forms/reg/"
                )
            ),
            "SOURCE_ASSET_PATH_INVALID",
        )
    return url


class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.entries = []
        self.href = None
        self.words = []
        self.recent = ""
        self.context = ""

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.href = dict(attrs).get("href", "")
            self.context = self.recent[-240:]
            self.words = []

    def handle_data(self, data):
        self.recent = (self.recent + data)[-500:]
        if self.href is not None:
            self.words.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.href is not None:
            self.entries.append((self.href, self.context + " " + "".join(self.words)))
            self.href = None


def extract_releases(html, page):
    parser = AnchorParser()
    parser.feed(html.decode("utf-8-sig"))
    parser.close()
    found = {}
    for href, label in parser.entries:
        url = urljoin(page, href.strip())
        try:
            allowed_url(url, "source")
        except SourceError:
            continue
        dates = DATE_RE.findall(label)
        if not dates:
            continue
        # The FNS link can say only 'Details'; the date precedes the anchor.
        day, month, year = map(int, dates[-1])
        try:
            d = date(year, month, day)
        except ValueError:
            raise SourceError("SOURCE_DATE_INVALID") from None
        check(day == 1, "SOURCE_REFERENCE_DAY_UNEXPECTED")
        if d in found and found[d] != url:
            raise SourceError("DUPLICATE_REFERENCE_DATE_LINK")
        found[d] = url
    check(found, "SOURCE_RELEASE_LINKS_MISSING")
    return found


def discover_year_pages(html):
    """Find explicitly linked future report pages in FNS's official forms index."""
    parser = AnchorParser()
    parser.feed(html.decode("utf-8-sig"))
    parser.close()
    result = {}
    for href, label in parser.entries:
        match = re.findall(
            r"1\s*[-–]\s*ЮР\W+(20\d{2})\s*год", label, flags=re.IGNORECASE
        )
        if not match:
            continue
        year = int(match[-1])
        url = urljoin(BASE, href)
        try:
            allowed_url(url, "page")
        except SourceError:
            continue
        check(url != BASE, "YEAR_INDEX_LINK_NOT_REPORT")
        if year in result and result[year] != url:
            raise SourceError("YEAR_PAGE_AMBIGUOUS")
        result[year] = url
    return result
