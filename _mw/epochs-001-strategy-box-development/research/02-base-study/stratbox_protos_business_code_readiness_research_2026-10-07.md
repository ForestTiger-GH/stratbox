# Strategy Box × PROTOS: требования к бизнес-коду для будущего распознавания и использования машинных когнитивных схем

**Дата:** 2026-10-07  
**Контур:** Strategy Box, вторая ветка исследований  
**Статус:** Research Result; архитектурное исследование и предложение, не изменение production-кода  
**Главный вопрос:** какие свойства должны иметь бизнес-операции, композиции и execution-контракты Strategy Box сегодня, чтобы будущий PROTOS мог распознать их как готовые, проверенные и повторно используемые когнитивные способности, безопасно включать их в Work и при необходимости возвращаться от скомпилированного пути к более общей cognition.

---

# 0. Executive conclusion

Белое пятно действительно существует, и оно находится **не в transport/API**.

Обычная схема:

```text
PROTOS
→ API
→ Strategy Box
```

слишком бедна. API отвечает в основном на вопрос:

> **как физически вызвать действие?**

Но будущему PROTOS нужно знать значительно больше:

```text
что это за способность;
какой смысл она реализует;
какой тип задачи закрывает;
когда применима;
какие semantic inputs ей нужны;
какой semantic outcome она создаёт;
какие факты и объекты она может изменить;
какие эффекты имеет;
какие версии данных и правил предполагает;
какие failure/unsupported/unknown states возможны;
можно ли её повторять;
можно ли исполнять параллельно;
можно ли остановить и возобновить;
какое evidence подтверждает её корректность;
где заканчивается область её применимости;
когда требуется deoptimization обратно к более общей cognition.
```

Поэтому правильная будущая интеграция имеет как минимум **четыре независимых канала**:

```text
1. DISCOVERY / SEMANTIC CHANNEL
   PROTOS узнаёт, какие способности существуют и что они означают.

2. RESOLUTION / COMPOSITION CHANNEL
   PROTOS понимает, когда capability применима и как она связана
   с другими capabilities / Scheme / типами данных.

3. EXECUTION CHANNEL
   Strategy Box application runtime реально исполняет выбранную
   Operation / Machine Scheme / ExecutionPlan.

4. OBSERVATION / EVIDENCE CHANNEL
   PROTOS получает Result, events, artifacts, failures,
   provenance, evidence и effect receipts.

5. LEARNING / ADMISSION CHANNEL — позднее
   PROTOS может предложить новую Scheme / fast path,
   но Strategy Box принимает её только через отдельный
   validation/admission lifecycle.
```

API, MCP, local Python call, IPC, HTTP, AppDock action surface — это лишь **возможные физические реализации третьего канала**. Они сами по себе не решают semantic compatibility.

Главный вывод исследования:

> **Strategy Box должен сегодня строить не “API для будущего PROTOS”, а каноническую машинно-читаемую модель собственных способностей. Будущий PROTOS-adapter должен проецировать эту модель в PROTOS Construct/Capability Fabric.**

То есть направление зависимости:

```text
Strategy Box canonical semantics
        ↓
neutral machine capability model
        ↓
derived PROTOS projection
        ↓
PROTOS resolver / cognitive runtime
```

а не:

```text
Strategy Box business code
        ↓
сразу PROTOS-specific API/objects
```

Это сохраняет независимость проектов и одновременно делает Strategy Box органически совместимым с PROTOS.

---

# 1. Что именно уточняет это исследование относительно предыдущих

Свежий `stratbox` research уже практически сформулировал сильную архитектуру:

```text
Mechanism
→ Building Block
→ Domain Service
→ Canonical Operation
→ Machine Scheme
→ ExecutionPlan
```

и прямо определил:

> `stratbox` стоит развивать как библиотеку типизированных машинных способностей, а повторяемые способы композиции этих способностей — как версионируемые Machine Schemes.

Это направление сохраняется.

Однако новый вопрос пользователя вскрывает более глубокую проблему:

> **Каким образом будущий PROTOS поймёт, что конкретный объект Strategy Box является уже готовой cognition, которую следует не изобретать заново, а найти, проверить на применимость и использовать?**

Ответ требует ещё одного различия:

```text
executable implementation
≠
machine-readable capability meaning
≠
runtime transport
```

Python-код сам по себе недостаточен.

API сам по себе недостаточен.

Даже `OperationSpec` с названием и JSON Schema недостаточен, если отсутствуют:

- applicability;
- validity envelope;
- effects;
- evidence;
- lifecycle/admission;
- failure semantics;
- relations;
- deoptimization.

Поэтому настоящий объект интеграции — **Semantic Capability Contract**, а execution API является лишь одним из его bindings.

---

# 2. Иерархия источников и уровень уверенности

## 2.1. Текущий PROTOS не имеет готового финального external capability ABI

Это принципиально важно.

На момент исследования текущий `ForestTiger-GH/PROTOS@main` находится на HEAD:

```text
3a10879625a4b5d1e9253bfe1b700229eac244a1
```

`knowledge-product/target-what/TARGET-WHAT.md` определяет PROTOS как training-ready AI-system architecture и является более сильной commitment surface, чем exploratory first-ideas research.

При этом документы Epoch 002:

- `PROTOS_From_Schemas_to_Semantic_Construct_Fabric_2026-09-16.md`;
- `PROTOS_Composable_Logical_Cognitive_Schemas_Architecture_2026-09-16.md`;
- `PROTOS_Cognitive_Microexecution_Relation_Algebra_and_Compiled_Fast_Paths_2026-09-16.md`;
- `PROTOS_Embedded_Cognitive_Systems_Host_Integration_2026-09-16.md`;
- `PROTOS_Cognitive_Operating_Environment_Architecture_Infrastructure_and_Computational_Economy_2026-09-17.md`;
- `PROTOS_Adaptive_Cognitive_Execution_Physiology_2026-09-23.md`;

являются research/development inputs, а не финальной спецификацией.

Следовательно, сегодня нельзя честно написать:

```text
PROTOS API v1 требует поля X/Y/Z
```

такого API ещё нет.

Можно, однако, достаточно уверенно вывести **compatibility requirements**, которые повторяются в maintained target и нескольких независимых исследовательских линиях.

## 2.2. Высоко уверенные требования из Target WHAT

Current Target WHAT прямо требует:

- solver-independent cognitive operations;
- heterogeneous solver bindings;
- bounded Capability Envelope;
- explicit Work lifecycle;
- durable state boundary;
- evidence boundary;
- Authority/effect boundary;
- explicit capability-change/admission lifecycle;
- resource/profile semantics;
- honest `unsupported/uncertain` states.

Особенно важная формула TARGET-WHAT:

> deterministic workflow/runtime, сохраняющий часть этих семантик, может быть **PROTOS-compatible infrastructure**, даже если сам по себе не является полным PROTOS.

Это фактически прямое архитектурное разрешение для Strategy Box.

## 2.3. Сильные recurring refinements из Epoch 002

Исследовательский корпус PROTOS неоднократно повторяет:

