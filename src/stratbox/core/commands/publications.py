"""Neutral publication evidence selection and source-assessment fallbacks."""
from __future__ import annotations
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import AssetSelection, PublicationListing, UpdateAssessment, fingerprint
from ._settings import _get


def publication_scan(inputs, settings, context):
    raise ExecutionFailure("publication.source_specification_required")


def issue_select(inputs, settings, context):
    listing, query = inputs["listing"], inputs.get("query") or context.parameters
    expected = _get(query, "source_id", _get(settings, "source_id"))
    issue = _get(query, "issue_id", _get(settings, "issue_id"))
    selected = tuple(a for a in listing.entries if (not expected or a.source_id == expected) and (not issue or a.issue_id == issue))
    if not selected:
        raise ExecutionFailure("publication.issue_not_found")
    keys = [(a.source_id, a.issue_id, a.asset_id) for a in selected]
    if len(keys) != len(set(keys)):
        raise ExecutionFailure("publication.ambiguous_asset")
    return {"selection": AssetSelection(selected, listing.assessment)}


def source_assess(inputs, settings, context):
    candidate, previous = inputs["evidence"], inputs.get("baseline")
    incomplete = any(not getattr(value.assessment, "complete", False) for value in (candidate, previous)
                     if value is not None and hasattr(value, "assessment"))
    if incomplete or isinstance(candidate, PublicationListing):
        return {"assessment": UpdateAssessment("unknown", _get(settings, "basis", "provided_evidence"),
            ("Evidence is incomplete or establishes only a publication listing, not actual asset content.",), evidence=(candidate, previous))}
    current = fingerprint(candidate)
    baseline = fingerprint(previous) if previous is not None else None
    return {"assessment": UpdateAssessment("first_seen" if previous is None else "unchanged" if current == baseline else "changed",
        _get(settings, "basis", "provided_evidence"), predecessor=baseline, candidate=current)}


def publication_transcribe(inputs, settings, context):
    return {"publication": inputs["physical"]}
