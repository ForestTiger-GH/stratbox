from __future__ import annotations

from pathlib import Path


def build_primary_output_actions(outputs: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in outputs:
        item = str(value).strip()
        if not item or item in seen:
            continue
        normalized.append(item)
        seen.add(item)
    return tuple(normalized)


def detect_operation_log(outputs: tuple[str, ...]) -> str | None:
    for item in outputs:
        if str(item).endswith('.log'):
            return str(item)
    return None


def output_parent(path: str) -> str:
    return str(Path(path).parent)
