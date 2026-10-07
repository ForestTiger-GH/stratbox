# Strategy Box × PROTOS: требования к фундаменту когнитивно-готовой архитектуры

**Дата исследования:** 2026-10-07  
**Контур:** Strategy Box, вторая ветка исследований  
**Предмет:** влияние текущей архитектуры и свежих исследований PROTOS на фундамент `stratbox` и универсального application/surface-слоя Strategy Box  
**Статус:** Research Result; архитектурное исследование, а не готовая спецификация реализации

---

## 0. Executive conclusion

Главный вывод исследования можно сформулировать так:

> **Strategy Box не требуется превращать в PROTOS и не требуется строить вокруг LLM. Нужно сделать Strategy Box хорошим host для когнитивной системы: с устойчивыми Work / Operation / State / Authority / Execution contracts, поверх которых PROTOS сможет сначала работать как небольшой текстовый когнитивный адаптер, затем как фоновая система, а позже — как отдельный федеративный когнитивный участник.**

Это существенно меняет постановку задачи.

Неправильный путь:

```text
чат
→ LLM / агент
→ прямые Python-вызовы / shell / файлы
→ результат
```

Он быстро даст демонстрацию, но создаст параллельную архитектуру рядом с уже существующими operations, scenarios, cases, artifacts и AppDock runtime. При появлении фоновых процессов, Android, remote execution и нескольких PROTOS придётся заново разносить состояние, полномочия, задания, транспорт и восстановление.

Целевой путь:

```text
вход пользователя / событие / таймер / изменение источника / peer request
        ↓
semantic ingress
        ↓
Work Candidate
        ↓
Work admission
        ↓
durable Work / Case
        ↓
Scenario / Operation contract
        ↓
Execution Backend
        ↓
stratbox canonical operation / other admitted capability
        ↓
structured Result + Events + Artifacts + Evidence
        ↓
Work transition
        ↓
presentation / notification / peer response
```

PROTOS входит в этот контур как **cognitive participant**:

```text
Host state / Work / capability catalog
        ↓ bounded projection
PROTOS
        ↓
candidate intent / plan / next operation / verification request / proposal
        ↓
Strategy Box validation + Authority + execution
```

В начальной версии PROTOS может физически быть всего одним model call, который получает пользовательский текст и выбирает готовый сценарий с параметрами. В более зрелой версии он сможет выполнять несколько когнитивных операций, переоценивать результат, инициировать новые Work, работать фоново и использовать разные solvers. В федеративной версии отдельные PROTOS разных пользователей смогут делегировать друг другу ограниченную работу через сетевой transport, включая A2A. При этом фундаментальные объекты Strategy Box останутся прежними.

### Что нужно заложить в фундамент сейчас

1. **Canonical Operations** в `stratbox`: stable ID, typed Request/Result, side-effect semantics, diagnostics, provenance и artifact contract.
2. **Durable Work/Case** в application layer: Work живёт дольше GUI-сеанса, потока, model call и процесса.
3. **Ingress semantics**: текст пользователя является carrier, а не готовой командой для модели.
4. **ExecutionBackend abstraction**: local сегодня; AppDock remote/node и peer execution позже.
5. **Job Manager**: foreground, background, remote и cognitive execution используют одну систему заданий.
6. **Trigger/Event model**: ручной запуск, расписание, source change, timer, AppDock event, peer delegation — разные источники одного Work lifecycle.
7. **Actor / Principal / Solver / Runtime identities** как разные сущности.
8. **Authority / Effect boundary**: возможность выполнить operation не означает право её выполнить.
9. **Revision/freshness fences**: долгий когнитивный результат привязан к исходному состоянию и может устареть до применения.
10. **Capability discovery**: человек и PROTOS получают машинно-читаемый каталог разрешённых operations/scenarios.
11. **Context projection**: cognitive system видит минимально достаточное представление host state, а не весь процесс и файловую систему.
12. **Artifact/evidence/provenance lineage**.
13. **Structured failure/uncertainty model**, включая `UNSUPPORTED`, `ABSTAIN`, `STALE_RESULT`, `POLICY_DENIED`, `RESOURCE_EXHAUSTED`, `UNKNOWN`.
14. **Observability correlation** по Work → Job → Step → Operation → Solver → Artifact.
15. **Resource controls**: минимум priority, deadline, cancellation, queue/concurrency limits и foreground reserve.
16. **CognitivePort**, а не зависимость application logic от конкретной LLM/PROTOS реализации.
17. **Frontend-neutral application/runtime** для будущего `stratbox-android`.
18. **Collaboration/Federation Port** с отдельным A2A adapter позже.
19. **Никакой общей mutable memory между PROTOS разных пользователей** как базовый принцип.
20. **Cross-scale conformance tests**: одна семантика Work/Scenario должна сохраняться при local, remote и federated execution.

Большая часть этих требований уже естественно продолжает текущую архитектуру Strategy Box. Поэтому PROTOS не требует переписать проект. Он усиливает направления, которые уже появились независимо: canonical operations, typed results, cases/events/artifacts, execution backend, background job manager, AppDock boundary и platform-neutral application layer.

---

# 1. Рамка и иерархия источников

## 1.1. Текущий PROTOS и свежие исследования — разные уровни знания

У PROTOS сейчас существуют два разных класса материалов.

### Maintained Product/Knowledge

Текущая рабочая маршрутизация PROTOS указывает на корневой `knowledge-product/` как на maintained Product/Knowledge baseline, сформированный по итогам завершённого первого Development Epoch.

Для настоящего исследования особенно важны:

```text
knowledge-product/
├── science/
│   ├── 01-COGNITIVE-SEMANTICS-AND-GOALS.md
│   ├── 02-COMPUTE-SOLVERS-AND-SCALING.md
│   ├── 03-STATE-MEMORY-WORLD-MODELS-AND-LEARNING.md
│   ├── 04-TOOLS-AUTHORITY-CONTROL-AND-SYSTEM-COMPOSITION.md
│   └── 05-ASSURANCE-IDENTITY-PRIVACY-INTERPRETABILITY-AND-PROVENANCE.md
├── target-what/
│   └── TARGET-WHAT.md
├── target-how/
│   ├── TARGET-HOW.md
│   ├── DESIGN-FREEDOM.md
│   └── DATA-PRIVACY-LIFECYCLE.md
└── product-architecture/
    └── PRODUCT-ARCHITECTURE.md
```

Именно этот слой используется как основной источник уже сформированной архитектурной семантики.

### Epoch 002 first-ideas research

В активном Epoch 002 находится большой набор свежих исследований сентября 2026 года. Текущие `_mw/AGENTS.md`, `WORK_ARCHITECTURE.md`, `EPOCH.md` и `WORK_STATE.md` прямо фиксируют, что эти файлы являются **Research/input carriers**, а наличие файла само по себе не делает его выводы новой Current Scientific Knowledge или Product commitment.

Поэтому в этом документе:

- maintained `knowledge-product/` используется как основной PROTOS baseline;
- свежие Epoch 002 studies используются как сильные архитектурные гипотезы и направления;
- при совпадении свежего исследования с maintained semantics оно считается дополнительным подтверждением;
- новые идеи из Epoch 002 не объявляются обязательными требованиями PROTOS только из-за их убедительности.

Для Strategy Box это особенно важно: фундамент должен учитывать вероятное развитие PROTOS, но не зависеть от ещё не стабилизировавшейся внутренней топологии PROTOS.

## 1.2. Исследованные свежие материалы PROTOS

В active Epoch 002 изучены материалы, непосредственно влияющие на host integration, persistent cognition, multi-user/federation, scale invariance и cognitive execution, включая:

- `PROTOS_Cognitive_World_Architecture_Ecology_2026-09-15.md`;
- `PROTOS_Persistent_Proactive_Cognitive_System_Operational_Physiology_2026-09-15.md`;
- `PROTOS_Microcognition_Algorithmic_Fast_Paths_Scale_Invariant_Cognitive_Execution_2026-09-15.md`;
- `PROTOS_Adaptive_Learning_Architecture_Multi_Timescale_Plasticity_2026-09-15.md`;
- `PROTOS_Challenge_Ecology_Governed_Self_Improvement_Development_Input_2026-09-15.md`;
- `PROTOS_Semantic_Logical_Mandates_Orthogonal_Cognition_2026-09-16.md`;
- `PROTOS_Embedded_Cognitive_Systems_Host_Integration_2026-09-16.md`;
- `PROTOS_From_Schemas_to_Semantic_Construct_Fabric_2026-09-16.md`;
- `PROTOS_Composable_Logical_Cognitive_Schemas_Architecture_2026-09-16.md`;
- `PROTOS_Cognitive_Microexecution_Relation_Algebra_and_Compiled_Fast_Paths_2026-09-16.md`;
- `PROTOS_Cognitive_Operating_Environment_Architecture_Infrastructure_and_Computational_Economy_2026-09-17.md`;
- `PROTOS_Adaptive_Cognitive_Execution_Physiology_2026-09-23.md`;
- `PROTOS_Learning_Artifact_Interchange_Tokenization_Model_and_Solver_Docking_2026-09-23.md`.

