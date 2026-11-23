"""Automatically discovered declarations of logical report sources.

Registries use the JSON subset of YAML 1.2. Delivery locations and executable
callbacks belong to runtime requests and registered profiles respectively.
"""
from __future__ import annotations

from functools import lru_cache
from stratbox.core.registry.sources import publication_families
import json
import re

from .contracts import ProfileRefs, SourceFamily, SourceSeries

_ID = re.compile(r"[a-z][a-z0-9_.-]{2,127}\Z")
_PROFILE_KEYS = ("discovery", "identification", "selection", "naming")


def _identity(value: object) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("frg.registry.invalid_identity")
    return value


def _title(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError("frg.registry.invalid_title")
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("frg.registry.duplicate_key")
        result[key] = value
    return result


def _decode(data: bytes) -> SourceFamily:
    if not isinstance(data, bytes) or len(data) > 256 * 1024:
        raise ValueError("frg.registry.invalid_yaml")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("frg.registry.invalid_yaml") from None
    if not isinstance(value, dict) or set(value) != {
        "schema", "family_id", "publisher_id", "title", "profiles", "series"
    } or value["schema"] != "stratbox.frg.registry.v1" or value["publisher_id"] != "frank_rg":
        raise ValueError("frg.registry.invalid_shape")
    family_id = _identity(value["family_id"])
    if not family_id.startswith("frg."):
        raise ValueError("frg.registry.invalid_family")
    refs = value["profiles"]
    if not isinstance(refs, dict) or set(refs) != set(_PROFILE_KEYS):
        raise ValueError("frg.registry.invalid_profiles")
    profiles = ProfileRefs(*(_identity(refs[key]) for key in _PROFILE_KEYS))
    items = value["series"]
    if not isinstance(items, list) or not 1 <= len(items) <= 128:
        raise ValueError("frg.registry.invalid_series")
    series = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {
            "source_id", "slot", "title", "periodicity", "kind"
        } or item["periodicity"] not in ("snapshot", "month_week") or item["kind"] != "workbook":
            raise ValueError("frg.registry.invalid_series")
        source_id = _identity(item["source_id"])
        if not source_id.startswith(family_id + "."):
            raise ValueError("frg.registry.invalid_source")
        series.append(SourceSeries(source_id, _identity(item["slot"]), _title(item["title"]),
                                   item["periodicity"], item["kind"]))
    if len({item.source_id for item in series}) != len(series) or len({item.slot for item in series}) != len(series):
        raise ValueError("frg.registry.duplicate_series")
    return SourceFamily(family_id, _title(value["title"]), profiles, tuple(series))


@lru_cache(maxsize=1)
def families() -> tuple[SourceFamily, ...]:
    declarations = publication_families("frank_rg", series_fields=(("source_id", "series_id"), ("title", "title")))
    result = tuple(_decode(json.dumps(value).encode("utf-8")) for value in declarations)
    if len({item.family_id for item in result}) != len(result):
        raise ValueError("frg.registry.duplicate_family")
    sources = [item.source_id for family in result for item in family.series]
    if len(sources) != len(set(sources)):
        raise ValueError("frg.registry.duplicate_source")
    return result


def family(family_id: str) -> SourceFamily:
    for item in families():
        if item.family_id == family_id:
            return item
    raise ValueError("frg.registry.unknown_family")


def source(source_id: str) -> SourceSeries:
    for parent in families():
        for item in parent.series:
            if item.source_id == source_id:
                return item
    raise ValueError("frg.registry.unknown_source")


def all_sources() -> tuple[str, ...]:
    return tuple(item.source_id for parent in families() for item in parent.series)


__all__ = ("families", "family", "source", "all_sources")
