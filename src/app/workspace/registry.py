
"""Загрузка рабочих схем из ресурсов приложения."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files

from app.core.errors import AppProfileError
from app.workspace.models import WorkspaceSchema


@dataclass(frozen=True, slots=True)
class WorkspaceRegistry:
    """Реестр доступных рабочих схем Strategy Box."""

    items: tuple[WorkspaceSchema, ...]

    def has(self, schema_id: str) -> bool:
        return any(item.id == schema_id for item in self.items)

    def get(self, schema_id: str) -> WorkspaceSchema:
        for item in self.items:
            if item.id == schema_id:
                return item
        raise AppProfileError(f"Unknown workspace schema: {schema_id}")


def load_workspace_registry() -> WorkspaceRegistry:
    """Читает встроенный реестр рабочих схем."""
    try:
        resource = files("app").joinpath("resources", "workspace", "default_workspaces.json")
        data = json.loads(resource.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AppProfileError("Failed to load workspace registry") from exc

    raw = data.get("workspaces") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        raise AppProfileError("Workspace registry must contain 'workspaces' list")
    items = tuple(WorkspaceSchema.from_dict(item) for item in raw)
    if not items:
        raise AppProfileError("Workspace registry is empty")
    return WorkspaceRegistry(items=items)
