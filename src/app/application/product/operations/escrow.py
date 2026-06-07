from __future__ import annotations

from pathlib import Path
from typing import Any

from stratbox.macrobanks.escrow import (
    CBR_ESCROW_INDEX_URL,
    EscrowHistoryBuildRequest,
    EscrowViewBuildRequest,
    EscrowWorkbookExportRequest,
    build_escrow_history,
    export_escrow_workbook,
)

from app.application.product.catalog.models import ProductOperationSpec
from app.application.product.execution.requests import ProductOperationContext, ProductResult

DEFAULT_ESCROW_XLSX_NAME = 'Escrow History.xlsx'
DEFAULT_ESCROW_ZIP_NAME = 'Escrow History.zip'
DEFAULT_ESCROW_CACHE_DIRNAME = 'escrow_sources'


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'да'}


def _build_output_path(*, target_dir: str, output_format: str) -> str:
    base = Path(str(target_dir)).expanduser()
    normalized = str(output_format or 'xlsx').strip().lower()
    if normalized == 'zip':
        return str((base / DEFAULT_ESCROW_ZIP_NAME).as_posix())
    return str((base / DEFAULT_ESCROW_XLSX_NAME).as_posix())


def _build_cache_dir(context: ProductOperationContext) -> str:
    if context.workspace_root_path is None:
        raise RuntimeError('Workspace root is not available for escrow operation')
    return str((context.workspace_root_path / 'input' / DEFAULT_ESCROW_CACHE_DIRNAME).as_posix())


def run(*, context: ProductOperationContext, params: dict[str, Any], spec: ProductOperationSpec) -> ProductResult:
    if context.filestore is None:
        raise RuntimeError('FileStore is not available for current workspace root')
    if context.workspace_root_path is None:
        raise RuntimeError('Workspace root is not available for current workspace root')

    output_format = str(params.get('output_format') or 'xlsx').strip().lower()
    if output_format not in {'xlsx', 'zip'}:
        raise ValueError(f'Unsupported output_format: {output_format}')

    target_dir = str(params.get('target_dir') or '').strip()
    if not target_dir:
        raise ValueError('Каталог результата не задан.')

    refresh = _as_bool(params.get('refresh'), default=False)
    output_path = _build_output_path(target_dir=target_dir, output_format=output_format)
    source_cache_dir = _build_cache_dir(context)

    context.logger.info('Escrow export started')
    context.logger.info('Output format: %s', output_format)
    context.logger.info('Target dir: %s', target_dir)
    context.logger.info('Output path: %s', output_path)
    context.logger.info('Source cache dir: %s', source_cache_dir)
    context.logger.info('Refresh sources: %s', refresh)

    history_request = EscrowHistoryBuildRequest(
        index_url=str(params.get('index_url') or CBR_ESCROW_INDEX_URL),
        source_cache_dir=source_cache_dir,
        refresh=refresh,
        timeout=int(params.get('timeout', 60)),
        retries=int(params.get('retries', 2)),
        backoff=float(params.get('backoff', 0.5)),
        min_bytes_ok=int(params.get('min_bytes_ok', 512)),
        headers=None,
        plugin_only=_as_bool(params.get('plugin_only'), default=True),
        show_progress=False,
        source_error_policy=str(params.get('source_error_policy') or 'fail_fast').strip().lower(),
    )
    history = build_escrow_history(history_request, filestore=context.filestore)

    export_request = EscrowWorkbookExportRequest(
        out_path=output_path,
        archive=(output_format == 'zip'),
        archive_member_name=None,
        show_progress=False,
    )
    view_request = EscrowViewBuildRequest(
        regions_mode=str(params.get('regions_mode') or 'latest').strip().lower(),
        custom_regions=tuple(),
    )
    export_result = export_escrow_workbook(
        history,
        export_request,
        view_request=view_request,
        filestore=context.filestore,
    )

    details = {
        'output_path': export_result.output_path,
        'archive': export_result.archive,
        'source_files_count': len(export_result.source_files),
        'source_files': list(export_result.source_files),
        'dates_count': len(export_result.dates),
        'dates': list(export_result.dates),
        'indicators_count': len(export_result.indicators),
        'indicators': list(export_result.indicators),
        'regions_count': len(export_result.regions),
        'regions': list(export_result.regions),
        'rows_long': export_result.rows_long,
        'source_links_count': export_result.source_links_count,
        'failure_count': export_result.failure_count,
        'workspace_root_path': str(context.workspace_root_path),
        'source_cache_dir': source_cache_dir,
        'refresh': refresh,
        'operation_log': str(context.operation_log_path),
    }

    message = (
        f'История счетов эскроу собрана. '
        f'Источников: {export_result.source_links_count}. '
        f'Периодов: {len(export_result.dates)}. '
        f'Показателей: {len(export_result.indicators)}. '
        f'Результат: {export_result.output_path}'
    )
    outputs = (export_result.output_path, str(context.operation_log_path))
    return ProductResult(ok=export_result.ok, message=message, outputs=outputs, details=details)