- stable identity/addressability;
- meaning ≠ owner ≠ applicability ≠ authority ≠ evidence;
- typed relations;
- three-valued applicability;
- resolved task-local configuration;
- cheapest suitable solver;
- compiled fast paths;
- guards;
- invalidation;
- deoptimization;
- explicit provenance;
- admission lifecycle;
- capability packages;
- host sovereignty;
- cognition через bounded integration boundary.

Именно эти свойства следует использовать как ориентир Strategy Box.

---

# 3. Главное уточнение: «когнитивная схема» не должна означать один огромный объект

Интуиция пользователя правильна:

> branching, retries, parallel steps, background jobs, resume и другие execution mechanics действительно могут входить в общую машинную реализацию ранее когнитивной работы.

Но если всё буквально положить в один `CognitiveScheme`, возникнет новая путаница.

PROTOS research уже сам движется от слишком крупной «схемы» к более тонкой архитектуре:

```text
semantic constructs
+
relations
+
task-local resolved configuration
+
compiler/projector
+
execution substrate
```

Для Strategy Box полезно аналогично разделить минимум пять объектов.

---

# 4. Пять объектов, которые должны существовать отдельно

## 4.1. Capability Definition

Отвечает:

> **что умеет система?**

Например:

```text
cbr.escrow.history.build
sors.restore
frg.cleanup.plan
```

Она описывает semantic contract операции.

Не содержит mutable runtime state.

---

## 4.2. Machine Scheme Definition

Отвечает:

> **каким проверенным повторно используемым способом несколько capabilities образуют более крупную способность?**

Например:

```text
cbr.escrow.update
```

Это compiled procedural knowledge.

Содержит:

- semantic goal;
- typed graph;
- conditions;
- dependencies;
- invariants;
- outcome contract;
- effect semantics;
- failure/deoptimization policy.

---

## 4.3. Activation Binding

Это новый важный объект, который полезно явно выделить.

Отвечает:

> **при каком событии и в каком контексте Scheme должна быть предложена или запущена?**

Например:

```text
manual launch
scheduled 07:00
source-change event
AppDock event
PROTOS decision
user request
peer delegation
```

Одна Scheme должна уметь использоваться:

```text
foreground
background
schedule
event
PROTOS
remote
```

без копирования определения.

Поэтому `background` — чаще **не свойство самой cognition**, а способ её активации.

---

## 4.4. ExecutionPlan

Отвечает:

> **как именно эта Scheme будет исполнена сейчас?**

Он уже содержит:

- exact capability versions;
- exact bindings;
- source snapshots;
- registry snapshots;
- branch resolution where possible;
- resource decisions;
- actual dependency graph;
- effect summary;
- authority gates;
- runtime guards.

Это аналог task-local compilation / resolved configuration.

---

## 4.5. Run / Activation State

Отвечает:

> **что сейчас происходит с конкретным исполнением?**

Здесь живут:

```text
QUEUED
RUNNING
WAITING
RETRYING
PAUSED
COMPLETED
FAILED
CANCELLED
UNKNOWN
```

а также:

- checkpoints;
- attempts;
- progress;
- runtime timestamps;
- worker/node;
- receipts;
- current step.

Scheme сама mutable state хранить не должна.

---

# 5. Где именно должны жить branching, retry, parallelism, background и resume

Это центральное уточнение текущего исследования.

| Механизм | Семантический слой | План | Runtime | Почему |
|---|---|---|---|---|
| Branching | **Да, если ветка меняет смысл/исход** | конкретизируется | исполняется | Condition должна быть inspectable |
| Retry | Operation объявляет retry safety | plan может выбрать policy | runtime делает attempts | Повторять можно только при известных effect/idempotency semantics |
| Parallel steps | Scheme объявляет независимость/зависимость | planner решает допустимую параллельность | scheduler размещает | Physical parallelism не должен менять semantics |
| Background | обычно нет | нет | через Activation Binding / scheduler | Та же Scheme должна работать foreground/background |
| Resume | Scheme/Operation объявляет recovery contract | plan pins revision/checkpoints | runtime восстанавливает | После pause нужен revalidation |
| Checkpoint | capability/scheme объявляет safe boundary | plan знает checkpoints | runtime сохраняет receipt/state | Нельзя resume из произвольного места |
| Timeout | иногда semantic deadline | plan/resource policy | runtime timer | SLA может быть смысловым, обычный timeout — механизм |
| Fallback | **Да** | plan materializes route | runtime follows | Это часть controlled deoptimization |
| Compensation | effect model | plan computes available compensation | runtime invokes | «rollback» внешнего мира нельзя выдумывать |
| Human approval | Authority/effect gate | gate включается в plan | runtime ждёт approval | Это не обычный branch |
| Trigger | Activation contract | создаёт новый plan | runtime dispatch | Не стоит вшивать schedule в Scheme |
| Loop | только отдельный stateful profile | explicit termination | runtime executes | Generic arbitrary loops разрушают static analyzability |

## 5.1. Branching

Правильная ветка:

```text
condition:
    predicate: source.snapshot.schema_version in supported_versions

true  → normal parse path
false → unsupported / fallback / general resolution
unknown → revalidate / escalate
```

Неправильно:

```python
if something:
    ...
else:
    ...
```

когда это единственное место, где зашита semantics.

PROTOS должен видеть **что именно определяет ветку**.

## 5.2. Retry

PROTOS не должен видеть просто:

```text
retryable = true
```

Недостаточно.

Нужно знать:

```text
failure class
idempotency scope
possible external effects
UNKNOWN outcome semantics
retry owner
revalidation requirement
```

Например:

```text
HTTP GET timeout
→ retry usually safe

remote write timeout after possible commit
→ outcome UNKNOWN
→ blind retry unsafe
→ reconcile first
```

Поэтому Strategy Box operation должна описать семантику повторения, а конкретный `3 retries / exponential backoff` может оставаться runtime policy.

## 5.3. Parallel steps

PROTOS должен понимать:

```text
A and B are semantically independent
```

а не:

```text
run A and B in two threads
```

Physical parallelism выбирает scheduler.

Operation/Scheme должна объявлять:

```text
safe_parallel
serialized_by(resource)
exclusive
destination_lock
ordered_dependency
```

Если две ветки могут независимо менять один объект, это уже не просто performance optimization.

## 5.4. Background execution

Очень важно:

```text
Scheme ≠ BackgroundProcess
```

Правильнее:

```text
Scheme
+
ActivationBinding(trigger = schedule/event/watch/manual/PROTOS)
→ Run
```

Так один `cbr.escrow.update` может:

- запускаться пользователем;
- запускаться по расписанию;
- запускаться source watcher;
- запускаться будущим PROTOS.

## 5.5. Resume

`resumable=True` тоже недостаточно.

Нужно определить:

```text
safe checkpoint boundaries
what state is durable
which inputs were pinned
which source/registry revisions were assumed
what requires revalidation
what makes the plan stale
whether restart continues same Plan or creates new revision
```

Правильный resume:

```text
load checkpoint
→ verify plan digest
→ revalidate source/registry/work revisions
→ continue
```

или:

