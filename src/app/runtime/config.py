"""Пользовательский конфиг интерфейса Strategy Box."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.runtime.errors import AppConfigError


@dataclass(slots=True)
class WindowConfig:
    width: int = 1440
    height: int = 860


@dataclass(slots=True)
class ShellLayoutConfig:
    selected_mode: str = 'workspace'
    left_panel_width: int = 344
    right_inspector_open: bool = True
    right_inspector_width: int = 408
    right_inspector_tab: str = 'case'


@dataclass(slots=True)
class ChatConfig:
    filter_mode: str = 'all'
    selected_author_id: str | None = None


@dataclass(slots=True)
class AppUserConfig:
    last_workspace_schema: str = 'default'
    last_scenario_id: str = 'scenario.atomic.cbr_file_collector.collect'
    scenario_form_values: dict[str, dict[str, Any]] = field(default_factory=dict)
    window: WindowConfig = field(default_factory=WindowConfig)
    shell: ShellLayoutConfig = field(default_factory=ShellLayoutConfig)
    chat: ChatConfig = field(default_factory=ChatConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_DEFAULT_CONFIG = AppUserConfig()


def _coerce_config(data: dict[str, Any]) -> AppUserConfig:
    window_raw = data.get('window') if isinstance(data.get('window'), dict) else {}
    shell_raw = data.get('shell') if isinstance(data.get('shell'), dict) else {}
    chat_raw = data.get('chat') if isinstance(data.get('chat'), dict) else {}
    window = WindowConfig(
        width=int(window_raw.get('width', _DEFAULT_CONFIG.window.width)),
        height=int(window_raw.get('height', _DEFAULT_CONFIG.window.height)),
    )
    shell = ShellLayoutConfig(
        selected_mode=str(shell_raw.get('selected_mode') or _DEFAULT_CONFIG.shell.selected_mode),
        left_panel_width=int(shell_raw.get('left_panel_width', _DEFAULT_CONFIG.shell.left_panel_width)),
        right_inspector_open=bool(shell_raw.get('right_inspector_open', _DEFAULT_CONFIG.shell.right_inspector_open)),
        right_inspector_width=int(shell_raw.get('right_inspector_width', _DEFAULT_CONFIG.shell.right_inspector_width)),
        right_inspector_tab=str(shell_raw.get('right_inspector_tab') or _DEFAULT_CONFIG.shell.right_inspector_tab),
    )
    chat = ChatConfig(
        filter_mode=str(chat_raw.get('filter_mode') or _DEFAULT_CONFIG.chat.filter_mode),
        selected_author_id=(str(chat_raw.get('selected_author_id')) if chat_raw.get('selected_author_id') else None),
    )
    raw_values = data.get('scenario_form_values')
    if not isinstance(raw_values, dict):
        raw_values = data.get('operation_form_values') if isinstance(data.get('operation_form_values'), dict) else {}
    scenario_form_values: dict[str, dict[str, Any]] = {}
    for scenario_id, values in raw_values.items():
        if isinstance(values, dict):
            key = str(scenario_id)
            if not key.startswith('scenario.'):
                key = f'scenario.atomic.{key}'
            scenario_form_values[key] = dict(values)
    last_scenario_id = data.get('last_scenario_id') or data.get('last_operation_id') or _DEFAULT_CONFIG.last_scenario_id
    last_scenario_id = str(last_scenario_id)
    if not last_scenario_id.startswith('scenario.'):
        last_scenario_id = f'scenario.atomic.{last_scenario_id}'
    return AppUserConfig(
        last_workspace_schema=str(data.get('last_workspace_schema') or _DEFAULT_CONFIG.last_workspace_schema),
        last_scenario_id=last_scenario_id,
        scenario_form_values=scenario_form_values,
        window=window,
        shell=shell,
        chat=chat,
    )


def load_user_config(path: Path) -> AppUserConfig:
    if not path.exists():
        save_user_config(path, _DEFAULT_CONFIG)
        return _coerce_config(_DEFAULT_CONFIG.to_dict())
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise AppConfigError(f'Failed to read app config: {path}') from exc
    if not isinstance(data, dict):
        raise AppConfigError(f'App config must be a JSON object: {path}')
    return _coerce_config(data)


def save_user_config(path: Path, config: AppUserConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
