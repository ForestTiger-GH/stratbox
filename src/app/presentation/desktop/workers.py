from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from app.application.artifacts.models import ArtifactRecord
from app.application.artifacts.store import ArtifactStore
from app.application.cases.models import ScenarioRunCase
from app.application.events.models import OperationalEvent
from app.application.events.store import OperationalEventStore
from app.application.logs.models import LogRecord
from app.application.logs.store import LogStore
from app.application.operations.catalog.models import OperationRegistry
from app.application.scenarios.models import ScenarioSpec
from app.application.scenarios.runner import run_scenario
from app.runtime.context import AppContext


class ScenarioWorker(QObject):
    case_updated = Signal(object)
    event_appended = Signal(object)
    artifacts_created = Signal(object)
    log_created = Signal(object)
    finished = Signal(object)

    def __init__(
        self,
        *,
        scenario: ScenarioSpec,
        operation_registry: OperationRegistry,
        context: AppContext,
        params: dict[str, Any],
        case: ScenarioRunCase,
    ) -> None:
        super().__init__()
        self._scenario = scenario
        self._operation_registry = operation_registry
        self._context = context
        self._params = dict(params)
        self._case = case

    @Slot()
    def run(self) -> None:
        try:
            final_case = run_scenario(
                scenario=self._scenario,
                operation_registry=self._operation_registry,
                context=self._context,
                params=self._params,
                case=self._case,
                on_case_updated=self.case_updated.emit,
                on_event=self.event_appended.emit,
                on_artifacts=self.artifacts_created.emit,
                on_log=self.log_created.emit,
            )
        except Exception as exc:  # pragma: no cover - defensive boundary
            self._context.logger.exception('Unhandled scenario worker failure: %s', self._scenario.id)
            self._case.status = 'failed'
            self._case.message = f'Unhandled scenario failure: {exc}'
            final_case = self._case
        self.finished.emit(final_case)
