# Strategy Box — тема 09. Whole-System Target Architecture

**Дата исследования:** 2026-10-09  
**Программа:** `strategy_box_03_consolidation_research_program.md`, тема 09  
**Тип:** самостоятельный Research Synthesis / Consolidation Result  
**Основной корпус:** `02-base-study` (27 исследований по карте темы 00) и завершённые темы 00–07 третьей ветки  
**Дополнительные источники:** выборочная прямая проверка актуальных открытых implementation owners; описание платформенной границы AppDock; официальные технические спецификации  
**Исторический материал:** `01-old-notes` — только происхождение вопросов и вытесненных гипотез  
**Статус темы 08 на дату проверки:** отдельный файл `Trust, Safety & System Qualities` в доступном перечне третьей ветки **не найден**. Требуемые качества консолидированы здесь как **предварительный самостоятельный сквозной слой** на основе тем 00–07 и исходных работ второй ветки. Это не выдаётся за выполненную тему 08.  
**Ограничение:** исследование **не** принимает Product Decision, не меняет код, не утверждает новый репозиторий или сетевой API и не фиксирует окончательный Target WHAT/HOW.  
**Публичная граница:** используются только нейтральные контракты расширений. Ни внутреннее устройство, ни частные реализации закрытых плагинов не раскрываются.  
**Методологическая граница:** применяются общие принципы MADAR-методологии; структура каких-либо внешних методологических или интеграционных репозиториев не описывается.

---

## 0. Executive synthesis: конечная модель

**[CONSOLIDATED]** Strategy Box — **единый аналитический продукт**, где строго разделяются: (а) предметная истина о макроэкономических и банковских данных, (б) жизненный цикл пользовательской работы и исполнения, (в) доверие/полномочия и управление эффектами, (г) долговечные результаты и их доказательная история, (д) клиентские представления и (е) внешний платформенный lifecycle.

**Самый важный физический вывод:** уже существующий `stratbox` остаётся самостоятельной headless библиотекой экономической и банковской логики; `stratbox-windows` остаётся Windows surface. **Отдельный headless Strategy Box application authority** является сильнейшей целевой физической гипотезой для следующего большого этапа. Его возможное имя — `stratbox-host`, однако **наличие особой ответственности не доказывает необходимость отдельного репозитория, а имя не является Product Decision**. AppDock продолжает владеть установкой, узлом, активацией, платформенной сессией, размещением управляемых процессов, общей диагностикой и механизмом доступа к среде.

**[TARGET-HYPOTHESIS]** Следующий устойчивый минимальный продуктовый профиль:

```text
               HUMAN · AUTOMATION · ALLOWED MACHINE/AI ACTOR
                                 │
                Windows / Web / Android / CLI / API
                     (authorized projections)
                                 │
                    command / query / events
                                 │
          ┌──────────────────────▼────────────────────────┐
          │ Strategy Box application authority            │
          │ identity mapping · authorization · Work       │
          │ Thread · Scenario · Scheme · ExecutionPlan    │
          │ Run · JobManager · Attempt · Automation       │
          │ events · collaboration · artifact catalog     │
          │ projections · recovery · product diagnostics  │
          └──────────────────────┬────────────────────────┘
                                 │ canonical operation binding
          ┌──────────────────────▼────────────────────────┐
          │ stratbox — analytical / domain core           │
          │ sources · registries · semantics · operations │
          │ validation · reconstruction · evidence        │
          │ result / artifact specification / FileStore   │
          └──────────────────────┬────────────────────────┘
                                 │ neutral ports
              storage / network / execution providers
                                 │
                      physical data and effects

  EXTERNAL PLATFORM: AppDock — installation, Node/Session,
  managed environments, service lifecycle, remote transport,
  health and platform-level incidents.

  EXTERNAL COGNITIVE CONSUMERS: use permitted canonical
  capabilities; they do not own Strategy Box execution truth.
```

Эта схема **логическая**: отдельные прямоугольники не обязательно являются независимыми процессами. Для direct Python потребителей вызов `stratbox` сохраняется без обязательного application authority; для управляемых продуктовых Work authority обязателен.

### 0.1. Двенадцать системных решений высокой уверенности

| № | Положение | Эпистемический статус |
|---|---|---|
| 1 | Один предметный core; расчёты, схемы данных и экономические определения не копируются в GUI/host/AI | **CONSOLIDATED** |
| 2 | Один application authority на область Work/Job и единый execution spine для foreground/background/remote/scheduled/AI | **CONSOLIDATED** на уровне ответственности; **TARGET** физически |
| 3 | `Work`, `Run`, `Job`, `OperationRun`, `Attempt` — разные роли; `Case` текущего Windows не становится новым универсальным aggregate | **CONSOLIDATED** |
| 4 | `Scenario` — курируемый user use case; `Scheme` — типизированная композиция; `Cascade` не требует собственного execution engine | **CONSOLIDATED / частично OPEN** |
| 5 | Источник, его снимок, наблюдение, dataset version, аналитический результат, claim/evidence и artifact имеют разные идентичности | **CONSOLIDATED** |
| 6 | Execution success, предметная корректность, acceptance и Work closure — самостоятельные оценки | **CONSOLIDATED** |
| 7 | Durable Work/Job/rights/event truth принадлежит headless application authority, а не UI или AppDock | **CONSOLIDATED** |
| 8 | Artifact manifest/provenance создаётся предметным слоем; artifact catalog/ACL/связи с Work — application; bytes — storage | **CONSOLIDATED** |
| 9 | Публичное расширение обнаруживается, проверяется, выбирается, связывается и авторизуется раздельно | **CONSOLIDATED** |
| 10 | Surface использует общие semantic projections; Windows/Web/Android рисуют нативно и сохраняют отдельный local convenience state | **CONSOLIDATED** |
| 11 | Ошибка, `UNKNOWN`, незавершённый destructive effect и непроверенный результат не маскируются «успехом» | **CONSOLIDATED** |
| 12 | Сначала responsibility → owner → contract → proof; затем package/process/repository, когда доказана независимость жизненного цикла | **CONSOLIDATED** |

### 0.2. Крупные всё ещё открытые развилки

- **Physicalization:** отдельный `stratbox-host` repository против выделенного пакета/сервиса при существующей repository topology; клиентский shared package и отдельный design package.
- **Persistence topology:** SQLite на локальном узле как первая гипотеза, PostgreSQL для серверного профиля при обоснованной нагрузке; схемы миграций, offline и backup/restore.
- **Knowledge scope:** степень материализации `Claim/Evidence/Knowledge` поверх лёгкого provenance; общий graph store сейчас не доказан.
- **Artifact store:** immutable managed layout обязателен по смыслу, обязательный CAS — **UNKNOWN** до workload pilot.
- **Scheme/extension contracts:** DSL, schema versions, contribution trust policy, exact compatibility/admission semantics требуют implementation probes.
- **Cross-surface:** toolkit Android, shared package, deep links, notifications, search, preview, offline command queue и проектирование доступности.
- **Trust/operations:** измеримые SLA/SLO, resource budgets, recovery objectives, threat model, object-level ACL, retention и policy владельцев.

### 0.3. Важнейшее ограничение исследования

**Тема 09 по программе должна следовать за 08.** На дату исследования работы 00–07 доступны, но самостоятельная 08 в каталоге не обнаружена. Поэтому раздел 12 ниже — **provisional Topic-08 bridge**, а не замена утверждённого исследования 08. Инварианты, требующие отдельного security/fault-injection/performance подтверждения, имеют соответствующие статусы и gate.

---

## 1. Метод, источники и границы уверенности

### 1.1. Как собрана консолидация

Применён двойной метод. **Сверху вниз:** программа → системная цель → семантические слои → ownership → контракты → физическая декомпозиция. **Снизу вверх:** 27 исследований второй ветки, консолидирующие темы 00–07, выборочно проверенный current implementation, проблемные пути событий, файлов и версий → корректировка target. Исторические заметки использованы только как provenance устаревших решений. Прямые источники и точные ссылки сведены в §18.

Внутри текста используются статусы:

- **CURRENT** — наблюдаемый код, package metadata, manifest или зафиксированный baseline с датой; не обещание работоспособности всех путей.
- **CONSOLIDATED** — устойчивый результат нескольких исследований, согласованный с фактическим baseline, но ещё не Product Decision.
- **TARGET-HYPOTHESIS** — предпочитаемая схема, требующая утверждения, прототипа или conformance proof.
- **CONFLICT** — взаимоисключающие варианты с одинаковым scope и authority.
- **SUPERSEDED** — прежнее предложение вытеснено новой семантикой либо фактическим разделением.
- **UNKNOWN** — выбор пока невозможно обосновать.

**Разная физическая технология при общей семантике — не обязательно конфликт.** Например, локальный SQLite и серверный PostgreSQL могут реализовать один repository contract; `SourceSnapshot` и `Artifact` не соперничают за имя, а обозначают разную семантику.

### 1.2. Provenance: где факты, а где интерпретации

Приоритет установлен следующий: **проверенный прямой implementation owner** для текущих фактов → исследования текущего состояния с фиксированными commit → темы 00–07 с проверяемыми evidence chains → тематические работы `02-base-study` → исторические источники → внешние технические стандарты как сравнение, а не доказательство реализации.

Исходная карта темы 00 подтверждает **27 содержательных исследований** второй ветки на момент её подготовки. Для полной карты см. [C00]. Система не была независимо полностью протестирована в рамках настоящего исследования; выборочные code probes подтвердили перечисленные конкретные файлы, а не green-status продукта. Статистика тестов и зрелости из исследований 06.10 является **исторически датированным baseline**, а не результатом нашего нового прогона.

### 1.3. Платформенные границы

`AppDock` — отдельный владелец managed node/environment/productization. Strategy Box не принимает на себя установку, универсальное удалённое подключение, управление окружением и platform problem journal. AppDock не получает владение содержанием банковской операции, Work, пользовательским каталогом результатов или предметным расписанием. Портовые контракты могут согласовываться, но обе системы сохраняют собственные authority. Ссылка на общее продуктовое описание AppDock — [AD].

Расширения и machine/AI consumers рассматриваются **только через общий публичный контракт**; внутреннее устройство закрытых реализаций отсутствует в тексте.

---

## 2. CURRENT: что действительно существует на 09.10.2026

### 2.1. `stratbox`

**[CURRENT, code-verified metadata + dated baseline]** Python-пакет `stratbox` версии **0.8.0**, `>=3.10`, с доменами `cbr_file_collector`, `cbr_forms`, `cbr_industries`, `cbr_sors_restoration`, `escrow`, `frg`, общими `base`/`registries`/`text`, FileStore/IO/network/style слоями и разными по зрелости typed Request/Result. [I-CORE-PY], [B-CORE].

Что уже особенно сильное:

1. Домены работают без пользовательского окна и имеют реальный внешне-статистический смысл.
2. `cbr_forms` отделяет physical parsing, semantic model и canonical long; форма 802 — более зрелый образец.
3. `cbr_industries` и `escrow` уже имеют последовательность от source discovery к формированию данных и выгрузке.
4. `cbr_sors_restoration` реализует специализированный доказательный вычислительный процесс: official published vs inferred/rounded, bounds, source-preserving evidence и conflict ledger.
5. FRG поддерживает scan/selection/cleanup plan/execute, но предметные parsers в исследованном baseline ещё stub.
6. `FileStore` изолирует physical storage от предметных операций.

Что **отсутствует как общая система**: единая стабилизированная registry канонических операций, общеобязательные versioned SourceSnapshot/DatasetVersion manifests, uniforme error/progress/result envelope, управляемая свежесть всех справочников, общий Work/Job service и единый runtime artifact catalog. Это следует из [B-CORE], [C03], [C06]; данные семантические contracts пока являются планом.

**Особая проверка extensibility.** В `src/stratbox/base/runtime.py` есть `entry_points()` и local provider fallback, кэш выбора на процесс. Наличие installed provider может приводить к попытке его подключения; ошибка discovery/load может перейти в local режим. Это **CURRENT neutral loader behavior**, а не целевой trusted activation/binding protocol. Существование плагина не должно автоматически означать право использовать его capability. [I-CORE-RUNTIME], [C06].

### 2.2. `stratbox-windows`

**[CURRENT, code-verified metadata + dated baseline]** Python-пакет `stratbox-windows` **0.1.0**, Windows/PySide6 surface; AppDock connector manifest `4.0`, Windows-only, `foreground`, `local`; три operation specs (две прикладные, одна диагностическая), atomic scenarios и один composite. Имеются Qt-поток для последовательного исполнения, scenario-chat/case cards, events, логи, выходные paths, локальный workspace explorer, UI-настройки, presence/background/assignments scaffolds. [I-WIN-PY], [I-WIN-MANIFEST], [B-WINDOWS].

**Важные ограничения факта:**

- `runtime/bootstrap.py` импортирует `ScenarioCoordinator` из `presentation.qt_desktop` внутри `build_runtime()`. Поэтому application runtime пока не Qt-neutral. [I-WIN-BOOT].
- `HistoryPersistenceService` сохраняет `cases.json`, `events.json`, `artifacts.json`, `logs.json`, `assignments.json` **отдельными прямыми записями**. Ошибка декодирования JSON истории возвращает пустой список; это не transactional shared authority. [I-WIN-HISTORY].
- Background UI/state не доказывают scheduler; presence — не общий live registry; assignments — не shared delivery; статус `cancelled` не равен реально управляемой отмене. [B-WINDOWS], [C04], [C05].
- Qt coordinator допускает один foreground scenario в собственном процессе; это не основание ограничивать future node-wide JobManager одним заданием. [B-WINDOWS].
- `Case` сегодня создаётся как контейнер запуска, и не соответствует всей целевой семантике долговечной Work. [C02], [C04].

### 2.3. Подтверждённые implementation drifts

| Проблема | Проверка | Следствие |
|---|---|---|
| Core объявляет `0.8.0`, desktop dependency требует `stratbox==0.2.1` | прямые `pyproject.toml` обоих owners, 09.10 | **P0 несовместимость declared installation contract**; реальное успешное развёртывание всего graph не подтверждено |
| Desktop manifest требует core `0.2.1`, несмотря на фактическую актуальную `0.8.0` | прямой `appdock/manifest.json` | package graph требует синхронизации вместе с package metadata |
| Contract smoke-test desktop требует manifest `3.0` и `package_identity`, а реальный manifest — `4.0` и `package_requirement` | прямые manifest и `tests/smoke/test_repository_contract.py` | минимум отдельные assertions **логически не пройдут**; новый запуск suite здесь не выполнялся |
| GUI bootstrap импортирует Qt coordinator | прямой `runtime/bootstrap.py` | cross-platform application reuse ограничен |
| История пишет пять отдельных JSON и молча пустеет при invalid JSON | прямой `application/history/persistence.py` | нет долговечного multi-user/recovery contract |

