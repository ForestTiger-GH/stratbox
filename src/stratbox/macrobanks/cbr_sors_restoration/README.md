# CBR SORS Restoration

Домен восстанавливает доказуемую часть региональной статистики кредитного портфеля юридических лиц и ИП по классам ОКВЭД2 из пересекающихся публикаций Банка России.

## Главный принцип

Результат считается strict-фактом только тогда, когда все допустимые таблицы, совместимые с официальными публикациями, дают для клетки одно точное значение или один и тот же публикационный bucket. Модельная оценка conditional bridge хранится отдельно.

## Источники

Обязательные книги:

- `01_05_A` — регионы × традиционная классификация;
- `01_02_A` — Россия × традиционная классификация;
- `01_02_C` — Россия × ОКВЭД2;
- `01_03_C` — федеральные округа × разделы ОКВЭД2.

Опционально:

- `01_05_D` — региональные итоги и история; используется для проверки и будущего аналитического prior, но не дублирует strict-ограничения.

## Производственный процесс

```text
Excel
→ source GRID
→ валидация
→ атомарные регионы и 88 классов ОКВЭД2
→ quantity/relation graph
→ deterministic interval closure
→ strict feasibility
→ пакетная min/max-сертификация
→ closure после каждого batch
→ полный Regional OKVED2 GRID
→ Pivot / Excel
```

Conditional bridge запускается отдельной операцией и никогда не блокирует strict-result.

## Основной API

```python
from stratbox.macrobanks.cbr_sors_restoration import (
    SorsRunConfig,
    SorsSourceFiles,
    run_sors_restoration,
)

result = run_sors_restoration(
    SorsSourceFiles(
        regional_traditional="01_05_A.xlsx",
        national_okved2="01_02_C.xlsx",
        federal_district_okved2="01_03_C.xlsx",
        national_traditional="01_02_A.xlsx",
        regional_totals_history="01_05_D.xlsx",
    ),
    SorsRunConfig(as_of_date="2026-06-01"),
)

result.regional_okved2_grid
result.strict_facts_grid
result.validation_grid
result.derivations_grid
result.summary
```

Для strict-feasibility и min/max нужен официальный `highspy`. При его отсутствии source preparation и closure завершаются, а идентифицированные клетки сохраняются как provisional до подтверждения общей совместимости.

Подробная документация находится в `docs/cbr_sors_restoration/`.
