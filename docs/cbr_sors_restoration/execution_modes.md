# Режимы исполнения

Первый deterministic publication fixed point выполняется всегда. `optimization.mode` управляет только последующим Solver-поиском.

- `none` — deterministic fixed point + global feasibility; без min/max targets.
- `targets` — только явно заданный `SorsTargetScope` по регионам/классам/метрикам.
- `priority` — до `max_targets` наиболее перспективных unresolved targets; узкие finite ranges выше широких, user-facing metrics выше internal components.
- `all` — exhaustive target catalog; `max_targets` должен быть `None`.

`include_internal_components=True` разрешает использовать компоненты как внутренние targets каскада. Основным объектом восстановления остаются шесть published metrics.

`SorsSelectionPolicy` управляет только последним controlled selection tier и никак не меняет numerical tolerance или официальный publication step.
