"""Editioned family registries; no executable parser or engine imports."""
from functools import lru_cache
from stratbox.core.registry.sources import source_documents
from .contracts import RosstatSourceSpec

@lru_cache(maxsize=1)
def list_rosstat_sources() -> tuple[RosstatSourceSpec, ...]:
    values = []
    for source in source_documents("rosstat"):
        record = source["publication"]
        if record["schema"] != "stratbox.rosstat.registry.v1" or source["publisher_id"] != "rosstat":
            raise ValueError("rosstat.registry_invalid")
        values.append(RosstatSourceSpec(
            source["series_id"], source["title"], record["landing_url"],
            record["profiles"]["discovery"], frozenset(source["formats"]),
            record["frequency_hint"],
        ))
    if len({value.series_id for value in values}) != len(values):
        raise ValueError("rosstat.catalog_duplicate")
    return tuple(values)


def get_rosstat_source(series_id: str) -> RosstatSourceSpec:
    for value in list_rosstat_sources():
        if value.series_id == series_id:
            return value
    raise ValueError("rosstat.series_unknown")
