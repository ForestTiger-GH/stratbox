# Strategy Box: архитектура бизнес-логики `stratbox` как машинных когнитивных схем

**Дата:** 2026-10-07  
**Контур:** Strategy Box, вторая ветка исследований  
**Предмет:** организация бизнес-кода `stratbox`, машинные контракты операций и схем, входы/выходы, состояния, реестры, источники, файлы, артефакты и пригодность для будущего PROTOS  
**Статус:** Research Result; целевая архитектурная гипотеза, а не утверждение о уже реализованном состоянии

---

# 0. Краткий вывод

Главный вывод исследования:

> **`stratbox` стоит развивать не как каталог Python-функций и не как набор “AI-tools”, а как библиотеку типизированных машинных способностей. Повторяемые способы композиции этих способностей образуют версионируемые Machine Schemes. PROTOS должен уметь читать их семантику, выбирать, комбинировать и исполнять, не зная внутренностей Python-кода.**

При этом исходную формулировку «весь бизнес-код — это когнитивные схемы» полезно немного исправить. Внутри `stratbox` существуют разные классы сущностей:

```text
Mechanism
    FileStore / HTTP / XLSX / DBF / ZIP / solver
        ↓
Building Block
    parse / normalize / validate / hash / transform
        ↓
Domain Service
    discover sources / parse domain file / select latest / build model
        ↓
Canonical Operation
    самостоятельная управляемая машинная способность
        ↓
Machine Scheme
    повторно используемая композиция Operations / Schemes
        ↓
ExecutionPlan
    конкретный разрешённый и зафиксированный граф исполнения
```

Для будущей когнитивной системы наиболее важны:

```text
Capability Catalog
Operation Contract
Scheme Contract
Typed Data / Knowledge Contracts
```

PROTOS должен видеть:

```text
что система умеет;
что capability принимает;
что возвращает;
когда применима;
что читает и изменяет;
какая свежесть нужна;
можно ли повторять, кэшировать, параллелить;
какие ошибки и частичные результаты возможны;
какое evidence/provenance возникает.
```

PROTOS **не должен** для обычной работы знать:

```text
имя Python-функции;
структуру pandas-кода;
как физически работает FileStore;
какой HTTP client используется;
как устроен XLSX parser;
какой backend хранит байты.
```

Самая точная итоговая формула:

> **Machine Scheme в Strategy Box — это admitted, versioned, typed, inspectable и effect-bounded компиляция повторяемого способа достижения семантического результата.**

---

# 1. Есть ли готовый стандарт «когнитивной AI-схемы»

## 1.1. Единого стандарта нет

На 2026 год нет общепринятого стандарта, который определял бы один универсальный объект `CognitiveScheme` и одновременно охватывал:

- semantic intent;
- типы данных;
- planning;
- workflow/dataflow;
- состояние и переходы;
- внешние эффекты;
- доказательность;
- Authority;
- provenance;
- capability discovery;
- обучение и компиляцию cognition.

Это совпадает и с текущими исследованиями PROTOS: слово «схема» скрывает несколько разных слоёв — онтологию, эпистемику, нормы, операции, control и физическое исполнение. Попытка сделать один гигантский DSL почти неизбежно создаст либо слишком бедную, либо чрезмерно сложную систему.

Правильнее использовать **несколько зрелых формализмов как источники идей**, а внутри `stratbox` определить небольшой собственный Scheme IR.

---

# 2. Какие стандарты и формализмы реально полезны

## 2.1. JSON Schema 2020-12

Полезен для:

- сериализуемых входов и выходов;
- runtime validation;
- reusable sub-schemas;
- schema identity;
- conditional structural constraints;
- генерации machine-readable contracts.

Для Strategy Box это лучший кандидат на **control-plane type system**.

Использование:

```text
Operation Request
Operation Result projection
Scheme inputs/outputs
Artifact metadata
Source/Registry refs
```

Не использовать JSON Schema как workflow language.

---

## 2.2. Model Context Protocol Tools

MCP даёт очень удачный внешний precedent AI-facing capability:

```text
name
description
inputSchema
outputSchema
annotations
structured result
```

Это почти то, что будущему PROTOS понадобится от `stratbox` на границе discovery/invocation.

Но MCP должен быть **проекцией** внутренних contracts:

```text
OperationSpec
→ MCP Tool
```

а не внутренней моделью `stratbox`.

Причины:

- MCP — внешний interoperability protocol;
- внутренние semantics Strategy Box богаче;
- не все операции должны быть доступны AI;
- одна и та же capability нужна Python/Jupyter/Windows/Android/remote consumers без MCP.

---

## 2.3. Common Workflow Language

CWL полезен как сильный precedent:

> typed dataflow workflow, где шаги имеют inputs/outputs, соединяются портами и могут исполняться на разных физических execution substrates.

Особенно полезные идеи:

- typed ports;
- explicit step inputs/outputs;
- workflow graph;
- portable execution;
- conditional steps;
- разделение workflow definition и конкретного runtime.

Для `stratbox` это один из лучших аналогов **Machine Scheme как typed DAG**.

Не стоит копировать:

- command-line/container orientation;
- весь формат и runtime CWL;
- assumptions, специфичные для научных batch pipelines.

---

## 2.4. BPMN

BPMN полезен концептуально:

- activity;
- event;
- gateway;
- parallel branches;
- human task;
- message interaction;
- compensation.

Он показывает, что process semantics значительно шире линейной последовательности функций.

Но полный BPMN для `stratbox` избыточен:

- слишком тяжёл;
- ориентирован на enterprise business-process modelling;
- XML-модель велика;
- для аналитических data pipelines большинство semantics не требуется.

Брать концепты, а не runtime.

---

## 2.5. DMN

DMN особенно полезен для:

```text
decision tables
structured deterministic business rules
```

Если некоторый `if/elif`-лес превращается в таблицу решений, это хороший сигнал вынести rule layer в data.

Например:

```text
source type × period × freshness × status
→ processing policy
```

Но полный DMN stack Strategy Box не нужен.

---

## 2.6. SCXML / statecharts

SCXML полезен там, где Scheme действительно представляет **жизненный цикл**, а не dataflow:

```text
WAITING_AUTH
→ READY
→ RUNNING
→ WAITING_EXTERNAL
→ RECONCILING
→ DONE
```

Подходит для:

- protocol-like interaction;
- resumable external effect;
- credential/auth flow;
- stateful long-lived domain objects.

Не подходит как базовая форма для обычного:

```text
fetch → parse → normalize → validate → calculate
```

Для такого процесса DAG проще.

---

## 2.7. PDDL / HDDL

PDDL/HDDL дают важный planner-oriented precedent:

```text
action
preconditions
effects
goal

hierarchical task
method
subtasks
```

Это интеллектуально близко будущему PROTOS:

```text
desired outcome
+
available capabilities
+
current state
→ plan
```

Особенно ценны:

- applicability;
- preconditions;
- effects;
- hierarchical decomposition.

Но PDDL/HDDL слабо подходят для:

- tabular datasets;
- artifacts;
- files;
- provenance;
- крупного dataflow.

Поэтому эти идеи стоит перенести в metadata Operations/Schemes, а не делать PDDL основным форматом.

---

## 2.8. CEL

Common Expression Language — интересный кандидат для ограниченных predicates:

```text
validation.error_count == 0
source.age_hours < 24
artifact.kind == "dataset"
```

Ключевое достоинство: expression language можно сделать bounded/non-Turing-complete и не давать generated Scheme произвольный Python `eval()`.

Для первого этапа можно обойтись named predicates. CEL-like syntax имеет смысл, когда появится реальный спрос.

---

## 2.9. W3C PROV

PROV полезен как reference model:

```text
Entity
Activity
Agent
```

Для Strategy Box это естественно маппится:

```text
Artifact / SourceSnapshot / Dataset
    → Entity

Run / Operation Invocation
    → Activity

Actor / implementation/provider
    → Agent
```

Внутри продукта необязательно использовать RDF/OWL. Важна сама provenance geometry.

---

## 2.10. CloudEvents

CloudEvents полезен как future transport envelope для distributed events.

Он не определяет workflow или domain semantics, зато показывает хороший минимум portable event metadata:

```text
id
source
type
subject
time
data
```

Это может пригодиться при AppDock/remote/multi-node execution.

---

# 3. Итог по стандартам

Ни один внешний формат не стоит брать целиком.

Целевая модель:

> **Stratbox Scheme IR — небольшой внутренний versioned формат, заимствующий typed schemas из JSON Schema, dataflow из CWL, preconditions/effects из planning systems, ограниченные guards из CEL-подобных языков, state-machine semantics только там, где они действительно нужны, а provenance — из W3C PROV-подобной модели.**

Это даст стандартизацию без архитектурной зависимости от одного внешнего стандарта.

---

# 4. Что такое Machine Scheme в `stratbox`

Machine Scheme — не Python-функция.

Она описывает:

```text
identity
purpose
semantic inputs
semantic outputs
applicability
graph/decomposition
invariants
effects
resources
failure policy
outcome contract
version
provenance
```

Физическая реализация может меняться.

Например:

```text
Scheme:
    cbr.escrow.update
```

может сегодня раскрываться в пять Python Operations, позже — в оптимизированный compiled Operation, а ещё позже — частично выполняться remote. Семантический смысл остаётся.

---

# 5. Четыре объекта, которые нельзя смешивать

## 5.1. Definition

```text
SchemeSpec
OperationSpec
```

Определяет capability.

---

## 5.2. Invocation

```text
OperationInvocation
SchemeInvocation
```

Конкретное применение с параметрами.

---

## 5.3. ExecutionPlan

Полностью разрешённый граф исполнения:

- exact versions;
- exact inputs;
- resolved snapshots;
- dependencies;
- resources;
- destinations;
- policy gates.

---

## 5.4. Run

Фактическое выполнение Plan.

Run lifecycle должен принадлежать application runtime, а не бизнес-core.

---

# 6. Рекомендуемая иерархия бизнес-кода

## L0 — Mechanism

Примеры:

```text
FileStore
HTTP transport
openpyxl
dbfread
ZIP
hashing
numerical solver
```

Это физические механизмы.

Они не должны автоматически попадать в PROTOS catalog.

---

## L1 — Building Block

Примеры:

```text
read_xlsx
parse_date
normalize_bank_name
transcode_dbf
calculate_hash
validate_columns
```

Маленькие reusable transformations.

Не каждый building block имеет смысл регистрировать глобально.

---

## L2 — Domain Service

Примеры:

```text
discover_escrow_sources
parse_escrow_workbook
select_latest_frg_files
build_sors_constraints
```

Уже содержит предметную семантику.

Некоторые Domain Services со временем могут стать machine-visible Operation, если доказана самостоятельная ценность.

---

