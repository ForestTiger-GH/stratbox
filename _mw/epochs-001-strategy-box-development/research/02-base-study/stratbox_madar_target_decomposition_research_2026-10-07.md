# Strategy Box × MADAR: целевая семантическая архитектура и разложение продукта

**Дата:** 2026-10-07  
**Контур:** Alta Veritas / Strategy Box / вторая исследовательская ветка  
**Статус:** Research Result / Consolidation Input  
**Предмет:** как **целевой**, а не текущий Strategy Box раскладывается по будущей архитектуре MADAR с учётом свежих Stage 3 consolidation inputs, накопленного MADAR Research corpus, шести `mandat-*` интеграционных пакетов, `MADAR-supplements`, текущей реализации Strategy Box и всего корпуса `02-base-study`.  
**Ключевая установка:** текущее устройство Strategy Box, текущие имена сущностей, текущие репозитории и все исследования второй ветки считаются **переходными материалами**. Они используются как evidence и архитектурные гипотезы, но не получают право определять целевую онтологию только потому, что уже существуют.

---

# 0. Executive conclusion

Главный вывод исследования:

> **Strategy Box нельзя корректно “положить в MADAR” как один Activity Method, один Work, один Skill или один software module. Strategy Box сам является сложной инженерной системой, которая одновременно материализует несколько разных MADAR-плоскостей: Engineering Object, Engineering Work, Engineering Knowledge, Activity Methods, bounded reusable Work, cross-cutting concerns, Dispatcher-like resolution, Guidance/Examples и specialist/domain packs.**

Самая важная ошибка — сделать однозначную физическую таблицу вида:

```text
MADAR EWM = stratbox-core
MADAR EKM = stratbox
MADAR Communication = UI
MADARAII = scenarios
```

MADAR определяет **семантических владельцев смысла**, а репозитории Strategy Box являются **реализациями и carriers**. Один репозиторий может реализовывать обязанности нескольких MADAR owners, а один MADAR owner может материализоваться сразу в нескольких репозиториях.

Целевая картина:

```text
                             MADAR
          semantic architecture / method / knowledge
                               │
                               ▼
                         STRATEGY BOX
┌─────────────────────────────────────────────────────────────────────┐
│ stratbox                                                            │
│ domain/business capabilities, source semantics, canonical data,     │
│ analytical computation, validation, domain provenance               │
│                                                                     │
│ stratbox-core                                                       │
│ platform-neutral product/application semantics: Work, capability,   │
│ scheme, activation binding, execution plan, run, result, authority, │
│ collaboration, settings resolution, artifact/runtime contracts      │
│                                                                     │
│ stratbox-host                                                       │
│ durable execution carrier/service: persistence, scheduler, jobs,    │
│ workers, API/events, background/remote/shared-node operation         │
│                                                                     │
│ stratbox-design                                                     │
│ derived visual/representation system; tokens, patterns, artifact    │
│ style language                                                       │
│                                                                     │
│ stratbox-windows / stratbox-web / stratbox-android                  │
│ platform-specific projections and interaction adapters              │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                            AppDock
        installation / node / environment / lifecycle / connection
        host substrate / recovery / platform health / deployment
```

Рядом подключаются environment-specific plugin packages через нейтральный capability contract. Их конкретная реализация остаётся за приватной границей и не должна попадать в публичные репозитории.

## 0.1. Центральное семантическое исправление

Накопленная Strategy Box линия пришла к `Operation → Scenario → Case → Job → OperationRun → Attempt`, а PROTOS-ветка — к `Thread → Work → Runs → Schemes/Operations → Cognitive Activations → Artifacts`.

MADAR показывает, что целевую модель следует выпрямить:

```text
Commission / Intent / Governing basis
                ↓
               Work
        ┌───────┼────────┐
        ▼       ▼        ▼
      Run     Run      Run ...
        │
        ▼
Activation Binding
        │
        ▼
ExecutionPlan
        │
        ▼
Job / OperationRun / Attempt
        │
        ▼
Observed execution/effects
        │
        ├── Result
        ├── Artifact(s)
        ├── Evidence / Provenance
        ├── Diagnostics / Problem refs
        └── residual obligations
                ↓
Assessment / Acceptance / Handoff / Closure
```

Критические различия:

```text
Work ≠ Run
Run ≠ Job
Job ≠ Operation
Operation ≠ Capability meaning
Capability ≠ Authority
Execution success ≠ intended effect
Result ≠ Artifact
Evidence ≠ Result
Result quality ≠ Acceptance
Acceptance ≠ deployment/effect
Message ≠ Work state
Thread ≠ Work
Log ≠ truth
Presence ≠ authority
Background ≠ отдельный тип работы
AI actor ≠ special bypass path
```

Это главный архитектурный итог.

## 0.2. Что сохраняется и что переосмысливается

По смыслу сохраняются:

- pure business/domain boundary `stratbox`;
- platform-neutral application/runtime owner;
- shared headless host;
- typed Request/Result;
- canonical operations;
- capability catalog;
- Machine Schemes;
- immutable ExecutionPlan;
- Work / Run split;
- Artifact as first-class durable result representation;
- SourceSnapshot and registry snapshot provenance;
- one execution engine for foreground/background/remote/AI;
- stable Resource/Artifact references instead of paths;
- structured observability and physical evidence logs;
- explicit authority, approval and effect boundaries;
- client surfaces as projections, not truth owners;
- plugins as explicitly activated capability providers;
- design tokens / ArtifactStyleSet as representation policy;
- PROTOS as optional cognitive participant.

Переосмыслить требуется:

- `Scenario` как универсальную основу;
- `Case` как смешение Work и Run;
- `BackgroundProcess` как отдельную execution system;
- общий `success/failure` как достаточный итог Work;
- local JSON-history как каноническое состояние;
- UI state как Settings;
- file path как identity;
- artifact path как identity;
- plugin discovery как activation;
- несколько reviewers как proof of independence;
- clean diagnostic result как proof of whole-system health;
- chat как Work truth;
- API-callability как proof of cognitive readiness.

## 0.3. Итоговая формула

> **Strategy Box должен стать MADAR-aligned execution and knowledge workbench: доменные способности описаны как типизированные и доказуемые capabilities; человеческая или машинная работа существует как durable bounded Work; execution является отдельной наблюдаемой реализацией; результаты, артефакты, evidence, authority и acceptance разделены; интерфейсы показывают производные представления; AppDock и environment plugins обеспечивают внешнюю среду, не становясь владельцами доменного смысла.**

---

# 1. Исследовательская рамка и source hierarchy

## 1.1. MADAR

На момент исследования `ForestTiger-GH/MADAR@main`:

```text
be4dc2b3d53410286d37172e8ec7a8f071c518ea
2026-10-07
research: add B4 evidence, assurance, independence and bounded reliance synthesis
```

Изучены cold-entry/consolidation файлы, архитектурная записка от 2026-10-01, Stage 3 wave и текущий `spec/`.

Ключевой принцип:

> **one material information class → one authoritative semantic owner → multiple typed/derived routes.**

Целевая Product topology MADAR различает:

```text
about/
madar/
science/
guidance/
custom-packs/
skills/
examples/
madaraii/
dispatcher/
позже: automation / schemas / indexes / adapters
```

## 1.2. Fixed Stage 3 baseline

| Source | Commit |
|---|---|
| MADAR | `06722be8e4afbb97ea30899b7630a2bbb7a35914` |
| MADARAII | `37d4115d715554625da3123a186f44218fb1f8bc` |
| mandat-analytics | `22e384f9cf64e37bb23554d9050916f98438b9a1` |
| mandat-forecast | `67dde20286a9618109e2e2afab9e0837d454e7c5` |
| mandat-programming | `4abdc42c3dbda71eabaebb82e8b1aa4b05e6c52a` |
| mandat-communication | `f4e50aacd0e356e3bf99a60d271f69d263306c61` |
| mandat-evaluation-challenge | `c63a192d501e4cf4924158df691ca1418a5fb85d` |
| mandat-strategy-decision | `ba4f70780ba84c515a8efad280466897a0a0424f` |

Шесть `mandat-*` heads на момент проверки совпадают с этими срезами. `MADAR-supplements@main`: `bf8d3b95e26a3f68318ea5b1eb15ba610efe9e59`.

## 1.3. Fresh Stage 3 inputs

На `MADAR@main` присутствуют A1–A8 и B1–B4:

