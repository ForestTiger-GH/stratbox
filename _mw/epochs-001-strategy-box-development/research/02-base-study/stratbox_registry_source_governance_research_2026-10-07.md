# Strategy Box: реестры, справочники, каталоги источников и управляющий слой

**Research branch:** `02-base-study`  
**Дата исследования:** 2026-10-07  
**Основной implementation owner:** `ForestTiger-GH/stratbox`  
**Проверенный `main`:** `7ac86a4c3331c27a22aecb014f26e3b68aa9ef07`  
**Связанный surface owner:** `ForestTiger-GH/stratbox-windows`  
**Статус:** Research Result — архитектурное исследование. Сам документ не меняет Product, код или текущие контракты.

---

# 0. Итог в одном абзаце

Strategy Box уже пришёл к реестровой архитектуре фактически, но пока она сложилась фрагментарно. В `stratbox.registries` живут packaged reference data — официальный список банков Банка России, пользовательские словари банковских названий и ОКВЭД2. В `cbr_file_collector.registry.py` живёт жёсткий каталог 41 внешнего статистического файла Банка России. В доменах есть собственные реестры правил: формы ЦБ, FRG-семейства файлов, географическая топология SORS, публикационные категории и другие code registries. Это разные сущности, хотя исторически все называются «реестрами».

Целевая архитектура должна **развести их по смыслу, но объединить governance**. Глобальный `stratbox.registries` следует оставить владельцем канонических справочных данных: банков, ОКВЭД2, географии и пользовательских alias/selection-наборов. Отдельный `stratbox.sources` должен стать владельцем машинно-читаемого каталога внешних источников и стабильных файлов: URL, stable ID, ожидаемых имён, периодичности, форматов, групп и правил проверки. Доменные registries уровня FRG/forms/SORS остаются внутри своих доменов, потому что они описывают алгоритм или публикационную семантику, а не общую reference data Strategy Box.

Редактирование реестров в самом приложении сейчас вводить не стоит. Целевой режим — **immutable runtime + Git-authoring**: человек меняет CSV/XLSX/manifest в GitHub, репозиторные проверки валидируют изменение, новая поставка `stratbox` попадает в Strategy Box через обычное обновление продукта. `stratbox-windows` показывает реестры и источники только для чтения: актуальность, snapshot ID, хэш, источник, статус проверки и ссылку на страницу сопровождения. Никаких Git-токенов, push API и пользовательской записи внутрь установленного пакета приложению для этого не требуется.

---

# 1. Цель исследования

Исследование отвечает на пять связанных вопросов.

1. Что сегодня фактически является реестром или реестроподобной сущностью в Strategy Box.
2. Какие из этих объектов следует объединять, а какие — принципиально держать раздельно.
3. Как оформить банки, ОКВЭД2 и будущую географию РФ как устойчивый reference layer.
4. Куда поместить списки внешних файлов и источников, включая текущий список `CBR File Collector`.
5. Как сохранить простой процесс обновления через Git и при этом дать Windows/mobile surface нормальную видимость состояния реестров без собственного Git-клиента и секретов.

Исследование сознательно рассматривает задачу как архитектуру **core + surface boundary**. `stratbox` владеет данными, контрактами, загрузкой, validation и provenance. Surface показывает и использует готовые возможности core. AppDock остаётся внешней продуктовой средой и участвует только как механизм поставки/обновления/managed runtime.

---

# 2. Источники и метод

## 2.1. Текущий Product owner

Проверены актуальные файлы `ForestTiger-GH/stratbox@main`, в том числе:

- `AGENTS.md`;
- `_mw/AGENTS.md`;
- `_mw/epochs-001-strategy-box-development/research/02-base-study/README.md`;
- root `README.md`;
- `src/stratbox/registries/**`;
- `src/stratbox/macrobanks/cbr_file_collector/**`;
- `src/stratbox/macrobanks/frg/registry.py`;
- `src/stratbox/macrobanks/cbr_forms/forms/registry.py`;
- `src/stratbox/macrobanks/cbr_industries/regions.py`;
- `src/stratbox/macrobanks/escrow/regions.py`;
- `src/stratbox/macrobanks/cbr_sors_restoration/registries/**`;
- `src/stratbox/base/styles/excel/registry.py`;
- актуальные Research Results ветки `02-base-study`.

Текущий workspace прямо фиксирует, что `02-base-study` является Research-веткой фактического состояния, а Product truth определяется прямыми implementation owners.

## 2.2. Предыдущий baseline

Baseline core от 2026-10-06 уже выделил отдельный будущий трек **Source & Registry Architecture** и назвал его составляющие:

- `SourceDescriptor`;
- `SourceSnapshot`;
- cache;
- checksums;
- freshness;
- schema versions;
- bank/OKVED/geography registries;
- automated update workflow;
- source-change detection.

Настоящее исследование разворачивает именно этот трек в целевую систему.

## 2.3. Внешняя проверка

Актуальность официальных источников дополнительно проверена по состоянию на 2026-10-07:

- Банк России — информация о кредитных организациях:  
  https://www.cbr.ru/banking_sector/credit/
- Банк России — список кредитных организаций:  
  https://www.cbr.ru/banking_sector/credit/FullCoList/
- Росстат — ОКВЭД2 open data:  
  https://rosstat.gov.ru/opendata/7708234640-okvedva
- Росстат — общероссийские классификаторы, включая ОКАТО/ОКТМО:  
  https://rosstat.gov.ru/classification

Внешняя проверка нужна здесь прежде всего как evidence для freshness/versioning. Архитектурное решение выводится из текущего кода Strategy Box.

---

# 3. Что уже существует сейчас

## 3.1. `stratbox.registries` уже является настоящим reference-data слоем

Текущий root README определяет `registries` как встроенные справочники и ресурсные таблицы. Физически в `src/stratbox/registries` находятся:

```text
registries/
├── README.md
├── __init__.py
├── _loader.py
├── cbr_banks.py
├── rosstat_okved2.py
└── _resources/
    ├── cbr_banks/
    ├── cbr_replacements/
    ├── cbr_standart/
    ├── cbr_legacy/
    └── rosstat_okved2/
```

Это уже не просто набор констант. Здесь есть:

- packaged upstream snapshot;
- пользовательские overlays;
- loader;
- semantic normalization;
- lookup API;
- offline availability после установки пакета.

То есть архитектурный owner в core уже найден правильно. Проблема находится в lifecycle, identity и смешении разных типов данных внутри одного банковского loader-а.

## 3.2. Текущий банковский набор фактически состоит из четырёх разных реестров

Сегодня `cbr_banks.py` композиционно объединяет:

1. официальный XLSX Банка России;
2. `cbr_replacements.csv` — пользовательский canon/alias;
3. `cbr_standart.csv` — пользовательский набор «основных банков»;
4. `cbr_legacy.csv` — исторический набор для старых расчётов.

Они имеют разную семантику.

### Официальный банковский реестр

Это upstream reference data. Его identity — регистрационный номер банка, а источник authority — Банк России.

### Replacements

Это policy overlay Strategy Box. Он не является частью официального реестра ЦБ. Он задаёт удобный канон отображения:

```text
СБЕРБАНК -> СБЕР
РОССЕЛЬХОЗБАНК -> РСХБ
...
```

### Standard list

Это selection set. Он отвечает на вопрос «какие банки входят в конкретный выбранный набор», а не «какие банки существуют».

### Legacy list

Это compatibility artifact. В текущем проекте обратная совместимость как цель отсутствует. Следовательно, `cbr_legacy` в целевой архитектуре лучше убрать, а воспроизводимость старых результатов обеспечивать snapshot/version provenance. Если когда-либо нужен фиксированный исторический cohort банков как содержательная аналитическая сущность, он должен стать нормально названным `bank_set`, а не «legacy-механизмом».

