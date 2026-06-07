"""Создание FileStore для рабочего каталога приложения."""

from __future__ import annotations

from pathlib import Path

from stratbox.base.filestore import FileStore, LocalFileStore


def build_filestore_for_workspace_root(workspace_root_path: Path) -> FileStore:
    """Создает FileStore для реального рабочего каталога приложения."""
    return LocalFileStore(root=str(workspace_root_path))


def build_filestore_for_data_root(data_root_path: Path) -> FileStore:
    """Совместимая обертка над новым именем функции."""
    return build_filestore_for_workspace_root(data_root_path)
