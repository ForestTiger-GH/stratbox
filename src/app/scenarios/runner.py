"""Единый механизм запуска сценариев приложения."""

from __future__ import annotations

import importlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.core.context import AppContext
from app.core.errors import AppScenarioError
from app.scenarios.models import ScenarioContext, ScenarioResult, ScenarioSpec
from app.scenarios.registry import ScenarioRegistry


def _load_adapter(adapter: str) -> Callable[..., ScenarioResult]:
    if ':' not in adapter:
        raise AppScenarioError(f"Adapter must use 'module:function' format: {adapter}")
    module_name, func_name = adapter.split(':', 1)
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)
    if not callable(func):
        raise AppScenarioError(f'Adapter is not callable: {adapter}')
    return func


def _build_scenario_logger(scenario_id: str, logs_dir: Path) -> tuple[logging.Logger, Path]:
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = logs_dir / f'{scenario_id}_{stamp}.log'
    logger = logging.getLogger(f'strategy_box_app.scenario.{scenario_id}.{stamp}')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    handler = logging.FileHandler(log_path, encoding='utf-8')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger, log_path


def run_scenario(spec: ScenarioSpec, *, context: AppContext, params: dict[str, Any] | None = None) -> ScenarioResult:
    scenario_params = spec.default_params()
    scenario_params.update(params or {})
    scenario_logger, scenario_log_path = _build_scenario_logger(spec.id, context.paths.scenario_logs_dir)
    scenario_context = ScenarioContext(
        workspace_schema=context.workspace_schema,
        data_root_selector_path=context.data_root_selector_path,
        data_root_status=context.data_root_status,
        workspace_root_path=context.workspace_root_path,
        workspace_status=context.workspace_status,
        filestore=context.filestore,
        paths=context.paths,
        version=context.version,
        logger=scenario_logger,
        scenario_log_path=scenario_log_path,
        appdock_handoff=context.appdock_handoff,
        run_mode=context.run_mode,
        launch_origin=context.launch_origin,
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

    scenario_logger.info('Scenario started: %s', spec.id)
    context.logger.info('Scenario started: %s', spec.id)

    if spec.requires_workspace and (not context.workspace_status.available or context.filestore is None):
        message = 'Scenario requires available workspace root'
        scenario_logger.error(message)
        context.logger.warning('Scenario blocked: %s', spec.id)
        return ScenarioResult(
            ok=False,
            message=message,
            outputs=(str(scenario_log_path),),
            details={
                'scenario_log': str(scenario_log_path),
                'data_root_status': context.data_root_status.to_dict(),
                'workspace_status': context.workspace_status.to_dict(),
                'requires_workspace': True,
                'session_id': context.session_id,
                'node_id': context.node_id,
            },
        )

    try:
        adapter = _load_adapter(spec.adapter)
        result = adapter(context=scenario_context, params=scenario_params, spec=spec)
        scenario_logger.info('Scenario finished: %s OK=%s', spec.id, result.ok)
        context.logger.info('Scenario finished: %s OK=%s', spec.id, result.ok)
        return result
    except Exception as exc:
        scenario_logger.exception('Scenario failed: %s', spec.id)
        context.logger.exception('Scenario failed: %s', spec.id)
        return ScenarioResult(
            ok=False,
            message=f'Scenario failed: {exc}',
            outputs=(str(scenario_log_path),),
            details={
                'error': str(exc),
                'scenario_log': str(scenario_log_path),
                'session_id': context.session_id,
                'node_id': context.node_id,
            },
        )
    finally:
        for handler in list(scenario_logger.handlers):
            handler.close()
            scenario_logger.removeHandler(handler)


def run_scenario_by_id(
    scenario_id: str,
    *,
    registry: ScenarioRegistry,
    context: AppContext,
    params: dict[str, Any] | None = None,
) -> ScenarioResult:
    return run_scenario(registry.get(scenario_id), context=context, params=params)
