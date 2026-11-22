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
        OperationRef("cbr.forms.read_flake_export", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:READ_FLAKE_EXPORT",
            "stratbox.domains.cbr.reporting_forms.flake_export:read_flake_export"),
        OperationRef("cbr.forms.render_flakes", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:RENDER_FLAKES",
            "stratbox.domains.cbr.reporting_forms.flake_export:render_flakes"),
        OperationRef("cbr.forms.discover_sources", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:DISCOVER",
            "stratbox.domains.cbr.reporting_forms.source_operations:discover_sources"),
        OperationRef("cbr.forms.extract", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:EXTRACT",
            "stratbox.domains.cbr.reporting_forms.source_operations:extract_forms"),
        OperationRef("cbr.forms.normalize", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:NORMALIZE",
            "stratbox.domains.cbr.reporting_forms.source_operations:normalize_form"),
        OperationRef("cbr.forms.flake_snapshot", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:FLAKE_SNAPSHOT",
            "stratbox.domains.cbr.reporting_forms.source_operations:flake_snapshot"),
        OperationRef("cbr.forms.restore_flakes", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:RESTORE_FLAKES",
            "stratbox.domains.cbr.reporting_forms.source_operations:restore_flakes"),
        OperationRef("cbr.forms.result_snapshot", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:RESULT_SNAPSHOT",
            "stratbox.domains.cbr.reporting_forms.source_operations:snapshot_result"),
        OperationRef("cbr.forms.restore_normalized", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:RESTORE_NORMALIZED",
            "stratbox.domains.cbr.reporting_forms.source_operations:restore_normalized"),
        OperationRef("cbr.forms.restore_data", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:RESTORE_DATA",
            "stratbox.domains.cbr.reporting_forms.source_operations:restore_data"),
        OperationRef("cbr.forms.restore_views", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:RESTORE_VIEWS",
            "stratbox.domains.cbr.reporting_forms.source_operations:restore_views"),
        OperationRef("cbr.forms.integrate", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:INTEGRATE",
            "stratbox.domains.cbr.reporting_forms.source_operations:integrate_forms"),
        OperationRef("cbr.forms.restore_history", 1,
            "stratbox.domains.cbr.reporting_forms.source_definitions:RESTORE_HISTORY",
            "stratbox.domains.cbr.reporting_forms.source_operations:restore_history"),
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
                OperationKey("dataset.write_snapshot", 1),
                OperationKey("dataset.read_snapshot", 1),
            ),
            "Bind the acquired payload to SaveOriginalRequest.source and supply a caller-owned "
            "destination. Retain source-issue association with the material; read its exact bytes "
            "through ReadOriginalRequest before source-specific readmission. Encode complete "
            "domain values as DatasetSnapshot for independent dataset write/read and replay.",
        ),
        StageDeclaration(
            ProcessingStage.READABLE, "missing", "processing.readable_not_implemented"
        ),
        StageDeclaration(
            ProcessingStage.INGEST, "delegated", "processing.logical_dataset_storage",
            (OperationKey("dataset.write_snapshot", 1),),
            "Encode flakes or a normalized history as DatasetSnapshot, write through a selected "
            "dataset adapter, read its pinned reference and restore the appropriate form result.",
        ),
    ),
)
