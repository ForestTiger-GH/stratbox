"""Published operation references for system.notifications."""

from stratbox.system.execution.registry import DomainRegistration, OperationRef

REGISTRATION = DomainRegistration(
    domain_id="system.notifications",
    operations=(
        OperationRef("notifications.prepare", 3, "stratbox.system.notifications.operations:PREPARE", "stratbox.system.notifications.operations:prepare"),
        OperationRef("notifications.deliver", 3, "stratbox.system.notifications.operations:DELIVER", "stratbox.system.notifications.operations:deliver"),
        OperationRef("notifications.qualify", 3, "stratbox.system.notifications.operations:QUALIFY", "stratbox.system.notifications.operations:qualify"),
        OperationRef("notifications.reconcile", 2, "stratbox.system.notifications.operations:RECONCILE", "stratbox.system.notifications.operations:reconcile"),
    ),
)