**[CONSOLIDATED]** Эти пункты — инженерный baseline-gate. Их устранение желательно **до** строительства второго крупного runtime и новых surfaces, чтобы переход не наследовал ошибочную совместимость. Обратная совместимость с предыдущими пользовательскими API проектом не требуется; однако migration ценных пользовательских данных, versioned stored schemas и безопасный rollback релиза являются самостоятельными задачами.

### 2.4. AppDock: current vs product vision

**[CURRENT as Strategy Box integration]** Есть managed activation, node/session context, пути, health/status projections и диагностический запуск через manifest. **[TARGET / external ownership]** Работа через host, remote attachments, permissioned agent actions, generic platform problem aggregation и companion clients являются ожидаемыми направлениями из продуктового описания AppDock; их полная готовность для Strategy Box этим исследованием **не подтверждена**. [B-WINDOWS], [AD].

---

## 3. Logical Architecture: система смыслов, а не папок

### 3.1. Две центральные оси

**Data/Knowledge axis** отвечает, *что известно, из чего выведено, насколько достоверно и актуально*. **Work/Execution axis** отвечает, *что требуется сделать, кем разрешено, что выполнялось и что завершено*. Пересечение — **AnalyticalResult + provenance + Artifact + assessment**. Эти оси должны быть связаны отношениями, но различать authority, lifecycle и способ доказательства.

```text
             [DATA / KNOWLEDGE]
SourceDescriptor → SourceSnapshot → Observation/DatasetVersion
                   │                       │
RegistrySnapshot ──┴───────────────→ validate / derive
                                           │
                             Evidence / Claim / Result
                                           │
                               Artifact / ArtifactRef
                                           │
                          [WORK / EXECUTION]
Thread ↔ Work → Run → ExecutionPlan → Jobs → OperationRuns → Attempts
          │                     │                  │
          └── assessment/closure└── effect receipts└── progress/problems

                  above: identity / authorization / policy
                  below: backend / storage / execution / AppDock
                  outside: native client renderers and machine consumers
```

Один source snapshot может питать несколько DatasetVersions, а один Result — несколько Artifacts. Несколько независимых Work могут пользоваться одним read-only source/cache, при этом право доступа, ссылки и effect provenance различаются. Это не обязательный линейный pipeline и не обещание отдельной таблицы на каждый объект.

### 3.2. Объектная карта и критерий существования

| Семантический объект | Роль | Identity/lifetime | Не путать с |
|---|---|---|---|
| `SourceDescriptor` | что и каким authority публикуется | stable source ID + definition version | URL |
| `SourceSnapshot` | конкретная полученная версия публикации | immutable snapshot/hash + retrieval/vintage | «последний файл» |
| `RegistrySnapshot` | версия reference definition/classification | immutable/qualified revision | mtime ресурса |
| `Observation` | значение + мера, период, единица, периметр, method | domain ID + temporal/semantic context | число/ячейка XLSX |
| `DatasetVersion` | смысловая версия набора наблюдений | schema/transform/source refs | DataFrame |
| `Claim`/`Evidence` | утверждение и его основания/границы | scoped, qualified, revisable claims | факт из файла |
| `AnalyticalResult` | содержательный итог операции/анализа | result ID + provenance/status | terminal Job status |
| `Artifact` | долговечный адресуемый выход | artifact ID + immutable manifest | path или binary blob |
| `Capability` | декларируемая семантическая способность | stable ID + contract version | разрешение запуска |
| `OperationDefinition` | канонический предметный use case | stable definition/ABI version | Python callable |
| `ScenarioDefinition` | курируемый повторяемый user workflow | versioned authored definition | Work/Run |
| `SchemeDefinition` | типизированная reusable композиция | immutable revision + ports/guards/effects | конкретный ExecutionPlan |
| `Thread` | контекст обмена сообщениями/решений | thread ID, many-to-many Work refs | Work |
| `Work` | долговечная цель, ответственность, критерий закрытия | Work ID, revisions, admission | UI Case |
| `Run` | одна траектория осуществления Work | run ID + plan snapshot | Job |
| `ExecutionPlan` | разрешённый конкретный DAG действий и binding | immutable plan revision/hash | Scheme definition |
| `Job` | планируемая и выделяемая executor единица | Job ID, resource/lease/queue status | Run |
| `OperationRun` | доменная invocation с исполнением | operation invocation ID | Attempt |
| `Attempt` | конкретная физическая попытка | attempt ID + executor incarnation | retry policy |
| `EffectReceipt` | доказательство/неопределённость внешнего эффекта | effect ID, claim and verification status | «успешно» из лога |
| `AutomationSpec` | долговечное правило запуска | spec version + trigger policy | фоновой Job |
| `TriggerOccurrence` | факт конкретного срабатывания правила | stable occurrence identity + decision | новая Work автоматически |
| `Principal`/`Actor` | кому принадлежат права и кто действует | authenticated principal / actor identity | display name |
| `Session`/`Node` | платформенный контекст среды | external AppDock identities | собственная Product Work |
| `ArtifactStyleSet` | управляемая версия оформления отчёта | style version/hash | UI Theme |
| `Problem`/`Diagnostic` | нормализованная проблема и evidence | problem ID/correlation + scope | traceback string |

**[TARGET-HYPOTHESIS]** Выделять объект физически следует только при появлении отдельных identity, business lifecycle, ownership, permissions, optimistic revision, consumer или надёжно проверяемого эффекта. `CaseView`, `RunCard`, `ArtifactPreview`, `AvailableAction` — производные projections без самостоятельной durable truth.

### 3.3. Строго ограниченная онтология вместо нового «универсального фреймворка»

- `Operation` — не все функции `stratbox`. Низкоуровневые parsers, transforms, format converters остаются building blocks/services.
- `Command` — допустимая внутренняя техническая единица при наличии потребителя. Глобальный CommandRegistry пока не требуется.
- `Cascade` — понятное название сложного пользовательского сценария/композиции, но собственный `CascadeRun` и каскадный движок пока не оправданы.
- `Case` из current UI — transition/projection; ввод нового долгоживущего Case aggregate потребовал бы отдельной доказанной ответственности.
- `Knowledge` — ответственность за качество смысловых утверждений и их grounds; единый тяжёлый graph-store и universal ClaimStore не следуют автоматически.
- `Result` — qualified semantic answer, `ExecutionOutcome` — состояние запуска, `Acceptance` — оценка полученного, `Closure` — решение закончить Work.

---

## 4. Data & Knowledge Plane: от внешней публикации к обоснованному выводу

### 4.1. Две петли одного предметного контура

**[CONSOLIDATED, C03]** Целевая архитектура данных содержит одновременно:

1. **Воспроизводимый data path:** `SourceDescriptor → SourceSnapshot → raw bytes → physical decode → Observation / DatasetVersion → validation → transform / derived / restoration → AnalyticalResult → Artifact`.
2. **Эпистемический path:** `semantic measure/perimeter → evidence/basis → Claim / inference → uncertainty / applicability → qualified Result → assessment / revalidation`.

Путь **не линейный**. SourceSnapshot и RegistrySnapshot могут образовывать DAG предшественников, один output может опираться на несколько периодов и разных источников, а новая публикация создаёт не замену старой истины, а новую vintage и повод пересчитать зависимые результаты.

Семантическая канонизация отвечает на вопрос «как понимать значение?». Она не подменяет проверку «насколько значение соответствует реальности?». Особенно важно для банковских данных: отчетность отдельного банка, группы, РСБУ и МСФО, квартальные/накопленные величины, остатки/обороты, опубликованные округления и реконструированные оценки нельзя объединять одной совпадающей русской подписью.

### 4.2. Минимальный semantic source contract

**[TARGET-HYPOTHESIS]** `SourceDescriptor` должен содержать `source_id`, authority, source-kind, publication policy, expected content/mime/schema, identifier/locator, cadence, applicability, discovery/validation policy. `SourceSnapshot` — отдельную immutable identity: raw content hash, requested/final URL, fetched_at, publication/observation period, vintage/revision signal, content metadata, validation result, trace и upstream links. URL остаётся locator: авторитетная публикация может меняться по тому же URL.

Для существенных расчётов `DatasetVersion` связывает `SourceSnapshotRef`, `RegistrySnapshotRef`, transform code/version, semantic schema, geography, measure, unit, currency/perimeter, missingness, validation results. DataFrame — только удобное представление такого набора, а не его идентичность.

**UNKNOWN:** обязательный срок физического хранения каждого сырого файла, формальная политика official vintage для всех источников, полнота базовой `DatasetVersion` schema. Их следует решать на двух-трёх неоднородных доменах, а не создавать сразу универсальный большой data catalog.

### 4.3. Относительная роль действующих доменов

| Домен | Доказанный вклад baseline | Следующий сквозной контракт |
|---|---|---|
| `cbr_file_collector` | сохранение исходных официальных файлов, source IDs, failures | descriptor/snapshot, content identity, cache/change detection |
| `cbr_forms` | physical DBF → semantic model → canonical long; особенно 802 | versioned physical schema, dataset/result split, complete semantic catalogs |
| `cbr_industries` | связный long/derived/pivot/export и проверки | единый series contract, geography snapshot, второе реальное series |
| `escrow` | historical publication parsing, history/view/export | source vintage, revised history, provenance and tests |
| `cbr_sors_restoration` | bounds, source-preserving evidence, conflict/assumption tiers, reproducible computational method | manifest source/registry/solver/config, performance and cache boundaries |
| `frg` | scan, classification, cleanup plan/apply, archive | typed operations, destructive receipts, parsers, tests |

**[CONSOLIDATED]** SORS служит **stress test доказательности**, но его специализированную математическую модель не требуется механически внедрять в каждый сборщик CSV. Общий минимум — источники, семантические определители, условия применимости, warning/error и воспроизводимые версии. Более сильные claims сохраняют свой domain-specific evidence, включая допущения и конфликтные основания.

### 4.4. Управление справочниками

`stratbox.registries` сейчас хранит packaged reference data, но по [B-CORE] bank/OKVED snapshots были старше официальных публикаций 2026 года; отсутствует единый freshness/admission workflow. **[CONSOLIDATED]** Нужен lifecycle:

```text
official change detection
       → candidate snapshot
       → provenance + validation + semantic diff
       → controlled admission/review
       → immutable RegistrySnapshot
       → explicit consumer pinning
       → impact assessment / revalidation
```

Для географии, ОКВЭД2 и банковских идентичностей действуют разные предметные правила. Общий lifecycle и IDs допустимы, общий «реестр на всё» — нет. Принадлежность snapshot к конкретной дате/периметру является частью результата; `mtime`, «самый новый XLSX» и «последняя изменённая строка» недостаточны для reproducibility.

### 4.5. Artifact Plane: продукт результата

**[CONSOLIDATED]** Артефакт — не файл в `output/`. Он имеет ID, содержательное назначение, immutable content version/manifest, creator/effect/Run refs, kind, schema/style metadata, lineage, access/retention policies и один или несколько способов материализации. Физическое расположение или имя файла меняется; stable ArtifactRef остаётся.

Сильное разделение владения:

- `stratbox`: сформировать корректный domain Result, семантику экспортируемого Artifact и воспроизводимый provenance;
- application authority: register/index artifact, link to Work/Run, visibility, ACL, notifications, retention decisions;
- storage adapter: хранить bytes, проверять digests, предоставлять physical materialization;
- surface: preview/reveal/download/open через разрешённые действия, не через абсолютный чужой путь;
- AppDock: управляемые roots, lifecycle и platform diagnostics, а не бизнес-смысл артефакта.

**[TARGET-HYPOTHESIS]** Безопасный выпуск использовать как stateful publication protocol:

```text
DRAFT/STAGING → write → validate bytes/schema/checksum
        → register commit intent → atomic metadata visibility
        → COMMITTED (resolvable ArtifactRef)
        ↘ on failure: ABORT / QUARANTINED / RECONCILE
```

Важно: **SQL transaction не охватывает произвольную ФС атомарно**. Поэтому нужен проверяемый recoverable protocol с content verification, commit barrier, outbox/reconciliation и очисткой orphan staging. Нельзя обещать распределённую атомарность только потому, что DB является транзакционной. При аварии во время записи материализация остаётся staging/incomplete, а не опубликованным успехом.

**CAS:** хэш как content identity полезен практически сразу; отдельный обязательный content-addressed storage engine — **UNKNOWN**. Допускается immutable versioned directory layout с content digest и контролем целостности. Решение о дедупликации/GC принимать после замера типичных объёмов XLSX/CSV/ZIP и политики хранения.

### 4.6. Cache и currentness

**Четыре разных смысла «актуально»:**

1. источник на момент retrieval соответствовал доступной публикации;
2. существует более свежая/исправленная vintage;
3. зависимый Dataset/Result всё ещё удовлетворяет validity и assumptions;
4. результат подходит конкретному пользовательскому Work «на сегодня».

Кэш допустим при ключе, включающем корректную identity dependency: source hash, registry snapshot, operation/transform version, параметры и при необходимости environment capability/binding. Shared cache не должен случайно смешивать ACL нескольких клиентов, независимо полученные внешние публикации и разные доказательные режимы. Cache hit — экономия работы, а не новое доказательство истины.

### 4.7. Артефактное оформление и авторство

**[CONSOLIDATED]** `ArtifactStyleSet`, `InterfaceTheme`, `Template`, `AuthoringMetadata` и `Presentation` различны. Форматирующий renderer может принимать версионированные палитры, стили таблиц/графиков, шрифты, правила подписей и метаданные автора, но предметный результат остаётся самостоятельным. Style identity/version включается в Artifact manifest, если от неё зависит воспроизводимое отображение.

Пользовательская настройка «автор документа» не должна подменять фактическую provenance `actor/principal` выполнения: отображаемое авторство файла, утверждающий лицо, запускающий actor и исходный автор источника — разные роли. Для отчётов с несколькими contributors требуется явная attribution policy. Реализация cross-format style tokens — сильная target-гипотеза, а фактическая поддержка каждого формата должна доказываться per-renderer tests.

---

## 5. Capability & Extension Plane: одна аналитическая система, разные способы вызова

### 5.1. Четыре уровня предметного кода

**[CONSOLIDATED, C02/C06]** Для сохранения composability и тестируемости полезна дисциплина:

```text
low-level mechanism → reusable building block → domain service
      → canonical OperationDefinition → optional Scheme/Scenario
```

Функция чтения DBF или сетевой retry — механизм. Нормализация формы — domain building block/service. Предметно законченный запрос `cbr.forms.build` с контрактом данных, ошибок, применимости и эффектов — кандидат canonical Operation. У него есть user/API consumers. `Scenario` — понятное человеку, курируемое повторяемое действие; `Scheme` — typed composition с зависимостями и guards. Наличие операции **не** обязывает создавать отдельную UI-кнопку.

### 5.2. Доступность способности — результат вычисления, а не один флаг

**[TARGET-HYPOTHESIS]** Различать:

```text
registered definition
    ∧ compatible implementation binding
    ∧ environment dependencies READY
    ∧ applicable to requested inputs/sources
    ∧ actor-authorized effects
    ∧ quotas/resources available
    ∧ version/capability evidence acceptable
    ⇒ available action (context-scoped)
```