- A1 Constitution;
- A2 EOM;
- A3 Work/result;
- A4 participation/authority/programs;
- A5 durable Work state/artifacts/workspaces/recovery/handoff;
- A6 Engineering Knowledge;
- A7 knowledge synthesis/provenance/lifecycle/learning;
- A8 semantic relations/applicability/resolution;
- B1 goals/values/requirements/decisions/commitments;
- B2 meaning/representation/models/measurement/comparability;
- B3 structure/composition/state/time/causality/effects;
- B4 evidence/assurance/independence/freshness/reliance.

B5 `Authority, участие и взаимодействие` предусмотрен architecture note, но отдельный B5 Result на исследованном `main` ещё отсутствует. Эту область здесь следует считать хорошо обоснованной A4/A8/spec/specialist packages, но подлежащей повторной проверке после B5.

## 1.4. Strategy Box Research corpus

`ForestTiger-GH/stratbox@main`:

```text
bfce897c952cdf0d9971175010b681da7116ef8d
2026-10-07
Document consolidation research branch
```

В исследование сведён весь `02-base-study`: current-state core/windows, machine schemes, portability, scenarios/cascades, execution control, files/artifacts/formats, observability, plugin contract, PROTOS series, registry/source governance, multi-user, target core/design, web/self-hosted, UI/motion, automation/AI, artifact styles, visual system, settings.

`03-consolidation-research` уже определена как ветка сведения этого корпуса. Настоящий файл является прямым consolidation input.

---

# 2. Как правильно читать MADAR применительно к Strategy Box

## 2.1. MADAR — не обязательная runtime dependency

Target Strategy Box должен прежде всего обеспечить **semantic alignment**, а не жестко встроить сегодняшние MADAR IDs/API.

MADAR сам движется:

```text
Research
→ Science
→ MADAR WHAT
→ Guidance
→ Packs
→ Skills
→ Examples
→ MADARAII
→ Dispatcher
→ Automation/machine views
```

Поэтому сейчас Strategy Box должен закрепить owner boundaries, product objects, provenance/evidence/authority distinctions и machine-readable capability contracts. Жёсткая машинная интеграция с MADAR разумна после стабилизации её machine layer.

## 2.2. Реализация не становится semantic owner

`stratbox-core.Work` может материализовать EWM, но `stratbox-core != EWM`.

`ArtifactStyleSet` реализует representation policy, но не владеет EKM claims.

`JobManager` координирует execution, но не определяет completion Work.

`ScenarioChat` показывает Work, но не является Work state.

## 2.3. Один owner, много projections

```text
Work owner → Windows card / Web card / Android card / AI context
Artifact owner → Explorer row / chat attachment / preview
RegistrySnapshot owner → UI freshness label
```

Projection не получает authority от удобства или близости к пользователю.

---

# 3. Constitutional invariants для Strategy Box

1. **Meaning ≠ representation.**
2. **Object state ≠ Work state ≠ Knowledge state.**
3. **Claim ≠ evidence.**
4. **Recommendation ≠ Decision.**
5. **Capability ≠ Authority.**
6. **Available ≠ applicable.**
7. **UNKNOWN ≠ false/failure.**
8. **Derived projection ≠ semantic owner.**
9. **Execution success ≠ intended effect.**
10. **Assessment ≠ acceptance.**
11. **Message ≠ commitment без соответствующего authority/context.**
12. **Machine-readable graph ≠ owner truth.**

Эти distinctions должны переживать любой carrier: Python, JSON, DB, UI, report, remote API, AI summary.

---

# 4. EOM: object system Strategy Box

Target object classes:

### Product/environment
- Strategy Box world/installation;
- Node;
- application runtime;
- client surface;
- plugin binding;
- ResourceSpace;
- Workspace.

### Domain/data
- SourceDescriptor;
- SourceSnapshot;
- RegistryAsset/RegistrySnapshot;
- canonical dataset;
- domain model.

### Capability
- CapabilityDefinition;
- CanonicalOperation;
- MachineScheme;
- CapabilityEnvelope.

### Work/execution
- Work;
- Run;
- ActivationBinding;
- ExecutionPlan;
- Job;
- OperationRun;
- Attempt.

### Result/knowledge
- Result;
- Artifact;
- EvidenceReference;
- ProvenanceManifest;
- ProblemOccurrence/ProblemRef;
- Assessment/Acceptance.

### Interaction/governance
- Principal;
- Actor;
- Participant;
- Role;
- AuthorityGrant;
- Assignment;
- Approval;
- Thread;
- Message;
- Presence;
- AutomationSpec/Trigger.

Identity не должна равняться location:

```text
artifact_id ≠ path
resource_id ≠ URI
source_snapshot_id ≠ URL
registry_snapshot_id ≠ filename
Work ID ≠ Thread ID
```

B3 также запрещает считать, что component success доказывает whole-system property.

---

# 5. EWM: Work как центральная product entity

## 5.1. Work определяется Commission

Commission может прийти из:

- chat/message;
- scenario launch;
- schedule/event;
- assignment;
- API;
- peer request;
- approved AI proposal.

Carrier не определяет Work. Work должен сохранять governing meaning:

- purpose;
- intended consumer/use;
- subject/scope;
- owed Result;
- constraints;
- Authority;
- material evidence/acceptance requirements;
- stop/reopen conditions.

## 5.2. Thread ≠ Work

Thread — interaction container. Один Thread содержит несколько Work; один Work переживает много сообщений, Runs, clients, restarts и participants.

## 5.3. Case следует разложить

```text
Work
  semantic purpose / scope / obligations / closure

Run
  concrete execution trajectory

CaseView
  user-facing projection
```

`Case` может остаться UI vocabulary, но не единственным canonical object.

## 5.4. Completion ≠ positive result

Inquiry может завершиться отрицательным/неопределённым результатом и всё равно быть completed Work, если он выполнил Commission.

## 5.5. Closure = residual disposition

Нужно знать unresolved effects, follow-up ownership, monitoring, acceptance, handoff and reopen triggers.

---

# 6. Execution semantics

Target chain:

```text
Work
→ Run
→ ActivationBinding
→ ExecutionPlan
→ Job(s)
→ OperationRun(s)
→ Attempt(s)
→ observed effects
→ Result / Artifacts / Evidence
→ Assessment / Acceptance / Closure
```

### ActivationBinding
Разрешает exact capability version, sources, registries, resources, permissions, plugins, outputs, style, backend, time/vintage.

### ExecutionPlan
Immutable/versioned contract concrete Run.

### Job
Schedulable host unit.

### OperationRun
Semantic invocation of canonical operation.

### Attempt
Physical attempt. Retry creates new Attempt only when operation/idempotency semantics это допускают.

---

# 7. EKM: knowledge-bearing analytical system

`stratbox` должен различать, где materially relevant:

```text
observed
reported
derived
inferred
estimated
forecast
scenario
hypothesis
contested
unknown
```

Не допускаются silent promotions:

```text
reported → world fact
derived → observed
scenario → forecast
forecast → target
model output → Decision
```

Target source chain:

```text
SourceDescriptor
→ Fetch
→ SourceSnapshot
→ validation
→ canonical data
→ transformation/model
→ Result
→ Artifact/projection
```

Сохраняются identity, version/vintage, transformations, assumptions, warnings, provenance and reliance bounds.

SORS — локальный эталон дисциплины доказательности, а не template сложности для каждого домена.

---

# 8. Knowledge synthesis and learning

```text
historical run record
≠ current knowledge
≠ current Product rule
≠ learned/admitted capability
```

Чтобы lesson стал learning:

1. сформулировать candidate lesson;
2. определить owner;
3. проверить grounds/applicability;
4. reconcile with current state;
5. admit/reject/limit;
6. сохранить lineage.

PROTOS-generated Scheme:

```text
proposal → validation → evidence → challenge → admission → versioned capability
```

Один успешный запуск не делает Scheme trusted production fast path.

---

# 9. B1: goals, requirements, decisions, commitments

Goal не обязателен для Inquiry. Work может начинаться с question/exploration.

Различать:

```text
Recommendation
→ Decision
→ Commitment
→ Execution/effect
→ Outcome
```

AI/analysis может recommend; Decision требует Authority.

Approval — bounded authority-bearing disposition over exact object/version/effect/conditions, а не декоративная кнопка.

---

# 10. B2: meaning, representation, models, measurement, comparability

- DataFrame полезен внутри Python, но не единственный external semantic contract.
- Format ≠ semantic type.
- `FormatRegistry` описывает representation capabilities; semantic adapter/domain parser — meaning.
- `ArtifactStyleSet` может менять visual representation, но не values, units, classification, epistemic status или formulas.
- UI/report/API projections обязаны сохранять materially relevant meaning.

---

# 11. B3: state, time, causality and effects

Разделять:

```text
ObjectState
WorkState
RunState
JobState
AttemptOutcome
KnowledgeState
AcceptanceState
SurfaceState
NodeHealthState
```

