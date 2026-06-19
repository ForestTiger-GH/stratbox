from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import uuid4

AssignmentStatus = Literal['active', 'completed', 'cancelled']


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
class AssignmentRecord:
    assignment_id: str
    title: str
    status: AssignmentStatus
    assignee_id: str | None
    author_id: str | None
    description: str = ''
    scenario_id: str | None = None
    case_id: str | None = None
    artifact_id: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        title: str,
        status: AssignmentStatus = 'active',
        assignee_id: str | None = None,
        author_id: str | None = None,
        description: str = '',
        scenario_id: str | None = None,
        case_id: str | None = None,
        artifact_id: str | None = None,
    ) -> 'AssignmentRecord':
        return cls(
            assignment_id=uuid4().hex,
            title=title,
            status=status,
            assignee_id=assignee_id,
            author_id=author_id,
            description=description,
            scenario_id=scenario_id,
            case_id=case_id,
            artifact_id=artifact_id,
        )

    def complete(self) -> None:
        self.status = 'completed'
        self.completed_at = datetime.now()

    def cancel(self) -> None:
        self.status = 'cancelled'
        self.completed_at = datetime.now()

    @property
    def timestamp_label(self) -> str:
        value = self.completed_at or self.created_at
        return value.strftime('%H:%M')

    def to_dict(self) -> dict[str, object]:
        return {
            'assignment_id': self.assignment_id,
            'title': self.title,
            'status': self.status,
            'assignee_id': self.assignee_id,
            'author_id': self.author_id,
            'description': self.description,
            'scenario_id': self.scenario_id,
            'case_id': self.case_id,
            'artifact_id': self.artifact_id,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> 'AssignmentRecord':
        status = str(data.get('status') or 'active')
        if status not in {'active', 'completed', 'cancelled'}:
            status = 'active'
        return cls(
            assignment_id=str(data.get('assignment_id') or uuid4().hex),
            title=str(data.get('title') or 'Поручение'),
            status=status,  # type: ignore[arg-type]
            assignee_id=str(data['assignee_id']) if data.get('assignee_id') else None,
            author_id=str(data['author_id']) if data.get('author_id') else None,
            description=str(data.get('description') or ''),
            scenario_id=str(data['scenario_id']) if data.get('scenario_id') else None,
            case_id=str(data['case_id']) if data.get('case_id') else None,
            artifact_id=str(data['artifact_id']) if data.get('artifact_id') else None,
            created_at=_parse_datetime(data.get('created_at')) or datetime.now(),
            completed_at=_parse_datetime(data.get('completed_at')),
        )
