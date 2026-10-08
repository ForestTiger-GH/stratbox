# Strategy Box — консолидирующее исследование 01: System Model

**Дата:** 2026-10-08  
**Программа:** третья ветка `03-consolidation-research`  
**Тема:** `01 — Strategy Box System Model`  
**Главный вопрос программы:** **что такое Strategy Box целиком, из каких систем он состоит и где проходят ownership boundaries?**  
**Статус:** Research Synthesis / Consolidation Result. Документ фиксирует исследовательское сведение и сам по себе не меняет Product, код, репозитории или внешние контракты.

---

## 0. Итог в одном абзаце

Strategy Box следует рассматривать как **один аналитический продукт с несколькими логическими слоями и несколькими способами присутствия**, а не как набор независимых приложений и не как один большой Python-пакет. Его устойчивое ядро уже разделилось на две принципиально разные ответственности: `stratbox` владеет предметной и аналитической истиной — источниками, нормализацией, моделями, вычислениями, проверками, provenance и каноническими аналитическими способностями; продуктовый application runtime владеет жизненным циклом пользовательской работы — контекстом Work, планированием, запусками, очередями, Case/Job state, автоматизациями, совместной работой, product authorization, durable state и проекциями артефактов. Сегодня значительная часть второго слоя физически живёт внутри `stratbox-windows`, но это переходное состояние: Windows-процесс не подходит на роль единственного authority для фоновой, многопользовательской, web/mobile и удалённой работы. Консолидированная целевая модель требует **headless-capable Strategy Box runtime с самостоятельным lifecycle**, а Windows, Web и Android должны стать клиентскими поверхностями одной application-семантики. AppDock остаётся внешней платформой установки, окружения, Node/Session, запуска сервисов, health, recovery и remote/platform boundary; он не становится владельцем банковской логики, Work или бизнес-расписаний Strategy Box. Отдельные репозитории `stratbox-core` и `stratbox-design`, предлагавшиеся во второй ветке, нельзя считать автоматически обязательными: логические ответственности application runtime и design system реальны, но физическая граница создаётся только при самостоятельном lifecycle/consumer/failure/maintenance. Для application runtime такой порог уже практически достигнут и наиболее обоснованная физическая гипотеза — `stratbox-host`; для общего design owner физическая форма пока остаётся открытой.

---

# 1. Рамка исследования

## 1.1. Что требует программа третьей ветки

Программа `strategy_box_03_consolidation_research_program.md` определяет тему 01 как первое большое системное исследование после картирования корпуса. Исходная декомпозиция программы задаёт следующий верхний уровень:

```text
Strategy Box
│
├── Product purpose
├── Users / actors
├── Work
├── Analytical capabilities
├── Data / knowledge
├── Runtime / execution
├── Artifacts
├── Collaboration
├── Surfaces
└── Environment / AppDock
```

Программа отдельно требует рассматривать появившиеся во второй ветке физические имена — `stratbox`, `stratbox-core`, `stratbox-design`, `stratbox-windows`, `stratbox-web`, `stratbox-android`, `stratbox-host`, AppDock, PROTOS — **не как заранее утверждённые компоненты**, а через последовательность:

```text
responsibility
    ↓
semantic owner
    ↓
contract
    ↓
physical boundary — только если она действительно нужна
```

Именно это правило является главным ограничителем данного synthesis.

## 1.2. Классификация утверждений

В документе используются шесть исследовательских статусов:

- **CURRENT** — подтверждено текущим implementation owner либо прямым кодом/manifest/package metadata;
- **CONSOLIDATED** — несколько независимых исследований сходятся, противоречие разрешается без нового Product Decision;
- **TARGET-HYPOTHESIS** — сильное целевое направление, ещё не реализованное и не принятое отдельным Product Decision;
- **CONFLICT** — корпус содержит несовместимые варианты либо два претендента на одну authority;
- **SUPERSEDED** — историческая или более ранняя гипотеза вытеснена текущим кодом или более сильным последующим исследованием;
- **UNKNOWN** — материала недостаточно либо выбор зависит от будущего implementation probe/внешнего owner.

Эти метки относятся к epistemic status вывода, а не к приоритету разработки.

## 1.3. Иерархия evidence

При конфликте использован следующий порядок:

```text
текущий код / manifest / package metadata прямого owner
        ↓
актуальная документация прямого owner
        ↓
02-base-study current-state research
        ↓
поздние тематические исследования 02-base-study
        ↓
ранние тематические исследования 02-base-study
        ↓
01-old-notes как исторический источник
```

Исследования, основанные на MADAR-методологии, использованы как семантическая проверка границ, типов истины, Work, evidence и authority. Они не превращаются здесь в структуру пакетов Strategy Box и не задают физическую топологию продукта.

---

# 2. Baseline: что Strategy Box представляет собой сейчас

## 2.1. Текущая физическая система

**CURRENT.** На дату исследования Strategy Box имеет два реально материализованных публичных implementation owner-а:

```text
ForestTiger-GH/stratbox
    ↓ Python dependency
ForestTiger-GH/stratbox-windows
```

и внешний платформенный owner:

```text
ForestTiger-GH/AppDock
```

Дополнительно существуют закрытые environment-specific extensions, но публичная архитектура должна знать только нейтральные extension/capability contracts. Их конкретные реализации, package identities, инфраструктурные детали и конфигурация не входят в данный документ и не должны появляться в публичных `stratbox` или `stratbox-windows`.

**CURRENT.** Репозитории `stratbox-host`, `stratbox-web`, `stratbox-android`, `stratbox-design` и отдельный application-runtime repository `stratbox-core` сейчас не являются implementation owners текущего продукта. Они существуют только как исследованные целевые варианты или ожидаемые будущие поверхности.

## 2.2. `stratbox` сегодня

**CURRENT.** `stratbox` — Python-библиотека, текущая версия пакета в `main` — `0.8.0`. Текущий Product owner прямо определяет его как core/library layer и запрещает GUI/application surface внутри репозитория.

Фактические классы ответственности:

```text
neutral infrastructure
    FileStore / IO / network / secrets contracts / runtime extension seams

reference and source semantics
    registries / aliases / classifiers / source catalogs in current domains

domain logic
    CBR forms / industries / escrow / FRG / source collection / SORS restoration

canonical analytical data and transformations
    parse / normalize / validate / derive / reconstruct

reproducible outputs
    views / exporters / analytical artifacts

increasingly structured contracts
    Request / Result / Failure / validation / provenance
```

**CURRENT.** Core уже умеет использоваться независимо от desktop-продукта — из Python/Jupyter-подобных consumers. Это не побочный режим, а важная часть boundary: Strategy Box product runtime является consumer core, но core не зависит от продукта.

## 2.3. `stratbox-windows` сегодня

**CURRENT.** `stratbox-windows` формально является Windows application/surface, но фактически содержит существенно больше rendering-а. Внутри него уже живут:

- operation registry;
- scenario registry;
- scenario execution;
- `ScenarioRunCase` и step state;
- events;
- artifacts;
- logs;
- assignments;
- presence projection;
- background-process model;
- recent-history persistence;
- workspace resolution;
- AppDock boundary;
- runtime composition;
- Qt desktop presentation.

Текущая цепочка исполнения выглядит примерно так:

```text
AppDock Activation Context / standalone-dev
        ↓
AppContext
        ↓
OperationRegistry + ScenarioRegistry
        ↓
AppRuntime
        ↓
Qt ScenarioCoordinator / QThread
        ↓
Scenario runner
        ↓
Operation runner
        ↓
handler
        ↓
stratbox
        ↓
outputs / logs / artifacts / events / cases
```

**CURRENT.** `ScenarioRunCase` является реальным persisted user-visible execution object. Его state machine содержит `prepared / queued / running / success / warning / failed / cancelled`.

**CURRENT.** `ScenarioSpec` всё ещё имеет `kind = atomic | composite | background | assignment`. Поздние исследования второй ветки считают такую классификацию переходной и предлагают убрать «background» из ontology сценария, поскольку фоновость относится к способу исполнения.

**CURRENT.** `BackgroundProcessState` существует, но scheduler/executor за ним нет. Это UI/domain scaffold, а не фоновая runtime-система.