```text
revalidation failed
→ mark old plan stale
→ replan
```

---

# 6. Самое важное: PROTOS не должен «понимать Python»

Будущий PROTOS не должен:

- читать исходники;
- анализировать названия функций;
- строить смысл из docstring;
- сканировать imports;
- угадывать effects;
- infer retryability из exceptions;
- infer Authority из человеческого description.

Он должен получать отдельную machine-readable semantic surface.

Именно это является настоящим requirement к бизнес-коду.

Формула:

```text
business implementation
        │
        ├─ canonical semantic definition
        │
        ├─ admitted executable binding
        │
        └─ evidence/provenance
```

PROTOS использует первые и третьи элементы для reasoning, а второй — для исполнения.

---

# 7. Canonical Capability Model: что должен знать PROTOS о каждой существенной Operation

## 7.1. Identity

**MUST**

```text
semantic_id
contract_version
semantic_type
domain
lifecycle_status
```

Отдельно:

```text
implementation_id
implementation_revision
```

Нужно различать:

```text
что это за capability
и
какая конкретная реализация сейчас её исполняет.
```

---

## 7.2. Meaning / intent

**MUST**

Машина должна уметь понять:

```text
какой semantic outcome создаёт capability;
какую предметную задачу она решает;
какой object/subject scope обслуживает.
```

Human description полезен, но одного текста мало.

Нужны structured tags/types.

---

## 7.3. Typed inputs

**MUST**

Не:

```text
dict
DataFrame
path
object
```

как единственная граница.

А:

```text
SourceSnapshot[CbrEscrowWorkbook]
RegistrySnapshot[CbrBanks]
Dataset[EscrowCanonicalHistory]
Period
BankId
ArtifactRef
```

Физическая Python-репрезентация может оставаться DataFrame/dataclass.

PROTOS должен видеть semantic types.

---

## 7.4. Typed outputs

**MUST**

Output type нужен для:

- capability search;
- type-first planning;
- composition;
- validation;
- artifact interpretation.

Пример:

```text
produces:
    Dataset[EscrowCanonicalHistory]
    Artifact[Workbook]
```

---

## 7.5. Applicability

**MUST**

Applicability не должна быть обычным `bool`.

Целевой результат:

```text
APPLICABLE
NOT_APPLICABLE
UNKNOWN
```

Нужно выразить:

- domain scope;
- supported source families;
- supported schema versions;
- required registries;
- period constraints;
- environment requirements;
- profile/policy constraints.

`UNKNOWN` заставляет PROTOS собирать дополнительные данные или эскалировать.

---

## 7.6. Preconditions

**MUST where material**

Например:

```text
source.validated == true
registry.version >= X
artifact.exists == true
plan.baseline_revision == current_revision
```

Precondition — не скрытая проверка глубоко в handler.

---

## 7.7. Effects

**MUST**

PROTOS должен различать:

```text
READ
COMPUTE
NETWORK_READ
CACHE_WRITE
ARTIFACT_CREATE
ARTIFACT_REPLACE
WORKSPACE_MUTATION
EXTERNAL_WRITE
DESTRUCTIVE
```

Effects важны для planning и Authority.

---

## 7.8. Frame conditions

**SHOULD, MUST для effectful/high-consequence capability**

Нужно уметь сказать:

```text
что capability имеет право менять
и
что она обязана сохранить.
```

Это очень сильная идея из PROTOS schema research.

Например:

```text
may_create: Artifact
may_update: CacheEntry
must_not_change: admitted RegistrySnapshot
```

---

## 7.9. Postconditions / invariants

**MUST where material**

Пример:

```text
output schema valid
row uniqueness holds
totals reconcile
artifact hash recorded
source lineage complete
```

Run заканчивается успешно не потому, что Python вернул значение, а потому, что outcome contract выполнен.

---

## 7.10. Failure semantics

**MUST**

Минимум:

```text
UNSUPPORTED
UNAVAILABLE
INVALID_INPUT
SOURCE_UNAVAILABLE
TIMEOUT
CONFLICT
STALE
POLICY_DENIED
RESOURCE_EXHAUSTED
VERIFICATION_FAILED
PARTIAL
CANCELLED
UNKNOWN
INTERNAL_FAILURE
```

И structured fields:

```text
code
category
stage
retry_semantics
safe_message
structured_context
```

---

## 7.11. Determinism

**MUST**

PROTOS должен знать:

```text
deterministic
deterministic_given_snapshots
solver-dependent
stochastic
externally_nondeterministic
```

Это влияет на:

- retries;
- caching;
- verification;
- confidence;
- reproducibility.

---

## 7.12. Idempotency

**MUST for effectful/retriable operations**

Именно scope, а не boolean:

```text
idempotent for same SourceSnapshot + Request
idempotent only with same destination key
non-idempotent external effect
unknown
```

---

## 7.13. Concurrency

**MUST**

```text
safe_parallel
serialized_by(resource_ref)
exclusive
destination_locked
unknown
```

Это необходимо и PROTOS, и обычному JobManager.

---

## 7.14. Cancellation

**MUST for long-running capability**

Нужно определить:

- cancellable;
- safe cancellation points;
- effect outcome if cancel races with external side effect;
- whether partial artifacts remain valid.

---

## 7.15. Recovery / resumability

**SHOULD; MUST для долгих Scheme**

```text
not_resumable
restart_from_beginning
resume_from_checkpoint
resume_requires_revalidation
```

---

## 7.16. Resources

**SHOULD**

PROTOS target прямо требует resource/profile semantics.

Полезно объявлять:

```text
network
disk
cpu
memory
solver
secrets
exclusive resource
estimated latency class
estimated cost class
```

Не как setup recipe, а как capability requirement.

---

## 7.17. Artifacts

**MUST when material output exists**

Возвращать stable identity:

```text
ArtifactRef
DatasetRef
SourceSnapshotRef
RegistrySnapshotRef
```

Path — только materialization detail.

---

## 7.18. Provenance

**MUST**

Material output должен связывать:

```text
capability id/version
implementation revision
semantic inputs
source snapshots
registry versions
request fingerprint
plan digest
artifacts
warnings
verification evidence
```

---

## 7.19. Evidence / Capability Envelope

Это один из наиболее важных дополнительных выводов данного исследования.

`OperationSpec` говорит:

> **что capability обещает.**

Но PROTOS Target WHAT требует bounded Capability Envelope:

> **на каком основании системе разумно полагаться на capability в конкретной области.**

Поэтому нужен отдельный evidence-bearing слой или derived projection:

```text
CapabilityEnvelope
    supported input classes
    supported schema/source versions
    known unsupported regions
    tested profiles
    assurance level
    evidence refs
    quality/performance evidence
    last validated revision
    invalidation triggers
```

PROTOS должен выбирать solver не только потому, что metadata говорит «я умею», но и потому, что есть evidence.

---

# 8. Требования к Machine Scheme

Operation — atomic semantic capability.

Machine Scheme — повторно используемая композиция.

## 8.1. Stable identity

**MUST**

```text
scheme_id
version
content_digest
lifecycle_status
```

Run pins exact Scheme version.

