"""Logical publisher declarations, independent of routes and executable code."""
from functools import lru_cache
from stratbox.core.registry.sources import publication_families

from .contracts import SourceSeries




@lru_cache(maxsize=1)
def _sources():
    result = []
    for document in publication_families("cbr", series_fields=(("series_id", "series_id"), ("family_id", "family_id"), ("title", "title"), ("formats", "formats"), ("issue_model", "issue_model"))):
        if (set(document) != {"schema_version", "family_id", "series"}
                or document["schema_version"] != 1 or not document["family_id"].startswith("cbr.")):
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
