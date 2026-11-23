"""Editioned family registries; no executable parser or engine imports."""
from functools import lru_cache
from importlib.resources import files
import json
from .contracts import RosstatSourceSpec

_REGISTRIES = (
    "REGISTRY_SOCIOECONOMIC_RUSSIA.yaml", "REGISTRY_SOCIOECONOMIC_REGIONS.yaml",
    "REGISTRY_SHORT_TERM_INDICATORS.yaml", "REGISTRY_POPULATION_MUNICIPALITIES.yaml",
)

@lru_cache(maxsize=1)
def list_rosstat_sources() -> tuple[RosstatSourceSpec, ...]:
    values = []
    for name in _REGISTRIES:
        record = json.loads(files("stratbox.domains.rosstat").joinpath(name).read_text(encoding="utf-8"))
        if record["schema"] != "stratbox.rosstat.registry.v1" or record["publisher_id"] != "rosstat":
            raise ValueError("rosstat.registry_invalid")
        values.append(RosstatSourceSpec(
            record["family_id"], record["title"], record["landing_url"],
            record["profiles"]["discovery"], frozenset(record["accepted_formats"]),
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
