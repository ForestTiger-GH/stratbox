"""Canonical metadata loading and catalogs, independent of handler execution."""

from stratbox.core.registry.catalog import (
    OperationCatalog, OperationRef, OperationRegistration, RegistryError, merge_catalogs,
)
from stratbox.core.registry.source_catalog import (
    SourceCatalog, SourceCard, SourceProfile, SourceOperation,
)


def _catalog(include):
    from stratbox.core.registry.operations import owner_ids, owner_registration
    from stratbox.core.registry.assembly import assemble_owners
    return assemble_owners(tuple(owner for owner in owner_ids() if include(owner)), owner_registration)[1]


def core_catalog() -> OperationCatalog:
    return _catalog(lambda owner: owner.startswith("core."))


def domain_catalog() -> OperationCatalog:
    return _catalog(lambda owner: not owner.startswith("core."))


def operation_catalog() -> OperationCatalog:
    return _catalog(lambda owner: True)
