from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.timeline.models import FeedEntry


@dataclass(slots=True)
class FeedFilterState:
    mode: str = 'all'
    author_id: str | None = None


class FeedStore:
    def __init__(self) -> None:
        self._entries: list[FeedEntry] = []
        self.filter_state = FeedFilterState()

    @property
    def entries(self) -> tuple[FeedEntry, ...]:
        return tuple(self._entries)

    def append(self, entry: FeedEntry) -> None:
        self._entries.append(entry)
        self._entries.sort(key=lambda item: item.created_at)

    def extend(self, entries: Iterable[FeedEntry]) -> None:
        for entry in entries:
            self.append(entry)

    def visible_entries(self) -> tuple[FeedEntry, ...]:
        entries = list(self._entries)
        mode = self.filter_state.mode
        author_id = self.filter_state.author_id
        if author_id:
            entries = [item for item in entries if item.author_id == author_id]
        if mode == 'all':
            return tuple(entries)
        if mode == 'mine':
            entries = [item for item in entries if item.author_id == author_id] if author_id else entries
        elif mode == 'errors':
            entries = [item for item in entries if item.status == 'error']
        elif mode == 'success':
            entries = [item for item in entries if item.status == 'success']
        elif mode == 'running':
            entries = [item for item in entries if item.status == 'running']
        return tuple(entries)

    def set_mode(self, mode: str) -> None:
        self.filter_state.mode = mode

    def set_author(self, author_id: str | None) -> None:
        self.filter_state.author_id = author_id
