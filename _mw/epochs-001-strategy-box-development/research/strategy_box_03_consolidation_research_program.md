# Strategy Box — программа консолидирующих исследований третьей ветки

## Общая идея

Третью ветку `03-consolidation-research` стоит строить не как ещё одну серию тематических исследований, а как **сведение Strategy Box в единую целевую систему**.

Во второй ветке уже накоплен большой корпус исследований: текущее состояние `stratbox`, `stratbox-windows`, отдельные работы по операциям и сценариям, файлово-артефактному слою, источникам и справочникам, наблюдаемости, multi-user, web/self-hosted, автоматизации и ИИ, настройкам, визуальной системе, переносимости, MADAR/PROTOS и целевой архитектуре core.

Поэтому третья ветка должна отвечать уже не на вопрос:

> «Как устроен или должен быть устроен конкретный аспект Strategy Box?»

а на вопрос:

> **«Как Strategy Box целиком устроен как одна система, если одновременно учесть все накопленные исследования?»**

Основной метод — несколько **сквозных проходов сверху вниз через весь Strategy Box**. Каждый такой проход должен затрагивать `stratbox`, application/runtime, Windows/Web/Android surfaces, AppDock boundary, данные, execution, пользователей, AI и расширения там, где они действительно относятся к теме.

Именно так локальные белые пятна будут проявляться естественно.

---

# Главное изменение подхода

`02-base-study` преимущественно исследовала отдельные аспекты:

- FileStore;
- артефакты;
- команды, сценарии и каскады;
- observability;
- multi-user;
- settings;
- visual system;
- automation/AI;
- PROTOS;
- MADAR;
- web/self-hosted;
- переносимость;
- целевую архитектуру core;
- и другие отдельные темы.

В `03-consolidation-research` не следует повторять ту же тематическую структуру. Иначе получится второй комплект похожих файлов.

Вместо этого третья ветка должна состоять из нескольких **системных сквозных исследований**, каждое из которых собирает воедино материалы сразу из нескольких исследований второй ветки.

Также необходимо постоянно различать три разных уровня материала:

1. **что существует сейчас**;
2. **что уже достаточно устойчиво как согласованный исследовательский вывод**;
3. **что пока является целевой гипотезой или рекомендацией**.

Консолидация не должна смешивать эти уровни.

---

# Предлагаемая структура третьей ветки

Предлагается провести **9 основных консолидирующих исследований плюс финальное сведение**.

| № | Исследование | Главный вопрос |
|---|---|---|
| 00 | Corpus Map & Open Questions | Что накоплено, где документы пересекаются, противоречат друг другу или оставляют UNKNOWN |
| 01 | Strategy Box System Model | Что такое Strategy Box целиком, из каких систем он состоит и где проходят ownership boundaries |
| 02 | Canonical Semantic Model | Какие сущности реально существуют в продукте и как они называются |
| 03 | Data → Knowledge Architecture | Как данные проходят путь от внешнего источника до доказуемого результата |
| 04 | Work → Execution Architecture | Как запрос превращается в Work, план, job, operation runs, artifacts и completion |
| 05 | State, Persistence & Collaboration | Где живёт состояние системы, пользователей, работ, запусков, истории и совместной работы |
| 06 | Capability, Extension & Automation Architecture | Как устроены операции, сценарии, расширения, фоновые процессы, AI и внешние execution backends |
| 07 | Product Surface Architecture | Как одна система проецируется в Windows, Web, Android и другие поверхности |
| 08 | Trust, Safety & System Qualities | Ошибки, observability, permissions, recovery, concurrency, reliability, versioning, performance |
| 09 | Whole-System Target Architecture | Итоговая целевая архитектура Strategy Box и реестр оставшихся развилок |

После `09` имеет смысл переходить к отдельной сборке Knowledge/Product решений.

---

# 00. Corpus Map & Open Questions

Это первое и сравнительно компактное исследование.

Его задача — не пересказать все исследования второй ветки, а построить **карту утверждений, пересечений, противоречий и пробелов**.

Для каждого файла `02-base-study` стоит фиксировать:

| Поле | Смысл |
|---|---|
| Research | исходный файл |
| Основные сущности | какие понятия он вводит |
| Current findings | факты о текущей реализации |
| Target propositions | предложенная целевая архитектура |
| Dependencies | какие другие исследования предполагает |
| Overlap | где повторяет другие документы |
| Conflict | где реально расходится |
| Superseded | какие ранние идеи уже вытеснены более поздними |
| UNKNOWN | что осталось открытым |
| Consolidation destination | в какое исследование 01–09 уходит материал |

Особенно важно собрать термины, которые исследовались с разных сторон:

- `Operation`;
- `Command`;
- `Scenario`;
- `Cascade`;
- `Machine Scheme`;
- `Capability`;
- `Work`;
- `Case`;
- `Job`;
- `Run`;
- `Attempt`;
- `Thread`;
- `Artifact`;
- `Result`.

Вторая ветка правильно рассматривала их в разных контекстах. В третьей нужно установить **единую непротиворечивую онтологию**.

---

# 01. Strategy Box System Model

Первое большое консолидирующее исследование.

Главный вопрос:

> **Что такое Strategy Box как целая вычислительная и продуктовая система?**

Начинать следует буквально сверху:

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

Далее постепенно раскладываются ответственности и владельцы.

Здесь необходимо окончательно разобраться с уже появившимися архитектурными сущностями и возможными будущими физическими компонентами:

```text
stratbox
stratbox-core
stratbox-design
stratbox-windows
stratbox-web
stratbox-android
stratbox-host
AppDock
PROTOS
```

Результатом исследования не должно быть автоматическое утверждение, что каждый из этих компонентов обязан существовать как отдельный пакет или репозиторий.

Сначала определяется:

> responsibility → owner

и только затем:

> owner → repository/package/process.

Это защищает архитектуру от появления физических границ только ради красивой схемы.

---

# 02. Canonical Semantic Model

Одно из наиболее важных исследований третьей ветки.

Strategy Box уже достаточно сложен, чтобы проблемы архитектуры возникали не только из-за кода, но и из-за неоднозначности сущностей.

Нужен единый словарь примерно такого уровня:

```text
Source
SourceSnapshot
Registry
Observation
Dataset
Claim
Evidence

Capability
Operation
Scenario
Cascade / Scheme

Thread
Work
ExecutionPlan
Job
OperationRun
Attempt

Artifact
ArtifactManifest
Result

User
Principal
Actor
Session
Node

Trigger
Automation

Plugin
Provider
ExecutionBackend
Surface
```

Конечная структура должна родиться из консолидации корпуса, а не быть заранее навязана этим черновым списком.

Именно здесь необходимо решить вопросы вроде:

- `Case` — это Work или Run?
- `Scenario` — workflow definition или capability?
- `Cascade` — самостоятельная сущность или разновидность Scenario?
- `Machine Scheme` — над Scenario или рядом?
- `Result` и `Artifact` — разные сущности?
- `Thread` и `Work` — какие отношения между ними?
- `Operation` — техническая функция или семантическая capability?

После стабилизации терминологии последующие архитектурные решения станут значительно проще.

MADAR и PROTOS здесь полезны как **проверочные линзы**, но не как владельцы архитектуры Strategy Box.

---

# 03. Data → Knowledge Architecture

Это полный вертикальный проход через данные.

Не отдельное исследование FileStore, registry или artifacts, а единая цепочка:

```text
external authority
        ↓
SourceDescriptor
        ↓
SourceSnapshot
        ↓
raw preservation
        ↓
technical decoding
        ↓
semantic normalization
        ↓
canonical data
        ↓
validation
        ↓
derived / reconstruction
        ↓
evidence
        ↓
claim / analytical result
        ↓
view
        ↓
artifact
        ↓
artifact lineage / provenance
```

Вместе должны быть рассмотрены:

- FileStore;
- Workspace;
- cache;
- scratch/staging;
- форматы файлов;
- source catalog;
- registry lifecycle;
- canonical datasets;
- provenance;
- artifact model;
- artifact catalog;
- style sets;
- metadata;
- authoring;
- retention;
- hashes;
- freshness;
- lineage;
- Knowledge.

Такой проход должен выявить и белые пятна, например:

- кто является canonical owner Artifact Catalog;
- какой объект связывает SourceSnapshot → Dataset → Artifact;
- где хранится provenance обычных операций;
- что считается current result, а что historical artifact;
- когда cache становится reproducibility dependency;
- как физический файл соотносится с логическим Artifact ID.

---

# 04. Work → Execution Architecture

Второй большой системный позвоночник.

Целевая цепочка для исследования:

```text
User / Automation / AI
        ↓
Intent
        ↓
Work
        ↓
Capability selection
        ↓
Scenario / Scheme
        ↓
ExecutionPlan
        ↓
Job
        ↓
OperationRun
        ↓
Attempt
        ↓
Progress / Events
        ↓
Terminal Outcome
        ↓
Artifacts / Result
        ↓
Closure
```

Здесь вместе сводятся исследования про:

- commands/scenarios/cascades;
- execution control;
- background automation;
- cancellation;
- AI;
- multi-user;
- observability.

Главная задача — определить **единую execution state machine**.

Foreground, background, scheduled, remote, user-triggered и AI-triggered запуск должны рассматриваться как разные способы инициировать один и тот же execution spine, а не как отдельные движки.

Это позволит избежать появления нескольких несовместимых систем исполнения.

---

# 05. State, Persistence & Collaboration

