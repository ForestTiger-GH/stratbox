
"""Рабочая схема бизнес-среды приложения."""

from app.workspace.models import WorkspaceSchema, DiagnosticItem, DiagnosticReport, DataRootStatus
from app.workspace.registry import WorkspaceRegistry, load_workspace_registry
from app.workspace.filestore import build_filestore_for_data_root
from app.workspace.diagnostics import resolve_data_root_status, run_workspace_diagnostics

__all__ = [
    "WorkspaceSchema",
    "DiagnosticItem",
    "DiagnosticReport",
    "DataRootStatus",
    "WorkspaceRegistry",
    "load_workspace_registry",
    "build_filestore_for_data_root",
    "resolve_data_root_status",
    "run_workspace_diagnostics",
]
