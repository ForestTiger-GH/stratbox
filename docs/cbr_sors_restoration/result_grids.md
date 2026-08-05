# Результирующие GRID

## `regional_okved2_grid`

Основной продукт. Для одного периода всегда содержит:

```text
85 регионов × 88 классов × 6 метрик = 44 880 строк
```

Неопределённые клетки присутствуют с `value = NULL`, bounds и статусом. Важные поля:

- регион, федеральный округ, раздел и класс;
- публикационная категория и признак индивидуальной публикации;
- value / exact_value / published_value;
- lower/upper и признаки включённости границ;
- identification status;
- derivation method;
- strict, reconstructed, LP-certified и zero flags;
- proof/solve identifiers.

## Остальные таблицы

- `source_grid` — все исходные наблюдения;
- `validation_grid` — проверки источников;
- `strict_components_grid` — 29 920 скрытых компонент;
- `strict_facts_grid` — фильтр основного GRID;
- `derivations_grid` — происхождение bound updates;
- `constraints_grid`, `variables_grid` — compiled model;
- `certification_plan_grid` — план и факт выполнения целей;
- `solver_runs_grid` — каждая попытка solve;
- `conflicts_grid` — локализованные конфликты.
