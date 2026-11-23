"""Deterministic discovery of bundled declarations, shared by every consumer.

The JSON subset of YAML keeps declarations dependency free. OWNER declarations
establish ownership; directories only organize records for readers.
"""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
import json
import re

_OWNER = re.compile(r"[a-z][a-z0-9_.-]*\Z")
_KINDS = {"sources": "SOURCE_", "operations": "OPERATION_", "profiles": "PROFILE_",
          "routes": "ROUTE_", "families": "FAMILY_", "groups": "GROUP_"}
_NAME = re.compile(r"[A-Za-z0-9_.-]+\.yaml\Z")


@lru_cache(maxsize=1)
def registry_root():
    """Reuse the immutable package root, including identity-hashed zip paths."""
    return files("stratbox.registry")


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("registry.duplicate_key")
        value[key] = item
    return value


def decode_document(data: bytes) -> dict:
    if not isinstance(data, bytes) or len(data) > 1024 * 1024:
        raise ValueError("registry.invalid_document")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("registry.invalid_document") from None
    if not isinstance(value, dict):
        raise ValueError("registry.invalid_document")
    return value


def read_document(resource) -> dict:
    return decode_document(resource.read_bytes())


def _children(root):
    return tuple(sorted((item for item in root.iterdir()
                         if not item.name.startswith(("__", "."))), key=lambda item: item.name))


@lru_cache(maxsize=16)
def _discover(root):
    """One immutable packaged-resource view for loading and delivery checks."""
    owners, records, inventory = {}, {}, []
    def visit(directory, owner=None, relative="", prefix=""):
        owner_file = directory.joinpath("OWNER.yaml")
        if owner_file.is_file():
            if owner is not None and relative.split("/", 1)[0] in _KINDS:
                raise ValueError("registry.nested_record_owner")
            owner = read_document(owner_file).get("owner_id")
            if not isinstance(owner, str) or not _OWNER.fullmatch(owner):
                raise ValueError("registry.invalid_owner")
            if owner in owners:
                raise ValueError("registry.duplicate_owner")
            owners[owner] = directory
            relative = ""
            inventory.append((prefix + "OWNER.yaml", owner_file))
        for item in _children(directory):
            name = prefix + item.name
            if item.is_dir():
                visit(item, owner, relative + item.name + "/", name + "/")
            elif item.name.endswith((".yaml", ".yml")) and item.name != "OWNER.yaml":
                kind = relative.split("/", 1)[0]
                if owner is None or kind not in _KINDS:
                    raise ValueError("registry.unowned_resource")
                if not item.name.startswith(_KINDS[kind]) or not _NAME.fullmatch(item.name):
                    raise ValueError("registry.invalid_resource_name")
                records.setdefault((owner, kind), []).append((name, item))
                inventory.append((name, item))
    visit(root)
    return (tuple(sorted(owners.items())),
            {key: tuple(item for _, item in sorted(values)) for key, values in records.items()},
            tuple(sorted(inventory)))


def owner_directories(*, root=None):
    """Find explicit owners recursively, independent of grouping directory names."""
    return _discover(registry_root() if root is None else root)[0]


def resource_owners(*, root=None) -> tuple[str, ...]:
    return tuple(owner for owner, _ in owner_directories(root=root))


def owner_directory(owner: str, *, root=None):
    if not isinstance(owner, str) or not _OWNER.fullmatch(owner):
        raise ValueError("registry.invalid_resource_scope")
    try:
        return dict(owner_directories(root=root))[owner]
    except KeyError:
        raise ValueError("registry.owner_unknown") from None


def iter_resources(owner: str, kind: str, *, root=None):
    if kind not in _KINDS:
        raise ValueError("registry.invalid_resource_scope")
    root = registry_root() if root is None else root
    owner_directory(owner, root=root)
    return _discover(root)[1].get((owner, kind), ())


def iter_documents(owner: str, kind: str) -> tuple[dict, ...]:
    return tuple(read_document(item) for item in iter_resources(owner, kind))


def resource_inventory(*, root=None) -> tuple[tuple[str, int, str], ...]:
    """Exact packaged bytes using the same owner/kind traversal as runtime."""
    return tuple((name, len(data := item.read_bytes()), sha256(data).hexdigest())
                 for name, item in _discover(registry_root() if root is None else root)[2])
