"""Source-use facts established by successful source geometry and value checks."""
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.values import fingerprint


def interpreted_use(tables, source_id, issue_id, layout, semantics):
    if tables.material is None:
        return ()
    identity = tables.material.identity
    coordinate = SourceCoordinate(source_id=source_id, family_id="fns.sme" if source_id == "fns.sme" else "fns.legal_entities",
        source_group_id="reviewed_counters" if source_id == "fns.sme" else "reviewed_part_i",
        issue_id=issue_id or None, asset_id=tables.metadata.get("asset_id"), material_identity=identity,
        layout_identity=fingerprint(layout), semantic_identity=fingerprint(semantics))
    return (SourceUse(coordinate, "interpreted_source", "domain_validated",
        f"sha256:{identity.sha256}#scope={coordinate.source_group_id}"),)
