"""Source identities, profiles and qualified bindings to operation templates."""
from stratbox.domains.registry.catalog import SourceCatalog, SourceCard, SourceProfile, SourceOperation

def source_catalog():
    from stratbox.operations import operation_catalog
    return operation_catalog().source_catalog()
