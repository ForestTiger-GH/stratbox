"""Загрузка профилей файловой среды из ресурсов приложения."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files

from app.core.errors import AppProfileError
from app.profiles.models import DataProfile


@dataclass(frozen=True, slots=True)
class ProfileRegistry:
    """Реестр доступных профилей данных."""

    items: tuple[DataProfile, ...]

    def has(self, profile_id: str) -> bool:
        """Проверяет наличие профиля."""
        return any(item.id == profile_id for item in self.items)

    def get(self, profile_id: str) -> DataProfile:
        """Возвращает профиль по id."""
        for item in self.items:
            if item.id == profile_id:
                return item
        raise AppProfileError(f"Unknown profile: {profile_id}")


def load_profile_registry() -> ProfileRegistry:
    """Читает встроенный реестр профилей."""
    try:
        resource = files("app").joinpath("resources", "profiles", "default_profiles.json")
        data = json.loads(resource.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AppProfileError("Failed to load profile registry") from exc

    profiles_raw = data.get("profiles") if isinstance(data, dict) else None
    if not isinstance(profiles_raw, list):
        raise AppProfileError("Profile registry must contain 'profiles' list")

    profiles = tuple(DataProfile.from_dict(item) for item in profiles_raw)
    if not profiles:
        raise AppProfileError("Profile registry is empty")
    return ProfileRegistry(items=profiles)
