
"""Создание FileStore для текущего business-root."""

from __future__ import annotations

from pathlib import Path

from stratbox.base.filestore import FileStore, LocalFileStore


def build_filestore_for_data_root(data_root_path: Path) -> FileStore:
    """Создает FileStore для текущего business-root."""
    return LocalFileStore(root=str(data_root_path))
