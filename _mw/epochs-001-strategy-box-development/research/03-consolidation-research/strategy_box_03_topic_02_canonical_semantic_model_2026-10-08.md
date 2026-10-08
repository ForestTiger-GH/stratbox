# Strategy Box — тема 02. Canonical Semantic Model

**Ветка:** `03-consolidation-research`  
**Тема программы:** `02 — Canonical Semantic Model`  
**Дата:** 2026-10-08  
**Статус:** **Research Synthesis / Consolidation Input**; не Product Decision, не утверждённый Target WHAT/HOW, не change request  
**Baseline:** материалы `02-base-study`, карта корпуса темы 00, текущие implementation studies `stratbox` и `stratbox-windows`  
**Исторический слой:** `01-old-notes` только как источник происхождения гипотез  
**Изменения репозиториев:** отсутствуют  
**Публичная граница:** исключительно нейтральные определения расширений; без сведений о закрытых реализациях  

---

## 0. Executive synthesis

### 0.1. Центральный результат

Текущий Strategy Box уже содержит операционный, аналитический и пользовательский словарь, но эти три языка пока соединены переходными именами. `Operation` в core означает предметную функциональность, в Windows — вызываемый handler с формой параметров; `Scenario` то пользовательская задача, то механически созданная обёртка операции; `Case` одновременно служит карточкой запуска, историей шагов и пользовательским контекстом; `Result` означает и выход метода, и итог выполнения, и создаваемый файл. Более поздние исследования добавили `Work`, `Thread`, `Run`, `Job`, `Attempt`, `Machine Scheme`, `Claim`, `Evidence`, `SourceSnapshot` и `Artifact`, существенно точнее выражающие разные ответственности.

**CONSOLIDATED.** Единая модель должна различать **смысл работы, определение способности, разрешённый план, факт исполнения, полученное знание, физические результаты и пользовательское представление**. Сводить эти уровни в один `Case`, `Scenario`, `Result` или `File` нельзя.

**TARGET-HYPOTHESIS.** Предлагается нормализованный словарь с шестью пересекающимися, но различимыми плоскостями:

1. **Предмет и знание:** `SourceDescriptor`, `SourceSnapshot`, `RegistrySnapshot`, `Entity`, `MeasureDefinition`, `Observation`, `Dataset`, `Claim`, `Evidence`, `AnalyticalResult`.
2. **Способности и определения:** `CapabilityDefinition`, `OperationDefinition`, `SchemeDefinition`, `ScenarioDefinition`, `ExecutionBinding`, `CapabilityEnvelope`.
3. **Намерение и работа:** `Thread`, `Message`, `Work`, `WorkRequirement`, `WorkResult`, `Assessment`, `Acceptance`, `Closure`.
4. **Исполнение:** `Run`, `ActivationBinding`, `ExecutionPlan`, `Job`, `OperationRun`, `Attempt`, `EffectReceipt`, `ProgressEvent`, `ExecutionOutcome`.
5. **Хранимые и представляемые объекты:** `Artifact`, `ArtifactManifest`, `ArtifactRef`, `Materialization`, `WorkspaceObject`, `View`, `LogRecord`, `Problem`.
6. **Участие и управление:** `Principal`, `User`, `Actor`, `Participant`, `Session`, `Node`, `AuthorityGrant`, `Approval`, `Assignment`, `AutomationSpec`, `TriggerSpec`, `TriggerOccurrence`, `PluginDescriptor`, `ProviderBinding`, `ExecutionBackend`, `Surface`.

Это **семантический словарь**, а не требование создать классы, таблицы и репозитории для каждого названия. Различие может существовать как отдельный тип, составная часть объекта, relation или projection. Физическая материализация допустима при независимых жизненном цикле, идентичности, изменении, потребителе или проверяемом эффекте.

### 0.2. Главные разрешения

| Вопрос | Консолидированное направление | Степень определённости |
|---|---|---|
| `Command` или `Operation`? | `Operation` — каноническая предметная вызываемая способность. `Command` — при необходимости внутреннее действие исполнительного/транспортного слоя. | **CONSOLIDATED / recommended naming** |
| Что такое `Scenario`? | Курируемое продуктово-пользовательское определение повторяемого use case; с параметрами, ожидаемым исходом и ссылкой на исполнимый способ. | **CONSOLIDATED** |
| Что такое `Machine Scheme`? | Версионируемая машинно-читаемая композиция способностей с типизированными связями и условиями применимости. | **TARGET-HYPOTHESIS, strong** |
| Нужен ли отдельный `Cascade`? | Как термин UI — да, если полезен. Как обязательный третий canonical execution type — оснований пока мало; прежде проверяется композиция Scenario/Scheme. | **OPEN / provisional resolution** |
| `Case` = `Work`? | Нет. Текущий `ScenarioRunCase` ближе к execution record + карточке UI. `Work` живёт дольше отдельных запусков. | **CONSOLIDATED** |
| `Run` = `Job`? | Нет. `Run` — конкретная траектория реализации Work. `Job` — планируемая, выделяемая исполнителю единица внутри Run. | **TARGET-HYPOTHESIS, high confidence** |
| `OperationRun` = `Attempt`? | Нет. Invocation операции переживает безопасный retry; новая физическая попытка получает новый `Attempt`. | **CONSOLIDATED** |
| `Result` = `Artifact`? | Нет. Result — установившийся смысловой итог; Artifact — устойчивый адресуемый носитель/выход. | **CONSOLIDATED** |
| `ExecutionOutcome` = `Work completion`? | Нет. Успешное исполнение не гарантирует удовлетворение поручения и принятие результата. | **CONSOLIDATED** |
| `Thread` = `Work`? | Нет. Thread организует взаимодействие; Work организует ответственность за результат. | **CONSOLIDATED** |
| `Plugin` = `Provider` = `Capability`? | Нет. Пакет расширения, поставщик реализации и объявленная способность имеют разные идентичности. | **CONSOLIDATED** |
| `Dataset` = `Observation` = `Claim`? | Нет. Набор наблюдений не делает аналитический тезис доказанным. | **CONSOLIDATED** |

### 0.3. Критические инварианты

- Стабильный ID определения, его версия, binding реализации, конкретный invocation и факт выполнения **всегда различимы**.
- Chat message, `CaseView`, UI card, path, log line и DataFrame **не становятся** семантическим источником истины Work/Job/Result.
- Одна Work может содержать много Runs; один Run — несколько Jobs и OperationRuns; Retry не создаёт молча новую Work.
- Фоновое, интерактивное, запланированное, удалённое и AI-инициированное выполнение — **режимы/источники**, а не пять видов сценариев.
- Число, полученное из официальной публикации, ещё требует семантики показателя, периметра, периода, версии источника и преобразования.
- `UNKNOWN` в пригодности способности, состоянии исполнения, доказанности тезиса и актуальности данных — **разные значения в разных типизированных полях**.
- Вывод, отображение и авторизация не могут усиливать исходный доказательный статус.
- Конкретные закрытые расширения остаются вне публичной онтологии. Публичной системе достаточно нейтральных `PluginDescriptor`, `Capability`, `ProviderBinding` и health/status.

### 0.4. Что этот результат решает, а что оставляет другим темам

Это исследование **предлагает смысловые определения и отношения**. Оно не выбирает СУБД (тема 05), не разрабатывает полный scheduler/state machine (04 и 08), не фиксирует Scheme DSL/extension ABI (06), не принимает навигацию Windows/Web/Android (07), не определяет физическое число репозиториев (01 и 09) и не принимает окончательную модель хранения Knowledge (03 и 05).

---

## 1. Источники, метод и уровни доказательности

### 1.1. Точный предмет программы

В [программе третьей ветки](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/strategy_box_03_consolidation_research_program.md) тема 02 названа `Canonical Semantic Model`. Её вопрос — **«Какие сущности реально существуют в продукте и как они называются?»**. Программа отдельно требует снять `Case` против `Work/Run`, `Operation` против `Command`, `Scenario` против `Cascade/Machine Scheme`, `Result` против `Artifact`, `Thread` против `Work`, а также согласовать способности, источники, акторов и автоматизацию.

Использованы [README третьей ветки](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/README.md), [тема 00 — карта корпуса](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_00_corpus_map_open_questions_2026-10-08.md), исходные тематические исследования второй ветки (полный ledger в §17), два опубликованных среза implementation-state от 2026-10-06 и описание AppDock как внешнего продукта.

### 1.2. Source hierarchy

1. **CURRENT:** прямой код/документация владельца реализации и проверенные current-state studies, привязанные к конкретному commit.
2. **CONSOLIDATED:** повторяющиеся выводы нескольких независимых исследований, согласованные по scope и времени.
3. **TARGET-HYPOTHESIS:** предлагаемые разделения или контракты, ещё без Product Decision/implementation verification.
4. **CONFLICT:** два действительно несовместимых значения, а не просто разные названия или уровни детализации.
5. **SUPERSEDED:** исторический вариант, вытесненный более поздней аргументированной моделью.
6. **UNKNOWN:** данные отсутствуют либо решение должно опираться на будущий vertical slice, тест, нагрузку или отдельное governance-решение.

Research документы, даже очень убедительные, сохраняют статус Research. Термин `target` здесь обозначает **предложение для дальнейшей сборки Product Knowledge**, а не вступившую в силу спецификацию.

### 1.3. Фактическая привязка

[Базовое исследование `stratbox`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_base_study_current_state_2026-10-06.md) проверяло `stratbox@e968853572676d8e5d963607d1f0cb50ff8f20b7`, версия `0.8.0`. [Windows baseline](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md) проверял `stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b`, версия `0.1.0`. Сверка, записанная в теме 00, показала отсутствие изменений `src/` и `tests/` core на тогдашнем `main` относительно среза и совпадение Windows HEAD. В этой работе новый запуск тестов этих репозиториев **не выполнялся**; current-сведения ниже опираются именно на указанный верифицированный baseline и релевантные исследования, а не выдаются за результат нового E2E.

### 1.4. Принцип минимальной онтологии

**Создавать объект только за самостоятельную ответственность.** Четыре проверочных вопроса:

1. Может ли объект возникнуть, исчезнуть или измениться независимо от соседнего?
2. Нужны ли ему собственная идентичность, версия, полномочия, history либо внешние ссылки?
3. Может ли один экземпляр участвовать в нескольких отношениях/запусках/пользовательских представлениях?
4. Влияет ли его потеря или смешение с соседним понятием на корректность, безопасность, восстановление или provenance?

Положительный ответ — довод в пользу самостоятельной сущности. Отрицательные ответы допускают property, relation, value object или projection без отдельного хранилища.

---

## 2. Фактический словарь действующей системы (CURRENT)

### 2.1. В `stratbox` 

`stratbox` — библиотечный domain/business owner без встроенного Windows UI. Он предоставляет `FileStore` и IO operations, загрузку данных и преобразование форматов, справочники банков/ОКВЭД2, `cbr_file_collector`, `cbr_forms`, `cbr_industries`, `cbr_sors_restoration`, `escrow`, `frg`, а также типизированные Request/Result в неодинаковой степени по доменам.

Конкретные semantic seeds:

- у источников присутствуют устойчивые `source_id` и descriptors/registry items;
- в `cbr_forms` `IndicatorId` отделяет показатель от отображаемой строки;
- `cbr_forms` разделяет physical data, semantic CSV model, canonical long, view и Excel;
- `cbr_industries` и `escrow` различают discovery, parse, derived data, view, export;
- `cbr_sors_restoration` различает quantity, официально опубликованную величину, интервалы округления, evidence tiers, факты, доказательные методы, assumption tiers и conflicts;
- `frg` различает план очистки и destructive execution;
- core API уже предоставляет `FileStore` и Excel style resources как отдельные контракты.

Но общего `SourceSnapshot`, `CapabilityDefinition`, `OperationDefinition`, `Work`, `Run`, `ArtifactManifest`, `Claim` или `KnowledgeItem` contract, охватывающего весь продукт, этот baseline **не устанавливает**. В большинстве обычных pipelines путь от DataFrame к XLSX короче желаемой модели provenance и аналитического обоснования.

### 2.2. В `stratbox-windows`

Текущие модели и их фактическая роль:

| Текущая сущность | CURRENT meaning | Слабость для целевой онтологии |
|---|---|---|
| `OperationSpec` | ID/title, handler reference, параметры, ограничения, metadata, visibility | definition, presentation metadata и executable binding сведены близко |
| `ScenarioSpec` | `atomic/composite/background/assignment` kinds, steps, params, policies | workflow structure смешана со способом запуска и источником запроса |
| `ScenarioRunCase` | запуск сценария, автор, параметры, timestamps, steps, progress, outputs, status | Run/history/UI card и возможная долговечная Work схлопнуты |
| `EventRecord` | историческое событие пользовательской timeline | событие пока прежде всего локальной UI/history системы |
| `ArtifactRecord` | path/kind/name, author, case/scenario/operation/log linkage | artifact ID и metadata есть, но identity остаётся path-oriented |
| `LogRecord` | ссылка на файл журнала запуска | лог — evidence, но не унифицированное состояние |
| `Assignment` | локальное поручение с автором/адресатом/status | отсутствует shared authority/workflow backend |
| `BackgroundProcessSpec/Store` | декларации и локальные переключатели фоновой активности | нет durable scheduler/executor |
| `PresenceService` | локальная проекция текущего пользователя и авторов cases | нет authoritative multi-user presence |
| `AppContext` | runtime binding: node/user/session, workspace, state, health | объединяет runtime context, но сам не новый universal product owner |