## 3.3. ОКВЭД2 уже packaged и используется downstream

`rosstat_okved2.py` загружает три ресурса Росстата:

```text
meta*.csv
structure*.csv
data*.csv
```

Основной `read()` использует `data*.csv` и строит canonical view:

```text
section
code
name
```

Этот глобальный registry уже потребляется SORS restoration, где из него строятся 88 классов ОКВЭД2.

Это важный пример правильного ownership:

```text
официальный ОКВЭД2 -> global registry
публикационные группировки SORS -> local SORS registry
```

Такое разделение следует сохранить.

## 3.4. Текущий loader выбирает «самый свежий» resource по mtime

`_loader.py` использует `importlib.resources` и функции `pick_latest_by_suffix()` / `pick_latest_by_prefix()`. При нескольких кандидатах выбирается файл с максимальным `stat().st_mtime`.

Для раннего ручного режима это удобно. Для воспроизводимой packaged-системы mtime является слабой identity:

- Git сам по себе не хранит семантический mtime файла;
- новый checkout меняет filesystem timestamps;
- wheel/install/extraction может давать другое время;
- одинаковая поставка может выбирать разные файлы в зависимости от способа материализации;
- человек не видит явный `current snapshot` в данных.

В целевой архитектуре выбор resource должен быть **декларативным**, через manifest, а mtime может остаться только диагностической информацией.

## 3.5. Freshness уже реально является проблемой

В текущем дереве банковский XLSX имеет имя:

```text
RC_F02_02_2026_T02_02_2026.xlsx
```

То есть snapshot относится к февралю 2026 года.

На 2026-10-07 официальный портал Банка России показывает актуальную информацию по кредитным организациям уже на начало октября 2026 года. Следовательно, current bundled snapshot значительно отстаёт.

В ОКВЭД2 current package resource называется:

```text
data-20251101T1411-structure-20180402T1704.csv
```

При этом Росстат сейчас публикует:

```text
data-20261001T1110-structure-20180402T1704.csv
```

То есть проблема freshness в baseline была диагностирована верно и уже подтверждается прямыми upstream sources.

Главный вывод: registry lifecycle — не косметическое улучшение. Он прямо влияет на корректность аналитики.

---

# 4. Вторая группа: `cbr_file_collector.registry.py`

## 4.1. Это уже не reference registry

`cbr_file_collector` содержит `DEFAULT_CBR_FILE_SOURCES` — tuple из 41 `CbrFileRegistryItem`.

Контракт сегодня минимален:

```python
source_id: str
url: str
title: str
expected_file_name: str | None
```

Эта сущность отвечает на другой вопрос:

> какие внешние файлы Strategy Box умеет получать и откуда их брать?

Это **Source Catalog**, а не reference-data registry.

Смешивать его с банковским справочником или ОКВЭД2 в один физический registry storage не стоит. Зато lifecycle и provenance для них действительно должны быть родственными.

## 4.2. Почему идея пользователя вынести списки файлов в управляющий слой правильная

Для многих статистических публикаций URL и filename стабильны месяцами или годами, а содержимое регулярно обновляется. Такой объект естественно описывается один раз:

```text
stable source id
authority
URL
stable/expected filename
format
cadence
tags
group
validation profile
```

После этого operation выбирает source descriptors и получает конкретные snapshots.

Сегодня эта информация находится внутри Python-кода CBR collector. При росте источников это создаст лишнюю стоимость сопровождения:

- для добавления URL требуется менять Python source;
- список неудобно ревьюить как data;
- нельзя единообразно показать источники в UI;
- metadata ограничена четырьмя полями;
- невозможно нормально считать freshness;
- нет общего source manifest;
- нет связки `descriptor -> fetched snapshot`.

Поэтому список CBR collector стоит вынести из domain implementation в общий source catalog.

## 4.3. Но все источники нельзя свести к «списку файлов»

У Strategy Box уже есть источники, которые ведут себя по-разному:

### Fixed/direct source

Пример: один XLSX по постоянному URL, имя обычно одинаково.

### Discovery source

Escrow и `cbr_industries` сначала читают индекс/страницу публикации и находят набор датированных файлов.

### Parameterized source

Отчётные формы могут строить URL по дате/банку/форме.

### Registry source

Банки/ОКВЭД2 получают upstream snapshot, который затем становится packaged reference data.

Значит, `SourceDescriptor` должен описывать **источник как способ получения**, а не только один конкретный файл.

---

# 5. Третья группа: доменные code registries

В репозитории уже много объектов с названием registry, и переносить их все в `stratbox.registries` было бы архитектурной ошибкой.

## 5.1. CBR forms registry

`cbr_forms/forms/registry.py` связывает:

```text
form code -> implementation module -> title -> Excel profile -> reporting frequency
```

Это registry adapters/use cases домена. Он должен остаться внутри `cbr_forms`.

## 5.2. FRG family registry

`frg/registry.py` содержит правила распознавания 14 семейств файлов:

- priority;
- tokens;
- exclusions;
- parser group/key;
- period mode;
- date boundaries.

Это **rule registry**, тесно связанный с кодом распознавания и parser dispatch. Его global migration пользы не даст.

## 5.3. SORS geography registry

SORS строит специализированную географическую топологию:

- 85 atomic territories;
- 96 publication nodes;
- федеральные округа;
- parent/member relations;
- source-specific nodes вроде «область без данных по ...».

Это не просто список регионов России. Это доказательная топология конкретной публикационной системы. Общий geography registry может поставлять canonical region identities и aliases, но membership/evidence topology SORS должна остаться локальной.

## 5.4. SORS publication categories

`publication_categories.py` описывает, какие классы и разделы ОКВЭД публикуются отдельно, а какие попадают в `PUBLISHED_OTHER`.

Это publication semantics домена. Глобальный ОКВЭД2 предоставляет классы; SORS сам владеет логикой группировки.

## 5.5. Excel styles registry

`base.styles.excel.registry` — runtime/capability registry стилей. Это инфраструктурный реестр объектов в памяти, а не reference dataset.

## 5.6. Operation registry в surface

`stratbox-windows` имеет собственный operation/scenario registry. Он описывает пользовательские операции и формы параметров. Это application catalog, а не reference data.

---

# 6. Главная терминологическая проблема: слово «реестр» перегружено

Сейчас одним словом фактически называются пять разных классов объектов.

| Класс | Пример | Что хранит | Владелец |
|---|---|---|---|
| **Reference Registry** | банки, ОКВЭД2, будущая география | канонические сущности/коды | `stratbox.registries` |
| **Policy Overlay / Set** | bank aliases, набор основных банков | пользовательскую политику над reference data | рядом с registry owner |
| **Source Catalog** | 41 файл CBR collector | как найти внешние данные | будущий `stratbox.sources` |
| **Domain Rule Registry** | FRG families, forms, SORS categories | кодовую/предметную конфигурацию алгоритма | внутри домена |
| **Runtime/Capability Registry** | Excel styles, operations | доступные runtime objects/capabilities | инфраструктурный/application owner |

Целевая архитектура должна сделать эту классификацию явной.

Ключевой принцип:

> **единый governance не означает одну папку.**

Единым должно быть поведение: stable IDs, validation, versioning, hashes, provenance, status API. Физическое ownership остаётся у смыслового слоя.

---

# 7. Целевая топология core

Рекомендую следующую форму.

