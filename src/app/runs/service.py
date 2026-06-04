from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal

from app.core.context import AppContext
from app.runs.models import RunRecord
from app.runs.workers import ScenarioWorker
from app.scenarios.models import ScenarioResult, ScenarioSpec
from app.timeline.models import FeedAction, FeedEntry


@dataclass(slots=True)
class RunLifecycleResult:
    run_record: RunRecord
    timeline_entries: tuple[FeedEntry, ...]
    scenario_result: ScenarioResult | None = None


class RunCoordinator(QObject):
    run_finished = Signal(object)

    def __init__(self, *, context: AppContext, on_log: Callable[[str], None]) -> None:
        super().__init__()
        self._context = context
        self._on_log = on_log
        self._thread: QThread | None = None
        self._worker: ScenarioWorker | None = None
        self._active_run: RunRecord | None = None
        self._active_spec: ScenarioSpec | None = None

    @property
    def is_busy(self) -> bool:
        return self._thread is not None

    def submit(self, spec: ScenarioSpec, params: dict[str, object]) -> RunLifecycleResult:
        if self.is_busy:
            raise RuntimeError('A scenario is already running')
        author_label = self._context.account_name or self._context.user_id or 'Пользователь'
        run = RunRecord.create(
            scenario_id=spec.id,
            scenario_title=spec.title,
            params=dict(params),
            author_id=self._context.user_id,
            author_label=author_label,
        )
        self._active_run = run
        self._active_spec = spec
        self._context.logger.info('Run submitted: %s (%s)', spec.id, run.run_id)
        self._on_log(f'Run submitted: {spec.title}')
        submitted = self._build_submitted_entry(run)
        self._start_worker(spec, params)
        started = self._build_started_entry(run)
        return RunLifecycleResult(run_record=run, timeline_entries=(submitted, started))

    def _start_worker(self, spec: ScenarioSpec, params: dict[str, object]) -> None:
        self._thread = QThread()
        self._worker = ScenarioWorker(spec=spec, context=self._context, params=dict(params))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._handle_worker_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _handle_worker_finished(self, result: ScenarioResult) -> None:
        if self._active_run is None or self._active_spec is None:
            return
        run = self._active_run
        run.outputs = result.outputs
        run.message = result.message
        run.finished_at = datetime.now()
        run.status = 'success' if result.ok else 'failed'
        lifecycle = RunLifecycleResult(
            run_record=run,
            scenario_result=result,
            timeline_entries=(self._build_finished_entry(run, result),),
        )
        self._context.logger.info('Run finished: %s OK=%s', run.scenario_id, result.ok)
        self._on_log(result.message)
        self._thread = None
        self._worker = None
        self._active_run = None
        self._active_spec = None
        self.run_finished.emit(lifecycle)

    def _build_submitted_entry(self, run: RunRecord) -> FeedEntry:
        body = f'Запуск подготовлен: {run.short_params_text()}'
        return FeedEntry(
            entry_id=f'{run.run_id}:submitted',
            kind='run_submitted',
            status='info',
            title=run.scenario_title,
            body=body,
            created_at=run.created_at,
            author_id=run.author_id,
            author_label=run.author_label,
            run_id=run.run_id,
            scenario_id=run.scenario_id,
            meta={'статус': 'отправлено'},
        )

    def _build_started_entry(self, run: RunRecord) -> FeedEntry:
        run.status = 'running'
        run.started_at = datetime.now()
        return FeedEntry(
            entry_id=f'{run.run_id}:started',
            kind='run_started',
            status='running',
            title=f'{run.scenario_title} выполняется',
            body='Сценарий принят в обработку.',
            created_at=run.started_at,
            author_id=run.author_id,
            author_label=run.author_label,
            run_id=run.run_id,
            scenario_id=run.scenario_id,
            meta={
                'режим': ('через host' if self._context.run_mode == 'appdock_managed' else 'локально'),
                'run_id': run.run_id[:8],
            },
        )

    def _build_finished_entry(self, run: RunRecord, result: ScenarioResult) -> FeedEntry:
        status = 'success' if result.ok else 'error'
        actions: list[FeedAction] = []
        primary_output = result.outputs[0] if result.outputs else None
        if primary_output:
            actions.append(FeedAction(id='open_primary', title='Открыть', payload=primary_output))
            actions.append(FeedAction(id='open_folder', title='Папка', payload=primary_output))
            actions.append(FeedAction(id='copy_path', title='Скопировать путь', payload=primary_output))
        actions.append(FeedAction(id='repeat_run', title='Повторить', payload=run.scenario_id))
        return FeedEntry(
            entry_id=f'{run.run_id}:finished',
            kind='run_completed' if result.ok else 'run_failed',
            status=status,
            title=(f'{run.scenario_title} завершён' if result.ok else f'{run.scenario_title} завершён с ошибкой'),
            body=result.message,
            created_at=run.finished_at or datetime.now(),
            author_id=run.author_id,
            author_label=run.author_label,
            run_id=run.run_id,
            scenario_id=run.scenario_id,
            outputs=result.outputs,
            actions=tuple(actions),
            meta={
                'статус': ('успешно' if result.ok else 'ошибка'),
                'артефакты': str(len(result.outputs)),
            },
        )
