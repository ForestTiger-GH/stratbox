# CBR SORS Restoration — внедрение Crosswalk Relation System

Дата: 2026-08-05  
Версия Strategy Box: `0.5.0`

## Что заменено

Старый `CONDITIONAL_BRIDGE` удалён. Он выбирал minimum-reclassification profile, использовал факторизованные atom/class residuals и затем считал min/max под objective cap. Такой контур отвечал на вопрос об оптимальном benchmark-профиле, а не о полном допустимом множестве crosswalk-уравнений.

## Новая фундаментальная модель

Введён домен `cbr_sors_restoration.crosswalk`.

Каждая переменная является явным потоком:

```text
atomic region × legacy atom × allowed OKVED2 class × component
```

Legacy и OKVED2 публикации используют одни и те же flow columns с разных сторон. Это реализует сохранение массы без целевой функции и без безымянного fallback.

## Исправленная атомарная логика

Core-сценарий явно задаёт остаточные соответствия, которые старая логика пересечения множеств теряла:

- forestry→02;
- mining_other→08;
- construction_other→43;
- machinery_other→26|27;
- transport_equipment_other→30;
- transport_communications_other исключает 51;
- class 58 сохраняется у pulp/paper/publishing/printing.

Техническая категория представлена явными `TECHNICAL_UNALLOCATED` потоками. Она расширяет min/max, но не скрывается в residual objective.

## Алгоритм

1. compile explicit flow graph;
2. add legacy, national OKVED2, FD and strict component constraints;
3. deterministic residual closure;
4. feasibility;
5. direct target min/max без objective cap;
6. scenario envelope;
7. заполнение `value` только при point/published-bucket identification.

## Публичный API

Добавлены:

- `SorsCrosswalkConfig`;
- `SorsCrosswalkResult`;
- `run_sors_crosswalk`.

Удалены:

- `SorsBridgeConfig`;
- `SorsBridgeResult`;
- `run_sors_bridge`;
- пакет `bridge`.

Обратная совместимость намеренно отсутствует.

## Результаты и экспорт

Введены `crosswalk_bounds_grid`, `crosswalk_facts_grid`, `scenario_bounds_grid`, mapping/relations/variables/constraints grids. `value` остаётся пустым для широкого диапазона. Pivot и XLSX поддерживают primary crosswalk-result.

## Проверки

Добавлены тесты:

- completeness/versioning mapping resources;
- corrected residual atom destinations;
- preservation of class 58;
- absence of economic universal fallback;
- cascading residual closure;
- synthetic equation `old broad=100`, `old narrow=90` ⇒ class01=90, class02=10;
- prohibition of final value for wide interval;
- provisional result without feasibility;
- solver-unavailable result;
- full orchestration from legacy publications through feasibility to accepted crosswalk facts;
- one-sided LP bound tightening;
- robust scenario envelope that blocks acceptance while any configured scenario is unresolved.

В текущем sandbox unit/domain suite проходит. Официальный `highspy` и исходные книги Банка России в переданном архиве отсутствуют, поэтому новый полный real-data HiGHS прогон здесь не выполнялся. Реальный performance gate сохранён как opt-in тест через `STRATBOX_SORS_REAL_DATA_DIR`.

## Дополнительная доказательная защита

- При нескольких сценариях scenario-envelope считается сертифицированным только после разрешения каждого настроенного сценария: `OPTIMAL`, `INFEASIBLE` либо `INFEASIBLE_BY_CLOSURE`. Сценарий с недоступным Solver, time limit или иной незавершённостью не исключается молча и блокирует принятие robust-value.
- Для каждой crosswalk-строки сохраняются `mapping_version`, `scenario_ids`, `scenario_coverage_complete` и `supporting_relation_ids`.
- Техническая масса `completion_of_settlements` остаётся явным универсальным потоком с фиксированной опубликованной величиной. Она расширяет допустимый min/max; значение принимается только если остаётся однозначным даже при любом допустимом распределении этой технической массы.

## Фактически выполненные проверки

- `64 passed` — доменные и unit-тесты SORS/репозитория, включая полный orchestration-тест crosswalk-контура;
- `5 skipped` — real-data integration/performance gates без настроенного каталога исходных книг;
- wheel `stratbox-0.5.0-py3-none-any.whl` успешно собран;
- wheel содержит новый пакет и все crosswalk resources, старый `bridge` в wheel отсутствует;
- import из установленного wheel подтверждает версию `0.5.0` и mapping `cbr-legacy-okved2-crosswalk-2026.3`;
- независимая проверка с `scipy.optimize.linprog` на синтетической системе подтвердила feasibility и min=max: класс 01 = 90, класс 02 = 10.

Официальный Python-пакет `highspy` отсутствует для Python 3.13 в доступном package index sandbox. Production-код не переключался на внутренние SciPy bindings: зависимость от официального `highspy` сохранена намеренно. Общий smoke/import контур также блокируется существующей зависимостью `dbfread`, отсутствующей в sandbox; это не связано с новым SORS-кодом.