Нельзя смешивать:

- *installed* — пакет физически присутствует;
- *discovered* — description валиден для чтения;
- *selected* — администратор/политика выбрали contribution;
- *bound* — consumer получил совместимую реализацию;
- *ready* — внешние зависимости доступны;
- *authorized* — конкретному Principal разрешён эффект;
- *applicable* — операция подходит данным и семантическому контексту.

Формально capability каталог, extension registry, binding registry, runtime availability index и actor-specific visible catalogue имеют разную изменчивость. Они могут быть реализованы без пяти физических databases, но не должны иметь одну искусственную `enabled` переменную для всех смыслов.

### 5.3. Минимальные OperationDefinition поля

**Кандидат контракта**, не готовый API:

```yaml
operation_id: cbr.forms.build
contract_version: 1
request_schema_ref: ...
result_schema_ref: ...
applicability: ...
source_requirements: ...
side_effects: [read_source, write_artifact]
destructive: false
idempotency_class: deterministic_for_pinned_inputs
retry_policy_ref: ...
cancellation: cooperative
resource_hints: {memory_class: medium, cpu_class: medium}
provenance_requirements: [sources, registry_snapshots, transform_version]
capability_envelope_ref: ...
```

`Operation` не превращается в giant универсальный pipeline: поля должны описывать подтверждаемые свойства, а не пустую декларацию «supports everything». Domain-specific request/result остаются богатыми, общий Result envelope — тонкий.

### 5.4. Машинные схемы и каскады

**[TARGET-HYPOTHESIS]** `SchemeDefinition` — immutable/versioned typed DAG из операций/подсхем с портами данных, applicability guards, outputs, effect profile, fallbacks, missingness/policy semantics. Его **compile/plan** связывает определения с конкретными источниками, versions, capabilities и execution policy; ExecutionPlan фиксирует результат разрешения до запуска. Схема не должна сама быть исполняющим процессом.

`Cascade` полезно для UX крупных скоординированных действий (например, обновление нескольких блоков статистики). Если каскаду понадобятся отдельные membership selectors, governance/release и aggregate acceptance, это может доказать самостоятельный `CascadeDefinition`. Сейчас новый `CascadeRun` и отдельный движок не имеют сильного обоснования: workflow идет через единый Run/Job graph.

### 5.5. Extension protocol — generic и bounded

**[CONSOLIDATED]** Публичная архитектура должна содержать нейтральные extension interfaces, а не знания о конкретной среде. Типы contribution различимы:

- infrastructure/provider binding (storage, secrets, network, execution boundary);
- source and registry descriptors/adapters;
- канонические domain operation contributions при проверенной модели доверия;
- artifact format adapter/style/template resources;
- декларативная surface-safe metadata/action descriptors;
- execution backends с explicit capability/effect profile.

**Два разных trust gate:** (1) можно ли исполнять данный код/ресурс в этой среде; (2) вправе ли конкретный actor выполнить конкретное действие. Python entry point — **механизм обнаружения**, а не гарантия совместимости, sandbox или выдача права. In-process trusted code остаётся in-process executable code с соответствующими рисками.

Запрещённый для целевой модели shortcut: «первое найденное расширение» + silent fallback из нерабочего обязательного provider в local режим. Для optional capability нужен явный degraded status; для required provider — fail-closed preflight/admission с безопасной диагностикой и without secret exposure.

### 5.6. Версии и conformance

Разделять как минимум:

1. distribution/build identity;
2. extension/contract schema version;
3. contribution definition revision;
4. runtime binding/activation revision;
5. policy/capability envelope version, если существенна для исполнения.

**[TARGET-HYPOTHESIS]** В immutable ExecutionPlan записываются binding refs и версии; running Run не может молча переключиться на другую реализацию после обновления пакета. Conformance pyramid: static manifest validation → hermetic fake-provider tests → contract/negative cases → isolated smoke в контролируемой среде → staging acceptance → product runtime health. Last known healthy ≠ сейчас available. Точные форматы ABI, подписей и версионных диапазонов — **UNKNOWN**.

### 5.7. AI, automation и CLI — те же способности

Внешний машинный потребитель видит **контекстно отфильтрованное** представление общего canonical catalogue с typed inputs/outputs, provenance, costs, restrictions, effect/approval policy и uncertainty. MCP или другой протокол — transport/projection, а не новый владелец способности. У агента нет общего `execute_python`/`shell` обходного пути; он предлагает Work/Plan либо инициирует разрешённое действие с теми же admission, audit и idempotency controls.

CLI/Python direct consumers могут импортировать `stratbox` как библиотеку для собственных расчетов. Если же пользователь хочет **управляемую продуктовую работу** с историей, permissions и notifications, вызов должен проходить через application service. Таким образом, direct reuse core и one execution spine **совместимы**: это два уровня потребления, а не две конкурирующие бизнес-логики.

---

## 6. Work & Execution Plane: единственная машина исполнения

### 6.1. Semantic spine и границы admission

**[CONSOLIDATED, C04]**:

```text
Human / Automation / AI / API request
   → Intent / WorkCandidate
   → identity + ACL + scope + effect policy
   → Work admission (or link to existing Work)
   → Scenario/Scheme/Operation selection
   → resolved parameters + source/binding/policy snapshot
   → ExecutionPlan
   → Run admission/commit
   → JobManager/queue (resource claims, leases)
   → Job / OperationRun / Attempt(s)
   → ProgressEvents, EffectReceipts, Diagnostics
   → ExecutionOutcome + qualified Result + Artifact refs
   → Assessment / Acceptance / Closure
```

Техническая операция при прямом использовании библиотеки не обязана создавать Work. Автоматическое обнаружение новой публикации может завершиться событием «изменений нет» без искусственной пустой Work. New Work vs continuation старой Work требует product admission rule, а не решения по строке `trigger_id`.

### 6.2. Семейство state machines вместо одного enums-комбайна

**[TARGET-HYPOTHESIS]** Минимально различать FSM:

| Aggregate | Возможные состояния | Что завершает |
|---|---|---|
| `Work` | `proposed/admitted/active/awaiting_review/blocked/closed/cancelled` | explicit closure/acceptance policy |
| `Run` | `created/planned/admitted/active/reconciling/succeeded/failed/cancelled/outcome_unknown` | единый terminal execution outcome после reconciliation |
| `Job` | `pending/queued/leased/running/retry_wait/cancel_requested/terminal` | durable job terminal receipt |
| `OperationRun` | `prepared/executing/result_ready/partial/failed/outcome_unknown` | domain and effect record |
| `Attempt` | `created/dispatched/started/ended/lost_contact` | physical attempt receipt/timeout evidence |
| `Artifact` | `staging/committed/quarantined/expired/deleted` | independent content lifecycle |

Названия **иллюстративные**; точные enum и переходы нужно formalize/test. `cancel_requested` не равен `cancelled`. Для `Run` неизвестный внешне эффект после потери связи не следует преждевременно объявлять «failed», пока reconciliation не установит исход. `Work` может оставаться awaiting review после успешного Run.

### 6.3. Нормативно важные различения «успеха»

Успех получения HTTP 200 не гарантирует корректного source content. Успешный parser не доказывает единицы измерения. Завершённый job может породить некорректную, но технически валидную таблицу. Commit XLSX не доказывает утверждение о банке. **ExecutionOutcome, DomainValidation, AnalyticalAssurance, WorkAcceptance** — четыре независимых наблюдения, которые нельзя свести к `success=True`.

Минимальный Result envelope может содержать `execution_outcome`, `domain_result_ref`, `warnings/failures`, `artifacts`, `provenance`, `effect_receipts`, `assurance_summary`, а статус Work определяется собственной приемкой. При partial results сохраняется установленный набор успехов/ошибок и используется честная квалификация.

### 6.4. Planner, JobManager, backend

**Planner** строит фиксированный граф, разрешает параметры, versions, capabilities, эффекты, зависимости, resource claims, approvals и reuse. **JobManager** отвечает за транзакционное admission очереди, планирование, fairness, leases/fencing, worker allocation, cancellation/retries/recovery и running attempt tracking. **ExecutionBackend** принимает уже разрешённую Job, исполняет locally/subprocess/remote, возвращает progress/effects — без права самостоятельно расширить полномочия или поменять план.

**[CONSOLIDATED]** Foreground, background, scheduled, remote, AI — измерения `trigger + locality + actor + service mode + interaction surface`, а не альтернативные job managers. В local profile executor может жить рядом с node authority. В server profile возможны отдельные workers, но одна authority определяет состояние и полномочия.

### 6.5. Параллельность и shared resources

Запрет `second_run` на уровне Qt-прототипа следует заменить управлением по объектным ресурсам:

- CPU/memory budget и per-job limits;
- rate limit/connection budgets внешних источников;
- source dedup/cache concurrency;
- workspace subtree/target output locks;
- destructive mutation scope;
- lease worker ≠ lock business resource;
- priority/fairness/quotas per principal/automation;
- atomic check-and-acquire с fencing для потерянного worker.

Не следует сериализовать весь узел ради одной конфликтной директории. Также не следует запускать два writer для одного artifact target, когда путь ещё не заменён immutable identity. Политика разделения Job определяет, что действительно можно retry/cancel independently.

### 6.6. Retry, cancellation и неизвестные эффекты

**[CONSOLIDATED]** Retry классифицируется по эффектам:

1. read-only deterministic — обычно повторяемо при pinned inputs;
2. idempotent write с проверяемым key/receipt — повторяемо при сохранении прежнего identity;
3. non-idempotent externally visible — до повторения требуется effect check/approval;
4. outcome unknown — сначала reconciliation, затем решение.

`idempotency_key` относится к определённому effect boundary и должен проверяться под транзакционной authority; «передали тот же HTTP request» само по себе не гарантирует exactly once для побочного эффекта. Cancellation кооперативная, сообщает о намерении, а не о magically cancelled IO. Force termination допустим лишь там, где можно изолировать worker и безопасно разобрать оставшиеся эффекты. Timed-out worker не должен быть объявлен failed и одновременно продолжать записывать результат; для lease expiry нужен fencing/receipt verification.

### 6.7. Durable automation

**[TARGET-HYPOTHESIS]** `AutomationSpec` задаёт источник срабатывания, часовую зону, календарную семантику, overlap/misfire policy, selector/scope, actor/rights, budget и revision. Каждый `TriggerOccurrence` имеет стабильную identity, decision (ignored/coalesced/admitted/failed-check/unknown), лог основания и, если нужно, ссылку на Work/Run. Source watcher сравнивает содержательный snapshot/official vintage/validation, а не просто filename или mtime.

Scheduler **продуктовый** и принадлежит Strategy Box application authority; AppDock обеспечивает процессный lifecycle, надзор за его здоровьем и инфраструктуру. При shutdown GUI расписание продолжает работать только при реально активном независимом backend — текущий `BackgroundProcessStore` этого не обеспечивает.

### 6.8. Testable end-to-end example: банковская отчётность

1. Пользователь открывает Work «подготовить сводку по форме 802 за период». Формируется WorkCandidate.
2. Admission проверяет principal, доступность источника, политику и quota.
3. Core каталог возвращает `cbr.forms.build` и семантические требования к дате/формату.
4. План фиксирует `SourceSnapshotRef`, `RegistrySnapshotRef`, contract/transform versions, пути staging и допустимый executor.
5. Job получает lease; OperationRun/Attempt записывают progress и validation.
6. Core создаёт canonical dataset/result; XLSX собирается в staging, проверяется и публикуется через ArtifactRef.
7. Run завершается `succeeded` **лишь на уровне исполнения**. Work переходит к review/acceptance; при ошибке проверки семантики Work может остаться blocked, несмотря на успешный XLSX.
8. Другой разрешённый клиент видит тот же Work/Run/Artifact, а не новую локальную историю. При пересмотре публикации старая версия остаётся доступной и получает currentness assessment.

Сценарий проверяет совместную работу всех planes; ни один из шагов не требует отдельного AI-only или background-only движка.

---

## 7. State, Persistence & Collaboration Plane

### 7.1. Три вида состояния — три разных договора

**[CONSOLIDATED, C05]** Сохранение каждого поля определяется не удобством сериализации, а тем, **кто имеет authority над его значением и что сломается при потере**:

| Категория | Примеры | Authority и надёжность |
|---|---|---|
| Authoritative durable | Work/Run/Job, policy decisions, approvals, assignment, AutomationSpec, TriggerOccurrence, Artifact index, effect receipt | транзакционный application authority; revision, audit, recovery |
| Derivable projection | timeline cards, unread count, running list, search indexes, preview summary, contextual availability | вычисляется из truth, допускает rebuild, cursor/replay |
| Local convenience | окно/вкладка, draft, фильтры, текущий selection, device theme | client/device, небольшой атомарный store или память |
| Platform state | AppDock Node/Session, environment roots, managed process health | внешний AppDock authority; Strategy Box получает snapshot/bridge |
| Domain facts | SourceSnapshot/RegistrySnapshot/DatasetVersion, domain evidence/result | `stratbox` semantics и domain-managed immutable identity; bytes отдельно |

**Важный случай:** `unread` для общего события не может быть одним полем общего объекта. У разных principals разные read cursors; вводится per-principal/authorized-feed cursor или receipt. Presence также не становится вечным полем пользователя — это производный статус с TTL/heartbeat policy.

### 7.2. Node authority и область консистентности

**[TARGET-HYPOTHESIS, high confidence]** В локальном однопроцессном/одноузловом профиле один headless authority принимает commands и выдаёт query/subscription snapshots. Он может физически размещаться в одном процессе с executor на раннем этапе. На многопользовательском узле клиенты подключаются к той же authority. В server deployment тот же contract может стоять за API/server pool с SQL transactions/leases и выделенными workers.

`node_id` — не замена instance epoch. При восстановлении backup или создании клона узла требуется **restore epoch/generation/fencing**: старые workers, подписки и idempotency scopes не могут автоматически считаться валидными в восстановленной копии. Это новое критическое белое пятно из [C05], которое важно закрыть совместно с платформенным owner.

### 7.3. Persistence contract

**[TARGET-HYPOTHESIS]** Для application authority нужен набор общих операций, а не привязка объектов к SQLite SQL:

```text
begin_unit_of_work()
create/update with expected_revision
reserve_unique_idempotency_identity()
append durable semantic event
write durable current-state projection
enqueue outbox effect/notification
commit / rollback
replay from authorized cursor
```

Принцип: **состояние и событие, подтверждающее переход, коммитятся совместно** в одной transaction boundary; доставка внешнего уведомления идёт через outbox/retry с dedup. Полный event sourcing не обязателен: полезна гибридная модель «текущие таблицы + append-only domain facts + outbox». Если ранний продукт может доказуемо обойтись меньшим, он не обязан хранить каждый технический клик как вечное событие.

### 7.4. SQLite и PostgreSQL — profile choice, не онтологический конфликт

