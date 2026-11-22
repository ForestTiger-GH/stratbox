"""Published operation references for cbr_file_collector."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="cbr.file_collection",
    operations=(
        OperationRef("cbr.file_collector.discover", 1, 'stratbox.domains.cbr.file_collection.definitions:DISCOVER', "stratbox.domains.cbr.file_collection.operations:discover"),
        OperationRef("cbr.file_collector.collect_raw", 2, 'stratbox.domains.cbr.file_collection.definitions:COLLECT', "stratbox.domains.cbr.file_collection.operations:collect_raw"),
        OperationRef("cbr.file_collector.prepare_archive", 1, 'stratbox.domains.cbr.file_collection.definitions:ARCHIVE', "stratbox.domains.cbr.file_collection.operations:prepare_archive"),
        OperationRef("cbr.file_collector.collect_to_store", 1, 'stratbox.domains.cbr.file_collection.definitions:COLLECT_TO_STORE', "stratbox.domains.cbr.file_collection.operations:collect_to_store"),
        OperationRef("cbr.file_collector.archive_to_store", 1, 'stratbox.domains.cbr.file_collection.definitions:ARCHIVE_TO_STORE', "stratbox.domains.cbr.file_collection.operations:archive_to_store"),
    ),
)
