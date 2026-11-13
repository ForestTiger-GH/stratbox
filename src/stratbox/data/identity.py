"""Canonical identities for manifests made from stable, typed inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import json
from typing import Mapping

from .evidence import ByteIdentity, UsedInputReceipt


def _canonical(value: object) -> object:
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            raise ValueError("Manifest timestamps require a timezone")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal) and value.is_finite():
        return format(value, "f")
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, Mapping) and all(isinstance(key, str) for key in value):
        return {key: _canonical(item) for key, item in value.items()}
    raise TypeError("Unsupported manifest value")


def canonical_manifest_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        _canonical(value),
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class DatasetVersion:
    dataset_id: str
    release_id: str
    method_version: str
    manifest_version: int
    identity: ByteIdentity
    manifest: bytes


def _input_manifest(inputs: tuple[UsedInputReceipt, ...]) -> list[dict[str, object]]:
    return [
        {
            "role": item.role,
            "sha256": item.identity.sha256,
            "size": item.identity.size,
            "container": item.container.sha256 if item.container else None,
            "member": item.member,
        }
        for item in inputs
    ]


def build_dataset_version(
    dataset_id: str,
    release_id: str,
    method_version: str,
    inputs: tuple[UsedInputReceipt, ...],
    result: ByteIdentity,
    *,
    parameters: Mapping[str, object] | None = None,
    resources: Mapping[str, str] | None = None,
) -> DatasetVersion:
    manifest = canonical_manifest_bytes(
        {
            "manifest_version": 1,
            "dataset_id": dataset_id,
            "release_id": release_id,
            "method_version": method_version,
            "inputs": _input_manifest(inputs),
            "parameters": parameters or {},
            "resources": resources or {},
            "result": {"sha256": result.sha256, "size": result.size},
        }
    )
    return DatasetVersion(
        dataset_id, release_id, method_version, 1, ByteIdentity.of(manifest), manifest
    )

def computation_identity(
    operation_id: str,
    contract_version: int,
    method_version: str,
    inputs: tuple[UsedInputReceipt, ...],
    *,
    parameters: Mapping[str, object] | None = None,
    resources: Mapping[str, str] | None = None,
    representation_profile: str | None = None,
    representation_options: Mapping[str, object] | None = None,
) -> ByteIdentity:
    """Identify an immutable computation. A cache owner separately checks access."""
    if representation_profile is None and representation_options:
        raise ValueError("Representation options require a profile")
    return ByteIdentity.of(canonical_manifest_bytes({
        "version": 1,
        "operation_id": operation_id,
        "contract_version": contract_version,
        "method_version": method_version,
        "inputs": [
            {**entry, "source_id": item.source_id, "media_type": item.media_type}
            for entry, item in zip(_input_manifest(inputs), inputs)
        ],
        "parameters": parameters or {},
        "resources": resources or {},
        "representation_profile": representation_profile,
        "representation_options": representation_options or {},
    }))
