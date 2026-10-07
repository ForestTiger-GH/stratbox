# Strategy Box × PROTOS: от сценарного интерфейса к Chat / Work / Cognitive Scheme architecture

**Дата:** 2026-10-07  
**Контур:** Strategy Box, вторая ветка исследований  
**Предмет:** пользовательская и runtime-архитектура Strategy Box с учётом длительных чатов, памяти, артефактов, машинных когнитивных схем и параллельных независимых PROTOS-исполнителей  
**Статус:** Research Result; развитие и частичная корректировка предыдущего исследования `stratbox_protos_foundation_research_2026-10-07.md`

---

# 0. Executive conclusion

Новая постановка заметно меняет предыдущую картину.

Ранее естественным центром Strategy Box выглядели:

```text
Operation
→ Scenario
→ Case
→ Events
→ Artifacts
```

Это было разумно для продукта, где пользователь в основном выбирает заранее определённую машинную процедуру и запускает её.

После добавления настоящего PROTOS эта модель становится слишком execution-centric.

Когда пользователь сможет:

- писать свободный текст;
- вести длительный разговор;
- продолжать работу спустя время;
- параллельно запускать несколько задач;
- создавать несколько независимых ветвей работы;
- возвращаться к старому обсуждению;
- использовать много когнитивных схем в рамках одной работы;
- получать много артефактов;
- запускать одну и ту же схему несколькими независимыми cognitive executions;
- взаимодействовать с PROTOS других пользователей,

главной пользовательской сущностью становится уже не сценарий и даже не один Case.

Самая сильная целевая геометрия выглядит так:

```text
NODE / USER SPACE
    │
    ├── Thread / Chat A
    │      ├── Message
    │      ├── Work 1
    │      │     ├── Run 1 ── Scheme X ── Cognitive Activation A
    │      │     ├── Run 2 ── Scheme Y ── Cognitive Activation B
    │      │     ├── Run 3 ── Scheme Y ── Cognitive Activation C
    │      │     └── Artifacts / Evidence
    │      ├── Message
    │      ├── Work 2
    │      └── Artifacts
    │
    ├── Thread / Chat B
    │      ├── Work 3
    │      └── ...
    │
    └── Thread / Chat C
```

Главный архитектурный вывод:

> **На пользовательском уровне Strategy Box логично постепенно сделать chat/thread-centric. На внутреннем уровне он должен оставаться Work-centric. Когнитивные схемы должны стать capability/execution layer, а артефакты — first-class outputs внутри Work и Chat.**

Неправильно:

```text
Chat = Work = memory = execution history = source of truth
```

Правильно:

```text
Chat / Thread
    = пользовательский контекст и interaction container

Work
    = долговечная смысловая единица работы

Run
    = одно конкретное исполнение

Cognitive Scheme
    = повторно используемая машинная программа/способность

Cognitive Activation
    = конкретный независимый исполнитель

Artifact
    = долговечный продукт выполнения

Message
    = interaction event / carrier
```

Сам чат становится главным UX-контейнером, но **не становится главным semantic owner**.

---

# 1. Что изменилось относительно предыдущего исследования

Предыдущее исследование правильно вывело на первый план:

- canonical operations;
- durable Work;
- Job Manager;
- CognitivePort;
- capability registry;
- Authority;
- execution backend;
- federation.

В нём `Case` рассматривался как хороший кандидат на развитие в durable Work.

После текущей постановки это надо уточнить.

Текущий `ScenarioRunCase` связан с одним `scenario_id`, параметрами, step runs и результатом одного запуска. Для будущего PROTOS этого недостаточно.

Один человеческий Work может выглядеть так:

```text
Пользователь:
"Посмотри, что происходит с корпоративным кредитованием."

PROTOS:
    interprets request
    ↓
    запускает source refresh scheme
    ↓
    параллельно:
        analytical scheme A
        analytical scheme A
        analytical scheme B
    ↓
    собирает результаты
    ↓
    задаёт пользователю уточнение
    ↓
Пользователь:
"Сравни теперь с прошлым кварталом и отдельно выдели АПК."
    ↓
    продолжает тот же Work
    ↓
    запускает ещё три схемы
    ↓
    формирует таблицу
    ↓
    формирует DOCX
```

Это всё — один смысловой Work, но много отдельных execution runs.

Поэтому новая целевая модель:

```text
Thread
    ↓
Work
    ↓
Run
```

а не:

```text
Scenario
    ↓
Case
```

Текущий Case фактически содержит элементы сразу двух будущих сущностей:

```text
Work:
    semantic purpose
    user-facing continuity
    lifecycle

Run:
    конкретный scenario
    params
    stages
    step executions
    status
```

С учётом отсутствия требования обратной совместимости правильнее в будущем разнести эти понятия чисто, чем бесконечно расширять `ScenarioRunCase`.

---

# 2. Базовая онтология будущего Strategy Box

## 2.1. Thread / Chat

**Thread** — долговечный пользовательский interaction context.

UI может называть его просто:

> Чат

Внутреннее имя лучше делать нейтральнее:

```text
Thread
ConversationThread
InteractionThread
```

Thread отвечает на вопрос:

> В каком длительном пользовательском контексте происходит эта работа и к чему пользователь хочет вернуться позже?

Он содержит ссылки на:

- сообщения;
- Work;
- артефакты;
- attachments;
- thread-level summary/memory projections;
- participants.

Thread не должен владеть всей semantic truth работы.

## 2.2. Work

Work отвечает:

> Какая смысловая задача сейчас решается?

Примеры:

```text
"Обновить данные ЦБ"
"Проанализировать банковский сектор"
"Сравнить два периода"
"Подготовить файл"
"Проверить новую публикацию"
```

Work может:

- начаться из одного сообщения;
- продолжаться через десяток сообщений;
- порождать несколько Runs;
- иметь child Work;
- ждать пользователя;
- уйти в background;
- пережить restart;
- получить дополнительные данные;
- завершиться несколькими artifacts.

## 2.3. Run

Run отвечает:

> Какое конкретное исполнение сейчас произошло?

Например:

```text
Run #1:
    Scheme = cbr.source.refresh

Run #2:
    Scheme = corporate_lending.analysis

Run #3:
    Scheme = corporate_lending.analysis
    independent replica

Run #4:
    Scheme = compare.periods

Run #5:
    Scheme = export.docx
```

Run имеет:

- `run_id`;
- `work_id`;
- конкретный scheme/capability;
- input snapshot;
- executor;
- status;
- events;
- result;
- produced artifacts;
- metrics;
- diagnostics.

## 2.4. Cognitive Scheme

Cognitive Scheme отвечает:

> Какая повторно используемая машинная процедура / capability может быть применена?

Это ближе всего к:

- skill;
- plugin capability;
- compiled cognitive procedure;
- machine program.

Именно здесь расположены нынешние сценарии и каскады, а operations образуют более низкий уровень capability primitives.

## 2.5. Cognitive Activation

