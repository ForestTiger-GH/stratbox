"""
net — сетевые утилиты stratbox.

Назначение:
- дать единый интерфейс для обработки URL
- работать одинаково и в публичной среде, и внутри контура
"""
from .http import DownloadResult, download_bytes  # noqa: F401
from .url import url  # noqa: F401
