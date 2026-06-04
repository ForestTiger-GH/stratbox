from __future__ import annotations

from collections import defaultdict

from app.scenarios.models import ScenarioSpec
from app.scenarios.registry import ScenarioRegistry


def group_scenarios(registry: ScenarioRegistry, *, search: str = '') -> dict[str, list[ScenarioSpec]]:
    grouped: dict[str, list[ScenarioSpec]] = defaultdict(list)
    needle = search.strip().lower()
    for scenario in registry.enabled():
        haystack = ' '.join([
            scenario.id,
            scenario.title,
            scenario.description,
            scenario.group,
            *scenario.tags,
            *scenario.search_aliases,
        ]).lower()
        if needle and needle not in haystack:
            continue
        grouped[scenario.group].append(scenario)
    return {
        group: sorted(items, key=lambda item: (item.group_order, item.order, item.title.lower()))
        for group, items in sorted(grouped.items(), key=lambda item: (min(spec.group_order for spec in item[1]), item[0].lower()))
    }
