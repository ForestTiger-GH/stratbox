"""Диагностика профиля файловой среды."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.profiles.models import DataProfile, DiagnosticItem, DiagnosticReport


def run_profile_diagnostics(profile: DataProfile) -> DiagnosticReport:
    """Проверяет доступность корня, чтение, запись и обязательные каталоги."""
    root = Path(profile.resolved_root)
    items: list[DiagnosticItem] = []

    exists = root.exists()
    is_dir = root.is_dir()
    items.append(
        DiagnosticItem(
            code="root_exists",
            title="Profile root exists",
            ok=exists,
            details=str(root),
            severity="error",
        )
    )
    items.append(
        DiagnosticItem(
            code="root_is_dir",
            title="Profile root is directory",
            ok=is_dir,
            details=str(root),
            severity="error",
        )
    )

    if not exists or not is_dir:
        for required_dir in profile.required_dirs:
            items.append(
                DiagnosticItem(
                    code=f"required_dir:{required_dir}",
                    title=f"Required directory exists: {required_dir}",
                    ok=False,
                    details="Root is not available",
                    severity="warning",
                )
            )
        return DiagnosticReport(title=f"Profile diagnostics: {profile.title}", items=tuple(items))

    try:
        names = [x.name for x in root.iterdir()]
        items.append(
            DiagnosticItem(
                code="read_access",
                title="Read access",
                ok=True,
                details=f"Items visible: {len(names)}",
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

    for required_dir in profile.required_dirs:
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

    if profile.readonly:
        items.append(
            DiagnosticItem(
                code="write_access",
                title="Write access",
                ok=True,
                details="Profile is readonly; write test skipped",
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

    return DiagnosticReport(title=f"Profile diagnostics: {profile.title}", items=tuple(items))
