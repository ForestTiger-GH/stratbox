# Pivot и Excel export

Primary pivot строится по `regional_okved2_grid`; reconstructed value уже содержит accepted publication-level facts всех официальных evidence methods.

`SorsWorkbookRequest` может дополнительно выгрузить:

```text
Restored_Facts
Fact_Ledger
Current_Component_Facts
Publication_Partitions
Inheritance_Events
Promotions
Fixed_Point_Passes
Optimization_Rounds
Target_Bounds
Rounding_Profiles
Selection_Attempts
Derivations
Constraints
Solver_Runs
Conflicts
```

Audit-листы включаются отдельными flags и не раздувают стандартный workbook без запроса.
