# Strategy Box — консолидирующее исследование 04: Work → Execution Architecture

**Дата исследования:** 2026-10-09  
**Программа:** третья ветка `03-consolidation-research`, тема **04 — Work → Execution Architecture**  
**Статус:** **Research Synthesis / Consolidation Result**. Документ не является Product Decision, утверждённым Target WHAT/HOW, реализованным API или заданием на изменение кода.  
**Первичный корпус:** `02-base-study`; контроль согласованности — темы 00, 01, 02 и 03 третьей ветки.  
**Исторический слой:** `01-old-notes` учитывается исключительно как источник прежних замыслов и смены решений.  
**Проверка implementation:** `stratbox` `main` — commit [`6c371407`](https://github.com/ForestTiger-GH/stratbox/commit/6c3714078791eabd64927b143aa1e5f4a76f9b88), 2026-10-09; `stratbox-windows` `main` — commit [`959e9c4c`](https://github.com/ForestTiger-GH/stratbox-windows/commit/959e9c4ce1441124af5111c1e025041714e04d3b), 2026-08-05. Текущий исполняемый код Windows выборочно проверен напрямую; выводы о нём отделены от перспективной архитектуры. Сопоставление core `e9688535` → `6c371407` обнаружило изменения исследовательских и управляющих файлов, **без изменений исполняемых `src/`, `tests/` и доменных операций**.  
**Границы:** в публичной архитектуре обсуждаются только общие нейтральные extension contracts; внутреннее устройство закрытых расширений не описывается. Методологические идеи применяются на уровне требований к Work, доказательности и воспроизводимости без метаописания чужих методологических проектов.  
**Размещение:** самостоятельный файл для передачи в чат; публикация или изменение репозиториев не выполнялись.

---

## 0. Executive synthesis

**[CONSOLIDATED]** Strategy Box нужен **один сквозной Work → Execution spine**, который обслуживает ручной запуск, обычную последовательность, сложную композицию, плановую автоматизацию, фоновое выполнение, межпользовательские поручения, API и разрешённого ИИ-инициатора. Способы подачи запроса и исполнения — *ортогональные измерения*, а не разные workflow engines.

Центральная цепочка после согласования с канонической семантикой темы 02:

```text
Human / Automation / AI / API / Assignment
                      │
             Intent / request
                      ↓
             WorkCandidate
                      ↓ admission, authority, scope
                    Work
                      ↓ select semantic capability
          Scenario / Scheme / Operation
                      ↓
                Run request
                      ↓
       effective parameters + Binding
                      ↓
         resolved ExecutionPlan
                      ↓ transactional admission
                     Run
                      ↓
          JobManager / queue / leases
                      ↓
               Job(s) / DAG
                      ↓
              OperationRun(s)
                      ↓
              Attempt(s)
                      ↓
  typed progress / events / effect receipts
                      ↓
   execution outcome + domain result + artifacts
                      ↓
     assessment / acceptance / residual work
                      ↓
                  Work closure
```

Схема — **семантический маршрут**, а не требование создавать отдельную таблицу и сетевой вызов для каждого прямоугольника. `Run` может включать один `Job` и один `OperationRun`; некоторые работы закрываются без вычислительного запуска; внутренний вызов `parse_xlsx()` через библиотечный `stratbox` не обязан превращаться в `Work`.

**Восемь ключевых консолидированных результатов:**

1. **Work ≠ Run ≠ Job ≠ Attempt.** Work — долговечная цель с обязательствами. Run — конкретный эпизод реализации. Job — планируемая исполнительная единица. OperationRun — факт исполнения предметной операции. Attempt — конкретная техническая попытка. Эти роли семантически нужны, хотя допускают компактное физическое представление.
2. **Сценарий — определение повторяемого пользовательского способа работы.** Machine Scheme — типизированная переиспользуемая композиция. ExecutionPlan — разрешённый на конкретных данных и полномочиях граф. `Cascade` полезен как продуктовый профиль композиции; отдельный движок каскадов не обоснован.
3. **`Case` текущего Windows — действующая GUI-модель, но не готовый канонический Work/Job authority.** Целевая карточка «кейса» предпочтительно становится проекцией Work/Run. Независимую durable Case сущность следует вводить лишь при доказанном дополнительном lifecycle.
4. **Планирование и выполнение разделяются.** Planner разрешает параметры, связывает semantic capability с исполнителем, строит зависимости, выявляет допустимый reuse, эффекты, approvals и resource claims. JobManager отвечает за очередь, выдачу работы, лимиты, cancellation, контроль попыток и восстановление.
5. **Единый runtime должен переживать клиент.** Qt `QThread`, веб-запрос, экран Android и чат не являются владельцами durable execution. AppDock управляет жизнью узла/среды/процессов; Strategy Box application runtime — предметным Work/Job состоянием.
6. **Success нескольких уровней различается.** Успех HTTP, OperationRun, Job, Run, создание XLSX, корректность аналитического результата и принятие Work — разные факты. Возможны успешный Run при `Work.awaiting_review`, частичный результат с ценными артефактами, отказ без запуска и `OUTCOME_UNKNOWN` после возможного внешнего эффекта.
7. **Отмена — запрос на безопасное прекращение дальнейших действий, не обещание rollback.** Retry допустим по policy и по эффектам. При неизвестном внешнем результате запрещён слепой автоматический повтор: требуется reconciliation.
8. **Durable events + state transitions + effect receipts образуют execution truth.** Текстовый лог, файл результата, UI-проекция и состояние AppDock не заменяют этот источник истины; каждый нужен для своей цели.

**[CURRENT]** Текущий `stratbox-windows` умеет последовательные сценарии, user-facing cases, operation handlers, Qt-асинхронность, события, файлы логов, локальную JSON-историю и ссылки на выходные пути. Но одного узлового JobManager, отдельного ExecutionPlan, устойчивого scheduler/worker, настоящей cancellation, node-wide queue, durable leases/recovery и независимого клиентского runtime **пока нет**. Это **главный фактический разрыв**, а не доказательство неработоспособности существующего desktop-прототипа.

---

## 1. Постановка и метод исследования

### 1.1. Точный scope темы 04

Программа требует пройти полный путь `User / Automation / AI → Intent → Work → Capability selection → Scenario / Scheme → ExecutionPlan → Job → OperationRun → Attempt → Progress / Events → Terminal Outcome → Artifacts / Result → Closure`, объединив работы по командам/сценариям/каскадам, execution control, фоновому исполнению, ИИ, multi-user и observability. Основной результат — **общая execution state machine и границы ownership**, позволяющие использовать разные frontends и execution backends без размножения engines.

**Соседние темы:** data identity, доказательность, артефакты и provenance закреплены в теме 03; persistence/сотрудничество — в теме 05; каталог расширений и схема capabilities — в теме 06; поверхности и UX — в теме 07; надёжность и security — в теме 08. Тема 04 должна задать необходимые контракты и системные инварианты, но не предрешать топологию БД, toolkit UI или создание нового репозитория.

### 1.2. Уровни утверждений

| Маркер | Интерпретация |
|---|---|
| **CURRENT** | проверенное текущее состояние кода/документации на указанном commit либо точно датированный факт предыдущей проверки |
| **CONSOLIDATED** | устойчивое смысловое заключение из нескольких источников, без статуса Product Decision |
| **TARGET-HYPOTHESIS** | предлагаемая будущая реализация, структура или policy, требующая утверждения/пилота |
| **CONFLICT** | одновременно предложены действительно несовместимые варианты |
| **SUPERSEDED** | прежняя гипотеза вытеснена реализацией или более строгой семантической моделью |
| **UNKNOWN** | корпус и актуальный код не дают достаточных оснований для выбора |

Приоритет источников: **текущий implementation owner для фактов → контролирующие консолидированные темы 00–03 для согласованной семантики → первичные тематические работы `02-base-study` для деталей и вариантов → исторические материалы для генезиса гипотез**. Новая дата документа сама по себе не доказывает правильность решений.

### 1.3. Как выполнена сверка

Изучены программа, README ветки, Corpus Map, System Model, Canonical Semantic Model, Data → Knowledge, исследования по командам/сценариям, управлению исполнением, фоновым задачам, automation/AI, наблюдаемости, единому узлу, web/host, машинным схемам, core, Windows, а также часть соседних материалов. Из `stratbox-windows` повторно проверены реальные `ScenarioSpec`, registry, `run_scenario()`, operation runner, `ScenarioCoordinator`, runtime bootstrap, background store и history persistence. Источники представлены в [§24](#24-source-ledger-и-provenance), с прямыми ссылками на документы и код.

Тесты в текущем исследовании **не запускались**, не создавалась работающая реализация планировщика. Поэтому проектные YAML/SQL и test cases ниже — **candidate contracts / acceptance probes**, а не заявления об успешно протестированном поведении.

---

## 2. CURRENT: как работает система сейчас

### 2.1. `stratbox`: предметное ядро, но пока не общий execution service

**CURRENT.** `stratbox` уже предоставляет domain pipelines: загрузку raw-публикаций ЦБ, обработку форм, отраслевых данных и эскроу, файловые операции FRG, сложную восстановительную подсистему SORS; у ряда доменов есть типизированные Request/Result, validation, diagnostics, provenance и tests. Предметные функции могут использоваться headless и вне пользовательского приложения. Отдельного **канонического реестра всех предметных OperationDefinition**, общесистемного JobManager или Work lifecycle в ядре нет. Реальные domain failures/result shapes различаются.

**CONSOLIDATED.** Это здоровая граница: `stratbox` владеет смыслом и реализацией банковских/макроэкономических операций, safety points и domain result; общий orchestration не должен переносить внутрь `stratbox` чаты, очередь, пользователей и историю поручений.

### 2.2. `stratbox-windows`: действительный путь `Scenario → Case → Steps → Operation`

**CURRENT.** Прямой просмотр [`application/scenarios/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/models.py), [`registry.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/registry.py), [`runner.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) подтверждает:

- `ScenarioKind` включает `atomic`, `composite`, `background`, `assignment` — будущая классификация не должна ошибочно выдаваться за уже реализованные разные engines;
- каждая включённая `OperationSpec` автоматически оборачивается в `scenario.atomic.<operation_id>`;
- существует один явно составной `scenario.cbr.full_update`, последовательно вызывающий загрузку файлов ЦБ и экспорт истории эскроу; `params_map` раскладывает параметры по шагам;
- `ScenarioStepSpec` содержит `operation_id`, `order`, `required`, `params_override`, `params_map`; настоящий dependency DAG, resource planning, dedup и snapshot разрешённых bindings здесь отсутствуют;
- `run_scenario()` переводит `ScenarioRunCase` в running, идёт по шагам, вызывает `run_operation`, собирает outputs и создаёт `LogRecord`, `ArtifactRecord` и события; применяется `fail_fast` либо продолжение при ошибках;
- `ScenarioRunCase` хранит user-facing статус, автора, сроки, параметры, steps, output paths и unread; он совмещает свойства **Run + карточки + части Work**;
- `run_operation()` динамически загружает handler по `module:function`, создаёт локальный operation log и переводит исключения в `OperationResult`, но не ведёт самостоятельный durable attempt journal.

Фактически в каталоге всего три операции: `cbr_file_collector.collect`, `escrow.history.export`, `system.diagnostics`. Это две предметные операции и диагностическая; отдельной сложной операционной композиции core в Windows ещё нет.

### 2.3. Qt действительно управляет исполнением

**CURRENT.** В [`presentation/qt_desktop/scenario_coordinator.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) один `_thread`, `_worker` и `_active_case`; `submit()` отказывает второму сценарию при `is_busy`. Qt-сигналы обновляют stores. В [`runtime/bootstrap.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py) application composition непосредственно импортирует Qt `ScenarioCoordinator`.

**Следствия:** лимит в один запуск — **процессно-локальный**, а не node-wide; runtime composition зависит от GUI toolkit; надёжное продолжение после закрытия GUI, reboot, remote worker restart и параллельная очередь не вытекают из текущей реализации.

### 2.4. Background, collaboration и история: каркасы ≠ engines

**CURRENT.** [`BackgroundProcessStore`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/store.py) содержит in-memory статусы и enable/disable, но ни scheduler, ни trigger evaluator, ни worker dispatcher в этом блоке нет. `PresenceService` и поручения существуют локально без общего collaboration backend. [`HistoryPersistenceService`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) сохраняет пять JSON-массивов (`cases/events/artifacts/logs/assignments`) независимыми `write_text` и при ошибке декодирования возвращает пустой список. Это **recent-state persistence**, а не транзакционная долговременная execution truth.

**Критический edge case current:** два клиента в одном узле могут поддерживать несовместимые in-memory картины статуса; нечитаемый `cases.json` может выглядеть как пустая история, не как диагностируемое повреждение. Текущий `unread` на case — один bool, тогда как многопользовательской модели нужны per-user cursors. Эти проблемы принадлежат главным образом теме 05, но влияют на корректность исполнения.

### 2.5. AppDock: управляющая платформа, а не предметный executor

**CURRENT / SCOPE-LIMITED.** Базовая модель AppDock описывает Node, Activation Context, health, managed environment, actions, host/remote capabilities, результаты и восстановление. Текущий Windows manifest ориентирован на локальный foreground; platform-level remote execution и долговременный Strategy Box application runtime нельзя выводить из того, что AppDock концептуально поддерживает узлы и хосты. Граница AppDock определена продуктово, а точный контракт service deployment и API для будущего host — **OPEN / external dependency**.

### 2.6. Свежесть implementation baseline

Сопоставление `stratbox` core-снимка от 2026-10-06 с его `main` от 2026-10-09 выявило новое исследовательское дерево, но **без изменений исполняемого ядра, доменных тестов и операций**. Windows HEAD остался прежним. Таким образом, выводы о текущем execution path из исследования 2026-10-06 всё ещё подтверждаются прямой выборочной проверкой кода, а не только повторением прежнего отчёта.

### 2.7. Нельзя принимать за CURRENT

В реализации нет оснований утверждать наличие отдельной Work authority, готовой Work/Run/Job FSM, Node-wide worker queue, cancellation token pipeline, distributed leases/fencing, exactly-once external effects, plan snapshot, сертифицированного automatic retry, checkpoint resume, полноценной совместной временной шкалы и удалённого Strategy Box host. Все эти механизмы далее помечаются как target proposals.

---

## 3. Каноническая онтология исполнения и жизненные циклы

### 3.1. Таблица однозначных определений

| Объект | Роль | Stable identity / срок жизни | Чего им не считать |
|---|---|---|---|
| `Intent` / `Commission` | выраженная цель и основание поручить действие | исходное событие, request ref | уже разрешённым execution |
| `WorkCandidate` | предложение work до admission | ephemeral или durable при review | активной Work без проверки |
| `Work` | долговечная смысловая цель с requirements и closure | `work_id`; может пережить много Runs | отдельной попыткой выполнения |
| `CapabilityDefinition` | что по смыслу поддерживается | capability ID + semantic version | полномочием выполнить |
| `OperationDefinition` | самостоятельный предметный вызываемый use case | ID + semantic contract version | произвольной Python-функцией |
| `ScenarioDefinition` | курируемая понятная пользователю повторяемая задача | scenario ID + version | конкретным запуском |
| `SchemeDefinition` | типизированная reusable композиция | scheme ID + version | уже разрешённым планом |
| `ExecutionBinding` | выбор provider/backend + контекст допустимости | binding snapshot/revision | самим определением capability |
| `ExecutionPlan` | разрешённый на входах/правилах граф | plan ID + digest | выполненным эффектом |
| `Run` | единый конкретный эпизод исполнения Work | `run_id`, immutable effective context | самим Work |
| `Job` | schedulable/claimable исполняемая единица Run | `job_id`, queue/resource lifecycle | общей пользовательской целью |
| `OperationInvocation` | параметры конкретного вызова операции | invocation ID, effect scope | уже состоявшимся run |
| `OperationRun` | факт выполнения invocation | operation_run ID, parent job | технической попыткой retry |
| `Attempt` | один try с executor, временем и observation | attempt ID | новым Work при retry |
| `ExecutionOutcome` | итог конкретного Run/Job/Attempt | terminal receipt | доказательством содержательной истинности |
| `AnalyticalResult` | предметный результат, квалификация, validation | result ID/ref, provenance | файлом в output каталоге |
| `Artifact` | логический опубликованный продукт | artifact ID/version | абсолютным OS path |
| `Acceptance` / `Closure` | оценка выполнения обещанного Work и закрытие обязательств | review/closure event | автоматическим следствием `SUCCEEDED` |
| `AutomationSpec` | долговременное правило новых активаций | automation ID/revision | активным Job |
| `Thread` | контекст взаимодействия и обсуждения | thread ID; many-to-many с Work | durable source of job state |
| `Case` | текущая Windows case-модель; потенциально UI projection | case ID CURRENT, target association refs | обязательным новым execution authority |

### 3.2. Почему Work должен жить дольше Run

Один Work: «Исследовать динамику средств клиентов банков по официальной отчётности за 2024–2026 годы, с проверкой сопоставимости и итоговой таблицей». `Run 1` загружает источники, `Run 2` строит преобразование по уточнённому периоду, `Run 3` повторно проверяет таблицу после новой публикации. Work остаётся той же по цели, если scope и acceptance criteria не изменены существенно. Она может быть `awaiting_input`, `awaiting_review`, `active`, `completed`, `closed` или `reopened`; Run может быть успешно завершён при Work `awaiting_review`.

**TARGET-HYPOTHESIS:** при расширении цели до самостоятельной задачи с иными потребителем и результатом создавать child/new Work с causal link, а не скрыто переписывать старую Work или маскировать смену цели техническим retry.

### 3.3. Job и OperationRun: принцип разбиения

**[CONSOLIDATED]** Job — единица, на которую JobManager может назначить worker/lease/resource claims. OperationRun — фиксированное исполнение семантически определённой Operation. Один Job может содержать один либо несколько OperationRuns (например, worker выполняет компактный последовательный fragment); один Run содержит несколько независимых Jobs, если требуется concurrency. Attempt относится к конкретному retryable logical operation или job attempt — **scope попытки обязан быть явным**.

**TARGET-HYPOTHESIS / v1 default:** один `Run` с одной короткой Operation вправе иметь `1 Job / 1 OperationRun / 1 Attempt`; не создавать пустые промежуточные записи без потребителя, но сохранять эти роли в contracts/IDs. Для составного графа разбивать Job на schedulable fragments с понятными ресурсными и effect boundaries, без «Job на каждый метод Python».

### 3.4. `Case`, `Cascade`, `Command`: три места, где легко создать дубликат

**[CONFLICT → RESOLVED AS RESEARCH DIRECTION]** Ранние исследования: `Command → Scenario → Cascade`, самостоятельный `CascadeSpec` и `Case` как запускаемая пользовательская единица. Поздняя тема 02 разделила semantic capability, workflow definition, Work, Run, Job, Attempt. Разрешение:

- **`Command`** используется как *control-plane request* (`SubmitWork`, `CancelRun`, `RetryOperation`) либо локальная техническая action внутри planner; отдельный публичный **Command Registry как обязательный слой** пока не доказан. Canonical user/machine capability — `OperationDefinition`.
- **`Cascade`** — полезное пользовательское имя крупной композиции; сначала проверять, покрывается ли `ScenarioDefinition + SchemeDefinition`. Самостоятельный `CascadeDefinition` вводить лишь при уникальном lifecycle каталога, динамическом membership и result aggregation, недоступных общей модели. `CascadeRun` как иной executor избыточен.
- **`Case`** текущего клиента содержательно нужен для карточки истории, но **target default**: проекция одного Run с refs к Work, Jobs, steps и артефактам. Дополнительная независимая Case persistence потребует обоснованной пользовательской семантики.

**Важно:** это разрешения уровня консолидации, а не принятые миграции кода. Автоматически удалять соответствующие current classes до создания новой модели нельзя.

### 3.5. Категории статусов не следует смешивать

| Ось | Пример значений | Авторитетный смысл |
|---|---|---|
| Work lifecycle | `candidate / active / awaiting_input / awaiting_review / completed / closed / reopened` | выполнены ли смысловые обязательства |
| Run lifecycle | `prepared / admitted / queued / running / finalizing / terminal` | эпизод выполнения |
| Job lifecycle | `queued / waiting_resource / waiting_approval / claimed / running / finalizing / terminal` | где исполнительная единица |
| Execution outcome | `succeeded / partial / failed / cancelled / outcome_unknown` | исход именно исполнения |
| Domain validity | `valid / qualified / invalid / unknown` | допустимость и корректность предметного результата |
| Acceptance | `pending / accepted / conditionally_accepted / rejected` | принял ли потребитель результат |
| Authority | `allowed / denied / approval_required / expired / unknown` | допустимость эффекта сейчас |
| Health/attention | `healthy / degraded / needs_action / unavailable` | операционная способность продолжать |

Таблица — рекомендуемая **раздельная семантика**, а не утверждённые строки будущего wire enum.

---

## 4. Work admission: от свободного запроса к обязательству

### 4.1. Четыре класса входа — одна проверка

| Вход | Первичный объект | Типичный риск | Нормализованное действие |
|---|---|---|---|
| человек / UI / чат | сообщение, выбор Scenario | неопределённая цель, размытые параметры | извлечь кандидат, проверить scope и подтвердить достаточность |
| automation / watcher | `AutomationSpec + TriggerOccurrence` | пропуски, дубликаты, старые права | разрешить occurrence, проверить policy и idempotency |
| AI / machine consumer | структурированный proposal/intention | выдуманные ID, prompt injection, превышение прав | resolve capability from registry + authorization + bounded plan |
| assignment / API / peer | поручение или typed submit | другой principal, scope, конкурирующий запрос | аутентифицировать, проверить delegation, revision/ownership |

**[TARGET-HYPOTHESIS]** Admission имеет три выхода: `admitted(work_ref)`, `awaiting_input/approval(candidate_ref)` и `rejected(reason)`. Отказ до выдачи разрешения не должен симулировать «успешно отменённый job», если ни одной Job не было. Для rejected request полезен audit admission record без создания фиктивного Work.

### 4.2. Admission не должен создавать Work для каждого технического шага

Правило кандидата: durable Work оправдана самостоятельной обещанной целью, результатом с consumer, сроком/ответственностью, возможностью вернуться к процессу, review/approval или множеством Runs. Технический `read_bytes`, парсинг DBF как шаг и внутренний retry остаются под Work/Run. Простой интерактивный запуск user-facing Scenario обычно создаёт Work (при необходимости «короткую Work»), но можно материализовать её в минимальной оболочке.

**[UNKNOWN]** Точный product admission threshold для однострочного «открой файл» и transient preview требует UX/engineering пилота. Безусловное правило «любое действие = новый Work» создаст шум и будет вредно.

### 4.3. Контракт WorkCandidate → Work

Проверки до admission, по возможности без эффектов: существует ли семантическая цель; указан ли requested_by/principal; выполнена ли авторизация; поддерживается ли capability и её applicability; достаточно ли typed параметров; доступны ли необходимые версии данных; какова граница эффекта; требуется ли согласование; есть ли уже тот же idempotent запрос; как пользователь узнает критерий completion. Discovery =/ authorization, available =/ applicable, approved =/ executed.

**TARGET-HYPOTHESIS:** зафиксировать `work_id`, immutable origin refs, `purpose`, `scope`, `requirements_snapshot`, `principal/run_as`, `authority_refs`, acceptance policy, revisions, primary thread (optional). Текст чата остаётся источником намерения, а не единственным authoritative описанием работы.

### 4.4. Один trigger — новая Work или продолжение старой?

**Рекомендуемый default:** каждое самостоятельное плановое производство отчёта за период образует свой `Work + Run` (с общей `AutomationSpec`, `occurrence_id` и возможным parent/campaign ref); это обеспечивает отдельное выполнение обязательств и отдельную приёмку. **Альтернатива:** непрерывное наблюдение источника может быть одной длительно живущей Work с множеством Runs/подработ, если обещанием является *ongoing monitoring*, а не серия независимых ежемесячных продуктов. Выбор фиксируется в `AutomationSpec.admission_policy` и виден клиентам. Он **не** должен зависеть от текущей раскладки чатов.

### 4.5. Параметры: defaults и run snapshot — разные сущности

Дефолты могут исходить из schema, node policy, shared preset, user preset и draft. Перед исполнением вызывается **детерминированный ParameterResolver**, который сообщает эффективные значения и provenance overrides. При Start Run создаётся **immutable effective parameters snapshot**. Изменение настройки профиля позже влияет на будущие запуски, но не переписывает исторический Run. Параметры, несущие секреты, фиксируются в виде защищённых references/credential handles и version metadata, без самого секрета в истории и diagnostics.

---

## 5. Capability selection, Scheme и planning

### 5.1. Каталог: semantic contract прежде технического handler

**CONSOLIDATED.** `OperationDefinition` должна описывать intent, typed input/output, source/applicability envelope, preconditions, effects/frame conditions, errors, cancellation, resource constraints, retry/idempotency, relevant versions и provenance. Отдельный binding выбирает фактическую реализацию. `module:function`, Qt button, MCP tool и удалённая RPC-команда — реализации или проекции, не identities предметной способности.

Существующие операции core служат образцами для нормализации, но непосредственное превращение всех функций в публичные capabilities нежелательно. Прежде нужен inventory самостоятельных use cases и contract tests.

### 5.2. Scenario не равен Workflow Engine

Пользовательский Scenario — имя полезной повторяемой задачи с входной формой и ожидаемым исходом. Он может ссылаться на одну Operation либо Scheme. Machine Scheme задаёт typed graph, guards, ports, constraints и postconditions. Workflow исполнит общий application engine; другая UI-поверхность отобразит тот же Scenario иначе. Нет оснований создавать отдельные execution engines для UI-сценария, каскада, агента и автоматизации.

### 5.3. Планирование — отдельная проверяемая фаза

```text
1. Resolve work requirements / target scenario / scheme version
2. Validate semantic inputs, availability and applicability
3. Resolve typed parameters and provenance of defaults
4. Resolve source/registry/data snapshot constraints
5. Resolve capability implementation bindings and executor compatibility
6. Expand reusable scheme into typed invocation graph
7. Compute effect set + read/write resource claims
8. Validate dependencies, cycles, preconditions and branch guards
9. Determine permissible equivalence/reuse, caching and shared resources
10. Apply resource, quota, priority and concurrency policy
11. Bind permission/approval checkpoints and their validity scope
12. Produce inspectable plan, estimated cost class and plan digest
13. Admit Run/Jobs transactionally or place in explicit wait/refusal
```

**TARGET-HYPOTHESIS.** План должен поддерживать DAG, но стартовать можно с одного линейного сценария и одной двухветвевой композиции. Прежде разработки собственного DSL проверить, какие реальные cases требуют branching, optional steps и динамических input refs.

### 5.4. `ExecutionPlan` — конкретный snapshot, не живой дефолт

Кандидат полей: `plan_id`, `run_id`, definition refs + versions, effective params digest, source/registry snapshot refs, binding snapshot, planner version, graph nodes/dependency edges, effect summary, resource claims, authorization/approval refs, retries/cancel policies, expected artifacts, deadline/budget, plan_digest, creation timestamp.

**Инвариант:** после admission нельзя молча заменить semantic operation version, snapshot ЦБ, destination, permissions или worker type в уже объявленном плане. До начала эффектов можно явно заменить план новой revision с повторной валидацией; после начала значимого исполнения требуется `PlanAmendment`/plan epoch с причинной историей, а в ряде случаев — новый Run. **[UNKNOWN]** точная грань между Run revision и новым Run требует пилота динамических схем.

### 5.5. Дедупликация, reuse и общий ресурс — разные решения

- **Dedup invocation:** два плановых узла доказанно обозначают одно действие с эквивалентными semantic inputs, versions, freshness, authorization scope, destinations и effect contract. Только тогда один actual producer может удовлетворить двух consumers.
- **Reuse completed work:** существующий verified результат подходит для нового входа; нужны source/registry freshness, versions, currentness, scope и permissions. Это независимое решение от dedup *в рамках одного Run*.
- **Cache:** физически сохранённый материал; наличие байтов не доказывает допустимость повторного использования.
- **Shared resource:** connection pool, rate limiter, read-only resource, worker initialization. Его надо описывать resource claim, а не фиктивной бизнес-операцией `connect()` в каждом сценарии.

**Пример:** два независимых расчёта требуют один и тот же подтверждённый SourceSnapshot; можно выполнить загрузку один раз и дать две логические ссылки. Однако две записи одинаковой таблицы в **разные адреса** имеют разные эффекты: вычислительная стадия reuseable, обе записи — самостоятельные.

**Запрет по умолчанию:** автоматическое dedup destructive/external effect, если не доказан idempotency contract и нет согласованной policy повторного эффекта. `operation_id == operation_id` никогда не достаточный критерий.

### 5.6. Machine planning и AI

ИИ может предложить выбор Scheme/Operation или структурированное дополнение графа, однако **валидатор и planner** обязаны пересчитать typed inputs, authority, effects, versions, applicability и resources. ИИ не получает `shell` как стандартную capability и не переписывает Work state собственным текстом. Если агент меняет план на ходу, это создаёт versioned плановый decision/checkpoint, а не невидимую новую ветку.

**UNKNOWN:** общий внешний cognitive protocol ещё требует контрактной проверки. Принцип единого execution spine устойчив независимо от будущего AI framework.

---
## 6. Единая execution state machine

### 6.1. Не один гигантский enum, а связанное семейство FSM

**[CONSOLIDATED]** Универсальная машина состояний должна покрывать admission, Run, Job, OperationRun, Attempt, контроль effects, acceptance и closure. Попытка хранить всё в поле `Case.status` (`running`, `success`, `failed`) разрушает причинность: работа может ждать ответа человека без вычислений, Job может ждать ресурс, физический worker может погибнуть после commit, а новый Run — уже выполняться при открытой прежней Work.

**[TARGET-HYPOTHESIS]** Каноническая модель — несколько ограниченных state machines с явными causal relations и transactionally committed transitions. У каждого объекта собственный authority. В UI можно агрегировать состояние до одной короткой подписи, но исходные статусы остаются доступными.

### 6.2. Work FSM: семантическое обязательство

```text
CANDIDATE
  ├─> REJECTED / WITHDRAWN       [admission result, Work не создана]
  └─> ADMITTED
         ├─> ACTIVE <──────────────┐
         │     ├─> AWAITING_INPUT  │
         │     ├─> AWAITING_APPROVAL
         │     └─> AWAITING_REVIEW─┘
         ├─> COMPLETED
         │      └─> CLOSED
         └─> CANCELLED / WITHDRAWN [по решению work authority]

CLOSED --explicit reopen with reason--> REOPENED / ACTIVE
```

**Правила:** `COMPLETED` — оценка того, что требования исполнены; `CLOSED` — административное/продуктовое закрытие и фиксация residuals. `WITHDRAWN` означает снятие поручения и не переписывает уже совершённые эффекты. `REOPENED` требует отдельного события и новой revision; history closure сохраняется. Work в `AWAITING_INPUT` может не иметь active Job; Run может завершиться раньше Work.

**[UNKNOWN]** Нужны ли одновременно `COMPLETED` и `CLOSED` в пользовательском v1? Семантически полезны, но могут отображаться одним состоянием до появления review/SLA. Обязательное требование — отличать *execution done* от *work accepted*.

### 6.3. Run FSM: эпизод исполнения и проверки

```text
PREPARED
   ├─> REJECTED              (не прошёл admission/validation)
   └─> ADMITTED
          ├─> WAITING_APPROVAL / WAITING_INPUT
          └─> QUEUED
                 ├─> RUNNING
                 │      ├─> WAITING_EXTERNAL / WAITING_APPROVAL
                 │      ├─> CANCEL_REQUESTED → CANCELLING
                 │      └─> FINALIZING
                 └─> CANCEL_REQUESTED

FINALIZING / CANCELLING → TERMINAL(outcome)
TERMINAL(outcome): SUCCEEDED | PARTIAL | FAILED | CANCELLED | OUTCOME_UNKNOWN
```

**Уточнение:** `REJECTED` до admission — статус request, а не обязательно terminal Run, если `run_id` ещё не выдавался. UI вправе показывать отказ отдельной карточкой, но не выдавать его за прошедшее исполнение. При approval внутри исполнения Run может находиться в `WAITING_APPROVAL`; рабочий ресурс желательно освобождать, если checkpoint безопасен. Для долгих external waits `RUNNING` непрозрачен и должен быть заменён явным ожиданием.

**Execution outcome и lifecycle — отдельные поля.** `terminal` сообщает необратимость зафиксированного перехода, а `outcome` — содержимое исхода. У одного Run только один initial terminal receipt, но позже возможны **ReconciliationAssessment** и новое Work decision без задним числом исправленной истории фактического наблюдения.

### 6.4. Job FSM: очередь и физическое исполнение

```text
                  ┌─> WAITING_RESOURCE ─┐
QUEUED ───────────┼─> WAITING_APPROVAL ─┼──> CLAIMED
                  └─> WAITING_EXTERNAL ─┘        │
                                               v
                                            RUNNING
                                               │
                       ┌───────────────────────┼──────────┐
                       v                       v          v
                 FINALIZING             CANCEL_REQUESTED  INTERRUPTED
                       │                       │          │
                       v                       v          v
                    TERMINAL                CANCELLING  RECONCILING
                                                          │
                                  safe reschedule <───────┤
                                  terminal outcome <──────┘
```

`CLAIMED` означает подтверждённое владение lease (если применяется распределённый или межпроцессный worker). Истечение lease не доказывает прекращение кода и не означает провал предметной операции. Повторная выдача возможна лишь с fencing и проверкой возможных эффектов. Отдельные `WAITING_*` и `RECONCILING` гарантируют честное отображение причины ожидания.

**Рекомендуемые ограничения переходов:**

- `QUEUED → TERMINAL(CANCELLED)` допустим без запуска worker и without effects;
- `RUNNING → CANCEL_REQUESTED` выражает accepted control command, но реальный outcome появляется после safe stop/commit verification;
- `FINALIZING` не может закончиться `SUCCEEDED` до validation и публикации обязательных outputs/receipts;
- `TERMINAL` недоступен прямому исправлению UI. Новый факт после неизвестного исхода оформляется reconciliation record;
- control command, полученная после терминального перехода, возвращает `already_terminal` с текущим receipt.

### 6.5. OperationRun / Attempt / EffectReceipt

`OperationRun` отвечает за выполнение одной semantic invocation и aggregated outcome. `Attempt` хранит `attempt_no`, `backend`, `lease_generation`, `started_at`, `heartbeat`, timestamps, observed errors, checkpoint ref, outcome. Перед потенциально необратимым действием оформляется `EffectIntent`, после наблюдаемого commit — `EffectReceipt` с идентификатором внешнего действия/объекта и степенью подтверждения. При timeout между commit и ACK Attempt получает `OUTCOME_UNKNOWN`, но это *не равно* логическому `FAILED`.

**TARGET-HYPOTHESIS:** всем side-effecting canonical operations требовать effect classification: `none/read_only`, `staged_write`, `idempotent_write`, `external_mutation`, `destructive`, а для фактического результата хранить `effect_status` (`not_started`, `prepared`, `committed`, `verified`, `partial`, `unknown`, `compensated`). Такая ось лучше, чем одни лишь `ok: bool` или `status=success`.

### 6.6. Кто выполняет переход и когда

| Событие | Владелец решения | Durable result |
|---|---|---|
| Request admitted | Work authority / admission service | Work/revision + origin/authorization |
| Plan sealed | Planner + admission owner | Plan snapshot/digest |
| Job queued | JobManager | Job state + outbox event + idempotency association |
| Job claimed | Scheduler/lease manager | owner/expiry/generation |
| Attempt started | Executor + JobManager | attempt start receipt |
| Progress advanced | Operation adapter / domain emitter | structured progress event, throttled projection |
| External effect prepared | Effect boundary | effect intent + staging ref |
| External effect confirmed | Effect boundary + verifier | effect receipt |
| Job finalized | JobManager/state authority | terminal receipt and linked outputs |
| Run finalized | Orchestrator | aggregate outcome and residual refs |
| Work accepted / closed | consumer/authorized work controller | assessment/closure record |

**[CONSOLIDATED]** Worker и UI вправе **предлагать** переход, но проверка revision, полномочий, правомерности и запись принадлежат единому authority. Иначе два окна могут одновременно поставить одному Job два terminal outcomes.

---

## 7. Сервис исполнения: команды, транзакции и события

### 7.1. One-way control plane

**TARGET-HYPOTHESIS:** все пользователи/триггеры обращаются к одному `ExecutionService` через typed commands:

```text
SubmitWork / SubmitRun
ApproveExecution / DenyExecution
CancelRun / CancelJob
RetryFailedOperation / StartNewRun
PauseJob (только при supports_checkpoint)
ResumeRun (только после reconciliation/validation)
RequestReconciliation
AcceptResult / RejectResult / CloseWork / ReopenWork
```

Команды — requests на изменение authoritative состояния; **events** — факты изменения. `CancelRun` не означает `RunCancelled`; `SubmitRun` не означает `JobStarted`; `ArtifactProposed` не означает `ArtifactPublished`.

### 7.2. Контракт команды

```yaml
# TARGET CONTRACT EXAMPLE — не существующий endpoint
command_id: cmd:...
kind: execution.submit_run
principal_id: principal:...
actor_kind: human | automation | ai | service
work_ref: work:...
scenario_ref: scenario:escrow-history@2
parameters_ref: parameter-snapshot:...
idempotency_key: client-or-trigger-scoped-key
expected_work_revision: 11
correlation_id: corr:...
requested_at: 2026-10-09T10:00:00Z
```

Ответу требуется различать `accepted`, `already_accepted` (возврат того же Work/Run/Job), `needs_input`, `needs_approval`, `unavailable`, `rejected` и `conflict`. Для network transport retry тот же idempotency key должен вернуть прежний результат admission. Если тот же ключ пришёл с *другим payload digest*, правильный ответ — `IDEMPOTENCY_CONFLICT`, а не незаметная замена параметров.

### 7.3. Атомарная точка admission

**TARGET-HYPOTHESIS:** в одной транзакции или эквивалентном durable commit создаются `Run`, ссылки на immutable Plan/Binding, Jobs, initial events, idempotency record и outbox notification. Внешний worker получает задания **после commit**, а не до него. Запуск worker до сохранения run identity создаёт orphan effects и ослабляет recovery.

**Возможная процедура:** `validate → check permissions → reserve uniqueness/idempotency → persist Work/Run/Plan/Jobs/event/outbox → commit → dispatch`. Side effects всегда вне DB-транзакции, с separate intent/receipt и reconciliation. Для single-node SQLite это реализуемо без Kafka/Celery; конкретная БД рассматривается темой 05.

### 7.4. Domain events vs telemetry vs platform problems

- `ExecutionEvent`: долговременное изменение состояния/контекста (`run.started`, `job.claimed`, `operation.failed`, `artifact.published`, `work.accepted`), с ID/causal refs.
- `ProgressEvent`: структурированный ход выполнения, stage, units/total, availability of estimate; может агрегироваться.
- `Diagnostic`: domain/operation explanation и validation issue; может иметь severity.
- `Trace/span/log`: инженерная диагностика, duration/correlation; не является state machine.
- `ProblemRef`: безопасная ссылка на зарегистрированную операционную проблему; AppDock может владеть платформенным problem/evidence контуром.

**Внешняя сверка:** OpenTelemetry различает **events** как point-in-time occurrences и **spans** как операции с длительностью; это подтверждает полезность разделения, но **не определяет** внутренний Work API Strategy Box. См. [OTel events](https://opentelemetry.io/docs/specs/semconv/general/events/) и [trace conventions](https://opentelemetry.io/docs/specs/semconv/general/trace/).

### 7.5. Correlation и causality

Минимальная цепочка идентификаторов:

```text
origin message / occurrence / API command
     → work_id
     → run_id
     → plan_id + binding snapshot
     → job_id
     → operation_run_id
     → attempt_id
     → effect_intent / effect_receipt
     → result_ref / artifact_ref / problem_ref
```

Для событий дополнительно `event_id`, `event_seq`, `causation_id`, `correlation_id`, `actor/principal`, `occurred_at`, `observed_at`, `schema_version`. Пользовательская карточка должна позволять пройти по цепочке, не показывая чувствительные технические поля.

---

## 8. JobManager, backend и ресурсы

### 8.1. Один JobManager на authoritative scope

**CONSOLIDATED.** У одного Strategy Box узла одна общая authoritative очередь/координатор независимо от числа Windows клиентов, открытых веб-вкладок, запущенных автоматизаций и подключённых машинных инициаторов. Это **логическая единственность**, не требование одного Python процесса при масштабировании: несколько worker процессов могут работать с общей транзакционной истиной.

`JobManager` управляет waiting/ready/claimed/running/finalizing/reconciling, учитывает fairness, priority, effect scopes, quotas, deadlines, cancellation, retry budgets и ресурсы. Пользователь вправе видеть очередь и причины ожиданий. Нельзя оставлять `is_busy` на уровне каждого desktop клиента как главное правило параллельности.

### 8.2. Executor интерфейс и backends

```python
# CONCEPTUAL ONLY
class ExecutionBackend(Protocol):
    def capabilities(self) -> BackendCapabilities: ...
    def start(self, job: JobEnvelope, lease: LeaseToken) -> StartReceipt: ...
    def query(self, job_id: str) -> JobObservation: ...
    def request_cancel(self, job_id: str, reason: str) -> CancelReceipt: ...
    def collect_result(self, job_id: str) -> ExecutionReceipt: ...
```

Локальный worker, isolated subprocess и удалённый host — разные реализации. Controller хранит product semantics и durable history; backend — фактическую механику процесса, task transport и изоляции. Для долгой CPU-bound операции предпочтителен отдельный процесс (а не Qt UI thread). `WorkerHeartbeat` показывает присутствие процесса, но не доказывает целостность вычисленного результата.

### 8.3. Конкретные resource claims

Для каждого Job/Operation требуются **декларации**: `cpu_class`, `memory_estimate`, `network/source quota`, `storage read set`, `storage write set`, exclusive target, expected duration class, backend constraints и optional accelerator. Примеры:

- чтение разных SourceSnapshots — параллельно, с rate limit authority/source;
- запись разных артефактов — параллельно при уникальных destinations;
- публикация одного и того же logical artifact alias — сериализация либо conditional commit;
- очистка каталога — эксклюзивная блокировка namespace после review плана;
- сложная SORS-оптимизация — отдельный memory/CPU budget и ограниченная конкуренция;
- массовая загрузка с сайта — лимит запросов, backoff и source-specific fairness.

**Важная деталь:** CPU/memory limits и expected duration — *административные estimates/quotas*, а не магические гарантии. Без process isolation трудно принудительно применять жёсткие memory budgets.

### 8.4. Resource locks ≠ worker lease

`ResourceLock` защищает объект/namespace от конфликтующих воздействий; `WorkerLease` защищает право утверждать состояние конкретного Job. Это разные отношения. В распределённой среде Job получает `lease_generation`/fencing token. После expiry старый worker может продолжать исполнять код; потому publish управляемого результата должен проверять актуальный token. Для неподконтрольного внешнего API, не поддерживающего fencing/idempotency, автоматический повтор должен быть запрещён либо ограничен reconciliation.

### 8.5. Starvation и fairness

**TARGET-HYPOTHESIS:** планировщик учитывает приоритет, вид инициатора, estimated resource cost, ожидание пользователя, deadline, source rate limits и age. Фоновые обновления не должны монополизировать worker pool; интерактивные read-only запросы не должны всегда вытеснять обслуживание очередей. До статистики реальных jobs достаточно простого bounded FIFO с несколькими resource classes, а не сложного priority scheduler.

### 8.6. One job vs many jobs: критерий дробления

Дробить граф нужно только если появляется реальная выгода от независимого scheduling/retry/resource placement или recovery. Микроскопические Jobs на каждый parser helper вызов увеличат журнал, overhead и сложность. Разделение на Jobs по настоящим source/dataset/publish boundaries даёт максимальную пользу: разный retry, независимые ресурсы, safe checkpoints и artifactual receipts.

---

## 9. Retry, cancellation, timeout и неопределённый исход

### 9.1. Повторение имеет четыре семантики

| Операция управления | Новый объект | Когда уместна |
|---|---|---|
| HTTP/client retransmission | тот же command/idempotency result | запрос потерял response |
| `RetryAttempt` | новый Attempt прежнего OperationRun/Job | recoverable failure; contract позволяет повтор |
| `ResumeRun` | новый checkpoint execution segment/Job либо Attempt с lineage | план и inputs остаются допустимы, checkpoint доказан |
| `StartNewRun` / `RepeatWork` | новый Run той же Work или новый Work | новый snapshot, изменённый план, новая поставка/период либо самостоятельный результат |

Нельзя одно слово «повторить» превращать в один обработчик. UI должен пояснять, *что именно* будет повторно выполнено и какие уже созданные результаты сохранены.

### 9.2. Governing retry budget на одной effect boundary

**CONSOLIDATED.** Слепое вложение HTTP retry × Operation retry × Scenario retry × Job retry увеличит число реальных попыток экспоненциально. Политика задаёт единый budget по определённому effect boundary, а нижние transports могут делать ограниченные transparent retries только в пределах объявленного budget. Требуются timeout classes, max attempts, backoff/jitter, retryable errors, overall deadline, idempotency, safe-points и policy on unknown.

**Категории ошибок:** transient unavailable, rate limit, timeout before side effect, validation rejected, permission denied, conflict/stale inputs, unsupported operation, partial effect, unknown effect. Только явно retryable классы допускают auto-retry.

### 9.3. Cooperative cancellation

```text
User/automation issues CancelRun
       ↓ authorize + accept + persist cancel_requested
JobManager propagates cancellation token
       ↓
executor checks safe point / closes stream if feasible
       ↓
stop before next effect / finish current uninterruptible step
       ↓
cleanup staging, verify committed effects
       ↓
finalize CANCELLED / PARTIAL / SUCCEEDED / OUTCOME_UNKNOWN
```

**`CANCEL_REQUESTED` ≠ `CANCELLED`.** Если worker успел выполнить commit до поступления запроса, корректным outcome может быть `SUCCEEDED`; поздний cancel возвращает `already_terminal`. Отмена после частичного безопасного результата может дать `PARTIAL` при явной policy. При неизвестной записи возвращать «отменено» запрещено.

**CONSOLIDATED:** cancel — прекращение дальнейших действий; rollback/compensation — отдельная операция с собственной applicability и effect history. Qt `QThread.terminate()` и насильственное уничтожение сетевого запроса нельзя считать универсальной бизнес-отменой.

### 9.4. Force termination

Допустима как аварийная control capability при изолированном worker process/process group, permission check и reason. После force stop проверяются staging, external receipts, output integrity и locks. До доказательства результата Job/Run остаётся в reconciliation/unknown, а не автоматически `FAILED`/`CANCELLED`. Секреты и частные данные не должны попасть в аварийные dump/logs.

### 9.5. `OUTCOME_UNKNOWN`: типичный сценарий

```text
Attempt 1: publish(report.xlsx)
   │
   ├─ remote endpoint persisted final object
   └─ network drops before acknowledgement

Observed state: transport timeout
Actual external effect: UNKNOWN to caller
Correct response: EffectReceipt(status=unknown), block blind retry
                   query destination / compare hash / seek remote receipt
                   → reconciliation: committed or not_committed
```

Здесь transport error и предметный outcome независимы. Если `report.xlsx` уже опубликован, второй `publish` может создать дубли/повреждение, даже когда клиент увидел timeout. Для локального managed artifact store можно использовать staging + hash + atomic publish/conditional replace; для внешнего API нужны provider-defined receipt/idempotency или ручная проверка.

### 9.6. Exactly once: что реально обещать

**[CONSOLIDATED]** Универсального exactly-once *external effect* без участия системы назначения обещать нельзя. Реалистичный contract: durable at-least-once delivery для разрешённых идемпотентных steps + dedup по identity + effect ledger + reconciliation/fencing. Для non-idempotent external writes — at-most-once *automatic attempt* с `OUTCOME_UNKNOWN`/manual reconciliation, если API не умеет idempotency token.

Сверка: [AWS Durable Execution: idempotency and retries](https://docs.aws.amazon.com/durable-execution/patterns/best-practices/idempotency/) различает at-least-once и at-most-once retries и прямо предостерегает от трактовки последних как end-to-end exactly once. Temporal показывает, как durable workflow state отделяется от повторно исполняемых activities ([Tasks](https://docs.temporal.io/tasks), [Activity execution](https://docs.temporal.io/encyclopedia/activities#activity-execution)). Это *technical precedents*, не рекомендация немедленно ставить Temporal.

### 9.7. Partial как результат, а не индульгенция на потерю данных

`PARTIAL` допустим только если есть явный `supports_partial`/acceptance profile, перечислены выполненные и невыполненные требования, опубликованы лишь валидные части, зафиксированы residuals, а пользователь не получил ложную общую отметку `SUCCEEDED`. У доменов с `continue_on_error` отдельный failure ledger обязателен; «книга XLSX создана» без проверки полноты входных данных — недостаточно.

---

## 10. Recovery и durable execution

### 10.1. Условия реального продолжения после закрытия UI

**TARGET-HYPOTHESIS:** Work/Run/Job authoritative state хранится на узле и управляется headless application runtime, работающим независимо от Windows GUI, вкладки Web, Android и активного Thread. AppDock устанавливает/активирует среду, организует startup/health/host lifecycle, а application service сохраняет собственные transactional work records. При выключенном физическом узле никакая фоновая задача, естественно, не исполняется; после его старта действует persisted recovery policy.

### 10.2. Minimal crash-safe storage semantics

- transactions для state transitions, job claims и outbox;
- уникальные constraints на `idempotency_key + principal/target scope` и scheduled `occurrence_id`;
- immutable plan/parameter snapshots и content digests;
- optimistic revision/compare-and-swap на изменяемых Work/Job records;
- append-only domain events либо журнал transition records, достаточный для восстановления причинности;
- atomic artifacts manifest publication и `staged/published/abandoned` states;
- schema versioning и corruption reporting вместо silent empty reset;
- durable backup/restore и восстановление индексов/projections из authority.

**[UNKNOWN]** SQLite WAL vs PostgreSQL, единственный event store vs tables+event log, physical location и масштаб retention относятся к теме 05. Execution contract не должен зависеть от выбора ORM/БД.

### 10.3. Recovery алгоритм

```text
1. AppDock raises environment/host; host validates durable store schema and identity
2. Recover pending transactions/outbox and acquire exclusive recovery coordination
3. Load active Runs, Jobs, leases, checkpoints and effect intents
4. For each claimed/running/finalizing Job inspect process/worker state
5. Detect still-live owners; do not blindly reassign on temporary heartbeat loss
6. Reconcile expired lease generation, staging, receipts, destination artifacts
7. Safe job: resume/retry with new Attempt and causal link
8. Unsafe unknown effect: mark reconciliation needed; require evidence/approval
9. Recompute dependent graph nodes and aggregate Run states
10. Deliver durable events/projections; calculate missed automation occurrences
11. Publish health summary and user-visible unresolved problems
```

**Особенно важно:** stale heartbeat — сигнал, не доказательство crash; lease expiry не прекращает старый process. После crash recovery система не должна автоматически переводить все бывшие `running` в `failed` или повторно запускать каждую операцию.

### 10.4. Checkpoint и validation

Checkpoint хранит **семантически безопасную точку**: завершённые plan nodes, source/registry identity, effects, artifact receipts, transform version, remaining DAG. Resume разрешён только когда inputs/bindings остаются совместимы и выполненные узлы можно reuse. При изменении исходной публикации, semantic definition или regulatory schema обычно требуется **новый Run** либо explicit replan с полной причинностью.

### 10.5. Recovery не заменяет human work closure

Даже если Run физически восстановился и произвёл валидный файл, Work может оставаться `awaiting_review`. И наоборот, допустим Work closure после documented impossibility без новых jobs. Это защищает продукт от подмены цели процедурой.

---

## 11. Foreground, background, scheduler, watcher и AI

### 11.1. Пять независимых измерений запуска

| Измерение | Возможные значения | Последствия |
|---|---|---|
| Origin | human / automation / AI / peer / API | attribution и authority |
| Trigger | immediate / scheduled / event / data change / manual resume | occurrence identity и deadline |
| Client presence | attached foreground / detached background | UI notification и responsiveness |
| Backend placement | local / node worker / remote execution | lease/transport/security/latency |
| Work pattern | single / composite DAG / ongoing monitor / approval-gated | planning и closure policy |

**CONSOLIDATED.** Нельзя вводить отдельный `ScenarioKind.background` как главный тип предметной операции. «Фон» — режим присутствия клиента; периодичность задаёт `AutomationSpec`; remote — способ размещения worker; AI — actor/consumer. Все они используют один Work/Run/Job spine.

### 11.2. Автоматизация как durable definition

```yaml
# TARGET CONTRACT EXAMPLE
spec_id: automation:cbr-monthly
revision: 4
target: scenario:cbr-monthly-update@2
trigger:
  type: calendar
  timezone: Europe/Moscow
  local_time: '08:00'
  calendar: monthly
run_as: principal:operator-1
admission_policy: new_work_per_occurrence
misfire_policy: skip | run_once | bounded_catch_up
coalesce_policy: no_parallel_duplicates
max_concurrent_runs: 1
enabled: true
```

**Разделение:** `AutomationSpec.enabled=true` не означает, что сейчас есть `running Job`. Отключение правила влияет на новые occurrences; уже начатый Run не отменяется без отдельного разрешённого control command.

### 11.3. Расписания и календарная семантика

Для «каждый день в 08:00» хранятся IANA timezone, локальное время и calendar policy; это отличается от «каждые 24 часа». UTC хранит timestamps фактических событий; wall-clock recurrence отдельно решает DST gap/fold, дни без запуска, выходные/праздничные календари, skip/coalesce/misfire. Уникальная identity `(automation_revision, scheduled_occurrence)` защищает от двойной подачи после restart. Для пропущенных срабатываний после offline предпочтителен bounded catch-up, а не бесконечный шквал старых jobs.

### 11.4. Источники и watchers

Watcher отслеживает публикацию/изменение source, но сам по себе не обязан быть бесконечной domain Operation. Он создаёт событие с обнаруженной source identity и может инициировать Work по automation policy. Домен `stratbox` подтверждает новый SourceSnapshot/validity; runtime решает, какую Work запускать. Failures source check не должны означать «публикации нет» или вызывать ложный successful Run.

### 11.5. AI инициатор

ИИ может выразить Intent, выбрать разрешённые capabilities, предложить параметры, запросить planning preview и создать candidate Work. Вся application authority остаётся в runtime: deterministic validation, grants, effect policy, approval и sealed plan. При смене агента, провайдера модели, истории Thread и клиента активный Job продолжает существовать; агент может получить его статус по ID. Machine reasoning не подменяет расчётного ядра и не переводит произвольный текст в технически признанный `SUCCEEDED`.

### 11.6. Источник истины scheduler

**[CONSOLIDATED]** Предметные расписания, правила watcher и automation history принадлежат **Strategy Box application layer**, а не операционной системе и не AppDock. AppDock может поддерживать сервисный uptime и управлять lifecycle headless host; OS Task Scheduler/systemd помогают поднять host/agent, но не являются главным каталогом пользовательских бизнес-автоматизаций.

---
## 12. Result, artifacts, acceptance и Closure

### 12.1. Три уровня «получилось»

Для каждого Work целесообразно хранить **три независимые оценки**:

1. **Execution outcome** — все ли обязательные execution contracts соблюдены; успешно ли завершены runs/jobs и совершены ли ожидаемые эффекты.
2. **Domain qualification** — валидны и сопоставимы ли полученные данные, что известно об источниках, полноте, методе, неопределённости, freshness и ограничениях вывода.
3. **Work acceptance/closure** — удовлетворены ли исходные требования поручения и принят ли результат ответственным потребителем, какие residuals остались.

Пример: `Run: SUCCEEDED`, `XLSX: PUBLISHED`, `Domain support: QUALIFIED / partial coverage`, `Work: AWAITING_REVIEW`. Никакого противоречия здесь нет. Другая ситуация: все вычислительные шаги выполнились, однако сравнительный коэффициент построен на разных периметрах РСБУ/МСФО, поэтому domain validation отклоняет его и Work остаётся открытой.

### 12.2. Что представляет `Result`

**CONSOLIDATED с темой 03.** Предметный `AnalyticalResult` является структурированной сущностью с outcome/relevant datasets, квалификацией, source snapshot refs, transformations, validation/provenance и expected artifact kinds. Артефакт — опубликованная materialization либо отдельный логический продукт с stable ID, manifest и provenance. Один Run может создать несколько результатов и артефактов; один результат можно представить в XLSX/CSV/MD без новой банковской расчётной операции.

**TARGET-HYPOTHESIS:** даже простым операциям возвращать тонкий typed envelope с `domain_result_refs`, `artifact_refs`, `warnings`, `failures`, `diagnostics`, `provenance_ref`. Богатые SORS/conflict grids остаются domain-specific. Не превращать общий envelope в гигантскую универсальную модель расчётов.

### 12.3. Finalization как commit protocol

```text
worker operation done
   → collect outputs into staging
   → validate type, completeness, integrity, semantic postconditions
   → write artifact manifest and source/provenance refs
   → commit/publish outputs (conditional/atomic where possible)
   → persist effect receipts
   → finalize OperationRun / Job with unique outcome
   → aggregate Run result and residuals
   → notify clients via outbox
   → Work awaits acceptance or auto-closes under declared policy
```

**Критическое правило:** `progress=100%` нельзя обещать до commit/verification обязательного результата. Для неизвестного объёма показывать stage и indeterminate progress, а не придуманную процентную шкалу. Публикация файла до успешной проверки означает ошибочную продуктовую семантику.

### 12.4. Acceptance policies

| Work profile | Кто принимает | Auto-close |
|---|---|---|
| простая техническая диагностика | policy/tested postcondition | допустимо при проверенном результате |
| выгрузка официальных файлов | requester/policy, manifest completeness | допустимо, если чёткие требования и failures=0 |
| аналитический отчёт/сравнение | человек либо отдельно авторизованный assessor | обычно `awaiting_review` |
| реконструкция неопубликованного показателя | evidence/qualification policy + человек при существенных предположениях | по умолчанию review |
| destructive cleanup | authorized actor + verified effect receipts | после явного postcondition и audit |
| регулярная автоматизация | preset acceptance policy, explicit exception rules | по occurrence; общий monitoring Work остаётся активным |

**[UNKNOWN]** Общесистемная таблица default acceptance profiles пока не доказана. Первоначальный vertical slice должен покрыть минимум read-only operation, экспорт с provenance и approval-gated destructive action.

### 12.5. Failed work не стирает результаты предыдущих Runs

Новый Run, оказавшийся `FAILED`, не должен скрывать предыдущий принятый Result или переписывать логический artifact. Work хранит историю попыток, причины, retained outputs и current-result selection policy. «Последний Run» не обязательно означает «лучший/актуальный Result»; новая публикация может инвалидировать прежний результат, а новый расчёт — всё ещё завершиться ошибкой. Это согласуется с раздельными currentness/lineage по теме 03.

---

## 13. Наблюдаемость как часть контракта исполнения

### 13.1. Пользователю нужна причинная история, не поток traceback

**CURRENT.** В Windows уже есть events, case/step links, operation files logs и UI inspector. Это основа. **TARGET:** structured status следует получать из durable execution service; progress и этапы показываются в Work/Run/Job projections; сырой log раскрывается при диагностике с RBAC/sanitization. Нельзя пытаться восстановить очереди и state transitions парсингом строк лога.

### 13.2. Модель события

```yaml
# CONCEPTUAL ONLY
schema_version: 1
event_id: evt:...
seq: 1256
type: operation.progress
occurred_at: 2026-10-09T10:02:20Z
correlation_id: corr:...
causation_id: evt:previous
work_id: work:W1
run_id: run:R1
job_id: job:J1
operation_run_id: operation-run:O1
actor_kind: system
stage: source_download
progress:
  completed: 18
  total: 41
  unit: source_file
severity: info
safe_message: 'Получено 18 из 41 исходных файлов'
problem_ref: null
```

**Важное distinction:** событие хранит status/measurement в момент наблюдения. Текущая клиентская карточка пересчитывается как projection; позднее сообщение не должно по ошибке «отменять» предыдущее terminal. Для reconnect нужны `snapshot_revision + cursor` с дедупом `event_id`.

### 13.3. Раздельные слои observability

| Слой | Факты/объекты | Семантический owner |
|---|---|---|
| Domain | validation, business failure, quality, source lineage | `stratbox` |
| Application execution | Run/Job/Attempt, progress, cancellation, queue, effect receipts | Strategy Box application runtime |
| Platform | process crash, node/session health, filesystem failures, install/update, support bundle | AppDock |
| Client | выбранный экран, unread/read cursor, визуальное состояние уведомления | Windows/Web/Android projection |

**Граница:** один и тот же сбой может породить domain diagnostic и platform ProblemOccurrence, но без многократного создания независимых «проблем» на каждое окно. Strategy Box хранит `ProblemRef` и безопасный impact status, AppDock — собственный платформенный контур evidence. Поскольку AppDock развивается отдельно, точные поля этого стыка требуют сверки с authoritative release contract перед внедрением.

### 13.4. Aggregation и oversharing

На общем узле полезно предупреждать других участников о недоступном источнике или занятом ресурсе. Показывать следует **impact-filtered shared condition**, а не чужие секреты, пользовательские параметры, пути и traceback. ACL применяется к Work/Run/Artifact и к проекции события; знание `job_id` само по себе не даёт право читать его содержимое или управлять им.

### 13.5. Performance событий

Долгая операция SORS может иметь тысячи внутренних solver decisions, загрузчик — десятки файлов, а parser — миллионы строк. Нужны разные частоты: domain checkpoint и summary для UI, подробная инженерная телеметрия на диске/по запросу, rate-limited progress projection. Каждую строку входного CSV превращать в client event недопустимо. Event retention и diagnostic log retention должны задаваться отдельно от срока жизни Work/Result.

---

## 14. Multi-user, Thread и права управления исполнением

### 14.1. Один Work допускает несколько контекстов

`Thread` — контекст разговора и ссылок на работы, а не процесс. Один Thread может содержать несколько независимых Work и параллельных Runs; одна Work может обсуждаться в разных Thread с разными участниками, если политика доступа допускает это. Archive/delete Thread не является `CancelRun`. Восстановленная Web/Android сессия получает state по Work/Run/Job IDs, а не читает случайные локальные JSON другого клиента.

### 14.2. Параллелизм выражается ресурсами, а не окнами

Два человека вправе запустить разные read-only операции одновременно. Конфликт возникает при общем destination, эксклюзивном source lease, несовместимом изменении registry либо превышении CPU/memory/network budgets. Система сериализует конкретный ресурс или ставит Job в `WAITING_RESOURCE`, **не блокируя весь узел** из-за одной тяжёлой задачи. Политика может ограничить один тяжелый solver Job и несколько лёгких reads одновременно.

### 14.3. Command authorization

**TARGET-HYPOTHESIS:** `StartRun`, `CancelRun`, `ForceTerminateJob`, `Retry`, `ApproveEffect`, `PublishArtifact`, `AcceptWork` проверяются отдельно. Полномочие `view` не включает `cancel`; право запуска read-only сценария не включает destructive mutation; владелец Automation не получает бессрочный bypass после утраты доступа. Текущую node/identity информацию можно принимать через AppDock trust boundary, но предметную authorization/effect policy определяет Strategy Box application owner.

### 14.4. Optimistic concurrency и гонки

Каждый изменяемый Work/Run/Job имеет revision. Две команды одновременно с `expected_revision=11`: один commit делает revision=12, второй получает typed `CONFLICT`, а не затирает принятое изменение. При конкурентных cancel/complete терминальный transition должен быть единственным и неизменяемым; событие `cancel_requested` не может автоматически победить committed `SUCCEEDED`.

### 14.5. Assignment отличается от Job

`Assignment` — обязательство другого участника принять решение, посмотреть результат или выполнить поручение. Оно может создавать WorkCandidate, approval или human review, но assignment не превращается в фоновый worker автоматически. Связи `assignment→work`, `review→run/result`, `participant→authority` сохраняются без копирования истории execution в заметку/чат.

---

## 15. Ownership: один смысловой владелец каждой истины

| Responsibility | Canonical owner | Другие участники |
|---|---|---|
| Банковские/макроэкономические Operation contracts и алгоритмы | `stratbox` | application связывает/вызывает; UI показывает |
| Семантика source/registry snapshot, validation, analytical provenance | `stratbox` | runtime фиксирует refs и storage lifecycle |
| Work admission/requirements/closure | Strategy Box application runtime | инициатор/потребитель принимает решения |
| Scenario catalogue и product presentation profile | Strategy Box application owner | core предоставляет capabilities; clients рендерят |
| Machine Scheme definition contract | semantic capability/scheme owner (может поставляться доменным пакетом) | application validates and binds |
| Concrete Plan/Binding, Run/Job/Attempt, queue/recovery | Strategy Box application runtime | execution backend исполняет |
| Artifact user catalog, permission/retention/Work refs | Strategy Box application runtime | core порождает result/provenance; FileStore хранит bytes |
| Scheduler/automation trigger, schedule occurrence | Strategy Box application runtime | AppDock поддерживает host availability |
| Node install/activation/environment/service lifecycle | AppDock | Strategy Box публикует health/readiness/events |
| Process/host runtime evidence, platform Problems | AppDock | Strategy Box использует безопасный ProblemRef |
| Windows rendering, local drafts, desktop open/reveal | `stratbox-windows` | читает shared semantic snapshots |
| Web/Android native rendering и narrow controls | будущие соответствующие surface owners | тот же Work/Job API |
| Machine cognition/goal interpretation | внешний cognitive consumer | не authoritative owner domain/result/job |
| Конкретные environment-dependent implementations | внешний extension provider | public core видит только generic contracts |

**Конфликт `stratbox-core` vs `stratbox-host`.** Устойчивым является **logical application/runtime responsibility**. Имя будущего physical package/process — открытый выбор. Для реальной длительной работы нужен headless service/daemon actor на узле, который условно называется `stratbox-host`, но это **ещё не существующий implementation owner**, и само имя не доказывает необходимость нового репозитория. Возможна одна библиотека application semantics плюс thin host service в составе той же поставки. Не смешивать physical and logical architectures.

**Реализуемый без нового движка путь:** desktop Windows может стать клиентом loopback/IPC instance того же headless application service, который обслужит remote/web clients. Отдельный процесс имеет смысл для lifecycle separation и crash isolation; физически единственный локальный worker может быть упрощённым вариантом данного контракта. AppDock обязан владеть запуском/мониторингом среды, а предметный JobManager — семантикой задач.

---

## 16. Отображение единой модели на поверхности

### 16.1. Windows

Текущий scenario chat и inspector следует эволюционно перевести с `ScenarioRunCase` как authoritative store на `Work/Run/Job` projections. Сохранить достоинства UI: сценарный каталог, composer, параметры, case cards, logs/artifacts inspector, incoming/outgoing author semantics. Кнопка запуска отправляет `SubmitRun`, дальше получает `work_id/run_id` и подписывается на events; Qt остаётся renderer/adapter. Наличие запущенного Run не обязано блокировать весь composer: запрет возникает по конкретным resource/permission constraints.

### 16.2. Web/Android

Одинаковые semantics и control actions, разный layout. Android companion может показывать статус/подтверждение/результат, не исполняя SORS на телефоне. Web вкладка может закрыться без остановки Job. Доступ к данным через API ограничивается правами principal и audit; reconnect обрабатывается snapshot+stream, а не созданием второго запуска.

### 16.3. Чат, центр задач и уведомления

Чат = narrative/context; Work card = смысловое поручение; Run card = запуск и результат; Jobs pane = техническая детализация; «Центр задач» агрегирует все разрешённые Jobs/Work/Automations узла. Активные чаты могут динамически подниматься выше, но это только UI sorting projection. `unread` должен быть per-user read cursor; статус Job нельзя выводить из того, что пользователь открыл сообщение.

### 16.4. План и управление в UX

Перед опасным/дорогим выполнением preview показывает цели, версию источников, объем, effect scope, destinations, ожидаемые артефакты, resource class, время как оценку, approvals. Во время выполнения — stage, прогресс, ожидаемую причину ожидания, cancel availability. После — `Run outcome`, domain validation, artifacts, residuals, кто принял Work. Кнопки «Отменить», «Повторить попытку», «Начать новый запуск», «Продолжить» и «Откатить» должны означать разные команды и показывать применимость.

---

## 17. Четыре сквозных acceptance traces

### 17.1. Trace A: пользователь запускает историю эскроу

**CURRENT basis:** `escrow.history.export` есть в Windows registry и вызывает core. **TARGET trace:**

```text
Пользователь выбирает «История счетов эскроу»
  → ScenarioDefinition@version
  → Work W1, требования: 2024–2026, XLSX, source provenance
  → Run R1; resolved parameters and snapshots; Plan P1
  → Job J1 admitted/queued/claimed
  → OperationRun O1: escrow.history.build/export
  → Attempt A1: source discovery → cache/fetch → normalize → validate
  → Artifact staging; validate workbook and publication manifest
  → Artifact ART1 published; Run R1 SUCCEEDED
  → Work W1 AWAITING_REVIEW или CLOSED по explicit acceptance profile
```

**Отказы/срывы:** недоступный официальный источник → `UNAVAILABLE`, partial только если `supports_partial`; отмена между source files; невыполненная валидация после записи XLSX не превращается в успешный Outcome. Новая ревизия статистики — новый `SourceSnapshot` и при повторном анализе новый Run, а не скрытое обновление старого Artifact.

### 17.2. Trace B: два отчёта используют общие raw-данные ЦБ

Два Scenario требуют один `source.fetch` с одинаковой snapshot identity, но один строит отраслевой аналитический Dataset, а второй — другой Report. Planner проверяет эквивалентность и может построить один shared producer node с двумя dependent consumers. Сохраняется `logical consumer count=2` и distinct lineage для каждого downstream Result. Отдельные Excel destinations публикуются независимо. Если один потребитель требует `fresh_current`, а второй допускает `cached`, reuse разрешён лишь при доказанном policy implication и одинаковом разрешённом source identity.

**Итог:** важна **не синтаксическая дедупликация одинакового HTTP URL**, а semantic equivalence включая freshness, permissions, dataset validity и effect scope.

### 17.3. Trace C: разрушительная очистка рабочего каталога

**CURRENT inspiration:** FRG использует безопасный `cleanup plan → execute` принцип. **TARGET execution:**

```text
Work W3: упорядочить каталог поставок
  → Operation frg.cleanup.plan (read-only)
  → result: enumerated actions, paths, reasons, risks
  → explicit Approval: actor + object set + version/hash + expiry
  → Run/Job execute uses approved plan digest
  → exclusive resource lock on affected namespace
  → per-effect intent/receipt and audit
  → postcondition: only permitted items changed, untouched files preserved
  → terminal outcome / partial receipts / reconciliation
```

Если исходный каталог изменился после утверждения, `execute` должен сообщить `PRECONDITION_CHANGED` и запросить новый plan/approval. Если удаление частично успешно, запрещено давать overall `SUCCEEDED` и запрещено скрывать, какие файлы исчезли. Force termination во время удаления не превращает ситуацию в «полностью отменено».

### 17.4. Trace D: мониторинг публикаций и crash после commit

`AutomationSpec` ежедневно в локальном календаре рассчитывает occurrence. Уникальный occurrence создаёт Work/Run; Job использует source watcher, условно создаёт downstream update. После изменения external/managed artifact worker погибает до получения ACK. При restart host:

1. Находит `EffectIntent` без final receipt.
2. Проверяет сохранённые байты, target hash и manifest, а не немедленно повторяет publish.
3. Если публикация подтверждена — создаёт reconciliation evidence, завершается корректный aggregate result.
4. Если outcome нельзя установить — фиксирует `OUTCOME_UNKNOWN`, блокирует автоматический повтор опасного эффекта, создаёт review item.
5. Новый UI получает ту же `run_id`; повторное нажатие в Web/Android с прежним idempotency key не создаёт второй Work/Job.

**Этот кейс — обязательный приемочный барьер** до обещания durable background execution.

### 17.5. Дополнительные проверки модели (коротко)

- Один Thread → три Work, две Jobs running параллельно; закрытие Thread не меняет Job.
- Одна Work → два независимых Runs: основной расчёт и последующая верификация; не требуется «две Work» автоматически.
- AI предложил несуществующий `scenario_id` — admission отклоняет; свободная формулировка не становится доверенной capability.
- У пользователя отозвали право во время ожидания approval — до effect проверяется current grant; прежний approval не обязателен к исполнению.
- Plan собран с snapshot A, публикация стала B до старта — соответствие freshness policy проверяется перед effect; silent A→B swap запрещён.
- Два workers получили один job из-за сетевой задержки — fencing и conditional commit допускают одного canonical publisher; второй не подтверждает свою запись.
- Remote link пропала, host healthy — отображается `client_disconnected`, а не `Run failed`.
- Работа требует человеческой аналитической оценки; Run successful, Work `AWAITING_REVIEW` до решения потребителя.

---

## 18. Строгие системные инварианты темы 04

| ID | Invariant | Проверка |
|---|---|---|
| **EX-01** | Все способы инициирования используют один admission/execution contract | same Scenario human/automation/AI creates comparable Run graph |
| **EX-02** | Work переживает любой отдельный Run/Attempt и клиентский процесс | close window, restart, open second client |
| **EX-03** | `Definition`, `Invocation`, `Binding`, `Plan`, `Run` имеют разные identities | same operation ID with two snapshots yields distinguishable runs |
| **EX-04** | План после admission immutable/explicitly versioned | mutate presets/source, old plan digest stays |
| **EX-05** | Один Job/Run имеет ровно один committed terminal receipt | concurrent complete/cancel tests |
| **EX-06** | Request cancel ≠ terminal cancelled | cancel while worker finishing must preserve truth |
| **EX-07** | Failure to contact backend ≠ failed business effect | timeout-after-commit fault injection |
| **EX-08** | `OUTCOME_UNKNOWN` блокирует unsafe auto retry до reconciliation | kill after publish before ACK |
| **EX-09** | Повтор command с тем же idempotency key не порождает второй эффект | duplicated submit, connection loss |
| **EX-10** | Two conflicting writers cannot both claim authoritative artifact publication | fencing/conditional commit |
| **EX-11** | Дедуп допустим по semantic equivalence, не имени действия | same op+different destination stays separate |
| **EX-12** | Domain Result и acceptance Work независимы от success Job | successful export but invalid comparison |
| **EX-13** | Каждый published Artifact связан с producer Run/OperationRun и provenance | inspect manifest and linkage |
| **EX-14** | Чат и UI не являются Work/Job authority | multi-client consistency |
| **EX-15** | AppDock Node/process health не заменяет outcome Strategy Box | healthy host and failed job; crashed host and succeeded committed job |
| **EX-16** | `FAILED`, `EMPTY`, `NOT_FOUND`, `PERMISSION_DENIED`, `UNKNOWN` различаются | mocked transport/server errors |
| **EX-17** | Никакие эффекты не происходят до authorization/approval relevant scope | revoked grant and expired approval |
| **EX-18** | При аварии частичный unverified artifact не публикуется как complete | kill during Excel write |
| **EX-19** | Automation disabled не отменяет running Job без control command | disable during execution |
| **EX-20** | External/AI consumers не получают обходной unrestricted execution path | machine API authorization test |
| **EX-21** | Ошибка одного Job не стирает исторические артефакты другой Run | retry/new run history |
| **EX-22** | Текущий busy indicator зависит от общих resources, не от количества окон | two nonconflicting readers concurrently |
| **EX-23** | Выполнение тяжёлого Job не блокирует отзывчивость клиента | UI event loop independence |
| **EX-24** | Все committed transitions имеют causal sequence и видны после reconnect | snapshot+cursor replay |
| **EX-25** | Возобновление использует checkpoint и версионные входы, а не произвольный повтор всей процедуры | restart with changed SourceSnapshot |

**Уровень статуса:** EX-01–25 — консолидированные **целевые инварианты/критерии**, **не** утверждение о текущем соблюдении.

---

## 19. Conflict & superseded register

| ID | Источники / тезисы | Суть конфликта | Консолидированное разрешение | Статус |
|---|---|---|---|---|
| **C01** | Ранние `Command → Scenario → Cascade` vs тема 02 `Operation → Scenario/Scheme` | Обязательный global Command Registry vs domain operation contracts | `OperationDefinition` — каноническая внешняя способность; low-level command остаётся implementation detail при необходимости | **CONSOLIDATED; API OPEN** |
| **C02** | `Case` как главный факт выполнения vs `Work/Run/Job` | один объект одновременно цель, запуск и карточка | Work/Run/Job как semantic truth; Case по умолчанию projection текущего клиента | **CONSOLIDATED; Case persistence UNKNOWN** |
| **C03** | Каскад отдельный engine vs Scheme composition | дублирование одного DAG исполнителя | Cascade — user/product view над Scheme/Scenario до доказательства уникального lifecycle | **CONSOLIDATED; отдельный definition UNKNOWN** |
| **C04** | Scenario-first UX vs Thread/Work-first UX | какой объект должен владеть историей работы | Scenario — reusable catalogue, Work — конкретная цель, Thread — discussion context; UI может делать scenario-first launcher | **resolved as different levels** |
| **C05** | `ScenarioKind.background` vs background execution policy | background как предметный тип | execution mode + AutomationSpec, один engine | **SUPERSEDED target** |
| **C06** | Qt `ScenarioCoordinator` vs headless runtime | GUI может быть executor authority? | current Qt — прототип; target long-lived headless application owner | **CURRENT/TARGET distinction** |
| **C07** | AppDock scheduler vs Strategy Box scheduler | кто владеет бизнес-расписанием | Strategy Box — automation/domain occurrences; AppDock — node/service lifecycle | **CONSOLIDATED** |
| **C08** | `stratbox-core` vs `stratbox-host` как repo/package | разные физические реализации одной роли | сначала platform-neutral application responsibility и interface, topology/название позже | **physical UNKNOWN** |
| **C09** | Retry на HTTP, Command, Scenario, Job | nested multiplicative attempts | один governing budget на effect boundary; lower retries scoped | **CONSOLIDATED** |
| **C10** | Job success = finished Work | execution vs acceptance | independent outcome/assessment/closure | **CONSOLIDATED** |
| **C11** | Remote timeout = failed action | неизвестный effect после потери связи | `OUTCOME_UNKNOWN` + reconciliation, no blind retry | **CONSOLIDATED** |
| **C12** | Local JSON history vs node truth | доступность текущего desktop cache vs durable collaboration | JSON остаётся projection/dev convenience; authoritative state transactional | **CONSOLIDATED; storage choice UNKNOWN** |
| **C13** | Source snapshot latest during run vs sealed plan | «самое новое» может изменить входы в середине выполнения | immutable effective source/version refs, explicit replan/new Run | **CONSOLIDATED** |
| **C14** | Один AgentRun как параллельный engine | AI обходит разрешённые операции | AI actor может создавать Work/Plans, но всё исполняется canonical JobManager | **CONSOLIDATED** |
| **C15** | Один Run = одна Job vs DAG jobs | стоимость модели и гибкость размещения | semantic Run↔many Job; реализация 1:1 допустима в простом случае | **CONSOLIDATED; decomposition policy OPEN** |
| **C16** | `TERMINAL(OUTCOME_UNKNOWN)` vs later successful reconciliation | можно ли переписать terminal историю? | сохранить initial observed terminal receipt, добавить reconciliation assessment/aggregate outcome; не стирать прошлую неопределённость | **TARGET-HYPOTHESIS; lifecycle semantics OPEN** |

### 19.1. Устаревшие направления, которые не следует возвращать

**SUPERSEDED:** пользовательский GUI внутри доменного `stratbox`; launcher/Windows как самостоятельный universal lifecycle owner; `background` как отдельная бизнес-логика; автоматическое превращение каждой технической функции в пользовательский Scenario; чат как единственный persistent container выполнения; «один Qt-worker» как узловая гарантия; автоматическое превращение технического `success` в accepted Knowledge/Work; отдельный AI-only catalogue и shell-модель как главный интерфейс агента.

Исторические заметки сохраняют ценность как происхождение UI сценариев, идеи launcher и ранней структуры команд. Они **не** опровергают текущую границу core/application/AppDock и не должны использоваться как current implementation evidence.

---

## 20. UNKNOWN / локальные белые пятна и программа верификации

| ID | Приоритет | Открытый вопрос | Почему корпус не закрывает | Минимальный способ решить |
|---|---|---|---|---|
| **U01** | P0 | Когда intent становится durable Work? | «каждая команда» создаёт шум, «только long running» теряет обещания | admission pilot: one-off, report, monitor, approval |
| **U02** | P0 | Нужно ли материализовать Run отдельно от Job в маленьком сценарии? | смысл различим, physical overhead неизвестен | implement 1-op + 2-job DAG, оценить query/UX complexity |
| **U03** | P0 | Как granularity Job связана с OperationRun и backend lease? | допустим whole fragment vs leaf task | двухпотребительский DAG + isolated worker crash |
| **U04** | P0 | Особая durable роль Case? | current Case смешивает уровни; иных contracts нет | mapping current fields to Work/Run projection, UX test |
| **U05** | P0 | Terminal outcome + reconciliation после unknown | immutability receipt vs evolving knowledge | timeout-after-commit fault injection, review schema |
| **U06** | P0 | Кто autorizes и хранит Approval конкретного effect? | AppDock identity, Strategy Box product policy, external provider | approval expiration/revoke/scope integration test |
| **U07** | P0 | При crash/lease expiry как подтвердить отсутствие старого worker? | heartbeat alone недостаточен | process isolation, fencing test, forced delay |
| **U08** | P0 | Реальный safe resume для каждого домена | checkpoints и idempotency различаются | collector + FRG + SORS resume matrix |
| **U09** | P1 | Как Work closure различает accepted, completed, withdrawn? | нет Product policy на разные классы аналитики | 3 acceptance profiles with human review |
| **U10** | P1 | Freshness/rebind после ожидания в очереди | plan sealed, но sources и grants меняются | update snapshot/revoke grant before job claim |
| **U11** | P1 | Какие steps безопасно дедуплицировать между Runs? | equivalence/permission boundary нет | two scenario sources + distinct destination tests |
| **U12** | P1 | Планирование динамической схемы во время AI reasoning | plan epochs / dynamic loops не проработаны | bounded adaptive scheme 2-step pilot |
| **U13** | P1 | Node-wide fairness, priorities, quotas | workload unknown | profile workloads + load/reliability budget |
| **U14** | P1 | SQLite vs Postgres и хранение event journal | требуются реальные concurrency/recovery metrics | single-node SQLite WAL pilot; multi-host benchmark if needed |
| **U15** | P1 | Exact host API, local IPC, AppDock service boundary | внешний owner/contract evolution | formal contract negotiation and E2E activation |
| **U16** | P1 | Полномочия multi-user cancellation/retry/approve | permission matrix нет | role-based tests + audit |
| **U17** | P1 | Scheduler recurrence, misfires, source watcher debouncing | нет operating history и выбранных calendars | timezone DST tests + week-offline recovery |
| **U18** | P1 | Artifact publication и immutable refs | result/materialization различены, physical commit открыт | stage/verify/publish fault test |
| **U19** | P2 | Русский UI: Работа / Задача / Запуск / Кейс | термины семантически шире пользовательских | 5–10 usability probes on case/Run card |
| **U20** | P2 | Нужен ли глобальный низкоуровневый Command registry | возможная оптимизация, нет consumer proof | start with op + internal step descriptors |
| **U21** | P2 | Какие категории machine schemes нужны физически | dynamic graph DSL не проверен | one op + composite + reused subgraph |
| **U22** | P2 | Нужен ли отдельный распределённый workflow engine | workload предполагает, но не доказывает | compare self-contained host, Celery, Temporal with real SLA |
| **U23** | P2 | Что делать с live Job при отключении Automation | research suggests continue; UX policy not decided | explicit user test on disable vs cancel |
| **U24** | P2 | Cross-node run migration, multi-host failover | модель узла ещё single-authority | defer until single-node durable engine stable |

**Что нельзя закрывать догадкой:** exact state enums, БД, названия repos, worker topology, globally guaranteed resume, distributed exactly once, automatic AI work acceptance и универсальную cancellation every operation. Исследовательская модель определяет **контракты**, их физический носитель требует инженерной проверки.

---
## 21. Candidate target contracts: компактная модель без лишней платформы

### 21.1. Обязательное семантическое ядро

```yaml
# TARGET CONTRACT EXAMPLE — поля/версии иллюстративны
work:
  work_id: work:...
  revision: 3
  purpose: 'Собрать отчёт по отраслевому кредитованию'
  origin_refs: [message:...]
  requester_principal: principal:...
  requirements_ref: work-requirements:...
  acceptance_profile: review_required
  work_state: awaiting_review
  run_refs: [run:R1]

run:
  run_id: run:R1
  work_id: work:...
  origin: human
  plan_ref: plan:P1
  binding_ref: binding:B1
  effective_params_ref: params:Q1
  source_snapshot_refs: [snapshot:CBR-1]
  lifecycle: terminal
  execution_outcome: succeeded
  result_refs: [result:X1]
  artifact_refs: [artifact:A1]
  assurance_ref: assessment:...

plan:
  plan_id: plan:P1
  plan_version: 1
  plan_digest: sha256:...
  scheme_ref: scheme:industry-report@2
  operation_invocations: [invocation:I1, invocation:I2]
  dependency_edges: ['I1 -> I2']
  resource_claims: [storage:report-output]
  effect_summary: [publish_artifact]
  approval_requirements: []
  frozen_bindings_ref: binding:B1

job:
  job_id: job:J1
  run_id: run:R1
  plan_fragment_ref: plan-fragment:F1
  lifecycle: terminal
  terminal_outcome: succeeded
  lease_generation: 7
  operation_run_refs: [operation-run:O1, operation-run:O2]

operation_run:
  operation_run_id: operation-run:O1
  job_id: job:J1
  operation_definition_ref: operation:source.fetch@1
  invocation_ref: invocation:I1
  attempt_refs: [attempt:T1]
  domain_result_ref: source-snapshot:CBR-1
  effect_receipt_refs: []

attempt:
  attempt_id: attempt:T1
  operation_run_id: operation-run:O1
  started_at: 2026-10-09T10:00:00Z
  terminal_observation: succeeded
  worker_ref: worker:local-1
  lease_generation: 7
```

**Почему это не обязательно шесть SQL-таблиц в v1.** Семантические поля позволяют дать адресуемые IDs и causal links. Физическая модель вправе вложить короткий Job/Attempt в один durable aggregate при том условии, что recovery/queries и state transitions остаются корректными. Нельзя экономить на audit identity/effect receipts там, где последствия уже реальны.

### 21.2. Operation metadata: лишь реально использующиеся поля

```yaml
# TARGET EXAMPLE
operation_id: frg.cleanup.apply
semantic_version: 1
input_schema_ref: schema:frg-cleanup-plan
output_schema_ref: schema:cleanup-result
applicability:
  requires_approved_plan: true
effects:
  kind: destructive
  scope: declared_plan_targets
  supports_dry_run: true
retry:
  automatic: false
cancel:
  mode: safe_points
resources:
  locks: [destination_namespace]
assurance:
  postconditions: [plan_targets_only, verified_survivors]
```

Для read-only операции намного более короткий descriptor достаточен; общий contract допускает profile-specific поля. Схемы именования/validation и точные wire enums принадлежат последующей спецификации.

### 21.3. Outcome envelope

```yaml
# TARGET EXAMPLE; success is NOT accepted knowledge
execution:
  lifecycle: terminal
  outcome: partial
  completed_required_nodes: 4
  failed_nodes: 1
  effect_receipt_refs: [effect:E1, effect:E2]
domain:
  result_refs: [result:X1]
  validity: qualified
  limitations: [source_missing_one_period]
work:
  acceptance: pending
  residual_requirement_refs: [requirement:period-2024]
operational:
  artifact_refs: [artifact:A1]
  problem_refs: [problem:P1]
  diagnostics_refs: [diagnostic:D1]
  provenance_ref: provenance:R1
```

Вариант `outcome=partial` не должен автоматически удовлетворять Work без явной политики. Каждая неуспешная часть остаётся в evidence ledger.

### 21.4. Предлагаемые контролируемые service methods

| Group | Methods / messages | Предел ответственности |
|---|---|---|
| Work | `propose_work`, `admit_work`, `get_work`, `list_work`, `update_requirements`, `accept_work`, `close_work` | цель/обязательства |
| Planning | `preview_plan`, `validate_plan`, `seal_plan`, `get_plan` | graph/preflight/immutable plan |
| Execution | `submit_run`, `get_run`, `list_jobs`, `cancel_run`, `retry_attempt`, `resume_run`, `reconcile_job` | durable runs/jobs |
| Observability | `get_snapshot`, `subscribe_events(cursor)`, `get_diagnostics` | authorized projections |
| Artifacts | `list_run_artifacts`, `get_artifact_manifest`, `materialize_artifact` | refs and safe materializations |
| Automation | `create_automation`, `enable_automation`, `list_occurrences`, `delete_automation` | triggers/recurrences |

`preview_plan` не гарантирует последующее admission: resources, source freshness, credentials и grants могли измениться. `seal_plan` перепроверяет critical preconditions и сохраняет exact binding snapshot. Во всех mutating methods нужны `principal`, `idempotency_key` и/или `expected_revision` по смыслу действия.

---

## 22. Implementation roadmap: вертикальными срезами, без обязательной legacy-совместимости

### Stage 0 — semantics и текущий baseline (P0)

1. Принять единое значение Work/Run/Job/OperationRun/Attempt, definitions/bindings/plan и отдельные axes `execution_outcome / domain_qualification / work_acceptance`.
2. Устранить version/contract drift `stratbox` ↔ `stratbox-windows`, синхронизировать manifest/tests/docs, очистить generated runtime state. Это независимая инженерная hygiene-задача.
3. Инвентаризировать **действующие** core use cases, typed requests/results, effect classes, idempotency/cancel safety и ресурсные требования.
4. Формализовать invariants EX-01–25 и code-owned contract tests, прежде чем переносить UI состояния.

**Exit:** один читаемый semantic contract, один inventory существующих capabilities, current vs target clearly separated.

### Stage 1 — headless local execution vertical slice (P0)

1. Реализовать platform-neutral `ExecutionService`, минимальные `Work`/`Run`/`Job` aggregate, typed command/response и durable event log.
2. Выделить Qt-сигналы и `ScenarioCoordinator` в клиентский adapter; удалить Qt imports из application composition.
3. Запустить **один** реальный core Scenario через headless worker в локальной managed среде, со stable IDs/Plan snapshot/Result envelope.
4. Сохранять immutable effective params, provisional artifact refs и terminal receipt в транзакционном storage.
5. Подключить Windows как client snapshot+events. Закрыть окно, открыть — получить тот же статус и историю.

**Exit tests:** EX-01/02/03/04/05/14/23/24 на одном read-only domain и одном export.

### Stage 2 — effect-safe workflow pilot (P0)

1. Ввести простой Scheme/DAG planner: две ветви, одно общее source acquisition, независимые exports.
2. Добавить bounded concurrency, resource locks, one governing retry budget, cooperative cancel и staging/atomic artifact publication.
3. Проверить `OUTCOME_UNKNOWN`, timeout-after-commit, idempotency collisions и reconciliation.
4. Реализовать `plan/apply` для одного согласуемого destructive use case (FRG как естественный кандидат) с неизменяемым effect scope.

**Exit tests:** EX-06–13/16–18/25, crash injection before/after publish.

### Stage 3 — durable automation и node-wide shared execution (P1)

1. Добавить AutomationSpec/TriggerOccurrence, календарные time zones/misfires и уникальную occurrence identity.
2. Включить JobManager для нескольких clients на одном Node, отдельные worker leases/fencing и устойчивые queues.
3. Настроить health/readiness/ProblemRef boundary с AppDock, необходимые file logs/support data и monitoring.
4. Ввести task center и безопасные per-user projections, permissioned control, notification/read cursor.

**Exit tests:** два клиента, два разрешённых параллельных read-only jobs; один конфликтующий writer; reboot; week-offline recurring schedule; revoke permission.

### Stage 4 — richer Work и machine/remote integration (P1/P2)

1. Добавить WorkCandidate с human/automation/API/AI admission, review/acceptance, reopen, residual tasks.
2. Позволить одной Work иметь несколько Runs и один Thread — несколько Works.
3. Реализовать versioned machine plan proposals (без отдельного executor), effect approvals и dynamic plan boundary.
4. Подключить remote backend после подтверждения AppDock host contract и отказоустойчивой локальной реализации.
5. Оценить Web/Android client projections, shared semantic models и supportable API compatibility.

**Exit:** одинаковый user-visible Work/Run/Artifact graph при Desktop/Web/Android и machine initiated execution без обходного SDK.

### Принцип миграции

Обратная совместимость ради старого `ScenarioKind`, `Case`-хранилища или handler ref ABI **не требуется**. Лучше прямо заменить концептуально неверные contracts и refactor Windows runtime. Однако **сохранность пользовательских фактических данных** и возможность экспортировать существующую историю не равны обратной совместимости API: если в реальных установках уже есть ценные данные, перед обновлением нужен разовый migration/export plan и backup.

---

## 23. Verification plan и критерии принятия выводов

### 23.1. Unit/property tests

- Work admission threshold: четыре разных источника Intent; rejected pre-admission без фиктивного worker;
- FSM transitions: запрещённые скачки, единственность terminal, отсутствие late cancel rewrite;
- plan canonicalization/version digests, циклы DAG, applicability и parameter type validation;
- equivalence/reuse: один источник для двух потребителей, два разных destinations не dedup;
- retry budget, timeouts, backoff, effect class, idempotency collision with changed payload;
- trigger DST, missing hour, repeated hour, timezone revisions, misfire/coalescing;
- provenance preservation: source snapshot/registry/binding revisions and artifact manifest;
- property tests: terminal monotonicity, no unauthorized effect, no false `SUCCEEDED` on validation failure.

### 23.2. Integration tests

- UI reconnect после logout/window close; один Run/Job сохраняет identity;
- два clients: optimistic concurrency, permission filtering, duplicate command submission;
- one-Node queue: parallel read operations and serial writer to shared destination;
- source unavailable vs empty valid dataset vs `NOT_FOUND` vs auth denied;
- stage→verify→publish и stable artifact links under failed export;
- approved cleanup execute with changed plan digest; must refuse stale approval;
- operation log + structured execution events + AppDock ProblemRef correlation;
- incompatible provider capability version must refuse activation before effect.

### 23.3. Fault-injection and chaos tests

| Injection | Ожидаемое наблюдение |
|---|---|
| kill before Job claim | Job remains queued and reschedulable |
| kill while read-only operation | safe new Attempt within budget |
| kill during staging | artifact absent as complete; staging retained/cleaned by policy |
| drop ACK after publish | `OUTCOME_UNKNOWN` then reconciliation, no blind duplicate publish |
| stale worker still alive after lease expiry | cannot publish with stale generation to managed target |
| corrupt case/event storage | diagnosable corruption/repair path; never silently empty history |
| disk full during DB transition | no half-admitted Run/Job; retry consistent |
| revoke permission while queued | effect permission recheck blocks action |
| client disconnect during long operation | host continues, client reconnects to same run |
| disable automation while job running | no new occurrences; existing Job changes only via separate cancellation |
| scheduler down for a week | bounded catch-up/skip according to policy, visible skipped occurrences |
| cancel vs success race | exactly one terminal receipt, late command says already_terminal |

### 23.4. Воспроизводимые real-data acceptance cases

**A.** `escrow.history.export`: документированная история source snapshots, периодов, statuses и артефактов. **B.** `cbr_file_collector`: partial download, 41-source catalog, cancellation between files, no false completeness. **C.** FRG: `scan → cleanup plan → approval → apply`, precondition changed and partial failure. **D.** SORS restoration: verified input/registry version identity, expensive computation resource budget, `OUTCOME_UNKNOWN` only on external effect, source-preserving evidence unchanged by orchestration.

Разные домены проверяют разные dimensions: простая загрузка не докажет корректность долгих расчетов; сложная математическая subsystem не докажет идемпотентность публикации файла.

### 23.5. Nonfunctional budgets и критерии качества

До реальных нагрузочных тестов точные цифры CPU/RAM/latency/p95 и storage retention **UNKNOWN**. Однако измеряемость должна появиться сразу: queue wait, admission p95, job startup overhead, worker memory peak, bytes downloaded, job cancellation latency at safe point, recovery duration, stuck `RUNNING` count, unknown-outcome backlog, source rate-limit errors, artifact verification failures, reconciliation lead time. Значение «0 unknown» не является обязательным качеством: качество определяется **правильной классификацией неизвестного и его разрешением**, а не сокрытием состояния.

### 23.6. Acceptance gate для утверждения архитектуры

Считать модель темы 04 готовой к переносу в Product только после доказательства, что:

1. короткий и составной scenarios работают через **один** headless execution service;
2. Run/Job переживает GUI restart и имеет единственный authoritative history;
3. взаимоисключающие ресурсные эффекты сериализуются на узле;
4. при timeout after commit нет ложного `failed` и unsafe повторения;
5. при cancellation нет ложного rollback и неправильной terminal attribution;
6. пользователь отличает execution success от accepted analytical result;
7. versioned plan/source identity и artifacts можно восстановить из manifest/events;
8. machine/automation/GUI инициаторы используют те же validation/authorization rules.

---

## 24. Source ledger и provenance

Ниже **открытые публичные ссылки** на материалы, из которых получены существенные смысловые выводы. Указанные «source of proposition» и «implementation truth» — разные уровни доказательности. В итоговом файле сознательно отсутствуют внутренние сведения и устройство закрытых корпоративных расширений.

### 24.1. Контроль третьей ветки

| Source | Что подтверждает | Статус использования |
|---|---|---|
| [Программа третьей ветки](https://github.com/ForestTiger-GH/stratbox/blob/6c3714078791eabd64927b143aa1e5f4a76f9b88/_mw/epochs-001-strategy-box-development/research/strategy_box_03_consolidation_research_program.md) | scope 04, общий spine, классификация Current/Target/UNKNOWN | framework |
| [README `03-consolidation-research`](https://github.com/ForestTiger-GH/stratbox/blob/6c3714078791eabd64927b143aa1e5f4a76f9b88/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/README.md) | research ≠ Product Decision; public/private/owner discipline | methodological boundary |
| [Тема 00 — Corpus Map](https://github.com/ForestTiger-GH/stratbox/blob/6c3714078791eabd64927b143aa1e5f4a76f9b88/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_00_corpus_map_open_questions_2026-10-08.md) | пересечения, конфликты scheduler/Case/Job/Command, неразрешённые вопросы | consolidation baseline |
| [Тема 01 — System Model](https://github.com/ForestTiger-GH/stratbox/blob/6c3714078791eabd64927b143aa1e5f4a76f9b88/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_01_System_Model_consolidated_research_2026-10-08.md) | ownership, AppDock boundary, durable runtime, one execution spine | consolidated proposition |
| [Тема 02 — Canonical Semantic Model](https://github.com/ForestTiger-GH/stratbox/blob/6c3714078791eabd64927b143aa1e5f4a76f9b88/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_02_canonical_semantic_model_2026-10-08.md) | Work/Run/Job/OperationRun/Attempt definitions, Scenario/Scheme/Cascade, outcome/acceptance distinctions | semantic authority for this research |
| [Тема 03 — Data → Knowledge](https://github.com/ForestTiger-GH/stratbox/blob/6c3714078791eabd64927b143aa1e5f4a76f9b88/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_03_data_to_knowledge_consolidated_research_2026-10-08.md) | SourceSnapshot/DatasetVersion, AnalyticalResult, Artifact provenance/commit/currentness | cross-topic control |

### 24.2. Основной `02-base-study` execution corpus

| Source | Существенная фактическая/исследовательская роль | Использовано в разделах |
|---|---|---|
| [Команды, сценарии, каскады](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md) | first planner/DAG/dedup/resource/retry proposal; исходный конфликт Command/Cascade | §§3,5,8,9,19 |
| [Execution control / user path](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_execution_control_user_path_research_2026-10-07.md) | typed control commands, cancellation, parameter resolution, revision, permission, retry vs resume | §§4,6,7,9,14 |
| [Фоновые задачи и процессы](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md) | automation trigger, misfire, Job FSM, leases/fencing, recovery, shared task center | §§6,8,10,11,16,18 |
| [Автоматизация и ИИ](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md) | source/event watchers, bounded AI, idempotency, budgets, agent tool boundary | §§4,5,9,11 |
| [Observability/errors/logs](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_observability_errors_logs_research_2026-10-07.md) | structured progress, problems, client observability, safe aggregation, crash evidence | §§7,13 |
| [Многопользовательский узел](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md) | node-wide authority, queue, presence/read cursors, permissions, resource conflicts | §§8,13–16 |
| [Web/self-hosted](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md) | headless host, API/IPC, idempotency, optimistic concurrency, disconnect behaviour | §§7,10,14–16 |
| [Business logic / Machine Schemes](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_logic_machine_schemes_architecture_research_2026-10-07.md) | Definition/Invocation/Plan/Run, semantic capability, effects, composition | §§3,5,21 |
| [Machine capability readiness](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md) | applicability, frame conditions, scheme/adaptive execution, assurance envelope | §§5,11 |
| [Chat / Work / schemes](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_chat_work_schemes_ui_research_2026-10-07.md) | Thread↔Work, Work↔Runs, parallel independent cognitive activations, artifacts | §§3,4,11,14,16 |
| [Core целевая архитектура](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_target_core_design_architecture_2026-10-07.md) | первоначальная физическая гипотеза application runtime; ее нельзя объявлять решённой | §§15,19 |
| [Текущее `stratbox`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_base_study_current_state_2026-10-06.md) | core domain facts, Request/Result, тестовый maturity, operation catalogue gap | §§2,17,23 |
| [Текущее Windows](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md) | actual Qt execution, cases, background scaffold, local history | §§2,3,16 |
| [File/artifact layer](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md) | artifact manifest, staging, lineage, result/file distinction | §§9,12 |
| [Source/registry governance](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_registry_source_governance_research_2026-10-07.md) | snapshots/freshness/source validity effect on plan | §§4,5,10,17 |
| [Portability/reuse of business segments](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_segments_portability_reuse_architecture_research_2026-10-07.md) | direct-core headless use, reusable logic vs orchestration | §§2,3,15 |

### 24.3. Прямой implementation evidence

| Исходник | Подтверждаемый факт |
|---|---|
| [`scenarios/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/models.py) | `ScenarioKind`, steps и error policy |
| [`scenarios/registry.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/registry.py) | auto-wrapping operations, composite CBR update |
| [`scenarios/runner.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) | sequence/step events, results/logs/artifacts, fail-fast |
| [`operations/execution/runner.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/execution/runner.py) | handler dispatch and per-operation log |
| [`cases/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/cases/models.py) | combined current case model |
| [`scenario_coordinator.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) | Qt QThread, single busy guard |
| [`runtime/bootstrap.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py) | Qt import in application runtime composition |
| [`background/store.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/store.py) | in-memory enabled/status flags, no scheduler |
| [`history/persistence.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) | five JSON snapshots, non-atomic saves, silent load failure |
| [`Windows repo HEAD`](https://github.com/ForestTiger-GH/stratbox-windows/commit/959e9c4ce1441124af5111c1e025041714e04d3b) | inspected source revision |
| [`Core repo HEAD`](https://github.com/ForestTiger-GH/stratbox/commit/6c3714078791eabd64927b143aa1e5f4a76f9b88) | new research corpus, unchanged executable core vs earlier checked baseline |

### 24.4. Внешние references: аналогии, а не заимствованные Product Decisions

- [OpenTelemetry Semantic Conventions — Events](https://opentelemetry.io/docs/specs/semconv/general/events/) — одноразовые события, causality/correlation и различие event/span.
- [OpenTelemetry — Trace](https://opentelemetry.io/docs/specs/semconv/general/trace/) — spans/operations для observability.
- [Temporal — Tasks](https://docs.temporal.io/tasks) — workflow event history, replay и separation workflow task/activity; демонстрирует требования к durable orchestration.
- [AWS Durable Execution — Idempotency and retries](https://docs.aws.amazon.com/durable-execution/patterns/best-practices/idempotency/) — retries, at-most/at-least-once и пределы exactly-once effect.
- [SQLite — WAL](https://www.sqlite.org/wal.html) — возможная технологическая основа single-node durable state, **не решение** о БД.
- [RFC 5545 iCalendar](https://www.rfc-editor.org/rfc/rfc5545) — recurrence и временная семантика.

### 24.5. Provenance matrix: самое важное по источникам

| Вывод | Источниковая опора | Доказательность |
|---|---|---|
| Текущий сценарий sequential и Qt-bound | конкретные Windows `runner`, `coordinator`, `bootstrap`, `history` | **CURRENT — direct code** |
| Work/Run/Job раздельны | Topic 02 §§6, 14, 18; Topic 01 §§5,9 | **CONSOLIDATED semantics** |
| `Case` лучше сначала трактовать как projection | Topic 02 §6.8, Topic 00 conflict C3, Windows model | **CONSOLIDATED direction; physical choice UNKNOWN** |
| One headless execution spine | Topic 01 §§9,21, Topic 02 §6; background study | **CONSOLIDATED target** |
| Планирование и dedup по эффектам | commands/scenarios study §§15–30; Machine Scheme/Capability studies | **TARGET-HYPOTHESIS with strong support** |
| Retry/cancel/unknown/reconciliation | execution control, background architecture, OTel/Temporal/AWS as references | **CONSOLIDATED requirement; implementation pending** |
| Scheduler принадлежит Strategy Box, host lifecycle — AppDock | Topic 01 §§6,9,15,23; background & web studies | **CONSOLIDATED ownership** |
| Result и accepted Work различны | Topic 02 §§7,14; Topic 03 §§8–10 | **CONSOLIDATED semantic distinction** |
| State storage must be transactional | Windows current history code; multi-user/background/web studies | **CONSOLIDATED target; DB UNKNOWN** |
| Exact physical repository topology/contract | Topic 01 §§9,20,24; target core design proposal | **UNKNOWN / external dependency** |

---

## 25. Decision / Gap Register темы 04

| Объект | Рекомендуемое состояние после консолидации | Следующий action/owner |
|---|---|---|
| Единый Work → Run → Job → OperationRun → Attempt spine | **устойчивый консолидированный вывод** | application contract owner |
| Отдельность execution/domain/acceptance outcomes | **устойчивый консолидированный вывод** | domain/result + application |
| Background/remote/AI как варианты инициирования/исполнения | **устойчивый консолидированный вывод** | application/runtime |
| Work admission threshold | **сильная целевая гипотеза; needs pilot** | application/Product UX |
| Case as projection, not durable root | **вероятная target direction** | Windows/application + UX |
| Cascade as profile of Scheme/Scenario | **вероятная target direction; unique definition UNKNOWN** | capability + application |
| Immutable plan/parameter/source binding | **целевой инвариант, высокий приоритет** | planner/domain provenance |
| JobManager/headless runtime | **устойчивый target owner; absent CURRENT** | application runtime |
| SQLite/PostgreSQL choice | **UNKNOWN, scope темы 05** | persistence owner |
| Effect receipts and reconciliation | **целевой инвариант, needs fault test** | executor/effect owner |
| Retry/cancel/timeout semantics | **консолидированные требования; not implemented** | operation/run owners |
| Source/data currentness before effects | **консолидированное требование, policy detail OPEN** | domain + planner |
| Product-specific scheduler vs AppDock lifecycle | **ownership resolved** | Strategy Box app + AppDock |
| Machine plan adaptation | **target proposal; external dependencies** | application/machine consumer |
| AppDock host API/service contract | **external dependency** | AppDock boundary owner |
| Windows GUI ↔ headless service transition | **P0 engineering gap** | Windows/application |
| Multi-client ACL/event stream | **P1 target, not CURRENT** | application/surface |
| Acceptance profile and residual obligations | **strong semantic requirement; policy OPEN** | Product/work owner |
| Distributed multi-node failover | **deferred** | future topology decision |

---

## 26. Заключение

**[CONSOLIDATED]** Strategy Box уже накопил необходимую предметную и UI-основу, но execution architecture сегодня ещё состоит из **локального последовательного runner** и набора исследованных, ещё не реализованных системных механизмов. Главный следующий шаг — создать **маленький, но действительно durable headless application runtime**, а не добавлять отдельные кнопки фоновой работы, новые виды сценариев или ещё один AI workflow engine.

Минимальная целевая формула:

```text
Work = смысловое обязательство
Run = конкретный эпизод его реализации
Plan = проверенный снимок графа и контекста
Job = управляемая исполняемая единица
OperationRun = наблюдаемый вызов предметной способности
Attempt = техническая попытка
ExecutionOutcome = фактический исход действия
AnalyticalResult = содержательно квалифицированный результат
Artifact = адресуемая публикация
Acceptance/Closure = доказанное удовлетворение обязательства
```

Порядок создания должен следовать доказательности: **semantic contracts → one headless local vertical slice → effect-safe retry/cancel/recovery → shared node scheduler/queue → human/AI/remote surfaces**. Это сохраняет ядро `stratbox` библиотечным, отделяет AppDock как владельца среды и превращает Windows/Android/Web в разные клиенты одной системы. Тема 04 тем самым формирует execution spine для будущего Whole-System Target Architecture, **не утверждая заранее новый набор репозиториев, движков и тяжёлой инфраструктуры**.

**Конечный исследовательский критерий:** пользователь, запустивший работу сегодня, должен завтра на другом клиенте без двусмысленности увидеть *что было поручено, почему и с какими полномочиями, какой точный план выполнялся, какие эффекты совершены или остались неизвестны, насколько доказателен результат и кто вправе считать работу завершённой*.
