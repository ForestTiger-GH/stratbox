"""Portable artifact metadata, independent of a store, operation or data role.

The representation's bytes remain separate from their semantic descriptor.
Neither a filename nor a media type establishes the represented data contract.
References are caller-owned integrity expectations, not origin attestations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json

from stratbox.shared.data.datasets import ComputationReceipt, DatasetVersion
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import MaterialReference, SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.source_publications import SourceAssetIdentity

MAX_DESCRIPTOR_BYTES = 8 * 1024 * 1024


def _identity(value: ByteIdentity | None):
    return None if value is None else {"sha256": value.sha256, "size": value.size}


def _read_identity(value):
    if not isinstance(value, dict) or set(value) != {"sha256", "size"} or type(value["size"]) is not int:
        raise ValueError("material.identity_invalid")
    return ByteIdentity(value["sha256"], value["size"])


def _input(value: UsedInputReceipt):
    return {"role": value.role, "identity": _identity(value.identity), "media_type": value.media_type,
            "availability": value.availability, "source_id": value.source_id,
            "container": _identity(value.container), "member": value.member, "version": _identity(value.version)}


def _read_input(value):
    if not isinstance(value, dict) or set(value) != {
        "role", "identity", "media_type", "availability", "source_id", "container", "member", "version"
    } or not isinstance(value["role"], str) or not value["role"] or value["availability"] not in {"inline", "reference_only"}:
        raise ValueError("material.lineage_invalid")
    if (value["container"] is None) != (value["member"] is None):
        raise ValueError("material.lineage_invalid")
    if not isinstance(value["media_type"], str) or any(
        value[key] is not None and (not isinstance(value[key], str) or not value[key])
        for key in ("source_id", "member")
    ):
        raise ValueError("material.lineage_invalid")
    SourcePayload(b"", value["media_type"])
    return UsedInputReceipt(
        value["role"], _read_identity(value["identity"]), value["media_type"], value["availability"],
        value["source_id"], _read_identity(value["container"]) if value["container"] else None,
        value["member"], _read_identity(value["version"]) if value["version"] else None,
    )


def _computation(value: ComputationReceipt | None, depth=0):
    if value is None:
        return None
    if depth > 32 or len(value.parents) > 256:
        raise ValueError("material.lineage_limit")
    v = value.version
    if ByteIdentity.of(v.manifest) != v.identity:
        raise ValueError("material.lineage_identity_mismatch")
    result = {"version": {"dataset_id": v.dataset_id, "release_id": v.release_id,
            "method_version": v.method_version, "manifest_version": v.manifest_version,
            "identity": _identity(v.identity), "manifest": v.manifest.decode("utf-8")},
            "output": _identity(value.output), "inputs": [_input(x) for x in value.inputs],
            "computation_id": _identity(value.computation_id),
            "parents": [[name, _computation(parent, depth + 1)] for name, parent in value.parents]}
    # Validate producer-owned values as strictly as retained values.
    _validate_computation_record(result)
    return result


def _validate_computation_record(value):
    v = value["version"]
    if (not isinstance(v, dict) or set(v) != {"dataset_id", "release_id", "method_version", "manifest_version", "identity", "manifest"}
            or any(not isinstance(v[key], str) or not v[key] for key in ("dataset_id", "release_id", "method_version", "manifest"))
            or type(v["manifest_version"]) is not int or v["manifest_version"] != 1
            or not isinstance(value["inputs"], list) or not isinstance(value["parents"], list)):
        raise ValueError("material.lineage_invalid")
    names = set()
    for pair in value["parents"]:
        if (not isinstance(pair, list) or len(pair) != 2 or not isinstance(pair[0], str)
                or not pair[0] or pair[0] in names or pair[1] is None):
            raise ValueError("material.lineage_invalid")
        names.add(pair[0])
    manifest = _json(v["manifest"].encode("utf-8"))
    if not isinstance(manifest, dict) or set(manifest) != {
        "manifest_version", "dataset_id", "release_id", "method_version", "inputs", "parameters", "arguments", "resources", "result"
    } or any(manifest[key] != v[key] for key in ("manifest_version", "dataset_id", "release_id", "method_version")):
        raise ValueError("material.lineage_manifest_mismatch")
    if any(not isinstance(manifest[key], dict) for key in ("parameters", "arguments", "resources")):
        raise ValueError("material.lineage_manifest_mismatch")
    if manifest["result"] != value["output"]:
        raise ValueError("material.lineage_manifest_mismatch")
    inputs = tuple(_read_input(x) for x in value["inputs"])
    expected = [{"role": x.role, "sha256": x.identity.sha256, "size": x.identity.size,
                 "container": x.container.sha256 if x.container else None, "member": x.member,
                 **({"version": x.version.sha256} if x.version else {})} for x in inputs]
    if manifest["inputs"] != expected or canonical_manifest_bytes(manifest) != v["manifest"].encode("utf-8"):
        raise ValueError("material.lineage_manifest_mismatch")


def _read_computation(value, depth=0):
    if value is None:
        return None
    if depth > 32 or not isinstance(value, dict) or set(value) != {
        "version", "output", "inputs", "computation_id", "parents"
    } or not isinstance(value["parents"], list) or len(value["parents"]) > 256:
        raise ValueError("material.lineage_invalid")
    _validate_computation_record(value)
    v = value["version"]
    version = DatasetVersion(v["dataset_id"], v["release_id"], v["method_version"],
                             v["manifest_version"], _read_identity(v["identity"]), v["manifest"].encode("utf-8"))
    if ByteIdentity.of(version.manifest) != version.identity:
        raise ValueError("material.lineage_identity_mismatch")
    return ComputationReceipt(version, _read_identity(value["output"]), tuple(_read_input(x) for x in value["inputs"]),
                              _read_identity(value["computation_id"]),
                              tuple((name, _read_computation(parent, depth + 1)) for name, parent in value["parents"]))


def _contract(value: DataContract):
    return {"schema_id": value.schema_id, "version": value.version,
            "role": value.role.value if value.role is not None else None}


def _read_contract(value):
    if not isinstance(value, dict) or set(value) != {"schema_id", "version", "role"}:
        raise ValueError("material.contract_invalid")
    return DataContract(value["schema_id"], value["version"], DataRole(value["role"]) if value["role"] is not None else None)


def _json(data: bytes):
    if not isinstance(data, bytes) or len(data) > MAX_DESCRIPTOR_BYTES:
        raise ValueError("material.descriptor_limit")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("material.duplicate_key")
            result[key] = value
        return result
    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs)


@dataclass(frozen=True, slots=True)
class MaterialArtifact:
    """A complete encoded value. Series, issue, bytes and storage are distinct."""
    contract: DataContract
    representation: Representation
    inputs: tuple[UsedInputReceipt, ...] = ()
    series_id: str | None = None
    source_asset: SourceAssetIdentity | None = None
    computation: ComputationReceipt | None = None

    def __post_init__(self):
        if not isinstance(self.contract, DataContract) or not isinstance(self.representation, Representation):
            raise ValueError("material.artifact_invalid")
        if not isinstance(self.inputs, tuple) or any(not isinstance(x, UsedInputReceipt) for x in self.inputs):
            raise ValueError("material.lineage_invalid")
        for receipt in self.inputs:
            _read_input(_input(receipt))
        if self.series_id is not None and (not isinstance(self.series_id, str) or not self.series_id):
            raise ValueError("material.series_invalid")
        if self.source_asset is not None and (
            not isinstance(self.source_asset, SourceAssetIdentity) or self.series_id != self.source_asset.series_id
        ):
            raise ValueError("material.source_identity_mismatch")
        if self.computation is not None and self.computation.output != self.representation.identity:
            raise ValueError("material.computation_output_mismatch")

    @property
    def descriptor(self) -> bytes:
        rep = self.representation
        asset = self.source_asset
        data = canonical_manifest_bytes({
            "schema": "stratbox.material.v1", "contract": _contract(self.contract),
            "representation": {"profile_id": rep.profile_id, "version": rep.version,
                "media_type": rep.media_type, "encoding": rep.encoding, "identity": _identity(rep.identity)},
            "series_id": self.series_id,
            "source_asset": None if asset is None else {"series_id": asset.series_id,
                "issue_id": asset.issue_id, "asset_id": asset.asset_id},
            "inputs": [_input(x) for x in self.inputs], "computation": _computation(self.computation),
        })
        if len(data) > MAX_DESCRIPTOR_BYTES:
            raise ValueError("material.descriptor_limit")
        return data

    @property
    def identity(self) -> ByteIdentity:
        """Descriptor identity; physical paths and backend IDs are excluded."""
        return ByteIdentity.of(self.descriptor)


def restore_artifact(descriptor: bytes, data: bytes) -> MaterialArtifact:
    """Decode a bounded descriptor and verify its complete representation."""
    try:
        obj = _json(descriptor)
        if set(obj) != {"schema", "contract", "representation", "series_id", "source_asset", "inputs", "computation"} or obj["schema"] != "stratbox.material.v1":
            raise ValueError("material.descriptor_schema_invalid")
        rep = obj["representation"]
        if set(rep) != {"profile_id", "version", "media_type", "encoding", "identity"}:
            raise ValueError("material.representation_invalid")
        value = Representation(rep["profile_id"], rep["version"], rep["media_type"], data, rep["encoding"])
        if value.identity != _read_identity(rep["identity"]):
            raise ValueError("material.identity_mismatch")
        result = MaterialArtifact(_read_contract(obj["contract"]), value,
            tuple(_read_input(x) for x in obj["inputs"]), obj["series_id"],
            SourceAssetIdentity(**obj["source_asset"]) if obj["source_asset"] is not None else None,
            _read_computation(obj["computation"]))
        if result.descriptor != descriptor:
            raise ValueError("material.descriptor_noncanonical")
        return result
    except (KeyError, TypeError, AttributeError, UnicodeError, RecursionError) as error:
        raise ValueError("material.descriptor_invalid") from error


def _reference(value: MaterialReference):
    return {"locator": value.locator, "store_id": value.store_id, "identity": _identity(value.identity),
            "media_type": value.media_type, "source_id": value.source_id, "revision": value.revision,
            "charset": value.charset, "store_scope": value.store_scope}


def _read_reference(value):
    if not isinstance(value, dict) or set(value) != {"locator", "store_id", "identity", "media_type", "source_id", "revision", "charset", "store_scope"}:
        raise ValueError("material.reference_invalid")
    if any(not isinstance(value[key], str) or not value[key] for key in ("locator", "store_id", "media_type")) or any(
        value[key] is not None and (not isinstance(value[key], str) or not value[key])
        for key in ("source_id", "revision", "charset", "store_scope")
    ):
        raise ValueError("material.reference_invalid")
    SourcePayload(b"", value["media_type"])
    return MaterialReference(**{**value, "identity": _read_identity(value["identity"])})


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    """Pinned bytes and descriptor; the two can be resolved through different stores."""
    material: MaterialReference
    descriptor: MaterialReference
    contract: DataContract
    identity: ByteIdentity

    def __post_init__(self):
        if (not isinstance(self.material, MaterialReference) or not isinstance(self.descriptor, MaterialReference)
                or not isinstance(self.contract, DataContract) or self.descriptor.identity != self.identity
                or self.descriptor.media_type != "application/json"):
            raise ValueError("material.reference_invalid")
        _read_reference(_reference(self.material))
        _read_reference(_reference(self.descriptor))

    def to_bytes(self) -> bytes:
        return canonical_manifest_bytes({"schema": "stratbox.artifact-reference.v1",
            "material": _reference(self.material), "descriptor": _reference(self.descriptor),
            "contract": _contract(self.contract), "identity": _identity(self.identity)})

    @classmethod
    def from_bytes(cls, data: bytes) -> ArtifactReference:
        try:
            value = _json(data)
            if set(value) != {"schema", "material", "descriptor", "contract", "identity"} or value["schema"] != "stratbox.artifact-reference.v1":
                raise ValueError("material.reference_schema_invalid")
            return cls(_read_reference(value["material"]), _read_reference(value["descriptor"]),
                       _read_contract(value["contract"]), _read_identity(value["identity"]))
        except (KeyError, TypeError, AttributeError, UnicodeError) as error:
            raise ValueError("material.reference_invalid") from error
