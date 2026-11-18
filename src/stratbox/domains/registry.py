"""Deterministically discover bundled operation owners at arbitrary package depth.

A local _registration.py marks exactly one operation owner. Grouping packages and
internal implementation packages do not need manifests. No external paths,
network sources, or execution handlers are scanned during catalog discovery.
"""

from __future__ import annotations

from importlib import import_module, resources

from stratbox.core.execution.catalog import (
    OperationCatalog, OperationRef, OperationRegistration, RegistryError,
    merge_catalogs,
)


def _registration_packages(directory, parents: tuple[str, ...] = ()):
    """Yield dotted owner paths for Python packages with an exact manifest."""
    for child in sorted(directory.iterdir(), key=lambda item: item.name):
        if not child.is_dir() or child.name.startswith((".", "_")):
            continue
        if not child.joinpath("__init__.py").is_file():
            continue
        parts = (*parents, child.name)
        if child.joinpath("_registration.py").is_file():
            yield ".".join(parts)
        yield from _registration_packages(child, parts)


def _within(module: str, owner_package: str) -> bool:
    """Compare Python module prefixes on complete segment boundaries."""
    return module == owner_package or module.startswith(owner_package + ".")


def domain_catalog() -> OperationCatalog:
    """Read local declarations only; resolve executable handlers on demand."""
    owners = tuple(_registration_packages(resources.files("stratbox.domains")))
    registrations: list[tuple[str, OperationRegistration]] = []
    for owner in owners:
        path = f"stratbox.domains.{owner}._registration"
        try:
            declaration = import_module(path).REGISTRATION
        except (ImportError, AttributeError) as exc:
            raise RegistryError(f"registry.invalid_manifest:{owner}") from exc
        if not isinstance(declaration, OperationRegistration):
            raise RegistryError(f"registry.invalid_registration:{owner}")
        if declaration.owner_id != owner:
            raise RegistryError(f"registry.invalid_owner:{owner}:{declaration.owner_id}")
        registrations.append((owner, declaration))

    owner_packages = {
        owner: f"stratbox.domains.{owner}" for owner, _ in registrations
    }
    refs: list[OperationRef] = []
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
                parents = [
                    candidate for candidate, prefix in owner_packages.items()
                    if _within(module, prefix)
                ]
                if not parents:
                    raise RegistryError(
                        f"registry.domain_ownership:{owner}:{role}:{module}"
                    )
                nearest = max(parents, key=lambda value: len(value.split(".")))
                if nearest != owner:
                    raise RegistryError(
                        f"registry.nearest_owner:{owner}:{nearest}:{role}:{module}"
                    )
            refs.append(ref)
    return OperationCatalog(tuple(refs))


def operation_catalog() -> OperationCatalog:
    from stratbox.core.registry import core_catalog

    return merge_catalogs(domain_catalog(), core_catalog())