- **SQLite/WAL** — кандидат для локального одиночного authority на **локальном файловом диске**, при ограниченной writer concurrency и управляемом backup/checkpoint. На сетевой файловой системе SQLite WAL применять нельзя: официальная документация прямо ограничивает WAL одним хостом, и у него один активный writer. [EXT-SQLITE]
- **PostgreSQL** — кандидат для самостоятельного web/server с операционным сопровождением, ростом конкурентной нагрузки, репликацией и более развитыми схемами эксплуатации. Не следует объявлять его обязательным, пока профиль пользователя не требует.
- **Стандартный contract** обязан сохранять одинаковые команды, optimistic revisions, idempotency, event ordering и privacy semantics. Топология БД остаётся **TARGET-HYPOTHESIS**, а не утверждённой реализацией.

`Data root`/workspace и transactional metadata store — разные области. Класть активную WAL DB на пользовательский network share ради «общих данных» — неверная архитектура для первого node authority. Backup должен захватывать согласованную DB и нужные Artifact manifests/content, а не только один `.db` файл.

### 7.5. Schema evolution без legacy API

Правило проекта «обратная совместимость не нужна» означает возможность **сразу заменять неудачные новые API/модели**. Из этого **не** следует право потерять ценные сохранённые Work/Artifacts/Settings. Нужно различать:

- **API backward compatibility:** на переходной стадии можно намеренно порвать.
- **On-disk schema migration:** должна быть одноразовая проверяемая forward migration или явная контролируемая новая база, с backup/rollback planning.
- **Historical result reproducibility:** требует сохранить references на старые definitions/versions, даже если старый исполняемый код уже удалён.
- **Running plan pinning:** новое обновление не переписывает executing snapshot.

Возможный релиз: pause admission → drain/stop/checkpoint → backup → schema migration → verify invariants → switch service → health → reopen admission. Во время несовместимости клиенты видят `upgrade_required`/`temporarily_unavailable`, а не ложное «успешно запущено».

### 7.6. Collaboration as authority, не UI-функция

Структурировать:

```text
Principal (удостоверенная identity)
  ├─ role/grants scoped to node/work/artifact/action
  ├─ Participant association with Work/Thread
  ├─ Assignment (кому поручено действие/проверка)
  ├─ Approval (кто разрешил эффект)
  ├─ ReadCursor (что человек видел)
  └─ Preferences (что человек настроил)
```

`Actor` фиксирует фактического инициатора — human, automation, permitted machine. Executor — отдельная runtime identity. Authenticated user ≠ actor ≠ process ≠ solver. Данные session принадлежности переводятся из AppDock в product-specific principal/grants на application boundary. Presence рассчитывается из разрешённых heartbeat/session данных, а shared mutation проходит через application authorization, где проверяются policy revision и объектные полномочия.

### 7.7. Reconnect и offline

**[CONSOLIDATED]** Клиент при подключении получает authorized consistent snapshot и opaque cursor, затем поток разрешённых изменений. При gap reconnect получает новую согласованную snapshot или bounded replay. Отсутствие связи не означает остановку Jobs.

Три состояния отображения надо различать: `LIVE`, `STALE_CACHED`, `UNAVAILABLE/UNKNOWN`. Android/Web может безопасно показать сохранённую последнюю проекцию с отметкой времени, но не выдавать старую available action за текущую permission. Offline queued destructive mutations по умолчанию запрещены до отдельной idempotency/authorization/revalidation policy. Черновики локальны, а их cross-device sync — отдельное Product Decision.

### 7.8. Notifications и search

**[TARGET-HYPOTHESIS]** Notification выводится из продуктового значимого события, адресной policy и per-principal delivery/read receipt. Источник истины — Work/Run/Problem/Assignment event, а не второй дублирующий фоновый канал. Search индексирует разрешённые Work, Threads, Artifacts, Sources, Scenarios и при необходимости логи; индекс является projection, а не authority. Search/notification latency, ranking, текстовый scope, retention и cross-user filtering остаются **UNKNOWN**.

---

## 8. Product Surface Plane: общая семантика, нативное представление

### 8.1. Семантические направления

**[CONSOLIDATED, C07]** Рекомендуемая information architecture как четыре логических направления:

1. **Работа** — Threads, Work, user interaction, notifications, assignments, approvals, review/closure.
2. **Проводник** — workspace objects, sources, materializations, Artifact Library и provenance.
3. **Сценарии** — curated ScenarioDefinition/Scheme catalogue, доступность, формы параметров, templates.
4. **Запуски** — все foreground/background/scheduled/remote Run/Job, очередь, progress, cancellation, recovery и debugging.

Это логическая продуктовая навигация, а не требование показать четыре одинаковые вкладки на каждом экране. «Каскады», «Участники», «Фоновые» и «Поручения» естественнее реализовать как контекстные projections: отдельные entry points появляются только при наличии собственной пользовательской цели. Текущий Windows шестираздельный mode rail остаётся **CURRENT**, но перестаёт определять целевую онтологию.

### 8.2. Thread/Work-first, но Scenario сохраняется

**[CONSOLIDATED]** Основной чат — не механический список стартов сценариев. Thread связывает сообщения и ссылки на несколько Work; Work живёт дольше одного Run и может включать review, корректировку, повторный запуск и результат без нового чата. При этом Scenario остаётся быстрым, понятным входом в повторяемое действие. Для опытных пользователей — search/catalog/command palette через ту же action projection, а не через независимый handler path.

Windows desktop может использовать трехзонную адаптивную композицию с Work timeline, Explorer, inspector; Web — responsive layouts; Android — touch-first навигацию и companion сначала, если это подтвердит сценарий использования. Renderer не должен сам вычислять permission и состояния Job из логов.

### 8.3. Semantic presentation contracts

**[TARGET-HYPOTHESIS]** Общий контракт между application authority и клиентом содержит:

```text
ViewSnapshot {entity_ref, revision, permitted_projection, cursor,
              freshness, selected_state, available_actions}
ActionDescriptor {action_id, input_schema, effect, confirmation_kind,
                  availability_reason, permission_context}
Command {request_id, actor_context, target_ref, expected_revision,
         idempotency_key, parameters, confirmation_ref?}
EventEnvelope {event_id, aggregate_ref, revision, sequence/cursor,
               timestamp, causal_ref, actor_ref, type, safe_payload}
```

Поля иллюстративны. Один channel обслуживает UI actions, API и машинную surface при разных представлениях и допущенных scopes. Backend производит projection с уже применённой ACL и безопасной редукцией полей. Frontend сам применяет platform layout, keyboard shortcuts, touch-targets, accessibility и понятный язык. Граница различает semantic `reason disabled` (нет прав, capability отсутствует, resource locked, offline, needs input) и визуальное disabled состояние.

### 8.4. Surface-specific contracts

| Surface | Наиболее полезный initial scope | Что остаётся adapter-specific |
|---|---|---|
| `stratbox-windows` | полноценный desktop workflow, локальный explorer, редактор параметров, log diagnostics | Qt UI, OS open/reveal, keyboard, tray/window lifecycle |
| Web | multi-client view, Work/Run/Artifacts/Approvals через node API | browser auth, safe downloads, responsive, SSE/WebSocket выбор |
| Android | companion: статус, уведомления, согласования, лёгкие запуски, preview | OS permissions, notification channels, touch, offline cache |
| CLI/Python | прямое исследование core либо управляемые application commands | terminal formatting, noninteractive auth |
| Narrow surfaces | bounded status/notification/approval | устройство/возможности и input constraints |

**Факты:** Windows реализован. Web, Android, API для них и независимый host — target directions; их production availability **не подтверждена**.

### 8.5. Shared client semantics и Android portability

**[CONSOLIDATED]** Reuse — это модели, контракты, состояния экранов, форм, workflow actions, messages и semantic design tokens. Копировать Qt-owned lifecycle/объекты в Android «как есть» — ошибка. `presentation/common` можно расширять, а runtime bootstrap необходимо освободить от Qt. При появлении второго независимого frontend следует выбрать: общий package, schema/codegen или повторение малых projection adapters по contract. **До сравнения language/toolchain consumer set отдельный `stratbox-design`/`stratbox-client` репозиторий остаётся UNKNOWN.**

### 8.6. Design tokens, motion и accessibility

**[CONSOLIDATED]** Interface theme принадлежит продуктовой design authority; semantic tokens выражают смысл (`surface`, `text`, `critical`, `selection`, `focus`, `progress`, `warning`) и адаптируются в Qt/CSS/mobile-native. Extension может добавлять **ограниченные декларативные artifact style resources**, но не произвольно инжектировать QWidget/HTML/CSS/QSS и менять основные navigation/permissions.

Animation — projection causal state change, а не источник прогресса. Reduced motion, high contrast, text scaling, keyboard navigation, focus semantics, contrast, touch-target sizing, localization — проверяемые требования. Для Web используем WCAG 2.2 как внешний ориентир, но соответствие Strategy Box сейчас **не сертифицировано**. [EXT-WCAG]

### 8.7. Settings — только действительно управляемые параметры

Разделить пять сущностей: `UserPreferences` (тема/язык/уведомления), `SurfaceState` (окно, фильтр, вкладка), `DraftState` (незапущенные параметры), `RunParametersSnapshot` (immutable параметры при запуске), `ManagedPolicy/RuntimeBinding` (права, окружение, storage, provider choices). Последняя группа обычно read-only для обычного пользователя. Убирать устаревшие/мертвые переключатели, а не переносить их все в красивый новый Settings dialog.

Минимальный набор настроек должен подтверждаться пользовательской необходимостью, иметь semantic owner, scope и default. `available theme` и `report artifact style` — разные группы; метаданные автора и оформление артефакта должны быть явно отделены от interface theme.

---

## 9. Platform Boundary: AppDock, узел и managed environment

### 9.1. Двухсторонняя граница

**AppDock → Strategy Box:** предоставляет нормализованный node/session identity context, selected Data/workspace roots, managed runtime lifecycle, environment readiness, process health, installation/version provenance, возможно remote transport и платформенные разрешения.  
**Strategy Box → AppDock:** публикует readiness/capabilities, application health summary, launch diagnostics, safe structured problem refs, clean/unclean shutdown и необходимые service endpoints/actions без раскрытия предметной базы и внутренних реализаций.

Пользователь может получить диагностику платформы из AppDock даже при падении поверхности Strategy Box. Однако AppDock не обязан понимать `SORS` evidence или `Work` acceptance. AppDock problem occurrence не превращается автоматически в терминальный status Job.

### 9.2. `Node`, `Session`, `Host`, `Worker`

- **Node** — управляемая платформа/среда в словаре AppDock.
- **Session** — платформенный контекст участия/активации, не Work/Run.
- **Application authority** — Strategy Box product truth в scope определённого узла/сервера.
- **Host/service process** — возможный физический носитель application authority.
- **Worker/ExecutionBackend** — конкретное исполнение Job, не обязательно та же машина, где GUI.

Лингвистическая коллизия слова «host» не должна маскировать собственника: AppDock host/remote substrate и `stratbox-host` как кандидат прикладного runtime — разные responsibilities. В документации полезнее писать `platform host` и `Strategy Box application service`, когда контекст неоднозначен.

### 9.3. Contract maturity и неизвестные внешние зависимости

**[CURRENT]** `stratbox-windows` умеет читать activation context/runtime-state, проверять bindings и выдавать диагностику, но manifest пока `local/foreground/Windows`.  
**[UNKNOWN]** Как именно новая headless application service будет регистрироваться, запускаться, обновляться, иметь service identity и remote routing в соответствующей будущей версии AppDock — требует согласования с владельцем AppDock и его актуальным SDK/manifest contracts. Нельзя придумывать имена несуществующих IPC endpoints и выдавать их за готовую интеграцию.

### 9.4. Boundary health: несколько разных «готов»

Развести:

1. Platform Node healthy (AppDock);
2. Strategy Box service process alive;
3. Application authority DB/recovery ready;
4. Core import/contracts/version compatible;
5. конкретные data/source/capability providers available;
6. конкретная Operation applicable and authorized для запроса;
7. последнее выполнение имеет terminal outcome.

«Process running» не означает «можно безопасно сделать отчёт»; «плагин импортировался» не означает «доступны данные»; «приложение закрыто» не означает «фоновые Work отменены».

---

## 10. Physical Architecture: кандидат размещения по пакетам, процессам и репозиториям

### 10.1. Порядок декомпозиции

Программа специально запрещает метод «придумали красивый компонент — создали repository». Для каждой физической границы требуется ответ на шесть вопросов:

1. Есть ли независимый semantic owner и отдельный контракт?
2. Нужны ли другой процесс/lifecycle и восстановление после crash независимо от UI?
3. Есть ли другой consumer, в том числе Web/Android/CLI/server?
4. Различаются ли технические зависимости, язык, packaging и release cadence?
5. Есть ли отдельная trust/security/performance boundary?
6. Стоимость разделения оправдана реальными integration/contract tests и сопровождением?

Первые два вопроса определяют логическую границу. Последующие определяют целесообразность physical package/repository/process split. Отдельный процесс может существовать **без отдельного репозитория**, а независимый package — **без собственного постоянно работающего сервиса**.

### 10.2. Candidate deployment graph

```text
 [AppDock product/world manifest + managed environment]
                         │
       provision packages / configure roots / launch
                         │
   ┌─────────────────────┴────────────────────────────────┐
   │                                                      │
   ▼                                                      ▼
[Strategy Box application service]                [Windows UI process]
  product authority / command API                   native presentation
  DB + outbox + jobs + scheduler                    UI local preferences
  data/artifact catalog                            projections/commands
  admission / ACL / recovery                                │
   │                                                       │
   ├── in-process or subprocess workers                     │
   │       │                                                │
   │       ▼                                                │
   │   stratbox core ←── neutral execution/provider binding │
   │       │                                                │
   │       ▼                                                │
   │   workspace / snapshots / artifacts                    │
   │                                                        │
   └────── command/query/event contract ────────────────────┘
                      │
            [Web / Android clients]
           (when separately implemented)

 Local profile: API may be local IPC; service and workers colocated.
 Server profile: API networked; worker pools and DB topology may differ.
 The product semantic contract is the same.
```

**[TARGET-HYPOTHESIS]** Сначала проверить локальный headless service с существующим Python core, DB на локальном диске и простым worker model. Отделить remote workers только если workload и AppDock service/host requirements этого требуют. Web consumer полезен как архитектурный тест независимости UI; Android может идти позже, без новой application ontology.

### 10.3. Repository/package/process decision matrix