Наиболее важным для Strategy Box оказался материал об **Embedded Cognitive Systems / Host Integration**. Он практически напрямую отвечает на вопрос настоящего исследования: как cognitive system должна жить внутри обычного software, сохраняя owner-ship точного состояния и эффектов у host.

## 1.3. Исходная архитектура Strategy Box

Сопоставление выполнено с текущими исследованиями:

- `stratbox_base_study_current_state_2026-10-06.md`;
- `stratbox-windows_current_state_full_research_2026-10-06.md`;
- базовым описанием AppDock.

Главные уже существующие предпосылки Strategy Box:

```text
stratbox
    domain/business core
    sources / canonical data / calculations / exports
    neutral infrastructure contracts

stratbox-windows
    application/runtime/surface
    operations
    scenarios
    cases
    events
    artifacts
    logs
    workspace
    AppDock integration
    desktop UI

AppDock
    product lifecycle
    node/session
    environment
    installation
    host/remote substrate
    health/recovery
    permissions and controlled actions
```

Это исходное разделение оказалось очень совместимым с PROTOS.

---

# 2. Что PROTOS на самом деле требует от Strategy Box

## 2.1. PROTOS не требует AI-first application

Самое важное уточнение из текущего PROTOS:

```text
semantic responsibility
≠ physical component
≠ process
≠ repository
≠ model call
```

PROTOS не определяется одной моделью, одним agent framework или фиксированным набором Planner/Researcher/Critic/Executor.

Следовательно, Strategy Box не должен проектироваться как:

```text
GUI
→ PROTOS
→ всё остальное
```

и тем более как:

```text
GUI
→ LLM
→ инструменты
```

Правильнее:

```text
Strategy Box host semantics
        │
        ├── exact domain state
        ├── operations
        ├── scenarios
        ├── Work/jobs
        ├── artifacts
        ├── Authority
        └── execution
                ↑
                │ Cognitive Port
                │
             PROTOS
```

PROTOS становится одним из участников execution/control, а не владельцем всего приложения.

## 2.2. Совпадение архитектурных направлений уже очень велико

Независимое исследование `stratbox` уже пришло к необходимости:

- canonical operations;
- typed Request/Result;
- structured failures;
- artifacts;
- provenance;
- operation registry;
- source snapshot/freshness;
- diagnostics/events.

Исследование `stratbox-windows` уже пришло к необходимости:

- application orchestration;
- Background Job Manager;
- cancellation/retry/resume;
- `ExecutionBackend`;
- real presence provider;
- remote assignments;
- artifact lineage;
- permissioned AI scenario API;
- separation Qt bridge from application/runtime.

PROTOS добавляет к этому не новую платформу, а объясняет, **почему эти контракты должны быть особенно строгими**.

Canonical operations оказываются не просто удобным API. Они становятся stable semantic capabilities.

Case оказывается не просто карточкой сценария. Он становится естественным кандидатом на durable Work projection.

ExecutionBackend оказывается не только remote abstraction. Он становится способом менять физическую топологию при сохранении Work semantics.

Artifact lineage оказывается основой evidence и межакторного обмена.

Background Job Manager становится физиологией persistent cognition.

---

# 3. Главная архитектурная граница: Host–Cognition Contract

## 3.1. Основная формула

Самая сильная идея свежего PROTOS Host Integration research:

```text
HOST DOMAIN
  owns exact state and invariants
        │
        ▼
COGNITIVE PORT
  states a stable semantic need
        │
        ▼
CONTEXT / OBSERVATION PROJECTION
        │
        ▼
COGNITIVE EXECUTION
  local / remote
  cheap / expensive
  dormant / active
        │
        ▼
CANDIDATE RESULT
        │
        ▼
VALIDATION / POLICY / EFFECT BOUNDARY
        │
        ▼
HOST STATE TRANSITION
```

Для Strategy Box это переводится почти буквально:

```text
stratbox + Strategy Box application
  authoritative operation/state semantics
        ↓
CognitivePort
        ↓
PROTOS
        ↓
WorkProposal / ScenarioPlan / NextOperation / Challenge
        ↓
validation + Authority
        ↓
Job/Scenario execution
        ↓
canonical operation
        ↓
structured result
```

## 3.2. Что остаётся у Strategy Box

Даже при очень сильном PROTOS host должен оставаться владельцем:

- реестра доступных аналитических операций;
- схем параметров;
- фактического состояния Work;
- статуса Job;
- workspace boundaries;
- source/artifact identities;
- exact operation preconditions;
- destructive/effect classifications;
- authorization decisions;
- факта успешного завершения операции;
- receipt/reconciliation внешнего эффекта;
- persisted user-visible history;
- application health;
- AppDock runtime relationship.

PROTOS не должен становиться скрытым authoritative owner этих сущностей.

## 3.3. Что может принадлежать PROTOS

PROTOS может владеть или выполнять:

- интерпретацию свободного текста;
- выбор подходящего scenario;
- построение candidate plan;
- выбор следующей cognitive operation;
- оценку необходимости дополнительных данных;
- формирование clarification;
- подбор solver;
- сравнительный анализ вариантов;
- challenge/verification;
- summarization/explanation;
- решение об эскалации;
- candidate delegation другому cognitive actor;
- background analysis при соответствующем grant.

Разница принципиальна:

```text
PROTOS может решить:
"нужно выполнить operation X"

Strategy Box решает:
"operation X существует, параметры валидны, выполнение разрешено,
baseline актуален, backend доступен, job создан и результат реально получен"
```

---

# 4. Первая версия: PROTOS в чате сценариев

## 4.1. Целевой пользовательский опыт

Пользователь пишет:

```text
"Собери последние данные по счетам эскроу и выгрузи Excel"
```

Внешне это выглядит как обычный чат.

Внутренне нужно избегать:

```text
text
→ LLM
→ arbitrary function call
```

Целевой путь:

```text
UserMessage
    ↓
CognitiveIngress
    ↓
CognitivePort.resolve_intent(...)
    ↓
WorkProposal
    scenario_id = "scenario.atomic.escrow.history.export"
    params = {...}
    assumptions = [...]
    required_effect_class = ...
    ↓
ScenarioRegistry validation
    ↓
Authority / parameter / precondition checks
    ↓
Work + Job
    ↓
normal scenario runner
    ↓
OperationResult + Artifacts
    ↓
PROTOS optional result interpretation
    ↓
Scenario chat projection
```

Чат здесь является интерфейсом к Work engine, а не самим Work engine.

## 4.2. Text message нельзя считать task object

Свежий PROTOS отдельно подчёркивает: natural-language input — carrier, а не автоматически task semantics.

Одна фраза может быть:

- вопросом;
- командой;
- ограничением;
- новым Work;
- продолжением старого Work;
- исправлением;
- загрузкой источника;
- решением;
- отменой;
- observation;
- Authority grant.

Поэтому application layer полезно иметь нейтральный ingress object:

```text
IngressEvent
    id
    kind
    actor_id
    principal_id
    occurred_at
    channel
    payload_ref
    related_work_id?
    correlation_id?
```

И поверх него:

```text
ResolvedIntent
    semantic_kind
    target_work_id?
    requested_outcome?
    constraints
    referenced_artifacts
    proposed_scenario?
    uncertainty
```

Не нужно сразу строить гигантскую ontology. Достаточно отделить carrier от принятой semantics.

## 4.3. Direct deterministic path должен сохраниться

PROTOS не должен становиться обязательным посредником.

Пользователь по-прежнему может нажать готовый сценарий:

```text
UI selection
→ ScenarioRequest
→ Work/Job
→ execution
```

Текстовый путь:

```text
natural language
→ PROTOS
→ тот же ScenarioRequest
→ тот же Work/Job
→ тот же execution
```

Это даёт:

- работу приложения без AI;
- детерминированный regression baseline;
- возможность слабого устройства;
- простое тестирование;
- безопасный degraded mode;
- сохранение UX при смене cognitive backend.

---

# 5. `stratbox`: каким должен стать core для PROTOS-ready host

## 5.1. Cognitive system должна видеть операции, а не Python internals

Текущий вектор на canonical operations становится фундаментальным.

Operation должна быть предметным use case, а не произвольной функцией.

Минимальный descriptor:

```text
OperationDescriptor
    operation_id
    version
    domain
    title
    description

    request_schema
    result_schema

    side_effect_class
    destructive
    idempotency_semantics

    network_required
    storage_required

    cancellable
    resumable
    retry_semantics

    supports_partial
    artifact_kinds

    authority_class
    required_capabilities

    provenance_level
    diagnostics_level
```

