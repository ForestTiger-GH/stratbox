from __future__ import annotations

from dataclasses import dataclass

from app.core.context import AppContext
from app.core.user_config import AppUserConfig, save_user_config


@dataclass(slots=True)
class SurfacePreferences:
    user_config: AppUserConfig

    @property
    def width(self) -> int:
        return self.user_config.window.width

    @property
    def height(self) -> int:
        return self.user_config.window.height

    @property
    def splitter_sizes(self) -> list[int]:
        return list(self.user_config.splitter_sizes)


class PreferencesService:
    def __init__(self, context: AppContext) -> None:
        self._context = context

    def current(self) -> SurfacePreferences:
        return SurfacePreferences(user_config=self._context.user_config)

    def save(self, *, width: int | None = None, height: int | None = None, splitter_sizes: list[int] | None = None, last_scenario_id: str | None = None) -> None:
        config = self._context.user_config
        if width is not None:
            config.window.width = width
        if height is not None:
            config.window.height = height
        if splitter_sizes is not None:
            config.splitter_sizes = splitter_sizes
        if last_scenario_id is not None:
            config.last_scenario_id = last_scenario_id
        save_user_config(self._context.paths.app_config_path, config)
