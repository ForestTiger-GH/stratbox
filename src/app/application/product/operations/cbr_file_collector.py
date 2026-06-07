from __future__ import annotations

from pathlib import Path
from typing import Any

from stratbox.macrobanks.cbr_file_collector import (
    CbrFileCollectRequest,
    DEFAULT_CBR_FILES_ARCHIVE_NAME,
    DEFAULT_CBR_FILES_DIRECTORY_NAME,
    collect_cbr_files,
)

from app.application.product.catalog.models import ProductOperationSpec
from app.application.product.execution.requests import ProductOperationContext, ProductResult


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'да'}


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _build_target_path(*, target_dir: str, save_mode: str) -> str:
    base = Path(str(target_dir)).expanduser()
    if save_mode == 'files':
        return str((base / DEFAULT_CBR_FILES_DIRECTORY_NAME).as_posix())
    return str((base / DEFAULT_CBR_FILES_ARCHIVE_NAME).as_posix())


def run(*, context: ProductOperationContext, params: dict[str, Any], spec: ProductOperationSpec) -> ProductResult:
    if context.filestore is None:
        raise RuntimeError('FileStore is not available for current workspace root')

    save_mode = str(params.get('save_mode') or 'zip').strip().lower()
    target_dir = str(params.get('target_dir') or '').strip()
    if not target_dir:
        raise ValueError('Каталог результата не задан.')
    target_path = _build_target_path(target_dir=target_dir, save_mode=save_mode)

    context.logger.info('CBR file collector started')
    context.logger.info('Save mode: %s', save_mode)
    context.logger.info('Target dir: %s', target_dir)
    context.logger.info('Target path: %s', target_path)

    result = collect_cbr_files(
        CbrFileCollectRequest(
            target_path=target_path,
            save_mode=save_mode,  # type: ignore[arg-type]
            overwrite=_as_bool(params.get('overwrite', True)),
            continue_on_error=_as_bool(params.get('continue_on_error', True)),
            retry_attempts=_as_int(params.get('retry_attempts', 3), 3),
            show_progress=False,
        ),
        filestore=context.filestore,
    )

    details = result.to_dict()
    details['operation_log'] = str(context.operation_log_path)
    details['workspace_root_path'] = str(context.workspace_root_path) if context.workspace_root_path else None

    if result.failure_count:
        message = (
            f'Загрузка завершена: скачано {result.success_count} из {result.requested_count}. '
            f'Проблемных файлов: {result.failure_count}. '
            f'Результат: {result.target_path}'
        )
    else:
        message = f'Загружено {result.success_count} из {result.requested_count}. Результат: {result.target_path}'

    outputs = (result.target_path, str(context.operation_log_path))
    return ProductResult(ok=result.ok, message=message, outputs=outputs, details=details)