Cognitive Activation отвечает:

> Какая конкретная независимая когнитивная система сейчас выполняет работу?

Это не обязательно новый permanent actor.

Например:

```text
PROTOS profile = analytical.default
activation A = independent execution 1
activation B = independent execution 2
activation C = independent execution 3
```

Все три могут быть логически одинаковыми, но иметь:

- разные activation IDs;
- разные transient state;
- разные scratch contexts;
- разные branch inputs;
- разные resource allocations;
- возможно разные solver bindings.

## 2.6. Artifact

Artifact отвечает:

> Что устойчивого произвела работа?

Например:

- dataset;
- table;
- chart;
- Excel;
- report;
- Markdown;
- DOCX;
- source snapshot;
- analytical result;
- validation report.

Artifact должен жить независимо от chat-message rendering.

---

# 3. Являются ли operations / scenarios / cascades когнитивными схемами?

Короткий ответ:

> **Сценарии и каскады очень близки к compiled cognitive schemes. Operations чаще являются более низким уровнем — машинными capability primitives.**

## 3.1. Operation

Operation:

```text
скачать источник
прочитать форму
собрать canonical dataset
посчитать показатель
выгрузить XLSX
```

По смыслу это ближе к:

```text
instruction
tool capability
machine primitive
```

Часть cognitive scheme может скомпилироваться всего в одну operation. Тогда внешне различие исчезает, но архитектурно остаётся:

```text
Scheme
    определяет "как решать класс задач"

Operation
    определяет "какое конкретное машинное действие доступно"
```

## 3.2. Scenario

Scenario уже ближе к настоящей машинной когнитивной схеме. Он содержит purpose, parameterization, последовательность/graph действий, expected result и error semantics.

То есть:

```text
Scenario ≈ compiled procedure / skill
```

## 3.3. Cascade

Отдельная категория «Каскад» выглядит всё менее фундаментальной.

С точки зрения PROTOS каскад — это одна из execution topologies:

```text
Scheme
    contains nested schemes
```

или:

```text
Scheme
    graph of scheme invocations
```

Поэтому в будущей domain model:

> **Cascade лучше перестать считать отдельным верхнеуровневым типом capability.**

Он может стать `CompositeScheme` или `SchemeSpec.composition = graph`, но для пользователя отдельный постоянный раздел «Каскады» теряет смысл.

## 3.4. Более общий каталог

Перспективная модель:

```text
Capability Catalog

Primitive Capability
    Operation

Compiled Capability
    Scheme

Scheme composition:
    sequential
    conditional
    parallel
    nested
    cognitive/dynamic
```

Сегодняшние Operation / Scenario / Cascade не обязаны исчезнуть одномоментно, но перестают диктовать информационную архитектуру UI.

---

# 4. Почему сценарии оказались во главе угла интерфейса

Current-state research фиксирует top-level режимы:

```text
Проводник
Сценарии
Каскады
Фоновые
Участники
Поручения
```

При этом центральная область уже работает как scenario chat и показывает:

- cases;
- notices;
- artifacts;
- status;
- author;
- params.

Это переходная архитектура.

Центр уже похож на будущий interaction thread, но primary navigation всё ещё построена вокруг выбора machine procedure.

Как только появляется PROTOS:

```text
user intent
→ cognitive resolution
→ capability selection
```

пользователю всё реже нужно сначала искать схему.

Значит UI может перейти из:

```text
выбери сценарий
→ запусти
```

в:

```text
скажи, что требуется
→ PROTOS выберет/соберёт execution
```

При этом ручной запуск схемы остаётся важным power-user path.

---

# 5. Главная UX-инверсия

Сегодня:

```text
Scenario
    ↓
Case
    ↓
Chat card
```

Целевая форма:

```text
Chat / Thread
    ↓
User intent
    ↓
Work
    ↓
PROTOS chooses:
    Scheme A
    Scheme B
    Scheme C
    ...
    ↓
Runs
    ↓
Artifacts / answers
```

Из этого следует:

> **Chat/Thread должен стать главным entry point повседневной работы.**

Но backend не должен становиться chat-centric.

User experience:

```text
Chat first
```

Semantic architecture:

```text
Work first
```

---

# 6. Chat не равен Work

Один Chat может содержать:

```text
Message 1
→ Work A

Message 2
→ continuation Work A

Message 3
→ Work B

Message 4
→ simple question, no durable Work

Message 5
→ Work C

Background update
→ affects Work A

Artifact from Work B
→ used by Work C
```

Поэтому:

```text
Chat != Work
```

Один Work обычно имеет primary thread, но может ссылаться на артефакты из других Threads, принимать peer results, порождать child Work и переживать отсутствие активного открытого чата.

---

# 7. Нужно ли создавать новый чат на каждый новый запрос?

Нет.

Новый Chat нужен для нового **контекстного пространства**, а не для каждой отдельной execution.

### Один Chat

```text
"Посмотри банковский сектор."
"Добавь сравнение с прошлым кварталом."
"Теперь отдельно посмотри вклады."
"Сделай таблицу."
```

Это естественный единый контекст.

### Новый Chat

```text
"Начнём совершенно новую тему: мировой рынок какао."
```

Создание нового Chat означает:

```text
start new conversational context
```

а не:

```text
erase system memory
create new PROTOS identity
cancel old work
```

---

# 8. Memory scopes

С появлением настоящих чатов слово «память» становится неоднозначным. Нужно минимум пять разных scope.

## 8.1. Message history

Фактическая история interaction внутри Thread.

## 8.2. Thread memory

Производная долговременная память конкретного чата:

- summary;
- active concepts;
- unresolved questions;
- relevant artifacts;
- context compaction.

Это projection, а не полная истина.

## 8.3. Work state

Самая важная память для реального выполнения:

```text
objective
accepted facts
decisions
pending actions
artifacts
dependencies
```

Она не должна зависеть от conversational summarization.

## 8.4. Personal PROTOS memory

Межчатовая память:

- preferences;
- stable user context;
- learned procedures;
- persistent cognitive state.

Она принадлежит cognitive actor, а не конкретному Thread.

## 8.5. Node / Workspace knowledge

Общая среда:

- datasets;
- sources;
- registries;
- shared artifacts;
- project facts.

Это самостоятельный owner.

---

# 9. Новый Chat и Fork

`NewThread()` создаёт новый `thread_id`, пустую local message history и новую local context projection, но сохраняет доступ к capability catalog, workspace, user settings, actor identity, разрешённой long-term memory и node sources.

Поэтому новый чат — context reset, а не full cognitive reset.

Кроме `Новый чат` полезна будущая операция:

```text
Продолжить в новом чате / Fork from here
```

Она должна явно переносить только выбранные элементы:

- messages;
- Artifact refs;
- SourceSnapshot refs;
- Work refs.

Это безопаснее, чем скрыто наследовать весь старый контекст.

---

# 10. Артефакты нужно вернуть на первый план