Часть полей может физически жить в application registry, если относится к product/surface semantics. Важно наличие единой машинно-читаемой contract chain.

## 5.2. Typed Request/Result становится обязательной нормой

Для cognitive execution особенно плохо, когда одна operation возвращает DataFrame, другая dict, третья пишет файл и `None`, четвёртая кидает исключение.

Целевая форма:

```text
Request
→ Operation
→ Result
```

Result может содержать:

```text
status
value / canonical_data
warnings
failures
artifacts
diagnostics
metrics
provenance
```

Домен может иметь богатый собственный Result. Общий envelope нужен для сквозной оркестрации.

## 5.3. Failure semantics должны перестать быть исключением UI

Минимальный общий словарь состояний полезно проектировать шире сегодняшнего `success/failed`:

```text
UNAVAILABLE
TIMEOUT
UNSUPPORTED
ABSTAIN
INVALID_OUTPUT
STALE_RESULT
POLICY_DENIED
RESOURCE_EXHAUSTED
VERIFICATION_FAILED
INTERNAL_FAILURE
```

Для Strategy Box также полезны:

```text
NOT_FOUND
SOURCE_UNAVAILABLE
AUTHENTICATION_REQUIRED
PARTIAL
CONFLICT
CANCELLED
```

Главный принцип:

```text
нет результата
≠ ошибка backend
≠ операция неподдерживаема
≠ пользователь отменил
≠ результат устарел
≠ не хватает Authority
≠ система сознательно abstain
```

## 5.4. `UNKNOWN` нужен как first-class state

```text
неизвестно
≠ false
≠ failed
≠ success
```

Это важно для сетевых эффектов, stale source, remote jobs, peer delegation, interrupted execution и reconciliation после crash.

---

# 6. Work: главный объект application foundation

## 6.1. Case уже близок к нужной сущности

Текущий `ScenarioRunCase` уже содержит identity, scenario, params, status, author, timestamps, current stage, step runs, outputs, message и unread.

Это отличный старт.

Для PROTOS-ready architecture понятие нужно семантически расширить от «одного запуска сценария» к **durable Work**. UI при этом вполне может продолжать использовать термин «кейс».

## 6.2. Candidate model

```text
Work
    work_id
    work_type

    principal_id
    owner_actor_id
    created_by_actor_id

    origin
    parent_work_id?
    correlation_id?

    objective
    constraints
    accepted_parameters

    status
    revision

    created_at
    updated_at
    deadline?
    expires_at?

    current_stage
    next_eligible_actions

    open_questions
    assumptions
    uncertainty

    source_refs
    artifact_refs
    evidence_refs

    pending_approvals
    pending_effects

    execution_refs
    child_work_refs

    completion_summary
    failure_state

    provenance
```

Не все поля нужны в первой реализации. Важно заранее выбрать Work как canonical lifecycle owner.

## 6.3. Work должна жить дольше execution

Ключевая PROTOS distinction:

```text
Inference Episode
≠ Work
```

Для Strategy Box:

```text
QThread
≠ Job
≠ Scenario
≠ Work
```

Процесс может упасть. UI может закрыться. Solver может смениться. Remote node может отключиться. Work должна остаться.

## 6.4. Chat history — projection

Источник истины:

```text
Work + Events + Artifacts + Execution state
```

UI projection:

```text
chat messages / cards / status rows / notifications
```

Conversational transcript не должен становиться единственным местом, где живёт важная Work semantics. Это облегчает Android, API, remote control, A2A, recovery, alternative UI и audit.

---

# 7. Persistence: локальная история должна стать durable runtime substrate

## 7.1. Текущий JSON storage хорош для прототипа

Для persistent cognition появляются дополнительные требования:

- atomicity;
- locking/concurrency;
- schema version;
- migration;
- crash consistency;
- reconciliation;
- retention;
- correlation;
- несколько одновременных jobs;
- peer events;
- replay/recovery.

## 7.2. Нужен Persistence Port

Не стоит сразу объявлять одну обязательную БД.

Достаточно:

```text
WorkRepository
EventRepository
ArtifactRepository
JobRepository
```

или объединённого:

```text
RuntimeStateStore
```

с контрактами.

Первая зрелая desktop-реализация может быть SQLite: один файл, транзакции, индексы, встроенность, отсутствие отдельного сервиса. Но SQLite — implementation choice, не фундаментальная семантика.

## 7.3. Event log полезен, но полный event sourcing не обязателен

Практический минимум:

```text
authoritative current Work record
+
append-only material events
+
separate artifacts/logs
```

Material events:

- Work created;
- Job submitted;
- Step started;
- Artifact produced;
- approval requested;
- effect proposed;
- effect committed;
- remote delegation;
- result invalidated;
- Work resumed;
- Work completed.

---

# 8. Job Manager: одна система foreground и background execution

## 8.1. Не создавать отдельный background engine

Правильная схема:

```text
Scenario / Work
        ↓
JobSpec
        ↓
JobManager
        ↓
ExecutionBackend
```

Trigger может быть разным:

```text
manual
chat
schedule
source_change
timer
peer_request
recovery
system_event
```

Но Job lifecycle остаётся одним.

## 8.2. Минимальный Job contract

```text
Job
    job_id
    work_id
    scenario_id?
    operation_id?

    backend_id
    state

    priority
    created_at
    started_at?
    deadline?
    finished_at?

    cancellation_state
    retry_state

    resource_budget?
    progress?

    result_ref?
    failure?
```

## 8.3. Cancellation нужна раньше полноценного PROTOS

Она нужна для долгих загрузок, background jobs, stale analysis, foreground resource preemption, application shutdown и peer cancellation.

Cancellation должна быть cooperative и typed.

## 8.4. Retry нельзя делать слепым

```text
read-only fetch
→ retry often safe

local deterministic transform
→ usually safe

file mutation
→ depends on atomicity/idempotency

external irreversible action
→ retry may duplicate effect
```

---

# 9. Trigger model и persistent background cognition

## 9.1. User request — только один источник Work

Свежий PROTOS предлагает lifecycle:

```text
signal
→ normalized observation
→ materiality
→ Work Candidate
→ admission
→ accepted Work
```

Для Strategy Box потенциальные сигналы:

```text
UserMessage
ManualScenarioLaunch
ScheduleTick
SourceChanged
SourcePublished
FileChanged
WorkspaceChanged
AppDockNodeStateChanged
JobFailed
DeadlineReached
PeerWorkOffer
PeerResultArrived
RevalidationNeeded
```

## 9.2. Work Candidate нужен как предохранитель

Нельзя делать:

```text
каждое событие → durable Work
```

Иначе появится ghost work.

Полезный промежуточный объект:

```text
WorkCandidate
    candidate_id
    trigger
    relevance
    reason
    proposed_work_type
    expires_at
    dedup_key
    admission_policy
```

## 9.3. Source monitoring — идеальный первый background use case

```text
schedule/event
    ↓
cheap fetch metadata / headers / source registry
    ↓
hash / revision / publication delta
    ↓
material change?
    ├── no → record check, sleep
    └── yes
          ↓
SourceSnapshot
          ↓
WorkCandidate
          ↓
admission
          ↓
optional PROTOS analysis
          ↓
Finding / Artifact / notification
```

Это значительно лучше постоянной отправки всех страниц в большую модель.

## 9.4. Background result обязан иметь validity

```text
prepared_at
source_revisions
assumptions
valid_until?
invalidation_conditions
```

В момент использования:

```text
VALID
REVALIDATE
RECOMPUTE
DISCARD
```

---

# 10. Resource model: жизнь системы должна быть дешевле мышления

Fresh PROTOS research формулирует лестницу compute minimization:

```text
0 exact rule / lookup / FSM
1 event filtering
2 context projection
3 cached/materialized result
4 compiled skill/rule/program
5 tiny learned model
6 small specialist
7 general model
8 search/simulation/multi-candidate
9 distributed/human escalation
```

Strategy Box не обязан реализовывать все уровни. Архитектура должна позволять им существовать.

Минимальный resource contract для Job:

```text
priority
deadline?
cancellable
max_concurrency_class
foreground/background
```

Позже:

```text
cpu_budget
memory_budget
gpu_budget
network_budget
api_cost_budget
energy/battery
human_attention
```

Главное — scheduler не должен быть навсегда зашит как «один QThread и всегда выполнять сразу».

Background cognition должна сохранять **foreground reserve**.

---

# 11. Scenario architecture как будущая когнитивная схема

## 11.1. Не превращать prompt в scenario definition

Опасная реализация:

```text
scenario = giant prompt
```

Она связывает semantic workflow, orchestration, model, wording и cognitive topology в один blob.

Целевая модель:

```text
ScenarioSpec
    semantic identity
    parameters
    operation references
    dependencies
    conditions
    verification requirements
    effect/authority class
    expected artifacts
    failure policy
    resource hints
```

Solver-specific prompts — отдельная реализация.

## 11.2. Scenario должен исполняться без PROTOS, где это возможно

Atomic и fixed composite scenarios могут быть детерминированными. PROTOS нужен там, где требуется распознать intent, составить bounded plan, выбрать ветку, проверить результат, определить недостающие данные или адаптировать ход работы.

## 11.3. Cognitive Schema может позже стать более общей сущностью

Свежие исследования PROTOS о semantic constructs / schemas / Mandate IR допускают более богатую модель:

```text
semantic operations
+ applicability
+ constraints
+ evidence requirements
+ authority
+ relations
→ runtime-resolved execution
```

Strategy Box сейчас не должен материализовывать полный Semantic Fabric PROTOS.

Достаточно сделать ScenarioSpec:

- декларативным;
- versioned;
- composition-friendly;
- independent from model prompts;
- grounded in canonical operations.

---

# 12. Fast paths и «компиляция когниции»

Repeated cognitive requests могут постепенно превращаться в direct scenario bindings и затем в exact event-driven paths.

Чтобы cognition могла «скомпилироваться вниз», потребуются:

- stable scenario IDs;
- stable operation IDs;
- versioned dependencies;
- validity envelope;
- guard;
- invalidation trigger;
- fallback/deoptimization route.

Пример:

```text
FastPath:
    intent_signature = "refresh_cbr_sources"
    binds_to = scenario.cbr.full_update
    valid_for = registry_version X + app_profile Y

guard failed
→ return to PROTOS resolution
```

Cache отвечает «есть ли готовый результат?». Compiled cognitive path отвечает «можно ли больше не рассуждать о том, как выполнить этот класс задачи?». Для регулярной аналитической системы это сильный потенциал.

---

# 13. Identity: пользователь, PROTOS, solver и process нельзя смешивать

PROTOS maintained Science специально разделяет:

```text
principal/user identity
≠ cognitive actor identity
≠ runtime/session/process identity
≠ device/node identity
≠ solver/model identity
≠ credential
≠ delegated Authority
```

Предлагаемая минимальная модель:

```text
PrincipalId
    от чьего имени идёт Work

ActorId
    устойчивый логический участник
    human или PROTOS

RuntimeInstanceId
    конкретный запущенный process/activation

NodeId
    AppDock node

SolverId
    фактический cognitive mechanism/model/provider

CredentialRef
    техническое средство доступа

AuthorityGrantId
    разрешение на конкретный scope/effect
```

## 13.1. Один PROTOS на пользователя — сильная модель

```text
User A Strategy Box
    ↳ PROTOS Actor A

User B Strategy Box
    ↳ PROTOS Actor B

User C Strategy Box
    ↳ PROTOS Actor C
```

Каждый имеет собственный actor identity, principal context, память/Work и capabilities, но может участвовать в shared Work.

Это лучше одного shared PROTOS, потому что universal multi-principal shared-actor governance у текущего PROTOS прямо остаётся условной и profile-specific областью.

---

# 14. Authority и Effect Gateway

Главный invariant:

```text
Capability
≠ Authority
```

Наличие operation в registry означает «Strategy Box умеет это делать», а не «этот PROTOS сейчас вправе это сделать».

Для аналитического Strategy Box effect classes могут быть:

```text
READ_ONLY
CREATE_LOCAL_ARTIFACT
MUTATE_WORKSPACE
DELETE_OR_REPLACE
COMMUNICATE_TO_OTHER_USER
REMOTE_EXECUTION
CHANGE_BACKGROUND_POLICY
INSTALL_OR_ENABLE_EXTENSION
EXTERNAL_CONSEQUENTIAL
```

PROTOS выдаёт `EffectProposal`, Strategy Box проверяет principal, Work, effect class, scope, preconditions, freshness, required confirmation и resource constraints.

Outcome:

```text
DENY
REQUEST_APPROVAL
ACCEPT
```

Approval не должна быть универсальным modal-костылём. Нужны standing grants, session grants, one-shot approval, policy deny и safe automatic class.

---

# 15. Revision and freshness fences

Типичная проблема долгой cognition:

```text
t0: PROTOS получил source/workspace revision 10
t1: начался анализ
t2: data обновились до revision 14
t3: PROTOS вернул result для revision 10
```

Candidate result должен нести:

```text
based_on_revision
source_versions
assumptions
produced_at
valid_until?
validity_conditions
```

Перед commit/use:

```text
ACCEPT
REVALIDATE
REPLAN
DISCARD
ESCALATE
```

Strategy Box уже имеет естественные revision sources: SourceSnapshot hashes/revisions, registry versions, file hashes, Work revision, scenario version, operation version, AppDock session/node state и artifact IDs.

---

# 16. Context projection: PROTOS не должен видеть весь Strategy Box

Awareness следует строить как bounded projection.

Плохой путь:

```text
дать AI filesystem root
дать полный state JSON
дать shell
дать все логи
дать все user data
```

Лучше:

```text
CognitiveContext
    principal
    current Work
    allowed scenarios
    relevant artifacts
    selected source snapshots
    bounded workspace refs
    current capabilities
    Authority
    resource envelope
    revision/freshness
```

Projection должна быть task-specific. Это одновременно security, privacy и compute optimization: меньше data leakage, prompt injection surface, token cost, latency, context overflow и accidental coupling.

---

# 17. Artifact, Evidence и Provenance как общий язык

Artifact уже first-class entity. Следующий шаг — расширить identity:

```text
Artifact
    artifact_id
    kind
    content_ref
    content_hash?
    schema/version?
    created_at

    work_id
    job_id
    operation_id
    scenario_id

    producer_actor_id
    solver_id?

    source_refs
    parent_artifact_refs

    provenance
    retention
```

Peer collaboration без artifact identity быстро развалится. Сообщение «я посчитал результат» должно сопровождаться идентичностью Work, revisions, artifact/evidence refs и producer provenance.

Evidence также не равно message. Peer transport переносит сообщение, а evidence должно ссылаться на отдельный объект или доказательную связь.

---

# 18. Observability для cognitive runtime

Текущая связь:

```text
Case
→ Step
→ Operation
→ Log
→ Artifact
→ Event
```

уже является хорошей основой.

PROTOS добавит:

```text
Work
→ Cognitive activation
→ Solver call
→ Tool/Operation request
→ Verification
→ Candidate
→ Effect proposal
```

Нужна общая correlation geometry:

```text
trace_id
work_id
job_id
case_id
step_id
operation_id
actor_id
solver_id
artifact_id
peer_task_id?
```

OpenTelemetry к октябрю 2026 года уже развивает GenAI semantic conventions и использует span patterns уровня `invoke_agent → chat / execute_tool`. Это хороший telemetry adapter, но сначала Strategy Box должен определить собственную Work/Job/Operation semantics. Full prompts, retrieved content и model completions лучше делать opt-in из-за размера и чувствительности.

---

# 19. AppDock: кто за что отвечает

## 19.1. AppDock даёт правильный внешний substrate

Базовое описание AppDock предусматривает node, environment, state, long operations, results, diagnostics/recovery, host, remote access, roles/permissions и controlled AI actions.

### AppDock владеет

- установкой/активацией продукта;
- managed environment;
- node/session substrate;
- remote connection;
- host availability;
- application lifecycle;
- health/recovery surfaces;
- внешними platform permissions;
- transport-level remote capability.

### Strategy Box владеет

- analytical operations;
- scenarios;
- Work;
- jobs;
- artifacts;
- application-level Authority;
- scenario state;
- collaboration semantics;
- cognitive host contract.

### PROTOS владеет

- cognitive resolution;
- planning/search/verification;
- solver selection внутри разрешённого contour;
- bounded background cognition;
- peer cognitive participation.

AppDock может знать active job, health, runtime state и recent artifacts, но canonical Strategy Box Work semantics должна оставаться у Strategy Box.

Remote execution проходит через:

```text
ExecutionBackend
├── LocalExecutionBackend
├── AppDockNodeExecutionBackend
└── PeerDelegationBackend?   # позже, если оправдано
```

Scenario не должен знать, где физически исполняется operation.

---

# 20. Frontend-neutral architecture и Android

PROTOS усиливает требование убрать Qt из application runtime. Cognitive Work должна выполняться без открытого desktop UI, в background, на host, на Android client, remote и после restart.

Целевая схема:

```text
application/
    work/
    operations/
    scenarios/
    jobs/
    triggers/
    artifacts/
    events/
    authority/
    cognition/
    collaboration/

runtime/
    context/
    composition/
    state/

adapters/
    persistence/
    local_execution/
    appdock/
    cognitive/
    collaboration/

presentation/common/
    semantic view models

presentation/qt_desktop/
    Qt bridge/widgets
```