## L3 — Canonical Operation

Главная управляемая machine capability.

Примеры:

```text
cbr.files.collect
cbr.escrow.history.build
cbr.escrow.workbook.export
cbr.industries.debt.stream.build
frg.cleanup.plan
frg.cleanup.apply
sors.restore
```

Operation имеет стабильный semantic contract.

---

## L4 — Machine Scheme

Повторяемая композиция Operations и/или других Schemes:

```text
cbr.escrow.update
frg.intake.normalize
bank_registry.refresh
monthly.banksector.refresh
```

Scheme — procedural knowledge.

---

## L5 — ExecutionPlan

Конкретный immutable execution artifact.

Plan уже знает:

```text
scheme version
operation versions
source snapshots
registry snapshots
artifact destinations
resolved parameters
guards
parallel branches
dedup
```

---

# 7. Главная граница: semantic capability ≠ implementation

Сегодня может существовать:

```python
stratbox.macrobanks.escrow.operations.build_escrow_history
```

Но PROTOS должен видеть:

```text
cbr.escrow.history.build@1
```

Это разные identity.

Целевая relation:

```text
OperationSpec
    ↓ binding
Python implementation
```

Позже bindings могут быть:

```text
local_python
remote
optimized_native
generated_and_admitted
```

Без изменения semantic Operation, если contracts действительно эквивалентны.

---

# 8. Candidate OperationSpec

Условная форма:

```yaml
id: cbr.escrow.history.build
version: 1
kind: operation

title: Построить историю счетов эскроу
domain: macrobanks.cbr.escrow

inputs:
  schema_ref: schema://stratbox/cbr/escrow/history-build-request@1

outputs:
  schema_ref: schema://stratbox/cbr/escrow/history-result@1

semantics:
  determinism: environment_bound

effects:
  - network_read
  - cache_write

resources:
  - network:cbr
  - storage:cache

freshness:
  caller_selectable: true

concurrency:
  mode: parallel_safe
  keys:
    - source:cbr.escrow

idempotency:
  scope: same_inputs_and_snapshots

cancellation:
  mode: cooperative

provenance:
  required: true

ai:
  visibility: standard
```

Имена полей пока не надо считать финальными. Важны различия смыслов.

---

# 9. Какие dimensions обязательны

## 9.1. Identity

```text
id
version
kind
```

---

## 9.2. Intent

```text
purpose
description
domain
semantic tags
```

Это нужно человеку и PROTOS.

---

## 9.3. Inputs

```text
schema
required/optional
semantic types
constraints
refs
```

---

## 9.4. Outputs

```text
schema
dataset/artifact types
evidence
```

---

## 9.5. Preconditions / applicability

```text
required capability
required source
required registry
state condition
supported input family
```

---

## 9.6. Effects

Минимальный vocabulary:

```text
PURE
READ
NETWORK_READ
CACHE_WRITE
ARTIFACT_CREATE
WORKSPACE_WRITE
EXTERNAL_WRITE
DESTRUCTIVE
```

---

## 9.7. Determinism

```text
deterministic
input_deterministic
environment_bound
probabilistic
```

---

## 9.8. Idempotency

Не `bool`.

Нужно scope:

```text
always
same_snapshot
same_destination
within_execution
never
```

---

## 9.9. Freshness

```text
allow_cached
prefer_fresh
require_fresh
require_snapshot
max_age
```

---

## 9.10. Concurrency

```text
parallel_safe
serialize_by_source
serialize_by_destination
exclusive_resource
```

---

## 9.11. Cancellation

```text
immediate
cooperative
safe_point
not_cancellable
```

---

## 9.12. Failure model

Typed error codes.

---

## 9.13. Assurance

```text
validation requirements
evidence
known unsupported regions
```

---

# 10. Почему текущий `stratbox` уже близок к этой модели

Несколько доменов уже независимо пришли к полезным patterns.

## `cbr_file_collector`

Имеет:

```text
CbrFileCollectRequest
CbrFileCollectResult
CbrFileCollectFailure
```

Это хороший простой прототип machine Operation.

---

## `escrow`

Разделяет стадии:

```text
HistoryBuildRequest
ViewBuildRequest
WorkbookExportRequest

HistoryResult
PivotPack
ExportResult
```

Это уже почти capability chain.

---

## `cbr_industries`

Особенно зрелый пример:

```text
Download Request/Result
Parsed File
Validation Issue
Stream Request/Result
Calculation Result
Pivot Request/Result
Workbook Request/Result
```

Такой домен очень хорошо показывает, что **машинные состояния лучше выражать типизированными контрактами, а не одним giant dict**.

---

## SORS

SORS сохраняет:

- source manifest;
- validation;
- constraints;
- solver runs;
- conflicts;
- derivations;
- audit.

Это важный пример: общий `OperationResult` не должен уничтожать богатство доменного evidence.

---

## FRG

FRG показывает сильный pattern:

```text
plan
→ inspect
→ apply
```

Для будущего AI это особенно важно.

---

# 11. Что пока мешает считать эти contracts полноценным Machine ABI

Основные gaps:

1. Contract style отличается между domains.
2. Нет общего `OperationSpec`.
3. Нет общего Capability Registry.
4. Не все boundary objects сериализуемы.
5. DataFrames встроены непосредственно в Result.
6. Path часто используется как identity результата.
7. Effects не объявляются формально.
8. Версии Operation/Schema не закреплены.
9. Freshness/idempotency/concurrency semantics локальны.
10. Environment-specific execution switches местами протекают в domain Request.
11. Нет общего machine discovery.
12. `latest` иногда разрешается скрыто во время выполнения.

---

# 12. Control plane и data plane

Это фундаментальное разделение.

## Control plane

Маленькие сериализуемые объекты:

```text
Request
ResultEnvelope
ArtifactRef
DatasetRef
SourceSnapshotRef
RegistrySnapshotRef
Failure
Diagnostic
ProvenanceRef
```

Оптимальный wire representation — JSON-compatible data + JSON Schema.

---

## Data plane

Крупные payloads:

```text
Parquet
Arrow
XLSX
CSV
ZIP
raw source bytes
```

Они передаются/хранятся отдельно.

---

# 13. DataFrame: оставить внутри Python, убрать из единственной внешней границы

`pd.DataFrame` удобен и его не надо искусственно выгонять из core.

Нужны две surfaces.

## Python-native

```python
result.df_stream
```

Отлично подходит Jupyter/Colab/plain Python.

## Machine/remote

```json
{
  "dataset_ref": "artifact://...",
  "rows": 123456,
  "schema_ref": "schema://...",
  "source_snapshot_refs": [...]
}
```

Используется:

- application runtime;
- PROTOS;
- remote execution;
- Android;
- persistence;
- MCP.

---

# 14. Pydantic vs dataclass

Текущие dataclasses хороши.

Но machine boundary требует:

- validation;
- serialization;
- JSON Schema;
- discriminated unions;
- strict typing.

Поэтому **Pydantic v2 является сильным кандидатом** для control-plane public contracts.

Рекомендуемая граница:

```text
Pydantic/equivalent
    contracts

pandas/numpy/Arrow
    computation and bulk data
```

Это recommendation, а не обязательная норма.

---

# 15. Machine Scheme как typed DAG

Для большинства аналитических задач default topology:

```text
source.resolve
      ↓
source.fetch
      ↓
parse
      ↓
normalize
      ↓
validate
      ↓
calculate
      ↓
artifact.write
```

Это dataflow graph, а не state machine.

---

# 16. Typed ports

Scheme nodes должны соединяться через явные outputs/inputs.

```yaml
nodes:
  - id: fetch
    use: source.fetch@2
    in:
      source: $inputs.source_ref

  - id: parse
    use: cbr.escrow.parse@1
    in:
      snapshot: $nodes.fetch.snapshot

  - id: validate
    use: cbr.escrow.validate@1
    in:
      dataset: $nodes.parse.dataset
```

Преимущества:

- static type checking;
- partial rerun;
- caching;
- parallelism;
- lineage;
- easier planning;
- reproducibility.

---

# 17. Не использовать global mutable context dict

Плохая модель:

```python
context["x"] = ...
context["y"] = ...
```

Где каждый step читает и пишет произвольные ключи.

Это разрушает:

- static analysis;
- parallelism;
- reproducibility;
- safe generation;
- type checking.

Лучше explicit ports и refs.

---

# 18. Edge types

Нужно минимум:

```text
data dependency
control dependency
conditional dependency
failure route
compensation relation
```

Для первого IR можно начать только с data/control, а остальные добавить по реальному спросу.

---

# 19. Parallelism должен следовать из графа

Если:

```text
B depends on A
C depends on A
D depends on B,C
```

planner автоматически получает:

```text
A
↓
B || C
↓
D
```

Не надо размечать каждую ветвь ручным `parallel=true`.

---

# 20. Map / foreach

Для обработки многих источников нужен bounded construct:

```text
sources[]
→ map fetch
→ map parse
→ collect
```

Это особенно естественно для статистических публикаций.

---

# 21. Fan-in должен быть типизирован

Варианты:

```text
collect
concat
union
join
all_success
first_success
best_by_verifier
```

Нельзя оставлять merge semantics скрытым внутри prompt.

---

# 22. Conditions

Arbitrary Python `eval()` в Scheme запрещать.

Первый этап:

```text
named predicates
```

Позже, если потребуется:

```text
CEL-like bounded expression
```

Это даст analyzability и безопасность.

---

# 23. State machines — только где действительно есть состояние

Нужно различать:

```text
Scheme definition
Run execution state
Domain object lifecycle
```

Они не одно и то же.

Обычный analytics pipeline — DAG.

State machine полезна для:

- long-lived protocol;
- approval/auth;
- external effect reconciliation;
- resumable domain lifecycle.

---

# 24. Preconditions и effects

Это один из важнейших AI-facing слоёв.

Operation должна сообщать:

```text
requires
produces
changes
```

Например:

```yaml
requires:
  - source_snapshot.kind == cbr.escrow.xlsx

produces:
  - dataset.kind == cbr.escrow.history

effects:
  - artifact_create
```

Но preconditions не должны повторять всю реализацию parser-а.

Они задают **границу применимости**.

---

# 25. Postconditions / invariants

Особенно важны:

```text
rows > 0
no duplicate semantic key
all dates normalized
validation.error_count == 0
artifact hash exists
```

Их можно проверять:

- runtime;
- tests;
- generated-code admission.

---

# 26. Capability Envelope

Для каждой существенной Operation полезно знать:

```text
supported inputs
known schema versions
tested periods
known unsupported cases
resource class
reliability evidence
```

Это PROTOS-friendly представление способности.

---

# 27. Applicability не должна быть только bool

Хороший outcome:

```text
APPLICABLE
NOT_APPLICABLE
UNKNOWN
```

