# Критерии принятия

Базовая РКВС попадает в Fact Ledger только если:

1. исходные книги распознаны и прошли validation;
2. география атомарна и взаимоисключающая;
3. округление представлено семантическими интервалами;
4. глобальная STRICT feasibility подтверждена;
5. deterministic closure либо локальная target system доказала одно значение;
6. служебные экстремальные задачи завершены полностью, если они требовались;
7. значение является точкой или одним публикационным bucket;
8. сохранены proof IDs и evidence metadata.

При нескольких допустимых опубликованных значениях:

```text
value = NULL
cell_resolution_status = MULTIPLE_FEASIBLE_VALUES
```

При недоступном Solver closure-границы сохраняются для диагностики, однако:

```text
facts_ledger_grid = empty
current_component_facts_grid = empty
```

Crosswalk-факт допускается только в собственном evidence layer после подтверждённой feasibility mapping-сценария. Benchmark и первая найденная таблица не являются фактами.