| Имя / carrier | CURRENT | Целевая ответственность | Physical decision |
|---|---|---|---|
| `stratbox` | существует: `0.8.0` | bank/macro domain, source/registry, semantic operation, domain evidence, neutral FileStore/format contract | **RETAIN** repository + library, независимо полезен |
| `stratbox-windows` | существует: `0.1.0` | Windows client, Qt native UX, local state, platform adapters | **RETAIN**, вывести authority/QThread runtime из client-ownership |
| Strategy Box application core (логическая роль) | частично живёт в Windows | Work/Job/Automation/Collaboration/Artifact index/ACL | **REQUIRED logical**, repository **UNKNOWN** |
| `stratbox-host` (имя-кандидат) | отсутствует как подтверждённый standalone owner в baseline | headless authority/service, API, scheduler, persistence, jobs, recovery | **STRONG TARGET-HYPOTHESIS** отдельного runtime process; отдельный repo требует gate |
| `stratbox-web` | реализации в baseline нет | web renderer/client | **CONDITIONAL**, когда есть реальный web consumer |
| `stratbox-android` | реализации в baseline нет | native mobile/companion renderer | **CONDITIONAL**, после мобильного scope/pilot |
| `stratbox-design` | нет как подтверждённого required package | semantic UI token definitions/test fixtures | **DEFER PHYSICAL SPLIT**; logical owner обязателен |
| generic extension distributions | механизм/сеam существует | bounded providers/resources/capabilities | **EXTERNAL**: только нейтральный public contract |
| AppDock | внешний проект | provisioning, Node/Session, managed processes, platform health and transport | **EXTERNAL OWNER**, explicit integration contract |
| внешний machine/cognitive consumer | не является текущим executor Strategy Box | propose/select/use permitted capabilities | **EXTERNAL CONSUMER**, no duplicated Work truth |

### 10.4. Самая разумная начальная package topology

**Рекомендуемый проверяемый вариант A:** оставить `stratbox` и `stratbox-windows` на местах, а headless application runtime выделить сперва как самостоятельный **package/module boundary с отдельным сервисным entrypoint**; его repository ownership решить после первого Windows+independent Web/API consumer и демонстрации отдельного выпуска/тестирования. При высокой независимости release/process правомерен отдельный `stratbox-host` репозиторий. Если implementation governance проще при отдельном repo сразу и соответствующие tests/owners имеются, вариант B возможен, но не вытекает автоматически из current study.

**Вариант B:** отдельный `stratbox-host` repository с собственным package и процессом. Плюсы: ясный lifecycle, CI/security/dep isolation, независимый worker/service release. Минусы: дополнительная зависимость двух репозиториев, межпакетное версионирование, необходимость согласовать service API и AppDock packaging, риск premature framework. **Порог выбора** — демонстрация end-to-end на двух consumer surfaces + remote/background lifecycle, а не соглашение об имени.

**Вариант C — оставить authority в `stratbox-windows`** — **SUPERSEDED как целевой**: UI shutdown, Android/Web, multi-user, scheduling и durability становятся зависимыми от Qt process. При этом временный локальный single-process режим возможен для development, если его не выдавать за multi-client/24×7 profile.

### 10.5. Техническая зависимость и запреты

```text
stratbox (domain)
    imports no application/surface/AppDock modules

application authority
    depends on published stratbox semantic contracts
    may consume AppDock boundary adapters
    provides its own product command/query/events

surface clients
    depend on application contract/projections
    do not import backend implementation as source of truth

AppDock
    invokes/hosts package entrypoints via its documented contracts
    does not import banking domain internals
```

Qt, platform-native libraries, terminal clipboard, browser/CSS и Android OS services не должны становиться зависимостями доменного `stratbox` или headless application runtime. `stratbox` можно использовать direct standalone как pure library для ноутбуков и чужих Python consumers.

### 10.6. Никакого автоматического распределения по микросервисам

Система пока не доказывает необходимости message broker, event-sourcing cluster, microservice mesh, отдельного API gateway, distributed knowledge graph, распределённого CAS и отдельного scheduler-server. Эти технологии остаются возможными реализациями реальных требований, но **не входят в обязательную Target Architecture**. На следующем этапе сильнее компактный headless node service с ясными boundaries, SQL metadata, managed files и воспроизводимыми domain jobs.

---

## 11. Обязательные contracts между логическими owner-ами

**[TARGET-HYPOTHESIS]** Контракты лучше описывать раздельно и создавать в порядке реального demand. Ниже — **минимальная cross-boundary contract map**, а не огромный единый SDK.

| Контракт | Provider → Consumer | Минимальное содержание | Gate |
|---|---|---|---|
| `OperationDefinition/Invocation/Result` | `stratbox` → application/CLI | schema, version, applicability, effect profile, typed result, failures | 2 real domains + CLI/UI consumer |
| `SourceSnapshot/RegistrySnapshot/DatasetVersion` | `stratbox` → result/artifact | source/registry identities, semantic context, hash/vintage | revised-source fixture |
| `ExecutionPlan` | Planner → JobManager | immutable definition/binding/inputs/policy/effects/resource snapshot | retry/upgrade test |
| `ExecutionBackend` | authority → local/remote worker | dispatch/cancel/heartbeat/effect receipt/reconcile | lost-worker/fencing test |
| `Command/Query/Subscription` | application → surfaces/AI | principal, expected revision, idempotency, pagination/opaque cursor, projection ACL | multi-client concurrency test |
| `ArtifactManifest/ArtifactRef` | core/result → catalog/storage | content identity, provenance, version, staging/commit | crash and relocation test |
| `Authorization/Approval` | identity/policy → admission | principal, scope, effect, policy revision, expiry, audit | revoked grant test |
| `AutomationSpec/Occurrence` | scheduler → admission | trigger identity, timezone, decision, overlap/catch-up, actor | DST, duplicate trigger, restart |
| `Problem/Diagnostic` | domain/authority → AppDock/UI | coded failure, correlation, severity, safe context, evidence ref | redact and incident correlation |
| `Projection/ActionDescriptor` | authority → native surfaces | entity revision, visibility, actions, stale flag, cursors | Web+Windows semantic equivalence |
| `ExtensionDescriptor/Binding` | neutral contribution → core/application | compatible contracts, selection, health, conformance | synthetic provider tests |
| `AppDock Activation/Health` | external platform ↔ Strategy Box | managed paths, Node/Session, lifecycle, readiness, error boundary | owner-to-owner integration |

### 11.1. Идентичность и время — общая дисциплина

Каждый критический агрегат получает stable ID, `definition_version` (где применимо), `revision` mutable state и immutable snapshot reference для исполнения/результата. Время различается:

- **event time** — когда наблюдение/публикация относится к периоду;
- **publication/vintage time** — когда издатель выпустил/пересмотрел данные;
- **retrieval time** — когда bytes получены;
- **admission/dispatch/attempt/commit time** — жизненный цикл работы;
- **notification/read time** — пользовательские проекции.

Event ordering должен опираться на authority sequence/revision, а не только на wall-clock. В cross-system trace нужны correlation/causation IDs, но это не означает один глобальный sequence для всех узлов мира.

### 11.2. Запрос и ответ — не только JSON schema

Структура должна включать qualifiers:

- class of effects and authorization requirements;
- retry/idempotency/cancellation semantics;
- environment/source capability requirements;
- schema/value validation, type/unit/perimeter;
- explicit limitations and assurance level;
- observable progress and terminal outcomes;
- backward-incompatible change policy;
- redaction/visibility class.

`Schema valid` говорит только о форме данных. Contract conformance должна проверять и семантику поведения.

### 11.3. Нейтральный минимальный error envelope

```text
code · layer · severity · retryability · effect_state
entity_ref · run_ref · attempt_ref · source_ref
message_safe · diagnostic_ref · correlation_id
failed_precondition? · partial_artifacts? · remediation_hint?
```

Публичный domain код возвращает typed errors; application runtime определяет lifecycle outcome; AppDock получает безопасную platform problem projection. Raw traceback хранится в защищённом техническом evidence/log, а не в multi-user banner. Все эти уровни связаны, но не должны перегружать один тип `Exception`.

---

## 12. Trust, Safety & System Qualities — provisional сквозной синтез недостающей темы 08

**Статус раздела:** **консолидированное предложение**, построенное по исследованиям 00–07 и релевантным `02-base-study`. Он не подменяет отдельный полный Research темы 08, отсутствующий среди доступных документов на момент проверки. Для регуляторных, юридических, threat-model и ресурсных параметров остаются **UNKNOWN**.

### 12.1. Три независимых контура доверия

1. **Epistemic trust:** можно ли утверждать, что число/тезис обоснован данным источником и методикой? Owner: `stratbox`/domain result, evidence, qualified claim.
2. **Effect/authority trust:** кто вправе совершить действие, используя какую capability, с какими последствиями? Owner: application authority + policy и platform identity boundary.
3. **Operational trust:** успешно ли реально исполнялась задача, целостны ли файлы/DB, жив ли узел и можно ли восстановиться? Owner: application execution/recovery + AppDock platform health.

**Никакой из этих уровней не усиливает другой автоматически.** Наличие разрешения не доказывает корректность расчёта, правильный расчёт не разрешает публикацию/удаление, successful worker не делает источник свежим, а trusted extension package не разрешает опасную операцию конкретному пользователю.

### 12.2. Reliability и ошибочные fallback

- `listdir` пустой ≠ storage unavailable, `exists=False` ≠ timeout, `not found` ≠ permission denied.
- Destructive action с частично успешным effect возвращает typed partial/unknown и verification status.
- File/data publication проходит staging/checksum/visible commit barrier.
- Незавершённая внешняя операция после timeout не объявляется безопасно повторяемой без effect reconciliation.
- Crash after DB commit/before artifact finalization разрешается replay/reconcile; crash после artifact bytes до DB commit не делает объект видимым.
- История/схемы DB: corruption должна давать diagnosable degradation/recovery, а не «у пользователя ничего никогда не было».

В `stratbox` FileStore/IO нужны unit/contract tests для backend unavailable, unreadable, overflow, large streams, partial write, rename/copy/delete. Текущие 132 test functions по baseline относятся в основном к SORS/forms/industries; системные boundary и Windows states тестируются неравномерно. [B-CORE], [B-WINDOWS].

### 12.3. Security и authorization

**[TARGET-HYPOTHESIS]** Нужна проверяемая `Principal → Role/Grant → Object/Action/Effect` модель. Её принципы:

- default deny для неизвестных полномочий и risky effects;
- capability existence не даёт права вызова;
- approval scoped к плану/эффекту/версии/policy; новый эффект требует повторного approval;
- в read-only projections применяются field-level redaction и object-level ACL;
- secrets не передаются через event history/telemetry/Artifact metadata;
- machine actor проходит те же policy checks, что человек;
- workspace/Artifact refs проходят canonical path checks, namespace scoping и защита от traversal/symlink escape;
- plugin code получает лишь предусмотренную среду исполнения; in-process plugin **не** считается sandbox;
- web API требует threat modeling auth/session/CSRF/XSS/SSRF/download control; мобильный клиент — platform-native secret storage and local-cache policy;
- side-effectful operation без проверенного actor scope не исполняется даже если frontend показал кнопку.

OWASP ASVS 5 — полезный внешний контрольный checklist для web/API безопасности, но **не** доказательство compliance проекта. [EXT-ASVS]

### 12.4. Observability и incident propagation

**[CONSOLIDATED]** Не путать четыре сигнала:

| Signal | Что показывает | Durable? | Owner |
|---|---|---|---|
| Semantic event | кто что сделал и каким стал агрегат | при значимых переходах да | application authority |
| Progress update | текущий этап/количество/оценка без ложной точности | часть может быть coalesced | executor/application |
| Diagnostic/log/trace | почему/где возникла ошибка | bounded retention и redaction | соответствующий runtime/platform |
| `Problem`/notice/notification | нормализованная проблема, доставка затронутым | problem evidence + delivery receipt | application + AppDock projection |

OpenTelemetry предлагает стандартные conventions для spans, metrics, logs и events; его смысловые принципы полезны для correlation, но внедрение полного стекa OTel/collector нельзя считать обязательным в первом local profile. [EXT-OTEL]

Событие с другого пользователя на общем узле нужно показывать **только разрешённой аудитории** и в безопасной форме: краткий код/влияние/affected run без credentials, filesystem secrets, private source data и raw traceback. Дубли проблем следует группировать по fingerprint/source/time scope; приложение сохраняет первичную причинную историю, платформа может иметь собственный ProblemRef. Cross-user broadcast по умолчанию не является безопасным решением.

### 12.5. Concurrency и idempotency

- Все команды на shared aggregate требуют `expected_revision` либо эквивалентной conditional semantics.
- Transactional uniqueness/idempotency охраняется authority, не GUI или сетевым клиентом.
- Resource lock, worker lease и user-level approval различаются и имеют expiry/fencing.
- Queue fairness/quotas защищают от «вечной» фоновой задачи, блокирующей интерактивные действия.
- Retry в effectful pipeline разрешается лишь при known-safe state; после ambiguous outcome выполняется reconciliation.
- Параллелизм определяется независимостью ресурсов и выходов, а не числом окон.

### 12.6. Воспроизводимость и версии

Для существенного результата фиксировать: source/registry snapshots, operation/scheme definition version, execution binding, settings/policy revision, transform/solver version, approved parameters, content digest, warnings and assumptions. Изменение одного элемента не переписывает старый record. Предметные доработки и повышение точности должны создавать новую version/Run/Result, а не ретроактивно усиливать ранее неподтверждённые claims.

### 12.7. Performance и ресурсные бюджеты

Ключевые риски имеют разные owners:

- **Core:** DataFrame/memory churn, large ZIP/PDF/XLSX streams, expensive SORS solver/matrix generation, source retries;
- **Runtime:** Job concurrency, CPU/RAM/disk/network budgets, worker isolation, cache eviction, log retention;
- **Surface:** медленные компьютеры, virtualized lists, bounded inspector/load, lazy previews, reduced UI motion;
- **AppDock:** managed env startup, process supervision, update/repair and platform telemetry.

**UNKNOWN:** допустимые задержки UI, throughput, sizes/quotas, tail-latency и SLO каждого deployment profile. Нельзя честно указать «максимум 2 ГБ RAM» без real workload/target hardware. Следует сформировать нагрузочные профили: 1) локальный один пользователь; 2) один узел/несколько пользователей; 3) web/self-hosted; 4) тяжёлый SORS; 5) degraded/offline.

### 12.8. Accessibility и portability

Accessible keyboard-only flow, screen readers/semantic labels, high contrast, reduced motion, locale/number/date formats, error recovery in forms и responsive layouts — **system qualities**, а не декоративные надстройки. Windows/Linux host differences, path normalisation, file locking, child process lifetime и mobile storage permissions тестировать отдельно по платформам. WCAG 2.2 применим как опорный web стандарт, но фактическая проверка ещё впереди. [EXT-WCAG]

### 12.9. Recovery objectives

**[UNKNOWN]** RPO/RTO, permitted data-loss window, offline tolerance, node restore SLA, archive retention и journal pruning policy. Их нужно определять по классам данных: длительные Work и proof manifests имеют более высокую ценность, чем transient UI cursor или кеш preview. Перед выпуском shared-node сервиса обязателен настоящий restore rehearsal, включая DB+files consistency, потерю worker lease, сохранение старых artifact hashes и невозможность двойного эффекта.

### 12.10. Security/operability acceptance suite — минимальный набор

