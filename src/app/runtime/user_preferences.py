from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_UNSET = object()

from app.runtime.context import AppContext
from app.runtime.config import AppUserConfig, save_user_config


@dataclass(slots=True)
class SurfacePreferences:
    user_config: AppUserConfig

    @property
    def width(self) -> int:
        return self.user_config.window.width

    @property
    def height(self) -> int:
        return self.user_config.window.height


class PreferencesService:
    def __init__(self, context: AppContext) -> None:
        self._context = context

    def current(self) -> SurfacePreferences:
        return SurfacePreferences(user_config=self._context.user_config)

    def load_scenario_values(self, scenario_id: str) -> dict[str, Any]:
        return dict(self._context.user_config.scenario_form_values.get(scenario_id) or {})

    def save_scenario_values(self, scenario_id: str, values: dict[str, Any]) -> None:
        self._context.user_config.scenario_form_values[scenario_id] = dict(values)
        self._save()

    def save(
        self,
        *,
        width: int | None = None,
        height: int | None = None,
        last_scenario_id: str | None = None,
        selected_mode: str | None = None,
        filter_mode: str | None = None,
        selected_author_id: str | None | object = _UNSET,
        right_inspector_open: bool | None = None,
        right_inspector_width: int | None = None,
        right_inspector_tab: str | None = None,
    ) -> None:
        config = self._context.user_config
        if width is not None:
            config.window.width = width
        if height is not None:
            config.window.height = height
        if last_scenario_id is not None:
            config.last_scenario_id = last_scenario_id
        if selected_mode is not None:
            config.shell.selected_mode = selected_mode
        if filter_mode is not None:
            config.chat.filter_mode = filter_mode
        if selected_author_id is not _UNSET:
            config.chat.selected_author_id = selected_author_id if isinstance(selected_author_id, str) else None
        if right_inspector_open is not None:
            config.shell.right_inspector_open = right_inspector_open
        if right_inspector_width is not None:
            config.shell.right_inspector_width = right_inspector_width
        if right_inspector_tab is not None:
            config.shell.right_inspector_tab = right_inspector_tab
        self._save()

    def _save(self) -> None:
        save_user_config(self._context.paths.app_config_path, self._context.user_config)