**CURRENT.** Recent history хранится отдельными JSON projections. Сам код `HistoryPersistenceService` прямо оговаривает, что это не database-grade durability. При ошибке чтения JSON текущая реализация возвращает пустой список. Для local prototype это терпимо; для общей durable truth — нет.

**CURRENT.** Runtime bootstrap импортирует Qt `ScenarioCoordinator`. Значит, текущая runtime composition ещё не является frontend-neutral.

## 2.4. AppDock сегодня

**CURRENT.** AppDock является внешней платформой productization/runtime. Его собственная текущая модель отделяет source/release/deployment/runtime truth и требует, чтобы product surfaces не владели domain truth. Для Strategy Box материальны следующие платформенные обязанности:

- intake/delivery и package composition;
- установка и обновление;
- managed environment;
- Node и Session context;
- activation;
- Data/runtime path binding;
- lifecycle процессов и сервисов;
- platform health/readiness;
- recovery;
- platform observability/evidence;
- remote/platform connection boundary.

AppDock принимает внешний продукт через declarative manifest и не требует переноса предметной архитектуры приложения внутрь себя.

## 2.5. Фактические дрейфы текущей системы

### Core/Windows version drift

**CURRENT / CONFLICT.** Актуальный `stratbox` имеет версию `0.8.0`, тогда как текущий `stratbox-windows` в `pyproject.toml` и AppDock package requirement всё ещё ориентирован на `stratbox==0.2.1`. Это не вопрос целевой архитектуры, а прямое несогласование текущих implementation owners.

Следствие: текущие `main` ветки нельзя считать полностью согласованной release pair без синхронизации contract/version metadata.

### AppDock contract documentation drift

**CURRENT / CONFLICT.** Текущий Windows manifest объявляет Connector/manifest contract `4.0`, тогда как README всё ещё описывает Connector `3.0`. Базовое исследование также обнаружило аналогичный drift в тестах и документации.

### Public/private boundary drift

**CURRENT / CONFLICT.** В публичной packaging/documentation поверхности обоих публичных репозиториев ещё сохраняются legacy/environment-specific ссылки на закрытый deployment contour. Это противоречит уже сформулированному public-boundary принципу.

**CONSOLIDATED.** Целевая публичная форма должна содержать только generic extension contracts, capability vocabulary, selection/activation semantics и diagnostics. Все конкретные закрытые реализации остаются вне публичных репозиториев.

---

# 3. Что такое Strategy Box как продукт

## 3.1. Минимальная формула

**CONSOLIDATED.** Strategy Box — это **аналитическая рабочая система**, которая соединяет:

```text
авторитетные внешние данные
        ↓
нормализацию / проверку / вычисления
        ↓
канонические аналитические capabilities
        ↓
управляемую пользовательскую Work
        ↓
длительное и наблюдаемое execution
        ↓
результаты / evidence / artifacts
        ↓
совместную работу и последующее использование
        ↓
Windows / Web / Android / automation / AI consumers
```

Она не сводится ни к Python-библиотеке, ни к desktop UI, ни к AppDock world, ни к каталогу сценариев.

## 3.2. Текущая и целевая идентичность — разные уровни

**CURRENT.** Сегодня наиболее зрелая часть Strategy Box — получение и обработка банковских/макроэкономических данных плюс desktop control surface.

**TARGET-HYPOTHESIS.** Целевая идентичность шире: эпистемически дисциплинированная аналитическая рабочая среда, где источник, наблюдение, преобразование, derived result, evidence, hypothesis/claim, решение и действие не смешиваются молча.

Эта формула сильна как direction, но общий first-class Knowledge/Claim layer пока реализован неравномерно. В core есть очень зрелые участки provenance/evidence, однако нет единой product-wide claim/knowledge ontology.

## 3.3. Что Strategy Box точно не является

**CONSOLIDATED.** Strategy Box не должен становиться:

- GUI к случайным Python-функциям;
- универсальным AppDock replacement;
- собственным installer/update platform;
- монолитом, где UI, scheduler, domain logic и persistence живут в одном процессе;
- отдельной «AI-версией» аналитики;
- системой, где каждый новый frontend получает собственный executor и свою историю;
- платформой произвольных third-party UI plugins;
- giant ETL framework, абстрагирующим всё на свете;
- проекцией структуры исследовательской методологии в package tree.

---

# 4. Users, principals, actors и executors

Точная ontology будет предметом темы 02, но System Model уже требует ownership boundary.

## 4.1. Human user

**CURRENT.** В Windows runtime есть `user/session/host/node` identity facts, приходящие через managed runtime context.

**CONSOLIDATED.** Платформенная идентичность пользователя/сессии и продуктовый participant — связанные, но разные вещи.

```text
AppDock principal/session fact
        ↓ mapping
Strategy Box participant/principal context
        ↓
product authorization / ownership / authorship
```

AppDock сообщает, **кто подключён к среде**. Strategy Box решает, **что этому principal разрешено делать внутри аналитического продукта**, если это продуктовая семантика.

## 4.2. Automation actor

**TARGET-HYPOTHESIS.** Automation/trigger не должна притворяться пользователем. Срабатывание имеет собственную инициирующую identity, владельца/creator-а правила и отдельный execution actor context.

## 4.3. Cognitive / AI actor

**TARGET-HYPOTHESIS.** PROTOS или иной cognitive consumer должен подключаться как внешний consumer canonical capabilities и Work runtime, а не становиться владельцем business semantics.

Ключевая граница:

```text
AI выбрал capability
≠ AI владеет capability

AI предложил Work transition
≠ AI автоматически получил Authority

AI вызвал operation
≠ operation стала AI-specific API
```

## 4.4. Executor

**CONSOLIDATED.** Actor и executor не равны.

Операцию может инициировать пользователь, а выполнить host worker. Automation может инициировать Case, а фактический executor будет локальным или удалённым worker. Cognitive actor может спланировать, а вычисление выполнит детерминированная domain operation.

Это различие критично для audit, permissions и remote execution.

---

# 5. Work: центральная product responsibility

## 5.1. Что есть сейчас

**CURRENT.** В текущем Windows-продукте главным user-visible execution object фактически является `ScenarioRunCase`. Центральная поверхность называется scenario chat, но durable Chat/Thread как отдельная authority отсутствует; persisted recent history привязана к cases/events/artifacts/logs/assignments.

**CURRENT.** `Work` как first-class durable semantic object в текущем коде не реализован.

## 5.2. Что устойчиво следует из корпуса

**CONSOLIDATED.** Пользовательская работа и конкретное исполнение нельзя считать одной сущностью.

Одна смысловая задача может:

- жить дольше одного клиента;
- продолжаться после закрытия UI;
- порождать несколько запусков;
- включать повторные попытки;
- ждать пользователя;
- получать новые данные;
- использовать несколько артефактов;
- выполняться частично в background;
- быть продолжена на другом устройстве.

Поэтому product runtime нужен собственный owner долговечной Work semantics.

## 5.3. Thread, Work, Case, Job и Run

**TARGET-HYPOTHESIS.** Поздние исследования сходятся в направлении:

```text
Thread / Chat = человеческий длительный контекст взаимодействия
Work          = смысловая задача
Case          = пользовательски наблюдаемая инстанциация/контур исполнения
Job           = durable runtime execution unit
Attempt       = конкретная попытка исполнения
```

**UNKNOWN.** Точные canonical definitions и кардинальности между этими сущностями пока не должны фиксироваться в теме 01. Они относятся к темам 02 и 04.

Системный вывод здесь ограничен ownership:

> durable Work/execution truth принадлежит Strategy Box application runtime, а не UI, не `stratbox` domain library и не AppDock platform runtime.

---

# 6. Analytical capabilities: что система умеет

## 6.1. `stratbox` как semantic capability owner

**CONSOLIDATED.** Одна предметная способность должна иметь одну каноническую реализацию/контракт в `stratbox` и несколько consumers.

```text
Jupyter / Python
Windows
Web
Android
Automation
AI
remote execution
        ↓
canonical Strategy Box capability
        ↓
stratbox domain implementation
```

