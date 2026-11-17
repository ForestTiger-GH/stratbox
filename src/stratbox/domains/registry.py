"""Discover built-in domain registrations without a central domain list."""

from __future__ import annotations

from importlib import import_module
from pkgutil import iter_modules

from stratbox.core.execution.catalog import (
    OperationRegistration, OperationCatalog, RegistryError, merge_catalogs,
)


def domain_catalog() -> OperationCatalog:
    import stratbox.domains as package

    refs = []
    for found in sorted(iter_modules(package.__path__), key=lambda item: item.name):
        if not found.ispkg or found.name.startswith("_"):
            continue
        name = f"{package.__name__}.{found.name}"
        try:
            registration = import_module(f"{name}.registration").REGISTRATION
        except (ImportError, AttributeError) as exc:
            raise RegistryError(f"registry.missing_registration:{found.name}") from exc
        if not isinstance(registration, OperationRegistration) or registration.owner_id != found.name:
            raise RegistryError(f"registry.invalid_domain:{found.name}")
        for ref in registration.operations:
            prefix = name + "."
            if not ref.definition_ref.startswith(prefix) or not ref.handler_ref.startswith(prefix):
                raise RegistryError(f"registry.domain_ownership:{found.name}")
            if ref.wire_codec_ref and not ref.wire_codec_ref.startswith(prefix):
                raise RegistryError(f"registry.codec_ownership:{found.name}")
            refs.append(ref)
    return OperationCatalog(tuple(refs))


def operation_catalog() -> OperationCatalog:
    from stratbox.core.registry import core_catalog
    return merge_catalogs(domain_catalog(), core_catalog())
