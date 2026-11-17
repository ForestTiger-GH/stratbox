"""Recipient-specific receipt qualification independent of delivery transport."""
from __future__ import annotations
from stratbox.core.notifications.contracts import HandoffLookup, HandoffReceipt
from stratbox.core.notifications.dispatch.contracts import QualifiedHandoff

def qualify_receipt(lookup: HandoffLookup, receipt: HandoffReceipt | None) -> QualifiedHandoff:
    if receipt is None:
        return QualifiedHandoff("unknown", "notification.acknowledgement_unconfirmed")
    if not isinstance(receipt, HandoffReceipt) or (
        receipt.dispatch_id, receipt.attempt_id, receipt.route, receipt.route_revision, receipt.payload_identity
    ) != (lookup.dispatch_id, lookup.attempt_id, lookup.route, lookup.route_revision, lookup.payload_identity):
        return QualifiedHandoff("unknown", "notification.receipt_mismatch")
    if receipt.state == "unknown" or receipt.evidence_ref is None:
        return QualifiedHandoff("unknown", receipt.reason_code or "notification.acknowledgement_unconfirmed")
    if receipt.state == "accepted":
        return QualifiedHandoff("accepted", "notification.consumer_accepted", receipt)
    if not receipt.final_rejection:
        return QualifiedHandoff("unknown", "notification.rejection_unconfirmed")
    return QualifiedHandoff("not_accepted", receipt.reason_code or "notification.not_accepted", receipt)
