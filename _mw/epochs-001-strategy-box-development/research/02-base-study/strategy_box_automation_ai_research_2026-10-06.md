# Strategy Box — автоматизация, планировщик и ИИ-контур

**Ветка исследования:** 02-base-study / automation & AI  
**Дата:** 2026-10-06  
**Статус:** Research Result  
**Назначение:** внутренний исследовательский материал проекта Strategy Box. Документ не предназначен для автоматической публикации в открытые репозитории.

---

## 0. Краткий вывод

Strategy Box уже имеет большую часть **семантического фундамента**, который нужен для автоматизации и ИИ, хотя сами эти механизмы пока реализованы лишь частично.

Текущая архитектура естественно раскладывается на три независимых уровня:

```text
1. Детерминированная автоматизация
   расписание / событие / изменение источника
        ↓
   scenario / operation
        ↓
   case / artifacts / diagnostics

2. Разговорное управление
   пользователь пишет обычным языком
        ↓
   AI понимает намерение
        ↓
   выбирает готовый scenario или cascade
        ↓
   система выполняет его детерминированно

3. Агентная работа
   пользователь задаёт цель
        ↓
   AI строит план
        ↓
   вызывает operations/scenarios
        ↓
   анализирует структурированные результаты и artifacts
        ↓
   выбирает следующий шаг
        ↓
   при необходимости запрашивает подтверждение
        ↓
   завершает работу или передаёт её человеку
```

Главный архитектурный вывод:

> **ИИ не должен становиться новым вычислительным ядром Strategy Box. Он должен стать управляющим слоем поверх канонических операций, сценариев, артефактов и состояния выполнения.**

Расчёты, загрузки, проверки, преобразования и построение финансовых/макроэкономических данных должны оставаться в `stratbox`. Сценарная семантика, jobs/cases, automation contracts и platform-neutral orchestration должны жить в общем application-слое Strategy Box. AppDock естественно становится владельцем долгоживущего host/runtime-контура, удалённого исполнения, разрешений и MCP-представления возможностей. Windows и будущий Android остаются пользовательскими поверхностями.

Самая перспективная схема:

```text
                        Пользователь
                             │
                  GUI / chat / mobile / API
                             │
            Strategy Box application contracts
        operations / scenarios / artifacts / cases
             jobs / automation / approvals / policy
                 │              │             │
                 ▼              ▼             ▼
        deterministic       AI control     scheduler
           runner             plane          / host
                 │              │             │
                 └──────────────┼─────────────┘
                                ▼
                           stratbox core
                                │
                  data / calculations /
                  validation / artifacts
```

Важнейшее решение для будущей реализации: **не делать отдельный AI API, отдельный background API и отдельный GUI API для одной и той же предметной функции**. Нужен один канонический capability/operation contract. GUI, scheduler, AI и remote host должны быть разными consumers одного контракта.

---

# I. Исходная позиция проекта

## 1. Что уже есть в `stratbox`

Текущее ядро уже движется к модели, где предметная функция представлена устойчивой операцией:

```text
Request
  ↓
domain operation
  ↓
Result
  ├─ status
  ├─ data
  ├─ warnings
  ├─ failures
  ├─ diagnostics
  ├─ artifacts
  └─ provenance
```

В исследовании core уже был выделен будущий operation registry со stable IDs и metadata уровня:

```text
operation_id
domain
title
request_type
result_type
side_effects
network_required
storage_required
destructive
supports_partial
artifact_kinds
```

Это почти идеальная основа для автоматизации и AI tool calling.

Ключевой принцип следует сохранить:

> Operation — это не любая Python-функция. Это устойчивый предметный use case.

Например:

```text
cbr.files.collect
cbr.forms.build
cbr.industries.build_stream
escrow.build_history
frg.scan
frg.cleanup.plan
frg.cleanup.execute
sors.restore
sors.export
```

Такой набор достаточно стабилен для GUI, scheduler, CLI, AppDock и ИИ.

## 2. Что уже есть в `stratbox-windows`

Текущий surface содержит особенно полезные для будущего элементы:

- `OperationSpec`;
- `ScenarioSpec`;
- atomic scenarios;
- composite scenario;
- последовательный scenario runner;
- cases и step runs;
- events;
- logs;
- artifacts;
- actor kinds, включая `ai`;
- `ai_visibility`;
- background-process model и UI;
- assignments;
- runtime-state projection;
- AppDock Activation Context;
- diagnostics;
- managed workspace;
- async execution через Qt worker.

То есть Strategy Box уже думает в правильных сущностях.

Сейчас разрыв находится между **семантикой** и **engine**:

```text
семантика background есть
scheduler отсутствует

семантика ai actor есть
AI runtime отсутствует

case.cancelled есть
реального cancellation path нет

remote направление есть
execution backend пока local

artifact entity есть
lineage/query/agent interaction ещё минимальны
```

Это хорошая ситуация: новый слой можно строить как развитие существующих contracts, а не как параллельную архитектуру.

## 3. Что даёт AppDock

В продуктовой модели AppDock уже заложены управляемая рабочая среда, узлы, действия вместо команд, долгие операции, host, remote execution, состояние, результаты, recovery, роли, permissions, подтверждения, история действий и будущие AI agents.

Это делает AppDock логичным владельцем **runtime и policy plane**, а Strategy Box — владельцем **domain/action semantics**.

Практически:

```text
Strategy Box говорит:
"что можно делать и как выглядит результат"

AppDock говорит:
"где это выполнять, кому разрешено, когда запускать,
как подключить модель, как дать remote access,
как восстановить выполнение и как показать состояние"
```

---

# II. Главная модель: пять разных сущностей

## 4. Operation

**Operation** — атомарный предметный use case.

Примеры: скачать публикации ЦБ, построить canonical dataset, выгрузить workbook, проверить workspace, построить историю escrow, восстановить SORS.

Operation должна быть пригодна для ручного вызова, GUI, тестов, сценария, scheduler, AI tool call и remote executor. Она обязана иметь typed input и typed result.

## 5. Scenario

**Scenario** — пользовательская композиция операций.

```text
scenario.cbr.full_update
  1. cbr.files.collect
  2. cbr.forms.build
  3. escrow.build_history
  4. export/report
```

Scenario отвечает за orchestration: порядок, mapping параметров, conditions, retries, parallel branches, continue/fail-fast, checkpoints и expected artifacts. Scenario не должен содержать собственную банковскую формулу.

## 6. Automation

**Automation** — правило, когда и при каких условиях создать новый запуск scenario.

