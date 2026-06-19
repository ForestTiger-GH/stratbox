from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from app.application.artifacts.models import ArtifactRecord
from app.application.cases.models import ScenarioRunCase, ScenarioStepRun
from app.application.events.models import OperationalEvent
from app.application.logs.models import LogRecord
from app.application.operations.catalog.models import OperationRegistry
from app.application.operations.execution.runner import run_operation
from app.runtime.context import AppContext
from .models import ScenarioSpec

CaseUpdated = Callable[[ScenarioRunCase], None]
EventEmitted = Callable[[OperationalEvent], None]
ArtifactEmitted = Callable[[list[ArtifactRecord]], None]
LogEmitted = Callable[[LogRecord], None]


def _build_step_params(*, scenario_params: dict[str, Any], step) -> dict[str, Any]:
    """Build operation params for one scenario step.

    Atomic scenarios pass scenario params through as-is. Composite scenarios may
    expose their own user-facing params and map them to operation-specific names.
    Step overrides always win.
    """
    if step.params_map:
        resolved: dict[str, Any] = {}
        for source_key, target_key in step.params_map.items():
            if source_key in scenario_params:
                resolved[target_key] = scenario_params[source_key]
    else:
        resolved = dict(scenario_params)
    resolved.update(step.params_override)
    return resolved


def build_case_for_scenario(*, scenario: ScenarioSpec, context: AppContext, params: dict[str, Any]) -> ScenarioRunCase:
    steps = [
        ScenarioStepRun(step_id=step.id, operation_id=step.operation_id, title=step.title)
        for step in sorted(scenario.steps, key=lambda item: item.order)
    ]
    return ScenarioRunCase.create(
        scenario_id=scenario.id,
        scenario_title=scenario.title,
        params=dict(params),
        author_id=context.user_id,
        author_label=context.account_name or 'Пользователь',
        steps=steps,
    )


def run_scenario(
    *,
    scenario: ScenarioSpec,
    operation_registry: OperationRegistry,
    context: AppContext,
    params: dict[str, Any],
    case: ScenarioRunCase,
    on_case_updated: CaseUpdated,
    on_event: EventEmitted,
    on_artifacts: ArtifactEmitted,
    on_log: LogEmitted,
) -> ScenarioRunCase:
    case.status = 'running'
    case.started_at = datetime.now()
    case.current_stage = 'Подготовка сценария'
    on_case_updated(case)
    on_event(OperationalEvent.create(
        kind='case_started',
        status='running',
        title=f'{scenario.title} запущен',
        body=f'Параметры: {case.short_params_text()}',
        actor_kind='user',
        author_id=case.author_id,
        author_label=case.author_label,
        case_id=case.case_id,
        scenario_id=scenario.id,
    ))

    all_outputs: list[str] = []
    step_specs = {step.id: step for step in scenario.steps}
    for step_run in case.steps:
        step_spec = step_specs[step_run.step_id]
        operation = operation_registry.get(step_run.operation_id)
        step_run.status = 'running'
        step_run.started_at = datetime.now()
        case.current_stage = step_run.title
        on_case_updated(case)
        on_event(OperationalEvent.create(
            kind='step_started',
            status='running',
            title=step_run.title,
            body='Шаг сценария принят в обработку.',
            actor_kind='system',
            case_id=case.case_id,
            scenario_id=scenario.id,
            operation_id=operation.id,
        ))
        step_params = _build_step_params(scenario_params=params, step=step_spec)
        result = run_operation(
            operation,
            context=context,
            params=step_params,
            scenario_id=scenario.id,
            case_id=case.case_id,
            step_id=step_run.step_id,
        )
        step_run.finished_at = datetime.now()
        step_run.outputs = result.outputs
        step_run.message = result.message
        step_run.log_path = str(result.details.get('operation_log') or '') or None
        status = 'success' if result.ok else 'failed'
        step_run.status = status
        if step_run.log_path:
            on_log(LogRecord.create(
                title=f'Лог: {step_run.title}',
                path=step_run.log_path,
                case_id=case.case_id,
                scenario_id=scenario.id,
                operation_id=operation.id,
                step_id=step_run.step_id,
                status=('success' if result.ok else 'error'),
            ))
        artifacts = [
            ArtifactRecord.from_path(
                output,
                scenario_id=scenario.id,
                case_id=case.case_id,
                operation_id=operation.id,
                author_id=case.author_id,
                author_label=case.author_label,
            )
            for output in result.outputs
        ]
        if artifacts:
            on_artifacts(artifacts)
        all_outputs.extend(result.outputs)
        on_event(OperationalEvent.create(
            kind='step_completed' if result.ok else 'step_failed',
            status='success' if result.ok else 'error',
            title=(f'{step_run.title} завершён' if result.ok else f'{step_run.title} завершён с ошибкой'),
            body=result.message,
            actor_kind='system',
            case_id=case.case_id,
            scenario_id=scenario.id,
            operation_id=operation.id,
            artifact_ids=tuple(artifact.artifact_id for artifact in artifacts),
        ))
        on_case_updated(case)
        if not result.ok and scenario.error_policy == 'fail_fast':
            case.status = 'failed'
            case.message = result.message
            break

    case.outputs = tuple(all_outputs)
    case.finished_at = datetime.now()
    if case.status != 'failed':
        case.status = 'success'
        case.message = 'Сценарий завершён.'
        event_kind = 'case_completed'
        event_status = 'success'
        event_title = f'{scenario.title} завершён'
    else:
        event_kind = 'case_failed'
        event_status = 'error'
        event_title = f'{scenario.title} завершён с ошибкой'
    case.current_stage = ''
    on_event(OperationalEvent.create(
        kind=event_kind,
        status=event_status,
        title=event_title,
        body=case.message,
        actor_kind='system',
        author_id=case.author_id,
        author_label=case.author_label,
        case_id=case.case_id,
        scenario_id=scenario.id,
    ))
    on_case_updated(case)
    return case
