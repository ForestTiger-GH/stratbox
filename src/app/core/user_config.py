
"""Пользовательский конфиг интерфейса Strategy Box."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.core.errors import AppConfigError


@dataclass(slots=True)
class WindowConfig:
    """Размер главного окна приложения."""

    width: int = 1200
    height: int = 760


@dataclass(slots=True)
class AppUserConfig:
    """Настройки GUI, которые не дублируют launcher bootstrap."""

    last_workspace_schema: str = "default"
    last_task: str = "environment_check"
    window: WindowConfig = field(default_factory=WindowConfig)

    def to_dict(self) -> dict[str, Any]:
        """Преобразует конфиг в JSON-совместимый словарь."""
        return asdict(self)


_DEFAULT_CONFIG = AppUserConfig()


def _coerce_config(data: dict[str, Any]) -> AppUserConfig:
    """Аккуратно приводит словарь к AppUserConfig."""
    window_raw = data.get("window") if isinstance(data.get("window"), dict) else {}
    window = WindowConfig(
        width=int(window_raw.get("width", _DEFAULT_CONFIG.window.width)),
        height=int(window_raw.get("height", _DEFAULT_CONFIG.window.height)),
    )
    return AppUserConfig(
        last_workspace_schema=str(data.get("last_workspace_schema") or _DEFAULT_CONFIG.last_workspace_schema),
        last_task=str(data.get("last_task") or _DEFAULT_CONFIG.last_task),
        window=window,
    )


def load_user_config(path: Path) -> AppUserConfig:
    """Читает пользовательский конфиг, при отсутствии создает дефолтный."""
    if not path.exists():
        save_user_config(path, _DEFAULT_CONFIG)
        return _coerce_config(_DEFAULT_CONFIG.to_dict())

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AppConfigError(f"Failed to read app config: {path}") from exc

    if not isinstance(data, dict):
        raise AppConfigError(f"App config must be a JSON object: {path}")

    return _coerce_config(data)


def save_user_config(path: Path, config: AppUserConfig) -> None:
    """Сохраняет пользовательский конфиг."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
