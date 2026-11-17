"""Published operation references for cbr_file_collector."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="cbr_file_collector",
    operations=(
        OperationRef("cbr.file_collector.discover", 1, "stratbox.domains.cbr_file_collector.operations:DISCOVER", "stratbox.domains.cbr_file_collector.operations:discover"),
        OperationRef("cbr.file_collector.collect_raw", 2, "stratbox.domains.cbr_file_collector.operations:COLLECT", "stratbox.domains.cbr_file_collector.operations:collect_raw"),
        OperationRef("cbr.file_collector.prepare_archive", 1, "stratbox.domains.cbr_file_collector.operations:ARCHIVE", "stratbox.domains.cbr_file_collector.operations:prepare_archive"),
        OperationRef("cbr.file_collector.collect_to_store", 1, "stratbox.domains.cbr_file_collector.operations:COLLECT_TO_STORE", "stratbox.domains.cbr_file_collector.operations:collect_to_store"),
        OperationRef("cbr.file_collector.archive_to_store", 1, "stratbox.domains.cbr_file_collector.operations:ARCHIVE_TO_STORE", "stratbox.domains.cbr_file_collector.operations:archive_to_store"),
    ),
)
