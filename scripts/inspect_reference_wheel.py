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
from zipfile import ZipFile, BadZipFile

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stratbox.shared.reference.assets import (  # noqa: E402
    REFERENCE_REQUIRED_ROLES, ReferenceError, parse_reference_manifest,
)

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


def verify_wheel(path: str) -> dict[str, object]:
    counts: dict[str, int] = {}
    with ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Wheel contains duplicate ZIP member names")
        members = set(names)
        old = sorted(name for name in names if any(name.startswith(prefix) for prefix in OBSOLETE))
        if old:
            raise ValueError("Wheel includes obsolete shared paths: " + str(old))
        for name in _REQUIRED_CODE:
            if name not in members:
                raise ValueError("Required semantic owner missing from wheel: " + name)
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
    return {"wheel": path, "asset_occurrences": counts, "result": "verified"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", help="Path to the built Stratbox .whl file")
    args = parser.parse_args()
    try:
        print(json.dumps(verify_wheel(args.wheel), indent=2, ensure_ascii=False))
        return 0
    except (OSError, KeyError, TypeError, ValueError, ReferenceError, BadZipFile) as error:
        parser.exit(1, f"Wheel reference verification failed: {error}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
