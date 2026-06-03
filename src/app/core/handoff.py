"""AppDock -> app handoff contract."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.errors import AppConfigError


@dataclass(frozen=True, slots=True)
class SourceRevisionRef:
    """Сведения о ревизии подключённого world source."""

    ref_kind: str
    ref: str
    commit: str | None
    sync_mode: str | None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceRevisionRef":
        return cls(
            ref_kind=str(payload.get("ref_kind") or ""),
            ref=str(payload.get("ref") or ""),
            commit=(str(payload["commit"]) if payload.get("commit") else None),
            sync_mode=(str(payload["sync_mode"]) if payload.get("sync_mode") else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class HandoffWorkspace:
    """Рабочий контекст, который shell передаёт приложению."""

    install_root: str
    system_root: str
    source_root: str
    config_root: str
    runtime_root: str
    bundle_root: str
    logs_root: str
    data_root_status: str
    data_root_path: str | None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HandoffWorkspace":
        return cls(
            install_root=str(payload.get("install_root") or ""),
            system_root=str(payload.get("system_root") or ""),
            source_root=str(payload.get("source_root") or ""),
            config_root=str(payload.get("config_root") or ""),
            runtime_root=str(payload.get("runtime_root") or ""),
            bundle_root=str(payload.get("bundle_root") or ""),
            logs_root=str(payload.get("logs_root") or ""),
            data_root_status=str(payload.get("data_root_status") or "unavailable"),
            data_root_path=(str(payload["data_root_path"]) if payload.get("data_root_path") else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class HandoffRefs:
    """Файловые ссылки на publishable state surfaces AppDock."""

    health_snapshot_ref: str | None = None
    user_state_ref: str | None = None
    session_ref: str | None = None
    active_session_ref: str | None = None
    app_state_ref: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HandoffRefs":
        return cls(
            health_snapshot_ref=(str(payload["health_snapshot_ref"]) if payload.get("health_snapshot_ref") else None),
            user_state_ref=(str(payload["user_state_ref"]) if payload.get("user_state_ref") else None),
            session_ref=(str(payload["session_ref"]) if payload.get("session_ref") else None),
            active_session_ref=(str(payload["active_session_ref"]) if payload.get("active_session_ref") else None),
            app_state_ref=(str(payload["app_state_ref"]) if payload.get("app_state_ref") else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AppHandoff:
    """Контракт запуска приложения из AppDock."""

    handoff_contract_version: str
    generated_at_utc: str
    world_id: str
    bundle_id: str
    bundle_profile: str | None
    active_app_surface: str
    entry_view: str
    declared_views: tuple[str, ...]
    attach_mode: str
    degraded_launch: bool
    source_revision: SourceRevisionRef
    workspace: HandoffWorkspace
    refs: HandoffRefs
    node_id: str | None = None
    node_created_at_utc: str | None = None
    user_id: str | None = None
    account_name: str | None = None
    host_name: str | None = None
    session_id: str | None = None
    session_started_at_utc: str | None = None
    available_route_groups: tuple[str, ...] = tuple()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppHandoff":
        source_revision_payload = payload.get("source_revision")
        if not isinstance(source_revision_payload, dict):
            raise AppConfigError("AppDock handoff misses source_revision object")
        workspace_payload = payload.get("workspace")
        if not isinstance(workspace_payload, dict):
            raise AppConfigError("AppDock handoff misses workspace object")
        refs_payload = payload.get("refs")
        if not isinstance(refs_payload, dict):
            raise AppConfigError("AppDock handoff misses refs object")

        declared_views_raw = payload.get("declared_views") or []
        if isinstance(declared_views_raw, str):
            declared_views = (declared_views_raw,) if declared_views_raw.strip() else tuple()
        else:
            declared_views = tuple(str(item) for item in declared_views_raw if str(item).strip())

        route_groups_raw = payload.get("available_route_groups") or []
        if isinstance(route_groups_raw, str):
            available_route_groups = (route_groups_raw,) if route_groups_raw.strip() else tuple()
        else:
            available_route_groups = tuple(str(item) for item in route_groups_raw if str(item).strip())

        return cls(
            handoff_contract_version=str(payload.get("handoff_contract_version") or ""),
            generated_at_utc=str(payload.get("generated_at_utc") or ""),
            world_id=str(payload.get("world_id") or ""),
            bundle_id=str(payload.get("bundle_id") or ""),
            bundle_profile=(str(payload["bundle_profile"]) if payload.get("bundle_profile") else None),
            active_app_surface=str(payload.get("active_app_surface") or ""),
            entry_view=str(payload.get("entry_view") or "overview"),
            declared_views=declared_views,
            attach_mode=str(payload.get("attach_mode") or ""),
            degraded_launch=bool(payload.get("degraded_launch", False)),
            source_revision=SourceRevisionRef.from_dict(source_revision_payload),
            workspace=HandoffWorkspace.from_dict(workspace_payload),
            refs=HandoffRefs.from_dict(refs_payload),
            node_id=(str(payload["node_id"]) if payload.get("node_id") else None),
            node_created_at_utc=(str(payload["node_created_at_utc"]) if payload.get("node_created_at_utc") else None),
            user_id=(str(payload["user_id"]) if payload.get("user_id") else None),
            account_name=(str(payload["account_name"]) if payload.get("account_name") else None),
            host_name=(str(payload["host_name"]) if payload.get("host_name") else None),
            session_id=(str(payload["session_id"]) if payload.get("session_id") else None),
            session_started_at_utc=(str(payload["session_started_at_utc"]) if payload.get("session_started_at_utc") else None),
            available_route_groups=available_route_groups,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_appdock_handoff_path_from_env() -> Path | None:
    """Возвращает путь до handoff-файла из окружения AppDock."""
    value = os.getenv("APPDOCK_HANDOFF_PATH", "").strip()
    return Path(value) if value else None


def get_appdock_config_path_from_env() -> Path | None:
    """Возвращает путь до shell-конфига из окружения AppDock."""
    value = os.getenv("APPDOCK_CONFIG_PATH", "").strip()
    return Path(value) if value else None


def load_appdock_handoff(path: Path) -> AppHandoff:
    """Читает и валидирует handoff-файл AppDock."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AppConfigError(f"Failed to read AppDock handoff: {path}") from exc
    if not isinstance(payload, dict):
        raise AppConfigError(f"AppDock handoff must be a JSON object: {path}")
    handoff = AppHandoff.from_dict(payload)
    if not handoff.world_id:
        raise AppConfigError("AppDock handoff misses world_id")
    if not handoff.active_app_surface:
        raise AppConfigError("AppDock handoff misses active_app_surface")
    if not handoff.workspace.source_root:
        raise AppConfigError("AppDock handoff misses workspace.source_root")
    if not handoff.workspace.install_root:
        raise AppConfigError("AppDock handoff misses workspace.install_root")
    if not handoff.workspace.system_root:
        raise AppConfigError("AppDock handoff misses workspace.system_root")
    return handoff


def load_appdock_handoff_from_env() -> AppHandoff | None:
    """Читает handoff AppDock из переменной окружения, если она задана."""
    path = get_appdock_handoff_path_from_env()
    if path is None or not path.exists():
        return None
    return load_appdock_handoff(path)