```text
src/stratbox/
├── common/
│   ├── identity/
│   └── provenance/
│
├── registries/
│   ├── contracts.py
│   ├── catalog.py
│   ├── status.py
│   ├── validation.py
│   │
│   ├── banks/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── normalize.py
│   │   ├── manifest.json
│   │   └── resources/
│   │       ├── official.xlsx
│   │       ├── aliases.csv
│   │       └── sets/
│   │           └── default.csv
│   │
│   ├── okved2/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── manifest.json
│   │   └── resources/
│   │       ├── data.csv
│   │       ├── meta.csv
│   │       └── structure.csv
│   │
│   └── geography/
│       ├── __init__.py
│       ├── loader.py
│       ├── manifest.json
│       └── resources/
│           ├── regions.csv
│           ├── aliases.csv
│           └── source_aliases/
│               ├── cbr.csv
│               └── rosstat.csv
│
├── sources/
│   ├── contracts.py
│   ├── catalog.py
│   ├── status.py
│   ├── selection.py
│   ├── snapshots.py
│   ├── validation.py
│   └── resources/
│       ├── cbr_statistics.csv
│       └── rosstat_statistics.csv
│
└── macrobanks/
    ├── cbr_file_collector/
    ├── cbr_forms/
    │   └── forms/registry.py
    ├── cbr_industries/
    ├── cbr_sors_restoration/
    │   └── registries/
    ├── escrow/
    └── frg/
        └── registry.py
```

Это пример целевой структуры, а не требование создать все файлы одним коммитом. Материализовать стоит только owners, для которых сразу появляется consumer.

---

# 8. Почему `registries` и `sources` должны быть соседями, а не одним пакетом

Они похожи lifecycle-ом, но имеют противоположную семантику.

## Registry

Registry отвечает:

> что это за сущность и каков её канонический identity?

Примеры:

- банк с `regn=1000`;
- класс ОКВЭД2 `47`;
- субъект РФ с internal `region_id`.

## Source

Source отвечает:

> откуда и каким способом получить данные?

Примеры:

- постоянный XLSX URL Банка России;
- страница-индекс SORS;
- parameterized URL формы;
- open-data endpoint Росстата.

## Snapshot

Snapshot отвечает:

> что именно мы фактически получили в конкретный момент?

Примеры:

- bytes конкретного XLSX;
- SHA-256;
- финальный URL после redirect;
- фактическое имя;
- размер;
- `Last-Modified`/ETag;
- дата загрузки;
- validation status.

Эти три сущности должны связываться через provenance, а не сливаться в одну таблицу.

---

# 9. Registry contracts

## 9.1. `RegistryDescriptor`

Минимальный descriptor:

```text
registry_id
title
kind
authority
source_page_url
source_data_url
schema_version
update_mode
freshness_policy
manifest_path
```

Пример IDs:

```text
banks.cbr
banks.aliases
banks.set.default
okved2.rosstat
geography.russia
geography.aliases
```

Stable ID должен переживать переименование файла и UI title.

## 9.2. `RegistrySnapshot`

```text
registry_id
snapshot_id
upstream_version
source_published_at
effective_from
effective_to
retrieved_at
schema_version
transform_version
files[]
status
```

Для каждого файла:

```text
path
sha256
size_bytes
encoding
media_type
```

## 9.3. `RegistryStatus`

Runtime status нужен отдельно от descriptor:

```text
registry_id
available
valid
freshness
snapshot_id
upstream_age_days
warnings
errors
```

Freshness следует делать политикой, а не универсальным «просрочен через N дней».

Например:

- банки: ожидаем обновление часто, warning после заданного окна;
- ОКВЭД2: изменение событийное, а не ежемесячное;
- aliases: freshness неприменима;
- geography aliases: обновляется по мере появления реальных mismatch.

---

# 10. Manifest вместо выбора по mtime

Это одно из самых важных практических изменений.

## 10.1. Сегодня

```text
найти все *.xlsx
↓
взять максимальный filesystem mtime
```

## 10.2. Целевая схема

```text
manifest.json
↓
explicit current resource path
↓
verify hash
↓
load
```

Пример:

```json
{
  "registry_id": "banks.cbr",
  "snapshot_id": "2026-10-05",
  "authority": "Bank of Russia",
  "source_page_url": "https://www.cbr.ru/banking_sector/credit/FullCoList/",
  "source_published_at": "2026-10-05",
  "retrieved_at": "2026-10-07T12:00:00Z",
  "schema_version": "1",
  "transform_version": "1",
  "files": [
    {
      "path": "resources/official.xlsx",
      "sha256": "..."
    }
  ]
}
```

Плюсы:

- одинаковый результат из source tree и wheel;
- clear diff;
- snapshot identity видна человеку;
- легко проверять hash;
- легко отдавать provenance;
- имя физического файла можно оставить постоянным.

Это особенно соответствует пользовательскому требованию: upstream-файлы могут обновляться, сохраняя одно и то же имя. Внутри репозитория тоже можно хранить стабильное `official.xlsx`, а изменение identity фиксировать в manifest и Git history.

---

# 11. Банки: целевая декомпозиция

## 11.1. `banks.cbr`

Официальный upstream registry.

Identity:

```text
regn
```

Обязательные проверки:

- `regn` существует;
- `regn` уникален;
- обязательные колонки upstream присутствуют;
- пустые/дублирующиеся строки диагностируются;
- неизвестные новые колонки сохраняются либо явно допускаются;
- source snapshot hash фиксируется.

## 11.2. `banks.aliases`

Пользовательский словарь имён.

Лучше отвязать его от имени `cbr_replacements`: это уже policy Strategy Box, а не реестр ЦБ.

Формат:

```csv
canonical_name,alias
СБЕР,СБЕРБАНК
РСХБ,РОССЕЛЬХОЗБАНК
```

Ещё более устойчивый вариант — привязать canonical identity к `regn`, а display name держать отдельно:

```csv
regn,canonical_name,alias
1481,СБЕР,СБЕРБАНК
3349,РСХБ,РОССЕЛЬХОЗБАНК
```

Тогда переименование банка не ломает entity identity.

## 11.3. `banks.set.default`

Текущий `cbr_standart` лучше переименовать в явный named set.

Например:

```text
banks/sets/default.csv
banks/sets/major.csv
banks/sets/peer_group_x.csv
```

Формат лучше строить по `regn`:

```csv
regn,enabled,order
1481,true,10
1000,true,20
```

Название банка может быть вспомогательной колонкой для человека, но identity остаётся `regn`.

## 11.4. `cbr_legacy`

Целевое решение: удалить как механизм backward compatibility.

Если существующий расчёт всё ещё реально использует этот список, сначала переводим consumer на нормальный named set или полный реестр. После этого `legacy` исчезает.

---

# 12. ОКВЭД2: целевая модель

## 12.1. Authority и identity

Authority — Росстат/open data.

Entity identity — code, а не label.

Canonical view:

```text
section
code
name
```

При необходимости дальше можно добавить:

```text
level
parent_code
valid_from
valid_to
```

Но эти поля стоит материализовать только при наличии реального consumer и уверенного способа построения.

## 12.2. Три upstream files лучше сохранять как один snapshot bundle

Manifest должен ссылаться одновременно на:

- `data.csv`;
- `meta.csv`;
- `structure.csv`.

Их snapshot identity едина.

Не стоит выбирать каждый файл независимо «самый свежий по prefix»: так теоретически можно случайно составить bundle из разных upstream revisions.

## 12.3. Исторические версии

На первом этапе Git history достаточно для сопровождения. В package можно держать один current snapshot.

Для каждого аналитического результата provenance фиксирует `snapshot_id + sha256`. Это позволяет понять, какой ОКВЭД2 использовался.

Если появится реальная потребность пересчитывать историю одновременно по нескольким версиям классификатора, тогда можно перейти к packaged history:

```text
snapshots/2025-11-01/
snapshots/2026-10-01/
```

До появления такого consumer хранить все версии в wheel избыточно.

## 12.4. SORS

SORS должен продолжать читать global OKVED2 registry.

При этом локальные объекты SORS остаются внутри SORS:

- 88-class projection;
- publication categories;
- crosswalk evidence;
- source publication grouping.

Global registry даёт official identity, домен добавляет свою семантику.

---