Typed time:

- publication/effective/fetch/discovery/vintage;
- Work commissioned/started/result-established/accepted/closed;
- forecast origin/cutoff/horizon/issuance/evaluation.

Effect semantics:

```text
request accepted
≠ attempt started
≠ backend acknowledged
≠ effect observed
≠ effect verified
```

---

# 12. B4: evidence, assurance, independence, freshness

Health/conformance должны быть claim-specific.

Пример:

```text
package loaded
plugin compatible
secret backend ready
storage reachable
write test passed
source reachable
registry current
```

не сводить к одному недифференцированному “green”.

Independence — causal property, не число reviewers/agents.

Freshness — relation to intended reliance. Один snapshot может быть годен для historical reproduction и stale для current decision.



---

# 13. B5–B9: concerns, особенно важные Strategy Box

Отдельный B5 Result ещё не опубликован на исследованном `MADAR@main`, поэтому Authority/interaction mapping ниже основан на A4/A8/B1, текущем spec и specialist packages.

## 13.1. Authority, participation and interaction

Различать:

```text
Principal
Actor
Participant
Role
Skill
Capability
AuthorityGrant
Permission
Approval
Work ownership
```

Нельзя:

```text
participant → may cancel any Work
AI actor → may execute destructive action
technical capability → granted authority
```

## 13.2. Human and organizational factors

Low-entropy UI и progressive disclosure должны уменьшать operator burden, но нельзя скрывать materially relevant:

- risk;
- authority;
- irreversibility;
- uncertainty;
- recovery;
- current Work state.

## 13.3. Change, continuity and recovery

Recovery должен восстанавливать governing state:

- Work meaning;
- current Run;
- plan;
- known/unknown effects;
- artifacts/evidence;
- pending approvals;
- residual obligations.

Восстановить последнюю UI card недостаточно.

## 13.4. Risk, trust and safety

Особенно активируются для:

- destructive file operations;
- plugin activation;
- remote execution;
- AI action;
- publication/sharing;
- secrets;
- multi-user shared resources.

## 13.5. Resources and proportionality

Не каждый Work требует полного provenance graph, независимого challenge, дорогого solver или explicit acceptance UI. Модель должна позволять включать эти вещи пропорционально consequence/uncertainty/reversibility.

---

# 14. Activity Methods: что реально нужно Strategy Box

## 14.1. Framing / Inquiry

Natural-language ingress не должен автоматически становиться execution.

```text
user request
→ qualify/frame
→ Work Candidate
→ route
```

Inquiry может завершиться qualified unknown/negative result.

## 14.2. Analysis

`mandat-analytics` даёт особенно важные reusable analytical operations:

```text
Comparison
Normalization / Reconciliation Bridge
Decomposition
Explanatory / Causal Interpretation
```

Ключевые firewalls:

```text
normalization ≠ correction of source truth
decomposition ≠ causal explanation
same label ≠ same construct
```

## 14.3. Forecasting

Будущий Forecast layer различает:

```text
Forecast
Scenario
Stress Path
baseline/convention projection
Counterfactual
Target
Plan
Strategy
Decision/Policy
Warning
Observation
Model Output
```

Forecast Vintage исторически immutable. Важны information cutoff и ex-ante integrity.

## 14.4. Design

Design Activity относится к development/product work и к user Work только при реальной design задаче. `ExecutionPlan` сам по себе не означает Design Activity.

## 14.5. Strategy and Decision

Если Strategy Box развивается в decision/strategy workbench:

```text
Strategy ≠ Plan
Strategy ≠ Forecast
Decision ≠ Recommendation
```

Strategy — persistent coordination object across coupled choices, commitments/options, time, resources, path dependence and adaptation.

## 14.6. Planning

MADAR Planning шире runtime DAG. ExecutionPlan — concrete runtime plan; не любая DAG-композиция является Planning Activity.

## 14.7. Realization / Integration

Programming/Software Realization относится прежде всего к разработке продукта. В product Work realization появляется, если Strategy Box materializes/publishes/changes managed objects.

## 14.8. Evaluation / Challenge

Evaluation checks criteria. Challenge seeks defeaters/alternatives.

```text
Evaluation ≠ Acceptance
Challenge ≠ Authority
```

## 14.9. Communication

Chat/report/notification становятся Communication Work, когда materially important:

- payload;
- audience;
- intended action;
- evidence;
- modality;
- repair;
- recipient effect.

## 14.10. Operation / Learning

Operation covers observation/intervention/recovery in live system. Learning requires qualified update, not merely a saved log.

---

# 15. Шесть mandat-пакетов: целевой вклад

| Repository | Что Strategy Box должен унаследовать по смыслу |
|---|---|
| `mandat-analytics` | inference ceilings, comparison/normalization/decomposition/explanation, banking/corporate/event Packs, currentness/default semantics, specialist bindings |
| `mandat-forecast` | Forecast identity, cutoff/vintage, uncertainty semantics, forecastability, candidate vs issued Vintage, evaluation boundary |
| `mandat-programming` | realization boundary, effect/error/resource semantics, durable/public contracts, representation preservation, computation-as-evidence |
| `mandat-communication` | joint action, payload/recipient/context, representation modality, epistemic communication, repair, artifact lineage |
| `mandat-evaluation-challenge` | Evaluation vs Challenge vs Assurance, criteria authority, findings/reliance, causal independence |
| `mandat-strategy-decision` | knowledge/values/Authority separation, Decision/commitment/effect lifecycle, Strategy as persistent coordination object, monitoring/revalidation |

Эти packages являются integration inputs, а не отдельными standards внутри Strategy Box.

---

# 16. MADAR-supplements: наиболее важные дополнения

`MADAR-supplements` остаётся non-authoritative Research input, но даёт сильные практические идеи.

## 16.1. Output-status preservation

```text
candidate hypothesis ≠ diagnosis
conditional consequence ≠ probability
robust action ≠ truth of one world
minimal UI ≠ simple underlying system
```

Strategy Box обязан сохранять epistemic operator через UI, artifacts, summaries and notifications.

## 16.2. Conditional consequence analysis

```text
IF H → propagate X
```

не означает:

```text
H likely
```

## 16.3. Robust action under unresolved hypotheses

Bounded action возможен при unresolved uncertainty, если сохранены protected constraints, reversibility, triggers, evidence and adaptation path.

## 16.4. Low-Entropy Interfaces

Минимизировать controls можно, но нельзя стирать semantics, меняющую allowed action/Authority/safety/reversibility/recovery/result meaning.

## 16.5. Temporal Priority Architecture

UI должен приоритизировать running/blocked/approval-required/shared-degraded/stale/deadline/new-artifact, а не просто chronologically latest.

## 16.6. Governed Adaptive Interfaces

Adaptive UI допустим только при сохранении policy, explainability, Authority and action semantics.

## 16.7. Epistemic Communication

```text
"Источник сообщает P" ≠ "P"
"Если H, то X" ≠ "Ожидается X"
```

Особенно важно для AI summaries.

---

# 17. Целевая Strategy Box ontology

## 17.1. Capability layer

### CapabilityDefinition

Описывает:

- semantic purpose;
- input/output;
- applicability;
- effects;
- limitations;
- validity/evidence;
- resource class;
- required environment capabilities.

### CanonicalOperation

Самостоятельная machine capability с stable identity.

### MachineScheme

Versioned reusable composition:

```text
Operations/Schemes
+ dependencies
+ guards
+ typed fan-in/out
+ effect constraints
```

### CapabilityEnvelope

Хранит validity/applicability/evidence/known limitations/deoptimization triggers.

## 17.2. Work layer

### Work
Durable bounded undertaking.

### Run
Concrete execution trajectory inside Work.

### ActivationBinding
Resolved context for Run.

### ExecutionPlan
Immutable versioned concrete plan.

### Result
Semantic result established.

### Acceptance
Qualified relation to exact result/object/version/use/criteria/Authority.

## 17.3. Execution layer

### Job
Schedulable unit.

### OperationRun
Invocation of CanonicalOperation.

### Attempt
Physical attempt.

### ProgressEvent
Observed progress, not Work truth.

### EffectReceipt
Evidence of external effect when material.

## 17.4. Artifact/knowledge layer

### Artifact
Stable durable logical output.

### SourceSnapshot
Immutable captured external source.

### RegistrySnapshot
Versioned reference state.

### EvidenceReference
Reference to grounds.

### ProvenanceManifest
Sources, registries, operations, parameters, environment, transforms.

## 17.5. Interaction/authority layer

### Principal
Security/account/ownership context.

### Actor
User/system/AI/peer entity.

