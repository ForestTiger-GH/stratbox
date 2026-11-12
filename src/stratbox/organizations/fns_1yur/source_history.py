from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin

from .history import HistoryError
from .source import SourceError, allowed_url


MIN_DATE = date(2012, 1, 1)


PATHS = (
    "/files/docs/gosreg/",
    "/files/docs/svot/",
    "/html/sites/www.new.nalog.ru/docs/",
    "/html/sites/www.new.nalog.ru/docs/otchet/",
    "/html/sites/www.new.nalog.ru/docs/analit/",
    "/html/sites/www.new.nalog.ru/svod/",
    "/html/sites/www.new.nalog.ru/files/related_activities/statistics_and_analytics/forms/reg/",
    "/html/sites/www.new.nalog.ru/2023/related_activities/statistics_and_analytics/forms/",
)


DATE_RX = re.compile(r"(?<!\d)(0[1-9]|[12]\d|3[01])\.(0[1-9]|1[0-2])\.(20\d{2})(?!\d)")


MAX_SOURCE = 30_000_000


class ListParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth, self.description, self.links = 0, [], []
        self.href = None
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            if not self.depth:
                self.description, self.links = [], []
            self.depth += 1
        if tag == "a" and self.depth:
            self.href = dict(attrs).get("href", "")

    def handle_data(self, data):
        if self.depth:
            self.description.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append(self.href.strip())
            self.href = None
        if tag == "li" and self.depth:
            self.depth -= 1
            if not self.depth:
                self.items.append((" ".join(self.description), self.links[:]))


def releases_from_page(raw, page, *, missing=None, require_releases=True):
    parser = ListParser()
    parser.feed(raw.decode("utf-8-sig"))
    parser.close()
    result = {}
    for label, links in parser.items:
        matches = DATE_RX.findall(label)
        if len(matches) != 1 or "регистрации юридических лиц" not in label.lower():
            continue
        try:
            day = date(*map(int, reversed(matches[0])))
        except ValueError:
            raise HistoryError("SOURCE_DATE_BAD") from None
        if day < MIN_DATE or day.day != 1:
            continue
        candidates = []
        for href in links:
            asset = urljoin(page, href)
            try:
                allowed_url(asset, "source")
                candidates.append(asset)
            except SourceError:
                continue
        if not candidates:
            # Some historical month entries have no downloadable official XLS/RAR/ZIP.
            # Record the gap, but keep the independently verified other releases.
            if missing is not None:
                missing.add(day)
            continue
        if len(set(candidates)) != 1:
            raise HistoryError("SOURCE_ASSET_AMBIGUOUS:" + day.isoformat())
        if day in result and result[day] != candidates[0]:
            raise HistoryError("SOURCE_DATE_DUPLICATE")
        result[day] = candidates[0]
    if require_releases and not result:
        raise HistoryError("YEAR_RELEASES_NOT_FOUND")
    return result