---

## 8.2. Semantic task signature

**MUST**

Нужно выразить:

```text
intent
subject type
required inputs
desired output
material constraints
```

Это позволяет PROTOS сопоставлять Work и готовую Scheme.

---

## 8.3. Typed graph

**MUST**

Node:

```text
Operation invocation
или
nested Scheme invocation
```

Edge:

```text
typed dependency
```

Начальный Scheme IR лучше держать маленьким:

```text
invoke
map
collect
condition
gate
```

Не превращать DSL во второй Python.

---

## 8.4. Relations

**SHOULD**

PROTOS research показывает важность typed relations:

```text
requires
precedes
produces
consumes
conflicts_with
specializes
compiled_as
deprecated_by
tested_by
valid_under_assumption
```

Strategy Box не обязан реализовать весь PROTOS relation vocabulary.

Но machine capability model должен позволять постепенно добавлять типизированные отношения.

---

## 8.5. Applicability and validity envelope

**MUST**

Scheme должна знать:

```text
где она применима;
какие assumptions делает;
какие версии допустимы;
что её инвалидирует.
```

---

## 8.6. Effects derivable before execution

**MUST**

Из definition должна быть возможность вывести:

```text
какие effects потенциально возникнут.
```

Это позволяет PROTOS заранее решить, допустимо ли вообще строить этот plan.

---

## 8.7. Outcome contract

**MUST**

Scheme не считается успешной только потому, что все nodes завершились.

Нужно определить:

```text
что является полезным semantic outcome;
какие postconditions должны выполняться;
какой partial outcome допустим.
```

---

## 8.8. Failure / fallback policy

**MUST**

Нужно различать:

```text
fail-fast
continue-with-partial
fallback capability
defer
ask human
deopt to general resolution
```

---

## 8.9. Deoptimization route

**MUST для compiled cognitive path**

Это одно из ключевых PROTOS requirements.

Каждый fast path должен иметь:

```text
guard
validity envelope
invalidation trigger
fallback/deoptimization route
```

Без этого compiled cognition превращается в мёртвую автоматизацию, которая продолжает уверенно работать после изменения мира.

---

# 9. Future PROTOS recognition: как ИИ поймёт «это готовая схема»

Пусть пользователь просит:

```text
"обнови историю счетов эскроу"
```

Будущий правильный flow:

```text
1. PROTOS формирует Task Signature
   intent = update_escrow_history

2. Resolver делает hierarchical capability discovery

   Domain: CBR / escrow
       ↓
   high-level Scheme candidates
       ↓
   cbr.escrow.update@3

3. PROTOS инспектирует Scheme descriptor

   inputs
   outputs
   applicability
   validity
   effects
   evidence
   resource class
   status=ADMITTED

4. Applicability resolver проверяет:

   source family supported
   registry compatible
   Authority sufficient
   required resources available

5. Если готовая Scheme покрывает intent,
   PROTOS НЕ создаёт новый plan с нуля.

6. Strategy Box semantic planner instantiates Scheme:

   pins operation versions
   pins snapshots
   type-checks ports
   derives effects
   validates plan

7. Application runtime исполняет Plan.

8. PROTOS получает:

   Result
   artifacts
   events
   provenance
   evidence

9. Если guard Scheme нарушен:

   DEOPT
       ↓
   более общая Scheme
       ↓
   dynamic PROTOS reasoning
```

Вот что в практическом смысле означает:

> **«PROTOS понимает, что это готовая когнитивная схема».**

Он не понимает её за счёт чтения Python.

Он понимает её через **адресуемый semantic contract + capability evidence + validity envelope + executable binding**.

---

# 10. API всё-таки нужен — но как execution binding

Пользовательская интуиция «через API и всё такое — мне кажется, это не совсем корректно» правильна.

Нужно различать:

```text
SEMANTIC CONTRACT
    what / when / effects / validity / evidence

DISCOVERY INDEX
    how to find

EXECUTION BINDING
    how to invoke

TRANSPORT
    how bytes/messages physically cross boundary
```

Они независимы.

Одна Operation может иметь несколько bindings:

```text
Python local binding
AppDock action binding
IPC binding
HTTP binding
MCP tool projection
remote node binding
```

PROTOS reasoning не должен зависеть от конкретного transport.

---

# 11. Правильная архитектура будущего стыка PROTOS ↔ Strategy Box

```text
┌──────────────────────────────────────────────────────────┐
│ PROTOS                                                  │
│                                                          │
│ Task Signature                                          │
│ Construct / Capability Resolver                         │
│ Solver Selection                                        │
│ Work / Evidence / Learning                              │
└───────────────┬──────────────────────────────────────────┘
                │
                │ derived cognitive projection
                ▼
┌──────────────────────────────────────────────────────────┐
│ PROTOS ↔ Strategy Box Adapter                           │
│                                                          │
│ Strategy Box types → PROTOS constructs                  │
│ Capability Envelope → solver evidence                   │
│ Effects → Authority model                               │
│ Result/Provenance → observation/evidence                │
└───────────────┬──────────────────────────────────────────┘
                │
                │ neutral Strategy Box machine semantics
                ▼
┌──────────────────────────────────────────────────────────┐
│ Strategy Box Canonical Capability Model                 │
│                                                          │
│ OperationSpec                                           │
│ SchemeSpec                                              │
│ ActivationSpec                                          │
│ CapabilityEnvelope                                      │
│ Type/Schema Registry                                    │
│ Capability Registry                                     │
└───────────────┬──────────────────────────────────────────┘
                │
                │ resolved invocation
                ▼
┌──────────────────────────────────────────────────────────┐
│ Strategy Box application runtime                       │
│                                                          │
│ ExecutionPlan → Job/Run → Events → Result               │
│ cancellation / retry / resume / scheduler               │
└───────────────┬──────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────┐
│ stratbox implementation                                 │
│ parsers / calculations / SORS / exporters / adapters    │
└──────────────────────────────────────────────────────────┘
```

Ключевой момент:

> **PROTOS-specific mapping находится в adapter, а canonical semantics Strategy Box остаётся нейтральной.**

---

# 12. Provisional mapping Strategy Box → PROTOS

Это не финальная спецификация PROTOS, а наиболее естественная текущая проекция.

| Strategy Box | Возможная роль в PROTOS |
|---|---|
| `OperationSpec` | semantic capability / solver-addressable operation |
| `OperationBinding` | concrete solver/backend binding |
| `SchemeSpec` | compiled cognitive recipe / reusable work capability |
| `CapabilityEnvelope` | evidence-backed capability envelope |
| `ActivationSpec` | trigger/activation policy |
| `ExecutionPlan` | task-local resolved/compiled execution configuration |
| `Run` | physical activation/execution instance |
| `Result` | observation/candidate result |
| `ArtifactRef` | durable external artifact reference |
| `Provenance` | evidence/provenance input |
| `Failure` | bounded failure/unsupported state |
| `EffectReceipt` | external effect/reconciliation evidence |

Очень важно: mapping не обязан быть 1:1.

Одна Scheme Strategy Box может проецироваться в несколько PROTOS constructs.