```text
AutomationSpec
├─ trigger
├─ target scenario
├─ parameters
├─ execution policy
├─ concurrency policy
├─ retry policy
├─ notification policy
└─ approval policy
```

Это отдельная сущность от background process. Например:

```text
"каждый рабочий день в 07:30"
        ↓
scenario.cbr.daily_update
```

или:

```text
"когда официальный источник изменился"
        ↓
scenario.cbr.refresh_source
```

## 7. Job

**Job** — техническая заявка на выполнение. Automation, пользователь, AI или remote caller создают одинаковый Job.

```text
Job
├─ job_id
├─ target_type = operation | scenario
├─ target_id
├─ params
├─ origin
├─ principal
├─ created_at
├─ requested_backend
├─ idempotency_key
├─ priority
├─ deadline
└─ policy snapshot
```

Job отвечает на вопрос: **что система должна выполнить?**

## 8. Case

**Case** — пользовательская история конкретного исполнения.

```text
Case
├─ case_id
├─ job_id
├─ scenario
├─ origin
├─ initiator
├─ status
├─ stages
├─ events
├─ logs
├─ artifacts
├─ diagnostics
├─ approvals
└─ timestamps
```

Case отвечает: **что произошло с этим запуском?** Текущий `ScenarioRunCase` уже близок к этой модели.

## 9. AgentRun

**AgentRun** — отдельная история интеллектуального решения задачи. Она может породить один или несколько Job/Case.

```text
AgentRun
├─ objective
├─ conversation_id
├─ model/provider
├─ policy
├─ tool calls
├─ referenced artifacts
├─ decisions
├─ approvals
├─ child cases
├─ final answer
└─ usage/limits
```

AgentRun не следует смешивать с Case.

Пример:

```text
AgentRun:
"проанализируй последние данные по кредитованию и подготовь вывод"

   ├─ Case #1: check sources
   ├─ Case #2: collect new CBR files
   ├─ Case #3: rebuild industry dataset
   └─ Case #4: export analytical workbook
```

---

# III. Автоматизация без ИИ

## 10. Почему сначала нужен scheduler, а потом agent

Планировщик должен быть полностью пригоден для работы без LLM. Расписание детерминировано; recurring job должен работать при недоступности AI provider; модель не нужна для вычисления cron; recovery/retry не должны зависеть от языка модели.

Правильная зависимость:

```text
AI может СОЗДАТЬ или ИЗМЕНИТЬ AutomationSpec
        ↓
после подтверждения она сохраняется
        ↓
дальше AutomationSpec исполняется без AI
```

То есть фраза «Каждое утро обновляй данные ЦБ в 7:30» может быть переведена AI в структурированный объект один раз. После этого обычный scheduler работает самостоятельно.

---

# IV. Модель триггеров и scheduler semantics

## 11. Time-based triggers

Минимальный набор:

```text
OnceTrigger
IntervalTrigger
CronTrigger
CalendarTrigger
```

Для каждого schedule следует хранить **IANA timezone**, а не только UTC offset. Это важно для DST и переноса расписаний между узлами.

## 12. Event triggers

Strategy Box особенно выиграет от событий:

```text
case.completed
case.failed
artifact.created
source.changed
source.missing
validation.failed
registry.changed
workspace.available
node.online
node.recovered
approval.granted
```

Пример:

```text
source.changed(cbr.corporate_lending)
        ↓
refresh source
        ↓
validate
        ↓
rebuild dependent datasets
        ↓
publish artifacts
```

## 13. Data-aware triggers

Для аналитического приложения они важнее простого cron.

Нужны условия:

```text
on_source_change
on_new_period
on_missing_period
on_registry_version_change
on_artifact_stale
on_validation_status
on_dependency_materialized
```

Такая модель близка по смыслу к asset-centric automation современных data orchestrators, но Strategy Box может реализовать её в собственной предметной форме.

## 14. Compound triggers

В перспективе полезны:

```text
AND:
  публикация обновилась
  И рабочий день
  И источник прошёл validation

OR:
  08:00
  ИЛИ manual force-refresh

SEQUENCE:
  source A changed
  затем source B changed
  в течение 2 часов
```

Эту сложность можно отложить, но schema лучше сразу не делать тупиковой.

## 15. Misfire policy

Что делать, если приложение/host был выключен во время запуска:

```text
skip
run_once_now
catch_up_all
catch_up_latest
```

Для большинства аналитических refresh-сценариев разумный default — `catch_up_latest`: после простоя обычно нужен актуальный snapshot, а не пять одинаковых запусков подряд.

## 16. Overlap policy

Если предыдущее выполнение ещё идёт:

```text
allow
forbid
replace
queue
coalesce
```

Для update pipelines чаще всего подходит `forbid + coalesce`.

## 17. Idempotency

Scheduler, remote retries и agent retries неизбежно создают повторные запросы. Поэтому Job нужен `idempotency_key`.

Пример ключа:

```text
scenario_id
+ normalized params
+ effective_period
+ source_snapshot_ids
```

Повторный request тогда может вернуть уже активный/готовый Case либо создать новый только при `force=true`.

## 18. Retry

Retry должен зависеть от класса ошибки.

```text
network timeout        → retry
HTTP 503               → retry
temporary host offline → retry
validation failure     → no retry
invalid parameters     → no retry
permission denied      → no retry
authentication needed  → pause / input_required
```

Нужны явные состояния:

```text
retryable
terminal
input_required
approval_required
cancelled
partial
```

---

# V. Где должен жить scheduler

## 19. Почему не внутри Qt GUI

Если расписание живёт только в `stratbox-windows`, окно должно быть постоянно запущено; закрытие приложения остановит задания; Android получит отдельный executor; remote host превратится в параллельную систему; recovery станет сложнее; несколько клиентов смогут породить дубли.

Поэтому GUI должен быть **control surface**, а не главным scheduler process.

## 20. Рекомендуемая граница

```text
stratbox-windows / stratbox-android
       │
       │ create/edit/pause automation
       ▼
AppDock node / host runtime
       │
       ├─ AutomationStore
       ├─ Scheduler
       ├─ JobStore
       ├─ JobManager
       ├─ ExecutionBackend registry
       └─ EventBus
               │
               ▼
      Strategy Box scenario runner
```

Если AppDock ещё не готов к этому уровню, временный local implementation можно сделать рядом с application layer, но интерфейс лучше сразу проектировать как host-service contract.

---

# VI. Хранилище состояния

## 21. JSON уже становится слишком слабым

