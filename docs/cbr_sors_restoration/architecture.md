# Архитектура SORS restoration

```text
sources
  ↓
SorsSourceBundle
  ↓
strict.quantities.SorsQuantityGraph
  ├─ latent components
  ├─ region×class metrics
  ├─ published aggregates
  └─ exact additive relations
  ↓
publication.partitions.SorsPublicationGraph
  ↓
publication.closure.run_publication_fixed_point
  ├─ strict.interval_closure.SorsIntervalClosureState
  ├─ publication.ledger.SorsPublicationLedger
  ├─ publication.tokens.PublishedMassToken
  └─ publication.inheritance
  ↓
strict.compiler.StrictCompilation
  ├─ sparse latent LP
  ├─ stable dynamic rows for every region×class×metric publication bound
  └─ unified metric/component target catalog
  ↓
strict.solver feasibility gate
  ↓
optimization.engine
  ├─ targets min/max
  ├─ distortion L∞ → L1
  ├─ optimal-face min/max
  └─ joint selection
  ↓
result_grid
```

## Publication layer

`publication/` владеет значением опубликованного числа и его provenance. Он не решает LP. `SorsPublicationLedger` является authoritative source финального `value`; result grid больше не пытается заново «угадать факт» только по финальному latent interval.

`publication/partitions.py` строит два типа complete/disjoint same-metric partitions: иерархию между официальными published aggregates и связи official aggregate→region×class targets. Иерархические partitions имеют две независимые роли: (1) token-localization на уровне publication representatives и (2) exact latent sum relations для interval closure. Во второй роли складываются скрытые денежные quantities, а не округлённые integers, поэтому расхождение вида `6 + 5 ≠ 10` в опубликованных таблицах остаётся допустимым. `publication/tokens.py` хранит support одной видимой опубликованной массы. Inheritance требует явного child=`v` и zero siblings; `parent=v + zeros` без matching child никогда не создаёт новое число. `METRIC_COMPONENT_SUM` участвует в interval closure/LP, но не в token inheritance.

## Strict layer

`strict/` означает latent continuous model, а не «единственный допустимый тип результата». Quantity graph и closure сохраняют официальную точность округления. Compiler удаляет только истинные latent points; publication buckets остаются bounded latent constraints. Для каждой пользовательской `region×class×metric` заранее существует стабильная dynamic Solver-row: когда inheritance/optimization создаёт новый bucket, `refresh_strict_problem_bounds()` обновляет не только component column bounds, но и границы линейной суммы компонентов. Поэтому следующий LP сохраняет всю корреляцию нового publication fact, а не только её проекции на отдельные компоненты.

## Optimization layer

`optimization/targets.py` работает с linear targets, а не только с одной LP-column. `distortion.py` строит augmented problem с residual variables и `tau`. `selection.py` валидирует buckets совместно. `engine.py` оркестрирует Solver tiers и каждый раз возвращается в deterministic publication fixed point.

## Удалённая старая архитектура

Прежние `strict/engine.py`, `strict/ledger.py`, `strict/cells.py`, `strict/subsystem.py`, `strict/target_solver.py`, `strict/result_grid.py` удалены. Их responsibilities распределены между `publication/`, новым `optimization/` и root `result_grid.py`.
