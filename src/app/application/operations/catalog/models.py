from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class OperationSpec:
    id: str
    title: str
    description: str
    handler: str
    group: str = 'General'
    kind: str = 'business'
    tags: tuple[str, ...] = ()
    enabled: bool = True
    requires_workspace: bool = True
    params: tuple[object, ...] = ()
    fixed_param_values: dict[str, object] = field(default_factory=dict)
    icon: str | None = None
    order: int = 100
    group_order: int = 100
    search_aliases: tuple[str, ...] = ()
    submit_label: str = 'Запустить'
    supports_repeat: bool = True
    result_preview_kind: str = 'artifacts'
    dangerous: bool = False
    visibility_policy: str = 'default'
    default_stage_title: str = 'Выполнение'
    expected_artifact_kinds: tuple[str, ...] = ()
    log_visibility: str = 'user_visible'
    ai_visibility: str = 'structured'

    def default_params(self) -> dict[str, object]:
        defaults = {getattr(param, 'name'): getattr(param, 'default') for param in self.params}
        defaults.update(self.fixed_param_values)
        return defaults

    def visible_params(self) -> tuple[object, ...]:
        return self.params

    def resolve_params(self, params: dict[str, object] | None = None) -> dict[str, object]:
        resolved = {getattr(param, 'name'): getattr(param, 'default') for param in self.params}
        resolved.update(params or {})
        resolved.update(self.fixed_param_values)
        return resolved


@dataclass(frozen=True, slots=True)
class OperationRegistry:
    items: tuple[OperationSpec, ...]

    def enabled(self) -> tuple[OperationSpec, ...]:
        return tuple(item for item in self.items if item.enabled)

    def has(self, operation_id: str) -> bool:
        return any(item.id == operation_id for item in self.items)

    def get(self, operation_id: str) -> OperationSpec:
        for item in self.items:
            if item.id == operation_id:
                return item
        raise KeyError(f'Unknown operation: {operation_id}')
