"""App-facing runtime and session surfaces inside an AppDock-managed session."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.runtime.errors import AppConfigError
from app.platform.appdock.runtime_contracts import AppActivationContext
from app.application.workspace import DataRootStatus

_RUNTIME_STATE_DEFAULT_VERSION = '1.0'
_SUPPORTED_RUNTIME_STATE_CONTRACT_MAJOR = 1
_EXTENSION_FIELD_NAMES = {
    'last_operation_id',
    'last_operation_title',
    'last_operation_ok',
    'last_outputs',
    'last_operation_log',
    'workspace_schema_id',
    'effective_workspace_root',
    'selected_data_root_path',
    'launch_warning',
    'recent_artifacts',
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise AppConfigError(f'Session surface file not found: {path}') from exc
    except Exception as exc:
        raise AppConfigError(f'Failed to read session surface file: {path}') from exc
    if not isinstance(payload, dict):
        raise AppConfigError(f'Session surface file must be a JSON object: {path}')
    return payload


def _write_json_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _tuple_strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value.strip() else tuple()
    if not isinstance(value, (list, tuple)):
        return tuple()
    return tuple(str(item) for item in value if str(item).strip())


def _parse_contract_major(*, version: str, contract_name: str) -> int:
    raw = version.strip()
    if not raw:
        raise AppConfigError(f'{contract_name} version is missing')
    major_text = raw.split('.', 1)[0].strip()
    if not major_text.isdigit():
        raise AppConfigError(f'{contract_name} version has invalid format: {version}')
    return int(major_text)


def _assert_supported_runtime_state_version(version: str) -> str:
    major = _parse_contract_major(version=version, contract_name='Strategy Box runtime_state contract')
    if major != _SUPPORTED_RUNTIME_STATE_CONTRACT_MAJOR:
        raise AppConfigError(
            f'Unsupported Strategy Box runtime_state contract version: {version}. '
            f'Supported line: {_SUPPORTED_RUNTIME_STATE_CONTRACT_MAJOR}.x'
        )
    return version.strip()


def _normalize_surface_state(value: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(value or {})
    normalized: dict[str, Any] = {}
    for key, item in raw.items():
        key_str = str(key)
        if key_str in {'last_outputs', 'recent_artifacts'}:
            normalized[key_str] = list(_tuple_strings(item))
        else:
            normalized[key_str] = item
    return normalized


def _read_surface_extension_value(payload: dict[str, Any], surface_state: dict[str, Any], key: str) -> Any:
    if key in surface_state:
        return surface_state[key]
    return payload.get(key)
    if legacy_key:
        return payload.get(legacy_key)
    return payload.get(key)


@dataclass(frozen=True, slots=True)
class UserStateRecord:
    user_id: str
    account_name: str
    host_name: str
    last_seen_at_utc: str | None = None
    preferred_data_root_path: str | None = None
    last_effective_data_root_path: str | None = None
    last_session_id: str | None = None
    current_session_id: str | None = None
    last_surface_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'UserStateRecord':
        return cls(
            user_id=str(payload.get('user_id') or ''),
            account_name=str(payload.get('account_name') or ''),
            host_name=str(payload.get('host_name') or ''),
            last_seen_at_utc=(str(payload['last_seen_at_utc']) if payload.get('last_seen_at_utc') else None),
            preferred_data_root_path=(str(payload['preferred_data_root_path']) if payload.get('preferred_data_root_path') else None),
            last_effective_data_root_path=(str(payload['last_effective_data_root_path']) if payload.get('last_effective_data_root_path') else None),
            last_session_id=(str(payload['last_session_id']) if payload.get('last_session_id') else None),
            current_session_id=(str(payload['current_session_id']) if payload.get('current_session_id') else None),
            last_surface_id=(str(payload['last_surface_id']) if payload.get('last_surface_id') else None),
        )


@dataclass(frozen=True, slots=True)
class SessionStateRecord:
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
    active_surface_id: str | None = None
    entry_view: str | None = None
    activation_context_ref: str | None = None
    runtime_state_ref: str | None = None
    app_pid: int | None = None
    failure_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def updated(self, **kwargs: Any) -> 'SessionStateRecord':
        return replace(self, **kwargs)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'SessionStateRecord':
        lifecycle_state = str(payload.get('lifecycle_state') or '')
        status = str(payload.get('status') or '')
        if not lifecycle_state:
            lifecycle_state = 'ended' if payload.get('ended_at_utc') else 'created'
        if not status:
            status = lifecycle_state
        return cls(
            session_id=str(payload.get('session_id') or ''),
            user_id=str(payload.get('user_id') or ''),
            account_name=str(payload.get('account_name') or ''),
            host_name=str(payload.get('host_name') or ''),
            node_id=str(payload.get('node_id') or ''),
            started_at_utc=str(payload.get('started_at_utc') or ''),
            attach_mode=str(payload.get('attach_mode') or ''),
            status=status,
            lifecycle_state=lifecycle_state,
            last_updated_at_utc=str(payload.get('last_updated_at_utc') or payload.get('started_at_utc') or ''),
            ended_at_utc=(str(payload['ended_at_utc']) if payload.get('ended_at_utc') else None),
            effective_data_root_path=(str(payload['effective_data_root_path']) if payload.get('effective_data_root_path') else None),
            data_root_status=(str(payload['data_root_status']) if payload.get('data_root_status') else None),
            source_commit=(str(payload['source_commit']) if payload.get('source_commit') else None),
            source_sync_mode=(str(payload['source_sync_mode']) if payload.get('source_sync_mode') else None),
            degraded_launch=(bool(payload['degraded_launch']) if payload.get('degraded_launch') is not None else None),
            world_id=(str(payload['world_id']) if payload.get('world_id') else None),
            active_surface_id=(str(payload['active_surface_id']) if payload.get('active_surface_id') else None),
            entry_view=(str(payload['entry_view']) if payload.get('entry_view') else None),
            activation_context_ref=(str(payload['activation_context_ref']) if payload.get('activation_context_ref') else None),
            runtime_state_ref=(str(payload['runtime_state_ref']) if payload.get('runtime_state_ref') else None),
            app_pid=(int(payload['app_pid']) if payload.get('app_pid') is not None else None),
            failure_message=(str(payload['failure_message']) if payload.get('failure_message') else None),
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
    active_surface_id: str | None = None
    app_pid: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'ActiveSessionProjectionRecord':
        return cls(
            session_id=str(payload.get('session_id') or ''),
            node_id=str(payload.get('node_id') or ''),
            user_id=str(payload.get('user_id') or ''),
            account_name=str(payload.get('account_name') or ''),
            host_name=str(payload.get('host_name') or ''),
            started_at_utc=str(payload.get('started_at_utc') or ''),
            last_state_change_at_utc=str(payload.get('last_state_change_at_utc') or ''),
            lifecycle_state=str(payload.get('lifecycle_state') or ''),
            effective_data_root_path=(str(payload['effective_data_root_path']) if payload.get('effective_data_root_path') else None),
            data_root_status=(str(payload['data_root_status']) if payload.get('data_root_status') else None),
            degraded_launch=(bool(payload['degraded_launch']) if payload.get('degraded_launch') is not None else None),
            active_surface_id=(str(payload['active_surface_id']) if payload.get('active_surface_id') else None),
            app_pid=(int(payload['app_pid']) if payload.get('app_pid') is not None else None),
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
    active_surface_id: str | None = None
    app_status: str | None = None
    pip_tls_mode: str | None = None
    pip_version: str | None = None
    install_error_category: str | None = None
    install_error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'NodeHealthSnapshotRecord':
        return cls(
            recorded_at_utc=str(payload.get('recorded_at_utc') or ''),
            node_id=payload.get('node_id'),
            user_id=payload.get('user_id'),
            session_id=payload.get('session_id'),
            overall_status=str(payload.get('overall_status') or ''),
            install_status=str(payload.get('install_status') or ''),
            install_message=str(payload.get('install_message') or ''),
            source_status=str(payload.get('source_status') or ''),
            source_message=str(payload.get('source_message') or ''),
            runtime_status=str(payload.get('runtime_status') or ''),
            runtime_message=str(payload.get('runtime_message') or ''),
            venv_status=str(payload.get('venv_status') or ''),
            venv_message=str(payload.get('venv_message') or ''),
            data_status=str(payload.get('data_status') or ''),
            data_message=str(payload.get('data_message') or ''),
            degraded_launch=bool(payload.get('degraded_launch', False)),
            effective_data_root_path=payload.get('effective_data_root_path'),
            source_commit=payload.get('source_commit'),
            source_sync_mode=payload.get('source_sync_mode'),
            world_id=payload.get('world_id'),
            active_surface_id=payload.get('active_surface_id'),
            app_status=payload.get('app_status'),
            pip_tls_mode=payload.get('pip_tls_mode'),
            pip_version=payload.get('pip_version'),
            install_error_category=payload.get('install_error_category'),
            install_error_message=payload.get('install_error_message'),
        )


@dataclass(frozen=True, slots=True)
class RuntimeStateRecord:
    contract_version: str
    surface_id: str
    updated_at_utc: str
    heartbeat_utc: str | None = None
    resumable: bool = False
    clean_shutdown: bool | None = None
    active_view: str | None = None
    selected_object: str | None = None
    active_job: str | None = None
    warnings: tuple[str, ...] = tuple()
    surface_state: dict[str, Any] = field(default_factory=dict)
    state_kind: str | None = None

    @property
    def last_operation_id(self) -> str | None:
        value = self.surface_state.get('last_operation_id')
        return str(value) if value not in (None, '') else None

    @property
    def last_operation_title(self) -> str | None:
        value = self.surface_state.get('last_operation_title')
        return str(value) if value not in (None, '') else None

    @property
    def last_operation_ok(self) -> bool | None:
        value = self.surface_state.get('last_operation_ok')
        return bool(value) if value is not None else None

    @property
    def last_outputs(self) -> tuple[str, ...]:
        return _tuple_strings(self.surface_state.get('last_outputs'))

    @property
    def last_operation_log(self) -> str | None:
        value = self.surface_state.get('last_operation_log')
        return str(value) if value not in (None, '') else None

    @property
    def workspace_schema_id(self) -> str | None:
        value = self.surface_state.get('workspace_schema_id')
        return str(value) if value not in (None, '') else None

    @property
    def effective_workspace_root(self) -> str | None:
        value = self.surface_state.get('effective_workspace_root')
        return str(value) if value not in (None, '') else None

    @property
    def selected_data_root_path(self) -> str | None:
        value = self.surface_state.get('selected_data_root_path')
        return str(value) if value not in (None, '') else None

    @property
    def launch_warning(self) -> str | None:
        value = self.surface_state.get('launch_warning')
        return str(value) if value not in (None, '') else None

    @property
    def recent_artifacts(self) -> tuple[str, ...]:
        return _tuple_strings(self.surface_state.get('recent_artifacts'))

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            'contract_version': self.contract_version,
            'surface_id': self.surface_id,
            'updated_at_utc': self.updated_at_utc,
            'heartbeat_utc': self.heartbeat_utc,
            'resumable': self.resumable,
            'clean_shutdown': self.clean_shutdown,
            'active_view': self.active_view,
            'selected_object': self.selected_object,
            'active_job': self.active_job,
            'warnings': list(self.warnings),
            'surface_state': _normalize_surface_state(self.surface_state),
            'state_kind': self.state_kind,
        }
        return payload

    def updated(self, **kwargs: Any) -> 'RuntimeStateRecord':
        base = self.to_dict()
        surface_state = _normalize_surface_state(base.get('surface_state'))
        incoming_surface_state = kwargs.pop('surface_state', None)
        if isinstance(incoming_surface_state, dict):
            surface_state.update(_normalize_surface_state(incoming_surface_state))

        for field_name in _EXTENSION_FIELD_NAMES:
            if field_name in kwargs:
                value = kwargs.pop(field_name)
                if field_name in {'last_outputs', 'recent_artifacts'}:
                    surface_state[field_name] = list(_tuple_strings(value))
                else:
                    surface_state[field_name] = value

        base.update(kwargs)

        warnings = base.get('warnings') or []
        if isinstance(warnings, str):
            warnings = [warnings]
        base['warnings'] = tuple(str(item) for item in warnings if str(item).strip())
        base['surface_state'] = surface_state
        return RuntimeStateRecord.from_dict(base)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'RuntimeStateRecord':
        version = str(payload.get('contract_version') or _RUNTIME_STATE_DEFAULT_VERSION)
        validated_version = _assert_supported_runtime_state_version(version)
        raw_surface_state = payload.get('surface_state') if isinstance(payload.get('surface_state'), dict) else {}
        surface_state = _normalize_surface_state(raw_surface_state)
        for field_name in _EXTENSION_FIELD_NAMES:
            legacy_value = _read_surface_extension_value(payload, surface_state, field_name)
            if legacy_value is None:
                continue
            if field_name in {'last_outputs', 'recent_artifacts'}:
                surface_state[field_name] = list(_tuple_strings(legacy_value))
            else:
                surface_state[field_name] = legacy_value
        return cls(
            contract_version=validated_version,
            surface_id=str(payload.get('surface_id') or ''),
            updated_at_utc=str(payload.get('updated_at_utc') or ''),
            heartbeat_utc=(str(payload['heartbeat_utc']) if payload.get('heartbeat_utc') else None),
            resumable=bool(payload.get('resumable', False)),
            clean_shutdown=payload.get('clean_shutdown'),
            active_view=(str(payload['active_view']) if payload.get('active_view') else None),
            selected_object=(str(payload['selected_object']) if payload.get('selected_object') else None),
            active_job=(str(payload['active_job']) if payload.get('active_job') else None),
            warnings=_tuple_strings(payload.get('warnings')),
            surface_state=surface_state,
            state_kind=(str(payload['state_kind']) if payload.get('state_kind') else None),
        )


@dataclass(frozen=True, slots=True)
class AppSessionSnapshot:
    activation_context: AppActivationContext
    session_state: SessionStateRecord | None
    user_state: UserStateRecord | None
    active_session: ActiveSessionProjectionRecord | None
    health_snapshot: NodeHealthSnapshotRecord | None
    runtime_state: RuntimeStateRecord | None


class AppSessionClient:
    """Client for AppDock-published session-facing JSON surfaces."""

    def __init__(self, activation_context: AppActivationContext) -> None:
        self.activation_context = activation_context
        self.user_state_path = Path(activation_context.refs.user_state_ref).expanduser() if activation_context.refs.user_state_ref else None
        self.session_state_path = Path(activation_context.refs.session_ref).expanduser() if activation_context.refs.session_ref else None
        self.active_session_path = Path(activation_context.refs.active_session_ref).expanduser() if activation_context.refs.active_session_ref else None
        self.health_snapshot_path = Path(activation_context.refs.health_snapshot_ref).expanduser() if activation_context.refs.health_snapshot_ref else None
        self.runtime_state_path = Path(activation_context.refs.runtime_state_ref).expanduser() if activation_context.refs.runtime_state_ref else None

    @property
    def enabled(self) -> bool:
        return self.session_state_path is not None or self.runtime_state_path is not None

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

    def load_runtime_state(self) -> RuntimeStateRecord | None:
        path = self.runtime_state_path
        if path is None or not path.exists():
            return None
        return RuntimeStateRecord.from_dict(_read_json_object(path))

    def snapshot(self) -> AppSessionSnapshot:
        return AppSessionSnapshot(
            activation_context=self.activation_context,
            session_state=self.load_session_state(),
            user_state=self.load_user_state(),
            active_session=self.load_active_session(),
            health_snapshot=self.load_health_snapshot(),
            runtime_state=self.load_runtime_state(),
        )

    def _default_runtime_state(self) -> RuntimeStateRecord:
        now = _utc_now()
        return RuntimeStateRecord(
            contract_version='1.0',
            surface_id=self.activation_context.active_surface_id,
            updated_at_utc=now,
            heartbeat_utc=now,
            resumable=True,
            clean_shutdown=None,
            active_view=(self.activation_context.entry_view or 'timeline'),
            selected_object=None,
            active_job=None,
            warnings=tuple(),
            surface_state={},
            state_kind='runtime',
        )

    def save_runtime_state(self, state: RuntimeStateRecord) -> RuntimeStateRecord:
        if self.runtime_state_path is None:
            return state
        _write_json_object(self.runtime_state_path, state.to_dict())
        return state

    def update_runtime_state(self, **kwargs: Any) -> RuntimeStateRecord:
        state = self.load_runtime_state() or self._default_runtime_state()
        merged = state.updated(updated_at_utc=_utc_now(), heartbeat_utc=_utc_now(), **kwargs)
        return self.save_runtime_state(merged)

    def mark_running(self, *, active_view: str | None = None) -> RuntimeStateRecord:
        resolved_view = active_view or self.activation_context.entry_view or 'timeline'
        return self.update_runtime_state(clean_shutdown=None, resumable=True, active_view=resolved_view, state_kind='runtime')

    def mark_ended(self, *, clean_shutdown: bool, active_view: str | None = 'closed', warning: str | None = None) -> RuntimeStateRecord | None:
        warnings: tuple[str, ...] = (warning,) if warning else tuple()
        return self.update_runtime_state(clean_shutdown=clean_shutdown, active_view=active_view, warnings=warnings, state_kind='shutdown')

    def update_workspace_selector(self, *, selector_path: Path | None, data_root_status: DataRootStatus) -> AppSessionSnapshot:
        surface_state = {
            'selected_data_root_path': (str(selector_path) if selector_path else None),
            'selected_data_root_status': 'available' if data_root_status.available else 'unavailable',
            'selected_data_root_message': data_root_status.message,
        }
        self.update_runtime_state(
            surface_state=surface_state,
            selected_data_root_path=(str(selector_path) if selector_path else None),
            state_kind='runtime',
        )
        return self.snapshot()
