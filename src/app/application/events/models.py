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
