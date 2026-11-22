"""Published independent escrow operations and storage delegation."""
from stratbox.core.execution.catalog import OperationRegistration, OperationRef
from stratbox.core.execution.semantics import ProcessingStage, StageDeclaration, OperationKey

_BASE = "stratbox.domains.cbr.escrow"
_ITEMS = (
    ("discover", 1, "DISCOVER", "operations", "discover"),
    ("acquire", 1, "ACQUIRE", "operations", "acquire"),
    ("parse", 3, "PARSE", "operations", "parse"),
    ("build_history", 3, "HISTORY", "operations", "build_history"),
    ("build_views", 3, "VIEWS", "operations", "build_views"),
    ("render_workbook", 2, "RENDER", "operations", "render_workbook"),
    ("integrate_flakes", 1, "INTEGRATE", "lifecycle", "integrate_flakes"),
    ("flake_snapshot", 1, "FLAKE_SNAPSHOT", "lifecycle", "build_flake_snapshot"),
    ("read_flake_snapshot", 1, "READ_FLAKE_SNAPSHOT", "lifecycle", "read_flake_snapshot"),
    ("dataset_snapshot", 1, "DATASET_SNAPSHOT", "lifecycle", "build_dataset_snapshot"),
    ("read_dataset_snapshot", 1, "READ_DATASET_SNAPSHOT", "lifecycle", "read_dataset_snapshot"),
    ("view_snapshot", 1, "VIEW_SNAPSHOT", "lifecycle", "build_view_snapshot"),
    ("read_view_snapshot", 1, "READ_VIEW_SNAPSHOT", "lifecycle", "read_view_snapshot"),
)
REGISTRATION = OperationRegistration(
    owner_id="cbr.escrow",
    operations=tuple(OperationRef(f"cbr.escrow.{name}", version, f"{_BASE}.definitions:{definition}",
                                  f"{_BASE}.{module}:{handler}") for name, version, definition, module, handler in _ITEMS),
    stages=(
        StageDeclaration(ProcessingStage.PRESERVE, "delegated", "processing.neutral_material_storage",
            (OperationKey("source.save_original", 1), OperationKey("source.read_original", 1),
             OperationKey("dataset.write_snapshot", 1), OperationKey("dataset.read_snapshot", 1),
             OperationKey("material.save_artifact", 1)),
            "Retain exact originals, encoded domain snapshots and rendered artifacts through caller-selected adapters; restore each with its matching domain decoder."),
        StageDeclaration(ProcessingStage.READABLE, "missing", "processing.readable_not_implemented"),
        StageDeclaration(ProcessingStage.INGEST, "delegated", "processing.logical_dataset_storage",
            (OperationKey("dataset.write_snapshot", 1),),
            "Encode a complete flake, integrated dataset or prepared view, retain it through a caller-selected dataset adapter, then decode the restored snapshot."),
        StageDeclaration(ProcessingStage.PUBLISH, "missing", "processing.external_publication_owned_by_consumer"),
    ),
)
