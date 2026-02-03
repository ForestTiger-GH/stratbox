"""
url — единая точка нормализации/переписывания URL.

Задача:
- Внутри контура: использовать логику плагина (шлюзы, переписывание cbr.ru/vfs -> gateway)
- Вне контура: работать без плагина и не падать (минимальная нормализация)
"""

from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit, urlunsplit


def url(raw: str, *, plugin_only: bool = True) -> str:
    """
    Нормализует URL и (если доступен плагин) применяет корпоративные шлюзы.

    Параметры:
    - plugin_only=True: переписывание (шлюз) делается только в plugin-режиме
      (аналогично поведению плагина).
    """
    if raw is None:
        return raw
    s = str(raw).strip()
    if not s:
        return s

    # 1) Пробует отдать обработку плагину, если он доступен
    try:
        from stratbox_plugin.utils.url import url as plugin_url  # type: ignore

        return plugin_url(s, plugin_only=plugin_only)
    except Exception:
        # 2) Если плагина нет — делает мягкую нормализацию и возвращает как есть
        s = s.replace("\\", "/")
        try:
            s = unquote(s)
        except Exception:
            pass

        # поддержка "голых" доменов без схемы: "cbr.ru/VFS/..."
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", s):
            if re.match(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/|$)", s):
                s = "https://" + s

        # на всякий случай нормализует двойные слеши в path (не трогая 'https://')
        parts = urlsplit(s)
        path = re.sub(r"/{2,}", "/", parts.path or "")
        return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
