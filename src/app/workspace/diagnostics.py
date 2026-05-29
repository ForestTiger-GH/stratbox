
"""Диагностика business-root и рабочей схемы."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.workspace.models import DataRootStatus, DiagnosticItem, DiagnosticReport, WorkspaceSchema


def resolve_data_root_status(data_root_path: Path | None) -> DataRootStatus:
    """Определяет текущее состояние business-root."""
    if data_root_path is None:
        return DataRootStatus(path=None, available=False, exists=False, message="Business root is not configured")
    path = Path(data_root_path)
    exists = path.exists()
    is_dir = path.is_dir()
    available = exists and is_dir
    if available:
        message = f"Business root available: {path}"
    elif exists and not is_dir:
        message = f"Business root is not a directory: {path}"
    else:
        message = f"Business root is unavailable: {path}"
    return DataRootStatus(path=path, available=available, exists=exists, message=message)


def run_workspace_diagnostics(schema: WorkspaceSchema, data_root_path: Path | None, *, readonly: bool | None = None) -> DiagnosticReport:
    """Проверяет business-root и ожидаемую рабочую схему."""
    status = resolve_data_root_status(data_root_path)
    items: list[DiagnosticItem] = [
        DiagnosticItem(
            code="data_root_available",
            title="Business root available",
            ok=status.available,
            details=str(status.path) if status.path else status.message,
            severity="error",
        )
    ]

    if not status.available or status.path is None:
        for required_dir in schema.required_dirs:
            items.append(
                DiagnosticItem(
                    code=f"required_dir:{required_dir}",
                    title=f"Required directory exists: {required_dir}",
                    ok=False,
                    details="Business root is unavailable",
                    severity="warning",
                )
            )
        return DiagnosticReport(title=f"Workspace diagnostics: {schema.title}", items=tuple(items))

    root = status.path
    try:
        count = sum(1 for _ in root.iterdir())
        items.append(
            DiagnosticItem(
                code="read_access",
                title="Read access",
                ok=True,
                details=f"Items visible: {count}",
                severity="error",
            )
        )
    except Exception as exc:
        items.append(
            DiagnosticItem(
                code="read_access",
                title="Read access",
                ok=False,
                details=str(exc),
                severity="error",
            )
        )

    for required_dir in schema.required_dirs:
        p = root / required_dir
        items.append(
            DiagnosticItem(
                code=f"required_dir:{required_dir}",
                title=f"Required directory exists: {required_dir}",
                ok=p.exists() and p.is_dir(),
                details=str(p),
                severity="warning",
            )
        )

    readonly_flag = schema.readonly if readonly is None else readonly
    if readonly_flag:
        items.append(
            DiagnosticItem(
                code="write_access",
                title="Write access",
                ok=True,
                details="Workspace is readonly; write test skipped",
                severity="info",
            )
        )
    else:
        test_path = root / f".stratbox_write_test_{uuid4().hex}.tmp"
        try:
            test_path.write_text("test", encoding="utf-8")
            test_path.unlink(missing_ok=True)
            items.append(
                DiagnosticItem(
                    code="write_access",
                    title="Write access",
                    ok=True,
                    details="Test file created and removed",
                    severity="error",
                )
            )
        except Exception as exc:
            try:
                test_path.unlink(missing_ok=True)
            except Exception:
                pass
            items.append(
                DiagnosticItem(
                    code="write_access",
                    title="Write access",
                    ok=False,
                    details=str(exc),
                    severity="error",
                )
            )

    return DiagnosticReport(title=f"Workspace diagnostics: {schema.title}", items=tuple(items))
