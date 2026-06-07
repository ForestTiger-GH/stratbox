from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal

from app.runtime.context import AppContext
from app.application.product.catalog.models import ProductOperationSpec
from app.application.product.execution.requests import ProductResult
from app.application.product.execution.run_record import RunRecord
from app.presentation.desktop.workers import ProductWorker
from app.application.timeline.models import FeedAction, FeedEntry


@dataclass(slots=True)
class RunLifecycleResult:
    run_record: RunRecord
    timeline_entries: tuple[FeedEntry, ...]
    operation_result: ProductResult | None = None


class RunCoordinator(QObject):
    run_finished = Signal(object)

    def __init__(self, *, context: AppContext, on_log: Callable[[str], None]):
        super().__init__()
        self._context = context
        self._on_log = on_log
        self._active_run: RunRecord | None = None
        self._thread: QThread | None = None
        self._worker: ProductWorker | None = None
        self._active_spec: ProductOperationSpec | None = None

    @property
    def is_busy(self) -> bool:
        return self._active_run is not None

    def submit(self, spec: ProductOperationSpec, params: dict[str, object]) -> RunLifecycleResult:
        if self.is_busy:
            raise RuntimeError('An operation is already running')
        run = RunRecord.create(
            operation_id=spec.id,
            operation_title=spec.title,
            params=dict(params),
            author_id=self._context.user_id,
            author_label=self._context.account_name or 'Пользователь',
        )
        run.status = 'running'
        run.started_at = datetime.now()
        self._active_run = run
        self._active_spec = spec
        timeline_entries = (
            self._build_submitted_entry(run),
            self._build_started_entry(run),
        )
        self._start_worker(spec, dict(params))
        return RunLifecycleResult(run_record=run, timeline_entries=timeline_entries)

    def _start_worker(self, spec: ProductOperationSpec, params: dict[str, object]) -> None:
        self._thread = QThread()
        self._worker = ProductWorker(spec=spec, context=self._context, params=dict(params))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._handle_worker_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _handle_worker_finished(self, result: ProductResult) -> None:
        run = self._active_run
        if run is None:
            return
        run.finished_at = datetime.now()
        run.status = 'success' if result.ok else 'failed'
        run.outputs = result.outputs
        run.message = result.message
        timeline_entry = self._build_finished_entry(run, result)
        lifecycle = RunLifecycleResult(
            run_record=run,
            timeline_entries=(timeline_entry,),
            operation_result=result,
        )
        self._context.logger.info('Run finished: %s OK=%s', run.operation_id, result.ok)
        self._active_run = None
        self._active_spec = None
        self._worker = None
        self._thread = None
        self.run_finished.emit(lifecycle)

    def _build_submitted_entry(self, run: RunRecord) -> FeedEntry:
        return FeedEntry(
            entry_id=f'{run.run_id}:submitted',
            kind='run_submitted',
            status='info',
            title=run.operation_title,
            body=f'Параметры: {run.short_params_text()}',
            created_at=run.created_at,
            author_id=run.author_id,
            author_label=run.author_label,
            run_id=run.run_id,
            operation_id=run.operation_id,
            meta={'операция': run.operation_id},
        )

    def _build_started_entry(self, run: RunRecord) -> FeedEntry:
        return FeedEntry(
            entry_id=f'{run.run_id}:started',
            kind='run_started',
            status='running',
            title=f'{run.operation_title} выполняется',
            body='Операция принята в обработку.',
            created_at=run.started_at,
            author_id=run.author_id,
            author_label=run.author_label,
            run_id=run.run_id,
            operation_id=run.operation_id,
            meta={
                'режим': ('через host' if self._context.run_mode == 'appdock_managed' else 'локально'),
                'run_id': run.run_id[:8],
            },
        )

    def _build_finished_entry(self, run: RunRecord, result: ProductResult) -> FeedEntry:
        status = 'success' if result.ok else 'error'
        actions: list[FeedAction] = []
        primary_output = result.outputs[0] if result.outputs else None
        if primary_output:
            actions.append(FeedAction(id='open_primary', title='Открыть', payload=primary_output))
            actions.append(FeedAction(id='open_folder', title='Папка', payload=primary_output))
            actions.append(FeedAction(id='copy_path', title='Скопировать путь', payload=primary_output))
        actions.append(FeedAction(id='repeat_run', title='Повторить', payload=run.operation_id))
        return FeedEntry(
            entry_id=f'{run.run_id}:finished',
            kind='run_completed' if result.ok else 'run_failed',
            status=status,
            title=(f'{run.operation_title} завершена' if result.ok else f'{run.operation_title} завершена с ошибкой'),
            body=result.message,
            created_at=run.finished_at or datetime.now(),
            author_id=run.author_id,
            author_label=run.author_label,
            run_id=run.run_id,
            operation_id=run.operation_id,
            outputs=result.outputs,
            actions=tuple(actions),
            meta={
                'статус': ('успешно' if result.ok else 'ошибка'),
                'артефакты': str(len(result.outputs)),
            },
        )
