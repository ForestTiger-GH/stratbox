# Архитектура CBR SORS Restoration

## Структура домена

```text
cbr_sors_restoration/
├── sources/       source adapters и canonical source bundle
├── registries/    география, ОКВЭД2, публикационные категории
├── strict/
│   ├── quantities.py     единый quantity/relation graph
│   ├── closure.py        persistent affected closure
│   ├── compiler.py       одна глобальная sparse LP
│   ├── cells.py          каталог и приоритеты РКВС
│   ├── subsystem.py      локальные cumulative horizons
│   ├── target_solver.py  внутренний uniqueness certificate
│   ├── ledger.py         append-only Fact Ledger
│   └── engine.py         поклеточный fixed-point orchestration
├── crosswalk/     отдельные условные mapping-сценарии
├── linear/        LP-контракты и официальный highspy adapter
├── contracts.py   публичные конфигурации
├── results.py     result-контракты
├── pivots.py      аналитические представления
└── export.py      XLSX-экспорт
```

## Центральный инвариант

Глобальная STRICT-модель формируется один раз из официальных публикаций. Локальная система цели получается удалением строк глобальной модели и сохранением всех переменных выбранных строк.

```text
F_global ⊆ F_local
```

Поэтому, если координата цели одинакова для всех решений `F_local`, она одинакова и для всех решений `F_global`. Локальная сертификация является доказательно безопасной, хотя ранние горизонты используют меньше уравнений.

## Публикационные endpoints

Quantity graph хранит семантические интервалы вместе с признаками достижимости endpoints. Два численных правила принципиальны:

1. Если остаточная нижняя граница отрицательна и обрезается неотрицательностью до нуля, endpoint `0` принадлежит допустимому множеству. Строгость отрицательного алгебраического остатка на ноль не переносится.
2. Не достигнутые endpoints при компиляции переводятся в закрытые Solver-bounds со сдвигом внутрь интервала на `point_tolerance`. Один `nextafter` недостаточен относительно обычной LP feasibility tolerance.

Semantic bounds не заменяются Solver-bounds и продолжают использоваться в доказательных GRID и bucket-сертификации.

## Постоянные и изменяемые части

Постоянны в рамках запуска:

- quantity IDs;
- relation graph;
- sparse matrix;
- solver-column identity;
- publication constraints.

Изменяются по мере каскада:

- bounds базовых компонент;
- Fact Ledger;
- closure derivations;
- target priority;
- набор завершённых целей.

После найденной РКВС матрица не пересобирается. Обновляются column bounds и affected closure.

## Целевая система

`SorsSubsystemBuilder` строит cumulative subsystem. Каждый следующий горизонт добавляет строки к уже выбранным строкам. `GLOBAL_CONNECTED` добавляет все строки связного компонента цели и эквивалентен последнему глобальному доказательному горизонту.

Локальные подсистемы решаются короткоживущими Solver-сессиями. Структурно одинаковые глобальные подсистемы используют persistent `SorsCellSolverPool`: модель загружается один раз, затем обновляются bounds и objective конкретной РКВС. Незавершённое направление повторяется отдельно, без пересчёта уже успешного экстремума.

## Движение факта

```text
cell proof
→ apply target bounds
→ affected closure
→ promote direct fact
→ promote cascade facts
→ update target queue
→ next fixed-point pass
```

## Crosswalk boundary

```text
STRICT не зависит от crosswalk
crosswalk получает STRICT bounds
crosswalk relation profile обязан отдельно пройти feasibility
```

Неподтверждённый или несовместимый mapping не может расширять официальный Fact Ledger.
