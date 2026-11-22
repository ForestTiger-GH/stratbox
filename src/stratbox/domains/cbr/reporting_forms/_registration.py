"""Published operation references for cbr_forms."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

from stratbox.core.execution.semantics import (
    ProcessingStage,
    StageDeclaration,
    OperationKey,
)

REGISTRATION = OperationRegistration(
    owner_id="cbr.reporting_forms",
    operations=(
        OperationRef(
            "cbr.forms.select_sources",
            1,
            "stratbox.domains.cbr.reporting_forms.definitions:SELECT",
            "stratbox.domains.cbr.reporting_forms.operations:select_sources",
        ),
        OperationRef(
            "cbr.forms.acquire",
            1,
            "stratbox.domains.cbr.reporting_forms.definitions:ACQUIRE",
            "stratbox.domains.cbr.reporting_forms.operations:acquire",
        ),
        OperationRef(
            "cbr.forms.parse",
            2,
            "stratbox.domains.cbr.reporting_forms.definitions:PARSE",
            "stratbox.domains.cbr.reporting_forms.operations:parse_form",
        ),
        OperationRef(
            "cbr.forms.build_data",
            2,
            "stratbox.domains.cbr.reporting_forms.definitions:BUILD",
            "stratbox.domains.cbr.reporting_forms.operations:build_form_data",
        ),
        OperationRef(
            "cbr.forms.build_views",
            2,
            "stratbox.domains.cbr.reporting_forms.definitions:VIEWS",
            "stratbox.domains.cbr.reporting_forms.operations:build_form_views",
        ),
        OperationRef(
            "cbr.forms.render_workbook",
            2,
            "stratbox.domains.cbr.reporting_forms.definitions:RENDER",
            "stratbox.domains.cbr.reporting_forms.operations:render_workbook",
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
