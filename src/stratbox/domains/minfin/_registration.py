"""One exact domain operation owner; registry YAML remains at this domain root."""
from stratbox.core.execution.catalog import OperationRegistration, OperationRef
from stratbox.core.execution.semantics import ProcessingStage, StageDeclaration, OperationKey

_BASE = "stratbox.domains.minfin"

REGISTRATION = OperationRegistration(
    owner_id="minfin",
    operations=(
        OperationRef("minfin.discover", 1, _BASE + ".definitions:DISCOVER", _BASE + ".operations:discover"),
        OperationRef("minfin.inspect", 1, _BASE + ".definitions:INSPECT", _BASE + ".operations:inspect"),
        OperationRef("minfin.acquire", 1, _BASE + ".definitions:ACQUIRE", _BASE + ".operations:acquire"),
        OperationRef("minfin.capture", 1, _BASE + ".definitions:CAPTURE", _BASE + ".operations:capture"),
        OperationRef("minfin.serialize", 1, _BASE + ".definitions:SERIALIZE", _BASE + ".operations:serialize_extract"),
        OperationRef("minfin.read_representation", 1, _BASE + ".definitions:READ_EXTRACT", _BASE + ".operations:read_representation"),
        OperationRef("minfin.extract", 1, _BASE + ".definitions:EXTRACT", _BASE + ".operations:extract"),
        OperationRef("minfin.validate", 1, _BASE + ".definitions:VALIDATE", _BASE + ".operations:validate"),
        OperationRef("minfin.compare", 1, _BASE + ".definitions:COMPARE", _BASE + ".operations:compare"),
        OperationRef("minfin.map_observations", 1, _BASE + ".definitions:MAP", _BASE + ".operations:map_observations"),
        OperationRef("minfin.render_csv", 1, _BASE + ".definitions:RENDER", _BASE + ".operations:render_csv_cells"),
        OperationRef("minfin.readable", 1, _BASE + ".definitions:READABLE", _BASE + ".operations:readable_document"),
        OperationRef("minfin.plan_updates", 1, _BASE + ".pipeline_definitions:PLAN_UPDATES", _BASE + ".pipeline_operations:plan_updates"),
        OperationRef("minfin.build_flake", 1, _BASE + ".pipeline_definitions:BUILD_FLAKE", _BASE + ".pipeline_operations:build_source_flake"),
        OperationRef("minfin.render_flake", 1, _BASE + ".pipeline_definitions:RENDER_FLAKE", _BASE + ".pipeline_operations:render_source_flake"),
        OperationRef("minfin.summarize", 1, _BASE + ".pipeline_definitions:SUMMARIZE", _BASE + ".pipeline_operations:calculate_headlines"),
        OperationRef("minfin.prepare_notice", 1, _BASE + ".pipeline_definitions:PREPARE_NOTICE", _BASE + ".pipeline_operations:prepare_notice_facts"),
    ),
    stages=(
        StageDeclaration(ProcessingStage.PRESERVE, "delegated", "minfin.original_storage_shared",
            (OperationKey("source.save_original", 1), OperationKey("source.read_original", 1)),
            "Bind a confirmed acquired SourcePayload to the neutral source original storage operation; the destination belongs to the caller."),
        StageDeclaration(ProcessingStage.INTEGRATE, "missing", "minfin.integration_pending"),
        StageDeclaration(ProcessingStage.INGEST, "missing", "minfin.ingestion_pending"),
        StageDeclaration(ProcessingStage.PUBLISH, "missing", "minfin.publication_owned_by_consumer"),
    ),
)