Наличие нескольких consumers не должно порождать отдельные «GUI operations», «AI operations» и «scheduler operations» для одного и того же предметного действия.

## 6.2. Внутренняя иерархия capability

**CONSOLIDATED.** Не каждая Python-функция является operation. В core полезно различать:

```text
mechanism / primitive
building block
domain service
canonical operation
reusable scheme / scenario definition
concrete execution plan
```

Физические имена этих уровней ещё могут измениться. Системный принцип устойчив: semantic capability identity отделяется от Python implementation identity.

## 6.3. Scheme / Scenario / Cascade

**CONFLICT.** Вторая ветка использует несколько пересекающихся моделей:

- Scenario как пользовательская composition;
- Cascade как крупная composition нескольких сценариев;
- Machine Scheme как versioned reusable machine procedure;
- поздняя Work-oriented модель, где scenario/cascade постепенно становятся capability-library representations, а не центром UI.

Для System Model конфликт разрешается только на уровне responsibility:

```text
Capability Definition
        ↓
Reusable Composition Definition
        ↓
Resolved Execution Plan
        ↓
Runtime Execution
```

**UNKNOWN.** Названия и точная граница Scenario/Cascade/Scheme должны быть решены в canonical semantic model, а не в этом исследовании.

---

# 7. Data / Knowledge responsibility

## 7.1. Что уже является current truth

**CURRENT.** `stratbox` уже владеет естественным data flow:

```text
source discovery
→ fetch/cache
→ raw preservation
→ physical parse
→ semantic normalization
→ canonical data
→ validation
→ derived/reconstruction
→ views/export
```

**CURRENT.** В наиболее зрелых подсистемах provenance/evidence уже first-class. В остальных доменах он пока легче и неоднороднее.

## 7.2. Registry и source governance

**CONSOLIDATED.** Общие reference registries и source descriptors относятся к domain/data core, а не к UI или AppDock. AppDock обновляет поставку; он не становится registry service Strategy Box.

## 7.3. Knowledge layer

**TARGET-HYPOTHESIS.** Strategy Box должен уметь различать как минимум:

- raw source;
- source snapshot;
- observation/canonical datum;
- derived analytical result;
- evidence/provenance;
- qualified claim/hypothesis там, где это materially необходимо.

**UNKNOWN.** Не доказано, что для каждого домена нужен тяжёлый универсальный `ClaimStore`. SORS-подобная evidence-rich модель показывает ценность строгого provenance, но software representation общего Knowledge plane следует материализовать только при реальных consumers.

## 7.4. Главная boundary

**CONSOLIDATED.** Application runtime может хранить ссылки, indexes и workflow metadata аналитических результатов, но **semantic truth аналитического результата принадлежит core/domain layer**.

Это предотвращает ситуацию, когда UI database начинает быть более авторитетной, чем код/модель, породившая результат.

---

# 8. File, Workspace, Artifact и provenance

## 8.1. FileStore

**CURRENT / CONSOLIDATED.** FileStore — правильный нижний нейтральный контракт физического файлового доступа.

Он не должен становиться универсальной моделью результатов Strategy Box.

## 8.2. Workspace

**CONSOLIDATED.** Workspace — изменяемая рабочая область. AppDock может передать Data/root binding, но смысл workspace внутри Strategy Box принадлежит продукту.

Клиентская поверхность владеет UX навигации, но не должна делать физический path общей product identity.

## 8.3. Artifact

**CURRENT.** В Windows artifact сейчас в основном metadata вокруг output path, связанная с Case/Operation.

**TARGET-HYPOTHESIS.** Целевой Artifact — логический durable object с ID, manifest, content identity/hash, provenance/lineage и lifecycle, который может быть materialized в разные физические места.

## 8.4. Разрешение ownership-конфликта Artifact Catalog

**CONFLICT.** Одно исследование помещает Artifact Catalog практически целиком в `stratbox`, более поздние host/runtime исследования относят artifact index и user-facing artifact state к application runtime.

Конфликт снимается разделением двух истин:

### Core/domain owner

`stratbox` владеет:

- Artifact semantic contracts для outputs domain operations;
- provenance/lineage, которую может доказать domain operation;
- artifact manifest schema для воспроизводимого результата;
- format/export semantics;
- content identity primitives, если они generic.

### Application runtime owner

Strategy Box application runtime владеет:

- runtime artifact catalogue/index как часть Work;
- visibility/authorization;
- связи Thread/Work/Case/Job;
- user-facing lifecycle/retention policy;
- availability/materialization references;
- shared-node projection.

### Physical storage owner

Физическое хранение реализуется через neutral storage contracts/environment capability. Surface не должна становиться storage authority.

**CONSOLIDATED.** Таким образом, `Artifact` как semantic output и `ArtifactRecord` как application workflow projection — разные responsibilities даже если позднее они используют общий ID.

---

# 9. Runtime / Execution

## 9.1. Current execution owner

**CURRENT.** Сейчас execution orchestration физически находится в `stratbox-windows`: Qt coordinator → worker thread → scenario runner → operation runner.

**CURRENT.** Только один scenario одновременно поддерживается текущим coordinator. Cancellation model в данных есть, полноценного cancel path нет.

## 9.2. Почему Windows process перестаёт подходить как authority

**CONSOLIDATED.** Требования, накопленные во второй ветке, делают GUI-process authority архитектурно недостаточным:

- фоновые задачи должны жить после закрытия окна;
- один узел должен поддерживать несколько клиентов;
- Web и Android должны видеть то же состояние;
- multi-user требует одной общей истины;
- job queue и resource locks должны быть node-scoped;
- scheduler должен переживать UI restart;
- remote execution требует reconnect;
- execution outcome не должен зависеть от жизни HTTP request или Qt thread;
- crash recovery требует durable state.

Это не «будущая красота», а совокупность самостоятельных lifecycle/failure requirements.

## 9.3. Целевая logical responsibility

**CONSOLIDATED.** Нужен общий **Strategy Box Application Runtime** со следующими responsibility classes:

```text
capability projection / application catalog
work + threads/context
scenario/scheme resolution
planning
cases / jobs / attempts
scheduler / automation rules
queues / resource coordination
cancellation / retry / resume
shared product state
product authorization
collaboration state
artifact runtime index
notifications semantics
application API / event stream
recovery / reconciliation
```

Он является отдельным owner от `stratbox` и от AppDock.

## 9.4. `stratbox-core` vs `stratbox-host`

Это главный физический конфликт второй ветки.

### Ранний вариант — `stratbox-core`

Исследование общей core/design architecture предложило отдельный application runtime `stratbox-core`, куда перемещаются application/runtime responsibilities из Windows.

### Поздний вариант — `stratbox-host`

Web/self-hosted, multi-user и background исследования показали, что тот же runtime должен:

- жить без GUI;
- иметь самостоятельный процесс/lifecycle;
- обслуживать несколько клиентов;
- сохранять shared durable truth;
- исполнять фоновые jobs;
- предоставлять API/events;
- восстанавливаться после crash.

Это уже не просто shared library.

### Консолидированное разрешение

**CONSOLIDATED.** `Strategy Box Application Runtime` — логическая ответственность.

**TARGET-HYPOTHESIS, strong.** Её основная физическая materialization должна быть headless service/host с самостоятельным lifecycle; рабочее имя `stratbox-host` лучше отражает эту роль, чем `stratbox-core`.

**SUPERSEDED AS PHYSICAL TOPOLOGY.** Идея обязательного отдельного repository/package `stratbox-core` как промежуточного владельца той же application truth больше не выглядит необходимой. Смысл, который она обнаружила, сохраняется; отдельная физическая граница — нет.

При необходимости внутри `stratbox-host` позднее может выделиться reusable application-contract library, если появятся минимум два независимых consumer-а с отдельным lifecycle. Создавать её заранее не требуется.

## 9.5. Локальная desktop-поставка

**TARGET-HYPOTHESIS.** Даже локальный Windows режим желательно свести к тому же execution spine:

```text
stratbox-windows
    ↓ local IPC / loopback client contract
Strategy Box Host
    ↓
stratbox
```

Это убирает вторую архитектуру «desktop-local executor».

