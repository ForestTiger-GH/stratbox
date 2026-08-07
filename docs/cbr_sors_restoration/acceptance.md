# Критерии приёмки

Реализация считается корректной, если:

1. 85 атомарных регионов и 88 реальных классов ОКВЭД2 формируют взаимоисключающий latent cube.
2. Официальные значения представлены исходными rounding intervals; numerical tolerance не используется как экономический допуск.
3. Deterministic publication phase действительно является fixed point `interval closure ↔ buckets/zeros ↔ inheritance`.
4. Inheritance разрешён только для complete/disjoint same-metric partitions; metric algebra не наследует visible published mass.
5. Publication fact возвращается в latent layer bucket-ом; точкой — только `LATENT_POINT_IDENTIFIED`.
6. Endpoint `assumption_tier` распространяется через суммы/остатки и предотвращает provenance laundering.
7. До global feasibility facts provisional; при latent conflict accepted publication grid не формируется.
8. Targets поддерживают linear metrics, а не только base component columns.
9. Minimum rounding distortion минимизирует L∞, затем L1 относительно исходных integer representatives без расширения официальных ±0.5.
10. Optimal-face fact принимается только при одном bucket на всём разрешённом face.
11. Controlled selection валидируется совместно и не зависит от порядка targets.
12. После каждого нового Solver/publication факта снова полностью исчерпывается deterministic publication fixed point.
13. Final `value` берётся из Fact Ledger, а latent bounds остаются отдельным audit representation.
14. Conditional crosswalk не смешивается с official publication evidence.
15. Повторный запуск на одинаковых входах детерминирован.