Три зарегистрированные операции: `cbr_file_collector.collect`, `escrow.history.export`, `system.diagnostics`. Сценарии автоматически оборачивают enabled operations, есть один composite `scenario.cbr.full_update`. Исполнение через Qt `QThread`, один сценарий одновременно, полноценной отмены нет. История хранится в нескольких локальных JSON; функции фоновых задач и реальных других участников ограничены каркасами. Это и есть **CURRENT**, а не предлагаемая долговечная система.

### 2.3. AppDock boundary

Внешняя система AppDock описывает **узел** как управляемую рабочую среду и отвечает за установку, запуск, readiness, состояние среды, восстановление и будущий удалённый доступ. Strategy Box получает activation/session/node binding, но предметные `Operation/Scenario/Work/Job` и банковские результаты остаются семантикой Strategy Box. `Node` — общий инфраструктурный контекст, не замена `Work`, `Workspace`, `Session` или `Job`.

### 2.4. Статус current implementation

Не приписывать готовность целевым типам: **нет подтверждённого durable Work store, общего headless JobManager, полноценного Scheme IR, единого source/evidence graph, реального Windows multi-user backend, отдельного `CaseView` и общего `ArtifactCatalog`**. Они являются целевыми моделями/кандидатами.

---

## 3. Канонические семантические оси

Прежде чем выбирать имена классов, нужен независимый набор координат. Иначе разные команды будут вынужденно называть одним словом разные вещи.

| Ось | Один полюс | Другой полюс | Пример ошибки при смешении |
|---|---|---|---|
| Definition ↔ occurrence | `OperationDefinition` | `OperationRun` | `operation_id` ошибочно считается ID исполнения |
| Meaning ↔ mechanism | `CapabilityDefinition` | Python handler/backend | `module:function` считается семантической identity |
| Intent ↔ execution | `Work` | `Run/Job` | закрытие worker закрывает поручение |
| Plan ↔ observed fact | `ExecutionPlan` | события/receipts | запланированный write объявляется совершённым |
| Logical ↔ physical | `Artifact` | storage path/blob | перенос файла «меняет» результат |
| Observed ↔ inferred | `Observation` | `DerivedValue/Claim` | реконструкция публикуется как прямая отчётность |
| Publication ↔ reliance | `SourceSnapshot` | `qualified Result/Claim` | достоверность публикации отождествляется с правотой вывода |
| Identity ↔ version | `source_id` | `snapshot_id` | получение новой публикации перезаписывает историю |
| Actor ↔ principal | causally acting entity | accountable auth context | `actor_kind=ai` принимается за permission |
| Durable ↔ ephemeral | `Work/Artifact` | presence/typing/surface cursor | online-флаг управляет правом доступа |
| Value ↔ representation | evidence/result | formatted table/chat card | округлённая подпись становится новым «фактом» |
| Domain ↔ platform | `stratbox` operations | AppDock node lifecycle | AppDock начинает определять бизнес-смысл сценариев |
| Configuration ↔ state | `UserSettings` | `SurfaceState/RunParameters` | последний выбранный сценарий превращается в настройку |
| Status ↔ outcome ↔ assurance | queued/running | succeeded/unknown | успешное завершение подменяет доказанность аналитики |

**TARGET-HYPOTHESIS:** смысловой каркас можно описывать ориентированным графом отношений, но для реализации достаточно типизированных ссылок/таблиц и явных invariant checks. Общая graph database, универсальная онтологическая платформа и гигантский `Entity` base class этому этапу не нужны.

---
## 4. Предметная и эпистемическая модель: Source → Knowledge

Здесь особенно важно зафиксировать **отношения, а не просто список существительных**. Подробная физическая data-архитектура остаётся темой 03. Данное исследование устанавливает значения слов.

### 4.1. `SourceDescriptor` и `SourceSnapshot`

**SourceDescriptor** — идентифицируемое описание внешнего источника, публикационной серии или канала получения. Оно отвечает: *«Что считается источником и где ожидается его публикация?»* Возможные поля: `source_id`, authority/publisher, family, declared construct, cadence, acquisition method, expected schema family, scope/limitations. Descriptor переживает множество обновлений.

**SourceSnapshot** — зафиксированное конкретное содержание источника в определённый момент наблюдения. Отвечает: *«Что именно было получено и на каком основании это содержимое можно использовать?»* Важны `snapshot_id`, `source_id`, `retrieved_at`, `published_at/released_at` при известности, `period`, `content_hash`, format/schema version, validation/fetch outcome, immutable locator.

**Разграничение.** Одна и та же публикация может быть повторно скачана без изменения байтов; разные редакции публикации могут относиться к одному отчётному периоду. Поэтому нельзя использовать `period`, URL или имя файла как уникальный `snapshot_id`. `content_hash` подтверждает идентичность байтов, но не эквивалентность значения (например, разные XLSX formatting могут содержать ту же таблицу). `Release` как самостоятельная сущность нужен, если появится потребитель, который различает публикационное событие от множественных его извлечений; **пока UNKNOWN, необязательный тип**.

**CURRENT:** существуют конкретные source registries/скачанные файлы и частные типизированные результаты, общего единообразного snapshot contract нет. **CONSOLIDATED:** identity descriptor и captured state должны отличаться.

### 4.2. `Registry`, `RegistryDefinition`, `RegistrySnapshot`

Слово «реестр» **перегружено**. Требуется минимум три категории:

- **Reference Registry** — утверждённая/сопровождаемая справочная система, например identity банков, ОКВЭД2, география. `RegistrySnapshot` фиксирует редакцию и effective interval.
- **Source Catalog** — набор `SourceDescriptor` и правил discovery; не превращается в реестр банков только потому, что обе структуры хранят строки.
- **Domain Rule Catalog** — определения форм, family recognition, publication categories, specialized semantic transformations внутри конкретного домена.

Отдельно существуют capability, format, style catalogs: это реестры **другого рода**. Схожий storage API не даёт им общую предметную identity. `RegistrySnapshot` связывает версию reference data, content hash, authority, schema/effective validity и admission/status. Использование справочника должно оставлять ссылку на его конкретную редакцию.

**Пример:** «Банк X» с одним названием в официальном реестре, другом alias и в отчёте консолидированной группы — не одна автоматически тождественная сущность. Название — display/alias; identity должна сохранять регистрационный/юридический/периметровый смысл и временную актуальность.

### 4.3. `Entity`, `MeasureDefinition`, `Observation`

**Entity / Subject** — предмет наблюдения: юридическое лицо, банковская группа, отрасль, географическая единица, сегмент экономики. Её identity должна допускать scope, version/effective interval и связанное reference system. Универсальный глобальный реестр всех entities вводить преждевременно: допустимы domain-specific stable IDs с явными crosswalks.

**MeasureDefinition / Construct** — *что именно измеряется*. Отвечает на вопросы: экономический смысл, unit, numerator/denominator, accounting/perimeter basis, aggregation rules, temporal role, definition revision, классификационный стандарт. `indicator_id` — правильный уже существующий seed, но одинаковые названия не гарантируют тождества показателей.

**Observation** — определённая величина/состояние для `subject + measure + reference period + perimeter + source/vintage`. Она содержит value/missingness, units, reported/derived qualification, method and provenance links. Нулевое значение, blank, подавленное наблюдение, not applicable и отсутствие источника должны быть различимы.

**CanonicalObservation** — результат явно указанной нормализации, а не «величина, которой теперь можно безусловно верить». **DerivedObservation/Estimate** — значение из преобразования, реконструкции или модели. При сильном reuse достаточно `Observation` с типизированными происхождением/методом; создавать отдельный базовый класс на каждую разновидность необязательно.

### 4.4. `Dataset` и `DatasetSnapshot`

**Dataset** — именованная семантически однородная коллекция/продукт данных с объявленной схемой, dimensions и governance. **DatasetSnapshot** — зафиксированное конкретное состояние набора с версией inputs/transform и digest. Не каждый промежуточный DataFrame заслуживает долговечный `Dataset`; многие являются transient value внутри `OperationRun`.

**Порог материализации:** dataset адресуется другими Work/Run, допускает независимые версии, используется в аналитических основаниях или требует воспроизводимости. Тогда нужны stable reference, schema version и provenance. Иначе достаточно payload/result part.

**CONFLICT/SCOPE:** `Dataset` нельзя путать с `Artifact`: первое обозначает семантическую коллекцию, второе — управляемый произведённый объект. Один DatasetSnapshot может быть представлен несколькими Artifacts (Parquet, XLSX, JSON); один Artifact (например, архив) может содержать несколько datasets.

### 4.5. `Claim`, `Evidence`, `Basis`, `Inference`

**Claim** — явно сформулированное, проверяемое в некоторой области утверждение, включая reported, descriptive, comparative, explanatory, causal, predictive, conditional и evaluative роли. Например, «корпоративный портфель вырос на 7%» и «рост обусловлен изменением периметра» — **разные claims**: первая может поддерживаться данными, вторая требует причинного обоснования.

**EvidenceReference** — ссылка на наблюдения, документы, расчёты, validation records, эксперименты или результаты, **относящиеся к конкретному claim**. Надёжность источника в целом не равна доказанности каждого тезиса.

**Basis / AnalyticalBasis** — совокупность определений, наблюдений, преобразований, допущений, альтернатив, ограничений и условий применимости конкретного вывода. **Inference/Transformation** — квалифицированная связь, показывающая, каким методом из оснований был выведен claim/result.

Многомерная квалификация: `support_state`, `scope`, `conditions`, `uncertainty`, `assumptions`, `defeaters`, `currentness`, `permitted_reliance`. Универсальный `confidence=0.87` не заменяет эти поля; оценка вероятности допустима только в конкретной модели, где число осмысленно.

**Нужен ли каждый Claim как отдельная запись?** **UNKNOWN / selective.** Для больших аналитических результатов и оспариваемых тезисов — да. Для каждой ячейки бухгалтерской формы — обычно избыточно. Минимальный контракт должен позволять получить ClaimRef/BasisRef при существенном выводе без требования превращать все данные в knowledge graph.

### 4.6. `Knowledge`, `ResearchHistory`, `Decision`

**Knowledge** — обоснованная, сопровождаемая и квалифицированная смысловая позиция, пригодная для определённого reliance. Это не синоним полнотекстового поиска, списка файлов или истории гипотез. Утверждение может быть сохранено исторически истинным как «так было опубликовано» и одновременно не годиться для сегодняшнего решения.

**ResearchHistory** хранит происхождение поиска, альтернатив и несогласованные состояния. **Decision** отражает принятую компетентным субъектом альтернативу/обязательство, а не автоматически более высокую версию AnalyticalResult. **Recommendation** может быть Result/Claim без превращения в Decision. **Authority** необходима для такого перехода.

### 4.7. `Currentness` не равно `latest_filename`

Для макро- и банковской аналитики требуется различать: `observed_at`, `reported_period`, `published_at`, `retrieved_at`, `effective_from/to`, `snapshot_validity`, `analysis_as_of`, `revalidated_at`. Одна редакция может быть самой недавно скачанной, но не самой поздней экономически; самая поздняя версия источника может пересмотреть старые периоды.

**CONSOLIDATED:** текущесть — отношение *объект × область применения × момент × источник/правила проверки*, а не универсальный boolean `is_current`.

### 4.8. Пример: банковский показатель

```text
SourceDescriptor: официальная серия отчётности
    ↓
SourceSnapshot: опубликованный файл конкретной редакции
    ↓
RegistrySnapshot: банки / классификация на дату
    ↓
MeasureDefinition: показатель, единица, отчётный периметр
    ↓
Observation: величина по банку и дате
    ↓
Transformation: изменение периода/валюты/периметра
    ↓
Claim: «показатель A сопоставим с B после корректировки X»
    ↘ Evidence + assumptions + limitations
    ↓
AnalyticalResult: сравнение с допустимой областью применения
    ↓
Artifact: рабочая книга, таблица или отчёт как проекция результата
```

Даже если всё отображается одним XLSX, внутренние смысловые переходы различимы. Подробные storage schemas и lineage materialization относятся к теме 03.

---

## 5. Capability, Operation, Command, Scenario, Scheme

### 5.1. `CapabilityDefinition` — «какая способность существует»

Семантическая способность описывает *what and when*, независимо от конкретной реализации. Минимальные смыслы: stable ID/version, intended task/result, typed inputs/outputs, applicability, preconditions, effects and frame conditions, failure classes, cancellation/idempotency/retry/concurrency/resource constraints, data freshness, assurance/known limitations. Это **не** функция Python и **не** автоматически предоставленное право запуска.