# 13. География РФ: как лучше сделать будущий registry

Это наиболее важная новая сущность, потому что географические списки уже дублируются в нескольких доменах.

## 13.1. Сегодня география уже существует минимум в трёх формах

### CBR industries

В `cbr_industries/regions.py` зафиксированы 96 source rows, включая:

- РФ;
- федеральные округа;
- регионы;
- автономные округа;
- специальные строки «в том числе»;
- специальные строки «область без данных по ...».

### SORS

На базе этих строк строится 85 atomic territories и 96 publication nodes.

### Escrow

Порядок географии сейчас берётся из последнего файла либо пользовательского списка. Зарезервированный раньше registry-mode был убран, потому что реального общего registry ещё нет.

Следовательно, общий geography owner уже нужен реальным consumers.

## 13.2. Нельзя сделать один плоский `regions.csv` и считать задачу решённой

В source files встречаются сущности разных типов:

```text
субъект РФ
федеральный округ
страна total
включённая территория
агрегат без части территории
публикационный узел
```

Например «Тюменская область без данных по ...» — аналитический publication node, а не обычный субъект РФ.

Поэтому целевая модель должна разделять **canonical geography entities** и **source/publication nodes**.

## 13.3. Базовый `geography.regions`

Рекомендованный минимальный schema:

```text
region_id
canonical_name
entity_kind
federal_district_id
sort_order
active
```

Опционально:

```text
okato_code
oktmo_code
iso_code
valid_from
valid_to
```

`region_id` должен быть внутренним стабильным identity и не зависеть от текущего русского названия.

## 13.4. `geography.aliases`

Именно сюда естественно ложатся будущие словари замен пользователя.

Schema:

```text
source_system
alias
region_id
valid_from
valid_to
note
```

Примеры `source_system`:

```text
cbr
rosstat
manual
historical
```

Преимущество source-aware aliases: одна и та же строка может иметь разную семантику в разных публикациях, и мы не превращаем нормализацию в глобальный fuzzy replace.

## 13.5. Source-specific publication geography остаётся локально

Например для `01_05_A_Debt_corp` можно хранить:

```text
publication_node_id
source_label
node_kind
canonical_region_id (nullable)
member_region_ids
order
```

Это domain/source registry. Он ссылается на global geography, но сам остаётся владельцем структуры конкретной публикации.

## 13.6. ОКАТО/ОКТМО

Росстат поддерживает актуальные общероссийские классификаторы ОКАТО и ОКТМО. Они могут стать полезным authority/crosswalk layer позже.

Сразу тянуть полный ОКТМО в Strategy Box необязательно. Для банковской макроаналитики сначала достаточно субъекта РФ + aliases + федерального округа. Коды можно добавить, когда они начинают решать реальную проблему сопоставления источников.

---

# 14. Source Catalog: целевая сущность для списков файлов

## 14.1. `SourceDescriptor`

Минимальный контракт:

```text
source_id
authority
title
source_kind
url
source_page_url
expected_file_name
expected_suffix
cadence
enabled
groups
tags
validation_profile
```

Полезные дополнительные поля:

```text
filename_strategy
content_type
schema_id
freshness_policy
notes
```

## 14.2. `source_kind`

Предлагаю минимум:

```text
direct_file
index_discovery
parameterized
registry_upstream
```

Это позволит описать CBR collector и будущие Росстат sources без искусственной унификации.

## 14.3. `cadence`

Cadence является metadata ожидания, а не scheduler instruction.

Примеры:

```text
monthly
quarterly
weekly
daily
on_change
irregular
```

Scheduler, когда он появится, сможет использовать эти данные, но source catalog сам ничего по времени не запускает.

## 14.4. Groups и tags

Текущий CBR collector станет гораздо удобнее, если источник можно выбирать группами:

```text
mortgage
corporate_loans
sme
borrowings
households
monetary_statistics
external_debt
exchange_rates
```

Тогда operation API поддерживает:

```text
all sources
source_ids=[...]
groups=[...]
tags=[...]
```

## 14.5. Что не должно жить в SourceDescriptor

Не следует складывать туда:

- output directory;
- overwrite policy;
- retry count для конкретного запуска;
- user headers конкретной сессии;
- UI labels/positions;
- бизнес-формулы;
- parser implementation object.

Эти вещи принадлежат Request/runtime/domain layers.

---

# 15. `SourceSnapshot`: связующее звено между source catalog и аналитикой

При каждой фактической загрузке должен появляться snapshot record.

```text
source_id
requested_url
used_url
final_url
fetched_at
file_name
size_bytes
sha256
etag
last_modified
content_type
validation_status
warnings
```

Это развитие уже существующих `CbrDownloadedFileSource` и `CbrCollectedFile`.

Главное изменение: snapshot получает cryptographic identity и становится reusable provenance object.

## 15.1. Почему SHA-256 важнее имени файла

Если URL и filename месяцами не меняются, то имя не говорит, изменились ли данные.

Hash сразу даёт:

- change detection;
- cache identity;
- reproducibility;
- duplicate detection;
- evidence для run manifest.

## 15.2. ETag/Last-Modified

Они полезны как оптимизация и diagnostics, но source server может их не давать или менять непредсказуемо. Канонический content identity лучше строить по SHA-256 полученных bytes.

---

# 16. Общий governance без «God Registry Manager»

Пользовательская идея управляющего слоя правильна, но централизованный объект, который знает всё обо всех доменах, быстро станет монолитом.

Лучше иметь тонкий общий contract + агрегирующий catalog.

## 16.1. Registry catalog

```python
list_registries()
get_registry_descriptor(registry_id)
get_registry_status(registry_id)
read_registry(registry_id)
```

## 16.2. Source catalog

```python
list_sources()
get_source(source_id)
select_sources(groups=..., tags=...)
```

## 16.3. Domain registries

Остаются собственными API доменов.

## 16.4. Aggregate diagnostics

Для UI можно дать один нейтральный view:

```text
ReferenceStatusReport
├── registries[]
└── sources[]
```

Это read model, а не новый owner данных.

---

# 17. Редактирование и обновление: Git должен остаться authoring surface

Пользовательская оценка полностью совпадает с целевой архитектурой.

Встроить полноценное редактирование Git-backed registries в Strategy Box означает добавить:

- аутентификацию GitHub;
- token storage;
- permission scopes;
- branch/commit/PR model;
- conflict resolution;
- optimistic locking;
- audit of remote writes;
- handling protected branches;
- network errors;
- разные hosting providers;
- UX diff/review;
- безопасность секретов.

Это отдельный продуктовый класс задач и сейчас он не окупается.

## 17.1. Целевой режим

```text
Git repository = authoring source of truth
↓
validation / tests
↓
immutable package/build
↓
AppDock-managed update
↓
Strategy Box runtime = read-only consumer
```

## 17.2. Почему установленный package тоже лучше считать read-only

Даже без Git write-back редактировать registry resources прямо внутри установленного Python package плохая идея:

- wheel resources могут жить в environment, которым управляет installer;
- update перезапишет изменения;
- provenance потеряет смысл;
- несколько пользователей получат divergent local registries;
- package hash/сборка перестанет быть immutable;
- recovery станет сложнее.

Editable dev checkout остаётся отдельным режимом для разработчика.

---

# 18. Три update workflows

## 18.1. Upstream registry update

Например banks/OKVED2.

```text
1. Скачать официальный snapshot.
2. Заменить resource file(s).
3. Обновить manifest metadata.
4. Пересчитать hashes.
5. Запустить registry validation/tests.
6. Посмотреть diff.
7. Commit/PR/push.
8. Выпустить новую immutable поставку.
```

## 18.2. Human policy update

Например aliases или default bank set.

```text
1. Изменить CSV.
2. Validation проверяет schema, duplicates и references.
3. Commit/PR.
4. Новая поставка.
```

