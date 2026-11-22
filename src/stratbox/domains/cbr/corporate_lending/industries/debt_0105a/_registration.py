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
        OperationRef("cbr.industries.0105a.integrate_flakes", 1,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:INTEGRATE_FLAKES",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.snapshot_operations:integrate_flakes"),
        OperationRef("cbr.industries.0105a.flake_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:FLAKE_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.snapshot_operations:build_flake_snapshot"),
        OperationRef("cbr.industries.0105a.read_flake_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:READ_FLAKE_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.snapshot_operations:read_flake_snapshot"),
        OperationRef("cbr.industries.0105a.stream_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:STREAM_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.snapshot_operations:build_stream_snapshot"),
        OperationRef("cbr.industries.0105a.read_stream_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:READ_STREAM_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.snapshot_operations:read_stream_snapshot"),
        OperationRef("cbr.industries.0105a.calculation_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:CALCULATION_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.snapshot_operations:build_calculation_snapshot"),
        OperationRef("cbr.industries.0105a.read_calculation_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:READ_CALCULATION_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.snapshot_operations:read_calculation_snapshot"),
        OperationRef("cbr.industries.0105a.view_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:VIEW_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.snapshot_operations:build_view_snapshot"),
        OperationRef("cbr.industries.0105a.read_view_snapshot", 1,
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.definitions:READ_VIEW_SNAPSHOT",
            "stratbox.domains.cbr.corporate_lending.industries.debt_0105a.snapshot_operations:read_view_snapshot"),
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