Одна из областей, где третья ветка, вероятно, обнаружит особенно много локальных белых пятен.

Главный вопрос:

> **Где находится durable truth Strategy Box?**

Нужно системно разобрать:

```text
configuration
preferences
surface state
draft state

thread state
work state
execution state
automation state

artifact metadata
provenance

user state
presence
read cursors
assignments

node-local state
shared-node state
host state
```

Для каждого типа состояния следует определить:

```text
owner
scope
lifetime
persistence
schema version
concurrency
recovery
projection
```

Это должно дать ответы на вопросы:

- где JSON ещё допустим;
- где уже нужна транзакционная persistence;
- какое состояние принадлежит AppDock;
- какое состояние принадлежит самому Strategy Box;
- что является локальным;
- что является shared-node truth;
- что должно переживать перезапуск;
- какие projections можно восстановить.

Для будущих Web и Android surfaces этот слой является критическим.

---

# 06. Capability, Extension & Automation Architecture

Здесь собирается всё, что позволяет Strategy Box расти, сохраняя архитектурную форму.

Нужно свести в одну модель:

```text
canonical operations
capability descriptors
scenario definitions
machine schemes
automation triggers
execution backends
generic plugins/extensions
style providers
source providers
AI tool exposure
```

Главный вопрос:

> **Что в Strategy Box может расширяться, каким contract, кто это обнаруживает, кто активирует и какие эффекты расширение получает?**

В публичной архитектуре рассматривается только **общий extension/plugin contract**.

Конкретные закрытые реализации внутренних расширений не должны проникать в публичные `stratbox` и `stratbox-windows`.

Это же исследование должно связать Machine Scheme / PROTOS-ready capability с обычной архитектурой операций.

Не следует создавать отдельную «AI-архитектуру операций». Машина должна видеть те же canonical capabilities, только через безопасную machine-readable projection.

---

# 07. Product Surface Architecture

После стабилизации System Model, semantics, data и execution можно полноценно консолидировать интерфейс.

Главный вопрос:

> **Какая одна семантическая система Strategy Box должна одинаково проецироваться в разные surfaces?**

```text
shared product semantics
        │
        ├── Windows desktop
        ├── Web
        ├── Android
        └── future narrow surfaces
```

Здесь сводятся:

- Work/chat;
- Explorer;
- scenario catalogue;
- runs;
- inspector;
- artifacts;
- settings;
- notifications;
- presence;
- assignments;
- design tokens;
- themes;
- motion;
- accessibility;
- responsive/adaptive behaviour.

Целевая архитектура должна строиться как:

```text
semantic surface contracts
        ↓
platform adaptation
        ↓
native rendering
```

То есть interface architecture не должна зависеть от Qt widgets как от смыслового владельца.

Это позволит `stratbox-android` повторно использовать стандартные application/presentation semantics.

---

# 08. Trust, Safety & System Qualities

Отдельное системное исследование нефункциональных качеств.

Нужно пройти весь Strategy Box по следующим осям:

| Ось | Что проверяем |
|---|---|
| Reliability | crash safety, partial failure, retries, recovery |
| Error semantics | typed failures, terminal outcomes, UNKNOWN |
| Observability | progress, events, logs, diagnostics, problems |
| Security | identity, authorization, secrets, network boundaries |
| Effect safety | destructive operations, confirmation, permissions |
| Concurrency | jobs, resources, multi-user conflicts |
| Idempotency | retries, reconnect, remote execution |
| Persistence | atomicity, corruption, migration |
| Versioning | schemas, contracts, registries, capabilities |
| Performance | memory, streaming, caches, expensive computation |
| Portability | Windows/Web/Android/host |
| Testability | unit/integration/E2E/property/contract tests |
| Operability | diagnostics, support bundle, repair |
| Accessibility | keyboard, reduced motion, contrast |
| Resource use | CPU/RAM/network/storage budgets |

Именно здесь должны быть сформулированы **system-wide invariants**.

Примеры:

> Ошибка transport никогда не маскируется как пустой результат.

> Завершённый Job имеет ровно один terminal outcome.

> Destructive operation не может молча завершиться частично.

> Artifact всегда можно связать с породившим его execution/provenance.

> UI не является authority durable work state.

> Повторный request с тем же idempotency identity не порождает случайно второй эффект.

Это свойства всей системы, а не отдельных модулей.

---

# 09. Whole-System Target Architecture

Финальное большое исследование третьей ветки.

Его не следует писать первым.

Оно должно собраться из результатов `01–08`.

Предлагаемая структура:

```text
Strategy Box
│
├── Purpose & invariants
│
├── Object / semantic model
│
├── Knowledge & data plane
│
├── Capability plane
│
├── Work & execution plane
│
├── State & persistence plane
│
├── Collaboration & authority plane
│
├── Artifact plane
│
├── Surface plane
│
├── Extension plane
│
└── Platform boundary
```

