"""Operation references aggregated by the single CBR domain registration."""
from stratbox.core.execution.catalog import OperationRef
from stratbox.core.execution.semantics import ProcessingStage, StageDeclaration, OperationKey

OPERATIONS = (
    OperationRef('cbr.offices.parse', 1, 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions:PARSE', 'stratbox.domains.cbr.operations.service_network.bank_offices.operations:parse', 'stratbox.domains.cbr.operations.service_network.bank_offices.machine:PARSE_CODEC', 'stratbox.domains.cbr.operations.service_network.bank_offices.machine_contracts:PARSE_CONTRACT'),
    OperationRef('cbr.offices.acquire', 2, 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions:ACQUIRE', 'stratbox.domains.cbr.operations.service_network.bank_offices.operations:acquire'),
    OperationRef('cbr.offices.capture', 2, 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions:CAPTURE', 'stratbox.domains.cbr.operations.service_network.bank_offices.operations:capture'),
    OperationRef('cbr.offices.read_representation', 2, 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions:READ', 'stratbox.domains.cbr.operations.service_network.bank_offices.operations:read_representation'),
    OperationRef('cbr.offices.snapshot', 1, 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions:SNAPSHOT', 'stratbox.domains.cbr.operations.service_network.bank_offices.snapshots:snapshot_release'),
    OperationRef('cbr.offices.restore', 1, 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions:RESTORE', 'stratbox.domains.cbr.operations.service_network.bank_offices.snapshots:restore_release'),
    OperationRef('cbr.offices.compare', 2, 'stratbox.domains.cbr.operations.service_network.bank_offices.definitions:COMPARE', 'stratbox.domains.cbr.operations.service_network.bank_offices.operations:compare', 'stratbox.domains.cbr.operations.service_network.bank_offices.machine:COMPARE_CODEC', 'stratbox.domains.cbr.operations.service_network.bank_offices.machine_contracts:COMPARE_CONTRACT'),
    OperationRef('cbr.offices_reg.discover', 1, 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions:DISCOVER', 'stratbox.domains.cbr.operations.service_network.territorial_offices.operations:discover'),
    OperationRef('cbr.offices_reg.acquire', 1, 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions:ACQUIRE', 'stratbox.domains.cbr.operations.service_network.territorial_offices.operations:acquire'),
    OperationRef('cbr.offices_reg.parse', 3, 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions:PARSE', 'stratbox.domains.cbr.operations.service_network.territorial_offices.operations:parse'),
    OperationRef('cbr.offices_reg.capture', 3, 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions:CAPTURE', 'stratbox.domains.cbr.operations.service_network.territorial_offices.operations:capture'),
    OperationRef('cbr.offices_reg.read_representation', 2, 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions:READ', 'stratbox.domains.cbr.operations.service_network.territorial_offices.operations:read_representation'),
    OperationRef('cbr.offices_reg.snapshot', 1, 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions:SNAPSHOT', 'stratbox.domains.cbr.operations.service_network.territorial_offices.snapshots:snapshot_release'),
    OperationRef('cbr.offices_reg.restore', 1, 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions:RESTORE', 'stratbox.domains.cbr.operations.service_network.territorial_offices.snapshots:restore_release'),
    OperationRef('cbr.offices_reg.compare', 2, 'stratbox.domains.cbr.operations.service_network.territorial_offices.definitions:COMPARE', 'stratbox.domains.cbr.operations.service_network.territorial_offices.operations:compare'),
    OperationRef('cbr.service_network.make_readable', 1, 'stratbox.domains.cbr.operations.service_network.lifecycle_definitions:READABLE', 'stratbox.domains.cbr.operations.service_network.lifecycle:make_readable'),
    OperationRef('cbr.service_network.build_history', 1, 'stratbox.domains.cbr.operations.service_network.lifecycle_definitions:HISTORY', 'stratbox.domains.cbr.operations.service_network.lifecycle:build_source_history'),
    OperationRef('cbr.service_network.restore_history', 1, 'stratbox.domains.cbr.operations.service_network.lifecycle_definitions:RESTORE_HISTORY', 'stratbox.domains.cbr.operations.service_network.lifecycle:restore_history'),
    OperationRef('cbr.service_network.align', 1, 'stratbox.domains.cbr.operations.service_network.lifecycle_definitions:ALIGN', 'stratbox.domains.cbr.operations.service_network.lifecycle:align_offices'),
    OperationRef('cbr.service_network.calculate_changes', 1, 'stratbox.domains.cbr.operations.service_network.lifecycle_definitions:CHANGES', 'stratbox.domains.cbr.operations.service_network.lifecycle:calculate_changes'),
    OperationRef('cbr.service_network.build_view', 1, 'stratbox.domains.cbr.operations.service_network.lifecycle_definitions:VIEW', 'stratbox.domains.cbr.operations.service_network.lifecycle:build_view'),
    OperationRef('cbr.service_network.render', 1, 'stratbox.domains.cbr.operations.service_network.lifecycle_definitions:RENDER', 'stratbox.domains.cbr.operations.service_network.lifecycle:render'),
)
OPERATIONS += (
    OperationRef('cbr.service_network.observations_snapshot',1,'stratbox.domains.cbr.operations.service_network.observation_definitions:SNAPSHOT','stratbox.domains.cbr.operations.service_network.observation_operations:snapshot_observations'),
    OperationRef('cbr.service_network.restore_observations',1,'stratbox.domains.cbr.operations.service_network.observation_definitions:RESTORE','stratbox.domains.cbr.operations.service_network.observation_operations:restore_observations'),
)

STAGES = (
    StageDeclaration(ProcessingStage.PRESERVE, "delegated", "processing.neutral_material_storage",
        (OperationKey("source.save_original", 1), OperationKey("source.read_original", 1),
         OperationKey("dataset.write_snapshot", 1), OperationKey("dataset.read_snapshot", 1)),
        "Retain exact original bytes or a complete typed source/result snapshot through the selected store."),
    StageDeclaration(ProcessingStage.INGEST, "delegated", "processing.logical_dataset_storage",
        (OperationKey("dataset.write_snapshot", 1),), "Write the admitted typed snapshot through the chosen dataset adapter."),
)
