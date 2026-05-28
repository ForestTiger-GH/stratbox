"""Базовые сервисы приложения: пути, конфиг, контекст, версия."""

from app.core.context import AppContext, build_app_context

__all__ = ["AppContext", "build_app_context"]