`UNKNOWN` означает, что нужно получить дополнительные данные.

---

# 28. Plan / Apply как общая pattern для effects

FRG уже демонстрирует правильную идею.

Вместо:

```python
run_cleanup(..., execute=False)
run_cleanup(..., execute=True)
```

цель:

```text
frg.cleanup.plan(...)
→ CleanupPlan

frg.cleanup.apply(plan_ref)
→ CleanupExecutionResult
```

`apply`:

- не принимает заново все исходные решения;
- revalidates preconditions;
- выполняет заранее определённые effects;
- выдаёт receipts.

Это намного сильнее для AI, approvals и audit.

---

# 29. Почему отдельный PlanRef важен

Между planning и apply может пройти время.

Plan фиксирует:

```text
что именно будет изменено
какие исходные revisions использованы
какие destinations
какие preconditions
```

Перед apply:

```text
VALID
STALE
CONFLICT
```

---

# 30. Общий Result Envelope

Не заменяет domain result.

Обёртка:

```yaml
outcome: succeeded | partial | failed | unsupported | no_change

payload:
  schema_ref: ...
  value_or_ref: ...

artifacts: []
diagnostics: []
failures: []
provenance: ...
metrics: ...
```

---

# 31. `ok: bool` слишком слаб

Нужны различия:

```text
SUCCEEDED
PARTIAL
FAILED
UNSUPPORTED
NO_CHANGE
ABSTAIN / UNKNOWN — где применимо
```

Плюс domain-specific status.

---

# 32. Typed Failure

```yaml
code: source.timeout
category: transient
stage: fetch
retryable: true
message: ...
details: ...
```

Тогда PROTOS может машинно решить:

```text
retry
switch source
defer
ask user
abort
```

---

# 33. Exceptions остаются для bugs/API misuse

Ожидаемые operational failures лучше превращать в typed result на public boundary.

Programmer errors и сломанные invariants могут оставаться exceptions.

---

# 34. Provenance

Любой material output должен связывать:

```text
capability id/version
implementation identity
semantic inputs
input refs
source snapshots
registry snapshots
configuration
environment identity where material
time
```

Это основа:

- reproducibility;
- cache;
- audit;
- AI confidence;
- debugging.

---

# 35. Registry — перегруженный термин

В `stratbox` нужно формально развести минимум четыре класса.

### Reference Registry

```text
banks
OKVED2
geography
```

Это structured knowledge.

### Source Catalog

```text
where/how to obtain official data
```

### Capability Registry

```text
Operations
Schemes
```

Его читает PROTOS.

### Format Registry

```text
DBF
XLSX
ZIP
CSV
```

и available parsers/transcoders.

---

# 36. Никакого MegaRegistry

Объединять можно интерфейс discovery/versioning.

Физическое содержание и ownership разное.

---

# 37. RegistrySnapshot

Текущий hidden выбор «самого свежего файла по mtime» не годится как воспроизводимый machine input.

Цель:

```yaml
registry_id: cbr.banks
snapshot_id: sha256:...
effective_date: 2026-09-01
retrieved_at: ...
source_ref: ...
schema_version: 2
content_hash: ...
```

---

# 38. `latest` должен разрешаться до запуска

Пользователь/PROTOS может сказать:

```text
latest bank registry
```

Planner делает:

```text
latest
→ exact RegistrySnapshotRef
```

Run получает уже pinned ref.

---

# 39. SourceDescriptor ≠ SourceSnapshot

```text
SourceDescriptor
    как и где получать

SourceSnapshot
    что фактически было получено
```

Это два разных knowledge objects.

---

# 40. Hardcoded source lists

Текущий `DEFAULT_CBR_FILE_SOURCES` является полезным ранним source catalog.

Целевой объект должен дополнительно иметь:

```text
source kind
authority
format
discovery/fetch strategy
validation profile
freshness semantics
```

---

# 41. FileStore остаётся правильным механизмом

Current `FileStore` хорошо абстрагирует:

```text
read/write
exists/stat/list
copy/rename/remove
walk/glob
```

Его не надо превращать в AI layer.

---

# 42. FileStore находится ниже cognitive capability layer

```text
Operation
↓
Artifact/Workspace service
↓
FileStore
↓
physical backend
```

---

# 43. PROTOS не должен видеть raw `remove(path)`

AI-facing capabilities должны быть curated:

```text
workspace.list
artifact.read
dataset.load
artifact.materialize
workspace.publish_artifact
```

а destructive filesystem semantics — только через governed operations.

---

# 44. Path не является artifact identity

Сегодня path часто удобен как output.

Машинная граница должна предпочитать:

```text
ArtifactRef
DatasetRef
SourceSnapshotRef
RegistrySnapshotRef
WorkspaceRef
```

Внутри implementation обычный `Path` остаётся нормальным.

---

# 45. ArtifactRef

Условно:

```yaml
artifact_id: art-...
kind: workbook
content_hash: sha256:...
media_type: application/vnd...
schema_ref: ...
storage_ref: ...
```

---

# 46. Форматы данных

Рекомендуемая роль:

```text
JSON/JSON Schema
    control plane

Arrow/Parquet
    canonical tabular machine data / transport

pandas
    in-process analytics

XLSX
    human-facing artifact

CSV
    simple interchange

ZIP
    bundle/transport
```

---

# 47. Semantic dataset schema

Machine schema должна знать больше, чем `column -> dtype`.

Полезные поля:

```text
column
physical type
semantic role
unit
dimension
key role
code system
nullability
time semantics
```

---

# 48. Units являются частью смысла

Число:

```text
123
```

без unit мало полезно cognition.

Нужно уметь выразить:

```text
RUB
million RUB
percent
count
persons
contracts
```

---

# 49. Semantic types

Постепенно можно ввести lightweight types:

```text
BankRegNumber
IndustryCode[OKVED2]
RegionCode
ReportingDate
Money[RUB]
Percentage
Count
```

Это metadata/type registry, а не обязательная сложная Python type system.

---

# 50. Type compatibility

Planner должен знать:

```text
exact match
compatible subtype
conversion available
incompatible
```

Conversion должна быть explicit capability.

---


# 51. Пример Machine Scheme: обновление escrow

Условный serializable Scheme:

```yaml
scheme_id: cbr.escrow.update
version: 1

inputs:
  date_from:
    type: date
    required: false
  date_to:
    type: date
    required: false
  freshness:
    type: freshness_policy

nodes:
  discover:
    use: cbr.escrow.sources.resolve@1

  fetch:
    use: source.fetch@2
    map_over: $nodes.discover.sources

  parse:
    use: cbr.escrow.parse@1
    map_over: $nodes.fetch.snapshots

  combine:
    use: cbr.escrow.history.combine@1
    inputs:
      datasets: $nodes.parse.datasets

  validate:
    use: cbr.escrow.history.validate@1
    inputs:
      dataset: $nodes.combine.dataset

outputs:
  dataset: $nodes.validate.dataset

outcome:
  requires:
    - validation.error_count == 0
```

Обращает внимание несколько вещей:

1. Scheme не знает Python module.
2. Fetch и parse можно параллелить.
3. SourceSnapshot является explicit output.
4. Canonical dataset существует до XLSX.
5. Export можно добавить отдельной capability.
6. PROTOS может использовать dataset дальше без materialization в Excel.

---

# 52. Почему экспорт лучше отделять

Центральная distinction:

```text
canonical analytical result
≠
presentation artifact
```

Один canonical dataset может дальше использоваться:

```text
analysis
chart
comparison
new Scheme
XLSX
CSV
API
report
```

Поэтому pattern:

```text
build canonical data
→ validate
→ optionally render/export
```

лучше, чем функция, где единственным результатом является `.xlsx`.

---

# 53. Пример FRG как effectful Scheme

Read-only часть:

```text
workspace scan
→ classify file families
→ normalize periods
→ select latest
→ build CleanupPlan
```

И отдельная effectful часть:

```text
CleanupPlanRef
→ revalidate source files / hashes
→ approval/authority boundary
→ apply exact actions
→ EffectReceipts
```

Это почти идеальный пример того, как machine-readable Scheme становится безопаснее обычной функции.

---

# 54. Пример обновления reference registry

```text
RegistryDescriptor
→ resolve official source
→ fetch SourceSnapshot
→ validate source
→ normalize
→ construct candidate RegistrySnapshot
→ compare with admitted current snapshot
→ regression/invariant checks
→ admit
```

Это полноценная Scheme.

Сам registry при этом остаётся **knowledge object**, а не Scheme.

---

# 55. Три класса cognitive assets

Очень полезно закрепить следующую taxonomy.

## Knowledge

```text
RegistrySnapshot
SourceSnapshot
Dataset
reference data
```

Отвечает:

> Что известно / какие данные доступны?

## Capability

```text
Operation
Scheme
```

Отвечает:

> Что система умеет сделать?

## Artifact

```text
workbook
report
dataset artifact
validation package
```

Отвечает:

> Какой устойчивый объект возник в результате работы?

Эти три класса нельзя сворачивать в одну сущность.

---

# 56. Важная поправка к исходной идее о реестрах и файлах

Формулировка:

> «реестры, работа с файлами и т.п. должны быть оформлены как когнитивные схемы»

верна только частично.

Точнее:

```text
реестр
→ machine-addressable knowledge

FileStore
→ low-level mechanism

файловая операция
→ bounded capability

процедура использования реестров/файлов ради результата
→ Scheme
```

Например:

```text
cbr.banks RegistrySnapshot
    !=
registry.update Scheme
```

---

# 57. PROTOS использует Schemes как procedural memory

Удобная аналогия:

```text
semantic/declarative memory
    → registries, datasets, knowledge

procedural memory
    → Operations, Schemes

episodic memory
    → Work/Run history
```

Это только conceptual analogy. Не нужно переносить психологические термины в package names.

---

# 58. Что означает «Scheme встроена в ИИ»

Физически Scheme лучше **не прятать в веса LLM**.

Логически cognitive actor знает:

```text
что capability существует
как её найти
когда она применима
как вызвать
что она выдаёт
```

Сама Scheme может оставаться external explicit object.

Это лучше weights для:

- versioning;
- revocation;
- freshness;
- audit;
- updates;
- exact execution;
- testing.

---

# 59. Capability discovery должна быть hierarchical

Если PROTOS получает 5 000 low-level tools, качество routing и context ухудшается.

Нужен progressive discovery:

```text
Domain summaries
    ↓
high-level Schemes
    ↓
selected Scheme detail
    ↓
lower-level Operations if planner needs them
```

---

# 60. AI visibility

CapabilitySpec может иметь:

```text
hidden
planner
standard
expert
```

### hidden

Implementation mechanism:

```text
FileStore.open_write
```

### planner

Низкоуровневая capability:

```text
source.fetch
dataset.validate
```

### standard

Пользовательская/высокоуровневая Scheme:

```text
cbr.escrow.update
```

### expert

Специализированные возможности:

```text
sors.restore.strict
```

---

# 61. Capability namespace

Рекомендуемый naming:

```text
source.fetch
artifact.materialize
registry.resolve

cbr.files.collect
cbr.escrow.history.build
cbr.escrow.workbook.export

cbr.industries.debt.stream.build
cbr.industries.debt.pivot.build

frg.cleanup.plan
frg.cleanup.apply

sors.restore
```

Имя описывает semantics, а не implementation.

Плохо:

```text
run_script_3
parse_v2_new
load_excel_helper
```

---

# 62. Capability Registry

Capability Registry должен стать одним machine-readable источником истины для:

```text
Python/Jupyter
stratbox-windows
future Android
PROTOS
remote execution
MCP projection
tests
docs generation
```

Registry entry знает:

```text
id
version
kind
title
description
tags
input schema
output schema
effects
resources
applicability
available implementation bindings
AI visibility
```

---

# 63. Capability Registry ≠ Python import scan

Не стоит автоматически считать все public functions capabilities.

Registry должен быть **curated**.

Причина:

- helpers меняются чаще;
- слишком много tools;
- неясные effects;
- accidental public API;
- невозможно поддерживать semantics.

---

# 64. Explicit OperationBinding

Вместо import magic:

```python
ESCROW_HISTORY_BUILD = OperationBinding(
    spec=ESCROW_HISTORY_BUILD_SPEC,
    handler=build_escrow_history,
    implementation_id="python.stratbox.escrow.history.v1",
)
```

Registry собирается из явных bindings.

Это:

- прозрачно;
- тестируемо;
- исключает import-time registration surprises.

---

# 65. Одна semantic Operation — несколько bindings

Например:

```text
Operation:
    cbr.dataset.normalize@2

Bindings:
    python.default
    python.optimized
    remote.host
```

Resolver может выбрать подходящий implementation.

Semantic version остаётся одной, если output/effects contract действительно эквивалентен.

---

# 66. Conformance tests между bindings

Для каждого binding:

```text
same semantic request
→ contract-equivalent result
```

Не обязательно byte-identical output, если semantics допускает различия.

---

# 67. Public/private extension boundary

Public `stratbox` может определять только generic contracts:

```text
CapabilityProvider
SourceProvider
FileStore
Artifact provider
```

Любая environment-specific реализация подключается через эти boundaries.

Публичный core не должен зависеть от конкретной внутренней инфраструктуры окружения.

---

# 68. Scheme IR должен быть intentionally limited

Главный anti-goal:

```text
Scheme DSL = второй Python
```

Если добавить:

```text
arbitrary loops
eval
dynamic imports
arbitrary code blocks
mutable globals
```

то теряются:

- static analysis;
- security;
- type checking;
- portability;
- inspectability.

---

# 69. Минимальные intrinsic constructs Scheme IR

На первом этапе может хватить:

```text
invoke
map
condition
collect
```

Причём `condition` можно сначала выразить отдельной Operation.

Всё сложное реализуется capability, а не расширением DSL.

---

# 70. Recursive composition

Scheme может вызывать:

```text
Operation
Scheme
```

По умолчанию graph должен быть acyclic.

Long-lived cycles/stateful loops — отдельный профиль, если реально потребуется.

---

# 71. Authoring format

Для первой реализации я бы выбрал:

> **Python-defined immutable specs, которые сериализуются в canonical JSON/YAML.**

Почему:

- IDE;
- type checking;
- безопасные refactors;
- нормальные constants/enums;
- простой bootstrap.

Generated/admitted Schemes позднее могут храниться уже как data artifacts.

---

# 72. Почему не YAML-first

YAML удобен для composition, но плохо подходит как источник сложной business logic.

Правило:

```text
YAML/JSON
    описывает graph/composition

Python Operation
    выполняет сложную business semantics
```

---

# 73. Canonical serialization

Для identity/hash Scheme нужна:

```text
canonical JSON representation
```

YAML остаётся human-friendly authoring/export.

---

# 74. Scheme identity

```text
scheme_id
exact version
content digest
```

Run всегда pin exact version.

---

# 75. Operation semantic version и implementation revision

Нужно различать:

```text
Operation Contract Version
Implementation Revision
```

Bugfix implementation может сохранить contract version.

Но Run provenance знает exact implementation revision.

---

# 76. Backward compatibility сейчас не нужна — это преимущество

Так как проект прямо допускает breaking redesign, стоит сразу:

- убрать случайные `dict` boundaries;
- ввести strict schemas;
- разделить plan/apply;
- перестать считать path identity;
- отказаться от скрытого `latest`;
- отделить semantic Operation от implementation.

Нельзя тратить архитектуру на сохранение слабых старых interfaces.

---

# 77. Scheme lifecycle

Candidate lifecycle:

```text
DRAFT
VALIDATING
TESTED
ADMITTED
DEPRECATED
REVOKED
```

Это lifecycle **knowledge/capability artifact**, а не execution Run.

---

# 78. Generated Scheme

PROTOS может построить temporary plan из существующих capabilities.

Если pattern:

- повторяется;
- стабилен;
- ценен;
- bounded;
- тестируем;

он становится `SchemeCandidate`.

---

# 79. Admission generated Scheme

Минимальные checks:

1. schema valid;
2. все referenced capabilities существуют;
3. versions resolved;
4. ports type-check;
5. graph допустим;
6. output reachable;
7. effect analysis complete;
8. resource analysis complete;
9. no undeclared arbitrary code;
10. invariants defined;
11. fixtures/regression tests;
12. provenance exists.

---

# 80. LLM-generated Scheme лучше LLM-generated Python

Если нужная capability уже существует:

```text
PROTOS
→ compose declarative Scheme
```

значительно лучше:

```text
PROTOS
→ write new arbitrary Python
```

Преимущества:

- меньше attack surface;
- легче review;
- меньше code sprawl;
- reuse;
- portable;
- static effect analysis.

---

# 81. Новый Python только при Capability Deficit

Если существующих capabilities недостаточно:

```text
CapabilityDeficit
→ propose new Operation implementation
→ tests
→ static/security checks
→ evaluation
→ admission
→ new capability
```

Это отдельный learning/engineering lifecycle.

---

# 82. Generated code тоже Artifact

В будущем:

```text
source code artifact
test artifact
evaluation artifact
build artifact
```

Capability binding ссылается на admitted implementation.

Обычная пользовательская Work не должна тихо переписывать `src/stratbox`.

---

# 83. Compile-down lifecycle PROTOS

Очень важная связь с PROTOS:

```text
novel task
→ expensive dynamic cognition
→ temporary ExecutionPlan
→ repeated similar tasks
→ Scheme candidate
→ evaluation/admission
→ explicit Scheme
→ hot/stable pattern
→ optimized Operation / compiled fast path
```

Это и есть практическое превращение cognition в machine scheme.

---

# 84. Further lowering

Стабильная Scheme может со временем стать одной optimized Operation:

```text
Scheme A+B+C
→ optimized implementation D
```

При этом:

```text
D provenance:
    derived_from Scheme@N
```

---

# 85. Deoptimization

Compiled capability всегда имеет validity envelope.

Если:

```text
source schema changed
registry incompatible
new validation failure
unsupported input
```

то:

```text
fast path
→ deopt
→ general Scheme
→ if needed PROTOS reasoning
```

---

# 86. Scheme validity envelope

Полезные поля:

```text
supported schema versions
source families
registry ranges
known unsupported cases
invalidation triggers
```

Нельзя считать compiled code вечной истиной.

---

# 87. Planner

Целевой pipeline:

```text
Intent / Scheme request
        ↓
resolve inputs
        ↓
resolve exact capability versions
        ↓
resolve Source/Registry snapshots
        ↓
expand nested Schemes
        ↓
type-check ports
        ↓
resolve resources
        ↓
deduplicate equivalent invocations
        ↓
build dependencies
        ↓
parallelization
        ↓
effect / authority gates
        ↓
ExecutionPlan
```

---

# 88. ExecutionPlan является first-class object

Plan содержит:

```text
plan_id
scheme refs
operation invocations
input refs
source snapshots
registry snapshots
artifact destinations
dependency graph
guards
effect summary
resource summary
```

Plan immutable после старта Run.

---

# 89. Изменение assumptions требует replan

Нельзя незаметно менять active Plan.

Если:

```text
source changed
registry changed
user constraint changed
```

то старый Plan может:

```text
remain valid
need revalidation
become stale
require new revision
```

---

# 90. Где должен жить Planner

Полезно разделить два слоя.

## Semantic planner

Может быть reusable core:

- expand Scheme;
- resolve capabilities;
- type-check;
- dedup;
- produce machine Plan.

## Runtime scheduler

Application layer:

- queue;
- worker placement;
- host/node;
- priority;
- concurrency slots;
- restart/resume;
- user approval lifecycle.

`stratbox` не должен становиться полноценным Job engine.

---

# 91. Deterministic planner до PROTOS planner

Сначала Scheme должен исполняться без LLM.

Только затем PROTOS получает способности:

```text
choose Scheme
compose capabilities
propose dynamic plan
```

Это создаёт strong baseline и degraded mode.

---

# 92. Type-first planning

Очень перспективное развитие:

```text
available typed objects
+
desired typed output
+
Capability graph
→ possible paths
```

Например:

```text
Have:
    SourceSnapshot[CbrEscrowXlsx]

Want:
    Dataset[CbrEscrowHistory]

Catalog:
    parse
    combine
    validate
```

Planner строит path без LLM.

---

# 93. Роль LLM после формализации

LLM нужна там, где есть:

- natural-language intent;
- semantic ambiguity;
- novel decomposition;
- conflict;
- uncertain source choice;
- open-ended analysis.

LLM больше не должна:

- помнить function names;
- угадывать params;
- читать exception text;
- строить технический glue каждый раз.

---

# 94. Это и есть вычислительная экономия

Чем больше routine semantics превращается в explicit capability graph:

```text
тем меньше general cognition требуется
```

Это напрямую соответствует PROTOS principle:

```text
known/stable/repeated
→ compile downward
```

---

# 95. Scheme не должна быть «мертвой автоматизацией»

Обязательны:

- applicability;
- validity;
- typed failures;
- fallback;
- deoptimization.

Если Scheme выходит из validity envelope:

```text
return to broader cognition
```

---

# 96. Semantic result Scheme

Success не означает:

```text
все функции завершились без exception
```

Success означает:

```text
declared outcome contract satisfied
```

---

# 97. Outcome contract

Например:

```text
canonical dataset exists
coverage >= threshold
validation has zero errors
artifact committed
```

