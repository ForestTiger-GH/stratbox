from __future__ import annotations

from .models import OperationalEvent


class OperationalEventStore:
    def __init__(self) -> None:
        self._events: dict[str, OperationalEvent] = {}

    def add(self, event: OperationalEvent) -> None:
        self._events[event.event_id] = event

    def extend(self, events: tuple[OperationalEvent, ...] | list[OperationalEvent]) -> None:
        for event in events:
            self.add(event)

    def all(self) -> tuple[OperationalEvent, ...]:
        return tuple(sorted(self._events.values(), key=lambda item: item.created_at))

    def recent(self, limit: int = 100) -> tuple[OperationalEvent, ...]:
        return self.all()[-limit:]

    def by_case(self, case_id: str) -> tuple[OperationalEvent, ...]:
        return tuple(event for event in self.all() if event.case_id == case_id)
