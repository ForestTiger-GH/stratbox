"""Клиент app-facing state surfaces внутри AppDock-managed session."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.app_state import AppStateRecord
from app.core.errors import AppConfigError
from app.core.handoff import AppDockHandoff
from app.workspace import DataRootStatus


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AppConfigError(f"Session surface file not found: {path}") from exc
    except Exception as exc:
        raise AppConfigError(f"Failed to read session surface file: {path}") from exc
    if not isinstance(payload, dict):
        raise AppConfigError(f"Session surface file must be a JSON object: {path}")
    return payload


def _write_json_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@dataclass(frozen=True, slots=True)
class UserStateRecord:
    """Состояние пользователя внутри AppDock node."""

    user_id: str
    account_name: str
    host_name: str
    last_seen_at_utc: str | None = None
    preferred_data_locator: dict[str, Any] | None = None
    last_effective_data_root_path: str | None = None
    last_session_id: str | None = None
    current_session_id: str | None = None
    last_app_target_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UserStateRecord":
        return cls(
            user_id=str(payload.get("user_id") or ""),
            account_name=str(payload.get("account_name") or ""),
            host_name=str(payload.get("host_name") or ""),
            last_seen_at_utc=(str(payload["last_seen_at_utc"]) if payload.get("last_seen_at_utc") else None),
            preferred_data_locator=(payload.get("preferred_data_locator") if isinstance(payload.get("preferred_data_locator"), dict) else None),
            last_effective_data_root_path=(str(payload["last_effective_data_root_path"]) if payload.get("last_effective_data_root_path") else None),
            last_session_id=(str(payload["last_session_id"]) if payload.get("last_session_id") else None),
            current_session_id=(str(payload["current_session_id"]) if payload.get("current_session_id") else None),
            last_app_target_id=(str(payload["last_app_target_id"]) if payload.get("last_app_target_id") else None),
        )


@dataclass(frozen=True, slots=True)
class SessionStateRecord:
    """Session metadata AppDock-managed среды."""

    session_id: str
    user_id: str
    account_name: str
    host_name: str
    node_id: str
    started_at_utc: str
    attach_mode: str
    deployment_profile: str
    status: str
    lifecycle_state: str
    last_updated_at_utc: str
    ended_at_utc: str | None = None
    effective_data_locator: dict[str, Any] | None = None
    effective_data_root_path: str | None = None
    data_root_status: str | None = None
    target_commit: str | None = None
    target_sync_mode: str | None = None
    degraded_launch: bool | None = None
    connector_id: str | None = None
    active_app_target: str | None = None
    entry_surface: str | None = None
    handoff_ref: str | None = None
    app_state_ref: str | None = None
    app_pid: int | None = None
    failure_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def updated(self, **kwargs: Any) -> "SessionStateRecord":
        return replace(self, **kwargs)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionStateRecord":
        attach_mode = payload.get("attach_mode") or payload.get("target_mode") or ""
        deployment_profile = payload.get("deployment_profile") or payload.get("target_deployment_profile") or ""
        return cls(
            session_id=str(payload.get("session_id") or ""),
            user_id=str(payload.get("user_id") or ""),
            account_name=str(payload.get("account_name") or ""),
            host_name=str(payload.get("host_name") or ""),
            node_id=str(payload.get("node_id") or ""),
            started_at_utc=str(payload.get("started_at_utc") or ""),
            attach_mode=str(attach_mode),
            deployment_profile=str(deployment_profile),
            status=str(payload.get("status") or ""),
            lifecycle_state=str(payload.get("lifecycle_state") or ""),
            last_updated_at_utc=str(payload.get("last_updated_at_utc") or payload.get("last_state_change_at_utc") or ""),
            ended_at_utc=(str(payload["ended_at_utc"]) if payload.get("ended_at_utc") else None),
            effective_data_locator=(payload.get("effective_data_locator") if isinstance(payload.get("effective_data_locator"), dict) else None),
            effective_data_root_path=(str(payload["effective_data_root_path"]) if payload.get("effective_data_root_path") else None),
            data_root_status=(str(payload["data_root_status"]) if payload.get("data_root_status") else None),
            target_commit=(str(payload["target_commit"]) if payload.get("target_commit") else None),
            target_sync_mode=(str(payload["target_sync_mode"]) if payload.get("target_sync_mode") else None),
            degraded_launch=(bool(payload["degraded_launch"]) if payload.get("degraded_launch") is not None else None),
            connector_id=(str(payload["connector_id"]) if payload.get("connector_id") else None),
            active_app_target=(str(payload["active_app_target"]) if payload.get("active_app_target") else None),
            entry_surface=(str(payload["entry_surface"]) if payload.get("entry_surface") else None),
            handoff_ref=(str(payload["handoff_ref"]) if payload.get("handoff_ref") else None),
            app_state_ref=(str(payload["app_state_ref"]) if payload.get("app_state_ref") else None),
            app_pid=(int(payload["app_pid"]) if payload.get("app_pid") is not None else None),
            failure_message=(str(payload["failure_message"]) if payload.get("failure_message") else None),
        )


@dataclass(frozen=True, slots=True)
class ActiveSessionProjectionRecord:
    session_id: str
    node_id: str
    user_id: str
    account_name: str
    host_name: str
    started_at_utc: str
    last_state_change_at_utc: str
    lifecycle_state: str
    effective_data_root_path: str | None = None
    data_root_status: str | None = None
    degraded_launch: bool | None = None
    active_app_target: str | None = None
    app_pid: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActiveSessionProjectionRecord":
        return cls(
            session_id=str(payload.get("session_id") or ""),
            node_id=str(payload.get("node_id") or ""),
            user_id=str(payload.get("user_id") or ""),
            account_name=str(payload.get("account_name") or ""),
            host_name=str(payload.get("host_name") or ""),
            started_at_utc=str(payload.get("started_at_utc") or ""),
            last_state_change_at_utc=str(payload.get("last_state_change_at_utc") or ""),
            lifecycle_state=str(payload.get("lifecycle_state") or ""),
            effective_data_root_path=(str(payload["effective_data_root_path"]) if payload.get("effective_data_root_path") else None),
            data_root_status=(str(payload["data_root_status"]) if payload.get("data_root_status") else None),
            degraded_launch=(bool(payload["degraded_launch"]) if payload.get("degraded_launch") is not None else None),
            active_app_target=(str(payload["active_app_target"]) if payload.get("active_app_target") else None),
            app_pid=(int(payload["app_pid"]) if payload.get("app_pid") is not None else None),
        )


@dataclass(frozen=True, slots=True)
class NodeHealthSnapshotRecord:
    recorded_at_utc: str
    node_id: str | None
    user_id: str | None
    session_id: str | None
    overall_status: str
    install_status: str
    install_message: str
    target_status: str
    target_message: str
    runtime_status: str
    runtime_message: str
    venv_status: str
    venv_message: str
    data_status: str
    data_message: str
    degraded_launch: bool
    effective_data_root_path: str | None = None
    target_commit: str | None = None
    target_sync_mode: str | None = None
    connector_id: str | None = None
    active_app_target: str | None = None
    app_status: str | None = None
    pip_tls_mode: str | None = None
    pip_version: str | None = None
    install_error_category: str | None = None
    install_error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NodeHealthSnapshotRecord":
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class AppSessionSnapshot:
    handoff: AppDockHandoff
    session_state: SessionStateRecord | None
    user_state: UserStateRecord | None
    active_session: ActiveSessionProjectionRecord | None
    health_snapshot: NodeHealthSnapshotRecord | None
    app_state: AppStateRecord | None


class AppSessionClient:
    """Клиент работы с app-facing state surfaces AppDock."""

    def __init__(self, handoff: AppDockHandoff) -> None:
        self.handoff = handoff
        self.user_state_path = Path(handoff.refs.user_state_ref).expanduser() if handoff.refs.user_state_ref else None
        self.session_state_path = Path(handoff.refs.session_ref).expanduser() if handoff.refs.session_ref else None
        self.active_session_path = Path(handoff.refs.active_session_ref).expanduser() if handoff.refs.active_session_ref else None
        self.health_snapshot_path = Path(handoff.refs.health_snapshot_ref).expanduser() if handoff.refs.health_snapshot_ref else None
        self.app_state_path = Path(handoff.refs.app_state_ref).expanduser() if handoff.refs.app_state_ref else None

    @property
    def enabled(self) -> bool:
        return self.session_state_path is not None or self.app_state_path is not None

    def load_user_state(self) -> UserStateRecord | None:
        path = self.user_state_path
        if path is None or not path.exists():
            return None
        return UserStateRecord.from_dict(_read_json_object(path))

    def load_session_state(self) -> SessionStateRecord | None:
        path = self.session_state_path
        if path is None or not path.exists():
            return None
        return SessionStateRecord.from_dict(_read_json_object(path))

    def load_active_session(self) -> ActiveSessionProjectionRecord | None:
        path = self.active_session_path
        if path is None or not path.exists():
            return None
        return ActiveSessionProjectionRecord.from_dict(_read_json_object(path))

    def load_health_snapshot(self) -> NodeHealthSnapshotRecord | None:
        path = self.health_snapshot_path
        if path is None or not path.exists():
            return None
        return NodeHealthSnapshotRecord.from_dict(_read_json_object(path))

    def load_app_state(self) -> AppStateRecord | None:
        path = self.app_state_path
        if path is None or not path.exists():
            return None
        return AppStateRecord.from_dict(_read_json_object(path))

    def snapshot(self) -> AppSessionSnapshot:
        return AppSessionSnapshot(
            handoff=self.handoff,
            session_state=self.load_session_state(),
            user_state=self.load_user_state(),
            active_session=self.load_active_session(),
            health_snapshot=self.load_health_snapshot(),
            app_state=self.load_app_state(),
        )

    def _default_app_state(self) -> AppStateRecord:
        now = _utc_now()
        return AppStateRecord(
            app_state_contract_version="1.0",
            app_id=self.handoff.active_app_target,
            updated_at_utc=now,
            heartbeat_utc=now,
            resumable=True,
            clean_shutdown=None,
            active_view=None,
            selected_object=None,
            active_job=None,
            warnings=tuple(),
            workspace_state={},
            state_kind="runtime",
            workspace_schema_id=None,
        )

    def save_app_state(self, state: AppStateRecord) -> AppStateRecord:
        if self.app_state_path is None:
            return state
        _write_json_object(self.app_state_path, state.to_dict())
        return state

    def update_app_state(self, **kwargs: Any) -> AppStateRecord:
        state = self.load_app_state() or self._default_app_state()
        merged = state.updated(updated_at_utc=_utc_now(), heartbeat_utc=_utc_now(), **kwargs)
        return self.save_app_state(merged)

    def mark_running(self, *, active_view: str | None = "overview") -> AppStateRecord:
        return self.update_app_state(clean_shutdown=None, resumable=True, active_view=active_view, state_kind="runtime")

    def mark_ended(self, *, clean_shutdown: bool, active_view: str | None = "closed", warning: str | None = None) -> AppStateRecord | None:
        warnings: tuple[str, ...] = (warning,) if warning else tuple()
        return self.update_app_state(clean_shutdown=clean_shutdown, active_view=active_view, warnings=warnings, state_kind="shutdown")

    def update_workspace_selector(self, *, data_locator: dict[str, Any], selector_path: Path | None, data_root_status: DataRootStatus) -> AppSessionSnapshot:
        workspace_state = {
            "selected_data_locator": dict(data_locator),
            "selected_data_root_path": (str(selector_path) if selector_path else None),
            "selected_data_root_status": "available" if data_root_status.available else "unavailable",
            "selected_data_root_message": data_root_status.message,
        }
        self.update_app_state(
            workspace_state=workspace_state,
            selected_data_root_path=(str(selector_path) if selector_path else None),
            state_kind="runtime",
        )
        return self.snapshot()