Если Strategy Box становится cognitive analytical workspace, продукт работы чаще всего не сообщение.

Продукт:

```text
таблица
dataset
расчёт
график
report
source snapshot
файл
decision artifact
```

Сообщение — интерфейс взаимодействия.

Artifact — продукт работы.

A2A Protocol v1.0.1 независимо проводит очень похожее различие: Message — communication turn, Task — stateful unit of work, Artifact — task output; specification отдельно рекомендует не использовать Messages как основной carrier task outputs.

Для Strategy Box это сильный внешний архитектурный precedent.

## 10.1. Inline artifacts

В timeline:

```text
PROTOS:
"Готово."

[Artifact: corporate_lending_2026Q2.xlsx]
```

## 10.2. Thread Artifact Shelf

Каждый Chat должен иметь список всех связанных artifacts.

## 10.3. Working Set

Некоторые artifacts становятся текущим рабочим набором:

```text
Pinned / Active artifacts
```

которые автоматически доступны Context Builder.

## 10.4. Global Artifact Library

Нужен глобальный search/browse по node/workspace с фильтрами:

- Chat;
- Work;
- author;
- date;
- type;
- source;
- status.

## 10.5. Lifecycle

Chat deletion не должна автоматически означать artifact deletion. Thread и Artifact имеют разные retention/lifecycle semantics.


---

# 11. Главный внешний precedent: A2A разделяет context и task

A2A Protocol v1.0.1 вводит очень полезную структуру:

```text
contextId
    groups related Tasks and Messages

taskId
    identifies stateful unit of work
```

Спецификация прямо позволяет:

```text
same contextId
+ no taskId
→ create a new Task in existing conversational context
```

Это почти точное подтверждение предлагаемой модели Strategy Box:

```text
Thread ≈ context
Work ≈ task
Message ≈ message
Artifact ≈ artifact
```

Strategy Box не обязан копировать A2A data model. Но независимый стандарт пришёл к тому же важному разделению:

> conversational continuity и unit of work — разные сущности.

Это особенно полезно для будущей федерации.

---

# 12. Multiple commands: последовательные, параллельные и одновременные

Здесь current UI нужно существенно пересмотреть.

Сегодня scenario composer при активной execution переходит в busy state.

Для будущего PROTOS это неверная фундаментальная модель.

Пользователь должен иметь возможность:

```text
send command A
send command B
send command C
```

не дожидаясь завершения A.

Целевой UX:

```text
User:
"Обнови escrow."

[Work A: running]

User:
"А пока посмотри динамику средств физлиц."

[Work B: running]

User:
"И сделай ещё таблицу по текущим счетам."

[Work C: queued/running]
```

Центр остаётся интерактивным.

Следовательно:

> **global composer busy lock надо убрать из целевой архитектуры.**

Busy может существовать:

- на конкретной кнопке;
- на конкретной Run card;
- на resource class;

но не на весь Chat.

---

# 13. One Thread → many concurrent Work

```text
Thread A

Work 1 ───────── running
Work 2 ─── completed
Work 3 ───────────── running
Work 4 ─ queued
```

Переключение на другой Chat не меняет lifecycle этих Work.

Это особенно важно для Android/remote control: UI может закрыться, а Work продолжает жить.

---

# 14. One Work → many concurrent Runs

Пример:

```text
Work:
"оценить ситуацию в банковском секторе"

              ┌─ Run A: deposits
              ├─ Run B: corporate loans
              ├─ Run C: retail loans
              └─ Run D: profitability
                         ↓
                    fan-in
                         ↓
                   synthesis
```

Каждый Run может выполняться независимо.

---

# 15. Одинаковые, но независимые когнитивные системы

Идея пользователя здесь выглядит очень сильной, если аккуратно определить уровень identity.

Нужно различить:

```text
Cognitive Actor
Cognitive Profile
Cognitive Activation
Solver
```

## 15.1. Cognitive Actor

Persistent identity.

Для обычного пользователя:

```text
PROTOS Actor пользователя
```

Он может иметь:

- долгосрочную память;
- Authority;
- Work commitments;
- preferences;
- actor-level history.

## 15.2. Cognitive Profile

Описывает тип/конфигурацию когнитивной системы:

```text
analytical.default
research.deep
verification.strict
local.light
```

## 15.3. Cognitive Activation

Конкретное физическое/логическое исполнение:

```text
activation #a7
activation #b2
activation #c9
```

Они могут иметь один `profile_id`.

## 15.4. Solver

Фактический механизм:

- deterministic;
- small model;
- large model;
- remote model;
- search;
- human;
- compound solver.

---

# 16. Для параллельных команд не нужно автоматически создавать несколько persistent PROTOS actors

Для:

```text
Command A
Command B
Command C
```

лучший default:

```text
one persistent PROTOS Actor
    ↓
three independent Cognitive Activations
```

а не:

```text
three permanent agents with separate long-term identity
```

Это проще для:

- memory;
- Authority;
- audit;
- user model;
- cleanup;
- recovery.

---

# 17. Independence должна быть реальной на execution state

Параллельные activations:

```text
same Profile
same actor lineage
different activation_id
different transient context
different scratch state
different Run
```

Они не должны писать напрямую в общий mutable scratchpad.

Правильнее:

```text
Activation A
→ Candidate / Artifact

Activation B
→ Candidate / Artifact

Activation C
→ Candidate / Artifact

Work owner
→ reconcile
```

---

# 18. Orleans как полезный системный аналог

Microsoft Orleans поддерживает stateless worker grains, где runtime может создавать несколько activations одного и того же grain type.

Это хороший внешний аналог:

> одна и та же логическая capability может масштабироваться множеством независимых activations.

При этом Orleans отдельно показывает проблему координации state между такими activations.

Для PROTOS это подтверждает важное направление:

```text
scale execution
without shared mutable cognitive state
```

Источник: `https://learn.microsoft.com/en-us/dotnet/orleans/grains/stateless-worker-grains`.

---

# 19. Когда нужны отдельные child cognitive actors

Не каждая параллельная ветка должна быть просто Activation.

Отдельный bounded child actor полезен, если ему требуется:

- собственный durable sub-Work;
- собственная временная memory namespace;
- отдельная Authority delegation;
- независимый lifecycle;
- remote placement;
- peer-like interaction;
- explicit cancellation;
- отдельный audit owner.

Тогда:

```text
Parent PROTOS Actor
    ↓ delegated scope
Child Cognitive Actor A
Child Cognitive Actor B
```

Но это уже более тяжёлая topology.

---

# 20. Temporal Child Workflows как аналог

Temporal разрешает Parent Workflow создавать независимые Child Workflows.

Child:

- имеет собственный event history;
- может исполняться другим worker pool;
- не делит local state с parent;
- имеет отдельную cancellation/lifecycle policy.

Это полезный precedent для Strategy Box:

```text
parent Work
→ child Work
→ independent execution
```

