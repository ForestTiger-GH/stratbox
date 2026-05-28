"""Загрузка задач приложения из JSON-ресурсов."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files

from app.core.errors import AppTaskError
from app.tasks.models import TaskSpec


@dataclass(frozen=True, slots=True)
class TaskRegistry:
    """Реестр задач приложения."""

    items: tuple[TaskSpec, ...]

    def enabled(self) -> tuple[TaskSpec, ...]:
        """Возвращает включенные задачи."""
        return tuple(item for item in self.items if item.enabled)

    def has(self, task_id: str) -> bool:
        """Проверяет наличие задачи."""
        return any(item.id == task_id for item in self.items)

    def get(self, task_id: str) -> TaskSpec:
        """Возвращает задачу по id."""
        for item in self.items:
            if item.id == task_id:
                return item
        raise AppTaskError(f"Unknown task: {task_id}")


def load_task_registry() -> TaskRegistry:
    """Читает все JSON-конфиги задач из ресурсов приложения."""
    try:
        root = files("app").joinpath("resources", "tasks")
        task_files = sorted(path for path in root.iterdir() if path.name.endswith(".json"))
        tasks = []
        for path in task_files:
            data = json.loads(path.read_text(encoding="utf-8"))
            tasks.append(TaskSpec.from_dict(data))
    except Exception as exc:
        raise AppTaskError("Failed to load task registry") from exc

    if not tasks:
        raise AppTaskError("Task registry is empty")
    return TaskRegistry(items=tuple(tasks))
