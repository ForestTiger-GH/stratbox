"""Validate owner boundaries once for catalogs and inventory projections."""
from stratbox.core.registry.catalog import OperationCatalog, OperationRef, OperationRegistration, RegistryError


def _within(module: str, owner_package: str) -> bool:
    """Compare module prefixes at Python package segment boundaries."""
    return module == owner_package or module.startswith(owner_package + ".")


def assemble_owners(owners, load_registration):
    """Load and validate exact owners once for both catalog and inventory."""
    registrations: list[tuple[str, OperationRegistration]] = []
    for owner in owners:
        declaration = load_registration(owner)
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
        owner: f"stratbox.domains.{owner}" for owner, _ in registrations if not owner.startswith("core.")
    }
    refs: list[OperationRef] = []
    logical_owners: dict[str, str] = {}
    for owner, declaration in registrations:
        for ref in declaration.operations:
            if not isinstance(ref, OperationRef):
                raise RegistryError(f"registry.invalid_reference:{owner}")
            for role, link in (
                ("handler", ref.handler_ref),
                ("codec", ref.wire_codec_ref),
                ("wire_contract", ref.wire_contract_ref),
            ):
                if link is None:
                    continue
                module = link.split(":", 1)[0]
                if owner.startswith("core."):
                    if not _within(module, "stratbox.core"):
                        raise RegistryError(f"registry.core_ownership:{owner}:{role}:{module}")
                    continue
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
    return tuple(registrations), OperationCatalog.from_registrations(
        *(declaration for _, declaration in registrations)
    )
