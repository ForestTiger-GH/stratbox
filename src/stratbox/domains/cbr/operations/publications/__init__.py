"""Public operation facade for publisher discovery, selection and acquisition."""
from importlib import import_module
from stratbox.domains.cbr.publications.contracts import (
    ListSourcesRequest, DiscoverRequest, IdentifyRequest, SelectPublicationRequest,
    AcquirePublicationRequest, AssessUpdatesRequest,
)

__all__ = (
    "list_sources", "discover", "identify", "select", "acquire", "assess_updates",
    "ListSourcesRequest", "DiscoverRequest", "IdentifyRequest", "SelectPublicationRequest",
    "AcquirePublicationRequest", "AssessUpdatesRequest",
)


def __getattr__(name):
    if name in {"list_sources", "discover", "identify", "select", "acquire", "assess_updates"}:
        value = getattr(import_module(__name__ + ".handlers"), name)
        globals()[name] = value
        return value
    raise AttributeError(name)