При этом Child Workflow нужен при реальной execution/lifecycle boundary, а не только ради code organization.

Источник: `https://docs.temporal.io/child-workflows`.

---

# 21. Одинаковые replicas: для скорости и для качества — разные вещи

## 21.1. Scale-out for speed

```text
same scheme
same model/profile
different data partitions
```

Это нормально.

Например:

```text
Scheme = analyze_bank
replica 1 → Sber
replica 2 → VTB
replica 3 → RSHB
```

## 21.2. Scale-out for candidate search

```text
same question
same scheme
N independent candidates
```

Тоже возможно.

## 21.3. Independent verification

Здесь простой clone уже недостаточен.

Если все copies используют:

- одну модель;
- одинаковый prompt;
- одинаковые sources;
- одинаковый method;

ошибки будут correlated.

Для quality scaling полезно менять:

- method;
- source universe;
- solver;
- prompt framing;
- verifier;
- temporal sample.

PROTOS maintained Science отдельно подчёркивает: несколько agents сами по себе не означают независимое evidence.

---

# 22. Масштабирование схемы через размножение исполнителей

Это лучше описывать не как:

```text
clone scheme
```

а как:

```text
one SchemeSpec
→ N Scheme Invocations
→ N Cognitive Activations
```

Scheme identity остаётся одной.

Execution topology меняется.

---

# 23. Candidate execution graph

Один Work может иметь graph:

```text
               ┌─ Scheme A / activation 1
Input ─────────┼─ Scheme A / activation 2
               └─ Scheme A / activation 3
                          │
                          ▼
                    Reconcile Scheme
                          │
               ┌──────────┴──────────┐
               ▼                     ▼
            Verify B              Export C
```

Это очень PROTOS-friendly форма.

---

# 24. Новый runtime vocabulary

Полезно сразу различать:

```text
ThreadId
WorkId
RunId
SchemeId
OperationId
ActorId
ActivationId
SolverId
ArtifactId
MessageId
```

Эти ID отвечают на разные вопросы.

---

# 25. Candidate contracts

## 25.1. Thread

```yaml
Thread:
  schema_version: 1
  thread_id: uuid

  owner_principal_id: string
  visibility: personal | shared
  participant_ids: []

  title: string
  created_at: datetime
  updated_at: datetime
  archived_at: datetime?

  message_ids: []
  work_ids: []
  pinned_artifact_ids: []

  context_policy: object
  memory_projection_ref: string?

  node_id: string
  workspace_ref: string?
```

## 25.2. Message

```yaml
Message:
  message_id: uuid
  thread_id: uuid

  actor_id: string
  role: user | cognitive | system | peer

  created_at: datetime
  content: structured-content

  referenced_work_ids: []
  referenced_artifact_ids: []
  attachment_refs: []

  reply_to_message_id: uuid?
```

## 25.3. Work

```yaml
Work:
  work_id: uuid
  thread_id: uuid

  parent_work_id: uuid?

  principal_id: string
  owner_actor_id: string

  objective: object
  constraints: object

  state: string
  revision: integer

  created_at: datetime
  updated_at: datetime
  deadline: datetime?

  run_ids: []
  artifact_ids: []

  accepted_facts: []
  open_questions: []
  pending_decisions: []
  pending_effects: []

  completion: object?
```

## 25.4. Run

```yaml
Run:
  run_id: uuid
  work_id: uuid

  scheme_id: string?
  operation_id: string?

  actor_id: string
  activation_id: string?
  solver_id: string?

  input_snapshot_ref: string
  based_on_work_revision: integer

  state: queued | running | waiting | completed | failed | cancelled | unknown

  started_at: datetime?
  completed_at: datetime?

  result_ref: string?
  artifact_ids: []
  event_ids: []
  diagnostics_ref: string?
```

## 25.5. CognitiveActivation

```yaml
CognitiveActivation:
  activation_id: uuid

  parent_actor_id: string
  profile_id: string

  work_id: uuid
  run_id: uuid

  isolation_scope: isolated
  transient_context_ref: string?

  solver_binding: object
  resource_budget: object

  started_at: datetime
  ended_at: datetime?
```

Обычно эта сущность может быть runtime-only. Её не обязательно хранить как большой permanent object, но ID в trace полезен.

## 25.6. SchemeSpec

```yaml
SchemeSpec:
  scheme_id: string
  version: string

  title: string
  description: string

  semantic_inputs: object
  semantic_outputs: object

  composition:
    kind: sequential | graph | conditional | dynamic
    nodes: []

  applicability: object
  required_capabilities: []

  authority_requirements: object
  verification_policy: object

  resource_profile: object

  valid_for: object
  invalidation_triggers: []

  provenance: object
```

---

# 26. Как PROTOS может «убивать» cognition в machine scheme

Исходная интуиция пользователя здесь очень сильна.

PROTOS может проходить цикл:

```text
novel task
→ expensive cognition
→ repeated pattern
→ stable procedure
→ validation
→ compiled scheme
→ cheap reuse
```

После компиляции:

```text
PROTOS no longer needs to deeply reason
```

Он может:

```text
resolve applicability
→ invoke Scheme
```

Это хорошо совпадает с fresh PROTOS research о compiled fast paths и cognitive microexecution.

---

# 27. Scheme Library становится внутренним capability layer

Именно поэтому сценарии не обязаны занимать главное место UI.

Пользователь может никогда не знать точное имя:

```text
scheme.cbr.escrow.export.v4
```

Он пишет:

```text
"обнови escrow и выгрузи файл"
```

PROTOS выбирает capability.

Но library нельзя полностью скрывать. Power users и debugging требуют:

- посмотреть available capabilities;
- запустить вручную;
- увидеть parameters;
- увидеть version;
- inspect graph;
- compare schemes;
- disable;
- pin/favorite.

Значит нужен `Capability Library`, но это уже не основной рабочий режим.

---

# 28. Предлагаемая новая Information Architecture

## 28.1. Primary modes

Наиболее сильная целевая форма:

```text
Чаты
Данные / Workspace
Фоновые
Команда / Участники
```

Возможно позже отдельно:

```text
Артефакты
```

если global artifact library станет крупной.

## 28.2. Не primary modes

Убрать из permanent top-level navigation:

```text
Сценарии
Каскады
```

Вместо этого `Capabilities` доступны через:

- composer;
- command palette;
- `+`;
- slash-like command;
- отдельный secondary catalog.

---

# 29. Где физически должен быть список чатов

Исходная идея вывести новые чаты в постоянное боковое поле правильна по направлению: чаты должны стать persistent primary navigation.

Но по текущей композиции интерфейса я бы **не закреплял их именно справа**.

Current right inspector уже естественно подходит для:

- Artifacts;
- Work state;
- active Runs;
- Logs;
- Context.

А список Chat лучше помещается в существующий secondary left panel.

Рекомендуемая desktop-композиция:

```text
┌────────────┬──────────────────┬────────────────────────────┬─────────────────────┐
│ Mode rail  │ Thread list      │ Active Chat / Thread       │ Context inspector   │
│            │                  │                            │                     │
│ Chats      │ + Новый чат      │ Messages                   │ Artifacts           │
│ Data       │                  │ Work cards                 │ Active Work         │
│ Background │ Chat A           │ Run cards                  │ Runs                │
│ Team       │ Chat B           │ Artifact cards             │ Logs                │
│            │ Chat C           │ PROTOS responses           │ Context             │
│            │ ...              │                            │                     │
│            │                  │ Composer                   │                     │
└────────────┴──────────────────┴────────────────────────────┴─────────────────────┘
```

Почему Chat list лучше слева:

- это primary navigation;
- пользователи сканируют список сверху вниз;
- туда естественно ложится title/search/archive;
- это соответствует текущему существованию left mode panel;
- right inspector можно сохранить для contextual information;
- Artifacts не теряются.

Это UX recommendation, а не semantic requirement. Layout можно зеркалить.

---

# 30. Что должно быть справа

Right inspector становится ещё важнее.

Вместо сегодняшних:

```text
Case
Logs
Artifacts
Parameters
```

целевая модель:

```text
Artifacts
Work
Runs
Context
Logs
```

`Parameters` становятся деталью конкретного Run, а не постоянной top-level tab.

Artifacts логично поставить выше Logs.

---

# 31. Composer

Новый composer должен поддерживать:

```text
free text
attachments
artifact references
capability picker
context scope
send
```

При этом composer никогда не блокируется глобально из-за running Work.

Manual capability invocation остаётся:

```text
+ Использовать схему
```

или command palette / slash-like command.

Это power-user path.

---

# 32. Execution cards внутри timeline

Вместо технического потока всех events:

```text
[Work: Анализ вкладов]
  ├ Running 2/4
  ├ Run A completed
  ├ Run B running
  └ 3 artifacts
```

Карточку можно развернуть.

Это снижает шум.

Timeline должен уметь показывать параллельность:

```text
15:10 User: обнови escrow
15:10 Work A started

15:11 User: посмотри вклады
15:11 Work B started

15:12 Work B completed
15:14 Work A completed
```

История не обязана группироваться только по строгому completion order.


---

# 33. Один личный PROTOS, много activations

Наиболее чистая модель для одного пользователя:

```text
1 user
→ 1 persistent logical PROTOS Actor
→ many independent activations
→ many Works
→ many Threads
```

Это хорошо согласует:

- personal memory;
- Authority;
- identity;
- concurrency;
- audit.

Для нескольких пользователей:

```text
User A → PROTOS Actor A
User B → PROTOS Actor B
```

между ними — federation of Work, а не shared actor.

Shared Chat также не означает shared cognitive actor. Оба PROTOS могут участвовать в одном Thread, но память и Authority остаются раздельными, каждый Message имеет Actor, а Work owner explicit.

---

# 34. Local scaling vs federation

## Local scaling

```text
same principal
same persistent actor
many independent activations
```

Цель:

- speed;
- decomposition;
- candidate diversity.

## Federation

```text
different principals
different persistent actors
independent memory/Authority
```

Цель:

- collaboration;
- specialization;
- separate data;
- independent evidence;
- resource pooling.

Одна Scheme может одновременно использоваться:

```text
Actor A / activation 1
Actor A / activation 2
Actor B / activation 1
```

Scheme identity никак не определяет actor identity.

---

# 35. Work ownership при параллельности

Нужен один owner accepted Work State.

Например:

```text
Work Coordinator
```

Он принимает:

```text
candidate A
candidate B
candidate C
```

и делает:

```text
accept
reject
merge
challenge
request more
```

Shared mutable scratchpad — плохой default.

Плохая схема:

```text
Activation A ─┐
Activation B ─┼→ same mutable memory
Activation C ─┘
```

Риски:

- race conditions;
- self-contamination;
- non-reproducibility;
- context drift;
- feedback loops.

Лучше:

```text
Work revision 17
        ↓
 immutable context snapshot
   ┌────┼────┐
   ▼    ▼    ▼
   A    B    C
   │    │    │
   └─ candidates
        ↓
 reconciliation
        ↓
 Work revision 18
```

Это особенно сильная модель для аналитической работы.

---

# 36. Write conflicts и optimistic revision checking

Параллельность разрешена только при безопасной topology.

Нужно различать хотя бы концептуально:

```text
read-set
write-set
effect-set
```

Минимально Scheme/Operation должна знать:

- какие resources читает;
- какие artifacts создаёт;
- что может заменить;
- есть ли external effect.

Если Activation начал на:

```text
Work revision 17
```

а Work уже стал:

```text
revision 20
```

candidate перед admission проверяется:

```text
still applicable?
```

Результат:

```text
ACCEPT
REBASE
REVALIDATE
DISCARD
```

---

# 37. Parallelism as runtime policy

Scheduler может считать Work независимыми, если:

- нет write conflict;
- нет Authority conflict;
- хватает ресурсов;
- нет explicit dependency.

Тогда:

```text
Work A || Work B || Work C
```

Scheme сама может содержать `parallel_group`.

Более динамический случай:

```text
PROTOS decides:
"worth spawning 4 independent analytical branches"
```

Но результат всё равно выражается через ordinary Runs/Work graph.

Не каждый Run требует cognitive system. Например `export Excel` может исполняться deterministic executor.

Поэтому executor class должен допускать:

```text
deterministic
cognitive
remote
human
```

PROTOS управляет capability fabric, а не обязательно физически исполняет всё сама.

---

# 38. Не показывать каждую Activation как отдельного агента

Если scale-out виден буквально, пользователь быстро получит интерфейс:

```text
Agent 1
Agent 2
Agent 3
Agent 4
...
```

Это плохой default.

Обычный UI показывает:

```text
"Анализируется параллельно: 4 ветви"
```

Детали доступны по раскрытию.

Показывать отдельного Actor имеет смысл, если это:

- другой пользователь;
- peer PROTOS;
- explicit specialist;
- независимый verifier;
- human reviewer.

Ephemeral local activations обычно остаются runtime detail.

---

# 39. Cases: что с ними делать

С учётом новой модели я рекомендую:

> **Не делать `Case` фундаментальной сущностью следующей архитектуры.**

Текущий Case полезен как transitional object.

В clean redesign его смысл расходится на:

```text
Work
Run
```

Поля `scenario id`, `params`, `stage`, `step runs`, `outputs`, `status` естественно принадлежат Run.

Поля `objective`, `conversation linkage`, `waiting user`, `continuation`, `multiple runs` принадлежат Work.

Сегодня:

```text
Case → ScenarioChatMessage
```

Позже:

```text
ThreadProjection
    Messages
    WorkCards
    RunCards
    ArtifactCards
    Notices
```

Current scenario chat — хороший proto-Thread UI. Его не нужно выбрасывать. Нужно поменять ownership: thread events становятся первичнее scenario cases.

---