**UNKNOWN / NEEDS IMPLEMENTATION PROBE.** Нужно проверить стоимость startup, packaging, process supervision и local IPC. Если она непропорционально велика для первого цикла, допустим временный embedded adapter, но semantic contracts и durable model должны оставаться host-ready.

---

# 10. Automation и background work

## 10.1. Background — не domain type

**CONSOLIDATED.** Самый сильный итог позднего исследования:

> фоновость является характеристикой исполнения, а не отдельным видом Scenario или отдельной системой бизнес-логики.

Одна и та же capability/workflow может быть:

- foreground;
- background;
- scheduled;
- event-triggered;
- user-triggered;
- API-triggered;
- AI-triggered;
- remote.

Все пути должны сходиться в один execution spine.

## 10.2. Scheduler ownership

**CONFLICT → RESOLVED.** Раннее AI/automation исследование допускало scheduler как часть AppDock host runtime. Позднее background research уточнило boundary.

**CONSOLIDATED.** Семантика `AutomationSpec`, `Trigger`, business schedule, overlap/misfire policy и создание Strategy Box Job принадлежат **Strategy Box Application Runtime**.

AppDock может:

- запустить host service;
- следить за его health;
- восстановить/перезапустить процесс;
- предоставить platform scheduling primitive при необходимости как backend.

Но AppDock не должен интерпретировать, что такое «обновить данные ЦБ каждый рабочий день» как product semantics.

---

# 11. Collaboration

## 11.1. Current state

**CURRENT.** Windows уже имеет participant/presence vocabulary, authorship, assignments и incoming/outgoing projection, но фактическая истина локальна одному GUI process.

Два одновременно запущенных клиента способны иметь разные Case history и разные представления о состоянии.

## 11.2. Target owner

**CONSOLIDATED.** Shared-node collaboration truth должна принадлежать application runtime/host.

Он владеет:

- shared Work/Case/Job state;
- product participants projection;
- assignments/approvals;
- read/unread/shared event cursors, если они materialize;
- application permissions;
- collaboration events;
- concurrency/revision control.

Client surfaces получают projections и отправляют commands.

## 11.3. AppDock boundary

**CONSOLIDATED.** AppDock остаётся owner платформенных Node/Session facts. Strategy Box не должен самостоятельно изобретать второй platform login/session authority.

Но AppDock session presence не означает автоматически:

- участие в конкретном Work;
- доступ к конкретному Artifact;
- право отменить чужой Job;
- принятие Assignment;
- application ownership.

Эти выводы делает Strategy Box по своим правилам.

---

# 12. Observability, errors и health

## 12.1. Три разных уровня истины

**CONSOLIDATED.** Нельзя сводить всё к одному «логу ошибок».

### Domain diagnostics — `stratbox`

```text
domain failure
validation issue
source status
progress-safe domain event
provenance
partial result
```

### Application execution truth — Strategy Box runtime

```text
Case / Job / Attempt state
progress
terminal outcome
retry/cancel/recovery
artifact links
user-facing problem projection
```

### Platform health/evidence — AppDock

```text
process/service health
Node/Session condition
platform problem/evidence reference
startup/runtime infrastructure failure
recovery/support boundary
```

## 12.2. Главная граница

**CONSOLIDATED.** `AppDock execution success` не означает `Strategy Box analytical Work success`, и наоборот.

Host process может быть healthy, а domain operation дать содержательный failure. Domain result может быть уже сформирован, а platform transport потерять confirmation outcome.

Поэтому связь строится через explicit references/context, а не через слияние двух state machines.

## 12.3. Логи

**CONSOLIDATED.** Raw exception/traceback/stdout — evidence. Product state должен быть typed и safe.

Application/runtime не должен считать текстовый лог единственным каналом progress или state reconstruction.

---

# 13. Surfaces

## 13.1. Общий принцип

**CONSOLIDATED.** Surface — projection и control client, а не owner domain/application truth.

```text
shared Strategy Box semantics
        ↓
platform adaptation
        ↓
native rendering
```

## 13.2. Windows

**CURRENT.** `stratbox-windows` — единственная реализованная конечная пользовательская surface.

Целевая responsibility после выделения host:

- Windows rendering;
- navigation;
- device-local drafts/preferences;
- local file picker/open/reveal/share integration;
- local notifications;
- reconnect/client cache;
- platform accessibility adaptation;
- semantic view models/projections.

Она перестаёт быть единственным owner cases/jobs/shared history.

## 13.3. Web

**TARGET-HYPOTHESIS.** `stratbox-web` оправдан как отдельная browser surface, когда материализуется web use case. Он не должен владеть business logic/jobs/files/users; работает через host API/event contract.

## 13.4. Android

**TARGET-HYPOTHESIS.** `stratbox-android` ожидается как отдельная mobile surface. Повторному использованию подлежат semantic models, form schema, status/action vocabulary, Work/Run/Artifact projections и client contract, а не Windows layout/Qt widgets.

## 13.5. Узкие future surfaces

**UNKNOWN.** Отдельные companion/notification surfaces могут появиться позже, но их нельзя материализовать заранее. Если они только отображают projection и отправляют bounded command, новый semantic owner им не нужен.

---

# 14. Product surface semantics и design system

## 14.1. Semantic presentation

**CONSOLIDATED.** Между application runtime и конкретным UI нужен view-neutral слой:

- navigation destinations;
- case/work projections;
- progress/status vocabulary;
- form schemas;
- action availability;
- artifact summaries;
- problem summaries;
- filters/search semantics;
- accessibility-relevant semantic states.

Сегодня часть такого слоя уже появилась в `presentation/common` Windows-репозитория.

## 14.2. Design system

**CONSOLIDATED.** Общая визуальная семантика продукта реальна как responsibility:

- semantic color tokens;
- typography roles;
- spacing/density;
- motion semantics;
- icon semantics;
- component/pattern contracts;
- accessibility rules;
- light/dark/system theme behavior.

## 14.3. Нужен ли `stratbox-design` как отдельный репозиторий

**TARGET-HYPOTHESIS / UNKNOWN.** Вторая ветка предложила отдельный `stratbox-design`. Логический design owner действительно нужен, но отдельный repository пока не доказан.

Почему:

- сейчас реальный consumer один — Windows;
- Web и Android ещё не materialized;
- cross-language delivery tokens может позже потребовать самостоятельную поставку;
- до этого дизайн-семантику можно держать рядом с текущей surface, сохраняя platform-neutral format.

Решение о repo extraction нужно принимать при появлении второго реального frontend consumer или отдельного release lifecycle.

## 14.4. Artifact styles не являются UI design system

**CONSOLIDATED.** Оформление XLSX/DOCX/PPTX/PDF — часть reporting/artifact capability и должно оставаться независимо от interface theme.

```text
UI Design System
≠ Artifact Style Set
```

Иначе branding generated files начинает случайно менять shell приложения.

---

# 15. Environment / AppDock boundary

## 15.1. Каноническая ответственность AppDock

**CONSOLIDATED.** AppDock — внешний platform owner для:

```text
source/release/deployment lifecycle
installation / update
managed environment
package/runtime binding
Node lifecycle
Session/platform identity context
Data binding
service/process activation
platform health/readiness
platform recovery
remote exposure/attachment
platform observability/evidence
```

## 15.2. Каноническая ответственность Strategy Box

Strategy Box application/runtime владеет:

```text
Work semantics
capability selection
plans
Cases / Jobs / Attempts
automations / product schedules
product collaboration
product authorization
artifact workflow
application state
analytical result interpretation
```

`stratbox` владеет domain/data truth внутри этой системы.

## 15.3. Почему эти слои нельзя сливать

Если AppDock начинает понимать конкретные банковские Scenario/Automation semantics, он перестаёт быть универсальной платформой.

Если Strategy Box начинает реализовывать install/update/Node/process recovery самостоятельно, он дублирует AppDock.

**CONSOLIDATED.** Правильная интеграция — typed boundary и projections/capabilities между двумя автономными systems.

## 15.4. Терминологическая коллизия «host»

**CONFLICT / NAMING.** AppDock использует host/node в платформенном смысле, а исследования Strategy Box предлагают `stratbox-host` как product application runtime.

Семантически это два уровня:

```text
AppDock Node/Host
    физическая/платформенная среда

Strategy Box Host
    продуктовый headless runtime, работающий внутри этой среды
```

Название `stratbox-host` остаётся удобным рабочим именем, но публичная документация должна всегда различать `platform host/node` и `Strategy Box runtime service`, чтобы избежать ложного ownership.

---

# 16. Extension boundary

## 16.1. Что принадлежит public Strategy Box

**CONSOLIDATED.** Публичный `stratbox` должен владеть только нейтральной extension architecture:

- versioned extension protocol;
- capability declarations;
- discovery;
- explicit activation/binding;
- error model;
- health/readiness;
- conformance tests;
- synthetic/reference implementations для публичного тестирования.

## 16.2. Что находится снаружи

Конкретные environment-specific implementations живут за публичной границей и не становятся частью public Product knowledge.

## 16.3. Discovery ≠ activation

**TARGET-HYPOTHESIS, strong.** Установленное расширение не должно автоматически становиться активным. Managed environment должен явно выбирать bindings required capabilities.

Если required capability выбрана, но broken, production runtime должен fail closed/readiness error, а не молча менять среду исполнения.

## 16.4. UI extensions

**CONSOLIDATED.** Исследования настроек и кастомизации не поддерживают идею произвольного внедрения UI shell extensions. Внешние capabilities могут добавлять business/infrastructure/reporting possibilities, но не должны получать unrestricted API для Qt widgets/QSS/sidebar replacement.

Это защищает переносимость Windows → Web → Android.

---

# 17. PROTOS / cognitive-system boundary

## 17.1. Роль

**TARGET-HYPOTHESIS.** PROTOS — потенциальный внешний cognitive consumer и planner, а не новый owner Strategy Box data/domain/application truth.

Он должен видеть:

- capability catalogue;
- typed inputs/outputs;
- effects;
- applicability;
- artifact/evidence references;
- current Work context в разрешённых пределах;
- разрешённые control actions.

## 17.2. Execution

**CONSOLIDATED.** Cognitive system может:

```text
interpret intent
→ choose/compose admitted capabilities
→ propose plan
→ request execution
→ inspect typed results
→ continue reasoning
```

Но actual Job state, authorization и effects остаются у Strategy Box application runtime.

## 17.3. Не создавать AI-specific duplicate architecture

**CONSOLIDATED.** GUI, scheduler, API и AI должны быть consumers одного capability/execution system. Отдельный `ai_operations` owner не нужен.

---

# 18. Сводная logical architecture

Ниже — консолидированная карта **responsibilities**, а не репозиториев.

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                         STRATEGY BOX PRODUCT                              │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Domain & Analytical Core                                        │  │
│  │ sources • registries • parsing • canonical data • models           │  │
│  │ validation • reconstruction • evidence • provenance                │  │
│  │ canonical operations • artifact/report generation                  │  │
│  └───────────────────────────┬─────────────────────────────────────────┘  │
│                              │                                            │
│                              ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ 2. Strategy Box Application Runtime                               │  │
│  │ Work/Thread semantics • capability projection • planning           │  │
│  │ Cases/Jobs/Attempts • automations • scheduler • resource control   │  │
│  │ collaboration • product authz • shared state • artifact index      │  │
│  │ application API/events • recovery                                  │  │
│  └───────────────────────────┬─────────────────────────────────────────┘  │
│                              │                                            │
│               ┌──────────────┼──────────────┐                             │
│               ▼              ▼              ▼                             │
│          Windows client    Web client    Android client                   │
│               │              │              │                             │
│               └────── common semantic surface contracts ───────────────┘ │
│                                                                           │
│                  Design-system semantics feed clients                    │
└───────────────────────────────────────────────────────────────────────────┘

                         ▲                    ▲
                         │                    │
          environment capabilities           │ cognitive consumer
                         │                    │
                         │                    │
                  neutral contracts           │
                         │                    │
                         └────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│                              APPDOCK                                      │
