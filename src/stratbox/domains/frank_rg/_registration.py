"""One operation owner for logical report sources and explicit file effects."""
from stratbox.core.execution.catalog import OperationRef, OperationRegistration
from stratbox.core.execution.semantics import OperationKey, ProcessingStage, StageDeclaration

_BASE = "stratbox.domains.frank_rg.operations"

REGISTRATION = OperationRegistration(
    owner_id="frank_rg",
    operations=(
        OperationRef("frg.discover", 1, _BASE + ".definitions:DISCOVER", _BASE + ".handlers:discover"),
        OperationRef("frg.inspect", 1, _BASE + ".definitions:INSPECT", _BASE + ".handlers:inspect"),
        OperationRef("frg.select", 1, _BASE + ".definitions:SELECT", _BASE + ".handlers:select"),
        OperationRef("frg.scan", 1, _BASE + ".definitions:SCAN", _BASE + ".handlers:scan"),
        OperationRef("frg.acquire", 1, _BASE + ".definitions:ACQUIRE", _BASE + ".handlers:acquire"),
        OperationRef("frg.capture", 1, _BASE + ".definitions:CAPTURE", _BASE + ".handlers:capture"),
        OperationRef("frg.prepare_file", 1, _BASE + ".definitions:PREPARE_FILE", _BASE + ".handlers:prepare_file"),
        OperationRef("frg.plan_updates", 1, _BASE + ".definitions:PLAN_UPDATES", _BASE + ".handlers:plan_updates"),
        OperationRef("frg.assess_material", 1, _BASE + ".definitions:ASSESS_MATERIAL", _BASE + ".handlers:assess_material"),
        OperationRef("frg.plan_cleanup", 1, _BASE + ".housekeeping_definitions:PLAN", _BASE + ".housekeeping:plan_cleanup",
                     _BASE + ".machine:PLAN_CODEC", _BASE + ".machine_contracts:PLAN_CONTRACT"),
        OperationRef("frg.apply_cleanup", 1, _BASE + ".housekeeping_definitions:APPLY", _BASE + ".housekeeping:apply_cleanup"),
        OperationRef("frg.prepare_archive", 1, _BASE + ".housekeeping_definitions:ARCHIVE", _BASE + ".housekeeping:prepare_archive"),
        OperationRef("frg.prepare_archive_to_store", 2, _BASE + ".housekeeping_definitions:STREAM_ARCHIVE", _BASE + ".housekeeping:prepare_archive_to_store"),
    ),
    stages=(
        StageDeclaration(ProcessingStage.PRESERVE, "delegated", "frg.original_storage_shared",
            (OperationKey("source.save_original", 1), OperationKey("source.read_original", 1)),
            "Pass an acquired or prepared report payload to neutral original storage; the destination and store belong to the caller."),
        StageDeclaration(ProcessingStage.EXTRACT, "missing", "frg.workbook_extraction_unimplemented"),
        StageDeclaration(ProcessingStage.READ_EXTRACT, "missing", "frg.extract_reading_unimplemented"),
        StageDeclaration(ProcessingStage.READABLE, "missing", "frg.readable_conversion_unimplemented"),
        StageDeclaration(ProcessingStage.CALCULATE, "missing", "frg.calculations_unimplemented"),
        StageDeclaration(ProcessingStage.INTEGRATE, "missing", "frg.integration_unimplemented"),
        StageDeclaration(ProcessingStage.INGEST, "missing", "frg.ingestion_unimplemented"),
    ),
)
