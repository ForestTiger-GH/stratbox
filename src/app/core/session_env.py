"""Клиент launcher-managed session environment."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.errors import AppConfigError
from app.core.handoff import LauncherHandoff
from app.workspace import DataRootStatus


def _utc_now() -> str:
    """Возвращает текущее UTC-время в ISO-формате."""
    return datetime.now(timezone.utc).isoformat()


def _read_json_object(path: Path) -> dict[str, Any]:
    """Читает JSON-объект из файла или бросает понятную ошибку."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AppConfigError(f"Session environment file not found: {path}") from exc
    except Exception as exc:
        raise AppConfigError(f"Failed to read session environment file: {path}") from exc
    if not isinstance(payload, dict):
        raise AppConfigError(f"Session environment file must be a JSON object: {path}")
    return payload


def _write_json_object(path: Path, payload: dict[str, Any]) -> None:
    """Сохраняет JSON-объект в файл."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@dataclass(frozen=True, slots=True)
class UserStateRecord:
    """Состояние пользователя внутри launcher-managed install-среды."""

    user_id: str
    account_name: str
    host_name: str
    last_seen_at_utc: str | None = None
    preferred_data_locator: dict[str, Any] | None = None
    last_effective_data_root_path: str | None = None
    last_session_id: str | None = None
    current_session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def updated(self, **kwargs: Any) -> "UserStateRecord":
        return replace(self, **kwargs)

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
        )


@dataclass(frozen=True, slots=True)
class SessionStateRecord:
    """Session metadata launcher-managed среды."""

    session_id: str
    user_id: str
    account_name: str
    host_name: str
    system_id: str
    started_at_utc: str
    launcher_mode: str
    install_profile: str
    status: str
    lifecycle_state: str
    last_updated_at_utc: str
    ended_at_utc: str | None = None
    effective_data_locator: dict[str, Any] | None = None
    effective_data_root_path: str | None = None
    data_root_status: str | None = None
    trusted_repo_commit: str | None = None
    repo_sync_mode: str | None = None
    degraded_launch: bool | None = None
    handoff_path: str | None = None
    app_pid: int | None = None
    failure_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def updated(self, **kwargs: Any) -> "SessionStateRecord":
        return replace(self, **kwargs)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionStateRecord":
        return cls(
            session_id=str(payload.get("session_id") or ""),
            user_id=str(payload.get("user_id") or ""),
            account_name=str(payload.get("account_name") or ""),
            host_name=str(payload.get("host_name") or ""),
            system_id=str(payload.get("system_id") or ""),
            started_at_utc=str(payload.get("started_at_utc") or ""),
            launcher_mode=str(payload.get("launcher_mode") or ""),
            install_profile=str(payload.get("install_profile") or ""),
            status=str(payload.get("status") or ""),
            lifecycle_state=str(payload.get("lifecycle_state") or ""),
            last_updated_at_utc=str(payload.get("last_updated_at_utc") or payload.get("started_at_utc") or ""),
            ended_at_utc=(str(payload["ended_at_utc"]) if payload.get("ended_at_utc") else None),
            effective_data_locator=(payload.get("effective_data_locator") if isinstance(payload.get("effective_data_locator"), dict) else None),
            effective_data_root_path=(str(payload["effective_data_root_path"]) if payload.get("effective_data_root_path") else None),
            data_root_status=(str(payload["data_root_status"]) if payload.get("data_root_status") else None),
            trusted_repo_commit=(str(payload["trusted_repo_commit"]) if payload.get("trusted_repo_commit") else None),
            repo_sync_mode=(str(payload["repo_sync_mode"]) if payload.get("repo_sync_mode") else None),
            degraded_launch=(bool(payload["degraded_launch"]) if payload.get("degraded_launch") is not None else None),
            handoff_path=(str(payload["handoff_path"]) if payload.get("handoff_path") else None),
            app_pid=(int(payload["app_pid"]) if payload.get("app_pid") is not None else None),
            failure_message=(str(payload["failure_message"]) if payload.get("failure_message") else None),
        )


@dataclass(frozen=True, slots=True)
class ActiveSessionProjectionRecord:
    """Короткая shared-проекция активной session."""

    session_id: str
    system_id: str
    user_id: str
    account_name: str
    host_name: str
    started_at_utc: str
    last_state_change_at_utc: str
    lifecycle_state: str
    effective_data_root_path: str | None = None
    data_root_status: str | None = None
    degraded_launch: bool | None = None
    app_pid: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActiveSessionProjectionRecord":
        return cls(
            session_id=str(payload.get("session_id") or ""),
            system_id=str(payload.get("system_id") or ""),
            user_id=str(payload.get("user_id") or ""),
            account_name=str(payload.get("account_name") or ""),
            host_name=str(payload.get("host_name") or ""),
            started_at_utc=str(payload.get("started_at_utc") or ""),
            last_state_change_at_utc=str(payload.get("last_state_change_at_utc") or ""),
            lifecycle_state=str(payload.get("lifecycle_state") or ""),
            effective_data_root_path=(str(payload["effective_data_root_path"]) if payload.get("effective_data_root_path") else None),
            data_root_status=(str(payload["data_root_status"]) if payload.get("data_root_status") else None),
            degraded_launch=(bool(payload["degraded_launch"]) if payload.get("degraded_launch") is not None else None),
            app_pid=(int(payload["app_pid"]) if payload.get("app_pid") is not None else None),
        )

    @classmethod
    def from_session(cls, session: SessionStateRecord) -> "ActiveSessionProjectionRecord":
        return cls(
            session_id=session.session_id,
            system_id=session.system_id,
            user_id=session.user_id,
            account_name=session.account_name,
            host_name=session.host_name,
            started_at_utc=session.started_at_utc,
            last_state_change_at_utc=session.last_updated_at_utc,
            lifecycle_state=session.lifecycle_state,
            effective_data_root_path=session.effective_data_root_path,
            data_root_status=session.data_root_status,
            degraded_launch=session.degraded_launch,
            app_pid=session.app_pid,
        )


@dataclass(frozen=True, slots=True)
class EnvironmentHealthSnapshotRecord:
    """Snapshot здоровья launcher-managed среды."""

    recorded_at_utc: str
    system_id: str | None
    user_id: str | None
    session_id: str | None
    overall_status: str
    install_status: str
    install_message: str
    repo_status: str
    repo_message: str
    runtime_status: str
    runtime_message: str
    venv_status: str
    venv_message: str
    data_status: str
    data_message: str
    degraded_launch: bool
    effective_data_root_path: str | None = None
    trusted_repo_commit: str | None = None
    repo_sync_mode: str | None = None
    app_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def updated(self, **kwargs: Any) -> "EnvironmentHealthSnapshotRecord":
        return replace(self, **kwargs)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EnvironmentHealthSnapshotRecord":
        return cls(
            recorded_at_utc=str(payload.get("recorded_at_utc") or ""),
            system_id=(str(payload["system_id"]) if payload.get("system_id") else None),
            user_id=(str(payload["user_id"]) if payload.get("user_id") else None),
            session_id=(str(payload["session_id"]) if payload.get("session_id") else None),
            overall_status=str(payload.get("overall_status") or "UNKNOWN"),
            install_status=str(payload.get("install_status") or "UNKNOWN"),
            install_message=str(payload.get("install_message") or ""),
            repo_status=str(payload.get("repo_status") or "UNKNOWN"),
            repo_message=str(payload.get("repo_message") or ""),
            runtime_status=str(payload.get("runtime_status") or "UNKNOWN"),
            runtime_message=str(payload.get("runtime_message") or ""),
            venv_status=str(payload.get("venv_status") or "UNKNOWN"),
            venv_message=str(payload.get("venv_message") or ""),
            data_status=str(payload.get("data_status") or "UNKNOWN"),
            data_message=str(payload.get("data_message") or ""),
            degraded_launch=bool(payload.get("degraded_launch", False)),
            effective_data_root_path=(str(payload["effective_data_root_path"]) if payload.get("effective_data_root_path") else None),
            trusted_repo_commit=(str(payload["trusted_repo_commit"]) if payload.get("trusted_repo_commit") else None),
            repo_sync_mode=(str(payload["repo_sync_mode"]) if payload.get("repo_sync_mode") else None),
            app_status=(str(payload["app_status"]) if payload.get("app_status") else None),
        )


@dataclass(frozen=True, slots=True)
class SessionEnvironmentSnapshot:
    """Единый снимок launcher-managed session environment для app."""

    handoff: LauncherHandoff
    session_state: SessionStateRecord | None
    user_state: UserStateRecord | None
    active_session: ActiveSessionProjectionRecord | None
    environment_health: EnvironmentHealthSnapshotRecord | None


class SessionEnvironmentClient:
    """Клиент работы с launcher-managed session environment."""

    def __init__(self, handoff: LauncherHandoff) -> None:
        self.handoff = handoff
        self.user_state_path = Path(handoff.user_state_path).expanduser() if handoff.user_state_path else None
        self.session_state_path = Path(handoff.session_state_path).expanduser() if handoff.session_state_path else None
        self.active_session_path = Path(handoff.active_session_path).expanduser() if handoff.active_session_path else None
        self.environment_health_path = Path(handoff.environment_health_path).expanduser() if handoff.environment_health_path else None

    @property
    def enabled(self) -> bool:
        return self.user_state_path is not None and self.session_state_path is not None

    def _require(self, path: Path | None, label: str) -> Path:
        if path is None:
            raise AppConfigError(f"Launcher handoff misses {label} path")
        return path

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

    def load_environment_health(self) -> EnvironmentHealthSnapshotRecord | None:
        path = self.environment_health_path
        if path is None or not path.exists():
            return None
        return EnvironmentHealthSnapshotRecord.from_dict(_read_json_object(path))

    def snapshot(self) -> SessionEnvironmentSnapshot:
        return SessionEnvironmentSnapshot(
            handoff=self.handoff,
            session_state=self.load_session_state(),
            user_state=self.load_user_state(),
            active_session=self.load_active_session(),
            environment_health=self.load_environment_health(),
        )

    def save_user_state(self, state: UserStateRecord) -> UserStateRecord:
        path = self._require(self.user_state_path, "user_state")
        _write_json_object(path, state.to_dict())
        return state

    def save_session_state(self, state: SessionStateRecord) -> SessionStateRecord:
        path = self._require(self.session_state_path, "session_state")
        _write_json_object(path, state.to_dict())
        return state

    def upsert_active_session(self, session: SessionStateRecord) -> ActiveSessionProjectionRecord | None:
        if self.active_session_path is None:
            return None
        projection = ActiveSessionProjectionRecord.from_session(session)
        _write_json_object(self.active_session_path, projection.to_dict())
        return projection

    def remove_active_session(self) -> None:
        path = self.active_session_path
        if path is None:
            return
        try:
            if path.exists():
                path.unlink()
        except Exception as exc:
            raise AppConfigError(f"Failed to remove active session projection: {path}") from exc

    def save_environment_health(self, snapshot: EnvironmentHealthSnapshotRecord) -> EnvironmentHealthSnapshotRecord:
        path = self._require(self.environment_health_path, "environment_health")
        _write_json_object(path, snapshot.to_dict())
        return snapshot

    def mark_running(self, *, app_pid: int | None = None) -> SessionStateRecord:
        session = self.load_session_state()
        if session is None:
            raise AppConfigError("Session state is missing for launcher-managed app startup")
        session = session.updated(
            status="app_running",
            lifecycle_state="running",
            app_pid=app_pid,
            failure_message=None,
            last_updated_at_utc=_utc_now(),
        )
        self.save_session_state(session)
        user = self.load_user_state()
        if user is not None:
            user = user.updated(
                current_session_id=session.session_id,
                last_session_id=session.session_id,
                last_seen_at_utc=_utc_now(),
                last_effective_data_root_path=session.effective_data_root_path,
            )
            self.save_user_state(user)
        self.upsert_active_session(session)
        health = self.load_environment_health()
        if health is not None:
            health = health.updated(
                recorded_at_utc=_utc_now(),
                session_id=session.session_id,
                user_id=session.user_id,
                effective_data_root_path=session.effective_data_root_path,
                data_status="OK" if session.data_root_status == "available" else "WARN",
                degraded_launch=bool(session.degraded_launch),
                trusted_repo_commit=session.trusted_repo_commit,
                repo_sync_mode=session.repo_sync_mode,
                app_status="running",
            )
            self.save_environment_health(health)
        return session

    def mark_ended(self, *, status: str = "app_closed", failure_message: str | None = None) -> SessionStateRecord | None:
        session = self.load_session_state()
        if session is None:
            return None
        now = _utc_now()
        session = session.updated(
            status=status,
            lifecycle_state="ended",
            ended_at_utc=now,
            last_updated_at_utc=now,
            failure_message=failure_message,
        )
        self.save_session_state(session)
        self.remove_active_session()
        user = self.load_user_state()
        if user is not None:
            user = user.updated(
                current_session_id=None,
                last_session_id=session.session_id,
                last_seen_at_utc=now,
                last_effective_data_root_path=session.effective_data_root_path,
            )
            self.save_user_state(user)
        health = self.load_environment_health()
        if health is not None:
            health = health.updated(
                recorded_at_utc=now,
                session_id=session.session_id,
                user_id=session.user_id,
                effective_data_root_path=session.effective_data_root_path,
                data_status="OK" if session.data_root_status == "available" else "WARN",
                degraded_launch=bool(session.degraded_launch),
                trusted_repo_commit=session.trusted_repo_commit,
                repo_sync_mode=session.repo_sync_mode,
                app_status="ended",
            )
            self.save_environment_health(health)
        return session

    def update_data_root(
        self,
        *,
        data_locator: dict[str, Any],
        data_root_path: Path | None,
        data_root_status: DataRootStatus,
    ) -> SessionEnvironmentSnapshot:
        now = _utc_now()
        session = self.load_session_state()
        if session is None:
            raise AppConfigError("Session state is missing for data-root update")
        session = session.updated(
            effective_data_locator=dict(data_locator),
            effective_data_root_path=(str(data_root_path) if data_root_path else None),
            data_root_status="available" if data_root_status.available else "unavailable",
            degraded_launch=not data_root_status.available,
            last_updated_at_utc=now,
        )
        self.save_session_state(session)
        active = self.upsert_active_session(session)
        user = self.load_user_state()
        if user is not None:
            user = user.updated(
                preferred_data_locator=dict(data_locator),
                last_effective_data_root_path=(str(data_root_path) if data_root_path else None),
                current_session_id=session.session_id,
                last_session_id=session.session_id,
                last_seen_at_utc=now,
            )
            self.save_user_state(user)
        health = self.load_environment_health()
        if health is not None:
            if health.install_status == "FAIL" or health.repo_status == "FAIL" or health.runtime_status == "FAIL" or health.venv_status == "FAIL":
                overall = "FAIL"
            elif not data_root_status.available or "WARN" in {health.repo_status, health.runtime_status, health.venv_status}:
                overall = "WARN"
            else:
                overall = "OK"
            health = health.updated(
                recorded_at_utc=now,
                user_id=session.user_id,
                session_id=session.session_id,
                overall_status=overall,
                data_status="OK" if data_root_status.available else "WARN",
                data_message=data_root_status.message,
                degraded_launch=not data_root_status.available,
                effective_data_root_path=(str(data_root_path) if data_root_path else None),
            )
            self.save_environment_health(health)
        return SessionEnvironmentSnapshot(
            handoff=self.handoff,
            session_state=session,
            user_state=user,
            active_session=active,
            environment_health=health,
        )
