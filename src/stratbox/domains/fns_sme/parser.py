"""Source validation for regional SME register releases."""

from __future__ import annotations

from datetime import date, datetime
from html.parser import HTMLParser
import json
import re


COLUMNS = (
    "region_code",
    "region_name",
    "total",
    "ul_micro",
    "ul_small",
    "ul_medium",
    "ip_micro",
    "ip_small",
    "ip_medium",
)


SOURCE_COLUMNS = (
    "ssrf",
    "name",
    "cnt_total",
    "cnt_ul_micro",
    "cnt_ul_mini",
    "cnt_ul_normal",
    "cnt_ip_micro",
    "cnt_ip_mini",
    "cnt_ip_normal",
)


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


def counter(value):
    require(
        type(value) is int
        and 0 <= value < 10**18
        or isinstance(value, str)
        and bool(re.fullmatch(r"(0|[1-9][0-9]{0,17})", value)),
        "COUNT_NOT_NONNEGATIVE_INTEGER",
    )
    # The JSON endpoint publishes some years as decimal strings, others as JSON integers.
    return str(value)


def published_date(value):
    require(
        isinstance(value, str) and re.fullmatch(r"\d\d\.\d\d\.20\d\d 00:00:00", value),
        "SOURCE_DATE_FORMAT_CHANGED",
    )
    return parse_date(value[:10])


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _invalid_constant(_):
    raise FnsError("JSON_NONFINITE_NUMBER")


def decode_snapshot(blob, d):
    try:
        decoded = json.loads(
            blob.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_constant,
        )
    except (UnicodeError, ValueError, RecursionError):
        raise FnsError("JSON_INVALID") from None
    require(
        isinstance(decoded, list) and 80 <= len(decoded) <= 200, "SOURCE_ROWS_INVALID"
    )
    rows = {}
    levels = {0: 0, 1: 0, 2: 0}
    national = None
    for item in decoded:
        require(isinstance(item, dict), "SOURCE_ITEM_NOT_OBJECT")
        require(published_date(item.get("stat_date")) == d, "SOURCE_DATE_MISMATCH")
        level = item.get("cnt_level")
        require(type(level) is int and level in levels, "SOURCE_LEVEL_INVALID")
        levels[level] += 1
        if level == 2:
            require(
                national is None and item.get("cnt_name") == "Российская Федерация",
                "NATIONAL_ROW_INVALID",
            )
            national = item
            continue
        if level == 1:
            continue
        code = item.get("ssrf")
        label = item.get("name")
        require(
            isinstance(code, str) and re.fullmatch(r"[0-9]{1,3}", code),
            "REGION_CODE_INVALID",
        )
        require(
            isinstance(label, str)
            and bool(label.strip())
            and isinstance(item.get("cnt_name"), str)
            and bool(item.get("cnt_name").strip())
            and not any(ord(ch) < 32 for ch in label),
            "REGION_NAME_INVALID",
        )
        require(code not in rows, "REGION_DUPLICATE")
        vals = [counter(item.get(key)) for key in SOURCE_COLUMNS[2:]]
        require(
            int(vals[0])
            == int(counter(item.get("cnt_ul_total")))
            + int(counter(item.get("cnt_ip_total"))),
            "SOURCE_TOTAL_INCONSISTENT",
        )
        require(
            int(counter(item.get("cnt_ul_total")))
            == sum(int(vals[i]) for i in (1, 2, 3)),
            "SOURCE_UL_INCONSISTENT",
        )
        require(
            int(counter(item.get("cnt_ip_total")))
            == sum(int(vals[i]) for i in (4, 5, 6)),
            "SOURCE_IP_INCONSISTENT",
        )
        rows[code] = (code, label, *vals)
    require(
        levels[2] == 1 and levels[1] >= 8 and 80 <= levels[0] <= 120,
        "SOURCE_COVERAGE_INVALID",
    )
    require(
        national is not None
        and int(counter(national.get("cnt_total")))
        == int(counter(national.get("cnt_ul_total")))
        + int(counter(national.get("cnt_ip_total"))),
        "SOURCE_NATIONAL_TOTAL_INVALID",
    )
    return rows
