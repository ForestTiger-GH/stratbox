"""
runtime — единственная точка, где определяется:
- установлен stratbox-plugin или нет
- какие провайдеры использовать (filestore/secrets)

Доменный код не должен импортировать stratbox-plugin напрямую.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from importlib.metadata import entry_points

from stratbox.base.filestore import FileStore, LocalFileStore
from stratbox.base.secrets import EnvSecretProvider, PromptSecretProvider, SecretProvider


@dataclass(frozen=True)
class Providers:
    filestore: FileStore
    secrets: SecretProvider
    source: str  # "plugin" | "local"


_PROVIDERS: Providers | None = None


def _load_plugin_providers() -> Providers | None:
    """Пытается загрузить провайдеры из stratbox-plugin через entry-points."""
    try:
        eps = entry_points().select(group="stratbox.plugin", name="providers")
        loaded_any = False
        for ep in eps:
            loaded_any = True
            factory = ep.load()
            result = factory()
            # 1) Новый формат: dict{"filestore": ..., "secrets": ...}
            if isinstance(result, dict):
                # поддержка возможных синонимов ключей (на случай старых версий плагина)
                fs = result.get("filestore") or result.get("store") or result.get("file_store")
                sec = result.get("secrets") or result.get("secret_provider")
                if fs is not None and sec is not None:
                    return Providers(filestore=fs, secrets=sec, source="plugin")

            # 2) Альтернативный формат: сразу Providers
            if isinstance(result, Providers):
                return Providers(
                    filestore=result.filestore,
                    secrets=result.secrets,
                    source="plugin",
                )

        if loaded_any:
            # entry-point существует, но формат ответа не распознан
            print(
                "WARN: Plugin entrypoint найден, но providers не распознаны; "
                "ожидается dict с ключами filestore/secrets"
            )
    except Exception as e:
        # Плагин может отсутствовать или быть не установлен в среде.
        # В этом случае stratbox обязан перейти на local-режим.
        if os.getenv("STRATBOX_DEBUG_PLUGIN", "0") in ("1", "true", "True"):
            import traceback
            print("ERROR: Failed to load plugin providers:", repr(e))
            traceback.print_exc()
        else:
            # Без подробного трейсбэка, но с понятным сигналом.
            # Пользователь сможет включить подробности, не переписывая код.
            print("WARN: Plugin providers load failed; set STRATBOX_DEBUG_PLUGIN=1 to see details")
        return None
    return None


def _build_local_providers() -> Providers:
    """Локальные провайдеры (fallback вне контура)."""
    root = os.getenv("STRATBOX_LOCAL_ROOT")  # опционально: базовый каталог для относительных путей
    filestore = LocalFileStore(root=root)

    envp = EnvSecretProvider(prefix="STRATBOX_")
    prompt = PromptSecretProvider()

    class _ChainedSecrets(SecretProvider):
        def get_secret(self, key: str) -> str | None:
            v = envp.get_secret(key)
            if v is not None:
                return v
            return prompt.get_secret(key)

    return Providers(filestore=filestore, secrets=_ChainedSecrets(), source="local")


def get_providers(force_reload: bool = False) -> Providers:
    """Возвращает активные провайдеры. Кэшируется на время процесса."""
    global _PROVIDERS
    if _PROVIDERS is not None and not force_reload:
        # Если закэширован local, но плагин включён — пробуем переподхватить один раз
        if _PROVIDERS.source == "local" and os.getenv("STRATBOX_USE_PLUGIN", "1").strip() not in ("0", "false", "False"):
            plugin_providers = _load_plugin_providers()
            if plugin_providers is not None:
                _PROVIDERS = plugin_providers
                print("INFO: Providers loaded from plugin")
                return _PROVIDERS
        return _PROVIDERS

    use_plugin = os.getenv("STRATBOX_USE_PLUGIN", "1").strip() not in ("0", "false", "False")
    if use_plugin:
        plugin_providers = _load_plugin_providers()
        if plugin_providers is not None:
            _PROVIDERS = plugin_providers
            print("INFO: Providers loaded from plugin")
            return _PROVIDERS

    _PROVIDERS = _build_local_providers()
    print("INFO: Providers loaded from local")
    return _PROVIDERS


def get_filestore() -> FileStore:
    return get_providers().filestore


def get_secrets() -> SecretProvider:
    return get_providers().secrets