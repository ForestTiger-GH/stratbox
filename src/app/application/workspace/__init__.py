"""Рабочая схема бизнес-среды приложения."""

from app.application.workspace.models import (
    WorkspaceSchema,
    DiagnosticItem,
    DiagnosticReport,
    DataRootStatus,
    WorkspaceRootStatus,
    WorkspaceResolution,
)
from app.application.workspace.registry import WorkspaceRegistry, load_workspace_registry
from app.application.workspace.filestore import build_filestore_for_data_root, build_filestore_for_workspace_root
from app.application.workspace.diagnostics import resolve_data_root_status, run_workspace_diagnostics
from app.application.workspace.resolver import resolve_workspace_root

__all__ = [
    "WorkspaceSchema",
    "DiagnosticItem",
    "DiagnosticReport",
    "DataRootStatus",
    "WorkspaceRootStatus",
    "WorkspaceResolution",
    "WorkspaceRegistry",
    "load_workspace_registry",
    "build_filestore_for_data_root",
    "build_filestore_for_workspace_root",
    "resolve_data_root_status",
    "resolve_workspace_root",
    "run_workspace_diagnostics",
]