---

# 98. Partial outcome

Для внешних источников особенно важен:

```text
PARTIAL
```

с:

```text
covered periods
missing sources
warnings
remaining uncertainty
```

PROTOS может решить, достаточно ли этого.

---

# 99. Evidence graph

Material result связывается:

```text
Outcome
↓
Validation Evidence
↓
Input Dataset
↓
SourceSnapshots
```

---

# 100. SORS как stress-test богатого Result

SORS уже показывает, что complex analytical capability должна сохранять:

- derivations;
- solver evidence;
- conflicts;
- audit;
- constraints.

Общая standardized boundary должна оборачивать это, а не выравнивать до примитивного:

```text
{"ok": true}
```

---

# 101. Uniform exterior, variable interior

Это лучший принцип для всех domains:

> **Стандартизируется внешняя форма capability, но внутренняя предметная сложность остаётся свободной.**

Escrow может быть простой Operation chain.

SORS может иметь сотни внутренних математических сущностей.

Оба внешне способны дать:

```text
Spec
Request
Result
Failure
Artifact/Evidence refs
Provenance
```

---

# 102. Не создавать UniversalDataset и UniversalDomainResult

Нельзя пытаться нормализовать весь banking/macroeconomic domain в одну universal таблицу.

Общими являются:

- refs;
- schema identity;
- provenance;
- lifecycle;
- operation boundary.

Содержимое остаётся typed domain-specific.

---

# 103. Организация root package

Целевая responsibility map:

```text
src/stratbox/
├─ base/
│  ├─ filestore/
│  ├─ net/
│  └─ ...
│
├─ common/
│
├─ capabilities/
│  ├─ contracts.py
│  ├─ schemas.py
│  ├─ effects.py
│  ├─ resources.py
│  ├─ registry.py
│  ├─ bindings.py
│  └─ scheme_ir.py
│
├─ sources/
│  ├─ contracts.py
│  ├─ catalog.py
│  ├─ snapshots.py
│  └─ validation.py
│
├─ artifacts/
│  ├─ contracts.py
│  ├─ refs.py
│  └─ manifests.py
│
├─ registries/
│  ├─ contracts.py
│  ├─ snapshots.py
│  ├─ banks/
│  ├─ okved2/
│  └─ geography/
│
├─ formats/
│  ├─ dbf/
│  ├─ xlsx/
│  ├─ csv/
│  └─ archives/
│
├─ macrobanks/
│  ├─ escrow/
│  ├─ cbr_industries/
│  ├─ cbr_forms/
│  ├─ cbr_sors_restoration/
│  └─ frg/
│
└─ text/
```

Это target responsibility map. Не нужно создавать все directories заранее.

---

# 104. Почему domain-first packages надо сохранить

Плохая архитектура:

```text
all_parsers/
all_validators/
all_calculators/
all_exports/
```

Она разрывает domain cohesion.

Хорошая:

```text
macrobanks/escrow/
    contracts
    sources
    parse
    validation
    operations
```

Generic capability выносится выше только после доказанного повторного использования.

---

# 105. Типичная форма зрелого domain package

По необходимости:

```text
contracts.py
models.py
sources.py
parse.py
normalize.py
validation.py
calculate.py
views.py
export.py
operations.py
schemes/
```

Не каждый domain обязан иметь все файлы.

---

# 106. `operations.py` должен быть коротким public machine facade

Туда не нужно складывать helpers.

`operations.py` содержит canonical Operations, которые:

- имеют semantic ID;
- могут быть зарегистрированы;
- имеют stable Request/Result;
- понятны без чтения implementation details.

---

# 107. Domain internals могут быть свободнее

Внутри:

```text
numpy
pandas
algorithmic helper classes
private functions
temporary data structures
```

не требуют общего platform contract.

---

# 108. Presentation metadata остаётся вне core semantics

Core знает:

```text
parameter type
default
constraint
semantic description
```

Surface может добавить:

```text
label
tooltip
control
group
advanced/basic
```

`stratbox-windows` не должен вручную переописывать semantic schema.

---

# 109. Human docs можно частично генерировать

Из OperationSpec/Schema автоматически строятся:

- parameter tables;
- output tables;
- effect notes;
- version;
- examples skeleton;
- MCP projection.

README остаётся для conceptual explanation.

---

# 110. Tests как capability evidence

Operation-level:

- contract tests;
- happy path;
- typed failure;
- invariants;
- known edge cases;
- idempotency tests;
- concurrency where material.

Scheme-level:

- graph validates;
- types connect;
- expected artifacts;
- failure route;
- no undeclared effects;
- regression fixture.

---


# 111. Static analyzability как стратегическое свойство

До запуска Scheme желательно уметь ответить:

- какие capabilities нужны;
- какие sources/registries будут прочитаны;
- какие writes/effects возможны;
- какие artifacts ожидаются;
- какие nodes независимы;
- что можно дедуплицировать;
- какие approvals нужны;
- какой resource class нужен.

Это одно из самых ценных свойств Machine Scheme для PROTOS.

---

# 112. Почему static analyzability важнее «красивого YAML»

Machine-readable Scheme ценна не тем, что выглядит декларативно, а тем, что runtime может **доказуемо извлечь её свойства**.

Если Scheme содержит opaque `python: | ...`, преимущества исчезают.

---

# 113. Resource semantics

Первый уровень можно сделать категориальным:

```text
CPU: small / medium / large
memory: small / medium / large
network: none / required
storage: read / write
solver: none / optional / required
```

Позже добавлять:

```text
estimated bytes
rows
wall-time
API cost
memory
```

только там, где это реально помогает planning.

---

# 114. Resource requirements не являются setup steps

Если десять Operations требуют:

```text
network:cbr
```

Scheme не должна десять раз вызывать `connect_to_cbr`.

Planner/runtime разрешает resource requirement отдельно.

---

# 115. Freshness как first-class semantics

Сегодня `refresh=True/False` часто является локальным flag.

Лучше иметь общий `FreshnessPolicy`:

```text
ALLOW_CACHED
PREFER_FRESH
REQUIRE_FRESH
REQUIRE_SNAPSHOT
MAX_AGE
```

Domain Request может ссылаться на policy.

---

# 116. Environment-specific flags следует выносить

Operation должна говорить:

```text
requires capability/network/storage
```

а не:

```text
use_environment_X = true
```

Конкретный provider/adapter решает, как capability реализуется.

Это особенно важно для public core и будущих разных deployment environments.

---

# 117. Neutral ExecutionContext

Условно:

```text
FileStore
ArtifactService
SourceResolver
RegistryResolver
Clock
ProgressSink
CancellationToken
```

Но `ExecutionContext` не должен превратиться в giant service locator.

Зависимости операции лучше делать явными там, где это помогает тестируемости.

---

# 118. Default runtime facade

Для Jupyter удобство можно сохранить:

```python
result = build_escrow_history(request)
```

facade подставляет default context.

Но underlying implementation должна быть исполнима с explicit dependencies.

---

# 119. Cache identity

Без формального capability contract безопасный cache очень сложен.

Корректный key зависит от:

```text
operation semantic version
canonical semantic inputs
input content identities
source/registry snapshot identities
relevant environment identity
```

---

# 120. Cache ≠ Scheme

Cache:

```text
materialized prior result
```

Scheme:

```text
procedure
```

Compiled Scheme:

```text
cheaper procedure
```

Это три разных объекта.

---

# 121. Reuse / dedup

Planner может объединить две invocations только если один результат допустим для обеих.

Не достаточно:

```text
same operation_id
```

Нужны:

```text
same semantic inputs
compatible freshness
same relevant snapshot/environment
compatible effect scope
```

---

# 122. Effects нельзя дедуплицировать по умолчанию

Для:

```text
delete
rename
publish
send
external write
```

reuse/dedup запрещён без explicit idempotency contract.

---

# 123. Side-effect receipts

Effectful Operation возвращает не только «done», а receipt:

```text
effect_id
target
precondition revision
actual outcome
timestamp
reconciliation state
```

Это важно для recovery после timeout/crash.

---

# 124. `UNKNOWN` effect state

Ключевой distributed-systems principle:

```text
локально не получили ответ
≠
эффект не произошёл
```

Поэтому:

```text
UNKNOWN
```

должен быть допустимым effect outcome.

---

# 125. Scheme и transitions

Пользователь спрашивал отдельно о переходах состояний.

Правильнее различить три transition systems.

## A. Run transitions

Application runtime:

```text
PENDING
QUEUED
RUNNING
WAITING
COMPLETED
FAILED
CANCELLED
UNKNOWN
```

## B. Domain object transitions

Например:

```text
SourceSnapshot:
DISCOVERED → FETCHED → VALIDATED / REJECTED
```

или:

```text
Artifact:
CANDIDATE → COMMITTED → ARCHIVED/TOMBSTONED
```

## C. Capability lifecycle

```text
DRAFT → TESTED → ADMITTED → DEPRECATED → REVOKED
```

Нельзя сводить всё в один `status`.

---

# 126. State ownership

`stratbox` может владеть:

- domain lifecycle semantics;
- capability lifecycle definitions;
- immutable ExecutionPlan format.

Application runtime владеет:

- actual Job/Run state;
- queues;
- workers;
- retries/resume orchestration;
- user approvals.

Это сохраняет core библиотечным.

---

# 127. Event semantics

Domain Operation может emit structured progress/domain events.

Но глобальная event database принадлежит runtime.

Operation event:

```text
phase_started
source_processed
validation_completed
artifact_candidate_created
```

Runtime добавляет:

```text
run_id
work_id
actor
node
timestamps
```

---

# 128. Machine Scheme и observability

Каждый Plan node получает:

```text
invocation_id
capability_id
capability_version
```

Тогда trace:

```text
Work
→ Run
→ Plan
→ Invocation
→ Artifact / Failure
```

---

# 129. CloudEvents как внешний adapter

При remote/distributed mode internal Event можно проецировать в CloudEvents-compatible envelope.

Внутренняя event semantics Strategy Box остаётся richer.

---

# 130. Current-domain migration: `cbr_file_collector`

Это лучший первый pilot.

Сегодня уже есть:

```text
RegistryItem
Request
DownloadedSource
CollectedFile
Failure
Result
```

Целевая decomposition:

```text
SourceCatalog
SourceDescriptor
SourceSnapshotRef
ArtifactRef
OperationSpec
ResultEnvelope
```

---

# 131. Почему collector первый

Он маленький, но проверяет почти весь фундамент:

- source identity;
- network;
- retries;
- FileStore;
- multiple inputs;
- partial failures;
- saved outputs;
- source registry.

При этом нет сложной аналитической математики.

---

# 132. Collector target Operations

Возможный набор:

```text
cbr.files.sources.list
cbr.files.collect
```

Позже generic primitives:

```text
source.fetch
artifact.bundle
```

следует выделять только если reuse действительно доказан.

---

# 133. `escrow` — второй pilot

Проверяет полный pipeline:

```text
discover
fetch/cache
parse
normalize
combine history
build views
export
```

---

# 134. Escrow target split

Возможные Operations:

```text
cbr.escrow.sources.resolve
cbr.escrow.parse
cbr.escrow.history.combine
cbr.escrow.history.validate
cbr.escrow.view.build
cbr.escrow.workbook.export
```

Не обязательно делать каждую функцию Operation. Граница должна соответствовать самостоятельной управляемой capability.

---

# 135. `cbr.escrow.update` как первый Machine Scheme

Именно здесь имеет смысл проверить:

- typed graph;
- map/fan-in;
- source snapshots;
- dataset refs;
- provenance;
- machine plan;
- optional export.

---

# 136. FRG — третий pilot

Главная цель:

```text
typed destructive semantics
```

Перевести:

```text
plan DataFrame
```

в domain model:

```text
CleanupPlan
CleanupAction
CleanupPlanRef
```

---

# 137. FRG target Operations

```text
frg.catalog.build
frg.latest.select
frg.cleanup.plan
frg.cleanup.apply
```

`apply` работает только с plan identity/revision.

---

# 138. FRG preconditions

Для каждого effect action:

```text
source exists
source hash/stat unchanged
target condition still valid
plan not expired
```

Если нет:

```text
STALE_PLAN
CONFLICT
```

---

# 139. `cbr_industries` — четвёртый pilot

Этот domain уже близок к идеальной typed decomposition.

Нужно проверить:

- machine schemas;
- DatasetRefs вместо единственного DataFrame transport;
- standardized ValidationIssue/Failure;
- common OperationSpec;
- ArtifactRefs;
- Scheme composition.

---

# 140. SORS — последний stress test

Начинать с него не стоит из-за сложности.

Но зрелая architecture должна выдержать:

- solver identity;
- constraint system;
- evidence;
- conflicts;
- audit;
- large tabular outputs;
- optional solver backends.

Если общий capability envelope способен обернуть SORS без потери domain richness, boundary выбран хорошо.

---

# 141. Registries migration

Приоритет:

1. `RegistryDescriptor`;
2. `RegistrySnapshot`;
3. exact snapshot identity;
4. content hash;
5. effective/source dates;
6. source provenance;
7. validation;
8. resolve `latest` before Run.

---

# 142. Source governance migration

Определить:

```text
SourceDescriptor
SourceSnapshot
SourceValidation
```

Далее домены перестают придумывать собственную форму source identity.

---

# 143. Artifact migration

Operation Result перестаёт считать:

```text
"C:\...\report.xlsx"
```

полным описанием результата.

Возвращается:

```text
ArtifactRef
```

с optional materialization path.

---

# 144. Schema Registry migration

Не нужен отдельный network service.

В первой версии:

```text
package resources
+
stable schema IDs
```

достаточно.

---

# 145. Capability Schema IDs

Например:

```text
schema://stratbox/source/snapshot@1
schema://stratbox/artifact/ref@1
schema://stratbox/cbr/escrow/history@1
```

Exact URI syntax можно выбрать позже.

---

# 146. Machine-readable business semantics

Особенно важно постепенно описывать:

```text
dimensions
measures
units
keys
code systems
time meaning
```

Это позволит PROTOS работать с данными на более высоком уровне.

---

# 147. Пример semantic dataset descriptor

```yaml
dataset_type: cbr.corporate.debt
schema_version: 2

dimensions:
  - report_date
  - region_code
  - industry_code
  - currency_scope

measures:
  - name: debt
    unit: million_rub
  - name: overdue_debt
    unit: million_rub

code_systems:
  industry_code: stratbox:cbr-industry
  region_code: stratbox:cbr-region
```

---

# 148. Почему это фактически «знание для ИИ»

PROTOS больше не должен угадывать по названиям колонок:

```text
что является датой;
что отраслью;
в каких единицах value;
что можно агрегировать.
```

Он получает explicit semantic data contract.

---

# 149. Views и artifacts

`pivot` / workbook / chart являются производными представлениями.

Canonical dataset остаётся reusable knowledge object.

---

# 150. Operation outcome vs Artifact

Operation может вернуть:

```text
canonical DatasetRef
```

без physical file.

Artifact появляется при commit/materialization.

Это особенно важно для chained machine workflows.

---

# 151. Does every Operation need Artifact?

Нет.

Pure transform может возвращать ephemeral/in-process object или DatasetRef.

Artifact нужен, когда output должен:

- жить дольше Run;
- передаваться;
- быть адресуемым;
- иметь provenance;
- использоваться другим actor/node.

---

# 152. Does every Operation need serialization?

Public canonical Operation — да, хотя бы control-plane projection.

Private helper — нет.

---

# 153. Does every Scheme need a file?

Нет.

Built-in Scheme может быть Python spec.

Generated/admitted Scheme может быть persistent artifact.

Важно, чтобы у definition была canonical machine representation.

---

# 154. Does every domain need a Scheme?

Нет.

Если Operation уже полностью представляет устойчивый outcome:

```text
Operation == sufficient capability
```

Scheme не нужна.

---

# 155. Does every pipeline become Scheme?

Нет.

Внутренний алгоритм Operation может иметь десятки стадий, но если они не нужны planner-у отдельно, их лучше оставить implementation detail.

---

# 156. Главный критерий границы Operation

Отдельная Operation оправдана, если есть самостоятельная потребность управлять хотя бы частью:

```text
inputs/outputs
effect
reuse
failure
retry
cancellation
parallelism
cache
evidence
```

Если нет — это helper.

---

# 157. Главный критерий Scheme

Scheme оправдана, если:

```text
композиция нескольких capabilities имеет устойчивый повторяемый semantic outcome
```

и её полезно:

- вызывать снова;
- версионировать;
- тестировать;
- выбирать planner-ом;
- объяснять пользователю/PROTOS.

---

# 158. Главный критерий нового primitive

Новый generic primitive выносится выше domain only if:

```text
reuse across domains
+
stable semantics
+
independent testing value
```

---

# 159. Pydantic migration strategy

Не надо переписывать все domain dataclasses сразу.

Пилот:

```text
common refs/envelopes/specs
```

на Pydantic/equivalent.

Domain dataclasses можно постепенно адаптировать.

---

# 160. Dual result adapter

Например:

```python
EscrowHistoryResult       # rich Python
EscrowHistoryResultView   # serializable machine projection
```

Но если Pydantic domain model не мешает pandas internals, можно объединять по месту.

Главное — не догматизировать library choice.

---

# 161. Python generics

Можно использовать для developer ergonomics:

```python
OperationSpec[RequestT, ResultT]
OperationBinding[RequestT, ResultT]
```

Но runtime identity всё равно определяется schema refs, а не Python generic reflection.

---

# 162. Suggested common contracts

Минимальный первый пакет:

```text
capabilities/
    identity
    operation
    result
    failure
    effects
    resources
    registry
```

Scheme IR добавлять после Operation foundation.

---

# 163. Candidate Result types

```text
OperationOutcome
OperationResultEnvelope[T]
Failure
Diagnostic
ProgressEvent
```

---

# 164. Candidate refs

```text
ArtifactRef
DatasetRef
SourceRef
SourceSnapshotRef
RegistryRef
RegistrySnapshotRef
SchemaRef
```

---

# 165. Candidate policy types

```text
FreshnessPolicy
IdempotencySpec
ConcurrencySpec
CancellationSpec
EffectClass
DeterminismClass
```

---

# 166. Avoid metadata explosion

Не каждое поле обязательно для каждой Operation.

Spec может иметь sane defaults.

Например pure operation:

```text
effect = PURE
parallel = safe
idempotent = always
```

---

# 167. Required metadata should be risk-proportional

Read-only deterministic transform требует мало.

Destructive/external effect требует:

- exact preconditions;
- idempotency;
- reconciliation;
- receipts;
- approval class.

---

# 168. Machine Scheme tests as executable specification

Scheme fixtures могут сказать:

```text
Given SourceSnapshots X/Y
When cbr.escrow.update
Then Dataset schema = Z
And validation errors = 0
And no undeclared effects
```

Это и documentation, и regression evidence.

---

# 169. Property-based tests

Особенно полезны для generic primitives:

- normalizers;
- parsers;
- converters;
- idempotent transforms.

Не обязательны для всего.

---

# 170. Contract linting

CI должна проверять:

```text
unique capability IDs
unique exact versions
valid schema refs
serializable specs
no unresolved references
Scheme graph valid
no type mismatch
AI-visible capabilities have descriptions
effectful capabilities declare effect policy
```

---

# 171. Documentation drift

Machine contracts позволяют автоматически ловить drift между:

```text
code
README
surface forms
AI catalog
```

Это большой операционный выигрыш.

---

# 172. Capabilities and plugins/extensions

Extension может поставлять:

```text
new OperationBinding
new SchemeSpec
new source/provider binding
```

через generic public contract.

Public `stratbox` и `stratbox-windows` должны знать только этот нейтральный contract.

---

# 173. Capability admission from extension

Нельзя считать capability trusted только потому, что package импортируется.

В будущем:

```text
discover
→ validate descriptors
→ compatibility
→ policy
→ admit
```

---

# 174. Capability collision

Если providers объявили одинаковый:

```text
capability_id + version
```

нужна explicit resolution/error.

Silent overwrite запрещён.

---

# 175. Scheme dependencies

Scheme может требовать capability range:

```text
source.fetch@2
```

На execution Plan resolver pin exact implementation/semantic version.

---

# 176. Scheme package / bundle

Позже можно иметь portable bundle:

```text
SchemeSpec
schemas
tests
metadata
provenance
```

без embedded arbitrary source code, если uses existing Operations.

---

# 177. User-local learned Schemes

Будущий PROTOS может создавать:

```text
personal Scheme
```

на основании повторяющейся работы пользователя.

Но она должна использовать тот же contract и lifecycle, что built-in Scheme.

---

# 178. Organizational Schemes

Также возможны:

```text
organization-admitted
signed
policy-bound
```

Это future profile, не текущий P0.

---

# 179. Trust level

Capability/Scheme metadata позднее может содержать:

```text
builtin
admitted
experimental
revoked
```

Trust ≠ capability correctness, но влияет на policy.

---

# 180. Formal minimal Scheme model

Можно мыслить:

```text
S = (
    Identity,
    Inputs,
    Outputs,
    Graph,
    Preconditions,
    Effects,
    Invariants,
    Policies,
    Provenance
)
```

Graph:

```text
G = (Nodes, Edges)
```

Node:

```text
Capability Invocation
```

Edge:

```text
Typed Dependency
```