`CapabilityEnvelope` квалифицирует пределы достоверно поддерживаемой способности: известные схемы/периоды данных, тестированные режимы, resource profile, ограничения, provenance validation и причины деоптимизации/fallback. Envelope способен изменяться без переименования core semantic ID, но должен быть versioned/traceable.

### 5.2. `OperationDefinition` (каноническая Operation)

**Operation** — самостоятельный предметно значимый вызываемый use case с устойчивым semantic contract и определённым профилем эффектов. Обладает идентичностью, независимой от Python `module:function`, transport protocol и UI. Примеры кандидатов: `cbr.files.collect`, `cbr.forms.build`, `escrow.history.build`, `frg.cleanup.plan`, `frg.cleanup.apply`, `sors.restore`.

`OperationDefinition` — это **одна из форм CapabilityDefinition**, которая допускает прямое выполнение через binding. В будущем можно реализовать semantic capability через локальный Python, remote worker или оптимизированную реализацию; совместимость доказывается по смыслу входа/выхода, effects и validity, а не по совпадению имени функции.

**OperationInvocation** — конкретный запрос применить OperationDefinition с параметрами и context. **OperationRun** — запись исполнения этой invocation. Эти ID раздельны; один invocation может быть отклонён до запуска или, при корректной retry policy, привести к нескольким attempts.

### 5.3. `Command` — спорный термин

Раннее исследование команд предлагало `CommandSpec` для «скачать файл», «прочитать XLSX», «открыть каталог», а `Scenario` — для пользовательского смысла. Исследования переносимости/машинных схем на том же уровне различают mechanisms, building blocks, domain services и canonical operations.

**CONFLICT RESOLUTION (proposed):** **не вводить `Command` как обязательный публичный объект**, если его можно выразить техническим step/action внутри операции или job. Каноническим внешним контрактом остаётся `OperationDefinition`. При появлении реального orchestration consumer термин `Command` можно использовать для атомарной инфраструктурной команды (например, `download_chunk`, `stage_file`) с собственными техническими требованиями, **без обещания бизнес-смысла**. `Command` не должен автоматически попадать в capability catalog или пользовательский сценарий.

Решение основано на семантике, а не на более поздней дате документа. `Operation` имеет несколько независимых пользователей — core, приложение, automation, AI и machine registry. Выделенный global Command Registry пока имеет более слабое обоснование. Его окончательный API остаётся **OPEN**.

### 5.4. `ScenarioDefinition` — курируемая пользовательская возможность

**Scenario** отвечает: *«Какой повторяемый понятный пользователю способ работы доступен?»* Это product-level definition, представляющее goal, inputs/defaults, output expectations, constraints/availability и объяснимое исполнение. Его не следует отождествлять ни с конкретным Work, ни с `Run`.

Scenario может ссылаться на одну Operation, несколько Operations или Scheme, но **не возникает автоматически из каждой технической Operation**. Вопрос «показать пользователю?» зависит от смысловой ценности и поддерживаемого UX, а не от наличия Python callable.

Один и тот же Scenario можно запускать из разных Threads, Work, по расписанию, через API и разрешённым machine actor. Результатом старта становится Work/Run по admission policy, а не новый ScenarioDefinition.

### 5.5. `SchemeDefinition` / `Machine Scheme`

**Machine Scheme** — версионируемая, типизированная, inspectable, reusable композиция Operations и других Schemes с dependencies, ports, guards, pre/postconditions, эффектами, обработкой отсутствия данных и условиями применимости. Scheme описывает *повторяемый способ исполнения*, но не связывает заранее конкретные креденшелы, исходные файлы, дату запуска или worker. Последние появляются в Binding и Plan.

Scheme может реализовывать один Scenario; одна Scheme может поддерживать несколько product scenarios с разными user-facing профилями; Scenario может временно реализовываться напрямую одной Operation. Следовательно, **Scenario и Scheme являются разными определениями**, но не обязательно разными runtime engines.

**Scheme != ExecutionPlan.** Definition допускает параметры, варианты и guards. Plan является уже разрешённой конкретной версией схемы на определённых входах, при конкретных capabilities и policies.

### 5.6. `Cascade`: самостоятельный объект или представление?

В раннем `commands/scenarios/cascades` исследовании **CascadeSpec** выделялся как композиция нескольких ScenarioSpec для общей пользовательской цели (например, «обновить весь блок статистики»). `Machine Scheme` исследовался как общая композиция машинных способностей. Поздние работы задают Work-центричную модель, где каталог повторяемых схем и сценариев подлежит объединению без повторения execution engines.

**Консолидационный выбор:**

- Слово **«каскад»** сохранить как полезное **product/UX обозначение масштабного многозадачного workflow**.
- **Не создавать отдельную обязательную execution primitive `CascadeRun`**. Его исполняет тот же `Run → Plan → Job` spine.
- Кандидат `CascadeDefinition` оправдан, **только если** композиция самостоятельных `ScenarioDefinition` обладает собственными governance, membership selectors, result aggregation, admission/versioning и потребителем каталога, которые невозможно чисто выразить в `SchemeDefinition + ScenarioDefinition`.
- До такого доказательства: `Cascade` — профиль/вид Scenario, реализуемый Scheme с вложенными сценарными целями; точное relation остаётся **UNKNOWN**.

Это сознательное уточнение ранее предлагавшейся обязательной отдельной сущности: оно минимизирует количество синонимов и убирает две параллельные «машины каскадов».

### 5.7. `ExecutionBinding`, `ProviderBinding`, `ExecutionBackend`

**ExecutionBinding** — выбор фактической реализации заявленного semantic contract в допустимой среде. **ProviderBinding** — привязка предоставленной implementation capability к интерфейсу и policy. **ExecutionBackend** — исполнитель, принимающий уже разрешённую Job/OperationInvocation и организующий её выполнение локально, в worker pool или удалённо.

Эти три вещи нельзя сливать в `OperationDefinition`:

```text
Capability / OperationDefinition
     ├── validity and effect contract
     └── chosen implementation binding
                  ↓
          resolved ExecutionPlan
                  ↓
         ExecutionBackend → Job / OperationRun / Attempt
```

**PluginDescriptor** описывает устанавливаемое расширение и его вклад; `Provider` — программный поставщик конкретной реализации; `Capability` — смысловое объявление возможности. **Installed != discovered != validated != activated != bound != authorized**. Публичный core использует только нейтральные protocols/metadata и versioned identities.

### 5.8. Capability — ещё не authority

Сведения «умеет удалить папку» не означают «этому участнику разрешено удалить эту папку сейчас». Право — отношение `Principal/Actor + operation/effect + resource + scope + time + grant/policy`. Нужны отдельно `Applicable`, `Available`, `Authorized`, `Approved` и `Executable` (возможно с UNKNOWN или refusal reason).

---

## 6. Thread, Work, Case, Run, Job и Attempt

Это главный конфликт корпуса. Более ранние документы называли одной «задачей» то поручение, то запуск, то фоновый job; поздние исследования предложили разложить его на несколько жизненных циклов. Здесь выбирается минимальная непротиворечивая модель.

### 6.1. `Thread` и `Message`

**Thread** — долговечный контекст взаимодействия: история сообщений, ссылки на работы и артефакты, участники, пользовательские представления, возможно summary. Он отвечает: *«В каком разговорном/рабочем контексте обсуждают предмет?»*

**Message** — запись коммуникационного акта с автором, временем, содержимым и ссылками. Текст сообщения **не равен** `Work` или технической команде; его нужно интерпретировать, валидировать и при необходимости преобразовать в `WorkCandidate`/`SubmitRun`.

**Предлагаемое отношение:** `Thread ↔ Work` **many-to-many через связи контекста**. Одна Work часто имеет primary Thread, но может обсуждаться в нескольких; Thread может содержать много Works и вообще не содержать ни одной (например, изучение справки). `Thread` не становится владельцем Work state. Для v1 можно материализовать primary_thread_id + optional links без сложной модели cross-thread sync.

### 6.2. `Work` — стабильный смысловой объект

**Work** — ограниченное поручение/исследование/производственная работа с заявленной целью, scope, потребителем, constraints, ответственностью и проверяемыми условиями удовлетворительного завершения. Источник Work может быть пользовательским сообщением, Scenario launch, automation trigger, assignment, API или разрешённым AI proposal.

Кандидат полей:

```text
work_id; title; purpose; requested_by/principal;
origin_refs[]; subject/scope; expected_result_contract;
constraints; acceptance_requirements; authority/policy_refs;
work_state; created_at; revision; participants/assignments;
run_refs[]; result_refs[]; residuals; closure_ref
```

**Особенно важно:** `Work` существует и в ожидании внешних данных, подтверждения или проверки; она может пережить закрытие окна, аварийный restart, смену пользователя/устройства, несколько вычислительных попыток и несколько отчётных артефактов.

**Admission threshold — OPEN:** не каждый внутренний вызов parser обязан создавать Work. Полноценная долговечная Work нужна при самостоятельном пользовательском намерении, обещанном результате, участнике/ответственности, многошаговости либо возврате к предмету. Простой `read_bytes()` внутри другой операции — механизм, а не Work.

### 6.3. `WorkCandidate`, `Commission`, `WorkRequirement`

**WorkCandidate** — предложение поручить работу до проверки scope/authority/feasibility; особенно полезно для AI, automations, peer requests. **Commission / Request / Intent** — основание возникновения Work. Не каждое исходное сообщение уже авторизованный Commission. **WorkRequirement** — одно проверяемое обязательство на результат или процесс (например, «собрать по МСФО, указать период, сохранить источники»). В минимальной реализации может быть частью Work, а не самостоятельной записью.

### 6.4. `Run` — конкретная траектория выполнения Work

**Run** — целостный эпизод реализации конкретной Work с заданными исходными условиями и наблюдаемой историей. Он отвечает: *«Какая попытка реализовать смысл Work была предпринята?»*

Одна Work может иметь `Run #1` для получения данных, `Run #2` для пересчёта по изменённой публикации, `Run #3` для независимой верификации; все относятся к тому же смысловому поручению. `Run` фиксирует immutable effective input/plan refs, versions, origin, timings, terminal outcome, produced result/evidence/artifacts. `Run` существует независимо от UI/thread и scheduler worker.

**Разница с `Work`:** завершение Run может привести к уточнению Work, а не автоматически закрыть её. Work иногда завершается без вычислительного Run — например, при обоснованной невозможности исследования или снятии поручения по полномочному решению.

### 6.5. `ActivationBinding` и `ExecutionPlan`

**ActivationBinding** — разрешённая на время запуска карта: exact capability definitions/versions, provider bindings, выбранные source/registry snapshots, parameters, output policy, security grants, resource limits, backend preference, artifact style defaults. Она фиксирует **с какой именно средой смысловая способность связывается**.

**ExecutionPlan** — конкретный, целостный, воспроизводимый план Run: resolved graph, dependencies, inputs, resources, effect boundaries, guards, expected outputs, plan digest. В отличие от SchemeDefinition, план не перенастраивается молча при изменении свежего реестра или установки расширения. Существенная смена плана — новая version/plan identity, иногда новый Run в зависимости от стадии выполнения и пользовательского scope.

**Plan != promise of effect:** наличие шага `delete(source)` в плане ничего не говорит о том, был ли выполнен destructive effect.

### 6.6. `Job` — планируемая/выделяемая исполнительная единица

**Job** — durable schedulable/claimable unit работы, которую JobManager может поставить в очередь, выделить исполнителю, ограничить по ресурсам, отменить, возобновить/перезапустить по policy и получить отдельный outcome. Один Run **может включать** одну или несколько Jobs; Job может исполнять одну canonical Operation или фрагмент Scheme. `Job` не тождественен рабочей цели.

Это разделение позволяет описать параллельные независимые вычисления и shared resources без создания отдельного Run/Work на каждую техническую подзадачу. `Job` имеет `job_id`, `run_id`, `plan_fragment_ref`, `claimed_by`, lifecycle, resource lease, checkpoints/attempts, events, outcome.

**TARGET-HYPOTHESIS:** при простом local run допустима одна Job. При длинных compositional workflows число Jobs и OperationRuns не обязано совпадать один к одному. Этот cardinality threshold следует проверить на FRG, escrow и SORS pilots (тема 04).

### 6.7. `OperationRun` и `Attempt`

**OperationRun** — логическая запись одной resolved invocation конкретной canonical Operation внутри Run/Job. Содержит входной semantic snapshot, version, start/finish, output/failure/provenance refs. **Attempt** — фактическая попытка выполнить данную invocation на выбранном executor/backend. Retry, если он допустим, создаёт **новый Attempt**, а не подменяет историю предыдущего.

Пример: операция получения публикации началась; сеть оборвалась; безопасный повтор с тем же idempotent request завершился успешно. Сохраняется одна логическая OperationRun и две Attempts. Если после timeout неизвестно, опубликован ли внешний результат (эффект), retry не допускается автоматически до reconciliation.

### 6.8. `Case` — не каноническая основа

Три разных значения во второй ветке:

1. **CURRENT Windows:** `ScenarioRunCase` — один запуск с шагами, статусом, параметрами и карточкой в чате.
2. **Ранние execution/observability исследования:** `Case` — широкое пользовательское поручение с несколькими jobs.
3. **Поздняя Work-модель:** `Work` — смысловой объект, `Run` — траектория; `Case` переходит в пользовательскую проекцию (`CaseView`, карточка, история).

