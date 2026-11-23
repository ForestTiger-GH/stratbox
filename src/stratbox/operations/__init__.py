"""Canonical metadata loading and catalogs, independent of handler execution."""

from stratbox.operations.catalog import (
    OperationCatalog, OperationRef, OperationRegistration, RegistryError, merge_catalogs,
)


def _catalog(include):
    from stratbox.operations.declarations import owner_ids, owner_registration
    from stratbox.operations.assembly import assemble_owners
    catalog = assemble_owners(tuple(owner for owner in owner_ids() if include(owner)), owner_registration)[1]
    catalog.admit(level="metadata")
    return catalog


def core_catalog() -> OperationCatalog:
    return _catalog(lambda owner: owner.startswith("core."))


def domain_catalog() -> OperationCatalog:
    return _catalog(lambda owner: not owner.startswith("core."))


def operation_catalog() -> OperationCatalog:
    return _catalog(lambda owner: True)


from stratbox.operations.admission import (
    AdmissionCheck, CatalogAdmission, admit_registry_snapshot, validate_catalog,
)


def domain_registration_inventory():
    """Project logical domain identities from the same canonical operation catalog."""
    catalog = domain_catalog()
    return tuple(sorted((catalog.owner_of(ref.operation_id), ref.operation_id)
                        for ref in catalog.references))
