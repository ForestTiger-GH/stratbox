from __future__ import annotations

from dataclasses import dataclass, field

from .evidence import ByteIdentity, SourcePayload

CSV = "text/csv"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass(frozen=True, slots=True)
class Representation:
    profile_id: str
    version: int
    media_type: str
    data: bytes
    encoding: str | None = None
    identity: ByteIdentity = field(init=False)

    def __post_init__(self) -> None:
        if not self.profile_id or self.version < 1:
            raise ValueError("Invalid representation profile")
        payload = SourcePayload(self.data, self.media_type)
        object.__setattr__(self, "data", payload.data)
        object.__setattr__(self, "identity", payload.identity)
