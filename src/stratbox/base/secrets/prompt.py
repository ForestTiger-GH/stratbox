"""
PromptSecretProvider — интерактивный ввод секрета (getpass) с кэшем.
"""

from __future__ import annotations

import getpass

from stratbox.base.secrets.base import SecretProvider


class PromptSecretProvider(SecretProvider):
    def __init__(self):
        self._cache: dict[str, str] = {}

    def get_secret(self, key: str) -> str | None:
        if key in self._cache:
            return self._cache[key]
        value = getpass.getpass(f"Enter secret for '{key}': ")
        if value is None:
            return None
        value = str(value).strip()
        if value == "":
            return None
        self._cache[key] = value
        return value