"""One exact CBR owner aggregates independently maintained operation segments."""
from importlib import import_module
from stratbox.core.execution.catalog import OperationRegistration
from stratbox.core.execution.semantics import OperationKey, ProcessingStage, StageDeclaration

_SEGMENTS = ("catalog", "publications", "collection", "statistics", "corporate_lending",
             "reporting_forms", "service_network", "project_finance")
OPERATIONS = tuple(reference for segment in _SEGMENTS for reference in
                   import_module(f"stratbox.domains.cbr.operations.{segment}.registration").OPERATIONS)
REGISTRATION = OperationRegistration("cbr", OPERATIONS, (
    StageDeclaration(ProcessingStage.PRESERVE, "delegated", "cbr.storage.caller_selected",
        (OperationKey("source.save_original", 1), OperationKey("source.read_original", 1),
         OperationKey("dataset.write_snapshot", 1), OperationKey("dataset.read_snapshot", 1),
         OperationKey("material.save_artifact", 1)),
        "Choose storage for exact originals, complete logical datasets and rendered products; source-scoped availability is described by cbr.describe_source."),
    StageDeclaration(ProcessingStage.INGEST, "delegated", "cbr.datasets.caller_selected",
        (OperationKey("dataset.write_snapshot", 1),),
        "Encode an admitted source, integrated or product snapshot and ingest it through the selected dataset adapter."),
    StageDeclaration(ProcessingStage.PUBLISH, "missing", "cbr.publication.consumer_owned"),
), source_catalog_ref="stratbox.domains.cbr.operations.source_catalog:source_cards")
