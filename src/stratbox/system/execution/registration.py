"""Published operation references for system.execution."""

from stratbox.system.execution.registry import DomainRegistration, OperationRef

REGISTRATION = DomainRegistration(
    domain_id="system.execution",
    operations=(
        OperationRef("source.receive_original", 1, "stratbox.system.execution.originals:RECEIVE", "stratbox.system.execution.originals:receive_original"),
        OperationRef("source.save_original", 1, "stratbox.system.execution.originals:SAVE", "stratbox.system.execution.originals:save_original"),
        OperationRef("source.receive_to_store", 1, "stratbox.system.execution.originals:RECEIVE_TO_STORE", "stratbox.system.execution.originals:receive_original_to_store"),
        OperationRef("source.read_original", 1, "stratbox.system.execution.originals:READ", "stratbox.system.execution.originals:read_original"),
        OperationRef("source.reconcile_original", 1, "stratbox.system.execution.originals:RECONCILE", "stratbox.system.execution.originals:reconcile_original"),
    ),
)
