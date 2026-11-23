"""Exact consumed preparation inputs, separate from runtime provider objects."""
from __future__ import annotations

from hashlib import sha256

from stratbox.core.execution.values import plain
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

_MEDIA = "application/vnd.stratbox.notification-input+json"


def depend(invocation, role, value, *, source=None):
    if invocation is None:
        return
    identity = ByteIdentity.of(canonical_manifest_bytes({"role": role, "value": plain(value)}))
    invocation.depend(UsedInputReceipt(role, identity, _MEDIA, "inline", source))


def scope_dependencies(invocation, scope):
    if invocation is None:
        return
    subscription = scope.subscription
    depend(invocation, "notification.subscription", {
        "spec": subscription.spec, "revision": subscription.revision,
        "status": subscription.status,
    })
    depend(invocation, "notification.journal_head", scope.head,
        source=scope.head.source_authority_id)
    depend(invocation, "notification.checkpoint", {"cursor": scope.cursor, "target": scope.target},
        source=scope.head.source_authority_id)


class PageEvidence:
    """Stream bounded observations into one receipt per consumed journal page.

    Record byte identities come from the verified positioned page. Pairing and
    order stay in the digest; large record bodies and provider instances are
    never copied into an input manifest. Per-record identities also remain in
    the normal notification state transaction for replay and deduplication.
    """

    def __init__(self, invocation, source):
        self.invocation = invocation
        self.source = source
        self.digest = sha256()
        self.size = 0

    def add(self, role, value):
        if self.invocation is None:
            return
        self.invocation.check_cancelled()
        raw = canonical_manifest_bytes({"role": role, "value": plain(value)})
        self.digest.update(len(raw).to_bytes(8, "big"))
        self.digest.update(raw)
        self.size += len(raw) + 8

    def __enter__(self):
        return self

    def __exit__(self, *error):
        if self.invocation is not None and self.size:
            self.invocation.depend(UsedInputReceipt("notification.journal_page",
                ByteIdentity(self.digest.hexdigest(), self.size), _MEDIA, "inline", self.source))


def topic_value(topic, projection):
    from stratbox.core.execution.methods import callable_fingerprint

    return {
        "topic_id": topic.topic_id, "version": topic.version, "schemas": topic.schemas,
        "event_key_kind": topic.event_key_kind, "semantic_fields": topic.semantic_fields,
        "filter_fields": topic.filter_fields, "source_authorities": topic.source_authorities,
        "explicit_opt_in": topic.explicit_opt_in,
        "eligible": None if topic.eligible is None else callable_fingerprint(topic.eligible),
        "projection": projection,
    }
