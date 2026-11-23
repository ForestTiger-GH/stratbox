"""Physical routes projected only for the named statistical selection."""
from .contracts import CbrFileRegistryItem
from stratbox.domains.cbr.publications.catalog import source
from stratbox.domains.cbr.publications.selection import CATALOG_SERIES, DEFAULT_COLLECTION_KEYS
from stratbox.domains.cbr.publications.profiles import acquisition_profile

DEFAULT_CBR_FILE_SOURCES = tuple(
    CbrFileRegistryItem(key, acquisition_profile(source(CATALOG_SERIES[key]).acquisition_profile).default_url,
        source(CATALOG_SERIES[key]).title, series_id=CATALOG_SERIES[key]) for key in DEFAULT_COLLECTION_KEYS)
