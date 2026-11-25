"""Logical source versions and chained transitions, separate from byte storage."""
from dataclasses import dataclass
import re

from stratbox.shared.identity import ByteIdentity


@dataclass(frozen=True, slots=True)
class OriginalVersion:
    source_id: str
    identity: ByteIdentity
    transition_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.source_id, str) or not 0 < len(self.source_id) <= 128 or not isinstance(self.identity, ByteIdentity):
            raise ValueError("source.version_identity_invalid")
        if self.transition_id is not None and (not isinstance(self.transition_id, str)
                or re.fullmatch(r"[0-9a-f]{64}", self.transition_id) is None):
            raise ValueError("source.transition_invalid")


@dataclass(frozen=True, slots=True)
class OriginalVersionComparison:
    source_id: str
    state: str
    reason: str
    old_identity: ByteIdentity | None
    new_identity: ByteIdentity
    transition_id: str | None = None
    previous_transition_id: str | None = None

    @property
    def changed(self):
        return self.state in {"first_seen", "new_release", "new_asset", "revised"}
