# Диагностика

Статусы Solver нормализованы: `OPTIMAL`, `INFEASIBLE`, `TIME_LIMIT`, `ITERATION_LIMIT`, `UNBOUNDED`, `ERROR`, `SOLVER_UNAVAILABLE`.

Только `INFEASIBLE` запускает elastic conflict model. Она сначала находит минимальное общее расширение интервалов, затем при этом epsilon минимизирует локальные lower/upper slacks. `conflicts_grid` показывает конкретные constraints и исходные observation IDs.

Отсутствие `highspy`, timeout или numerical failure не называются несовместимостью.
