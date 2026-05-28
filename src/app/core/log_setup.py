"""Настройка логирования приложения."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_app_logger(logs_dir: Path) -> logging.Logger:
    """Создает основной логгер приложения."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("strategy_box_app")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Повторная настройка не должна плодить обработчики при тестах и перезапуске GUI.
    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(logs_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
