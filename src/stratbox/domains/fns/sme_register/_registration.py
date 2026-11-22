"""Published operation references for fns_sme."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

from stratbox.core.execution.semantics import (
    ProcessingStage,
    StageDeclaration,
    OperationKey,
)

REGISTRATION = OperationRegistration(
    owner_id="fns.sme_register",
    operations=(
        OperationRef(
            "fns.sme.discover",
            1,
            "stratbox.domains.fns.sme_register.definitions:DISCOVER",
            "stratbox.domains.fns.sme_register.operations:discover",
        ),
        OperationRef(
            "fns.sme.acquire",
            1,
            "stratbox.domains.fns.sme_register.definitions:ACQUIRE",
            "stratbox.domains.fns.sme_register.operations:acquire",
        ),
        OperationRef(
            "fns.sme.parse",
            1,
            "stratbox.domains.fns.sme_register.definitions:PARSE",
            "stratbox.domains.fns.sme_register.operations:parse",
        ),
        OperationRef(
            "fns.sme.capture",
            1,
            "stratbox.domains.fns.sme_register.definitions:CAPTURE",
            "stratbox.domains.fns.sme_register.operations:capture",
        ),
        OperationRef(
            "fns.sme.read_representation",
            1,
            "stratbox.domains.fns.sme_register.definitions:READ",
            "stratbox.domains.fns.sme_register.operations:read_representation",
        ),
        OperationRef(
            "fns.sme.compare",
            2,
            "stratbox.domains.fns.sme_register.definitions:COMPARE",
            "stratbox.domains.fns.sme_register.operations:compare",
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