│ install • release • environment • node/session • activation              │
│ service lifecycle • health • recovery • platform remote/observability    │
└───────────────────────────────────────────────────────────────────────────┘
```

Важная особенность схемы: AppDock находится **вокруг/под runtime deployment**, а не «над `stratbox` как второй business layer». Cognitive consumer находится **снаружи capability boundary**, а не внутри domain implementation.

---

# 19. Ownership matrix

| Responsibility | Current physical owner | Consolidated semantic owner | Target physical direction |
|---|---|---|---|
| Banking/macro domain logic | `stratbox` | `stratbox` | `stratbox` |
| Source semantics / registries | `stratbox` | `stratbox` | `stratbox` |
| Canonical analytical operations | `stratbox` unevenly | `stratbox` | `stratbox` |
| Domain provenance/evidence | `stratbox`, maturity varies | `stratbox` | `stratbox` |
| Low-level FileStore/format contracts | `stratbox` | `stratbox` | `stratbox` |
| Environment-specific capability implementation | external/private | external/private | external/private via neutral contract |
| Extension protocol | current seam in `stratbox` | `stratbox` | versioned public contract in `stratbox` |
| Scenario/application catalog | `stratbox-windows` | Strategy Box application runtime | headless runtime service |
| Planning | mostly implicit in Windows runner | Strategy Box application runtime | headless runtime service |
| Case/Job/Attempt truth | partial Case in Windows; Job absent | Strategy Box application runtime | headless runtime service |
| Scheduler/Automation truth | scaffold only | Strategy Box application runtime | headless runtime service |
| Shared collaboration state | local Windows scaffold | Strategy Box application runtime | headless runtime service |
| Product authorization | incomplete | Strategy Box application runtime | headless runtime service |
| Platform identity/session/node | AppDock boundary | AppDock | AppDock |
| Product participant mapping | Windows local projection | Strategy Box application runtime | host/service |
| Platform process/service lifecycle | AppDock | AppDock | AppDock |
| Application execution lifecycle | Windows process today | Strategy Box application runtime | host/service |
| Platform health/evidence | AppDock | AppDock | AppDock |
| Domain/application diagnostics | core + Windows | respective domain/runtime owner | core + host, projected to AppDock when needed |
| Artifact semantic output/provenance | core + Windows split | `stratbox` | `stratbox` contracts |
| Artifact workflow/index/visibility | Windows local | application runtime | host/service |
| Physical artifact bytes | workspace/FileStore | storage capability | neutral backend |
| Windows rendering | `stratbox-windows` | `stratbox-windows` | `stratbox-windows` |
| Web rendering | absent | future web surface | materialize when real |
| Android rendering | absent | future Android surface | materialize when real |
| Shared surface semantics | partly Windows `presentation/common` | Strategy Box client contract | host API/schema + per-client view models |
| UI visual semantics/design tokens | Windows resources/QSS | Strategy Box design system | physical owner TBD |
| Artifact/report visual styles | core + extensions unevenly | `stratbox` reporting/artifact layer | core contracts/providers |
| User device-local preferences | Windows | concrete client | each client |
| Shared/cross-device product preferences | absent | application runtime if required | host/service, TBD |
| Installation/update | AppDock | AppDock | AppDock |
| Research/provenance workspace | `_mw` | engineering workspace only | outside runtime product |
| Cognitive planning | absent | external cognitive system | external integration |

---

# 20. Physical architecture: что уже оправдано, а что ещё нет

## 20.1. `stratbox`

**CURRENT + CONSOLIDATED.** Отдельный repository/package полностью оправдан. Имеет самостоятельный consumer set, lifecycle, testing, packaging и возможность direct use без Strategy Box application runtime.

## 20.2. `stratbox-windows`

**CURRENT + CONSOLIDATED.** Отдельный surface repository оправдан platform-specific rendering/desktop integration.

Его application/runtime код должен постепенно потерять роль authoritative shared runtime и стать client/application adapter относительно общего host contract.

## 20.3. `stratbox-host`

**TARGET-HYPOTHESIS, strong.** Отдельный headless runtime owner практически обоснован, потому что имеет самостоятельные:

- lifecycle;
- process supervision;
- persistence;
- crash/recovery behavior;
- multi-client API;
- background execution;
- scheduler;
- resource management;
- security boundary;
- server-side testing/deployment.

Это соответствует критерию программы для новой физической границы.

## 20.4. `stratbox-core`

**SUPERSEDED AS REQUIRED REPOSITORY.** Название полезно было для обнаружения application runtime responsibility. После появления обоснованного headless host отдельный `stratbox-core` как второй owner той же truth создаёт риск дублирования.

Возможный shared library package допустим позже только при доказанном independent consumer set.

## 20.5. `stratbox-web`

**TARGET-HYPOTHESIS.** Физически оправдан при реальной browser surface. Пока implementation owner отсутствует.

## 20.6. `stratbox-android`

**TARGET-HYPOTHESIS.** Будущий mobile owner оправдан platform integration/rendering. Общие semantics должны быть подготовлены уже сейчас в Windows/host contracts, чтобы Android не копировал orchestration.

## 20.7. `stratbox-design`

**UNKNOWN.** Логический design system нужен. Отдельный repository пока преждевременен. Re-evaluate после второго реального frontend consumer или появления независимого release lifecycle design assets/tokens.

## 20.8. AppDock

**CURRENT.** Отдельный внешний проект с собственной authority; не входит в Strategy Box implementation subject.

## 20.9. PROTOS

**EXTERNAL / TARGET INTEGRATION.** Отдельный cognitive owner; Strategy Box должен быть готов к потреблению capabilities без зависимости domain code от cognitive runtime.

---

# 21. System invariants темы 01

Ниже свойства, которые выдержали весь корпус и должны ограничивать последующие темы.

## Invariant 01 — один semantic owner на одну durable truth

Нельзя одновременно считать Windows JSON, host DB и AppDock runtime state равноправной authority одного Case/Job.

Проекции допустимы; competing truth — нет.

## Invariant 02 — core не зависит от surfaces

`stratbox` должен работать независимо от Windows/Web/Android/AppDock application surface.

## Invariant 03 — surface не владеет domain truth

UI отображает и запрашивает transitions. Он не определяет смысл банковского показателя, валидность source snapshot или доказательность результата.

## Invariant 04 — application runtime не становится вторым domain core

Host управляет lifecycle исполнения. Банковские parsers/calculations остаются в `stratbox`.

## Invariant 05 — AppDock не становится Strategy Box application runtime

AppDock управляет платформенной средой и жизненным циклом. Strategy Box владеет Work/jobs/product schedules.

## Invariant 06 — один execution spine

Foreground/background/scheduled/AI/API/remote — способы инициирования одной модели Work → plan → execution, а не отдельные engines.

## Invariant 07 — client lifetime не определяет job lifetime

Закрытие Windows/Web/Android client не отменяет durable Job автоматически.

## Invariant 08 — identity, actor и executor различаются

Кто попросил, кто имеет Authority и кто физически выполнил действие — разные отношения.

## Invariant 09 — Artifact identity выше path

Physical path — locator/materialization detail, не durable identity результата.

## Invariant 10 — public extension boundary нейтральна

Публичные repos знают generic capability contracts, но не внутреннее устройство закрытых implementations.

## Invariant 11 — UI design и artifact/report design независимы

Theme приложения не должна случайно определять Excel/PPTX/DOCX identity и наоборот.

## Invariant 12 — UNKNOWN сохраняется

Недоступность, неопределённый effect outcome, отсутствующее знание или ambiguous state не превращаются автоматически в success/false/empty.

## Invariant 13 — implementation topology не определяет ontology

То, что Case сейчас лежит в Windows package, не означает, что Windows является его естественным semantic owner.

## Invariant 14 — direct core use остаётся допустимым

Jupyter/Python consumer может вызывать `stratbox` напрямую. В этом режиме он сознательно находится вне Strategy Box application Work/history/authorization контура, если явно к нему не подключён.

## Invariant 15 — новый repository требует независимой причины существования

Минимум одна материальная причина из:

```text
independent lifecycle
independent deployment
independent consumer set
independent trust/access boundary
independent failure/recovery
independent release cadence
independent maintenance ownership
```

Красивой диаграммы недостаточно.

---

# 22. Главные конфликты корпуса и их разрешение

## C1. `stratbox-core` или `stratbox-host`

**Статус:** resolved at responsibility level.

- общая application runtime responsibility — устойчива;
- как библиотечный `stratbox-core` она была полезной промежуточной моделью;
- независимый headless lifecycle делает host/service физически более естественным owner;
- отдельный core repo не создаётся только ради названия.

**Result:** logical Application Runtime + strong target physical `stratbox-host`.

## C2. Scheduler — AppDock или Strategy Box

**Статус:** resolved.

- platform scheduling/process primitives могут находиться в AppDock;
- product automation semantics, triggers, policies и создание Strategy Box Job принадлежат Strategy Box runtime.

## C3. Artifact Catalog — core или application runtime

**Статус:** resolved by decomposition.

- artifact semantic contracts/provenance — core;
- runtime index/visibility/Work relations — application runtime;
- bytes — storage backend.

## C4. Scenario как главный объект продукта или Work/Thread

**Статус:** unresolved semantic detail, direction clarified.

Current UI scenario-first. Поздний корпус показывает, что durable Work шире одного Scenario и Thread шире одного run.

**Result:** не закреплять Scenario как главный product object в System Model. Exact ontology → тема 02/04.

## C5. Background как тип Scenario

**Статус:** superseded.

Current enum допускает `background`, но поздний synthesis убедительно показывает, что background — execution mode/policy.

## C6. AppDock как владелец файлов/логов/задач продукта

**Статус:** ранняя формулировка refined/superseded.

AppDock предоставляет platform/runtime capabilities и observability boundary; Strategy Box остаётся владельцем product workspace/artifact/work/job semantics.

## C7. Общий design repository прямо сейчас

**Статус:** open.

Design responsibility доказана. Отдельный repo — нет.

## C8. Один universal Knowledge graph

**Статус:** open.

Epistemic distinctions нужны. Universal heavy storage/model ещё не доказан всеми consumers.

---

# 23. Исторические идеи, которые считать вытесненными

Материалы `01-old-notes` дали полезные исходные вопросы, но несколько прежних решений больше не должны влиять на current architecture.

## H1. Launcher.exe как самостоятельный owner установки и lifecycle

**SUPERSEDED.** Эти responsibilities перешли к AppDock platform model.

## H2. GUI внутри репозитория `stratbox`

**SUPERSEDED.** Core/surface split уже материализован отдельным `stratbox-windows` и защищён текущими owner rules.

## H3. `stratbox` одновременно functional core + GUI application

**SUPERSEDED.** Core сохраняется reusable library.

## H4. Background processes как отдельный класс Scenario

**SUPERSEDED.** Background — runtime mode/automation execution concern.

## H5. Внешний scheduler как единственная естественная автоматизация

**PARTIALLY SUPERSEDED.** Core operations должны оставаться пригодными для Airflow/other external orchestration, но сам Strategy Box product нуждается в собственном durable automation semantics, если хочет показывать те же jobs во всех clients.

## H6. Scenario как контейнер практически всей пользовательской работы

**SUPERSEDED AS UNIVERSAL MODEL.** Scenario остаётся reusable capability/workflow definition, но долгоживущая Work и interaction context шире execution definition.

## H7. AppDock как прямой owner прикладных files/logs/results Strategy Box

**REFINED.** Он даёт platform roots, lifecycle и capabilities; предметная семантика workspace/artifacts/results остаётся Strategy Box-side.

## H8. Ручная app-прокладка рядом с domain code внутри одного repo

**SUPERSEDED PHYSICALLY, PRINCIPLE RETAINED.** Сохраняется принцип «broad canonical operation → product projection → thin platform boundary», но app projection больше не принадлежит `stratbox` repository.

---

# 24. Локальные белые пятна, выявленные системным проходом

## 24.1. Canonical Work ontology

**UNKNOWN.** Требуется тема 02/04:

- Thread ↔ Work cardinality;
- Work ↔ Case;
- Case ↔ Job;
- retry/new attempt semantics;
- child Work;
- background system Work;
- closure/acceptance.

## 24.2. Host API contract

**UNKNOWN.** Нужно определить:

- local IPC vs HTTP loopback;
- REST/event stream contract;
- command idempotency;
- reconnect snapshot + event cursor;
- compatibility negotiation;
- client SDK generation.

## 24.3. Local mode topology

**UNKNOWN / implementation probe.** Всегда ли desktop запускает отдельный host process, либо допустим embedded single-user mode с теми же interfaces.

## 24.4. Durable persistence

**UNKNOWN.** Logical owner ясен — application runtime. Физический выбор, schema migration, transaction/outbox/recovery — тема 05.

## 24.5. Product authorization

**UNKNOWN.** Требуется конкретный split:

- AppDock/platform access;
- Strategy Box product roles/capabilities;
- object-level access Work/Artifact;
- approvals/destructive effects;
- delegated AI authority.

## 24.6. Cross-device preferences

**UNKNOWN.** Device-local theme/window/navigation принадлежат client. Shared defaults/presets возможно должны жить в application runtime. Нужен реальный consumer и lifecycle.

## 24.7. Notification boundary

**UNKNOWN.** Product decides **что** является notification-worthy; platform/client decides **как** доставить OS/mobile notification. Требуется contract.

## 24.8. Artifact retention и garbage collection

**UNKNOWN.** Semantic owner split понятен, но кто принимает retention policy, как учитываются pinned/shared artifacts, source snapshots и reproducibility dependencies — ещё не сведено.

## 24.9. Search/indexing

**UNKNOWN.** Будущий поиск по Work, Threads, artifacts, datasets, sources и events требует отдельного projection/index owner.

## 24.10. Backup / recovery

**UNKNOWN.** AppDock восстанавливает platform/runtime environment; Strategy Box host восстанавливает application durable state. Нужен explicit boundary и согласованный support flow.

## 24.11. Resource governance

**UNKNOWN.** CPU/RAM/network/storage/solver capacity и resource leases должны стать node-scoped, но конкретный resource model ещё требует отдельного системного решения.

## 24.12. Host/client version skew

**UNKNOWN.** После появления разных clients будет нужен version negotiation contract; простой Python package pin перестанет быть достаточным.

## 24.13. Knowledge object granularity

**UNKNOWN.** Нужно определить, какие analytical claims/evidence становятся durable first-class objects, а какие достаточно хранить как structured Result + provenance.

## 24.14. Design distribution

**UNKNOWN.** JSON/tokens package, generated SDK/resources или самостоятельный repo — решать после появления второго frontend implementation.

## 24.15. Extension lifecycle

**UNKNOWN at application level.** Core extension activation semantics достаточно хорошо исследована. Отдельно требуется решить, как application runtime сообщает availability/capability changes clients и что происходит с saved Work при исчезновении capability/version.

---

# 25. Candidate target system model

Это целевая гипотеза, собранная из разрешённых конфликтов. Она сознательно отделяет **logical system** от **physical repositories**.

## 25.1. Logical system

### A. Domain & Analytical Core

Owner: `stratbox`.

Responsibilities:

```text
source semantics
reference data
format/data decoding
canonical datasets
banking/macro calculations
validation/reconstruction
provenance/evidence
canonical capabilities
artifact/report generation semantics
neutral infrastructure contracts
extension contracts
```

### B. Strategy Box Application Runtime

Owner: отдельная product responsibility.

Responsibilities:

```text
Work / interaction contexts
capability projection
planning
execution submission
Case / Job / Attempt
scheduler / automation
resource coordination
cancellation/retry/recovery
shared application state
collaboration
product authorization
artifact runtime catalogue
application events/API
```

### C. Client/Surface Semantics

Owner: product client contract + per-surface implementation.

Responsibilities:

```text
view-neutral projections
action availability
forms
navigation semantics
filters/search requests
local drafts
reconnect/client cache
```

### D. Platform-specific Surfaces

Owners:

```text
Windows → stratbox-windows
Web     → future owner when materialized
Android → future owner when materialized
```

Responsibilities: rendering + OS/browser/mobile integration only.

### E. Design System

Owner: logical Strategy Box design responsibility.

Responsibilities: UI visual semantics, tokens, motion, accessibility patterns.

Physical owner TBD.

### F. Platform Environment

Owner: AppDock.

Responsibilities: release/deployment/node/session/environment/service lifecycle/health/recovery/platform remote.

### G. Environment Capability Implementations

Owner: external/private deployments.

Responsibilities: concrete infrastructure implementations behind public neutral contracts.

### H. Cognitive Consumer

Owner: PROTOS or another future cognitive system.

Responsibilities: intent interpretation, planning/selection/composition under granted authority. No ownership of Strategy Box domain truth.

## 25.2. Candidate physical topology

```text
                           AppDock
          deployment / node / session / service lifecycle
                              │
                              ▼
                     ┌─────────────────┐
                     │ stratbox-host   │   TARGET, strong
                     │ app runtime     │
                     └───────┬─────────┘
                             │
                             ▼
                         stratbox
                    domain/business core

              ▲              ▲              ▲
              │              │              │
     stratbox-windows   stratbox-web   stratbox-android
        CURRENT          FUTURE          FUTURE
              \              |              /
               \──── host/client contract ─/

