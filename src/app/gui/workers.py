"""Фоновые рабочие объекты GUI."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from app.core.context import AppContext
from app.tasks.models import TaskResult, TaskSpec
from app.tasks.runner import run_task


class TaskWorker(QObject):
    """Выполняет задачу в отдельном Qt-потоке."""

    finished = Signal(object)

    def __init__(self, *, spec: TaskSpec, context: AppContext, params: dict[str, Any]):
        super().__init__()
        self._spec = spec
        self._context = context
        self._params = params

    @Slot()
    def run(self) -> None:
        """Запускает задачу и отправляет результат в GUI-поток."""
        result: TaskResult = run_task(self._spec, context=self._context, params=self._params)
        self.finished.emit(result)
