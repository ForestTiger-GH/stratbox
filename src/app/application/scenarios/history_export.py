from __future__ import annotations

from app.application.artifacts.store import ArtifactStore
from app.application.cases.store import ScenarioCaseStore
from app.application.events.store import OperationalEventStore


def build_ai_history_snapshot(*, case_store: ScenarioCaseStore, event_store: OperationalEventStore, artifact_store: ArtifactStore) -> dict[str, object]:
    return {
        'cases': [
            {
                'case_id': case.case_id,
                'scenario_id': case.scenario_id,
                'scenario_title': case.scenario_title,
                'status': case.status,
                'author': case.author_label,
                'created_at': case.created_at.isoformat(),
                'outputs': list(case.outputs),
            }
            for case in case_store.all()
        ],
        'events': [
            {
                'event_id': event.event_id,
                'kind': event.kind,
                'status': event.status,
                'title': event.title,
                'body': event.body,
                'case_id': event.case_id,
                'created_at': event.created_at.isoformat(),
            }
            for event in event_store.all()
        ],
        'artifacts': [
            {
                'artifact_id': artifact.artifact_id,
                'name': artifact.name,
                'path': artifact.path,
                'kind': artifact.kind,
                'case_id': artifact.case_id,
                'scenario_id': artifact.scenario_id,
                'created_at': artifact.created_at.isoformat(),
            }
            for artifact in artifact_store.all()
        ],
    }
