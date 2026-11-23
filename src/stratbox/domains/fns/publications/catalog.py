"""Validated declarations for the two independent FNS publication families."""
from functools import lru_cache
from importlib.resources import files
import json

from .contracts import SourceSeries


@lru_cache(maxsize=1)
def _catalog():
    root = files("stratbox.domains.fns")
    index = json.loads(root.joinpath("REGISTRY_FAMILIES.yaml").read_text(encoding="utf-8"))
    if index["schema_version"] != 1 or index["domain_id"] != "fns":
        raise ValueError("fns.registry.invalid")
    result = []
    for family in index["families"]:
        document = json.loads(root.joinpath(family["registry"]).read_text(encoding="utf-8"))
        if document["schema_version"] != 1 or document["family_id"] != family["family_id"]:
            raise ValueError("fns.registry.family_mismatch")
        for item in document["series"]:
            value = dict(item)
            value["formats"] = tuple(value["formats"])
            series = SourceSeries(**value)
            if series.family_id != family["family_id"]:
                raise ValueError("fns.registry.series_family_mismatch")
            result.append(series)
    if len({item.series_id for item in result}) != len(result):
        raise ValueError("fns.registry.duplicate_series")
    return tuple(result)


def all_sources(family_id=None):
    if family_id is not None and family_id not in families():
        raise ValueError("fns.registry.family_unknown")
    return tuple(item for item in _catalog() if family_id is None or item.family_id == family_id)


def families():
    return tuple(dict.fromkeys(item.family_id for item in _catalog()))


def source(series_id):
    for item in _catalog():
        if item.series_id == series_id:
            return item
    raise ValueError("fns.registry.series_unknown")