# 40. Сценарии перестают быть объектом главной навигации, но не теряют важность

Это ключевая продуктовая инверсия.

Сегодня:

```text
пользователь управляет схемами
```

Позже:

```text
PROTOS управляет схемами
пользователь управляет целями и контекстами
```

Cognitive Scheme Library становится аналогом internal capability ecosystem.

Она может содержать:

```text
source operations
analytical schemes
report schemes
validation schemes
communication schemes
monitoring schemes
extensions
```

Чтобы PROTOS мог выбирать Scheme, нужен machine-readable catalog:

```text
purpose
semantic tags
inputs
outputs
preconditions
effects
cost
latency
quality/evidence
applicability
known failure regions
version
```

Scheme selection не должен зависеть от naming внутри system prompt.

---

# 41. Scheme versioning, validity and learning

Run должен знать:

```text
scheme_id
scheme_version
```

Compiled Scheme должна иметь:

```text
validity envelope
invalidation triggers
```

Например:

```text
source schema changed
operation version changed
policy changed
```

→ deopt обратно к более общей cognition.

В будущем PROTOS learning может изменять:

- routing;
- scheme selection;
- scheme graph;
- compiled shortcuts;
- verification policy.

Но это отдельный admission lifecycle.

Новая Scheme не должна появляться как тихий побочный эффект одного Chat.

Если пользователь десять раз просит одно и то же:

```text
Thread memory
    remembers context

Learning
    notices repeated task

Scheme compilation
    creates reusable capability
```

Это три разных процесса.

---

# 42. Background cognition и Threads

Фоновая Work может быть связана с Thread или быть threadless system Work.

Например:

```text
watch CBR source
```

может жить независимо.

Когда появляется material result:

```text
notify existing Thread
или
create/update System Inbox Thread
```

Не надо создавать новый Chat для каждого фонового tick.

Background process создаёт user-visible Work/Chat entry только при materiality.

Полезная будущая projection:

```text
System / Background Inbox
```

куда попадают:

- source alerts;
- completed background Work;
- peer requests;
- failures.

Но это UI projection, не отдельная runtime universe.

---

# 43. Что делать с текущими top-level режимами

## `Сценарии`

Долгосрочно:

```text
→ Capability Library / picker
```

## `Каскады`

Долгосрочно:

```text
→ composite Scheme type
```

Отдельный primary mode лучше убрать.

## `Проводник`

Сохранить, но постепенно развивать в:

```text
Data / Workspace
```

с sources + files + datasets.

## `Фоновые`

Оставить как operational view, если monitoring/automation — существенная функция. Backend при этом использует тот же Work/Run system.

## `Участники`

Сохранить. В будущем здесь могут жить humans и peer cognitive actors.

## `Поручения`

Backend можно постепенно свести к:

```text
Work assigned_to Actor
```

а UI оставить как projection `My assigned Work`.

---

# 44. Home screen

При запуске Strategy Box логичнее показывать:

```text
Recent Chats
Running Work
Background alerts
Recent artifacts
```

вместо default scenario catalog.

Главный вопрос пользователя при открытии:

> Где я продолжу работу?

а не:

> Какую машинную функцию я сейчас запущу?

Это не «копирование ChatGPT». Chat UX здесь возникает из собственной domain logic: long-running context, text interaction, memory, multiple Works, artifacts и cognitive systems.

Strategy Box будет отличаться от обычного chatbot, потому что Thread содержит running Work, machine executions, data, artifacts, sources, background events и peer actors.

Это скорее:

```text
conversational analytical workspace
```

---

# 45. Critical architecture deltas

## 45.1. Remove single-current-scenario assumption

Current composer ориентирован на `selected scenario`.

Future composer ориентирован на `current Thread`.

PROTOS сам выбирает Scheme. Manual selection optional.

## 45.2. Remove single global busy state

Current UI blocks composer during execution.

Target:

```text
many Work
many Runs
one interactive Thread
```

Global busy state несовместим.

## 45.3. Split Case

```text
ScenarioRunCase
→ Work + Run
```

Это, вероятно, самый важный model refactor.

## 45.4. Promote Thread persistence

Не просто recent projection. Thread/message store становится first-class persistent substrate.

## 45.5. Promote artifact working set

Artifact должен иметь first-class relation:

```text
Thread
Work
Run
```

## 45.6. Unify Scheme catalog

Scenario/Cascade как top-level user taxonomy постепенно исчезают.

---

# 46. Potential target package layout

```text
application/
├─ threads/
│  ├─ contracts
│  ├─ service
│  └─ projections
│
├─ messages/
│  ├─ contracts
│  └─ service
│
├─ work/
│  ├─ contracts
│  ├─ lifecycle
│  ├─ admission
│  └─ graph
│
├─ runs/
│  ├─ contracts
│  ├─ scheduler
│  └─ execution
│
├─ capabilities/
│  ├─ operations
│  ├─ schemes
│  └─ registry
│
├─ cognition/
│  ├─ port
│  ├─ proposals
│  ├─ activations
│  └─ context
│
├─ artifacts/
├─ events/
├─ authority/
├─ background/
├─ collaboration/
└─ workspace/
```

Не надо материализовывать всё заранее. Это target responsibility map.

Presentation:

```text
presentation/common/
├─ threads
├─ timeline
├─ work_cards
├─ run_cards
├─ artifacts
├─ capability_picker
├─ participants
└─ inspector
```

Desktop и Android используют те же semantic models.

---

# 47. Persistence

Текущий JSON recent history не подходит для долгоживущей chat architecture.

Понадобятся:

- transactional writes;
- concurrency;
- search;
- thread indexing;
- message pagination;
- schema migrations;
- retention;
- atomic relationships между Work/Artifacts.

SQLite остаётся очень сильным first implementation для desktop node, но contract должен быть независимым.

Логические repositories:

```text
ThreadRepository
MessageRepository
WorkRepository
RunRepository
ArtifactRepository
EventRepository
```

Физически они могут жить в одной БД.

Message лучше делать immutable или versioned. Если пользователь редактирует сообщение, создаётся новая revision, чтобы не ломать audit.

---

# 48. Long Chat и context building

Длинный Chat нельзя целиком подавать в model.

Нужна обычная PROTOS distinction:

```text
stored history
≠ current context
```

Context Builder выбирает:

- recent messages;
- relevant old messages;
- Work state;
- artifacts;
- thread summary;
- user memory.

Chat summary не является authoritative. Критические facts должны ссылаться на Work state, source, artifact или decision.

Новый Chat полезен именно как context hygiene boundary: уменьшает contamination, упрощает retrieval и даёт понятный human scope.

---

# 49. Chats по узлу

Идея хранить память чатов по узлу логична.

Semantic key лучше делать:

```text
node_id
principal_id
thread_id
```

а не просто local path.

Это позволит позже:

- mobile;
- remote;
- node migration;
- AppDock-managed state.

Первая версия может показывать:

```text
Recent
Pinned
Archived
```

и поддерживать search.

Не стоит сразу строить сложные folder/project hierarchies.

---

# 50. Personal vs shared Thread

Первая версия:

```text
visibility = personal
```

Позже:

```text
shared
```

Но shared Thread не должен автоматически означать shared PROTOS memory.

Он означает shared interaction surface с отдельными Participants.

В shared Chat могут присутствовать:

```text
Human A
PROTOS A
Human B
PROTOS B
```

Underlying Work ownership и Authority остаются explicit.

---

# 51. A2A Mapping

Очень естественный future mapping:

```text
Strategy Box Thread
    ↔ A2A contextId

Strategy Box Work / delegated Work
    ↔ A2A Task

Strategy Box Message
    ↔ A2A Message

Strategy Box Artifact
    ↔ A2A Artifact
```

Но Strategy Box objects могут быть богаче.

Не стоит использовать A2A objects прямо внутри Strategy Box, потому что:

- protocol может меняться;
- local Work содержит больше semantics;
- Authority model richer;
- storage/lifecycle local;
- cross-platform UI не должен зависеть от protocol schema.

Нужен adapter.

---

# 52. Android и remote execution

Новая architecture отлично подходит Android:

- thread list;
- messages;
- Work status;
- artifacts;
- approvals;
- background notifications.

Heavy execution остаётся host-side.

Android user отправляет Message, Work может физически выполняться на desktop/remote node, Thread остаётся единым interaction context.

Если один user имеет несколько nodes:

```text
Thread owner
≠ execution node
```

Один Chat в будущем может включать:

```text
Work 1 → desktop
Work 2 → remote host
Work 3 → peer
```

UI остаётся единым.

---

# 53. Strongest anti-patterns

## Scenario-first forever

Пользователь вынужден понимать внутреннюю machine taxonomy.

## Chat = source of truth

Material state живёт только в messages.

## One global agent loop

Все команды последовательно идут через одну active model session.

## One busy flag

Любой Run блокирует интерфейс.

## Shared mutable AI memory

Все parallel agents пишут в общий scratch state.

## One Case = all semantics

Case разрастается до thread/work/run/artifact container.

## Clone agent = independent evidence

Идентичные copies считаются независимыми экспертами.

## Every event creates chat

Фоновые процессы захламляют UI.

## Schemes hidden completely

Невозможно ручное управление/debug.

---

# 54. Что должно стать first-class

P0 architecture objects:

```text
Thread
Message
Work
Run
Artifact
Capability/Scheme Registry
Actor
```

Implementation details, которые могут пока оставаться лёгкими:

```text
CognitiveActivation
replica group
solver call
model session
```

пока observability не потребует более глубокой persistence.

---

# 55. Recommended migration sequence

## Phase 1 — split user continuity from execution

1. Introduce `Thread`.
2. Introduce `Message`.
3. Make central scenario chat become Thread timeline.
4. Introduce `Work`.
5. Introduce `Run`.
6. Map current Case into transitional Work + Run.

## Phase 2 — remove scenario-first UI

1. Add Chats primary mode.
2. Move scenarios to Capability Picker.
3. Collapse Cascades into composite capabilities.
4. Change composer from selected-scenario composer to free-text composer.
5. Keep manual capability invocation.

## Phase 3 — promote artifacts

1. Artifact shelf in Chat.
2. Pin/active working set.
3. Global artifact search.
4. Explicit attach artifact to message.
5. Artifact lineage.

## Phase 4 — concurrency

1. Remove global busy lock.
2. Multi-job manager.
3. Run dependency graph.
4. Cancellation per Run/Work.
5. Work revision fences.
6. Concurrent Chat execution.

## Phase 5 — PROTOS

1. One persistent user actor.
2. CognitivePort.
3. Thread/Work context builder.
4. Scheme resolver.
5. Multiple independent activations.
6. Dynamic execution graph.
7. Fan-in.

## Phase 6 — background

1. Trigger-created Work.
2. Background Thread projection.
3. Materiality filters.
4. Quiet notifications.
5. Long-running Work recovery.

## Phase 7 — federation

1. Distinct per-user actors.
2. Shared Threads.
3. Delegated Work.
4. A2A adapter.
5. Artifacts/evidence exchange.
6. Peer cognitive systems.

---

# 56. Что я бы изменил в текущем UI первым

Если redesign начинать до PROTOS implementation:

### 1. Add `Чаты` as first mode

Это становится default.

### 2. Existing scenario chat becomes active Thread timeline

Минимальный визуальный разрыв.

### 3. Add persistent Thread list

Использовать existing left panel.

### 4. Add `+ Новый чат`

Создаёт новый Thread.

### 5. Keep current Scenario launcher temporarily

Но постепенно переносить его в composer/palette.

### 6. Remove separate `Каскады` mode eventually

Composite scheme category.

### 7. Keep right inspector

Изменить tabs в сторону:

```text
Artifacts
Work
Runs
Logs
```

### 8. Stop global composer blocking

Allow many concurrent jobs.

Эти изменения уже готовят продукт для PROTOS без реализации PROTOS.

---

# 57. Не является ли это overfit на будущий PROTOS?

Скорее нет.

Даже без PROTOS design улучшает обычный Strategy Box:

- multiple concurrent tasks;
- better history;
- persistent work contexts;
- artifact organization;
- Android;
- background jobs;
- multi-user collaboration.

Поэтому фундамент оправдан независимо.

---

# 58. Финальная архитектурная формула

Самая сильная формула исследования:

> **Thread — основной human navigation object. Work — основной semantic object. Scheme — reusable execution capability. Run — конкретная execution. Activation — независимый cognitive executor. Artifact — durable output.**

Именно это разделение снимает большую часть текущей путаницы.

---

# 59. Final target runtime

```text
USER
 │
 ▼
THREAD / CHAT
 │
 ├─ Message
 │
 ├─ Work A
 │   │
 │   ├─ PROTOS resolves execution
 │   │
 │   ├─ Run A1 ─ Scheme X ─ Activation 1
 │   ├─ Run A2 ─ Scheme X ─ Activation 2
 │   ├─ Run A3 ─ Scheme Y ─ deterministic
 │   │
 │   ├─ reconciliation
 │   └─ Artifacts
 │
 ├─ Message
 │
 └─ Work B
      └─ ...
```

---

# 60. Final target multi-user runtime

```text
User A
  │
PROTOS Actor A
  │
Thread / Work A
  │
  ├─ local activations A1/A2/A3
  │
  └──────── federation ────────┐
                               │
                           PROTOS Actor B
                               │
                           User B
                               │
                           independent Work
                               │
                           Artifacts/Evidence
                               │
  ◄──────── reconciliation ────┘
```

---

# 61. Final verdict

Исходная тревога относительно того, что Strategy Box поставил scenarios/cascades слишком высоко в UI, **обоснована**.

Это не ошибка ранней версии: когда cognitive layer отсутствовал, machine procedures были естественным главным объектом пользователя.

