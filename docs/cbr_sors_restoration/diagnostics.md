# Диагностика

Crosswalk различает:

- `OPTIMAL` — feasibility подтверждена;
- `INFEASIBLE_BY_CLOSURE` — противоречие доказано до Solver;
- `INFEASIBLE` — HiGHS доказал несовместимость сценария;
- `SOLVER_UNAVAILABLE` — модель собрана, но доказательство feasibility отсутствует;
- `TIME_LIMIT`/`INCOMPLETE` — доказательство не завершено и не трактуется как infeasibility.

`conflicts_grid` хранит сценарий и конкретное ограничение. `diagnostics_grid` содержит размер модели, число closure-pass, updates, выбранных и завершённых min/max целей.
