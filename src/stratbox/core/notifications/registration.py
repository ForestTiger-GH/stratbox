"""Published operation references for core notification operations."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="core.notifications",
    operations=(
        OperationRef("notifications.prepare", 3, "stratbox.core.notifications.operations:PREPARE", "stratbox.core.notifications.operations:prepare"),
        OperationRef("notifications.deliver", 3, "stratbox.core.notifications.operations:DELIVER", "stratbox.core.notifications.operations:deliver"),
        OperationRef("notifications.qualify", 3, "stratbox.core.notifications.operations:QUALIFY", "stratbox.core.notifications.operations:qualify"),
        OperationRef("notifications.reconcile", 2, "stratbox.core.notifications.operations:RECONCILE", "stratbox.core.notifications.operations:reconcile"),
    ),
)
