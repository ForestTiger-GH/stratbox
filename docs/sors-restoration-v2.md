# SORS Restoration 0.3.1

Актуальная методика и API описаны в:

- `src/stratbox/macrobanks/cbr_sors_restoration/README.md`;
- `docs/SORS_RESTORATION_METHOD_V2.md`.

Ключевое правило версии 0.3.1: условные bridge-значения не входят в `facts_grid`; их диапазоны рассчитываются по всему множеству глобально minimum-reclassification решений и сохраняются отдельно.
