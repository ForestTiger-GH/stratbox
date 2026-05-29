
"""Модели рабочей схемы и диагностики business-root."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True, slots=True)
class WorkspaceSchema:
    """Описание рабочей схемы поверх уже выбранного business-root."""

    id: str
    title: str
    required_dirs: tuple[str, ...] = ()
    description: str = ""
    readonly: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkspaceSchema":
        required_dirs = data.get("required_dirs") or []
        return cls(
            id=str(data["id"]),
            title=str(data.get("title") or data["id"]),
            required_dirs=tuple(str(x) for x in required_dirs),
            description=str(data.get("description") or ""),
            readonly=bool(data.get("readonly", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["required_dirs"] = list(self.required_dirs)
        return out


@dataclass(frozen=True, slots=True)
class DataRootStatus:
    """Состояние business-root в текущей сессии."""

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
