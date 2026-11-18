"""Verify the actual bytes of manifest-pinned references inside a built wheel.

Unlike editable imports, a ZIP inspection proves that the distribution includes
every referenced material with the expected content identity.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import PurePosixPath
from zipfile import ZipFile, BadZipFile

PACKAGES = {
    "banks": frozenset({"official_xlsx", "aliases", "default_selection", "legacy_selection"}),
    "okved2": frozenset({"data", "meta", "structure"}),
    "geography": frozenset({"aliases"}),
}
OBSOLETE = (
    "stratbox/shared/registries/",
    "stratbox/shared/text/",
    "stratbox/shared/data/identity.py",
    "stratbox/shared/data/evidence.py",
)


def verify_wheel(path: str) -> dict[str, object]:
    counts: dict[str, int] = {}
    with ZipFile(path) as archive:
        members = set(archive.namelist())
        old = [name for name in members if any(name.startswith(p) for p in OBSOLETE)]
        if old:
            raise ValueError("Wheel includes obsolete shared paths: " + str(sorted(old)))
        required_code = (
            "stratbox/shared/identity.py", "stratbox/shared/evidence.py",
            "stratbox/shared/data/datasets.py", "stratbox/shared/reference/assets.py",
        )
        for expected in required_code:
            if expected not in members:
                raise ValueError("Required semantic owner missing from wheel: " + expected)
        for name, mandatory_roles in PACKAGES.items():
            prefix = f"stratbox/shared/reference/{name}/_resources/"
            manifest_name = prefix + "manifest.json"
            if manifest_name not in members:
                raise ValueError("Reference manifest missing from wheel: " + manifest_name)
            meta = json.loads(archive.read(manifest_name))
            if meta.get("manifest_schema_version") != 1:
                raise ValueError("Unsupported edition manifest in wheel")
            editions = meta.get("editions", [])
            active = meta.get("active_edition")
            if len([entry for entry in editions if entry["edition_id"] == active]) != 1:
                raise ValueError("Invalid active reference edition: " + name)
            if not editions:
                raise ValueError("Empty reference edition family: " + name)
            for entry in editions:
                roles = set()
                for asset in entry["assets"]:
                    rel = asset["path"]
                    if (rel.startswith("/") or "\\" in rel
                            or ".." in PurePosixPath(rel).parts
                            or str(PurePosixPath(rel)) != rel):
                        raise ValueError("Unsafe reference path in wheel manifest")
                    role = asset["role"]
                    if role in roles:
                        raise ValueError("Duplicate asset role in wheel manifest")
                    roles.add(role)
                    filename = prefix + rel
                    if filename not in members:
                        raise ValueError("Reference asset missing from wheel: " + filename)
                    data = archive.read(filename)
                    if len(data) != asset["size"] or sha256(data).hexdigest() != asset["sha256"]:
                        raise ValueError("Reference asset digest mismatch in wheel: " + filename)
                    counts[name] = counts.get(name, 0) + 1
                if not mandatory_roles <= roles:
                    raise ValueError("Reference family has incomplete required roles: " + name)
    return {"wheel": path, "asset_occurrences": counts, "result": "verified"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", help="Path to the built Stratbox .whl file")
    args = parser.parse_args()
    try:
        print(json.dumps(verify_wheel(args.wheel), indent=2, ensure_ascii=False))
        return 0
    except (OSError, KeyError, ValueError, BadZipFile) as error:
        parser.exit(1, f"Wheel reference verification failed: {error}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
