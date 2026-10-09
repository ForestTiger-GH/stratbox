# Strategy Box — консолидирующее исследование 03: Data → Knowledge Architecture

**Дата:** 2026-10-08  
**Программа:** `03-consolidation-research`, тема **03 — Data → Knowledge Architecture**  
**Статус:** **Research Synthesis / Consolidation Result**. Исследовательское сведение, а не Product Decision, утверждённый Target WHAT/HOW, спецификация уже реализованного API или поручение на изменение репозиториев.  
**Основной корпус:** `02-base-study`, в особенности исследования core, FileStore/форматов, источников/реестров, артефактов, стилей и эпистемической семантики.  
**Контрольные исследования:** тема 00 `Corpus Map & Open Questions` и тема 01 `System Model` третьей ветки.  
**История:** `01-old-notes` рассматривается только как исторический источник.  
**Проверка реализации:** выборочная повторная сверка `ForestTiger-GH/stratbox` `main` и ранее зафиксированных срезов `stratbox-windows` от 2026-10-06. Автоматические тесты в рамках этого исследования не запускались.  
**Граница публикации:** используется только нейтральная публичная модель расширений и хранилищ; внутреннее устройство закрытых корпоративных расширений не рассматривается. Методологические выводы используются как смысловые правила без описания структуры внешних методологических репозиториев.

---

## 0. Executive synthesis

**[CONSOLIDATED]** Целевая Data → Knowledge Architecture Strategy Box — **две взаимосвязанные, но различимые вертикали**:

1. **Data & reproducibility**: источник → фиксированный снимок публикации → техническое декодирование → семантическое наблюдение/набор данных → валидация → вычисление/реконструкция → воспроизводимый результат → артефакт и lineage.
2. **Evidence & meaning**: определение измеряемой величины → наблюдение → интерпретация/модель → основание → квалифицированное утверждение → границы неопределённости и сопоставимости → разрешённый способ использования → актуализация и повторная оценка.

Второй контур принципиален. **Файл не является данными по смыслу; канонические данные не становятся доказанной истиной; операция не становится доказательством только потому, что завершилась успешно; артефакт не равен аналитическому результату.**

Исходный программный путь:

```text
external authority
 → SourceDescriptor
 → SourceSnapshot
 → raw preservation
 → technical decoding
 → semantic normalization
 → canonical data
 → validation
 → derived / reconstruction
 → evidence
 → claim / analytical result
 → view
 → artifact
 → artifact lineage / provenance
```

нужно понимать как **ориентир разбора**, а не как обязательный линейный конвейер каждой операции. В реальной аналитике это ориентированный граф: один источник содержит несколько серий, набор данных зависит от нескольких snapshot, результат может объединять наблюдения и модельные допущения, а один результат представляется несколькими артефактами. Обратная связь необходима: новое наблюдение или новая версия классификатора может потребовать переоценить прежнее утверждение.

### Восемь основных консолидированных решений

| № | Вывод | Уровень |
|---|---|---|
| 1 | `stratbox` остаётся владельцем предметной семантики источников, данных, алгоритмов, валидации и доказательных связей | **CONSOLIDATED** |
| 2 | `FileStore` остаётся интерфейсом физических файловых действий; `FormatRegistry` и семантические адаптеры находятся выше | **CONSOLIDATED** |
| 3 | `SourceDescriptor`, `SourceSnapshot`, `RegistrySnapshot` и `DatasetVersion` различаются по identity и жизненному циклу | **CONSOLIDATED** на уровне семантики; **TARGET-HYPOTHESIS** на уровне сериализуемых схем |
| 4 | Исходные байты, использованные для существенного расчёта, должны иметь фиксируемую content identity и воспроизводимое происхождение | **CONSOLIDATED**; политика обязательной физической архивации зависит от класса данных |
| 5 | `Artifact` — логический результат с устойчивым ID, manifest и provenance; `Workspace` остаётся изменяемой областью | **CONSOLIDATED** |
| 6 | Семантика аналитического результата принадлежит core; пользовательский каталог, доступ, поиск, retention и связь с Work — application runtime | **CONSOLIDATED**, устраняет прежнее пересечение ownership |
| 7 | Claim/Evidence/Knowledge нужны как **смысловые различения**; единый тяжёлый ClaimStore не доказан | **CONSOLIDATED / UNKNOWN** |
| 8 | Полноценный content-addressed store и выбранная физическая DB-топология требуют workload-пилота; немедленное построение общей платформы избыточно | **TARGET-HYPOTHESIS**, не Product Decision |

**Главный результат исследования:** для следующего шага важнее стабилизировать **идентичности, временную семантику, contracts и обязательные связи**, чем создавать много новых пакетов и хранилищ. Маленький работающий сквозной путь с настоящими исходными данными ценнее гигантской таксономии без пользователя.

---

# 1. Scope, исследовательская дисциплина и provenance

## 1.1. Что именно требует тема 03

Тема 03 программы требует исследовать совместно `FileStore`, workspace, cache, scratch/staging, файловые форматы, каталоги источников, lifecycle справочников, canonical datasets, provenance, artifact model/catalog, наборы оформления, metadata, authoring, retention, hashes, freshness, lineage и Knowledge. Обязательные неразрешённые вопросы: владелец Artifact Catalog; связующий объект между SourceSnapshot/Dataset/Artifact; provenance обычных операций; current result против historical artifact; момент, когда cache входит в воспроизводимость; физический путь против Artifact ID.

Это **исследование семантического data/knowledge spine**, а не полная спецификация execution engine (тема 04), БД и совместного состояния (тема 05), плагинной модели (тема 06), UI (тема 07) или безопасности и отказоустойчивости (тема 08). Здесь фиксируются их зависимости и границы.

## 1.2. Уровни утверждений

- **CURRENT** — подтверждено изученным кодом либо точным фактическим baseline с указанной датой; после среза требует обычной проверки изменений.
- **CONSOLIDATED** — устойчивый межисследовательский вывод, согласованный с фактами и логическими границами.
- **TARGET-HYPOTHESIS** — рекомендуемая целевая модель, ещё ожидающая Product Decision и/или пилота.
- **CONFLICT** — предложения расходятся по ответственности, семантике или физической реализации.
- **SUPERSEDED** — прежнее предложение вытеснено актуальным baseline или более точным выводом.
- **UNKNOWN** — данных для честного решения недостаточно.

Такая классификация **не является приоритетом источников**: поздняя идея не становится истинной просто за счёт даты; большое количество повторений также не означает независимое подтверждение.

## 1.3. Иерархия источников и пределы проверки

1. **Программа и governance:** [программа темы 03](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/strategy_box_03_consolidation_research_program.md), [README третьей ветки](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/README.md), [карта корпуса темы 00](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_00_corpus_map_open_questions_2026-10-08.md) и [System Model темы 01](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_01_System_Model_consolidated_research_2026-10-08.md).
2. **CURRENT baseline:** [срез `stratbox` от 2026-10-06](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_base_study_current_state_2026-10-06.md), [срез `stratbox-windows` от 2026-10-06](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md). Фиксированные commit baseline: `stratbox e968853572676d8e5d963607d1f0cb50ff8f20b7`; `stratbox-windows 959e9c4ce1441124af5111c1e025041714e04d3b`.
3. **Тематическая доказательная база:** исследования файлов/артефактов, реестров/источников, форматов, переносимости бизнес-кода, стилей, источников ошибок, multi-user и эпистемической семантики (полный ledger — §22).
4. **Выборочный текущий code probe:** публичные исходники `FileStore`, HTTP, CBR collector, escrow, cbr_forms, SORS и ресурсного loader (перечень в §22). Эти проверки **не являются** полным новым аудитом всего кода и не заменяют runtime tests.
5. **Внешние технические ориентиры:** W3C PROV, DCAT 3, CSVW, OpenLineage, SQLite; используются как проверка архитектурных понятий, а не как доказательство того, что Strategy Box их реализует.
6. **Исторические заметки:** используются для выявления прежних намерений и устаревших решений; актуальную архитектуру определяет текущий owner и новая консолидация.

В этом файле нет публикации закрытых технических подробностей конкретных расширений. Внешние инфраструктурные реализации рассматриваются только как нейтральные providers по собственным открытым контрактам.

---

# 2. Current Truth: что реально есть сегодня

## 2.1. `stratbox` уже содержит настоящее аналитическое ядро

**[CURRENT]** Исследованный пакет `stratbox` `0.8.0` содержит `base` (FileStore, IO API, network, runtime, styles), `common`, `registries`, `text` и банковские/макроэкономические домены `cbr_file_collector`, `cbr_forms`, `cbr_industries`, `cbr_sors_restoration`, `escrow`, `frg`. Подсистемы имеют разную зрелость; их объединяет естественная цепь от официального источника к проверяемому результату.

| Подсистема | Реальный data path | Что служит архитектурным доказательством | Главный gap |
|---|---|---|---|
| `cbr_file_collector` | встроенный source list → загрузка → сохранение raw ZIP/файлов | typed `CbrFileRegistryItem`, `CbrDownloadedFileSource`, `CbrCollectedFile`, `CbrFileCollectResult` | нет единого зафиксированного SourceSnapshot с SHA, validation и version identity |
| `cbr_forms` | archive/DBF → physical model → semantic model → canonical long → Excel | form 802, `IndicatorId`, CSV semantic catalog, различение blank/zero | у части форм сильна близость build/export; схемы и provenance неодинаковы |
| `cbr_industries` | discovery → download/cache → parse → normalized stream → derived → pivots → workbook | typed contracts и тесты, явная география | ограничение одной основной series; локальная geography/version policy |
| `cbr_sors_restoration` | множественные публикации/ограничения → deterministic closure/solver → qualified reconstructed facts → audit grids | строгая evidence hierarchy, source intervals, proof IDs, assumption tiers | воспроизводимый run manifest, performance cache и registry governance ещё надо свести в общий contract |
| `escrow` | index discovery → monthly XLSX/cache → canonical history → views → XLSX/ZIP | разделённые Request/Result, исторические layouts, structured failures | hash/snapshot/registry версии не унифицированы; dedicated tests на срезе отсутствуют |
| `frg` | file scan → classification/period → latest set → cleanup plan/apply → archive | plan/apply и сохранение неизвестных файлов | parser functions пока заглушки; полноценный semantic data path отсутствует |

**Важно:** SORS — не «просто более умный parser»: он различает опубликованные округлённые числа и латентные количественные величины, сохраняет ограничения, источник и доказательную силу каждого восстановленного значения. Именно этот пример показывает, почему общее `value` без epistemic qualification недостаточно.

## 2.2. FileStore, IO и network

**[CURRENT]** [`FileStore`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/filestore/base.py) задаёт read/write/exists/stat/list/mkdir/remove/rename; `read_bytes` и `write_bytes` реализуются поверх потоков, а `copy` по умолчанию использует чтение всего содержимого в память. Это нейтральный файловый интерфейс, **без предметного знания формата**.

**[CURRENT]** `base.ioapi` охватывает Excel, CSV, DBF, архивы, XML, текст, изображения и документные форматы, но полнота чтения/записи и установка optional dependencies различаются. Не следует считать «формат встречается в ioapi» доказательством полноценного semantic parser или writer.

**[CURRENT]** [`DownloadResult`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/net/http.py) содержит `ok`, `status_code`, `content`, `error`, `final_url`, `headers`. Это HTTP result, **не SourceSnapshot**: в нём отсутствуют обязательные для воспроизводимости source ID, fetched_at, checksum, schema validation, lineage и логический artifact ref. Текущий downloader загружает response content целиком.

## 2.3. Sources / registries

