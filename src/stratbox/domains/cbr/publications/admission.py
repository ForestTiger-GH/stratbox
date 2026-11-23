"""Source-format admission with caller-qualified publication identity."""
from dataclasses import replace
from datetime import date, datetime
from pathlib import PurePosixPath
import re
from urllib.parse import unquote, urljoin, urlsplit

from stratbox.core.execution import OperationFailure
from stratbox.core.formats.html import link_targets
from stratbox.core.operations.source.validation import use_payload
from stratbox.domains.cbr.publications.access import HTML_TYPES, official_url, receive_cbr, validate_workbook
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.source_publications import SourceAssetIdentity
from .contracts import IdentifiedOriginal, PublicationAsset, PublicationInventory
from .profiles import acquisition_profile
from .catalog import source


from .discovery import _profile


def identify_value(request, invocation):
    item, _ = _profile(request.series_id)
    if request.format not in item.formats:
        raise OperationFailure("cbr.publication.format_unsupported")
    try:
        asset = SourceAssetIdentity(item.series_id, request.issue_id, request.asset_id)
        if item.issue_model == "dated" and date.fromisoformat(request.issue_id).isoformat() != request.issue_id:
            raise ValueError("cbr.publication.issue_noncanonical")
    except (ValueError, TypeError):
        raise OperationFailure("cbr.publication.issue_invalid") from None
    payload = request.payload
    data = payload.data
    if request.format == "xlsx":
        validate_workbook(data, budget=invocation.budget)
    elif request.format == "rar" and not data.startswith(b"Rar!\x1a\x07"):
        raise OperationFailure("source.archive_signature_invalid")
    elif request.format == "zip" and not data.startswith(b"PK\x03\x04"):
        raise OperationFailure("source.archive_signature_invalid")
    elif request.format == "dbf" and (len(data) < 33 or data[0] not in {0x02, 0x03, 0x04, 0x05, 0x30, 0x31, 0x32, 0x43, 0x63, 0x83, 0x8B, 0x8E, 0xF5}):
        raise OperationFailure("source.dbf_signature_invalid")
    elif request.format == "html" and not data.lstrip(b"\xef\xbb\xbf \t\n\r").startswith(b"<"):
        raise OperationFailure("source.html_signature_invalid")
    return IdentifiedOriginal(asset, payload, request.format,
        lineage=(UsedInputReceipt("supplied_original", payload.identity, payload.media_type,
                                  "inline", asset.series_id),))
