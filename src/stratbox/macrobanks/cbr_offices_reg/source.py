from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit, unquote

from stratbox.base.net.contracts import public_https_parts

from .parser import CaptureError, clean, require


SOURCE_PAGE = "https://www.cbr.ru/statistics/bank_sector/lic/"


FILENAME = re.compile(r"DivisionsPerRegion_(\d{2})(\d{2})(\d{2})\.xlsx\Z", re.I)


LIMIT_HTML = 5_000_000


LIMIT_XLSX = 8_000_000


def url_date(raw):
    u = public_https_parts(raw)
    require(
        u.scheme == "https"
        and u.hostname in ("www.cbr.ru", "cbr.ru")
        and u.port in (None, 443)
        and not u.username
        and not u.password
        and not u.query
        and not u.fragment
        and u.path.startswith("/vfs/statistics/bank_system/"),
        "INVALID_SOURCE_URL",
    )
    m = FILENAME.fullmatch(unquote(u.path.rsplit("/", 1)[-1]))
    require(m is not None, "INVALID_XLSX_NAME")
    try:
        d = date(2000 + int(m[3]), int(m[2]), int(m[1]))
    except ValueError:
        raise CaptureError("INVALID_REPORT_DATE") from None
    require(d.day == 1 and d.year >= 2019, "INVALID_REPORT_DATE")
    return d


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.href = None
        self.text = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.text = []

    def handle_data(self, data):
        if self.href is not None:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, clean(" ".join(self.text))))
            self.href = None


def discover(html):
    parser = PageLinks()
    parser.feed(html)
    parser.close()
    found = {}
    for href, label in parser.links:
        u = urljoin(SOURCE_PAGE, href)
        if not FILENAME.fullmatch(unquote(urlsplit(u).path.rsplit("/", 1)[-1])):
            continue
        d = url_date(u)
        # The official link caption must agree with the date in the target filename.
        lab = re.search(r"(20\d{2})\s*г\.?:\s*на\s*(\d{2})\.(\d{2})", label, re.I)
        require(
            lab is not None
            and (int(lab[1]), int(lab[2]), int(lab[3])) == (d.year, d.day, d.month),
            "SOURCE_LINK_DATE_MISMATCH",
        )
        require(d not in found or found[d] == u, "SOURCE_DUPLICATE_REPORT_DATE")
        found[d] = u
    require(len(found) >= 1, "SOURCE_INDEX_INCOMPLETE")
    return dict(sorted(found.items()))