Design semantics: shared logical owner, physical packaging TBD.
Cognitive integration: external consumer of host/capability contracts.
Environment-specific implementations: external/private behind generic contracts.
```

Direct library use remains valid:

```text
Jupyter / Python / external scheduler
              ↓
           stratbox
```

Такой consumer сознательно обходит product-level Work/Job history, если сам не использует application-runtime API.

---

# 26. Что должно произойти с текущим `stratbox-windows`

Это не migration plan, но System Model позволяет классифицировать существующие зоны.

## Остаётся в Windows

```text
Qt widgets/shell
Windows window lifecycle
file dialogs
open/reveal/clipboard
Windows notifications
platform-specific accessibility/rendering
client-side drafts/preferences
Windows-specific resources
```

## Уходит из роли authoritative owner

```text
Case store
shared event truth
shared artifact index
assignments truth
presence truth
background/automation state
job execution coordination
scheduler
shared persistence
product authorization
```

Эти responsibilities переходят в общий application runtime/host.

## Может стать shared semantic contract

```text
operation/scenario presentation models
form schemas
chat/work projections
case/job projections
status/action vocabulary
artifact/problem projections
```

Физически exact placement определяется после host API design.

---

# 27. Что должно произойти с `stratbox`

## Сохранить

- pure library nature;
- neutral storage/network/runtime contracts;
- direct Python use;
- domain packages;
- typed Requests/Results;
- source/reference governance;
- provenance/evidence;
- business artifact/export generation.

## Усилить

- stable canonical operation identity;
- capability descriptors;
- unified Result/Failure/Progress conventions;
- source snapshot/provenance envelope;
- artifact semantic contracts;
- extension API neutrality;
- explicit error semantics;
- public/private hygiene.

## Не добавлять

- UI navigation;
- user presence;
- shared chat;
- global job queue;
- product scheduler;
- AppDock Node lifecycle;
- mobile/web code;
- arbitrary organization-specific policy.

---

# 28. What belongs to AppDock — final boundary

Для последующих исследований полезно закрепить короткую таблицу.

| Вопрос | Owner |
|---|---|
| Как поставить Strategy Box? | AppDock |
| Какую release/package graph запустить? | AppDock |
| На каком Node живёт environment? | AppDock |
| Какая Session активна? | AppDock platform truth |
| Как стартовать/остановить Strategy Box Host process? | AppDock |
| Healthy ли process/environment? | AppDock |
| Что пользователь сейчас анализирует? | Strategy Box |
| Какой Work открыт? | Strategy Box runtime |
| Какой Job выполняется и почему? | Strategy Box runtime |
| Какой domain result получен? | `stratbox` + application projection |
| Какое расписание должно обновлять банковские данные? | Strategy Box runtime |
| Кто может отменить конкретный Work/Job? | Strategy Box product authz, опираясь на platform principal |
| Как открыть remote Node/transport? | AppDock platform boundary |
| Как исполнить конкретный Strategy Box plan на этом node? | Strategy Box runtime/execution backend |
| Где platform evidence о crash? | AppDock |
| Где domain diagnostics результата? | `stratbox` |

---

# 29. Decision / Gap register темы 01

| Объект | Статус | Вывод |
|---|---|---|
| `stratbox` как отдельный Domain Library | **устойчиво** | сохранять независимым reusable core |
| Windows как отдельная surface | **устойчиво** | rendering/desktop integration owner |
| Общий application runtime | **устойчиво логически** | отдельная authority от core/surface/AppDock |
| Headless runtime service | **вероятная target direction** | требования lifecycle уже материальны |
| Имя/repo `stratbox-host` | **сильная гипотеза** | лучше соответствует самостоятельному runtime lifecycle |
| Отдельный `stratbox-core` repo | **вытеснено как обязательная физическая граница** | responsibility survives, repo not required |
| Web surface | **target hypothesis** | materialize при реальном browser product |
| Android surface | **target hypothesis** | готовить shared semantics сейчас, repo при реализации |
| Design system responsibility | **устойчиво логически** | общий visual language нужен |
| Отдельный `stratbox-design` repo | **UNKNOWN** | дождаться второго consumer/release lifecycle |
| AppDock как platform owner | **устойчиво** | deployment/node/session/lifecycle/health/recovery |
| AppDock как business scheduler | **вытеснено** | product automation belongs Strategy Box runtime |
| Windows process как durable shared authority | **вытеснено target-моделью** | current prototype only |
| Background как Scenario kind | **вытеснено** | execution policy/mode |
| Scenario как главный durable Work object | **не подтверждено** | Work wider; exact ontology deferred |
| Shared collaboration truth | **target direction** | node/application-runtime scoped |
| Artifact identity выше path | **устойчиво** | logical ID + provenance |
| Artifact semantic owner | **устойчиво** | core/domain |
| Artifact workflow/catalog owner | **устойчиво на responsibility level** | application runtime |
| Generic extension boundary | **устойчиво** | public contracts only |
| Concrete private extension knowledge in public repos | **запрещено** | sanitation required |
| AI-specific operation API | **не нужно** | AI is consumer of canonical capabilities |
| General Knowledge/Claim store | **UNKNOWN** | need real consumer and Topic 03 analysis |
| Single-node transactional persistence | **strong target need** | technology/schema deferred to Topic 05 |
| Local desktop always-through-host | **needs implementation probe** | semantic target yes; packaging/performance check needed |

---

# 30. Приоритетные системные проблемы, которые тема 01 передаёт дальше

## P0 — Current-owner consistency

1. Синхронизировать Windows dependency/manifest metadata с текущим `stratbox`.
2. Синхронизировать Windows manifest/docs/tests по версиям AppDock contracts.
3. Очистить public packaging/docs от environment-specific private references.

Это hygiene, необходимый до любой крупной архитектурной миграции.

## P0 — Canonical semantic model

Следующая тема должна разрешить Work/Thread/Case/Job/Run/Attempt/Scenario/Scheme/Artifact/Result relations. Без этого host API и persistence легко закрепят случайную промежуточную терминологию.

## P1 — Host boundary

После semantic model нужен explicit application-runtime contract:

```text
commands
queries
snapshots
subscription/events
idempotency
version negotiation
principal context
artifact refs
```

## P1 — Durable state

Нужно отдельно решить authoritative stores, transaction model, migrations, recovery и projections.

## P1 — Core capability normalization

Host нельзя строить поверх неровного каталога ad hoc handlers. Canonical operations должны иметь stable identity и machine-readable contracts.

---

# 31. Provenance существенных выводов

Ниже перечислены Strategy Box-side источники, использованные в synthesis. Список показывает происхождение вывода, но не делает Research Result текущим Product owner.

## 31.1. Программная рамка

- `_mw/epochs-001-strategy-box-development/research/strategy_box_03_consolidation_research_program.md` — scope темы 01, метод responsibility → owner → physical boundary, классификация current/target/conflict/unknown.
- `_mw/AGENTS.md` — текущая owner model Strategy Box workspace и правило, что Research не переносит implementation ownership.
- `_mw/epochs-001-strategy-box-development/research/02-base-study/README.md` — baseline и authority source hierarchy.

## 31.2. Current-state owners

### `stratbox`

- root `AGENTS.md`, `README.md`, `docs/architecture.md`;
- `pyproject.toml`;
- `src/stratbox/base/runtime.py`;
- `stratbox_base_study_current_state_2026-10-06.md`;
- актуальный `main` точечно перепроверен 2026-10-08.

### `stratbox-windows`

- root `README.md`, `docs/architecture.md`;
- `pyproject.toml`;
- `appdock/manifest.json`;
- `application/cases/models.py`;
- `application/scenarios/models.py`;
- `application/background/models.py`;
- `application/history/persistence.py`;
- `runtime/bootstrap.py`;
- `stratbox-windows_current_state_full_research_2026-10-06.md`;
- актуальный `main` точечно перепроверен 2026-10-08.

### AppDock boundary

- базовое описание AppDock из материалов проекта;
- актуальный root README/engineering constraints AppDock;
- current platform observability boundary использован только для ownership separation platform state vs product state.

## 31.3. Архитектурные исследования `02-base-study`

Ключевые линии synthesis:

- целевая core/application/design декомпозиция;
- web/self-hosted и headless host architecture;
- commands/scenarios/cascades;
- execution control и user path;
- background jobs/processes;
- automation/AI;
- single-node multi-user;
- observability/errors/logs;
- file/artifact layer;
- FileStore/file formats;
- registry/source governance;
- system settings;
- interface visual system;
- artifact style sets;
- Windows interface requirements;
- business-segment portability/reuse;
- generic corporate extension contract;
- machine capability/scheme architecture;
- PROTOS integration boundary;
- Strategy Box epistemic/semantic target research на основе MADAR-методологии.

## 31.4. `01-old-notes`

Использованы только как historical provenance:

- ранняя модель Launcher + GUI inside core;
- ранняя interface/scenario model;
- исторический business-logic refactor;
- майский patch history.

Из них сохранены только идеи, подтверждённые текущим кодом или свежими исследованиями; старые physical boundaries получили статус `SUPERSEDED` там, где текущий owner уже изменился.

---

# 32. Финальный консолидированный вывод

Strategy Box уже нельзя правильно описать формулой:

```text
stratbox + Windows GUI
```

Но также преждевременно описывать его списком будущих репозиториев.

Самая устойчивая модель — это **четыре authority уровня и несколько projections**:

```text
1. Domain/Analytical Truth
   owner: stratbox

