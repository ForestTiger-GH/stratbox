# Stratbox: полное исследование текущего состояния core

**Research branch:** `02-base-study`  
**Дата исследования:** 2026-10-06  
**Репозиторий:** `ForestTiger-GH/stratbox`, ветка `main`  
**Исследованный commit:** `e968853572676d8e5d963607d1f0cb50ff8f20b7`  
**Версия пакета:** `0.8.0`  
**Статус:** Research Result — описание фактического состояния и направлений развития; документ сам по себе не меняет Product/код.

---

## 0. Краткий вывод

Текущий `stratbox` уже является не набором разрозненных аналитических скриптов, а самостоятельным Python-core Strategy Box. Его конструкция читается достаточно ясно:

```text
нейтральная инфраструктура
        ↓
общие утилиты + встроенные справочники
        ↓
макроэкономические и банковские домены
        ↓
канонические данные / вычисления / проверки
        ↓
витрины, Excel и другие артефакты
```

Core отделён от пользовательской поверхности и от AppDock. Эта граница правильная: `stratbox` владеет бизнес-логикой, данными, моделями, нейтральными инфраструктурными контрактами и вычислительными операциями; UI, desktop lifecycle и платформенная упаковка находятся снаружи.

Внутри `stratbox` фактически сосуществуют несколько разных по зрелости классов систем:

1. **общая инфраструктура** — `base`, `common`, `registries`, `text`;
2. **обычные data pipelines** — `cbr_file_collector`, `escrow`, `cbr_industries`;
3. **регуляторная отчетность банков** — `cbr_forms`;
4. **файловый operational/pre-processing домен** — `frg`;
5. **отдельная вычислительно-доказательная подсистема** — `cbr_sors_restoration`.

Последняя принципиально крупнее остальных. Из примерно 0,90 МБ Python-кода `stratbox.macrobanks` около 0,47 МБ приходится на `cbr_sors_restoration`. Она содержит собственную модель данных, граф количеств, provenance, fixed-point closure, sparse LP, оптимизацию, crosswalk, диагностические реестры, acceptance criteria, integration/performance tests. Архитектурно это уже subsystem внутри core, а не одна функция или parser.

Главная сила текущего `stratbox` — **правильное направление разделения ответственности**: источники, файловая среда и пользовательская поверхность постепенно отделяются от предметной логики. Лучшие домены уже строятся как `Request → Result`, возвращают структурированные ошибки и не заставляют внешний caller знать внутреннее устройство расчёта.

Главная слабость — **неравномерность архитектуры**. Одни домены уже используют зрелые контракты, другие всё ещё отдают словари и DataFrame без единого operation contract; одни разделяют discovery/download/parse/view/export, другие сразу ведут к Excel; тестовый контур очень концентрирован; справочники обновляются вручную; optional dependencies описаны неполно; отсутствует автоматизированный CI-контур; public documentation местами содержит слишком окружно-специфичные детали и уже расходится с фактической структурой проекта.

Следующий этап развития стоит строить не вокруг добавления ещё большего количества отдельных скриптов, а вокруг **нормализации core как системы предметных операций, источников, контрактов, provenance и артефактов**.

---

# 1. Метод исследования и иерархия источников

Исследование выполнялось одновременно сверху вниз и снизу вверх.

## 1.1. Сверху вниз

Изучены:

- корневое описание продукта;
- архитектурная документация;
- engineering/workspace passport;
- назначение активной Research-ветки `02-base-study`;
- упаковка и зависимости;
- README доменов;
- документация SORS restoration;
- текущая граница между core и внешними surface/runtime слоями.

Цель верхнего прохода — понять, **каким `stratbox` заявляет себя как система**.

## 1.2. Снизу вверх

Проверены:

- фактическое дерево `src/stratbox`;
- public `__init__` и экспортируемые API;
- dataclass-контракты;
- FileStore и IO API;
- сетевой слой;
- реестры и встроенные ресурсы;
- каждый текущий домен `macrobanks`;
- parsers, registries, operations, exports;
- тесты, smoke/integration/performance checks;
- примеры;
- release/import scripts.

Цель нижнего прохода — понять, **что реально существует в коде**, независимо от деклараций документации.

## 1.3. Исторические материалы

`01-old-notes` использован только как источник прежних гипотез. Текущая реализация имеет приоритет.

Это важно, потому что часть старых идей предполагала размещение продуктовой пользовательской поверхности непосредственно внутри `stratbox`. Текущая архитектура это уже отвергла: core и surface разделены. Эту часть старых материалов следует считать исторической.

При этом несколько старых выводов подтвердились текущим кодом:

- доменным операциям нужен более единообразный публичный контракт;
- `Request → Result` лучше случайных словарей;
- FRG хорошо подходит как пилот унификации операций;
- после нормализации доменов имеет смысл единый registry канонических операций;
- файловая и сетевая среда должны оставаться ниже доменной логики.

## 1.4. Внешняя сверка

Дополнительно проверены официальные актуальные источники Банка России и Росстата. Они использованы только для вопросов свежести источников, изменения схем и потенциального расширения данных. Внешние источники не заменяли анализ репозитория.

---

# 2. Репозиторий как целое

## 2.1. Физический размер и состав

На исследованном commit в дереве находится **285 файлов**.

| Раздел | Файлов |
|---|---:|
| `src/` | 212 |
| `tests/` | 28 |
| `docs/` | 18 |
| `examples/` | 13 |
| `_mw/` | 8 |
| `scripts/` | 2 |
| корневые служебные файлы | остальное |

Python-код основных зон:

| Зона | Python-файлов | Примерный размер |
|---|---:|---:|
| `base` | 42 | 104 КБ |
| `common` | 3 | 5 КБ |
| `macrobanks` всего | 126 | 899 КБ |
| └ `cbr_file_collector` | 7 | 30 КБ |
| └ `cbr_forms` | 25 | 119 КБ |
| └ `cbr_industries` | 11 | 139 КБ |
| └ `cbr_sors_restoration` | 54 | 470 КБ |
| └ `escrow` | 12 | 65 КБ |
| └ `frg` | 16 | 72 КБ |
| `registries` | 4 | 21 КБ |
| `text` | 2 | 11 КБ |
| тесты | 28 | 170 КБ |

