"""Published operation references for system.notifications."""

from stratbox.core.execution.catalog import DomainRegistration, OperationRef

REGISTRATION = DomainRegistration(
    domain_id="system.notifications",
    operations=(
        OperationRef("notifications.prepare", 3, "stratbox.core.notifications.operations:PREPARE", "stratbox.core.notifications.operations:prepare"),
        OperationRef("notifications.deliver", 3, "stratbox.core.notifications.operations:DELIVER", "stratbox.core.notifications.operations:deliver"),
        OperationRef("notifications.qualify", 3, "stratbox.core.notifications.operations:QUALIFY", "stratbox.core.notifications.operations:qualify"),
        OperationRef("notifications.reconcile", 2, "stratbox.core.notifications.operations:RECONCILE", "stratbox.core.notifications.operations:reconcile"),
    ),
)
