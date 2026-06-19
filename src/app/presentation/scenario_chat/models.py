from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ScenarioStepLine:
    title: str
    status: str
    message: str = ''


@dataclass(slots=True)
class ScenarioArtifactLine:
    title: str
    path: str


@dataclass(slots=True)
class ScenarioChatMessage:
    message_id: str
    message_kind: str
    tone: str
    title: str
    summary: str
    status_label: str
    status: str
    author_label: str
    timestamp_label: str
    stage_label: str | None = None
    params_summary: str = ''
    steps: tuple[ScenarioStepLine, ...] = ()
    artifacts: tuple[ScenarioArtifactLine, ...] = ()
    source_case_id: str | None = None
    source_event_id: str | None = None
