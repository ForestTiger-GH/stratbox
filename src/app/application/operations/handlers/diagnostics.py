from __future__ import annotations

import importlib
import importlib.util
import sys
from typing import Any

from app.application.operations.catalog.models import OperationSpec
from app.application.operations.execution.requests import OperationContext, OperationResult
from app.application.workspace import resolve_workspace_root, run_workspace_diagnostics


def _package_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _module_import_status(name: str) -> dict[str, str | bool]:
    try:
        importlib.import_module(name)
    except Exception as exc:
        return {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
    return {'ok': True, 'error': ''}


def run(*, context: OperationContext, params: dict[str, Any], spec: OperationSpec) -> OperationResult:
    mode = str(params.get('mode') or 'full')
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
    internal_import_checks = {
        'app.runtime.bootstrap': _module_import_status('app.runtime.bootstrap'),
        'app.presentation.desktop.main': _module_import_status('app.presentation.desktop.main'),
        'app.application.scenarios.runner': _module_import_status('app.application.scenarios.runner'),
    }
    if package_checks['PySide6']:
        internal_import_checks['app.presentation.desktop.shell.main_window'] = _module_import_status('app.presentation.desktop.shell.main_window')
    for item in workspace_report.items:
        level = 'OK' if item.ok else 'FAIL'
        context.logger.info('%s | %s | %s', level, item.title, item.details)
    for package_name, ok in package_checks.items():
        context.logger.info('Package %s: %s', package_name, 'OK' if ok else 'missing')
    for module_name, check in internal_import_checks.items():
        context.logger.info(
            'Internal import %s: %s%s',
            module_name,
            'OK' if check['ok'] else 'FAIL',
            f" | {check['error']}" if check['error'] else '',
        )

    degraded_launch = (
        (context.appdock_activation.degraded_launch if context.appdock_activation is not None else False)
        or (context.session_state.degraded_launch if context.session_state is not None and context.session_state.degraded_launch is not None else False)
        or (not context.data_root_status.available)
    )

    degraded_preflight_allowed = (
        mode == 'appdock_preflight'
        and context.run_mode == 'appdock_managed'
        and degraded_launch
        and not context.data_root_status.available
    )

    details = {
        'workspace_schema': context.workspace_schema.to_dict(),
        'data_root_selector_path': str(context.data_root_selector_path) if context.data_root_selector_path else None,
        'data_root_status': context.data_root_status.to_dict(),
        'workspace_root_path': str(workspace_resolution.workspace_root_path) if workspace_resolution.workspace_root_path else None,
        'workspace_status': workspace_resolution.workspace_status.to_dict(),
        'workspace_resolution': workspace_resolution.to_dict(),
        'workspace_diagnostics': workspace_report.to_dict(),
        'packages': package_checks,
        'internal_imports': internal_import_checks,
        'python': sys.version,
        'version': context.version.to_dict(),
        'run_mode': context.run_mode,
        'launch_origin': context.launch_origin,
        'node_id': context.node_id,
        'session_id': context.session_id,
        'user_id': context.user_id,
        'account_name': context.account_name,
        'host_name': context.host_name,
        'appdock_activation': context.appdock_activation.to_dict() if context.appdock_activation else None,
        'session_state': context.session_state.to_dict() if context.session_state else None,
        'user_state': context.user_state.to_dict() if context.user_state else None,
        'active_session': context.active_session.to_dict() if context.active_session else None,
        'health_snapshot': context.health_snapshot.to_dict() if context.health_snapshot else None,
        'operation_log': str(context.operation_log_path),
        'degraded_preflight_allowed': degraded_preflight_allowed,
    }

    if mode == 'appdock_preflight':
        workspace_available = workspace_resolution.workspace_status.available
        required_packages_ok = package_checks['stratbox'] and package_checks['PySide6']
        internal_imports_ok = all(bool(item['ok']) for item in internal_import_checks.values())
        ok = required_packages_ok and internal_imports_ok and (workspace_available or degraded_preflight_allowed)
        if ok and degraded_preflight_allowed and not workspace_available:
            message = 'AppDock preflight finished in degraded mode'
        elif ok:
            message = 'AppDock preflight finished'
        elif not package_checks['PySide6']:
            message = 'AppDock preflight failed: PySide6 is required for the desktop surface'
        elif not internal_imports_ok:
            broken = ', '.join(name for name, item in internal_import_checks.items() if not item['ok'])
            message = f'AppDock preflight failed: internal imports are broken: {broken}'
        else:
            message = 'AppDock preflight finished with issues'
    else:
        ok = workspace_report.ok and package_checks['stratbox']
        message = 'Диагностика среды завершена' if ok else 'Диагностика среды завершена с замечаниями'

    return OperationResult(ok=ok, message=message, outputs=(str(context.operation_log_path),), details=details)
