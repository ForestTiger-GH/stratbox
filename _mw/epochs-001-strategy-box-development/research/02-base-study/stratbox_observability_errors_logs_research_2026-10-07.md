# Strategy Box: наблюдаемость, ошибки, логи, фоновые и удалённые выполнения

**Research branch:** вторая ветка исследований Strategy Box  
**Дата исследования:** 2026-10-07  
**Статус:** Research Result — архитектурное исследование; код и репозитории не изменялись  
**Охват:** `stratbox`, `stratbox-windows`, граница с AppDock, будущие background/remote/AI/Android-сценарии

---

# 0. Краткий вывод

Тема «логи и ошибки» для Strategy Box на самом деле состоит из нескольких связанных контуров: наблюдаемость выполняющегося сценария, единая модель результата, структурированная модель проблемы, физические журналы и crash evidence, фоновые задания, передача состояния через AppDock, совместная наблюдаемость внутри узла и remote/AI execution.

Главный архитектурный вывод:

> **Strategy Box не должен строить собственную независимую систему ошибок поверх AppDock.**
>
> `stratbox` должен выдавать структурированные предметные результаты, diagnostics и progress; `stratbox-windows` должен владеть пользовательскими cases/jobs и их проекциями; AppDock должен оставаться каноническим узловым институтом проблем, evidence, здоровья Node/Session и будущего remote/audit-контура.

Целевая сквозная цепочка:

```text
пользователь / ИИ / background trigger
        ↓
Scenario Case
        ↓
Job
        ↓
Operation Run
        ↓
Attempt
        ↓
stratbox operation
        ↓
structured progress / diagnostics / result
        ↓
stratbox-windows execution boundary
        ↓
success / partial / cancelled / failure / unknown
        ↓
при проблеме: safe ProblemDraft
        ↓
AppDock Recorder
        ↓
canonical ProblemOccurrence
        ↓
ProblemRef
        ├── case / step projection
        ├── Node health / Session state
        ├── user explanation
        ├── operator/developer evidence
        ├── shared warning, если impact общий
        └── AI-safe allowed actions
```

Raw exception, traceback, stdout и stderr при этом остаются техническими свидетельствами. Они не должны становиться публичным состоянием сами по себе.

Самое удачное совпадение с AppDock состоит в следующем: там уже разделены `Event`, `ProblemOccurrence`, текущее `Condition` и будущий `Incident`; Python exception считается только технической причиной внутри процесса; ошибка регистрируется один раз, а остальные части системы передают `ProblemRef`.

---

# 1. Источники и метод

Исследование выполнено сверху вниз и снизу вверх.

## 1.1. Strategy Box

Использованы актуальные исследования от 2026-10-06:

- `stratbox_base_study_current_state_2026-10-06.md`;
- `stratbox-windows_current_state_full_research_2026-10-06.md`;
- приватное исследование environment-specific расширения Strategy Box;
- `AppDock - Базовое описание.docx`.

Дополнительно фактически проверены актуальные исходники `stratbox-windows` на `main`, включая:

```text
application/operations/execution/runner.py
application/scenarios/runner.py
application/cases/models.py
application/events/models.py
application/logs/*
application/history/persistence.py
application/background/*
adapters/appdock/surface_state.py
runtime/logging.py
runtime/session_runtime.py
```

## 1.2. AppDock

Проверен актуальный приватный репозиторий:

```text
ForestTiger-GH/AppDock
main
HEAD: a4d87c643e620e54e04083d4d0b8d867513e7065
```

Отдельно изучены:

```text
docs/architecture/observability/README.md
docs/architecture/observability/TARGET_MODEL.md
docs/architecture/observability/IMPLEMENTATION_STATUS.md

src/appdock/domains/observability/public/*
src/appdock/domains/observability/problems/*
src/appdock/domains/observability/explanations/*
src/appdock/domains/execution/results/operation_results.py
src/appdock/domains/node/health/*
src/appdock/domains/sessions/models.py
```

На текущем `main` AppDock имеет package/build model `0.2.0`; `BUILD.json` относится к build `2608.21.1736`.

## 1.3. Внешняя техническая сверка

Проверены официальные OpenTelemetry Semantic Conventions и Logs Data Model, W3C Trace Context, Python `logging.handlers`, `faulthandler`, `sys.excepthook`, `sys.unraisablehook` и `threading.excepthook`.

Внешние стандарты используются только как interoperability/implementation reference. Каноническая предметная модель должна оставаться собственной моделью Strategy Box/AppDock.

## 1.4. Публичная граница

Целевая архитектура `stratbox` и `stratbox-windows` ниже сформулирована через нейтральные публичные contracts и AppDock boundary. Детали закрытых environment-specific реализаций не должны попадать в публичные репозитории, imports или документацию.

---

# 2. Что существует сейчас в `stratbox`

Core уже содержит несколько зрелых паттернов:

- typed `Request → Result`;
- structured failures;
- validation issues;
- partial results;
- diagnostics/audit grids в отдельных подсистемах;
- provenance;
- artifacts;
- стабильные идентификаторы.

При этом модель результата неоднородна:

```text
collector      → failures
industries     → validation issues
escrow         → partial collection
SORS           → conflicts / ledgers / audit grids
FRG            → табличные статусы
часть infra    → exceptions / direct messages
```

Поэтому core пока не даёт внешнему executor единую форму ответа на вопросы: на какой стадии задача находится, каков прогресс, какие warnings существуют, каков terminal disposition, что является ожидаемой предметной ошибкой, а что внутренним crash.

Предыдущее исследование уже правильно предложило тонкий общий envelope:

```text
status
warnings
failures
metrics
artifacts
diagnostics
provenance
```

Ключевой принцип стоит закрепить явно:

> Библиотека формирует structured diagnostics/events/results; caller решает, как показывать их пользователю.

---

# 3. Что существует сейчас в `stratbox-windows`

Desktop surface уже содержит почти все семантические заготовки:

```text
ScenarioRunCase
ScenarioStepRun
OperationalEvent
LogRecord
ArtifactRecord
BackgroundProcessState
AssignmentRecord
Presence participant
AppDock runtime-state projection
```

Реальная execution chain:

```text
ScenarioCoordinator
→ QThread
→ ScenarioWorker
→ ScenarioRunner
→ OperationRunner
→ handler
→ stratbox
```

## 3.1. Сильные стороны

Case уже является пользовательской единицей: хранит scenario, автора, параметры, status, текущую стадию, steps, outputs, timestamps и unread.

Scenario runner уже генерирует значимые lifecycle events:

```text
case_started
step_started
step_completed / step_failed
case_completed / case_failed
```