**Рекомендуемое разрешение:** `Case` **не делать обязательной третьей долговечной сущностью между Work и Run**. Для чистой архитектуры: идентичности `work_id` и `run_id`, а `case` — допустимое пользовательское слово/`CaseView` поверх них. `ScenarioRunCase` текущего кода при переработке следует разложить: параметры/шаги/статус запуска → Run/Job; цель, потребитель, несколько запусков, дальнейшая проверка → Work; содержимое карточки → Projection.

**CONFLICT remaining:** если окажется, что пользователи требуют устойчивое «дело» с own admission/assignment/retention, отличающееся и от Work, и от Thread, это потребует независимого доказательства и возможно сущность Case. Пока такой consumer не установлен.

### 6.9. Нормализованный execution spine

```text
Thread ─── Message ──► WorkCandidate
  │                        │ admission/authorization
  │                        ▼
  └── contextual link ───► Work (goal / obligations / closure)
                             │
                        0..n Run
                             │
                    ActivationBinding
                             │
                       ExecutionPlan
                             │
                        1..n Job
                             │
                     0..n OperationRun
                             │
                        1..n Attempt
                             │
             Events / EffectReceipts / Diagnostics
                             │
              ExecutionOutcome / RunResult
                             │
          Work assessment / Acceptance / Closure

OperationDefinition / SchemeDefinition / ScenarioDefinition
          ── are REFERENCED, not mutated by Runs
```

Схема описывает возможные отношения, а **не обязательное правило «одна Attempt на каждый stage»**. Отказ при admission создаёт durable rejection receipt без Jobs; операция без фактической попытки может быть skipped/unsupported; Work может иметь ноль Runs.

### 6.10. Рабочие примеры различий

| Ситуация | Thread | Work | Run | Job/Attempt |
|---|---|---|---|---|
| Аналитик спрашивает о доступном сценарии | один разговор | ещё может отсутствовать | нет | нет |
| Пользователь просит обновить историю эскроу | контекст заявки | одна Work | один или несколько Runs | загрузка/обработка/экспорт как Jobs/OperationRuns по плану |
| Сбой сети и безопасный повтор загрузки | тот же | та же | тот же | новый Attempt конкретной OperationRun |
| Переход на исправленную редакцию публикации | тот же либо другой | та же, если цель неизменна | новый Run с другим SourceSnapshot | новые Jobs |
| Повторная независимая проверка вывода | может быть другой | та же либо child Work | новый Run | отдельные Jobs/Attempts |
| Ежедневный мониторинг | общий Thread или task center | Work по каждому значимому событию либо общая наблюдаемая Work — policy открыта | каждый запуск отдельный | каждая occurrence имеет собственную identity |
| Пользователь открыл XLSX | тот же | обычно новая Work не нужна | нет | UI action, не доменная Job |
| Долгая работа в фоне при закрытом UI | связь с Thread сохраняется | та же | тот же | Jobs продолжаются в host, если deployment это поддерживает |

---
## 7. Result, Outcome, Evidence, Artifact, Materialization

### 7.1. Три «результата», которые особенно легко спутать

**ExecutionOutcome** отвечает: *«Как завершилось выполнение?»* (`SUCCEEDED`, `PARTIAL`, `FAILED`, `CANCELLED`, `OUTCOME_UNKNOWN`, а также `REJECTED/SKIPPED/UNSUPPORTED`, когда это соответствующая стадия).

**OperationResult / RunResult** отвечает: *«Что вернуло исполнение и что получено?»* Здесь могут быть payload, validation findings, warnings, structured failures, metrics, artifact references, provenance. Даже при `SUCCEEDED` предметный результат может оказаться «изменений нет», «источник не опубликовал свежие данные» или «восстановление неопределённо».

**AnalyticalResult / WorkResult** отвечает: *«Какой смысловой ответ/продукт создан для цели?»* Он связан с поставленным вопросом, областью применимости, аналитическими основаниями и оценкой удовлетворения потребности. Работу можно корректно закончить с отрицательным, ограниченным или неизвестным ответом, если это ожидаемый и допустимый outcome поручения.

**CONSOLIDATED:** не делать одну универсальную колонку `status`, которая одновременно хранит `running`, `verified`, `approved`, `warning` и `unknown`.

### 7.2. `Assessment`, `Acceptance`, `Closure`

- **Assessment** — оценка конкретного Result/Claim относительно условий Work; может выявить расхождения, неопределённость или недостающие проверки.
- **Acceptance** — квалифицированное принятие *именно этой версии* результата для *определённого использования* и по *указанным критериям/полномочию*. Это не автоматическое свойство «тесты зелёные».
- **Closure** — решение о завершённости Work с указанием остаточных вопросов, неизвестных эффектов, обязательств, follow-up owner и reopen conditions.

У простой выгрузки accepted outcome может быть автоматическим после проверки mandatory output и явной policy; у серьёзного аналитического заключения принятие может требовать человеческого review. Не следует навязывать ручное подтверждение каждому CSV.

**Approval** при этом отличается от Acceptance: Approval разрешает запланированный эффект/действие; Acceptance оценивает уже полученное. Пользователь может одобрить запуск рискованной операции, но не принять её итог.

### 7.3. `Artifact` — устойчивый логический продукт

**Artifact** — адресуемый результат/объект, сохраняющий идентичность независимо от временной UI-карточки и места хранения. Это может быть отчёт, XLSX, ZIP, canonical data export, rendered plot, validation report или source preservation payload. Artifact должен иметь `artifact_id`, kind, origin relation, manifest (при необходимости), storage/availability/retention information. **Artifact** — не обязательно «отдельный физический файл».

**ArtifactManifest** — проверяемое описание конкретного артефакта/версии, включая content parts, hashes, format, created time, producing run/operation, source/registry snapshot refs, validation/provenance, ownership, lifecycle. **ArtifactRef** — переносимая ссылка на него. **Materialization** — конкретная физическая проекция этого артефакта в файл/папку/кэш/доступный пользователю экспорт.

Один Artifact может иметь несколько materializations; одна materialization может быть удалена без утраты семантической identity Artifact, пока сохраняются его canonical bits и разрешённый способ восстановления. **UNKNOWN:** гарантия immutable contents, CAS topology и retention policy должны быть решены в теме 03 по реальным нагрузкам.

### 7.4. `WorkspaceObject`, `Blob`, `FileStore`

**FileStore** — path-based интерфейс физических I/O операций. **Blob/Content** — содержимое с собственной content identity. **WorkspaceObject** — изменяемый рабочий файл или каталог под управлением пользователя; его path может быть именем рабочей сущности, но не заменяет immutable artifact identity. **Artifact** — логически оформленный результат с provenance и lifecycle.

```text
FileStore          ↔ physical operations / locators
Content / Blob     ↔ bytes identity
WorkspaceObject    ↔ mutable user working state
Artifact           ↔ managed stable output
ArtifactManifest   ↔ verifiable composition + lineage
Materialization    ↔ actual filesystem presentation / delivery
```

Простой user-created файл не должен автоматически считаться Artifact с полным архивным контрактом. Обратно, документ Word, полученный как проверенный итог аналитической работы, не должен терять provenance из-за переименования в проводнике.

### 7.5. `View`, `Presentation`, `ArtifactStyleSet`

**View** — преобразование семантического Result/Dataset в форму восприятия: таблица, график, summary, отчетная workbook view. **ArtifactStyleSet** — versioned presentation resource, определяющий типографику/стили артефакта. **InterfaceTheme** — оформление самого приложения. **ArtifactMetadataContext** — данные об авторе/происхождении для создаваемого файла; display author и фактический executing actor могут различаться.

Это **разные обязанности**. Пользователь не должен получать новые `Claim` или новую `Observation` только из-за переключения темы. Один и тот же AnalyticalResult можно оформить в XLSX и DOCX без изменения предметного вывода. Если presentation rounding скрывает расхождение, это дефект representation, а не изменение исходных данных.

### 7.6. `Provenance` как отношение, а не магическое поле

Provenance должна отвечать на вопросы:

1. **source lineage:** из каких SourceSnapshots и RegistrySnapshots получены данные;
2. **transformation lineage:** какие semantic operations, definitions, versions и параметры использованы;
3. **execution lineage:** каким Run/Job/OperationRun/Attempt сформирован payload;
4. **evidence lineage:** какие grounds обосновывают конкретный Claim/Result;
5. **authorship and responsibility:** кто инициировал/исполнял/проверял/принял результат;
6. **artifact lineage:** в каких объектах/версиях результат зафиксирован и представлен.

Не всё требуется хранить единым монолитным JSON. Возможны отдельные `ProvenanceManifest`, typed links и refs. Но **lossy conversion**, уничтожающее возможность ответа на существенный вопрос происхождения, запрещено.

---

## 8. Actor, User, Principal, Participant, Session, Node, Authority

### 8.1. Идентичность человека и фактического деятеля

**User** — человек/учётная пользовательская сущность. **Principal** — контекст, от имени которого проверяются полномочия: пользователь, допустимый сервисный principal, delegated principal. **Actor** — причинный участник конкретного события/действия: человек, система, автоматика, AI, внешний участник. Объекты связаны, но не тождественны:

```text
User ── associated with ─► Principal
Actor ── acts using ───────► Principal / bounded delegation
Event ── caused by ────────► Actor
```

AI-actor может составить план, предложить действие или выполнить разрешённый вызов, но его `actor_kind='ai'` само по себе **не даёт права** изменить Data root. Agent/model profile, transient cognitive activation и service principal тоже различаются.

### 8.2. `Participant`, `Role`, `Assignment`

**Participant** — Actor, вовлечённый в определённую Work/Thread/Session. **Role** — scope-bound функция в контексте этой работы: владелец, исполнитель, reviewer, наблюдатель. **Assignment** — поручение/ответственность с адресатом, предметом, due/review policy и own status. Assignment может ссылаться на Work/Result/Artifact, но сама по себе не является Job и не должна автоматически создавать исполнение без соответствующего permission/admission flow.

### 8.3. `AuthorityGrant`, `Approval`, `AccessPolicy`

**AuthorityGrant** — ограниченное, проверяемое право на действие/ресурс/временной интервал. **AccessPolicy** — управляющее правило для principal, ресурса и effect. **Approval** — подтверждение конкретного предложенного эффекта/плана с version, expected revision, requester, approver и scope.

Три решения должны быть различимы:

- *Can system technically perform?* — capability + availability.
- *May this actor cause it?* — authorization/approval.
- *Did it happen?* — actual effect receipt/observation.

Отдельно `Assessment/Acceptance` относится к удовлетворительности результата, а не к разрешению.

### 8.4. `Session`, `Node`, `Host`

**Session** — ограниченная во времени связь/контекст участника и доступной поверхности. **Node** — управляемая среда продукта со стабильной platform identity, состоянием, доступными ресурсами и readiness. **Host** — физический/виртуальный носитель runtime/execution. Один Node может иметь несколько Sessions и несколько Surfaces; одно устройство может обслуживать разные среды согласно внешним контрактам. Не следует молча отождествлять machine ID, node ID, user ID, process ID и principal ID.

**Boundary:** AppDock задаёт platform/node/activation lifecycle и свои доступы; Strategy Box использует эти identity в своих scoped grants/Work/Jobs, но не переносит предметный scheduler или аналитические contracts во внешнюю оболочку. Детальная федерация полномочий и remote security — темы 05/08.

### 8.5. `Presence`, `ReadCursor`, `Notification`

**Presence** — временная, подверженная устареванию проекция активности participant/session. Это не долговечное подтверждение авторства и не право доступа. **ReadCursor** — личное состояние прочтения списка/Thread относительно event sequence; общий `unread: bool` в Work/Case является некорректным при нескольких пользователях. **Notification** — событие доставки внимания конкретному адресату/каналу с delivery policy; оно не заменяет предметное событие и не делает его источником истины.

### 8.6. `Problem` и `Diagnostic`

**Diagnostic** — структурированное наблюдение о сбое/предупреждении. **Problem** — устойчивый адресуемый случай, требующий операционной реакции/наблюдения. **LogRecord** — физическое evidence, поддерживающее диагностику. AppDock владеет платформенными/node-level problems и aggregation boundary; Strategy Box — domain/run-level diagnostics и controlled user-facing projection. Ошибки одного пользователя не должны автоматически транслироваться другим в виде raw tracebacks или утечки чужих данных.

---

## 9. Automation, Trigger, Background, Scheme Activation

### 9.1. `AutomationSpec` ≠ `Job`

**AutomationSpec** — сохраняемое правило *когда и при каких условиях инициировать работу*, от чьего имени, с каким target и параметрами. Оно переживает десятки Jobs и не содержит `status=running` как собственную state truth.

**TriggerSpec** — определение условия (`once`, `interval`, `calendar`, `source_change`, `event`, `dependency` и т. п.); **TriggerOccurrence** — конкретное обнаруженное наступление условия; **AutomationExecutionPolicy** определяет schedule/coalescing/misfire/approval/resource режим. Срабатывание может породить `WorkCandidate`, новую Work либо Run существующей Work — **по явному binding policy**, а не по тому, виден ли сейчас чат.

