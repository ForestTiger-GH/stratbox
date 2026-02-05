"""
http — сетевые утилиты stratbox (скачивание bytes).

Ключевая деталь:
- Перед скачиванием URL прогоняется через stratbox.base.net.url.url(),
  чтобы внутри контура (при наличии stratbox_plugin) применялись корпоративные шлюзы
  (например для cbr.ru/vfs).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests

from stratbox.base.net.url import url as normalize_url


@dataclass(frozen=True)
class DownloadResult:
    """
    Результат скачивания.
    """
    ok: bool
    status_code: int | None
    content: bytes | None
    error: str | None = None
    final_url: str | None = None


def download_bytes(
    url: str,
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    headers: dict[str, str] | None = None,
    plugin_only: bool = True,
) -> DownloadResult:
    """
    Скачивает bytes по URL.

    Важно:
    - URL предварительно нормализуется и (внутри контура) переписывается через шлюз,
      используя stratbox.base.net.url.url().
    - Возвращает DownloadResult, без print-логов.

    plugin_only:
      - True: переписывание/шлюз применяется только в plugin-режиме (как принято в stratbox).
    """
    raw = url
    final = None
    try:
        final = normalize_url(raw, plugin_only=plugin_only)
    except Exception:
        final = raw

    last_err: str | None = None
    last_status: int | None = None

    for attempt in range(retries + 1):
        try:
            r = requests.get(final, timeout=timeout, headers=headers)
            last_status = r.status_code

            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}"
            else:
                b = r.content or b""
                if len(b) < min_bytes_ok:
                    last_err = f"Too small ({len(b)} bytes)"
                else:
                    return DownloadResult(
                        ok=True,
                        status_code=r.status_code,
                        content=b,
                        error=None,
                        final_url=final,
                    )

        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"

        if attempt < retries:
            time.sleep(backoff * (attempt + 1))

    return DownloadResult(
        ok=False,
        status_code=last_status,
        content=None,
        error=last_err,
        final_url=final,
    )
