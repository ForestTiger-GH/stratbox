"""Published operation references for 01_05_A debt."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

from stratbox.core.execution.semantics import (
    ProcessingStage,
    StageDeclaration,
    OperationKey,
)

REGISTRATION = OperationRegistration(
    owner_id="cbr.corporate_lending.industries.debt_0105a",
    operations=(
        OperationRef(
            "cbr.industries.0105a.discover",
            1,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:DISCOVER",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.operations:discover",
        ),
        OperationRef(
            "cbr.industries.0105a.acquire",
            1,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:ACQUIRE",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.operations:acquire",
        ),
        OperationRef(
            "cbr.industries.0105a.parse",
            3,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:PARSE",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.operations:parse",
        ),
        OperationRef(
            "cbr.industries.0105a.build_stream",
            3,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:BUILD_STREAM",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.operations:build_stream",
        ),
        OperationRef(
            "cbr.industries.0105a.calculate_apk",
            2,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:CALCULATE_APK",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.operations:calculate_apk",
        ),
        OperationRef(
            "cbr.industries.0105a.build_pivots",
            2,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:PIVOT",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.operations:build_pivots",
        ),
        OperationRef(
            "cbr.industries.0105a.render_pivots",
            2,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:RENDER_PIVOTS",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.operations:render_pivots",
        ),
        OperationRef(
            "cbr.industries.0105a.render_industry",
            2,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:RENDER_INDUSTRY",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.operations:render_industry",
        ),
        OperationRef(
            "cbr.industries.0105a.render_industries",
            1,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:RENDER_INDUSTRIES",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.operations:render_industries",
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