### 9.2. `Background` — execution mode

Фоновый режим означает, что исполнение может продолжаться при отсутствии активного интерактивного клиента. Он **не является** самостоятельным `ScenarioKind` или отдельной архитектурой операций. Аналогично remote/local, user-/AI-triggered — свойства context/activation/backend, ортогональные предметному назначению Scenario.

**Фоновый процесс** как scheduler/listener/worker OS-service отличается от **фоновой задачи** как user-visible Job. У работающего scheduler могут вообще отсутствовать активные пользовательские Jobs; запущенная вручную задача может исполняться в фоне без AutomationSpec.

### 9.3. `ConditionWatcher` и `LongRunningListener`

**ConditionWatcher** — механизм, периодически проверяющий лёгкое условие и создающий Work/Run только при изменении/подтверждении, согласно policy. **LongRunningListener** — служебный процесс/подписчик, который может инициировать много occurrences. Ни один не превращается в бесконечную Work автоматически.

### 9.4. Когнитивная активация и машинный исполнитель

Если внешний когнитивный участник исполняет отдельный reasoning/proposal цикл, **CognitiveActivation** может иметь отдельный transient/durable ID, resource scope и provenance. Но это **не** новая параллельная система выполнения банковских операций: её предложения превращаются в обычные capability invocations через authorization/planning, а эффекты исполняет Strategy Box execution spine. Не требуются отдельные типы `AIOperation`, `AIScenario`, `AIJob`.

**UNKNOWN:** точные границы persistence transient cognitive state и связи activation ↔ Run/Job требуют pilot. Они не должны искусственно раздувать первый schema contract.

---

## 10. Конфигурация, расширения и поверхности

### 10.1. Пять состояний, которым тесно в одном `Settings`

- **UserSettings** — долговечные пользовательские предпочтения (тема, ограниченный акцент, разумные defaults артефактов).
- **SurfaceState** — геометрия/текущая навигация/фильтр/selected item; восстанавливается автоматически.
- **DraftState/RecentState** — введённые, но не submitted параметры, последние обращения, незавершённый ввод.
- **RunParameters / ParameterSnapshot** — фактически разрешённая immutable конфигурация конкретного Run; меняется новая invocation, а не ретроактивная история.
- **ManagedPolicy** — права, ограничения и обязательная конфигурация среды от соответствующего owner; не переопределяется пользователем в Preferences.

`Workspace` (рабочая область данных) тоже самостоятельный предметный/файловый контекст, а не «галочка» настроек. `RuntimeBinding` выбирает Data root/Node/Session на старте; может быть объявленным внешней платформой и применяемым по policy.

### 10.2. `Plugin`, `Provider`, `Extension`, `StyleProvider`

**PluginDescriptor**: версия пакета/API, declared capabilities, dependencies, health, compatibility, allowed configuration schema. **Provider**: одна или несколько реализаций конкретных нейтральных interfaces. **ProviderBinding**: выбранный и разрешённый в данной среде provider для capability slot. **StyleProvider**: источник декларативных style resources для артефактов; это не право произвольно модифицировать shell UI.

Различать lifecycle:

```text
installed → discovered → validated → activated → bound → usable
                                                 ↘ denied / unavailable
```

Конкретная последовательность может иметь промежуточные/откатные состояния и policy gates. Реальное управление установкой остаётся в environment/AppDock, а product UI показывает status и разрешённые настройки. Никаких конкретных закрытых типов интеграций/путей/провайдеров в публичный словарь не требуется.

### 10.3. `Surface` и `ViewModel`

**Surface** — платформа взаимодействия (Windows desktop, будущие Web/Android) и её capability profile, но не semantic owner Work, Dataset, Job или Auth. **ViewModel/Projection** — представление общих objects для конкретного устройства/контекста. `CaseView`, `JobCard`, `ArtifactCard`, `ThreadTimeline`, `TaskCenter` — производные projections, а не отдельные authoritative business objects.

Одно semantic событие может порождать уведомление, карточку в чате, запись в центре задач и статус узла. При этом у события/Work/Job остаётся единая identity.

---

## 11. Концептуальная «карта отношений» Strategy Box

```text
  Publisher/Authority ──publishes──► SourceDescriptor
                                       │ captured as
                                       ▼
                                 SourceSnapshot
                                       │ interpreted with
               RegistrySnapshot ───────┤────► MeasureDefinition
                                       ▼
                            Observation / Dataset
                                       │ evaluated/derived into
                                       ▼
                         Claim + Evidence / Basis
                                       │ contributes to
                                       ▼
                                AnalyticalResult
                                       │ realized as
                                       ▼
                             Artifact + Manifest

  CapabilityDefinition ──specialized into──► OperationDefinition
               │                                │
               └────────► SchemeDefinition ◄────┘
                                   │ supports
                              ScenarioDefinition
                                   │ selected by
  Thread ◄──context link──► Work ──► Run
    │                     │           │
  Message              Acceptance  ActivationBinding
    │                     │           │
    └─may propose Work     Closure    ExecutionPlan
                                       │
                                       ▼
                                      Job
                                       │
                                   OperationRun
                                       │
                                     Attempt
                                       │
                     ExecutionOutcome / Receipts / Logs
                                       │
                           Results / Evidence / Artifacts

  User/Actor ──using──► Principal ──authorized by──► Grant/Policy
  Node ──hosts──► Session / ExecutionBackend / Work state authority
  AutomationSpec ──on TriggerOccurrence──► WorkCandidate/Run
  Surface ──projects──► Thread/Work/Job/Artifact/Problem
  ProviderBinding ──implements──► Capability at execution boundary
```

На рисунке многие стрелки — краткая визуализация **отношений с собственной policy/версией/контекстом**. Например `SourceSnapshot → Observation` подразумевает parser/schema/method; `Claim → Result` подразумевает оценку оснований; `User → Principal` не означает безусловный доступ. Это **логическая схема**, не утверждение о текущем состоянии классов или SQL-таблиц.

---
## 12. Consolidation Conflict Register: что именно согласовано

Матрица учитывает хронологию и текущий owner, но ни одно исследование не побеждает другое автоматически за счёт поздней даты.

| ID | Коллизия | Происхождение | Решение темы 02 | Статус и дальнейшая проверка |
|---|---|---|---|---|
| S01 | `Command` — канонический атом или `Operation`? | Commands/Cascades vs Machine Schemes/Portability/Core | `Operation` — machine/domain use case; `Command` — только локальная техническая primitive при доказанном consumer | **CONSOLIDATED** naming; низкоуровневый command ABI **OPEN** |
| S02 | `Scenario` создаётся на каждую `Operation`? | CURRENT Windows и ранний Scenario-first UX | Только курируемые user-meaningful scenarios; direct invocation Operation допустим для машинного/опытного пользователя согласно policy | **SUPERSEDED** automatic wrapping as target |
| S03 | `Scenario.kind=atomic/composite/background/assignment`? | CURRENT Windows | граф композиции, режим execution, automation trigger и assignment — разные оси | **SUPERSEDED** current kind taxonomy |
| S04 | `Cascade` и `Machine Scheme` одно? | Commands/Cascades vs Machine schemes | Scheme — typed machine composition; Cascade — вид крупного user workflow. Отдельная canonical CascadeDefinition только при самостоятельном contract/governance | **TARGET-HYPOTHESIS**; нужен pilot с вложенными scenarios |
| S05 | `Scenario` = `Scheme`? | Scenario-first UX vs machine-readiness | Product/use-case definition ≠ reusable computational composition; возможна связь один-ко-многим | **CONSOLIDATED** distinction; serialization **OPEN** |
| S06 | `Case` — пользовательская цель или отдельный запуск? | CURRENT `ScenarioRunCase`, observability, background, Work-oriented studies | Разложить на `Work`, `Run`, optional `CaseView`; не делать Case третьим обязательным aggregate | **TARGET-HYPOTHESIS high confidence** |
| S07 | `Run` — один Job или полный этап Work? | Background/observability vs later Work decomposition | `Run` = concrete trajectory Work; `Job` = schedulable unit; `OperationRun` = one canonical invocation; `Attempt` = physical execution try | **TARGET-HYPOTHESIS high confidence**; validate cardinality |
| S08 | `Thread` является контейнером Work? | Scenario chat vs chat/work research | Thread — interaction context с refs к Work; независимые lifecycle и persistence | **CONSOLIDATED** |
| S09 | AI memory и chat history — Work state? | Early AI vs later Work research | Memory/context — separate bounded projections; Work/Run state отдельна | **SUPERSEDED** conflation |
| S10 | `Result` и `Artifact` равны? | current path-oriented outputs vs artifact/epistemic studies | Result = qualified semantic answer/outcome; Artifact = durable addressable output | **CONSOLIDATED** |
| S11 | `Succeeded` означает `Accepted`? | Current operation status vs epistemic/Work | Execution outcome, Work assessment, acceptance и closure отличаются | **CONSOLIDATED** |
| S12 | `FileStore` становится ArtifactCatalog? | Current physical IO vs artifact layer | FileStore — lower storage access; Artifact identity/lifecycle выше | **CONSOLIDATED**; immediate CAS **UNKNOWN** |
| S13 | `SourceSnapshot` можно считать канонической Observation? | Core data pipelines vs epistemic research | Snapshot — зафиксированная публикация; Observation — semantic measurement with context | **CONSOLIDATED** |
| S14 | Dataset и DataFrame — одно? | Python-native current APIs vs machine capability contracts | DataFrame — in-memory representation; Dataset — semantic/versioned collection при materiality | **CONSOLIDATED** |
| S15 | Reference registry, source catalog, domain rules — один реестр? | `stratbox.registries`, collector, forms/FRG/SORS | Разные classes по смыслу; общие governance rules | **CONSOLIDATED** |
| S16 | Опубликованное число = фактическая величина? | Simple reporting vs SORS evidence semantics | Published representative, latent quantity, reconstructed estimate имеют разные epistemic statuses | **CONSOLIDATED** |
| S17 | Platform session/Node = product User/Work? | AppDock activation vs Windows context | Node/Session как context/external boundary, Work/Jobs как product semantics | **CONSOLIDATED** |
| S18 | AppDock владеет предметным scheduler? | Раннее automation исследование vs background/web | AppDock — platform/service lifecycle; Strategy Box — product triggers/automations/execution | **SUPERSEDED** early owner assignment |
| S19 | Plugin installed автоматически активен? | Current extension seams vs generic extension research | Discovery, validation, activation, binding и authorization строго раздельны | **CONSOLIDATED** |
| S20 | Настройки = сохранённое состояние? | CURRENT user config vs settings research | Preferences, surface state, drafts, policy, immutable run params различаются | **CONSOLIDATED** |
| S21 | Публичная библиотека должна знать environment implementation? | Ранние интеграционные shortcuts vs публичная граница | Только нейтральные contracts, capability namespace, discovery/binding; private details outside public | **CONSOLIDATED / boundary invariant** |
| S22 | Отдельные хранилища/движки для Windows, web, AI и background? | Current GUI-oriented execution vs system studies | Один semantic execution spine; разные adapters/backends/projections | **CONSOLIDATED** |

### 12.1. Настоящий конфликт против различий уровней

**Не являются настоящим конфликтом:** `OperationDefinition` против `OperationRun`, `SourceDescriptor` против `SourceSnapshot`, `Widget` против `ViewModel`, `SQLite` против `PostgreSQL` (это варианты physical deployment), `FileStore` против `ArtifactStore` (разные уровни). В таких случаях надо **разнести объекты по типам/отношениям**, а не выбирать одно имя победителем.

**Остаются настоящими design choices:** отдельность CascadeDefinition; состав `Work` admission; точная cardinality Run/Job; степень материализации Claim/Evidence; необходимость самостоятельного DatasetSnapshot/Release; единая минимальная schema событий/исходов. Эти вопросы нельзя закрыть простым переименованием.

### 12.2. Устаревшие решения, которые не следует реанимировать

1. `Case` = chat message + user goal + one execution + history + artifact container.
2. `Scenario` как автоматическая обёртка каждой технической функции.
3. `background` как отдельный тип сценария, а не execution mode.
4. `AIOperation` как самостоятельная параллельная архитектура исполнения.
5. Qt-процесс и локальные JSON как durable node-wide Work/Job authority.
6. «Успешно скачали файл» как достаточное доказательство корректного dataset/claim.
7. Перезапись одного и того же файла как versioning стратегии.
8. `latest mtime` как гарантия свежести registry.
9. `str(exception)` или лог в качестве единственной typed failure.
10. «Установленное расширение = разрешённая способность».
11. Автоматическое создание репозитория для каждого нового семантического имени.

Исторические материалы сохраняют provenance, но **не сохраняют нормативную силу** для целевого продукта.

---

## 13. Семантические правила идентичности, времени и ссылок

### 13.1. Шесть классов ID

