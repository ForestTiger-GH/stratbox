"""Dataset versions, computation receipts and manifest identities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.evidence import UsedInputReceipt

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
            **({"version": item.version.sha256} if item.version else {}),
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
    arguments: Mapping[str, object] | None = None,
) -> DatasetVersion:
    manifest = canonical_manifest_bytes(
        {
            "manifest_version": 1,
            "dataset_id": dataset_id,
            "release_id": release_id,
            "method_version": method_version,
            "inputs": _input_manifest(inputs),
            "parameters": parameters or {},
            "arguments": arguments or {},
            "resources": resources or {},
            "result": {"sha256": result.sha256, "size": result.size},
        }
    )
    return DatasetVersion(
        dataset_id, release_id, method_version, 1, ByteIdentity.of(manifest), manifest
    )

def computation_identity(
    operation_id: str,
    method_id: str,
    inputs: tuple[UsedInputReceipt, ...],
    *,
    parameters: Mapping[str, object] | None = None,
    resources: Mapping[str, str] | None = None,
    arguments: Mapping[str, object] | None = None,
    representation_profile: str | None = None,
    representation_options: Mapping[str, object] | None = None,
) -> ByteIdentity:
    """Identify an immutable computation. A cache owner separately checks access."""
    if representation_profile is None and representation_options:
        raise ValueError("Representation options require a profile")
    return ByteIdentity.of(canonical_manifest_bytes({
        "operation_id": operation_id,
        "method_id": method_id,
        "inputs": [
            {**entry, "source_id": item.source_id, "media_type": item.media_type}
            for entry, item in zip(_input_manifest(inputs), inputs)
        ],
        "parameters": parameters or {},
        "arguments": arguments or {},
        "resources": resources or {},
        "representation_profile": representation_profile,
        "representation_options": representation_options or {},
    }))

@dataclass(frozen=True, slots=True)
class ComputationReceipt:
    version: DatasetVersion
    output: ByteIdentity
    inputs: tuple[UsedInputReceipt, ...]
    computation_id: ByteIdentity
    parents: tuple[tuple[str, ComputationReceipt], ...] = ()