Здесь source_published_at не нужен; snapshot identity может быть Git-derived или date/revision.

## 18.3. Source catalog update

Например Банк России меняет URL или добавляется новый стабильный файл.

```text
1. Изменить descriptor row.
2. Static validation.
3. Опциональный live smoke HEAD/GET.
4. Commit/PR.
5. Новая поставка.
```

---

# 19. Git history или packaged history?

Это важное архитектурное решение.

## Вариант A — хранить все snapshots в package

Плюсы:

- runtime может выбирать старую версию без переустановки.

Минусы:

- растёт wheel;
- дублируются большие XLSX/CSV;
- повышается сложность выбора;
- history уже существует в Git.

## Вариант B — package содержит только current snapshot

Плюсы:

- простой runtime;
- маленькая поставка;
- одно значение `current`;
- Git остаётся историей.

Минус:

- для пересчёта на старом registry надо установить старую build/revision.

## Рекомендация

Сейчас выбрать **B**.

Для Strategy Box текущий главный use case — работа с актуальными reference data. Reproducibility обеспечивается run manifest + immutable build identity + Git history.

Packaged multi-version history добавлять только при появлении реального runtime consumer.

---

# 20. Versioning поставки

Registry snapshot имеет собственную identity, но distributed package тоже должен быть immutable.

Плохая схема:

```text
stratbox 0.8.0
сегодня содержит один banks.xlsx
завтра под тем же 0.8.0 — другой
```

Такой package нельзя воспроизводимо кешировать и сравнивать.

Целевые варианты:

### Вариант 1. Patch release на registry update

```text
0.8.1
0.8.2
...
```

Самый простой для wheel-based distribution.

### Вариант 2. Build identity по commit

AppDock/managed deployment фиксирует exact repository revision/build digest. Python semver может меняться реже, но сам артефакт всё равно immutable и однозначно идентифицирован.

### Практическая рекомендация

В runtime provenance всегда хранить одновременно:

```text
stratbox_version
build/revision identity
registry_snapshot_id
registry_sha256
```

Тогда способ release versioning можно доработать отдельно без потери воспроизводимости.

---

# 21. Freshness model

Freshness нельзя выражать одним полем `is_latest=True`.

Нужно различать:

```text
CURRENT
STALE
UNKNOWN
MANUAL
NOT_APPLICABLE
```

## 21.1. Upstream-based registry

Можно сравнивать:

- source published date;
- retrieved date;
- known upstream update;
- configurable warning horizon.

## 21.2. Human-maintained registry

Aliases или selection set имеют `MANUAL`. Система не должна ругать их за «старую дату».

## 21.3. Source catalog

Freshness descriptor — это скорее «когда последний раз проверяли endpoint» и «когда менялся content hash», а не возраст CSV в репозитории.

---

# 22. Validation как first-class часть слоя

## 22.1. Banks

Проверки:

- schema upstream;
- unique `regn`;
- aliases refer to known banks либо помечены как accepted unresolved;
- canonical names не конфликтуют;
- bank sets содержат существующие `regn`;
- order уникален при его использовании;
- duplicate alias запрещён для разных entities.

## 22.2. OKVED2

- bundle completeness data/meta/structure;
- CSV decoding;
- unique codes;
- known section codes;
- hierarchy/basic pattern validation;
- expected minimum population;
- snapshot hash.

## 22.3. Geography

- unique `region_id`;
- duplicate canonical labels диагностируются;
- alias однозначно ведёт к одной entity в рамках source_system/validity;
- parent district reference существует;
- publication nodes, если они вынесены в source layer, покрываются отдельно.

## 22.4. Source catalog

- unique `source_id`;
- valid URL;
- recognized source_kind;
- expected suffix/filename согласованы;
- duplicate stable filenames внутри одной output group диагностируются;
- tags/groups нормализованы;
- validator IDs существуют;
- live smoke отделён от deterministic unit validation.

---

# 23. Provenance: registry versions должны попадать в каждый существенный Result

Baseline core уже выделил provenance как сквозную идею. Registry/source architecture делает её практически полезной.

Пример run manifest:

```json
{
  "stratbox_version": "0.9.0",
  "revision": "...",
  "registries": {
    "banks.cbr": {
      "snapshot_id": "2026-10-05",
      "sha256": "..."
    },
    "banks.aliases": {
      "snapshot_id": "2026-10-07-r1",
      "sha256": "..."
    },
    "okved2.rosstat": {
      "snapshot_id": "2026-10-01",
      "sha256": "..."
    }
  },
  "sources": [
    {
      "source_id": "corp_debt_a",
      "fetched_at": "...",
      "sha256": "..."
    }
  ]
}
```

Это позволяет ответить на вопросы:

- почему результат прошлого месяца отличается;
- какой список банков использовался;
- какой ОКВЭД2 использовался;
- менялся ли source content при неизменном filename;
- какой alias policy применялась;
- можно ли переиспользовать cache.

---

# 24. Change detection

Source catalog естественно позволяет построить будущий watcher без переноса scheduler в core.

Pure core operation:

```text
check_source(source_id)
↓
fetch metadata/content
↓
build SourceSnapshot
↓
compare previous known snapshot
↓
SourceChangeResult
```

Возможные состояния:

```text
UNCHANGED
CONTENT_CHANGED
URL_CHANGED
SCHEMA_SUSPECTED_CHANGED
UNAVAILABLE
VALIDATION_FAILED
```

Scheduler остаётся внешним consumer — Windows background job, host, GitHub Actions или AppDock-side orchestration.

---

# 25. Как должен измениться CBR File Collector

Сегодня collector одновременно владеет:

- source list;
- download operation;
- filename resolution;
- save behavior.

Целевое разделение:

```text
stratbox.sources
    ↓ select descriptors
cbr_file_collector
    ↓ fetch using common source contract
SourceSnapshots
    ↓ save raw bytes
CbrFileCollectResult
```

Collector остаётся доменом/use case «собрать выбранные сырые статистические файлы ЦБ».

Он перестаёт быть владельцем master list источников.

## 25.1. Migration без backward compatibility

Поскольку обратная совместимость не требуется, можно сразу заменить:

```python
DEFAULT_CBR_FILE_SOURCES
```

на data-driven catalog и новый typed API, вместо поддержки двух параллельных путей.

## 25.2. Default output metadata

`DEFAULT_OUTPUT_BASE_DIR = "/content"` является environment-specific default и с registry governance напрямую не связан. В целевой архитектуре output location должен задаваться request/surface, а source catalog хранит только source identity.

---

# 26. Что делать с dynamic discovery domains

## Escrow

В source catalog хранится descriptor страницы/семейства:

```text
source_id = cbr.escrow.publications
source_kind = index_discovery
source_page_url = ...
```

Конкретные месячные XLSX становятся `SourceSnapshot`/discovered items, а не 100 строками master catalog.

## CBR industries / SORS

Аналогично: catalog содержит series/index descriptor. Домен discovery извлекает dated source links.

## CBR forms

Source descriptor может описывать parameterized family, а form registry продолжает описывать implementations/forms.

Это удерживает source layer компактным и устойчивым.

---

# 27. Что показывать в `stratbox-windows`

Редактирование сейчас не нужно, но read-only visibility очень полезна.

## 27.1. Поверхность «Реестры и источники»

Её можно разместить в Settings/Diagnostics или отдельном system inspector.

Для registry показывать:

```text
Название
Registry ID
Authority
Snapshot
Source date
Packaged/retrieved date
Status
Hash short
Warnings
Source page
```

Для source:

```text
Название
Source ID
Authority
Kind
Cadence
Expected file
Last fetched/checked
Last hash/change
Status
```

## 27.2. Действия surface

Безопасный базовый набор:

```text
Просмотреть детали
Скопировать ID
Открыть официальный источник
Открыть страницу сопровождения в GitHub
Перепроверить доступность источника
Запустить validation/status check
```

