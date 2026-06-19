from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

LogStatus = Literal['info', 'running', 'success', 'warning', 'error']


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
class LogRecord:
    log_id: str
    title: str
    path: str
    created_at: datetime
    status: LogStatus = 'info'
    case_id: str | None = None
    scenario_id: str | None = None
    operation_id: str | None = None
    step_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        title: str,
        path: str,
        status: LogStatus = 'info',
        case_id: str | None = None,
        scenario_id: str | None = None,
        operation_id: str | None = None,
        step_id: str | None = None,
    ) -> 'LogRecord':
        return cls(
            log_id=uuid4().hex,
            title=title,
            path=str(Path(path)),
            created_at=datetime.now(),
            status=status,
            case_id=case_id,
            scenario_id=scenario_id,
            operation_id=operation_id,
            step_id=step_id,
        )

    @property
    def timestamp_label(self) -> str:
        return self.created_at.strftime('%H:%M')

    def to_dict(self) -> dict[str, object]:
        return {
            'log_id': self.log_id,
            'title': self.title,
            'path': self.path,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'case_id': self.case_id,
            'scenario_id': self.scenario_id,
            'operation_id': self.operation_id,
            'step_id': self.step_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> 'LogRecord':
        status = str(data.get('status') or 'info')
        if status not in {'info', 'running', 'success', 'warning', 'error'}:
            status = 'info'
        return cls(
            log_id=str(data.get('log_id') or uuid4().hex),
            title=str(data.get('title') or 'Лог'),
            path=str(data.get('path') or ''),
            created_at=_parse_datetime(data.get('created_at')) or datetime.now(),
            status=status,  # type: ignore[arg-type]
            case_id=str(data['case_id']) if data.get('case_id') else None,
            scenario_id=str(data['scenario_id']) if data.get('scenario_id') else None,
            operation_id=str(data['operation_id']) if data.get('operation_id') else None,
            step_id=str(data['step_id']) if data.get('step_id') else None,
        )
