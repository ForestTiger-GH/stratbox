from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

CaseStatus = Literal['prepared', 'queued', 'running', 'success', 'warning', 'failed', 'cancelled']
StepStatus = Literal['pending', 'running', 'success', 'warning', 'failed', 'skipped']


@dataclass(slots=True)
class ScenarioStepRun:
    step_id: str
    operation_id: str
    title: str
    status: StepStatus = 'pending'
    started_at: datetime | None = None
    finished_at: datetime | None = None
    message: str = ''
    outputs: tuple[str, ...] = ()
    log_path: str | None = None

    @property
    def timestamp_label(self) -> str:
        value = self.finished_at or self.started_at
        return value.strftime('%H:%M') if value else ''


@dataclass(slots=True)
class ScenarioRunCase:
    case_id: str
    scenario_id: str
    scenario_title: str
    params: dict[str, Any]
    status: CaseStatus
    created_at: datetime
    author_id: str | None = None
    author_label: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    current_stage: str = ''
    steps: list[ScenarioStepRun] = field(default_factory=list)
    outputs: tuple[str, ...] = ()
    message: str = ''
    unread: bool = True

    @classmethod
    def create(
        cls,
        *,
        scenario_id: str,
        scenario_title: str,
        params: dict[str, Any],
        author_id: str | None,
        author_label: str | None,
        steps: list[ScenarioStepRun],
    ) -> 'ScenarioRunCase':
        return cls(
            case_id=uuid4().hex,
            scenario_id=scenario_id,
            scenario_title=scenario_title,
            params=dict(params),
            status='prepared',
            created_at=datetime.now(),
            author_id=author_id,
            author_label=author_label,
            steps=steps,
        )

    @property
    def timestamp_label(self) -> str:
        value = self.finished_at or self.started_at or self.created_at
        return value.strftime('%H:%M')

    def short_params_text(self) -> str:
        parts: list[str] = []
        for key, value in self.params.items():
            if value in (None, '', False):
                continue
            parts.append(f'{key}={value}')
        return ', '.join(parts) if parts else 'без параметров'

    def duration_label(self) -> str:
        if self.started_at is None or self.finished_at is None:
            return ''
        seconds = max(0, int((self.finished_at - self.started_at).total_seconds()))
        if seconds < 60:
            return f'{seconds} сек.'
        minutes, rest = divmod(seconds, 60)
        return f'{minutes} мин. {rest} сек.'
