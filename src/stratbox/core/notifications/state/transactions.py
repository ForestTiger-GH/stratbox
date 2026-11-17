"""Qualified notification state commit and lookup reconciliation."""
from __future__ import annotations
from stratbox.core.notifications.state.contracts import NotificationStateStore, StateMutation, StateReceipt

def commit_and_lookup(store: NotificationStateStore, mutation: StateMutation) -> StateReceipt:
    try:
        receipt = store.commit(mutation)
    except Exception:
        receipt = None
    if (isinstance(receipt, StateReceipt) and receipt.command_id == mutation.command_id
            and receipt.state in {"confirmed", "conflict", "rejected"}):
        return receipt
    try:
        recovered = store.lookup_command(mutation.scope_id, mutation.command_id)
    except Exception:
        recovered = None
    if (isinstance(recovered, StateReceipt) and recovered.state == "confirmed"
            and recovered.command_id == mutation.command_id):
        return recovered
    return StateReceipt(mutation.command_id, "unknown", "notification.state_commit_unknown")


