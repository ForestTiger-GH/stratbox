"""Задача проверки рабочей среды приложения."""

from __future__ import annotations

import importlib.util
import sys

from app.tasks.models import TaskContext, TaskResult, TaskSpec
from app.workspace import resolve_workspace_root, run_workspace_diagnostics


def _package_available(name: str) -> bool:
    """Проверяет доступность Python-пакета без его импорта."""
    return importlib.util.find_spec(name) is not None


def run(*, context: TaskContext, params: dict[str, object], spec: TaskSpec) -> TaskResult:
    """Выполняет диагностику business-root selector, workspace root и базовых зависимостей."""
    context.logger.info('Environment check started')
    mode = str(params.get('mode') or 'detailed')
    create_missing = mode == 'appdock_preflight'
    workspace_resolution = resolve_workspace_root(
        context.workspace_schema,
        context.data_root_selector_path,
        run_mode=context.run_mode,
        create_missing=create_missing,
    )
    workspace_report = run_workspace_diagnostics(
        context.workspace_schema,
        workspace_resolution,
        create_missing=create_missing,
    )

    package_checks = {
        'stratbox': _package_available('stratbox'),
        'pandas': _package_available('pandas'),
        'openpyxl': _package_available('openpyxl'),
        'requests': _package_available('requests'),
        'PySide6': _package_available('PySide6'),
    }

    for item in workspace_report.items:
        level = 'OK' if item.ok else 'FAIL'
        context.logger.info('%s | %s | %s', level, item.title, item.details)

    for package_name, ok in package_checks.items():
        context.logger.info('Package %s: %s', package_name, 'OK' if ok else 'missing')

    details = {
        'workspace_schema': context.workspace_schema.to_dict(),
        'data_root_selector_path': str(context.data_root_selector_path) if context.data_root_selector_path else None,
        'data_root_path': str(context.data_root_path) if context.data_root_path else None,
        'data_root_status': context.data_root_status.to_dict(),
        'workspace_root_path': str(workspace_resolution.workspace_root_path) if workspace_resolution.workspace_root_path else None,
        'workspace_status': workspace_resolution.workspace_status.to_dict(),
        'workspace_resolution': workspace_resolution.to_dict(),
        'workspace_diagnostics': workspace_report.to_dict(),
        'packages': package_checks,
        'python': sys.version,
        'version': context.version.to_dict(),
        'run_mode': context.run_mode,
        'node_id': context.node_id,
        'session_id': context.session_id,
        'user_id': context.user_id,
        'account_name': context.account_name,
        'host_name': context.host_name,
        'appdock_handoff': context.appdock_handoff.to_dict() if context.appdock_handoff else None,
        'session_state': context.session_state.to_dict() if context.session_state else None,
        'user_state': context.user_state.to_dict() if context.user_state else None,
        'active_session': context.active_session.to_dict() if context.active_session else None,
        'health_snapshot': context.health_snapshot.to_dict() if context.health_snapshot else None,
        'task_log': str(context.task_log_path),
    }

    if mode == 'appdock_preflight':
        ok = workspace_resolution.workspace_status.available and package_checks['stratbox']
        message = 'AppDock preflight finished' if ok else 'AppDock preflight finished with issues'
    else:
        ok = workspace_report.ok and package_checks['stratbox']
        message = 'Environment check finished' if ok else 'Environment check finished with issues'
    return TaskResult(ok=ok, message=message, outputs=(str(context.task_log_path),), details=details)
