# Критерии приёмки

Реализация считается корректной, если:

1. 85 атомарных регионов и 88 реальных классов ОКВЭД2 формируют взаимоисключающие latent cubes.
2. Внутри одной модели существуют scopes `CORPORATE_TOTAL`, `SME`, `SME_IE`; scope является частью quantity identity.
3. Пользовательский восстановленный GRID и Solver-targets формируются только для `CORPORATE_TOTAL`; SME/SME_IE остаются auxiliary constraints.
4. Официальные значения представлены собственными исходными rounding intervals; numerical tolerance не используется как экономический допуск.
5. Source interval не расширяется из-за длины пути. Накопленная неопределённость выражается диапазоном конечной РКВС.
6. Deterministic publication phase является настоящим fixed point `interval closure ↔ buckets/zeros ↔ inheritance ↔ dominance`.
7. Inheritance разрешён только внутри одного portfolio scope и только через complete/disjoint same-metric partitions.
8. Совпавшие числа разных scopes никогда не объединяются одним token; межscope-перенос происходит только через `SME_IE <= SME <= CORPORATE_TOTAL`.
9. Publication fact возвращается в latent layer bucket-ом; точкой — только строгий latent-point факт.
10. `overdue <= debt` работает как явное deterministic dominance правило и остаётся математически согласованным с non-overlapping component formulation.
11. Scope dominance работает как в deterministic closure, так и hard LP inequalities.
12. Endpoint `assumption_tier` распространяется через суммы, остатки и dominance и предотвращает provenance laundering.
13. До global feasibility факты provisional; при latent conflict accepted publication grid не формируется.
14. Targets поддерживают линейные corporate metrics, а не только base component columns.
15. Strong minimum-rounding profile минимизирует L∞, затем L1 без расширения официальных source intervals.
16. `ROUNDING_OPTIMUM_IDENTIFIED` принимается только при одном bucket на всём сильном optimal face.
17. Relaxed bucket competition может отойти от `tau_star`, но каждая исходная публикация остаётся внутри собственного hard-интервала.
18. Relaxed selection оценивает bucket по whole-model L1 source-rounding cost относительно `relaxed_l1_star`, а не по midpoint и не по числу пройденных агрегатов.
19. Controlled weak selection по умолчанию не выбирает target, пока bucket `0` остаётся допустимой альтернативой.
20. Preferred/selected buckets проходят совместную global-witness проверку; target order не легализует соседние значения greedily.
21. После каждого нового Solver/publication факта снова полностью исчерпывается deterministic publication fixed point.
22. Final `value` берётся из Fact Ledger, а latent bounds остаются отдельным audit representation.
23. Conditional crosswalk не смешивается с official/multi-scope evidence.
24. Повторный запуск на одинаковых входах детерминирован.
25. Реальный 01.07.2026 testcase должен восстанавливать `CORPORATE_TOTAL × Удмуртия × class 47 × overdue_fx = 6` через SME/SME_IE constraints, без weak rounding selection.
