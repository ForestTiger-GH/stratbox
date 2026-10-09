# Диагностика

При проверке расчёта идти сверху вниз:

1. `summary.strict_status` и `conflicts_grid` — подтверждена ли latent feasibility.
2. `fixed_point_passes_grid` — сколько bounds/facts дал deterministic cycle и почему остановился.
3. `facts_ledger_grid` — точный `evidence_method`, `assumption_tier`, supersession и proof lineage.
4. `publication_tokens_grid` — root source/fact, текущий region/class support, anchor quantities и supporting partitions одного Published Mass Token.
5. `inheritance_events_grid` — локализации токена и singleton promotions; неизвестный child никогда не получает parent-value только из нулевых siblings.
6. `target_bounds_grid` — диапазоны target на соответствующей evidence surface.
7. `rounding_profiles_grid` — фактический масштаб unavoidable rounding distortion (`tau*`, `L1*`).
8. `selection_attempts_grid` — какие common-witness joint batches были приняты/отклонены.
9. `solver_runs_grid` — Solver status/runtime/iteration counts.

Если факт выглядит слишком сильным, прежде всего проверить `assumption_tier`: tier никогда не должен уменьшаться при выводе, который зависит от более слабой premise. Независимый более сильный proof может supersede старый факт и тогда tier законно снижается.
