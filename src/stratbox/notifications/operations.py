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
    NotificationIntent,
    NotificationTransport,
    OriginalStoredConfirmed,
    PrepareDecision,
    PrepareRequest,
    PublicationConfirmed,
    QualifyDeliveryRequest,
    SendReceipt,
)

PREPARE = OperationDefinition(
    "notifications.prepare", 1, "notification-intent-1", PrepareRequest, PrepareDecision
)
DELIVER = OperationDefinition(
    "notifications.deliver",
    1,
    "notification-delivery-1",
    DeliverRequest,
    DeliveryResult,
    frozenset({"notification"}),
    frozenset({"notification.send"}),
)

QUALIFY = OperationDefinition(
    "notifications.qualify",
    1,
    "notification-acknowledgement-1",
    QualifyDeliveryRequest,
    DeliveryResult,
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
    )
    return PrepareDecision(intent, "notification.prepared")


def prepare(
    request: PrepareRequest, *, context: ExecutionContext | None = None
) -> OperationResult[PrepareDecision]:
    return run(PREPARE, request, _prepare, context=context)


def _validate_intent(intent):
    if intent.effect_key != _key(
        intent.event_identity, intent.route
    ) or intent.payload_identity != ByteIdentity.of(intent.payload):
        raise OperationFailure("notification.intent_invalid")


def _qualify(intent, receipt):
    if isinstance(receipt, SendReceipt) and receipt.effect_key == intent.effect_key:
        if (
            receipt.state == "accepted"
            and isinstance(receipt.acknowledgement, str)
            and receipt.acknowledgement.strip()
        ):
            return DeliveryResult(
                "accepted",
                intent.effect_key,
                intent.payload_identity,
                receipt.acknowledgement,
                "done",
            )
        if receipt.state == "not_accepted":
            return DeliveryResult(
                "not_accepted",
                intent.effect_key,
                intent.payload_identity,
                None,
                "retry",
            )
    return DeliveryResult(
        "unknown", intent.effect_key, intent.payload_identity, None, "reconcile"
    )


def qualify(
    request: QualifyDeliveryRequest, *, context: ExecutionContext | None = None
) -> OperationResult[DeliveryResult]:
    """Qualify an externally obtained receipt without contacting the channel."""

    def work(req, invocation):
        invocation.stage("qualify_receipt")
        _validate_intent(req.intent)
        result = _qualify(req.intent, req.receipt)
        if result.state == "unknown":
            return Completion(
                result, "unknown", "notification.acknowledgement_unconfirmed"
            )
        return result

    return run(QUALIFY, request, work, context=context)


def deliver(
    request: DeliverRequest,
    *,
    transport: NotificationTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[DeliveryResult]:
    def work(req, invocation):
        invocation.stage("validate_intent")
        intent = req.intent
        if intent.route != req.authorized_route:
            raise OperationFailure("notification.route_forbidden")
        _validate_intent(intent)
        previous = req.previous
        if previous is not None:
            if previous.effect_key != intent.effect_key:
                raise OperationFailure("notification.effect_key_mismatch")
            if previous.payload_identity != intent.payload_identity:
                raise OperationFailure("notification.payload_conflict")
            if previous.state == "accepted":
                return previous
            if previous.state == "unknown" and not req.idempotent_channel_verified:
                return Completion(
                    previous, "unknown", "notification.reconciliation_required"
                )
        invocation.stage("send")
        try:
            ack = transport.send(intent)
        except Exception:
            ack = None
        result = _qualify(intent, ack)
        if result.state == "accepted":
            invocation.effects.append(
                EffectReceipt("notification.send", "confirmed", intent.effect_key)
            )
            return result
        if result.state == "not_accepted":
            invocation.effects.append(
                EffectReceipt("notification.send", "failed", intent.effect_key)
            )
            return Completion(result, "failed", "notification.not_accepted")
        invocation.effects.append(
            EffectReceipt("notification.send", "unknown", intent.effect_key)
        )
        return Completion(result, "unknown", "notification.acknowledgement_unconfirmed")

    return run(
        DELIVER, request, work, providers={"notification": transport}, context=context
    )
