"""App-owned runtime state для Strategy Box."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AppStateRecord:
    """Минимальный обратный контракт app -> AppDock."""

    app_state_contract_version: str
    app_id: str
    updated_at_utc: str
    heartbeat_utc: str | None = None
    resumable: bool = False
    clean_shutdown: bool | None = None
    active_view: str | None = None
    selected_object: str | None = None
    active_job: str | None = None
    warnings: tuple[str, ...] = tuple()
    workspace_state: dict[str, Any] | None = None
    state_kind: str | None = None
    last_scenario_id: str | None = None
    last_scenario_title: str | None = None
    last_scenario_ok: bool | None = None
    last_outputs: tuple[str, ...] = tuple()
    last_scenario_log: str | None = None
    workspace_schema_id: str | None = None
    effective_workspace_root: str | None = None
    selected_data_root_path: str | None = None
    launch_warning: str | None = None
    recent_artifacts: tuple[str, ...] = tuple()

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_state_contract_version": self.app_state_contract_version,
            "app_id": self.app_id,
            "updated_at_utc": self.updated_at_utc,
            "heartbeat_utc": self.heartbeat_utc,
            "resumable": self.resumable,
            "clean_shutdown": self.clean_shutdown,
            "active_view": self.active_view,
            "selected_object": self.selected_object,
            "active_job": self.active_job,
            "warnings": list(self.warnings),
            "workspace_state": self.workspace_state or {},
            "state_kind": self.state_kind,
            "last_scenario_id": self.last_scenario_id,
            "last_scenario_title": self.last_scenario_title,
            "last_scenario_ok": self.last_scenario_ok,
            "last_outputs": list(self.last_outputs),
            "last_scenario_log": self.last_scenario_log,
            "workspace_schema_id": self.workspace_schema_id,
            "effective_workspace_root": self.effective_workspace_root,
            "selected_data_root_path": self.selected_data_root_path,
            "launch_warning": self.launch_warning,
            "recent_artifacts": list(self.recent_artifacts),
        }

    def updated(self, **kwargs: Any) -> "AppStateRecord":
        data = self.to_dict()
        data.update(kwargs)
        warnings = data.get("warnings") or []
        if isinstance(warnings, str):
            warnings = [warnings]
        data["warnings"] = tuple(str(item) for item in warnings if str(item).strip())
        outputs = data.get("last_outputs") or []
        if isinstance(outputs, str):
            outputs = [outputs]
        data["last_outputs"] = tuple(str(item) for item in outputs if str(item).strip())
        artifacts = data.get("recent_artifacts") or []
        if isinstance(artifacts, str):
            artifacts = [artifacts]
        data["recent_artifacts"] = tuple(str(item) for item in artifacts if str(item).strip())
        workspace_state = data.get("workspace_state")
        if workspace_state is None:
            data["workspace_state"] = {}
        return AppStateRecord.from_dict(data)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppStateRecord":
        def _tuple_strings(value: Any) -> tuple[str, ...]:
            if isinstance(value, str):
                return (value,) if value.strip() else tuple()
            if not isinstance(value, (list, tuple)):
                return tuple()
            return tuple(str(item) for item in value if str(item).strip())

        workspace_state = payload.get("workspace_state") if isinstance(payload.get("workspace_state"), dict) else {}
        return cls(
            app_state_contract_version=str(payload.get("app_state_contract_version") or ""),
            app_id=str(payload.get("app_id") or ""),
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
            last_scenario_id=(str(payload["last_scenario_id"]) if payload.get("last_scenario_id") else None),
            last_scenario_title=(str(payload["last_scenario_title"]) if payload.get("last_scenario_title") else None),
            last_scenario_ok=(bool(payload["last_scenario_ok"]) if payload.get("last_scenario_ok") is not None else None),
            last_outputs=_tuple_strings(payload.get("last_outputs")),
            last_scenario_log=(str(payload["last_scenario_log"]) if payload.get("last_scenario_log") else None),
            workspace_schema_id=(str(payload["workspace_schema_id"]) if payload.get("workspace_schema_id") else None),
            effective_workspace_root=(str(payload["effective_workspace_root"]) if payload.get("effective_workspace_root") else None),
            selected_data_root_path=(str(payload["selected_data_root_path"]) if payload.get("selected_data_root_path") else None),
            launch_warning=(str(payload["launch_warning"]) if payload.get("launch_warning") else None),
            recent_artifacts=_tuple_strings(payload.get("recent_artifacts")),
        )