2. Product Work/Execution Truth
   owner: Strategy Box Application Runtime
   target materialization: headless host/service

3. Platform Runtime Truth
   owner: AppDock

4. Presentation Truth
   owner: concrete surface + shared design semantics
```

Снаружи к ним подключаются:

```text
Environment capabilities
    через нейтральную public extension boundary

Cognitive system
    как consumer/planner admitted capabilities
```

Аналитические сущности проходят другой разрез:

```text
source/data/evidence/result
    → stratbox

Work/plan/job/automation/collaboration
    → Strategy Box runtime

node/session/environment/lifecycle
    → AppDock

rendering/navigation/device integration
    → Windows/Web/Android
```

Это снимает главное противоречие корпуса. `stratbox-core`, `stratbox-host`, application logic внутри Windows и AppDock host semantics описывали **разные попытки найти место для одной недостающей ответственности**. Ответ состоит не в выборе красивого имени, а в признании отдельной Strategy Box application-runtime authority. После этого физическая форма выводится естественно: текущий Windows prototype временно содержит её части, но целевая длительная/multi-user/background/mobile система требует headless owner с отдельным lifecycle. Именно поэтому `stratbox-host` является сильной физической гипотезой, тогда как отдельный `stratbox-core` repository перестаёт быть обязательным.

Следующий системный риск теперь лежит уже не в вопросе «какой репозиторий создать», а в **канонической семантике объектов**. Пока `Scenario`, `Scheme`, `Thread`, `Work`, `Case`, `Job`, `Run`, `Attempt`, `Result` и `Artifact` не сведены в одну непротиворечивую модель, нельзя безопасно замораживать host API, database schema или cross-platform client contracts. Это и является естественным переходом к теме 02 третьей ветки.