Outputs превращаются в `ArtifactRecord`. Есть application log и отдельный operation log. `LogRecord` связан с case/scenario/operation/step. Surface уже проецирует в AppDock active view, active job, last operation, outputs, artifacts, scenario, case и workspace state.

То есть база наблюдаемости реально существует и её не надо строить с нуля.

---

# 4. Главные проблемы текущей реализации

## 4.1. Raw exception протекает в product model

Текущий `OperationRunner` при произвольном исключении фактически делает:

```text
logger.exception(...)
message = "Operation failed: {exc}"
details["error"] = str(exc)
```

Дальше этот текст может стать `step_run.message`, `OperationalEvent.body`, частью history и UI.

Это опасно: `str(exception)` способен содержать локальный path, URL, username, server name, внутренний библиотечный текст и иной чувствительный контекст.

Целевая граница:

```text
safe product explanation
≠
technical cause
≠
traceback/evidence
```

## 4.2. Boolean `ok` слишком слаб

Текущий surface в основном сводит terminal result к `True/False`. Для распределённой системы нужны минимум:

```text
SUCCESS
PARTIAL
CANCELLED
FAILURE
UNKNOWN
```

`UNKNOWN` особенно важен после network partition, process crash, timeout после side effect или потери ответа от remote/AI host. Если система не может доказать итог, она не должна выдумывать failure или success.

## 4.3. `warning` смешивает lifecycle и outcome

Лучше разделить:

```text
Lifecycle State:
prepared / queued / running / waiting_input / cancelling / terminal

Terminal Disposition:
success / partial / cancelled / failure / unknown
```

Warnings становятся отдельными diagnostics.

## 4.4. `operation_id` перегружен

Сейчас `operation_id` означает в основном стабильный ID типа операции, например `cbr_file_collector.collect`. Для causality нужны разные сущности:

```text
operation_name     — стабильный тип операции
operation_run_id   — конкретный запуск
attempt_id         — конкретная попытка/retry
job_id             — единица исполнения scheduler/host
case_id            — пользовательская общая цель/correlation
step_id            — стабильный шаг scenario
step_run_id        — конкретный экземпляр шага
```

Это одно из самых важных изменений.

## 4.5. Physical logs не ограничены

Текущий logger использует обычный Python `FileHandler`:

- `app.log` растёт без retention;
- operation logs не имеют rotation;
- нет schema;
- нет redaction;
- нет causal IDs в каждой записи.

## 4.6. `LogRecord` хранит абсолютный OS path

Это удобно локально, но плохо переносится между Windows, Android и remote Node. Application model нужен `LogRef`; физический locator должен разрешать локальный adapter.

## 4.7. Параметры сохраняются слишком свободно

Case хранит `params: dict`, а start event может отображать параметры текстом. При росте operations туда попадут paths, URLs, internal identifiers и потенциально credentials.

`OperationParamSpec` нужен policy layer:

```text
sensitivity: public / private / secret
persist: true / false
display: local / participants / never
log: safe / masked / never
```

Secret value не должно сохраняться в Case вообще.

## 4.8. History persistence слишком слаб

Пять JSON projection files не дают транзакционности, locking, schema version, retention и согласованного recovery. Повреждённые записи могут тихо исчезать.

## 4.9. Background пока отдельный каркас

Фоновые процессы имеют собственный in-memory state, но executor/scheduler отсутствует. Отдельный background engine строить не стоит. Background должен запускать тот же Scenario через тот же Job Manager.

## 4.10. Cancellation отсутствует как execution contract

Case status `cancelled` уже есть, но cancellation token, request/acknowledgement и commit-point semantics отсутствуют.

---

# 5. Что AppDock уже решил концептуально

AppDock Observability существенно глубже текущей Strategy Box модели. Его главный принцип: observability — это институт доказуемости работы платформы, а не централизованный сборщик логов.

## 5.1. Четыре разные сущности

```text
Event
    что произошло в конкретный момент

ProblemOccurrence
    почему цель не достигнута, каково влияние и что делать

Condition
    в каком состоянии объект находится сейчас

Incident
    какая группа связанных проблем требует общей оперативной работы
```

Это напрямую отвечает на идею «подсвечивать ошибки пользователей друг у друга»: чужая единичная ошибка и общая проблема узла — разные вещи.

## 5.2. Один сбой — одна регистрация

Canonical flow:

```text
owner detects failure
↓
ProblemDraft
↓
operation boundary
↓
Recorder
↓
ProblemOccurrence
↓
ProblemRef
```

Node, Session, UI, CLI, agent, logs и telemetry дальше не создают собственные версии одной ошибки.

## 5.3. Exception не является durable state

Python exception остаётся механизмом передачи причины внутри процесса. Он не должен жить в persisted state, UI state, session state или remote job payload.

## 5.4. AppDock уже имеет правильные terminal outcomes

```text
SUCCESS
PARTIAL
CANCELLED
FAILURE
UNKNOWN
```

Для failure нужен подтверждённый `ProblemRef` либо явное состояние `NOT_WRITTEN`. Для unknown нужен `ProblemRef` либо `OUTCOME_UNKNOWN`. Это особенно хорошо подходит remote execution.

## 5.5. Causal context уже определён

Текущий `ContextEnvelope` содержит:

```text
operation_id
attempt_id
correlation_id
job_id
causation_event_id
trace_id
span_id
external_protocol_ids
```

## 5.6. ProblemOccurrence уже является immutable typed record

В текущем AppDock присутствуют:

```text
occurrence_id
code
version/digest
occurred_at / observed_at
severity
impact
disposition
retry_advice
ContextEnvelope
safe context
EvidenceRef[]
parent ProblemRef
safe cause snapshot
fingerprint
```

## 5.7. Node и Session уже несут ссылки на проблемы

Есть `NodeHealthSnapshot.active_problem_ref` и `SessionState.failure_problem_ref`.

## 5.8. Но полный внешний observability stack ещё развивается

Уже зрелы problem contracts, registration/query, diagnostics contracts, evidence references, durable local problem journal, Node/Session projection и Execution result/progress contracts.

Дальнейшие этапы AppDock включают semantic Events, Audit, Telemetry, Support, Incidents, MCP/A2A и более полный external-product SDK. Поэтому Strategy Box должен сейчас построить чистый integration port, а не копировать будущие механизмы AppDock.

---

# 6. Целевое разделение ответственности

## `stratbox`

Владеет предметной операцией, validation, diagnostics, domain failure codes, progress semantics, artifacts, provenance и предметным Result.