Профиль показывает, что `stratbox` — прежде всего **доменная библиотека**. Инфраструктура сравнительно компактна, основная масса системы сосредоточена в банковской и макроэкономической логике.

## 2.2. Граница продукта

Фактическая граница:

```text
stratbox
├─ предметная бизнес-логика
├─ нейтральная инфраструктура
├─ встроенные справочники и модели
├─ работа с внешними статистическими источниками
├─ вычислительные методы
├─ формирование данных и артефактов
└─ стабильная extension/runtime boundary

вне stratbox
├─ desktop/UI
├─ lifecycle приложения
├─ AppDock surface
└─ окружно-специфичные реализации
```

В репозитории уже есть release-integrity check, который защищает core от возврата app/AppDock surface внутрь него.

## 2.3. Что `stratbox` сегодня по сути

Наиболее точное определение:

> `stratbox` — библиотечное аналитическое ядро для получения, нормализации, проверки, моделирования и преобразования внешних макроэкономических и банковских данных в структурированные данные и воспроизводимые артефакты.

У него уже присутствуют четыре класса ответственности:

- **transport** — получить и сохранить данные;
- **semantic normalization** — понять источник и получить canonical data;
- **domain operations** — выполнить предметный use case;
- **analytical reconstruction** — вывести новые значения из неполных официальных наблюдений с контролем доказательности.

Последний класс выводит `stratbox` за пределы обычного ETL.

---

# 3. Архитектура сверху вниз

Фактическая структура пакета:

```text
stratbox
├─ base
├─ common
├─ macrobanks
├─ registries
└─ text
```

### `base`

Нейтральная инфраструктура:

- файловая абстракция;
- IO форматов;
- HTTP/URL;
- secrets contract;
- runtime provider selection;
- Excel styles;
- optional dependency helpers;
- временные рабочие каталоги.

### `common`

Общие утилиты. Сейчас практически один содержательный блок — временные периоды.

### `registries`

Встроенные reference data: банки, aliases/replacements, legacy/standard списки, ОКВЭД2, resource loader.

### `text`

Текстовая нормализация. Текущая реальная ответственность — канонизация банковских названий.

### `macrobanks`

Основной доменный слой:

```text
cbr_file_collector
cbr_forms
cbr_industries
cbr_sors_restoration
escrow
frg
```

---

# 4. Сквозной data flow

Хотя домены реализованы по-разному, из кода выводится единая естественная модель:

```text
Source Catalog / Discovery
        ↓
Fetch / Cache
        ↓
Raw Source Preservation
        ↓
Parse / Physical Normalize
        ↓
Semantic Canonical Data
        ↓
Validation
        ↓
Derived / Reconstruction
        ↓
Views / Pivots
        ↓
Export / Artifact
```

Не каждому домену нужны все стадии:

- `cbr_file_collector` заканчивается примерно на raw preservation;
- FRG решает catalog/selection/file operations;
- `escrow` проходит почти всю цепочку;
- `cbr_forms` строит physical data → semantic model → canonical long → Excel;
- SORS добавляет огромный mathematical inference layer.

Главный будущий ориентир — **унифицировать названия и контракты стадий, не заставляя все домены искусственно иметь одинаковую внутреннюю реализацию**.

---

# 5. `stratbox.base`: инфраструктурный фундамент

## 5.1. FileStore

`FileStore` — один из главных контрактов проекта. Он абстрагирует:

- open read/write;
- exists/is_file/is_dir;
- stat/listdir;
- makedirs;
- remove/rmdir/rmtree;
- rename;
- bytes read/write;
- copy;
- walk;
- glob.

Локальная реализация — `LocalFileStore`.

Это сильное решение: предметный код может работать с логическими путями без знания физического storage backend.

Потенциальные нейтральные расширения:

- atomic write;
- checksum;
- metadata/etag;
- stream read/write;
- copy between stores;
- capability discovery;
- temp→commit write для артефактов.

## 5.2. IO API

`stratbox.base.ioapi` реализует форматный слой поверх FileStore.

Текущие модули:

```text
archives bytes csv dbf docx excel excel_xls excel_xlsb excel_xlsm
excel_xlsx images pdf pptx rar txt xml zip
```

| Формат | Read | Write | Особенности |
|---|---|---|---|
| bytes | да | да | базовый транспорт |
| CSV | да | да | pandas |
| XLSX | да | да | основной Excel |
| XLSM | да | да | поверх XLSX-механики |
| XLS | да | да | optional dependencies |
| XLSB | да | нет | write явно `NotImplemented` |
| DBF | да | да | собственная обвязка |
| TXT/XML | да | да | базовые wrappers |
| ZIP | да | да | memory-oriented utilities |
| RAR | да | — | optional runtime |
| PDF | текст | нет | optional reader |
| DOCX | текст | простой DOCX | optional package |
| PPTX | текст | простая презентация | optional package |
| images | PIL | PIL | optional Pillow |

### Dependency gap

`pyproject.toml` декларирует меньше optional dependencies, чем фактически умеет IO API. Это означает, что API и installation contract сейчас расходятся.

Целевой вариант — явная capability/dependency matrix либо extras уровня `documents`, `images`, `excel-legacy`, `archives`, `pdf`, `sors-restoration`.

## 5.3. Runtime boundary

Архитектурная схема правильная:

```text
domain
   ↓
base contract
   ↓
runtime provider
   ↓
actual environment
```

При этом граница реализована не полностью единообразно: часть public core обращается к extension layer конкретнее, чем требуется идеальному нейтральному ядру.

Целевое правило:

> `stratbox` знает только собственные Protocol/entry-point contracts; конкретные внешние реализации полностью остаются за границей репозитория.

## 5.4. Network layer

`base.net` содержит URL normalization и `download_bytes`. `DownloadResult` возвращает status, content, error, final URL и headers; есть retries/backoff/min-size check.

Это хороший низкоуровневый contract, но пока не полноценная модель source snapshot.

Полезный общий контракт:

