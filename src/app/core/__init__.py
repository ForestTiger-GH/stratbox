
"""Базовые сервисы приложения: контекст, activation-bound runtime и user-space настройки."""

from app.core.context import AppContext, build_app_context

__all__ = ["AppContext", "build_app_context"]
