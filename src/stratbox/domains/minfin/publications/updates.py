"""Pure publication-marker preflight, distinct from material and processing versions.

Operation binding supplies the registered asset IDs and method identities. This
module knows nothing about actual filenames, parser implementations or stores.
"""
from __future__ import annotations
from collections import defaultdict
from collections.abc import Mapping
from .contracts import SourceCheckpoint, UpdateDecision, UpdatePlan, UpdateRequest, SourceFamily


def assess_updates(request: UpdateRequest, *, source: SourceFamily,
                   asset_ids: Mapping[str, str], method_versions: Mapping[str, str]) -> UpdatePlan:
    if request.index.family_id != source.family_id:
        raise ValueError("minfin.update.family_mismatch")
    eligible = {item.source_id: item for item in source.series}
    sources = request.selected_sources or tuple(s.source_id for s in source.series if s.kind == "table")
    if len(sources) != len(set(sources)) or any(s not in eligible for s in sources):
        raise ValueError("minfin.update.invalid_source_selection")
    if (request.target not in {"probe", "flake"} or type(request.force_reprocess) is not bool
            or type(request.force_refresh) is not bool):
        raise ValueError("minfin.update.invalid_target")
    if request.target == "flake" and any(eligible[s].kind != "table" for s in sources):
        raise ValueError("minfin.update.flake_source_unsupported")
    if not request.retained_sources <= set(sources):
        raise ValueError("minfin.update.invalid_retention_scope")
    checkpoints = {}
    for cp in request.checkpoints:
        if cp.source_id in checkpoints or cp.source_id not in eligible or not cp.original_identity.size:
            raise ValueError("minfin.update.invalid_checkpoint")
        checkpoints[cp.source_id] = cp
    discovered = defaultdict(list)
    for asset in request.index.assets:
        if asset.recognition == "registered_variant":
            discovered[asset.source_id].append(asset)
    decisions = []
    for source_id in sources:
        candidates = discovered.get(source_id, ())
        previous = checkpoints.get(source_id)
        if not candidates:
            conflicting = asset_ids.get(source_id) in request.index.ambiguous_asset_ids
            decisions.append(UpdateDecision(source_id, None, "ambiguous" if conflicting else "missing", False, False,
                                            "minfin.update.conflicting_asset_evidence" if conflicting else
                                            "minfin.update.not_visible_on_current_page"))
            continue
        if len(candidates) != 1 or candidates[0].asset_id in request.index.ambiguous_asset_ids:
            decisions.append(UpdateDecision(source_id, None, "ambiguous", False, False,
                                            "minfin.update.multiple_current_candidates"))
            continue
        asset = candidates[0]
        if previous is None:
            decisions.append(UpdateDecision(source_id, asset, "initial", True, request.target == "flake",
                                            "minfin.update.no_confirmed_baseline"))
            continue
        marker = previous.publication
        if marker.asset_id != asset.asset_id or marker.document_id != asset.document_id:
            state, reason = "indeterminate", "minfin.update.publisher_identity_changed"
        elif marker.modified_on is None or asset.modified_on is None:
            state, reason = "indeterminate", "minfin.update.publisher_date_unavailable"
        elif asset.modified_on != marker.modified_on:
            state, reason = "revised", "minfin.update.publisher_modified_date_changed"
        elif asset.url != marker.url:
            state, reason = "indeterminate", "minfin.update.url_changed_without_date_change"
        else:
            state, reason = "unchanged", "minfin.update.publisher_marker_unchanged"
        required_method = method_versions.get(source_id)
        if request.target == "flake" and not required_method:
            raise ValueError("minfin.update.method_unavailable")
        needs_processing = request.target == "flake" and (
            state != "unchanged" or previous.processing.method_version != required_method
            or request.force_reprocess
        )
        needs_download = (state != "unchanged" or request.force_refresh or
                          (needs_processing and source_id not in request.retained_sources))
        if state == "unchanged" and request.force_refresh:
            reason = "minfin.update.forced_material_verification"
        decisions.append(UpdateDecision(source_id, asset, state, needs_download, needs_processing, reason))
    return UpdatePlan(source.family_id, request.index.index_identity, tuple(decisions))


def checkpoint_for(asset, flake) -> SourceCheckpoint:
    """Candidate only: caller commits it after persisting the requested results."""
    if asset.source_id != flake.source_id or asset.family_id != flake.family_id:
        raise ValueError("minfin.update.checkpoint_source_mismatch")
    return SourceCheckpoint(asset.source_id, asset.asset_id, asset.document_id,
                            asset.modified_on, asset.url, flake.original_identity, flake.method_version)


__all__ = ("assess_updates", "checkpoint_for")