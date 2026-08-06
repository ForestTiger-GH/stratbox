# Result grids

## STRICT result

- `regional_okved2_grid` — полный официальный bounds/facts grid;
- `strict_facts_grid` — принятые официальные факты;
- `strict_components_grid` — компонентные bounds;
- `derivations_grid`, `constraints_grid`, `solver_runs_grid` — proof trail.

## CROSSWALK result

- `regional_okved2_grid` — primary grid: STRICT имеет приоритет, затем принятые CROSSWALK значения;
- `crosswalk_bounds_grid` — robust scenario envelope;
- `crosswalk_facts_grid` — только принятые conditional facts;
- `scenario_bounds_grid` — отдельные результаты сценариев;
- `mapping_edges_grid` — допустимые атом→класс рёбра;
- `relations_grid` — семантические conservation relations;
- `variables_grid` — явные flow columns;
- `constraints_grid` — публикационные и strict-bound строки;
- `derivations_grid` — interval closure;
- `solver_runs_grid`, `conflicts_grid`, `diagnostics_grid`, `audit_grid`.

## Ключевые флаги

- `bounds_certified` — границы опираются на подтверждённую совместимую модель;
- `value_identified` — диапазон схлопнулся;
- `is_final_accepted` — значение разрешено к использованию;
- `is_strict_fact` — официальный слой;
- `is_benchmark_estimate` — всегда `False` в основном crosswalk-контуре;
- `evidence_layer`, `evidence_profile`, `scenario_ids` — происхождение доказательства.
