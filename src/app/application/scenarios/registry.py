from __future__ import annotations

from app.application.operations.catalog.models import OperationRegistry
from app.application.operations.forms.models import OperationParamSpec
from .models import ScenarioRegistry, ScenarioSpec, ScenarioStepSpec


def _atomic_scenario_id(operation_id: str) -> str:
    return f'scenario.atomic.{operation_id}'


def build_scenario_registry(operation_registry: OperationRegistry) -> ScenarioRegistry:
    scenarios: list[ScenarioSpec] = []
    for operation in operation_registry.enabled():
        scenarios.append(
            ScenarioSpec(
                id=_atomic_scenario_id(operation.id),
                title=operation.title,
                description=operation.description,
                kind='atomic',
                group=operation.group,
                steps=(
                    ScenarioStepSpec(
                        id='step.main',
                        operation_id=operation.id,
                        title=getattr(operation, 'default_stage_title', None) or operation.title,
                        description=operation.description,
                        order=10,
                    ),
                ),
                params=operation.params,
                icon=operation.icon,
                order=operation.order,
                group_order=operation.group_order,
                submit_label=operation.submit_label,
                supports_repeat=operation.supports_repeat,
                visibility_policy=operation.visibility_policy,
            )
        )
    if operation_registry.has('cbr_file_collector.collect') and operation_registry.has('escrow.history.export'):
        cbr = operation_registry.get('cbr_file_collector.collect')
        escrow = operation_registry.get('escrow.history.export')
        cbr_defaults = cbr.default_params()
        escrow_defaults = escrow.default_params()
        scenarios.append(
            ScenarioSpec(
                id='scenario.cbr.full_update',
                title='Обновление данных Банка России',
                description='Загружает исходные файлы ЦБ и собирает историческую сводку по счетам эскроу одним рабочим кейсом.',
                kind='composite',
                group='Сценарные блоки',
                steps=(
                    ScenarioStepSpec(
                        id='step.collect_cbr_files',
                        operation_id='cbr_file_collector.collect',
                        title='Загрузка исходных файлов ЦБ',
                        order=10,
                        params_map={
                            'cbr_save_mode': 'save_mode',
                            'target_dir': 'target_dir',
                            'overwrite': 'overwrite',
                        },
                    ),
                    ScenarioStepSpec(
                        id='step.export_escrow_history',
                        operation_id='escrow.history.export',
                        title='Сбор истории счетов эскроу',
                        order=20,
                        params_map={
                            'escrow_output_format': 'output_format',
                            'target_dir': 'target_dir',
                            'refresh_sources': 'refresh',
                        },
                    ),
                ),
                params=(
                    OperationParamSpec(
                        name='target_dir',
                        title='Каталог результата',
                        type='path_dir',
                        default=str(escrow_defaults.get('target_dir') or cbr_defaults.get('target_dir') or ''),
                        description='Единый каталог для результатов сценария. Каждый шаг создаёт внутри него свои файлы.',
                        required=True,
                        placeholder='Выберите каталог результата',
                    ),
                    OperationParamSpec(
                        name='cbr_save_mode',
                        title='Формат сохранения исходников ЦБ',
                        type='select',
                        default=str(cbr_defaults.get('save_mode') or 'zip'),
                        options=(('ZIP-архив', 'zip'), ('Каталог файлов', 'files')),
                        description='Как сохранить исходные файлы Банка России.',
                    ),
                    OperationParamSpec(
                        name='escrow_output_format',
                        title='Формат итоговой сводки эскроу',
                        type='select',
                        default=str(escrow_defaults.get('output_format') or 'xlsx'),
                        options=(('Excel-файл', 'xlsx'), ('ZIP-архив', 'zip')),
                        description='Формат итогового артефакта по счетам эскроу.',
                    ),
                    OperationParamSpec(
                        name='refresh_sources',
                        title='Перескачать исходники эскроу',
                        type='bool',
                        default=bool(escrow_defaults.get('refresh', False)),
                        description='Заново скачать исходники, даже если они уже есть в локальном кэше.',
                    ),
                    OperationParamSpec(
                        name='overwrite',
                        title='Перезаписывать результат',
                        type='bool',
                        default=bool(cbr_defaults.get('overwrite', True)),
                        description='Разрешить перезапись файлов, которые уже есть в каталоге результата.',
                    ),
                ),
                submit_label='Обновить данные',
                order=10,
                group_order=20,
                error_policy='fail_fast',
            )
        )
    return ScenarioRegistry(tuple(sorted(
        scenarios,
        key=lambda item: (item.group_order, item.group.lower(), item.order, item.title.lower()),
    )))