Будущий Android получает другой presentation/host adapter, а semantics остаётся прежней.

Отдельный shared repository пока создавать рано. Сначала полезнее стабилизировать границу внутри `stratbox-windows`, сделать application/runtime импортируемыми без Qt и только после реального Android reuse решать вопрос физического выноса common package.

---

# 21. Phase 2: persistent/background PROTOS

Background mode не должен быть отдельным «вторым PROTOS».

Один actor может существовать логически постоянно, а физически активироваться только по событиям:

```text
PROTOS Actor Identity
    durable Work
    timers/subscriptions
    memory/state refs
        │
        ├── asleep
        ├── cheap watcher active
        └── solver activation on demand
```

Хорошие background categories Strategy Box:

- проверка появления новых официальных публикаций;
- source freshness;
- изменение schema;
- пересмотр исторических данных;
- workspace integrity;
- pending Work/deadline;
- artifact validation;
- scheduled analytical refresh;
- consistency check между связанными источниками;
- подготовка вероятно нужного отчёта;
- bounded re-analysis после source update.

Полезная PROTOS distinction:

```text
permission to observe
≠ permission to reason
≠ permission to create Work
≠ permission to notify/interact
≠ permission to cause external effect
≠ permission to self-change
```

Например watcher может иметь право читать source metadata, создавать internal Work и запускать read-only analysis, но не иметь права мутировать workspace или отправлять данные peer.

---

# 22. Phase 3: Cognitive Schemas в аналитической работе

Эволюция может выглядеть так:

```text
сегодня:
ScenarioSpec → fixed steps

позже:
Cognitive Procedure
→ semantic goals
→ operation candidates
→ constraints
→ verification criteria
→ runtime-resolved plan

ещё позже, если PROTOS semantic fabric стабилизируется:
task signature
→ applicable constructs
→ resolved cognitive configuration
→ physical execution
```

Чтобы этот переход не требовал rewrite, сейчас достаточно stable operation IDs, scenario version, step identity, explicit dependencies, parameter schemas, conditions as data, effect policy, verification metadata, artifact expectations и provenance.

Fixed scenario тогда является частным случаем будущей cognitive schema.

---

# 23. Multi-user: правильная модель — federation of actors

Для многопользовательского Strategy Box предпочтительна схема:

```text
┌────────────────────┐       ┌────────────────────┐
│ Strategy Box A     │       │ Strategy Box B     │
│ Principal A        │       │ Principal B        │
│ PROTOS Actor A     │◄─────►│ PROTOS Actor B     │
│ Local Work/Memory  │       │ Local Work/Memory  │
└────────────────────┘       └────────────────────┘
```

Общим становится не сознание, а конкретная Shared Work / Collaboration scope.

Разные пользователи могут иметь разные private data, memory, Authority, preferences, subscriptions, solver capabilities, resources и права на workspace. Слияние в shared mutable memory создаёт privilege leakage, unclear ownership, stale facts, deletion problems, memory poisoning, recovery complexity и conflict of principals.

Shared Work не требует shared memory:

```text
authoritative local/domain state
        ↓
typed projection
        ↓
peer task
        ↓
peer local cognition
        ↓
typed result / artifact / evidence
        ↓
reconciliation
```

---

# 24. A2A: где он действительно нужен

A2A Protocol v1.0 вышел 12 марта 2026 года как первый stable production-ready release. Он предназначен для interoperability независимых AI agents и предоставляет общую модель capability discovery и stateful tasks/messages/artifacts.

Это делает A2A подходящим кандидатом для **federation transport layer** Strategy Box.

Но protocol authentication/authorization не равно semantic Authority. Поэтому A2A не должен владеть Strategy Box Work semantics, principal model, domain truth, artifact acceptance, operation authorization, user intent, peer trust или evidence quality.

Правильный boundary:

```text
CollaborationPort
    discover_peer(...)
    offer_work(...)
    accept/reject(...)
    get_status(...)
    submit_result(...)
    challenge(...)
    cancel(...)
        │
        ▼
A2ACollaborationAdapter
```

Если стандарт сменится, application layer останется прежним.

---

# 25. Что PROTOS разных пользователей могут делать друг с другом

## 25.1. Capability Advertisement

Actor A может запросить bounded capabilities Actor B.

```text
CapabilityAdvertisement
    actor_id
    operations/scenarios
    data scopes
    artifact types
    execution locality
    resource/cost class
    evidence level
    validity/expiry
```

Capability не означает автоматического разрешения использовать её.

## 25.2. Work Delegation

```text
WorkOffer
    offer_id
    parent_work_id
    requested_outcome
    constraints
    inputs/artifact refs
    deadline
    authority scope
    disclosure scope
    expected result
```

Peer может вернуть:

```text
ACCEPT
REJECT
COUNTERPROPOSE
UNSUPPORTED
```

## 25.3. Parallelism for speed

Parent Work можно разбить на независимые partitions и выполнить параллельно, если serial/fan-in cost не съедает выигрыш.

## 25.4. Parallelism for quality

```text
A produces candidate
B independently verifies/challenges
```

Независимость должна быть реальной. Полезно хранить solver lineage, source set, method и toolchain. Два одинаковых model instances на одинаковых данных не являются двумя независимыми доказательствами.

## 25.5. Specialist delegation

Один пользователь/узел может иметь локальные данные, specialized scenario, более мощный compute, иной solver или human expertise. Peer delegation позволяет использовать специализацию без копирования всего cognitive state.

---

# 26. Federation contract Strategy Box

Независимо от wire protocol полезно определить product-level objects:

```text
PeerHello / PeerIdentity
CapabilityAdvertisement
WorkOffer
WorkAccepted
WorkRejected
WorkStatus
CandidateResult
ArtifactReference
EvidenceReference
Challenge
AuthorityRequest
ApprovalResponse
Cancellation
Completion
Failure
```

Transport-neutral поля:

```text
message_id
causation_id
correlation_id
sender_actor_id
sender_principal_context
recipient_actor_id
work_id
parent_work_id?
created_at
expires_at?
schema_version
```

Для effect/retry — `idempotency_key`.

Для replay/dedup — stable `message_id` и causation/correlation chain.

Без backpressure multi-PROTOS легко создаёт thundering herd. Нужны max fan-out, delegation depth, active peer Work quota, per-peer rate limit, deadline/TTL, dedup, cancellation propagation, stop conditions и resource budget.

---

# 27. Shared Work ownership

Несколько actors допустимы; несколько неявных владельцев одного authoritative state — источник хаоса.

Для shared Work нужен явный Work Coordinator/Owner. Физически owner может быть actor, designated node, collaboration service или project owner, но ownership должен быть однозначным.

Fan-in — reconciliation, а не voting.

Плохая схема:

```text
3 PROTOS сказали "рост"
2 сказали "падение"
→ рост
```

Правильнее:

```text
collect candidates
→ compare evidence / baselines / methods
→ resolve conflicts
→ preserve unresolved uncertainty
→ accepted result
```

При network partition local Work может продолжаться в разрешённом scope, shared state не притворяется синхронизированным, Authority не расширяется, а после reconnect выполняется reconciliation.

---

# 28. Presence, Assignments и PROTOS

Текущие Presence, Assignments, actor kinds, case authorship и incoming/outgoing chat semantics могут стать человеческой projection будущей actor/collaboration model.

Полезно постепенно прийти к:

```text
Participant
    participant_id
    kind = human | cognitive_actor | system
    principal_ref
    actor_ref?
    presence
    node_ref?
    capabilities_summary
```

UI может отображать человека и его PROTOS отдельно либо группировать их.

Assignment логически можно рассматривать как `Work assigned_to Actor/Participant`, сохранив привычный UX-термин.

---

# 29. Privacy и data boundaries

Один PROTOS на пользователя создаёт хороший privacy boundary:

```text
User A private state
→ projection
→ shared Work
→ peer
```

лучше, чем global AI memory.

Peer disclosure должна быть explicit. Делегирование должно передавать конкретные ArtifactRefs, SourceSnapshots, question/constraints и bounded metadata, а не доступ ко всему workspace.

В persistent logs по умолчанию лучше сохранять operation IDs, solver identity, timings, token/resource metrics, structured tool calls, errors и artifact/evidence links. Raw prompts, retrieved content и full completions — opt-in/debug profile с retention policy.

---

# 30. Recovery: crash не должен уничтожать cognition

Boot с PROTOS perspective — это reconciliation:

```text
load authoritative Work
→ inspect unfinished Jobs
→ inspect pending effects
→ check source revisions
→ check AppDock/node state
→ restore timers/subscriptions
→ determine current capabilities
→ mark stale assumptions
→ resume/replan where valid
```

Особенно важен случай неизвестного внешнего эффекта:

```text
operation started
network timeout/crash
unknown whether remote effect happened
```

Нельзя автоматически повторять. Work получает `effect_state = UNKNOWN` и reconciliation path.

AppDock отвечает за environment/node/application recovery. Strategy Box — за Work recovery, Job recovery, application data, effect reconciliation и source revalidation.

---

# 31. Solver abstraction и CognitivePort

Даже если первая реализация использует одну LLM, application contract должен быть шире.

Strategy Box достаточно видеть:

```text
CognitivePort
```

Потенциальный минимальный API:

```text
resolve_ingress(event, host_context) -> WorkProposal

propose_next(work_snapshot, host_context) -> CognitiveProposal

review_result(work_snapshot, operation_result) -> CognitiveProposal?
```

Можно начать только с `resolve_ingress`.

PROTOS сам развивается, а свежие Epoch 002 materials ещё research-level. Поэтому Strategy Box должен зависеть только от минимального stable host-side contract:

```text
input projection
→ candidate proposal
```

Всё остальное остаётся за adapter boundary.

---

# 32. Cognitive proposal model

Пример:

```text
CognitiveProposal
    proposal_id
    work_id?

    kind:
        CREATE_WORK
        INVOKE_SCENARIO
        INVOKE_OPERATION
        ASK_USER
        REQUEST_SOURCE
        VERIFY
        DELEGATE
        WAIT
        COMPLETE
        ABSTAIN

    payload
    rationale_summary?
    assumptions
    evidence_refs
    required_authority
    based_on_revision
    valid_until?
```

`rationale_summary` — user-facing explanation, а не hidden chain-of-thought.

Proposal не выполняется автоматически:

```text
CognitiveProposal
→ schema validation
→ applicability
→ Authority
→ freshness
→ Job/Work transition
```

---

# 33. Capability Registry как интерфейс к PROTOS

PROTOS должен уметь спросить «что Strategy Box сейчас умеет?» через machine-readable registry, а не получать ручной prompt со списком функций.

Candidate capability description:

```text
Capability
    id
    version
    title
    semantic_tags

    input_schema
    output_schema

    preconditions
    required_sources
    required_workspace

    side_effect_class
    authority_requirement

    estimated_resource_class
    expected_duration_class

    artifact_kinds

    supports_background
    supports_remote
    supports_cancel
    supports_partial

    ai_visibility
```

Scenario Registry тоже является capability surface. PROTOS обычно должен предпочитать готовый scenario, если он закрывает intent, а не случайно компоновать low-level operations.

---

# 34. Verification как отдельная ответственность

Generation ≠ verification.

Для Strategy Box verification может включать:

- schema validation;
- source hash;
- reconciliation totals;
- cross-source comparison;
- expected row count;
- business invariant;
- independent recomputation;
- human review.

Result contract может содержать:

```text
verification:
    state
    checks
    evidence_refs
```

PROTOS может решить, нужен ли дополнительный verification step, но не должен объявлять результат проверенным только потому, что сам его сгенерировал.

---

# 35. Уровни автономности Strategy Box

Вместо одного `AI autonomy = on/off` лучше понимать независимые grants.

| Право | Пример политики |
|---|---|
| Observe source metadata | Allowed |
| Read selected workspace artifacts | Allowed |
| Interpret user messages | Allowed |
| Create Work candidate | Allowed |
| Start read-only scenarios | Allowed |
| Create local artifacts | Allowed |
| Overwrite existing artifacts | Approval |
| Delete files | Denied / Approval |
| Notify user | Policy |
| Delegate to peer | Approval / Policy |
| Accept peer Work | Policy |
| Install/change capabilities | Denied |
| Self-modify learned behavior | Separate lifecycle |

Эти настройки не обязательно показывать пользователю в технической форме. Это semantic model под UI.

---

# 36. Что не надо строить сейчас

## 36.1. Giant `ProtosManager`

Не создавать объект, который одновременно хранит memory, запускает models, выбирает scenarios, владеет jobs, пишет artifacts, общается с AppDock, управляет peers и решает permissions. Это новый Orchestrator God.

## 36.2. Global AI memory

Не нужна единая «память агента» для Work state, conversation, source cache, artifacts, preferences, peer memory и logs. Эти классы имеют разные owners и lifecycle.

## 36.3. Agent classes Planner/Researcher/Critic как фундамент

Они могут появляться как execution topology, но не должны определять persistent data model Strategy Box.

## 36.4. A2A types внутри core application model

A2A — adapter. Внутренние domain contracts должны быть transport-neutral.

## 36.5. LLM provider types внутри ScenarioSpec

Scenario semantics не должна зависеть от OpenAI/Anthropic/local-model API.

## 36.6. Full cognitive ontology

Свежие PROTOS research о semantic fabric интересны, но Strategy Box пока нужен concrete vertical slice. Contracts лучше расширять по реальным use cases.

## 36.7. Multi-agent до durable Work

PROTOS предлагает сначала закрепить semantics, построить reference lifecycle, проверить local/distributed physical profiles, затем добавлять application DX, learning/fast paths и лишь потом federation. Для Strategy Box последовательность должна быть похожей.

---

# 37. Целевая архитектура Strategy Box с PROTOS-ready boundary

```text
┌────────────────────────────────────────────────────────────┐
│                        PRESENTATION                         │
│ Qt Desktop / future Android / API                          │
│ scenario chat / inspector / participants / artifacts       │
└───────────────────────┬────────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────────┐
│                    APPLICATION CORE                        │
│                                                            │
│ Ingress ──► Work ──► Scenarios ──► Jobs ──► Artifacts      │
│              │          │           │                       │
│              │          │           ├─ Events               │
│              │          │           ├─ Diagnostics          │
│              │          │           └─ Provenance           │
│              │          │                                   │
│              │          ├─ Authority / Effect Policy        │
│              │          └─ Capability Registry              │
│              │                                              │
│              ├──────── CognitivePort ◄──── PROTOS adapter    │
│              │                                              │
│              └──────── CollaborationPort ◄─ A2A adapter     │
└───────────────────────┬────────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────────┐
│                    EXECUTION LAYER                         │
│ ExecutionBackend                                           │
│   ├─ Local                                                 │
│   └─ AppDock Remote Node                                   │
└───────────────────────┬────────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────────┐
│                         STRATBOX                            │
│ canonical domain operations                                │
│ sources / data / models / validation / exports              │
└────────────────────────────────────────────────────────────┘

AppDock surrounds the product with:
installation / node / session / environment / host / health / recovery
```

---

# 38. Рекомендуемое физическое размещение ответственности

## 38.1. `stratbox`

Должен содержать:

- domain logic;
- canonical operations;
- typed Request/Result;
- source/provenance contracts;
- validation;
- neutral diagnostics;
- artifacts as domain outputs where appropriate.

Не должен содержать chat, PROTOS integration, peer networking, presence, AppDock UI или multi-user orchestration.

## 38.2. Универсальный application layer Strategy Box

Сегодня он физически находится в `stratbox-windows`.

Логичная целевая структура:

```text
application/
    ingress/
    work/
    operations/
    scenarios/
    jobs/
    triggers/
    events/
    artifacts/
    authority/
    cognition/
    collaboration/
```

Эти модули должны быть platform-neutral.

## 38.3. `runtime`

```text
runtime/
    context
    composition
    persistence
    capability state
    recovery
```

Без Qt imports.

## 38.4. `adapters`

```text
adapters/
    appdock/
    persistence/
    local_execution/
    protos/
    collaboration/
        a2a/   # только когда реально понадобится
```

## 38.5. Presentation

```text
presentation/
    common/
    qt_desktop/
```

Будущий Android получает `presentation/android/` или отдельный repo с теми же contracts.

---

# 39. Initial PROTOS vertical slice

Первая реализация должна доказать только одну вещь:

> пользователь пишет естественным языком запрос, PROTOS корректно связывает его с готовой Strategy Box capability, а вся execution/recovery/observability остаётся в обычном Strategy Box runtime.

Минимальная цепочка:

```text
1. UserMessage
2. IngressEvent
3. bounded CognitiveContext
4. CognitivePort.resolve_ingress()
5. WorkProposal
6. validate against ScenarioRegistry
7. create Work
8. submit Job
9. execute Scenario
10. persist Events/Artifacts
11. optional PROTOS summarize result
12. render chat projection
```

PROTOS в MVP разрешено:

- читать каталог AI-visible scenarios;
- читать parameter schemas;
- получать bounded defaults/context;
- предлагать scenario;
- заполнять параметры;
- задавать clarification;
- получать structured result;
- делать user-facing summary.

PROTOS в MVP не разрешено:

- arbitrary Python;
- shell;
- свободный filesystem crawl;
- прямое изменение Work state;
- прямой commit destructive action;
- установка packages;
- произвольный network access;
- peer delegation;
- self-modification.