```text
SourceRequest
SourceResponse
source_id
requested_url
final_url
fetched_at
status
content_type
content_length
sha256
etag
last_modified
validation_status
cache_status
```

## 5.5. Secrets

Есть общий `SecretProvider`. Для public core это правильный уровень абстракции.

## 5.6. Excel styles

`base.styles.excel` уже имеет `FontTheme`, `BlockStyle`, `StyleSpec`, builtin presets, registry и `apply_preset`.

Проблема — домены пользуются этим неодинаково: escrow, например, содержит собственные hardcoded font/fill/border/width rules.

Целевой принцип: domain описывает semantic workbook structure, общий style layer отвечает за visual tokens/presets.

---

# 6. `stratbox.common`

Сейчас основной модуль — `common/time/periods.py`:

- Y/Q/M/W/D;
- anchor `start/end`;
- step;
- `PeriodSpec`;
- `period_points`;
- `period_spec_points`.

Минимализм здесь полезен. `common` не превратился в dumping ground.

Добавлять сюда стоит только реально cross-domain сущности: stable date IDs, общие identity/hash helpers, provenance basics, возможно generic geography IDs.

---

# 7. `stratbox.registries`

## 7.1. Текущая роль

`registries` хранит reference data вместе с пакетом и код их загрузки:

- реестр банков Банка России;
- aliases/replacements;
- standard/legacy lists;
- ОКВЭД2 Росстата.

Это позволяет работать offline после установки.

## 7.2. Bank registry

Код выбирает packaged XLSX snapshot, нормализует REGN и имена, использует alias/canonical registries.

Текущий bundled bank snapshot соответствует февралю 2026 года, тогда как официальный сайт ЦБ на дату исследования показывает информацию по кредитным организациям по состоянию на **04.10.2026**.

Это не доказывает, что каждое значение bundled snapshot уже неверно. Это показывает отсутствие формального **freshness contract**.

## 7.3. ОКВЭД2

В resource tree лежит snapshot с именем, соответствующим **01.11.2025**. Росстат на **02.10.2026** публикует ОКВЭД2 с изменениями **1/2015–91/2026**.

Это уже архитектурно важно, особенно потому что ОКВЭД2 участвует в SORS.

## 7.4. Целевая модель registry asset

```text
registry_id
source_authority
source_url
source_version
source_published_at
downloaded_at
sha256
effective_from
effective_to
schema_version
transform_version
```

После этого любой результат сможет отвечать на вопрос: **какая версия справочника использовалась при его построении?**

---

# 8. `stratbox.text`

`text.banks` реализует развитую нормализацию названий банков:

1. чистка пробелов, тире, кавычек и мусора;
2. нормализация организационно-правовых форм;
3. специальные варианты;
4. управление размещением OPF;
5. удаление краевого слова «банк»;
6. canonical alias replacement из registry.

Поддерживаются scalar, list/tuple, pandas Series и Index.

Слой стоит сохранять узким: generic text normalization, а не предметные classifiers/parsers.

---

# 9. `stratbox.macrobanks`: карта зрелости

| Домен | Что делает | Текущая зрелость | Главный следующий шаг |
|---|---|---|---|
| `cbr_file_collector` | сохраняет официальные raw-файлы | хороший компактный pipeline | versioned source catalog + tests |
| `cbr_forms` | DBF → semantic canonical long → Excel | зрелый, но формы неоднородны | довести формы до модели 802 |
| `cbr_industries` | SORS XLSX → long → derived → pivots → workbook | зрелый single-series шаблон | generalize на несколько series |
| `cbr_sors_restoration` | evidence-preserving reconstruction | очень зрелая специализированная подсистема | performance/caching + registry governance |
| `escrow` | discovery → history → views → workbook | хороший pipeline | tests + region registry + shared styles |
| `frg` | catalog/latest/cleanup/archive | полезный stage 1, parsers пока stub | canonical operations + реальные parsers + tests |

---

# 10. `cbr_file_collector`

Домен скачивает и сохраняет **исходные** статистические файлы ЦБ, сознательно не занимаясь parsing/analytics.

Есть typed contracts для registry item, request, downloaded source, collected file, failure и result.

Текущий built-in registry содержит **41 источник**, включая ипотеку, корпоративное кредитование, МСП, долговые бумаги, средства клиентов, депозиты, escrow, бюджеты, household statistics, monetary aggregates, банковские surveys, внешний долг и валютный курс.

Поток:

```text
registry item
   ↓
download
   ↓
reject HTML/error payload
   ↓
resolve filename
   ↓
deduplicate filename
   ↓
save files or ZIP
   ↓
structured result
```

Сильные стороны:

- raw source сохраняется без преобразования;
- ошибки представлены данными;
- используется FileStore;
- есть stable `source_id`;
- download и save разделены.

Ограничения:

- source catalog статичен;
- нет freshness/change detection;
- нет общего source manifest;
- нет dedicated tests;
- registry metadata минимальна.

Этот домен — естественная база общего `sources` layer.

---

# 11. `cbr_forms`

## 11.1. Текущий охват

Поддерживаются формы 101, 102, 123, 135, 802, 805.

Наиболее развитая — **802**.

## 11.2. Архитектура

```text
официальный archive/DBF
        ↓
physical parser
        ↓
physical normalized data
        +
semantic CSV model
        ↓
canonical long
        ↓
view profile
        ↓
Excel
```

Это сильная модель, потому что отделяет physical schema от semantic identity и presentation.

## 11.3. Semantic model

Каждая форма имеет CSV общей схемы:

```text
form, order, id, kind, dataset, source_code, parent_code,
measure, name, expression, section, unit, params
```

Kinds:

- `direct`;
- `formula`;
- `passthrough`.

Canonical long использует `IndicatorId` вместо русского label как identity. Это правильный дизайн и хороший шаблон для других доменов.

## 11.4. 802 как архитектурный эталон

802 имеет:

- 86 строк основной формы;
- иерархию `parent_code`;
- physical raw channels;
- строгую семантику `blank != 0`;
- quarterly cadence;
- hierarchical Excel profile;
- `Обзор`, `Полная форма`, `Данные`;
- canonical long.