### Participant
Actor participating in Work.

### Role
Work-local function.

### AuthorityGrant
Scoped authorization.

### Assignment
Coordination/requested responsibility.

### Approval
Authority-bearing bounded decision.

### Thread
Interaction container.

### Message
Interaction event/carrier.

### Presence
Ephemeral projection, not authority.

## 17.6. Automation

### AutomationSpec
Trigger policy for proposing/creating Work.

### TriggerOccurrence
Concrete trigger event.

AutomationSpec does not own execution state.

## 17.7. Diagnostics

### Diagnostic
Expected structured warning/failure/observation.

### ProblemOccurrence / ProblemRef
Canonical platform/product problem identity and safe reference.

### LogRef / EvidenceRef
Physical evidence references.

---

# 18. Fate of Scenario / Cascade / Command terminology

## 18.1. Command

Не делать фундаментальным noun. Конкретное значение обычно является Mechanism, CanonicalOperation или Job control action.

## 18.2. Scenario

Сохранить как user-facing curated Scheme/Work template.

Operation не обязана автоматически иметь Scenario wrapper.

## 18.3. Cascade

Сохранить как user-facing composite Scheme family. Canonical execution composition — `MachineScheme`.

Итого:

```text
Capability Library
├─ Operations
├─ Scenarios
├─ Cascades
├─ Analytical Schemes
└─ admitted generated Schemes
```

UI показывает applicable high-level subset.

---

# 19. `stratbox`: целевая MADAR-aligned роль

`stratbox` остаётся pure domain/business library.

## 19.1. Owns

- domain source semantics;
- canonical datasets;
- parsers/normalizers;
- domain validation;
- analytical/reconstruction algorithms;
- domain models;
- CanonicalOperation implementations;
- domain CapabilityDefinitions;
- Source Catalog contracts/resources;
- Reference Registries;
- generic format/codecs needed by data processing;
- domain provenance;
- domain export operations.

## 19.2. Does not own

- user/session;
- Work persistence;
- multi-user queue;
- scheduler;
- chat;
- presence;
- UI settings;
- AppDock lifecycle;
- remote transport;
- generic notifications;
- client layout.

## 19.3. Activity-aware, not MADAR-copy

Domain operation может описывать transformation/claim/applicability semantics без встраивания полного MADAR tree в runtime.

---

# 20. `stratbox-core` vs `stratbox-host`: синтез двух research-линий

В `02-base-study` возникли две гипотезы:

1. `stratbox-core` = общий product/application runtime;
2. `stratbox-host` = headless canonical runtime для web/shared/remote.

Их не следует считать взаимоисключающими.

MADAR owner/carrier separation даёт чистое решение.

## 20.1. `stratbox-core`

Platform-neutral semantic/application owner:

- Work/Run;
- capability/scheme catalog semantics;
- ActivationBinding;
- ExecutionPlan;
- Result/Acceptance;
- artifact metadata contracts;
- authority/permissions semantics;
- assignments/approvals;
- collaboration semantics;
- settings resolution;
- client-neutral DTO/events.

Importable without Qt/browser/OS UI.

## 20.2. `stratbox-host`

Long-lived process/service carrier:

- persistence;
- transactions;
- queue;
- scheduler;
- workers;
- Job Manager;
- background;
- remote clients;
- HTTP/API/event transport;
- session/auth adapter;
- database repositories;
- crash/restart recovery;
- resource arbitration;
- node-wide concurrency.

Host uses `stratbox-core`.

## 20.3. Why this resolves the conflict

```text
semantic owner ≠ deployment carrier
```

Same core can be carried by embedded/light host, Linux headless host, Windows service, container or later alternative.

---

# 21. Windows / Web / Android

Clients own:

- rendering;
- navigation;
- local drafts;
- local non-sensitive prefs;
- reconnect state;
- platform integration.

Clients do not own:

- Work truth;
- shared jobs;
- permission truth;
- artifact identity;
- node-wide presence;
- canonical history.

Current Windows UI can remain visually familiar. Its modes become projections of canonical state.

Android should copy shared semantic/client contracts, not Qt/Desktop implementation.

---

# 22. AppDock: external platform owner

AppDock naturally owns:

- install/update;
- environment;
- Node;
- activation;
- managed directories;
- process lifecycle;
- platform health;
- host substrate;
- remote connection substrate;
- platform recovery;
- deployment/package graph;
- secure environment capability delivery.

Boundary:

```text
AppDock knows process lifecycle / platform condition.
Strategy Box knows Work/Run/result semantics.
```

`stratbox-host` is product service; AppDock is platform manager around it.

---

# 23. Plugins: target semantics

Corporate/environment plugin is a trusted capability provider, not magical import.

Target chain:

```text
discover
→ compatibility
→ explicit selection
→ capability binding
→ activation
→ readiness
→ runtime
→ conformance
```

Important:

```text
installed ≠ selected
selected ≠ ready
ready ≠ applicable
```

Public `stratbox`/`stratbox-windows` contain only neutral versioned contracts, vocabulary and synthetic/reference test providers. Private identifiers/implementation details stay outside public repos.

Plugin does not become domain truth owner merely by supplying environment infrastructure.

---

# 24. Sources and registries

Distinguish:

```text
Reference Registry
Policy Overlay / Set
Source Catalog
Domain Rule Registry
Runtime Capability Registry
```

Common governance does not imply one folder.

Recommended lifecycle:

```text
Git authoring
→ validation/tests
→ immutable build asset
→ AppDock-managed update
→ read-only runtime consumer
```

Material Run pins:

- stratbox revision/build;
- Capability/Scheme version;
- SourceSnapshot IDs;
- RegistrySnapshot IDs;
- parameters;
- capability bindings;
- ArtifactStyleSet digest;
- ExecutionPlan hash;
- backend/runtime identity.

---

# 25. FileStore, ResourceSpace, FormatRegistry

## FileStore
Low-level storage transport; format-agnostic.

## ResourceSpace
Higher-level stable address space using `ResourceRef`/`ItemRef`.

## ArtifactStore
Logical durable result system. `FileStore ≠ ArtifactStore`.

## FormatRegistry
Representation capability owner: detection/read/write/container/materialization.

Domain operation declares accepted semantic/file formats.

Recommended policy: **read broad / write narrow**.

---

# 26. Artifact architecture

Artifact minimum:

```text
artifact_id
kind
version/revision
producer Work/Run
content parts
content hashes
created_at
actor
provenance
storage refs
visibility
retention
```

Managed Work artifacts are immutable/versioned. Workspace may be mutable.

Delete:

```text
logical tombstone
→ reference/retention check
→ GC
```

And:

```text
Result ≠ Artifact
```

---

# 27. ArtifactStyleSet / InterfaceTheme / metadata

Keep three owners distinct:

```text
InterfaceTheme
ArtifactStyleSet
ArtifactMetadataContext
```

InterfaceTheme is client presentation.

ArtifactStyleSet is versioned cross-format representation policy, pinned per Run.

ArtifactMetadataContext includes creator/title/actual actor/Work/Run/provenance.

Plugin may contribute ArtifactStyleSet, but cannot change Strategy Box shell/UI.

---

# 28. Settings

Permanent user-facing Settings should remain small:

```text
Appearance
Artifacts & Reports
Plugins
Notifications — only when capability exists
```

Not Settings:

```text
window geometry
selected tab
chat filter
last scenario
form drafts
panel widths
```

These belong to SurfaceState/RecentState/DraftState.

Managed values such as workspace/data/update/log/security/plugin deployment come from runtime/AppDock policy.



---

# 29. Observability: evidence, а не альтернативная истина

## 29.1. Один execution spine

Foreground, background, scheduled, remote и AI execution должны идти через одну модель Work/Run/Job.

Отдельный “background runtime” создаст вторую семантику статусов, ошибок и recovery.

## 29.2. Terminal execution outcome

Полезный технический набор:

```text
SUCCESS
PARTIAL
CANCELLED
FAILURE
UNKNOWN
```

Но это outcome execution boundary, а не универсальный Work status.

`SUCCESS` может означать:

> executor получил доказательство успешного завершения заявленного invocation.

Он сам по себе не означает:

- result accepted;
- business objective achieved;
- external system permanently changed;
- source data correct;
- user approved output.

## 29.3. Structured problems

Целевая цепочка:

```text
Diagnostic
→ safe ProblemDraft
→ canonical ProblemOccurrence
→ ProblemRef
```

Raw Python exception / traceback / stdout / stderr остаются technical evidence.

## 29.4. Physical logs

Обязательны:

- bounded;
- rotating;
- structured where possible;
- redacted;
- node-local;
- linked by `LogRef`.

