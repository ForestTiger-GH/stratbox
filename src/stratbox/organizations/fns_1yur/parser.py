"""Form 1-YUR workbook constants and exact source-cell decoders."""

from __future__ import annotations

import re

from .source import check, SourceError


OLE = bytes.fromhex("D0CF11E0A1B11AE1")


MAX_XLS = 16_000_000
REGION_RE = re.compile(r"[0-9]{2}\Z")


def integer(value, what):
    if isinstance(value, bool):
        raise SourceError(what)
    if isinstance(value, (int, float)):
        check(0 <= value <= 10**12 and value == int(value), what)
        return str(int(value))
    if (
        isinstance(value, str)
        and re.fullmatch(r"[0-9]{1,13}", value)
        and int(value) <= 10**12
    ):
        return str(int(value))
    raise SourceError(what)


def code(value, n):
    try:
        result = integer(value, "CODE_INVALID")
    except SourceError:
        return None
    return result.zfill(n) if len(result) <= n else None