Не владеет UI, Node, AppDock Session, collaboration и canonical AppDock ProblemOccurrence.

Правило:

```text
stratbox does not import AppDock
```

## `stratbox-windows`

Владеет Scenario Case, Job projection, foreground/background UX, orchestration, operation invocation, пользовательским timeline, локальным technical logging, local surface state и mapping domain failure → safe platform problem draft.

## AppDock

Владеет Node, Session, platform execution infrastructure, canonical ProblemOccurrence/ProblemRef, health, evidence custody, process lifecycle, remote/agent permissions и будущим audit/support/incident контуром.

## UI

UI читает projections, показывает safe explanations и вызывает allowed actions. Он не должен классифицировать traceback, создавать второй occurrence или самостоятельно определять retry policy.

---

# 7. Главная модель исполнения

Предлагается явная цепочка:

```text
ScenarioDefinition
        ↓
Case
        ↓
Job
        ↓
OperationRun
        ↓
Attempt
```

## 7.1. Case

Case — пользовательская или командная цель. Например: «Обновить данные Банка России».

Минимальные поля:

```text
case_id
scenario_id
created_by
created_at
correlation_id = case_id
execution_mode
target_node_id
lifecycle_state
terminal_disposition?
current_job_id
current_stage
problem_ref?
warning_count
artifact_refs
started_at
updated_at
finished_at
```

## 7.2. Job

Job — реальная единица исполнения. Один Case может иметь foreground, background, remote, retry или resumed job.

```text
job_id
case_id
execution_backend
requested_by
delegated_to?
executed_by?
target_node_id
state
heartbeat_at
terminal_disposition?
problem_ref?
started_at
updated_at
finished_at
```

## 7.3. OperationRun

```text
operation_name
operation_run_id
step_id
step_run_id
```

## 7.4. Attempt

Retry сохраняет `operation_run_id`, но получает новый `attempt_id`.

---

# 8. Mapping Strategy Box → AppDock ContextEnvelope

| Strategy Box | AppDock |
|---|---|
| `case_id` | `correlation_id` |
| `operation_run_id` | `operation_id` |
| `attempt_id` | `attempt_id` |
| `job_id` | `job_id` |
| parent event | `causation_event_id` |
| optional OTel trace | `trace_id` |
| optional OTel span | `span_id` |
| remote protocol ID | `external_protocol_ids` |

`scenario_id`, `operation_name`, `step_id` и `step_run_id` остаются отдельными safe context fields.

Ключевое изменение: существующее поле `operation_id`, где сейчас хранится имя use case, лучше сразу разделить на operation name и execution identity. Обратная совместимость проекту не нужна.


---

# 9. Целевой operation result в `stratbox`

Core нужен лёгкий нейтральный contract. Концептуально:

```python
OperationResult[T](
    disposition=SUCCESS | PARTIAL | CANCELLED | FAILURE,
    value=T | None,
    warnings=...,
    failures=...,
    artifacts=...,
    diagnostics=...,
    metrics=...,
    provenance=...,
)
```

`UNKNOWN` чаще возникает на внешней execution boundary, когда caller потерял доказательство результата. При чистом локальном выполнении `stratbox` обычно способен определить собственный outcome.

Expected domain failures лучше возвращать как typed data: source unavailable, authentication required, invalid input, schema changed, data invalid, partial source set, unsupported operation, conflict.

Неожиданная programmer/internal ошибка может оставаться exception. Но после пересечения operation boundary она превращается в generic safe internal failure, а traceback уходит только в evidence/log.

Никакого `str(exc)` в public result.

---

# 10. Problem codes: namespaced, а не giant enum

Не нужен единый огромный `StrategyBoxErrorType`. Лучше стабильные коды владельцев:

```text
cbr.source.unavailable
cbr.source.schema_changed
escrow.source.partial
frg.cleanup.conflict
workspace.unavailable
execution.handler_failed
execution.cancel_timeout
remote.connection_lost
```

В AppDock-managed режиме adapter связывает domain issue с соответствующим `ProblemDefinition`.

Это даёт стабильную идентичность, переводимость, safe explanations, retry/action policy, fingerprinting и независимую evolution каждой problem family.

---

# 11. Progress как отдельный сигнал

Прогресс нельзя восстанавливать из text log parsing. Нужен явный structured event.

Минимум:

```text
operation_name
operation_run_id
attempt_id
case_id
job_id
phase
step
message
current?
total?
detail?
occurred_at
```

AppDock уже имеет практически такой `OperationProgressEvent`.

Примеры:

```text
phase = source_discovery
step = cbr_publications
message = "Поиск публикаций"
```

```text
phase = download
step = files
current = 18
total = 41
message = "Загрузка файлов"
```

```text
phase = export
step = workbook
message = "Формирование Excel"
```

## 11.1. Progress в UI

Scenario chat не должен получать тысячи сообщений. Нужны два уровня:

```text
technical progress stream
↓
coalescing / throttling
↓
latest semantic progress projection
↓
case card / inspector
```

Например:

```text
Выполняется · 18 из 41 файлов · 44%
```

---

# 12. Foreground и background должны использовать один execution engine

Целевая модель:

```text
Trigger
  ├── manual
  ├── schedule
  ├── source-change
  ├── assignment
  ├── remote request
  └── AI request
        ↓
Scenario
        ↓
JobManager
        ↓
ExecutionBackend
        ↓
same ScenarioRunner / OperationRunner
```

## 12.1. BackgroundProcessSpec должен стать trigger/config

Background process не должен владеть execution state. Вместо `BackgroundProcessStore.mark_running()` trigger создаёт Case/Job, а Job Manager исполняет его.

UI «Фоновые» просто фильтрует jobs по execution mode и отдельно показывает schedule configuration.

## 12.2. Что показывать для фонового сценария

```text
Название
Включён / выключен
Trigger
Следующий запуск
Последний запуск
Текущий статус
Узел исполнения
Текущий progress
Последний outcome
ProblemRef / safe explanation
Последний artifact
```

---

# 13. Job Manager

Это один из главных недостающих элементов `stratbox-windows`. Он должен быть frontend-neutral и жить вне Qt.

Основные операции:

```text
submit
start
observe
cancel
retry
resume
reconcile
list_active
list_recent
```

## 13.1. Concurrency policy

Текущий Qt coordinator допускает один активный scenario. Целевой Job Manager должен иметь явную policy:

```text
max foreground jobs
max background jobs
resource groups
mutual exclusion keys
per-operation concurrency
```

Два read-only downloads могут идти параллельно, а две destructive операции над одним workspace — блокировать друг друга.

## 13.2. Cancellation

