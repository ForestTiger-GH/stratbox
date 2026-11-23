"""Explicit source-collection compositions; no separate statistical owner."""
from stratbox.core.execution.catalog import OperationRef

_BASE = "stratbox.domains.cbr.operations.collection"
OPERATIONS = (
    OperationRef("cbr.file_collector.collect_materials", 1, _BASE + ".material_definitions:COLLECT_MATERIALS", _BASE + ".materials:collect_materials"),
    *(OperationRef("cbr.file_collector." + name, version, _BASE + ".definitions:" + definition,
        _BASE + ".handlers:" + name) for name, version, definition in (
        ("discover", 1, "DISCOVER"), ("collect_raw", 2, "COLLECT"),
        ("prepare_archive", 2, "ARCHIVE"), ("collect_to_store", 1, "COLLECT_TO_STORE"),
        ("archive_to_store", 2, "ARCHIVE_TO_STORE"))),
)
STAGES = ()
