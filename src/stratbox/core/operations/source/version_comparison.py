"""Publisher-neutral comparison of confirmed byte versions and qualified absence."""

from __future__ import annotations

from hashlib import sha256

from stratbox.shared.identity import (
    canonical_manifest_bytes,
)
from stratbox.core.execution import (
    ExecutionContext, OperationResult, run,
)

from .version_definitions import (
    BaselineState, COMPARE, Change, CompareOriginalVersionsRequest, OriginalVersion, OriginalVersionComparison, _HASH,
)


def _compare(req: CompareOriginalVersionsRequest) -> OriginalVersionComparison:
    old = req.baseline
    if req.baseline_state == "unavailable":
        state, reason = "indeterminate", "baseline.unavailable"
    elif req.baseline_state == "initial":
        state, reason = "first_seen", "source.initial_observation"
    elif req.baseline_state == "absent_proven":
        state = "new_asset" if req.absence.existing_issue else "new_release"
        reason = "inventory.qualified_absence"
    elif old.identity == req.candidate.identity:
        state, reason = "unchanged", "original.bytes_equal"
    else:
        state, reason = "revised", "original.bytes_changed"

    transition_id = None
    parent = (
        old.transition_id if old is not None
        else req.absence.inventory.identity if req.absence is not None
        else "genesis"
    )
    if state in {"first_seen", "new_release", "new_asset", "revised"}:
        transition_id = sha256(canonical_manifest_bytes({
            "contract": 2, "source_id": req.candidate.source_id, "state": state,
            "parent": parent,
            "old_sha256": old.identity.sha256 if old else None,
            "old_size": old.identity.size if old else None,
            "new_sha256": req.candidate.identity.sha256,
            "new_size": req.candidate.identity.size,
        })).hexdigest()
    return OriginalVersionComparison(
        req.candidate.source_id, state, reason,
        old.identity if old is not None else None,
        req.candidate.identity, transition_id,
        old.transition_id if old is not None else None,
    )


def compare_original_versions(
    request: CompareOriginalVersionsRequest, *,
    context: ExecutionContext | None = None,
) -> OperationResult[OriginalVersionComparison]:
    def work(req, invocation):
        invocation.stage("compare_original_versions")
        return _compare(req)
    return run(COMPARE, request, work, context=context)