И наоборот, PROTOS может собрать Work из нескольких Strategy Box Schemes.

---

# 13. Важное архитектурное требование: semantic source of truth должен быть внутри Strategy Box

Не стоит делать:

```text
stratbox code
+
отдельный PROTOS manifest,
который вручную дублирует смысл
```

Так появятся две истины.

Лучше:

```text
canonical OperationSpec / SchemeSpec
        ↓ derived
docs
UI forms
MCP
PROTOS projection
search index
tests
```

То есть AI-facing представление должно **генерироваться/проецироваться** из того же canonical capability contract, который используют Windows/Android/runtime/tests.

---

# 14. Static analyzability — одно из главных свойств PROTOS-readiness

Будущий PROTOS должен уметь понять capability **до запуска**.

Следовательно, важны:

- immutable specs;
- no arbitrary eval;
- no hidden code blocks;
- typed ports;
- explicit effects;
- explicit dependencies;
- bounded condition language;
- canonical serialization;
- content digest;
- no hidden mutable globals;
- version pinning.

Если смысл capability становится известен только после исполнения Python, cognition уже не может безопасно планировать.

---

# 15. No hidden state

Особенно опасны:

```text
global current_period
global active_registry
global current_workspace
global mutable cache affecting semantics
global selected_bank
global retry counter
```

Run-specific state должен жить:

```text
Invocation
ExecutionPlan
Run
ExecutionContext
```

Definition — immutable.

Это одновременно даёт:

- thread safety;
- concurrent PROTOS activations;
- reproducibility;
- remote execution;
- testability.

---

# 16. Versioning: четыре версии, которые нельзя смешивать

## 16.1. Semantic Contract Version

Изменился смысл Operation/Scheme.

## 16.2. Implementation Revision

Bugfix/optimization без изменения contract.

## 16.3. Dependency/Snapshot Versions

Sources, registries, schemas, models.

## 16.4. Plan Digest

Конкретно разрешённая композиция одного Run.

PROTOS должен иметь возможность узнать:

```text
same semantic capability
but different implementation
```

и:

```text
same Scheme version
but different source snapshot
```

---

# 17. Admission lifecycle: как PROTOS понимает, что Scheme можно доверять

Нельзя считать любую зарегистрированную функцию готовой cognition.

Полезный lifecycle:

```text
DRAFT
VALIDATING
TESTED
ADMITTED
DEPRECATED
REVOKED
```

PROTOS planner по умолчанию должен использовать:

```text
ADMITTED
```

а experimental capability — только при явной политике.

Для generated Scheme:

```text
dynamic PROTOS plan
→ repeated success
→ SchemeCandidate
→ schema validation
→ type checking
→ effect analysis
→ tests/evals
→ evidence
→ admission
→ discoverable capability
```

Это и есть переход:

```text
reasoning
→ procedural memory
→ compiled machine cognition
```

---

# 18. Tests должны становиться evidence для capability

Обычный unit test сегодня отвечает:

> код работает?

Для PROTOS readiness тесты дополнительно могут подтверждать:

```text
какие входы поддержаны;
какие границы известны;
какие invariants сохраняются;
какие profiles прошли;
какие performance/resource limits измерены.
```

Из этого можно строить `CapabilityEnvelope`.

Именно поэтому PROTOS Target WHAT говорит о evidence-backed capability, а не только о self-declared feature.

---

# 19. Hierarchical discovery

Нельзя отдавать PROTOS 5 000 helper-функций.

Правильное discovery:

```text
Domain summary
    ↓
high-level admitted Schemes
    ↓
selected Scheme details
    ↓
Operations
    ↓
lower-level capabilities only if required
```

Это снижает:

- search noise;
- context cost;
- routing errors;
- accidental low-level effects.

---

# 20. AI visibility — отдельное измерение

Не каждая Operation должна быть видна cognition.

Например:

```text
hidden
planner
standard
expert
```

или другой небольшой vocabulary.

Важно:

```text
discoverable capability
≠ automatically authorized capability
```

Visibility регулирует discovery.

Authority регулирует execution.

---

# 21. Authority нельзя выводить из descriptions

Плохая модель:

```text
description:
  "Deletes obsolete files"

LLM:
  "звучит подходяще"
→ execute
```

Правильная модель:

```text
effect_class = destructive.workspace.delete
required_authority = ...
precondition = PlanRef + fresh baseline
```

PROTOS может предложить действие.

Strategy Box/AppDock policy решает, разрешено ли его выполнять.

---

# 22. Validity envelope: главное свойство compiled cognition

Compiled Scheme — это не вечная истина.

Она корректна в некотором envelope:

```text
source schemas
registry versions
input classes
policy versions
environment capabilities
known assumptions
validated profiles
```

Пример:

```text
cbr.escrow.update@3
valid if:
    source_family = CBR_ESCROW_MONTHLY
    workbook_schema in [2019_v2, 2022_v1, 2025_v1]
    cbr_region_registry >= 2026.06
    network capability available
```

Если появился новый workbook schema:

```text
NOT_APPLICABLE / UNKNOWN
→ deopt
→ general resolver
```

Именно это превращает автоматизацию в безопасный cognitive fast path.

---

# 23. Compiled cognitive lineage

Нужно уметь хранить:

```text
Scheme D
compiled_from:
    Scheme A@2
    Operation B@5
    PROTOS Work W
    evidence set E
```

Это важно по двум причинам:

1. будущий PROTOS может объяснить происхождение capability;
2. при invalidation можно понять, какие более общие конструкции доступны для deopt.

---

# 24. Capability deficit: когда PROTOS должен писать новый код

Порядок должен быть:

```text
1. Найти готовую Scheme.
2. Если нет — скомпоновать existing Operations.
3. Если repeated pattern стабилен — создать Scheme.
4. Только если отсутствует необходимая primitive capability —
   синтезировать новый code candidate.
```

Не:

```text
каждая новая задача
→ сгенерировать Python
```

Это крайне важный принцип вычислительной и инженерной экономии.

---

# 25. Illustrative Strategy Box Machine Scheme Contract

Ниже — **не финальный формат**, а иллюстрация того, какой смысл должен быть доступен машине.

