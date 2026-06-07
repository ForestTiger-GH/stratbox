from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

FeedKind = Literal['run_submitted', 'run_started', 'run_completed', 'run_failed', 'artifact', 'system_notice']
FeedStatus = Literal['info', 'running', 'success', 'warning', 'error']


@dataclass(slots=True)
class FeedAction:
    id: str
    title: str
    payload: str | None = None


@dataclass(slots=True)
class FeedEntry:
    entry_id: str
    kind: FeedKind
    status: FeedStatus
    title: str
    body: str
    created_at: datetime
    author_id: str | None = None
    author_label: str | None = None
    run_id: str | None = None
    operation_id: str | None = None
    outputs: tuple[str, ...] = tuple()
    tags: tuple[str, ...] = tuple()
    actions: tuple[FeedAction, ...] = tuple()
    meta: dict[str, str] = field(default_factory=dict)

    @property
    def timestamp_label(self) -> str:
        return self.created_at.strftime('%H:%M')
