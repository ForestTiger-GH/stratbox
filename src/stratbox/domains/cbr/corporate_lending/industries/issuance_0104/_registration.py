"""Published 01_04_A issuance operation references."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

from stratbox.core.execution.semantics import (
    ProcessingStage,
    StageDeclaration,
    OperationKey,
)

REGISTRATION = OperationRegistration(
    owner_id="cbr.corporate_lending.industries.issuance_0104",
    operations=(
        OperationRef("cbr.industries.0104a.render_pivots", 1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:RENDER_PIVOTS",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:render_pivots"),
        OperationRef(
            "cbr.industries.0104a.discover",
            1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:DISCOVER",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:discover",
        ),
        OperationRef(
            "cbr.industries.0104a.acquire",
            1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:ACQUIRE",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:acquire",
        ),
        OperationRef(
            "cbr.industries.0104a.parse",
            3,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:PARSE",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:parse",
        ),
        OperationRef(
            "cbr.industries.0104a.build_stream",
            3,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:BUILD_STREAM",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:build_stream",
        ),
        OperationRef(
            "cbr.industries.0104a.calculate_apk",
            2,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:CALCULATE_APK",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:calculate_apk",
        ),
        OperationRef(
            "cbr.industries.0104a.build_pivots",
            2,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:PIVOT",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:build_pivots",
        ),
        OperationRef(
            "cbr.industries.0104a.render_industry",
            2,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:RENDER_INDUSTRY",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:render_industry",
        ),
        OperationRef(
            "cbr.industries.0104a.render_industries",
            1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:RENDER_INDUSTRIES",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:render_industries",
        ),
        OperationRef("cbr.industries.0104a.integrate_flakes", 1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:INTEGRATE_FLAKES",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.snapshot_operations:integrate_flakes"),
        OperationRef("cbr.industries.0104a.flake_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:FLAKE_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.snapshot_operations:build_flake_snapshot"),
        OperationRef("cbr.industries.0104a.read_flake_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:READ_FLAKE_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.snapshot_operations:read_flake_snapshot"),
        OperationRef("cbr.industries.0104a.stream_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:STREAM_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.snapshot_operations:build_stream_snapshot"),
        OperationRef("cbr.industries.0104a.read_stream_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:READ_STREAM_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.snapshot_operations:read_stream_snapshot"),
        OperationRef("cbr.industries.0104a.calculation_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:CALCULATION_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.snapshot_operations:build_calculation_snapshot"),
        OperationRef("cbr.industries.0104a.read_calculation_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:READ_CALCULATION_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.snapshot_operations:read_calculation_snapshot"),
        OperationRef("cbr.industries.0104a.view_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:VIEW_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.snapshot_operations:build_view_snapshot"),
        OperationRef("cbr.industries.0104a.read_view_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:READ_VIEW_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.snapshot_operations:read_view_snapshot"),
    ),
    stages=(
        StageDeclaration(ProcessingStage.PRESERVE, "delegated", "processing.logical_dataset_storage",
            (OperationKey("source.save_original", 1), OperationKey("source.read_original", 1),
             OperationKey("dataset.write_snapshot", 1), OperationKey("dataset.read_snapshot", 1)),
            "Retain exact original bytes or a complete encoded flake, stream, calculation or view snapshot through independently selected stores; restore with the matching domain decoder."),
        StageDeclaration(
            ProcessingStage.READABLE, "missing", "processing.readable_not_implemented"
        ),
        StageDeclaration(
            ProcessingStage.INGEST, "delegated", "processing.logical_dataset_storage",
            (OperationKey("dataset.write_snapshot", 1),),
            "Encode a domain value as a complete DatasetSnapshot and ingest it through the selected dataset writer."
        ),
    ),
)
