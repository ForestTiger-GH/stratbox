"""Acquire a selected official asset; issue context is explicit for rolling data."""
from stratbox.shared.evidence import UsedInputReceipt
from .access import ARCHIVE_TYPES, HTML_TYPES, XLSX_TYPES, receive_cbr
from .admission import identify_value
from .contracts import IdentifiedOriginal, IdentifyRequest


def acquire_publication(request, invocation, *, transport=None):
    asset = request.asset
    if asset.alternative_urls:
        raise ValueError("cbr.selection.publication_ambiguous")
    issue = asset.issue_id or request.issue_id
    if issue is None or asset.issue_id is not None and request.issue_id is not None and request.issue_id != asset.issue_id:
        raise ValueError("cbr.publication.issue_context_required")
    types = HTML_TYPES if asset.format == "html" else ARCHIVE_TYPES if asset.format in {"zip", "rar"} else (
        frozenset({"application/octet-stream", "application/x-dbf", "application/dbf"}) if asset.format == "dbf" else XLSX_TYPES)
    acquired = receive_cbr(asset.url, roots=(), media_types=types, limit=256 * 1024**2,
                           source_id=asset.series_id, transport=transport, invocation=invocation)
    admitted = identify_value(IdentifyRequest(asset.series_id, issue, acquired.payload, asset.format, asset.asset_id), invocation)
    lineage = (UsedInputReceipt("acquired_original", acquired.payload.identity, acquired.payload.media_type, "inline", asset.series_id),)
    invocation.use(lineage[0])
    invocation.account_output(acquired.payload.identity)
    return IdentifiedOriginal(admitted.asset, acquired.payload, admitted.format,
        "verified_official_route_and_format", lineage, acquired.receipt)
