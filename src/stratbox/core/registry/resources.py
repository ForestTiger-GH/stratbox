"""Deterministic, dependency-free reading of bundled registry declarations.

Registry resources use the JSON subset of YAML 1.2. Executable references are
metadata here; reading a declaration never imports the referenced module.
"""
from __future__ import annotations

from importlib.resources import files
import json
import re
from hashlib import sha256

_OWNER = re.compile(r"[a-z][a-z0-9_.-]*\Z")
_KINDS = {"sources": "SOURCE_", "operations": "OPERATION_", "profiles": "PROFILE_"}


def registry_root():
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


def iter_resources(owner: str, kind: str):
    if not isinstance(owner, str) or not _OWNER.fullmatch(owner) or kind not in _KINDS:
        raise ValueError("registry.invalid_resource_scope")
    root = registry_root().joinpath(owner, kind)
    if not root.is_dir():
        return ()
    prefix = _KINDS[kind]
    result = []
    for item in root.iterdir():
        if item.name.endswith((".yaml", ".yml")):
            if not item.name.startswith(prefix) or not re.fullmatch(r"[A-Za-z0-9_.-]+\.yaml", item.name):
                raise ValueError("registry.invalid_resource_name")
            if not item.is_file():
                raise ValueError("registry.invalid_resource_name")
            result.append(item)
    return tuple(sorted(result, key=lambda item: item.name))


def iter_documents(owner: str, kind: str) -> tuple[dict, ...]:
    return tuple(read_document(item) for item in iter_resources(owner, kind))


def resource_owners(*, root=None) -> tuple[str, ...]:
    root = registry_root() if root is None else root
    owners = []
    for item in root.iterdir():
        if not item.is_dir() or item.name.startswith(("__", ".")):
            continue
        if not _OWNER.fullmatch(item.name) or not item.joinpath("OWNER.yaml").is_file():
            raise ValueError("registry.invalid_owner_directory")
        if read_document(item.joinpath("OWNER.yaml")).get("owner_id") != item.name:
            raise ValueError("registry.owner_directory_mismatch")
        owners.append(item.name)
    return tuple(sorted(owners))


def resource_inventory() -> tuple[tuple[str, int, str], ...]:
    """Stable identities of exact packaged declaration bytes, without execution."""
    result = []
    def visit(root, prefix):
        for item in sorted(root.iterdir(), key=lambda value: value.name):
            name = prefix + item.name
            if item.is_dir():
                if not item.name.startswith("__"):
                    visit(item, name + "/")
            elif item.name.endswith(".yaml"):
                data = item.read_bytes()
                result.append((name, len(data), sha256(data).hexdigest()))
    visit(registry_root(), "")
    return tuple(result)
