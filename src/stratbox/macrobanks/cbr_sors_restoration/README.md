# CBR SORS Restoration

Домен восстанавливает доказуемую часть региональной статистики задолженности юридических лиц и ИП по классам ОКВЭД2 из пересекающихся публикаций Банка России.

## Два доказательных слоя

### STRICT

Использует только непосредственно опубликованные ограничения:

- региональные итоги из `01_05_A`;
- национальные классы ОКВЭД2 из `01_02_C`;
- федеральные округа × разделы ОКВЭД2 из `01_03_C`;
- национальные итоги;
- неотрицательность и публикационное округление.

### CROSSWALK

Добавляет условную систему соответствий старой и новой классификаций. Для каждого допустимого перехода создаётся поток:

```text
регион × старый атом × класс ОКВЭД2 × денежный компонент
```

Одна и та же переменная входит:

- в опубликованную сумму старой отрасли как исходящий поток старого атома;
- в опубликованную сумму нового класса как входящий поток класса;
- в региональные, окружные и национальные агрегаты.

Поэтому crosswalk является системой уравнений сохранения денежной массы, а не целевой функцией выбора удобного профиля.

Пример сценария `core`:

```text
старое узкое сельское хозяйство = класс 01
старое широкое сельское хозяйство и лес = классы 01 + 02
следовательно, лесной остаток = класс 02
```

## Правило принятия значения

Для каждой целевой ячейки вычисляется полный допустимый интервал:

```text
lower = min(value)
upper = max(value)
```

`value` заполняется только при одновременном выполнении условий:

1. вся выбранная система уравнений совместима;
2. min/max подтверждены либо безопасно схлопнуты интервальным замыканием;
3. диапазон является точкой или целиком округляется в один публикационный миллион.

При широком диапазоне:

```text
value = NULL
lower_bound = ...
upper_bound = ...
identification_status = ...BOUNDED
```

В основном crosswalk-контуре отсутствуют:

- optimizer-selected benchmark value;
- универсальный безымянный fallback residual;
- повышение одной найденной таблицы до восстановленного факта.

## Основной API

```python
from stratbox.macrobanks.cbr_sors_restoration import (
    SorsCrosswalkConfig,
    SorsRunConfig,
    SorsSourceFiles,
    SorsTargetScope,
    run_sors_crosswalk,
    run_sors_restoration,
)

strict = run_sors_restoration(
    SorsSourceFiles(
        regional_traditional="01_05_A.xlsx",
        national_okved2="01_02_C.xlsx",
        federal_district_okved2="01_03_C.xlsx",
        national_traditional="01_02_A.xlsx",
    ),
    SorsRunConfig(as_of_date="2026-06-01"),
)

crosswalk = run_sors_crosswalk(
    strict,
    SorsCrosswalkConfig(
        mode="targets",
        scenario_ids=("core",),
        scope=SorsTargetScope(
            region_names=("Белгородская область",),
            class_codes=("01", "02"),
        ),
    ),
)

crosswalk.regional_okved2_grid
crosswalk.crosswalk_facts_grid
crosswalk.crosswalk_bounds_grid
crosswalk.scenario_bounds_grid
crosswalk.mapping_edges_grid
crosswalk.relations_grid
```

## Сценарии

- `core` — атомарные остаточные соответствия: forestry→02, construction_other→43, mining_other→08 и т.д.;
- `broad` — более широкий граф допустимых переходов для проверки устойчивости результата к менее точной трактовке.

Несколько сценариев объединяются через feasible envelope. Значение получает статус robust identified только тогда, когда объединённый min/max всех совместимых сценариев остаётся в одном публикационном bucket.

## Solver

Для проверки совместимости и min/max требуется официальный пакет `highspy`:

```bash
python -m pip install -e ".[sors-restoration]"
```

При его отсутствии source preparation, компиляция и интервальное замыкание доступны, однако crosswalk-значения остаются provisional и не попадают в финальные восстановленные факты.