Текущие JSON history files удобны для прототипа, но automation/agent потребуют atomic updates, concurrent readers/writers, indexing, job claiming, retries, leases, audit, query by state, retention и relationships между jobs/cases/artifacts/agent runs.

Для локального узла естественный следующий шаг — SQLite.

```text
strategy_box_runtime.db

automations
jobs
job_attempts
cases
case_steps
events
artifacts
artifact_links
approvals
agent_runs
agent_tool_calls
conversations
notifications
```

Файлы артефактов продолжают жить в FileStore/workspace. База хранит metadata и runtime state.

---

# VII. Первый ИИ-путь: conversational control

## 22. Что это такое

Это самый полезный и самый безопасный первый AI слой.

Пользователь вместо выбора формы пишет:

> «Обнови данные Банка России и собери новую историю эскроу».

ИИ выполняет только semantic routing:

```text
natural language
     ↓
intent extraction
     ↓
scenario selection
     ↓
typed parameter generation
     ↓
policy validation
     ↓
preview/confirmation if needed
     ↓
normal scenario runner
```

После выбора сценария AI больше не управляет шагами.

## 23. Почему начинать стоит именно с этого

- почти нет новой runtime complexity;
- мало риска;
- легко оценивать качество;
- результат воспроизводим;
- пользователь перестаёт искать сценарий вручную;
- AI не получает свободный контроль;
- существующий `ScenarioRegistry` сразу становится полезен.

## 24. Как должен выглядеть результат AI router

Не строка с Python-командой, а typed intent:

```json
{
  "intent": "run_scenario",
  "scenario_id": "scenario.cbr.full_update",
  "params": {
    "refresh": true
  },
  "confidence": 0.94,
  "needs_confirmation": false
}
```

Дальше application service валидирует schema и доступность exact ID.

## 25. Не позволять модели выдумывать scenario IDs

Модель должна получать фактически доступный каталог. При росте каталога нужен search/retrieval слой:

```text
user text
→ scenario search
→ small candidate set
→ model chooses exact ID
→ server validates ID and params
```

---

# VIII. Второй ИИ-путь: настоящий агент

## 26. Отличие от conversational router

Router отвечает: «Какой готовый сценарий имел в виду пользователь?»

Agent отвечает: «Как достичь цели, если заранее неизвестно, сколько шагов понадобится?»

Пример:

> «Проверь, вышли ли свежие данные ЦБ по корпоративному кредитованию, обнови расчёты, сравни с прошлым месяцем и если увидишь аномалию — найди, на каком этапе она возникла».

Здесь заранее неизвестен полный cascade.

## 27. Базовый agent loop

```text
1. Understand objective
2. Inspect available capabilities/resources
3. Build short execution plan
4. Select next safe action
5. Validate arguments
6. Execute tool
7. Read structured result
8. Inspect artifacts/diagnostics
9. Decide whether objective is complete
10. Continue / ask user / stop
```

## 28. Planner и executor должны быть разделены

```text
LLM planner
   │ proposes
   ▼
Policy Engine
   │ approves capability
   ▼
Deterministic Executor
   │
   ▼
Operation / Scenario
```

Модель не должна напрямую импортировать Python modules, писать shell-команды, удалять файлы, менять runtime database, обращаться к credentials или обходить operation registry.

## 29. «LLM планирует, код считает»

Для финансового приложения это центральный принцип.

Плохо:

```text
AI получил Excel
→ сам в тексте посчитал темпы роста
→ сам сделал вывод
```

Лучше:

```text
AI: "мне нужна динамика показателя X"
→ вызывает deterministic operation
core: строит canonical calculation
→ возвращает typed result
AI: объясняет результат
```

Числовая бизнес-логика должна быть воспроизводимой.

---

# IX. Agent interaction with artifacts

## 30. Артефакт должен стать адресуемым объектом

Для агента нужен расширенный contract:

```text
artifact_id
kind
mime_type
storage_uri
content_hash
size
created_at
created_by_case
created_by_operation
parent_artifact_ids
source_snapshot_ids
schema_id
period
tags
sensitivity
preview_capabilities
query_capabilities
retention
provenance
```

## 31. Агенту лучше давать artifact ID, а не произвольный path

Например:

```text
artifact://case/01J.../output/3
```

Инструменты:

```text
artifact.get_metadata
artifact.preview
artifact.read_text
artifact.read_table_slice
artifact.describe_table
artifact.compare
artifact.export
artifact.open_for_user
```

Это даёт security boundary, одинаковый Windows/Android/remote интерфейс, lineage и permission checks.

## 32. Большие таблицы нельзя целиком класть в LLM context

Нужен query/preview слой.

```text
describe_table:
  rows: 1_200_000
  columns: ...
  null stats: ...
  date range: ...
  units: ...

read_table_slice:
  columns=[...]
  filter=...
  limit=100
```

AI должен получать только необходимую часть.

---

# X. Artifact lineage и AI provenance

## 33. Почему lineage нужен именно сейчас

При автоматизации быстро появятся цепочки:

```text
source snapshot
  ↓
canonical dataset
  ↓
derived dataset
  ↓
Excel
  ↓
report
```

Agent должен уметь ответить: «Из каких источников построен этот файл?»

Минимальный lineage graph:

```text
Artifact
  ├─ produced_by_case
  ├─ produced_by_step
  ├─ produced_by_operation
  ├─ input_artifacts
  ├─ source_snapshots
  ├─ registry_versions
  └─ parameters_hash
```

## 34. Решение агента тоже должно иметь provenance

Скрытый chain-of-thought сохранять не нужно. Нужна структурированная запись решения:

```text
DecisionRecord
├─ decision_id
├─ agent_run_id
├─ objective
├─ selected_action
├─ selected_tool
├─ referenced_result_ids
├─ referenced_artifact_ids
├─ concise_reason
├─ policy_outcome
├─ approval_id
└─ timestamp
```

Это позволяет объяснить, почему система запустила именно этот сценарий, без зависимости от внутреннего reasoning trace модели.

---

# XI. MCP как внешний AI-контракт

## 35. Где MCP особенно хорошо подходит

MCP естественно отображает Strategy Box.

### MCP Tools

То, что модель может вызвать:

```text
scenario.search
scenario.describe
scenario.run
operation.run
job.get
job.cancel
case.get
artifact.preview
artifact.query
automation.create_draft
automation.validate
automation.activate
```

### MCP Resources

То, что приложение/агент может читать как контекст:

```text
strategybox://catalog/operations
strategybox://catalog/scenarios
strategybox://case/{id}
strategybox://artifact/{id}/metadata
strategybox://artifact/{id}/preview
strategybox://runtime/health
strategybox://workspace/schema
strategybox://data-dictionary/...
```

### MCP Prompts

User-selected templates:

```text
"Обновить данные ЦБ"
"Объяснить артефакт"
"Сравнить два периода"
"Проверить качество источников"
```

## 36. Не кодировать MCP внутри `stratbox`

Плохая связь:

```text
stratbox domain
  imports MCP SDK
```

Лучше:

```text
stratbox
  exposes canonical operations

Strategy Box application
  exposes capability catalog

AppDock adapter
  translates capabilities → MCP
```

Так MCP остаётся транспортом/AI protocol, а не частью предметной модели.

## 37. Capability catalog как единый источник истины

Полезно расширить descriptor:

```text
CapabilityDescriptor
├─ id
├─ title
├─ description
├─ input_schema
├─ output_schema
├─ kind = operation | scenario | query | control
├─ read_only
├─ destructive
├─ idempotent
├─ open_world
├─ network_required
├─ storage_required
├─ risk_level
├─ approval_policy
├─ ai_visibility
├─ user_visibility
├─ supports_async
├─ supports_cancel
├─ estimated_duration_class
├─ artifact_inputs
└─ artifact_outputs
```

Из него автоматически строятся GUI forms, AI tools, документация, permission UI, scheduler target picker, Android forms и API schemas.

---

# XII. Актуальный MCP 2026 и последствия

## 38. Tools имеют structured schemas

Актуальный MCP позволяет задавать input/output schemas. Это хорошо совпадает с typed Request/Result Strategy Box.

Следствие:

> Чем лучше нормализованы contracts в `stratbox`, тем меньше специального кода понадобится для MCP.

## 39. Tool annotations

MCP поддерживает hints:

```text
readOnly
destructive
idempotent
openWorld
```

Они хорошо отображаются на Strategy Box descriptors. Но это именно **подсказки клиенту**, а не механизм безопасности. Strategy Box/AppDock должны самостоятельно enforce policy.

## 40. MCP Tasks

Актуальное расширение Tasks позволяет tool call вернуть task handle вместо мгновенного результата.

Это почти прямая проекция:

```text
MCP Task
   ↕ adapter mapping
Strategy Box Job / Case
```

Но внутренние сущности Strategy Box не следует делать MCP-зависимыми.

Правильно:

```text
internal Job/Case = source of truth
MCP task = external representation
```

## 41. Input required

Современный MCP поддерживает состояние, когда long-running action требует дополнительного ввода.

Это полезно для approval, выбора варианта, authentication flow, уточнения параметров и conflict resolution.

Например:

```text
agent calls frg.cleanup.execute
        ↓
Policy Engine
        ↓
APPROVAL_REQUIRED
        ↓
MCP task/input_required
        ↓
Windows/Android shows approval
        ↓
user accepts
        ↓
execution continues
```

## 42. Не строить новую архитектуру вокруг старых MCP back-channels

В ревизии MCP 2026-07-28 standalone sampling/roots/logging были объявлены deprecated, а взаимодействие с дополнительным вводом было переведено к multi-round-trip/input-required модели.

Практический вывод:

- LLM provider лучше подключать через AppDock AI runtime напрямую;
- рабочие области передавать через capability/resource identifiers;
- не делать старый server→client sampling фундаментом Strategy Box.

---

# XIII. AppDock как AI gateway

## 43. Предлагаемая роль AppDock

AppDock может стать:

```text
AI Host
+ MCP Host/Client
+ permission broker
+ credential boundary
+ scheduler host
+ remote execution broker
+ notification surface
```

При этом Strategy Box остаётся обычным подключаемым world/product.

## 44. Поток запроса из чата

```text
User
 ↓
stratbox-windows chat
 ↓
AIConversationService
 ↓
AppDock AI bridge
 ↓
LLM
 ↓
MCP tool choice
 ↓
AppDock policy check
 ↓
Strategy Box capability adapter
 ↓
Scenario/Operation
 ↓
Case
 ↓
Artifacts
 ↓
MCP result/resource
 ↓
LLM summary
 ↓
chat
```

Windows surface при этом не обязана знать конкретного AI provider.

## 45. Будущий Android

Android получает тот же contract:

```text
presentation/android
        ↓
shared application contracts
        ↓
AppDock mobile bridge
        ↓
same cases / approvals / artifacts / AI conversations
```

Так mobile может быть полноценным client, companion, approval surface и notification surface.

---

# XIV. Уровни автономности

## 46. Не делать один флаг `ai_enabled`

Полезнее явно задавать policy.

### Level A — Explain only

ИИ может читать catalog/metadata, объяснять и рекомендовать. Tool execution отсутствует.

### Level B — Propose

ИИ формирует план и параметры, пользователь нажимает «Запустить».

### Level C — Auto read/compute

ИИ самостоятельно вызывает read-only operations, deterministic calculations, validations и artifact previews.

### Level D — Controlled writes

ИИ может создавать новые artifacts и запускать additive operations.

### Level E — Approval-gated destructive

Удаление, overwrite, cleanup и privileged external side effects требуют явного approval.

---

# XV. Risk model и approvals

## 47. Полезные категории операций

```text
R0  read metadata
R1  read data / compute
R2  create artifact
R3  update non-critical state
R4  overwrite / move / external write
R5  delete / destructive / privileged
```

Политика задаётся на уровне capability.

## 48. Plan/apply для опасных операций

Вместо:

```text
agent → delete
```

нужно:

```text
agent → build_cleanup_plan
      → preview
      → approval
      → execute exact plan
```

Plan получает immutable ID/hash. Execute принимает именно этот plan ID. Если состояние изменилось, plan становится stale и execution блокируется.

## 49. Approval — first-class entity

```text
ApprovalRequest
├─ approval_id
├─ agent_run_id
├─ case_id
├─ action
├─ arguments_summary
├─ impact
├─ plan_id
├─ expires_at
├─ requested_by
├─ decided_by
├─ decision
└─ timestamp
```

Пользователь должен видеть **что будет сделано, какие данные затронуты, какие артефакты изменятся, почему агент хочет это сделать и можно ли отменить**. UI «Разрешить tool call?» слишком беден для серьёзного аналитического продукта.

---

# XVI. Credentials, secrets и prompt injection

## 50. Модель никогда не должна получать секрет

Правильный tool:

```text
download_from_source(source_id)
```

а не:

```text
download(url, username, password)
```

