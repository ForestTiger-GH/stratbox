"""Verify every edition and every resource within an actual built wheel.

The same pure manifest validator powers runtime admission, edition staging
and distribution checks. This reader intentionally never imports from a wheel
or executes any code inside the ZIP archive.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import tarfile
from zipfile import ZipFile, BadZipFile

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stratbox.domains._structure import discover_operation_owners  # noqa: E402

from stratbox.shared.reference.assets import (  # noqa: E402
    REFERENCE_REQUIRED_ROLES, ReferenceError, parse_reference_manifest,
)

DOMAIN_SOURCE = SRC / "stratbox" / "domains"
REGISTRY_SOURCE = SRC / "stratbox" / "registry"
DOMAIN_OBSOLETE_DIRS = (
    "cbr_file_collector", "cbr_forms", "cbr_industries",
    "cbr_offices", "cbr_offices_reg", "cbr_sors_restoration",
    "escrow", "fns_1yur", "fns_sme", "frg",
)
# All non-code packaged files are treated as domain data, independent of the
# present or future format. This makes a newly added YAML, parquet or binary
# resource part of release completeness checks without editing this script.
NONDATA_SUFFIXES = frozenset({".py", ".pyi", ".md", ".pyc"})


def _domain_asset(path: str) -> bool:
    member = Path(path)
    return (
        not path.endswith("/")
        and not any(
            part.startswith(".") or part == "__pycache__" for part in member.parts
        )
        and member.suffix.lower() not in NONDATA_SUFFIXES
    )


def _identity(payload: bytes) -> tuple[int, str]:
    return len(payload), sha256(payload).hexdigest()


def _source_registry_inventory() -> dict[str, tuple[int, str]]:
    """Include every canonical declaration and its package boundary by bytes."""
    from stratbox.core.registry.resources import resource_inventory
    result = {name: (size, digest) for name, size, digest in resource_inventory()}
    result["__init__.py"] = _identity((REGISTRY_SOURCE / "__init__.py").read_bytes())
    return result


def _verify_registry_members(names: set[str], prefix: str, read_bytes) -> dict[str, int]:
    """Compare source, wheel and sdist declarations without executing archive code."""
    base = prefix + "stratbox/registry/"
    expected = _source_registry_inventory()
    if "__init__.py" not in expected or not any(name.endswith(".yaml") for name in expected):
        raise ValueError("Canonical registry source declarations are missing")
    actual = {
        name[len(base):]
        for name in names if name.startswith(base)
        and (name.endswith((".yaml", ".yml")) or name.endswith("/__init__.py"))
    }
    missing = sorted(expected.keys() - actual)
    extra = sorted(actual - expected.keys())
    changed = sorted(name for name in actual & expected.keys()
                     if _identity(read_bytes(base + name)) != expected[name])
    if missing or extra or changed:
        raise ValueError("Registry distribution mismatch: "
                         f"missing={missing}, extra={extra}, changed={changed}")
    return {"declarations": sum(name.endswith((".yaml", ".yml")) for name in actual),
            "owners": sum(name.endswith("/OWNER.yaml") for name in actual)}


def _source_domain_inventory() -> tuple[
    dict[str, tuple[int, str]], dict[str, tuple[int, str]]
]:
    """Inventory actual manifests and arbitrary packaged data without hand lists."""
    owners = {}
    for name in discover_operation_owners(DOMAIN_SOURCE):
        filename = name.replace(".", "/") + "/_registration.py"
        owners[filename] = _identity((DOMAIN_SOURCE / filename).read_bytes())
    data = {}
    for file in sorted(DOMAIN_SOURCE.rglob("*")):
        if not file.is_file() or not _domain_asset(file.relative_to(DOMAIN_SOURCE).as_posix()):
            continue
        data[file.relative_to(DOMAIN_SOURCE).as_posix()] = _identity(file.read_bytes())
    return owners, data


def _verify_domain_members(
    names: set[str], prefix: str, read_bytes
) -> dict[str, int]:
    """Require all and only current domain owners/data, with exact payload digests."""
    base = prefix + "stratbox/domains/"
    source_owners, source_data = _source_domain_inventory()
    actual_owners = {
        name[len(base):]
        for name in names
        if name.startswith(base) and name.endswith("/_registration.py")
    }
    missing = sorted(source_owners.keys() - actual_owners)
    extra = sorted(actual_owners - source_owners.keys())
    changed_owners = [
        name for name in sorted(actual_owners & source_owners.keys())
        if _identity(read_bytes(base + name)) != source_owners[name]
    ]
    package_missing = []
    for owner_file in actual_owners:
        parts = owner_file.split("/")[:-1]
        for depth in range(1, len(parts) + 1):
            package_init = base + "/".join(parts[:depth]) + "/__init__.py"
            if package_init not in names:
                package_missing.append(package_init)
    if base + "__init__.py" not in names:
        package_missing.append(base + "__init__.py")

    actual_data = {
        name[len(base):]
        for name in names if name.startswith(base)
        and _domain_asset(name[len(base):])
    }
    missing_data = sorted(set(source_data) - actual_data)
    extra_data = sorted(actual_data - set(source_data))
    data_changed = []
    for name in sorted(set(source_data) & actual_data):
        payload = read_bytes(base + name)
        actual_identity = _identity(payload)
        if actual_identity != source_data[name]:
            data_changed.append(name)

    forbidden = sorted(
        name for name in names
        if name.startswith(tuple(base + part + "/" for part in DOMAIN_OBSOLETE_DIRS))
    )
    if base + "_cbr.py" in names:
        forbidden.append(base + "_cbr.py")
    if missing or extra or changed_owners or package_missing or missing_data or extra_data or data_changed or forbidden:
        raise ValueError(
            "Domain distribution mismatch: "
            f"missing_owners={missing}, extra_owners={extra}, changed_owners={changed_owners}, "
            f"missing_init={sorted(set(package_missing))}, "
            f"missing_data={missing_data}, extra_data={extra_data}, "
            f"changed_data={data_changed}, obsolete={forbidden[:15]}"
        )
    return {"owners": len(actual_owners), "data_files": len(actual_data)}


OBSOLETE = (
    "stratbox/shared/registries/",
    "stratbox/shared/text/",
    "stratbox/shared/data/identity.py",
    "stratbox/shared/data/evidence.py",
)
_REQUIRED_CODE = (
    "stratbox/shared/identity.py",
    "stratbox/shared/evidence.py",
    "stratbox/shared/data/datasets.py",
    "stratbox/shared/reference/assets.py",
)


def _source_code_inventory():
    root = SRC / "stratbox"
    return {"stratbox/" + path.relative_to(root).as_posix(): _identity(path.read_bytes())
            for path in sorted(root.rglob("*")) if path.is_file()
            and (path.suffix in {".py", ".pyi"} or path.name == "py.typed")}


def _verify_code_members(names, prefix, read_bytes):
    """Verify the installed implementation as well as declarative resources."""
    base = prefix + "stratbox/"
    expected = _source_code_inventory()
    actual = {name[len(prefix):] for name in names if name.startswith(base)
              and (name.endswith((".py", ".pyi")) or name.endswith("/py.typed"))}
    missing = sorted(expected.keys() - actual)
    extra = sorted(actual - expected.keys())
    changed = sorted(name for name in actual & expected.keys()
                     if _identity(read_bytes(prefix + name)) != expected[name])
    bytecode = sorted(name for name in names if name.startswith(base)
                      and ("/__pycache__/" in name or name.endswith((".pyc", ".pyo"))))
    if missing or extra or changed or bytecode:
        raise ValueError("Implementation distribution mismatch: "
                         f"missing={missing}, extra={extra}, changed={changed}, bytecode={bytecode}")
    manifest = json.dumps(sorted(expected.items()), separators=(",", ":")).encode("utf-8")
    return {"files": len(expected), "identity": sha256(manifest).hexdigest()}


def _distribution_identity(path):
    digest, size = sha256(), 0
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "size": size}


def verify_wheel(path: str) -> dict[str, object]:
    counts: dict[str, int] = {}
    with ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Wheel contains duplicate ZIP member names")
        members = set(names)
        domain_counts = _verify_domain_members(members, "", archive.read)
        registry_counts = _verify_registry_members(members, "", archive.read)
        old = sorted(name for name in names if any(name.startswith(prefix) for prefix in OBSOLETE))
        if old:
            raise ValueError("Wheel includes obsolete shared paths: " + str(old))
        for name in _REQUIRED_CODE:
            if name not in members:
                raise ValueError("Required semantic owner missing from wheel: " + name)
        code_counts = _verify_code_members(members, "", archive.read)
        root = "stratbox/shared/reference/"
        bundled_families = {
            item[len(root):].split("/")[0]
            for item in members if item.startswith(root) and "/_resources/" in item
        }
        known = set(REFERENCE_REQUIRED_ROLES)
        if bundled_families != known:
            raise ValueError(
                "Wheel reference family discovery mismatch: "
                f"missing={sorted(known - bundled_families)}, "
                f"undeclared={sorted(bundled_families - known)}"
            )
        for family in sorted(known):
            prefix = f"{root}{family}/_resources/"
            manifest_name = prefix + "manifest.json"
            if manifest_name not in members:
                raise ValueError("Reference manifest missing from wheel: " + manifest_name)
            package = f"stratbox.shared.reference.{family}"
            _, editions = parse_reference_manifest(package, archive.read(manifest_name))
            referenced = set()
            for edition in editions:
                for asset in edition.assets:
                    filename = prefix + asset.path
                    referenced.add(filename)
                    if filename not in members:
                        raise ValueError("Reference asset missing from wheel: " + filename)
                    data = archive.read(filename)
                    if len(data) != asset.identity.size or sha256(data).hexdigest() != asset.identity.sha256:
                        raise ValueError("Reference asset digest mismatch in wheel: " + filename)
                    counts[family] = counts.get(family, 0) + 1
            unknown = sorted(
                name for name in members
                if name.startswith(prefix) and name != manifest_name
                and not name.endswith("/") and name not in referenced
            )
            if unknown:
                raise ValueError("Undeclared reference resources in wheel: " + str(unknown))
    return {"wheel": path, "asset_occurrences": counts,
            "domain_inventory": domain_counts, "registry_inventory": registry_counts,
            "implementation_inventory": code_counts, "distribution_identity": _distribution_identity(path),
            "result": "verified"}



def verify_sdist(path: str) -> dict[str, object]:
    """Inspect an actual source distribution without extracting untrusted members."""
    counts: dict[str, int] = {}
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members if member.isfile()]
        if len(names) != len(set(names)):
            raise ValueError("Source distribution contains duplicate member names")
        if not names:
            raise ValueError("Empty source distribution")
        roots = {name.split("/", 1)[0] for name in names}
        if len(roots) != 1:
            raise ValueError("Source distribution requires one top-level package root")
        root = next(iter(roots)) + "/src/"
        directory = set(names)
        def read_domain_member(filename: str) -> bytes:
            item = archive.getmember(filename)
            if not item.isfile():
                raise ValueError("Domain data is not a regular file: " + filename)
            handle = archive.extractfile(item)
            if handle is None:
                raise ValueError("Domain data unreadable: " + filename)
            with handle:
                return handle.read()
        domain_counts = _verify_domain_members(directory, root, read_domain_member)
        registry_counts = _verify_registry_members(directory, root, read_domain_member)
        for name in _REQUIRED_CODE:
            if root + name not in directory:
                raise ValueError("Required semantic owner missing from sdist: " + name)
        code_counts = _verify_code_members(directory, root, read_domain_member)
        reference_root = root + "stratbox/shared/reference/"
        present = {
            name[len(reference_root):].split("/")[0]
            for name in names if name.startswith(reference_root) and "/_resources/" in name
        }
        if present != set(REFERENCE_REQUIRED_ROLES):
            raise ValueError("Source distribution reference family discovery mismatch")
        for family in sorted(REFERENCE_REQUIRED_ROLES):
            prefix = reference_root + family + "/_resources/"
            manifest_name = prefix + "manifest.json"
            def read_member(filename: str) -> bytes:
                if filename not in directory:
                    raise ValueError("Source distribution asset missing: " + filename)
                item = archive.getmember(filename)
                if not item.isfile():
                    raise ValueError("Source distribution asset is not a regular file: " + filename)
                handle = archive.extractfile(item)
                if handle is None:
                    raise ValueError("Source distribution asset cannot be read: " + filename)
                with handle:
                    return handle.read()
            _, editions = parse_reference_manifest(
                f"stratbox.shared.reference.{family}", read_member(manifest_name)
            )
            referenced = {manifest_name}
            for edition in editions:
                for asset in edition.assets:
                    filename = prefix + asset.path
                    referenced.add(filename)
                    data = read_member(filename)
                    if len(data) != asset.identity.size or sha256(data).hexdigest() != asset.identity.sha256:
                        raise ValueError("Source distribution reference digest mismatch: " + filename)
                    counts[family] = counts.get(family, 0) + 1
            orphans = sorted(name for name in names if name.startswith(prefix) and name not in referenced)
            if orphans:
                raise ValueError("Undeclared resources in source distribution: " + str(orphans))
    return {"sdist": path, "asset_occurrences": counts,
            "domain_inventory": domain_counts, "registry_inventory": registry_counts,
            "implementation_inventory": code_counts, "distribution_identity": _distribution_identity(path),
            "result": "verified"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", help="Built Stratbox .whl or .tar.gz distribution")
    args = parser.parse_args()
    try:
        result = verify_sdist(args.wheel) if args.wheel.endswith(".tar.gz") else verify_wheel(args.wheel)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, KeyError, TypeError, ValueError, ReferenceError, BadZipFile, tarfile.TarError) as error:
        parser.exit(1, f"Reference distribution verification failed: {error}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
