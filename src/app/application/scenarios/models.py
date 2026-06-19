from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ScenarioKind = Literal['atomic', 'composite', 'background', 'assignment']
ScenarioErrorPolicy = Literal['fail_fast', 'continue_with_warnings']


@dataclass(frozen=True, slots=True)
class ScenarioStepSpec:
    id: str
    operation_id: str
    title: str
    description: str = ''
    order: int = 100
    required: bool = True
    params_override: dict[str, object] = field(default_factory=dict)
    params_map: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    id: str
    title: str
    description: str
    kind: ScenarioKind
    group: str
    steps: tuple[ScenarioStepSpec, ...]
    params: tuple[object, ...] = ()
    icon: str | None = None
    order: int = 100
    group_order: int = 100
    submit_label: str = 'Запустить'
    expected_artifact_kinds: tuple[str, ...] = ()
    error_policy: ScenarioErrorPolicy = 'fail_fast'
    supports_repeat: bool = True
    supports_background: bool = False
    visibility_policy: str = 'default'

    def is_atomic(self) -> bool:
        return self.kind == 'atomic' and len(self.steps) == 1

    def default_params(self) -> dict[str, object]:
        defaults = {getattr(param, 'name'): getattr(param, 'default') for param in self.params}
        return defaults

    def visible_params(self) -> tuple[object, ...]:
        return self.params

    def resolve_params(self, params: dict[str, object] | None = None) -> dict[str, object]:
        resolved = self.default_params()
        resolved.update(params or {})
        return resolved


@dataclass(frozen=True, slots=True)
class ScenarioRegistry:
    items: tuple[ScenarioSpec, ...]

    def enabled(self) -> tuple[ScenarioSpec, ...]:
        return self.items

    def has(self, scenario_id: str) -> bool:
        return any(item.id == scenario_id for item in self.items)

    def get(self, scenario_id: str) -> ScenarioSpec:
        for item in self.items:
            if item.id == scenario_id:
                return item
        raise KeyError(f'Unknown scenario: {scenario_id}')