Credentials разрешаются внутри environment capability. Модель может видеть `auth_status = READY`, но не credential value.

## 51. Экономические источники считаются данными, а не инструкциями

Agent будет читать HTML, Excel, документы, PDF, тексты и metadata. Такой контент потенциально может содержать prompt injection.

Rule:

```text
system/policy instructions
    >
capability contract
    >
user objective
    >
external data content
```

Внешний документ не может повысить permissions.

## 52. Tool output тоже недоверенный

Даже описание стороннего MCP server/tool нельзя считать authority для privilege escalation. AppDock policy должен решать:

- разрешён ли server;
- разрешён ли tool;
- какие scopes доступны;
- нужен ли approval;
- какие данные можно вернуть модели.

---

# XVII. Agent limits

## 53. Любой AgentRun должен иметь budget

```text
max_tool_calls
max_steps
max_wall_time
max_model_cost
max_artifacts_read
max_external_requests
deadline
```

Это защищает от зацикливания, чрезмерных расходов, endless retries и слишком широкого исследования.

## 54. Stop reasons

Нужны явные:

```text
completed
user_input_required
approval_required
blocked_by_policy
budget_exhausted
deadline_exceeded
tool_failed
no_safe_next_action
cancelled
```

---

# XVIII. Notifications

## 55. Automation без notifications неполна

Нужен отдельный `NotificationPolicy`.

Примеры:

```text
on_success = silent
on_failure = notify
on_partial = notify
on_approval_required = urgent
on_new_artifact = summary
```

Каналы позже могут быть Windows, Android, AppDock, email или corporate messenger. Runtime event должен оставаться один.

---

# XIX. AI-created automations

## 56. Очень полезный сценарий

Пользователь:

> «Каждый будний день в 8 утра проверяй, не вышли ли новые данные ЦБ. Если вышли — обновляй расчёты и сообщай только при ошибке или сильном изменении».

AI переводит это в draft:

```yaml
trigger:
  type: cron
  expression: "0 8 * * 1-5"
  timezone: "Europe/Helsinki"

target:
  scenario_id: scenario.cbr.daily_refresh

conditions:
  - source_changed

policy:
  overlap: coalesce
  misfire: catch_up_latest
  notify_on:
    - failure
    - anomaly
```

После user approval draft становится AutomationSpec. Дальнейшие ежедневные запуски AI не требуют.

## 57. Когда модель действительно нужна при scheduled run

Иногда automation может содержать AI stage:

```text
refresh official data
 ↓
deterministic validation
 ↓
calculate change metrics
 ↓
IF abs(change) > threshold
    ↓
AI summarize anomaly
    ↓
send notification
```

Так модель включается только там, где нужен смысловой текст.

## 58. Агентная automation

Продвинутый вариант:

```text
trigger
 ↓
start AgentRun with objective
 ↓
agent investigates using approved tools
 ↓
produces report/artifacts
```

Такие automations стоит делать только после появления budgets, approvals, durable agent state, tool policy, evaluation и audit.

---

# XX. Source watchers и data-quality automation

## 59. Один из самых сильных будущих механизмов

Core research уже естественно ведёт к контрактам:

```text
SourceDescriptor
SourceSnapshot
SourceFetchResult
SourceValidationResult
```

После этого `source.check` становится обычной operation:

```text
check source
  ↓
compare snapshot identity/hash/schema
  ↓
SourceChangeResult
```

Scheduler остаётся внешним consumer.

## 60. Цепочка source-driven automation

```text
check official source
 ↓
changed?
 ├─ no → finish
 └─ yes
      ↓
   fetch snapshot
      ↓
   validate
      ↓
   materialize canonical data
      ↓
   run data checks
      ↓
   build dependent artifacts
      ↓
   notify
```

Это для Strategy Box полезнее, чем слепой «скачивать всё каждый день».

## 61. Validation должна влиять на workflow

```text
new source fetched
 ↓
schema check
 ↓
row-count check
 ↓
period check
 ↓
domain checks
 ↓
PASS
  → publish

WARN
  → publish with warning / request review

FAIL
  → stop downstream chain
```

Agent может объяснить failure, но gate остаётся deterministic.

---

# XXI. Сравнение с существующими orchestration patterns

## 62. APScheduler

Хорошо подходит как lightweight backend для single-node AppDock host, cron/interval/date triggers, persisted schedules и локального Python runtime.

Плюсы:

- небольшой dependency surface;
- соответствует текущему масштабу;
- легко завернуть в собственный `SchedulerBackend`;
- чёткое разделение task/schedule/job/data store/executor в современной архитектуре.

Минус: сам по себе не решает полноценную distributed durable workflow problem.

**Вывод:** хороший ранний adapter, если AppDock scheduler ещё не реализован.

## 63. Celery

Подходит, если появятся много workers, broker, distributed execution, очереди, routing и масштабирование.

Но сейчас может принести лишнюю инфраструктуру и отдельную модель workflow.

**Вывод:** не делать базовой зависимостью Strategy Box. Рассматривать только при реальной потребности в distributed worker queue.

## 64. Temporal

Temporal показывает сильную модель durable execution:

- workflow state survives crashes;
- retries;
- long-running execution;
- signals/human-in-the-loop;
- durable agent loops.

Это особенно интересно для будущего AppDock host/server.

**Вывод:** использовать как архитектурный ориентир и потенциальный backend, если AppDock действительно перерастёт в distributed durable runtime. Не тянуть Temporal внутрь `stratbox`.

## 65. Dagster

Полезные идеи:

- asset-centric model;
- dependency-aware automation;
- materialization;
- asset checks;
- cron + dependency conditions.

Для Strategy Box особенно ценен принцип: downstream запускается, когда upstream data обновлены и blocking checks прошли.

**Вывод:** заимствовать паттерны, а не превращать Strategy Box в оболочку Dagster.

## 66. Prefect

Интересны event triggers, compound/sequence triggers и event-driven actions. Это хороший reference design для будущего `TriggerSpec`.

**Вывод:** использовать как ориентир для trigger algebra, а dependency принимать только если появится отдельная эксплуатационная причина.

---

# XXII. Предлагаемые platform-neutral contracts

## 67. `OperationDescriptor`

```python
@dataclass(frozen=True)
class OperationDescriptor:
    id: str
    title: str
    description: str
    request_schema: dict
    result_schema: dict

    read_only: bool
    destructive: bool
    idempotent: bool
    open_world: bool

    requires_network: bool
    requires_storage: bool

    risk_level: str
    approval_policy: str
    ai_visibility: str

    supports_async: bool
    supports_cancel: bool
    expected_artifact_kinds: tuple[str, ...]
```