```yaml
kind: machine_scheme

identity:
  id: cbr.escrow.update
  version: 3
  status: admitted
  digest: sha256:...

semantic:
  intent: update_canonical_escrow_history
  domain: cbr.escrow

  inputs:
    - type: PeriodRange
    - type: SourcePolicy

  outputs:
    - type: Dataset[EscrowCanonicalHistory]
    - type: Artifact[EscrowWorkbook]

  applicability:
    source_family: CBR_ESCROW_MONTHLY
    unknown_policy: escalate

  invariants:
    - canonical_schema_valid
    - source_lineage_complete
    - indicator_identity_preserved

effects:
  classes:
    - network.read
    - cache.write
    - artifact.create
  authority:
    artifact.create: normal

execution_semantics:
  determinism: deterministic_given_snapshots
  idempotency:
    scope: same_request_and_source_snapshots

  concurrency:
    mode: safe_parallel
    lock: artifact_destination

  cancellation:
    supported: true
    safe_points: [after_fetch, after_parse, before_commit]

  recovery:
    resumable: true
    checkpoint_boundaries: [sources_resolved, parsed, validated]
    resume_requires_revalidation: true

graph:
  - invoke: cbr.escrow.sources.resolve
  - map:
      operation: source.fetch
      over: sources
  - map:
      operation: cbr.escrow.parse
      over: snapshots
  - invoke: cbr.escrow.history.combine
  - invoke: cbr.escrow.history.validate
  - invoke: cbr.escrow.export

validity:
  supported_source_schemas:
    - 2019_v2
    - 2022_v1
    - 2025_v1
  invalidation:
    - source_schema_unknown
    - region_registry_breaking_change
    - validation_contract_changed
  fallback:
    route: general_resolution

evidence:
  conformance_tests:
    - ...
  regression_suite:
    - ...
  capability_envelope_ref: ...

provenance:
  derived_from: ...
```

PROTOS должен уметь понять этот объект без чтения handler implementation.

---

# 26. Activation Binding: отдельный пример

```yaml
activation:
  id: cbr.escrow.daily-refresh
  target: cbr.escrow.update@3

  trigger:
    kind: schedule
    schedule: "07:00"

  bindings:
    period_range: latest_available

  policy:
    if_no_change: suppress_run
    max_frequency: daily
    on_failure: notify
```

Будущий PROTOS может создать другой activation:

```yaml
trigger:
  kind: cognitive_decision
  work_ref: ...
```

Scheme остаётся той же.

Это один из наиболее важных способов сохранить границу между cognition и runtime.

---

# 27. Resume и Work continuity: не путать procedural memory с episodic state

Пользователь прав, что resume является частью общей «умной» способности.

Но физически:

```text
Scheme
```

описывает **как можно продолжать**.

А:

```text
Run state / checkpoint / Work state
```

хранит **где мы сейчас находимся**.

Это аналогично:

```text
процедура
≠
конкретное состояние исполнения процедуры.
```

PROTOS later может иметь procedural memory и episodic Work state как разные классы.

Strategy Box стоит сохранить такое же разделение уже сейчас.

---

# 28. Что должно быть в `stratbox`, а что в application runtime

## `stratbox` / core

Должен владеть:

- domain Operations;
- OperationSpec;
- semantic types;
- input/output schemas;
- effects;
- applicability;
- domain invariants;
- domain failure codes;
- idempotency semantics;
- concurrency constraints where domain-owned;
- cancellation safe points where domain-owned;
- SchemeSpec;
- Scheme graph;
- capability lifecycle definition;
- source/registry semantics;
- artifacts/provenance contracts;
- capability evidence.

## application/runtime layer

Должен владеть:

- queue;
- job placement;
- workers;
- actual parallel scheduling;
- retry attempts;
- backoff;
- timers;
- background schedules;
- actual checkpoint persistence;
- resume orchestration;
- user approval state;
- local/remote backend;
- runtime resource allocation;
- crash recovery;
- notifications.

## будущий PROTOS

Должен владеть:

- Task Signature;
- cognitive Work;
- semantic resolution;
- choosing existing Scheme;
- dynamic composition;
- solver selection;
- cognitive resource allocation;
- uncertainty;
- deoptimization upward;
- learning/candidate skill creation.

---

# 29. Новый полезный объект: Capability Envelope

Существующие Strategy Box research уже близки к нему, но этот объект стоит выделить концептуально.

```text
CapabilityDefinition:
    what it claims

CapabilityEnvelope:
    where evidence supports reliance

CapabilityBinding:
    how it is executed
```

Это очень хорошо совпадает с PROTOS Target WHAT.

Пример:

```yaml
capability_envelope:
  capability: sors.restore@5

  validated_for:
    source_schema: [...]
    regions: all_official
    metrics: [...]
    optimization_modes: [...]

  known_unsupported:
    - malformed_nonofficial_snapshot
    - unresolved_registry_mapping

  evidence:
    unit_tests: ...
    integration_snapshots: ...
    property_tests: ...
    performance_gates: ...

  validated_implementation:
    revision: ...

  invalidates_on:
    - semantic_contract_change
    - solver_major_change
    - registry_break
```

PROTOS получает возможность выбирать SORS как специализированный solver на evidence, а не по красивому description.

---

# 30. Conformance levels Strategy Box → future PROTOS

Полезно ввести исследовательскую шкалу.

## Level 0 — Callable

```text
можно вызвать функцию
```

Недостаточно.

## Level 1 — Typed Operation

Есть:

- stable ID;
- Request/Result;
- schemas;
- failures;
- effects.

PROTOS может безопасно invoke.

## Level 2 — Discoverable Capability

Есть:

- applicability;
- semantic types;
- lifecycle;
- AI visibility;
- provenance;
- Capability Envelope.

PROTOS может самостоятельно найти и выбрать.

## Level 3 — Composable Capability

Есть:

- typed relations;
- explicit pre/postconditions;
- concurrency/recovery semantics;
- static analyzability.

PROTOS может строить динамический Plan.

## Level 4 — Machine Scheme

Есть:

- declarative composition;
- outcome contract;
- effect derivation;
- version pinning;
- tests;
- validity/deoptimization.

PROTOS может предпочесть готовую procedural cognition динамическому reasoning.

## Level 5 — Compilable / Evolvable

Есть:

- lineage;
- admission lifecycle;
- SchemeCandidate path;
- invalidation;
- evidence refresh;
- compile-down/deopt-up.

PROTOS может учиться и создавать новые capabilities без скрытого self-modification.

---

# 31. PROTOS-readiness requirements: MUST / SHOULD / MAY

## MUST

1. Stable semantic identity.
2. Exact contract version.
3. Semantic input/output types.
4. Serializable machine schema for public capability boundary.
5. Applicability with `UNKNOWN`.
6. Explicit effects.
7. Explicit outcome/failure semantics.
8. Distinction semantic contract / implementation binding.
9. Exact implementation revision in provenance.
10. Determinism class.
11. Idempotency semantics where retry/effects matter.
12. Concurrency semantics.
13. Cancellation semantics for long operations.
14. Artifact identity beyond path.
15. Source/registry/version provenance.
16. Immutable capability/scheme definition.
17. No hidden mutable global semantic state.
18. Capability lifecycle/admission status.
19. Validity envelope.
20. Invalidation trigger.
21. Fallback/deoptimization for compiled fast path.
22. Capability discoverability without reading Python.
23. Tests/evidence for admitted capabilities.
24. Strategy Box standalone execution without PROTOS.

## SHOULD

1. Resource/cost/latency class.
2. Capability Envelope as first-class projection.
3. Typed relations between capabilities.
4. Hierarchical discovery.
5. AI visibility profile.
6. Canonical serialization + content digest.
7. Checkpoint/resume contract for long Scheme.
8. Effect receipts.
9. Frame conditions.
10. Outcome verification contract.
11. Generated docs from canonical contracts.
12. Conformance linting.
13. Property-based tests for invariants.
14. Type-first planner compatibility.
15. Static effect/resource derivation for Scheme.

