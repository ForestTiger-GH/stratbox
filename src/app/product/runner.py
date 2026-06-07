from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any, Callable

from app.core.context import AppContext
from app.product.models import ProductOperationContext, ProductOperationSpec, ProductRegistry, ProductResult


def _load_handler(handler_ref: str) -> Callable[..., ProductResult]:
    if ':' not in handler_ref:
        raise ValueError(f"Handler must use 'module:function' format: {handler_ref}")
    module_name, func_name = handler_ref.split(':', 1)
    module = importlib.import_module(module_name)
    handler = getattr(module, func_name)
    if not callable(handler):
        raise ValueError(f'Handler is not callable: {handler_ref}')
    return handler


def _build_operation_logger(operation_id: str, logs_dir: Path) -> tuple[logging.Logger, Path]:
    logs_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = logs_dir / f'{operation_id.replace(".", "_")}_{stamp}.log'
    logger = logging.getLogger(f'strategy_box_app.operation.{operation_id}.{stamp}')
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
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
    operation_logger, operation_log_path = _build_operation_logger(spec.id, context.paths.logs_dir / 'operations')
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
        operation_logger.info('Operation finished: %s OK=%s', spec.id, result.ok)
        context.logger.info('Operation finished: %s OK=%s', spec.id, result.ok)
        return result
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
