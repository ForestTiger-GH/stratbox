from __future__ import annotations

from pathlib import Path

from .models import ArtifactRecord


class ArtifactStore:
    def __init__(self) -> None:
        self._items: dict[str, ArtifactRecord] = {}

    def add(self, artifact: ArtifactRecord) -> None:
        self._items[artifact.artifact_id] = artifact

    def extend(self, artifacts: list[ArtifactRecord] | tuple[ArtifactRecord, ...]) -> None:
        for item in artifacts:
            self.add(item)

    def all(self) -> tuple[ArtifactRecord, ...]:
        return tuple(sorted(self._items.values(), key=lambda item: item.created_at, reverse=True))

    def by_case(self, case_id: str) -> tuple[ArtifactRecord, ...]:
        return tuple(item for item in self.all() if item.case_id == case_id)

    def by_path(self, path: str) -> ArtifactRecord | None:
        try:
            needle = str(Path(path).resolve())
        except Exception:
            needle = str(path)
        for item in self._items.values():
            try:
                current = str(Path(item.path).resolve())
            except Exception:
                current = item.path
            if current == needle:
                return item
        return None