| Test | Инъекция / сценарий | Ожидаемое доказательство |
|---|---|---|
| TQ-01 | storage недоступен при `exists/listdir` | typed unavailable, не `False`/`[]` как успех |
| TQ-02 | обрыв записи после половины XLSX | committed artifact отсутствует; staging recoverable |
| TQ-03 | fail после DB commit до publish | reconciliation, без ложной карточки успеха |
| TQ-04 | двойной одинаковый command | один effect/admission identity, два безопасных ответа |
| TQ-05 | lost worker after external effect | unknown/receipt/reconcile, нет blind retry |
| TQ-06 | user B пытается увидеть Work A | denied/filtered projection, отсутствует metadata leak |
| TQ-07 | approval revoked while queued | check-before-effect, blocked/denied |
| TQ-08 | upgrade extension during active run | plan binding pinned; no silent switch |
| TQ-09 | crash GUI while scheduler active | job lifecycle independent; no ghost running flag |
| TQ-10 | restore backup as clone | new generation/fencing, no duplicated action |
| TQ-11 | offline Android sees stale progress | explicit stale timestamp/disabled risky actions |
| TQ-12 | source officially revised in place | new SourceSnapshot/Result; old retained with impact status |
| TQ-13 | registry schema changes | version pinning and validation, no silent semantic drift |
| TQ-14 | offline/online actor and principal mismatch | authorization applies to actual actor; audit complete |
| TQ-15 | font scaling/reduced motion/keyboard | usable actions, visible focus, no animation as truth |

Эти проверки — **предложенные gates**. Их выполнение в действующем Strategy Box на 09.10.2026 не заявляется.

---

## 13. System-wide invariants: минимальная конституция будущей системы

Статус: **CONSOLIDATED** семантические правила (если иначе не оговорено); превращение в принятые Product Requirements требует отдельного admission. Каждый инвариант сформулирован так, чтобы его можно было опровергнуть тестом.

| ID | Инвариант | Контрольный контрпример / проверка |
|---|---|---|
| INV-01 | Одно семантическое значение имеет один authoritative owner в данном scope | GUI и host одновременно объявляют разные terminal Run outcome |
| INV-02 | `stratbox` остаётся вызываемым без GUI и AppDock | импорт core тянет Qt/AppDock runtime |
| INV-03 | Product Work/Job переживает закрытие клиента при включённом managed service | закрытие окна отменяет scheduler или теряет active Job |
| INV-04 | Один управляемый execution spine для всех источников активации | AI и background ведут независимые inconsistent run histories |
| INV-05 | Capability/definition, binding, invocation, plan, run и attempt — отдельные identity | update пакета изменяет исполняющийся Run без нового Plan |
| INV-06 | Work и Thread отделены, один Work допускает несколько запусков | один failed Run уничтожает долгоживущую Work |
| INV-07 | `Scenario` не создаётся автоматически для каждой низкоуровневой функции | технический helper произвольно появляется в UI catalogue |
| INV-08 | `ExecutionOutcome` ≠ аналитическая достоверность ≠ принятие Work | valid XLSX автоматически закрывает аналитическое поручение |
| INV-09 | `UNKNOWN` сохраняется в данных, эффектах и состоянии | timeout возвращает `success=False` при возможном уже выполненном effect |
| INV-10 | Проблема backend не маскируется пустым результатом | `listdir()` возвращает `[]` после отсутствия сети |
| INV-11 | Destructive operation не завершает успехом непроверенный частичный effect | ренейм удаляет source после skipped copy |
| INV-12 | idempotency соблюдается на границе реального side effect | повтор сетевого запроса случайно создаёт второй output/delete |
| INV-13 | Авторизация проверяется на стороне authority для каждого эффекта | UI скрывает кнопку, но API позволяет обойти grant |
| INV-14 | Installed extension ≠ active/authorized/ready capability | первый entry point сам выбирается для risky operation |
| INV-15 | In-process extension не объявляется sandbox | сторонний код выполняется с полномочиями процесса, несмотря на ярлык plugin |
| INV-16 | Снимок источника и текущая доступная публикация различаются | исправление CSV по прежнему URL переписывает старую доказательную версию |
| INV-17 | Published number, canonical observation и inferred value сохраняют epistemic tier | округлённое значение silently трактуется как точное |
| INV-18 | Artifacts имеют identity выше физического path | перемещение файла уничтожает весь audit lineage |
| INV-19 | Partial/staged artifact невидим как committed | после crash пользователь скачивает недописанный файл |
| INV-20 | Каждый significant Result связан с исходниками/версией обработки/исполнением | отчёт не может указать исходный source snapshot |
| INV-21 | Кэш не подменяет provenance или authorization | результат из другого scope используется как «общий» без проверки |
| INV-22 | User read state не мутирует общий event | один пользователь помечает событие прочитанным у другого |
| INV-23 | Client subscription может восстановиться после reconnect с ACL | потерян cursor приводит к silent пропуску terminal outcome |
| INV-24 | Node/Session AppDock не заменяют Work/Run Strategy Box | platform heartbeat выводится как успешное выполнение отчёта |
| INV-25 | Shared mutation имеет version/idempotency guard | два пользователя перетирают разные поручения без conflict |
| INV-26 | Domain diagnostics и platform incident связаны, но не слиты | секреты из technical traceback видны всем участникам узла |
| INV-27 | UI theme/animation не определяют предметное состояние | цвет/анимация «успеха» появляются раньше durable commit |
| INV-28 | Дизайн семантический, а рендеринг platform-native | Qt Widgets являются обязательными для headless runtime |
| INV-29 | Persistent schema изменяется управляемо, независимо от обещаний backward API compatibility | релиз удаляет Work database без migration/backup decision |
| INV-30 | Новый физический компонент имеет доказанную ownership/lifecycle причину | создан отдельный сервис без отдельного consumer/failure/perf boundary |
| INV-31 | Нет невидимого усиления прав AI, automation и delegated actors | machine actor вызывает effect, запрещённый инициирующему principal |
| INV-32 | Необратимые решения/отчёты не усиливают Evidence при презентации | forecast с допущением отображён как официальный факт |

**Приоритет**: INV-01/03/04/08/09/10/11/12/13/18/19/20/24 являются release blockers для первого shared-node headless runtime; INV-16/17/32 — blockers для доказательных аналитических результатов; INV-27/28 — blockers для переносимости UI.

---

## 14. Матрица ownership: один system map для implementation owners

**Смысл `owner` — кто определяет контракт и хранит authority**, а не кто импортирует метод.

| Responsibility | Semantic owner | Current carrier | Candidate physical target | Статус |
|---|---|---|---|---|
| Macro/banking algorithms, methods | `stratbox` | `stratbox` | same | CURRENT / CONSOLIDATED |
| Sources, reference models, canonical observations | `stratbox` | uneven domain modules/resources | versioned core/domain contracts | CONSOLIDATED |
| Statistical restoration, evidence tiers | `stratbox` | domain SORS | specialized domain subsystem | CURRENT / CONSOLIDATED |
| Canonical OperationDefinition / domain results | `stratbox` | mixed domain facades | stable domain facade/registry | TARGET strong |
| FileStore and format-neutral IO ports | `stratbox` | `base` | core contracts, backend adapters outside | CURRENT / CONSOLIDATED |
| Managed source/network provider selection | neutral public contract owner | partial core runtime | verified binding resolver | TARGET |
| Work/Thread/Run semantics | application authority | partial Windows cases/events | headless service | CONSOLIDATED logical |
| Planner/JobManager/automation | application authority | sequential Qt runner + scaffolds | headless service/worker | TARGET strong |
| Product authorization/effects/approvals | application authority | incomplete | service auth/effect policy | TARGET strong |
| Participant mapping/read cursors/assignments | application authority | local Windows data | durable shared authority | TARGET strong |
| Platform user/session/node identity | AppDock | existing activation context | external platform contract | CURRENT boundary |
| Platform process/service management | AppDock | local foreground activation | managed headless process | EXTERNAL DEPENDENCY |
| Product semantic events/problems | domain + application authority | local logs/events | typed events + safe platform bridge | TARGET |
| Platform incidents/health | AppDock | external platform | AppDock | EXTERNAL |
| Artifact semantics/manifest/provenance | core/domain | output paths + domain results | common ArtifactRef/manifest contract | CONSOLIDATED |
| Artifact catalog/visibility/retention | application authority | local Windows projection | transactional service catalog | TARGET |
| Artifact bytes/materialization | storage capability | workspace/FileStore | immutable content + adapters | TARGET |
| Windows UI layout/rendering | `stratbox-windows` | Qt widgets | Qt client | CURRENT |
| Cross-surface projection schema | application/product surface contract | partial `presentation/common` | common schema or shared client boundary | TARGET |
| Web native rendering | future `stratbox-web` | none | browser client if demand | UNKNOWN deployment |
| Android native rendering | future `stratbox-android` | none | mobile companion/full client | UNKNOWN deployment |
| UI tokens/visual/accessibility contract | product design owner | QSS/assets in Windows | versioned tokens; package optional | CONSOLIDATED logical |
| Report/artifact style resources | `stratbox` artifact/export contract | Excel registry + local renderer patterns | versioned ArtifactStyleSet | TARGET |
| Device layout/preferences | each client | Windows config | each platform | CONSOLIDATED |
| Managed policy/bindings | AppDock/platform plus application policy by scope | scattered | explicit precedence and read-only projections | TARGET |
| External machine planning/interpretation | external cognitive consumer | not a product authority | permitted public capabilities only | BOUNDARY |

### 14.1. Нормативная dependency rule

**Application runtime зависит от core contracts, не наоборот. Surface зависит от application contract, не наоборот. AppDock — самостоятельный внешний contract.** Никакая тема бизнеса в `stratbox` не должна требовать `stratbox-windows` для своего расчёта. Никакое ядро Windows/Web/Android не может держать права и историю только в оперативной памяти конкретного renderer.

### 14.2. Почему physical/semantic границы отличаются

- `Artifact` логически один объект, но metadata indexing и bytes естественно принадлежат разным owners.
- `Problem` имеет semantic cause в исполнении и platform evidence в AppDock; это не два одинаковых журнала.
- `CapabilityDefinition` и specific provider могут выпускаться разными distributions, но policy выбора находится в application authority.
- `Principal` отображает platform identity, однако product grants/assignment/Work ACL принадлежат приложению.
- `ViewModel` воспроизводим из product data; он не требует server-side forever state для каждой открытой вкладки.

---

## 15. Conflict / Superseded Register: что разрешено окончательно, а что нет

### 15.1. Конфликты, разрешённые через разложение по ответственности

| Код | Исходное столкновение | Результат темы 09 | Статус |
|---|---|---|---|
| CF-01 | `Command` vs `Operation` | Operation — предметный stable use case; Command допускается как внутренний technical action | CONSOLIDATED |
| CF-02 | `Scenario` vs `Scheme` | продуктовый authored use case vs reusable typed machine composition | CONSOLIDATED |
| CF-03 | `Cascade` vs Scheme | UX/крупный workflow profile; собственная canonical entity только при governance proof | PARTLY OPEN |
| CF-04 | `Case` = `Work` | current Case run-like; целевая Work долговечна, CaseView — projection | CONSOLIDATED |
| CF-05 | `Run` vs `Job` | Run — эпизод Work; Job — schedulable unit; Attempt — конкретная попытка | CONSOLIDATED semantic / target schema |
| CF-06 | Scheduler в AppDock или в Strategy Box | product trigger/admission/workflow — Strategy Box; process/host lifecycle — AppDock | CONSOLIDATED |
| CF-07 | Artifact Catalog в core или host | core artifact semantics/evidence, runtime index/ACL, storage bytes | CONSOLIDATED |
| CF-08 | FileStore = Artifact Store | нижняя physical абстракция vs logical Artifact identity/commit | CONSOLIDATED |
| CF-09 | Background — тип сценария | background — execution mode, AutomationSpec — launch definition | SUPERSEDED старый enum как target |
| CF-10 | Один registry для capability/plugin/availability | разные logical views и binding status; physical co-location возможна | CONSOLIDATED |
| CF-11 | Trusted plugin = allowed action | code trust ≠ actor authorization/effect policy | CONSOLIDATED |
| CF-12 | Scenario-first vs Work/Thread-first | сценарий — быстрый вход; Work — durable цель; Thread — conversation context | CONSOLIDATED |
| CF-13 | SQLite vs PostgreSQL | deployment profiles, одна semantics | NOT A CONFLICT |
| CF-14 | Web/Android как копии Windows | разные renderers одной product semantics | CONSOLIDATED |
| CF-15 | UI theme и report style | разные визуальные контракты, разные owners | CONSOLIDATED |
| CF-16 | AppDock observability vs Strategy Box observability | application semantic state и platform problem evidence связаны refs | NOT A CONFLICT |
| CF-17 | AI-specific operations vs general capability | один каталог с context-filtered machine projection | SUPERSEDED duplicate architecture |

### 15.2. Настоящие неразрешённые архитектурные развилки

| Код | Варианты | Предпочитаемое направление / причина незавершённости |
|---|---|---|
| CF-18 | application semantic package и service в текущем repo **vs** отдельный `stratbox-host` | сильная гипотеза service, но repository split требует выпуск/consumer lifecycle proof |
| CF-19 | shared client library **vs** schema/codegen + native local view models | проверить Windows+Web+Android tooling; не преждевременно вводить новый repo |
| CF-20 | design tokens в current package **vs** отдельный `stratbox-design` | нужен второй renderer/independent release cadence |
| CF-21 | обязательный CAS **vs** immutable ordinary managed layout | решить на storage/retention/large-artifact workload |
| CF-22 | lightweight qualified claims **vs** universal ClaimStore/graph | реальные domain consumers ещё не требуют глобальной онтологической БД |
| CF-23 | RPC/IPC local service **vs** loopback HTTP **vs** network API | AppDock/service integration и security profiles требуют прототипа |
| CF-24 | SQLite local DB **vs** PostgreSQL server | выбирать per-profile по измеримой concurrency/ops нагрузке |
| CF-25 | Scheme DSL/typed-DAG physical representation | сертификационный pilot вложенной композиции нужен до спецификации |
| CF-26 | отдельный trigger watcher service **vs** встроенный scheduler | логическая automation ответственность одна; процессная граница зависит от нагрузки |
| CF-27 | persistent Work acceptance/Claim validation generalization | конкретные domain policies и реальные user tasks ещё различны |
| CF-28 | full-featured mobile client **vs** companion | mobile workflows/permissions/preview performance должны быть замерены |

### 15.3. Явно вытесненные идеи

**SUPERSEDED**: GUI/launcher внутри доменного `stratbox`; Qt thread как durable execution authority; scenario auto-generation на любую функцию как целевой принцип; `Scenario.kind=background` как отдельный двигатель; read/unread в общем event; местный JSON каждой поверхности как shared truth; постоянные самостоятельные AI operations; path/mtime как identity; успешный скачанный XLSX как доказательство корректного аналитического вывода; одно глобальное хранилище для всех фактов ради самого термина Knowledge; отдельный репозиторий под каждое логическое имя.