Process-level crash лучше наблюдать внешнему parent runtime/AppDock, потому что погибший process может не успеть корректно зарегистрировать собственную проблему.

## 29.5. Shared conditions

Multi-user system не должен broadcast каждую чужую ошибку.

Shared warning создаётся, когда impact действительно общий:

- Node degraded;
- shared storage unavailable;
- common source unavailable;
- workspace corruption;
- shared runtime incompatibility;
- repeated background failure.

---

# 30. Cancellation, retry, resume and unknown effects

## 30.1. Cancellation cooperative

```text
cancel requested
→ token propagates
→ operation reaches safe point
→ terminal outcome
```

`QThread.terminate()` и process kill — не штатная cancellation.

## 30.2. Terminal truth beats late control request

Если operation уже committed success, поздний cancel request не переписывает историю.

## 30.3. Force terminate

Если process убит после возможного внешнего effect:

```text
AttemptOutcome = UNKNOWN
```

до reconciliation.

## 30.4. Retry

Retry policy зависит от:

- idempotency;
- effect class;
- observed acknowledgement;
- compensability;
- freshness;
- retry budget.

Нельзя иметь один универсальный “retry 3 times” для всех operations.

## 30.5. Resume

Resume обязан revalidate:

- plan/version;
- already completed nodes;
- known/unknown effects;
- artifact availability;
- current sources/registries;
- changed permissions/Authority;
- changed environment capabilities.

`resume(step_index)` недостаточно.

---

# 31. Automation and background

Background — execution origin/mode, а не особый Work kind.

```text
AutomationSpec
→ TriggerOccurrence
→ Work proposal/instantiation
→ ordinary Work/Run/Job engine
```

Scheduler owns trigger delivery and time semantics, но не Work meaning.

Нужны explicit misfire policies:

- skip;
- run once now;
- bounded catch-up;
- revalidate before run.

Automation может включать AI stage только там, где нужен semantic judgment. Deterministic stages остаются deterministic.

---

# 32. AI / PROTOS

## 32.1. Optional cognitive participant

Strategy Box должен полностью работать без PROTOS/LLM.

PROTOS добавляет cognition, а не фундамент product state.

## 32.2. Host sovereignty

PROTOS может:

- discover capabilities;
- propose Work;
- build candidate plan;
- invoke allowed capabilities;
- interpret Results;
- request approval;
- challenge.

Strategy Box:

- validates;
- resolves Authority;
- creates canonical Work/Run;
- commits product state;
- owns domain effects.

## 32.3. Five integration channels

Future PROTOS integration requires:

1. discovery / semantic;
2. resolution / composition;
3. execution;
4. observation / evidence;
5. learning / admission.

HTTP, MCP, Python or IPC are transport options, primarily for channel 3.

## 32.4. Cognitive Activation

Persistent Actor must be distinct from individual model executions:

```text
PROTOS Actor
├─ CognitiveActivation A
├─ CognitiveActivation B
└─ CognitiveActivation C
```

This allows isolated parallel cognition and prevents accidental shared scratch state.

## 32.5. Deoptimization

Compiled Scheme needs applicability envelope and guards.

If envelope violated:

```text
do not force fast path
→ deopt to broader cognition / alternate capability / human
```

## 32.6. Generated capability admission

Generated code/scheme remains candidate until:

- validated;
- verified;
- challenged where needed;
- given explicit scope/limitations;
- admitted/versioned.

---

# 33. Multi-user and collaboration

## 33.1. One node — one operational truth

Several clients must observe one shared Work/Run/job/artifact state.

Qt/Web/Android client cannot be authoritative owner of shared cases.

## 33.2. Presence is ephemeral

Presence answers:

> who appears active now?

It does not answer:

- who owns Work;
- who may approve;
- who may cancel;
- who authored historical result.

## 33.3. Unread/read is per user

Use cursor/receipt:

```text
UserReadCursor
node_id
user_id
last_seen_seq
```

rather than shared `unread: bool`.

## 33.4. Assignment

Assignment is a durable shared coordination object:

```text
assignment_id
status
assignee
author
description
Work/Artifact/Problem refs
due_at?
revision
```

But Assignment does not itself grant Authority.

## 33.5. Shared Work without shared memory

Multi-PROTOS topology should federate bounded Work:

```text
typed Work offer
→ peer cognition
→ typed Result / Artifact / Evidence
→ reconciliation
```

not merge private memory into one mutable pool.

---

# 34. Communication: chat and artifacts as joint action

## 34.1. Message is a carrier

A message may be:

- question;
- request;
- report;
- proposal;
- challenge;
- approval;
- decision communication.

Semantic effect depends on actor/Authority/context.

## 34.2. Communication artifact lineage

Report/summary/notification/chat rendering should preserve:

- source Result;
- transformation;
- claim status;
- intended audience/use;
- version.

## 34.3. Modality selection

One Result may have:

- short chat summary;
- table;
- chart;
- Excel;
- DOCX;
- notification.

Choice should follow recipient task, complexity and material semantic preservation.

## 34.4. Repair

If communication distorted meaning, correction should create explicit correction/supersession relation, not silently rewrite historical evidence.

---

# 35. Security, trust and governed effects

## 35.1. Deny-by-default for remote/shared access

Especially:

- Work details;
- artifacts;
- source data;
- logs;
- workspace resources;
- approvals;
- private collaboration.

## 35.2. Secrets stay outside model and UI payloads

AI receives:

```text
auth_status = READY / NEEDS_USER / UNAVAILABLE
```

but never credential value.

## 35.3. Destructive actions

Require proportionate:

- explicit effect class;
- Authority;
- optional approval;
- plan/dry-run;
- strict success semantics;
- effect evidence;
- recovery/compensation.

---

# 36. Evaluation, Challenge, Assurance, Acceptance

These are four different things.

### Evaluation
Checks against criteria.

### Challenge
Actively seeks defeaters, counterexamples and hidden assumptions.

### Assurance
Builds bounded grounds for reliance.

### Acceptance
Authorized disposition by appropriate owner.

They can be physically co-located in a small Work, but must not be semantically collapsed.

A Jester/red-team function should activate by failure/consequence profile, not exist as mandatory role in every Work.

---

# 37. MADARAII vs Strategy Box Machine Schemes

Это одна из принципиальных границ.

## 37.1. MADARAII / bounded reusable Work

Future target semantics require independent Work meaning:

- selection condition;
- readiness;
- Authority/boundary;
- meaningful Result;
- substantial action geometry;
- stop;
- recovery;
- result validation;
- downstream use/lifecycle.

## 37.2. Machine Scheme

Strategy Box Scheme is reusable machine execution composition:

- operations;
- dependencies;
- typed inputs/outputs;
- guards;
- branches;
- effects.

## 37.3. They overlap, but are not identical

```text
every MachineScheme ≠ Madaraiya
Madaraiya ≠ necessarily MachineScheme
```

A parser DAG usually lacks independent Work meaning.

A Madaraiya may involve human judgment, external decisions or non-machine steps.

Recommended relation:

```text
Madaraiya / bounded Work definition
    may reference
MachineScheme / Capability
```

---

# 38. Dispatcher and capability resolution

Strategy Box research already found a product-specific resolver:

```text
task signature
→ hierarchical capability discovery
→ semantic contract/envelope
→ applicability
→ Authority
→ validity/currentness
→ ActivationBinding
→ ExecutionPlan
```

This is strongly compatible with future MADAR Dispatcher ideas.

But it should remain product-specific realization, not claim to own generic MADAR routing semantics.

---

# 39. `stratbox-design`

Design layer belongs mainly to:

- product Guidance;
- Examples/defaults;
- representation realization;
- platform adaptation.

It must preserve B2 meaning/representation constraints.

## 39.1. Low entropy

Correct simplification:

```text
hide implementation detail
preserve materially relevant control semantics
```

## 39.2. Accessibility

Status cannot rely on color alone.

## 39.3. Motion

Motion communicates transitions/state but does not own state truth.

---

# 40. Recommended repository topology

```text
ForestTiger-GH/
│
├─ stratbox
│   pure domain/business/data capabilities
│
├─ stratbox-core
│   platform-neutral application semantics
│
├─ stratbox-host
│   durable headless service/runtime carrier
│
├─ stratbox-design
│   shared design / representation language
│
├─ stratbox-windows
│   Windows client + desktop adapters
│
├─ stratbox-web
│   browser client
│
├─ stratbox-android
│   Android client
│
└─ environment-specific extension packages
    private / external as appropriate
```

AppDock remains separate universal platform.

`stratbox-core` and `stratbox-host` may physically share one repository if convenient. The **semantic boundary** is more important than repository count.

