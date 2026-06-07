"""Настройка логирования приложения."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_app_logger(logs_dir: Path) -> logging.Logger:
    """Создаёт основной логгер приложения и перевязывает его на актуальный log path."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("strategy_box_app")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    target_path = (logs_dir / "app.log").resolve()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    existing_file_handlers = [handler for handler in logger.handlers if isinstance(handler, logging.FileHandler)]
    active_paths = {
        Path(getattr(handler, 'baseFilename', '')).resolve()
        for handler in existing_file_handlers
        if getattr(handler, 'baseFilename', None)
    }

    if target_path in active_paths and len(logger.handlers) == len(existing_file_handlers):
        return logger

    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)

    file_handler = logging.FileHandler(target_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
