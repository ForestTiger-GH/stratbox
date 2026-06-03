"""Клиент app-facing state surfaces внутри AppDock-managed session."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.app_state import AppStateRecord
from app.core.errors import AppConfigError
from app.core.handoff import AppHandoff
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
    last_effective_data_root_path: str | None = None
    last_session_id: str | None = None
    current_session_id: str | None = None
    last_app_surface_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UserStateRecord":
        return cls(
            user_id=str(payload.get("user_id") or ""),
            account_name=str(payload.get("account_name") or ""),
            host_name=str(payload.get("host_name") or ""),
            last_seen_at_utc=(str(payload["last_seen_at_utc"]) if payload.get("last_seen_at_utc") else None),
            last_effective_data_root_path=(str(payload["last_effective_data_root_path"]) if payload.get("last_effective_data_root_path") else None),
            last_session_id=(str(payload["last_session_id"]) if payload.get("last_session_id") else None),
            current_session_id=(str(payload["current_session_id"]) if payload.get("current_session_id") else None),
            last_app_surface_id=(str(payload["last_app_surface_id"]) if payload.get("last_app_surface_id") else None),
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
    status: str
    lifecycle_state: str
    last_updated_at_utc: str
    ended_at_utc: str | None = None
    effective_data_root_path: str | None = None
    data_root_status: str | None = None
    source_commit: str | None = None
    source_sync_mode: str | None = None
    degraded_launch: bool | None = None
    world_id: str | None = None
    active_app_surface: str | None = None
    entry_view: str | None = None
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
        lifecycle_state = str(payload.get("lifecycle_state") or "")
        status = str(payload.get("status") or "")
        if not lifecycle_state:
            lifecycle_state = 'ended' if payload.get('ended_at_utc') else 'created'
        if not status:
            status = lifecycle_state
        return cls(
            session_id=str(payload.get("session_id") or ""),
            user_id=str(payload.get("user_id") or ""),
            account_name=str(payload.get("account_name") or ""),
            host_name=str(payload.get("host_name") or ""),
            node_id=str(payload.get("node_id") or ""),
            started_at_utc=str(payload.get("started_at_utc") or ""),
            attach_mode=str(payload.get("attach_mode") or ""),
            status=status,
            lifecycle_state=lifecycle_state,
            last_updated_at_utc=str(payload.get("last_updated_at_utc") or payload.get("started_at_utc") or ""),
            ended_at_utc=(str(payload["ended_at_utc"]) if payload.get("ended_at_utc") else None),
            effective_data_root_path=(str(payload["effective_data_root_path"]) if payload.get("effective_data_root_path") else None),
            data_root_status=(str(payload["data_root_status"]) if payload.get("data_root_status") else None),
            source_commit=(str(payload["source_commit"]) if payload.get("source_commit") else None),
            source_sync_mode=(str(payload["source_sync_mode"]) if payload.get("source_sync_mode") else None),
            degraded_launch=(bool(payload["degraded_launch"]) if payload.get("degraded_launch") is not None else None),
            world_id=(str(payload["world_id"]) if payload.get("world_id") else None),
            active_app_surface=(str(payload["active_app_surface"]) if payload.get("active_app_surface") else None),
            entry_view=(str(payload["entry_view"]) if payload.get("entry_view") else None),
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
    active_app_surface: str | None = None
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
            active_app_surface=(str(payload["active_app_surface"]) if payload.get("active_app_surface") else None),
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
    source_status: str
    source_message: str
    runtime_status: str
    runtime_message: str
    venv_status: str
    venv_message: str
    data_status: str
    data_message: str
    degraded_launch: bool
    effective_data_root_path: str | None = None
    source_commit: str | None = None
    source_sync_mode: str | None = None
    world_id: str | None = None
    active_app_surface: str | None = None
    app_status: str | None = None
    pip_tls_mode: str | None = None
    pip_version: str | None = None
    install_error_category: str | None = None
    install_error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NodeHealthSnapshotRecord":
        return cls(
            recorded_at_utc=str(payload.get("recorded_at_utc") or ""),
            node_id=payload.get("node_id"),
            user_id=payload.get("user_id"),
            session_id=payload.get("session_id"),
            overall_status=str(payload.get("overall_status") or ""),
            install_status=str(payload.get("install_status") or ""),
            install_message=str(payload.get("install_message") or ""),
            source_status=str(payload.get("source_status") or ""),
            source_message=str(payload.get("source_message") or ""),
            runtime_status=str(payload.get("runtime_status") or ""),
            runtime_message=str(payload.get("runtime_message") or ""),
            venv_status=str(payload.get("venv_status") or ""),
            venv_message=str(payload.get("venv_message") or ""),
            data_status=str(payload.get("data_status") or ""),
            data_message=str(payload.get("data_message") or ""),
            degraded_launch=bool(payload.get("degraded_launch", False)),
            effective_data_root_path=payload.get("effective_data_root_path"),
            source_commit=payload.get("source_commit"),
            source_sync_mode=payload.get("source_sync_mode"),
            world_id=payload.get("world_id"),
            active_app_surface=payload.get("active_app_surface"),
            app_status=payload.get("app_status"),
            pip_tls_mode=payload.get("pip_tls_mode"),
            pip_version=payload.get("pip_version"),
            install_error_category=payload.get("install_error_category"),
            install_error_message=payload.get("install_error_message"),
        )


@dataclass(frozen=True, slots=True)
class AppSessionSnapshot:
    handoff: AppHandoff
    session_state: SessionStateRecord | None
    user_state: UserStateRecord | None
    active_session: ActiveSessionProjectionRecord | None
    health_snapshot: NodeHealthSnapshotRecord | None
    app_state: AppStateRecord | None


class AppSessionClient:
    """Клиент работы с app-facing state surfaces AppDock."""

    def __init__(self, handoff: AppHandoff) -> None:
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
            surface_id=self.handoff.active_app_surface,
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

    def update_workspace_selector(self, *, selector_path: Path | None, data_root_status: DataRootStatus) -> AppSessionSnapshot:
        workspace_state = {
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
