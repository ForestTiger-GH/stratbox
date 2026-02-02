"""
optional_deps — ленивые (опциональные) зависимости.

Задача:
- не импортировать тяжёлые библиотеки заранее
- не делать pip install, пока формат реально не используется

Политика:
- по умолчанию (STRATBOX_AUTO_PIP=0) — только понятная ошибка
- при STRATBOX_AUTO_PIP=1 — пробует поставить пакет через pip и импортировать
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from typing import Any


def _auto_pip_enabled(auto_install: bool | None = None) -> bool:
    """
    Определяет, разрешена ли автозагрузка pip.

    Приоритет:
    1) параметр auto_install (если задан)
    2) переменная окружения STRATBOX_AUTO_PIP=1
    """
    if auto_install is not None:
        return bool(auto_install)
    return os.getenv("STRATBOX_AUTO_PIP", "0").strip() in ("1", "true", "True", "yes", "YES")


def _pip_install(requirement: str) -> None:
    """
    Ставит пакет через pip.

    В Jupyter старается использовать магию %pip (чтобы установка шла в текущее окружение),
    иначе — subprocess.
    """
    # Пытается использовать IPython %pip, если доступно
    try:
        from IPython import get_ipython  # type: ignore

        ip = get_ipython()
        if ip is not None:
            # Важно: именно line_magic pip — это ближе всего к "!pip install ..."
            ip.run_line_magic("pip", f"install {requirement}")
            return
    except Exception:
        pass

    # Fallback: обычный pip
    subprocess.check_call([sys.executable, "-m", "pip", "install", requirement])


def ensure_import(
    module: str,
    pip_requirement: str | None = None,
    *,
    auto_install: bool | None = None,
    hint: str | None = None,
) -> Any:
    """
    Гарантирует импорт модуля.

    Если модуля нет:
    - при STRATBOX_AUTO_PIP=1 (или auto_install=True) попробует поставить pip_requirement
    - иначе поднимет ImportError с подсказкой
    """
    try:
        return importlib.import_module(module)
    except Exception as e:
        req = pip_requirement or module

        if _auto_pip_enabled(auto_install=auto_install):
            _pip_install(req)
            return importlib.import_module(module)

        msg = f"Optional dependency is missing: '{module}'. Install: pip install {req}"
        if hint:
            msg += f"\nHint: {hint}"
        raise ImportError(msg) from e