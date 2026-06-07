"""Пользовательский конфиг интерфейса Strategy Box."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.core.errors import AppConfigError


@dataclass(slots=True)
class WindowConfig:
    width: int = 1200
    height: int = 760


@dataclass(slots=True)
class AppUserConfig:
    last_workspace_schema: str = 'default'
    last_operation_id: str = 'cbr_file_collector.collect'
    splitter_sizes: list[int] = field(default_factory=lambda: [420, 900])
    environment_panel_expanded: bool = True
    window: WindowConfig = field(default_factory=WindowConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_DEFAULT_CONFIG = AppUserConfig()


def _coerce_config(data: dict[str, Any]) -> AppUserConfig:
    window_raw = data.get('window') if isinstance(data.get('window'), dict) else {}
    window = WindowConfig(
        width=int(window_raw.get('width', _DEFAULT_CONFIG.window.width)),
        height=int(window_raw.get('height', _DEFAULT_CONFIG.window.height)),
    )
    splitter_sizes_raw = data.get('splitter_sizes') if isinstance(data.get('splitter_sizes'), list) else _DEFAULT_CONFIG.splitter_sizes
    splitter_sizes = [int(x) for x in splitter_sizes_raw if isinstance(x, (int, float, str)) and str(x).strip()]
    if not splitter_sizes:
        splitter_sizes = list(_DEFAULT_CONFIG.splitter_sizes)
    last_operation_id = str(
        data.get('last_operation_id') or data.get('last_scenario_id') or _DEFAULT_CONFIG.last_operation_id
    )
    return AppUserConfig(
        last_workspace_schema=str(data.get('last_workspace_schema') or _DEFAULT_CONFIG.last_workspace_schema),
        last_operation_id=last_operation_id,
        splitter_sizes=splitter_sizes,
        environment_panel_expanded=bool(data.get('environment_panel_expanded', _DEFAULT_CONFIG.environment_panel_expanded)),
        window=window,
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
