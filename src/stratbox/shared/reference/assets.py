"""Integrity-checked, explicitly selected offline reference editions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from importlib import resources
import json
from pathlib import PurePosixPath

from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt


class ReferenceError(ValueError):
    """A reference manifest or one of its declared assets is invalid."""


@dataclass(frozen=True, slots=True)
class ReferenceAsset:
    role: str
    package: str
    path: str
    media_type: str
    identity: ByteIdentity
    required: bool = True


@dataclass(frozen=True, slots=True)
class ReferenceEdition:
    reference_id: str
    edition_id: str
    schema_version: int
    assets: tuple[ReferenceAsset, ...]
    publisher: str | None = None
    source_url: str | None = None
    published_at: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None


@dataclass(frozen=True, slots=True)
class LoadedReference:
    edition: ReferenceEdition
    snapshot_identity: ByteIdentity

    def asset(self, role: str) -> ReferenceAsset:
        for asset in self.edition.assets:
            if asset.role == role:
                return asset
        raise ReferenceError(f"Undeclared reference role: {role}")

    def read(self, role: str, *, inputs: list[UsedInputReceipt] | None = None) -> bytes:
        asset = self.asset(role)
        try:
            data = resources.files(asset.package).joinpath("_resources", *asset.path.split("/")).read_bytes()
        except FileNotFoundError as exc:
            if asset.required:
                raise ReferenceError(f"Reference asset missing: {self.edition.reference_id}:{role}") from exc
            raise ReferenceError(f"Optional reference asset unavailable: {self.edition.reference_id}:{role}") from exc
        if ByteIdentity.of(data) != asset.identity:
            raise ReferenceError(f"Reference asset integrity mismatch: {self.edition.reference_id}:{role}")
        if inputs is not None:
            source_id = f"{self.edition.reference_id}:{self.edition.edition_id}:{role}"
            inputs.append(replace(
                UsedInputReceipt.for_payload(SourcePayload(data, asset.media_type, source_id), role),
                version=self.snapshot_identity,
            ))
        return data

    def validate_all(self) -> None:
        for asset in self.edition.assets:
            if asset.required:
                self.read(asset.role)


@dataclass(frozen=True, slots=True)
class ReferenceUse:
    """A verified semantic projection of an existing generic input receipt.

    The package manifest and exact resource bytes are checked on reconstruction.
    Neither a generic role such as "data" nor a caller-written source_id alone
    is sufficient to identify the consumed reference.
    """

    reference_id: str
    edition_id: str
    role: str
    identity: ByteIdentity
    snapshot_identity: ByteIdentity

    def manifest_entry(self) -> dict[str, object]:
        return {
            "reference_id": self.reference_id,
            "edition_id": self.edition_id,
            "role": self.role,
            "byte_identity": {"sha256": self.identity.sha256, "size": self.identity.size},
            "snapshot_identity": {
                "sha256": self.snapshot_identity.sha256, "size": self.snapshot_identity.size,
            },
        }


def qualified_reference_use(
    inputs: tuple[UsedInputReceipt, ...] | list[UsedInputReceipt],
    *,
    package: str,
    role: str,
) -> ReferenceUse:
    """Require exactly one versioned, byte-verified use of a declared reference role."""
    reference_id = package.removeprefix("stratbox.shared.reference.")
    if not package.startswith("stratbox.shared.reference.") or not reference_id:
        raise ReferenceError("Invalid reference package")
    # Resolve the semantic reference ID from the package's trusted manifest,
    # rather than guessing it from the local role or asset filename.
    candidate = load_reference(package)
    reference_id = candidate.edition.reference_id
    relevant = []
    for item in inputs:
        if item.source_id is None or not item.source_id.startswith(reference_id + ":"):
            continue
        parts = item.source_id.split(":")
        if len(parts) != 3 or not all(parts):
            raise ReferenceError("Malformed reference input source identity")
        if parts[2] == role:
            relevant.append((item, parts[1]))
    if len(relevant) != 1:
        raise ReferenceError(f"Expected exactly one qualified reference use: {reference_id}:{role}")
    receipt, edition_id = relevant[0]
    selected = load_reference(package, edition_id=edition_id)
    asset = selected.asset(role)
    if (receipt.role != role or receipt.identity != asset.identity
            or receipt.version != selected.snapshot_identity
            or receipt.media_type != asset.media_type
            or receipt.availability != "inline"):
        raise ReferenceError(f"Unqualified reference receipt: {reference_id}:{role}")
    selected.read(role)
    return ReferenceUse(reference_id, edition_id, role, asset.identity, selected.snapshot_identity)


def _safe_path(path: str) -> str:
    if not isinstance(path, str) or not path or "\\" in path or path.startswith("/"):
        raise ReferenceError("Invalid reference asset path")
    parts = PurePosixPath(path).parts
    if any(part in {".", "..", ""} for part in parts) or str(PurePosixPath(path)) != path:
        raise ReferenceError("Reference asset path escapes package root")
    return path


def load_reference(package: str, *, edition_id: str | None = None) -> LoadedReference:
    """Use the active manifest edition or an explicitly named packaged edition."""
    if not package.startswith("stratbox.shared.reference."):
        raise ReferenceError("Reference package must be an owned reference package")
    try:
        raw = resources.files(package).joinpath("_resources", "manifest.json").read_bytes()
    except FileNotFoundError as exc:
        raise ReferenceError(f"Missing reference manifest: {package}") from exc
    try:
        index = json.loads(raw)
        if index["manifest_schema_version"] != 1:
            raise ReferenceError("Unsupported reference manifest schema")
        selected = edition_id or index["active_edition"]
        matches = [entry for entry in index["editions"] if entry["edition_id"] == selected]
        if len(matches) != 1:
            raise ReferenceError("Missing or duplicated reference edition")
        entry = matches[0]
        roles, paths, assets = set(), set(), []
        for item in entry["assets"]:
            role, path = item["role"], _safe_path(item["path"])
            if not isinstance(role, str) or not role or role in roles or path in paths:
                raise ReferenceError("Duplicate/invalid asset role or path")
            roles.add(role)
            paths.add(path)
            mandatory = item.get("required", True)
            if type(mandatory) is not bool:
                raise ReferenceError("Reference asset required flag must be a boolean")
            assets.append(ReferenceAsset(role, package, path, item["media_type"],
                ByteIdentity(item["sha256"], item["size"]), mandatory))
        if not assets:
            raise ReferenceError("Empty reference edition")
        reference_id = index["reference_id"]
        if not isinstance(reference_id, str) or not reference_id.startswith("reference."):
            raise ReferenceError("Invalid reference identity")
        if not isinstance(selected, str) or not selected:
            raise ReferenceError("Invalid edition identity")
        edition = ReferenceEdition(reference_id, selected, 1, tuple(assets),
            entry.get("publisher"), entry.get("source_url"),
            date.fromisoformat(entry["published_at"]) if entry.get("published_at") else None,
            date.fromisoformat(entry["effective_from"]) if entry.get("effective_from") else None,
            date.fromisoformat(entry["effective_to"]) if entry.get("effective_to") else None)
        if edition.effective_from and edition.effective_to and edition.effective_from > edition.effective_to:
            raise ReferenceError("Reference edition has an inverted validity interval")
        snapshot_manifest = {
            "reference_id": reference_id, "edition_id": selected, "schema_version": 1,
            "publisher": edition.publisher, "source_url": edition.source_url,
            "published_at": edition.published_at,
            "effective_from": edition.effective_from, "effective_to": edition.effective_to,
            "assets": [{"role": asset.role, "path": asset.path,
                        "sha256": asset.identity.sha256, "size": asset.identity.size,
                        "media_type": asset.media_type, "required": asset.required}
                       for asset in sorted(assets, key=lambda asset: (asset.role, asset.path))],
        }
        return LoadedReference(edition, ByteIdentity.of(canonical_manifest_bytes(snapshot_manifest)))
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        if isinstance(exc, ReferenceError):
            raise
        raise ReferenceError(f"Malformed reference manifest: {package}") from exc
