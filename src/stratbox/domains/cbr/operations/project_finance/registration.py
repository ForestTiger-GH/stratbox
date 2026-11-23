"""Published independent escrow operations and storage delegation."""
from stratbox.core.execution.catalog import OperationRef
from stratbox.core.execution.semantics import ProcessingStage, StageDeclaration, OperationKey

_BASE = "stratbox.domains.cbr.operations.project_finance"
_ITEMS = (
    ("validate", 1, "VALIDATE", "inspection", "validate"),
    ("compare", 1, "COMPARE", "inspection", "compare"),
    ("readable", 1, "READABLE", "inspection", "readable"),
    ("align_observations", 1, "ALIGN", "inspection", "align_observations"),
    ("discover", 1, "DISCOVER", "handlers", "discover"),
    ("acquire", 1, "ACQUIRE", "handlers", "acquire"),
    ("parse", 4, "PARSE", "handlers", "parse"),
    ("build_history", 4, "HISTORY", "handlers", "build_history"),
    ("build_views", 4, "VIEWS", "handlers", "build_views"),
    ("render_workbook", 3, "RENDER", "handlers", "render_workbook"),
    ("integrate_flakes", 2, "INTEGRATE", "lifecycle", "integrate_flakes"),
    ("flake_snapshot", 2, "FLAKE_SNAPSHOT", "lifecycle", "build_flake_snapshot"),
    ("read_flake_snapshot", 2, "READ_FLAKE_SNAPSHOT", "lifecycle", "read_flake_snapshot"),
    ("dataset_snapshot", 2, "DATASET_SNAPSHOT", "lifecycle", "build_dataset_snapshot"),
    ("read_dataset_snapshot", 2, "READ_DATASET_SNAPSHOT", "lifecycle", "read_dataset_snapshot"),
    ("view_snapshot", 2, "VIEW_SNAPSHOT", "lifecycle", "build_view_snapshot"),
    ("read_view_snapshot", 2, "READ_VIEW_SNAPSHOT", "lifecycle", "read_view_snapshot"),
)
OPERATIONS = tuple(OperationRef(f"cbr.escrow.{name}", version, f"{_BASE}.definitions:{definition}",
                                  f"{_BASE}.{module}:{handler}") for name, version, definition, module, handler in _ITEMS)
STAGES = (
    StageDeclaration(ProcessingStage.PRESERVE, "delegated", "processing.neutral_material_storage",
        (OperationKey("source.save_original", 1), OperationKey("source.read_original", 1),
         OperationKey("dataset.write_snapshot", 1), OperationKey("dataset.read_snapshot", 1),
         OperationKey("material.save_artifact", 1)),
        "Retain exact originals, complete typed snapshots and rendered artifacts through the caller's storage adapters."),
    StageDeclaration(ProcessingStage.INGEST, "delegated", "processing.logical_dataset_storage",
        (OperationKey("dataset.write_snapshot", 1),),
        "Encode complete source flakes, integrated datasets or prepared views and ingest with the selected dataset adapter."),
    StageDeclaration(ProcessingStage.PUBLISH, "missing", "processing.external_publication_owned_by_consumer"),
)