---

# 41. Ownership matrix

| Concept | MADAR family | Strategy Box semantic owner | Main realization |
|---|---|---|---|
| Domain metric/source semantics | EOM/EKM + specialist Analysis | `stratbox` | domain packages |
| SourceDescriptor/Snapshot | EOM/EKM/B4 | `stratbox` | `sources` |
| RegistrySnapshot | EOM/EKM/B2/B4 | `stratbox` | `registries` |
| CanonicalOperation | Activity/specialist capability | `stratbox` | operations |
| CapabilityDefinition | applicability/activity binding | `stratbox` + core catalog | capability registry |
| MachineScheme | reusable composition | `stratbox-core` | scheme registry |
| Work | EWM | `stratbox-core` | Work service |
| Run | EWM/B3 | `stratbox-core` | runtime model |
| ActivationBinding | applicability/dispatcher | `stratbox-core` | resolver |
| ExecutionPlan | planning/execution | `stratbox-core` | planner |
| Job/Attempt | execution/operation | core semantics / host carrier | Job Manager |
| Result | EWM/EKM/activity | Work/domain owner | result store |
| Artifact | EOM/EWM/B2 | core artifact contract | ArtifactStore |
| Evidence/Provenance | EKM/B4 | domain/core | provenance |
| Acceptance | EWM/B1/B4 | core + authority owner | acceptance service |
| Thread/Message | B5/Communication | core collaboration | clients/host |
| Participant/Role | A4/B5 | core | collaboration |
| AuthorityGrant | B1/B5/security | core/policy | authorization |
| Presence | interaction projection | host | ephemeral service |
| Assignment | EWM/B5 | core | collaboration |
| AutomationSpec | planning/operation | core | scheduler binding |
| ProblemOccurrence | operations/observability | AppDock node + product refs | recorder |
| InterfaceTheme | B2 representation | design/client | design tokens |
| ArtifactStyleSet | B2/Communication | reporting contract | renderers |
| Plugin binding | applicability/platform/trust | extension runtime | core/AppDock deployment |
| SurfaceState | representation/local state | client | local persistence |

---

# 42. Что уже directionally correct в current Strategy Box

## `stratbox`

- core separated from UI;
- FileStore abstraction;
- raw source preservation;
- stable IDs emerging;
- typed Request/Result in mature domains;
- canonical data before presentation in strongest pipelines;
- SORS provenance/evidence discipline;
- FRG plan/apply.

## `stratbox-windows`

- operation/scenario specs;
- schema-driven forms;
- cases/events/artifacts/logs;
- AppDock activation;
- degraded mode;
- semantic chat projector;
- actor kinds;
- portability seams.

## AppDock

- Node as managed environment;
- actions rather than shell;
- health/readiness;
- recovery;
- host/remote direction;
- agent-safe action concept.

---

# 43. Что не должно выжить как target doctrine

1. Hardcoded OperationRegistry inside client.
2. Auto-wrap every operation into user Scenario.
3. `ScenarioRunCase` as only durable unit.
4. One active scenario/global busy state.
5. Background as independent execution subsystem.
6. Local JSON as shared truth.
7. Shared `unread: bool`.
8. Path-oriented Artifact identity.
9. Silent failure/fallback.
10. UI prefs mixed with runtime binding.
11. Qt orchestration in shared runtime.
12. Current package/API compatibility as architectural constraint.
13. DataFrame as universal external ABI.
14. “Latest” resolution during execution without pinning exact snapshot.
15. Raw destructive filesystem primitives exposed to AI.
16. UI/frontend computing permissions.
17. Status color as sole status meaning.
18. Plugin install implying activation.
19. One health flag standing for many unrelated claims.
20. Logs/history treated as canonical semantic state.

---

# 44. State machines: preserve distinctions, avoid premature universal enums

## Work — illustrative

```text
proposed
→ admitted
→ ready / blocked
→ active
→ waiting
→ result-established
→ assessment/acceptance pending
→ completed / transferred / terminated
→ closed
→ reopened
```

This is not proposed as one mandatory universal enum. The target is to preserve distinctions and allow profile-specific simplification.

## Run

```text
planned → queued → running → cancelling → terminal
```

Terminal execution:

```text
SUCCESS / PARTIAL / CANCELLED / FAILURE / UNKNOWN
```

## Artifact

```text
draft → committed → available → superseded/tombstoned → retained/GC
```

## Approval

```text
requested → approved / rejected / expired / withdrawn
```

---

# 45. API implications

API should expose semantic resources, not GUI controls.

Conceptual resources:

```text
/me
/node

/capabilities
/schemes

/threads
/work
/runs
/jobs
/events

/results
/artifacts
/evidence

/resources
/workspaces

/assignments
/approvals

/automations
/notifications

/settings
/health
```

Avoid product API built around `open_right_panel`, `run_button`, `chat_card`.

---

# 46. Persistence

Canonical persistence should preserve product semantic objects and transactional relations.

Server/shared host:

- PostgreSQL strong production candidate;
- SQLite useful for local embedded/light host.

Semantics/migrations/tests should remain equivalent.

Artifact/blob payload storage can be separate from relational metadata.

Client-local storage:

- UserSettings;
- SurfaceState;
- DraftState;
- caches;
- reconnect hints.

---

# 47. Event architecture

Recommended pattern:

```text
authoritative state owner
+
meaningful append-only events
+
derived projections
```

Event fields where relevant:

```text
event_id
type
occurred_at
actor
subject refs
causation_id
correlation_id
schema_version
safe payload
```

For federation: stable message IDs, idempotency, ordering semantics, replay/dedup.

---

# 48. Workspace and durable Work state

Workspace is environment/resource grouping, not Work identity.

Separate:

```text
Workspace
ResourceSpace
WorkState
ArtifactStore
```

A Work can use multiple resources/workspaces; one workspace can serve many Work objects.

---

# 49. Conformance and assurance strategy

## Layer 1 — semantic contract tests
IDs, schemas, versioning, serialization invariants.

## Layer 2 — fake adapter failure matrix
Storage/secrets/network/remote failures.

## Layer 3 — system composition
Consumer-like end-to-end Work.

## Layer 4 — live environment certification
Claim-bounded readiness/effect checks.

## Challenge cases
Inject:

- partial copy;
- stale registry;
- duplicate/dependent sources;
- timeout after possible commit;
- permission changes;
- artifact corruption;
- concurrent writes;
- event reordering;
- backend unavailable after acknowledgement.

---

# 50. Priority sequence

Backward compatibility is not required, so target contracts should replace weak intermediate ones directly.

## Phase 0 — semantic freeze

1. canonical vocabulary;
2. ownership matrix;
3. relation matrix;
4. state distinctions;
5. Authority model;
6. Work/Result/Acceptance model.

## Phase 1 — `stratbox`

1. CanonicalOperation;
2. CapabilityDefinition/Envelope;
3. SourceSnapshot;
4. registry versioning;
5. provenance;
6. FormatRegistry;
7. artifact output contract;
8. plugin v1 neutral contract.

## Phase 2 — `stratbox-core`

1. Work/Run;
2. Scheme;
3. ActivationBinding;
4. ExecutionPlan;
5. Result/Acceptance;
6. participant/Authority;
7. assignment/approval;
8. settings resolution;
9. client-neutral projections.

## Phase 3 — `stratbox-host`

1. persistence;
2. jobs/attempts;
3. cancellation;
4. retry/idempotency;
5. reconciliation/resume;
6. event stream;
7. scheduler;
8. API;
9. shared-node concurrency.

## Phase 4 — artifact/resource plane

1. ArtifactStore;
2. ResourceSpace;
3. stable refs;
4. materialization;
5. lineage;
6. retention/GC.

## Phase 5 — client rebinding

1. Windows without visual redesign;
2. Web;
3. Android;
4. shared semantic projections.

## Phase 6 — observability/shared operation

1. AppDock ProblemRef bridge;
2. physical logs;
3. shared conditions;
4. Node health;
5. notifications/support bundles.

## Phase 7 — PROTOS

1. CognitivePort;
2. capability discovery projection;
3. proposal → Work admission;
4. controlled execution;
5. result interpretation;
6. generated Scheme admission later.

---

# 51. What should be postponed

By MADAR proportionality:

- universal semantic graph DB;
- giant ontology engine;
- universal BPMN replacement;
- mandatory rich provenance graph for trivial runs;
- AI-driven adaptive UI;
- full peer federation before single-node semantics;
- self-modifying production schemes;
- giant policy DSL;
- premature workflow language;
- excessive DB abstraction.

Build semantic seams first.

---

# 52. Genuine open questions

