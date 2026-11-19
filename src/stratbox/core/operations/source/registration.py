"""Published operation references for neutral source operations."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="core.sources",
    operations=(
        OperationRef("source.receive_original", 1, "stratbox.core.operations.source.originals:RECEIVE", "stratbox.core.operations.source.originals:receive_original"),
        OperationRef("source.save_original", 1, "stratbox.core.operations.source.originals:SAVE", "stratbox.core.operations.source.originals:save_original"),
        OperationRef("source.receive_to_store", 1, "stratbox.core.operations.source.originals:RECEIVE_TO_STORE", "stratbox.core.operations.source.originals:receive_to_store"),
        OperationRef("source.read_original", 1, "stratbox.core.operations.source.originals:READ", "stratbox.core.operations.source.originals:read_original"),
        OperationRef("source.reconcile_original", 1, "stratbox.core.operations.source.originals:RECONCILE", "stratbox.core.operations.source.originals:reconcile_original"),
        OperationRef("source.compare_original_versions", 1, "stratbox.core.operations.source.version_comparison:COMPARE", "stratbox.core.operations.source.version_comparison:compare_original_versions"),
    ),
)