Нужен `CancellationToken`. Core loop проверяет его в безопасных точках:

```text
running
↓
cancellation_requested
↓
cancelling
↓
cancelled
```

Если пройдена необратимая граница, отмена должна явно отклоняться или откладываться, а не игнорироваться.

---

# 14. Physical logging: целевая модель

Логи нужны обязательно, но они должны занимать правильное место.

## 14.1. Четыре уровня

### Product events

Низкообъёмные смысловые факты:

```text
case started
job started
step changed
retry scheduled
artifact produced
problem registered
case completed
```

### Technical structured logs

Подробный поток для диагностики.

### Evidence

Тяжёлые или чувствительные свидетельства: traceback, bounded stdout/stderr, crash record, diagnostic snapshot, source response metadata.

### Audit

Привилегированные действия: remote command, действие ИИ, destructive operation, approval, доступ к чувствительным evidence. Audit должен принадлежать AppDock boundary, а не обычному app log.

---

# 15. Рекомендуемая физическая раскладка

App не должен угадывать глобальный filesystem root. AppDock/Activation Context предоставляет app-owned system directories.

Внутри собственной области Strategy Box логически можно иметь:

```text
system/
├── logs/
│   ├── app/
│   │   ├── app-2026-10-07.jsonl
│   │   └── ...
│   ├── operations/
│   │   └── <case_id>/
│   │       └── <operation_run_id>/
│   │           ├── <attempt_id>.jsonl
│   │           └── <attempt_id>.raw.log
│   ├── crash/
│   └── bootstrap/
│
├── runtime/
│   └── strategy-box.sqlite
│
└── support/
```

Физический path — implementation detail. В application model хранится `LogRef`/`EvidenceRef`.

---

# 16. Structured log record

Минимальная полезная запись:

```json
{
  "timestamp": "...",
  "level": "INFO",
  "event_name": "operation.progress",
  "case_id": "...",
  "job_id": "...",
  "scenario_id": "...",
  "operation_name": "...",
  "operation_run_id": "...",
  "attempt_id": "...",
  "step_id": "...",
  "step_run_id": "...",
  "node_id": "...",
  "session_id": "...",
  "actor_id": "...",
  "trace_id": "...",
  "span_id": "...",
  "message": "...",
  "safe_fields": {}
}
```

Нельзя автоматически dump-ить `params`, environment, headers, credentials, full URL with query, request body, full manifest, secret values или arbitrary object repr.

OperationParamSpec желательно расширить:

```text
sensitivity: public / private / secret
persist: true / false
display: local / participants / never
log: safe / masked / never
```

---

# 17. Rotation и retention

Текущий `FileHandler` следует заменить. Python предоставляет `RotatingFileHandler`, `TimedRotatingFileHandler`, `QueueHandler` и `QueueListener`.

Пример product policy:

```text
app technical logs         → rolling, 14 дней / size cap
successful operation logs  → 14 дней
failed/unknown logs        → 30 дней
crash evidence             → 30 дней
support bundles            → до удаления пользователем / policy
```

Конкретные значения лучше задавать профилем. Обязательны общий disk budget, cleanup, dropped-record counters и observable состояние деградации logging.

---

# 18. Queue logging и crash durability

Асинхронный logging снижает влияние file I/O на UI/job, но часть последних записей может потеряться при crash.

Поэтому:

- INFO/DEBUG могут идти через bounded queue;
- ERROR/CRITICAL и terminal execution events должны принудительно flush-иться;
- bootstrap/crash sink должен быть максимально простым;
- overflow должен считаться;
- mandatory audit терять нельзя.

Это совпадает с целевой моделью AppDock observability self-health.

---

# 19. Unhandled exception и process crash

Одного `try/except` в OperationRunner недостаточно.

## Python top-level

Нужно рассмотреть:

```text
sys.excepthook
sys.unraisablehook
threading.excepthook
```

## Fatal diagnostics

`faulthandler` может дать low-level traceback при ряде аварий. На Windows набор возможностей отличается от POSIX, поэтому это platform capability, а не универсальная гарантия.

## Qt boundary

Нужна явная обработка UI callback exception, worker exception, Qt message handler и clean shutdown marker.

## Главный внешний наблюдатель

Если весь Strategy Box process умер, он может не успеть зарегистрировать собственную проблему.

> **Process-level crash должен наблюдаться AppDock как родительским runtime/Node layer.**

Это надёжнее любого in-process crash hook.

---

# 20. Clean / unclean shutdown и reconciliation

Текущий Strategy Box уже проецирует clean shutdown в AppDock. При следующем старте:

```text
если предыдущая Session/Job была running
и clean shutdown не подтверждён
↓
recovery/reconciliation
```

Нельзя автоматически записывать `failed`. Если operation имела side effects, правильный outcome может быть `UNKNOWN`.

После проверки artifacts/state:

```text
UNKNOWN → SUCCESS / PARTIAL / FAILURE
```

когда итог доказан.

---

# 21. Local persistence: уйти от пяти JSON projection files

Целевой `stratbox-windows` уже перерос отдельные JSON. Предлагается:

```text
SurfaceStateStore Protocol
        ↓
SQLite implementation
```

## 21.1. Что хранить

```text
cases
jobs
operation_runs
attempts
case_events
artifact_refs
log_refs
assignments
background trigger config
per-user read/ack state
```

Canonical AppDock ProblemOccurrence туда копировать не нужно — только `ProblemRef`.

## 21.2. Почему SQLite

Он даёт транзакции, schema version, locking, atomic multi-table update, indexed active jobs, bounded retention, consistency и WAL.

При этом SQLite остаётся Strategy Box product read model, а не новым AppDock problem journal.

---

# 22. Error propagation через AppDock

Нужен отдельный application port, условно:

```text
ObservabilityBridge
```

Application layer не должен импортировать внутренности AppDock. Conceptual capabilities:

```text
register_problem(...)
query_problem(...)
get_safe_explanation(...)
attach_evidence(...)
report_progress(...)
update_job_projection(...)
query_node_health(...)
```

Точные API имена должны следовать финальному AppDock public SDK/IPC, а не фиксироваться в Strategy Box как параллельный протокол.

Managed mode:

```text
Strategy Box
↓
adapters/appdock/observability
↓
stable AppDock public SDK / IPC
↓
AppDock Recorder / Node / Session
```

Для standalone-dev допустим локальный adapter, который не претендует на production Node truth.

---

# 23. Mapping domain failure → AppDock problem

Пример:

```text
stratbox:
    code = cbr.source.unavailable
    safe context = source_id
    retry hint = later

↓ surface boundary

ProblemDraft:
    code = strategy_box.cbr.source.unavailable
    safe context:
        source_id
        scenario_id
        step_id
```

