"""Frank RG report discovery, recognition and exact original file handling.

Logical registries and typed methods are independent of caller-selected storage.
Public names load lazily; importing the domain opens no files or workbooks.
"""
from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    ".publications.contracts": (
        "ProfileRefs", "SourceSeries", "SourceFamily", "ReportPeriod", "FileEntry",
        "DiscoveryRequest", "SourceIndex", "Asset", "InspectionRequest", "Inventory",
        "Selection", "SelectionRequest", "Catalog", "AcquireRequest", "CaptureRequest",
        "AcquiredReport", "SourceCheckpoint", "UpdateRequest", "UpdateDecision", "UpdatePlan",
        "MaterialAssessment", "AssessMaterialRequest", "PrepareFileRequest", "PreparedFile",
    ),
    ".publications.catalog": ("families", "family", "source", "all_sources"),
    ".publications.cleanup": (
        "CleanupAction", "PlanCleanupRequest", "CleanupPlan", "ApplyCleanupRequest", "CleanupReceipt",
    ),
    ".publications.updates": ("checkpoint_for",),
    ".operations.bindings": (
        "BoundFamily", "BoundSource", "bind_family", "bind_source", "validate_all_profiles",
    ),
    ".operations.handlers": (
        "discover", "inspect", "select", "scan", "acquire", "capture", "prepare_file",
        "plan_updates", "assess_material",
    ),
    ".operations.definitions": (
        "DISCOVER", "INSPECT", "SELECT", "SCAN", "ACQUIRE", "CAPTURE", "PREPARE_FILE",
        "PLAN_UPDATES", "ASSESS_MATERIAL",
    ),
    ".operations.housekeeping": (
        "plan_cleanup", "apply_cleanup", "prepare_archive", "prepare_archive_to_store",
    ),
    ".operations.housekeeping_definitions": (
        "StreamArchiveRequest", "PLAN", "APPLY", "ARCHIVE", "STREAM_ARCHIVE",
    ),
}
_MODULES = {name: module for module, names in _EXPORTS.items() for name in names}


def __getattr__(name):
    module = _MODULES.get(name)
    if module is None:
        raise AttributeError(name)
    value = getattr(import_module(module, __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(_MODULES))


__all__ = tuple(_MODULES)
