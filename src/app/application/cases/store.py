from __future__ import annotations

from .models import ScenarioRunCase


class ScenarioCaseStore:
    def __init__(self) -> None:
        self._cases: dict[str, ScenarioRunCase] = {}

    def upsert(self, case: ScenarioRunCase) -> None:
        self._cases[case.case_id] = case

    def get(self, case_id: str) -> ScenarioRunCase:
        return self._cases[case_id]

    def all(self) -> tuple[ScenarioRunCase, ...]:
        return tuple(sorted(self._cases.values(), key=lambda item: item.created_at))

    def visible(self, *, mode: str = 'all', author_id: str | None = None) -> tuple[ScenarioRunCase, ...]:
        items = list(self.all())
        if author_id:
            items = [item for item in items if item.author_id == author_id]
        if mode == 'mine':
            items = [item for item in items if item.author_id == author_id]
        elif mode == 'running':
            items = [item for item in items if item.status in {'prepared', 'queued', 'running'}]
        elif mode == 'success':
            items = [item for item in items if item.status in {'success', 'warning'}]
        elif mode == 'errors':
            items = [item for item in items if item.status == 'failed']
        elif mode == 'unread':
            items = [item for item in items if item.unread]
        return tuple(items)
