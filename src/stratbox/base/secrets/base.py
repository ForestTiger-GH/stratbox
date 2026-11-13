"""Secret lookup for trusted adapters using configured symbolic names."""

from typing import Protocol


class SecretProvider(Protocol):
    def get_secret(self, key: str) -> str | None: ...
