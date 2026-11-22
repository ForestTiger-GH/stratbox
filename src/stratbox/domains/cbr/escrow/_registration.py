"""Published operation references for escrow."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

from stratbox.core.execution.semantics import (
    ProcessingStage,
    StageDeclaration,
    OperationKey,
)

REGISTRATION = OperationRegistration(
    owner_id="cbr.escrow",
    operations=(
        OperationRef(
            "cbr.escrow.discover",
            1,
            "stratbox.domains.cbr.escrow.definitions:DISCOVER",
            "stratbox.domains.cbr.escrow.operations:discover",
        ),
        OperationRef(
            "cbr.escrow.acquire",
            1,
            "stratbox.domains.cbr.escrow.definitions:ACQUIRE",
            "stratbox.domains.cbr.escrow.operations:acquire",
        ),
        OperationRef(
            "cbr.escrow.parse",
            2,
            "stratbox.domains.cbr.escrow.definitions:PARSE",
            "stratbox.domains.cbr.escrow.operations:parse",
        ),
        OperationRef(
            "cbr.escrow.build_history",
            2,
            "stratbox.domains.cbr.escrow.definitions:HISTORY",
            "stratbox.domains.cbr.escrow.operations:build_history",
        ),
        OperationRef(
            "cbr.escrow.build_views",
            2,
            "stratbox.domains.cbr.escrow.definitions:VIEWS",
            "stratbox.domains.cbr.escrow.operations:build_views",
        ),
        OperationRef(
            "cbr.escrow.render_workbook",
            2,
            "stratbox.domains.cbr.escrow.definitions:RENDER",
            "stratbox.domains.cbr.escrow.operations:render_workbook",
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