Ниже — ownership:

```text
stratbox
Strategy Box application core
surface clients
host
design system
AppDock boundary
external cognitive system boundary
```

Обязательно должны существовать две отдельные карты.

## Logical architecture

Какие системы и ответственности существуют концептуально.

## Physical architecture

В каких packages, repositories и processes эти ответственности физически размещены.

Это разделение особенно важно, чтобы не превращать каждую найденную архитектурную ответственность в новый репозиторий.

---

# Финальный synthesis: Decision / Gap Register

После `09` стоит сделать небольшой отдельный итоговый файл.

Его задача — не создавать ещё одну архитектуру, а показать степень решённости вопросов.

| Объект | Статус |
|---|---|
| Решение устойчиво | несколько исследований сходятся, фактических противоречий нет |
| Вероятная target direction | сильная гипотеза, но Product Decision ещё отсутствует |
| Conflict | существуют реально несовместимые варианты |
| UNKNOWN | материала недостаточно |
| Needs implementation probe | без кода/прототипа выбрать нельзя |
| External dependency | ответ зависит от AppDock/PROTOS/другого owner |
| Deferred | сознательно оставлено на следующую эпоху |

Этот реестр станет мостом от Research к следующей фазе.

---

# Одинаковая внутренняя процедура каждого исследования

Чтобы `01–09` действительно складывались друг с другом, каждому исследованию стоит задать одну форму.

Сначала выполняется **cold entry**:

1. README текущей ветки;
2. Corpus Map;
3. относящиеся исследования `02-base-study`;
4. текущий код владельцев только там, где требуется проверить факт или разрешить конфликт.

После этого исследование проходит один и тот же путь:

```text
Baseline
→ Current Truth
→ Existing Propositions
→ Conflicts
→ Cross-system Synthesis
→ White Spots
→ Candidate Target Model
→ Invariants
→ Ownership
→ Open Questions
```

Каждое существенное утверждение следует логически классифицировать как:

```text
CURRENT
CONSOLIDATED
TARGET-HYPOTHESIS
CONFLICT
SUPERSEDED
UNKNOWN
```

Необязательно буквально ставить эту метку перед каждым абзацем, но такая классификация должна существовать в исследовательской логике.

---

# Белые пятна должны искаться активно

Третья ветка не должна ограничиваться механическим сведением существующего материала.

Если при системном проходе возникает сущность или проблема, для которой нет устойчивого ответа, это становится новой исследовательской задачей внутри текущего synthesis.

Уже сейчас возможными белыми пятнами выглядят:

- durable persistence architecture;
- schema migration;
- node-wide resource locking;
- search/indexing по Work и artifacts;
- notification semantics;
- artifact retention;
- authorization/effect model;
- host/client compatibility;
- offline/reconnect semantics;
- configuration ownership;
- backup/recovery boundary;
- resource budgeting;
- accessibility;
- localization;
- API evolution;
- database choice;
- lifecycle долгоживущего Work.

Некоторые из них после анализа окажутся деталями. Некоторые могут стать отдельными крупными блоками.

Поэтому список исследований третьей ветки должен быть устойчивым на уровне **сквозных системных вопросов**, а локальные исследования должны рождаться только при обнаружении реального разрыва.

---

# Рекомендуемый порядок выполнения

1. `00` — карта корпуса, пересечений, противоречий и UNKNOWN.
2. `01` — система целиком и ownership.
3. `02` — единая семантика объектов.
4. `03` — Data → Knowledge.
5. `04` — Work → Execution.
6. `05` — State / Persistence / Collaboration.
7. `06` — Capabilities / Extensions / Automation.
8. `07` — Surfaces / Windows / Web / Android / design.
9. `08` — Trust / Safety / Reliability / engineering qualities.
10. `09` — итоговая Whole-System Architecture.
11. Финальный Decision / Gap Register.

Такой порядок сильнее тематического:

- первые два исследования задают язык всему остальному;
- следующие четыре собирают машину Strategy Box;
- затем формируется поверхность;
- затем системные качества;
- финальная архитектура уже не придумывается отдельно, а получается из накопленного synthesis.

---

# Главный методологический принцип

В третьей ветке стоит отдельно закрепить правило:

> **Никаких преждевременных новых abstractions, repositories или packages только ради красивой схемы.**

Сначала:

```text
semantic responsibility
        ↓
owner
        ↓
contract
        ↓
physical boundary при реальной необходимости
```

Это особенно важно сейчас, когда Research corpus уже очень велик и существует риск построить архитектурно красивую, но избыточную систему.

Цель третьей ветки — не увеличить количество концепций, а **свести Strategy Box к минимальной, согласованной и проверяемой системной модели**.