Последние два действия вызывают core operation и ничего не коммитят.

## 27.3. Чего в UI сейчас делать не стоит

- inline CSV editor;
- push to GitHub;
- ввод personal access token;
- merge conflict UX;
- создание commits/PR;
- запись в package resources.

Это оставляет приложение значительно проще и безопаснее.

---

# 28. Windows/Android portability

Текущий `stratbox-windows` уже движется к platform-neutral `application` и `presentation/common`.

Registry/source UI следует сразу описать platform-neutral моделями:

```text
RegistryStatusViewModel
SourceStatusViewModel
ReferenceHealthViewModel
```

Тогда Windows surface рендерит их в Qt, а будущий Android — своим frontend.

Shared semantics:

- status vocabulary;
- display title;
- source/snapshot dates;
- warnings;
- available actions;
- links;
- last check/change.

Platform-specific слой решает только то, как открыть browser/link и как показать список.

---

# 29. AppDock boundary

AppDock по своей общей модели занимается установкой, обновлением, состоянием и восстановлением продукта. Для registries это даёт простой и чистый boundary.

AppDock **не должен становиться редактором или registry service** Strategy Box.

Его роль:

```text
получить новую product revision
↓
обновить managed environment
↓
запустить Strategy Box
↓
Strategy Box сам читает packaged registries/sources
```

Опционально Strategy Box может отдавать AppDock одну aggregated readiness capability:

```text
reference_data_status = READY / WARN / ERROR
```

Детальная семантика banks/OKVED/source IDs остаётся core-side.

---

# 30. Почему отдельный registry backend/server сейчас не нужен

Теоретически можно было бы сделать центральный сервер справочников, который Strategy Box запрашивает при запуске. Сейчас это ухудшит систему:

- появится network dependency даже для offline analysis;
- понадобится API versioning;
- access/control;
- availability/retry;
- server deployment;
- cache coherence;
- больше failure modes;
- отдельный owner и lifecycle.

Packaged registry snapshots лучше соответствуют текущей архитектуре: deterministic, offline, versioned, легко тестируются.

Серверная registry service становится оправданной только при реальной потребности синхронно обслуживать много независимых продуктов/команд с очень частыми изменениями.

---

# 31. Почему отдельный `stratbox-data` package сейчас тоже преждевременный

Вынести banks/OKVED/geography в отдельный package можно. Но сейчас это создаст:

- ещё один repository/package lifecycle;
- version matrix core ↔ data;
- installer complexity;
- дополнительные AppDock bindings;
- больше release automation.

Пока registry assets малы и тесно связаны с core contracts, лучше оставить их в `stratbox`.

Признаки, при которых выделение станет рациональным:

- registry updates значительно чаще code releases;
- один registry bundle потребляют несколько независимых продуктов;
- размер assets становится существенным;
- требуется отдельный owner/access regime;
- нужны параллельные версии registry data в одной runtime environment.

---

# 32. Domain-local registry rule

Полезное простое правило размещения:

> Если сущность нужна нескольким доменам и описывает внешний канонический мир — global registry. Если она описывает поведение одного алгоритма — domain registry.

Примеры.

### Global

- банки;
- ОКВЭД2;
- субъекты РФ;
- общие aliases регионов.

### Domain-local

- FRG family detection rules;
- CBR form adapters;
- SORS publication categories;
- SORS proof topology;
- escrow indicator catalog;
- workbook view profiles.

### Sources

- endpoints/files/index pages — global source catalog, если источник является общим data acquisition asset;
- narrow endpoint, используемый одним доменом, может физически оставаться рядом с доменом, но реализовывать общий `SourceDescriptor` contract.

Последний пункт позволяет избежать преждевременного централизованного каталога из сотен частных деталей.

---

# 33. Как оформить файлы source catalog

Для human-maintained стабильных источников CSV является хорошим первым форматом.

Пример:

```csv
source_id,authority,title,source_kind,url,expected_file_name,expected_suffix,cadence,groups,tags,enabled,validation_profile
corp_debt_a,cbr,Корпорации: долг A,direct_file,https://www.cbr.ru/.../01_02_A_Debt_corp_by_activity.xlsx,01_02_A_Debt_corp_by_activity.xlsx,.xlsx,monthly,corporate_loans,"cbr;sors",true,xlsx_basic
```

Плюсы CSV:

- легко редактировать на GitHub;
- хорошо diff-ится;
- не нужен новый parser dependency;
- удобно проверять pandas/stdlib;
- подходит для десятков/сотен строк.

JSON лучше оставить для manifest, где структура вложенная.

---

# 34. Naming

Текущие имена накопили несколько исторических артефактов.

Рекомендация:

```text
cbr_banks              -> banks/cbr official registry
cbr_replacements       -> banks/aliases
cbr_standart           -> banks/sets/default
cbr_legacy             -> удалить после migration
rosstat_okved2          -> okved2/rosstat
```

Использовать `standard`, если термин всё же останется. Но `set.default` семантически точнее, чем «standard bank registry».

Для source IDs лучше сохранить уже существующие stable IDs, если их смысл хороший. Переименование source ID ломает provenance сильнее, чем переименование title.

---

# 35. API design: DataFrame остаётся удобным, identity становится typed

Current `read() -> DataFrame` удобен и может сохраниться как user-facing primitive.

При этом system-level API стоит сделать typed:

```python
snapshot = get_registry_snapshot("banks.cbr")
df = read_registry("banks.cbr")
status = get_registry_status("banks.cbr")
```

А для конкретного registry оставить convenience:

```python
from stratbox.registries.banks import read, lookup
```

То есть typed metadata вокруг DataFrame, а не попытка заменить табличные данные тысячами Python objects.

---

# 36. Ошибки и diagnostics

Registry/source layer должен различать:

```text
ResourceMissing
ManifestInvalid
HashMismatch
SchemaMismatch
DuplicateIdentity
AliasConflict
UnknownReference
SourceUnavailable
SourceValidationFailed
FreshnessWarning
```

Freshness warning обычно не должен ломать импорт библиотеки. Например stale bank registry — серьёзная диагностика, но пользователь может сознательно воспроизводить старый run.

Hash mismatch, напротив, означает повреждённую/несогласованную поставку и должен считаться validation error.

---

# 37. Tests

Registry layer сейчас почти не имеет dedicated test coverage. После redesign это один из самых дешёвых и полезных тестовых контуров.

## Unit

- manifests parse;
- hashes match;
- bank IDs unique;
- aliases resolve;
- alias conflicts fail;
- sets reference existing banks;
- OKVED codes unique;
- geography IDs unique;
- source IDs unique;
- source group selection deterministic;
- manifest chooses explicit file, not mtime.

## Fixture/schema evolution

- old/new CBR banks XLSX headers;
- old/new Rosstat data files;
- renamed source region labels with explicit alias;
- source URL/filename variants.

## Packaging

- build wheel;
- install wheel;
- list registries;
- read each current registry offline;
- verify manifest hashes after install.

## Live smoke

Отдельный optional test:

- official source page reachable;
- direct sources return expected content type/size;
- upstream changed warning.

Live smoke не должен быть частью deterministic unit suite.

---

# 38. Repository checks и CI

Даже до полноценного GitHub Actions workflow можно добавить один deterministic script:

```text
scripts/check_registries.py
```

Он проверяет:

```text
all manifests
all packaged resources
all hashes
all schemas
all cross-references
all source descriptors
```

Дальше CI просто вызывает его вместе с existing release integrity/import/tests.

Для manual Git editing это особенно важно: человек может спокойно менять CSV/XLSX через GitHub, потому что машина ловит structural errors до release.

---

# 39. UX сопровождения через GitHub

Поскольку Git остаётся authoring surface, README каждого registry стоит сделать операционным, но коротким.

