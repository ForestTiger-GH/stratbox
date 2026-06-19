from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.application.artifacts.models import ArtifactRecord
from app.application.artifacts.store import ArtifactStore
from app.application.assignments.models import AssignmentRecord
from app.application.assignments.store import AssignmentStore
from app.application.cases.models import ScenarioRunCase
from app.application.cases.store import ScenarioCaseStore
from app.application.events.models import OperationalEvent
from app.application.events.store import OperationalEventStore
from app.application.logs.models import LogRecord
from app.application.logs.store import LogStore


class HistoryPersistenceService:
    """Lightweight JSON persistence for recent Strategy Box history.

    The goal here is not full database-grade durability. The service stores the
    latest projections of cases, events, artifacts, logs and assignments inside
    the app-owned runtime area so the desktop surface can restore recent context
    across restarts and AppDock relaunches.
    """

    def __init__(self, runtime_dir: Path) -> None:
        self._history_dir = Path(runtime_dir).expanduser() / 'history'
        self._history_dir.mkdir(parents=True, exist_ok=True)
        self._cases_path = self._history_dir / 'cases.json'
        self._events_path = self._history_dir / 'events.json'
        self._artifacts_path = self._history_dir / 'artifacts.json'
        self._logs_path = self._history_dir / 'logs.json'
        self._assignments_path = self._history_dir / 'assignments.json'

    def load_into(
        self,
        *,
        case_store: ScenarioCaseStore,
        event_store: OperationalEventStore,
        artifact_store: ArtifactStore,
        log_store: LogStore,
        assignment_store: AssignmentStore,
    ) -> None:
        case_store.replace_all(tuple(self._decode_cases(self._load_list(self._cases_path))))
        event_store.replace_all(tuple(self._decode_events(self._load_list(self._events_path))))
        artifact_store.replace_all(tuple(self._decode_artifacts(self._load_list(self._artifacts_path))))
        log_store.replace_all(tuple(self._decode_logs(self._load_list(self._logs_path))))
        assignment_store.replace_all(tuple(self._decode_assignments(self._load_list(self._assignments_path))))

    def save_from(
        self,
        *,
        case_store: ScenarioCaseStore,
        event_store: OperationalEventStore,
        artifact_store: ArtifactStore,
        log_store: LogStore,
        assignment_store: AssignmentStore,
    ) -> None:
        self._save_list(self._cases_path, [item.to_dict() for item in case_store.all()])
        self._save_list(self._events_path, [item.to_dict() for item in event_store.all()])
        self._save_list(self._artifacts_path, [item.to_dict() for item in artifact_store.all()])
        self._save_list(self._logs_path, [item.to_dict() for item in log_store.all()])
        self._save_list(self._assignments_path, [item.to_dict() for item in assignment_store.all()])

    def _load_list(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]

    def _save_list(self, path: Path, payload: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    @staticmethod
    def _decode_cases(items: list[dict[str, Any]]) -> list[ScenarioRunCase]:
        records: list[ScenarioRunCase] = []
        for item in items:
            try:
                records.append(ScenarioRunCase.from_dict(item))
            except Exception:
                continue
        return records

    @staticmethod
    def _decode_events(items: list[dict[str, Any]]) -> list[OperationalEvent]:
        records: list[OperationalEvent] = []
        for item in items:
            try:
                records.append(OperationalEvent.from_dict(item))
            except Exception:
                continue
        return records

    @staticmethod
    def _decode_artifacts(items: list[dict[str, Any]]) -> list[ArtifactRecord]:
        records: list[ArtifactRecord] = []
        for item in items:
            try:
                records.append(ArtifactRecord.from_dict(item))
            except Exception:
                continue
        return records

    @staticmethod
    def _decode_logs(items: list[dict[str, Any]]) -> list[LogRecord]:
        records: list[LogRecord] = []
        for item in items:
            try:
                records.append(LogRecord.from_dict(item))
            except Exception:
                continue
        return records

    @staticmethod
    def _decode_assignments(items: list[dict[str, Any]]) -> list[AssignmentRecord]:
        records: list[AssignmentRecord] = []
        for item in items:
            try:
                records.append(AssignmentRecord.from_dict(item))
            except Exception:
                continue
        return records
