"""Exact integer and publisher-code rules for historical 1-YUR tables."""

from decimal import Decimal

import re


REGION_RE = re.compile(r"[0-9]{2}\Z")


def check(condition, code):
    if not condition:
        raise ValueError(code)

def integer(value, what):
    if isinstance(value, bool):
        raise ValueError(what)
    if isinstance(value, (int, float, Decimal)):
        check(0 <= value <= 10**12 and value == int(value), what)
        return str(int(value))
    if (
        isinstance(value, str)
        and re.fullmatch(r"[0-9]{1,13}", value)
        and int(value) <= 10**12
    ):
        return str(int(value))
    raise ValueError(what)

def code(value, n):
    try:
        result = integer(value, "CODE_INVALID")
    except ValueError:
        return None
    return result.zfill(n) if len(result) <= n else None