Официальная страница ЦБ подтверждает изменение схемы 0409802 с 01.04.2026. Текущий parser уже учитывает исторические различия physical fields — хороший пример schema-evolution aware design.

## 11.5. 135 и 805

Они уже переведены на общий direct dataset mechanism.

## 11.6. 101, 102, 123

Их старая расчетная логика сохранена, хотя semantic CSV и stable IDs уже введены. Это основной внутренний migration path.

## 11.7. Дальнейшее развитие

Естественные расширения:

- полный passthrough 101;
- полный passthrough 102;
- полный официальный каталог 123;
- дополнительные datasets/measures 135;
- остальные разделы 805.

Официальная страница ЦБ также публикует **0409803 — консолидированный отчет о финансовых результатах** рядом с 0409802 и 0409805. Если consolidated reporting входит в scope, 803 является естественным следующим кандидатом.

## 11.8. Архитектурная доработка

Главный public entry-point сейчас — `run_all_forms_to_xlsx`. Удобно, но data-building и export слишком близки.

Желательная форма:

```text
discover/fetch
   ↓
build_form_data
   ↓
FormDataResult
   ↓
build_form_views
   ↓
export_form_workbook
```

`run_all_forms_to_xlsx` тогда остается convenience wrapper.

---

# 12. `cbr_industries`

Домен назван широко, но сейчас фактически специализируется на одной серии: `01_05_A_Debt_corp`.

Pipeline:

```text
discover official links
        ↓
download/cache
        ↓
parse workbook
        ↓
validate
        ↓
normalized stream
        ↓
derived industries
        ↓
pivot set
        ↓
CBR-like workbook
```

Есть зрелые typed contracts для source links, download, failures, validation, stream build, derived calculation, pivots и workbook export.

### Geography

Зафиксирован reference layout:

- reference date `2026-06-01`;
- expected count 96;
- normalization к current local layout.

Это работает, но подсказывает будущий architectural owner: geography должна стать versioned reference dimension.

### Derived logic

В домене живут вычисляемые отрасли, включая АПК, с проверкой полноты компонент. Это правильное место для предметной формулы.

### Tests

Есть **22 unit tests**, которые покрывают discovery, parsing, geography, cache, dtypes, validation, pivots, partial policy, derived formulas и export.

### Потенциал

Логично превратить current single-series implementation в series-adapter pattern:

```text
CbrIndustrySeriesSpec
├─ source discovery
├─ parser
├─ schema
├─ geography semantics
├─ metrics
└─ export profile
```

Обобщение стоит подтверждать вторым реальным series, а не строить абстракцию заранее.

---

# 13. `cbr_sors_restoration`: отдельная подсистема

## 13.1. Масштаб

- 54 Python-файла;
- ~470 КБ кода;
- специализированный docs tree;
- 76 test functions с integration/performance;
- optional LP solver;
- собственные registries/resources;
- собственная evidence hierarchy;
- собственные result/audit grids.

Это полноценный внутренний subsystem.

## 13.2. Цель

Основной user-facing результат:

```text
CORPORATE_TOTAL × region × OKVED2 class × metric
```

SME и SME_IE используются как constraint scopes.

## 13.3. Latent model

```text
SME_IE <= SME <= CORPORATE_TOTAL
```

На уровне каждого `region × class` есть четыре непересекающихся компонента:

```text
performing_rub
overdue_rub
performing_fx
overdue_fx
```

Из них формируются шесть пользовательских метрик:

```text
debt_rub
overdue_rub
debt_fx
overdue_fx
debt_total
overdue_total
```

Размер модели, зафиксированный real tests:

- 85 атомарных регионов;
- 88 классов ОКВЭД2;
- 3 scopes;
- **89 760** atomic component quantities;
- **134 640** region-class metric quantities;
- **44 880** user-facing corporate cells.

## 13.4. Главная методологическая идея

Система различает:

- latent money — скрытую реальную величину;
- published integer — округленное значение ЦБ.

Публикация `6 млн руб.` означает bucket около `[5.5; 6.5)`, а не обязательное `x = 6`.

Отсюда следует запрет на наивную арифметику опубликованных агрегатов: exact additive relations существуют на уровне latent quantities, а independently rounded representatives могут не складываться точно.

## 13.5. Deterministic fixed point

Перед Solver выполняется цикл:

```text
interval closure
    ↕
publication bucket facts
    ↕
source-preserving inheritance
    ↕
dominance
```

до fixed point.

## 13.6. Source-preserving inheritance

Unknown child нельзя просто приравнять к parent value из условия нулевых siblings. Используются Published Mass Tokens и complete/disjoint partitions. Это один из наиболее сильных элементов проекта с точки зрения доказательности.

## 13.7. Evidence/provenance

Факт хранит evidence method, assumption tier, proof/source IDs, supporting partitions, bounds, publication status и accepted flags.

Тиры:

```text
STRICT_OFFICIAL
SOURCE_PRESERVING
ROUNDING_OPTIMAL
ROUNDING_PREFERRED
ROUNDING_SELECTED
```

Слабая premise не может автоматически стать сильным выводом.

## 13.8. Strict LP и global feasibility

После deterministic closure строится sparse LP по scopes, exact relations, source intervals, dominance и dynamic metric rows. До принятия результата выполняется global feasibility gate.

## 13.9. Optimization

Поддерживаются:

1. target min/max;
2. minimum rounding distortion;
3. optimal-face certification;
4. controlled weak selection;
5. повторный deterministic fixed point после новых фактов.

Rounding profile строится как `min L∞`, затем `min L1` без расширения официальных source intervals.

Weak selection имеет важную zero-protection: пока bucket `0` остается допустимым, положительное значение по умолчанию не выбирается слабым методом.

## 13.10. Crosswalk

Legacy→ОКВЭД2 вынесен в отдельный conditional evidence layer с versioned mapping resources. Mapping uncertainty не маскируется под official evidence.

## 13.11. Result model

Кроме основного grid система формирует:

- restored facts;
- fact ledger;
- components;
- publication partitions/tokens;
- inheritance/promotion events;
- fixed-point passes;
- optimization rounds;
- target bounds;
- rounding profiles;
- selection attempts;
- solver runs;
- conflicts.

Это гораздо сильнее простой схемы «выдать Excel».

## 13.12. Execution modes

Optimization: `none`, `targets`, `priority`, `all`.

## 13.13. Real snapshot и performance gates

Integration tests проверяют реальные 2026 snapshots при наличии source files. Ключевой acceptance case:

```text
2026-07-01
CORPORATE_TOTAL
Удмуртия
OKVED2 class 47
overdue_fx
= 6
```

Он должен восстанавливаться через multi-scope constraints без weak selection.

Performance tests задают gates для structural pass, workbook export, target budgets и crosswalk feasibility. Это именно записанные критерии, а не результаты нового запуска в рамках данного Research.

## 13.14. Потенциал SORS

### Compile/topology cache

Кэшировать topology, sparse matrices, mappings и target catalog по source/registry/config identities.

### Incremental periods

Соседние месячные наборы структурно похожи. Возможен refresh bounds поверх прежней topology, если воспроизводимость строго контролируется.

### Reproducibility manifest

Формализовать единый run manifest:

```text
core version
source hashes
registry versions
solver version
config hash
mapping version
runtime duration
result hash
```

### Property-based tests

Полезны генеративные проверки conservation, monotonicity, tier non-decrease, no false exactness, determinism.

### Internal subsystem boundary

Несмотря на размер, сейчас нет необходимости автоматически выносить SORS в отдельный репозиторий: он тесно связан с CBR data, ОКВЭД и `macrobanks`. Лучше признать его отдельной внутренней подсистемой и сохранить optional dependency boundary. Вынос оправдан только отдельным lifecycle/ownership/consumer set.

---

# 14. `escrow`

Pipeline уже очень чистый:

```text
discover
   ↓
download/cache
   ↓
parse historical workbook variants
   ↓
canonical history
   ↓
views/pivots
   ↓
xlsx/zip
```

Есть contracts для sources, failures, indicators, rows/files, history/view/export request/result.

Parser:

- ищет header;
- выбирает рабочий sheet;
- поддерживает исторические variants columns;
- классифицирует РФ/ФО/регион;
- сохраняет display order;
- отделяет failures.

Официальная страница ЦБ продолжает публиковать данные 2026 года, поэтому домен остается практически актуальным.

Главные проблемы:

- dedicated tests отсутствуют;
- workbook styles захардкожены внутри домена вместо общего style layer;
- region registry пока не стал полноценным versioned owner.

Следующие шаги:

1. fixtures разных historical layouts;
2. parser/column/region tests;
3. common geography registry;
4. shared Excel styles;
5. source manifest.

---

# 15. `frg`

FRG сейчас — **file operational stage**, а не аналитический parser.

Он выполняет:

1. scan;
2. family recognition;
3. period extraction;
4. catalog;
5. latest selection;
6. cleanup plan;
7. optional execution;
8. safe deletion rules;
9. archive of current set.

## 15.1. Family registry

Описано **14 семейств**:

```text
regional_issuance_mortgage
regional_portfolios_mortgage
regional_issuance_cards
regional_issuance
regional_portfolios
express_issuance_weekly
express_passives
express_issuance_cards
express_issuance
express_portfolios
rbm_volumes_q
rbm_portfolios_q
volumes_cards_q
mortgage_refinancing
```

Правила содержат priority, token matching, exclusions, period mode, date boundaries и parser keys.

## 15.2. Naming

FRG умеет нормализовать имена, распознавать supplier prefix, извлекать date/week, разбирать internal standard name и строить canonical filename.

## 15.3. Safety

Очень правильный паттерн:

```text
build cleanup plan
        ↓
inspect
        ↓
apply cleanup plan
```

Нераспознанные файлы защищены от удаления. Это можно сделать общим паттерном destructive operations.

## 15.4. Главный ограничитель

Все parser modules пока содержат **stub functions**.

Следовательно, FRG сегодня умеет привести файловое пространство в воспроизводимое состояние, но ещё не извлекает содержательные данные из поставок.

## 15.5. Почему FRG лучший pilot для operation architecture

Он содержит почти все типы операций: read-only scan, classification, selection, planning, destructive execution, archive artifact и будущий parsing.

Целевая форма:

```text
FrgScanRequest → FrgScanResult
FrgCleanupPlanRequest → FrgCleanupPlanResult
FrgCleanupExecuteRequest → FrgCleanupExecuteResult
FrgArchiveRequest → FrgArchiveResult
```

Dedicated FRG tests сейчас отсутствуют; их нужно построить до расширения destructive behavior и реальных parsers.

---

# 16. Public API и canonical operations

Новые домены всё чаще используют dataclass contracts: Request, Result, Failure, SourceLink, Parsed, Export.

Но umbrella API `stratbox.macrobanks` экспортирует крупные домены неравномерно. Сейчас нет ясного единого правила, что считается canonical public operation и где её находить.

Необязательно строить giant top-level API. Чистая модель:

```python
from stratbox.macrobanks.frg import ...
from stratbox.macrobanks.cbr_forms import ...
from stratbox.macrobanks.escrow import ...
```

при условии, что у каждого домена есть один явный public facade.

Поверх этого полезен **operation registry**, но только после стабилизации contracts.

Operation — не любая функция, а предметный use case со stable ID, Request/Result, side-effect profile и независимостью от UI.

Примеры:

```text
cbr.files.collect
cbr.forms.build
cbr.industries.build_stream
cbr.industries.export
escrow.build_history
escrow.export
frg.scan
frg.cleanup.plan
frg.cleanup.execute
sors.restore
sors.crosswalk
sors.export
```

Descriptor может хранить:

```text
operation_id
domain
title
request_type
result_type
side_effects
network_required
storage_required
destructive
supports_partial
artifact_kinds
```

Правильная последовательность:

```text
inventory → normalize contracts → stabilize operations → operation registry
```

---

# 17. Errors, diagnostics, progress и artifacts

Сейчас стратегии различаются:

