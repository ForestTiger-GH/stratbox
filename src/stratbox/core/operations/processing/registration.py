"""Lazy declarations for source-neutral processing functions."""
from stratbox.core.execution.catalog import OperationRef, OperationRegistration

_ROOT = "stratbox.core.operations.processing."
REGISTRATION = OperationRegistration("core.processing", tuple(
    OperationRef(op, 1, _ROOT+"definitions:"+definition, _ROOT+"handlers:"+handler)
    for op, definition, handler in (
        ("processing.plan_update", "UPDATE", "plan_update"),
        ("workbook.extract", "WORKBOOK", "extract_workbook"),
        ("workbook.readable", "WORKBOOK_READABLE", "readable_workbook"),
        ("workbook.snapshot", "WORKBOOK_SNAPSHOT", "snapshot_workbook"),
        ("workbook.replay", "WORKBOOK_REPLAY", "replay_workbook"),
        ("workbook.compare", "WORKBOOK_COMPARE", "compare_workbooks"),
        ("document.extract", "DOCUMENT", "extract_document"),
        ("document.readable", "DOCUMENT_READABLE", "readable_document"),
        ("document.snapshot", "DOCUMENT_SNAPSHOT", "snapshot_document"),
        ("document.replay", "DOCUMENT_REPLAY", "replay_document"),
        ("observations.prepare_view", "VIEW", "prepare_view"),
        ("observations.view_snapshot", "VIEW_SNAPSHOT", "snapshot_view"),
        ("observations.replay_view", "VIEW_REPLAY", "replay_view"),
        ("observations.render_view", "VIEW_RENDER", "render_view"),
    )))
