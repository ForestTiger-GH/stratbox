"""Контекст приложения Strategy Box."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from stratbox.base.filestore import FileStore

from app.core.log_setup import setup_app_logger
from app.core.paths import AppPaths, build_app_paths
from app.core.user_config import AppUserConfig, load_user_config
from app.core.version import VersionInfo, get_version_info
from app.profiles.filestore import build_filestore_for_profile
from app.profiles.models import DataProfile
from app.profiles.registry import ProfileRegistry, load_profile_registry


@dataclass(slots=True)
class AppContext:
    """Единый объект состояния приложения.

    Он передается в GUI и задачи, чтобы модули не искали пути и настройки самостоятельно.
    """

    paths: AppPaths
    user_config: AppUserConfig
    profiles: ProfileRegistry
    active_profile: DataProfile
    filestore: FileStore
    version: VersionInfo
    logger: logging.Logger


def build_app_context(profile_id: str | None = None) -> AppContext:
    """Собирает контекст приложения для GUI или сервисного запуска."""
    paths = build_app_paths()
    logger = setup_app_logger(paths.logs_dir)
    user_config = load_user_config(paths.app_config_path)
    profiles = load_profile_registry()

    selected_profile_id = profile_id or user_config.active_profile
    if not profiles.has(selected_profile_id):
        logger.warning("Unknown profile '%s'; fallback to local_c", selected_profile_id)
        selected_profile_id = "local_c" if profiles.has("local_c") else profiles.items[0].id

    active_profile = profiles.get(selected_profile_id)
    filestore = build_filestore_for_profile(active_profile)
    version = get_version_info(paths.repo_dir)

    logger.info("App context initialized. Profile=%s Root=%s", active_profile.id, active_profile.root)

    return AppContext(
        paths=paths,
        user_config=user_config,
        profiles=profiles,
        active_profile=active_profile,
        filestore=filestore,
        version=version,
        logger=logger,
    )
