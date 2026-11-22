"""Shared logical CBR publications, acquisition profiles and original admission."""
from importlib import import_module

_EXPORTS = {
    "all_sources": ".registry", "families": ".registry", "source": ".registry",
    "acquisition_profile": ".profiles", "SourceSeries": ".contracts",
    "PublicationAsset": ".contracts", "PublicationInventory": ".contracts",
    "ListSourcesRequest": ".contracts", "DiscoverRequest": ".contracts",
    "IdentifyRequest": ".contracts", "IdentifiedOriginal": ".contracts",
    "list_sources": ".operations", "discover": ".operations", "identify": ".operations",
}
__all__ = tuple(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    value = getattr(import_module(_EXPORTS[name], __name__), name)
    globals()[name] = value
    return value
