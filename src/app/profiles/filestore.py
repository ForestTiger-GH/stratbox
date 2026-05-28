"""Создание FileStore на основе выбранного профиля."""

from __future__ import annotations

from stratbox.base.filestore import FileStore, LocalFileStore

from app.core.errors import AppProfileError
from app.profiles.models import DataProfile


def build_filestore_for_profile(profile: DataProfile) -> FileStore:
    """Создает FileStore для активного профиля."""
    # На первом этапе NetDrive считается обычным локальным диском.
    if profile.kind == "local":
        return LocalFileStore(root=profile.resolved_root)
    raise AppProfileError(f"Unsupported profile kind: {profile.kind}")
