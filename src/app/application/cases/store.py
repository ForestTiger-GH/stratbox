from __future__ import annotations

from .models import ScenarioRunCase


class ScenarioCaseStore:
    def __init__(self) -> None:
        self._cases: dict[str, ScenarioRunCase] = {}

    def upsert(self, case: ScenarioRunCase) -> None:
        self._cases[case.case_id] = case

    def replace_all(self, cases: tuple[ScenarioRunCase, ...] | list[ScenarioRunCase]) -> None:
        self._cases = {case.case_id: case for case in cases}

    def get(self, case_id: str) -> ScenarioRunCase:
        return self._cases[case_id]

    def has(self, case_id: str) -> bool:
        return case_id in self._cases

    def all(self) -> tuple[ScenarioRunCase, ...]:
        return tuple(sorted(self._cases.values(), key=lambda item: item.created_at))

    def recent(self, limit: int = 100) -> tuple[ScenarioRunCase, ...]:
        return self.all()[-limit:]

    def visible(self, *, mode: str = 'all', author_id: str | None = None) -> tuple[ScenarioRunCase, ...]:
        items = list(self.all())
        if mode == 'mine':
            items = [item for item in items if author_id and item.author_id == author_id]
        elif author_id:
            items = [item for item in items if item.author_id == author_id]
        if mode == 'running':
            items = [item for item in items if item.status in {'prepared', 'queued', 'running'}]
        elif mode == 'success':
            items = [item for item in items if item.status in {'success', 'warning'}]
        elif mode == 'errors':
            items = [item for item in items if item.status == 'failed']
        elif mode == 'unread':
            items = [item for item in items if item.unread]
        return tuple(items)