Пример `banks/README.md`:

```text
Что это
Authority/source link
Какие файлы менять
Как обновить manifest
Какая команда validation
Какие invariants
```

UI может давать deep link прямо на этот README или resource folder.

Так Strategy Box сохраняет простоту:

```text
пользователь приложения -> read-only status
сопровождающий разработчик -> GitHub edit/PR
```

---

# 40. Что делать с обновлением «прямо из Strategy Box» в будущем

Если однажды такая потребность реально появится, её лучше строить как отдельную capability, а не писать GitHub API внутрь registry loader.

Возможная будущая модель:

```text
RegistryAuthoringBackend
├── GitHubPullRequestBackend
└── LocalCheckoutBackend
```

Surface отправляет change proposal, backend создаёт branch/PR. Runtime package по-прежнему остаётся read-only.

Но сегодня это **future option**, а не часть целевой первой реализации.

---

# 41. Security

Текущий Git-only authoring выигрывает по безопасности:

- приложение не хранит Git credentials;
- нет remote write permission у обычного пользователя;
- каждый change имеет Git audit trail;
- branch protection/PR review можно подключить позже;
- package resources immutable;
- compromised desktop session не получает автоматический push path.

Для банковского аналитического инструмента это важнее удобства редактирования одной CSV-кнопкой.

---

# 42. Связь с file/artifact architecture

Registry/source identities должны естественно входить в artifact provenance.

Пример artifact metadata:

```text
artifact_id
producer_operation
source_snapshots[]
registry_snapshots[]
created_at
content_hash
```

Тогда Excel/CSV/report становится воспроизводимым артефактом, а не просто файлом на диске.

Особенно полезно для файлов, которые строятся повторно при одинаковом имени.

---

# 43. Связь с caching

Registry/source hashes дают корректные cache keys.

Вместо:

```text
cache key = URL + date
```

можно строить:

```text
operation id
+ params hash
+ source snapshot hashes
+ registry snapshot hashes
+ transform/schema version
```

Это делает cache безопасным для SORS и других тяжёлых pipelines.

---

# 44. Связь с AI/automation

AI или background process должен получать read-only registry/source metadata через operations/capabilities, а не доступ к package files.

Разрешённые действия:

```text
list registries
show status
list sources
check source
run validation
collect selected sources
```

Запрещённый базовый путь:

```text
arbitrary edit registry file
push repository
```

Если authoring capability появится позже, она должна иметь отдельное permission boundary.

---

# 45. Матрица текущих сущностей и целевого места

| Сегодня | Фактический смысл | Целевое место | Действие |
|---|---|---|---|
| `registries/_resources/cbr_banks` | upstream bank snapshot | `registries/banks/resources/official.xlsx` | сохранить, version manifest |
| `cbr_replacements` | alias policy | `registries/banks/resources/aliases.csv` | переименовать |
| `cbr_standart` | selected bank set | `registries/banks/resources/sets/default.csv` | переименовать/нормализовать |
| `cbr_legacy` | compatibility list | — | вывести из целевой архитектуры |
| `rosstat_okved2` | official classifier snapshot | `registries/okved2` | bundle manifest |
| future region replacements | geography aliases | `registries/geography/aliases.csv` | создать |
| `cbr_industries/regions.py` | source publication layout | domain/source registry | сохранить локально, связать с global geography |
| SORS geography | evidence/publication topology | SORS local registry | сохранить локально |
| `cbr_file_collector/registry.py` | direct external source list | `sources/resources/cbr_statistics.csv` | перенести ownership |
| FRG `registry.py` | file-family rules | FRG local | оставить |
| CBR forms `registry.py` | form adapter catalog | forms local | оставить |
| Excel styles registry | runtime capability | base styles | оставить |
| Windows operation registry | surface use-case catalog | surface/application | оставить |

---

# 46. Приоритетный migration plan

## P0. Зафиксировать taxonomy и contracts

1. Определить `RegistryDescriptor`, `RegistrySnapshot`, `RegistryStatus`.
2. Определить `SourceDescriptor`, `SourceSnapshot`.
3. Зафиксировать stable ID naming.
4. Зафиксировать правило global-vs-domain-local.

## P0. Убрать mtime как semantic selector

1. Добавить manifest для banks.
2. Добавить manifest для OKVED2.
3. Loader читает explicit resource path.
4. Добавить hash validation.

## P0. Обновить stale snapshots

1. Банки — свежий официальный XLSX.
2. ОКВЭД2 — текущий open-data bundle.
3. Зафиксировать snapshot dates/hashes.

## P1. Перестроить banks bundle

1. Разделить official/aliases/sets.
2. Перевести sets на `regn` identity.
3. Убрать `legacy` после migration consumers.
4. Исправить naming `standart`.

## P1. Создать geography registry

1. `regions.csv`.
2. `aliases.csv`.
3. Stable `region_id`.
4. Подключить как минимум escrow и common normalization.
5. Затем аккуратно связать CBR industries/SORS без разрушения source-specific topology.

## P1. Создать source catalog

1. Перенести 41 CBR direct source в data file.
2. Расширить descriptor metadata.
3. Collector читает catalog.
4. Добавить groups/tags.
5. Добавить SHA-256 snapshots.

## P1. Provenance

1. Registry snapshot IDs в domain results.
2. Source snapshots в download results.
3. Общий run/artifact manifest.

## P2. Surface visibility

1. `registry/source status` operation.
2. platform-neutral view model.
3. read-only Windows screen.
4. reusable Android presentation semantics.

## P2. Automation

1. source change-check operation;
2. optional scheduled watcher снаружи core;
3. PR-based updater только если появится реальная потребность.

---

# 47. Что я бы сделал первым реальным Work

Если после этого Research переходить к реализации, наиболее сильный первый vertical slice выглядит так:

```text
banks + OKVED2 manifest lifecycle
```

Он маленький, но проверяет почти всю архитектуру:

- descriptor;
- snapshot;
- explicit resource selection;
- hashes;
- validation;
- provenance;
- Git update flow;
- wheel resource loading;
- status API.

После него `geography` и `sources` можно добавлять уже по проверенному шаблону.

Второй slice:

```text
CBR file collector -> common source catalog
```

Третий:

```text
geography registry -> escrow + region aliases
```

Так архитектура растёт от реальных consumers, а не от пустого framework.

---

# 48. Антипаттерны, которых стоит избежать

## 48.1. Один огромный `registries/registry.py`

Он быстро станет свалкой банков, регионов, URL, форм, стилей и операций.

## 48.2. «Последний файл по mtime»

Это удобный dev shortcut, но слабый production contract.

## 48.3. Identity по русскому label

Для банков identity — `regn`; для ОКВЭД — code; для geography нужен stable internal ID.

## 48.4. Смешение official data и corporate/user policy

Official bank list, aliases и peer sets должны быть разными snapshots.

## 48.5. Сведение всех географических source rows к «региону»

Publication totals/aggregates имеют другую семантику.

## 48.6. Хранить Git credentials ради редактирования CSV из UI

Слишком большая security/product complexity для текущего спроса.

## 48.7. Автоматически обновлять packaged registry при каждом запуске

Это разрушает reproducibility: один и тот же установленный product revision внезапно начинает считать на других reference data.

## 48.8. Молчаливый fallback на старый registry при failed update

Update workflow должен быть отдельным от runtime. Runtime читает уже валидную поставку.

## 48.9. Считать source filename version identity

При постоянном имени identity даёт content hash/snapshot metadata.

---

# 49. Решения, которые уже можно считать сильными рекомендациями этого Research

