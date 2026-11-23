"""SME publication dates, index discovery and source admission constants."""
from datetime import date, datetime
from html.parser import HTMLParser
import re

LIMIT_HTML = 3_000_000


LIMIT_JSON = 4_000_000


DATE_VALUE = re.compile(r"\d{2}\.\d{2}\.20\d{2}\Z")


class FnsError(Exception):
    """Source, schema, or publication contract violation."""


def require(condition, code):
    if not condition:
        raise FnsError(code)


def parse_date(value):
    try:
        result = datetime.strptime(value, "%d.%m.%Y").date()
    except (TypeError, ValueError):
        raise FnsError("DATE_INVALID") from None
    require(result >= date(2016, 8, 1), "DATE_OUT_OF_RANGE")
    require(result.year <= 2099, "DATE_OUT_OF_RANGE")
    return result


def format_source_date(d):
    return d.strftime("%d.%m.%Y")


class DateOptions(HTMLParser):
    def __init__(self):
        super().__init__()
        self.dates = set()

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "option":
            return
        value = dict(attrs).get("value", "")
        if DATE_VALUE.fullmatch(value):
            self.dates.add(parse_date(value))


def discover_dates(html):
    try:
        page = html.decode("utf-8")
    except UnicodeDecodeError:
        raise FnsError("HTML_NOT_UTF8") from None
    parser = DateOptions()
    parser.feed(page)
    parser.close()
    dates = sorted(parser.dates)
    require(len(dates) >= 2, "SOURCE_DATES_UNAVAILABLE")
    require(dates[0] == date(2016, 8, 1), "SOURCE_DATES_START_UNEXPECTED")
    return dates
