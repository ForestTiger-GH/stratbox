"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.execution.contracts import OperationDefinition, RuntimeDependency
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
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)

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

PREPARE = OperationDefinition(
    "notifications.prepare",
    3,
    "notification-preparation-3",
    PrepareRequest,
    PreparationReport,
    possible_effects=frozenset({"notification.state_commit"}),
    partial_allowed=True,
    runtime_dependencies=_SCOPE_PORTS + (_JOURNAL_PORT,),
    processing=OperationSemantics(
        stages=(ProcessingStage.INSPECT,),
        summary="Prepare configured notification intents from qualified journal facts.",
        outputs=(
            OutputPort("result", DataContract("notifications.prepare.result", 1, None)),
        ),
    ),
)

DELIVER = OperationDefinition(
    "notifications.deliver",
    3,
    "notification-handoff-3",
    DeliverRequest,
    DeliveryResult,
    possible_effects=frozenset({"notification.state_commit", "notification.handoff"}),
    runtime_dependencies=_SCOPE_PORTS + (_JOURNAL_PORT, _CONSUMER_PORT),
    processing=OperationSemantics(
        stages=(ProcessingStage.PUBLISH,),
        summary="Hand off an authorized notification intent and retain uncertain effects.",
        outputs=(
            OutputPort("result", DataContract("notifications.deliver.result", 1, None)),
        ),
    ),
)

QUALIFY = OperationDefinition(
    "notifications.qualify",
    3,
    "notification-handoff-receipt-3",
    QualifyDeliveryRequest,
    QualifiedHandoff,
    processing=OperationSemantics(
        stages=(ProcessingStage.VALIDATE,),
        summary="Qualify a notification handoff receipt independently of final delivery.",
        outputs=(
            OutputPort("result", DataContract("notifications.qualify.result", 1, None)),
        ),
    ),
)

RECONCILE = OperationDefinition(
    "notifications.reconcile",
    2,
    "notification-handoff-lookup-2",
    ReconcileDeliveryRequest,
    DeliveryResult,
    possible_effects=frozenset({"notification.state_commit"}),
    runtime_dependencies=_SCOPE_PORTS + (_JOURNAL_PORT, _CONSUMER_PORT),
    processing=OperationSemantics(
        stages=(ProcessingStage.VALIDATE,),
        summary="Reconcile an unresolved notification handoff under its owner scope.",
        outputs=(
            OutputPort(
                "result", DataContract("notifications.reconcile.result", 1, None)
            ),
        ),
    ),
)
