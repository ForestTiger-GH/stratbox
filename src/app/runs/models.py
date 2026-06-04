from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

RunStatus = Literal['submitted', 'running', 'success', 'failed']


@dataclass(slots=True)
class RunRecord:
    run_id: str
    scenario_id: str
    scenario_title: str
    params: dict[str, Any]
    status: RunStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    author_id: str | None = None
    author_label: str | None = None
    outputs: tuple[str, ...] = tuple()
    message: str = ''

    @classmethod
    def create(cls, *, scenario_id: str, scenario_title: str, params: dict[str, Any], author_id: str | None, author_label: str | None) -> 'RunRecord':
        return cls(
            run_id=uuid4().hex,
            scenario_id=scenario_id,
            scenario_title=scenario_title,
            params=params,
            status='submitted',
            created_at=datetime.now(),
            author_id=author_id,
            author_label=author_label,
        )

    def short_params_text(self) -> str:
        parts: list[str] = []
        for key, value in self.params.items():
            if value in (None, '', False):
                continue
            parts.append(f'{key}={value}')
        return ', '.join(parts) if parts else 'без параметров'
