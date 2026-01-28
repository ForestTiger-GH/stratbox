"""
EnvSecretProvider — секреты из переменных окружения.
"""

from __future__ import annotations

import os

from stratbox.base.secrets.base import SecretProvider


class EnvSecretProvider(SecretProvider):
    def __init__(self, prefix: str = ""):
        self._prefix = prefix

    def get_secret(self, key: str) -> str | None:
        return os.getenv(f"{self._prefix}{key}")