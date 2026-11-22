"""Canonical, automatically discovered root REGISTRY_*.yaml declarations.

The format deliberately uses YAML 1.2's JSON subset; Python's stdlib validates
source identities without importing any handler or optional format provider.
"""
from __future__ import annotations
from functools import lru_cache
from importlib import resources
import json
import re

from .contracts import SourceFamily, SourceProfileRefs, SourceSeries

_ID = re.compile(r"[a-z][a-z0-9_.-]{2,127}\Z")
_BASIS = frozenset({"ytd", "annual", "stock", "unknown"})
_FREQ = frozenset({"monthly", "quarterly", "annual", "unknown"})


def _identity(value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("minfin.registry.invalid_identity")
    return value


def _decode(data: bytes) -> SourceFamily:
    try:
        obj = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("minfin.registry.invalid_yaml") from None
    if not isinstance(obj, dict) or set(obj) != {
        "schema", "family_id", "publisher_id", "title", "profiles", "series"
    } or obj["schema"] != "stratbox.minfin.registry.v3" or obj["publisher_id"] != "minfin":
        raise ValueError("minfin.registry.invalid_shape")
    refs = obj["profiles"]
    if not isinstance(refs, dict) or set(refs) != {"acquisition", "discovery", "identification", "table", "metrics"}:
        raise ValueError("minfin.registry.invalid_profiles")
    profiles = SourceProfileRefs(*(_identity(refs[key]) for key in ("acquisition", "discovery", "identification", "table", "metrics")))
    items = obj["series"]
    if not isinstance(items, list) or not 1 <= len(items) <= 64:
        raise ValueError("minfin.registry.invalid_series")
    series = []
    family_id = _identity(obj["family_id"])
    if not family_id.startswith("minfin."):
        raise ValueError("minfin.registry.invalid_family")
    for item in items:
        if not isinstance(item, dict) or set(item) != {
            "source_id", "slot", "title", "periodicity", "basis", "kind"
        } or item["periodicity"] not in _FREQ or item["basis"] not in _BASIS or item["kind"] not in {"table", "document"}:
            raise ValueError("minfin.registry.invalid_series")
        identity = _identity(item["source_id"])
        if not identity.startswith(family_id + ".") or not isinstance(item["title"], str) or not item["title"].strip():
            raise ValueError("minfin.registry.invalid_series")
        if item["kind"] == "table" and (item["periodicity"] == "unknown" or item["basis"] == "unknown"):
            raise ValueError("minfin.registry.invalid_table_series")
        series.append(SourceSeries(identity, _identity(item["slot"]), item["title"],
                                   item["periodicity"], item["basis"], item["kind"]))
    if len({s.source_id for s in series}) != len(series) or len({s.slot for s in series}) != len(series):
        raise ValueError("minfin.registry.duplicate_series")
    if not isinstance(obj["title"], str) or not obj["title"].strip():
        raise ValueError("minfin.registry.invalid_title")
    return SourceFamily(family_id, obj["title"], profiles, tuple(series))


@lru_cache(maxsize=1)
def families() -> tuple[SourceFamily, ...]:
    root = resources.files("stratbox.domains.minfin")
    names = sorted(entry.name for entry in root.iterdir() if entry.is_file() and
                   entry.name.startswith("REGISTRY_") and entry.name.endswith(".yaml"))
    if not 1 <= len(names) <= 128 or any(not re.fullmatch(r"REGISTRY_[A-Z0-9_]+\.yaml", name) for name in names):
        raise ValueError("minfin.registry.invalid_inventory")
    result = tuple(_decode(root.joinpath(name).read_bytes()) for name in names)
    if len({fam.family_id for fam in result}) != len(result):
        raise ValueError("minfin.registry.duplicate_family")
    ids = [v for fam in result for v in (fam.default_source_id, *(s.source_id for s in fam.series))]
    if len(set(ids)) != len(ids):
        raise ValueError("minfin.registry.duplicate_source")
    return result


def family(family_id: str) -> SourceFamily:
    for item in families():
        if item.family_id == family_id:
            return item
    raise ValueError("minfin.registry.unknown_family")


def all_sources() -> tuple[str, ...]:
    return tuple(src for f in families() for src in (f.default_source_id, *(s.source_id for s in f.series)))


__all__ = ("families", "family", "all_sources")