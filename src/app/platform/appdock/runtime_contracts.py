"""AppDock activation-context contract adapter for Strategy Box.

This module intentionally stays stdlib-only. Strategy Box can run inside an
AppDock-managed Python runtime and still keep the standalone developer route
lightweight. The contract shape mirrors the current AppDock runtime boundary:
activation_context in, runtime_state out.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.runtime.errors import AppConfigError

SUPPORTED_ACTIVATION_CONTRACT_MAJOR = 1
ACTIVATION_CONTEXT_ENV = 'APPDOCK_ACTIVATION_CONTEXT_PATH'
APPDOCK_CONFIG_ENV = 'APPDOCK_CONFIG_PATH'


def _parse_contract_major(*, version: str, contract_name: str) -> int:
    raw = version.strip()
    if not raw:
        raise AppConfigError(f'{contract_name} version is missing')
    major_text = raw.split('.', 1)[0].strip()
    if not major_text.isdigit():
        raise AppConfigError(f'{contract_name} version has invalid format: {version}')
    return int(major_text)


def _assert_supported_activation_version(version: str) -> str:
    major = _parse_contract_major(version=version, contract_name='AppDock activation context contract')
    if major != SUPPORTED_ACTIVATION_CONTRACT_MAJOR:
        raise AppConfigError(
            f'Unsupported AppDock activation context contract version: {version}. '
            f'Strategy Box supports {SUPPORTED_ACTIVATION_CONTRACT_MAJOR}.x'
        )
    return version.strip()


def _tuple_strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value.strip() else tuple()
    if not isinstance(value, (list, tuple)):
        return tuple()
    return tuple(str(item) for item in value if str(item).strip())


def _required_string(payload: dict[str, Any], key: str, *, scope: str) -> str:
    value = str(payload.get(key) or '').strip()
    if not value:
        raise AppConfigError(f'{scope} misses {key}')
    return value


@dataclass(frozen=True, slots=True)
class SourceRevisionRef:
    ref_kind: str
    ref: str
    commit: str | None
    sync_mode: str | None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'SourceRevisionRef':
        return cls(
            ref_kind=_required_string(payload, 'ref_kind', scope='activation_context.source_revision'),
            ref=_required_string(payload, 'ref', scope='activation_context.source_revision'),
            commit=(str(payload['commit']) if payload.get('commit') else None),
            sync_mode=(str(payload['sync_mode']) if payload.get('sync_mode') else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActivationWorkspace:
    install_root: str
    system_root: str
    source_root: str
    bundle_root: str
    data_root_status: str
    data_root_path: str | None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'ActivationWorkspace':
        return cls(
            install_root=_required_string(payload, 'install_root', scope='activation_context.workspace'),
            system_root=_required_string(payload, 'system_root', scope='activation_context.workspace'),
            source_root=_required_string(payload, 'source_root', scope='activation_context.workspace'),
            bundle_root=_required_string(payload, 'bundle_root', scope='activation_context.workspace'),
            data_root_status=_required_string(payload, 'data_root_status', scope='activation_context.workspace'),
            data_root_path=(str(payload['data_root_path']) if payload.get('data_root_path') else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActivationSystemDir:
    kind: str
    directory_name: str
    path: str
    provider_class: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> 'ActivationSystemDir | None':
        if not isinstance(payload, dict) or not payload:
            return None
        path = str(payload.get('path') or '').strip()
        if not path:
            return None
        return cls(
            kind=str(payload.get('kind') or ''),
            directory_name=str(payload.get('directory_name') or ''),
            path=path,
            provider_class=str(payload.get('provider_class') or ''),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActivationProvidedSystemDirs:
    install_root_system_dir: ActivationSystemDir | None = None
    user_local_system_dir: ActivationSystemDir | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> 'ActivationProvidedSystemDirs':
        payload = payload or {}
        if not isinstance(payload, dict):
            payload = {}
        return cls(
            install_root_system_dir=ActivationSystemDir.from_dict(payload.get('install_root_system_dir')),
            user_local_system_dir=ActivationSystemDir.from_dict(payload.get('user_local_system_dir')),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            'install_root_system_dir': self.install_root_system_dir.to_dict() if self.install_root_system_dir else None,
            'user_local_system_dir': self.user_local_system_dir.to_dict() if self.user_local_system_dir else None,
        }


@dataclass(frozen=True, slots=True)
class ActivationRefs:
    health_snapshot_ref: str | None = None
    user_state_ref: str | None = None
    session_ref: str | None = None
    active_session_ref: str | None = None
    runtime_state_ref: str | None = None
    cleanup_registry_ref: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'ActivationRefs':
        return cls(
            health_snapshot_ref=(str(payload['health_snapshot_ref']) if payload.get('health_snapshot_ref') else None),
            user_state_ref=(str(payload['user_state_ref']) if payload.get('user_state_ref') else None),
            session_ref=(str(payload['session_ref']) if payload.get('session_ref') else None),
            active_session_ref=(str(payload['active_session_ref']) if payload.get('active_session_ref') else None),
            runtime_state_ref=(str(payload['runtime_state_ref']) if payload.get('runtime_state_ref') else None),
            cleanup_registry_ref=(str(payload['cleanup_registry_ref']) if payload.get('cleanup_registry_ref') else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActivationNode:
    node_id: str | None = None
    node_created_at_utc: str | None = None
    host_name: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> 'ActivationNode | None':
        if not isinstance(payload, dict) or not payload:
            return None
        return cls(
            node_id=(str(payload['node_id']) if payload.get('node_id') else None),
            node_created_at_utc=(str(payload['node_created_at_utc']) if payload.get('node_created_at_utc') else None),
            host_name=(str(payload['host_name']) if payload.get('host_name') else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActivationUser:
    user_id: str | None = None
    account_name: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> 'ActivationUser | None':
        if not isinstance(payload, dict) or not payload:
            return None
        return cls(
            user_id=(str(payload['user_id']) if payload.get('user_id') else None),
            account_name=(str(payload['account_name']) if payload.get('account_name') else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActivationSession:
    session_id: str | None = None
    session_started_at_utc: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> 'ActivationSession | None':
        if not isinstance(payload, dict) or not payload:
            return None
        return cls(
            session_id=(str(payload['session_id']) if payload.get('session_id') else None),
            session_started_at_utc=(str(payload['session_started_at_utc']) if payload.get('session_started_at_utc') else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActiveSurface:
    surface_id: str
    entry_view: str
    declared_views: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'ActiveSurface':
        return cls(
            surface_id=_required_string(payload, 'surface_id', scope='activation_context.active_surface'),
            entry_view=str(payload.get('entry_view') or 'timeline'),
            declared_views=_tuple_strings(payload.get('declared_views')),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data['declared_views'] = list(self.declared_views)
        return data


@dataclass(frozen=True, slots=True)
class ActivationFlags:
    attach_mode: str = 'local'
    degraded_launch: bool = False

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> 'ActivationFlags':
        payload = payload or {}
        if not isinstance(payload, dict):
            payload = {}
        return cls(
            attach_mode=str(payload.get('attach_mode') or 'local'),
            degraded_launch=bool(payload.get('degraded_launch', False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AppActivationContext:
    contract_version: str
    generated_at_utc: str
    world_id: str
    world_display_name: str | None
    active_surface: ActiveSurface
    activation: ActivationFlags
    source_revision: SourceRevisionRef
    workspace: ActivationWorkspace
    provided_system_dirs: ActivationProvidedSystemDirs = field(default_factory=ActivationProvidedSystemDirs)
    refs: ActivationRefs = field(default_factory=ActivationRefs)
    node: ActivationNode | None = None
    user: ActivationUser | None = None
    session: ActivationSession | None = None
    available_route_groups: tuple[str, ...] = tuple()

    @property
    def entry_view(self) -> str:
        return self.active_surface.entry_view

    @property
    def declared_views(self) -> tuple[str, ...]:
        return self.active_surface.declared_views

    @property
    def active_surface_id(self) -> str:
        return self.active_surface.surface_id

    @property
    def attach_mode(self) -> str:
        return self.activation.attach_mode

    @property
    def degraded_launch(self) -> bool:
        return self.activation.degraded_launch

    @property
    def node_id(self) -> str | None:
        return self.node.node_id if self.node is not None else None

    @property
    def node_created_at_utc(self) -> str | None:
        return self.node.node_created_at_utc if self.node is not None else None

    @property
    def user_id(self) -> str | None:
        return self.user.user_id if self.user is not None else None

    @property
    def account_name(self) -> str | None:
        return self.user.account_name if self.user is not None else None

    @property
    def host_name(self) -> str | None:
        if self.node is not None and self.node.host_name:
            return self.node.host_name
        return None

    @property
    def session_id(self) -> str | None:
        return self.session.session_id if self.session is not None else None

    @property
    def session_started_at_utc(self) -> str | None:
        return self.session.session_started_at_utc if self.session is not None else None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'AppActivationContext':
        world = payload.get('world')
        if not isinstance(world, dict):
            raise AppConfigError('AppDock activation context misses world object')
        active_surface = payload.get('active_surface')
        if not isinstance(active_surface, dict):
            raise AppConfigError('AppDock activation context misses active_surface object')
        source_revision = payload.get('source_revision')
        if not isinstance(source_revision, dict):
            raise AppConfigError('AppDock activation context misses source_revision object')
        workspace = payload.get('workspace')
        if not isinstance(workspace, dict):
            raise AppConfigError('AppDock activation context misses workspace object')
        refs = payload.get('refs') or {}
        if not isinstance(refs, dict):
            raise AppConfigError('AppDock activation context misses refs object')
        return cls(
            contract_version=_assert_supported_activation_version(str(payload.get('contract_version') or '')),
            generated_at_utc=_required_string(payload, 'generated_at_utc', scope='activation_context'),
            world_id=_required_string(world, 'world_id', scope='activation_context.world'),
            world_display_name=(str(world['display_name']) if world.get('display_name') else None),
            active_surface=ActiveSurface.from_dict(active_surface),
            activation=ActivationFlags.from_dict(payload.get('activation')),
            source_revision=SourceRevisionRef.from_dict(source_revision),
            workspace=ActivationWorkspace.from_dict(workspace),
            provided_system_dirs=ActivationProvidedSystemDirs.from_dict(payload.get('provided_system_dirs')),
            refs=ActivationRefs.from_dict(refs),
            node=ActivationNode.from_dict(payload.get('node')),
            user=ActivationUser.from_dict(payload.get('user')),
            session=ActivationSession.from_dict(payload.get('session')),
            available_route_groups=_tuple_strings(payload.get('available_route_groups')),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            'contract_version': self.contract_version,
            'generated_at_utc': self.generated_at_utc,
            'world': {
                'world_id': self.world_id,
                'display_name': self.world_display_name,
            },
            'active_surface': self.active_surface.to_dict(),
            'activation': self.activation.to_dict(),
            'source_revision': self.source_revision.to_dict(),
            'workspace': self.workspace.to_dict(),
            'provided_system_dirs': self.provided_system_dirs.to_dict(),
            'refs': self.refs.to_dict(),
            'node': (self.node.to_dict() if self.node is not None else None),
            'user': (self.user.to_dict() if self.user is not None else None),
            'session': (self.session.to_dict() if self.session is not None else None),
            'available_route_groups': list(self.available_route_groups),
        }


def get_activation_context_path_from_env() -> Path | None:
    value = os.getenv(ACTIVATION_CONTEXT_ENV, '').strip()
    if not value:
        return None
    return Path(value).expanduser()


def get_appdock_config_path_from_env() -> Path | None:
    value = os.getenv(APPDOCK_CONFIG_ENV, '').strip()
    if not value:
        return None
    return Path(value).expanduser()


def load_activation_context(path: Path) -> AppActivationContext:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise AppConfigError(f'Failed to read AppDock activation context: {path}') from exc
    if not isinstance(payload, dict):
        raise AppConfigError(f'AppDock activation context must be a JSON object: {path}')
    context = AppActivationContext.from_dict(payload)
    if not context.world_id:
        raise AppConfigError('AppDock activation context misses world.world_id')
    if not context.active_surface_id:
        raise AppConfigError('AppDock activation context misses active_surface.surface_id')
    if not context.workspace.source_root:
        raise AppConfigError('AppDock activation context misses workspace.source_root')
    if not context.workspace.install_root:
        raise AppConfigError('AppDock activation context misses workspace.install_root')
    if not context.workspace.system_root:
        raise AppConfigError('AppDock activation context misses workspace.system_root')
    return context


def load_activation_context_from_env() -> AppActivationContext | None:
    path = get_activation_context_path_from_env()
    if path is None:
        return None
    return load_activation_context(path)
