"""Диагностика business-root selector и рабочего каталога."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.workspace.models import DataRootStatus, DiagnosticItem, DiagnosticReport, WorkspaceResolution, WorkspaceSchema


def resolve_data_root_status(data_root_path: Path | None) -> DataRootStatus:
    """Определяет текущее состояние business-root selector."""
    if data_root_path is None:
        return DataRootStatus(path=None, available=False, exists=False, message='Business root selector is not configured')
    path = Path(data_root_path)
    exists = path.exists()
    is_dir = path.is_dir()
    available = exists and is_dir
    if available:
        message = f'Business root selector available: {path}'
    elif exists and not is_dir:
        message = f'Business root selector is not a directory: {path}'
    else:
        message = f'Business root selector is unavailable: {path}'
    return DataRootStatus(path=path, available=available, exists=exists, message=message)


def run_workspace_diagnostics(
    schema: WorkspaceSchema,
    resolution: WorkspaceResolution,
    *,
    readonly: bool | None = None,
    create_missing: bool = False,
) -> DiagnosticReport:
    """Проверяет selector и resolved workspace root."""
    items: list[DiagnosticItem] = [
        DiagnosticItem(
            code='data_root_selector_available',
            title='Business root selector available',
            ok=resolution.selector_status.available,
            details=str(resolution.selector_path) if resolution.selector_path else resolution.selector_status.message,
            severity='info' if resolution.selector_status.available else 'error',
        )
    ]

    if resolution.selector_status.available:
        items.append(
            DiagnosticItem(
                code='workspace_resolution',
                title='Workspace root resolved',
                ok=resolution.workspace_root_path is not None,
                details=(f'{resolution.workspace_root_path} ({resolution.source_description})' if resolution.workspace_root_path else resolution.source_description),
                severity='info' if resolution.workspace_root_path is not None else 'error',
            )
        )

    if resolution.workspace_root_path is None or resolution.workspace_status.path is None:
        return DiagnosticReport(title=f'Workspace diagnostics: {schema.title}', items=tuple(items))

    root = resolution.workspace_status.path
    if not resolution.workspace_status.available:
        items.append(
            DiagnosticItem(
                code='workspace_root_available',
                title='Workspace root available',
                ok=False,
                details=resolution.workspace_status.message,
                severity='error',
            )
        )
        return DiagnosticReport(title=f'Workspace diagnostics: {schema.title}', items=tuple(items))

    if create_missing and schema.auto_create_required_dirs:
        for required_dir in schema.required_dirs:
            (root / required_dir).mkdir(parents=True, exist_ok=True)

    items.append(
        DiagnosticItem(
            code='workspace_root_available',
            title='Workspace root available',
            ok=True,
            details=f'{root} ({resolution.source_description})',
            severity='info',
        )
    )

    try:
        count = sum(1 for _ in root.iterdir())
        items.append(DiagnosticItem(code='read_access', title='Read access', ok=True, details=f'Items visible: {count}', severity='info'))
    except Exception as exc:
        items.append(DiagnosticItem(code='read_access', title='Read access', ok=False, details=str(exc), severity='error'))

    for required_dir in schema.required_dirs:
        p = root / required_dir
        exists = p.exists() and p.is_dir()
        items.append(
            DiagnosticItem(
                code=f'required_dir:{required_dir}',
                title=f'Required directory exists: {required_dir}',
                ok=exists,
                details=str(p),
                severity='info' if exists else 'warning',
            )
        )

    readonly_flag = schema.readonly if readonly is None else readonly
    if readonly_flag:
        items.append(DiagnosticItem(code='write_access', title='Write access', ok=True, details='Workspace is readonly; write test skipped', severity='info'))
    else:
        test_path = root / f'.stratbox_write_test_{uuid4().hex}.tmp'
        try:
            test_path.write_text('test', encoding='utf-8')
            test_path.unlink(missing_ok=True)
            items.append(DiagnosticItem(code='write_access', title='Write access', ok=True, details='Test file created and removed', severity='info'))
        except Exception as exc:
            try:
                test_path.unlink(missing_ok=True)
            except Exception:
                pass
            items.append(DiagnosticItem(code='write_access', title='Write access', ok=False, details=str(exc), severity='error'))

    return DiagnosticReport(title=f'Workspace diagnostics: {schema.title}', items=tuple(items))
