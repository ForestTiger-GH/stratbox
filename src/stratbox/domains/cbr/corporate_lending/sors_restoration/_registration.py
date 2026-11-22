"""Published operation references for cbr_sors_restoration."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef
from stratbox.core.execution.semantics import ProcessingStage, StageDeclaration, OperationKey

REGISTRATION = OperationRegistration(
    owner_id="cbr.corporate_lending.sors_restoration",
    operations=(
        OperationRef("cbr.sors.read_source_files", 2, 'stratbox.domains.cbr.corporate_lending.sors_restoration.definitions:READ', "stratbox.domains.cbr.corporate_lending.sors_restoration.api:read_source_files"),
        OperationRef("cbr.sors.load_sources", 4, 'stratbox.domains.cbr.corporate_lending.sors_restoration.definitions:LOAD', "stratbox.domains.cbr.corporate_lending.sors_restoration.api:load_sources"),
        OperationRef("cbr.sors.restore", 4, 'stratbox.domains.cbr.corporate_lending.sors_restoration.definitions:RESTORE', "stratbox.domains.cbr.corporate_lending.sors_restoration.api:restore"),
        OperationRef("cbr.sors.crosswalk", 3, 'stratbox.domains.cbr.corporate_lending.sors_restoration.definitions:CROSSWALK', "stratbox.domains.cbr.corporate_lending.sors_restoration.api:run_crosswalk"),
        OperationRef("cbr.sors.build_pivot", 3, 'stratbox.domains.cbr.corporate_lending.sors_restoration.definitions:PIVOT', "stratbox.domains.cbr.corporate_lending.sors_restoration.api:build_pivot"),
        OperationRef("cbr.sors.render_workbook", 3, 'stratbox.domains.cbr.corporate_lending.sors_restoration.definitions:RENDER', "stratbox.domains.cbr.corporate_lending.sors_restoration.api:render_workbook"),
        *tuple(OperationRef(f"cbr.sors.{name}", 1,
            f"stratbox.domains.cbr.corporate_lending.sors_restoration.definitions:{definition}",
            f"stratbox.domains.cbr.corporate_lending.sors_restoration.snapshot_operations:{handler}")
            for name, definition, handler in (
                ("bundle_snapshot", "BUNDLE_SNAPSHOT", "build_bundle_snapshot"),
                ("read_bundle_snapshot", "READ_BUNDLE_SNAPSHOT", "read_bundle_snapshot"),
                ("restoration_snapshot", "RESTORATION_SNAPSHOT", "build_restoration_snapshot"),
                ("read_restoration_snapshot", "READ_RESTORATION_SNAPSHOT", "read_restoration_snapshot"),
                ("crosswalk_snapshot", "CROSSWALK_SNAPSHOT", "build_crosswalk_snapshot"),
                ("read_crosswalk_snapshot", "READ_CROSSWALK_SNAPSHOT", "read_crosswalk_snapshot"),
            )),
    ),
    stages=(
        StageDeclaration(ProcessingStage.PRESERVE, "delegated", "processing.logical_dataset_storage",
            (OperationKey("dataset.write_snapshot", 1), OperationKey("dataset.read_snapshot", 1)),
            "Retain complete SORS snapshots through caller-selected dataset storage and read their pinned references."),
        StageDeclaration(ProcessingStage.INGEST, "delegated", "processing.logical_dataset_storage",
            (OperationKey("dataset.write_snapshot", 1),),
            "Write a complete source bundle, restoration or crosswalk snapshot to the logical dataset store."),
        StageDeclaration(ProcessingStage.READABLE, "missing", "processing.readable_not_implemented"),
        StageDeclaration(ProcessingStage.PUBLISH, "missing", "processing.external_publication_consumer_owned"),
    ),
)
