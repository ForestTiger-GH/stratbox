"""Published operation references for cbr_offices_reg."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

from stratbox.core.execution.semantics import (
    ProcessingStage,
    StageDeclaration,
    OperationKey,
)

REGISTRATION = OperationRegistration(
    owner_id="cbr.service_network.territorial_offices",
    operations=(
        OperationRef(
            "cbr.offices_reg.discover",
            1,
            "stratbox.domains.cbr.service_network.territorial_offices.definitions:DISCOVER",
            "stratbox.domains.cbr.service_network.territorial_offices.operations:discover",
        ),
        OperationRef(
            "cbr.offices_reg.acquire",
            1,
            "stratbox.domains.cbr.service_network.territorial_offices.definitions:ACQUIRE",
            "stratbox.domains.cbr.service_network.territorial_offices.operations:acquire",
        ),
        OperationRef(
            "cbr.offices_reg.parse",
            3,
            "stratbox.domains.cbr.service_network.territorial_offices.definitions:PARSE",
            "stratbox.domains.cbr.service_network.territorial_offices.operations:parse",
        ),
        OperationRef(
            "cbr.offices_reg.capture",
            3,
            "stratbox.domains.cbr.service_network.territorial_offices.definitions:CAPTURE",
            "stratbox.domains.cbr.service_network.territorial_offices.operations:capture",
        ),
        OperationRef(
            "cbr.offices_reg.read_representation",
            1,
            "stratbox.domains.cbr.service_network.territorial_offices.definitions:READ",
            "stratbox.domains.cbr.service_network.territorial_offices.operations:read_representation",
        ),
        OperationRef(
            "cbr.offices_reg.compare",
            2,
            "stratbox.domains.cbr.service_network.territorial_offices.definitions:COMPARE",
            "stratbox.domains.cbr.service_network.territorial_offices.operations:compare",
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
