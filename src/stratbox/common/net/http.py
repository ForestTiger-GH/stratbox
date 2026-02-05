"""
Модуль содержит универсальные HTTP-утилиты.

Требования:
- Возвращать bytes или None (если файл недоступен / слишком мал / статус не 200).
- Поддерживать retries + backoff.
- Не завязываться на macrobanks.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass(frozen=True)
class DownloadResult:
    """
    Результат скачивания.
    """
    ok: bool
    status_code: int | None
    content: bytes | None
    error: str | None = None


def download_bytes(
    url: str,
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
) -> DownloadResult:
    """
    Скачивает bytes по URL.

    Возвращает DownloadResult:
      - ok=True, content=bytes при успехе
      - ok=False, content=None при неуспехе (404/403/timeout/мало байт)

    Логи не пишет — вызывающий код сам решает, что печатать.
    """
    last_err: str | None = None
    last_status: int | None = None

    for attempt in range(retries + 1):
        try:
            r = requests.get(url, timeout=timeout, headers=headers)
            last_status = r.status_code

            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}"
            else:
                b = r.content or b""
                if len(b) < min_bytes_ok:
                    last_err = f"Too small ({len(b)} bytes)"
                else:
                    return DownloadResult(ok=True, status_code=r.status_code, content=b, error=None)

        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"

        if attempt < retries:
            time.sleep(backoff * (attempt + 1))

    return DownloadResult(ok=False, status_code=last_status, content=None, error=last_err)
