"""Relational evidence for reviewed fiscal geometry and source-local semantics."""
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.values import fingerprint
from collections.abc import Mapping


def issue_id(inputs, tables, context, source_id):
    supplied = inputs.get("issue")
    if supplied is not None and getattr(supplied, "source_id", source_id) != source_id:
        raise ValueError("minfin.issue_source_mismatch")
    if isinstance(supplied, Mapping):
        if supplied.get("source_id", source_id) != source_id:
            raise ValueError("minfin.issue_source_mismatch")
        candidate = supplied.get("issue_id", "")
    elif isinstance(supplied, str):
        candidate = supplied
    else:
        candidate = getattr(supplied, "issue_id", "")
    candidates = tuple(str(value) for value in (candidate, tables.issue_id, context.parameters.get("issue_id")) if value)
    if len(set(candidates)) > 1:
        raise ValueError("minfin.issue_context_conflict")
    return candidates[0] if candidates else ""


def interpreted_use(tables, source_id, family_id, layout, semantics):
    if tables.material is None:
        return ()
    identity = tables.material.identity
    coordinate = SourceCoordinate(source_id=source_id, family_id=family_id,
        source_group_id="reviewed_fields", issue_id=tables.issue_id or None,
        asset_id=tables.metadata.get("asset_id"), material_identity=identity,
        layout_identity=fingerprint(layout), semantic_identity=fingerprint(semantics))
    return (SourceUse(coordinate, "interpreted_source", "domain_validated",
        f"sha256:{identity.sha256}#scope=reviewed_fields"),)
