"""Фоновые рабочие объекты GUI."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from app.core.context import AppContext
from app.scenarios.models import ScenarioResult, ScenarioSpec
from app.scenarios.runner import run_scenario


class ScenarioWorker(QObject):
    """Выполняет сценарий в отдельном Qt-потоке."""

    finished = Signal(object)

    def __init__(self, *, spec: ScenarioSpec, context: AppContext, params: dict[str, Any]):
        super().__init__()
        self._spec = spec
        self._context = context
        self._params = params

    @Slot()
    def run(self) -> None:
        result: ScenarioResult = run_scenario(self._spec, context=self._context, params=self._params)
        self.finished.emit(result)
