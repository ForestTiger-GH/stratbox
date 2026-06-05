"""App-owned runtime state for Strategy Box.

The shared AppDock-facing contract stays intentionally small. Strategy Box specific
runtime details are stored under ``app_extensions`` and exposed via convenience
properties so the rest of the app does not depend on top-level extra keys.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.errors import AppConfigError

SUPPORTED_APP_STATE_CONTRACT_MAJOR = 1
_APP_STATE_DEFAULT_VERSION = "1.0"

_EXTENSION_FIELD_NAMES = (
    "last_scenario_id",
    "last_scenario_title",
    "last_scenario_ok",
    "last_outputs",
    "last_scenario_log",
    "workspace_schema_id",
    "effective_workspace_root",
    "selected_data_root_path",
    "launch_warning",
    "recent_artifacts",
)


def _parse_contract_major(*, version: str, contract_name: str) -> int:
    raw = version.strip()
    if not raw:
        raise AppConfigError(f"{contract_name} version is missing")
    major_text = raw.split(".", 1)[0].strip()
    if not major_text.isdigit():
        raise AppConfigError(f"{contract_name} version has invalid format: {version}")
    return int(major_text)


def _assert_supported_app_state_version(version: str) -> str:
    major = _parse_contract_major(version=version, contract_name="Strategy Box app_state contract")
    if major != SUPPORTED_APP_STATE_CONTRACT_MAJOR:
        raise AppConfigError(
            f"Unsupported Strategy Box app_state contract version: {version}. "
            f"Supported line: {SUPPORTED_APP_STATE_CONTRACT_MAJOR}.x"
        )
    return version.strip()


def _tuple_strings(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value.strip() else tuple()
    if not isinstance(value, (list, tuple)):
        return tuple()
    return tuple(str(item) for item in value if str(item).strip())


def _normalize_extensions(value: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(value or {})
    normalized: dict[str, Any] = {}
    for key, item in raw.items():
        key_str = str(key)
        if key_str in {"last_outputs", "recent_artifacts"}:
            normalized[key_str] = list(_tuple_strings(item))
        else:
            normalized[key_str] = item
    return normalized


def _read_extension_compat_value(payload: dict[str, Any], extensions: dict[str, Any], key: str) -> Any:
    if key in extensions:
        return extensions[key]
    return payload.get(key)


@dataclass(frozen=True, slots=True)
class AppStateRecord:
    """Shared app -> AppDock runtime state with Stratbox-owned extensions."""

    app_state_contract_version: str
    surface_id: str
    updated_at_utc: str
    heartbeat_utc: str | None = None
    resumable: bool = False
    clean_shutdown: bool | None = None
    active_view: str | None = None
    selected_object: str | None = None
    active_job: str | None = None
    warnings: tuple[str, ...] = tuple()
    workspace_state: dict[str, Any] = field(default_factory=dict)
    state_kind: str | None = None
    app_extensions: dict[str, Any] = field(default_factory=dict)

    @property
    def last_scenario_id(self) -> str | None:
        value = self.app_extensions.get("last_scenario_id")
        return str(value) if value not in (None, "") else None

    @property
    def last_scenario_title(self) -> str | None:
        value = self.app_extensions.get("last_scenario_title")
        return str(value) if value not in (None, "") else None

    @property
    def last_scenario_ok(self) -> bool | None:
        value = self.app_extensions.get("last_scenario_ok")
        return bool(value) if value is not None else None

    @property
    def last_outputs(self) -> tuple[str, ...]:
        return _tuple_strings(self.app_extensions.get("last_outputs"))

    @property
    def last_scenario_log(self) -> str | None:
        value = self.app_extensions.get("last_scenario_log")
        return str(value) if value not in (None, "") else None

    @property
    def workspace_schema_id(self) -> str | None:
        value = self.app_extensions.get("workspace_schema_id")
        return str(value) if value not in (None, "") else None

    @property
    def effective_workspace_root(self) -> str | None:
        value = self.app_extensions.get("effective_workspace_root")
        return str(value) if value not in (None, "") else None

    @property
    def selected_data_root_path(self) -> str | None:
        value = self.app_extensions.get("selected_data_root_path")
        return str(value) if value not in (None, "") else None

    @property
    def launch_warning(self) -> str | None:
        value = self.app_extensions.get("launch_warning")
        return str(value) if value not in (None, "") else None

    @property
    def recent_artifacts(self) -> tuple[str, ...]:
        return _tuple_strings(self.app_extensions.get("recent_artifacts"))

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "app_state_contract_version": self.app_state_contract_version,
            "surface_id": self.surface_id,
            "updated_at_utc": self.updated_at_utc,
            "heartbeat_utc": self.heartbeat_utc,
            "resumable": self.resumable,
            "clean_shutdown": self.clean_shutdown,
            "active_view": self.active_view,
            "selected_object": self.selected_object,
            "active_job": self.active_job,
            "warnings": list(self.warnings),
            "workspace_state": dict(self.workspace_state),
            "state_kind": self.state_kind,
        }
        if self.app_extensions:
            payload["app_extensions"] = _normalize_extensions(self.app_extensions)
        return payload

    def updated(self, **kwargs: Any) -> "AppStateRecord":
        base = self.to_dict()
        extensions = _normalize_extensions(base.get("app_extensions"))
        incoming_extensions = kwargs.pop("app_extensions", None)
        if isinstance(incoming_extensions, dict):
            extensions.update(_normalize_extensions(incoming_extensions))

        for name in _EXTENSION_FIELD_NAMES:
            if name in kwargs:
                value = kwargs.pop(name)
                if name in {"last_outputs", "recent_artifacts"}:
                    extensions[name] = list(_tuple_strings(value))
                else:
                    extensions[name] = value

        base.update(kwargs)

        warnings = base.get("warnings") or []
        if isinstance(warnings, str):
            warnings = [warnings]
        base["warnings"] = tuple(str(item) for item in warnings if str(item).strip())

        workspace_state = base.get("workspace_state")
        if not isinstance(workspace_state, dict):
            base["workspace_state"] = {}
        else:
            base["workspace_state"] = {str(key): value for key, value in workspace_state.items()}

        base["app_extensions"] = extensions
        return AppStateRecord.from_dict(base)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppStateRecord":
        version = str(payload.get("app_state_contract_version") or _APP_STATE_DEFAULT_VERSION)
        validated_version = _assert_supported_app_state_version(version)

        workspace_state = payload.get("workspace_state") if isinstance(payload.get("workspace_state"), dict) else {}
        raw_extensions = payload.get("app_extensions")
        extensions = _normalize_extensions(raw_extensions if isinstance(raw_extensions, dict) else None)

        for field_name in _EXTENSION_FIELD_NAMES:
            legacy_value = _read_extension_compat_value(payload, extensions, field_name)
            if legacy_value is None:
                continue
            if field_name in {"last_outputs", "recent_artifacts"}:
                extensions[field_name] = list(_tuple_strings(legacy_value))
            else:
                extensions[field_name] = legacy_value

        return cls(
            app_state_contract_version=validated_version,
            surface_id=str(payload.get("surface_id") or ""),
            updated_at_utc=str(payload.get("updated_at_utc") or ""),
            heartbeat_utc=(str(payload["heartbeat_utc"]) if payload.get("heartbeat_utc") else None),
            resumable=bool(payload.get("resumable", False)),
            clean_shutdown=payload.get("clean_shutdown"),
            active_view=(str(payload["active_view"]) if payload.get("active_view") else None),
            selected_object=(str(payload["selected_object"]) if payload.get("selected_object") else None),
            active_job=(str(payload["active_job"]) if payload.get("active_job") else None),
            warnings=_tuple_strings(payload.get("warnings")),
            workspace_state={str(key): value for key, value in workspace_state.items()},
            state_kind=(str(payload["state_kind"]) if payload.get("state_kind") else None),
            app_extensions=extensions,
        )