Такой MVP скромен, но архитектурно правильный.

---

# 40. Второй vertical slice: background source watcher

После MVP следующий сильный тест:

```text
official source
→ cheap change detection
→ WorkCandidate
→ bounded PROTOS relevance/analysis
→ Artifact/Finding
→ notification policy
```

Он проверит triggers, background Job Manager, source revisions, context projection, persistent Work, resource priority, quiet notifications, stale result и recovery.

Это естественный мост между Strategy Box как аналитическим продуктом и persistent PROTOS.

---

# 41. Третий vertical slice: два Strategy Box / два PROTOS

Минимальный federation test:

```text
A creates Work
→ A delegates bounded subtask to B
→ B accepts
→ B executes local Scenario
→ B returns ArtifactRef + Result
→ A validates/reconciles
→ Parent Work continues
```

Без shared memory.

Тест должен доказать:

- actor/principal identities не смешиваются;
- scope delegation bounded;
- data projection selective;
- correlation preserved;
- cancellation works;
- peer failure не corrupt-ит parent Work;
- repeated message deduplicated;
- artifact provenance preserved;
- peer result остаётся candidate до acceptance;
- Authority не расширяется через peer boundary.

---

# 42. Cross-scale conformance

Один Scenario должен сохранять semantics при исполнении через:

```text
LocalExecutionBackend
AppDockNodeExecutionBackend
```

а позже — delegated peer execution.

Должны сохраняться operation identity, Request semantics, Result semantics, artifacts, Work transition, failure model и Authority. Меняется placement, latency, resources и transport.

---

# 43. Версионирование contracts

С учётом отсутствия требования обратной совместимости сейчас лучше сразу ввести чистую версионность.

Нужны версии как минимум для:

```text
OperationDescriptor
ScenarioSpec
Work persisted schema
Event schema
Artifact metadata
CognitivePort contract
Collaboration envelope
```

Persisted/networked objects должны иметь `schema_version` с самого начала. Это дешёвая инвестиция сейчас и дорогая миграция потом.

---

# 44. Порядок реализации

## Phase A — Core semantic foundation

1. Довести canonical operation contracts в `stratbox`.
2. Унифицировать Result envelope / diagnostics / artifacts / provenance.
3. Стабилизировать operation IDs.
4. Добавить operation capability metadata.

**PROTOS пока не нужен.**

## Phase B — Durable application runtime

1. Расширить Work semantics поверх текущего Case.
2. Ввести Persistence Port.
3. Перевести material application events в durable form.
4. Ввести Job Manager.
5. Добавить cancellation.
6. Добавить retry/recovery semantics.
7. Отделить application execution coordination от Qt.

## Phase C — Execution and trigger abstraction

1. `ExecutionBackend`.
2. `LocalExecutionBackend`.
3. Trigger model.
4. Background scheduler/watchers.
5. priority/deadline/backpressure.
6. restart reconciliation.

## Phase D — Authority, identity, validity

1. Actor/Principal/Runtime/Solver IDs.
2. operation effect classes.
3. Authority policy.
4. approval flow.
5. revision/freshness fences.
6. explicit `UNKNOWN`.

## Phase E — Cognitive MVP

1. `CognitivePort`.
2. PROTOS adapter.
3. AI-visible capability catalog.
4. bounded CognitiveContext.
5. `WorkProposal`.
6. free-text scenario selection.
7. clarification.
8. result summarization.
9. trace/metrics.

## Phase F — Persistent cognition

1. source-change triggers;
2. background Work admission;
3. salience/materiality;
4. notification policy;
5. foreground reserve;
6. precompute/revalidation;
7. compiled fast-path experiments.

## Phase G — Remote/Android

1. AppDock remote ExecutionBackend;
2. application/runtime fully frontend-neutral;
3. Android surface;
4. approvals/status/artifacts from mobile;
5. remote Work continuation.

## Phase H — Federation

1. CollaborationPort.
2. peer identity/capabilities.
3. bounded WorkOffer lifecycle.
4. artifact/evidence exchange.
5. dedup/causal IDs/backpressure.
6. A2A adapter.
7. independent verification topology.
8. partition/reconciliation tests.

---

# 45. P0 / P1 / P2 requirements

## P0 — заложить до PROTOS integration

- canonical operations;
- durable Work identity/state;
- jobs;
- frontend-neutral execution;
- structured Result/failure;
- artifacts/provenance;
- cancellation;
- persistence schema version;
- actor/principal distinctions;
- effect classes;
- ExecutionBackend interface;
- capability discovery.

Если этого нет, PROTOS быстро начнёт владеть тем, чем владеть не должен.

## P1 — сделать вместе с первым PROTOS

- CognitivePort;
- ingress semantics;
- bounded context;
- proposal validation;
- AI-visible scenario registry;
- trace/correlation;
- stale result;
- approval;
- solver identity;
- resource class.

## P2 — подготовить contracts, реализовать позже

- trigger-driven background cognition;
- peer federation;
- A2A;
- independent verifier routing;
- cognitive compilation;
- multi-solver resource optimization;
- learning/self-improvement;
- large-scale semantic fabric.

---

# 46. Что PROTOS меняет в уже намеченном roadmap Strategy Box

## 46.1. Canonical Operations становятся P0

Ранее они выглядели как системное улучшение core. Теперь это ещё и основной ABI между host и cognition.

## 46.2. Background Job Manager нужно делать как общий executor

Не как feature вкладки «Фоновые». Он должен стать общей runtime infrastructure для normal scenarios, background, remote, cognitive и delegated Work.

## 46.3. Cases должны стать durable Work projections

Текущую Case-модель не требуется выбрасывать. Её стоит развить так, чтобы она переживала restart, смену backend, смену solver, long-running pause и peer delegation.

## 46.4. Presence/Assignments получают более сильный смысл

Они становятся ранними проекциями будущей actor/collaboration model.

## 46.5. Android становится проще

Если Work/Jobs/Artifacts/Cognition/Collaboration принадлежат application layer, Android становится ещё одной surface, а не вторым продуктовым runtime.

---

# 47. Основные риски

1. **AI-first shortcut:** встроить LLM прямо в MainWindow — cognition захватит orchestration.
2. **Prompt as architecture:** workflow и правила живут в system prompt — отсутствуют versioned semantics и deterministic baseline.
3. **Agent owns state:** memory/conversation агента становится источником истины — crash/model swap уничтожает continuity.
4. **Shared AI memory для команды:** privacy, ownership, stale facts, poisoning, deletion и conflicts.
5. **Capability = permission:** видимая operation автоматически доступна модели — ambient Authority.
6. **Background = permanent LLM loop:** compute runaway, privacy creep, stale analysis, notification spam.
7. **Multi-agent by default:** coordination cost, common-mode error, branch explosion, duplicated effects.
8. **A2A as domain model:** product semantics привязана к внешнему transport standard.
9. **One central orchestrator:** огромная trusted surface, bottleneck и hidden coupling.
10. **Federation before local recovery:** распределение умножит state ambiguity.

---

# 48. Acceptance criteria фундамента

Перед первым серьёзным PROTOS integration Strategy Box должен уметь ответить на следующие вопросы.

### Work

- Что является canonical Work identity?
- Где authoritative Work state?
- Как Work переживает restart?
- Как resume проверяет свежесть?
- Как Work отменяется?

### Capability

- Какие operations/scenarios доступны?
- Как получить их schema машинно?
- Какие из них доступны AI?
- Какие side effects они имеют?

### Execution

- Как submit Job?
- Как читать status/progress?
- Как cancel?
- Как различить local и remote execution без изменения Scenario?

### Results

- Где structured Result?
- Где warnings/failures?
- Какие artifacts созданы?
- Как связать результат с sources/revisions?

### Authority

- Кто principal?
- Кто actor?
- Что может сделать actor?
- Какие действия требуют approval?
- Что делать при изменившемся baseline?

### Recovery

- Что происходит с running Job после crash?
- Как определяется `UNKNOWN`?
- Как избежать blind retry?

### Cognition

- Как PROTOS получает bounded context?
- Как он предлагает действие?
- Кто валидирует proposal?
- Может ли приложение работать без PROTOS?

### Collaboration

- Можно ли идентифицировать peer actor отдельно от user/node?
- Есть ли correlation/causal IDs?
- Можно ли передать bounded Work без shared memory?
- Кто принимает peer result?

Если ответы существуют независимо от конкретной LLM, фундамент в правильном направлении.

---

# 49. Итоговая архитектурная позиция

Исследование PROTOS не приводит к выводу, что Strategy Box должен сейчас получить большой agent framework.

Наоборот:

> **Strategy Box следует сделать семантически устойчивым host-приложением, в котором cognition является заменяемой и масштабируемой способностью.**

Три будущих режима становятся одной эволюционной линией.

