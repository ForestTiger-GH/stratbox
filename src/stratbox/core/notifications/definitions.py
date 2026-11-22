"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.execution.contracts import OperationDefinition, RuntimeDependency
from stratbox.core.notifications.dispatch.contracts import DeliverRequest, DeliveryResult, QualifiedHandoff, QualifyDeliveryRequest, ReconcileDeliveryRequest
from stratbox.core.notifications.dispatch.preparation_contracts import PreparationReport, PrepareRequest

_SCOPE_PORTS = (
    RuntimeDependency("notification_authority", "scoped", "notification_runtime"),
    RuntimeDependency("notification_state", "scoped", "notification_runtime"),
)

_JOURNAL_PORT = RuntimeDependency("journal_source", "conditional", "notification_runtime")

_CONSUMER_PORT = RuntimeDependency("notification", "conditional", "notification_runtime")

PREPARE = OperationDefinition(
    "notifications.prepare", 3, "notification-preparation-3", PrepareRequest, PreparationReport,
    possible_effects=frozenset({"notification.state_commit"}), partial_allowed=True,
    runtime_dependencies=_SCOPE_PORTS + (_JOURNAL_PORT,),
)

DELIVER = OperationDefinition(
    "notifications.deliver", 3, "notification-handoff-3", DeliverRequest, DeliveryResult,
    possible_effects=frozenset({"notification.state_commit", "notification.handoff"}),
    runtime_dependencies=_SCOPE_PORTS + (_JOURNAL_PORT, _CONSUMER_PORT),
)

QUALIFY = OperationDefinition(
    "notifications.qualify", 3, "notification-handoff-receipt-3", QualifyDeliveryRequest, QualifiedHandoff,
)

RECONCILE = OperationDefinition(
    "notifications.reconcile", 2, "notification-handoff-lookup-2", ReconcileDeliveryRequest, DeliveryResult,
    possible_effects=frozenset({"notification.state_commit"}),
    runtime_dependencies=_SCOPE_PORTS + (_JOURNAL_PORT, _CONSUMER_PORT),
)