| Класс | Пример | Что идентифицирует | Что запрещено использовать вместо ID |
|---|---|---|---|
| Definition identity | `operation_id`, `scheme_id`, `source_id`, `measure_id` | долговечный смысловой тип/серия | Python import path, display name |
| Definition version | `operation_contract_version`, `scheme_version`, `registry_revision` | редакцию объявления/правил | package version как единственную версию смысла |
| State/snapshot identity | `snapshot_id`, `dataset_snapshot_id`, `plan_digest` | конкретно зафиксированное состояние | `latest`, mtime, отчётный период сам по себе |
| Work identity | `thread_id`, `work_id`, `automation_id` | долговечные пользовательские/управляющие объекты | UI card ID, chat position |
| Execution identity | `run_id`, `job_id`, `operation_run_id`, `attempt_id` | разные уровни конкретного исполнения | `operation_id`, thread ID, process PID |
| Product/output identity | `result_ref`, `claim_id` при наличии, `artifact_id`, `effect_receipt_id` | установленный итог, тезис, артефакт или эффект | path, текст лога, filename |

**Важно:** UUID, ULID, hash и composite natural key — выбор физического механизма. Semantic identity определяется смыслом и lifecycle, а не конкретным форматом генератора. Хэш нужен для content integrity, но **не** заменяет logical ID: разные бизнес-артефакты могут иметь одинаковое содержимое, сохраняя разных авторов, Work lineage и access policy.

### 13.2. Версии и revisions — разные понятия

- **Semantic contract version** говорит, изменилось ли значение операции/показателя/scheme.
- **Implementation revision** говорит, какой код реализовал тот же смысл.
- **Data/registry snapshot version** фиксирует исходные данные/классификаторы.
- **Object revision** служит optimistic concurrency при изменении долговечной Work/Automation/Thread.
- **Plan digest** фиксирует конкретное разрешённое исполнение.
- **Artifact content digest** подтверждает байты.

Версии разных классов не следует сводить в одно поле `version: "0.8.0"`.

### 13.3. Временные координаты

Минимальное различие:

| Контекст | Время |
|---|---|
| Источник | reported/effective period, original publication time, retrieval time |
| Регистры | effective interval, published/revised time |
| Work | commissioned, admitted, revised, closed, reopened |
| Run/Job | submitted, queued, started, terminal, reconciled |
| Claim/Result | as-of, assessed/accepted, revalidated, superseded |
| Artifact | created, committed, materialized, retained, deleted |
| Session/Presence | connected, last seen, expires |

DST/timezone относятся к TriggerSchedule, а не ко всем датам хранилища одинаково. Человеческое расписание требует time-zone identity; machine timestamps предпочтительно фиксировать как offset-aware/UTC.

### 13.4. Mutable revision и immutable snapshot

Следует избегать ложного требования «всё иммутабельно». `Work`, `Thread`, AutomationSpec и пользовательские preferences закономерно изменяются, сохраняя identity и revision history. `SourceSnapshot`, resolved Run parameters/ExecutionPlan и committed artifact version должны оставаться стабильными как основание воспроизводимости. Новый вход/контракт/публикация создаёт новый snapshot/plan/artifact version, а не переписывает доказательную историю.

### 13.5. Provenance минимального результата

```yaml
# Пример TARGET-семантики, а не существующий API
result_ref: result:...
subject_ref: bank:...
measure_ref: measure:...
period: 2026-H1
scope: IFRS-group
source_snapshot_refs: [source-snapshot:...]
registry_snapshot_refs: [registry-snapshot:...]
transformation_refs: [operation-definition:...]
run_ref: run:...
claims: [claim:...]
evidence_refs: [evidence:...]
qualification:
  currentness: evaluated-as-of-...
  uncertainty: declared
  limitations: []
artifact_refs: [artifact:...]
```

Это пример *обязательных смысловых различий*; он не делает обязательными именно такие строковые префиксы, имена полей или YAML как wire format.

---

## 14. Минимальный набор candidate contracts (не готовая реализация)

Программа третьей ветки запрещает преждевременную физическую архитектуру. Поэтому здесь показаны **семантические ядра** возможных контрактов, а не библиотека классов для прямого копирования.

### 14.1. Базовые семейства

| Семейство | Стабильная identity | Обязательное смысловое ядро | Что остаётся optional/profile-specific |
|---|---|---|---|
| SourceDescriptor | source_id | authority, source semantics, acquisition/discovery rule | aliases/tags/cadence detail |
| SourceSnapshot | snapshot_id | source_ref, content identity, acquisition provenance, period/publication distinction | Release object, multiple materializations |
| RegistrySnapshot | registry_snapshot_id | registry ref, authority/version/effective validity, hash | distributed history |
| MeasureDefinition | measure_id+version | meaning, units, perimeter, temporal semantics | complex ontology/crosswalk graph |
| Observation | observation key/ref | subject, measure, period, value/missingness, source & method | individual durable row ID |
| Dataset | dataset_id/version | declared data schema, scope, references | separate data catalog/search index |
| Claim | claim_id where durable | text/structured proposition, scope, qualification, grounds | independent persistence for every claim |
| OperationDefinition | operation_id+contract version | semantic inputs/outputs, effects, applicability, failures | optimized backends |
| SchemeDefinition | scheme_id+version | reusable typed composition, guards, policies, outcome | complex DSL, dynamic planning |
| ScenarioDefinition | scenario_id+version | product use case, parameter profile, expected outcome, scheme/operation binding | curated catalog UI tags |
| Work | work_id | purpose, scope, requirements, authority, state, result/closure refs | collaborative branching/forks |
| Run | run_id | work_ref, resolved context/plan ref, lifecycle, outcomes | full cognitive activation metadata |
| Job | job_id | run_ref, scheduler ownership/state, resources, effect boundary | distributed execution transport |
| OperationRun | operation_run_id | definition+version, invocation, input/output/failure refs | detailed step graph |
| Attempt | attempt_id | logical parent, backend, timestamps, observed outcome | low-level process diagnostics |
| Artifact | artifact_id/version | kind, producer, contents/ref, provenance, lifecycle | CAS/multi-location registry |
| AutomationSpec | automation_id+revision | target, trigger, run-as, policy, enabled | complex calendars/condition graphs |
| Principal/Grant | principal_id/grant_ref | actor/scope/action/resources/constraints | federation protocols |
| PluginDescriptor | plugin_id+plugin version | declared capabilities, API compatibility, configuration schema | user-facing management UI |
| ProviderBinding | binding_id/revision | capability slot, chosen provider, activation/policy validity | hot reload |

### 14.2. Typed Result Envelope — три независимых оси

```yaml
# CONCEPTUAL ONLY
execution:
  lifecycle: TERMINAL
  outcome: SUCCEEDED        # independent of epistemic success
semantic:
  result_kind: analytical
  qualification:
    applicability: applicable
    support: qualified
    currentness: current-as-of-snapshot
  result_ref: result:...
operational:
  diagnostics: []
  problem_refs: []
  effect_receipts: []
  artifact_refs: []
  provenance_ref: provenance:...
```

Здесь `execution.outcome=SUCCEEDED` утверждает только, что обязательный execution contract выполнен. Это не эквивалентно `semantic.support=proved`, `work.accepted=true` или `decision.authorized=true`.

### 14.3. Нормализованная модель Work/Run/Job

```yaml
# CONCEPTUAL ONLY
work:
  work_id: work:W1
  purpose: "Сравнить показатели двух банков"
  requirements_ref: requirements:R1
  scope_ref: scope:S1
  state: awaiting_review
  run_refs: [run:R1, run:R2]
  result_refs: [result:A1]
run:
  run_id: run:R2
  work_ref: work:W1
  activation_binding_ref: binding:B2
  plan_ref: plan:P2
  job_refs: [job:J2]
  outcome: succeeded
job:
  job_id: job:J2
  run_ref: run:R2
  operation_run_refs: [operation-run:O21, operation-run:O22]
  state: terminal
  outcome: succeeded
operation_run:
  operation_run_id: operation-run:O22
  operation_definition_ref: operation:compare@1
  attempt_refs: [attempt:T221, attempt:T222]
```

Модель оставляет Work `awaiting_review` при успешном Run. Это не ошибка: удовлетворение Commission ещё требует review/acceptance.

### 14.4. Outcome и assurance — пространства имён, а не один enum

| Пространство | Возможные значения | Владелец значения |
|---|---|---|
| Work lifecycle | candidate, active, awaiting_input/review, completed, closed, reopened | Work authority |
| Job lifecycle | queued, waiting_resource/approval, running, finalizing, terminal, reconciling | execution owner |
| Execution terminal | succeeded, partial, failed, cancelled, outcome_unknown | runtime verification |
| Applicability | applicable, not_applicable, unknown | capability resolver |
| Support state | supported, contested, insufficient, unknown | evidence/evaluation |
| Source validity | validated, rejected, pending, unverified | source validation |
| Currentness | as_of, stale, unknown, not_applicable | data/revalidation owner |
| Approval | requested, granted, denied, expired, revoked | authority owner |
| Acceptance | pending, accepted, rejected, conditionally_accepted | result consumer/criteria |
| Presence | online, idle, unavailable, unknown | ephemeral session projection |

Это иллюстративные словари, не утверждённые wire enums. **Invariant:** `OUTCOME_UNKNOWN` в execution относится к неизвестному внешнему эффекту/финалу; `UNKNOWN` у Claim — к недостаточности оснований. Система не должна смешивать их из-за общего слова.

---
## 15. Validation: проверяем онтологию на трудных сценариях

Семантическая модель полезна, только если она даёт единственные непротиворечивые ответы на реальные кейсы. Ниже — **acceptance probes** для будущих исследований 03–08 и vertical slices.

### V01. Публикация ЦБ пересмотрена задним числом

**Дано:** исходный XLSX по периоду P скачан в понедельник, а во вторник официальный источник заменил содержимое за тот же P.

**Ожидаем:** один `SourceDescriptor`, два `SourceSnapshot` (в зависимости от содержимого); тот же `MeasureDefinition`, potentially new Observations/DatasetSnapshot; Results/Claims старого Run сохраняют прежний input provenance и получают новую оценку currentness при переиспользовании. Имя файла и период P не заменяют snapshot ID. Новый export не стирает прошлый Artifact.

**Fail condition:** система незаметно пересчитывает прежнюю Work на новых байтах, оставляя старый `run_id` и прежний manifest.

### V02. Две формы с одинаковым названием показателя

**Дано:** «средства клиентов» в РСБУ standalone и МСФО группы имеют сходное русское имя.

**Ожидаем:** разные `MeasureDefinition/perimeter` или явно квалифицированный comparison bridge. Одинаковый label сам по себе не поддерживает сопоставимость. AnalyticalResult включает условия сравнения.

**Fail condition:** обе серии автоматически объединены только по названию столбца.

### V03. SORS восстанавливает неопубликованную величину

**Дано:** метод доказательной реконструкции выводит значение через ограничения официальной публикации и округления.

**Ожидаем:** `SourceSnapshot` исходного наблюдения, различие published integer / latent quantity / derived result, evidence tier/assumption profile, provenance и output qualification. Reconstruction не переписывает исходный reported fact.

**Fail condition:** реконструированная величина маркируется как непосредственно опубликованная.

### V04. Успешно создан XLSX, но ответ неверен

**Дано:** Job завершил экспорт без ошибок I/O, однако аналитический review обнаружил ошибку в формуле.

**Ожидаем:** `Job.ExecutionOutcome=SUCCEEDED` как факт выполнения прежнего контракта, отдельная domain validation/assessment failure и `Work.Acceptance=REJECTED` или Work reopened; Artifact получает исправленную новую версию, старый не стирается из provenance.

**Fail condition:** система объявляет поручение выполненным и принятым только потому, что файл существует.

### V05. Внешний destructive effect после timeout неизвестен

**Дано:** операция переместила или удалила объект на удалённой стороне; ответ о завершении потерян.

**Ожидаем:** Attempt/Job `OUTCOME_UNKNOWN` до reconciliation, EffectReceipt только для подтверждённых изменений, запрет blind retry, Work остаётся awaiting resolution. Состояние Thread/карточки не выводит ошибочно `FAILED` или `CANCELLED`.

**Fail condition:** повторный запуск случайно повторяет необратимый эффект.

### V06. Несколько пользователей работают с одним узлом

**Дано:** A запустил Job, B наблюдает его, C открывает связанный Artifact, у всех собственные настройки интерфейса.

**Ожидаем:** один `node_id`, единые `work_id/run_id/job_id`, несколько Sessions/Principals/ReadCursors, permission-scoped projections и отдельный доступ к самому Artifact. Presence B не даёт B право отмены.

**Fail condition:** каждый UI локально создаёт новую «истину Job» либо shared unread-флаг перезаписывает персональные состояния.

### V07. Автоматизация запускается ежедневно

**Дано:** расписание каждый день проверяет наличие публикации.

**Ожидаем:** одна `AutomationSpec` и множество `TriggerOccurrence`. Пустая проверка может закончиться `NO_CHANGE` без создания большого пользовательского Work; существенное изменение может создать новую Work либо Run по заданной policy. Каждая реальная Job имеет собственную identity и наблюдаемость.

**Fail condition:** `AutomationSpec.status=running` используется как запись всех ежедневных запусков.

