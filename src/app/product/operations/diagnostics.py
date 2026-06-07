from __future__ import annotations

import importlib.util
import sys
from typing import Any

from app.product.models import ProductOperationContext, ProductOperationSpec, ProductResult
from app.workspace import resolve_workspace_root, run_workspace_diagnostics


def _package_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def run(*, context: ProductOperationContext, params: dict[str, Any], spec: ProductOperationSpec) -> ProductResult:
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
    for item in workspace_report.items:
        level = 'OK' if item.ok else 'FAIL'
        context.logger.info('%s | %s | %s', level, item.title, item.details)
    for package_name, ok in package_checks.items():
        context.logger.info('Package %s: %s', package_name, 'OK' if ok else 'missing')

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
        ok = package_checks['stratbox'] and (workspace_available or degraded_preflight_allowed)
        if ok and degraded_preflight_allowed and not workspace_available:
            message = 'AppDock preflight finished in degraded mode'
        else:
            message = 'AppDock preflight finished' if ok else 'AppDock preflight finished with issues'
    else:
        ok = workspace_report.ok and package_checks['stratbox']
        message = 'Диагностика среды завершена' if ok else 'Диагностика среды завершена с замечаниями'

    return ProductResult(ok=ok, message=message, outputs=(str(context.operation_log_path),), details=details)
