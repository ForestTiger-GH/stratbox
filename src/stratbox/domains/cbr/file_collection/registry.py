"""Default file selection projected from the shared CBR publication catalog."""
from .contracts import CbrFileRegistryItem
from stratbox.domains.cbr.publications.registry import CATALOG_SERIES, DEFAULT_COLLECTION_KEYS, source
from stratbox.domains.cbr.publications.profiles import acquisition_profile

DEFAULT_CBR_FILE_SOURCES = tuple(
    CbrFileRegistryItem(key, acquisition_profile(source(CATALOG_SERIES[key]).acquisition_profile).default_url,
                        source(CATALOG_SERIES[key]).title, series_id=CATALOG_SERIES[key])
    for key in DEFAULT_COLLECTION_KEYS
)
