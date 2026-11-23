"""Logical publisher declarations, independent of routes and executable code."""
from functools import lru_cache
from importlib.resources import files
import json

from .contracts import SourceSeries

_FAMILIES = (
    "reporting_forms", "corporate_lending", "household_lending", "funding",
    "project_finance", "service_network", "household_finance", "monetary_statistics",
    "banking_sector_structure", "securities", "external_debt", "exchange_rates",
)


@lru_cache(maxsize=1)
def _sources():
    result = []
    for name in _FAMILIES:
        document = json.loads(files("stratbox.domains.cbr").joinpath(
            f"REGISTRY_{name.upper()}.yaml").read_text(encoding="utf-8"))
        if (set(document) != {"schema_version", "family_id", "series"}
                or document["schema_version"] != 1 or document["family_id"] != "cbr." + name):
            raise ValueError("cbr.registry.family_invalid")
        for declaration in document["series"]:
            value = dict(declaration)
            value["formats"] = tuple(value["formats"])
            item = SourceSeries(**value)
            if item.family_id != document["family_id"] or not item.series_id.startswith(item.family_id + "."):
                raise ValueError("cbr.registry.series_family_mismatch")
            result.append(item)
    if len({item.series_id for item in result}) != len(result):
        raise ValueError("cbr.registry.duplicate_series")
    return tuple(result)


def families():
    return tuple("cbr." + name for name in _FAMILIES)


def all_sources(family_id=None):
    if family_id is not None and family_id not in families():
        raise ValueError("cbr.registry.family_unknown")
    return tuple(item for item in _sources() if family_id is None or item.family_id == family_id)


def source(series_id):
    for item in _sources():
        if item.series_id == series_id:
            return item
    raise ValueError("cbr.registry.series_unknown")


FORM_CODES = tuple(item.series_id.rsplit(".f", 1)[1]
                   for item in all_sources("cbr.reporting_forms"))
