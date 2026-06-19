from __future__ import annotations

from pathlib import Path


def read_log_tail(path: str, max_lines: int = 300) -> str:
    log_path = Path(path)
    if not log_path.exists():
        return f"Лог не найден: {log_path}"
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as exc:
        return f"Не удалось прочитать лог: {exc}"
    if not lines:
        return "Лог пуст."
    return "\n".join(lines[-max_lines:])