---

# 181. Plan validity

Plan допустим, если:

```text
all capability refs resolve
input bindings type-check
required outputs reachable
preconditions satisfiable
effects allowed by requested profile
graph valid
no unresolved mandatory resource
```

---

# 182. Outcome validity

Run технически завершился только тогда, когда:

```text
outcome contract evaluated
```

а не когда последний Python call вернулся.

---

# 183. PROTOS-facing operations

Когнитивной системе нужны концептуально три meta-capabilities:

```text
DISCOVER
INVOKE
COMPOSE
```

Плюс inspect evidence/results.

---

# 184. Capability search

Поиск может комбинировать:

```text
semantic tags
input/output types
effects
domains
text description
```

Embeddings можно добавить как индекс, но не как source of truth.

---

# 185. Example type-first search

Запрос:

```text
Input:
    Dataset[CbrDebt]

Goal:
    Artifact[XLSX]

Constraints:
    no destructive effects
```

Registry может найти:

```text
pivot.build
→ workbook.export
```

без общего LLM reasoning.

---

# 186. PROTOS context economy

В model context не нужно класть full details 1 000 capabilities.

Можно:

```text
domain summaries
→ candidate IDs/signatures
→ selected full specs
```

---

# 187. Почему capability descriptions всё равно важны

Types не всегда полностью выражают intent.

Например два Operations могут иметь одинаковые входы/выходы, но разный semantic interpretation.

Нужны:

```text
description
applicability
domain tags
```

---

# 188. PROTOS не должен infer Authority из description

Capability metadata сообщает effects.

Application policy решает, разрешена ли invocation.

---

# 189. Business code and cognitive code boundary

Важно не создавать отдельный:

```text
ai_operations/
```

который дублирует обычный core.

Один capability должен иметь много consumers.

---

# 190. Scheme and Scenario

С учётом предыдущего исследования интерфейса:

```text
Machine Scheme
```

— core/runtime capability.

Пользовательский Chat/Work может использовать много Schemes.

`Scenario` как UI/product term может постепенно стать presentation/projection этой capability, но core не должен зависеть от UI taxonomy.

---

# 191. Cascade

В новой архитектуре отдельный фундаментальный `Cascade` уже не обязателен.

Это может быть:

```text
composite Scheme
```

или resolved graph из нескольких Scheme invocations.

---

# 192. Compatibility with parallel PROTOS activations

Одна SchemeSpec может одновременно инстанцироваться:

```text
Run A / Activation 1
Run B / Activation 2
Run C / Activation 3
```

Scheme сама не хранит mutable execution state.

Это важное требование thread safety/reentrancy.

---

# 193. Pure definitions

`OperationSpec` и `SchemeSpec` должны быть immutable.

Run-specific values живут:

```text
Invocation
Plan
Run
```

---

# 194. Concurrency by design

Operations должны объявлять, если:

- safe parallel;
- serialized by resource;
- exclusive;
- destination lock.

Это позволит тем самым одинаковым независимым cognitive activations реально исполняться одновременно.

---

# 195. No hidden globals

Глобальный mutable cache / current period / active registry внутри domain module сильно мешает parallelism.

Нужно минимизировать.

---

# 196. Global immutable registry definitions допустимы

Например constant specs.

Но resolved current/latest state должен быть explicit input/ref.

---

# 197. Deterministic core where possible

Бизнес-code должен предпочитать:

```text
input → result
```

с explicit dependencies.

Это облегчает:

- repeatability;
- parallelism;
- generated planning;
- testing.

---

# 198. Stateful external systems через adapters

Если unavoidable state:

```text
network session
storage transaction
solver session
```

он остаётся provider/resource object, а semantic Operation всё равно имеет explicit contract.

---

# 199. Implementation does not need to mirror Scheme graph one-to-one

PROTOS principle:

```text
fine semantic granularity
≠ fine physical granularity
```

Runtime может:

- batch;
- fuse;
- optimize;
- call one compiled function.

Semantics graph сохраняется для reasoning/provenance.

---

# 200. Physical fusion

Если nodes A/B/C часто всегда вместе:

```text
semantic graph A→B→C
physical optimized binding ABC
```

Resolver может использовать optimized binding, если capability envelope доказывает equivalence.

---

# 201. This is analogous to compiler lowering

High-level Scheme:

```text
semantic IR
```

ExecutionPlan:

```text
lowered IR
```

Bindings:

```text
backend implementation
```

Это полезная инженерная аналогия.

---

# 202. Но не строить compiler framework преждевременно

Сначала:

```text
explicit operations
simple Scheme graph
```

Потом optimization.

---

# 203. Acceptance criteria: canonical Operation

Operation зрелая, если:

- stable semantic ID;
- exact version;
- typed request;
- serializable input schema;
- rich domain result;
- serializable result projection;
- effects declared;
- resource requirements declared;
- failures typed;
- idempotency scope known;
- concurrency semantics known;
- freshness semantics known where material;
- cancellation semantics known;
- artifacts identified;
- provenance available;
- tests exist;
- discoverable without reading implementation.

---

# 204. Acceptance criteria: Machine Scheme

Scheme зрелая, если:

- stable ID/version;
- machine-readable definition;
- typed inputs/outputs;
- every node uses admitted capability;
- ports type-check;
- graph valid;
- effects statically derivable;
- failure policy exists;
- outcome contract exists;
- provenance exists;
- no undeclared arbitrary code;
- test fixture/regression exists;
- exact definition can be pinned by ExecutionPlan.

---

# 205. Acceptance criteria: PROTOS-ready `stratbox`

PROTOS может через neutral interface:

```text
list capabilities
search/filter capabilities
inspect one capability
understand inputs/outputs/effects
find a Scheme for outcome
instantiate a Scheme
validate resulting Plan
request execution through application runtime
receive typed Result
inspect artifacts/evidence/provenance
```

без импорта внутренних modules и чтения Python source.

---

# 206. Recommended implementation roadmap

## Stage 1 — Canonical Operation Contract

Создать:

```text
OperationSpec
OperationBinding
SchemaRef
EffectClass
ResourceRequirement
OperationOutcome
Failure
ResultEnvelope
```

Не строить Scheme IR раньше этого.

---

## Stage 2 — JSON Schema pilot

На:

1. collector;
2. escrow;
3. FRG cleanup plan.

Проверить:

- serialization;
- validation;
- generated docs/forms;
- schemas across process boundary.

---

## Stage 3 — Source/Registry contracts

Ввести:

```text
SourceDescriptor
SourceSnapshot
RegistryDescriptor
RegistrySnapshot
```

Убрать скрытый `latest` из critical Run inputs.

---

## Stage 4 — Artifact/Dataset refs

Ввести:

```text
ArtifactRef
DatasetRef
```

Path-only outputs считать presentation/materialization detail.

---

## Stage 5 — CapabilityRegistry

Curated explicit registration.

Сначала только несколько canonical Operations.

---

## Stage 6 — First Scheme IR

Реализовать минимальный:

```text
Invoke
Map
Collect
typed bindings
```

Первый Scheme:

```text
cbr.escrow.update
```

---

## Stage 7 — ExecutionPlan

Planner:

- expands Scheme;
- pins versions;
- pins snapshots;
- type-checks;
- builds DAG;
- computes effects/resources.

---

## Stage 8 — FRG plan/apply

Проверить:

- effect classes;
- PlanRef;
- stale preconditions;
- approval readiness;
- receipts.

---

## Stage 9 — `cbr_industries`

Проверить complex typed chain.

---

## Stage 10 — SORS stress test

Проверить богатый evidence/result без flattening.

---

## Stage 11 — PROTOS adapter

Только после стабильного Capability Contract.

Тогда cognitive layer получает естественный substrate вместо bespoke AI API.

---

# 207. Что не стоит делать сейчас

1. Не внедрять BPMN engine.
2. Не внедрять полноценный PDDL planner.
3. Не создавать отдельный Schema microservice.
4. Не строить universal ontology всех банковских данных.
5. Не переписывать все domain dataclasses на Pydantic одним PR.
6. Не регистрировать все helper functions.
7. Не делать generic workflow DSL Turing-complete.
8. Не давать LLM raw FileStore/shell/Python.
9. Не смешивать sources, registries и capabilities в один catalog.
10. Не делать SORS первым пилотом.
11. Не превращать `stratbox` в durable workflow/job server.
12. Не хранить current state только в prompt/conversation.

---

# 208. Самые сильные практические выводы

1. **Current domain-first organization хороша и должна сохраниться.**
2. **Нужен новый общий machine capability layer поверх domains.**
3. **Canonical Operation — главный ABI core.**
4. **Scheme — composition, а не замена Operations.**
5. **FileStore остаётся infrastructure mechanism.**
6. **Registry становится versioned knowledge resource.**
7. **Source становится Descriptor + Snapshot.**
8. **Artifact/Dataset получает stable ref вместо path identity.**
9. **JSON Schema стандартизирует control plane.**
10. **DataFrames остаются удобными внутри Python, но получают serializable projection/ref.**
11. **Default Scheme — typed DAG.**
12. **State machine используется только для genuine lifecycle.**
13. **Preconditions/effects делают capability пригодной для planner-а.**
14. **FRG plan/apply — правильный образец effectful AI-safe work.**
15. **Generated Scheme должна быть declarative прежде generated code.**
16. **Compiled Scheme имеет validity envelope и deoptimization path.**
17. **Capability definitions immutable; execution state separate.**
18. **Одинаковые Scheme invocations могут выполняться параллельно независимыми PROTOS activations.**
19. **Routine planning постепенно может стать type-driven и не требовать LLM.**
20. **Главный тест: machine понимает capability без чтения Python source.**

---

# 209. Целевая архитектура

```text
                           PROTOS
                             │
              discover / select / compose capabilities
                             │
                             ▼
┌───────────────────────────────────────────────────────────────┐
│                   STRATBOX CAPABILITY FABRIC                  │
│                                                               │
│ Capability Registry                                           │
│   ├─ Canonical Operations                                     │
│   └─ Machine Schemes                                          │
│                                                               │
│ Type / Schema Registry                                        │
│ Effects / Resources / Applicability                           │
│ Failure / Evidence / Provenance Contracts                     │
└────────────────────────────┬──────────────────────────────────┘
                             │
                             ▼
                    ExecutionPlan / Invocation
                             │
                             ▼
┌───────────────────────────────────────────────────────────────┐
│                       DOMAIN LOGIC                             │
│                                                               │
│ macrobanks/...                                                 │
│ source → parse → normalize → validate → calculate → view      │
│                                                               │
│ Reference Registries / Source Semantics                       │
└────────────────────────────┬──────────────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────────────┐
│                       MECHANISMS                               │
│                                                               │
│ FileStore / HTTP / formats / serializers / numeric solvers    │
└───────────────────────────────────────────────────────────────┘
```

