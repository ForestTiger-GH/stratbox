# Диагностика

## Глобальный STRICT status

- `OPTIMAL` — feasibility подтверждена;
- `INFEASIBLE` — несовместимость доказана;
- `SOLVER_UNAVAILABLE` — официальный HiGHS недоступен;
- `TIME_LIMIT`/`ITERATION_LIMIT` — доказательство не завершено.

Незавершённый статус не трактуется как infeasibility и блокирует продвижение Fact Ledger.

## Поклеточные статусы

`cell_attempts_grid` показывает, на каком horizon цель остановилась. `cell_subsystems_grid` позволяет проверить, какие официальные constraints вошли в локальную систему. `solver_runs_grid` содержит отдельные служебные MIN/MAX solve IDs.

## Fixed point

`fixed_point_passes_grid` содержит:

- target attempts;
- bound updates;
- new facts;
- resolved targets;
- cumulative facts;
- stop reason.

Нормальные причины остановки:

- `NO_NEW_BOUNDS_OR_FACTS`;
- `TARGET_BUDGET_EXHAUSTED`;
- `RUN_TIME_LIMIT`;
- `FIXED_POINT_PASS_LIMIT`.

## Crosswalk

Crosswalk conflicts остаются в `SorsCrosswalkResult.conflicts_grid`. Они не влияют на официальный STRICT status.
