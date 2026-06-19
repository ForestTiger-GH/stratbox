from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

CaseStatus = Literal['prepared', 'queued', 'running', 'success', 'warning', 'failed', 'cancelled']
StepStatus = Literal['pending', 'running', 'success', 'warning', 'failed', 'skipped']


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


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

    def to_dict(self) -> dict[str, object]:
        return {
            'step_id': self.step_id,
            'operation_id': self.operation_id,
            'title': self.title,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'message': self.message,
            'outputs': list(self.outputs),
            'log_path': self.log_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> 'ScenarioStepRun':
        status = str(data.get('status') or 'pending')
        if status not in {'pending', 'running', 'success', 'warning', 'failed', 'skipped'}:
            status = 'pending'
        outputs = data.get('outputs') if isinstance(data.get('outputs'), list) else []
        return cls(
            step_id=str(data.get('step_id') or 'step'),
            operation_id=str(data.get('operation_id') or ''),
            title=str(data.get('title') or 'Шаг'),
            status=status,  # type: ignore[arg-type]
            started_at=_parse_datetime(data.get('started_at')),
            finished_at=_parse_datetime(data.get('finished_at')),
            message=str(data.get('message') or ''),
            outputs=tuple(str(x) for x in outputs),
            log_path=str(data['log_path']) if data.get('log_path') else None,
        )


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

    def to_dict(self) -> dict[str, object]:
        return {
            'case_id': self.case_id,
            'scenario_id': self.scenario_id,
            'scenario_title': self.scenario_title,
            'params': self.params,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'author_id': self.author_id,
            'author_label': self.author_label,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'current_stage': self.current_stage,
            'steps': [step.to_dict() for step in self.steps],
            'outputs': list(self.outputs),
            'message': self.message,
            'unread': self.unread,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> 'ScenarioRunCase':
        status = str(data.get('status') or 'prepared')
        if status not in {'prepared', 'queued', 'running', 'success', 'warning', 'failed', 'cancelled'}:
            status = 'prepared'
        steps_raw = data.get('steps') if isinstance(data.get('steps'), list) else []
        outputs_raw = data.get('outputs') if isinstance(data.get('outputs'), list) else []
        params = data.get('params') if isinstance(data.get('params'), dict) else {}
        return cls(
            case_id=str(data.get('case_id') or uuid4().hex),
            scenario_id=str(data.get('scenario_id') or ''),
            scenario_title=str(data.get('scenario_title') or 'Сценарий'),
            params=dict(params),
            status=status,  # type: ignore[arg-type]
            created_at=_parse_datetime(data.get('created_at')) or datetime.now(),
            author_id=str(data['author_id']) if data.get('author_id') else None,
            author_label=str(data['author_label']) if data.get('author_label') else None,
            started_at=_parse_datetime(data.get('started_at')),
            finished_at=_parse_datetime(data.get('finished_at')),
            current_stage=str(data.get('current_stage') or ''),
            steps=[ScenarioStepRun.from_dict(x) for x in steps_raw if isinstance(x, dict)],
            outputs=tuple(str(x) for x in outputs_raw),
            message=str(data.get('message') or ''),
            unread=bool(data.get('unread', True)),
        )
