"""Observed source revisions, processing versions and destinations are separate."""
from .catalog import source
from .contracts import ProcessingCheckpoint, PublicationUpdatePlan


def assess_updates(request):
    original, previous = request.original, request.checkpoint
    descriptor = source(original.asset.series_id)
    if request.target not in {"original", "processed"} or len({item.destination_id for item in request.destinations}) != len(request.destinations):
        raise ValueError("cbr.updates.request_invalid")
    if any(not item.destination_id for item in request.destinations):
        raise ValueError("cbr.updates.destination_invalid")
    if previous is None:
        state = "initial"
    elif (previous.asset.series_id, previous.asset.asset_id) != (original.asset.series_id, original.asset.asset_id):
        raise ValueError("cbr.updates.checkpoint_source_mismatch")
    elif previous.asset.issue_id != original.asset.issue_id and descriptor.issue_model == "dated":
        state = "new_issue"
    elif previous.original_identity != original.payload.identity:
        state = "revised_bytes"
    elif previous.asset.issue_id != original.asset.issue_id:
        state = "new_capture_same_bytes"
    else:
        state = "unchanged"
    required = (previous is None or previous.original_identity != original.payload.identity
                or previous.processing_signature != request.processing_signature or previous.result_identity is None)
    # An official dated context is part of interpretation, even if bytes happen
    # to agree. Capture-only labels do not invalidate unchanged observations.
    required = required or state == "new_issue"
    target = original.payload.identity if request.target == "original" else (
        previous.result_identity if previous is not None and not required else None)
    actions = tuple((item.destination_id, "await_processing" if target is None else
                     "confirmed" if item.confirmed_identity == target else "write_required")
                    for item in request.destinations)
    candidate = ProcessingCheckpoint(original.asset, original.payload.identity, request.processing_signature,
                                     previous.result_identity if previous is not None and not required else None)
    return PublicationUpdatePlan(state, required, actions, original.payload.identity, candidate)
