from __future__ import annotations

from pathlib import Path

from app.runtime.context import AppContext
from app.application.product.catalog.models import ProductOperationSpec, ProductRegistry
from app.application.product.forms.defaults import default_cbr_target_dir, default_escrow_target_dir
from app.application.product.forms.models import ProductParamSpec


def build_product_registry(context: AppContext) -> ProductRegistry:
    items = (
        ProductOperationSpec(
            id='cbr_file_collector.collect',
            title='Загрузчик исходных файлов ЦБ',
            description='Скачивает исходные файлы Банка России по встроенному реестру и сохраняет их как ZIP-архив или каталог файлов.',
            handler='app.application.product.operations.cbr_file_collector:run',
            group='Банк России',
            kind='business',
            tags=('cbr', 'files', 'collector'),
            search_aliases=('Банк России', 'исходники', 'zip', 'raw files'),
            result_preview_kind='artifact_summary',
            order=10,
            group_order=10,
            params=(
                ProductParamSpec(
                    name='save_mode',
                    title='Формат сохранения',
                    type='select',
                    default='zip',
                    options=(('ZIP-архив', 'zip'), ('Каталог файлов', 'files')),
                    description='Сохранить исходники одним архивом или как каталог отдельных файлов.',
                ),
                ProductParamSpec(
                    name='target_dir',
                    title='Каталог результата',
                    type='path_dir',
                    default=default_cbr_target_dir(context),
                    description='Каталог, внутри которого приложение создаст ZIP-архив или папку результата.',
                    required=True,
                    placeholder='Выберите каталог результата',
                ),
                ProductParamSpec(
                    name='overwrite',
                    title='Перезаписывать результат',
                    type='bool',
                    default=True,
                    description='Разрешить перезапись итогового ZIP-файла или существующих файлов в каталоге результата.',
                ),
            ),
            fixed_param_values={
                'continue_on_error': True,
                'retry_attempts': 3,
            },
            submit_label='Загрузить файлы',
        ),

        ProductOperationSpec(
            id='escrow.history.export',
            title='История счетов эскроу',
            description='Строит историческую сводку по ежемесячным публикациям Банка России о счетах эскроу и сохраняет результат как Excel-файл или ZIP-архив.',
            handler='app.application.product.operations.escrow:run',
            group='Банк России',
            kind='business',
            tags=('cbr', 'escrow', 'history'),
            search_aliases=('эскроу', 'счета эскроу', 'история эскроу', 'Банк России'),
            result_preview_kind='artifact_summary',
            order=20,
            group_order=10,
            params=(
                ProductParamSpec(
                    name='output_format',
                    title='Формат результата',
                    type='select',
                    default='xlsx',
                    options=(('Excel-файл', 'xlsx'), ('ZIP-архив', 'zip')),
                    description='Сохранить сводку как обычный Excel-файл или как ZIP-архив с одним Excel-файлом внутри.',
                ),
                ProductParamSpec(
                    name='target_dir',
                    title='Каталог результата',
                    type='path_dir',
                    default=default_escrow_target_dir(context),
                    description='Каталог, внутри которого приложение создаст итоговый Excel-файл или ZIP-архив.',
                    required=True,
                    placeholder='Выберите каталог результата',
                ),
                ProductParamSpec(
                    name='refresh',
                    title='Перескачать исходники',
                    type='bool',
                    default=False,
                    description='Заново скачать ежемесячные файлы ЦБ, даже если они уже есть в локальном кэше workspace.',
                ),
            ),
            fixed_param_values={
                'index_url': 'https://www.cbr.ru/statistics/bank_sector/equity_const_financing/',
                'timeout': 60,
                'retries': 2,
                'backoff': 0.5,
                'min_bytes_ok': 512,
                'plugin_only': True,
                'source_error_policy': 'fail_fast',
                'regions_mode': 'latest',
            },
            submit_label='Собрать сводку',
        ),

        ProductOperationSpec(
            id='system.diagnostics',
            title='Техническая диагностика',
            description='Проверяет рабочую среду приложения, доступность workspace и базовых зависимостей.',
            handler='app.application.product.operations.diagnostics:run',
            group='Система',
            kind='service',
            tags=('system', 'diagnostics'),
            search_aliases=('система', 'проверка среды', 'workspace'),
            result_preview_kind='diagnostics',
            order=10,
            group_order=90,
            requires_workspace=False,
            params=tuple(),
            submit_label='Проверить среду',
        ),
    )
    return ProductRegistry(items=items)
