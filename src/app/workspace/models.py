"""Модели рабочей схемы и диагностики business-root."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

Severity = Literal["info", "warning", "error"]
WorkspaceRootMode = Literal["derived_from_selector", "explicit_workspace_root"]


@dataclass(frozen=True, slots=True)
class WorkspaceSchema:
    """Описание рабочей схемы поверх выбранного business-root."""

    id: str
    title: str
    required_dirs: tuple[str, ...] = ()
    description: str = ""
    readonly: bool = False
    root_mode: WorkspaceRootMode = "derived_from_selector"
    workspace_dirname: str = "Strategy Box Data"
    use_user_profile_for_system_drive: bool = True
    auto_create_workspace_root: bool = True
    auto_create_required_dirs: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkspaceSchema":
        required_dirs = data.get("required_dirs") or []
        return cls(
            id=str(data["id"]),
            title=str(data.get("title") or data["id"]),
            required_dirs=tuple(str(x) for x in required_dirs),
            description=str(data.get("description") or ""),
            readonly=bool(data.get("readonly", False)),
            root_mode=str(data.get("root_mode") or "derived_from_selector"),  # type: ignore[arg-type]
            workspace_dirname=str(data.get("workspace_dirname") or "Strategy Box Data"),
            use_user_profile_for_system_drive=bool(data.get("use_user_profile_for_system_drive", True)),
            auto_create_workspace_root=bool(data.get("auto_create_workspace_root", True)),
            auto_create_required_dirs=bool(data.get("auto_create_required_dirs", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["required_dirs"] = list(self.required_dirs)
        return out


@dataclass(frozen=True, slots=True)
class DataRootStatus:
    """Состояние business-root selector в текущей сессии."""

    path: Path | None
    available: bool
    exists: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path) if self.path else None,
            "available": self.available,
            "exists": self.exists,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceRootStatus:
    """Состояние реального рабочего каталога приложения."""

    path: Path | None
    available: bool
    exists: bool
    writable: bool | None
    created: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path) if self.path else None,
            "available": self.available,
            "exists": self.exists,
            "writable": self.writable,
            "created": self.created,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceResolution:
    """Результат разрешения рабочего каталога поверх business-root selector."""

    selector_path: Path | None
    selector_status: DataRootStatus
    workspace_root_path: Path | None
    workspace_status: WorkspaceRootStatus
    resolution_mode: str
    source_description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "selector_path": str(self.selector_path) if self.selector_path else None,
            "selector_status": self.selector_status.to_dict(),
            "workspace_root_path": str(self.workspace_root_path) if self.workspace_root_path else None,
            "workspace_status": self.workspace_status.to_dict(),
            "resolution_mode": self.resolution_mode,
            "source_description": self.source_description,
        }


@dataclass(frozen=True, slots=True)
class DiagnosticItem:
    """Одна строка диагностики среды."""

    code: str
    title: str
    ok: bool
    details: str = ""
    severity: Severity = "error"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    """Итог диагностики рабочей среды."""

    title: str
    items: tuple[DiagnosticItem, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return all(item.ok or item.severity != "error" for item in self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "ok": self.ok,
            "items": [item.to_dict() for item in self.items],
        }
