from dataclasses import replace

from stratbox.data import ByteIdentity, canonical_manifest_bytes
from stratbox.execution import (
    Completion,
    EffectReceipt,
    ExecutionContext,
    OperationDefinition,
    OperationFailure,
    OperationResult,
    run,
)
from stratbox.execution.contracts import safe_token

from .contracts import (
    DeliverRequest,
    DeliveryResult,
    DiagnosticFact,
    ManagedNotificationChannel,
    NotificationIntent,
    NotificationTransport,
    OriginalStoredConfirmed,
    PrepareDecision,
    PrepareRequest,
    PublicationConfirmed,
    QualifyDeliveryRequest,
    ReconcileDeliveryRequest,
    SendReceipt,
)

PREPARE = OperationDefinition(
    "notifications.prepare", 2, "notification-intent-2", PrepareRequest, PrepareDecision
)
DELIVER = OperationDefinition(
    "notifications.deliver",
    2,
    "notification-delivery-2",
    DeliverRequest,
    DeliveryResult,
    frozenset({"notification"}),
    frozenset({"notification.send"}),
)

QUALIFY = OperationDefinition(
    "notifications.qualify",
    2,
    "notification-acknowledgement-2",
    QualifyDeliveryRequest,
    DeliveryResult,
)


RECONCILE = OperationDefinition(
    "notifications.reconcile", 1, "notification-owner-lookup-1",
    ReconcileDeliveryRequest, DeliveryResult, frozenset({"notification"}),
)


def _key(event: bytes, route) -> str:
    return ByteIdentity.of(
        canonical_manifest_bytes(
            {
                "version": 1,
                "event_identity_sha256": ByteIdentity.of(event).sha256,
                "route": route.route_id,
                "destination": route.destination_id,
            }
        )
    ).sha256


def _prepare(req, invocation):
    invocation.stage("qualify_fact")
    if req.dry_run:
        return PrepareDecision(None, "policy.dry_run")
    fact = req.fact
    if isinstance(fact, PublicationConfirmed):
        receipt = fact.receipt
        if receipt.confirmation != "confirmed":
            return PrepareDecision(None, "publication.unconfirmed")
        if fact.change not in {"first_seen", "new_release", "revised"}:
            return PrepareDecision(None, "publication.no_material_change")
        if fact.change == "first_seen" and not req.policy.first_import:
            return PrepareDecision(None, "policy.first_import_disabled")
        if fact.backfill and not req.policy.backfill:
            return PrepareDecision(None, "policy.backfill_disabled")
        event = {
            "kind": "publication",
            "owner": receipt.owner_id,
            "destination": receipt.destination_id,
            "release": receipt.release_id,
            "transition": receipt.transition_id,
        }
        message = {
            **event,
            "artifact_sha256": receipt.identity.sha256,
            "change": fact.change,
        }
    elif isinstance(fact, OriginalStoredConfirmed):
        if not req.policy.original_storage or fact.receipt.status not in {
            "stored",
            "already_present",
        }:
            return PrepareDecision(None, "storage.unqualified")
        event = {"kind": "original_stored", "event_id": safe_token(fact.event_id)}
        message = {**event, "artifact_sha256": fact.receipt.identity.sha256}
    elif isinstance(fact, DiagnosticFact):
        if not req.policy.diagnostics:
            return PrepareDecision(None, "policy.diagnostics_disabled")
        event = {"kind": "diagnostic", "event_id": safe_token(fact.event_id)}
        message = {**event, "code": safe_token(fact.code)}
    else:
        raise OperationFailure("notification.fact_invalid")
    identity = canonical_manifest_bytes(event)
    payload = canonical_manifest_bytes(message)
    intent = NotificationIntent(
        req.route,
        _key(identity, req.route),
        identity,
        payload,
        ByteIdentity.of(payload),
        safe_token(req.route_revision) if req.route_revision is not None else None,
    )
    return PrepareDecision(intent, "notification.prepared")


def prepare(
    request: PrepareRequest, *, context: ExecutionContext | None = None
) -> OperationResult[PrepareDecision]:
    return run(PREPARE, request, _prepare, context=context)


def _validate_intent(intent):
    if intent.route_revision is not None:
        safe_token(intent.route_revision)
    if intent.effect_key != _key(
        intent.event_identity, intent.route
    ) or intent.payload_identity != ByteIdentity.of(intent.payload):
        raise OperationFailure("notification.intent_invalid")