### V08. Один расчёт запускают Windows и AI

**Дано:** пользователь выбирает Scenario, а позже внешний когнитивный участник предлагает ту же каноническую Operation.

**Ожидаем:** одинаковый `OperationDefinition`, те же input/effect/authorization contracts; отличаются origin actor, admission, plan и Run IDs, но не предметный алгоритм. Доступ AI ограничен разрешёнными capability scopes.

**Fail condition:** существуют два независимых `AI operation runner` и `GUI runner` с различными бизнес-результатами/ошибками.

### V09. Один файл отображает два анализа

**Дано:** XLSX содержит два листа, полученных разными Results/срезами данных, затем скопирован пользователем.

**Ожидаем:** ArtifactManifest знает части/lineage, materialization path не является ключом семантических claims. Копирование файла может создать новую materialization либо новый unmanaged workspace object без изменения исходного Result.

**Fail condition:** любой новый путь автоматически трактуется как отдельный независимый analytical result.

### V10. Расписание отключили во время работы

**Дано:** пользователь выключает AutomationSpec в момент `Job.RUNNING`.

**Ожидаем:** прекращаются новые TriggerOccurrences/submit по policy; уже запущенный Job завершается или отдельно получает корректный cancellation request. Work/Run history не удаляется.

**Fail condition:** `enabled=false` автоматически меняет Job outcome на `cancelled`.

### V11. В UI изменён акцент и выбран другой стиль артефакта

**Дано:** пользователь переключает тему приложения, затем запускает отчёт с другим ArtifactStyleSet.

**Ожидаем:** данные/Claim/Result и SourceSnapshot остаются прежними, меняется только rendered representation/artifact style provenance; оформление shell и форматирование документов управляются разными contracts.

**Fail condition:** изменение темы заменяет semantic operation config или стирает author/evidence metadata.

### V12. План одобрен, но перед выполнением изменились исходные данные

**Дано:** destructive cleanup plan был создан и одобрен для revision R, к моменту применения часть источников изменилась.

**Ожидаем:** `Approval` связан с конкретным plan digest и effect scope; revalidation перед apply возвращает STALE/CONFLICT и требует нового plan/approval. Старое разрешение не распространяется автоматически на новый список файлов.

**Fail condition:** одобрение «операции вообще» используется для любых будущих эффектов.

### V13. «Неизвестный результат» и «отрицательный результат»

**Дано:** исследование не нашло опубликованных данных после корректной проверки источников.

**Ожидаем:** фактический Run может быть `SUCCEEDED`; Result = «подтверждённых наблюдений не найдено в обследованном наборе источников на дату» с limitations, а не ложное утверждение «показатель равен нулю». Work может быть закрыта с qualified negative result, если Commission это допускает.

### V14. Одна Work обсуждается в двух чатах

**Дано:** результаты общей Work обсуждаются аналитиком и reviewer в двух Thread, при этом доступы различаются.

**Ожидаем:** Work имеет один `work_id`, два разрешённых thread-context links; каждый Thread получает permission-filtered projection, но нет двух отдельных Work states. Удаление Thread не удаляет результат/Work.

### V15. Операция оптимизирована, но её смысловая версия прежняя

**Дано:** вместо многошаговой Scheme используется оптимизированная реализация с тем же semantic contract.

**Ожидаем:** совпадение Operation/Scheme meaning доказано conformance evidence, меняется implementation binding/revision, plan digest и provenance. Если область допустимости сузилась, CapabilityEnvelope это раскрывает. Иначе нельзя подменять связывание молча.

---

## 16. Семантические ownership boundaries

### 16.1. Responsibility → owner, затем возможный physical carrier

| Смысловая ответственность | Логический owner | CURRENT carrier / target hypothesis | Граница |
|---|---|---|---|
| Источники, показатели, наблюдения, доменные данные | `stratbox` domain core | текущий `stratbox` | без knowledge о Windows/Node UI |
| Бизнес-операции/их смысловые контракты | `stratbox` domain core | current domain packages; будущий curated Operation catalog | surface не переопределяет экономический смысл |
| Work, Thread, Scenario catalog, Runs/Jobs, application policy | Strategy Box application semantics | текущие фрагменты в Windows; целевой platform-neutral owner | без Qt-only state authority |
| Planner, scheduler, durable execution, worker dispatch | Strategy Box execution runtime | целевой headless runtime/host, физическое имя не определено | внешний AppDock управляет процессом/узлом, а не предметным workflow |
| Artifacts и их metadata/lineage | совместный контракт domain producer + application storage/catalog | current path-oriented Windows output, будущая единая interface boundary | FileStore остаётся физической нижней абстракцией |
| Пользовательские темы и native UI rendering | surface/design responsibility | Windows Qt сегодня, будущие adapters | UI токены не изменяют domain facts |
| Installation, Node lifecycle, activation, host platform health | AppDock | внешний владелец | Strategy Box использует published contracts |
| Generic extension discovery/binding | `stratbox`/application по классу capability, с platform policy на границе | действующие частичные seams; target versioned contract | никаких раскрытий private implementations в public owners |
| External reasoning/AI participation | внешний cognitive consumer + Strategy Box admission/authority | целевая интеграция | аналитическая истина и эффекты остаются у Strategy Box |

**Существенное уточнение:** названия вроде `stratbox-core`, `stratbox-host`, `stratbox-design` в исследованиях **не являются утверждёнными физическими пакетами/репозиториями**. Логическая ответственность application/execution/design подтверждена сильнее, чем выбор отдельного Git repository. Эту развилку должна закрывать тема 01/09 на основании независимого жизненного цикла/потребителей, а не изображения дерева каталогов.

### 16.2. Семантический контракт между owners

- `stratbox` возвращает typed domain values/results/diagnostics/provenance, не меняя состояние UI.
- Application выбирает/admit Work, разрешает capabilities и параметры, создаёт Run/Plan, управляет Jobs и правами.
- Execution backend производит факты выполнения/receipts, но сам не принимает аналитический Claim и не закрывает Work без соответствующей policy.
- Artifact layer фиксирует и доставляет outputs, не меняя смысл результата.
- Surfaces проецируют state и собирают intent, не создавая локальные конкурирующие durable truths.
- AppDock provides node and environment guarantees through external contracts; внутреннее устройство платформы не является частью Strategy Box ontology.

### 16.3. Структура API — НЕ следствие терминологии

Наличие сущности `Work` **не доказывает**, что нужен `work_service.py` в новом repository, SQL-таблица `works` и API `/works` уже в первой реализации. Сначала фиксируются purpose, references, authority и lifecycle; затем строится один small vertical slice; затем выбираются таблицы/классы/пакеты. То же относится к `Claim`, `Evidence`, `Scheme` и `ArtifactCatalog`.

---

## 17. Provenance ledger: откуда взяты существенные выводы

Вместо копирования десятков документов дана адресуемая карта источников по конкретным semantic clusters. Весь каталог `02-base-study` насчитывает **27 исследований на момент темы 00**. Здесь они использованы с различными ролями: baseline, прямое обоснование терминов, cross-check и контрпримеры. Исторический слой не служит доказательством актуального поведения.

