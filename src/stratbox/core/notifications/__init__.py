"""Qualified subscriptions and structured handoff for the Strategy Box core."""
from stratbox.core.notifications.contracts import (
    AccessDecision, AccessRequest, AdmittedHandoff, EventPointer, FilterCondition, HandoffLookup,
    HandoffReceipt, NotificationAuthority, NotificationConsumer, NotificationIntent, NotificationRoute,
    Subscription, SubscriptionSpec,
)
from stratbox.core.notifications.dispatch.delivery import (
    DeliverRequest, DeliveryResult, QualifiedHandoff, QualifyDeliveryRequest, ReconcileDeliveryRequest,
    RetryPolicy,
)
from stratbox.core.notifications.operations import deliver, prepare, qualify, reconcile
from stratbox.core.notifications.dispatch.preparation import Inspection, InspectRequest, PreparationReport, PrepareRequest, inspect
from stratbox.core.notifications.runtime import ConsumerBinding, NotificationReadRuntime, NotificationRuntime, SourceBinding
from stratbox.core.notifications.projections import (
    DispatchStatus, DownstreamStage, ExternalDeliveryReceipt, NotificationHealth, TopicAvailability,
    accessible_topics, inspect_dispatch, notification_health, project_downstream, record_external_delivery,
)
from stratbox.core.notifications.state.contracts import (
    Attempt, AuditBatch, CheckpointKey, CheckpointUpdate, Dispatch, DispatchUpdate,
    NotificationStateReader, NotificationStateStore, RecordIdentity, Replay, StateMutation,
    StateReceipt,
)
from stratbox.core.notifications.state.memory import MemoryNotificationState
from stratbox.core.notifications.state.audit import flush_audit
from stratbox.core.notifications.subscriptions import SubscriptionChange, amend_checkpoint, configure_subscription, register_replay
from stratbox.core.notifications.state.codec import decode_state_mutation, encode_state_mutation
from stratbox.core.notifications.topics import NotificationTopic, Projection, TopicCatalog, build_catalog
