"""Discover, validate and list bundled source-domain operation owners.

The source layout has one authoritative discovery rule, shared by runtime,
static architecture checks and distribution checks. Catalog declarations are
loaded without resolving executable handlers or optional engines.
"""

from __future__ import annotations

from importlib import import_module, resources

from stratbox.core.execution.catalog import (
    OperationCatalog,
    OperationRef,
    OperationRegistration,
    RegistryError,
    merge_catalogs,
)

from ._structure import DomainLayoutError, discover_operation_owners


def _within(module: str, owner_package: str) -> bool:
    """Compare module prefixes at Python package segment boundaries."""
    return module == owner_package or module.startswith(owner_package + ".")


def _validated_domain_snapshot() -> tuple[
    tuple[tuple[str, OperationRegistration], ...], OperationCatalog
]:
    """Load and validate exact owners once for both catalog and inventory."""
    try:
        owners = discover_operation_owners(resources.files("stratbox.domains"))
    except (DomainLayoutError, OSError) as exc:
        raise RegistryError(str(exc)) from exc

    registrations: list[tuple[str, OperationRegistration]] = []
    for owner in owners:
        try:
            declaration = import_module(
                f"stratbox.domains.{owner}._registration"
            ).REGISTRATION
        except (ImportError, AttributeError, SyntaxError) as exc:
            raise RegistryError(f"registry.invalid_manifest:{owner}") from exc
        if not isinstance(declaration, OperationRegistration):
            raise RegistryError(f"registry.invalid_registration:{owner}")
        if declaration.owner_id != owner:
            raise RegistryError(
                f"registry.invalid_owner:{owner}:{declaration.owner_id}"
            )
        if not declaration.operations:
            raise RegistryError(f"registry.empty_owner:{owner}")
        registrations.append((owner, declaration))

    owner_packages = {
        owner: f"stratbox.domains.{owner}" for owner, _ in registrations
    }
    refs: list[OperationRef] = []
    logical_owners: dict[str, str] = {}
    for owner, declaration in registrations:
        for ref in declaration.operations:
            if not isinstance(ref, OperationRef):
                raise RegistryError(f"registry.invalid_reference:{owner}")
            for role, link in (
                ("definition", ref.definition_ref),
                ("handler", ref.handler_ref),
                ("codec", ref.wire_codec_ref),
            ):
                if link is None:
                    continue
                module = link.split(":", 1)[0]
                candidates = (
                    candidate for candidate, package in owner_packages.items()
                    if _within(module, package)
                )
                nearest = max(
                    candidates, key=lambda value: len(value.split(".")),
                    default=None,
                )
                if nearest is None:
                    raise RegistryError(
                        f"registry.domain_ownership:{owner}:{role}:{module}"
                    )
                if nearest != owner:
                    raise RegistryError(
                        f"registry.nearest_owner:{owner}:{nearest}:{role}:{module}"
                    )
            original_owner = logical_owners.setdefault(ref.operation_id, owner)
            if original_owner != owner:
                raise RegistryError(
                    f"registry.logical_owner:{ref.operation_id}:"
                    f"{original_owner}:{owner}"
                )
            refs.append(ref)
    return tuple(registrations), OperationCatalog(tuple(refs))


def domain_catalog() -> OperationCatalog:
    """Read-only domain catalog with deterministic, fail-closed owner discovery."""
    return _validated_domain_snapshot()[1]


def operation_catalog() -> OperationCatalog:
    """Merge the independently registered domain and neutral-core operations."""
    from stratbox.core.registry import core_catalog

    return merge_catalogs(domain_catalog(), core_catalog())


def domain_registration_inventory() -> tuple[tuple[str, str, int], ...]:
    """Return full owner/operation/version identities without loading handlers.

    This view uses the same validated declarations as runtime discovery.
    It is suitable for source-to-wheel/sdist inventory comparisons.
    """
    registrations, _ = _validated_domain_snapshot()
    return tuple(sorted(
        (owner, ref.operation_id, ref.contract_version)
        for owner, declaration in registrations
        for ref in declaration.operations
    ))
