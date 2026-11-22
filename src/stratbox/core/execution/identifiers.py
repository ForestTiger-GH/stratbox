"""Bounded semantic identifiers shared by execution contracts and descriptions."""

import re

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", re.ASCII)


def safe_token(value: str) -> str:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError("Expected a bounded identifier")
    return value