## 68. `ScenarioDescriptor`

```python
@dataclass(frozen=True)
class ScenarioDescriptor:
    id: str
    title: str
    description: str
    input_schema: dict
    steps: tuple[ScenarioStepSpec, ...]

    supports_background: bool
    supports_cancel: bool
    risk_level: str
    ai_visibility: str
```

## 69. `AutomationSpec`

```python
@dataclass(frozen=True)
class AutomationSpec:
    id: str
    title: str
    enabled: bool

    trigger: TriggerSpec
    target: TargetSpec
    params: dict

    misfire_policy: str
    overlap_policy: str
    retry_policy: RetryPolicy
    notification_policy: NotificationPolicy
    approval_policy: ApprovalPolicy

    timezone: str
```

## 70. `Job`

```python
@dataclass
class Job:
    id: str
    target_id: str
    target_kind: str
    params: dict

    origin: str
    principal_id: str | None

    idempotency_key: str | None
    backend: str | None
    priority: int

    status: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
```

## 71. `ExecutionBackend`

```python
class ExecutionBackend(Protocol):
    def submit(self, job: Job) -> JobHandle: ...
    def get(self, job_id: str) -> JobState: ...
    def cancel(self, job_id: str) -> CancelResult: ...
```

Implementations:

```text
LocalExecutionBackend
AppDockHostExecutionBackend
RemoteNodeExecutionBackend
```

---

# XXIII. Event model

## 72. Один event vocabulary

```text
automation.triggered
job.created
job.started
job.retrying
job.completed
job.failed
job.cancelled

case.started
case.step_started
case.step_completed
case.step_failed
case.completed
case.failed

artifact.created
artifact.validated
artifact.superseded

approval.requested
approval.granted
approval.rejected

agent.started
agent.tool_requested
agent.tool_completed
agent.input_required
agent.completed
agent.failed

source.checked
source.changed
source.validation_failed
```

Windows, Android, scheduler, AI и notifications должны слушать один event stream.

---

# XXIV. Conversational UX

## 73. Чат не должен быть отдельным миром

Текущий scenario-chat уже является хорошей поверхностью. Можно добавить два типа сообщений:

```text
ConversationMessage
CaseMessage
```

User message:

> «Обнови ЦБ».

AI answer:

> «Запускаю “Обновление данных Банка России”».

Следом тот же chat показывает Case card. Conversation и execution остаются связаны визуально.

## 74. Команды естественным языком

Примеры:

```text
"Обнови всё по ЦБ"
"Построй историю эскроу до сентября"
"Покажи, что упало ночью"
"Повтори последний успешный запуск"
"Сравни этот Excel с предыдущим"
"Каждый понедельник пересобирай отчёт"
```

Каждая команда должна приводить к структурированному intent/tool call, а не к скрытой строке shell/Python.

---

# XXV. Dynamic agent workflows

## 75. Agent может строить временный plan

Важно различать:

```text
saved Scenario
и
ephemeral Agent Plan
```

Saved Scenario устойчив, тестируется, доступен пользователю и может быть scheduled.

Ephemeral Plan создаётся под конкретную цель, состоит из разрешённых capabilities, сохраняется в AgentRun и не становится новым Scenario автоматически.

## 76. Превращение удачного agent plan в scenario

Полезная функция:

> «Сохранить этот процесс как сценарий».

После AgentRun система может построить draft ScenarioSpec из tool-call trace. Но перед сохранением нужен review: случайный execution path не всегда является хорошим reusable workflow.

---

# XXVI. Agent evaluation

## 77. Что измерять

Для conversational router:

```text
scenario selection accuracy
parameter extraction accuracy
unnecessary confirmation rate
invalid tool-call rate
```

Для agent:

```text
task completion
tool-call correctness
policy violation rate
unnecessary tool calls
artifact grounding
numerical correctness
approval correctness
loop rate
cost
latency
```

## 78. Regression set

Нужно собрать набор реальных запросов:

```text
"обнови ЦБ"
"проверь свежесть ОКВЭД"
"собери форму 802"
"найди последний успешный файл"
"удали старые FRG файлы"  ← должен запросить approval
```

И прогонять их при обновлении prompt/model/tool catalog.

---

# XXVII. Multi-agent и skills

## 79. Не начинать с multi-agent

Большинство задач Strategy Box решаются одним agent orchestrator + tools. Multi-agent нужен позже, если появятся явно разные роли: Data Agent, Analysis Agent, Report Agent, Reviewer Agent.

Multi-agent повышает стоимость, latency, сложность состояния, trace complexity и риск расхождений. Первый production agent должен быть один.

## 80. Где полезны AI skills

Современный MCP ecosystem поддерживает reusable skills/workflow instructions. Strategy Box потенциально может публиковать instructions вроде:

```text
"как анализировать обновление формы 802"
"как проверять SORS result"
"как готовить monthly banking refresh"
```

Но Skill не должен содержать секрет, business formula, permission rule или критический safety gate. Это instruction layer; source of truth остаётся в code/contracts.

---

# XXVIII. Что нельзя делать

## 81. Не давать агенту shell как основной tool

Shell может быть developer capability, но для обычного Strategy Box agent он слишком широк. Нужны domain tools.

## 82. Не разрешать произвольный Python

Иначе operation registry теряет смысл, а auditability исчезает.

## 83. Не создавать второй набор AI-only сценариев

GUI, automation и AI должны использовать одинаковые capabilities.

## 84. Не хранить расписание в prompt

Schedule — структурированный объект.

## 85. Не хранить критическое состояние только в conversation

Conversation — UX context. Jobs, cases, approvals, artifacts и automations должны иметь независимое durable storage.

## 86. Не делать модель ответственным источником истины для status

Status знает executor/job store. AI только объясняет его.

---

# XXIX. Конкретные пользовательские сценарии

## 87. Простой чат

Пользователь: «Обнови данные ЦБ».

```text
AI router
→ scenario.cbr.full_update
→ params validation
→ Job
→ Case
→ run
→ artifacts
→ AI summarizes result
```

## 88. Schedule

Пользователь: «Каждый будний день в 7:45 запускай обновление ЦБ».

```text
AI parses intent
→ AutomationDraft
→ user confirms
→ save AutomationSpec
→ scheduler owns recurrence
```

## 89. Source watcher

```text
07:00 source.check
→ unchanged
→ finish silently
```

На следующий день:

