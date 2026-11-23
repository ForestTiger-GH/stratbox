"""Logical publisher declarations, independent of routes and executable code."""
from functools import lru_cache
from stratbox.core.registry.sources import source_documents

from .contracts import SourceSeries




@lru_cache(maxsize=1)
def _sources():
    result = []
    for document in source_documents("cbr"):
        value = dict(document["publication"])
        for field in ("series_id", "family_id", "title", "formats", "issue_model"):
            value[field] = document[field]
        value["formats"] = tuple(value["formats"])
        item = SourceSeries(**value)
        if not item.family_id.startswith("cbr.") or not item.series_id.startswith(item.family_id + "."):
            raise ValueError("cbr.registry.series_family_mismatch")
        result.append(item)
    if len({item.series_id for item in result}) != len(result):
        raise ValueError("cbr.registry.duplicate_series")
    return tuple(result)


def families():
    return tuple(sorted({item.family_id for item in _sources()}))


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
