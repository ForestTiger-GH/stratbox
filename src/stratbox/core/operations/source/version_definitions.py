"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.operations.declarations import definition as _registry_definition

from dataclasses import dataclass
import re
from typing import Literal
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.source_publications import (
    InventoryAbsenceEvidence,
    QualifiedAssetPresenceEvidence,
)

from stratbox.shared.data.processing import DataContract, DataRole

Change = Literal[
    "first_seen",
    "new_release",
    "new_asset",
    "revised",
    "unchanged",
    "indeterminate",
]

BaselineState = Literal["initial", "available", "absent_proven", "unavailable"]

_HASH = re.compile(r"[0-9a-f]{64}\Z")


from stratbox.shared.source_versions import OriginalVersion, OriginalVersionComparison


@dataclass(frozen=True, slots=True)
class CompareOriginalVersionsRequest:
    candidate: OriginalVersion
    baseline_state: BaselineState
    baseline: OriginalVersion | None = None
    absence: InventoryAbsenceEvidence | None = None
    presence: QualifiedAssetPresenceEvidence | None = None

    def __post_init__(self):
        if (
            not isinstance(self.candidate, OriginalVersion)
            or self.candidate.transition_id is not None
        ):
            raise ValueError("source.candidate_invalid")
        if self.baseline_state not in {
            "initial",
            "available",
            "absent_proven",
            "unavailable",
        }:
            raise ValueError("source.baseline_state_invalid")
        if self.baseline_state == "available":
            if (
                not isinstance(self.baseline, OriginalVersion)
                or self.baseline.source_id != self.candidate.source_id
                or self.baseline.transition_id is None
                or self.absence is not None
                or self.presence is not None
            ):
                raise ValueError("source.baseline_chain_required")
        elif self.baseline is not None:
            raise ValueError("source.baseline_unexpected")
        if self.baseline_state == "absent_proven":
            if (
                not isinstance(self.absence, InventoryAbsenceEvidence)
                or not isinstance(self.presence, QualifiedAssetPresenceEvidence)
                or self.absence.asset.source_id != self.candidate.source_id
                or self.presence.asset.source_id != self.candidate.source_id
            ):
                raise ValueError("source.absence_unproven")
            prior = self.absence.inventory
            current = self.presence
            if (
                prior.series_id != current.series_id
                or prior.scope_id != current.scope_id
                or prior.profile_id != current.profile_id
                or prior.profile_version != current.profile_version
                or prior.issue_lower_bound != current.issue_lower_bound
                or prior.issue_upper_bound != current.issue_upper_bound
            ):
                raise ValueError("source.inventory_profile_mismatch")
            if current.observed_at_utc < prior.observed_at_utc:
                raise ValueError("source.inventory_out_of_order")
        elif self.absence is not None or self.presence is not None:
            raise ValueError("source.absence_unexpected")


COMPARE = _registry_definition('source.compare_original_versions')
