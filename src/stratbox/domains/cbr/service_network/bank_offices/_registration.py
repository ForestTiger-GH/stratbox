"""Published operation references for cbr_offices."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

from stratbox.core.execution.semantics import (
    ProcessingStage,
    StageDeclaration,
    OperationKey,
)

REGISTRATION = OperationRegistration(
    owner_id="cbr.service_network.bank_offices",
    operations=(
        OperationRef(
            "cbr.offices.parse",
            1,
            "stratbox.domains.cbr.service_network.bank_offices.definitions:PARSE",
            "stratbox.domains.cbr.service_network.bank_offices.operations:parse",
            "stratbox.domains.cbr.service_network.bank_offices.machine:PARSE_CODEC",
            "stratbox.domains.cbr.service_network.bank_offices.machine_contracts:PARSE_CONTRACT",
        ),
        OperationRef(
            "cbr.offices.acquire",
            2,
            "stratbox.domains.cbr.service_network.bank_offices.definitions:ACQUIRE",
            "stratbox.domains.cbr.service_network.bank_offices.operations:acquire",
        ),
        OperationRef(
            "cbr.offices.capture",
            2,
            "stratbox.domains.cbr.service_network.bank_offices.definitions:CAPTURE",
            "stratbox.domains.cbr.service_network.bank_offices.operations:capture",
        ),
        OperationRef(
            "cbr.offices.read_representation",
            2,
            "stratbox.domains.cbr.service_network.bank_offices.definitions:READ",
            "stratbox.domains.cbr.service_network.bank_offices.operations:read_representation",
        ),
        OperationRef(
            "cbr.offices.snapshot", 1,
            "stratbox.domains.cbr.service_network.bank_offices.definitions:SNAPSHOT",
            "stratbox.domains.cbr.service_network.bank_offices.snapshots:snapshot_release",
        ),
        OperationRef(
            "cbr.offices.restore", 1,
            "stratbox.domains.cbr.service_network.bank_offices.definitions:RESTORE",
            "stratbox.domains.cbr.service_network.bank_offices.snapshots:restore_release",
        ),
        OperationRef(
            "cbr.offices.compare",
            2,
            "stratbox.domains.cbr.service_network.bank_offices.definitions:COMPARE",
            "stratbox.domains.cbr.service_network.bank_offices.operations:compare",
            "stratbox.domains.cbr.service_network.bank_offices.machine:COMPARE_CODEC",
            "stratbox.domains.cbr.service_network.bank_offices.machine_contracts:COMPARE_CONTRACT",
        ),
    ),
    stages=(
        StageDeclaration(
            ProcessingStage.PRESERVE, "delegated", "processing.neutral_material_storage",
            (OperationKey("source.save_original", 1), OperationKey("source.read_original", 1),
             OperationKey("dataset.write_snapshot", 1), OperationKey("dataset.read_snapshot", 1)),
            "Save exact originals through source operations. Encode the complete release with "
            "cbr.offices.snapshot, write and read its pinned dataset version, then call cbr.offices.restore.",
        ),
        StageDeclaration(
            ProcessingStage.READABLE, "missing", "processing.readable_not_implemented"
        ),
        StageDeclaration(
            ProcessingStage.INTEGRATE,
            "missing",
            "processing.integration_not_implemented",
        ),
        StageDeclaration(
            ProcessingStage.INGEST, "delegated", "processing.logical_dataset_storage",
            (OperationKey("dataset.write_snapshot", 1),),
            "Pass the complete office DatasetSnapshot to a selected dataset writer.",
        ),
    ),
)
