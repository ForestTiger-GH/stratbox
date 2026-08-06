# Result grids

## Основной результат

- `regional_okved2_grid` — шесть пользовательских метрик по регионам и классам;
- `strict_facts_grid` — принятые STRICT-метрики;
- `strict_components_grid` — четыре базовые РКВС-компоненты и их bounds;
- `constraints_grid`, `variables_grid`, `solver_runs_grid` — математический proof trail.

## Поклеточный контур

### `facts_ledger_grid`

Append-only история продвижений базовых РКВС. Содержит supersession, precision, uniqueness basis, horizon, proof IDs и supporting relations.

### `current_component_facts_grid`

Текущая лучшая версия каждого принятого компонента.

### `cell_target_plan_grid`

Полный каталог 29 920 целей с bounds, scope, priority, cascade score, attempt count и skip reason.

### `cell_attempts_grid`

Одна строка на попытку цели: статус, самый большой horizon, факт изменения bounds, число новых каскадных фактов и runtime.

### `cell_subsystems_grid`

Размер и происхождение каждой cumulative local system:

- число constraints;
- число variables;
- nnz;
- исходные solver rows/columns;
- supporting constraint IDs.

### `promotion_events_grid`

События записи и улучшения фактов.

### `fixed_point_passes_grid`

Итоги каскадных проходов и причина остановки.

## Ключевые статусы

- `UNIQUE_FEASIBLE_VALUE`;
- `UNIQUE_AT_PUBLISHED_PRECISION`;
- `MULTIPLE_FEASIBLE_VALUES`;
- `SOLVER_INCOMPLETE`;
- `IDENTIFIED_BEFORE_SOLVER`;
- `UNRESOLVED_AT_HORIZON`;
- `UNRESOLVED_GLOBAL`.

Поля `cell_lower_solve_id` и `cell_upper_solve_id` ссылаются на реальные `solve_id` в `solver_runs_grid`.
