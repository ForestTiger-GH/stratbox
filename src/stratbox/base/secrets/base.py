"""
SecretProvider — универсальный интерфейс для получения секретов.

Вне контура: env/getpass.
Внутри контура: через stratbox-plugin (корпоративный провайдер).
"""

from __future__ import annotations

from typing import Protocol


class SecretProvider(Protocol):
    """Провайдер секретов."""

    def get_secret(self, key: str) -> str | None:
        """Возвращает секрет по ключу или None."""
        ...