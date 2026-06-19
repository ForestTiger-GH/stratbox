from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

ArtifactKind = Literal['file', 'folder', 'excel', 'zip', 'log', 'report', 'dataset', 'unknown']


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
class ArtifactRecord:
    artifact_id: str
    name: str
    path: str
    kind: ArtifactKind
    created_at: datetime
    author_id: str | None = None
    author_label: str | None = None
    scenario_id: str | None = None
    case_id: str | None = None
    operation_id: str | None = None
    log_id: str | None = None

    @classmethod
    def from_path(
        cls,
        path: str,
        *,
        scenario_id: str | None,
        case_id: str | None,
        operation_id: str | None,
        author_id: str | None,
        author_label: str | None,
    ) -> 'ArtifactRecord':
        p = Path(path)
        suffix = p.suffix.lower()
        if suffix in {'.xlsx', '.xlsm', '.xlsb', '.xls'}:
            kind: ArtifactKind = 'excel'
        elif suffix == '.zip':
            kind = 'zip'
        elif suffix == '.log':
            kind = 'log'
        elif p.exists() and p.is_dir():
            kind = 'folder'
        elif p.exists():
            kind = 'file'
        else:
            kind = 'unknown'
        return cls(
            artifact_id=uuid4().hex,
            name=p.name or str(p),
            path=str(p),
            kind=kind,
            created_at=datetime.now(),
            scenario_id=scenario_id,
            case_id=case_id,
            operation_id=operation_id,
            author_id=author_id,
            author_label=author_label,
        )

    @property
    def timestamp_label(self) -> str:
        return self.created_at.strftime('%H:%M')

    def to_dict(self) -> dict[str, object]:
        return {
            'artifact_id': self.artifact_id,
            'name': self.name,
            'path': self.path,
            'kind': self.kind,
            'created_at': self.created_at.isoformat(),
            'author_id': self.author_id,
            'author_label': self.author_label,
            'scenario_id': self.scenario_id,
            'case_id': self.case_id,
            'operation_id': self.operation_id,
            'log_id': self.log_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> 'ArtifactRecord':
        kind = str(data.get('kind') or 'unknown')
        if kind not in {'file', 'folder', 'excel', 'zip', 'log', 'report', 'dataset', 'unknown'}:
            kind = 'unknown'
        return cls(
            artifact_id=str(data.get('artifact_id') or uuid4().hex),
            name=str(data.get('name') or Path(str(data.get('path') or '')).name or 'Артефакт'),
            path=str(data.get('path') or ''),
            kind=kind,  # type: ignore[arg-type]
            created_at=_parse_datetime(data.get('created_at')) or datetime.now(),
            author_id=str(data['author_id']) if data.get('author_id') else None,
            author_label=str(data['author_label']) if data.get('author_label') else None,
            scenario_id=str(data['scenario_id']) if data.get('scenario_id') else None,
            case_id=str(data['case_id']) if data.get('case_id') else None,
            operation_id=str(data['operation_id']) if data.get('operation_id') else None,
            log_id=str(data['log_id']) if data.get('log_id') else None,
        )