```text
source.check
→ changed
→ fetch
→ validate
→ rebuild
→ artifact created
→ mobile notification
```

## 90. Agent investigation

Пользователь: «Проверь, почему значения отраслевого кредитования резко изменились».

Agent:

```text
1. locate latest canonical artifact
2. compare with previous
3. identify affected region/classes
4. inspect source snapshot and validation
5. run deterministic diagnostics
6. produce explanation
```

## 91. Destructive flow

Пользователь: «Очисти старые поставки».

```text
frg.cleanup.plan
→ returns candidate files
→ approval request
→ user reviews
→ frg.cleanup.execute(plan_id)
→ verify result
```

---

# XXX. Целевая архитектура по репозиториям

## 92. `stratbox`

```text
stratbox
│
├─ domain operations
├─ source contracts
├─ canonical data
├─ validation
├─ calculations
├─ provenance
└─ artifact generation
```

Никакого scheduler/LLM/MCP dependency в core.

## 93. Shared application semantics

Логически:

```text
Strategy Box application semantics
│
├─ operation catalog
├─ scenario catalog
├─ scenario orchestration
├─ jobs
├─ cases
├─ events
├─ artifacts
├─ automations
├─ approvals
├─ assignments
└─ AI-facing capability descriptors
```

Пока это может развиваться внутри platform-neutral части `stratbox-windows`, а затем быть переиспользовано Android. Ключевое требование — runtime/application orchestration не должна зависеть от Qt.

## 94. AppDock

```text
AppDock
│
├─ managed environment
├─ host/runtime
├─ scheduler backend
├─ job execution broker
├─ remote nodes
├─ identity
├─ permissions
├─ secrets boundary
├─ AI provider bridge
├─ MCP gateway
└─ notifications
```

## 95. Windows

```text
stratbox-windows
│
├─ presentation/common
├─ presentation/qt_desktop
├─ local UX adapters
└─ AppDock client adapter
```

## 96. Android

```text
stratbox-android
│
├─ same application semantics
├─ same presentation/common semantics
├─ mobile UI
├─ notifications
├─ approvals
└─ remote/host control
```

---

# XXXI. Что делать с MCP физически

## 97. Вариант A — Strategy Box MCP server

Сам surface поднимает MCP endpoint.

Плюсы: просто понять, direct integration.

Минусы: protocol coupling, lifecycle/auth в каждом product surface, Windows/Android duplication, сложнее remote discovery.

## 98. Вариант B — AppDock MCP gateway

AppDock читает capability catalog подключённого world и публикует его через MCP.

Плюсы:

- единая auth/policy;
- единый remote transport;
- единый AI provider bridge;
- Strategy Box остаётся protocol-neutral;
- одинаково для Windows/Android/host;
- механизм подходит и другим AppDock products.

**Это предпочтительный вариант.**

## 99. Вариант C — гибрид

Strategy Box предоставляет local in-process capability provider, а AppDock gateway оборачивает его в MCP.

```text
StrategyBoxCapabilityProvider
        ↓
AppDock MCP Adapter
        ↓
MCP tools/resources/tasks
```

Это наиболее чистый технический вариант.

---

# XXXII. Roadmap

## 100. Этап 1 — нормализовать core operations

До AI:

1. завершить common Request/Result direction;
2. stable operation IDs;
3. `OperationDescriptor`;
4. structured diagnostics;
5. provenance;
6. side-effect metadata;
7. risk/destructive metadata;
8. artifact outputs.

Это фундамент всего остального.

## 101. Этап 2 — platform-neutral Job/Case engine

1. отделить execution coordinator от Qt;
2. `JobManager`;
3. `ExecutionBackend`;
4. cancellation;
5. retries;
6. concurrency policy;
7. durable state;
8. event vocabulary.

## 102. Этап 3 — scheduler

1. `TriggerSpec`;
2. `AutomationSpec`;
3. persistent scheduler backend;
4. misfire;
5. overlap;
6. idempotency;
7. source watcher;
8. notification policy.

На первой стадии backend может быть lightweight local scheduler, сохраняя AppDock-compatible interface.

## 103. Этап 4 — artifact intelligence

1. stable artifact IDs;
2. hashes;
3. lineage;
4. previews;
5. table query APIs;
6. sensitivity labels;
7. agent-readable resource model.

## 104. Этап 5 — conversational router

1. AI provider abstraction через AppDock;
2. scenario search;
3. typed intent;
4. schema validation;
5. run preview;
6. eval dataset;
7. low-risk automatic execution.

Это первый полезный AI release.

## 105. Этап 6 — MCP gateway

1. capability → MCP tools;
2. catalogs/artifacts → MCP resources;
3. saved templates → MCP prompts;
4. Job/Case → Tasks mapping;
5. approval/input-required bridge;
6. OAuth/scopes/policy;
7. tracing.

## 106. Этап 7 — bounded agent

1. AgentRun model;
2. planner loop;
3. tool policy;
4. budgets;
5. approvals;
6. artifact queries;
7. structured decision records;
8. failure recovery;
9. evals.

## 107. Этап 8 — host/remote/mobile

1. scheduler moves to long-running AppDock host;
2. remote execution backend;
3. mobile notifications;
4. mobile approvals;
5. remote artifact previews;
6. agent continuation across devices.

---

# XXXIII. Приоритеты

## P0

- operation contracts;
- Job/Case separation;
- execution backend interface;
- durable state;
- cancellation;
- risk metadata;
- artifact IDs/lineage.

## P1

- scheduler;
- source-change triggers;
- notifications;
- conversational router;
- AppDock MCP adapter.

## P2

- full agent loop;
- event/condition automation;
- remote host;
- mobile approval;
- artifact query engine.

## P3

- multi-agent;
- autonomous recurring agents;
- complex conditional workflow DSL.

---

# XXXIV. Наиболее важные проектные правила

## 108. Один capability — много consumers

```text
GUI
scheduler
AI
remote API
tests
```

все используют один operation/scenario contract.

## 109. AI не владеет вычислениями

Он выбирает и интерпретирует. Числовая и банковская логика остаётся детерминированной.

## 110. Scheduler не владеет бизнес-логикой

Он создаёт Job.

## 111. MCP не владеет внутренней моделью

Это adapter.

## 112. AppDock не владеет банковской логикой

Он владеет execution/policy/runtime.

## 113. Windows не владеет универсальной orchestration semantics

Она должна быть platform-neutral для будущего Android.

---

# XXXV. Финальный вывод

Strategy Box уже подошёл к точке, где ИИ можно добавить **без архитектурного переворота**.

