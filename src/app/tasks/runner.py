"""Единый механизм запуска задач приложения."""

from __future__ import annotations

import importlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.core.context import AppContext
from app.core.errors import AppTaskError
from app.tasks.models import TaskContext, TaskResult, TaskSpec
from app.tasks.registry import TaskRegistry


def _load_adapter(adapter: str) -> Callable[..., TaskResult]:
    """Загружает функцию adapter из строки вида 'module:function'."""
    if ':' not in adapter:
        raise AppTaskError(f"Adapter must use 'module:function' format: {adapter}")
    module_name, func_name = adapter.split(':', 1)
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)
    if not callable(func):
        raise AppTaskError(f'Adapter is not callable: {adapter}')
    return func


def _build_task_logger(task_id: str, logs_dir: Path) -> tuple[logging.Logger, Path]:
    """Создает отдельный логгер и файл лога для одного запуска задачи."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = logs_dir / f'{task_id}_{stamp}.log'
    logger = logging.getLogger(f'strategy_box_app.task.{task_id}.{stamp}')
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    handler = logging.FileHandler(log_path, encoding='utf-8')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger, log_path


def run_task(spec: TaskSpec, *, context: AppContext, params: dict[str, Any] | None = None) -> TaskResult:
    """Синхронно запускает задачу через ее adapter."""
    task_params = spec.default_params()
    task_params.update(params or {})

    task_logger, task_log_path = _build_task_logger(spec.id, context.paths.task_logs_dir)
    task_context = TaskContext(
        workspace_schema=context.workspace_schema,
        data_root_selector_path=context.data_root_selector_path,
        data_root_path=context.data_root_path,
        data_root_status=context.data_root_status,
        workspace_root_path=context.workspace_root_path,
        workspace_status=context.workspace_status,
        filestore=context.filestore,
        paths=context.paths,
        version=context.version,
        logger=task_logger,
        task_log_path=task_log_path,
        appdock_handoff=context.appdock_handoff,
        run_mode=context.run_mode,
        node_id=context.node_id,
        session_id=context.session_id,
        user_id=context.user_id,
        account_name=context.account_name,
        host_name=context.host_name,
        session_state=context.session_state,
        user_state=context.user_state,
        active_session=context.active_session,
        health_snapshot=context.health_snapshot,
    )

    task_logger.info('Task started: %s', spec.id)
    context.logger.info('Task started: %s', spec.id)

    if spec.requires_data_root and (not context.workspace_status.available or context.filestore is None):
        message = 'Task requires available workspace root'
        task_logger.error(message)
        context.logger.warning('Task blocked: %s', spec.id)
        return TaskResult(
            ok=False,
            message=message,
            outputs=(str(task_log_path),),
            details={
                'task_log': str(task_log_path),
                'data_root_status': context.data_root_status.to_dict(),
                'workspace_status': context.workspace_status.to_dict(),
                'requires_data_root': True,
                'session_id': context.session_id,
                'node_id': context.node_id,
            },
        )

    try:
        adapter = _load_adapter(spec.adapter)
        result = adapter(context=task_context, params=task_params, spec=spec)
        task_logger.info('Task finished: %s OK=%s', spec.id, result.ok)
        context.logger.info('Task finished: %s OK=%s', spec.id, result.ok)
        return result
    except Exception as exc:
        task_logger.exception('Task failed: %s', spec.id)
        context.logger.exception('Task failed: %s', spec.id)
        return TaskResult(
            ok=False,
            message=f'Task failed: {exc}',
            outputs=(str(task_log_path),),
            details={
                'error': str(exc),
                'task_log': str(task_log_path),
                'session_id': context.session_id,
                'node_id': context.node_id,
            },
        )
    finally:
        for handler in list(task_logger.handlers):
            handler.close()
            task_logger.removeHandler(handler)


def run_task_by_id(
    task_id: str,
    *,
    registry: TaskRegistry,
    context: AppContext,
    params: dict[str, Any] | None = None,
) -> TaskResult:
    """Запускает задачу по id."""
    return run_task(registry.get(task_id), context=context, params=params)