Technical exception вроде `ConnectionError(...)` не идёт в UI. Он становится SafeCauseSnapshot/Evidence.

UI получает примерно:

```text
Не удалось получить данные источника.
Повторить: можно.
Problem: ...abcd
```

---

# 24. Scenario chat во время выполнения

Case card должна быть живой projection:

```text
Обновление данных Банка России

● Выполняется
Загрузка исходных файлов
18 из 41 · 44%

Узел: Office Mini-PC
Запустил: Дмитрий
Выполняет: Strategy Box Host

[Открыть детали] [Отменить]
```

Fine-grained progress обновляет card/inspector, а не создаёт сотни chat messages.

В timeline фиксируются значимые переходы:

```text
queued
started
step changed
waiting for input
retry
partial result
completed
failed
unknown
cancelled
recovered
```

---

# 25. Right Inspector: целевая структура

Текущие вкладки уже близки к нужным.

## Кейс

Scenario, actor, execution node, timestamps, disposition, current state, attempts, recovery.

## Прогресс

Phase/step timeline, progress, retries, current activity.

## Проблема

Появляется только при ProblemRef: safe title, explanation, problem code, short occurrence ID, impact, retry advice, allowed actions.

## Логи

Два уровня:

```text
Пользовательский журнал
Технический журнал
```

Raw evidence доступен только при допустимом уровне доступа.

## Артефакты

First-class outputs.

## Параметры

Только safe projection.

---

# 26. «Показывать ошибки друг другу»: правильная модель

Broadcast каждой ошибки всем участникам создаст шум и утечку данных.

Главный принцип:

> **Другим пользователям показывается shared Condition, когда проблема действительно влияет на общий Node/World/Workspace/Resource, а не чужая raw error.**

Обычно не надо broadcast:

```text
неверный параметр одного пользователя
его локальный path
отмена его операции
персональная permission/auth issue
ошибка private artifact
```

Полезно broadcast:

```text
общий source недоступен
Node degraded
общий storage недоступен
повреждён shared workspace
host перегружен
background refresh систематически падает
общая версия runtime повреждена
```

---

# 27. SharedCondition

Рекомендуемая концепция:

```text
condition_id
fingerprint
scope_kind:
    node
    world
    workspace
    shared_resource
    source
scope_id
status:
    active
    recovering
    resolved
severity
impact
first_seen
last_seen
occurrence_count
latest_problem_ref
action_refs
visibility
```

`ProblemOccurrence` остаётся immutable фактом, `Condition` — текущей агрегированной проекцией.

Если один пользователь получает общую ошибку source, остальные видят:

```text
⚠ Источник Банка России сейчас недоступен.
Некоторые сценарии могут завершаться с ошибкой.
[Подробнее]
```

Они не получают его Case, параметры, traceback, paths или request contents.

После восстановления Condition переходит в `resolved`.

---

# 28. Deduplication

Если десять пользователей столкнулись с одной причиной, не нужно показывать десять предупреждений. Fingerprint AppDock ProblemOccurrence естественно позволяет агрегировать:

```text
fingerprint
↓
SharedCondition
↓
occurrence_count = 10
```

UI может показать:

```text
Проблема наблюдалась 10 раз за последние 7 минут
```

---

# 29. Incident нужен позже

Если Condition длится долго, влияет на много пользователей/узлов и требует назначения/acknowledgement, тогда возможен Incident.

AppDock сам считает incidents более поздней стадией. Strategy Box сейчас не нужен отдельный incident-management subsystem.

---

# 30. AI как actor и host operator

Предположим:

```text
Device A
    user

Device B
    AppDock Node
    Strategy Box Host
    AI actor
```

Пользователь на A делегирует задачу AI на B.

## 30.1. Actor chain

Одного `author = ai` недостаточно. Нужны:

```text
requested_by
delegated_to
executed_by
approved_by?
```

Например:

```text
requested_by = user:Dima
delegated_to = agent:strategy-analyst
executed_by = node:B / agent:strategy-analyst
```

## 30.2. AI получает разрешённую поверхность

AI может:

```text
list allowed scenarios
inspect parameter schema
submit allowed scenario
get case/job status
read safe progress
read safe Problem explanation
get allowed ActionRefs
retrieve allowed artifacts
request approval
```

По умолчанию он не получает raw filesystem, raw logs, environment, tokens, all node files, arbitrary shell или полный traceback.

## 30.3. Ошибки для AI

Вместо сырых driver/library errors AI получает:

```text
problem_code
ProblemRef
impact
retry_advice
safe context
allowed actions
```

Это одновременно безопаснее и полезнее для agent reasoning.

---

# 31. AI actions и Audit

Для agent, remote, destructive и privileged actions нужен durable audit.

Если обязательный audit недоступен до необратимого действия:

```text
BLOCK ACTION
```

Нельзя допускать модель «audit сломался, но AI всё равно выполнил destructive operation».

---

# 32. Remote execution

Нужно выделить:

```text
ExecutionBackend
├── LocalExecutionBackend
└── RemoteNodeExecutionBackend
```

UI и Scenario Runner не должны знать, где реально выполняется operation.

Минимальный remote exchange:

```text
submit
→ accepted(job_id)

observe
→ progress/events/heartbeat

cancel
→ cancellation result

complete
→ terminal disposition + ProblemRef? + artifacts
```

Heartbeat и progress — разные сигналы. Heartbeat доказывает, что executor жив; progress доказывает продвижение задачи.

---

# 33. Network partition: использовать UNKNOWN

Если remote AI host выполняет задачу и связь пропадает, нельзя сразу писать `failed`.

Правильная projection:

```text
job connectivity = lost
terminal truth = unresolved
display = "Связь потеряна, итог уточняется"
```

После исчерпания reconciliation timeout возможен `UNKNOWN`.

При reconnect:

```text
query authoritative remote state
↓
success / partial / failure / cancelled
```

---

# 34. Process crash на remote host

Если remote Strategy Box process умер:

1. AppDock Node видит process exit;
2. AppDock регистрирует platform occurrence;
3. remote Job становится disconnected/unknown;
4. после восстановления выполняется reconciliation;
5. Case на client получает update;
6. shared Node Condition при необходимости показывается участникам.

Strategy Box process не является достаточным свидетелем собственного crash.

---

# 35. Causal problem chain

Возможен сценарий:

```text
Node storage unavailable
    ↓
Strategy Box export failed
```

Нельзя создавать две несвязанные проблемы. Допустимо:

```text
AppDock node.storage.unavailable
ProblemRef = P1

Strategy Box export failure
ProblemRef = P2
parent_problem_ref = P1
```

Либо Case может ссылаться напрямую на P1, если Node problem полностью объясняет failure и отдельный domain occurrence ничего не добавляет.


---

# 36. Observability self-health

Observability сама может деградировать. Это тоже должно быть частью модели.

## Debug log unavailable

Обычно operation продолжает работу, а система создаёт warning `observability degraded`.

## Problem journal unavailable

Если operation failure уже произошёл:

```text
FAILURE + registration_state = NOT_WRITTEN
```

## Recorder outcome unknown

```text
UNKNOWN + registration_state = OUTCOME_UNKNOWN
```

## Mandatory audit unavailable before destructive action

```text
BLOCK ACTION
```

## Disk full

Нужны emergency sink, drop counters, Node warning, cleanup по policy и отсутствие silent loss.

---

# 37. Bootstrap logging

Ошибки startup могут возникнуть до построения полного AppContext.

Нужен минимальный bootstrap sink:

```text
stderr
или
app-owned bootstrap file
или
ring buffer
```

После появления Node/AppDock context bootstrap evidence связывается с нормальной observability.

Важно: нельзя создавать fake `ProblemRef`, если Recorder ещё недоступен. Это совпадает с текущей AppDock моделью pre-Node startup failure.

---

# 38. Metrics

Metrics полезны как вторичный слой.

Минимальный набор:

```text
job queue wait
operation duration
scenario duration
success count
partial count
cancelled count
failure count
unknown count
retry count
active jobs
background lag
progress stalls
problem fingerprint frequency
log queue dropped records
observability write failures
```

Нельзя автоматически экспортировать банковские данные, содержимое файлов, URLs с query или user parameters.

---

# 39. OpenTelemetry и W3C Trace Context

OpenTelemetry имеет общую модель traces, metrics, logs, resources и events. Её полезно использовать как export/interoperability layer, а не как внутреннюю модель Strategy Box.

Правильная зависимость:

```text
Strategy Box causal IDs
        ↓
AppDock ContextEnvelope
        ↓
optional OTel trace/span
```

При remote execution через HTTP/RPC можно переносить W3C `traceparent`/`tracestate`, но trace ID не заменяет Case ID, Operation Run ID, actor, approval, Job ID и ProblemRef.

---

# 40. Security and privacy

Observability легко становится каналом утечки. Нужны audience-specific projections.

## User

Видит:

```text
что не получилось
что сохранилось
каков impact
можно ли retry
какие actions доступны
```

## Operator

Дополнительно видит Node, stage, frequency и safe diagnostics.

## Developer

При наличии права получает technical evidence, stack traces и version/revision.

## AI

Получает stable codes, safe context и allowed actions.

## Forensic

Только отдельный explicit permission.

---

# 41. Support bundle

На Case с ошибкой полезна кнопка `Собрать диагностику`.

Strategy Box support bundle может добавлять:

```text
Strategy Box version/revision
Case ID
Job ID
Operation Run IDs
ProblemRefs
safe runtime projection
relevant technical log excerpts
artifact metadata
redaction report
```

По умолчанию исключаются raw business data, credentials, secrets, unrestricted environment и полный workspace.

---

# 42. Artifact linkage

Артефакты должны иметь причинность:

```text
artifact_id
case_id
job_id
operation_run_id
attempt_id
created_at
producer
content hash?
source provenance?
```

Это позволяет понять, какой run создал файл, не принять artifact от старой неуспешной попытки и строить downstream chaining.

---

# 43. Retry и recovery

Retry должен быть first-class. Нужно различать:

```text
retry same operation
restart whole scenario
resume from checkpoint
reconcile existing remote job
```

Problem/domain issue даёт `retry_advice`, например:

```text
retry_immediately
retry_later
retry_after_user_action
do_not_retry
unknown
```

Observability сама не ремонтирует систему. Правильная схема:

```text
ProblemRef
↓
ActionRef
↓
owner recovery operation
↓
new OperationRun
↓
verified state
↓
Condition resolved
```

---

# 44. Diagnostics и repair — разные операции

Diagnostic должен быть read-only, bounded, cancellable и возвращать PASS/WARN/FAIL/UNKNOWN/SKIPPED плюс refs/evidence.

Repair — отдельная command, которая может менять state и требует собственного execution/audit.

Это важная AppDock идея, которую Strategy Box стоит принять напрямую.

---

# 45. Android и cross-device UI

Будущий Android должен получать те же semantic projections:

```text
CaseProjection
JobProjection
ProgressProjection
ProblemProjection
ArtifactProjection
NodeConditionProjection
AssignmentProjection
```

Он не должен получать Qt objects или Windows paths. Тяжёлая работа может оставаться на host.

Общими между Windows и Android должны стать:

```text
application execution models
job models
case models
problem links
progress models
artifact refs
assignment models
presence models
presentation/common projectors
AppDock contract DTOs
status vocabulary
redaction/display policy
```

Platform-specific остаются rendering и OS integration.

---

# 46. Target architecture `stratbox-windows`

Концептуальная структура:

```text
stratbox_windows/
│
├── application/
│   ├── operations/
│   │   ├── catalog/
│   │   ├── contracts/
│   │   └── execution/
│   ├── scenarios/
│   ├── jobs/
│   │   ├── models.py
│   │   ├── manager.py
│   │   └── ports.py
│   ├── observability/
│   │   ├── models.py
│   │   ├── ports.py
│   │   ├── projections.py
│   │   └── redaction.py
│   ├── cases/
│   ├── artifacts/
│   ├── assignments/
│   ├── presence/
│   └── workspace/
│
├── adapters/
│   ├── appdock/
│   │   ├── observability.py
│   │   ├── execution.py
│   │   └── runtime_state.py
│   ├── local_execution/
│   ├── persistence/
│   │   ├── sqlite_state.py
│   │   └── file_logs.py
│   └── desktop_host/
│
├── runtime/
│   ├── context.py
│   ├── bootstrap.py
│   ├── crash_capture.py
│   └── paths.py
│
└── presentation/
    ├── common/
    │   ├── scenario_chat/
    │   ├── execution/
    │   ├── problems/
    │   ├── node_conditions/
    │   └── case_inspector/
    └── qt_desktop/
```

Это направление, а не требование материализовать пустые пакеты заранее.

---

# 47. Минимальные additions в `stratbox`

Core нужна только нейтральная база, например:

```text
stratbox/
├── operations/
│   ├── contracts.py
│   ├── progress.py
│   └── diagnostics.py
└── ...
```

