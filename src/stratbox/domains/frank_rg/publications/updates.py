"""Separate observed file metadata, exact byte revisions and report periods."""
from __future__ import annotations

from .contracts import (
    AcquiredReport, AssessMaterialRequest, MaterialAssessment, SourceCheckpoint,
    UpdateDecision, UpdatePlan, UpdateRequest,
)


def assess_updates(request: UpdateRequest) -> UpdatePlan:
    if type(request.force_refresh) is not bool:
        raise ValueError("frg.update.force_invalid")
    selected = request.catalog.selections
    source_ids = {x.source_id for x in selected}
    checkpoints = {x.source_id: x for x in request.checkpoints}
    if (len(source_ids) != len(selected) or len(checkpoints) != len(request.checkpoints)
            or set(checkpoints) - source_ids):
        raise ValueError("frg.update.checkpoints_invalid")
    decisions = []
    for selection in selected:
        source_id, asset = selection.source_id, selection.asset
        if selection.state in {"missing", "ambiguous"}:
            decisions.append(UpdateDecision(source_id, None, selection.state, False,
                                            "frg.update." + selection.state))
            continue
        if selection.state != "selected" or asset is None or not asset.valid:
            raise ValueError("frg.update.selection_invalid")
        old = checkpoints.get(source_id)
        if old is None:
            state, required, reason = "initial", True, "frg.update.initial"
        elif (old.period != asset.period or old.entry is None or old.entry != asset.entry
              or asset.entry.size_bytes is None or asset.entry.mtime is None):
            state, required, reason = "changed", True, "frg.update.metadata_changed"
        else:
            # Equal path/size/mtime is only a cheap observation, never byte proof.
            state, required = "metadata_unchanged", request.force_refresh
            reason = ("frg.update.forced_material_verification" if required
                      else "frg.update.metadata_only")
        decisions.append(UpdateDecision(source_id, asset, state, required, reason))
    return UpdatePlan(tuple(decisions), request.catalog.inventory.index.identity)


def assess_material(request: AssessMaterialRequest) -> MaterialAssessment:
    report, previous = request.report, request.checkpoint
    if previous is None:
        state = "initial"
    elif previous.source_id != report.source_id:
        raise ValueError("frg.material.source_mismatch")
    elif previous.period != report.period:
        state = "new_period"
    elif previous.original_identity == report.payload.identity:
        state = "unchanged"
    else:
        state = "revised"
    return MaterialAssessment(report.source_id, state, report.payload.identity)


def checkpoint_for(report: AcquiredReport) -> SourceCheckpoint:
    """Return a candidate checkpoint; the consumer commits it after its effects."""
    return SourceCheckpoint(report.source_id, report.period, report.payload.identity, report.entry)
