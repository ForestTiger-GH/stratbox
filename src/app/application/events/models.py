from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import uuid4

EventKind = Literal[
    'case_prepared', 'case_started', 'case_completed', 'case_failed',
    'step_started', 'step_completed', 'step_failed', 'artifact_created',
    'system_notice', 'background_notice', 'assignment_notice'
]
EventStatus = Literal['info', 'running', 'success', 'warning', 'error']
ActorKind = Literal['user', 'host_user', 'ai', 'system', 'background']


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
class OperationalEvent:
    event_id: str
    kind: EventKind
    status: EventStatus
    title: str
    body: str
    created_at: datetime
    actor_kind: ActorKind = 'system'
    author_id: str | None = None
    author_label: str | None = None
    case_id: str | None = None
    scenario_id: str | None = None
    operation_id: str | None = None
    artifact_ids: tuple[str, ...] = ()
    log_ids: tuple[str, ...] = ()
    meta: dict[str, str] = field(default_factory=dict)
    unread: bool = True

    @classmethod
    def create(cls, **kwargs) -> 'OperationalEvent':
        return cls(
            event_id=kwargs.pop('event_id', uuid4().hex),
            created_at=kwargs.pop('created_at', datetime.now()),
            **kwargs,
        )

    @property
    def timestamp_label(self) -> str:
        return self.created_at.strftime('%H:%M')

    def to_dict(self) -> dict[str, object]:
        return {
            'event_id': self.event_id,
            'kind': self.kind,
            'status': self.status,
            'title': self.title,
            'body': self.body,
            'created_at': self.created_at.isoformat(),
            'actor_kind': self.actor_kind,
            'author_id': self.author_id,
            'author_label': self.author_label,
            'case_id': self.case_id,
            'scenario_id': self.scenario_id,
            'operation_id': self.operation_id,
            'artifact_ids': list(self.artifact_ids),
            'log_ids': list(self.log_ids),
            'meta': dict(self.meta),
            'unread': self.unread,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> 'OperationalEvent':
        kind = str(data.get('kind') or 'system_notice')
        if kind not in {
            'case_prepared', 'case_started', 'case_completed', 'case_failed',
            'step_started', 'step_completed', 'step_failed', 'artifact_created',
            'system_notice', 'background_notice', 'assignment_notice'
        }:
            kind = 'system_notice'
        status = str(data.get('status') or 'info')
        if status not in {'info', 'running', 'success', 'warning', 'error'}:
            status = 'info'
        actor_kind = str(data.get('actor_kind') or 'system')
        if actor_kind not in {'user', 'host_user', 'ai', 'system', 'background'}:
            actor_kind = 'system'
        artifact_ids = data.get('artifact_ids') if isinstance(data.get('artifact_ids'), list) else []
        log_ids = data.get('log_ids') if isinstance(data.get('log_ids'), list) else []
        meta = data.get('meta') if isinstance(data.get('meta'), dict) else {}
        return cls(
            event_id=str(data.get('event_id') or uuid4().hex),
            kind=kind,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            title=str(data.get('title') or 'Событие'),
            body=str(data.get('body') or ''),
            created_at=_parse_datetime(data.get('created_at')) or datetime.now(),
            actor_kind=actor_kind,  # type: ignore[arg-type]
            author_id=str(data['author_id']) if data.get('author_id') else None,
            author_label=str(data['author_label']) if data.get('author_label') else None,
            case_id=str(data['case_id']) if data.get('case_id') else None,
            scenario_id=str(data['scenario_id']) if data.get('scenario_id') else None,
            operation_id=str(data['operation_id']) if data.get('operation_id') else None,
            artifact_ids=tuple(str(x) for x in artifact_ids),
            log_ids=tuple(str(x) for x in log_ids),
            meta={str(k): str(v) for k, v in meta.items()},
            unread=bool(data.get('unread', True)),
        )
