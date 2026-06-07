"""Разрешение рабочего каталога поверх business-root selector."""

from __future__ import annotations

from pathlib import Path

from app.application.workspace.models import DataRootStatus, WorkspaceResolution, WorkspaceRootStatus, WorkspaceSchema
from app.application.workspace.diagnostics import resolve_data_root_status


def _is_drive_root(path: Path) -> bool:
    """Возвращает True, если путь указывает на корень диска Windows."""
    try:
        return path.resolve() == Path(path.anchor)
    except Exception:
        return path == Path(path.anchor)


def _workspace_root_from_selector(selector_path: Path, schema: WorkspaceSchema) -> tuple[Path, str]:
    """Строит рабочий каталог из selector path."""
    if _is_drive_root(selector_path):
        home = Path.home()
        home_drive = Path(home.anchor)
        selector_drive = Path(selector_path.anchor)
        if schema.use_user_profile_for_system_drive and selector_drive == home_drive:
            return home / schema.workspace_dirname, 'user_profile_workspace'
        return selector_drive / schema.workspace_dirname, 'drive_workspace'
    return selector_path, 'explicit_workspace_root'


def resolve_workspace_root(
    schema: WorkspaceSchema,
    data_root_path: Path | None,
    *,
    run_mode: str,
    create_missing: bool = False,
) -> WorkspaceResolution:
    """Разрешает реальный рабочий каталог приложения."""
    explicit_mode = run_mode == 'standalone_dev' or schema.root_mode == 'explicit_workspace_root'
    if data_root_path is None:
        selector_status = resolve_data_root_status(data_root_path)
        workspace_status = WorkspaceRootStatus(
            path=None,
            available=False,
            exists=False,
            writable=None,
            created=False,
            message='Workspace root is unavailable because selector is unavailable',
        )
        return WorkspaceResolution(
            selector_path=None,
            selector_status=selector_status,
            workspace_root_path=None,
            workspace_status=workspace_status,
            resolution_mode='unresolved',
            source_description='selector unavailable',
        )

    raw_path = Path(data_root_path)
    if explicit_mode and create_missing and not raw_path.exists() and schema.auto_create_workspace_root:
        raw_path.mkdir(parents=True, exist_ok=True)
    selector_status = resolve_data_root_status(raw_path)
    if not selector_status.available or selector_status.path is None:
        workspace_status = WorkspaceRootStatus(
            path=(raw_path if explicit_mode else None),
            available=False,
            exists=raw_path.exists(),
            writable=None,
            created=False,
            message='Workspace root is unavailable because selector is unavailable',
        )
        return WorkspaceResolution(
            selector_path=(raw_path if explicit_mode else None),
            selector_status=selector_status,
            workspace_root_path=(raw_path if explicit_mode else None),
            workspace_status=workspace_status,
            resolution_mode='explicit_workspace_root' if explicit_mode else 'unresolved',
            source_description='workspace root uses provided path directly' if explicit_mode else 'selector unavailable',
        )

    selector_path = selector_status.path
    if explicit_mode:
        workspace_root_path = selector_path
        resolution_mode = 'explicit_workspace_root'
        source_description = 'workspace root uses provided path directly'
    else:
        workspace_root_path, resolution_mode = _workspace_root_from_selector(selector_path, schema)
        source_description = f'workspace root derived from selector via {resolution_mode}'

    created = False
    exists = workspace_root_path.exists()
    if not exists and create_missing and schema.auto_create_workspace_root:
        workspace_root_path.mkdir(parents=True, exist_ok=True)
        exists = workspace_root_path.exists()
        created = exists

    available = exists and workspace_root_path.is_dir()
    writable = None
    if available:
        writable = not schema.readonly
        message = f'Workspace root available: {workspace_root_path}'
    elif exists:
        message = f'Workspace root is not a directory: {workspace_root_path}'
    else:
        message = f'Workspace root is unavailable: {workspace_root_path}'

    workspace_status = WorkspaceRootStatus(
        path=workspace_root_path,
        available=available,
        exists=exists,
        writable=writable,
        created=created,
        message=message,
    )
    return WorkspaceResolution(
        selector_path=selector_path,
        selector_status=selector_status,
        workspace_root_path=workspace_root_path,
        workspace_status=workspace_status,
        resolution_mode=resolution_mode,
        source_description=source_description,
    )