Либо contracts могут временно оставаться рядом с domain facade до появления нескольких consumers.

Главные ограничения:

```text
никакого AppDock import
никакого UI import
никакого global logger configuration
```

Library может использовать стандартный logger, но handlers конфигурирует caller.

---

# 48. Конкретные целевые projection models

## CaseProjection

```text
case_id
scenario_id
title
created_by
created_at
execution_mode
target_node_id
state
disposition?
current_job_id
current_stage
progress?
warning_count
problem_ref?
artifact_refs[]
started_at
updated_at
finished_at
unread
```

## JobProjection

```text
job_id
case_id
backend
target_node_id
requested_by
delegated_to?
executed_by?
state
heartbeat_status
current_operation_run_id?
current_attempt_id?
progress?
disposition?
problem_ref?
submitted_at
started_at
updated_at
finished_at
```

## ProblemProjection

UI обычно не нужен полный ProblemOccurrence:

```text
problem_ref
code
title
summary
severity
impact
retry_advice
status
allowed_actions[]
short_reference
```

## LogRef

```text
log_id
kind: app / operation / crash / stdout_stderr
node_id
case_id?
job_id?
operation_run_id?
attempt_id?
created_at
availability
evidence_ref?
```

## NodeNotice

```text
notice_id
condition_id
scope
severity
impact
title
summary
first_seen
last_seen
occurrence_count
latest_problem_ref
actions[]
```

Per-user read/ack state хранится отдельно и не меняет Condition.

---

# 49. Примеры end-to-end

## A. Local success

```text
user launch
↓
case prepared
↓
job queued
↓
job running
↓
operation run
↓
progress
↓
artifacts
↓
SUCCESS
↓
case completed
```

Physical log сохраняется. ProblemOccurrence не создаётся.

## B. Expected domain failure

```text
operation
↓
source unavailable
↓
typed domain failure
↓
surface maps to ProblemDraft
↓
AppDock Recorder
↓
ProblemRef
↓
FAILURE
↓
Case failed
```

UI показывает safe explanation; network exception остаётся Evidence.

## C. Partial result

```text
40 of 41 sources downloaded
1 source unavailable
policy allows partial
↓
PARTIAL
```

UI: «Завершено частично · 40/41 источников · 1 предупреждение».

## D. Process crash

```text
operation running
↓
process dies
↓
AppDock observes process exit
↓
canonical platform problem
↓
Case terminal truth absent
↓
UNKNOWN
↓
next launch reconciliation
```

После доказательства итог переводится в SUCCESS/PARTIAL/FAILURE.

## E. Shared resource failure

```text
user A
↓
shared source fails
↓
ProblemOccurrence P1
↓
shared Condition active
↓
users B/C receive NodeNotice
```

B/C не получают Case A или его raw details.

## F. AI-host

```text
user A
↓
delegated case
↓
remote Job on Node B
↓
AI actor executes allowed scenario
↓
progress + heartbeat
↓
ProblemRef / artifacts
↓
client updates Case
```

Destructive recovery проходит через ActionRef → policy → approval → audit → action.

---

# 50. Testing strategy

Observability требует сильных fault-path tests.

## Core

- success;
- partial;
- expected failure;
- validation issues;
- cancellation;
- progress ordering;
- no UI/AppDock imports;
- no handler configuration.

## Surface execution

- raw exception never leaks into product result;
- safe failure projection;
- distinct execution IDs;
- retry changes attempt, а не user goal;
- cancellation;
- unknown result;
- artifact linkage.

## Persistence

- transaction rollback;
- crash during write;
- corrupt DB;
- schema mismatch;
- concurrent reader/writer;
- retention.

## Logs

- rotation;
- disk full;
- permission denied;
- queue overflow;
- flush on terminal error;
- redaction;
- secret parameter never persists;
- foreign unauthorized log cannot be resolved.

## AppDock bridge

- exactly one problem registration;
- `ProblemRef` propagated unchanged;
- recorder unavailable;
- recorder outcome unknown;
- Node health projection;
- Session linkage;
- no raw exception in transport.

## Remote

- submit/accept;
- duplicate delivery;
- reconnect;
- heartbeat timeout;
- lost completion;
- UNKNOWN reconciliation;
- cancellation race;
- late result.

## Collaboration

- private user error not broadcast;
- shared Node problem broadcast;
- dedup by fingerprint;
- resolved notice;
- per-user unread state;
- permission filtering.

## AI

- actor identity;
- delegation chain;
- denied action;
- approval;
- audit unavailable blocks destructive action;
- raw logs unavailable without privilege.

---

# 51. Fault injection matrix

Обязательные сценарии:

```text
disk full
log directory readonly
problem journal unavailable
corrupt local state
network unavailable
remote node disappears
clock skew
duplicate remote event
out-of-order remote event
process hard kill
worker thread crash
UI exception
unraisable exception
artifact write succeeds but response lost
cancel during commit
```

Observability без fault injection быстро превращается в логирование happy path.

---

# 52. Приоритетный roadmap

## Этап 0 — очистить baseline

1. синхронизировать contracts/tests/docs `stratbox-windows`;
2. удалить tracked `.tmp`;
3. удалить `.pyc`/`__pycache__`;
4. исправить `.gitignore`;
5. добавить CI;
6. покрыть текущие ScenarioRunner/OperationRunner/history тестами.

## Этап 1 — единый Result/Progress contract в `stratbox`

1. terminal disposition;
2. typed domain issues;
3. progress reporter;
4. diagnostics;
5. artifact/provenance envelope;
6. library logging policy.

## Этап 2 — новый execution model `stratbox-windows`

1. разделить operation name и operation run ID;
2. Case → Job → OperationRun → Attempt;
3. frontend-neutral Job Manager;
4. local execution backend;
5. cancellation;
6. retries;
7. `UNKNOWN`.

## Этап 3 — безопасная local observability

1. structured logs;
2. rotation/retention;
3. LogRef;
4. redaction;
5. crash/bootstrap hooks;
6. SQLite `SurfaceStateStore`;
7. safe parameter persistence policy.

## Этап 4 — AppDock Observability Bridge

1. causal mapping;
2. ProblemDraft → Recorder;
3. canonical ProblemRef;
4. Node/Session projection;
5. evidence linkage;
6. self-health degradation.

Этот этап должен стыковаться с фактическим развитием AppDock public SDK, а не замораживать частный промежуточный protocol Strategy Box.

## Этап 5 — background execution

1. TriggerSpec;
2. scheduler;
3. background submits same jobs;
4. active job view;
5. persistence;
6. restart recovery.