**[CURRENT]** Collector хранит встроенный каталог из 41 источника; другие домены делают собственный discovery. Реестры банков, aliases, наборов банков и ОКВЭД2 находятся внутри core, а варианты географии живут в нескольких доменах. [`registries/_loader.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/registries/_loader.py) выбирает packaged resource по файловому `mtime`. Это плохо определяет смысл версии, хотя в обычном установленном wheel может технически работать.

**[CURRENT, датированный факт 2026-10-06]** В bundled bank registry использовался snapshot примерно февраля 2026 года; для ОКВЭД2 — resource с датой 01.11.2025. Публичные источники к октябрю 2026 года уже содержали более новые материалы. Это сигнал отсутствия управляемого freshness contract, а не доказательство неверности каждой отдельной записи.

## 2.4. Фактическое состояние артефактов в `stratbox-windows`

**[CURRENT на срезе 2026-10-06]** Windows сохраняет `ArtifactRecord` с именем/путём, видом, автором, датой и связями с case/operation/log. Виды в основном выводятся из расширения файла. Логи и артефакты проецируются в сценарный чат и инспектор. Пять JSON-проекций истории содержат cases/events/artifacts/logs/assignments.

**[CURRENT]** Эта модель уже лучше простого списка путей, но пока не является content-identified artifact service: нет подтверждённого сквозного immutable manifest/transactional commit, глобального каталога, retention и полноценной lineage identity. Local JSON не гарантирует durable multi-user truth.

## 2.5. Чего не следует выдавать за реализованное

| Целевой элемент | Реальный статус на исследованном baseline |
|---|---|
| Общий `SourceDescriptor` / `SourceSnapshot` API для всех доменов | **UNKNOWN как утверждённый контракт / отсутствует как единый зрелый слой** |
| Единый versioned `RegistrySnapshot` и updater | **целевая гипотеза** |
| Cross-domain `DatasetVersion`, пригодный для lineage | **целевая гипотеза** |
| Универсальный `FormatRegistry` с detection/capability matrix | **целевая гипотеза** |
| Immutable ArtifactStore и Artifact Catalog | **целевая гипотеза** |
| Полный Content-Addressed Store | **целевая гипотеза** |
| Универсальный Claim/Evidence Store | **открытый вопрос** |
| Автоматическая invalidation всех зависимых результатов | **открытый вопрос** |
| Работающий shared-node artifact catalog / remote materialization | **целевая гипотеза** |

---

# 3. Каноническая предметная семантика данных

## 3.1. Восемь смысловых границ

| Различение | Что означает | Ошибка при смешении |
|---|---|---|
| `SourceDescriptor` / `SourceSnapshot` | ожидаемая серия или endpoint / фактически полученное содержимое | поздняя ревизия незаметно подменяет использованную публикацию |
| `Registry` / `SourceCatalog` | что за сущности и коды / откуда и как получить данные | политика идентичностей перемешивается со списками URL |
| `RawFile` / `Observation` | физические байты / интерпретированное измерение | числа без единиц, периметра и периода |
| `DatasetDefinition` / `DatasetVersion` | устойчивый semantic набор / конкретная materialized version | изменяемый DataFrame становится «той же самой» версией |
| `Reported` / `Derived` / `Reconstructed` | официально опубликовано / вычислено / доказательно восстановлено | модельный результат выдаётся за публикацию |
| `Evidence` / `Claim` | основание / проверяемое утверждение | одинаковый файл считается доказательством любого вывода |
| `AnalyticalResult` / `Artifact` | результат анализа и его квалификация / представление результата в файле | красивый Excel с ошибкой интерпретации воспринимается как success |
| `ContentIdentity` / `ArtifactId` / `Path` | одинаковые байты / логический объект / местонахождение | переименование файла ломает историю либо разные результаты ошибочно сливаются |

## 3.2. Observation: минимальная восстановимая семантика

**[CONSOLIDATED]** Для банковской и макроэкономической аналитики значение является осмысленным наблюдением только при восстановимых измерениях:

- **subject identity** — банк, группа, территория, отрасль, сектор или другой объект;
- **measure/construct** — определение показателя, а не пользовательский label;
- **value + value semantics** — тип, точность, unit/currency/scale, пустое значение, нуль и special codes;
- **perimeter** — standalone/consolidated, РСБУ/МСФО, prudential/statistical, включения/исключения;
- **time** — период состояния или потока, период публикации, информация as-of, revision/vintage;
- **classification identity** — версии ОКВЭД, региональных справочников, форм и иных mapping;
- **epistemic role** — reported, normalized, derived, reconstructed, estimated, selected и т. п.;
- **provenance handle** — ссылка на source snapshot, transformation или proof, достаточная для восстановления происхождения.

Это **требование к доступности смысла**, а не команда хранить все поля физически в каждой строке таблицы: часть может идти через DatasetVersion manifest и ссылки на общие `MeasureDefinition`, `RegistrySnapshot` и `SourceSnapshot`.

### Пример существенного смыслового конфликта

Показатель «кредиты корпоративным клиентам, млрд руб.» без указания, консолидированная ли группа, включает ли он отдельные виды требований, как обрабатывается секьюритизация, по какому стандарту он получен и на какую дату зафиксирован, **не образует автоматически сопоставимую серию**. Приведение к одинаковой денежной единице решает только масштаб, но не периметр. Необходимы либо explicit bridge/adjustment, либо qualifier `NOT_COMPARABLE` / `COMPARABLE_WITH_LIMITATIONS`.

## 3.3. Missingness — часть данных, а не косметика

**[CONSOLIDATED]** Пусто, 0, «нет публикации», suppressed, недоступно, «вне определения», «не применимо», «ниже порога», техническая ошибка и интервал возможных значений различаются. В ядре `cbr_forms` уже есть пример сохранения `blank != 0`; SORS демонстрирует ещё более строгую семантику округления и восстановленного диапазона.

**[TARGET-HYPOTHESIS]** Унифицированное представление должно как минимум уметь нести `present`, `missing`, `not_applicable`, `suppressed`, `unknown`, `interval`, `invalid`, а исходный источник/версия метода уточняют детали. Для первой реализации допустимо ограничить этот перечень реальными потребителями, но смешивать `None` и 0 нельзя.

## 3.4. Semantic definition и versioning

- `MeasureDefinition` описывает имя, определение, расчёт/формулу (если применимо), единицу, частотность, basis, perimeter, временную семантику, нормативную редакцию/действие и известные structural breaks.
- `EntityIdentity` не привязывается к отображаемому названию; одинаковый бренд может относиться к разным юридическим сущностям.
- `ComparabilityRelation` связывает пары measure/entity datasets **для конкретного use case и при конкретном bridge**, а не предоставляет один глобальный булев флаг `comparable`.
- `Version` определяется изменением content, definition, source authority, методики или classification, а не только названием файла.

## 3.5. Canonical не равно true

**[CONSOLIDATED]** Каноническая модель — стандартизованное внутреннее представление для определённого смысла. Она может верно воспроизводить официальную публикацию, но ещё не доказывать причинное объяснение, корректность внешней оценки либо текущую применимость. `Normalized` не означает «исправлено до объективной истины». Автоматическое повышение статуса запрещено.

---

# 4. Source plane: каталог → фактическая публикация

## 4.1. Источник как descriptor, а не URL

**[CONSOLIDATED]** `SourceDescriptor` имеет устойчивый `source_id` и сообщает, какую серию/канал/authority система ожидает, как искать её данные и чем проверить соответствие. Одна публикация может появиться на новом URL, а один URL может многократно отдавать пересмотренный файл.

**[TARGET-HYPOTHESIS]** Компактный верхний contract:

```text
SourceDescriptor
  source_id
  authority_id
  semantic_series_id / declared_construct
  discovery_kind       # direct / index_discovery / parameterized / registry_upstream
  locator / discovery_spec
  publication_cadence  # expectation, not schedule
  format/schema expectations
  validation_profile_id
  freshness_policy_id
  status/policy
```

Source Catalog принадлежит core как семантика источников; scheduler, который решает, когда проверять новые публикации, принадлежит application execution owner. `cadence = monthly` **не означает** автоматического выполнения операции первого числа.

## 4.2. SourceSnapshot как главное место фиксации bytes/vintage

**[TARGET-HYPOTHESIS, высокий приоритет]** При фактическом получении содержимого создаётся record, который отдельно описывает **происшествие получения**, **то, что зафиксировано**, и **валидацию**:

```text
SourceSnapshot
  snapshot_id
  source_id
  authority_id / publication_id, if known
  requested_url / resolved_url / final_url
  retrieved_at
  released_at / published_at / effective_period, if known
  HTTP status, ETag, Last-Modified, content type
  content_size_bytes
  content_digest = sha256:...
  declared_extension / detected_format_id / source_schema_version
  validation_status + validator_version + issues[]
  raw_content_ref          # immutable blob/artifact ref OR certified external immutable locator
  access/retention policy reference
```

**Важное уточнение:** одинаковый SHA-256 означает идентичные байты, **но не тождество публикационных событий**. Две загрузки с одного URL могут иметь разные `retrieved_at` и результаты validation, сохраняя тот же digest. Снимок публикации и событие скачивания не обязаны быть одним объектом: на первом этапе возможна единая модель с отдельным fetch metadata и стабильным `snapshot_id`. При частом polling полезно выделить `FetchAttempt`/`FetchReceipt` без создания дубликатов raw payload.

**Второе уточнение:** digest достаточен для проверки идентичности содержимого; он сам по себе не подтверждает, что данные действительно поступили от объявленного authority. Для этого сохраняют trusted origin, цепочку redirect/transport verification, при необходимости подпись/аттестацию и условия внешнего получения.

## 4.3. Три независимые даты

Для обычной публикации нельзя слить в одно поле:

1. `period_covered` — к чему относится статистика;
2. `published_at` / `information_available_at` — когда содержание могло стать доступным аналитику;
3. `retrieved_at` — когда Strategy Box его получил.

Для пересмотренных данных дополнительно нужен `vintage/as_of_revision`. Это критично для backtest и реконструкции «что можно было знать на дату X». Историческая серия, скачанная в октябре, не становится автоматически октябрьской статистикой.

## 4.4. Discovery, validation и ошибки

Путь загрузки:

```text
resolve SourceDescriptor
 → discover expected publication
 → fetch with bounded network policy
 → identify bytes/format
 → apply source-aware validation
 → stage original content
 → commit SourceSnapshot + content identity
 → publish typed result
```

**[CONSOLIDATED]** HTTP 200 с HTML-страницей ошибки, ZIP с неполным составом, XLSX неожиданной схемы, повреждённый архив, новая версия формы и отсутствие публикации должны выдавать разные результатные статусы. `not_found`, `unavailable`, `schema_changed`, `validation_failed`, `needs_review` и `unchanged` — разные исходы.

**[TARGET-HYPOTHESIS]** До окончания commit должен существовать `SourceFetchResult` / `SourceValidationResult`; завершившийся HTTP GET **не равен** принятому SourceSnapshot.

## 4.5. Один source — несколько физических представлений

Семантическая серия может публиковаться через страницу-индекс, ZIP, DBF, Excel или API; один bundle может включать `data.csv + structure.csv + meta.csv`. Каталог описывает discovery, форматный слой идентифицирует физический container, а домен определяет смысл. При bundle все взаимозависимые компоненты должны фиксироваться как **одна согласованная source revision**, а не выбираться независимо «по самому свежему файлу».

---

# 5. Registry plane: reference identity и управляющие snapshots

## 5.1. Слово «реестр» перегружено

**[CONSOLIDATED]** Нельзя смешивать пять классов:

| Класс | Назначение | Owner |
|---|---|---|
| Reference Registry | банк, ОКВЭД, география, версии кодов/названий | `stratbox` domain/reference layer |
| Human/Policy Overlay | aliases, ручные replacement, выбранные наборы | semantic registry/policy owner; права редактирования отдельно |
| Source Catalog | где и как получить внешние данные | `stratbox` source semantics |
| Domain Rule Registry | семейства FRG, модели форм, SORS-публикации | соответствующий домен |
| Capability/Style Registry | доступные operations, formats, styles | соответствующий contract owner, не общий God Registry |

Едиными должны быть жизненный цикл snapshot, stable IDs, схемы, проверка, provenance, status; физическая общая папка или «супер-реестр» не требуется.

## 5.2. RegistrySnapshot и provenance

**[TARGET-HYPOTHESIS]** Минимум:

```text
registry_id
snapshot_id
upstream_version / effective_from / effective_to
source_publication_ref(s)
retrieved_at
schema_version
transform_version
file_part_digests[]
validation_status
```

`RegistryDescriptor` задаёт семантику и policy, `RegistrySnapshot` — конкретную принятую редакцию. Манифест явно выбирает resource, проверяет SHA и устраняет неоднозначность зависимости от `mtime`. Для `registry` с человеческими overlays срок актуальности не определяется теми же правилами, что для ежемесячного upstream.

## 5.3. География: реальный cross-domain gap

**[CURRENT]** `cbr_industries` использует публикационный layout примерно из 96 строк; SORS строит иные атомарные и публикационные представления; escrow полагается на собственный порядок/нормализацию. Плоский файл `regions.csv` недостаточен: «регион», «федеральный округ», «РФ», «публикационная строка» и «область без части территории» — разные типы объектов.

**[CONSOLIDATED]** Общая география должна хранить устойчивые canonical entities и valid-time relations, а локальная source-specific geography mapping остаётся доменной проекцией. Архитектура должна позволять восстановить, каким mapping конкретная серия пришла к canonical `region_id`.

## 5.4. ОКВЭД2 и банки

- Устойчивые bank identity строятся вокруг кода/регистрационного идентификатора, а не только русского label.
- Aliases и пользовательские sets — другая authority, чем официальный банковский registry.
- ОКВЭД2 — версионируемый кодовый справочник; SORS-specific 88-class projection и crosswalk являются доменными derivations, а не глобальной истиной ОКВЭД.
- При изменении версии классификатора исторические значения автоматически не пересчитываются как «та же серия»: нужна явная версия mapping и правила comparability.

## 5.5. Authoring, admission, history

**[CONSOLIDATED]** Для packaged reference registry подходит Git-based authoring: отдельный fetch/updater создаёт candidate revision → schema/semantic tests → review/admission → manifest + packaged asset. Установленный пакет читается как immutable build. **Current runtime** не должен молча править packaged registry.

**[TARGET-HYPOTHESIS]** Первый package может хранить один current snapshot при наличии Git/build-history и надёжного run manifest. Но для долгосрочного replay нельзя полагаться исключительно на возможность когда-либо переустановить старый wheel: если источник или набор данных критичен, нужно либо удерживать старую принятую версию, либо явно объявлять невозможность полного replay. Где именно лежит историческая версия — отдельная storage/retention policy.

## 5.6. Freshness — статус с основанием, а не возраст файла

```text
freshness = current / stale / unknown / manual / not_applicable
reason = authoritative change | missed cadence | failed check | policy | ...
as_of = timestamp
last_checked_at = timestamp
next_check_expectation = optional
```

Статус **не может** выводиться из одного `mtime`, HTTP `Last-Modified` или наличия нового файла. `unknown` предпочтительнее необоснованного `current`.

---

# 6. Физические файлы, форматы и staging

## 6.1. Строгие уровни вместо фразы «поддерживаем XLSX»

**[CONSOLIDATED]** Вторая ветка предложила пять независимых уровней работы с форматом. Их следует сохранить, но использовать только нужные данному use case:

| Уровень | Возможность | Пример | Где находится смысл |
|---|---|---|---|
| L0 | opaque storage/transport | записать bytes, получить stream, проверить digest | FileStore / storage capabilities |
| L1 | identification | MIME, magic, container, format ID | Format detector |
| L2 | technical decoding | DBF rows, Excel sheets, ZIP members, XML tree | codec |
| L3 | safe technical encoding | CSV/JSONL/XLSX/Parquet/ZIP | writer/export adapter |
| L4 | semantic interpretation | строка формы 0409802, показатель эскроу, XBRL taxonomy fact | domain parser / semantic adapter |

**Физический формат ≠ предметный формат.** `zip → dbf` может обозначать форму банковской отчётности; `xlsx` может быть выгрузкой регулятора, пользовательским workbook или артефактом отчёта. Расширение сообщает слишком мало.

**[TARGET-HYPOTHESIS]** `FormatRegistry` описывает capabilities (`detect`, `read`, `write`, `stream`, `seekable`, `materialize`, `security_profile`, `dependency_group`); `SourceSnapshot` дополнительно хранит `physical_format_id`, `container_format_id`, `semantic_source_type`, `source_schema_version`. Но наличие одного общего registry не превращает все форматы в общий semantic parser. XBRL и SDMX требуют отдельной предметной обработки, а PDF/DOCX/PPTX не дают автоматически достоверных таблиц.

## 6.2. Read broad / write narrow

**[CONSOLIDATED]** Принимать разнообразные внешние форматы необходимо; обещать качественную универсальную запись во все них — нет. Базовые воспроизводимые outputs: typed in-memory result, CSV/JSONL, XLSX, ZIP; Parquet — для крупных машинных таблиц при потребности. Другие exporters включаются под доказанный use case. Для source-faithful конвертации отдельно сохраняется семантика исходного формата (например, точные DBF types, даты, deleted records, encoding), а не только визуальная похожесть результата.

## 6.3. Scratch, staging, cache, workspace и managed artifact area

| Область | Природа | Можно удалять | Можно использовать как воспроизводимый вход |
|---|---|---|---|
| **Scratch** | временные файлы конкретной операции | после выполнения / recovery lease | нет, пока объект не зафиксирован |
| **Staging** | незавершённая запись в процессе commit | после abort или recovery | нет |
| **Cache** | пересоздаваемое ускорение | по policy, если действительно воспроизводим | только через immutable входную identity и правило восстановления |
| **Workspace** | изменяемые пользовательские файлы | по действию пользователя/политике | после snapshot/import либо explicit mutable-risk qualification |
| **Managed artifact area** | committed outputs и retained raw inputs | по retention/GC с проверкой ссылок | да, при успешно проверенной identity |

**[CONSOLIDATED]** Разделение основано на гарантиях, не на названии директории. Файл `cache/report.xlsx` может фактически быть единственной копией данных — тогда он ошибочно назван cache. Папка `output/` тоже сама по себе не превращает Excel в immutable artifact.

## 6.4. Materialization — явная операция

**[TARGET-HYPOTHESIS]** `materialize_read()` предоставляет локальную временную копию для libraries, которым нужен physical path/seek; `materialize_write()` фиксирует output **только после успешного завершения и validation**. Следует различать:

```text
artifact_ref → materialized local copy
workspace path → imported immutable snapshot
remote artifact → verified local replica
```

При изменении пользователем materialized workbook committed artifact остаётся прежним; изменённый файл является новым mutable workspace state и может быть отдельно импортирован как новая версия. Для большого backend или remote host materialization должна быть ленивой, по требованию клиента, с digest verification.

## 6.5. Настоящие потоки и safety

**[CURRENT]** Дефолтный `FileStore.copy` может прочитать весь файл в память. Несколько кодеков работают через `bytes → tempfile`; отдельные exporters держат весь архив в RAM. **[TARGET-HYPOTHESIS]** Общий потоковый контракт, size limits, chunked hashing, безопасная распаковка и atomic-ish staged commit критичны для масштабных статистических источников.

Важные ошибки: `UnsupportedFormat`, `CorruptFile`, `SchemaMismatch`, `InvalidEncoding`, `DependencyUnavailable`, `ArchiveUnsafe`, `ResourceLimitExceeded`, `PartialExtraction`, `StorageUnavailable`. Каждый тип должен попадать в structured failure, а не превращаться в пустую таблицу.

При импорте ZIP/RAR/7z следует контролировать path traversal, symlink, количество members, глубину nested archives, размер распаковки, compression ratio и потенциальное превышение ресурсов. Успешное техническое декодирование не даёт права исполнять макросы, embedded scripts или внешние ссылки документа.

---

# 7. Dataset plane: от строки к версионированной семантической коллекции

## 7.1. Почему DatasetVersion — недостающее звено

**[CURRENT]** В разных доменах canonical data часто представлены `pandas.DataFrame`, таблицей `long`, набором pivots или собственной dataclass-моделью. Этот способ удобен **в памяти одного процесса**, но без внешней identity невозможно ответить, какие конкретно наблюдения сформировали исторический XLSX, был ли пересчёт после замены справочника, какие ошибки были приняты и можно ли безопасно использовать DataFrame другим сервисом.

**[CONSOLIDATED]** Требуется различать:

- `DatasetDefinition` — смысл серии/набора, схема, dimensions, определения измерений и domain owner;
- `DatasetVersion` — конкретные данные для этих определений, привязанные к источникам, registry snapshots и transformation;
- `DatasetMaterialization` — байтовое представление конкретной версии в CSV/Parquet/XLSX/DB/backend, возможно несколько;
- `DatasetView` — выбранная форма представления, pivot/фильтр/региональный срез, которая при существенном преобразовании может стать отдельной версией.

Один `dataset_id` не идентифицирует содержимое версии, а content digest не выражает семантический смысл набора. Поэтому при потенциально одинаковых bytes разные `DatasetDefinition` могут ссылаться на один blob, сохраняя разные semantic IDs.

## 7.2. Минимальный DatasetVersion contract

**[TARGET-HYPOTHESIS]** Обязательные поля только там, где они реально требуются downstream:

```text
DatasetVersion
  dataset_id
  version_id
  semantic_schema_id + version
  source_snapshot_refs[]
  registry_snapshot_refs[]
  build_operation_id + operation_version
  computation_provenance_ref
  observed_period / vintage / as_of
  row_count / column_count, if tabular
  validation_result_ref
  primary_materialization_ref, optional
  content/semantic digest(s), optional by policy
  created_at
```

`version_id` — opaque ID конкретного построения либо детерминированная identity при строго определённой canonicalization. `content_digest` относится к конкретному сериализованному представлению; он не всегда устойчив к сортировке строк, precision, timezone или codec version. Для semantic equality нужен отдельный, договорённый метод canonicalization, **не “SHA-256 любого parquet”**.

## 7.3. Валидация по нескольким уровням

Вместо одного `valid: true` нужны разные gates:

| Gate | Пример | Что подтверждает |
|---|---|---|
| Transport | HTTP/IO successful, content readable | физическая доставка |
| Format | ZIP/DBF/XLSX корректны | техническая читаемость |
| Schema | обязательные поля, типы, версионированная layout | структурное соответствие |
| Semantic | коды, units, periods, balance identities | правильность интерпретации по выбранной модели |
| Domain consistency | агрегаты, допустимые отношения, crosswalk | предметная согласованность |
| Evidence qualification | источник, rounding, assumption tier, proof | доказательная сила результата |
| Consumer fitness | пригодно ли для конкретного использования | ограниченная допущенность применения |

`transport_success = true` **не** означает `semantic_valid = true`; `semantic_valid = true` не означает `suitable_for_decision = true`. Частичный успех должен хранить `accepted_parts`, `rejected_parts`, `warnings`, `failure_policy` и residual UNKNOWN.

## 7.4. TransformationRecord и lineage

**[CONSOLIDATED]** Объект, который связывает `SourceSnapshot → DatasetVersion → Artifact`, — **не одна универсальная таблица “File”**. Связь создают:

1. stable `SourceSnapshotRef` для фиксированного входа;
2. `Transformation/DomainOperationRun` с versioned operation, параметрами и method identity;
3. `DatasetVersionRef` на полученную семантическую коллекцию;
4. `AnalyticalResultRef` на квалифицированный вывод, если он есть;
5. `ArtifactRef` на материализованное представление;
6. typed lineage edges между ними.

Ближайший минимальный вариант — `RunProvenanceManifest`, содержащий списки inputs/outputs, versioned program/parameters/registries. Для сложных результатов необходимо хранить не только связь наборов данных, но и конкретные evidence/proof references.

## 7.5. Unit, currency, perimeter, geography

Нормализация валюты и масштаба — не одна операция. Пересчёт через FX предполагает `rate_source_snapshot`, quote date, temporal convention, валютную пару, округление и цель приведения. Банковская консолидация требует отдельного perimeter bridge. При split/merge регионов и изменениях ОКВЭД нужна versioned map с указанием loss/aggregation и допустимого temporal interval.

**[TARGET-HYPOTHESIS]** Общий слой должен давать primitives для units/period/identity/provenance. Предметное решение о конкретной методике IFRS/RAS, округлении ЦБ, кросс-сопоставлении банков или реконструкции SORS остаётся внутри домена.

---

# 8. Knowledge plane: когда данные становятся доказательным знанием

## 8.1. Source ≠ Fact, Canonical ≠ Truth

**[CONSOLIDATED]** Источник с высоким авторитетом достоверно устанавливает **что именно он опубликовал** в данной редакции. Он не гарантирует автоматически истинность внешнего мира, безусловную сопоставимость с другим источником или корректность причинного вывода. Концептуальные переходы требуют оснований:

```text
SourceSnapshot
   ├→ Observation (что опубликовано / измерено)
   ├→ Semantic normalization (что означает значение в принятой модели)
   └→ Qualified statement about publication

Observation(s) + Definitions + Assumptions + Method
   → Derived Result / Inference
   → Evidence argument
   → Qualified Claim
   → Reliance for specific use
```

**Нельзя** превращать каждый ряд данных в отдельный `Claim` и каждый нормализованный столбец в `Knowledge` автоматически. Эпистемический слой нужен там, где производится утверждение, сравнение, объяснение, оценка, прогноз или вывод, способный повлиять на работу пользователя.

## 8.2. Claim как квалифицированное утверждение

**[TARGET-HYPOTHESIS]** Для material claim полезны следующие смысловые атрибуты:

```text
Claim
  claim_id
  proposition / predicate + subjects
  kind = reported | descriptive | comparative | explanatory |
         causal | predictive | conditional | evaluative | ...
  scope / period / perimeter / conditions
  support_state
  uncertainty + assumptions
  contradiction / alternative hypotheses
  valid_time / information_as_of
  currentness_state
  permitted_reliance
  grounds[] → EvidenceRefs
  produced_by → Result/RunRef
```

Эта схема **не является** требованием создать тяжёлый graph DB или все типы Claim с первого дня. На начальном этапе достаточно структурированного statement в `AnalyticalResult` для случаев, где квалификация материальна.

## 8.3. Evidence — не только ссылка на CSV

**[CONSOLIDATED]** Обоснование должно отвечать: *какие факты, определения, ограничения, преобразования и допущения делают именно этот вывод допустимым?* Возможные evidence roles:

- `reported_source` — буквальная публикация;
- `semantic_mapping` — правила интерпретации;
- `aggregation_identity` — тождество суммы/компонент;
- `transform_proof` — проверенная детерминированная операция;
- `model_assumption` — предпосылка модели, в отличие от официального факта;
- `inference_certificate` — математический сертификат/feasibility/оптимизационный статус;
- `reconciliation` — объяснённое расхождение источников;
- `human_review` — проверка и допуск, без автоматического повышения authority опубликованного значения.

При нескольких «источниках», которые переписывают один и тот же первичный документ, lineage должен хранить их общую зависимость, иначе повторение ошибочно усиливает доказательную силу.

## 8.4. SORS как проверка эпистемической модели

**[CURRENT]** Специализированный модуль реконструкции строит модель latent quantities, учитывает интервалы округления и ограничения, различает `STRICT_OFFICIAL`, `SOURCE_PRESERVING`, `ROUNDING_OPTIMAL`, `ROUNDING_PREFERRED`, `ROUNDING_SELECTED`, сохраняет поддерживающие факты, target bounds, events и conflicts.

Например, официальное значение **6 млн руб.**, округлённое до миллиона, представляет допустимый bucket вокруг 6, а не обязательно точно 6 на латентном уровне. Целевая общая модель должна сохранять `value + value_kind + interval + evidence_tier + proof_ref`; просто `value=6, status=verified` будет эпистемически ложным сжатием.

**[CONSOLIDATED]** Базовый data plane обязан **сохранять возможность** для такого богатого доказательного результата, но **не копировать** весь специализированный solver/evidence architecture в обычные домены escrow и collector. Общий contract должен быть малым, расширяемым и не повышающим статус; SORS-specific evidence/ledgers остаются внутри SORS.

## 8.5. Аналитический результат — больше, чем таблица

`AnalyticalResult` отделяет собственный вывод от источников, алгоритма и его representations:

```text
AnalyticalResult
  result_id
  subject / question / intended_use
  primary_findings[]             # qualified claims or structured outcomes
  evidence_refs[]
  dataset_refs[]
  methods/assumptions[]
  limits / unresolved[]
  currentness/validity qualifier
  assessment / acceptance state, if needed
  provenance_ref
  artifact_refs[]                 # materializations, not truth
```

Система должна допускать result **без Excel**, result с несколькими файлам и result с неопределённостью. Проверка выполнения операции (`job complete`) не эквивалентна принятию аналитического вывода человеком (`result accepted`). Отдельное человеческое согласование тоже не доказывает математическую истинность данных.

## 8.6. Knowledge не должно быть копией Research History

**[CONSOLIDATED]** Текущее поддерживаемое знание — это согласованные определения, основания, актуальные квалифицированные выводы, ограничения и оставшиеся противоречия. Исторические исследования сохраняют историю гипотез и решений. **Их следует связывать**, но нельзя считать архив отдельных записок автоматически актуальным Knowledge.

В продуктовой архитектуре это различение проявляется как:

```text
Immutable historical observations/results/evidence
      │
      ├── currentness / challenge / revalidation relations
      ▼
Qualified maintained knowledge projection, when needed
```

**[UNKNOWN]** Достаточно ли `Result + ClaimRefs + provenance + review state` или нужен независимый Knowledge Catalog/ClaimStore? Ответ зависит от реальных потребителей — долгоживущих исследований, cross-report reconciliation, аудита и machine reasoning. До появления таких сценариев универсальную инфраструктуру создавать преждевременно.

## 8.7. Контроль эпистемических границ

При каждом значимом преобразовании полезно задать три вопроса:

1. **Что изменилось?** Только представление, сами данные, определение показателя или статус доказательности?
2. **На каком основании?** Есть ли новая публикация, проверка, модель, допущение или независимое подтверждение?
3. **Что осталось UNKNOWN?** Какие периоды, регионы, компоненты, предпосылки либо сравнения по-прежнему не разрешены?

Для автоматизированного или AI-потребителя эти distinctions должны быть машинно доступными; интерфейс может делать их краткими, но не должен менять исходную qualification.

---

# 9. Provenance, lineage и reproducibility

## 9.1. Единая семантика provenance при разных глубинах

**[CONSOLIDATED]** Каждый существенный run несёт лёгкий `RunProvenanceManifest`; специализированные домены расширяют его собственными proof/ledger. Сведения сохраняются рядом с соответствующей authority, а не собираются в один гигантский объект.

Минимум:

```text
run_id / domain_operation_id / operation_revision
code_build_id / runtime_environment_version
input_refs[] + exact content digests where material
source_snapshot_refs[]
registry_snapshot_refs[]
parameters_digest + safe reproducibility parameters
semantic_schema_versions[]
method/model/solver_version, when relevant
validation_result_refs[]
outputs[] + artifact_refs[]
started_at / completed_at
partial/failure/warnings/unknown flags
```

Важна **фиксированная effective configuration** на момент запуска. Если стиль, ручной набор банков или template позднее меняются, исторический результат остаётся объяснимым по зафиксированной версии.

## 9.2. DAG как минимальный общий язык

```text
SourceSnapshot S1 ─┐
                   ├── used_by T1 ── generates DatasetVersion D1
RegistrySnapshot R1┘                       │
                                         used_by T2
                                            │
                                 ┌──────────┴────────────┐
                                 ▼                       ▼
                          AnalyticalResult A       View V1
                                 │                       │
                                 └──── represented_as ───┴──> Artifact F1
                                                              │
                                                        materialized_at
                                                              ▼
                                                        Workspace path
```

Типы рёбер минимально: `used`, `derived_from`, `generated`, `validated_by`, `represented_as`, `depends_on_registry`, `materialized_at`, `supersedes`, `challenges`, `revalidates`. Смысл `supersedes` не означает, что старые bytes или старое evidence уничтожены.

## 9.3. Почему нельзя строить только по файлам

**[CONSOLIDATED]** Два одинаково названных файла из разных периодов — разные source snapshots; один файл может быть представлением нескольких datasets; один dataset — основой нескольких reports; один claim — иметь evidence из разных source families. Directory tree, имена и timestamps недостаточны. Система должна хранить явные refs и typed edges.

## 9.4. Reproducibility tiers

**[TARGET-HYPOTHESIS]** Вместо бинарного `reproducible` полезнее различать:

| Tier | Что гарантировано | Требования |
|---|---|---|
| R0 — traceable | можно объяснить, откуда результат | source IDs, method, basic provenance |
| R1 — input-identical | есть точные входы и версии | retained bytes/immutable refs, versioned registries |
| R2 — replayable | можно заново исполнить согласованный метод | code/runtime deps, параметризация, solver/model versions, controlled environment |
| R3 — output-verifiable | можно проверить output по заявленным правилам | stable validation/certificate, digest/semantic equivalence policy |
| R4 — audited/accepted | результат прошёл самостоятельную оценку для указанного назначения | review, acceptance, scope, decision lineage |

R4 не является «самой истинной версией» R3: техническая повторяемость, доказательная пригодность и человеческая ответственность — разные оси. Эта шкала — **только кандидат**, её не следует превращать в обязательную универсальную enum для всех операций.

## 9.5. Эффект обновления источника

При новом SourceSnapshot:

```text
new snapshot
 → compare old content/schema/period/authority
 → determine actual downstream dependencies
 → mark impacted DatasetVersions/Results as needs_review or stale_for_use
 → retain old versions
 → optionally propose successor Work / targeted recomputation
```

**[CONSOLIDATED]** Новый файл не делает каждое прежнее утверждение автоматически ложным. «Вышла новая статистика» и «на дату старого результата доступной информацией была предыдущая публикация» одновременно могут быть истинными. Currentness зависит от **вопроса, времени и intended use**.

## 9.6. Дедупликация content и независимость свидетельств

SHA-256 помогает хранить одинаковые bytes один раз и находить повторные публикации, но не устраняет семантическое различие источников. Аналогично два независимых файла с одинаковым числом не являются автоматически независимыми доказательствами, если оба восходят к одной базе. Поэтому в графе должны существовать **два уровня**: physical content identity и semantic/provenance relationship.

---

# 10. Artifact system: стабильная идентичность результата

## 10.1. File, Artifact, Result, Workspace

**[CONSOLIDATED]** Нужны четыре разных вопроса:

- **File/Blob:** где лежат bytes и можно ли их прочитать?
- **Artifact:** какой это зафиксированный логический output, из каких частей состоит и с какой идентичностью?
- **AnalyticalResult:** какой вывод/структурированный результат существует и на каких основаниях?
- **Workspace:** где человек редактирует, импортирует, экспортирует и организует файлы?

`Artifact` может быть raw-source artifact, dataset snapshot, Excel workbook, report, log bundle или archive. Обычный файл в workspace **не обязан** автоматически получать immutable identity. Как только файл становится долговременным результатом, общим вводом, опубликованным объектом или evidence, возникает необходимость snapshot/commit.

## 10.2. Logical Artifact contract

**[TARGET-HYPOTHESIS]**

```text
ArtifactDescriptor
  artifact_id                 # opaque, immutable logical identity
  artifact_kind              # report / dataset / raw_snapshot / ...
  display_name
  manifest_schema_version
  manifest_digest
  origin_result_ref, optional
  producer_run_ref, optional
  owner_scope / access_policy_ref
  created_at
  committed_at
  lifecycle_state
  content_parts[]            # independent digest/size/media_type/role
```

`artifact_id` отличен от SHA. Один и тот же набор bytes может быть материализацией разных аналитических результатов или повторным импортом с новой authority/owner. Физические blobs при этом можно дедуплицировать.

## 10.3. Manifest и commit

**[TARGET-HYPOTHESIS]** Versioned manifest может быть минимальным JSON с ID, частями, digests и semantic refs. Все parts должны существовать и быть проверены **до** видимого commit.

```text
begin staging
  → write parts
  → close/verify bytes
  → checksum + validation
  → create canonical manifest
  → commit metadata transaction
  → publish ArtifactCommitted
  → cleanup staging
```

Если запись manifests/content проходит, а транзакция каталога не завершилась, остаётся *orphaned content* для последующей GC, **не видимый успешный artifact**. Автоматическое `close()` потока при исключении никогда не должно означать успешный commit. После `ArtifactCommitted` содержимое является immutable; любое изменение создаёт новую version/ID.

## 10.4. Artifact lifecycle

**[TARGET-HYPOTHESIS]** Минимально полезные состояния/отношения:

```text
staging → committed
        ↘ aborted / quarantined
committed → tombstoned → GC eligible (после retention/hold/reference checks)
committed --superseded_by--> another committed artifact
```

`superseded_by` предпочтительно relation, а не признак физического удаления. `quarantined` должно запрещать опасное использование подозрительных bytes, но сохранять метаданные проблемы для расследования. Retention находится на стыке данных, application policy и storage operations (см. §13).

## 10.5. Content-addressed store: что устойчиво и что открыто

**[CONFLICT разрешён частично]** Файлово-артефактное исследование 02 рекомендует сразу построить небольшой CAS/BlobStore, тогда как тема 00 справедливо требует проверять необходимость новой инфраструктуры реальным workload. Согласованный результат:

1. **Content identity и integrity checks — базовая необходимость.**
2. **Immutable artifact manifest и transactional visibility — сильная целевая позиция.**
3. **Физический CAS как обязательный backend на первом этапе — пока гипотеза.**
4. Возможен pilot: `ArtifactRef + manifest + SHA + managed files` без тяжёлого blob platform; после измерения дубликатов/объёмов/параллелизма выбрать CAS/metadata backend.

В обоих вариантах API не должен раскрывать физическую CAS-топологию потребителю; решение о дедупликации не меняет семантическую identity.

## 10.6. Artifact Catalog: разрешение ownership-конфликта

Существует реальный конфликт литературы: ранняя файловая архитектура склоняется к размещению каталога внутри `stratbox`, поздняя multi-user/host architecture — внутри application runtime.

**[CONSOLIDATED]** Каталог следует разделить **по виду authority**:

| Ответственность | Semantic owner |
|---|---|
| Контракт выходного domain Artifact и его provenance/manifest schema | `stratbox` / соответствующий домен |
| Методический `Result`, доказательства и input/output relations | `stratbox` / соответствующий домен |
| Физическая запись blobs и проверка digests | нейтральный storage capability / storage service |
| Runtime catalog/index, Work/Job links, поиск, visibility, access, favorites, retention decisions | Strategy Box application runtime |
| Node/system paths, storage binding, platform lifecycle и platform evidence | AppDock boundary |
| Отображение списка и инспектора артефактов | Windows/Web/Android client projections |

Один и тот же `artifact_id` может упоминаться во всех проекциях, однако именно **application runtime управляет пользовательской жизнью зафиксированного объекта**, а **domain core отвечает за то, что аналитически было произведено**.

## 10.7. Current Result vs Historical Artifact

**[CONSOLIDATED]** `current` — **отношение к вопросу и времени**, не свойство bytes. Текущий результат по заданному запросу может указывать на `result_id` с самой актуальной обоснованной версией; старые artifacts остаются доступными как исторические материализации старых результатов.

Требуется различать:

- `latest_committed` — последнее успешное сохранение;
- `latest_validated` — последняя прошедшая оговорённую validation;
- `current_for_use` — применимость для конкретного назначения и as-of;
- `superseded` — имеется преемник;
- `historical_at_time` — достоверный слепок состояния знания на прошлую дату.

Нельзя автоматически выбирать «последний файл в output-папке» как current analytical truth.

---

# 11. Оформление, metadata и authoring

## 11.1. ArtifactStyleSet отдельно от UI theme

**[CONSOLIDATED]** Интерфейсная тема (`InterfaceTheme`) относится к surface; внешний вид аналитических файлов (`ArtifactStyleSet`) — к общему artifact/reporting слою в `stratbox`. В current core уже существуют Excel style presets; в escrow часть стилей пока закодирована внутри домена, что указывает на неоднородность.

**[TARGET-HYPOTHESIS]** Один результат должен использовать **один эффективный, валидированный `ResolvedArtifactStyleSet`** для всех его форматных проекций (XLSX/DOCX/PPTX/PDF), где это поддерживается. Набор имеет `style_set_id`, version, digest, semantic roles, compatibility/capabilities. Форматные writers интерпретируют роли, но не выбирают независимо несовместимые цветовые/шрифтовые системы. Внутреннее наследование набора допустимо **до** compile/resolve; во время run действует зафиксированная версия.

## 11.2. Template, style, data и metadata — разные контракты

- `ArtifactStyleSet` — шрифты/палитры/semantic visual roles;
- `ArtifactTemplate` — композиция документа, листов, слайдов, placeholders;
- `ArtifactMetadataContext` — author/creator/title/org, release info, provenance references;
- `Dataset/Result` — собственно аналитическое содержимое;
- `Renderer/Exporter` — создаёт конкретную physical representation.

Авторство отчёта **не является цветовой темой**. Метаданные источника, автора расчёта, исполнителя и издателя могут отличаться; хранить их нужно без подмены одного другим.

## 11.3. Воспроизводимость оформления

**[TARGET-HYPOTHESIS]** Каждый materialized report фиксирует:

```text
style_set_id + version + resolved_digest
renderer_id + version
template_id + version, if used
metadata_policy_id + applied author/creator fields
fonts/assets identity, where material to output
```

Это позволяет понять, почему исходные данные одинаковы, а повторно сформированный файл отличается визуально. Если требуется bit-for-bit reproducibility, дополнительно фиксируются версии writer libraries, locale/timezone и порядок сериализации; **не каждый офисный формат гарантирует byte-identical output при эквивалентном содержимом**.

## 11.4. Кастомизация через нейтральные ресурсы

Пакет расширения может в рамках общего публичного контракта предоставить источники, styles или templates. Сам ресурс остаётся версионированным, валидируемым и может жить дольше процесса extension. Никакие конкретные закрытые реализации для определения публичных контрактов не требуются.

---

# 12. Currentness, cache, retention и переоценка результата

## 12.1. Разделить четыре вопроса о «свежести»

**[CONSOLIDATED]** Для источников, регистров, данных, результатов и артефактов слово *актуальный* обозначает разные отношения. Единое поле `is_fresh: bool` теряет смысловую информацию.

| Объект | Проверяемый вопрос | Допустимый результат |
|---|---|---|
| `SourceDescriptor` | Доступен ли ожидаемый канал публикации и когда проверялся? | reachable / unavailable / unknown |
| `SourceSnapshot` | Появилась ли новая редакция или публикация для того же source/vintage? | unchanged / new / revised / unknown |
| `RegistrySnapshot` | Соответствует ли версия установленной policy и effective date? | current / stale / manual / unknown / not applicable |
| `DatasetVersion` | Сохраняет ли набор данных своё назначение при новых input/version? | valid / impacted / needs revalidation / invalid |
| `Claim` | Сохранились ли основания, сфера применимости и допустимый reliance? | supported / contested / stale / unresolved / withdrawn — **несколько осей одновременно** |
| `Artifact` | Доступен ли файл и соответствует ли фиксированному digest? | available / missing / integrity failure / quarantined |
| `Result` | Какой результат обоснован для конкретного вопроса и as-of? | current for use / historical / superseded / revalidation required |

**[TARGET-HYPOTHESIS]** `FreshnessAssessment` должен быть отдельной оценкой, содержащей `target_ref`, `assessed_at`, `policy_id`, `policy_version`, `evidence_refs`, `state`, `reason_codes`, `next_check_after`, а не перезаписью исходного snapshot или результата. Оценка может изменяться без мутации исторических байтов.

## 12.2. Временная неоднозначность: «данные за июнь»

Один июньский показатель может иметь одновременно:

- `observation_period = 2026-06`;
- `publication_date = 2026-07-...`;
- `retrieved_at = 2026-08-...`;
- `source_vintage = initial`;
- `revised_at = 2026-09-...`;
- `effective_classification_version`;
- `result_computed_at`;
- `knowledge_assessed_at`.

Период показателя и дата доступности информации принципиально различны. При historical backtest доступность на момент принятия решения является ограничением данных: нельзя ретроспективно подставить пересмотренную публикацию и объявить её известной раньше. При обычной текущей аналитике, напротив, может быть уместна последняя редакция. Оба режима должны явно присутствовать в запросе.

## 12.3. Алгоритм impact / revalidation

**[TARGET-HYPOTHESIS]** Новый upstream snapshot или RegistrySnapshot обрабатывается так:

```text
new source/registry revision
  → establish stable identity + content hash
  → compare with previous admitted version
  → decide: no material change / byte change / semantic change / unknown
  → traverse recorded dependency edges
  → filter by used sections/periods/identities, if recorded
  → mark dependent Results/Claims with qualified impact assessment
  → suggest verification or successor execution
  → preserve prior snapshots and outputs
  → publish new current projection only after validation/admission
```

Новый файл ещё не означает, что **все** downstream-данные устарели: иногда меняется только метадата, неиспользуемый период, оформление или безвредное форматирование. И обратное тоже верно: изменение справочника или формулы при тех же байтах меняет семантику результата. Поэтому impact должен учитывать и **content**, и **semantic dependencies**.

## 12.4. Cache и source evidence

**[CONSOLIDATED]** Кэш отвечает за ускорение и может быть восстановлен или удалён; managed artifact и source evidence отвечают за воспроизводимость. Если единственная копия использованных сырых байтов находится в удаляемом кэше, этот кэш фактически выполняет роль *архива доказательств* без соответствующих гарантий.

Следовательно, режимы имеют разные обязательства:

1. **Transient computation.** Разрешён временный response cache; результат явно помечен как невоспроизводимый после очистки.
2. **Reproducible analytical result.** Использованные source contents либо архивируются под content identity, либо имеют доказуемо неизменяемую и доступную ссылку с проверяемым digest; способ восстановления указан.
3. **Regulated/long-lived evidence.** Срок удержания, допустимый storage, backup, проверка целостности и удаление определяются явной policy.

Выбор уровня — продуктовая политика, но скрытая смена роли cache запрещена. Сохранять *все* когда-либо увиденные HTTP responses бессрочно также неоправданно.

### Cache keys

Предпочтительный fingerprint вычисления:

```text
input content digest(s)
+ semantic schema/measure definition version(s)
+ registry snapshot digest(s)
+ operation / algorithm / parser version
+ normalized safe parameter digest
+ relevant policy/selection identities
```

Environment path, file mtime и UI-имя выступают только вспомогательными hints. Даже при совпавшем cache key следует проверять compatibility и воспроизводимый результат, а не полагаться на совпадение имени.

## 12.5. Retention и garbage collection

**[CONSOLIDATED]** Immutable означает «содержимое сохранённого объекта нельзя незаметно изменить», а не «файл невозможно никогда удалить». Требуются отдельные отношения:

- `superseded_by` — более новая версия представления/результата;
- `tombstoned` — логически исключён из обычного использования;
- `quarantined` — небезопасен или не проходит integrity checks;
- `retained_due_to` — есть действующая retention/legal/audit/lineage причина;
- `materialized_at` — физическая копия, которую можно удалить отдельно от логического объекта.

**[TARGET-HYPOTHESIS]** GC выполняется после анализа ссылок и retention locks. Физический blob можно удалить лишь когда нет живых manifest references, резервных копий с отдельным обязательством, активных readers и запрета retention. `Materialization` в пользовательском workspace может жить по другой политике. Удаление UI-карточки не должно молча удалять исходные evidence bytes.

**[UNKNOWN]** Конкретные retention classes, сроки и порядок восстановления historical outputs требуют Product Decision с учётом банковского, локального, общего и удалённого режимов.

---

# 13. Ownership и интерфейсы между слоями

## 13.1. Матрица разделения ответственности

| Data/Knowledge concern | Domain `stratbox` | Strategy Box application runtime | AppDock / environment | Windows/Web/Android |
|---|---|---|---|---|
| Source/registry semantic definition | **owner** | каталог доступности как projection | installation/network capability | выбор и визуализация |
| Fetch/parse/normalize/calculation | **owner** | вызов, scheduling и execution identity | transport/environment | ввод параметров |
| Domain `Observation`, `DatasetVersion`, evidence/claim | **owner** | ссылки, access policy, discoverability | — | чтение и объяснение |
| Source/registry version provenance | **owner** контракта | фиксация зависимостей в Work/Job | supply/install provenance | визуальная карточка |
| Low-level `FileStore` и format contracts | **owner** интерфейса | потребитель | physical capability реализации и binding | explorer UI |
| Immutable payload/manifest | определяет семантику и вид результата | lifecycle/index; может оркестрировать commit | storage placement и platform health | materialize/open |
| Artifact catalog/search | обеспечивает domain metadata | **owner общей product projection** | — | consumer |
| Work/Job/Run/actor linkage | сообщает domain record, если доступно | **owner durable work/execution truth** | session/node identity | client projection |
| User file operations | format/library utilities | access and workflow policy | выбранная рабочая среда | действия пользователя |
| Retention/visibility/authorization | classification metadata | **owner правил доступа и retention** | platform access constraints | permission-aware UI |
| UI Theme | — | shared preferences, если нужны | — | **owner rendering** |
| ArtifactStyleSet | **owner** нейтральной семантики | эффективный выбор на запуск | установка resource | selection UI |
| Operational recovery | source/read/compute diagnostics | Work state recovery | node/platform recovery | показ состояния |

Это матрица *семантических владельцев*. Один Python-процесс может содержать несколько ролей, а одна роль может позднее потребовать отдельный сервис. Из этой матрицы не следует создавать новый репозиторий на каждую строку.

## 13.2. Где проходит граница AppDock

По базовой модели AppDock узел управляет установкой, data binding, запуском, состоянием среды, результатами на уровне продукта, диагностикой и восстановлением. Для Strategy Box это означает:

```text
AppDock provides:
  node identity / session / activation / data binding /
  platform service lifecycle / operational diagnostics /
  remote access boundary / storage capability

Strategy Box owns:
  meaning of SourceSnapshot / Observation / Result /
  artifact lineage / analyst permissions and currentness /
  work-specific storage and catalog semantics
```

AppDock вправе знать, что зарегистрирован `artifact_ref` и есть локальная или remote materialization. Ему **не нужно** знать, например, почему отраслевой показатель восстановлен методом интервалов, какой реестр кодов выбран для банковского показателя и допустим ли экономический вывод. Это ответственность domain core.

## 13.3. Portable references

**[TARGET-HYPOTHESIS]** Межпроцессные границы должны передавать типизированные ссылки: `source_snapshot_ref`, `dataset_version_ref`, `result_ref`, `artifact_ref`, `registry_snapshot_ref`. Сама ссылка:

- opaque/stable и версионируемая;
- разрешается через authorization-aware service;
- не содержит OS file path как первичной identity;
- может иметь semantic kind и hash;
- допускает `unavailable`, `unauthorized`, `stale reference`, `integrity failure`.

Absolute path подходит внутри локального storage adapter, но не должен становиться обязательным ключом Web/Android API или вычислительным доказательством.

## 13.4. Сервис — не новое предметное ядро

В будущей headless/runtime поверхности может появиться общий каталог и API. Этот сервис не должен реализовывать второй parser форм 0409802, собственные банковские формулы или альтернативный SORS. Он принимает доменные результаты и provenance у `stratbox`, присваивает/связывает application identity, управляет доступом и жизненным циклом результатов. Библиотечный Python/Jupyter consumer продолжает использовать `stratbox` напрямую без обязательного запуска Strategy Box host.

---

# 14. End-to-end разбор на реальных классах задач

Приведённые ниже схемы — **целевые трассы на основании существующих доменных алгоритмов**, а не утверждение, что описанные manifests/IDs уже записываются текущим кодом.

## 14.1. Форма 0409802: из официальной DBF в показатель и Excel

**[CURRENT]** В `cbr_forms` существуют physical parser/semantic CSV model/canonical long и export; форма 802 служит наиболее развитым примером. Система уже сохраняет различие пустого значения и нуля и учитывает изменение схемы публикаций во времени.

**[TARGET-HYPOTHESIS]** Полная трасса:

```text
SourceDescriptor: cbr.form.0409802
  └─ requested reporting period 2026-Q2
       └─ SourceSnapshot: exact official ZIP/DBF bytes, fetched_at, sha256
            └─ Format identification: ZIP → DBF
                 └─ Physical rows with source row/field location
                      └─ Semantic model 802/version, indicator_id
                           └─ Canonical observations
                                └─ DatasetVersion: 802/period/build/version
                                     └─ Validation report + warnings
                                          └─ AnalyticalResult
                                               └─ XLSX view under one style set
                                                    └─ ArtifactManifest
                                                         └─ runtime catalog / case link
```

**Acceptance trace** для одной ячейки: `artifact → result_id → dataset_version → indicator_id + bank REGN + period + measure → semantic model version + source field/row → source snapshot digest`. Если ячейка формульная, дополнительно хранится expression identity и dependency list. Это обеспечивает объяснение без обещания, что каждая вычисленная ячейка обязательно хранится отдельной строкой БД.

**Критерий корректности:** вариант source schema меняется, но смысловой indicator остаётся прежним только при явном подтверждении семантической эквивалентности. Если значение отсутствует, вместо нуля записывается `missing` с причиной или unknown, если причина неизвестна.

## 14.2. Escrow: revised monthly publication

**[CURRENT]** Домен escrow умеет discover → download/cache → parse исторические layouts → canonical history → views → XLSX/ZIP, имеет typed requests/results и допускает частичное получение источников.

**[TARGET-HYPOTHESIS]** Сценарий:

1. Июльский файл впервые получен: создаётся `SourceSnapshot A`, затем `DatasetVersion D1`, `Result R1`, `Artifact X1`.
2. Через месяц внешний publisher обновляет *тот же URL* и возможно *то же имя файла*; SHA-256 меняется: создаётся `SourceSnapshot B` с relation `revises A` или `new_version_of A`, если это установлено.
3. Перезапуск сохраняет `D1/R1/X1`; строит `D2/R2/X2` и объясняет разницу (`revised rows`, `changed indicators`, `unchanged`).
4. `current_for_use` может переключиться на `R2` только после validation. Факт существования `X2` не отменяет историческое `X1`.
5. При сбое загрузки одного периода `partial` не маскируется как полная история; в dataset manifest отражаются missing periods и failure references.

**Критерий корректности:** два файла с одинаковым basename, но разным содержимым дают разные evidence identities и две воспроизводимые версии результата.

## 14.3. SORS restoration: published integer и предел вывода

**[CURRENT]** Подсистема восстановления SORS различает латентные величины, интервалы официального округления, ограничения между областями, strong/source-preserving evidence и слабые варианты выбора. У неё есть богатые diagnostics и фактовые реестры. Это более строгая доказательная модель, чем в обычном collector.

**[TARGET-HYPOTHESIS]** Для вывода об отдельной восстановленной ячейке трасса должна показывать:

```text
source publication snapshot(s)
  → source interval / publication bucket
  → semantic measurement and classification version
  → constraint graph + mapping version
  → inference run / solver configuration
  → evidence method and assumption tier
  → bounds / selected published bucket / unresolved alternatives
  → supported Claim with validity scope
  → Result with supporting ledger references
  → generated workbook / diagnostic artifacts
```

Наличие рассчитанной точки не означает, что значение доказано с одинаковой силой для всех методов. Если допустим интервал нескольких публикационных buckets, честным результатом остаётся интервал и причина неопределённости. Слабый selection не превращается в официальное значение в отчёте или при дальнейшей передаче AI.

**Критерий корректности:** при воспроизведении результата сохранены не только число и XLSX, но и доказательный статус, допустимые bounds, версии source/classifier/mapping, версия алгоритма и limitations.

## 14.4. Cross-source comparison: банка по РСБУ и группы по МСФО

**[TARGET-HYPOTHESIS]** Ещё один тест эпистемической полноты: пользователь просит сравнить темпы банковского портфеля, но одна публикация относится к отдельному юридическому лицу по РСБУ, другая к консолидированной группе по МСФО, а единицы отличаются. У системы есть только два честных пути:

- создать явно документированный bridge/normalization с ограничениями и вывести `conditionally comparable`;
- отказать в прямой сопоставимости и вернуть `comparability_unknown` / `incompatible`, сохранив оба наблюдения.

Совпадающие заголовки показателей и единая таблица XLSX не дают права автоматически трактовать данные как экономически эквивалентные.

---

# 15. Conflict / superseded register

Следующий реестр отделяет **действительное расхождение** от вариации уровня абстракции.

| ID | Различающиеся положения | Классификация | Консолидированное разрешение / дальнейший статус |
|---|---|---|---|
| CF-01 | Artifact Catalog «целиком в `stratbox`» против «каталог у host/runtime» | **CONFLICT resolved** | `stratbox` — semantic contract/provenance; application runtime — Work/user catalog/visibility/retention; bytes — storage capability |
| CF-02 | «Сразу внедрить CAS» против «не строить преждевременные подсистемы» | **TARGET-HYPOTHESIS / UNKNOWN** | Сначала invariant immutable manifest+digest; CAS физически после workload-пилота |
| CF-03 | SourceSnapshot иногда называется raw Artifact | **Apparent conflict** | `SourceSnapshot` — source/retrieval semantics; raw Artifact — immutable bytes; linkage через ref |
| CF-04 | Registry как один общий модуль vs source registries и domain rules | **Terminology conflict resolved** | reference registry, source catalog, domain rule registry, capability registry имеют разные semantic owners |
| CF-05 | Справочник «самый новый по mtime» vs version manifest | **SUPERSEDED recommendation** | mtime — технический hint; semantic identity выбирается по snapshot manifest и policy |
| CF-06 | Готовый XLSX/path — результат всей аналитики | **SUPERSEDED** | domain Result и DatasetVersion существуют до view/export; artifact — его representation |
| CF-07 | Достаточно «успешно скачал» как доказательства корректности | **SUPERSEDED** | отдельно transport success, integrity, format/schema validation, semantic validity, claim support |
| CF-08 | У источника одна дата публикации и один `latest` | **SUPERSEDED** | отделить observation time, publication time, availability time, retrieval time, revised vintage |
| CF-09 | Одно boolean `ok`/`confidence` покрывает состояние данных и выводов | **SUPERSEDED** | раздельные ошибки, quality, epistemic support, currentness, availability и reliance |
| CF-10 | Поддержка PDF/XBRL/ZIP определяется расширением файла | **SUPERSEDED** | separate physical/container/semantic format identities, capability levels и inspection |
| CF-11 | Каждая версия registry должна входить в wheel | **TARGET-HYPOTHESIS** | current packaged snapshot плюс Git-controlled history допустимы, пока runtime historical replay не обязателен; raw dependencies обязаны идентифицироваться |
| CF-12 | Выбор шаблона/цветов — часть самой domain metric | **SUPERSEDED** | content/Result, ArtifactStyleSet, template и authoring metadata — независимые смысловые контракты |
| CF-13 | Можно безусловно считать `canonical` фактом/доказательством | **CONFLICT resolved** | canonical — локально утверждённое представление при указанной семантике; claim требует оснований |
| CF-14 | Универсальный ClaimStore нужен каждому банковскому pipeline | **UNKNOWN** | нужен общий квалифицированный смысл; storage/schema только при доказанной нагрузке и нескольких consumers |
| CF-15 | Source Catalog должен быть единым реестром «URL-ов всех доменов» | **SUPERSEDED** | общий descriptor/governance, но доменные discovery/parameterized sources живут у source-specific owners |
| CF-16 | Runtime host должен перерасчитывать business data, чтобы строить lineage | **CONFLICT resolved** | `stratbox` возвращает domain provenance; application runtime индексирует связи, а не дублирует вычисление |

## 15.1. Исторические идеи: что сохраняется, что отступило

`01-old-notes` остаётся полезен как история пользовательских ожиданий, каталог предложений и ранних намерений по обработке данных/файлов. Из них сохраняется потребность в удобном доступе к данным и экспорте. **[SUPERSEDED]** Ранние предложения помещать весь пользовательский UI или файловую организацию непосредственно внутрь core не определяют сегодняшнюю границу: `stratbox` — самостоятельная библиотека, surface/application — отдельный уровень. Новая архитектура не обязана сохранять устаревшие имена методов или старые физические пути ради совместимости.

---

# 16. UNKNOWN и локальные белые пятна: реестр с методом разрешения

Система с высокой детализацией не должна подменять незнание именем нового класса. Ниже — вопросы, которые остаются открытыми **после** чтения тематического корпуса и выборочной сверки реализации.

| ID | Вопрос / недостающий факт | Почему существенно | Что должно разрешить | Semantic owner | Приоритет |
|---|---|---|---|---|---|
| U03-01 | Какова минимальная `SourceSnapshot` schema для всех доменов? | без неё обычный collector не даёт одинаковый provenance | пилот collector + escrow + forms, contract tests | `stratbox` | P0 |
| U03-02 | Для каких задач обязательна physical raw preservation? | reproducibility vs стоимость storage | продуктовая матрица операций и сроков хранения | domain + application policy | P0 |
| U03-03 | Где проходит atomicity между blob/manifest и catalog transaction? | crash может дать orphan/полуобъект | fault-injection с durable catalog | application/storage | P0 |
| U03-04 | Что является минимальным `DatasetVersion` identity? | одинаковый DataFrame может иметь разный смысл | междоменный pilot с semantic schema + source set | `stratbox` | P0 |
| U03-05 | Когда считать данные reported, derived, reconstructed или estimated? | epistemic status влияет на выводы | ontology fixture для forms/escrow/SORS | domain | P0 |
| U03-06 | Какие статусы missingness стандартны, а какие доменно-специфичны? | blank/zero/secret data нельзя смешивать | sample datasets, roundtrip tests, schema contracts | domain + common | P0 |
| U03-07 | Достаточно ли run-level provenance, когда требуется cell-level? | granular lineage может быть очень дорог | cost/performance pilot на forms/escrow/SORS | domain + provenance | P1 |
| U03-08 | Нужен ли отдельный ClaimStore или достаточно typed claims в Results? | риск преждевременной knowledge platform | две реальные cross-work задачи reuse/revalidation | domain + application | P1 |
| U03-09 | Каково минимальное содержимое `EvidenceRef`? | слишком слабый ref — ссылка на файл вместо основания | traceability acceptance по 3 доменам | domain | P0 |
| U03-10 | Как версионировать Measure/Construct и semantic bridges? | банковские perimeters/единицы меняются | форма + отрасль + IFRS/RAS comparison | domain/registries | P1 |
| U03-11 | Общий geography registry: что считается entity, что publication node? | иначе неверная агрегация субъектов | joint test industries/SORS/escrow с историей | `stratbox.registries` | P0 |
| U03-12 | Как publication vintage соотнести с effective date registry? | backtests/пересмотры | period/vintage fixture + regression | `stratbox` | P1 |
| U03-13 | Сколько исторических snapshots хранить в wheel/runtime? | immutable input не всегда доступен | offline replay requirement и storage budget | registries + product | P1 |
| U03-14 | CAS нужен немедленно или достаточно immutable manifests+payloads? | цена внедрения/GC | локальный и remote workload pilot, сравнение затрат | application/storage | P1 |
| U03-15 | Какой durable Artifact Catalog backend и search topology? | node-local vs shared-host работа | транзакционный pilot; профиль нагрузок | application runtime | P1; решать в теме 05 |
| U03-16 | Кто принимает и хранит legal hold/retention policy? | стирание evidence при cleanup | owner model, permission matrix, retention tests | application + organization policy | P1 |
| U03-17 | Как имплементировать currentness для нескольких use contexts? | один `latest` не отражает применимость | qualification model + impact cases | domain + application | P1 |
| U03-18 | Как не раскрывать sensitive path/URL/author metadata в provenance? | полезный lineage может стать каналом утечки | threat modeling, redaction rules, authorization | application/security | P0 |
| U03-19 | Какие форматы необходимо certified-read/serialize в первом релизе? | workload и зависимости неодинаковы | sample inventory+fixtures+CI matrix | core format owner | P1 |
| U03-20 | Как переносить directory/bundle artifacts без потери part integrity? | ZIP и directory имеют разные semantics | manifest/part-level copy tests | storage/artifact | P1 |
| U03-21 | Как безопасно выполнять cancel во время data staging/commit? | полуартефакт и ошибочная durable ссылка | failpoint tests с cancellation | operation runtime/storage | P0; тема 04/08 |
| U03-22 | Как будут устроены backup/restore и DB reconstruction? | manifests могут сохраниться без индекса | restore drill на отдельном узле | application/AppDock boundary | P1; тема 05/08 |
| U03-23 | Как измерять реальное resource budget крупного SORS/dataset? | streaming, spill-to-disk, recomputation | benchmark peak RSS/IO/disk/cache hit | domain/execution | P1 |
| U03-24 | Какие действия по revalidation разрешены AI/automation? | знание об устаревании ≠ разрешение на пересчёт/публикацию | capability/effect policy + approval tests | application runtime | P2; тема 06 |
| U03-25 | Есть ли достоверная ассоциация `author` и реального producer? | auth/metadata/provenance конфликт | identity mapping, provenance signoff | application + AppDock identity | P1 |
| U03-26 | Как экспортировать результат и сохранить доказательства при переносе вне Strategy Box? | XLSX может оторваться от manifest | portable sidecar/embed strategy; roundtrip | reporting/artifact owner | P1 |
| U03-27 | Как хранить contradictions между независимыми публикациями? | один canonical value не должен стирать конфликт | overlapping-vintage и source dispute fixtures | domain/knowledge | P1 |
| U03-28 | Как отличить real-world event от ревизии старой публикации? | impacts/trends искажаются | source release model + semantic diff | source/domain | P1 |

**Не следует** закрывать эти пункты разработкой большого универсального «DataManager». Они требуют отдельных и небольших проверок с реальными файлами и явно измеримым результатом.

---

# 17. Candidate target contracts: минимальные переносимые формы

Предлагаемые структуры — **иллюстративные schema sketches**, а не утверждение об уже существующих Python-классах. Поля отражают семантическую необходимость; физическая реализация может быть dataclass, JSON Schema, таблицей БД или API message.

## 17.1. Source и reference snapshots

```text
SourceDescriptor {
  source_id, authority_id, source_family,
  discovery_kind, expected_cadence,
  semantic_kind?, expected_format_family?, validator_id?,
  descriptor_version
}

SourceSnapshot {
  snapshot_id, source_id, source_descriptor_version,
  publication_period?, publication_time?, retrieval_time,
  requested_locator, final_locator?,
  response_metadata?, content_digest, size,
  physical_format_id?, semantic_source_schema_id?,
  raw_artifact_ref?, validation_report_ref?,
  retrieval_status, revision_relation?
}

RegistrySnapshot {
  registry_id, snapshot_id, authority?, upstream_version?,
  semantic_schema_version, transform_version,
  effective_from?, effective_to?, obtained_at?,
  content_parts[{digest, size, role}], validation_status,
  manifest_digest
}
```

**Требование:** `SourceSnapshot` может фиксировать `failure` без `raw_artifact_ref`, но тогда это **attempt/failed retrieval record**, а не притворно успешный снимок байтов. Операционная запись о попытке может быть отдельной сущностью; границу следует решить на U03-01 и U03-21. Здесь для компактности показана связь.

## 17.2. Observation и DatasetVersion

```text
Observation {
  observation_id?,
  subject_ref, measure_definition_ref, value | missing,
  unit, perimeter?, period, temporal_role,
  source_snapshot_ref | derivation_ref,
  classification_refs[], vintage?,
  value_kind: reported | derived | reconstructed | estimated | modeled,
  quality_flags[], source_locator?
}

DatasetVersion {
  dataset_id, version_id,
  semantic_schema_ref, observation_scope,
  source_snapshot_refs[], registry_snapshot_refs[],
  transform_refs[], validation_report_refs[],
  content_ref?, content_digest?,
  as_of?, admitted_at?, quality_state,
  provenance_manifest_ref
}
```

`observation_id` может быть производным стабильным ключом составной семантики или локальным ID; не нужно требовать глобальную UUID для каждой ячейки, пока это не оправдано стоимостью. `DatasetVersion` должен сохранять **ссылку на структуру, которая задаёт смысл полей**, иначе Parquet/CSV с тем же layout может выдавать семантически разные результаты.

## 17.3. Evidence, Claim и AnalyticalResult

```text
EvidenceRef {
  evidence_id, evidence_kind,
  basis_refs[], method_ref?,
  asserted_scope?, limitations[],
  source_locator?, produced_by_run_ref?
}

QualifiedClaim {
  claim_id, claim_kind, proposition_or_expression,
  subject_scope, time_scope,
  premises[], evidence_refs[], assumptions[],
  support_state, uncertainty_description?,
  contestation_refs[], currentness_assessment_ref?,
  permitted_reliance?, known_limitations[]
}

AnalyticalResult {
  result_id, operation_ref,
  domain_output_refs[], claim_refs[], evidence_refs[],
  validation_reports[], warnings[], failures[],
  source_snapshot_refs[], registry_snapshot_refs[],
  data_quality_state, epistemic_state,
  produced_by_execution_ref?,
  artifact_intents[]
}
```

`EvidenceRef` указывает на основу/метод и границы применения, а не содержит только цитату. `Claim` не обязан появляться для каждого raw upload: он нужен при формировании содержательного аналитического утверждения. В production-версии `epistemic_state` может стать несколькими квалификационными осями вместо одного enum.

## 17.4. Artifact и lineage

```text
ArtifactManifest {
  artifact_id, schema_version,
  artifact_kind, created_at, content_parts[],
  result_ref?, dataset_version_refs[],
  produced_by_run_ref?,
  provenance_manifest_ref,
  style_set_ref?, template_ref?, renderer_ref?,
  authoring_metadata_ref?, manifest_digest
}

ContentPart {
  part_id, role, media_type?, size_bytes, sha256,
  logical_filename?, object_locator?  // access-controlled
}

LineageEdge {
  from_ref, relation_kind, to_ref,
  scope_ref?, method_ref?, recorded_at
}
```

Связи следует делать *типизированными* (`wasDerivedFrom`, `usedSnapshot`, `usedRegistry`, `generatedBy`, `supports`, `revises`, `representedBy`) с валидируемыми domain/range. Само имя конкретного стандарта provenance не является обязательной программной зависимостью.

## 17.5. Минимальный runtime API

```text
resolve_artifact(ArtifactRef, actor_context) -> Availability/AuthorizedLocation
inspect_artifact(ArtifactRef) -> Manifest + policy-aware lineage
list_artifacts(filters, actor_context) -> CatalogPage
materialize_artifact(ArtifactRef, target, policy) -> MaterializationResult
get_result(ResultRef) -> domain-qualified summary
get_source_snapshot(SourceSnapshotRef) -> safe metadata/read permission
assess_currentness(TargetRef, UseContext) -> qualified assessment
trace_lineage(TargetRef, depth/scope/policy) -> authorized lineage graph
```

Для headless `stratbox` потребителя эти сервисы могут быть легковесными локальными объектами; для shared-node используются те же semantics через service/API. User-facing UI получает проекции, а не authority над результатом.

---

# 18. Проверяемые инварианты и критерии приёмки

Это исследовательские **candidate invariants** для будущих Product/Engineering решений; запуск тестов в данном проходе не выполнялся.

| ID | System invariant | Отрицательная проверка / fault case |
|---|---|---|
| INV-DK-01 | `SourceDescriptor` и `SourceSnapshot` имеют разные идентичности | тот же URL возвращает другой payload; original snapshot остаётся различимым |
| INV-DK-02 | Использованный raw input можно идентифицировать по digest | переименовать файл, переместить в другое хранилище, повторить hash check |
| INV-DK-03 | `RegistrySnapshot` выбирается явно, а не по mtime | изменить timestamps файлов — semantic registry version остаётся прежней |
| INV-DK-04 | Canonical datum сохраняет measure/unit/perimeter/period/vintage | два одинаковых числа с разным perimeter не объединяются silently |
| INV-DK-05 | Missing ≠ 0, Unknown ≠ False | пустая ячейка официальной формы и 0 roundtrip без потери различия |
| INV-DK-06 | Validation success не повышает claim support выше evidence | parser успешно выполнился, но population/definition конфликтуют |
| INV-DK-07 | `DatasetVersion` связывается с точным набором source/registry refs | обновить только один upstream, проверить изменение dependency fingerprint |
| INV-DK-08 | Результат и артефакт имеют разные identity | один Result экспортирован в XLSX и CSV — один смысл, два artifacts |
| INV-DK-09 | После `commit` содержимое artifact immutable | попытка overwrite создаёт новую версию/ошибку, не изменяя старый digest |
| INV-DK-10 | Невыполненный commit не публикует валидный artifact | crash между blob upload и catalog commit, visible artifact отсутствует |
| INV-DK-11 | Физический путь не является durable identity | новый workspace root/remote materialization сохраняет artifact ref |
| INV-DK-12 | Work/runtime index не заменяет domain evidence | удалить UI projection, восстановить claim provenance из domain records |
| INV-DK-13 | Source/registry revision не уничтожает historical results | два vintages остаются доступны с их as-of |
| INV-DK-14 | Нет silent evidence promotion | SORS weak selection не маркируется как strong official |
| INV-DK-15 | Partial failure не становится полностью успешным dataset | один исходный период недоступен, результат содержит explicit gap |
| INV-DK-16 | Cache deletion не уничтожает promised reproducibility | очистить cache и воспроизвести Result по retained artifacts либо получить explicit limitation |
| INV-DK-17 | Sensitive provenance фильтруется по access policy | пользователь без прав получает safe summary без приватных storage locators |
| INV-DK-18 | Identity автора и генератора различается | scheduled run и пользователь, одобривший результат, не сливаются в одного actor |
| INV-DK-19 | Shared catalog согласован при конкурентных commit | два worker публикуют раздельные artifacts без partial index record |
| INV-DK-20 | Смена style set не меняет value/claim truth | два XLSX оформлены по-разному, canonical dataset digest одинаков |
| INV-DK-21 | Внешний формат не является сам по себе semantic source | XLSX с HTML/error payload отвергается до semantic parser |
| INV-DK-22 | Impact assessment имеет scope и основание | изменился неиспользуемый source period — related result не становится stale автоматически |

## 18.1. Метрики проверки качества

Для оценки пилота стоит собирать: долю outputs с полным provenance, долю source snapshots с content digest, replay success rate, time-to-trace одной ячейки до публикации, число false successful downloads, peak RAM при streaming, размер staging/orphan накопления после crash, число unsigned/unknown schema migrations, artifact catalog query latency и долю impacted Results после точечного source revision. **Числовые пороги заранее не утверждены**: их следует выбрать по замерам на реальной рабочей станции/узле и фактическим размерам банковских файлов.

## 18.2. Что не является критерием доказанности

Красивый Inspector, наличие SHA-256 у итогового XLSX, зелёный статус операции, наличие 100% строк в CSV и валидная JSON Schema **не подтверждают** корректность экономического вывода. Они подтверждают разные технические свойства. Evidence и applicability проверяются отдельно.

---

# 19. Приоритетный план исследования и реализации: вертикальные срезы

**[TARGET-HYPOTHESIS]** Измеряемый путь лучше полной предварительной перестройки.

## Slice A — Source and registry provenance (P0)

Домен-пилот: `cbr_file_collector` плюс один `escrow`/формный источник. Результат:

1. общий read-only `SourceDescriptor` и `SourceSnapshot` minimal contract;
2. digest, retrieval timestamps, final URL, format detection и validation result;
3. manifest с source ID и revision relation;
4. deterministic offline fixtures при одинаковом URL и меняющихся bytes;
5. removal of implicit registry mtime selection в одном конкретном справочнике, explicit RegistrySnapshot manifest;
6. проверка отсутствия секретов и окружающей конкретики в публичной документации.

**Критерий выхода:** конкретный файл можно переименовать и переместить, а parser/Result всё равно связан с той же immutable source identity. Повторная загрузка изменённой версии источника не затирает прежнюю.

## Slice B — Canonical DatasetVersion + analytical provenance (P0/P1)

Домен-пилот: форма 802 и escrow; SORS как stress test. Результат:

1. `DatasetVersion` с semantic schema и source/registry links;
2. явная temporal/vintage/missingness semantics;
3. валидируемые transform/version relations;
4. простой `AnalyticalResult` с run provenance и optional EvidenceRef;
5. trace одного показателя от domain result до official raw bytes.

**Критерий выхода:** после обновления источника пользователь видит две версии, причины расхождения и использованные определения. Базовые домены умеют выдавать provenance без обязательного GUI.

## Slice C — Transactional artifact publication (P1)

Домен-пилот: XLSX/CSV Result и bundle/ZIP. Результат:

1. стабильный ArtifactRef и immutable manifest;
2. staging, content digest, commit visibility barrier и abort;
3. небольшой runtime catalog с links к result/execution/author;
4. explicit `materialize` в mutable workspace;
5. simulated crash/cancel during write;
6. deployment decision CAS vs ordinary immutable content layout на реальных замерах.

**Критерий выхода:** ни один клиент не видит committed artifact с недописанным содержимым, а после переноса или смены physical path artifact остаётся разрешимым.

## Slice D — Freshness, impact и Knowledge qualification (P1)

Домен-пилот: revised escrow publication; registry change; SORS evidence. Результат:

1. `currentness assessment` отдельно от snapshots;
2. dependency traversal;
3. targeted revalidation с сохранением historical Result;
4. квалифицированные Claims только для операций, создающих содержательные утверждения;
5. UI-safe lineage projection и explanation of uncertainty;
6. storage/retention и access policy решения, необходимые для многоузлового режима.

**Критерий выхода:** появление новой версии upstream сопровождается объяснимым перечнем *возможно затронутых* результатов, а не переписыванием истории и не глобальной волной обязательных перерасчётов.

## 19.1. Почему такой порядок

Сначала формируются **source/registry identity**, затем semantic dataset/result, и лишь после них сложные ускорения и хранилища. Иначе CAS эффективно сохранит большой объём байтов, связь которых с экономическими определениями останется неизвестной. Аналогично, полноценная user-facing currentness без lineage будет вынуждена гадать по датам и названиям файлов.

## 19.2. Что сознательно не требуется в первом цикле

Не нужны немедленно: универсальный knowledge graph server, система отдельного persistence класса для каждой ячейки, полномасштабный event sourcing, обязательный распределённый CAS, единый «суперформат» всех доменов, выделение нового репозитория ради каждого protocol и полная поддержка XBRL/SDMX без real consumer. Эти направления можно материализовать позже при наличии измеримой потребности.

---

# 20. Decision / Gap Register темы 03

| Решение или вопрос | Итоговый статус | Основание / следующий владелец |
|---|---|---|
| `FileStore` — format-neutral transport | **CONSOLIDATED** | код core + format research; `stratbox` |
| `SourceDescriptor` / `SourceSnapshot` separate | **CONSOLIDATED semantic** | source research + program; schema pilot — `stratbox` |
| `RegistrySnapshot` identity/version manifest | **CONSOLIDATED direction** | loader mtime defect + governance research; `stratbox` |
| Physical/semantic format separation | **CONSOLIDATED** | format research + direct-form parser; `stratbox` |
| Canonical `Observation` includes period/unit/perimeter/vintage when material | **CONSOLIDATED** | forms/SORS + semantic research; `stratbox` |
| Universal `DatasetVersion` contract | **TARGET-HYPOTHESIS, strong** | requires two-domain pilot |
| Domain-specific evidence remains richer than generic provenance | **CONSOLIDATED** | SORS / cross-domain comparisons |
| One general ClaimStore for all operations | **UNKNOWN** | avoid until consumers demonstrated |
| Same source content may support different claims, with qualification | **CONSOLIDATED** | epistemic reasoning |
| Artifact separate from `Result` and physical path | **CONSOLIDATED** | file research + System Model 01 |
| Artifact domain manifest semantics owner | **CONSOLIDATED** | `stratbox` |
| Artifact runtime catalogue/visibility owner | **CONSOLIDATED** | application runtime (System Model 01) |
| Immutable commit barrier and no partial success | **CONSOLIDATED invariant** | artifact/security research |
| Physical CAS layout as mandatory first step | **UNKNOWN / TARGET-HYPOTHESIS** | actual workload pilot |
| Local SQLite catalog | **TARGET-HYPOTHESIS** | local transactional pilot; scope limited |
| Network/client-server catalog | **TARGET-HYPOTHESIS** | shared-node requirements; topic 05 |
| One effective cross-format ArtifactStyleSet | **TARGET-HYPOTHESIS, strong** | style research + renderer test |
| `InterfaceTheme` separate from ArtifactStyleSet | **CONSOLIDATED** | style/settings/surface boundary |
| Authoring metadata separate from visual style | **CONSOLIDATED** | style research |
| Freshness/currentness as qualified assessments | **CONSOLIDATED semantic** | governance/evidence + topic 00 |
| Retention duration, legal hold, backup | **UNKNOWN** | Product/security + topics 05/08 |
| Revalidation/impact graph | **TARGET-HYPOTHESIS** | dependency pilot; next Work in topic 04 |
| AppDock ownership of banking/macro data meaning | **REJECTED/SUPERSEDED** | separate domain and platform boundaries |
| Private extension details inside public research/docs | **PROHIBITED** | generic public contracts only |

Этот реестр фиксирует **исследовательскую решённость**, а не авторизацию на изменение репозиториев. Переход к Product Decision и stable contracts требует отдельного утверждения.

---

# 21. Пределы исследования и требования к дальнейшей проверке

1. **Baseline.** Для реализации взяты проверенные срезы 2026-10-06 и выборочная проверка исходников `stratbox` на `main` 2026-10-08. Текущая ветка исследований могла добавлять документы без изменения производственного кода; не следует считать дату документа датой внедрения функции.
2. **Тесты.** Новый end-to-end, benchmark, fault injection и test suite в рамках этого файла не запускались. Все приведённые acceptance cases — предложенные проверки, а не отчёт об успешном прохождении.
3. **Пилотный объём.** Единого реального artifact catalog, SourceSnapshot API и DatasetVersion API не установлено текущим baseline. Code sketches остаются целевой гипотезой.
4. **Экономическая доказательность.** SORS показывает высокий стандарт доказательности для своей задачи; нельзя автоматически переносить его конкретную методику на все банковские серии. Другим доменам обычно достаточно более лёгких, но честных схем.
5. **Storage topology.** Конкретный способ хранения large blobs, локальный или удалённый catalog, retention и CAS требуют измерений и требований доступа; в отсутствие этих данных точный выбор является UNKNOWN.
6. **Публичная граница.** Файл сознательно содержит только публично нейтральные контракты providers/форматов/storage. Детали закрытых расширений не раскрываются и не становятся dependency публичной архитектуры.
7. **Методологическая граница.** Взяты только общие правила эпистемической аккуратности. Структура внешних методологических проектов и входящих в них репозиториев здесь не описывается.

---

# 22. Source ledger и provenance исследования

Все внутрипроектные ссылки ниже ведут на материал репозитория `ForestTiger-GH/stratbox` на ветке `main`, если не указано иное. Это **источники исследовательских тезисов**, а не утверждение, что все тезисы уже реализованы. Для последующей строгой фиксации рекомендуется заменить branch ссылки commit-pinned URLs при admission в maintained Knowledge.

## 22.1. Program / synthesis controls

- [Программа консолидирующей ветки и точное определение темы 03](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/strategy_box_03_consolidation_research_program.md) — scope, исследовательская процедура, открытые вопросы.
- [README `03-consolidation-research`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/README.md) — статус результата и граница Product Decision.
- [Тема 00 — Corpus Map & Open Questions](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_00_corpus_map_open_questions_2026-10-08.md) — периметр корпуса, ложные конфликты, CAS/registry/knowledge gaps.
- [Тема 01 — System Model](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_01_System_Model_consolidated_research_2026-10-08.md) — ownership Artifact Catalog, domain/application/AppDock boundaries.

## 22.2. Primary `02-base-study` research

- [`stratbox_base_study_current_state_2026-10-06.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_base_study_current_state_2026-10-06.md) — CURRENT core, доменные pipelines, SORS, sources, registries, тесты.
- [`stratbox-windows_current_state_full_research_2026-10-06.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md) — CURRENT artifact/Workspace/user history representations.
- [`stratbox_file_artifact_layer_research_2026-10-06.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md) — principal storage/artifact/CAS/manifest/lineage hypotheses.
- [`stratbox_registry_source_governance_research_2026-10-07.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_registry_source_governance_research_2026-10-07.md) — source and registry identity, version, governance, geography, freshness.
- [`stratbox_filestore_file_formats_research_2026-10-07.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md) — format semantics, codecs, Materialization, security, read/write scope.
- [`stratbox_business_segments_portability_reuse_architecture_research_2026-10-07.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_segments_portability_reuse_architecture_research_2026-10-07.md) — domain operation portability, source fidelity, reuse without UI.
- [`strategy_box_customization_artifact_style_sets_research_2026-10-07.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md) — cross-format ArtifactStyleSet, metadata, templates, reproducible visuals.
- [`Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md) — qualified observation/claim/evidence, currentness, reliance; используются общие смысловые выводы.

## 22.3. Secondary cross-theme research

- [`stratbox_observability_errors_logs_research_2026-10-07.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_observability_errors_logs_research_2026-10-07.md) — distinction domain failure, execution state и platform evidence.
- [`stratbox_single_node_multiuser_research_2026-10-07.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md) — shared-node authority, client projections, artifact permission scope.
- [`stratbox_web_self_hosted_architecture_research_2026-10-07.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md) — host/local/remote data boundaries.
- [`strategy_box_system_settings_research_2026-10-07.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_system_settings_research_2026-10-07.md) — settings vs runtime state, style selection.
- [`strategy_box_automation_ai_research_2026-10-06.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md) — operation/result/artifact access for automation and AI.
- [`stratbox_business_logic_machine_schemes_architecture_research_2026-10-07.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_logic_machine_schemes_architecture_research_2026-10-07.md) — typed inputs/outputs, declared effects and evidence.
- [`stratbox_execution_control_user_path_research_2026-10-07.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_execution_control_user_path_research_2026-10-07.md) — execution parameter snapshots, safe cancellation.
- [`stratbox_target_core_design_architecture_2026-10-07.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_target_core_design_architecture_2026-10-07.md) — domain vs application/renderer architecture; subsequent System Model 01 has priority on repository choices.

## 22.4. Implementation probes: checked public code

- [`stratbox/base/filestore/base.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/filestore/base.py) — FileStore Protocol and RAM-oriented fallback `copy`.
- [`stratbox/base/net/http.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/net/http.py) — current DownloadResult, retries and whole-payload bytes.
- [`stratbox/registries/_loader.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/registries/_loader.py) — current resource `mtime` selection.
- [`cbr_file_collector/contracts.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/macrobanks/cbr_file_collector/contracts.py) — source_id and current typed download/collect records.
- [`escrow/contracts.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/macrobanks/escrow/contracts.py) — historical source/cache/dataset/view/exports contracts.
- [`cbr_forms/common/direct_form.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/macrobanks/cbr_forms/common/direct_form.py) — DBF physical-to-semantic mapping and missingness.
- [`cbr_sors_restoration/contracts.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/macrobanks/cbr_sors_restoration/contracts.py) — specialized configuration, source sets and inference contracts.

