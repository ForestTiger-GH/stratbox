"""Immutable byte identities and deterministic canonical manifest encoding."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import re
from typing import Mapping

_DIGEST = re.compile(r"[0-9a-f]{64}", re.ASCII)

@dataclass(frozen=True, slots=True)
class ByteIdentity:
    sha256: str
    size: int

    def __post_init__(self) -> None:
        if type(self.size) is not int or not _DIGEST.fullmatch(self.sha256) or self.size < 0:
            raise ValueError("Invalid byte identity")

    @classmethod
    def of(cls, data: bytes) -> ByteIdentity:
        return cls(sha256(data).hexdigest(), len(data))



def _canonical(value: object) -> object:
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            raise ValueError("Manifest timestamps require a timezone")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal) and value.is_finite():
        return format(value, "f")
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, Mapping) and all(isinstance(key, str) for key in value):
        return {key: _canonical(item) for key, item in value.items()}
    raise TypeError("Unsupported manifest value")


def canonical_manifest_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        _canonical(value),
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


