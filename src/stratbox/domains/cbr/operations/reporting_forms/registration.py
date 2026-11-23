"""Operation references aggregated by the single CBR domain registration."""
from stratbox.core.execution.catalog import OperationRef
from stratbox.core.execution.semantics import ProcessingStage, StageDeclaration, OperationKey

OPERATIONS = (
    OperationRef('cbr.forms.read_flake_export', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:READ_FLAKE_EXPORT', 'stratbox.domains.cbr.operations.reporting_forms.flake_export:read_flake_export'),
    OperationRef('cbr.forms.render_flakes', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:RENDER_FLAKES', 'stratbox.domains.cbr.operations.reporting_forms.flake_export:render_flakes'),
    OperationRef('cbr.forms.discover_sources', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:DISCOVER', 'stratbox.domains.cbr.operations.reporting_forms.extracts:discover_sources'),
    OperationRef('cbr.forms.extract', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:EXTRACT', 'stratbox.domains.cbr.operations.reporting_forms.extracts:extract_forms'),
    OperationRef('cbr.forms.normalize', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:NORMALIZE', 'stratbox.domains.cbr.operations.reporting_forms.extracts:normalize_form'),
    OperationRef('cbr.forms.flake_snapshot', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:FLAKE_SNAPSHOT', 'stratbox.domains.cbr.operations.reporting_forms.extracts:flake_snapshot'),
    OperationRef('cbr.forms.restore_flakes', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:RESTORE_FLAKES', 'stratbox.domains.cbr.operations.reporting_forms.extracts:restore_flakes'),
    OperationRef('cbr.forms.result_snapshot', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:RESULT_SNAPSHOT', 'stratbox.domains.cbr.operations.reporting_forms.extracts:snapshot_result'),
    OperationRef('cbr.forms.restore_normalized', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:RESTORE_NORMALIZED', 'stratbox.domains.cbr.operations.reporting_forms.extracts:restore_normalized'),
    OperationRef('cbr.forms.restore_data', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:RESTORE_DATA', 'stratbox.domains.cbr.operations.reporting_forms.extracts:restore_data'),
    OperationRef('cbr.forms.restore_views', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:RESTORE_VIEWS', 'stratbox.domains.cbr.operations.reporting_forms.extracts:restore_views'),
    OperationRef('cbr.forms.build_history', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:HISTORY', 'stratbox.domains.cbr.operations.reporting_forms.extracts:build_source_history'),
    OperationRef('cbr.forms.restore_history', 1, 'stratbox.domains.cbr.operations.reporting_forms.source_definitions:RESTORE_HISTORY', 'stratbox.domains.cbr.operations.reporting_forms.extracts:restore_history'),
    OperationRef('cbr.forms.select_sources', 1, 'stratbox.domains.cbr.operations.reporting_forms.definitions:SELECT', 'stratbox.domains.cbr.operations.reporting_forms.acquisition:select_sources'),
    OperationRef('cbr.forms.acquire', 1, 'stratbox.domains.cbr.operations.reporting_forms.definitions:ACQUIRE', 'stratbox.domains.cbr.operations.reporting_forms.acquisition:acquire'),
    OperationRef('cbr.forms.parse', 2, 'stratbox.domains.cbr.operations.reporting_forms.definitions:PARSE', 'stratbox.domains.cbr.operations.reporting_forms.extracts:parse_form'),
    OperationRef('cbr.forms.build_data', 2, 'stratbox.domains.cbr.operations.reporting_forms.definitions:BUILD', 'stratbox.domains.cbr.operations.reporting_forms.calculation:build_form_data'),
    OperationRef('cbr.forms.build_views', 2, 'stratbox.domains.cbr.operations.reporting_forms.definitions:VIEWS', 'stratbox.domains.cbr.operations.reporting_forms.products:build_form_views'),
    OperationRef('cbr.forms.render_workbook', 2, 'stratbox.domains.cbr.operations.reporting_forms.definitions:RENDER', 'stratbox.domains.cbr.operations.reporting_forms.products:render_workbook'),
    OperationRef('cbr.forms.align', 1, 'stratbox.domains.cbr.operations.reporting_forms.integration_definitions:ALIGN', 'stratbox.domains.cbr.operations.reporting_forms.integration:align_forms'),
)
OPERATIONS += (
    OperationRef("cbr.forms.compare", 1, "stratbox.domains.cbr.operations.reporting_forms.source_products_definitions:COMPARE", "stratbox.domains.cbr.operations.reporting_forms.source_products:compare_sources"),
    OperationRef("cbr.forms.make_readable", 1, "stratbox.domains.cbr.operations.reporting_forms.source_products_definitions:READABLE", "stratbox.domains.cbr.operations.reporting_forms.source_products:make_readable"),
)

OPERATIONS += (
    OperationRef('cbr.forms.observations_snapshot',1,'stratbox.domains.cbr.operations.reporting_forms.observation_definitions:SNAPSHOT','stratbox.domains.cbr.operations.reporting_forms.observation_operations:snapshot_observations'),
    OperationRef('cbr.forms.restore_observations',1,'stratbox.domains.cbr.operations.reporting_forms.observation_definitions:RESTORE','stratbox.domains.cbr.operations.reporting_forms.observation_operations:restore_observations'),
)

STAGES = (
    StageDeclaration(ProcessingStage.PRESERVE, "delegated", "processing.neutral_material_storage",
        (OperationKey("source.save_original", 1), OperationKey("source.read_original", 1),
         OperationKey("dataset.write_snapshot", 1), OperationKey("dataset.read_snapshot", 1)),
        "Retain exact original bytes or a complete typed source/result snapshot through the selected store."),
    StageDeclaration(ProcessingStage.INGEST, "delegated", "processing.logical_dataset_storage",
        (OperationKey("dataset.write_snapshot", 1),), "Write the admitted typed snapshot through the chosen dataset adapter."),
)

OPERATIONS += (
    OperationRef("cbr.forms.prepare_model_inputs", 1, "stratbox.domains.cbr.operations.reporting_forms.model_definitions:PREPARE", "stratbox.domains.cbr.operations.reporting_forms.calculation:prepare_model_inputs"),
    OperationRef("cbr.forms.calculate", 1, "stratbox.domains.cbr.operations.reporting_forms.model_definitions:CALCULATE", "stratbox.domains.cbr.operations.reporting_forms.calculation:calculate"),
)