Ранние материалы `01-old-notes` остаются историческим свидетельством архитектурной эволюции. Они не имеют приоритета над нынешними реализациями и согласованными semantics.

---

## 16. Decision / Gap Register темы 09

**Назначение:** дать конкретный переход от Research Synthesis к Product Decisions и implementation probes. `Устойчиво` означает высокую межисследовательскую согласованность, **не** уже принятое решение Product owner. `Gate` — обязательный способ доказать возможность и корректность.

| ID | Решение/развилка | Статус | Следующий owner / gate |
|---|---|---|---|
| D01 | Headless `stratbox` как bank/macro semantic authority | УСТОЙЧИВО | core public API + CI |
| D02 | One product application runtime authority | УСТОЙЧИВО логически | headless Windows-independent pilot |
| D03 | Independent `stratbox-host` service | СИЛЬНАЯ ГИПОТЕЗА | service lifecycle, crash test, AppDock integration |
| D04 | Separate `stratbox-host` repository | UNKNOWN | release/consumer/isolation analysis |
| D05 | No mandatory `stratbox-core` duplicate repo | УСТОЙЧИВО | retain application semantics boundary without duplication |
| D06 | No mandatory `stratbox-design` repo now | УСТОЙЧИВО как принцип | revisit after two native renderers |
| D07 | Canonical semantic dictionary Work/Run/Job/Attempt | УСТОЙЧИВО | schema and cardinality pilot |
| D08 | Case current as UI projection, not new durable aggregate | СИЛЬНАЯ ГИПОТЕЗА | migrate Case UI against Work/Run |
| D09 | Scenario/Scheme distinct, Cascade UI profile | УСТОЙЧИВО / часть OPEN | nested scenario pilot |
| D10 | One JobManager/admission for managed work | УСТОЙЧИВО | long-running/cancel/restart test |
| D11 | Durable AutomationSpec/Occurrence | СИЛЬНАЯ ГИПОТЕЗА | cron/DST/misfire/dedup test |
| D12 | Owner scheduler = Strategy Box, lifecycle = AppDock | УСТОЙЧИВО | cross-owner API review |
| D13 | Resource claims, leases, effect receipts | УСТОЙЧИВО по смыслу | fault injection & concurrency |
| D14 | Effect-aware idempotency and UNKNOWN | УСТОЙЧИВО | lost worker/external side-effect test |
| D15 | Local node SQL metadata authority | СИЛЬНАЯ ГИПОТЕЗА | SQLite/WAL on local disk pilot |
| D16 | PostgreSQL server profile | УСЛОВНЫЙ ВАРИАНТ | concurrent clients/ops evidence |
| D17 | Current-state+events+outbox hybrid | СИЛЬНАЯ ГИПОТЕЗА | transactional durability and replay |
| D18 | Restoration epoch and fenced jobs | НОВОЕ БЕЛОЕ ПЯТНО | joint AppDock/node restore drill |
| D19 | Backups of DB+Artifacts coherent | НОВОЕ БЕЛОЕ ПЯТНО | consistent restore epoch proof |
| D20 | Immutable SourceSnapshot/RegistrySnapshot | УСТОЙЧИВО | revised-source and registry fixtures |
| D21 | DatasetVersion canonical semantics | СИЛЬНАЯ ГИПОТЕЗА | forms+escrow+SORS consumer proof |
| D22 | Epistemic Claim/Evidence qualification | УСТОЙЧИВО по смыслу | two domain claims, no heavy store upfront |
| D23 | Universal ClaimStore / knowledge graph | UNKNOWN/DEFERRED | real consumers and retrieval workload |
| D24 | Artifact ID + manifest + publication barrier | УСТОЙЧИВО | crash/relocation/cross-client tests |
| D25 | Mandatory CAS object store | UNKNOWN | dedup/retention/GC performance |
| D26 | Report style set different from shell Theme | УСТОЙЧИВО | cross-format renderer fixtures |
| D27 | Generic extension discovery/activation/binding separation | УСТОЙЧИВО | public synthetic conformance harness |
| D28 | Versioned Scheme DSL | СИЛЬНАЯ ГИПОТЕЗА | end-to-end typed DAG compilation |
| D29 | AI/automation uses same admission | УСТОЙЧИВО | actor identity/approval tests |
| D30 | Surface projection contract | СИЛЬНАЯ ГИПОТЕЗА | Windows+Web semantic equivalence |
| D31 | Android first as companion | СИЛЬНАЯ ГИПОТЕЗА | UX/power/security prototype |
| D32 | Android toolkit | UNKNOWN | native/Qt Quick comparative prototype |
| D33 | Deep-link/node routing | UNKNOWN | secure URL/identity/ACL contract |
| D34 | Search/index/notifications | UNKNOWN | workload, ACL filtering, retention |
| D35 | Object-level product authorization | УСТОЙЧИВО по смыслу | permission matrix and revocation tests |
| D36 | Security threat model + policy profiles | ОБЯЗАТЕЛЬНАЯ РАБОТА | external/platform/security stakeholder |
| D37 | Resource budgets, performance, SLO | UNKNOWN | target devices, load and fault tests |
| D38 | Accessibility/localization certification | NOT VERIFIED | cross-platform manual+automated audits |
| D39 | Core/Windows dependency + manifest + smoke drift | CURRENT ENGINEERING BLOCKER | pin/graph/tests correction |
| D40 | Current history JSON and Qt bootstrap | CURRENT ENGINEERING BLOCKER | authority extraction and typed migration |
| D41 | Dedicated Topic 08 synthesis | MISSING INPUT | отдельная 08, после чего revisit §12 и Decisions |
| D42 | Public/private hygiene | УСТОЙЧИВО / CURRENT concerns | neutral code/docs contract review |
| D43 | Historical read-only reproducibility after breaking APIs | УСТОЙЧИВО | snapshot/version recording + migration policy |

**Дисциплина перехода:** Dxx с «УСТОЙЧИВО» допускается переносить в Proposed Product Decision, но не в статус «уже реализовано». `UNKNOWN` закрывается либо конкретным experiment, либо осознанной отсрочкой с trigger condition.

---

## 17. Sequenced architecture roadmap: вертикальные срезы с выходными воротами

План — **не список ещё несуществующих репозиториев**, а порядок получения доказательств, при котором каждый шаг оставляет систему более работоспособной. Все этапы предполагают свободу breaking API changes при сохранении целостности важных данных.

### Stage 0. Санация baseline — P0, до любых новых крупных сервисов

**Owner:** соответствующие публичные implementation owners (`stratbox`, `stratbox-windows`), совместимость с AppDock согласуется отдельно.

Работы:

1. Синхронизировать core requirement в `stratbox-windows/pyproject.toml`, AppDock package graph и проверяемых tests/docs; выбрать release identity, а не механически подменить строку.
2. Исправить manifest 4.0 vs obsolete 3.0 assertions, задать раздельные version axes.
3. Очистить tracked `.tmp`, generated state, `.pyc` и некорректные `.gitignore` исключения в Windows owner.
4. Устранить публично-специфичную конфигурационную/документальную конкретику, оставить нейтральные providers/contract descriptions.
5. Включить CI: wheel→install→imports, manifest validation, baseline unit tests, negative dependency tests, optional extras, documentation path checks.
6. Зафиксировать clean baseline commit по каждому owner и совместимую release matrix.

**Gate G0:** clean install из package graph; baseline tests на выбранных Python версиях; отсутствие сломанных contract assertions; build/diagnostics в управляемой среде без скрытых локальных assumptions. До G0 нельзя считать существующую AppDock-поставку надёжным эталоном новой архитектуры.

### Stage 1. Canonical Operation + Source/Result pilot — P0

**Owner:** `stratbox`, независимый test consumer.

1. Выбрать реальные разнопрофильные операции `cbr.forms.build`, `escrow.history.build/export`, `frg.cleanup.plan/apply` (точные IDs — candidate, ещё не утверждены).
2. Стабилизировать typed Request/Result, failures, side effects и domain provenance без giant framework.
3. Свести SourceSnapshot/RegistrySnapshot/DatasetVersion на форме 802 и пересмотренном escrow source.
4. Проверить URL changes same source, schema evolution, provenance of one value and unknown evidence.
5. Ввести neutral capability descriptor/admission contract без обязательной отдельной plugin registry database.

**Gate G1:** один и тот же domain operation доступен из direct Python и synthetic application consumer, возвращает воспроизводимый snapshot/result, честные errors/UNKNOWN и сохраняет source provenance. Ядро не импортирует Qt/Application/AppDock.

### Stage 2. Headless local authority + Work/Run/Job spine — P0

**Owner:** будущий platform-neutral application runtime; physical repository decision пока открыт.

1. Выделить Work/Thread/Run/Job/OperationRun/Attempt семантические модели из текущих Qt run/case контуров.
2. Реализовать transaction-backed admission, command idempotency, current-state+events, local JobManager, cancellation request и safe result envelope.
3. Перенести Qt Coordinator в adapter; Qt не создаёт authoritative service objects.
4. Запустить один сложный сценарий, закрыть GUI, восстановить состояние через новый клиент; проверить stuck worker и process restart.
5. Вынести локальные preferences/drafts из durable runtime state; согласовать AppDock managed service activation.

**Gate G2:** headless operation с одной независимой client projection переживает GUI shutdown и service restart; sealed test подтверждает отсутствие Qt imports в application core; duplicate command и cancellation имеют корректные receipts.

### Stage 3. Artifacts, effects, recovery — P0/P1

**Owner:** `stratbox` (semantic manifest) + application runtime (catalog/admission) + storage adapter + AppDock lifecycle.

1. Создать ArtifactRef/Manifest, staging/verification/commit barrier, восстановление неполной публикации.
2. Ввести effect receipts, resource lock, lease generation, retry/reconcile policy.
3. Протестировать destructive FRG scenario как `plan → approval → apply → verify`.
4. Добавить atomic/transactional сохранение shared state, DB+artifact backup/restore rehearsal.
5. Развести structured product diagnostics и AppDock platform Problem projection.

**Gate G3:** crash/partial write/lost worker/two writers/duplicate destructive request не приводят к silent data loss, partial success или ложной восстановленной истории; все committed artifacts доступны по immutable ref независимо от physical path.

### Stage 4. Shared-node collaboration и trusted execution — P1

**Owner:** application runtime + AppDock boundary + security/Product decisions.

1. Principal mapping, per-Work/Artifact ACL, authorization before effects, Assignment/Approval lifecycle.
2. Per-principal read receipts, notifications, presence TTL, authorized cursor/replay.
3. Multi-user queuing and resource claims; concurrency/revision conflicts.
4. Typed capability selection, bindings, version pinning; synthetic neutral provider conformance harness.
5. Threat model и role policy: operator/admin/human/machine actor scopes.

**Gate G4:** два клиента одного узла безопасно работают с общими и закрытыми Work, одновременно запускают независимые Jobs, получают одинаковые terminal outcomes и не получают чужие secret/log/data fields. При отмене/отзыве approval эффект не выполняется без полномочий.

### Stage 5. Windows surface modernization + independent Web consumer — P1

**Owner:** `stratbox-windows`, application projection contracts, будущий web client.

1. Перевести центр на Work/Thread-first с каталогом Scenarios и view Запуски.
2. Вынести reusable presentation semantics и action schemas; UI получает state из authority snapshot/stream.
3. Добавить безопасный Explorer: mutable WorkspaceObject ≠ ArtifactRef; search/preview/display только по ACL.
4. Проверить Web client как **первый независимый consumer** того же API (REST+SSE — кандидат, не норматив).
5. Accessibility, performance, locale tests и reconnect behavior.

**Gate G5:** Windows и Web показывают одинаковую семантику Work/Run/Artifact, используют одни права и notifications, но имеют свои renderer/layout; закрытие одного клиента не меняет shared truth. При обнаружении самостоятельного build/release demand принимается решение о shared client package/design package.

### Stage 6. Durable automation, watchers, Schemes и machine consumers — P1/P2

**Owner:** application authority + domain capability registry.

1. Versioned AutomationSpec/TriggerOccurrence: расписание, source change, event, manual/API; DST/misfire/catch-up/overlap policy.
2. Scheme compiler typed DAG, explicit capabilities, bindings and effect plan.
3. External machine/AI consumer использует разрешённый тот же catalogue, policy/admission/receipts.
4. Возможность remote backend через согласованный AppDock service/transport boundary.
5. Приоритетно проверить один реальный ежемесячный источник и одну композицию из двух разных доменов.

**Gate G6:** repeat/duplicate occurrence после restart не создаёт второй эффект, AI и человек получают одинаковые публичные result/evidence semantics, remote unknown outcome корректно reconcilable.

### Stage 7. Android companion, расширение областей и качество эксплуатации — P2

**Owner:** будущий mobile surface + shared product contracts + platform adapters.

1. Companion profile: statuses, notifications, approvals, lightweight parameter forms, permitted launches and artifact preview.
2. Cross-device semantic consistency, mobile offline/staleness, safe notification privacy, deep links.
3. Уточнение Android toolkit по независимому PoC, без копирования Qt thread runtime.
4. Benchmarks по профилям локальный/multiuser/server/heavy data, accessibility certification, backup/recovery metrics, update compatibility and retention.

**Gate G7:** мобильное приложение не создаёт нового Work/Job world; любые отличия касаются navigation/input/offline support, но не полномочий, идентичностей, результата и истории.

### 17.1. Critical path и запрет неправильного порядка

```text
G0 baseline graph/CI
   ↓
G1 canonical domain operation + provenance
   ↓
G2 headless authority / transaction / independent GUI lifetime
   ↓
G3 effects + immutable artifact publication + recovery
   ↓
G4 authorization / shared-node / safe events
   ↓
G5 second consumer Web and UI semantics
   ↓
G6 automation / schemes / machine / remote
   ↓
G7 Android and operational hardening
```

Возможна разумная частичная параллельность: design token/accessibility исследования идут параллельно G1–G3; регистры и source governance улучшаются, пока выделяется host. Но **сложный AI, scheduler, multi-user и Web не должны становиться владельцами скрытого параллельного execution state**.

### 17.2. Дополнительные сквозные acceptance stories

**ST-A — Исправленная официальная публикация.** Один URL, новые bytes. Old SourceSnapshot/Result immutable, новый snapshot имеет собственный hash/vintage, Work получает revalidation recommendation, старый artifact остаётся объяснимым. Проверяет D20/D21/D22/D24.

**ST-B — Два автора и один отчёт.** Пользователь A запускает Work, B имеет read+approve, C не имеет прав. A закрывает окно, B принимает результаты, C не видит имя внутреннего артефакта. Проверяет D02/D13/D17/D35.

**ST-C — Automation after crash.** Scheduled occurrence commit зафиксирован, процесс завершился до dispatch. После восстановления admission/replay создаёт не больше одного соответствующего effect, при неизвестном внешнем эффекте выполняется reconciliation. Проверяет D11/D13/D14/D18.

