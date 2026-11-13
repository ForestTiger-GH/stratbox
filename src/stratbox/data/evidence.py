"""Identity and evidence for the exact bytes crossing an operation boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
import re
from typing import Literal

_DIGEST = re.compile(r"[0-9a-f]{64}", re.ASCII)
_MEDIA = re.compile(r"[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+", re.ASCII)
InputAvailability = Literal["inline", "reference_only"]


@dataclass(frozen=True, slots=True)
class ByteIdentity:
    sha256: str
    size: int

    def __post_init__(self) -> None:
        if not _DIGEST.fullmatch(self.sha256) or self.size < 0:
            raise ValueError("Invalid byte identity")

    @classmethod
    def of(cls, data: bytes) -> ByteIdentity:
        return cls(sha256(data).hexdigest(), len(data))


@dataclass(frozen=True, slots=True)
class SourcePayload:
    data: bytes
    media_type: str = "application/octet-stream"
    source_id: str | None = None
    expected_sha256: str | None = field(default=None, repr=False)
    identity: ByteIdentity = field(init=False)
    charset: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data, (bytes, bytearray, memoryview)):
            raise TypeError("Source data must be bytes-like")
        if not _MEDIA.fullmatch(self.media_type):
            raise ValueError("Invalid media type")
        data = bytes(self.data)
        identity = ByteIdentity.of(data)
        if self.expected_sha256 is not None and self.expected_sha256 != identity.sha256:
            raise ValueError("Source digest mismatch")
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "identity", identity)


@dataclass(frozen=True, slots=True)
class AcquisitionReceipt:
    source_id: str
    identity: ByteIdentity
    observed_at_utc: datetime
    media_type: str
    status_code: int
    safe_locator: str
    origin_assurance: Literal["provider_reported", "tls_host", "peer_bound"] = "provider_reported"
    request_sha256: str | None = None
    target_sha256: str | None = None
    etag: str | None = field(default=None, repr=False)
    reused: bool = False


@dataclass(frozen=True, slots=True)
class AcquiredSource:
    payload: SourcePayload
    receipt: AcquisitionReceipt

    def __post_init__(self) -> None:
        if (
            self.payload.identity != self.receipt.identity
            or self.payload.media_type != self.receipt.media_type
            or self.payload.source_id != self.receipt.source_id
        ):
            raise ValueError("Acquisition receipt disagrees with the exact payload")


@dataclass(frozen=True, slots=True)
class UsedInputReceipt:
    role: str
    identity: ByteIdentity
    media_type: str
    availability: InputAvailability
    source_id: str | None = None
    container: ByteIdentity | None = None
    member: str | None = None

    @classmethod
    def for_payload(
        cls,
        payload: SourcePayload,
        role: str,
        *,
        container: ByteIdentity | None = None,
        member: str | None = None,
    ) -> UsedInputReceipt:
        if (container is None) != (member is None):
            raise ValueError("Archive evidence requires a container and member")
        return cls(
            role,
            payload.identity,
            payload.media_type,
            "inline",
            payload.source_id,
            container,
            member,
        )


@dataclass(frozen=True, slots=True)
class StoredBytesReceipt:
    destination: str = field(repr=False)
    identity: ByteIdentity
    status: Literal["stored", "already_present", "failed", "unknown"]
    guarantee: Literal["atomic_create", "compare_and_replace", "read_back"]
    store_id: str
    diagnostic_code: str | None = None
    stage: Literal["preflight", "commit", "verify"] = "verify"
    observed_identity: ByteIdentity | None = None
    expected_revision: str | None = field(default=None, repr=False)
    effect_id: str | None = None


@dataclass(frozen=True, slots=True)
class PublicationReceipt:
    owner_id: str
    destination_id: str
    release_id: str
    transition_id: str
    identity: ByteIdentity
    confirmation: Literal["confirmed", "unknown", "rejected"]

    def __post_init__(self) -> None:
        if not all(
            (self.owner_id, self.destination_id, self.release_id, self.transition_id)
        ):
            raise ValueError("Publication identity is incomplete")
        if self.confirmation not in {"confirmed", "unknown", "rejected"}:
            raise ValueError("Invalid publication confirmation")
