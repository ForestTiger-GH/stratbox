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
            1,
            "stratbox.domains.cbr.service_network.bank_offices.definitions:READ",
            "stratbox.domains.cbr.service_network.bank_offices.operations:read_representation",
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
            ProcessingStage.PRESERVE,
            "delegated",
            "processing.neutral_original_storage",
            (
                OperationKey("source.save_original", 1),
                OperationKey("source.read_original", 1),
            ),
            "Bind the acquired payload to SaveOriginalRequest.source and supply a caller-owned "
            "destination. Retain source-issue association with the material; read its exact bytes "
            "through ReadOriginalRequest before source-specific readmission.",
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
            ProcessingStage.INGEST, "missing", "processing.ingestion_not_implemented"
        ),
    ),
)