Для `stratbox-windows` используются указанные выше current-state срез и System Model 01; свежий полный построчный аудит всех Windows modules **в этом исследовании не проводился**.

## 22.5. External reference models: сравнение, не импорт архитектуры

- [W3C PROV-O](https://www.w3.org/TR/prov-o/) — различение Entity / Activity / Agent и типов provenance relations.
- [W3C DCAT 3](https://www.w3.org/TR/vocab-dcat-3/) — понятия catalogued Dataset / Distribution, version и series.
- [W3C CSVW](https://www.w3.org/TR/tabular-data-model/) — semantics табличных данных и metadata/schema.
- [OpenLineage specification](https://openlineage.io/docs/spec/) — Run / Job / Dataset / facets для наблюдаемой data lineage.
- [SQLite WAL documentation](https://www.sqlite.org/wal.html) — локальная транзакционная индексация и ограничения WAL для сетевых файловых систем.

Следует использовать эти модели **селективно**: совместимую семантику отношений и проверки без обязательного внедрения полной стандартной программной инфраструктуры.

## 22.6. Historical material

`01-old-notes` — исключительно historical provenance, полезный для пользовательских мотивов и устаревших вариантов физической архитектуры. Не используется как доказательство текущей функции. Базовое описание AppDock, загруженное в материалы проекта, используется только для разграничения владельца среды и владельца аналитической семантики.

---

# 23. Финальный консолидированный вывод

**[CONSOLIDATED]** Data → Knowledge architecture Strategy Box должна обеспечивать не просто движение байтов в Excel-файл, а **прослеживаемую трансформацию содержания с явными пределами утверждаемого**:

```text
external source / authority
  → admitted source snapshot with exact content identity
  → physical decoding / source schema
  → semantically-defined observation
  → dataset version and validation
  → declared transformation / reconstruction / evidence
  → qualified analytical result and, if warranted, claim
  → one or more immutable representations (artifacts)
  → runtime catalog, permissions and user projection
  → currentness / impact / revalidation over time
```

Эта система должна отвечать на семь практических вопросов: **что получено; откуда; когда и в какой редакции; что это означает; как рассчитано; насколько подтверждено; каким результатом/артефактом представлено и действительно ли применимо сейчас**.

**[TARGET-HYPOTHESIS]** Ближайшая реализация должна начинаться с минимального вертикального пилота `SourceSnapshot + RegistrySnapshot → DatasetVersion → AnalyticalResult/Provenance → ArtifactManifest` на существующих core-доменах. Совместная модель должна оставаться доступной из чистого Python без GUI; application runtime добавляет durable workflow/catalog/access, AppDock — operational substrate, клиенты — визуальные проекции. Полноценный CAS, ClaimStore, распределённая БД и общий Knowledge server выбираются только после явных требований и пилотов.

**[UNKNOWN]** Конкретные API schemas, policy thresholds, retention regimes, physical stores, revalidation rules и лицензируемые/организационные ограничения пока не являются утверждёнными решениями. Именно их — а не ещё одну переработку существующего текстового корпуса — нужно проверять следующими инженерными срезами.

**Граница результата:** этот документ является самостоятельным Research Synthesis темы 03 третьей ветки; он не меняет поддерживаемое Knowledge, Product Decision, репозитории или текущий код.
