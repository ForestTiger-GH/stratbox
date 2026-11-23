"""Immutable composition of heterogeneous materials and explicit batch outcomes.

Member identities and semantic contracts describe the logical collection. Store
addresses and provider selections are supplied separately when packaging or
publishing it. A complete selected batch does not imply complete source history.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from unicodedata import normalize

from stratbox.shared.data.lineage import input_from, input_value
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import SnapshotCoverage, identifier, coverage_value, coverage_from
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.source_publications import SourceAssetIdentity

MAX_MANIFEST_BYTES = 8 * 1024 * 1024


def _identity(value):
    return {"sha256": value.sha256, "size": value.size}


def _read_identity(value):
    if (not isinstance(value, dict) or set(value) != {"sha256", "size"}
            or not isinstance(value["sha256"], str) or type(value["size"]) is not int):
        raise ValueError("collection.identity_invalid")
    return ByteIdentity(value["sha256"], value["size"])


def _name(value):
    if (not isinstance(value, str) or not 0 < len(value) <= 512 or "\\" in value or ":" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError("collection.name_invalid")
    return normalize("NFC", value).casefold()


@dataclass(frozen=True, slots=True)
class CollectionMember:
    key: str
    name: str
    contract: DataContract
    identity: ByteIdentity
    media_type: str = "application/octet-stream"
    source_asset: SourceAssetIdentity | None = None
    descriptor_identity: ByteIdentity | None = None

    def __post_init__(self):
        identifier(self.key)
        _name(self.name)
        if not isinstance(self.contract, DataContract) or not isinstance(self.identity, ByteIdentity):
            raise ValueError("collection.member_invalid")
        _read_identity(_identity(self.identity))
        SourcePayload(b"", self.media_type)
        if self.source_asset is not None and not isinstance(self.source_asset, SourceAssetIdentity):
            raise ValueError("collection.asset_invalid")
        if self.descriptor_identity is not None and not isinstance(self.descriptor_identity, ByteIdentity):
            raise ValueError("collection.descriptor_invalid")
        if self.descriptor_identity is not None:
            _read_identity(_identity(self.descriptor_identity))


@dataclass(frozen=True, slots=True)
class CollectionDisposition:
    key: str
    status: str
    diagnostic: str | None = None

    def __post_init__(self):
        identifier(self.key)
        if self.status not in {"completed", "failed", "unsupported", "not_attempted", "unknown"}:
            raise ValueError("collection.status_invalid")
        if self.diagnostic is not None:
            identifier(self.diagnostic)


@dataclass(frozen=True, slots=True)
class CollectionManifest:
    collection_id: str
    version_id: str
    members: tuple[CollectionMember, ...]
    dispositions: tuple[CollectionDisposition, ...]
    coverage: SnapshotCoverage
    inputs: tuple[UsedInputReceipt, ...] = ()

    def __post_init__(self):
        identifier(self.collection_id)
        identifier(self.version_id)
        if (not isinstance(self.members, tuple) or not isinstance(self.dispositions, tuple)
                or any(not isinstance(x, CollectionMember) for x in self.members)
                or any(not isinstance(x, CollectionDisposition) for x in self.dispositions)
                or not self.dispositions or len(self.dispositions) > 100_000
                or not isinstance(self.coverage, SnapshotCoverage)):
            raise ValueError("collection.manifest_invalid")
        keys = tuple(x.key for x in self.dispositions)
        names = {_name(x.name) for x in self.members}
        if (len(set(keys)) != len(keys) or len(names) != len(self.members)
                or len({x.key for x in self.members}) != len(self.members)):
            raise ValueError("collection.duplicate_member")
        if tuple(x.key for x in self.members) != tuple(x.key for x in self.dispositions if x.status == "completed"):
            raise ValueError("collection.completion_mismatch")
        if any("/".join(name.split("/")[:i]) in names for name in names
               for i in range(1, len(name.split("/")))):
            raise ValueError("collection.name_conflict")
        if not isinstance(self.inputs, tuple):
            raise ValueError("collection.inputs_invalid")
        for item in self.inputs:
            if not isinstance(item, UsedInputReceipt):
                raise ValueError("collection.inputs_invalid")
            input_from(input_value(item))

    @property
    def complete(self) -> bool:
        return all(item.status == "completed" for item in self.dispositions)

    @property
    def identity(self) -> ByteIdentity:
        value = collection_value(self)
        for item in value["inputs"]:
            item.pop("availability")
        return ByteIdentity.of(canonical_manifest_bytes(value))


def collection_value(value: CollectionManifest) -> dict:
    return {
        "schema": "stratbox.material-collection.v1",
        "collection_id": value.collection_id, "version_id": value.version_id,
        "members": [{
            "key": x.key, "name": x.name,
            "contract": {"schema_id": x.contract.schema_id, "version": x.contract.version,
                         "role": x.contract.role.value if x.contract.role is not None else None},
            "identity": _identity(x.identity), "media_type": x.media_type,
            "source_asset": None if x.source_asset is None else {
                "series_id": x.source_asset.series_id, "issue_id": x.source_asset.issue_id,
                "asset_id": x.source_asset.asset_id},
            "descriptor_identity": _identity(x.descriptor_identity) if x.descriptor_identity is not None else None,
        } for x in value.members],
        "dispositions": [{"key": x.key, "status": x.status, "diagnostic": x.diagnostic}
                         for x in value.dispositions],
        "coverage": coverage_value(value.coverage),
        "inputs": [input_value(x) for x in value.inputs],
    }


def encode_collection(value: CollectionManifest) -> bytes:
    if not isinstance(value, CollectionManifest):
        raise ValueError("collection.manifest_invalid")
    data = canonical_manifest_bytes(collection_value(value))
    if len(data) > MAX_MANIFEST_BYTES:
        raise ValueError("collection.manifest_limit")
    return data


def decode_collection(data: bytes) -> CollectionManifest:
    if not isinstance(data, bytes) or len(data) > MAX_MANIFEST_BYTES:
        raise ValueError("collection.manifest_limit")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("collection.duplicate_key")
            result[key] = value
        return result
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs)
        if set(value) != {"schema", "collection_id", "version_id", "members", "dispositions", "coverage", "inputs"} or value["schema"] != "stratbox.material-collection.v1":
            raise ValueError("collection.schema_invalid")
        members = []
        for item in value["members"]:
            if set(item) != {"key", "name", "contract", "identity", "media_type", "source_asset", "descriptor_identity"}:
                raise ValueError("collection.member_invalid")
            contract = item["contract"]
            if set(contract) != {"schema_id", "version", "role"}:
                raise ValueError("collection.contract_invalid")
            members.append(CollectionMember(item["key"], item["name"],
                DataContract(contract["schema_id"], contract["version"],
                             DataRole(contract["role"]) if contract["role"] is not None else None),
                _read_identity(item["identity"]), item["media_type"],
                SourceAssetIdentity(**item["source_asset"]) if item["source_asset"] is not None else None,
                _read_identity(item["descriptor_identity"]) if item["descriptor_identity"] is not None else None))
        result = CollectionManifest(value["collection_id"], value["version_id"], tuple(members),
            tuple(CollectionDisposition(**item) for item in value["dispositions"]),
            coverage_from(value["coverage"]), tuple(input_from(item) for item in value["inputs"]))
        if encode_collection(result) != data:
            raise ValueError("collection.manifest_noncanonical")
        return result
    except (KeyError, TypeError, AttributeError, UnicodeError, RecursionError) as error:
        raise ValueError("collection.manifest_invalid") from error


__all__ = ("CollectionMember", "CollectionDisposition", "CollectionManifest",
           "collection_value", "encode_collection", "decode_collection")