В ссылках ниже префикс `R02/` означает каталог [`02-base-study`](https://github.com/ForestTiger-GH/stratbox/tree/main/_mw/epochs-001-strategy-box-development/research/02-base-study).

### 17.1. Прямые семантические источники (основная evidence chain)

| Код | Источник | Использование в теме 02 |
|---|---|---|
| B01 | [stratbox base current-state (06.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_base_study_current_state_2026-10-06.md) | CURRENT core: domains, typed contracts, source/registry, SORS provenance, operation maturity |
| B02 | [stratbox-windows current-state (06.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md) | CURRENT `OperationSpec/ScenarioSpec/ScenarioRunCase`, Event/Artifact/Log, Qt/state limits |
| B03 | [commands, scenarios, cascades (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md) | ранняя трёхуровневая модель и конкретные противоположные трактовки Command/Cascade |
| B04 | [execution control/user path (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_execution_control_user_path_research_2026-10-07.md) | invocation, resolved parameter snapshot, cancellation, Case/Job separation |
| B05 | [business logic and machine schemes (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_logic_machine_schemes_architecture_research_2026-10-07.md) | semantic operation vs mechanism; Scheme vs plan; validity/effects/envelope |
| B06 | [business segments portability/reuse (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_segments_portability_reuse_architecture_research_2026-10-07.md) | Mechanism/Building Block/Domain Service/Operation threshold, neutral execution context |
| B07 | [PROTOS business-code readiness (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md) | Definition, ActivationBinding, Plan, Run, CapabilityEnvelope, authority/admission; external machine projection only |
| B08 | [PROTOS chat/work/schemes UI (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_chat_work_schemes_ui_research_2026-10-07.md) | Thread, Work, Run, CognitiveActivation, Case decomposition, many-to-many interaction |
| B09 | [PROTOS foundation (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_foundation_research_2026-10-07.md) | Work admission, durable truth, effect authority, memory/interaction separation; ранняя Case близость уточнена |
| B10 | [target semantic decomposition (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md) | Work/Run/Job/OperationRun/Attempt, Acceptance/Closure, authority/effects, responsibility-before-physical-boundary |
| B11 | [target epistemic architecture (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md) | Source/Observation/Measure/Claim/Evidence/Result/currentness/reliance distinctions; method-level ideas, без описания внешней методологической структуры |
| B12 | [background jobs and processes (08.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md) | Automation/Trigger/Job semantics, фон как execution mode; ранний Case-centric vocabulary уточнён Work model |

### 17.2. Данные, артефакты, многопользовательская работа и внешние контракты

| Код | Источник | Использование |
|---|---|---|
| B13 | [file and artifact layer (06.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md) | FileStore vs Workspace/Blob/Artifact/Manifest/Catalog/SourceSnapshot |
| B14 | [FileStore/file formats (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md) | format/detection/codec/semantic-adapter distinction |
| B15 | [registry/source governance (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_registry_source_governance_research_2026-10-07.md) | Reference Registry vs Source Catalog vs domain rule registry; version/currentness |
| B16 | [observability/errors/logs (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_observability_errors_logs_research_2026-10-07.md) | typed problems, terminal outcomes, Attempt/progress/receipts, AppDock error boundary |
| B17 | [single-node multi-user (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md) | Principal/Session/Participant, shared truth, read cursor, leases/assignments |
| B18 | [web/self-hosted (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md) | host/client, durable application state, node API, remote execution |
| B19 | [system settings (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_system_settings_research_2026-10-07.md) | Settings/SurfaceState/Draft/Policy/RunParams, neutral plugin settings |
| B20 | [artifact style sets (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md) | ArtifactStyleSet vs interface theme vs metadata, style provenance |
| B21 | [generic plugin contract (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_corporate_plugin_contract_research_2026-10-07.md) | публичный generic plugin API: discovery, activation, capability, bindings, conformance; закрытые реализации исключены |

### 17.3. Surface/architectural cross-checks

| Код | Источник | Использование |
|---|---|---|
| B22 | [Windows interface requirements (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_windows_interface_requirements_research_2026-10-07.md) | Scenario-first vs Work/Thread-first projection; inspector/runs UX |
| B23 | [interface visual system (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_interface_visual_system_research_2026-10-07.md) | InterfaceTheme/tokens, UI representation independent from domain semantics |
| B24 | [Windows motion/animation (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_windows_motion_animation_research_2026-10-07.md) | semantic state vs motion projection; animation не создаёт состояние |
| B25 | [PROTOS boundary (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_boundary_research_2026-10-07.md) | external cognitive consumer vs domain/application ownership |
| B26 | [target core/design architecture (07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_target_core_design_architecture_2026-10-07.md) | logical ownership distinct from physical repository proposal |
| B27 | [automation/AI research (06.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md) | early automation/agent/case vocabulary; поздняя корректировка product scheduler ownership |

### 17.4. Исторические материалы и предел их роли

Документы `01-old-notes` — `О приложении Strategy Box.md`, `Интерфейс Strategy Box.md`, `Рефактор бизнес-логики Stratbox.md`, `Патч stratbox Май 2026.md` — рассматриваются как **исторический input**. Их вклад: возникновение идеи приложения, ранней оболочки, рефакторинга операций, разграничения домена и интерфейса. Идеи UI внутри core и тождество runtime/window с application owner уступили последующей подтверждённой архитектуре. Исторические утверждения не считаются current implementation facts.

### 17.5. Внешняя системная граница

Базовое описание AppDock, предоставленное среди материалов проекта, подтверждает роль управляемого узла, readiness, lifecycle, actions и результатов как частей внешней среды. Из него **не следует**, что AppDock должен становиться владельцем предметного Work/Job/Registry/Claim. Детальная архитектура AppDock здесь не исследовалась заново; семантика границы взята из его продуктового описания и релевантных studies.

---
## 18. Open Questions и локальные белые пятна

Ниже вопросы сформулированы как **конкретные неразрешённые семантические развилки**, а не произвольный future backlog. Приоритет относится к архитектурной блокирующей силе для тем 03–09.

| ID | Приоритет | Открытый вопрос | Почему нельзя решить из текущего корпуса | Что даст ответ / кому передать |
|---|---|---|---|---|
| Q01 | **P0** | Когда intent становится first-class `Work`? | Есть кандидаты из chat, сценария, automation и API; порог самостоятельной жизни не зафиксирован | 04: Work-admission state machine на 4 входных каналах |
| Q02 | **P0** | Обязательна ли `Run` между Work и Job для простого сценария? | Поздняя модель разделяет их семантически, current implementation такого опыта не имеет | 04: pilot на одном коротком и одном составном сценарии |
| Q03 | **P0** | Как разграничить Job и OperationRun в DAG и при делегировании удалённому executor? | Возможна Job на один leaf либо whole Scheme fragment; численность различается | 04/06: планировщик с parent-child causal refs и retry |
| Q04 | **P0** | Нужно ли сохранять `Case` как durable отдельный объект? | Текущий `ScenarioRunCase` смешивает роли; независимый use case для Case сверх Work/Run не доказан | 04/05/07: mapping legacy fields + UX pilot; default — projection |
| Q05 | **P0** | Как именно ScenarioDefinition связан с SchemeDefinition? | Разные исследования допускают one-to-one, one-to-many и composition of scenarios | 06: 3 real schemes (single op, composite, reusable sub-scheme) |
| Q06 | **P0** | Нужен ли отдельный `CascadeDefinition`? | Раннее исследование требует его, поздняя семантика покрывает многое Scheme + Scenario | 06/07: проверить membership selectors, nested goal, shared result aggregation |
| Q07 | **P0** | Минимальный `ExecutionOutcome` и WorkResult contract? | Текущие OperationResult и proposed terminal enums неполностью согласованы | 04/08: failure/retry/reconciliation matrix; schema conformance tests |
| Q08 | **P0** | Что происходит при `OUTCOME_UNKNOWN` и Work closure? | Нужны effect receipts, reconciliation и ownership unresolved effects | 04/08: fault-injection tests для external effects |
| Q09 | **P1** | Какие Claims должны иметь durable identity? | Для каждой цифры тяжело; для важных рекомендаций без этого нельзя | 03: pilot на банковском сравнении и SORS evidence |
| Q10 | **P1** | Нужен ли самостоятельный объект `AnalyticalBasis` или достаточно manifest/references? | Основания бывают не только файловыми и иногда спорными | 03: одна reusable claim chain с alternate evidence |
| Q11 | **P1** | `DatasetSnapshot` vs `ArtifactVersion` — как минимум пересечения? | Данные и носитель должны быть различны, но физическая материализация open | 03/05: один dataset в 3 форматах, retention/rebuild test |
| Q12 | **P1** | Отдельный `SourceRelease` или только Snapshot? | Два URL/файла могут составлять одну публикацию; ревизии/повторные загрузки различаются | 03: history с corrections/republishing |
| Q13 | **P1** | Модель `MeasureDefinition/Perimeter/Subject` и comparability bridges | Есть bank/entity/OKVED seeds, но нет общего minimal semantic identity | 03: IFRS vs RAS и SORS crosswalk acceptance case |
| Q14 | **P1** | Как currentness и validity фиксируются при повторном использовании? | `latest` недостаточно, но schema revalidation ещё нет | 03/08: source/registry revision and stale-result test |
| Q15 | **P1** | Thread↔Work cardinality и access-scoped links | Одни исследования предлагают primary thread, другие many-to-many | 05/07: два Thread, одна Work, разные права |
| Q16 | **P1** | Какое событие позволяет объявить Work completed, accepted, closed? | Execution success и substantive acceptance разные; автоматизация Review varied | 04/05: acceptance/closure policy profiles |
| Q17 | **P1** | Где берётся Principal и как разрешается delegation/run-as? | AppDock и Strategy Box имеют разные responsibilities | 05/08: explicit permission/effect model, threat cases |
| Q18 | **P1** | Сколько одновременно действует версий определения Operation/Scheme? | Core/Windows version drift, installed extensions, released plans | 06/08: versioned capability registry compatibility and invalidation |
| Q19 | **P1** | Какие бизнес-способности следует курировать в каталог, а какие оставить internal services? | Нет достаточной эксплуатации каталога >3 операций | 06: inventory 2–3 domains + applicability/effect tests |
| Q20 | **P1** | Сколько Artifact/Source/Result identity нужно в v1? | Content-addressed design сильный, immediate CAS не доказан нагрузкой | 03/05/08: cheap pilot с durable IDs + digest + storage path |
| Q21 | **P2** | Как именовать user-facing «Задача», «Работа», «Кейс», «Запуск» на русском? | Машинный словарь можно стабилизировать раньше UX labels | 07: usability study и controlled terminology glossary |
| Q22 | **P2** | Что делать с отдельным `CommandSpec`? | Низкоуровневые actions могут потребовать planning optimizations | 06: доказать недостающую выразительность Operation/Scheme |
| Q23 | **P2** | Нужен ли dedicated `Release`, `ValidationResult`, `EvidencePackage`, `DecisionInput` table? | Смыслы различимы, однако каждый самостоятельный lifecycle не доказан | 03/05: вводить только при реальном consumer |
| Q24 | **P2** | Отдельная cognitive activation persistence? | Внешняя cognition ещё не стала рабочим Strategy Box runtime | 06: first bounded integration pilot |
| Q25 | **P2** | Где живёт global search/index across Thread/Work/Artifact? | Это storage/projection decision, не часть identity | 05/07: search semantics and access filtering |

### 18.1. Три особенно опасные локальные белые пятна

**(A) Семантика повторения при разных эффектах.** Простейший `Attempt` моделирует технический retry, однако при частично опубликованном результате, staged file и delayed reconciliation может понадобиться отдельный `EffectIntent/EffectReceipt` со scope/idempotency identity. Важно решить, когда новая попытка допускается, а когда нужен новый Job/Run/Work. Само слово `retry` ответа не содержит.

**(B) Один аналитический результат — несколько независимых выводов.** Банковский отчёт может состоять из нескольких утверждений с разной свежестью, источниками и квалификацией. Если Result имеет только один `verified: true`, возникает ложная атомарность качества. Нужен хотя бы optional набор квалифицированных claims/result parts; для агрегированного user-facing Outcome требуется правило, что делать с частично подтверждёнными компонентами.

**(C) Триггер порождает новое поручение или продолжает существующее?** Ежедневный watcher можно моделировать как одну непрерывную Work с множеством Runs или как одну AutomationSpec с множеством самостоятельных Works. Семантический ответ зависит от того, что обещано потребителю, как учитываются обязательства и как закрываются результаты. Оба варианта допустимы, но правило должно быть **explicit admission policy**, а не скрытым следствием UI.

---

## 19. Что применять в последующих исследованиях и реализации

### 19.1. Тема 03 — Data → Knowledge

Использовать distinctions `SourceDescriptor/SourceSnapshot`, `RegistrySnapshot`, `MeasureDefinition`, `Observation/Dataset`, `Claim/Evidence/Basis`, `AnalyticalResult`, `Artifact/Materialization`. Проверить lightweight provenance graph на одном реальном источнике, одном изменённом snapshot и одном сложном банковском сравнении. **Не** материализовать универсальную Knowledge Graph БД до доказательства необходимости.

### 19.2. Тема 04 — Work → Execution

Использовать `WorkCandidate → Work → Run → ActivationBinding → Plan → Job → OperationRun → Attempt`. Проверить lifecycle cross-product: success vs acceptance; cancellation requested vs cancelled; timeout vs unknown; retry vs new Run; user vs automation vs AI. Центральная проверка: client closure не уничтожает durable Work/Job truth.

### 19.3. Тема 05 — State / Persistence / Collaboration

Для каждого ID назначить authoritative owner, lifetime, mutation model, schema revision, consistency/recovery и projection. Особый фокус: `Thread↔Work`, `Work↔Runs`, `Run↔Jobs`, `ArtifactRef↔Materializations`, actor/principal grants, read cursors, notification, settings vs drafts. SQLite/local и PostgreSQL/server остаются deployment choices, а не разными онтологиями.

### 19.4. Тема 06 — Capability / Extension / Automation

Развести definition/discovery/admission/binding/authorization/execution. Проверить три composition profiles: single Operation; Scenario over Scheme; большой workflow с reused sub-schemes. `Cascade` вводить отдельной сущностью только при доказанной семантике membership/identity, недоступной в общем Scheme/Scenario.

### 19.5. Тема 07 — Product Surfaces

Проецировать одни и те же `Thread, Work, Run, Job, Artifact, Problem` в Windows/Web/Android. Не держать предметную state truth внутри Qt. Названия экранов и карточек могут быть короткими русскими («Задачи», «Запуски», «Результаты»), но должны указывать на точные IDs. Пользовательский «кейс» допустим только как синоним представления, если модель явно не требует иного.

### 19.6. Тема 08 — Trust/Safety/System Qualities

Закрепить invariant tests для неизвестных внешних эффектов, scope-bound approvals, immutable plan refs, structured diagnostics, provenance, partial outcomes, concurrent mutation и permission filtering. Failure от transport/backend не может маскироваться пустым Dataset и не может создавать ложный Claim.

### 19.7. Тема 09 — Whole-System Target Architecture

Перевести эту **логическую** онтологию в конечную owner-map, затем только по инженерным критериям выбрать package/process/repository topology. Имена `stratbox-core`, `stratbox-host`, `stratbox-design` остаются предложениями до решения о жизненном цикле и потребителях.

---

## 20. Decision/Gaps summary: статус после темы 02

| Группа | Результат | Статус |
|---|---|---|
| Source vs Snapshot vs Observation vs Claim | независимые смыслы зафиксированы; текущий код имеет только часть общей модели | **CONSOLIDATED** |
| Measure/Entity/Perimeter | обязательные semantic dimensions при material comparison; универсальная schema open | **CONSOLIDATED / OPEN implementation** |
| Capability vs Operation vs implementation | semantic contracts и bindings отдельны | **CONSOLIDATED** |
| Command | не становиться обязательным global canonical object без consumer | **TARGET-HYPOTHESIS** |
| Scenario | user/product use case definition, отдельно от Run и execution mode | **CONSOLIDATED** |
| Scheme | reusable machine composition, отдельно от Plan | **TARGET-HYPOTHESIS strong** |
| Cascade | UX/aggregation concept; отдельный canonical object не доказан | **UNKNOWN / pilot** |
| Thread vs Work | контекст общения и смысловое поручение независимы | **CONSOLIDATED** |
| Work vs Case | Work — durable semantic unit; current Case разложить на Work/Run/projection | **TARGET-HYPOTHESIS high confidence** |
| Run vs Job vs OperationRun vs Attempt | четыре разных уровня причинности и исполнения | **TARGET-HYPOTHESIS high confidence** |
| Run/Work terminal status vs Acceptance | execution success/partial/unknown отдельно от результата, принятия и closure | **CONSOLIDATED** |
| Result vs Artifact vs File | semantic result ≠ managed output ≠ physical location | **CONSOLIDATED** |
| Claim/Evidence materialization threshold | selective durable claims, не все наблюдения требуют object row | **UNKNOWN / pilot** |
| Automation vs Trigger vs Job | правило, факт срабатывания, выполнение различны | **CONSOLIDATED** |
| Principal vs Actor vs Session vs Node | security/causality/connection/environment различны | **CONSOLIDATED** |
| Plugin vs Provider vs Capability vs Authorization | нейтральная многоступенчатая модель; приватные детали вне публичного корпуса | **CONSOLIDATED** |
| UI projections vs authority | клиент отображает, application/headless owner управляет durable truth | **CONSOLIDATED** |
| Storage, schema, repo topology | логическая модель дана; физический дизайн далее | **OPEN** |

---

## 21. Итоговая формулировка для следующей фазы

**Canonical Semantic Model Strategy Box** — это не большой словарь типов ради полноты. Это минимальная система явно разделённых смысловых отношений:

> **Источник публикует содержание; Snapshot фиксирует наблюдённое состояние; определение показателя придаёт данным смысл; Observations и преобразования поддерживают квалифицированные Claims и Results; Capability определяет допустимый способ работы; Work фиксирует порученную цель и обязательства; Run/Plan/Job/OperationRun/Attempt фиксируют конкретное исполнение; EffectReceipts и diagnostics отделяют намерение от факта; Artifacts материализуют результаты; Acceptance/Closure завершают ответственность; Thread и Surfaces представляют взаимодействие, не владея истиной; Principal и Authority ограничивают эффекты; AppDock предоставляет внешнюю управляемую среду.**

Такое разграничение сохраняет сильные элементы действующего `stratbox` и Windows-прототипа, не превращает переходные имена в вечные нормативы и обеспечивает общую основу для дальнейших исследований Data → Knowledge, Work → Execution, Persistence, Extensions, Surfaces и Trust.

**Окончательный статус документа:** самостоятельный консолидированный **Research Synthesis**. Все новые определения и recommended resolutions должны проходить отдельное Product/Knowledge admission и затем проверяться на реальных вертикальных срезах. Код и публичные репозитории данным исследованием не менялись.

---

**End of Research Synthesis — Topic 02 / Canonical Semantic Model.**