## MAY / later

1. MCP projection.
2. HTTP/IPC transport.
3. CEL-like predicate language.
4. CloudEvents projection.
5. PROTOS-specific adapter.
6. Dynamic Scheme generation.
7. Automatic compile-down.
8. Remote federation.
9. Learned small-model bindings.

---

# 32. Что не нужно делать сейчас

## 32.1. Не создавать `protos/` внутри `stratbox`

Это преждевременная зависимость.

## 32.2. Не копировать PROTOS Construct IR в Strategy Box

PROTOS ещё исследуется.

Strategy Box должен иметь нейтральную canonical semantic model.

## 32.3. Не делать PROTOS manifest вторым source of truth

Projection должна быть derived.

## 32.4. Не отдавать AI helper functions

PROTOS должен видеть curated canonical capabilities.

## 32.5. Не делать Scheme DSL Turing-complete

Сложность остаётся в Operations.

## 32.6. Не кодировать scheduler policy как domain semantics

Queue/backoff/worker placement — application runtime.

## 32.7. Не привязывать Scheme к foreground/background

Это activation mode.

## 32.8. Не считать `resume=True` достаточной recovery semantics

Нужны checkpoints + revision revalidation.

## 32.9. Не считать `retryable=True` достаточной retry semantics

Нужны idempotency/effects/UNKNOWN.

## 32.10. Не считать successful return достаточным semantic success

Нужен outcome contract.

---

# 33. Где текущий Strategy Box уже очень близок

Судя по свежим исследованиям `stratbox`:

- typed Request/Result direction уже доказала ценность;
- canonical operations признаны главным следующим шагом;
- sources/snapshots/freshness исследованы;
- registries рассматриваются как versioned knowledge;
- artifacts/provenance развиваются как first-class layer;
- SORS уже содержит сильный evidence/provenance model;
- Machine Scheme research уже определяет OperationSpec/SchemeSpec/ExecutionPlan;
- current research уже выделяет effects, idempotency, concurrency, cancellation, validity, deoptimization;
- current PROTOS foundation research уже требует capability discovery.

То есть новый фундамент изобретать с нуля не требуется.

Нужно **свести эти идеи в один формальный compatibility contract**.

---

# 34. Где остаётся реальный gap

После анализа свежих материалов gap выглядит так:

## Gap A — нет одного canonical semantic capability model

Идеи есть в нескольких research-файлах.

Нужен единый принятый target для:

```text
OperationSpec
SchemeSpec
CapabilityEnvelope
ActivationSpec
ExecutionPlan
Result/Failure/Artifact/Provenance
```

## Gap B — capability evidence пока не оформлено как отдельный слой

PROTOS требует evidence-backed Capability Envelope.

Strategy Box уже имеет tests/provenance, но нужен единый способ связать их с capability reliance.

## Gap C — activation semantics недостаточно отделены от Scheme

Особенно для:

- background;
- schedule;
- event;
- PROTOS activation.

## Gap D — нужно жёстко разделить semantic retry/concurrency/recovery и runtime policy

Иначе Machine Scheme станет job engine.

## Gap E — нет formal derived cognitive projection

Нужен будущий adapter:

```text
Strategy Box capability model
→ PROTOS capability/construct package
```

Но сам adapter следует делать **после стабилизации внутреннего contract**.

---

# 35. Рекомендуемая целевая модель пакетов

Не как окончательное дерево, а как ownership map:

```text
stratbox/
│
├─ capabilities/
│   ├─ contracts.py
│   ├─ operation.py
│   ├─ scheme.py
│   ├─ lifecycle.py
│   ├─ effects.py
│   ├─ policies.py
│   ├─ envelope.py
│   └─ registry.py
│
├─ schemas/
│   └─ semantic type / schema registry
│
├─ provenance/
│
├─ artifacts/
│
├─ sources/
├─ registries/
├─ domains/
│   └─ ...
│
└─ execution/
    └─ deterministic semantic planner
       (без durable queue/job server)
```

Application layer:

```text
Strategy Box application/
│
├─ jobs/
├─ runs/
├─ activation/
├─ scheduling/
├─ persistence/
├─ approvals/
└─ execution_backends/
```

PROTOS adapter позднее:

```text
protos-strategy-box adapter
or equivalent external integration package
```

---

# 36. Приоритетный roadmap

## P0 — сделать сейчас

### 1. Canonical Operation Contract

Принять один `OperationSpec`.

### 2. Semantic types

Убрать path/DataFrame/dict как единственную machine boundary.

### 3. Result / Failure / Artifact / Provenance

Свести общие envelopes.

### 4. Effect / idempotency / concurrency / cancellation semantics

Чтобы operations были реально composable.

### 5. Capability Registry

Curated, explicit, hierarchical.

### 6. First Machine Scheme IR

Минимально:

```text
invoke
map
collect
condition
gate
```

### 7. Validity / deoptimization fields

Сразу, а не позже.

### 8. Capability lifecycle

DRAFT → TESTED → ADMITTED → ...

---

## P1 — сразу после первого Scheme pilot

### 9. Capability Envelope

Связать spec с tests/evidence.

### 10. ExecutionPlan

Exact versions/snapshots/effects/resources.

### 11. ActivationSpec

Manual/event/schedule/cognitive decision.

### 12. Resume/checkpoint contract

На одной реально долгой Scheme.

### 13. Contract linting

Проверять:

- missing effects;
- missing versions;
- dangling capability refs;
- untyped ports;
- missing failure policy;
- no validity envelope.

---

## P2 — когда PROTOS материализуется

### 14. PROTOS adapter

Derived projection из canonical Strategy Box contracts.

### 15. Cognitive discovery

Domain → Scheme → Operation.

### 16. Task Signature → Scheme resolution

### 17. Generated SchemeCandidate

### 18. Admission/eval/deopt loop

---

# 37. Практический acceptance test для любого нового бизнес-кода

Для каждой существенной бизнес-способности Strategy Box спросить:

```text
1. Есть ли stable semantic ID?
2. Может ли машина понять цель без чтения Python?
3. Ясны ли semantic inputs?
4. Ясен ли semantic output?
5. Ясна ли applicability?
6. Есть ли UNKNOWN?
7. Ясны ли effects?
8. Ясны ли pre/postconditions?
9. Ясна ли failure semantics?
10. Известна ли retry safety?
11. Известна ли concurrency semantics?
12. Известна ли cancellation semantics?
13. Известно ли, как recovery/resume работает?
14. Есть ли provenance?
15. Есть ли evidence?
16. Есть ли validity envelope?
17. Есть ли invalidation trigger?
18. Есть ли fallback/deoptimization?
19. Есть ли lifecycle/admission status?
20. Можно ли capability найти без import scan?
21. Можно ли её исполнить без PROTOS?
22. Можно ли заменить implementation без изменения semantic ID?
```

Если большинство ответов «нет», способность ещё не PROTOS-ready.

---

# 38. Самое важное уточнение исходной формулировки пользователя

Пользовательская формула:

> «ветвления, retries, parallel steps, background jobs и resume — часть когнитивной схемы PROTOS»

