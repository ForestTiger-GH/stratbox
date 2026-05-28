"""Исключения пользовательской оболочки Strategy Box."""

from __future__ import annotations


class AppError(RuntimeError):
    """Базовая ошибка слоя приложения."""


class AppConfigError(AppError):
    """Ошибка чтения или проверки пользовательского конфига."""


class AppProfileError(AppError):
    """Ошибка профиля файловой среды."""


class AppTaskError(AppError):
    """Ошибка регистрации или запуска задачи."""
