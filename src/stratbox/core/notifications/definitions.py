"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.operations.declarations import definition as _registry_definition

from stratbox.core.execution.contracts import RuntimeDependency
from stratbox.core.notifications.dispatch.contracts import (
    DeliverRequest,
    DeliveryResult,
    QualifiedHandoff,
    QualifyDeliveryRequest,
    ReconcileDeliveryRequest,
)
from stratbox.core.notifications.dispatch.preparation_contracts import (
    PreparationReport,
    PrepareRequest,
)

from stratbox.shared.data.processing import DataContract, DataRole

_SCOPE_PORTS = (
    RuntimeDependency("notification_authority", "scoped", "notification_runtime"),
    RuntimeDependency("notification_state", "scoped", "notification_runtime"),
)

_JOURNAL_PORT = RuntimeDependency(
    "journal_source", "conditional", "notification_runtime"
)

_CONSUMER_PORT = RuntimeDependency(
    "notification", "conditional", "notification_runtime"
)

PREPARE = _registry_definition('notifications.prepare')

DELIVER = _registry_definition('notifications.deliver')

QUALIFY = _registry_definition('notifications.qualify')

RECONCILE = _registry_definition('notifications.reconcile')
