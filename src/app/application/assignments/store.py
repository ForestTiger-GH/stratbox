from __future__ import annotations

from .models import AssignmentRecord


class AssignmentStore:
    def __init__(self) -> None:
        self._items: dict[str, AssignmentRecord] = {}

    def add(self, record: AssignmentRecord) -> None:
        self._items[record.assignment_id] = record

    def all(self) -> tuple[AssignmentRecord, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.created_at, reverse=True))

    def active(self) -> tuple[AssignmentRecord, ...]:
        return tuple(item for item in self.all() if item.status == 'active')
