from __future__ import annotations

from .models import LogRecord


class LogStore:
    def __init__(self) -> None:
        self._items: dict[str, LogRecord] = {}

    def add(self, log: LogRecord) -> None:
        self._items[log.log_id] = log

    def all(self) -> tuple[LogRecord, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.created_at, reverse=True))

    def by_case(self, case_id: str) -> tuple[LogRecord, ...]:
        return tuple(item for item in self.all() if item.case_id == case_id)

    def by_path(self, path: str) -> LogRecord | None:
        for item in self._items.values():
            if item.path == path:
                return item
        return None
