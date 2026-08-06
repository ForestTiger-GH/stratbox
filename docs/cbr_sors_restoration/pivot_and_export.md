# Pivot и Excel

`build_sors_pivot` работает с основным регионально-классовым grid и сохраняет прежние ориентации «регион → классы» и «класс → регионы».

`export_sors_workbook` может включать новые листы:

```text
Fact_Ledger
Current_Cell_Facts
Cell_Target_Plan
Cell_Attempts
Cell_Subsystems
Promotions
Fixed_Point_Passes
```

Управление выполняется полями `SorsWorkbookRequest`:

```text
include_fact_ledger
include_cell_attempts
include_cell_subsystems
include_promotion_events
include_fixed_point_passes
```

Primary grid содержит `cell_resolution_status`, `cell_largest_horizon`, `cell_attempt_id` и `cell_subsystem_id` для трассировки происхождения метрики.
