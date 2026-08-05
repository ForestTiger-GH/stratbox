# SORS Restoration — актуальная методика

Этот путь сохранён как стабильная точка документации. Актуальная реализация версии **0.3.1** описана в:

- `docs/SORS_RESTORATION_METHOD_V2.md`;
- `src/stratbox/macrobanks/cbr_sors_restoration/README.md`.

Версия 0.3.1 строго разделяет:

- `facts_grid`: опубликованные и только STRICT-восстановленные значения;
- `estimates_grid`: условные результаты minimum-reclassification bridge;
- `bounds_grid`: strict-диапазоны;
- `bridge_bounds_grid`: диапазоны по всему множеству глобально оптимальных bridge-решений.

Прежние singleton/local-profile shortcuts удалены.