- collector возвращает failures;
- industries имеет validation issues и policies;
- escrow поддерживает partial collection;
- SORS имеет typed conflicts, ledgers и audit grids;
- FRG возвращает табличные статусы;
- инфраструктура местами пишет сообщения напрямую.

Для общего core полезен тонкий envelope:

```text
status
warnings
failures
metrics
artifacts
diagnostics
provenance
```

Он не должен заменять богатые domain results.

Для logging желательно правило: **библиотека генерирует structured diagnostics/events; caller решает, как это показывать пользователю**.

---

# 18. Provenance как сквозная идея

SORS уже показывает очень высокий стандарт provenance. Для обычных доменов достаточно более легкой версии:

```text
sources
hashes
registry versions
stratbox version
parameters
fetch timestamps
schema versions
warnings
```

Это даст reproducibility, auditability, caching и автоматическую диагностику изменений официальных источников.

---

# 19. Tests: фактическая картина

В текущем дереве находится **132 test functions**.

| Область | Test functions |
|---|---:|
| SORS restoration, включая integration/performance | 76 |
| CBR forms | 31 |
| CBR industries | 22 |
| smoke/examples/runtime | 3 |
| FRG | 0 dedicated |
| escrow | 0 dedicated |
| CBR file collector | 0 dedicated |

Сильные области: SORS, 802/forms model, industries.

Риски: collector, escrow, FRG, большая часть base, registries freshness, самостоятельные text normalization tests.

**Важно:** в рамках этого Research тесты прочитаны, но не запускались. Наличие 132 test functions — факт; green-status suite на исследованном commit данным документом не подтверждается.

---

# 20. Verification и CI

Есть два полезных scripts:

### Release integrity

Проверяет обязательные файлы, отсутствие surface paths, игнорирование temp/venv и случайного Python bytecode.

### Internal imports

Импортирует критические core modules и ловит broken imports.

### Gap

В текущем дереве нет `.github/workflows`. В `pyproject.toml` также нет полноценной конфигурации lint/type/coverage/build automation.

Минимальный ideal CI:

```text
Python 3.10 + current stable
        ↓
install core
        ↓
release integrity
        ↓
internal imports
        ↓
unit tests
        ↓
optional-extra matrix
        ↓
build wheel
        ↓
install wheel
        ↓
smoke imports
```

Real-data/performance SORS gates могут быть manual/nightly.

---

# 21. Documentation

SORS documentation — самая зрелая: architecture, methodology, source contracts, execution modes, result grids, diagnostics, acceptance, crosswalk и implementation reports.

Root `docs/architecture.md` уже слишком краток относительно реального проекта. Он не показывает общий data flow, maturity разных domains, SORS subsystem, contracts/results/artifacts и provenance.

Public FileStore documentation требует санитарной переработки: оставить нейтральный FileStore/runtime contract и убрать окружно-специфичную конкретику.

Также есть документационный drift: `docs/files_catalog_methods.md` ссылается на IO examples как `scripts/...`, тогда как текущие файлы лежат в `examples/...`.

---

# 22. Packaging

Текущее состояние:

- setuptools;
- `src` layout;
- Python `>=3.10`;
- package data declared;
- version `0.8.0`.

Базовые dependencies: `numpy`, `pandas`, `openpyxl`, `XlsxWriter`, `requests`, `tqdm`, `beautifulsoup4`, `dbfread`.

Плюсы: src-layout, package data, тяжелый solver optional, test dependency optional.

Проблемы:

- IO optional dependencies шире pyproject;
- нет wheel/install smoke CI;
- в текущем public tree нет top-level `LICENSE`;
- нет tooling metadata lint/type;
- version дублируется в package metadata и `__version__`.

Если публичный репозиторий должен быть реально open-source reusable, лицензионную модель нужно зафиксировать отдельно: public visibility сама по себе прав на reuse не дает.

---

# 23. Внешние источники и потенциал

## 23.1. CBR SORS

Официальная страница продолжает обновляться ежемесячно и содержит длинные исторические ряды по корпоративным кредитам, МСП, депозитам, счетам, ипотеке и другим datasets. Это подтверждает большой потенциал `cbr_file_collector`, `cbr_industries` и SORS без смены authority.

## 23.2. Escrow

Официальная страница проектного финансирования содержит данные 2026 года и историю с 2019 года. Escrow стоит доводить до production-quality, а не считать разовой выгрузкой.

## 23.3. Reporting forms

Официальная страница ЦБ на 30.09.2026 публикует 101, 102, 0409802, 0409803, 0409805 и историю форматов. Source schemas реально меняются, поэтому schema versioning — базовая необходимость.

## 23.4. Bank registry

Официальная информация по кредитным организациям актуальна на 04.10.2026, bundled snapshot в core заметно старше. Нужен freshness workflow.

## 23.5. Rosstat classifiers

Росстат на 02.10.2026 публикует ОКВЭД2 с изменениями до 91/2026; bundled resource старше. Это наиболее наглядный аргумент за versioned registry updater.

---

# 24. Что уже сделано архитектурно правильно

1. Core отделен от surface.
2. FileStore абстрагирует physical storage.
3. Домены разнесены по отдельным packages.
4. Canonical long появляется раньше presentation.
5. Используются stable IDs (`IndicatorId`, `source_id`, quantity IDs).
6. Новые домены используют structured Result contracts.
7. Raw official sources сохраняются без лишней трансформации.
8. Validation всё чаще является частью domain result.
9. SORS имеет сильный provenance/evidence layer.
10. FRG использует plan/apply для destructive actions.

---

# 25. Основные слабые места и приоритет

## P0 — публичная граница

Часть public docs/runtime glue содержит окружно-специфичную конкретику. Public core следует очистить до нейтральных contracts.

## P0 — тестовый дисбаланс

FRG/escrow/collector уже рабочие домены, но dedicated tests отсутствуют.

## P0 — freshness registries

Bank/OKVED snapshots не имеют version/freshness lifecycle.

## P1 — неединый operation contract

Одни domains имеют Request/Result, другие dict/DataFrame/convenience APIs.

## P1 — смешение build и export

