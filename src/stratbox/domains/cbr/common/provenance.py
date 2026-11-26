"""Actual consumed source coordinates established during table interpretation."""
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse


def source_use(series_id, issue_id, identity, *, asset_id="main", role="source"):
    return SourceUse(SourceCoordinate(source_id=series_id, issue_id=issue_id or None,
        asset_id=asset_id, material_identity=identity), role, "domain_validated",
        "sha256:" + identity.sha256)
