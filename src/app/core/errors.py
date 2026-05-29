
"""Исключения пользовательской оболочки Strategy Box."""

from __future__ import annotations


class AppError(RuntimeError):
    """Базовая ошибка слоя приложения."""


class AppConfigError(AppError):
    """Ошибка чтения или проверки пользовательского конфига."""


class AppProfileError(AppError):
    """Ошибка рабочей схемы данных или business-root."""


class AppTaskError(AppError):
    """Ошибка регистрации или запуска задачи."""


class AppStartupError(AppError):
    """Ошибка стартового маршрута приложения."""
