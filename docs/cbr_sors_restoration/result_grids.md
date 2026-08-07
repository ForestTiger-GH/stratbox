# Result grids

## `regional_okved2_grid`

Главный GRID: region × class × metric. `value` берётся из текущего accepted Publication Fact Ledger.

Ключевые поля:

```text
value
publication_status
latent_status
evidence_method
assumption_tier
evidence_strength
lower_bound / upper_bound
source_observation_ids
supporting_partition_ids
supporting_fact_ids
proof_ids
is_primary_fact
is_final_accepted
```

## `restored_facts_grid`

Подмножество primary grid, где `is_primary_fact=True`.

## `facts_ledger_grid`

Append-only история facts, включая supersession более сильным доказательством той же publication value.

## `components_grid`

Внутренние четыре component quantities с latent bounds, endpoint provenance и publication facts.

## Audit grids

- `publication_partitions_grid` — complete/disjoint partitions, через которые разрешена token-localization;
- `publication_tokens_grid` — текущие supports и lineage Published Mass Tokens;
- `inheritance_events_grid` — цепочки source-preserving наследования;
- `promotion_events_grid` — все promotion/supersession событий ledger;
- `fixed_point_passes_grid` — deterministic publication passes;
- `optimization_rounds_grid` — outer Solver rounds;
- `target_bounds_grid` — min/max по strict/publication-constrained и rounding-optimal surfaces;
- `rounding_profiles_grid` — `tau*`, `L1*`, assumption tier;
- `selection_attempts_grid` — common-witness joint-batch validation;
- `solver_runs_grid` — feasibility/min/max/distortion/selection Solver runs;
- `conflicts_grid` — infeasibility/audit conflicts.
