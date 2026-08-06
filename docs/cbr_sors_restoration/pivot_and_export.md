# Pivot и Excel

`build_sors_pivot` принимает STRICT и CROSSWALK results. Значение `evidence_layer="PRIMARY"` использует итоговый primary grid. Можно отдельно выбрать `STRICT` или `CROSSWALK`.

`include_unidentified=False` фильтрует по `is_final_accepted`, а для старого strict-result — по `is_strict_fact`.

`export_sors_workbook` для crosswalk-result умеет добавлять:

- `Crosswalk_Facts`;
- `Crosswalk_Bounds` и `Crosswalk_Scenarios`;
- `Crosswalk_Edges` и `Crosswalk_Relations`.

Управление выполняется полями `SorsWorkbookRequest`:

```text
include_crosswalk_facts
include_crosswalk_bounds
include_crosswalk_mapping
```