1. Physical repo count for core/host.
2. Exact threshold for creating independent durable Work.
3. Which Results require explicit Acceptance.
4. How rich Scheme IR must become.
5. When to bind directly to future MADAR machine projections.
6. How B5+ fresh consolidation alters authority/interaction details.
7. Which artifacts require immutable managed storage versus ordinary workspace files.
8. Which execution effects require explicit reconciliation after UNKNOWN.

---

# 53. Forty target invariants

1. One semantic fact has one owner.
2. Projection never silently becomes owner.
3. Work survives UI/process lifetime when materially durable.
4. Run is not Work.
5. Operation is not Work.
6. Scheme is not automatically bounded Work.
7. Result is not Artifact.
8. Artifact identity is not path.
9. Source identity is not URL.
10. Registry identity is not filename.
11. Capability is not Authority.
12. Installed plugin is not active plugin.
13. Active plugin is not ready plugin.
14. Ready capability is not applicable capability.
15. Request accepted is not effect achieved.
16. Execution success is not acceptance.
17. Acceptance is not external outcome.
18. Recommendation is not Decision.
19. Decision is not execution.
20. Chat is not Work state.
21. Message is not commitment without Authority/context.
22. Presence is not ownership.
23. Background is not a parallel execution architecture.
24. AI is not a bypass path.
25. Log is evidence, not truth.
26. Exception is technical evidence, not public problem identity.
27. Clean test is not universal assurance.
28. Multiple reviewers do not prove independence.
29. Freshness is reliance-relative.
30. UNKNOWN is legitimate.
31. User-facing simplicity may not erase material control semantics.
32. Client rendering may not alter product meaning.
33. Artifact style may not alter epistemic meaning.
34. Plugin may not implicitly alter public domain semantics.
35. AppDock platform concerns stay outside domain core.
36. `stratbox` remains usable without Strategy Box application runtime.
37. Strategy Box remains usable without PROTOS.
38. PROTOS effects pass through admitted capabilities and Authority.
39. Generated capability requires admission before trusted fast path.
40. Recovery restores governing meaning, not merely last screen.



---

# 54. Final architectural synthesis: five planes

Целевой Strategy Box лучше всего описывается пятью связанными planes.

## Plane A — Domain & Knowledge

```text
stratbox
```

Владеет:

- external source semantics;
- canonical data;
- registries;
- domain calculations;
- validation;
- reconstruction;
- analytical capabilities;
- domain provenance.

MADAR anchors:

- EOM;
- EKM;
- Analysis;
- Forecasting where applicable;
- specialist/domain bindings;
- meaning/measurement/evidence concerns.

## Plane B — Work & Product Semantics

```text
stratbox-core
```

Владеет:

- Work;
- Run;
- capabilities/schemes;
- applicability resolution;
- ActivationBinding;
- ExecutionPlan;
- product result/acceptance semantics;
- Authority/participants;
- assignments/approvals;
- collaboration;
- settings resolution;
- client-neutral projections.

MADAR anchors:

- EWM;
- applicability;
- dispatcher-like resolution;
- decisions/commitments;
- authority/participation;
- coordination/interaction;
- continuity/recovery.

## Plane C — Execution & Operations

```text
stratbox-host
```

Материализует:

- persistence;
- Job Manager;
- attempts;
- scheduler;
- foreground/background/remote;
- API/events;
- worker execution;
- concurrency;
- reconciliation/restart.

MADAR anchors:

- state/time/effects;
- operation;
- reliability/observability/recovery;
- resource/proportionality concerns.

## Plane D — Representation & Interaction

```text
stratbox-design
stratbox-windows
stratbox-web
stratbox-android
```

Владеет presentation realizations, но не underlying business/Work truth.

MADAR anchors:

- meaning/representation;
- Communication;
- human factors;
- low-entropy/adaptive interface Guidance.

## Plane E — Platform & Environment

```text
AppDock
environment-specific extension packages
```

Владеет:

- installation;
- environment;
- Node;
- process/platform lifecycle;
- connection/hosting substrate;
- platform health/recovery;
- deployment graph;
- bounded environment capabilities.

MADAR anchors:

- interoperability;
- security/trust;
- managed operational environment;
- applicability/profile;
- external system boundaries.

---

# 55. Why the current research corpus is transitionally valuable but must not become target authority

Вторая ветка Strategy Box оказалась качественным discovery corpus. Она независимо пришла ко многим различениям, которые свежий MADAR теперь объясняет более фундаментально:

| Strategy Box research discovery | MADAR interpretation |
|---|---|
| core vs UI separation | semantic owner vs representation/carrier |
| canonical operation | activity/capability result contract |
| scenario/cascade | reusable composition / product projection |
| Case | incomplete projection of bounded Work + Run |
| immutable ExecutionPlan | bounded execution state / time/effects |
| artifacts/provenance | EOM/EKM/EWM durable result/evidence |
| plugin capability contracts | applicability + environment adapter |
| job manager | execution realization, not Work meaning |
| background unification | same Work semantics, different trigger/execution mode |
| multi-user node truth | shared Work state + participation/Authority |
| PROTOS capability surface | governed external actor / semantic capability resolver |
| ArtifactStyleSet | representation policy, not semantic truth |
| settings cleanup | preference vs surface state vs policy |
| source/registry governance | currentness/provenance/measurement/evidence |
| observability spine | evidence of execution/effects, not substitute for result/acceptance |

Главное изменение после MADAR — **перестать считать конкретные слова, придуманные в research, обязательной ontology**.

Например, хорошие идеи могут сохраниться после переименования:

```text
Case          → Work/Run projection
Scenario      → user-facing Scheme/Work template
Cascade       → composite Scheme family
Background    → trigger/execution mode
Plugin theme  → ArtifactStyleSet contribution
History       → projection over canonical state/events
```

---

# 56. Recommended next consolidation artifact

До roadmap и массового рефакторинга нужен отдельный короткий, но нормативно-похожий **Strategy Box Target Semantic Contract**.

Он должен содержать только поддерживаемую целевую семантику:

```text
1. Product boundary
2. Canonical vocabulary
3. Semantic owners
4. Canonical object identities
5. Typed relations
6. Work/Run/Result/Acceptance distinctions
7. Capability/Scheme/Activation/Plan distinctions
8. Source/Registry/Artifact/Evidence distinctions
9. Actor/Participant/Role/Authority distinctions
10. State/time/effect semantics
11. Applicability/freshness/UNKNOWN semantics
12. Platform/client/plugin boundaries
13. Required machine-addressable contracts
14. Explicit non-goals
15. Reopen triggers
```

Этот документ не должен описывать Qt widgets, database tables или concrete folder layout.

После него `03-consolidation-research` сможет раскладывать весь `02-base-study` по semantic units:

```text
admit
refine
compose
defer
reject
move to Guidance
move to Example/default
move to realization design
keep as open question
```

Именно это соответствует MADAR lossless-consolidation discipline намного лучше, чем свести исследования в один “большой архитектурный документ”.

---

# 57. Recommended disposition of the `02-base-study` research themes

| Research theme | Target disposition |
|---|---|
| current state core/windows/plugin | historical/current-state evidence; not target norm |
| machine schemes | admit/refine into capability/scheme/activation/plan model |
| portability/reuse | admit as `stratbox` consumer/contract boundary |
| commands/scenarios/cascades | refine terminology; keep product UX aliases |
| execution control | admit into Work/Run/job/cancellation/Authority semantics |
| file/artifact | admit with EOM/EKM identity/provenance corrections |
| formats | admit as representation capability layer |
| observability | admit with execution-result-acceptance separation |
| plugin contract | admit as neutral extension/applicability/conformance model |
| PROTOS boundary | admit: optional cognition + host sovereignty |
| PROTOS readiness | admit Semantic Capability Contract / deoptimization |
| chat/work/schemes | admit Thread vs Work vs Run vs Scheme distinctions |
| PROTOS foundation | refine Case→Work and host/core split |
| source/registry governance | admit |
| single-node multi-user | admit with participation/Authority semantics |
| target core/design | refine `core` semantic owner vs `host` carrier |
| web/self-hosted | admit headless host + shared client contract |
| Windows interface | retain as client realization/Guidance, not product semantic owner |
| motion/animation | design Guidance/defaults |
| automation/AI | admit trigger/Work unification; AI as participant |
| ArtifactStyleSet | admit as representation resource |
| visual system | design Guidance/defaults |
| settings | admit semantic separation settings/state/policy |

---

# 58. Research gaps exposed by the MADAR comparison

Несмотря на большой corpus, после MADAR видны несколько недоисследованных областей.

## 58.1. Acceptance model

