"""Domain-local, immutable catalog of source descriptions.

REGISTRY_*.yaml are deliberately YAML 1.2's JSON subset so the public core
retains its zero-dependency installation. This is not a second operation runner.
"""
from __future__ import annotations

from functools import lru_cache
from importlib import resources
import json
import re

from .models import SourceFamily, Variant

_NAMES = ("FEDBUD", "CONBUD", "SUBBUD", "NWF")
_ID = re.compile(r"[a-z][a-z0-9_.-]{2,127}\Z")
_FORMATS = frozenset({"xlsx", "xls", "xlsm", "csv", "zip", "pdf", "doc", "docx"})
_OPERATIONS = {"discover", "acquire", "extract", "compare", "render", "map", "readable", "capture", "serialize", "read_extract", "validate", "plan_updates", "build_flake", "render_flake", "summarize", "prepare_notice"}


def _identity(value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("minfin.registry.invalid_identity")
    return value


def _decode(data: bytes) -> SourceFamily:
    try:
        obj = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise ValueError("minfin.registry.invalid_yaml") from None
    if not isinstance(obj, dict) or set(obj) != {
        "schema", "family_id", "publisher_id", "title", "landing_url", "frequency",
        "formats", "default_source_id", "variants", "operations",
    } or obj["schema"] != "stratbox.minfin.registry.v1" or obj["publisher_id"] != "minfin":
        raise ValueError("minfin.registry.invalid_shape")
    from .source import allowed_page
    if not allowed_page(obj["landing_url"]):
        raise ValueError("minfin.registry.invalid_page")
    formats = obj["formats"]
    if not isinstance(formats, list) or not formats or any(x not in _FORMATS for x in formats) or len(formats) != len(set(formats)):
        raise ValueError("minfin.registry.invalid_formats")
    variants = []
    if not isinstance(obj["variants"], list):
        raise ValueError("minfin.registry.invalid_variants")
    for v in obj["variants"]:
        if not isinstance(v, dict) or set(v) != {"source_id", "asset_id", "title", "prefix", "suffix", "basis_hint", "periodicity"}:
            raise ValueError("minfin.registry.invalid_variant")
        for key in ("prefix", "suffix", "title"):
            if not isinstance(v[key], str) or not v[key] or len(v[key]) > 256:
                raise ValueError("minfin.registry.invalid_variant")
        if "/" in v["prefix"] or "/" in v["suffix"] or "\\" in v["suffix"]:
            raise ValueError("minfin.registry.invalid_variant")
        if v["basis_hint"] not in {"ytd", "annual", "stock", "unknown"}:
            raise ValueError("minfin.registry.invalid_basis")
        if v["periodicity"] not in {"monthly", "quarterly", "annual", "unknown"}:
            raise ValueError("minfin.registry.invalid_periodicity")
        variants.append(Variant(_identity(v["source_id"]), _identity(v["asset_id"]), v["title"], v["prefix"], v["suffix"], v["basis_hint"], v["periodicity"]))
    if len({v.asset_id for v in variants}) != len(variants) or len({v.source_id for v in variants}) != len(variants):
        raise ValueError("minfin.registry.duplicate_variant")
    operations = obj["operations"]
    if not isinstance(operations, dict) or not operations or set(operations) - _OPERATIONS:
        raise ValueError("minfin.registry.invalid_operations")
    for kind, operation_id in operations.items():
        if not isinstance(kind, str) or not isinstance(operation_id, str) or not operation_id.startswith("minfin."):
            raise ValueError("minfin.registry.invalid_operation")
    if not isinstance(obj["title"], str) or not obj["title"].strip() or not isinstance(obj["frequency"], str):
        raise ValueError("minfin.registry.invalid_shape")
    return SourceFamily(
        _identity(obj["family_id"]), obj["title"], obj["landing_url"], obj["frequency"],
        tuple(formats), _identity(obj["default_source_id"]), tuple(variants),
        tuple(sorted(operations.items())),
    )


@lru_cache(maxsize=1)
def families() -> tuple[SourceFamily, ...]:
    root = resources.files("stratbox.domains.minfin")
    result = tuple(_decode(root.joinpath(f"REGISTRY_{name}.yaml").read_bytes()) for name in _NAMES)
    if len({family.family_id for family in result}) != len(result):
        raise ValueError("minfin.registry.duplicate_family")
    ids = [value for item in result for value in (item.default_source_id, *(v.source_id for v in item.variants))]
    if len(set(ids)) != len(ids):
        raise ValueError("minfin.registry.duplicate_source")
    return result


def family(family_id: str) -> SourceFamily:
    for item in families():
        if item.family_id == family_id:
            return item
    raise ValueError("minfin.registry.unknown_family")


def all_sources() -> tuple[str, ...]:
    return tuple(source for f in families() for source in (f.default_source_id, *(v.source_id for v in f.variants)))


__all__ = ("families", "family", "all_sources")