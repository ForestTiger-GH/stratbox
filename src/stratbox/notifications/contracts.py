"""Facts, intent and qualified acknowledgements for caller-owned delivery."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from stratbox.data import ByteIdentity, PublicationReceipt, StoredBytesReceipt

DeliveryState = Literal["accepted", "not_accepted", "unknown"]


@dataclass(frozen=True, slots=True)
class PublicationConfirmed:
    receipt: PublicationReceipt
    change: Literal[
        "first_seen", "new_release", "revised", "unchanged", "indeterminate"
    ]
    backfill: bool = False


@dataclass(frozen=True, slots=True)
class OriginalStoredConfirmed:
    receipt: StoredBytesReceipt
    event_id: str


@dataclass(frozen=True, slots=True)
class DiagnosticFact:
    event_id: str
    code: str


@dataclass(frozen=True, slots=True)
class NotificationPolicy:
    first_import: bool = False
    backfill: bool = False
    original_storage: bool = False
    diagnostics: bool = False


@dataclass(frozen=True, slots=True)
class NotificationRoute:
    route_id: str
    destination_id: str

    def __post_init__(self) -> None:
        if not self.route_id or not self.destination_id:
            raise ValueError(
                "Notification route requires a route and destination identity"
            )


@dataclass(frozen=True, slots=True)
class NotificationIntent:
    route: NotificationRoute
    effect_key: str
    event_identity: bytes = field(repr=False)
    payload: bytes = field(repr=False)
    payload_identity: ByteIdentity
    route_revision: str | None = None


@dataclass(frozen=True, slots=True)
class PrepareRequest:
    fact: PublicationConfirmed | OriginalStoredConfirmed | DiagnosticFact
    policy: NotificationPolicy
    route: NotificationRoute
    dry_run: bool = False
    route_revision: str | None = None


@dataclass(frozen=True, slots=True)
class PrepareDecision:
    intent: NotificationIntent | None
    reason: str


@dataclass(frozen=True, slots=True)
class SendReceipt:
    effect_key: str
    state: DeliveryState
    acknowledgement: str | None = field(default=None, repr=False)
    route: NotificationRoute | None = None
    payload_identity: ByteIdentity | None = None
    route_revision: str | None = None


class NotificationTransport(Protocol):
    def send(self, intent: NotificationIntent) -> SendReceipt: ...


class ManagedNotificationChannel(Protocol):
    """The receiving owner of a scoped, authoritatively checked delivery.

    The owner verifies the publication/diagnostic fact, payload, current recipient
    and grant at acceptance. It preserves the logical key across attempts.
    """

    def send_admitted(self, intent: NotificationIntent) -> SendReceipt: ...
    def lookup(self, intent: NotificationIntent) -> SendReceipt: ...


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    state: DeliveryState
    effect_key: str
    payload_identity: ByteIdentity
    acknowledgement: str | None = field(repr=False)
    next_action: Literal["done", "retry", "reconcile"]
    route: NotificationRoute | None = None
    route_revision: str | None = None


@dataclass(frozen=True, slots=True)
class DeliverRequest:
    intent: NotificationIntent
    authorized_route: NotificationRoute
    previous: DeliveryResult | None = None


@dataclass(frozen=True, slots=True)
class QualifyDeliveryRequest:
    intent: NotificationIntent
    receipt: SendReceipt | None


@dataclass(frozen=True, slots=True)
class ReconcileDeliveryRequest:
    intent: NotificationIntent