1. **Сохранить `stratbox.registries` как core owner общих reference data.**
2. **Создать отдельный `stratbox.sources` для каталогов внешних источников и source snapshots.**
3. **Считать banks/OKVED/geography reference registries, а FRG/forms/SORS rules — domain registries.**
4. **Заменить mtime-based selection на explicit manifest.**
5. **Дать каждому registry snapshot ID + SHA-256 + source metadata.**
6. **Разделить official bank list, aliases и bank sets.**
7. **Убрать legacy compatibility registry после перевода consumers.**
8. **Создать geography registry из canonical entities + source-aware aliases; publication nodes держать отдельно.**
9. **Перенести hardcoded CBR collector source list в data-driven Source Catalog.**
10. **Оставить GitHub/Git authoring единственным способом редактирования реестров на текущем этапе.**
11. **Сделать runtime/package resources immutable.**
12. **В Windows/Android показывать read-only registry/source status и links, без Git credentials.**
13. **Записывать registry/source snapshots в provenance аналитических результатов.**
14. **Использовать source hashes для change detection и caching.**
15. **Автоматизацию обновлений в будущем строить через PR/updater workflow, а не скрытую runtime mutation.**

---

# 50. Целевая картина Strategy Box

После реализации базового слоя data path будет выглядеть так:

```text
Git-authored Registry Assets
    │
    ├── Banks
    ├── OKVED2
    └── Geography
    │
    ↓
Registry Manifests + Validation
    │
    ↓
Immutable packaged Registry Snapshots
    │
    ├───────────────────────────────┐
    │                               │
    ↓                               ↓
Domain operations              Source Catalog
    │                               │
    │                               ↓
    │                         Fetch / Discovery
    │                               ↓
    │                         Source Snapshot
    │                               │
    └───────────────┬───────────────┘
                    ↓
             Canonical data
                    ↓
          Result / Artifact
                    ↓
               Provenance
        registry IDs + source hashes
                    ↓
      stratbox-windows / Android
     read-only status + operations
                    ↓
          AppDock managed product
```

Это архитектура, в которой реестры становятся не «папкой CSV», а частью воспроизводимости Strategy Box, при этом сопровождение остаётся простым: официальный файл или словарь меняется в Git, проходит validation, попадает в новую поставку и автоматически становится доступен всем consumers core.

---

# 51. Короткий ответ на исходные вопросы

### Нужен ли отдельный реестровый слой?

Да. Он уже фактически существует и должен быть формализован как versioned reference-data layer.

### Нужно ли туда положить будущие словари регионов?

Да — canonical geography и aliases. Source-specific агрегаты и publication nodes остаются в соответствующих доменах.

### Нужно ли туда вынести списки файлов, которые система регулярно скачивает?

Да как общий управляющий контур, но физически лучше оформить их отдельным **Source Catalog**, а не смешивать с reference registries.

### Нужно ли редактировать реестры из Strategy Box?

Сейчас — нет. GitHub/Git является более простым, прозрачным и безопасным authoring surface.

### Что должно уметь приложение?

Читать, валидировать, показывать версии/freshness/status, использовать registry/source IDs в операциях и provenance, открывать официальный источник или GitHub страницу сопровождения.

### Как обновления попадают к пользователю?

Через обычное обновление immutable поставки Strategy Box. AppDock обновляет продукт/managed environment; core внутри новой поставки уже содержит новые registry assets/catalog descriptors.

---

# Appendix A. Предлагаемый manifest банков

```json
{
  "contract_version": "1",
  "registry_id": "banks.cbr",
  "title": "Банки Российской Федерации — Банк России",
  "kind": "official_reference",
  "authority": "Банк России",
  "source_page_url": "https://www.cbr.ru/banking_sector/credit/FullCoList/",
  "snapshot_id": "2026-10-05",
  "source_published_at": "2026-10-05",
  "retrieved_at": "2026-10-07T12:00:00Z",
  "schema_version": "1",
  "transform_version": "1",
  "update_mode": "manual_git",
  "files": [
    {
      "role": "data",
      "path": "resources/official.xlsx",
      "sha256": "..."
    }
  ]
}
```

# Appendix B. Предлагаемый manifest ОКВЭД2

```json
{
  "contract_version": "1",
  "registry_id": "okved2.rosstat",
  "title": "ОКВЭД2",
  "kind": "official_reference",
  "authority": "Росстат",
  "source_page_url": "https://rosstat.gov.ru/opendata/7708234640-okvedva",
  "snapshot_id": "2026-10-01T1110",
  "source_published_at": "2026-10-01",
  "retrieved_at": "2026-10-07T12:00:00Z",
  "schema_version": "1",
  "transform_version": "1",
  "update_mode": "manual_git",
  "files": [
    {"role": "data", "path": "resources/data.csv", "sha256": "..."},
    {"role": "meta", "path": "resources/meta.csv", "sha256": "..."},
    {"role": "structure", "path": "resources/structure.csv", "sha256": "..."}
  ]
}
```

# Appendix C. Geography aliases example

```csv
source_system,alias,region_id,valid_from,valid_to,note
cbr,Кемеровская область,ru-kem,,2021-01-01,historical source label
cbr,Кемеровская область - Кузбасс,ru-kem,2021-01-01,,current source label
```

`region_id` выше приведён только как иллюстрация internal identity; финальную схему ID надо зафиксировать отдельным Product/Work решением.

# Appendix D. Source Catalog example

```csv
source_id,authority,title,source_kind,url,source_page_url,expected_file_name,expected_suffix,cadence,groups,tags,enabled,validation_profile
mortgage_debt_ind,cbr,Кредиты физлиц: задолженность,direct_file,https://www.cbr.ru/vfs/statistics/BankSector/Mortgage/02_05_Debt_ind.xlsx,https://www.cbr.ru/statistics/bank_sector/sors/,02_05_Debt_ind.xlsx,.xlsx,monthly,mortgage,"cbr;retail",true,xlsx_basic
corp_debt_a,cbr,Корпорации: долг A,direct_file,https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/01_02_A_Debt_corp_by_activity.xlsx,https://www.cbr.ru/statistics/bank_sector/sors/,01_02_A_Debt_corp_by_activity.xlsx,.xlsx,monthly,corporate_loans,"cbr;corporate",true,xlsx_basic
```

# Appendix E. Registry/source status for surface

```json
{
  "registries": [
    {
      "registry_id": "banks.cbr",
      "title": "Банки — Банк России",
      "snapshot_id": "2026-10-05",
      "status": "CURRENT",
      "source_published_at": "2026-10-05",
      "warnings": []
    }
  ],
  "sources": [
    {
      "source_id": "corp_debt_a",
      "title": "Корпорации: долг A",
      "status": "READY",
      "last_checked_at": "2026-10-07T11:00:00Z",
      "last_content_change_at": "2026-10-01T08:15:00Z"
    }
  ]
}
```

# Appendix F. Внешние ссылки, проверенные в Research

1. Банк России — информация о кредитных организациях:  
   https://www.cbr.ru/banking_sector/credit/

2. Банк России — список кредитных организаций:  
   https://www.cbr.ru/banking_sector/credit/FullCoList/

3. Банк России — статистика банковского сектора / SORS:  
   https://www.cbr.ru/statistics/bank_sector/sors/

4. Росстат — ОКВЭД2 open data:  
   https://rosstat.gov.ru/opendata/7708234640-okvedva

5. Росстат — общероссийские и ведомственные классификаторы:  
   https://rosstat.gov.ru/classification

---

**Конечный вывод:** тема реестров должна стать отдельным устойчивым архитектурным контуром Strategy Box, но без превращения `registries` в универсальную свалку. Reference data, source catalogs и domain registries должны иметь разные owners и общие правила identity/versioning/validation/provenance. Такой дизайн одновременно решает сегодняшнюю проблему устаревающих банков/ОКВЭД snapshots, готовит общий geography layer, убирает hardcoded list источников из CBR collector и сохраняет самый простой эксплуатационный режим — редактирование через Git, read-only runtime и поставка обновлений вместе с продуктом.
