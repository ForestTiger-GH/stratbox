"""Рабочая схема бизнес-среды приложения."""

from app.workspace.models import (
    WorkspaceSchema,
    DiagnosticItem,
    DiagnosticReport,
    DataRootStatus,
    WorkspaceRootStatus,
    WorkspaceResolution,
)
from app.workspace.registry import WorkspaceRegistry, load_workspace_registry
from app.workspace.filestore import build_filestore_for_data_root, build_filestore_for_workspace_root
from app.workspace.diagnostics import resolve_data_root_status, run_workspace_diagnostics
from app.workspace.resolver import resolve_workspace_root

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