Особенно заметно в forms: canonical data/result должны быть first-class раньше Excel.

## P1 — optional dependency contract

IO surface шире installation metadata.

## P1 — отсутствие CI

Проверки есть локально, но current public tree их автоматически не выполняет.

## P1 — docs drift

System architecture слишком краткая, отдельные paths устарели.

## P2 — geography/classifier ownership

Несколько доменов имеют свои локальные представления географии/классификаторов.

## P2 — logging/progress

Нет единого structured event/diagnostics contract.

## P2 — operation discovery

External caller должен знать конкретные imports/functions каждого домена.

---

# 26. Предлагаемая целевая архитектура core

Это не новая большая платформа, а выпрямление уже существующих patterns:

```text
stratbox
│
├─ base
│  ├─ filestore
│  ├─ ioapi
│  ├─ net
│  ├─ runtime
│  ├─ secrets
│  ├─ styles
│  └─ diagnostics
│
├─ common
│  ├─ time
│  ├─ identity
│  └─ provenance
│
├─ sources
│  ├─ contracts
│  ├─ fetch
│  ├─ cache
│  └─ manifest
│
├─ registries
│  ├─ banks
│  ├─ okved2
│  ├─ geography
│  └─ versioning
│
├─ macrobanks
│  ├─ cbr_file_collector
│  ├─ cbr_forms
│  ├─ cbr_industries
│  ├─ cbr_sors_restoration
│  ├─ escrow
│  └─ frg
│
├─ operations
│  ├─ contracts
│  └─ registry
│
└─ text
```

Новые directories стоит материализовать только после появления реальных consumers.

---

# 27. Source contract как центральное развитие

Сегодня почти каждый домен повторяет часть одной задачи: URL, source ID, download, filename, cache, validation, error, identity.

Полезный минимум:

```text
SourceDescriptor
SourceSnapshot
SourceFetchResult
SourceValidationResult
```

`SourceDescriptor` описывает ожидание; `SourceSnapshot` — фактический полученный объект; `SourceValidationResult` — почему он допустим.

Это делает будущие source watchers простыми pure-core operations:

```text
check source → compare last snapshot → return structured change
```

Scheduler остается внешним consumer.

---

# 28. Registry lifecycle

Для каждого справочника нужен единый процесс:

```text
official source
   ↓
fetch
   ↓
validate
   ↓
normalize
   ↓
version manifest
   ↓
package resource
   ↓
tests
```

Automated updater может создавать PR, но принятие нового registry asset остается контролируемым изменением.

---

# 29. Domain-by-domain roadmap

## FRG — первый pilot

1. typed Request/Result;
2. dedicated tests;
3. canonical scan;
4. cleanup plan;
5. cleanup execute;
6. archive result;
7. parser contracts;
8. actual parsers.

## CBR file collector

1. tests;
2. enrich SourceDescriptor;
3. checksums/manifest;
4. change detection;
5. selection by tags/groups.

## Escrow

1. historical layout fixtures;
2. full tests;
3. region registry;
4. shared styles;
5. source manifest.

## CBR forms

1. split build-data/export;
2. migrate 101/102/123 to full semantic catalogs;
3. complete 135/805 datasets;
4. add 803 if in scope;
5. schema-version fixtures;
6. live-source smoke отдельно от unit suite.

## CBR industries

1. formal series spec;
2. second series as proof of abstraction;
3. versioned geography;
4. common source snapshot;
5. preserve typed contracts.

## SORS

1. keep subsystem boundary;
2. reproducibility manifest;
3. compile/topology cache;
4. benchmark datasets;
5. property-based mathematical tests;
6. registry/version integration;
7. incremental execution where mathematically safe.

---

# 30. Что не стоит делать

1. Не возвращать UI в core.
2. Не делать giant universal ETL framework.
3. Не превращать `common` в dumping ground.
4. Не скрывать provenance ради простого API.
5. Не сохранять слабые старые interfaces только ради обратной совместимости.
6. Не делать operation registry реестром всех функций.
7. Не смешивать source, semantic model и presentation.

---

# 31. Приоритетная последовательность работ

## Этап A — hygiene и воспроизводимость

1. очистить public boundary от окружно-специфичных деталей;
2. исправить stale docs paths;
3. формализовать optional dependencies;
4. добавить CI;
5. определить single version source;
6. решить license policy.

## Этап B — contracts

1. minimal operation result protocol;
2. source snapshot/provenance contract;
3. unified diagnostics conventions;
4. policy public domain facade.

## Этап C — FRG pilot

1. tests;
2. typed operations;
3. plan/execute contracts;
4. parsers.

## Этап D — закрыть test gaps

1. escrow;
2. collector;
3. FileStore/ioapi;
4. registries/text.

## Этап E — registry freshness

1. bank registry;
2. OKVED2;
3. geography;
4. version manifests.

## Этап F — forms completion

Довести остальные формы до архитектурного уровня 802 и подключать соседние официальные формы по реальному продуктовому спросу.

## Этап G — multi-series CBR data

Расширять industries/source catalog после появления общего source contract.

## Этап H — SORS acceleration

Caching/incremental optimization лучше делать после стабилизации source/registry identity, чтобы cache keys были надежными.

---

# 32. Как должен выглядеть `stratbox` после следующего большого цикла

Новый consumer должен иметь простой путь:

```text
1. Узнать доступные предметные operations.
2. Создать typed Request.
3. Запустить operation.
4. Получить typed Result.
5. Увидеть structured warnings/failures.
6. Получить canonical data и/или artifacts.
7. Получить provenance manifest.
8. Повторить run в другой среде без изменения domain code.
```

Разработчик нового domain:

```text
1. Описывает sources.
2. Реализует parsing/semantic normalization.
3. Определяет Request/Result.
4. Отделяет views/export.
5. Добавляет validation/provenance.
6. Регистрирует только устойчивые use-case operations.
7. Добавляет tests.
```

Это естественное продолжение текущего проекта, а не новая архитектура с нуля.

---

# 33. Связь с AppDock — только на уровне границы

Из внешнего базового описания AppDock следует, что AppDock занимается установкой, lifecycle, состоянием рабочей среды, действиями, результатами, recovery и host/remote scenarios.