Но при движении к PROTOS продукт должен поменять центр тяжести.

### Было

```text
Scenario
→ launch
→ Case
→ Artifact
```

### Должно стать

```text
Chat / Thread
→ intent
→ Work
→ one or many Schemes
→ one or many independent executions
→ Artifacts
→ continuing conversation
```

Schemes:

- становятся менее заметны пользователю;
- становятся гораздо важнее runtime;
- могут быть полностью deterministic;
- могут быть «скомпилированным мышлением»;
- могут исполняться одним или множеством independent cognitive activations;
- могут комбинироваться внутри одного Work;
- не определяют пользовательский контекст.

Artifacts, напротив, должны подняться выше. Они являются материальным продуктом Work и естественным мостом:

```text
Run
→ Work
→ Thread
→ other Work
→ peer actor
```

Самая важная архитектурная корректировка:

> **Нельзя превращать нынешний `ScenarioRunCase` в универсальный контейнер будущего. Лучше выделить `Thread`, `Work` и `Run` как разные уровни.**

И самая важная cognitive корректировка:

> **Один пользовательский PROTOS логично считать одним persistent Actor, а параллелизм реализовывать множеством независимых Cognitive Activations/child Work, использующих одни и те же SchemeSpecs. Отдельные persistent PROTOS actors возникают прежде всего на границах пользователей/principals или действительно независимого durable actor lifecycle.**

Это даёт Strategy Box фундамент, который одинаково естественно поддерживает:

- сегодняшние deterministic scenarios;
- будущий текстовый PROTOS;
- много параллельных запросов;
- долгие разговоры;
- память;
- артефакты;
- background cognition;
- Android;
- remote execution;
- много пользователей;
- A2A;
- масштабирование одной cognitive scheme множеством independent executors.

---

# Appendix A. Key design decisions

| Вопрос | Рекомендация |
|---|---|
| Главный пользовательский объект | Thread / Chat |
| Главный semantic object | Work |
| Одно конкретное выполнение | Run |
| Повторно используемая machine procedure | Scheme |
| Atomic capability | Operation |
| Persistent PROTOS identity | Actor |
| Parallel local cognition | independent Activations |
| Durable output | Artifact |
| Раздел «Каскады» | убрать как отдельный top-level concept |
| Раздел «Сценарии» | перенести в Capability Library / picker |
| Правый inspector | сохранить, усилить Artifacts/Work |
| Список Chats | persistent side panel; предпочтительно existing left secondary panel |
| Global busy composer | убрать |
| Один запрос = новый Chat | нет |
| Один Chat = один Work | нет |
| Один Work = одна Scheme | нет |
| Одна Scheme = один agent | нет |
| Same Scheme × N copies | N Runs / Activations |
| Shared mutable AI memory | default запрещать |
| Multi-user | federation of Actors |
| A2A | adapter, не internal domain model |

---

# Appendix B. External precedents

## A2A Protocol v1.0.1

Official specification:

`https://a2a-protocol.org/v1.0.1/specification/`

Особенно важные элементы:

- `contextId` логически группирует related Tasks и Messages;
- `taskId` определяет отдельную stateful unit of work;
- один context может содержать несколько Tasks;
- Task содержит lifecycle, history и Artifacts;
- Messages предназначены для communication;
- task outputs рекомендуется представлять Artifacts.

Это сильный внешний precedent для:

```text
Thread
≠ Work
≠ Message
≠ Artifact
```

## Microsoft Orleans — Stateless Worker Grains

`https://learn.microsoft.com/en-us/dotnet/orleans/grains/stateless-worker-grains`

Полезный precedent:

- runtime может создавать несколько activations одного logical worker type;
- scale-out не требует одного shared mutable state;
- state между activations координировать трудно.

Это поддерживает Strategy Box модель:

```text
same cognitive profile
→ many isolated activations
```

## Temporal — Child Workflows

`https://docs.temporal.io/child-workflows`

Полезный precedent:

- parent Work может spawn separate child Workflows;
- child имеет самостоятельный lifecycle/history;
- может обрабатываться отдельным worker set;
- child boundary полезна для реальной lifecycle/partition need, а не просто code organization.

Это хорошо соответствует:

```text
Work
→ child Work
→ independent cognitive execution
```

---

# Appendix C. Internal source base

## Strategy Box

`stratbox-windows_current_state_full_research_2026-10-06.md`

Особенно важные current-state facts:

- mode rail включает `Сценарии` и `Каскады`;
- центральный `Scenario chat` уже является semantic projection;
- `ScenarioRunCase` привязан к scenario;
- artifacts уже first-class records;
- composer сегодня блокируется через global busy state;
- background/presence/assignments существуют как ранние scaffolds;
- application/runtime постепенно отделяются от Qt;
- AI actor semantics уже подготовлены, но executor отсутствует.

`stratbox_base_study_current_state_2026-10-06.md`

Ключевые направления:

- canonical operations;
- typed Request/Result;
- provenance;
- diagnostics;
- operation discovery.

## PROTOS maintained baseline

`ForestTiger-GH/PROTOS/knowledge-product/`

Ключевые принципы, использованные здесь:

- Work не равен inference context;
- solver-independence;
- durable state;
- multi-agent execution — topology, not ontology;
- shared state требует explicit owner;
- identity actor ≠ solver/process/principal;
- capability ≠ Authority;
- artifact/evidence lifecycle;
- physical topology может масштабироваться при сохранении semantics.

## PROTOS active Epoch 002 research

Особенно релевантны:

- `PROTOS_Embedded_Cognitive_Systems_Host_Integration_2026-09-16.md`;
- `PROTOS_Persistent_Proactive_Cognitive_System_Operational_Physiology_2026-09-15.md`;
- `PROTOS_Cognitive_Operating_Environment_Architecture_Infrastructure_and_Computational_Economy_2026-09-17.md`;
- `PROTOS_Adaptive_Cognitive_Execution_Physiology_2026-09-23.md`;
- `PROTOS_Cognitive_World_Architecture_Ecology_2026-09-15.md`;
- `PROTOS_Semantic_Logical_Mandates_Orthogonal_Cognition_2026-09-16.md`;
- `PROTOS_From_Schemas_to_Semantic_Construct_Fabric_2026-09-16.md`;
- `PROTOS_Cognitive_Microexecution_Relation_Algebra_and_Compiled_Fast_Paths_2026-09-16.md`.

Как и в предыдущем исследовании, свежие Epoch 002 carriers рассматриваются как Research inputs/hypotheses, а не автоматически admitted current PROTOS Product truth.

---

# Appendix D. One-sentence design rule

> **Пользователь работает в Threads, смысл живёт в Work, исполнение живёт в Runs, повторно используемая машинная способность живёт в Schemes, а параллельный PROTOS масштабируется independent Activations — при этом Artifacts остаются отдельными first-class результатами и никогда не растворяются в истории сообщений.**