Strategy Box хорошо исследовал execution/result, но почти не формализовал:

- кто принимает результат;
- когда acceptance нужен;
- accepted for what use;
- conditional acceptance;
- revoked/superseded acceptance.

## 58.2. Work Commission / admission

Нужна отдельная модель:

```text
message/trigger/request
→ candidate undertaking
→ qualify
→ admit/commission
→ Work
```

Особенно для AI-generated Work.

## 58.3. Effect reconciliation

Remote/destructive operations требуют явной процедуры:

```text
UNKNOWN effect
→ inspect/reconcile
→ establish outcome
→ continue/compensate
```

## 58.4. Whole-system assurance

Plugin/core/client/AppDock component checks уже исследованы, но нужен claim-specific whole-product assurance model.

## 58.5. Epistemic payload in ordinary analytical Results

SORS очень зрелый, обычные domains слабее. Нужен минимальный generic EKM envelope без превращения каждого DataFrame в knowledge graph.

## 58.6. Authority/participation after B5

После выхода B5 MADAR нужно обновить:

- cancellation rights;
- approvals;
- delegation;
- peer Work;
- AI authority;
- shared node roles.

## 58.7. Work economics and proportionality

Нужны правила выбора:

- simple direct operation;
- durable Work;
- explicit verification;
- independent challenge;
- AI involvement;
- expensive provenance.

Иначе rich target model начнёт навязывать overhead мелким задачам.

---

# 59. Architectural anti-patterns

Ниже — вещи, которые в целевой Strategy Box следует считать прямыми архитектурными ошибками.

### 59.1. UI owns product truth
```text
Qt store = canonical case store
```

### 59.2. Transport defines semantics
```text
MCP tool schema = product capability meaning
```

### 59.3. File defines identity
```text
artifact_id = C:\output\file.xlsx
```

### 59.4. Plugin presence changes behavior implicitly
```text
try import external package
except: silently local fallback
```

### 59.5. AI bypasses normal execution
```text
LLM → arbitrary Python/shell
```

### 59.6. Log success proves effect
```text
"upload OK" → external state definitely changed
```

### 59.7. Scenario catalog is the whole product ontology
```text
everything must be Scenario
```

### 59.8. Common memory for all users/agents
```text
shared mutable cognitive context
```

### 59.9. One global “confidence”
Different uncertainty/evidence/forecast/reliance concepts collapsed into scalar.

### 59.10. One overall health score
Unrelated readiness/assurance claims hidden behind green status.

---

# 60. Compact target model

Если свести всё исследование к одной схеме:

```text
                    ┌────────────────────────┐
                    │ Principal / Authority  │
                    └───────────┬────────────┘
                                │
                                ▼
Thread / Trigger ───────► Work Candidate
                                │
                         qualify / admit
                                │
                                ▼
                              Work
                    purpose / scope / result
                    participants / obligations
                                │
                ┌───────────────┼────────────────┐
                ▼               ▼                ▼
              Run A           Run B            Run C
                │
                ▼
       Capability Resolution
                │
                ▼
       Activation Binding
                │
                ▼
        ExecutionPlan
                │
          ┌─────┴─────┐
          ▼           ▼
        Job         Job ...
          │
    OperationRun
          │
       Attempt
          │
        effects
          │
          ├── Result
          ├── Artifact
          ├── Evidence
          ├── Diagnostic
          └── ProblemRef
                │
                ▼
       Evaluation / Challenge
                │
                ▼
           Acceptance?
                │
                ▼
     Handoff / Closure / Reopen
```

Рядом:

```text
SourceSnapshots / RegistrySnapshots
ResourceSpace / Workspace
Automation triggers
Participant/Role/Authority
AppDock Node/environment
Plugin capability bindings
PROTOS cognitive participation
```

Clients and reports project this model without owning it.

---

# 61. Final conclusion

Текущий Strategy Box уже вышел за рамки “библиотеки банковских скриптов + desktop GUI”. В исследовательском корпусе фактически сформировалась архитектура **управляемой аналитической рабочей системы**:

- domain capabilities;
- reusable schemes;
- durable work;
- shared execution;
- artifacts;
- evidence;
- collaboration;
- automation;
- AI participation;
- remote clients;
- managed environment.

Свежий MADAR показывает, как довести эту систему до более строгой формы.

Его главный вклад не в том, чтобы добавить Strategy Box ещё больше сущностей. Наоборот, он позволяет **развести то, что текущие исследования иногда складывали в один объект**:

```text
смысл ↔ представление
объект ↔ знание об объекте
Work ↔ execution
execution ↔ effect
Result ↔ Artifact
evidence ↔ claim
evaluation ↔ acceptance
capability ↔ authority
actor ↔ role ↔ participant
interaction ↔ commitment
scheme ↔ Work
runtime semantic owner ↔ process carrier
platform ↔ product
domain ↔ environment adapter
```

После этого target Strategy Box становится значительно стабильнее.

Самая короткая итоговая формула:

> **`stratbox` знает предметный мир; `stratbox-core` знает смысл продуктовой работы; `stratbox-host` надёжно исполняет и хранит эту работу; clients показывают её; `stratbox-design` задаёт язык представления; AppDock управляет внешней средой; plugins адаптируют среду; MADAR задаёт более высокий семантический метод, с которым все эти слои должны быть согласованы, но который ни один из них не должен присваивать себе.**

Следующий шаг второй ветки исследований должен быть уже не очередным тематическим исследованием, а **semantic consolidation Strategy Box**: target vocabulary + ownership + relations + lifecycle + dispositions всего `02-base-study`. После этого можно формировать supported Knowledge и только затем целевую Product Architecture / implementation roadmap.

---

# Appendix A. Canonical vocabulary candidate

```text
Principal
Actor
Participant
Role
AuthorityGrant

Thread
Message

Work
Run
Result
Acceptance

CapabilityDefinition
CapabilityEnvelope
CanonicalOperation
MachineScheme

ActivationBinding
ExecutionPlan

Job
OperationRun
Attempt
EffectReceipt

SourceDescriptor
SourceSnapshot
RegistrySnapshot

ResourceSpace
ResourceRef
Workspace

Artifact
ArtifactRef
EvidenceReference
ProvenanceManifest

Assignment
Approval

AutomationSpec
TriggerOccurrence

Diagnostic
ProblemOccurrence
ProblemRef
LogRef

UserSettings
SurfaceState
DraftState
ManagedPolicy

InterfaceTheme
ArtifactStyleSet
ArtifactMetadataContext
```

# Appendix B. Product/UI aliases that should not become deep ontology by default

```text
Scenario
Cascade
Case card
Background
Explorer
Inspector
Notification
Recent
Favorite
Preset
Profile
```

These can remain excellent user vocabulary.

# Appendix C. Source register

## MADAR
- `ForestTiger-GH/MADAR@be4dc2b3d53410286d37172e8ec7a8f071c518ea`
- `AGENTS.md`
- `_mw/AGENTS.md`
- `_mw/consolidation/STATE.md`
- `_mw/consolidation/BASELINE.md`
- `_mw/consolidation/ARCHITECTURE.md`
- `_mw/consolidation/PROCESS.md`
- `_mw/research/05_consolidation-input-research/README.md`
- `_mw/consolidation/notes/MADAR_Consolidation_Sequence_and_Target_Directory_Architecture_2026-10-01.md`
- Stage 3 Results A1–A8, B1–B4
- current `spec/` as present normative comparison surface.

## Mandat packages
- `mandat-analytics@22e384f9cf64e37bb23554d9050916f98438b9a1`
- `mandat-forecast@67dde20286a9618109e2e2afab9e0837d454e7c5`
- `mandat-programming@4abdc42c3dbda71eabaebb82e8b1aa4b05e6c52a`
- `mandat-communication@f4e50aacd0e356e3bf99a60d271f69d263306c61`
- `mandat-evaluation-challenge@c63a192d501e4cf4924158df691ca1418a5fb85d`
- `mandat-strategy-decision@ba4f70780ba84c515a8efad280466897a0a0424f`

## MADAR-supplements
- `MADAR-supplements@bf8d3b95e26a3f68318ea5b1eb15ba610efe9e59`
- `01-thinking`
- `02-coding`
- `03-communicating`
- architectural decomposition, cross-mandat and lossless-disposition studies.

## Strategy Box
- `ForestTiger-GH/stratbox@bfce897c952cdf0d9971175010b681da7116ef8d`
- complete `02-base-study`
- `03-consolidation-research/README.md`
- current-state `stratbox` research
- current-state `stratbox-windows` research
- private current-state plugin research retained outside public repository semantics
- AppDock base product description.

---

**End of Research Result**