---

# 210. Как это изменяет mental model разработчика

Сегодня:

```text
я написал функцию;
потом кто-то должен знать, как её вызвать.
```

Цель:

```text
я реализовал capability;
её semantic contract зарегистрирован;
любой authorised consumer умеет понять,
может ли и как её использовать.
```

Consumers:

```text
Python/Jupyter
Windows
Android
PROTOS
remote host
tests
docs
MCP adapter
```

---

# 211. Как это изменяет mental model PROTOS

Не:

```text
прочитать repository
найти подходящую функцию
написать glue code
```

А:

```text
current typed state
+
desired semantic outcome
+
available capabilities
+
effects/constraints
        ↓
resolve/plan
        ↓
Scheme / ExecutionPlan
        ↓
execute
```

---

# 212. Самый важный design rule №1

> **Смысл canonical capability должен быть полностью понятен и проверяем машине без чтения её Python-реализации.**

Если для ответа:

```text
что принимает?
что создаёт?
когда допустима?
что изменяет?
что может пойти не так?
```

нужно читать 500 строк реализации — contract недостаточен.

---

# 213. Design rule №2

> **Стандартизировать semantic boundaries, а не пытаться декларативно переписать каждый алгоритм.**

Pandas/solver/complex math спокойно остаются обычным кодом.

---

# 214. Design rule №3

> **Knowledge, Capability, Artifact и Execution State должны оставаться разными объектами.**

```text
Registry != Scheme
FileStore != Capability Catalog
Artifact != path
Run != Scheme
```

---

# 215. Design rule №4

> **Machine Scheme должна быть достаточно ограниченной, чтобы её можно было статически проверить до исполнения.**

---

# 216. Design rule №5

> **PROTOS сначала должен компилировать повторяющуюся cognition в декларативные Schemes из существующих Operations; новый код создаётся только при реальном capability deficit.**

---

# 217. Design rule №6

> **Любой compiled fast path обязан иметь provenance, validity envelope, invalidation trigger и route обратно к более общей cognition.**

---

# 218. Итоговый вердикт

Изначальная идея — рассматривать бизнес-логику `stratbox` как будущий набор машинных когнитивных схем — **очень продуктивна**, если провести важное разделение уровней.

В `stratbox` действительно уже формируется procedural substrate будущей cognitive system. Особенно это видно по:

- `Request → Result`;
- stage separation;
- source discovery;
- parse/normalize/validate;
- plan/apply;
- rich SORS evidence;
- FileStore abstraction.

Но правильная целевая форма — не:

```text
каждый кусок Python = cognitive Scheme
```

а:

```text
механизмы
    ↓
типизированные semantic capabilities
    ↓
версионируемые Machine Schemes
```

Реестры, source snapshots и datasets дают **knowledge**. Operations дают **abilities**. Schemes дают **procedural knowledge**. Artifacts дают **durable results**. ExecutionPlan связывает всё это в конкретное выполнение.

В таком виде `stratbox` становится очень сильным фундаментом PROTOS:

- слабая cognitive system просто выбирает готовую Scheme;
- сильная строит временный Plan из Operations;
- повторяемый Plan превращается в Scheme;
- стабильная Scheme может компилироваться дальше в оптимизированную Operation;
- при изменении мира fast path инвалидируется и cognition поднимается обратно вверх.

То есть архитектура одновременно подходит и для сегодняшней обычной Python-библиотеки, и для будущего масштабируемого cognitive runtime.

---

# Appendix A. Краткое сопоставление внешних формализмов

| Формализм | Что полезно Strategy Box | Что не стоит брать как основу |
|---|---|---|
| JSON Schema 2020-12 | input/output types, validation, schema IDs | workflow semantics |
| MCP Tools | AI capability discovery, schemas, structured result | internal domain model |
| CWL | typed ports, dataflow DAG, portable execution | CLI/container assumptions |
| BPMN 2.0 | events, gateways, parallelism, compensation concepts | полный BPMN runtime/XML |
| DMN | decision tables | enterprise decision platform целиком |
| SCXML | real state-machine semantics | обычные analytics pipelines |
| PDDL/HDDL | preconditions, effects, hierarchical planning | data/artifact model |
| CEL | bounded guards/predicates | business implementation |
| W3C PROV | provenance Entity/Activity/Agent geometry | обязательный RDF storage |
| CloudEvents | distributed event envelope | workflow semantics |

---

# Appendix B. Предлагаемая taxonomy machine objects

```text
Knowledge Objects
    RegistryDescriptor
    RegistrySnapshot
    SourceDescriptor
    SourceSnapshot
    Dataset

Capability Definitions
    OperationSpec
    SchemeSpec

Implementations
    OperationBinding
    ProviderBinding

Execution
    Invocation
    ExecutionPlan
    Run

Results / State
    Artifact
    DatasetRef
    EffectReceipt

Assurance
    Validation
    Failure
    Diagnostic
    Evidence
    Provenance
```

---

# Appendix C. Mapping текущих доменов

## CBR File Collector

```text
Current:
RegistryItem
Request
Result
Failure
FileStore

Target:
SourceCatalog
SourceDescriptor
OperationSpec
SourceSnapshotRef
ArtifactRef
ResultEnvelope
Failure
```

## Escrow

```text
Current:
SourceLink
DownloadedSource
ParsedFile
HistoryResult
PivotPack
ExportResult

Target:
SourceSnapshot
DatasetRef[EscrowHistory]
typed validation
Artifact[XLSX]
Operation chain
Scheme cbr.escrow.update
```

## CBR Industries

```text
Current:
Download
Parse
Validation
Stream
Calculation
Pivot
Workbook

Target:
сохранить богатую stage decomposition
+ machine schemas
+ Dataset/Artifact refs
+ OperationSpecs
+ Scheme
```

## FRG

```text
Current:
catalog
latest
plan DataFrame
execution DataFrame
execute flag

Target:
Catalog DatasetRef
CleanupPlan
PlanRef
frg.cleanup.apply
EffectReceipt
```

## SORS

```text
Current:
rich result
solver/evidence
constraints/conflicts
derivations/audit

Target:
сохранить rich domain model
+ common capability envelope
+ typed machine projection
```

---

# Appendix D. Candidate minimal Python surface

```python
CapabilityId
CapabilityVersion
SchemaRef

OperationSpec
OperationBinding
CapabilityRegistry

ArtifactRef
DatasetRef
SourceSnapshotRef
RegistrySnapshotRef

OperationResultEnvelope
Failure
Diagnostic
Provenance

SchemeSpec
SchemeNode
SchemeEdge

ExecutionPlan
PlanNode
PlanEdge
```

---

# Appendix E. Candidate OperationSpec

```python
@dataclass(frozen=True, slots=True)
class OperationSpec:
    id: str
    version: str

    title: str
    description: str
    domain: str

    input_schema: SchemaRef
    output_schema: SchemaRef

    effect_class: EffectClass
    determinism: DeterminismClass
    idempotency: IdempotencySpec
    concurrency: ConcurrencySpec
    cancellation: CancellationSpec

    resource_requirements: tuple[ResourceRequirement, ...]
    failure_codes: tuple[str, ...]

    ai_visibility: AiVisibility
```

---

# Appendix F. Candidate OperationBinding

```python
@dataclass(frozen=True)
class OperationBinding:
    spec: OperationSpec
    handler: Callable[..., object]
    implementation_id: str
```

---

# Appendix G. Candidate Scheme

```python
SchemeSpec(
    id="cbr.escrow.update",
    version="1",
    inputs=...,
    outputs=...,
    nodes=(
        Invoke("discover", "cbr.escrow.sources.resolve"),
        MapInvoke(
            "fetch",
            "source.fetch",
            over="discover.sources",
        ),
        MapInvoke(
            "parse",
            "cbr.escrow.parse",
            over="fetch.snapshots",
        ),
        Invoke(
            "combine",
            "cbr.escrow.history.combine",
            inputs={"datasets": "parse.datasets"},
        ),
        Invoke(
            "validate",
            "cbr.escrow.history.validate",
            inputs={"dataset": "combine.dataset"},
        ),
    ),
)
```

---

# Appendix H. External references

1. JSON Schema Draft 2020-12  
   https://json-schema.org/draft/2020-12/json-schema-core

2. Model Context Protocol — Tools, 2026-07-28  
   https://modelcontextprotocol.io/specification/2026-07-28/server/tools

3. Common Workflow Language v1.2  
   https://www.commonwl.org/v1.2/Workflow.html

4. BPMN 2.0.2  
   https://www.omg.org/spec/BPMN/2.0.2

5. DMN 1.5  
   https://www.omg.org/spec/DMN/1.5

6. W3C SCXML  
   https://www.w3.org/TR/scxml/

7. Common Expression Language  
   https://cel.dev/

8. W3C PROV-O  
   https://www.w3.org/TR/prov-o/

9. CloudEvents  
   https://github.com/cloudevents/spec

10. PDDL / HDDL / Hierarchical Planning  
    International Planning Competition hierarchical-track materials and HDDL literature.

---

# Appendix I. Internal research base

Исследование синтезирует текущее состояние `ForestTiger-GH/stratbox` и материалы первой эпохи Strategy Box, прежде всего:

```text
stratbox_base_study_current_state_2026-10-06.md
stratbox_commands_scenarios_cascades_research_2026-10-07.md
stratbox_business_segments_portability_reuse_architecture_research_2026-10-07.md
stratbox_registry_source_governance_research_2026-10-07.md
stratbox_file_artifact_layer_research_2026-10-06.md
strategy_box_automation_ai_research_2026-10-06.md
stratbox_protos_foundation_research_2026-10-07.md
stratbox_protos_chat_work_schemes_ui_research_2026-10-07.md
```

Из PROTOS особенно важны исследования:

```text
PROTOS_Semantic_Logical_Mandates_Orthogonal_Cognition_2026-09-16.md
PROTOS_From_Schemas_to_Semantic_Construct_Fabric_2026-09-16.md
PROTOS_Composable_Logical_Cognitive_Schemas_Architecture_2026-09-16.md
PROTOS_Cognitive_Microexecution_Relation_Algebra_and_Compiled_Fast_Paths_2026-09-16.md
```

Свежие Epoch 002 материалы используются как research input и не объявляются автоматически принятой текущей Product-семантикой PROTOS.

---

# Appendix J. Одно правило для дальнейшего рефактора

> **`stratbox` должен описывать каждую существенную повторно используемую бизнес-способность как версионируемый типизированный capability contract, а повторяемые способы композиции этих способностей — как ограниченные декларативные Machine Schemes; Python, FileStore, parsers и solvers остаются заменяемыми implementation mechanisms под этой семантической поверхностью.**
