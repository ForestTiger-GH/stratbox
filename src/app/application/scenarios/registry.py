from __future__ import annotations

from app.application.operations.catalog.models import OperationRegistry
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
                    ),
                    ScenarioStepSpec(
                        id='step.export_escrow_history',
                        operation_id='escrow.history.export',
                        title='Сбор истории счетов эскроу',
                        order=20,
                    ),
                ),
                params=operation_registry.get('escrow.history.export').params,
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
