from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProductOperationSpec:
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
    icon: str | None = None
    order: int = 100
    group_order: int = 100
    search_aliases: tuple[str, ...] = ()
    submit_label: str = 'Запустить'
    supports_repeat: bool = True
    result_preview_kind: str = 'artifacts'
    dangerous: bool = False
    visibility_policy: str = 'default'

    def default_params(self) -> dict[str, object]:
        return {getattr(param, 'name'): getattr(param, 'default') for param in self.params}


@dataclass(frozen=True, slots=True)
class ProductRegistry:
    items: tuple[ProductOperationSpec, ...]

    def enabled(self) -> tuple[ProductOperationSpec, ...]:
        return tuple(item for item in self.items if item.enabled)

    def has(self, operation_id: str) -> bool:
        return any(item.id == operation_id for item in self.items)

    def get(self, operation_id: str) -> ProductOperationSpec:
        for item in self.items:
            if item.id == operation_id:
                return item
        raise KeyError(f'Unknown product operation: {operation_id}')
