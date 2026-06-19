from __future__ import annotations

from .models import AssignmentRecord


class AssignmentStore:
    def __init__(self) -> None:
        self._items: dict[str, AssignmentRecord] = {}

    def add(self, record: AssignmentRecord) -> None:
        self._items[record.assignment_id] = record

    def extend(self, records: tuple[AssignmentRecord, ...] | list[AssignmentRecord]) -> None:
        for record in records:
            self.add(record)

    def replace_all(self, records: tuple[AssignmentRecord, ...] | list[AssignmentRecord]) -> None:
        self._items = {record.assignment_id: record for record in records}

    def get(self, assignment_id: str) -> AssignmentRecord:
        return self._items[assignment_id]

    def all(self) -> tuple[AssignmentRecord, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.created_at, reverse=True))

    def active(self) -> tuple[AssignmentRecord, ...]:
        return tuple(item for item in self.all() if item.status == 'active')

    def completed(self) -> tuple[AssignmentRecord, ...]:
        return tuple(item for item in self.all() if item.status == 'completed')

    def by_participant(self, participant_id: str) -> tuple[AssignmentRecord, ...]:
        return tuple(
            item for item in self.all()
            if item.assignee_id == participant_id or item.author_id == participant_id
        )

    def by_case(self, case_id: str) -> tuple[AssignmentRecord, ...]:
        return tuple(item for item in self.all() if item.case_id == case_id)

    def complete(self, assignment_id: str) -> None:
        self._items[assignment_id].complete()

    def cancel(self, assignment_id: str) -> None:
        self._items[assignment_id].cancel()
