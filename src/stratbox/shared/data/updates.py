"""Update planning separates source revisions, processing revisions and retention.

The caller supplies observed inputs and the exact desired methods/references.
The planner performs no discovery, acquisition, execution, save or deletion.
"""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.source_publications import SourceAssetIdentity


@dataclass(frozen=True, slots=True)
class ProcessingTarget:
    asset: SourceAssetIdentity
    contract: DataContract
    source_identity: ByteIdentity
    method_version: str
    references: tuple[tuple[str, ByteIdentity], ...] = ()
    destinations: tuple[str, ...] = ()

    def __post_init__(self):
        if (not isinstance(self.asset, SourceAssetIdentity) or not isinstance(self.contract, DataContract)
                or not isinstance(self.source_identity, ByteIdentity) or not self.method_version
                or not isinstance(self.references, tuple) or any(not isinstance(r, tuple) or len(r) != 2
                    or type(r[0]) is not str or not r[0] or not isinstance(r[1], ByteIdentity) for r in self.references)
                or len({n for n,_ in self.references}) != len(self.references)
                or not isinstance(self.destinations, tuple) or len(set(self.destinations)) != len(self.destinations)
                or any(type(d) is not str or not d for d in self.destinations)):
            raise ValueError("update.target_invalid")


@dataclass(frozen=True, slots=True)
class RetainedProcessing:
    target: ProcessingTarget
    result_identity: ByteIdentity
    confirmed_destinations: tuple[str, ...] = ()

    def __post_init__(self):
        if (not isinstance(self.target, ProcessingTarget) or not isinstance(self.result_identity, ByteIdentity)
                or not isinstance(self.confirmed_destinations, tuple)
                or len(set(self.confirmed_destinations)) != len(self.confirmed_destinations)
                or any(type(d) is not str or not d for d in self.confirmed_destinations)):
            raise ValueError("update.retained_result_invalid")


@dataclass(frozen=True, slots=True)
class UpdateDecision:
    target: ProcessingTarget
    source_state: str
    processing_state: str
    recompute: bool
    reasons: tuple[str, ...]
    destinations_to_write: tuple[str, ...]
    reusable_result: ByteIdentity | None


@dataclass(frozen=True, slots=True)
class UpdatePlan:
    decisions: tuple[UpdateDecision, ...]
    coverage: SnapshotCoverage
    qualifications: tuple[str, ...]


def plan_updates(targets: tuple[ProcessingTarget, ...], retained: tuple[RetainedProcessing, ...] = (), *, coverage=None):
    if (not isinstance(targets, tuple) or any(not isinstance(t, ProcessingTarget) for t in targets)
            or not isinstance(retained, tuple) or any(not isinstance(r, RetainedProcessing) for r in retained)):
        raise ValueError("update.inputs_invalid")
    key = lambda t: (t.asset, t.contract.schema_id)
    previous = {key(r.target): r for r in retained}
    if len(previous) != len(retained) or len({key(t) for t in targets}) != len(targets):
        raise ValueError("update.ambiguous_checkpoint")
    result = []
    for target in targets:
        old = previous.get(key(target))
        reasons = []
        source_state, processing_state = "unseen", "unseen"
        if old is None:
            reasons.append("result_missing")
        else:
            source_state = "same" if target.source_identity == old.target.source_identity else "changed"
            if source_state == "changed":
                reasons.append("source_content_changed")
            if target.contract != old.target.contract:
                reasons.append("schema_changed")
            if target.method_version != old.target.method_version:
                reasons.append("method_changed")
            if dict(target.references) != dict(old.target.references):
                reasons.append("reference_edition_changed")
            processing_state = "changed" if any(r != "source_content_changed" for r in reasons) else "same"
        recompute = bool(reasons)
        destinations = target.destinations if recompute else tuple(
            d for d in target.destinations if d not in old.confirmed_destinations)
        result.append(UpdateDecision(target, source_state, processing_state, recompute, tuple(reasons),
            destinations, old.result_identity if old is not None and not recompute else None))
    return UpdatePlan(tuple(result), coverage or SnapshotCoverage("unknown", "Exactly the caller-supplied observed targets."),
        ("Unlisted sources are outside this plan; absence is not deletion authority.",
         "Destination confirmation is supplied by the caller and must be reconciled with actual storage receipts."))
