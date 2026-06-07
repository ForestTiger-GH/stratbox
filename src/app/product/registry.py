from __future__ import annotations

from pathlib import Path

from app.core.context import AppContext
from app.product.models import ProductOperationSpec, ProductParamSpec, ProductRegistry


def _default_cbr_target_dir(context: AppContext) -> str:
    base = context.workspace_root_path if context.workspace_root_path is not None else Path('.')
    return str((base / 'output' / 'cbr_file_collector').as_posix())


def build_product_registry(context: AppContext) -> ProductRegistry:
    items = (
        ProductOperationSpec(
            id='cbr_file_collector.collect',
            title='Загрузчик исходных файлов ЦБ',
            description='Скачивает исходные файлы Банка России по встроенному реестру и сохраняет их как ZIP-архив или каталог файлов.',
            handler='app.product.operations.cbr_file_collector:run',
            group='Банк России',
            kind='business',
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
                    default=_default_cbr_target_dir(context),
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
                ProductParamSpec(
                    name='continue_on_error',
                    title='Продолжать при ошибках',
                    type='bool',
                    default=True,
                    description='Продолжать загрузку других файлов, даже если часть источников не скачалась.',
                    section='advanced',
                ),
                ProductParamSpec(
                    name='retry_attempts',
                    title='Повторные попытки',
                    type='int',
                    default=3,
                    description='Сколько раз повторять загрузку проблемного файла.',
                    section='advanced',
                    min_value=1,
                    max_value=10,
                ),
            ),
            submit_label='Загрузить файлы',
        ),
        ProductOperationSpec(
            id='system.diagnostics',
            title='Техническая диагностика',
            description='Проверяет рабочую среду приложения, доступность workspace и базовых зависимостей.',
            handler='app.product.operations.diagnostics:run',
            group='Система',
            kind='service',
            order=10,
            group_order=90,
            requires_workspace=False,
            params=tuple(),
            submit_label='Проверить среду',
        ),
    )
    return ProductRegistry(items=items)
