from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(slots=True)
class AssignmentRecord:
    assignment_id: str
    title: str
    status: str
    assignee_id: str | None
    author_id: str | None
    scenario_id: str | None = None
    case_id: str | None = None
    artifact_id: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @classmethod
    def create(cls, *, title: str, status: str = 'active', assignee_id: str | None = None, author_id: str | None = None) -> 'AssignmentRecord':
        return cls(uuid4().hex, title, status, assignee_id, author_id)
