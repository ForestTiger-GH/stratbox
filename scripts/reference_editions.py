"""Inspect or stage fully verified, manifest-pinned reference asset editions.

This maintainer tool is intentionally separate from the public shared package:
reference owners are offline/read-only and never mutate installed assets.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stratbox.shared.reference.assets import load_reference, ReferenceError  # noqa: E402

PACKAGES = {
    "banks": "stratbox.shared.reference.banks",
    "okved2": "stratbox.shared.reference.okved2",
    "geography": "stratbox.shared.reference.geography",
}
_EDITIONS = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}\\Z")


def _manifest_path(reference: str) -> Path:
    return SRC / "stratbox" / "shared" / "reference" / reference / "_resources" / "manifest.json"


def _validated_path(value: str) -> str:
    if not value or value.startswith("/") or "\\\\" in value or "\\" in value:
        raise ValueError("A reference asset requires a relative POSIX path")
    path = PurePosixPath(value)
    if any(part in {".", "..", ""} for part in path.parts) or str(path) != value:
        raise ValueError("Reference asset must remain inside its package")
    return value


def verify(reference: str) -> None:
    selections = tuple(PACKAGES) if reference == "all" else (reference,)
    for family in selections:
        package = PACKAGES[family]
        root = _manifest_path(family)
        manifest = json.loads(root.read_text(encoding="utf-8"))
        for edition in manifest["editions"]:
            resolved = load_reference(package, edition_id=edition["edition_id"])
            for asset in resolved.edition.assets:
                resolved.read(asset.role)  # Verify optional assets as well.
                print(f"OK  {family}:{resolved.edition.edition_id}:{asset.role} "
                      f"{asset.identity.sha256} {asset.identity.size}")
            print(f"OK  snapshot {family}:{resolved.edition.edition_id} "
                  f"{resolved.snapshot_identity.sha256}")


def stage(reference: str, edition_id: str, replacements: list[str], *, activate: bool,
          publisher: str | None, source_url: str | None, published_at: str | None,
          effective_from: str | None, effective_to: str | None) -> None:
    from datetime import date

    if not _EDITIONS.fullmatch(edition_id):
        raise ValueError("Invalid edition ID")
    for value in (published_at, effective_from, effective_to):
        if value:
            date.fromisoformat(value)
    root = _manifest_path(reference)
    manifest = json.loads(root.read_text(encoding="utf-8"))
    entries = manifest["editions"]
    if any(item["edition_id"] == edition_id for item in entries):
        raise ValueError("Edition ID already exists; never mutate a historical edition")
    old = next(item for item in entries if item["edition_id"] == manifest["active_edition"])
    bundle = load_reference(PACKAGES[reference], edition_id=old["edition_id"])
    # Old data is frozen: verify every historical role before creating an edition.
    for asset in bundle.edition.assets:
        bundle.read(asset.role)

    target = deepcopy(old)
    target["edition_id"] = edition_id
    target["publisher"] = publisher
    target["source_url"] = source_url
    target["published_at"] = published_at
    target["effective_from"] = effective_from
    target["effective_to"] = effective_to
    updated = {}
    for item in replacements:
        role, separator, path = item.partition("=")
        if separator != "=" or not role or role in updated:
            raise ValueError("Each --asset must be a unique ROLE=PATH")
        updated[role] = _validated_path(path)
    known = {asset["role"] for asset in target["assets"]}
    if not updated.keys() <= known:
        raise ValueError("Unknown reference role(s): " + str(sorted(updated.keys() - known)))
    used = {item["path"] for ed in entries for item in ed["assets"]}
    base = root.parent
    for asset in target["assets"]:
        if asset["role"] not in updated:
            continue
        new_path = updated[asset["role"]]
        if new_path in used:
            raise ValueError("Updated asset must use a new, edition-specific path")
        content = (base / new_path).read_bytes()
        asset.update(path=new_path, sha256=sha256(content).hexdigest(), size=len(content))
    # Every new and unchanged role is admitted as bytes, not just a filename.
    for asset in target["assets"]:
        raw = (base / _validated_path(asset["path"])).read_bytes()
        if sha256(raw).hexdigest() != asset["sha256"] or len(raw) != asset["size"]:
            raise ValueError("New edition contains a mismatched reference asset")
    entries.append(target)
    if activate:
        manifest["active_edition"] = edition_id
    data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(dir=root.parent, prefix=".manifest-", delete=False) as file:
        tmp_path = Path(file.name)
        try:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise
    os.replace(tmp_path, root)
    print(f"STAGED  {reference}:{edition_id}; active={manifest['active_edition']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--reference", choices=tuple(PACKAGES) + ("all",), default="all")
    stage_parser = commands.add_parser("stage")
    stage_parser.add_argument("--reference", choices=tuple(PACKAGES), required=True)
    stage_parser.add_argument("--edition-id", required=True)
    stage_parser.add_argument("--asset", action="append", default=[], metavar="ROLE=PATH")
    stage_parser.add_argument("--activate", action="store_true")
    stage_parser.add_argument("--publisher")
    stage_parser.add_argument("--source-url")
    stage_parser.add_argument("--published-at")
    stage_parser.add_argument("--effective-from")
    stage_parser.add_argument("--effective-to")
    args = parser.parse_args()
    try:
        if args.command == "verify":
            verify(args.reference)
        else:
            stage(args.reference, args.edition_id, args.asset, activate=args.activate,
                  publisher=args.publisher, source_url=args.source_url,
                  published_at=args.published_at, effective_from=args.effective_from,
                  effective_to=args.effective_to)
        return 0
    except (ValueError, OSError, KeyError, ReferenceError) as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
