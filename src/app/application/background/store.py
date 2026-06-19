from __future__ import annotations

from .models import BackgroundProcessSpec


class BackgroundProcessStore:
    def __init__(self, items: tuple[BackgroundProcessSpec, ...]):
        self._items = {item.id: item for item in items}
        self._enabled: set[str] = {item.id for item in items if item.enabled_by_default}

    def all(self) -> tuple[BackgroundProcessSpec, ...]:
        return tuple(self._items.values())

    def enabled_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._enabled))

    def is_enabled(self, process_id: str) -> bool:
        return process_id in self._enabled

    def set_enabled(self, process_id: str, enabled: bool) -> None:
        if enabled:
            self._enabled.add(process_id)
        else:
            self._enabled.discard(process_id)
