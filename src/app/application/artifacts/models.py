from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

ArtifactKind = Literal['file', 'folder', 'excel', 'zip', 'log', 'report', 'dataset', 'unknown']


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
