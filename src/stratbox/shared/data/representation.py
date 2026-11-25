from __future__ import annotations

from dataclasses import dataclass, field

from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.data.assessment import ValueEvidence

CSV = "text/csv"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass(frozen=True, slots=True)
class Representation:
    profile_id: str
    version: int
    media_type: str
    data: bytes
    encoding: str | None = None
    evidence: ValueEvidence | None = None
    identity: ByteIdentity = field(init=False)

    def __post_init__(self) -> None:
        if (not isinstance(self.profile_id, str) or not self.profile_id
                or type(self.version) is not int or self.version < 1
                or self.encoding is not None and (not isinstance(self.encoding, str) or not self.encoding)):
            raise ValueError("Invalid representation profile")
        if self.evidence is not None and not isinstance(self.evidence, ValueEvidence):
            raise ValueError("representation.evidence_invalid")
        payload = SourcePayload(self.data, self.media_type)
        object.__setattr__(self, "data", payload.data)
        object.__setattr__(self, "identity", payload.identity)