Основная работа теперь состоит не в том, чтобы встроить чат-бота, а в том, чтобы довести до строгого состояния промежуточный слой:

```text
canonical operations
→ scenarios
→ jobs/cases
→ artifacts/events
→ automations
→ capability catalog
```

После этого:

```text
GUI = один consumer
scheduler = второй consumer
AI = третий consumer
MCP = внешний adapter
remote host = execution backend
Android = ещё одна surface
```

Самый правильный первый AI-релиз — **conversational router**:

> пользователь пишет обычным языком → система выбирает готовый сценарий → валидирует параметры → выполняет обычным runner.

Самый правильный второй AI-релиз — **bounded agent**:

> модель сама выбирает последовательность разрешённых операций, читает структурированные результаты и артефакты, но все действия проходят через capability policy, а опасные шаги — через approval.

Самый правильный путь автоматизации — **background jobs как обычные scenarios**, запускаемые по сохранённым `AutomationSpec`, а не отдельная параллельная подсистема.

Самый правильный способ интеграции с MCP — **AppDock gateway, автоматически публикующий Strategy Box capability catalog**, а не внедрение MCP SDK в предметный core.

В таком варианте Strategy Box постепенно превращается из desktop аналитического приложения в **управляемую аналитическую среду**, где один и тот же предметный механизм может быть вызван человеком, расписанием, событием, удалённым узлом или ИИ — с одинаковыми результатами, provenance, безопасностью и audit trail.

---

# Приложение A. Рекомендуемая единая схема

```text
                        User / Analyst
                             │
                 Windows / Android / Chat
                             │
                 Strategy Box Application
                 ────────────────────────
                 Operation Catalog
                 Scenario Catalog
                 Automation Catalog
                 Job Manager
                 Case/Event/Artifact Model
                 Approval Policy
                 Capability Catalog
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
          Deterministic Runner       AppDock Runtime
                 │                   ───────────────
                 │                   Scheduler
                 │                   AI Gateway
                 │                   MCP Adapter
                 │                   Permissions
                 │                   Remote Nodes
                 │                   Notifications
                 │                       │
                 └───────────┬───────────┘
                             ▼
                        stratbox core
                             │
              source → canonical → validation
                 → calculations → artifacts
```

---

# Приложение B. Возможная MCP-проекция

```text
TOOLS
-----
strategybox.scenario.search
strategybox.scenario.run
strategybox.operation.run
strategybox.job.get
strategybox.job.cancel
strategybox.case.get
strategybox.artifact.query
strategybox.automation.create_draft
strategybox.automation.activate

RESOURCES
---------
strategybox://catalog/scenarios
strategybox://catalog/operations
strategybox://runtime/health
strategybox://case/{id}
strategybox://artifact/{id}/metadata
strategybox://artifact/{id}/preview

PROMPTS
-------
update_cbr
explain_artifact
compare_periods
investigate_anomaly

TASKS
-----
long-running operation/scenario execution
mapped to Strategy Box Job/Case
```

---

# Приложение C. Исследованные проектные материалы

1. `stratbox_base_study_current_state_2026-10-06.md`
2. `stratbox-windows_current_state_full_research_2026-10-06.md`
3. `stratbox_plugin_current_state_research_2026-10-06.md` — использован только как внутренний контекст environment capabilities; детали закрытого слоя не предназначены для переноса в публичные репозитории.
4. `AppDock - Базовое описание.docx`

---

# Приложение D. Внешние источники

Проверка выполнена по актуальным материалам на 2026-10-06.

## Model Context Protocol

- MCP TypeScript SDK v2 overview — current stable implementation of MCP 2026-07-28:  
  https://ts.sdk.modelcontextprotocol.io/v2/
- MCP TypeScript server SDK — tools/resources/prompts and tool annotations:  
  https://ts.sdk.modelcontextprotocol.io/v2/api/%40modelcontextprotocol/server/
- MCP Tasks Extension:  
  https://tasks.extensions.modelcontextprotocol.io/
- MCP Tasks specification:  
  https://tasks.extensions.modelcontextprotocol.io/specification/2026-07-28/tasks
- MCP Python SDK — resources:  
  https://py.sdk.modelcontextprotocol.io/servers/resources/
- MCP Python SDK — prompts:  
  https://py.sdk.modelcontextprotocol.io/servers/prompts/
- MCP 2026 migration / multi-round-trip model:  
  https://ts.sdk.modelcontextprotocol.io/v2/migration/support-2026-07-28
- MCP Skills extension:  
  https://skills.extensions.modelcontextprotocol.io/specification/stable/skills

## Agent architecture / approvals

- OpenAI Agents SDK overview:  
  https://developers.openai.com/api/docs/guides/agents/sdk
- OpenAI Agents SDK — guardrails and human review:  
  https://developers.openai.com/api/docs/guides/agents/guardrails-approvals
- OpenAI Agents SDK — running agents:  
  https://developers.openai.com/api/docs/guides/agents/running-agents
- OpenAI Agents SDK — MCP integration and observability:  
  https://developers.openai.com/api/docs/guides/agents/integrations-observability

Эти материалы использованы как подтверждение общих современных паттернов. Предлагаемая архитектура Strategy Box остаётся provider-neutral.

## Scheduling / durable execution / data orchestration

- APScheduler user guide:  
  https://apscheduler.readthedocs.io/en/master/userguide.html
- Celery periodic tasks:  
  https://docs.celeryq.dev/en/main/userguide/periodic-tasks.html
- Temporal — durable execution:  
  https://docs.temporal.io/temporal
- Temporal AI Cookbook:  
  https://docs.temporal.io/ai/cookbook
- Dagster declarative automation:  
  https://dagster.io/docs/guides/automate/declarative-automation
- Dagster schedules:  
  https://dagster.io/docs/guides/automate/schedules
- Prefect automation schemas/events reference:  
  https://reference.prefect.io/prefect/events/schemas/automations/

---

# Приложение E. Следующие исследования

## E1. Canonical Operations & Capability Contract

Подробно определить final `OperationDescriptor`, Request/Result envelope, side effects, risk, idempotency, cancellation, progress, artifact input/output, AI visibility, MCP projection, registry discovery и versioning.

Это должно предшествовать реализации AI.

## E2. Automation / Job / Case Runtime

Подробно определить `AutomationSpec`, trigger algebra, scheduler backend, JobStore, event store, SQLite schema, locking/leases, retries, misfires, concurrency, cancellation, approvals, notification events и AppDock host boundary.

После этих двух исследований implementation path станет почти механическим.
