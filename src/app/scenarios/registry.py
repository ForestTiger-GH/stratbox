"""Загрузка сценариев приложения из JSON-ресурсов."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files

from app.core.errors import AppScenarioError
from app.scenarios.models import ScenarioSpec


@dataclass(frozen=True, slots=True)
class ScenarioRegistry:
    """Реестр сценариев приложения."""

    items: tuple[ScenarioSpec, ...]

    def enabled(self) -> tuple[ScenarioSpec, ...]:
        return tuple(item for item in self.items if item.enabled)

    def has(self, scenario_id: str) -> bool:
        return any(item.id == scenario_id for item in self.items)

    def get(self, scenario_id: str) -> ScenarioSpec:
        for item in self.items:
            if item.id == scenario_id:
                return item
        raise AppScenarioError(f"Unknown scenario: {scenario_id}")


def load_scenario_registry() -> ScenarioRegistry:
    try:
        root = files("app").joinpath("resources", "scenarios")
        scenario_files = sorted(path for path in root.iterdir() if path.name.endswith(".json"))
        scenarios = []
        for path in scenario_files:
            data = json.loads(path.read_text(encoding="utf-8"))
            scenarios.append(ScenarioSpec.from_dict(data))
    except Exception as exc:
        raise AppScenarioError("Failed to load scenario registry") from exc
    if not scenarios:
        raise AppScenarioError("Scenario registry is empty")
    return ScenarioRegistry(items=tuple(scenarios))