может быть сохранена, если уточнить уровень:

> **Они являются частью общей машинной реализации когнитивной способности, но не обязаны принадлежать одному semantic Scheme object.**

Правильная декомпозиция:

```text
Cognitive capability meaning
        ↓
Machine Scheme
        ↓
Activation policy
        ↓
Resolved ExecutionPlan
        ↓
Runtime scheduling/retry/resume
```

С точки зрения пользователя или PROTOS это может восприниматься как одна готовая способность.

С точки зрения архитектуры эти уровни должны оставаться различимыми.

Именно это позволит будущему PROTOS менять:

- solver;
- placement;
- parallelism;
- trigger;
- retry policy;

не меняя смысл Scheme.

---

# 39. Финальный ответ на вопрос «как конкретно пристыковать PROTOS»

Не одним API.

Правильный future handshake:

```text
A. Strategy Box публикует machine-readable capability index.

B. PROTOS discovery находит admitted Scheme.

C. PROTOS загружает semantic descriptor +
   Capability Envelope.

D. Resolver проверяет applicability, evidence,
   Authority, resource envelope и validity.

E. Strategy Box semantic planner превращает Scheme
   в immutable ExecutionPlan с exact versions.

F. PROTOS или пользователь запрашивает execution.

G. Strategy Box application runtime запускает Run
   через local/remote backend.

H. PROTOS наблюдает typed events и получает
   structured Result / Artifact / Provenance / Receipts.

I. Если validity guard нарушен, Strategy Box возвращает
   typed deopt/unsupported state.

J. PROTOS возвращается к более общей cognition.

K. Если новый dynamic path становится повторяемым,
   PROTOS может предложить SchemeCandidate,
   который проходит Strategy Box admission.
```

Только шаг F может быть «API вызовом».

Настоящая интеграция — это вся цепочка.

---

# 40. Главный design rule

Если свести исследование к одному правилу:

> **Каждая существенная повторно используемая бизнес-способность Strategy Box должна иметь независимый от реализации, версионируемый, типизированный и проверяемый machine-semantic contract, достаточно богатый, чтобы будущий cognitive resolver мог найти capability, доказать её применимость, понять эффекты и ограничения, выбрать её вместо нового reasoning и безопасно deopt-нуться обратно при нарушении validity envelope.**

И второе правило:

> **PROTOS adapter должен быть проекцией этой semantic surface, а не местом, где смысл бизнес-кода описывается заново.**

---

# 41. Итоговый вердикт

Да, обеспокоенность пользователя полностью обоснована, но решение уже хорошо просматривается.

Strategy Box не должен сегодня строить PROTOS runtime.

Однако Strategy Box должен строить бизнес-код **так, как если бы каждая зрелая способность в будущем могла стать элементом внешней cognitive fabric**.

Это означает:

```text
business code
≠ opaque Python
```

а:

```text
semantic capability
+
typed contract
+
evidence-backed envelope
+
admitted executable binding
+
validity/deoptimization
```

Тогда будущий PROTOS сможет воспринимать Strategy Box не как набор tools, который надо каждый раз заново интерпретировать, а как **библиотеку уже скомпилированной domain cognition**.

В самом кратком виде:

> **API делает capability вызываемой. Semantic Capability Contract делает capability понятной. Capability Envelope делает её заслуживающей доверия. Validity/Deoptimization делает её безопасной для повторного использования.**

Вот эти четыре свойства и являются настоящей PROTOS-readiness Strategy Box.

---

# Appendix A. Что из свежих исследований уже можно считать базой

## `stratbox_business_logic_machine_schemes_architecture_research_2026-10-07.md`

Уже сформулированы:

- OperationSpec;
- SchemeSpec;
- Machine Scheme;
- ExecutionPlan;
- Capability Registry;
- typed ports;
- effects;
- determinism;
- idempotency;
- freshness;
- concurrency;
- cancellation;
- failures;
- assurance;
- capability lifecycle;
- deoptimization;
- PROTOS-facing discovery.

Это основной непосредственный predecessor настоящего исследования.

## `stratbox_protos_foundation_research_2026-10-07.md`

Уже сформулированы:

- Host–Cognition Contract;
- CognitivePort;
- capability discovery;
- Work/Job foundation;
- bounded context;
- structured proposal;
- revision/freshness fences;
- PROTOS as replaceable cognitive participant.

Настоящее исследование уточняет именно machine-cognition side этой границы.

## `stratbox_base_study_current_state_2026-10-06.md`

Показывает текущую неоднородность доменов и необходимость canonical Operations.

## `stratbox-windows_current_state_full_research_2026-10-06.md`

Показывает текущие Scenario/Operation/Case/Artifact/Event abstractions и будущую потребность в JobManager, cancellation, retry/resume и frontend-neutral orchestration.

---

# Appendix B. PROTOS sources

## Higher-authority current target

`ForestTiger-GH/PROTOS@3a10879625a4b5d1e9253bfe1b700229eac244a1`

- `knowledge-product/target-what/TARGET-WHAT.md`

Материальные положения:

- solver-independent cognitive operations;
- heterogeneous solver bindings;
- evidence-backed Capability Envelope;
- durable Work state;
- evidence boundary;
- Authority/effect boundary;
- capability-change/admission lifecycle;
- resource/profile semantics;
- deterministic workflow/runtime может быть PROTOS-compatible infrastructure.

## Exploratory / Development Inputs

- `PROTOS_From_Schemas_to_Semantic_Construct_Fabric_2026-09-16.md`
- `PROTOS_Composable_Logical_Cognitive_Schemas_Architecture_2026-09-16.md`
- `PROTOS_Cognitive_Microexecution_Relation_Algebra_and_Compiled_Fast_Paths_2026-09-16.md`
- `PROTOS_Embedded_Cognitive_Systems_Host_Integration_2026-09-16.md`
- `PROTOS_Cognitive_Operating_Environment_Architecture_Infrastructure_and_Computational_Economy_2026-09-17.md`
- `PROTOS_Adaptive_Cognitive_Execution_Physiology_2026-09-23.md`

Ключевые recurring ideas:

- meaning / applicability / authority / evidence are separate;
- typed relations;
- task-local resolved configuration;
- capability packages;
- compiled recipes;
- guards;
- validity envelope;
- deoptimization;
- admission;
- host sovereignty;
- developer-provided capability package through contracts rather than internal knowledge of PROTOS.

---

# Appendix C. Самая короткая модель

```text
PROTOS wants:

"What can you do?"
    → Capability Registry

"What does it mean?"
    → Semantic Contract

"When may I rely on it?"
    → Capability Envelope

"When may I use it?"
    → Applicability + Authority

"How do I combine it?"
    → Types + Relations + Scheme

"What exactly will run?"
    → ExecutionPlan

"How do I start it?"
    → Execution Binding

"What happened?"
    → Result + Events + Artifacts

"Why should I trust the result?"
    → Evidence + Provenance

"When must I stop using this shortcut?"
    → Validity + Invalidation

"What if the world changed?"
    → Deoptimization / Replan / General Cognition
```