def _qualify(intent, receipt, *, managed=False):
    valid = isinstance(receipt, SendReceipt) and receipt.effect_key == intent.effect_key
    if valid and (managed or receipt.route is not None):
        valid = receipt.route == intent.route and receipt.route_revision == intent.route_revision
    if valid and (managed or receipt.payload_identity is not None):
        valid = receipt.payload_identity == intent.payload_identity
    state, acknowledgement, next_action = "unknown", None, "reconcile"
    if valid and receipt.state == "accepted" and (
        isinstance(receipt.acknowledgement, str) and 0 < len(receipt.acknowledgement) <= 256
        and receipt.acknowledgement.strip()
    ):
        state, acknowledgement, next_action = "accepted", receipt.acknowledgement, "done"
    elif valid and receipt.state == "not_accepted":
        state, next_action = "not_accepted", "retry"
    return DeliveryResult(
        state, intent.effect_key, intent.payload_identity, acknowledgement, next_action,
        intent.route, intent.route_revision,
    )


def qualify(
    request: QualifyDeliveryRequest, *, context: ExecutionContext | None = None
) -> OperationResult[DeliveryResult]:
    """Qualify an externally obtained receipt without contacting the channel."""

    def work(req, invocation):
        invocation.stage("qualify_receipt")
        _validate_intent(req.intent)
        if invocation.context.profile == "managed":
            raise OperationFailure("notification.owner_lookup_required")
        result = _qualify(req.intent, req.receipt)
        if result.state == "unknown":
            return Completion(
                result, "unknown", "notification.acknowledgement_unconfirmed"
            )
        return result

    return run(QUALIFY, request, work, context=context)


def _owner_lookup(channel, intent):
    try:
        receipt = channel.lookup(intent)
    except Exception:
        receipt = None
    return _qualify(intent, receipt, managed=True)


def reconcile(
    request: ReconcileDeliveryRequest, *,
    transport: ManagedNotificationChannel | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[DeliveryResult]:
    """Ask the competent channel about an existing logical effect."""

    def work(req, invocation):
        invocation.stage("reconcile")
        _validate_intent(req.intent)
        if not callable(getattr(transport, "lookup", None)):
            raise OperationFailure("provider.capability_missing")
        result = _owner_lookup(transport, req.intent)
        if result.state == "unknown":
            return Completion(result, "unknown", "notification.reconciliation_required")
        return result

    return run(
        RECONCILE, request, work, providers={"notification": transport}, context=context,
    )


def deliver(
    request: DeliverRequest,
    *,
    transport: NotificationTransport | ManagedNotificationChannel | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[DeliveryResult]:
    def work(req, invocation):
        invocation.stage("validate_intent")
        intent = req.intent
        if intent.route != req.authorized_route:
            raise OperationFailure("notification.route_forbidden")
        _validate_intent(intent)
        managed = invocation.context.profile == "managed"
        if managed:
            if intent.route_revision is None:
                raise OperationFailure("notification.route_revision_required")
            if not callable(getattr(transport, "send_admitted", None)) or not callable(
                getattr(transport, "lookup", None)
            ):
                raise OperationFailure("provider.capability_missing")
        previous = req.previous
        if previous is not None:
            if previous.effect_key != intent.effect_key:
                raise OperationFailure("notification.effect_key_mismatch")
            if previous.payload_identity != intent.payload_identity:
                raise OperationFailure("notification.payload_conflict")
            if previous.route != intent.route or previous.route_revision != intent.route_revision:
                raise OperationFailure("notification.route_conflict")
            if managed:
                invocation.stage("reconcile")
                previous = _owner_lookup(transport, intent)
            if previous.state == "accepted":
                return previous
            if previous.state == "unknown":
                return Completion(previous, "unknown", "notification.reconciliation_required")
        invocation.stage("send")
        effect = EffectReceipt(
            "notification.send", "unknown", effect_id=intent.effect_key, stage="send",
            identity=intent.payload_identity, guarantee="channel_acceptance", reconciliation_owner="channel",
        )
        invocation.effect(effect)
        try:
            ack = transport.send_admitted(intent) if managed else transport.send(intent)
        except Exception:
            ack = None
        result = _qualify(intent, ack, managed=managed)
        state = {"accepted": "confirmed", "not_accepted": "failed", "unknown": "unknown"}[
            result.state
        ]
        invocation.effect(replace(effect, state=state, stage="acceptance"))
        if result.state == "accepted":
            return result
        if result.state == "not_accepted":
            return Completion(result, "failed", "notification.not_accepted")
        return Completion(result, "unknown", "notification.acknowledgement_unconfirmed")

    return run(
        DELIVER, request, work, providers={"notification": transport}, context=context,
    )
