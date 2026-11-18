"""Source-domain package discovery shared by runtime and offline quality gates.

Only exact _registration.py files define operation owners. An undiscoverable
manifest below a non-package directory is a structural error, never a silent
omission. No operation handlers or optional data engines are imported here.
"""

from __future__ import annotations

from collections.abc import Iterator


class DomainLayoutError(ValueError):
    """A registration manifest is unreachable through Python packages."""


def _walk(directory, parents: tuple[str, ...], reachable: bool) -> Iterator[str]:
    for child in sorted(directory.iterdir(), key=lambda entry: entry.name):
        if not child.is_dir() or child.name.startswith((".", "_")):
            continue
        parts = (*parents, child.name)
        is_package = child.joinpath("__init__.py").is_file()
        next_reachable = reachable and is_package
        if child.joinpath("_registration.py").is_file():
            if not next_reachable:
                raise DomainLayoutError(
                    "domain.unreachable_manifest:" + ".".join(parts)
                )
            yield ".".join(parts)
        yield from _walk(child, parts, next_reachable)


def discover_operation_owners(directory, parents: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Return all manifest owners in deterministic dotted-path order.

    Works with filesystem Path and importlib.resources Traversable, including
    packages loaded from supported zip-based importers.
    """
    if not directory.joinpath("__init__.py").is_file():
        raise DomainLayoutError("domain.root_not_package")
    return tuple(_walk(directory, parents, True))