Для `stratbox` важен один вывод:

> core должен отдавать наружу ясные операции, состояния выполнения, diagnostics и artifacts, но не принимать на себя функции платформенной оболочки.

Это полностью совместимо с operation/result architecture.

---

# 34. Итоговая оценка зрелости

Условная шкала:

```text
1 — набор скриптов
2 — модули
3 — библиотечные домены
4 — системный core с устойчивыми contracts
5 — воспроизводимая domain platform
```

Текущий `stratbox` в целом находится между **3 и 4**.

| Область | Уровень |
|---|---|
| Base FileStore/ioapi | 3.5 |
| CBR file collector | 3.5 |
| CBR forms | 3.5–4 |
| CBR industries | 4 |
| SORS restoration | 4.5 |
| Escrow | 3.5–4 |
| FRG | 3 по file stage, 1–2 по parsing |
| Registries governance | 2.5–3 |
| Testing system-wide | 3 |
| CI/release automation | 2 |
| Documentation system-wide | 3, при SORS ≈ 4.5 |

Проект уже имеет серьезное ядро. Следующий скачок качества зависит прежде всего от **системной унификации**, а не от очередной пачки независимых функций.

---

# 35. Самые важные выводы в 12 тезисах

1. `stratbox` уже самостоятельный core, а не кодовая папка desktop-приложения.
2. Главная архитектурная единица — domain package поверх нейтрального `base`.
3. FileStore — правильный фундамент переносимости.
4. Общий data pattern уже возник: source → raw → canonical → validation → derived → view → artifact.
5. 802 — лучший шаблон будущей архитектуры `cbr_forms`.
6. `cbr_industries` — хороший шаблон обычного end-to-end data domain.
7. SORS restoration — отдельная вычислительно-доказательная подсистема и самый зрелый участок core.
8. FRG — полезный файловый operational domain, но parsers пока stubs.
9. Typed Request/Result contracts доказали ценность, но применены неравномерно.
10. Встроенные registries нуждаются в version/freshness lifecycle; current bank/OKVED snapshots отстают от официальных источников.
11. Tests сильны локально, но распределены крайне неравномерно; CI отсутствует.
12. Следующий правильный этап — source/provenance contracts + canonical operations + registry governance + выравнивание доменов.

---

# 36. Следующее логичное исследование

После фиксации этого baseline имеет смысл выбрать один из двух Research tracks.

### A. Canonical Operations Architecture

- что считается operation;
- Request/Result contract;
- error/failure/diagnostic model;
- artifacts;
- provenance;
- destructive plan/apply;
- registry;
- FRG pilot.

### B. Source & Registry Architecture

- SourceDescriptor;
- SourceSnapshot;
- cache;
- checksums;
- freshness;
- schema versions;
- bank/OKVED/geography registries;
- automated update workflow;
- source-change detection.

Приоритет я бы дал **Canonical Operations Architecture**, потому что она выровняет public core boundary; затем Source & Registry Architecture даст ей воспроизводимую data foundation.

---

# Appendix A. Фактическое дерево значимых модулей

```text
src/stratbox/
├─ __init__.py
├─ base/
│  ├─ filestore/
│  ├─ ioapi/
│  ├─ net/
│  ├─ secrets/
│  ├─ styles/excel/
│  ├─ utils/
│  └─ runtime.py
├─ common/
│  └─ time/
├─ registries/
│  ├─ _loader.py
│  ├─ cbr_banks.py
│  ├─ rosstat_okved2.py
│  └─ _resources/
├─ text/
│  └─ banks.py
└─ macrobanks/
   ├─ cbr_file_collector/
   ├─ cbr_forms/
   │  ├─ common/
   │  ├─ forms/
   │  └─ models/
   ├─ cbr_industries/
   ├─ cbr_sors_restoration/
   │  ├─ crosswalk/
   │  ├─ linear/
   │  ├─ optimization/
   │  ├─ publication/
   │  ├─ registries/
   │  ├─ sources/
   │  └─ strict/
   ├─ escrow/
   └─ frg/
      └─ parsers/
```

# Appendix B. Verification tree

```text
tests/
├─ cbr_sors_restoration/
├─ integration/cbr_sors_restoration/
├─ performance/cbr_sors_restoration/
├─ smoke/
└─ unit/
   └─ macrobanks/
      └─ cbr_forms/
```

Существенный вывод: test packages сформированы прежде всего вокруг новых/сложных разработок, а не вокруг всех текущих production domains.

# Appendix C. Examples

`examples/` содержит примеры для:

- CBR file collector;
- CBR industries;
- CBR industries Colab/multi-workbook;
- SORS restoration;
- SORS crosswalk;
- SORS targets;
- escrow;
- FRG stage 1;
- FRG cleanup;
- IO API Excel;
- pandas Excel.

Отдельного простого end-to-end example для `cbr_forms` в current examples tree нет.

# Appendix D. Внешние источники сверки

1. Банк России — Сведения о размещенных и привлеченных средствах  
   https://www.cbr.ru/statistics/bank_sector/sors/

2. Банк России — Финансирование долевого строительства  
   https://www.cbr.ru/statistics/bank_sector/equity_const_financing/

3. Банк России — Отчетность кредитных организаций  
   https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/

4. Банк России — Информация о кредитных организациях  
   https://www.cbr.ru/banking_sector/credit/

5. Росстат — Общероссийские и ведомственные классификаторы  
   https://rosstat.gov.ru/classification

6. AppDock — базовое описание  
   Использовано только как внешний контекст продуктовой границы.

# Appendix E. Evidence limitations

- Репозиторий исследован на current `main` commit, указанном в шапке.
- Код, docs, tests и packaging прочитаны через GitHub repository access.
- Test suite в рамках Research не запускалась.
- Performance numbers — gates из тестов, а не новый benchmark run.
- Исторические материалы использованы только после сверки с current code.
- Внешние страницы ЦБ/Росстата использованы для current/freshness verification.
- Детали внешних закрытых реализаций намеренно исключены: для public core значима только нейтральная extension/runtime boundary.
