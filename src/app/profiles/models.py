"""Модели профилей данных и диагностики."""

from __future__ import annotations

import getpass
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

ProfileKind = Literal["local"]
Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True, slots=True)
class DataProfile:
    """Описание одной файловой среды приложения."""

    id: str
    title: str
    kind: ProfileKind
    root: str
    required_dirs: tuple[str, ...] = ()
    description: str = ""
    readonly: bool = False

    @property
    def resolved_root(self) -> str:
        """Возвращает root с подстановкой базовых пользовательских переменных."""
        user = getpass.getuser()
        home = str(Path.home()).replace("\\", "/")
        value = self.root.format(user=user, home=home)
        value = os.path.expandvars(value)
        return str(Path(value).expanduser())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DataProfile":
        """Создает профиль из словаря JSON."""
        required_dirs = data.get("required_dirs") or []
        return cls(
            id=str(data["id"]),
            title=str(data.get("title") or data["id"]),
            kind=str(data.get("kind") or "local"),  # type: ignore[arg-type]
            root=str(data["root"]),
            required_dirs=tuple(str(x) for x in required_dirs),
            description=str(data.get("description") or ""),
            readonly=bool(data.get("readonly", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Преобразует профиль в словарь."""
        out = asdict(self)
        out["required_dirs"] = list(self.required_dirs)
        out["resolved_root"] = self.resolved_root
        return out


@dataclass(frozen=True, slots=True)
class DiagnosticItem:
    """Одна строка диагностики."""

    code: str
    title: str
    ok: bool
    details: str = ""
    severity: Severity = "error"

    def to_dict(self) -> dict[str, object]:
        """Преобразует строку диагностики в словарь."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    """Итог диагностики профиля или среды."""

    title: str
    items: tuple[DiagnosticItem, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        """Возвращает True, если нет критических ошибок."""
        return all(item.ok or item.severity != "error" for item in self.items)

    def to_dict(self) -> dict[str, object]:
        """Преобразует отчет в JSON-совместимый словарь."""
        return {
            "title": self.title,
            "ok": self.ok,
            "items": [item.to_dict() for item in self.items],
        }
