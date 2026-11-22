"""Channel-neutral notification facts; no delivery, journal or Telegram client."""
from __future__ import annotations
import hashlib
import json
from .contracts import NoticeRequest, NotificationDatum, NotificationFacts

def prepare_notification(request: NoticeRequest) -> tuple[NotificationFacts | None, str]:
    """Return data suitable for a later notification topic, never send a message.

    One candidate is produced only after an eligible *publisher* transition and
    a successful source-local summary. Initial history remains quiet by default.
    """
    summary, asset, decision = request.summary, request.asset, request.decision
    if asset.source_id != summary.source_id or asset.family_id != summary.family_id or (
        decision.asset != asset or decision.source_id != asset.source_id
    ):
        raise ValueError("minfin.notice.source_mismatch")
    if (request.baseline_original_identity is not None and
            request.baseline_original_identity == summary.original_identity):
        return None, "minfin.notice.source_bytes_unchanged"
    if decision.state == "initial" and not request.include_initial:
        return None, "minfin.notice.initial_suppressed"
    if decision.state not in {"revised", "initial"}:
        return None, "minfin.notice.no_new_publication"
    if asset.document_id is None or asset.modified_on is None:
        return None, "minfin.notice.publication_marker_unqualified"
    version = {
        "schema": 1, "source_id": summary.source_id, "asset_id": asset.asset_id,
        "document_id": asset.document_id, "modified_on": asset.modified_on.isoformat(),
        "source_sha": summary.original_identity.sha256,
        "period": summary.period_id, "summary_method": summary.flake_method_version,
    }
    key = hashlib.sha256(json.dumps(version, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    topic = "minfin.nwf_headline" if summary.family_id == "minfin.nwf" else "minfin.budget_headline"
    tags = ("minfin", summary.family_id.split(".")[-1], summary.frequency, summary.period_id)
    values = tuple(NotificationDatum(x.metric_id, x.label, x.value, x.yoy_pct, x.comparison, x.unit)
                   for x in summary.metrics)
    return NotificationFacts(key, topic, summary.family_id, summary.source_id, summary.period_id,
                             asset.published_on, asset.modified_on, summary.original_identity.sha256,
                             asset.url, values, decision.state, tags), "minfin.notice.ready"
