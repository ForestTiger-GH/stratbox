from __future__ import annotations

import importlib
import logging
from logging import Logger
from pathlib import Path
from typing import Any, Callable

from app.core.context import AppContext
from app.product.catalog.models import ProductOperationSpec, ProductRegistry
from app.product.execution.requests import ProductOperationContext, ProductResult
from app.state.session_runtime import (
    ActiveSessionProjectionRecord,
    NodeHealthSnapshotRecord,
    SessionStateRecord,
    UserStateRecord,
)


def _load_handler(handler_ref: str) -> Callable[..., ProductResult]:
    module_name, _, attr_name = handler_ref.partition(':')
    if not module_name or not attr_name:
        raise ValueError(f'Invalid handler ref: {handler_ref}')
    module = importlib.import_module(module_name)
    handler = getattr(module, attr_name)
    if not callable(handler):
        raise TypeError(f'Handler is not callable: {handler_ref}')
    return handler


def _build_operation_logger(operation_id: str, operation_logs_dir: Path) -> tuple[Logger, Path]:
    operation_logs_dir.mkdir(parents=True, exist_ok=True)
    safe_name = operation_id.replace('/', '_').replace(':', '_').replace('.', '_')
    log_path = operation_logs_dir / f'{safe_name}.log'
    logger = logging.getLogger(f'app.operation.{safe_name}')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    logger.addHandler(file_handler)
    return logger, log_path


def _build_operation_context(context: AppContext, *, logger: logging.Logger, operation_log_path: Path) -> ProductOperationContext:
    return ProductOperationContext(
        workspace_schema=context.workspace_schema,
        data_root_selector_path=context.data_root_selector_path,
        data_root_status=context.data_root_status,
        workspace_root_path=context.workspace_root_path,
        workspace_status=context.workspace_status,
        filestore=context.filestore,
        paths=context.paths,
        version=context.version,
        logger=logger,
        operation_log_path=operation_log_path,
        appdock_activation=context.appdock_activation,
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


def run_product_operation(spec: ProductOperationSpec, *, context: AppContext, params: dict[str, Any] | None = None) -> ProductResult:
    operation_params = spec.default_params()
    operation_params.update(params or {})
    operation_logger, operation_log_path = _build_operation_logger(spec.id, context.paths.operation_logs_dir)
    operation_context = _build_operation_context(context, logger=operation_logger, operation_log_path=operation_log_path)
    operation_logger.info('Operation started: %s', spec.id)
    context.logger.info('Operation started: %s', spec.id)

    if spec.requires_workspace and (context.workspace_root_path is None or context.filestore is None or not context.workspace_status.available):
        message = 'Операция требует доступный workspace root.'
        operation_logger.error(message)
        return ProductResult(
            ok=False,
            message=message,
            outputs=(str(operation_log_path),),
            details={
                'operation_log': str(operation_log_path),
                'workspace_root_path': str(context.workspace_root_path) if context.workspace_root_path else None,
                'workspace_status': context.workspace_status.to_dict(),
            },
        )

    try:
        handler = _load_handler(spec.handler)
        result = handler(context=operation_context, params=operation_params, spec=spec)
        from app.product.execution.result_mapper import finalize_product_result

        finalized = finalize_product_result(result)
        operation_logger.info('Operation finished: %s OK=%s', spec.id, finalized.ok)
        context.logger.info('Operation finished: %s OK=%s', spec.id, finalized.ok)
        return finalized
    except Exception as exc:
        operation_logger.exception('Operation failed: %s', spec.id)
        context.logger.exception('Operation failed: %s', spec.id)
        return ProductResult(
            ok=False,
            message=f'Operation failed: {exc}',
            outputs=(str(operation_log_path),),
            details={'error': str(exc), 'operation_log': str(operation_log_path)},
        )
    finally:
        for handler in list(operation_logger.handlers):
            handler.close()
            operation_logger.removeHandler(handler)


def run_product_operation_by_id(
    operation_id: str,
    *,
    registry: ProductRegistry,
    context: AppContext,
    params: dict[str, Any] | None = None,
) -> ProductResult:
    return run_product_operation(registry.get(operation_id), context=context, params=params)
