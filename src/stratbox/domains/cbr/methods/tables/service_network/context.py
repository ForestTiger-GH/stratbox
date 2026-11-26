"""Source coordinates established by the office publication parsers."""
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse

_SOURCES = {"cbr.offices": "cbr.service_network.bank_offices",
            "cbr.offices_reg": "cbr.service_network.territorial_offices"}


def source_uses(dataset_id, payload, issue, method):
    return (SourceUse(SourceCoordinate(_SOURCES[dataset_id], "cbr.service_network",
        source_group_id="office_counts", issue_id=issue.isoformat(), material_identity=payload.identity,
        semantic_identity=method), "publication", "domain_validated",
        "sha256:" + payload.identity.sha256),)
