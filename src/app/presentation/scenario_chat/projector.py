from __future__ import annotations

from app.application.artifacts.store import ArtifactStore
from app.application.cases.models import ScenarioRunCase
from app.application.events.models import OperationalEvent
from .models import ScenarioArtifactLine, ScenarioChatMessage, ScenarioStepLine


_STATUS_LABELS = {
    'prepared': 'Подготовлено',
    'queued': 'В очереди',
    'running': 'Выполняется',
    'success': 'Завершено',
    'warning': 'С замечаниями',
    'failed': 'Ошибка',
    'cancelled': 'Отменено',
    'info': 'Инфо',
    'error': 'Ошибка',
}


def project_case(case: ScenarioRunCase, artifacts: ArtifactStore) -> ScenarioChatMessage:
    case_artifacts = artifacts.by_case(case.case_id)
    return ScenarioChatMessage(
        message_id=case.case_id,
        message_kind='case',
        tone=case.status,
        title=case.scenario_title,
        summary=case.message or ('Сценарий выполняется.' if case.status == 'running' else 'Сценарий подготовлен.'),
        status_label=_STATUS_LABELS.get(case.status, case.status),
        status=case.status,
        author_label=case.author_label or 'Пользователь',
        timestamp_label=case.timestamp_label,
        stage_label=case.current_stage or None,
        params_summary=case.short_params_text(),
        steps=tuple(ScenarioStepLine(step.title, step.status, step.message) for step in case.steps),
        artifacts=tuple(ScenarioArtifactLine(item.name, item.path) for item in case_artifacts),
        source_case_id=case.case_id,
    )


def project_event(event: OperationalEvent) -> ScenarioChatMessage:
    return ScenarioChatMessage(
        message_id=event.event_id,
        message_kind='notice',
        tone=event.status,
        title=event.title,
        summary=event.body,
        status_label=_STATUS_LABELS.get(event.status, event.status),
        status=event.status,
        author_label=event.author_label or ('Фоновый процесс' if event.actor_kind == 'background' else 'Система'),
        timestamp_label=event.timestamp_label,
        source_event_id=event.event_id,
        source_case_id=event.case_id,
    )
