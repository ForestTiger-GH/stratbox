"""Информация о версии и Git-состоянии локального репозитория."""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class VersionInfo:
    """Краткая информация о текущей копии приложения."""

    repo_dir: str
    branch: str = "unknown"
    commit: str = "unknown"
    commit_short: str = "unknown"
    dirty: bool = False
    last_commit_time: str = "unknown"

    def to_dict(self) -> dict[str, object]:
        """Преобразует сведения о версии в словарь."""
        return asdict(self)


def _git(repo_dir: Path, *args: str) -> str:
    """Выполняет git-команду и возвращает stdout."""
    completed = subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    return completed.stdout.strip()


def get_version_info(repo_dir: Path) -> VersionInfo:
    """Возвращает Git-сведения, если Git доступен."""
    try:
        branch = _git(repo_dir, "rev-parse", "--abbrev-ref", "HEAD")
        commit = _git(repo_dir, "rev-parse", "HEAD")
        commit_short = _git(repo_dir, "rev-parse", "--short", "HEAD")
        status = _git(repo_dir, "status", "--porcelain")
        last_commit_time = _git(repo_dir, "log", "-1", "--format=%ci")
        return VersionInfo(
            repo_dir=str(repo_dir),
            branch=branch or "unknown",
            commit=commit or "unknown",
            commit_short=commit_short or "unknown",
            dirty=bool(status),
            last_commit_time=last_commit_time or "unknown",
        )
    except Exception:
        return VersionInfo(repo_dir=str(repo_dir))
