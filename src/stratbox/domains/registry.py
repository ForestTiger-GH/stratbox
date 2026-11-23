"""Discover, validate and list bundled source-domain operation owners.

Canonical registry resources supply domain owners and contracts. The same
validated snapshot supplies runtime catalogs and distribution inventories;
executable handlers and optional engines remain unresolved during discovery.
"""

from __future__ import annotations


from stratbox.core.registry.catalog import (
    OperationCatalog,
    OperationRef,
    OperationRegistration,
    RegistryError,
    merge_catalogs,
)

from stratbox.core.registry.operations import owner_ids, owner_registration


def _validated_domain_snapshot():
    from stratbox.core.registry.assembly import assemble_owners
    return assemble_owners(
        tuple(owner for owner in owner_ids() if not owner.startswith("core.")),
        owner_registration,
    )


def domain_catalog() -> OperationCatalog:
    """Read-only domain catalog with deterministic, fail-closed owner discovery."""
    return _validated_domain_snapshot()[1]


def operation_catalog() -> OperationCatalog:
    """Merge the independently registered domain and neutral-core operations."""
    from stratbox.core.registry import operation_catalog as build
    return build()


def domain_registration_inventory() -> tuple[tuple[str, str], ...]:
    """Return owner/operation identities without loading handlers.

    This view uses the same validated declarations as runtime discovery.
    It is suitable for source-to-wheel/sdist inventory comparisons.
    """
    registrations, _ = _validated_domain_snapshot()
    return tuple(sorted(
        (owner, ref.operation_id)
        for owner, declaration in registrations
        for ref in declaration.operations
    ))
