"""Qualified subscriptions and structured handoff for the Strategy Box core."""
from .contracts import (
    AccessDecision, AccessRequest, AdmittedHandoff, EventPointer, FilterCondition, HandoffLookup,
    HandoffReceipt, NotificationAuthority, NotificationConsumer, NotificationIntent, NotificationRoute,
    Subscription, SubscriptionSpec,
)
from .delivery import (
    DeliverRequest, DeliveryResult, QualifiedHandoff, QualifyDeliveryRequest, ReconcileDeliveryRequest,
    RetryPolicy,
)
from .operations import deliver, prepare, qualify, reconcile
from .preparation import Inspection, InspectRequest, PreparationReport, PrepareRequest, inspect
from .runtime import ConsumerBinding, NotificationReadRuntime, NotificationRuntime, SourceBinding
from .projections import (
    DispatchStatus, DownstreamStage, ExternalDeliveryReceipt, NotificationHealth, TopicAvailability,
    accessible_topics, inspect_dispatch, notification_health, project_downstream, record_external_delivery,
)
from .state import (
    Attempt, AuditBatch, CheckpointKey, CheckpointUpdate, Dispatch, DispatchUpdate, MemoryNotificationState,
    NotificationStateReader, NotificationStateStore, RecordIdentity, Replay, StateMutation,
    StateReceipt, flush_audit,
)
from .subscriptions import SubscriptionChange, amend_checkpoint, configure_subscription, register_replay
from .state_codec import decode_state_mutation, encode_state_mutation
from .topics import NotificationTopic, Projection, TopicCatalog, build_catalog
