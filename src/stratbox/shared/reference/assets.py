"""Integrity-checked, explicitly selected offline reference editions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from importlib import resources
import json
from pathlib import PurePosixPath
from collections.abc import Mapping
import re

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
    publisher: str | None = None
    curator: str | None = None
    source_url: str | None = None
    origin_kind: str | None = None


@dataclass(frozen=True, slots=True)
class ReferenceEdition:
    reference_id: str
    edition_id: str
    schema_version: int
    assets: tuple[ReferenceAsset, ...]
    publisher: str | None = None
    source_url: str | None = None
    curator: str | None = None
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


# One independently declared family contract; all readers and build tools use it.
REFERENCE_REQUIRED_ROLES: dict[str, frozenset[str]] = {
    "banks": frozenset({"official_xlsx", "aliases", "default_selection", "legacy_selection"}),
    "okved2": frozenset({"data", "meta", "structure"}),
    "geography": frozenset({"aliases"}),
}
_EDITION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}\Z")
_ROLE_ID = re.compile(r"[a-z][a-z0-9_]*\Z")
_ORIGINS = frozenset({"published_source", "curated_policy", "unknown"})


def _nullable_text(value: object, label: str) -> str | None:
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise ReferenceError(f"Invalid reference {label}")
    return value


def _edition_date(value: object, field: str) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ReferenceError(f"Invalid reference date {field}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ReferenceError(f"Invalid reference date {field}") from exc


def parse_reference_manifest(package: str, document: bytes | Mapping[str, object]) -> tuple[str, tuple[ReferenceEdition, ...]]:
    """Pure, all-edition manifest admission, shared by runtime, stage and wheel.

    Returns the selected active edition ID and every independently validated
    edition. Does no IO and makes no claims about publisher authenticity.
    """
    prefix = "stratbox.shared.reference."
    if not isinstance(package, str) or not package.startswith(prefix):
        raise ReferenceError("Reference package must be an owned reference package")
    family = package[len(prefix):]
    if family not in REFERENCE_REQUIRED_ROLES:
        raise ReferenceError(f"Reference family has no declared role contract: {family}")
    try:
        document = json.loads(document) if isinstance(document, bytes) else document
        if not isinstance(document, Mapping) or type(document.get("manifest_schema_version")) is not int:
            raise ReferenceError("Invalid reference manifest envelope")
        if document["manifest_schema_version"] != 1:
            raise ReferenceError("Unsupported reference manifest schema")
        reference_id = document["reference_id"]
        if not isinstance(reference_id, str) or not reference_id.startswith("reference."):
            raise ReferenceError("Invalid reference identity")
        active = document["active_edition"]
        records = document["editions"]
        if not isinstance(active, str) or not _EDITION_ID.fullmatch(active):
            raise ReferenceError("Invalid reference active edition")
        if not isinstance(records, list) or not records:
            raise ReferenceError("Reference manifest requires editions")
        editions, edition_names = [], set()
        for entry in records:
            if not isinstance(entry, Mapping):
                raise ReferenceError("Invalid reference edition record")
            eid = entry["edition_id"]
            if not isinstance(eid, str) or not _EDITION_ID.fullmatch(eid) or eid in edition_names:
                raise ReferenceError("Missing, malformed or duplicate reference edition ID")
            edition_names.add(eid)
            declared = entry["assets"]
            if not isinstance(declared, list) or not declared:
                raise ReferenceError("Reference edition must declare assets")
            roles, paths, assets = set(), set(), []
            for item in declared:
                if not isinstance(item, Mapping):
                    raise ReferenceError("Invalid reference asset")
                role, path = item["role"], _safe_path(item["path"])
                if (not isinstance(role, str) or not _ROLE_ID.fullmatch(role)
                        or role in roles or path in paths):
                    raise ReferenceError("Duplicate or invalid reference asset role/path")
                roles.add(role)
                paths.add(path)
                required = item.get("required", True)
                if type(required) is not bool:
                    raise ReferenceError("Reference asset required flag must be boolean")
                size = item["size"]
                if type(size) is not int or size < 0:
                    raise ReferenceError("Reference asset size must be a nonnegative integer")
                media_type = item["media_type"]
                if not isinstance(media_type, str) or "/" not in media_type:
                    raise ReferenceError("Invalid reference asset media type")
                origin_kind = _nullable_text(item.get("origin_kind"), "origin_kind")
                if origin_kind is not None and origin_kind not in _ORIGINS:
                    raise ReferenceError("Unknown reference asset origin kind")
                assets.append(ReferenceAsset(
                    role, package, path, media_type,
                    ByteIdentity(item["sha256"], size), required,
                    _nullable_text(item.get("publisher"), "publisher"),
                    _nullable_text(item.get("curator"), "curator"),
                    _nullable_text(item.get("source_url"), "source_url"),
                    origin_kind,
                ))
            if not REFERENCE_REQUIRED_ROLES[family].issubset(roles):
                raise ReferenceError(f"Incomplete {family} reference roles: "
                                     f"{sorted(REFERENCE_REQUIRED_ROLES[family] - roles)}")
            start = _edition_date(entry.get("effective_from"), "effective_from")
            end = _edition_date(entry.get("effective_to"), "effective_to")
            if start and end and start > end:
                raise ReferenceError("Inverted reference edition validity interval")
            editions.append(ReferenceEdition(
                reference_id, eid, 1, tuple(assets),
                _nullable_text(entry.get("publisher"), "publisher"),
                _nullable_text(entry.get("source_url"), "source_url"),
                _nullable_text(entry.get("curator"), "curator"),
                _edition_date(entry.get("published_at"), "published_at"), start, end,
            ))
        if active not in edition_names:
            raise ReferenceError("Active reference edition is not declared")
        return active, tuple(editions)
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError) as exc:
        if isinstance(exc, ReferenceError):
            raise
        raise ReferenceError(f"Malformed reference manifest: {package}") from exc


def load_reference(package: str, *, edition_id: str | None = None) -> LoadedReference:
    """Resolve a fully validated reference edition and reproducible snapshot."""
    try:
        raw = resources.files(package).joinpath("_resources", "manifest.json").read_bytes()
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise ReferenceError(f"Missing reference manifest: {package}") from exc
    active, editions = parse_reference_manifest(package, raw)
    selected = edition_id if edition_id is not None else active
    matching = [entry for entry in editions if entry.edition_id == selected]
    if len(matching) != 1:
        raise ReferenceError(f"Unknown reference edition: {selected}")
    edition = matching[0]
    snapshot_manifest = {
        "snapshot_schema": 2,
        "reference_id": edition.reference_id,
        "edition_id": edition.edition_id,
        "publisher": edition.publisher,
        "curator": edition.curator,
        "source_url": edition.source_url,
        "published_at": edition.published_at,
        "effective_from": edition.effective_from,
        "effective_to": edition.effective_to,
        "assets": [{
            "role": asset.role, "path": asset.path, "media_type": asset.media_type,
            "sha256": asset.identity.sha256, "size": asset.identity.size,
            "required": asset.required, "publisher": asset.publisher,
            "curator": asset.curator, "source_url": asset.source_url,
            "origin_kind": asset.origin_kind,
        } for asset in sorted(edition.assets, key=lambda value: (value.role, value.path))],
    }
    return LoadedReference(edition, ByteIdentity.of(canonical_manifest_bytes(snapshot_manifest)))
