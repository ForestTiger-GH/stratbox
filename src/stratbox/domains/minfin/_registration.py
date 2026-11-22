"""One exact domain operation owner; registry YAML remains at this domain root."""
from stratbox.core.execution.catalog import OperationRegistration, OperationRef
from stratbox.core.execution.semantics import ProcessingStage, StageDeclaration, OperationKey

_BASE = "stratbox.domains.minfin.operations"

REGISTRATION = OperationRegistration(
    owner_id="minfin",
    operations=(
        OperationRef("minfin.discover", 1, _BASE + ".definitions:DISCOVER", _BASE + ".handlers:discover"),
        OperationRef("minfin.inspect", 1, _BASE + ".definitions:INSPECT", _BASE + ".handlers:inspect"),
        OperationRef("minfin.acquire", 1, _BASE + ".definitions:ACQUIRE", _BASE + ".handlers:acquire"),
        OperationRef("minfin.capture", 1, _BASE + ".definitions:CAPTURE", _BASE + ".handlers:capture"),
        OperationRef("minfin.serialize", 1, _BASE + ".definitions:SERIALIZE", _BASE + ".handlers:serialize_extract"),
        OperationRef("minfin.read_representation", 1, _BASE + ".definitions:READ_EXTRACT", _BASE + ".handlers:read_representation"),
        OperationRef("minfin.extract", 1, _BASE + ".definitions:EXTRACT", _BASE + ".handlers:extract"),
        OperationRef("minfin.validate", 1, _BASE + ".definitions:VALIDATE", _BASE + ".handlers:validate"),
        OperationRef("minfin.compare", 1, _BASE + ".definitions:COMPARE", _BASE + ".handlers:compare"),
        OperationRef("minfin.map_observations", 1, _BASE + ".definitions:MAP", _BASE + ".handlers:map_observations"),
        OperationRef("minfin.render_csv", 1, _BASE + ".definitions:RENDER", _BASE + ".handlers:render_csv_cells"),
        OperationRef("minfin.readable", 1, _BASE + ".definitions:READABLE", _BASE + ".handlers:readable_document"),
        OperationRef("minfin.plan_updates", 1, _BASE + ".definitions:PLAN_UPDATES", _BASE + ".handlers:plan_updates"),
        OperationRef("minfin.build_flake", 1, _BASE + ".definitions:BUILD_FLAKE", _BASE + ".handlers:build_source_flake"),
        OperationRef("minfin.render_flake", 1, _BASE + ".definitions:RENDER_FLAKE", _BASE + ".handlers:render_source_flake"),
        OperationRef("minfin.serialize_flake", 1, _BASE + ".definitions:SERIALIZE_FLAKE", _BASE + ".handlers:serialize_source_flake"),
        OperationRef("minfin.read_flake", 1, _BASE + ".definitions:READ_FLAKE", _BASE + ".handlers:read_source_flake"),
        OperationRef("minfin.flake_snapshot", 1, _BASE + ".definitions:FLAKE_SNAPSHOT", _BASE + ".handlers:build_flake_snapshot"),
        OperationRef("minfin.read_flake_snapshot", 1, _BASE + ".definitions:READ_FLAKE_SNAPSHOT", _BASE + ".handlers:read_flake_snapshot"),
        OperationRef("minfin.summarize", 1, _BASE + ".definitions:SUMMARIZE", _BASE + ".handlers:calculate_headlines"),
        OperationRef("minfin.prepare_notice", 1, _BASE + ".definitions:PREPARE_NOTICE", _BASE + ".handlers:prepare_notice_facts"),
    ),
    stages=(
        StageDeclaration(ProcessingStage.PRESERVE, "delegated", "minfin.original_storage_shared",
            (OperationKey("source.save_original", 1), OperationKey("source.read_original", 1),
             OperationKey("dataset.write_snapshot", 1), OperationKey("dataset.read_snapshot", 1)),
            "Bind confirmed original bytes or a complete source-flake DatasetSnapshot to the neutral storage operation; the destination belongs to the caller."),
        StageDeclaration(ProcessingStage.INTEGRATE, "missing", "minfin.integration_pending"),
        StageDeclaration(ProcessingStage.INGEST, "delegated", "minfin.flake_dataset_storage",
            (OperationKey("dataset.write_snapshot", 1),),
            "Encode the complete source flake with minfin.flake_snapshot and ingest its typed tables through the selected dataset adapter."),
        StageDeclaration(ProcessingStage.PUBLISH, "missing", "minfin.publication_owned_by_consumer"),
    ),
)
