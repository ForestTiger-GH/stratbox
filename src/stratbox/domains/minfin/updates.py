"""Effect-free, publication-marker-first update planning for Minfin sources.

Publisher modification dates are a *cheap signal*, not cryptographic evidence
of byte identity. The returned decisions are conditional on the caller's
confirmed checkpoint and retained-material availability.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from .pipeline_models import SourceCheckpoint, UpdateDecision, UpdatePlan, UpdateRequest
from .registry import family


def assess_updates(request: UpdateRequest) -> UpdatePlan:
    spec = family(request.index.family_id)
    eligible = {v.source_id for v in spec.variants}
    # Default processing targets only the statistical table families. Other
    # officially listed documentary assets remain explicitly selectable for
    # source inventory checks without being mistaken for XLSX flakes.
    sources = request.selected_sources or tuple(
        v.source_id for v in spec.variants
        if v.periodicity in {"monthly", "quarterly", "annual"}
    )
    if request.target == "flake" and any(
        v.source_id in sources and v.periodicity not in {"monthly", "quarterly", "annual"}
        for v in spec.variants
    ):
        raise ValueError("minfin.update.flake_source_unsupported")
    if len(sources) != len(set(sources)) or any(s not in eligible for s in sources):
        raise ValueError("minfin.update.invalid_source_selection")
    if request.target not in {"probe", "flake"} or not request.method_version:
        raise ValueError("minfin.update.invalid_target")
    if not request.retained_sources <= set(sources):
        raise ValueError("minfin.update.invalid_retention_scope")
    checkpoints = {}
    for cp in request.checkpoints:
        if cp.source_id in checkpoints or cp.source_id not in eligible:
            raise ValueError("minfin.update.invalid_checkpoint")
        if not cp.original_identity.size or not cp.original_identity.sha256:
            raise ValueError("minfin.update.invalid_checkpoint")
        checkpoints[cp.source_id] = cp
    discovered = defaultdict(list)
    for asset in request.index.assets:
        if asset.recognition == "registered_variant":
            discovered[asset.source_id].append(asset)
    results = []
    for source_id in sources:
        candidates = discovered.get(source_id, ())
        baseline = checkpoints.get(source_id)
        asset = candidates[0] if len(candidates) == 1 else None
        if not candidates:
            results.append(UpdateDecision(source_id, None, "missing", False, False,
                                          "minfin.update.not_visible_on_current_page"))
            continue
        if len(candidates) > 1 or asset.asset_id in request.index.ambiguous_asset_ids:
            results.append(UpdateDecision(source_id, None, "ambiguous", False, False,
                                          "minfin.update.multiple_current_candidates"))
            continue
        if baseline is None:
            results.append(UpdateDecision(source_id, asset, "initial", True, request.target == "flake",
                                          "minfin.update.no_confirmed_baseline"))
            continue
        if baseline.asset_id != asset.asset_id or baseline.document_id != asset.document_id:
            state, reason = "indeterminate", "minfin.update.publisher_identity_changed"
        elif baseline.modified_on is None or asset.modified_on is None:
            state, reason = "indeterminate", "minfin.update.publisher_date_unavailable"
        elif asset.modified_on != baseline.modified_on:
            state, reason = "revised", "minfin.update.publisher_modified_date_changed"
        elif asset.url != baseline.asset_url:
            state, reason = "indeterminate", "minfin.update.url_changed_without_date_change"
        else:
            state, reason = "unchanged", "minfin.update.publisher_marker_unchanged"
        must_reprocess = request.target == "flake" and (
            baseline.flake_method_version != request.method_version or state != "unchanged"
        )
        must_download = state != "unchanged" or (
            must_reprocess and source_id not in request.retained_sources
        )
        results.append(UpdateDecision(source_id, asset, state, must_download, must_reprocess, reason))
    return UpdatePlan(spec.family_id, request.index.index_identity, tuple(results))


def checkpoint_for(asset, flake):
    """Build a checkpoint only from a completed validated extraction.

    Callers must commit it after they confirm any required persistence effect.
    """
    if asset.source_id != flake.source_id or asset.family_id != flake.family_id:
        raise ValueError("minfin.update.checkpoint_source_mismatch")
    return SourceCheckpoint(
        asset.source_id, asset.asset_id, asset.document_id,
        asset.modified_on, asset.url, flake.original_identity, flake.method_version,
    )