### Режим 1 — текстовый помощник

```text
User text
→ PROTOS intent resolution
→ existing Scenario
→ Result
```

PROTOS тонкий. Strategy Box почти весь детерминированный.

### Режим 2 — persistent analytical cognition

```text
source/timer/event
→ Work Candidate
→ background Work
→ selective PROTOS cognition
→ Artifact/Finding
```

PROTOS существует логически постоянно, но дорогой solver просыпается выборочно.

### Режим 3 — federation

```text
PROTOS A
↔ bounded Work / evidence / artifacts
↔ PROTOS B
```

Каждый Strategy Box сохраняет собственного actor, principal context, memory и Authority. Общение происходит вокруг конкретной Work, а не через общую «мозговую память».

Именно этот путь лучше всего соответствует и текущему PROTOS, и свежим направлениям его развития, и уже сформировавшейся архитектуре Strategy Box.

---

# 50. Самые важные выводы в 20 тезисах

1. Strategy Box должен интегрировать **CognitivePort**, а не конкретную LLM architecture.
2. `stratbox` остаётся owner предметных операций и данных.
3. Natural-language chat является ingress carrier, а не command bus.
4. Canonical operation — основной ABI между Strategy Box и cognition.
5. Scenario — user-level capability и потенциальный будущий compiled cognitive procedure.
6. Case следует развить в durable Work projection.
7. Work state должен переживать process/model/UI lifetime.
8. Job Manager должен быть один для foreground, background, remote и cognitive execution.
9. Local/remote execution разделяются через `ExecutionBackend`.
10. Background cognition начинается с дешёвого event/change detection, а не с постоянной LLM.
11. Result должен быть revision/freshness-bound.
12. Capability и Authority должны быть разными contract layers.
13. PROTOS возвращает candidate/proposal; Strategy Box commit-ит допустимые transitions/effects.
14. Artifacts, evidence и provenance должны иметь stable identities.
15. Actor, principal, node, runtime и solver нельзя смешивать.
16. Один PROTOS на пользователя — сильная базовая multi-user topology.
17. Multi-user должен быть federation of Work, а не shared mutable memory.
18. A2A подходит как будущий adapter/transport, но не как semantic core.
19. Android и remote modes требуют frontend-neutral application/runtime уже сейчас.
20. Чем лучше сейчас будет Work/operation/execution foundation, тем меньше самой PROTOS-интеграции придётся переделывать при её будущем усложнении.

---

# Appendix A. Candidate contracts

## A.1. Work

```yaml
Work:
  schema_version: 1
  work_id: string
  revision: integer

  principal_id: string
  owner_actor_id: string
  created_by_actor_id: string

  origin:
    kind: user | trigger | peer | recovery | system
    ref: string?

  objective: string?
  constraints: object
  status: string

  scenario_id: string?
  scenario_version: string?

  created_at: datetime
  updated_at: datetime
  deadline: datetime?
  expires_at: datetime?

  source_refs: []
  artifact_refs: []
  evidence_refs: []

  open_questions: []
  assumptions: []

  pending_approvals: []
  pending_effects: []
  execution_refs: []

  failure: object?
```

## A.2. Job

```yaml
Job:
  schema_version: 1
  job_id: string
  work_id: string

  backend_id: string
  state: queued | running | waiting | completed | failed | cancelled | unknown

  priority: integer
  foreground: boolean
  deadline: datetime?

  cancellable: boolean
  retry_policy: object?

  created_at: datetime
  started_at: datetime?
  finished_at: datetime?

  progress: object?
  result_ref: string?
  failure: object?
```

## A.3. Cognitive Proposal

```yaml
CognitiveProposal:
  schema_version: 1
  proposal_id: string

  actor_id: string
  work_id: string?

  kind: >
    create_work |
    invoke_scenario |
    invoke_operation |
    ask_user |
    request_source |
    verify |
    delegate |
    wait |
    complete |
    abstain

  payload: object

  based_on_work_revision: integer?
  source_revisions: object

  assumptions: []
  evidence_refs: []

  required_authority: object?
  valid_until: datetime?
```

## A.4. Peer Work Offer

```yaml
WorkOffer:
  schema_version: 1

  offer_id: string
  message_id: string
  correlation_id: string
  causation_id: string?

  sender_actor_id: string
  recipient_actor_id: string

  parent_work_id: string
  requested_outcome: object

  input_artifact_refs: []
  evidence_refs: []

  disclosure_scope: object
  authority_scope: object

  deadline: datetime?
  expires_at: datetime?
```

---

# Appendix B. Proposed status vocabulary

```text
PENDING
QUEUED
RUNNING
WAITING
WAITING_APPROVAL
WAITING_EXTERNAL
COMPLETED
PARTIAL
FAILED
CANCELLED

UNSUPPORTED
ABSTAIN
UNAVAILABLE
TIMEOUT
INVALID_OUTPUT
STALE_RESULT
POLICY_DENIED
RESOURCE_EXHAUSTED
VERIFICATION_FAILED
AUTHENTICATION_REQUIRED
CONFLICT
UNKNOWN
```

Не обязательно использовать один enum для всех сущностей. Важно сохранить различия смыслов.

---

# Appendix C. External standards and precedents

## A2A Protocol

- A2A Protocol v1.0 announcement, 2026-03-12:  
  https://a2a-protocol.org/dev/blog/2026/03/12/a2a-protocol-ships-v10-production-ready-standard-for-agent-to-agent-communication/
- Official project/specification:  
  https://github.com/a2aproject/A2A

Использование в Strategy Box: кандидат для federation transport adapter между независимыми cognitive actors.

## OpenTelemetry

- GenAI observability overview, 2026-05-14:  
  https://opentelemetry.io/blog/2026/genai-observability/
- OpenTelemetry semantic conventions:  
  https://opentelemetry.io/docs/specs/semconv/

Использование в Strategy Box: внешний telemetry/export standard после определения собственных Work/Job/Operation semantics.

---

# Appendix D. Internal source map

## PROTOS maintained baseline

```text
ForestTiger-GH/PROTOS
knowledge-product/
  science/
  target-what/
  target-how/
  product-architecture/
```

Ключевые материалы:

```text
knowledge-product/target-what/TARGET-WHAT.md
knowledge-product/target-how/TARGET-HOW.md
knowledge-product/target-how/DESIGN-FREEDOM.md
knowledge-product/target-how/DATA-PRIVACY-LIFECYCLE.md
knowledge-product/product-architecture/PRODUCT-ARCHITECTURE.md

knowledge-product/science/01-COGNITIVE-SEMANTICS-AND-GOALS.md
knowledge-product/science/02-COMPUTE-SOLVERS-AND-SCALING.md
knowledge-product/science/03-STATE-MEMORY-WORLD-MODELS-AND-LEARNING.md
knowledge-product/science/04-TOOLS-AUTHORITY-CONTROL-AND-SYSTEM-COMPOSITION.md
knowledge-product/science/05-ASSURANCE-IDENTITY-PRIVACY-INTERPRETABILITY-AND-PROVENANCE.md
```

## PROTOS active Epoch 002 research

```text
_mw/epochs/002-capability-architecture-and-evolution/research/01-first-ideas/results/
```

Особенно значимые для настоящей темы:

```text
PROTOS_Embedded_Cognitive_Systems_Host_Integration_2026-09-16.md
PROTOS_Persistent_Proactive_Cognitive_System_Operational_Physiology_2026-09-15.md
PROTOS_Cognitive_Operating_Environment_Architecture_Infrastructure_and_Computational_Economy_2026-09-17.md
PROTOS_Adaptive_Cognitive_Execution_Physiology_2026-09-23.md
PROTOS_Cognitive_World_Architecture_Ecology_2026-09-15.md
PROTOS_Semantic_Logical_Mandates_Orthogonal_Cognition_2026-09-16.md
PROTOS_From_Schemas_to_Semantic_Construct_Fabric_2026-09-16.md
PROTOS_Cognitive_Microexecution_Relation_Algebra_and_Compiled_Fast_Paths_2026-09-16.md
```

Важно: текущий Epoch 002 прямо маркирует эти Research Result как входные/исследовательские carriers. Они не использованы здесь как автоматически admitted Product truth.

## Strategy Box current-state research

```text
stratbox_base_study_current_state_2026-10-06.md
stratbox-windows_current_state_full_research_2026-10-06.md
AppDock — Базовое описание
```

---

# Appendix E. Final design rule

Если требуется одно правило, по которому можно проверять будущие изменения Strategy Box, оно такое:

> **Любая новая AI/PROTOS функция должна по возможности добавляться как новый consumer или adapter существующих Work, Operation, Job, Artifact, Authority и Execution contracts. Если для неё приходится создавать отдельную параллельную модель заданий, состояния, результатов, permissions или recovery — фундамент, вероятно, выбран неверно.**
