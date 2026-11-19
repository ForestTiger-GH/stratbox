"""Pure byte-version comparison; independent of publisher and economic data."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.core.execution import (
    ExecutionContext, OperationDefinition, OperationFailure, OperationResult, run,
)

Change = Literal["first_seen", "new_release", "revised", "unchanged", "indeterminate"]
BaselineState = Literal["available", "confirmed_absent", "unavailable"]


@dataclass(frozen=True, slots=True)
class OriginalVersion:
    """One logical source asset, not one URL or one publication series."""

    source_id: str
    identity: ByteIdentity
    transition_id: str | None = None

    def __post_init__(self):
        if not self.source_id or len(self.source_id) > 128 or not isinstance(self.identity, ByteIdentity):
            raise ValueError("Invalid original version")
        if self.transition_id is not None and (
            len(self.transition_id) != 64
            or any(c not in "0123456789abcdef" for c in self.transition_id)
        ):
            raise ValueError("Invalid original transition")


@dataclass(frozen=True, slots=True)
class CompareOriginalVersionsRequest:
    candidate: OriginalVersion
    baseline_state: BaselineState
    baseline: OriginalVersion | None = None
    # An authoritative previous inventory permits NEW_RELEASE rather than FIRST_SEEN.
    prior_inventory_identity: str | None = None

    def __post_init__(self):
        if self.baseline_state not in {"available", "confirmed_absent", "unavailable"}:
            raise ValueError("Invalid baseline qualification")
        if (self.baseline_state == "available") != (self.baseline is not None):
            raise ValueError("Baseline and qualification disagree")
        if self.baseline is not None and self.baseline.source_id != self.candidate.source_id:
            raise ValueError("Cannot compare different logical assets")
        if self.prior_inventory_identity is not None and (
            len(self.prior_inventory_identity) != 64
            or any(c not in "0123456789abcdef" for c in self.prior_inventory_identity)
        ):
            raise ValueError("Invalid previous inventory identity")


@dataclass(frozen=True, slots=True)
class OriginalVersionComparison:
    source_id: str
    state: Change
    reason: str
    old_identity: ByteIdentity | None
    new_identity: ByteIdentity
    transition_id: str | None = None

    @property
    def changed(self) -> bool:
        return self.state in {"first_seen", "new_release", "revised"}


COMPARE = OperationDefinition(
    "source.compare_original_versions", 1, "original-byte-comparison-1",
    CompareOriginalVersionsRequest, OriginalVersionComparison,
)


def _compare(req: CompareOriginalVersionsRequest) -> OriginalVersionComparison:
    old = req.baseline
    candidate = req.candidate
    if req.baseline_state == "unavailable":
        state, reason = "indeterminate", "baseline.unavailable"
    elif old is not None and old.identity == candidate.identity:
        state, reason = "unchanged", "original.bytes_equal"
    elif old is not None:
        state, reason = "revised", "original.bytes_changed"
    elif req.prior_inventory_identity is not None:
        state, reason = "new_release", "inventory.confirmed_absent"
    else:
        state, reason = "first_seen", "original.first_observation"
    parent = (
        old.transition_id
        if old is not None and old.transition_id is not None
        else old.identity.sha256 if old is not None
        else req.prior_inventory_identity or "initial"
    )
    transition_id = None
    if state in {"first_seen", "new_release", "revised"}:
        transition_id = sha256(canonical_manifest_bytes({
            "contract": 1, "source_id": candidate.source_id,
            "state": state, "parent": parent,
            "old_sha256": old.identity.sha256 if old else None,
            "old_size": old.identity.size if old else None,
            "new_sha256": candidate.identity.sha256,
            "new_size": candidate.identity.size,
        })).hexdigest()
    return OriginalVersionComparison(
        candidate.source_id, state, reason,
        old.identity if old is not None else None, candidate.identity, transition_id,
    )


def compare_original_versions(
    request: CompareOriginalVersionsRequest, *,
    context: ExecutionContext | None = None,
) -> OperationResult[OriginalVersionComparison]:
    def work(req, invocation):
        invocation.stage("compare_original_versions")
        return _compare(req)
    return run(COMPARE, request, work, context=context)