## Этап 6 — collaboration

1. shared Condition projection;
2. Node notices;
3. real presence provider;
4. remote assignments;
5. permissions;
6. acknowledgements.

## Этап 7 — remote Node execution

1. RemoteExecutionBackend;
2. heartbeat;
3. reconciliation;
4. artifact references/transfer;
5. remote cancellation;
6. network UNKNOWN semantics.

## Этап 8 — AI actor

1. machine-readable scenario catalog;
2. actor/delegation chain;
3. policy;
4. approvals;
5. durable audit;
6. safe Problem/Action projection.

## Этап 9 — Android

Android переиспользует application models, jobs, cases, progress, problem projections, `presentation/common` и AppDock contract DTOs; меняются rendering и platform adapters.

---

# 53. Что делать первым именно по этой теме

Если выделить ближайшее ядро разработки:

1. убрать `str(exc)` из product model;
2. заменить boolean `ok` на terminal disposition;
3. ввести `case_id / job_id / operation_run_id / attempt_id`;
4. сделать explicit progress contract;
5. вынести Job Manager из Qt;
6. перевести background на тот же execution path;
7. заменить local JSON history на transactional state store;
8. сделать structured rotating physical logs + redaction;
9. ввести AppDock Observability Bridge port;
10. связать failures с canonical `ProblemRef` AppDock;
11. после этого строить shared warnings и remote/AI execution.

Так сохраняется правильный порядок причинности и не возникает второй параллельной observability платформы.

---

# 54. Что не стоит делать

- Не строить центральный Log Manager как основу архитектуры: лог — evidence, а не state truth.
- Не передавать traceback пользователю по умолчанию.
- Не использовать `str(exception)` как API.
- Не превращать expected domain failures в произвольные exceptions.
- Не превращать exceptions в `False`, `[]`, `None` без сохранения смысла.
- Не считать пустой результат доказательством отсутствия данных.
- Не строить отдельный background engine.
- Не broadcast все ошибки всем участникам.
- Не хранить OS path как remote contract.
- Не считать timeout доказательством failure.
- Не давать AI raw log access по умолчанию.
- Не делать OpenTelemetry источником истины.
- Не копировать AppDock ProblemOccurrence в Strategy Box database — хранить `ProblemRef`.
- Не смешивать diagnostics и repair.
- Не позволять destructive/agent action без обязательного audit, если policy требует audit.

---

# 55. Главные решения в 15 тезисах

1. **Case — пользовательская цель; Job — исполняемая единица.**
2. **Foreground, background, remote и AI проходят через один Job Manager.**
3. **Stable operation name и конкретный operation run ID — разные вещи.**
4. **Retry получает новый attempt ID.**
5. **Case ID естественно становится correlation ID.**
6. **Terminal outcomes: SUCCESS / PARTIAL / CANCELLED / FAILURE / UNKNOWN.**
7. **Warnings — diagnostics, а не terminal outcome.**
8. **`stratbox` выдаёт structured result/progress и не знает AppDock.**
9. **`stratbox-windows` владеет case/job projections, но не canonical platform problem.**
10. **AppDock владеет canonical ProblemOccurrence и Node/Session problem linkage.**
11. **Raw exception и traceback живут только как technical evidence.**
12. **Physical logs обязательны, bounded, rotating, redacted и node-local.**
13. **Другим пользователям показываются shared Conditions, а не чужие raw errors.**
14. **ИИ — audited actor с более строгими permissions, а не отдельная магическая система.**
15. **Windows и Android должны рендерить один platform-neutral execution/observability смысл.**

---

# 56. Итоговая целевая пользовательская картина

В зрелом Strategy Box пользователь видит:

```text
Сценарии
────────────────────────────────────

Обновление данных Банка России

● Выполняется на Host-Office
  Загрузка файлов · 18/41 · 44%

  Запустил: Дмитрий
  Выполняет: Strategy Box Host
  15:31 · 2 мин. 14 сек.

  [Детали] [Отменить]
```

При общей проблеме:

```text
⚠ На узле обнаружена общая проблема

Источник Банка России временно недоступен.
Затронуты 3 активных сценария.

[Подробнее] [Перепроверить]
```

При персональной problem:

```text
История счетов эскроу

✕ Не выполнено

Не удалось завершить загрузку.
Уже сформированные результаты сохранены.

Код: cbr.source.unavailable
Problem: …7f31

[Повторить] [Диагностика]
```

Technical traceback остаётся в локальном evidence/log, доступном оператору или support bundle.

Удалённый AI получает машинную эквивалентную projection:

```text
disposition = failure
problem_ref = ...
retry_advice = retry_later
allowed_actions = [...]
```

и не получает секреты или бесконтрольный shell.

Именно такой контур превращает Strategy Box из desktop-приложения с логами в **наблюдаемую распределённую рабочую систему**, где человек, background scheduler, удалённый host, Android-клиент и ИИ-актор видят одну и ту же доказуемую картину выполнения.

---

# 57. Источники

## Strategy Box research corpus

- `stratbox_base_study_current_state_2026-10-06.md`
- `stratbox-windows_current_state_full_research_2026-10-06.md`
- приватное исследование environment-specific extension от 2026-10-06
- `AppDock - Базовое описание.docx`

## AppDock repository

- `ForestTiger-GH/AppDock`
- `docs/architecture/observability/README.md`
- `docs/architecture/observability/TARGET_MODEL.md`
- `docs/architecture/observability/IMPLEMENTATION_STATUS.md`
- `src/appdock/domains/observability/public/*`
- `src/appdock/domains/execution/results/operation_results.py`
- `src/appdock/domains/node/health/*`
- `src/appdock/domains/sessions/models.py`

## Current `stratbox-windows` source

- `application/operations/execution/runner.py`
- `application/scenarios/runner.py`
- `application/cases/models.py`
- `application/events/models.py`
- `application/logs/*`
- `application/history/persistence.py`
- `application/background/*`
- `adapters/appdock/surface_state.py`
- `runtime/logging.py`

## External standards and official documentation

- OpenTelemetry Semantic Conventions: https://opentelemetry.io/docs/specs/semconv/
- OpenTelemetry Logs Data Model: https://opentelemetry.io/docs/specs/otel/logs/data-model/
- W3C Trace Context: https://www.w3.org/TR/trace-context/
- Python logging handlers: https://docs.python.org/3/library/logging.handlers.html
- Python faulthandler: https://docs.python.org/3/library/faulthandler.html
- Python sys hooks: https://docs.python.org/3/library/sys.html
- Python threading exception hook: https://docs.python.org/3/library/threading.html
