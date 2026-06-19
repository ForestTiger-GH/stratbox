from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from app.application.artifacts.models import ArtifactRecord
from app.application.artifacts.store import ArtifactStore
from app.application.cases.models import ScenarioRunCase
from app.application.cases.store import ScenarioCaseStore
from app.application.events.models import OperationalEvent
from app.application.events.store import OperationalEventStore
from app.application.logs.models import LogRecord
from app.application.logs.store import LogStore
from app.application.operations.catalog.models import OperationRegistry
from app.application.scenarios.models import ScenarioSpec
from app.application.scenarios.runner import build_case_for_scenario
from app.presentation.desktop.workers import ScenarioWorker
from app.runtime.context import AppContext


class ScenarioCoordinator(QObject):
    case_created = Signal(object)
    case_updated = Signal(object)
    event_appended = Signal(object)
    artifacts_created = Signal(object)
    log_created = Signal(object)
    run_finished = Signal(object)

    def __init__(
        self,
        *,
        context: AppContext,
        operation_registry: OperationRegistry,
        case_store: ScenarioCaseStore,
        event_store: OperationalEventStore,
        artifact_store: ArtifactStore,
        log_store: LogStore,
    ) -> None:
        super().__init__()
        self._context = context
        self._operation_registry = operation_registry
        self._case_store = case_store
        self._event_store = event_store
        self._artifact_store = artifact_store
        self._log_store = log_store
        self._thread: QThread | None = None
        self._worker: ScenarioWorker | None = None
        self._active_case: ScenarioRunCase | None = None

    @property
    def is_busy(self) -> bool:
        return self._thread is not None or self._active_case is not None

    @property
    def active_case_id(self) -> str | None:
        return self._active_case.case_id if self._active_case is not None else None

    def submit(self, scenario: ScenarioSpec, params: dict[str, Any]) -> ScenarioRunCase:
        if self.is_busy:
            raise RuntimeError('A scenario is already running')
        case = build_case_for_scenario(scenario=scenario, context=self._context, params=dict(params))
        self._active_case = case
        self._case_store.upsert(case)
        self.case_created.emit(case)
        self._start_worker(scenario, dict(params), case)
        return case

    def _start_worker(self, scenario: ScenarioSpec, params: dict[str, Any], case: ScenarioRunCase) -> None:
        thread = QThread()
        worker = ScenarioWorker(
            scenario=scenario,
            operation_registry=self._operation_registry,
            context=self._context,
            params=params,
            case=case,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.case_updated.connect(self._handle_case_updated)
        worker.event_appended.connect(self._handle_event)
        worker.artifacts_created.connect(self._handle_artifacts)
        worker.log_created.connect(self._handle_log)
        worker.finished.connect(self._handle_worker_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda *, _thread=thread, _worker=worker: self._handle_thread_finished(_thread, _worker))
        self._thread = thread
        self._worker = worker
        thread.start()

    def _handle_case_updated(self, case: ScenarioRunCase) -> None:
        self._case_store.upsert(case)
        self.case_updated.emit(case)

    def _handle_event(self, event: OperationalEvent) -> None:
        self._event_store.add(event)
        self.event_appended.emit(event)

    def _handle_artifacts(self, artifacts: list[ArtifactRecord]) -> None:
        self._artifact_store.extend(artifacts)
        self.artifacts_created.emit(tuple(artifacts))

    def _handle_log(self, log: LogRecord) -> None:
        self._log_store.add(log)
        self.log_created.emit(log)

    def _handle_worker_finished(self, case: ScenarioRunCase) -> None:
        self._case_store.upsert(case)
        self._context.logger.info('Scenario case finished: %s status=%s', case.case_id, case.status)
        self._active_case = None
        self.run_finished.emit(case)

    def _handle_thread_finished(self, thread: QThread, worker: ScenarioWorker) -> None:
        if self._worker is worker:
            self._worker = None
        if self._thread is thread:
            self._thread = None