**ST-D — Replacement of UI toolkit.** Qt consumer заменён synthetic Web consumer. Без изменения доменных результатов, базы Work и набора разрешений доступны одинаковые команды/проекции. Проверяет D02/D30/D31.

**ST-E — Offline/low-resource Android.** Клиент видит stale cached Work, ограничивает risky actions, а после reconnect получает актуальный cursor. Large artifact не открывается через unsafe host path. Проверяет D31–D34/D37/D38.

**ST-F — Extension degraded.** Реализация обнаружена, но недоступна по health/contract. Каталог показывает конкретную availability cause; required capability блокирует admission, offline optional feature остаётся видимым как unavailable. Никакой silent provider substitution для effectful job. Проверяет D27/D29.

---

## 18. Provenance / Source Ledger: карта происхождения целевой архитектуры

### 18.1. Статусы источников и предел их доказательной силы

**Программа и правила ветки** определяют предмет и исследовательскую дисциплину. **Код прямого implementation owner** подтверждает исключительно текущее поведение/метаданные на момент обращения. **Датированные current-state исследования** объясняют широкий проверенный baseline, но не заменяют новый аудит изменившегося кода. **Консолидирующие темы 00–07** поддерживают согласованность целевой модели, но сами по себе не превращают гипотезу в реализованную функцию или утверждённое Product Decision. **`02-base-study`** поставляет факты, альтернативы, контрпримеры и направления; **`01-old-notes`** — исторические намерения без силы current-state доказательства.

Корпус 27 исследований второй ветки охвачен в первую очередь через его адресную карту темы 00 и сквозные сведения 01–07; для ключевых фактических и архитектурных вопросов использованы также соответствующие исходные исследования. Это **консолидирующий анализ**, а не утверждение о новом построчном повторном аудите каждого файла, каждой версии external toolchain или всех исполняемых тестов. Если исходное исследование доказывает только предложение, его ссылка подтверждает происхождение предложения, а не наличие реализованного кода.

Главные контролирующие источники:

| Ключ | Источник | Предмет в этой теме |
|---|---|---|
| `PROGRAM` | [Программа третьей ветки][PROGRAM] | Topic 09, logical/physical architecture, целевой реестр решений, метод |
| `BR-02` / `BR-03` | [README второй ветки][BR-02], [README третьей ветки][BR-03] | Implementation ownership, ограничение Research vs Product |
| `C00` | [Корпус, конфликты и UNKNOWN][C00] | Инвентаризация 27 исследований и ранние развилки |
| `C01` | [System Model][C01] | Purpose, owners, AppDock boundary, candidate physical owners |
| `C02` | [Canonical Semantic Model][C02] | Объекты и отношения, Case/Work, Operation/Scenario/Scheme, identity |
| `C03` | [Data → Knowledge][C03] | Source/Registry/Dataset, доказательность, Artifact, currentness |
| `C04` | [Work → Execution][C04] | Admission, Plan, Job, Attempt, state, effects, recovery |
| `C05` | [State, Persistence & Collaboration][C05] | Authority, shared truth, transactions, cursors, backups |
| `C06` | [Capability, Extension & Automation][C06] | Typed catalogs, binding, permissions, scheduler, machine consumers |
| `C07` | [Product Surface Architecture][C07] | Windows/Web/Android, UI semantics, design, accessibility |
| `C08` | **Отдельного файла на момент проверки не обнаружено** | §12 данного исследования — только provisional cross-cutting synthesis |

### 18.2. Полная адресная карта `02-base-study` — 27 исследований

В этой таблице каждая исходная работа второй ветки имеет собственный адрес и назначение в финальной архитектуре. Названия **не** подразумевают перенос ответственности в исследовательский workspace; код и Product Decisions по-прежнему принадлежат implementation/product owners.

| № | Исследование | Вклад в Topic 09 |
|---:|---|---|
| 01 | [Текущее состояние `stratbox`][B-CORE] | Current domain core, FileStore, registries, typed results, gaps |
| 02 | [Текущее состояние `stratbox-windows`][B-WINDOWS] | Current GUI, сценарии, local runtime, AppDock integration, deficits |
| 03 | [Файлово-артефактный слой](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md) | FileStore/Workspace/Artifact/CAS distinction |
| 04 | [Автоматизация и ИИ](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md) | Ранние вопросы automation/agent и позднее уточнение owner |
| 05 | [Команды, сценарии, каскады](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md) | Конфликт Command/Operation и составных определений |
| 06 | [Путь пользователя и управление выполнением](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_execution_control_user_path_research_2026-10-07.md) | Parameters/admission, cancel, retry, status/progress |
| 07 | [FileStore и форматы файлов](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md) | Physical IO, format layers, risky effects |
| 08 | [Переносимость бизнес-сегментов](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_segments_portability_reuse_architecture_research_2026-10-07.md) | Mechanism/domain operation и независимость от consumer |
| 09 | [Машинные схемы бизнес-логики](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_logic_machine_schemes_architecture_research_2026-10-07.md) | Typed composition, contracts, validity/effect limitations |
| 10 | [Управление источниками и справочниками](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_registry_source_governance_research_2026-10-07.md) | Source/Registry snapshot, freshness, versioning |
| 11 | [Ошибки, наблюдаемость и логи](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_observability_errors_logs_research_2026-10-07.md) | Structured problem/event layers, AppDock telemetry boundary |
| 12 | [Многопользовательская работа одного узла](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md) | Node truth, ACL, read receipts, presence, collaboration |
| 13 | [Web/self-hosted архитектура](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md) | Headless authority, deployment profiles, remote consumers |
| 14 | [Фоновые задания и процессы](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md) | Durable automation, triggers, job lifecycle, service survival |
| 15 | [Настройки системы](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_system_settings_research_2026-10-07.md) | Settings ≠ surface state ≠ policy ≠ run parameters |
| 16 | [Визуальная система интерфейса](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_interface_visual_system_research_2026-10-07.md) | Design semantics, theme, tokens, native adaptation |
| 17 | [Анимации Windows](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_windows_motion_animation_research_2026-10-07.md) | UI motion as projection, reduced motion, performance |
| 18 | [Требования к Windows-интерфейсу](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_windows_interface_requirements_research_2026-10-07.md) | Work-first vs scenario-first UX, inspector and navigation |
| 19 | [Настройка стилей артефактов](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md) | ArtifactStyleSet ≠ InterfaceTheme, authoring metadata |
| 20 | [Общий контракт корпоративно-управляемых расширений](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_corporate_plugin_contract_research_2026-10-07.md) | **Только нейтральный публичный ABI, qualification и conformance** |
| 21 | [Граница внешнего когнитивного потребителя](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_boundary_research_2026-10-07.md) | External planner/tool consumer vs Strategy Box semantic owner |
| 22 | [Общие требования к когнитивной интеграции](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_foundation_research_2026-10-07.md) | Work, authority, evidence, machine-readable capabilities |
| 23 | [Готовность бизнес-кода к машинным потребителям](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md) | Operation/Scheme contracts, machine suitability, effects |
| 24 | [Чат, работа и схемы](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_chat_work_schemes_ui_research_2026-10-07.md) | Thread/Work/Cases, consumer-independent execution |
| 25 | [Методологическая целевая декомпозиция Strategy Box](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_madar_target_decomposition_research_2026-10-07.md) | Уровни семантической ответственности и отбор target abstractions |
| 26 | [Эпистемическая архитектура аналитики](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md) | Claim/Evidence/Currentness, границы аналитической доказательности |
| 27 | [Целевая архитектура core и оформления](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_target_core_design_architecture_2026-10-07.md) | Различение логических ролей и опциональных физических packages |

### 18.3. Прямо проверенные файлы implementation owners

Выполнена адресная повторная сверка следующих публичных источников на `main` 2026-10-09. **Эта сверка статическая**: автоматизированные E2E, CI, нагрузочные и отказные испытания в ходе подготовки данного файла не запускались.

| Ключ | Проверенный файл | Установленный факт |
|---|---|---|
| `I-CORE-PY` | [`stratbox/pyproject.toml`][I-CORE-PY] | Core distribution `0.8.0`, Python `>=3.10` |
| `I-CORE-RUNTIME` | [`stratbox/base/runtime.py`][I-CORE-RUNTIME] | Entry-point selection и local fallback, включая отсутствие строгого обязательного provider-binding режима |
| `I-WIN-PY` | [`stratbox-windows/pyproject.toml`][I-WIN-PY] | Desktop distribution `0.1.0`, жёсткая зависимость `stratbox==0.2.1` |
| `I-WIN-MANIFEST` | [`stratbox-windows/appdock/manifest.json`][I-WIN-MANIFEST] | Manifest contract `4.0`; core package requirement `0.2.1`; foreground/local/windows activation |
| `I-WIN-TEST` | [`stratbox-windows/tests/smoke/test_repository_contract.py`][I-WIN-TEST] | Старые проверки `contract_version == 3.0`, `package_identity` в конфликте с текущим manifest |
| `I-WIN-HISTORY` | [`application/history/persistence.py`][I-WIN-HISTORY] | Пять отдельных JSON-историй, неатомарные записи, invalid payload → empty list |
| `I-WIN-BOOT` | [`runtime/bootstrap.py`][I-WIN-BOOT] | AppRuntime строит coordinator прямым импортом Qt presentation module |

**Что эта таблица не доказывает:** что конкретная сборка Strategy Box уже развернута в production, что все тесты заведомо выполнены или что состояние какого-либо внешнего сервиса совпадает с заявленной моделью. Наличие кода и логическое несоответствие файлов подтверждены, полноценная динамическая проверка — отдельный gate G0.

### 18.4. AppDock и внешние технические стандарты

- **[AD]** — предоставленный пользователем материал «AppDock — Базовое описание.docx». Использован как продуктовый источник о Node/installation/activation/actions/results/recovery/remote/permissions. Его обещанные будущие функции **не** принимаются за готовые API.
- [SQLite — Write-Ahead Logging][EXT-SQLITE] — внешняя техническая справка к профилю single-node metadata store; **не** доказывает достаточность SQLite для всех будущих нагрузок или хранение БД на сетевой шаре.
- [OpenTelemetry Semantic Conventions][EXT-OTEL] — vocabulary для traces/logs/metrics; **не** подтверждает существование такой реализации в Strategy Box/AppDock.
- [OWASP ASVS][EXT-ASVS] — проверочная рамка к secure API, access control и input handling; **не** означает завершённый security audit.
- [WCAG 2.2][EXT-WCAG] — внешний ориентир для доступности UI; **не** означает пройденную сертификацию текущего Windows surface.

### 18.5. Исторические исходники и вытесненные решения

Исторический корпус представлен четырьмя материалами: «О приложении Strategy Box.md», «Интерфейс Strategy Box.md», «Рефактор бизнес-логики Stratbox.md», «Патч stratbox Май 2026.md». Он полезен для объяснения происхождения идей, но не является доказательством текущего кода. Его наиболее заметные вытесненные положения: UI/launcher как часть domain core; case/scenario как единая сущность всей работы; самостоятельный локальный background engine; platform shell как владелец прикладного Work; ручная упаковочная связка вместо контрактов AppDock. Актуальность каждого такого тезиса оценивается по прямому owner и позднему смысловому сведению.

### 18.6. Reference links (стабильные имена источников)

[PROGRAM]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/strategy_box_03_consolidation_research_program.md
[BR-02]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/README.md
[BR-03]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/README.md
[C00]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_00_corpus_map_open_questions_2026-10-08.md
[C01]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_01_System_Model_consolidated_research_2026-10-08.md
[C02]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_02_canonical_semantic_model_2026-10-08.md
[C03]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_03_data_to_knowledge_consolidated_research_2026-10-08.md
[C04]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_04_work_to_execution_consolidated_research_2026-10-09.md
[C05]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_05_state_persistence_collaboration_consolidated_research_2026-10-09.md
[C06]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_06_capability_extension_automation_consolidated_research_2026-10-09.md
[C07]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_07_product_surface_architecture_consolidated_research_2026-10-09.md
[B-CORE]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_base_study_current_state_2026-10-06.md
[B-WINDOWS]: https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md
[I-CORE-PY]: https://github.com/ForestTiger-GH/stratbox/blob/main/pyproject.toml
[I-CORE-RUNTIME]: https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/runtime.py
[I-WIN-PY]: https://github.com/ForestTiger-GH/stratbox-windows/blob/main/pyproject.toml
[I-WIN-MANIFEST]: https://github.com/ForestTiger-GH/stratbox-windows/blob/main/appdock/manifest.json
[I-WIN-TEST]: https://github.com/ForestTiger-GH/stratbox-windows/blob/main/tests/smoke/test_repository_contract.py
[I-WIN-HISTORY]: https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/history/persistence.py
[I-WIN-BOOT]: https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/bootstrap.py
[EXT-SQLITE]: https://www.sqlite.org/wal.html
[EXT-OTEL]: https://opentelemetry.io/docs/specs/semconv/general/
[EXT-ASVS]: https://owasp.org/www-project-application-security-verification-standard/
[EXT-WCAG]: https://www.w3.org/WAI/standards-guidelines/wcag/

---

## 19. Финальная исследовательская позиция

**[CONSOLIDATED]** Strategy Box уже имеет реальное аналитическое ядро и работающую Windows-поверхность. Целевая **единая** система должна сохранить эту основу, отделив долгоживущую application authority от Qt и жизни конкретного клиента, сделав источники и результаты воспроизводимыми, а разрешение и исполнение операций — сквозными для человека, автоматики и внешних машинных потребителей.

**[TARGET-HYPOTHESIS, strong]** Следующий большой архитектурный шаг — **малый headless authority с транзакционным состоянием и одним execution spine**; затем — безопасная публикация артефактов, общий многопользовательский доступ, независимый Web consumer и только после этого усложнение автоматизации, host/remote и мобильного клиента. У этого owner уже есть содержательное обоснование, но его имя, packaging и репозиторная граница остаются предметом отдельного решения.

**[CURRENT gap]** Ближайший инженерный долг измерим: версия core/Windows разошлась, manifest/tests рассинхронизированы, Qt участвует в сборке shared runtime, локальная JSON-история не обеспечивает durable authority, системный фон и multi-user пока представлены лишь частично, общий source/artifact provenance и safe extension activation требуют развития.

**[UNKNOWN]** Точная схема работы с БД, полный protocol event stream, устойчивые performance/SLA, Android toolkit, shape machine scheme DSL, retention/backup и выбранный physical host/package должны закрываться независимыми пилотами и ownership agreements. При отсутствии этих доказательств полезнее оставлять чёткую развилку, чем объявлять преждевременный «идеальный» технологический стек.

**Результат этого файла:** две целевые архитектурные карты, системные инварианты, анализ пересечений и конфликта ownership, последовательность проверяемых работ и отдельный Decision / Gap Register. Это **завершённое исследовательское сведение темы 09**, предназначенное для следующего этапа Product/Knowledge assembly, а **не** молчаливое решение изменить implementation owners или открыть внутренние детали чужих расширений.
