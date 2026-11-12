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
            "inputs": [
                {
                    "role": item.role,
                    "sha256": item.identity.sha256,
                    "size": item.identity.size,
                    "container": item.container.sha256 if item.container else None,
                    "member": item.member,
                }
                for item in inputs
            ],
            "parameters": parameters or {},
            "resources": resources or {},
            "result": {"sha256": result.sha256, "size": result.size},
        }
    )
    return DatasetVersion(
        dataset_id, release_id, method_version, 1, ByteIdentity.of(manifest), manifest
    )
