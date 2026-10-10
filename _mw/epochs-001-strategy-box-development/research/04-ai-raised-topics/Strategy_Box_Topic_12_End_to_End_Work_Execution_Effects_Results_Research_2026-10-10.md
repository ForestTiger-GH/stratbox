# Тема 12. Сквозная семантика работы, исполнения, эффектов и результатов Strategy Box

**Дата:** 10 октября 2026 года  
**Тип:** самостоятельное межрепозиторное исследование / Research; **не** Product Decision, не Target WHAT/HOW, не задание на изменение реализации.  
**Статус выводов:** дифференцирован по меткам `CURRENT`, `CONSOLIDATED RESEARCH`, `TARGET HYPOTHESIS`, `CONFLICT`, `GAP`, `UNKNOWN`, `NOT APPLICABLE`.  
**Исследованные ветки:** `ForestTiger-GH/stratbox@main` (`928da3d768eb5932853a9035d683ed83a23f5c12`); `ForestTiger-GH/stratbox-windows@main` (`959e9c4ce1441124af5111c1e025041714e04d3b`); `ForestTiger-GH/MADAR@main` (`7029b47676659161d9f54b4def8f0c1aa979b614`); граница `ForestTiger-GH/AppDock@main` (`a4d87c643e620e54e04083d4d0b8d867513e7065`).  
**Действующая спецификация MADAR:** `spec/` (Editor's Draft, `manifest.yaml` `1.0.0-dev`); Stage 3 A1–A8 и B1–B9 — отдельные исследовательские входы, а не принятые нормы.  
**Изменения:** продуктовый код, репозитории, существующие исследования, документация и настройки не изменялись.  
**Граница раскрытия:** только публичные семантики и нейтральные контракты расширений; сведения о закрытых реализациях отсутствуют.

---

## 0. Итог исследования

**Основная находка — семантическая, а не инфраструктурная.** Для Strategy Box уже исследованы почти все важные части цепочки «запрос → работа → способность → план → выполнение → эффект → результат → доказательства → принятие → закрытие». Главный незакрытый разрыв — **единый способ устанавливать и долговременно подтверждать переходы между этими частями**. Нынешняя Windows-реализация склеивает их карточкой сценарного запуска и булевым `OperationResult.ok`; лучшие доменные подсистемы core, напротив, уже отделяют вычислительный результат и обоснованность аналитического вывода. Эти практики пока не образуют общую гарантию.

**CONSOLIDATED RESEARCH.** Целевой принцип: **долговременная подотчётность работы, воспроизводимый снимок решения о запуске, преимущественно прерываемое вычисление, контролируемые внешние эффекты и отдельная доказательная приёмка результата**. Удобная формула — `durable accounting / disposable computation / safe effects / bounded acceptance`. Она не означает автоматического возобновления всех вычислений, универсальных транзакций или обязательного выделенного сервера.

**Ключевое уточнение темы 12:** одной линейной state machine недостаточно. Нужны **несколько связанных осей истины**, с явными правилами, какие утверждения допустимы при их сочетании:

1. **Work truth:** что поручено, в каких пределах и при каких условиях может быть закрыто;
2. **execution truth:** что было допущено, действительно запущено, прервано, завершено;
3. **effect truth:** какие изменения во внешнем мире подтверждены, отклонены или остаются неопределёнными;
4. **analytical truth:** что вычислено, на каких исходных данных и насколько обоснован результат;
5. **artifact truth:** какие байты произведены, проверены, опубликованы, доступны потребителю;
6. **assessment / acceptance truth:** что оценено по каким критериям и кем принято;
7. **environment truth:** работоспособность среды AppDock, хранилища и worker-ресурсов; сама по себе ничего не доказывает о банковском расчёте.

**TARGET HYPOTHESIS.** Ввести **один логический application authority на область управляемых Work/Run/Job** и один маршрут исполнения для ручных, фоновых, машинных и будущих совместных запусков. Это может начинаться как модуль в существующей локальной поставке; физический процесс, выделенный пакет, БД, служба и имя репозитория остаются открытыми. Публичный Python-core продолжает работать напрямую без обязательного application service.

**Самый опасный путь:** по успешному завершению Python-handler или наличию `output_path` объявлять результат «созданным», внешнее действие «совершённым», а поручение «выполненным». Даже правильный математический расчёт не доказывает сохранность XLSX; успешное сохранение XLSX не доказывает корректность данных; отсутствие ответа на удалённое действие не доказывает отсутствие эффекта; завершённый Job не равен принятому Work.

**Рамка достаточности.** Для первого управляемого локального профиля можно обойтись *одним приложением, одним авторитетным писателем, небольшим долговременным журналом команд/переходов, проверяемыми снимками, строго размеченными эффектами, исполнительным интерфейсом и управляемой файловой публикацией*. Отдельный workflow engine, брокер сообщений, графовая БД, всеобщий event sourcing и распределённый координатор пока не обоснованы.

## 1. Метод, источники и границы утверждений

### 1.1. Холодный вход и свежесть

Осуществлены прямые чтения: `stratbox/AGENTS.md`, `_mw/AGENTS.md`, структура research 02/03/04, новые `docs/`, исследовательский корпус тем 01–11, `stratbox-windows` application/runtime/manifest, а также MADAR `AGENTS.md`, `spec/README.md`, `spec/manifest.yaml`, `consolidation/{STATE,BASELINE,ARCHITECTURE,PROCESS}.md`, Stage 3 `results/`, архитектурная записка 01.10.2026. Использован приложенный обзор AppDock. Исследования прочитаны тематически, а не механически перенесены в итог.

Прямые code probes охватили `stratbox-windows/application/scenarios/{models,runner}.py`, `operations/execution/runner.py`, `cases/models.py`, `artifacts/models.py`, `history/persistence.py`, `background/store.py`, `presentation/qt_desktop/scenario_coordinator.py`, `appdock/manifest.json`. Для core фактическая реконструкция опирается на независимый base-study, свежие исследования 01–11, поддерживаемые `docs/current-how` и сведения прямых implementation owners. Здесь **не** выполнялись запуск GUI, исполняемый интеграционный тест, реальная запись под отказом хранилища или E2E совместного узла. Доказанность CURRENT — статическая, с точной областью наблюдения.

Сверка `stratbox@beb3e484…` с текущим `stratbox@928da3d…` выявила два последующих коммита и 11 затронутых файлов, без изменений `src/`, `tests/`, `pyproject.toml` и `scripts/`; следовательно, новые Research-файлы не следует трактовать как новые runtime-гарантии. Для Windows `main` совпадает с указанным базовым срезом.

### 1.2. Приоритет источников

1. **Действующий implementation owner и его исполняемый код** — правда о существующем поведении.
2. **Действующая, явно статусная документация `docs/current-how/`** — ограниченный code-backed снимок; `docs/what`, `docs/how`, `docs/architecture`, `docs/ldd` имеют смешанные или кандидатные статусы.
3. **Консолидированные исследования** — согласованное объяснение/гипотеза, пока вне Product Authority.
4. **Исследования 04/01–11 и 02-base-study** — конкретные гипотезы, альтернативы и границы; противоречия разрешаются по области действия, а не голосованием.
5. **MADAR `spec/`** — действующая методологическая норма в своей области; Stage 3 — приоритетные входы будущей методологии, без автоматического превращения в требования Strategy Box.
6. **AppDock** — отдельный владелец платформенных контрактов, не источник предметных фактов об аналитическом результате.

### 1.3. Метки

| Метка | Смысл в этом документе |
|---|---|
| **CURRENT** | Кодом либо прямым действующим contract owner подтверждённое поведение в указанном срезе. |
| **CONSOLIDATED RESEARCH** | Повторно обоснованное согласованное исследовательское различение; пока без статуса принятого API/обязательства. |
| **TARGET HYPOTHESIS** | Предложенный механизм или конкретизация, нуждающаяся в принятии и проверке. |
| **CONFLICT** | Несовместимые смысловые обещания, контракты или способы трактовки; указывается масштаб конфликта. |
| **GAP** | Механизм, необходимый для определённой заявленной возможности, пока отсутствует. |
| **UNKNOWN** | Нет достаточного прямого испытания или Product Decision. |
| **NOT APPLICABLE** | Требование не активировано текущим deployment/capability-профилем. |

**Важно:** «исследовано достаточно» ≠ «утверждено» ≠ «реализовано» ≠ «проверено на авариях». Каждый вывод ниже сохраняет это различение.

## 2. CURRENT: реконструкция фактического пути пользователя

### 2.1. Исполняемая цепочка

```text
Пользователь выбирает ScenarioSpec и параметры
  → Qt ScenarioCoordinator.submit(...)
  → build_case_for_scenario(...) → ScenarioRunCase(status='prepared')
  → in-memory case store + signal `case_created`
  → QThread / ScenarioWorker
  → run_scenario(...): case.status='running', case_started event
  → линейный ScenarioStepRun: `running` → run_operation(...)
  → OperationSpec.resolve_params → OperationContext → dynamic handler
  → фактическая core-функция/внешний IO
  → OperationResult(ok, message, outputs, details)
  → step.status success/failed + per-operation log
  → ArtifactRecord.from_path(output) + artifact_created event
  → case.status success/failed + case event
  → in-memory stores → отдельные JSON projections при сохранении
  → UI chat, inspector, runtime-state projection AppDock
```

**CURRENT.** `ScenarioSpec` различает `atomic`, `composite`, `background`, `assignment`; реально исполняются автоматически созданные atomic и один линейный composite; остальные виды — главным образом scaffold. `ScenarioCoordinator` допускает один активный запуск и основан на Qt `QThread`. Кооперативной отмены с доказуемым последствием и долговременного диспетчера Job/Attempt нет.

**CURRENT.** `ScenarioRunCase` имеет статусы `prepared`, `queued`, `running`, `success`, `warning`, `failed`, `cancelled`, но статус в dataclass шире действительных ветвей исполнения. Step имеет `pending`, `running`, `success`, `warning`, `failed`, `skipped`; это уже различие *декларации* и *реализованных переходов*. `OperationResult.ok` редуцирует множество исходов к `True/False`.

**CURRENT.** `ArtifactRecord.from_path` присваивает новый UUID и определяет тип преимущественно по расширению или `Path.exists()`; **не** удостоверяет digest, полноту записи, безопасность публикации, видимость другим пользователям, независимую проверку содержания и durable catalog commit. Даже `unknown` kind не препятствует созданию записи об артефакте. `outputs` могут содержать путь operation log: лог и пользовательский продукт способны попасть в один общий набор путей.

**CURRENT.** `HistoryPersistenceService` хранит `cases.json`, `events.json`, `artifacts.json`, `logs.json`, `assignments.json` отдельными вызовами `Path.write_text`; чтение повреждённого файла возвращает `[]`. В методе отсутствуют межфайловая транзакция, версия commit-журнала, single-writer lock и подтверждённое восстановление исходного состояния после crash. Docstring честно называет хранилище *recent local context*, а не durable database.

**CURRENT.** Core `stratbox` обеспечивает нейтральную FileStore/IO-среду и предметные операции разных уровней зрелости: typed Request/Result и failures у ряда доменов; provenance/evidence-rich SORS; plan/apply у FRG. В нём нет обще-продуктового Work/Run/Job/Acceptance authority. Прямой Python API — самостоятельный законный consumer.

**CURRENT.** Windows manifest задаёт локальную foreground surface для Windows (`contract_version 4.0`, `launch_mode=foreground`, `locality=local`), а не headless worker или общий remote node. AppDock activation/session/runtime-state передаются и читаются, но эти проекции не делают AppDock владельцем аналитического Job. Декларированные presence и artifacts не доказывают готовности совместного backend.

### 2.2. Где теряется смысл

| Фактическое звено | Что оно сейчас знает | Чего не может доказать |
|---|---|---|
| Scenario choice | Определение UI-сценария и введённые параметры | Принятую долговечную Work, её критерии закрытия |
| `submit()` | Объект Case принят локальным coordinator | Durable admission, права перед эффектом, idempotency |
| `case_started` | Runner дошёл до вызова callback | Старт физической попытки на другом worker, сохранённость факта |
| `run_operation()` | Handler вернул Result либо выбросил exception | Что произошёл/не произошёл внешний эффект |
| `result.ok=True` | Handler сообщил успех по своему контракту | Полноту результата, независимую проверку, пользовательское принятие |
| `outputs=(path,)` | Handler назвал locator | Наличие, полноту, digest, финальную публикацию и доступность |
| `ArtifactRecord` | Метаданные от path | Доказанную materialization/commit, ACL |
| Event/log | Событие/строка/диагностика записаны | Самостоятельную истинность effect/assurance claim |
| Five JSONs | Последние проекции | Атомарность жизненного цикла и lossless восстановление |
| AppDock runtime-state | Состояние surface/сессии | Domain correctness, Work acceptance/closure |

### 2.3. Что уже хорошо и сохраняется

**CURRENT → DESIGN REUSE.** Сохранять предметную автономность core, декларативные `OperationSpec`/`ScenarioSpec` для UI, раздельные логи, семантический chat projector, проверку workspace/degraded mode, FRG plan/apply, типизированные domain failures и доказательную модель SORS. Тема 12 **не** рекомендует переписать эти решения в одну гигантскую модель. Речь о контрактном шве между ними.

## 3. Целевая семантическая карта без преждевременной физической онтологии

### 3.1. Плоскости и связи

```text
Thread(s) / Message(s) ───────────────┐
                                      │ контекст, требования, диалог
Intent / Request → WorkCandidate → [admission] → Work ──────────────┐
                                              │ purpose/criteria       │
                    Capability catalog         │                       │
OperationDefinition ─┐                         ▼                       │
ScenarioDefinition ──┼─→ selected definition / version → ExecutionPlan│
SchemeDefinition ────┘                                  │             │
                                                     Run ── Job(s)     │
                                                              │        │
                                                       OperationRun(s)  │
                                                              │        │
                                                         Attempt(s)     │
                                                           /     \      │
                                         computed Result /       \ EffectIntent
                                               │                     │
                                        Claim + Evidence         EffectReceipt
                                               │                     │
                                          Assessment           Materialization
                                               │                     │
                                        WorkResult ← Artifact ← Publish
                                               │
                                        Acceptance / Rejection
                                               │
                                    Closure + residual obligations
                                               │
                            Thread/UI projections, access-filtered views
```

Стрелки обозначают смысловые связи, **не** обязательный каталог классов/таблиц. Один execution event может хранить несколько идентификаторов; несколько логических сущностей могут жить внутри одного persisted record/aggregate. Обратные отношения допустимы (например, артефакт может участвовать в нескольких Work; Work может иметь несколько Threads), но authority каждого перехода должна оставаться единственной.

### 3.2. Минимальные различения

| Понятие | Уникальный вопрос | ID/версия | Физическая материализация |
|---|---|---|---|
| **Intent / WorkCandidate** | Что человек/автоматизация предлагает сделать? | request/correlation key | Может быть одноразовым DTO или записью review-очереди. |
| **Work** | За какой результат и остаток отвечаем? | `work_id`, criteria revision | Durable в управляемом профиле; отдельная сущность только если жизненный цикл шире одного Run. |
| **Thread** | Где обсуждается, спрашивается и показывается? | `thread_id`, message IDs | UI/conversation aggregate; один Thread может ссылаться на несколько Work и наоборот. |
| **Case** | Как показать одну историю случая пользователю? | В CURRENT `case_id` | UI projection; текущий `ScenarioRunCase` близок к Run-card; не новый обще-системный root. |
| **OperationDefinition** | Какая атомарная предметная способность доступна? | stable ID + semantic revision | Стабильный descriptor/facade в core; UI-параметры отдельно. |
| **ScenarioDefinition** | Какую курируемую задачу может выбрать пользователь? | stable ID + revision | Catalog/UI definition; атомарная обёртка Operation допустима. |
| **SchemeDefinition / Composition** | Как связаны способности и типизированные данные? | definition revision | Машинное представление *может совпадать* с Scenario definition; самостоятельный объект только при своём lifecycle. |
| **ExecutionPlan** | Что именно будет выполнено с какими версиями, параметрами, target/effects? | plan ID/digest/revision | Immutable snapshot, возможно поле Run, не обязательно отдельная таблица. |
| **Run** | Какой конкретный эпизод выполнения Work запросили? | `run_id` | Durable только там, где принято управляемое исполнение. |
| **Job** | Что можно поставить в очередь и выделить executor? | `job_id` | Может быть 1:1 с Run в простом случае; отдельный ID нужен при независимом планировании, ресурсах, правах. |
| **OperationRun** | Какое логическое invocation конкретной операции произошло внутри Run? | `operation_run_id` | Может быть вложенной записью Job/Run. |
| **Attempt** | Какая именно физическая попытка состоялась? | `attempt_id` | Каждая retry/worker takeover — новый occurrence, прежний исход сохраняется. |
| **EffectIntent / Receipt** | Какой внешний эффект разрешён и что о нём достоверно известно? | `effect_id`, scope/key | Durable до effect boundary; receipt с evidence, в том же журнале. |
| **AnalyticalResult / Claim** | Что аналитически получилось и что именно утверждается? | result digest, semantic context | Предметный результат core; не `bool ok`. |
| **Evidence / Assessment** | На чём основана проверка и что она подтверждает? | refs, evaluator, criteria version | Лёгкая ссылка для простого случая; развитый ledger для сложной математики. |
| **Artifact / Materialization** | Какой логический продукт создан и где его проверенные байты? | `artifact_id`, generation/digest | Manifest/catalog + locator, раздельные от bytes. |
| **Acceptance / Closure** | Кто согласился с результатом, и какие обязательства остаются? | actor/authority, criteria, revision | Durable решение или обоснованная диспозиция; может быть авто по заранее согласованным критериям. |

### 3.3. Кардинальности и защита от «сущностной инфляции»

- Один Work может иметь 0..N Runs; Run всегда имеет 1 Work в управляемом контуре. *Для прямого Python-вызова Work может вообще отсутствовать.*
- Один Run имеет 1 pinned plan; план может описывать один Job и одну OperationRun без отдельного графа. Nested/parallel Jobs возникают лишь при реальной независимости resource/scheduling/lifecycle.
- Одна OperationRun имеет 1..N Attempts при retry; каждый Attempt **новый факт**, а не изменение старого ID.
- Один Attempt может иметь 0..N effect intents; эффект может существовать и при failed/timed-out Attempt.
- Один AnalyticalResult может породить 0..N артефактов; один Artifact может иметь множество materializations/versions; публикация — отдельное подтверждаемое событие.
- Acceptance может быть ручной либо policy-bound автоматически, но это всегда *другое утверждение*, чем «worker окончил».
- Closure допускает `closed_with_residue`, `terminated_with_residue` или `blocked`, если критерии и полномочия позволяют; ложное `complete` запрещено.
- Не нужно вводить отдельные `Command`, `Cascade`, `Workflow`, `Scheme`, `Scenario`, `JobTask` как равноправные обязательные реестры только ради сохранения всех исторических слов. `Cascade` остаётся вариантом представления составного сценария; `Command` — форма invocation; `Scheme` может быть machine projection.

### 3.4. Два допустимых профиля применения одной логики

**P0 / библиотечный direct Python.** `request → core operation → typed domain result`; у вызывающего кода — контроль ошибок, файлов и повторов. `Work`, долговременный Run/Job, UI, журнал не обязательны (**NOT APPLICABLE**). При существенных файловых эффектах действуют те же контрактные требования honesty, provenance и storage adapter — даже без полноценного application authority.

**P1+ / управляемая работа.** `Work → immutable Run/Plan → Job/Attempt → result/effect/artifact → assessment/closure`. Идентификаторы и источники истины общие для desktop, background, permitted machine action, а при появлении P3 shared-node — для нескольких клиентов. Различается уровень гарантий размещения, не смысл статусов.

## 4. Состояния: семейство конечных автоматов и допустимые переходы

**CONSOLIDATED RESEARCH.** Один `status` с вариантами `running/success/failed` — слишком бедная модель. Но столь же неверен единый комбинаторный enum для всех 7 плоскостей. Предлагается небольшой набор state machines, связанных идентификаторами, событиями и проверяемыми guard-условиями. Точные имена enum остаются **TARGET HYPOTHESIS**, а перечисленные ниже смысловые различения — сильный консолидированный результат.

### 4.1. Матрица источников истины, состояний и переходов

| Контур | Различимые состояния / фазы (предлагаемый минимум) | Владелец перехода | Условия и свидетельства | Недопустимая подмена |
|---|---|---|---|---|
| **Intent → Work** | `PROPOSED → ADMITTED / REJECTED / NEEDS_CLARIFICATION` | application authority либо direct caller в P0 | идентичность инициатора, scope, критерии, capability, authority, ограничения | UI click = Work admitted |
| **Work** | `OPEN → ACTIVE ↔ BLOCKED/WAITING_REVIEW → ACCEPTED / REJECTED / TERMINATED → CLOSED[_WITH_RESIDUE]` | Work owner/application policy + разрешённый assessor | версия критериев, оценка результата, outstanding obligations | `Job.SUCCEEDED` = `Work.CLOSED` |
| **Run** | `REQUESTED → ADMITTED → PLANNED → EXECUTING → AWAITING_EFFECTS/ASSESSMENT → DISPOSED` | application execution authority | immutable parameters + binding, effect/review status | `RUNNING` в UI = физически началось |
| **Job** | `QUEUED/WAITING_RESOURCE → CLAIMED → RUNNING → FINISHING → TERMINAL` | JobManager/authority; worker сообщает факты | reservation/lease/fence, heartbeat, executor ACK | отсутствие heartbeat = подтверждённый failure без эффектов |
| **OperationRun** | `PENDING → DISPATCHED → EXECUTING → RESULT_REPORTED / OUTCOME_UNCERTAIN` | application authority, на основе executor report | operation revision, step identity, attempt lineage | failed Attempt отменяет факт внешней записи |
| **Attempt** | `CREATED → START_REQUESTED → START_CONFIRMED → STOP_REQUESTED? → ENDED/LOST` + отдельный outcome | непосредственный executor сообщает, authority закрепляет | worker identity, timestamps, exit/status/evidence | request-to-start = started; cancel requested = stopped |
| **Effect** | `INTENDED → AUTHORIZED → ATTEMPTING → CONFIRMED / DEFINITELY_NOT_APPLIED / PARTIAL / UNKNOWN → RECONCILED` | authority планирует/разрешает; effect owner/adapter удостоверяет | target, precondition, operation key, receipt/lookup/verification | timeout/exception = точно не совершилось |
| **Artifact** | `PROPOSED → STAGING → BYTES_WRITTEN → VERIFIED → PUBLISH_PENDING → PUBLISHED` + `ABORTED/FAILED/UNKNOWN/QUARANTINED` | publication coordinator + storage adapter | bytes/digest, schema, catalog commit, ACL, availability | существует путь = опубликовано |
| **AnalyticalResult** | `PRODUCED → CHECKED/QUALIFIED → VALID_FOR_SCOPE / INVALID / INCONCLUSIVE / STALE` | core/domain validator; независимая проверка по риску | source/registry/method snapshots, constraints, validation evidence | файл открылся = числа верны |
| **Assessment** | `NOT_REQUESTED / PENDING → PASS / FAIL / INCONCLUSIVE / WAIVED_BY_AUTHORITY` | уполномоченный reviewer/policy | критерий, субъект, evidence refs, scope, дата | тест «зелёный» = принята Work |
| **Acceptance** | `PENDING → ACCEPTED / REJECTED / CONDITIONAL` | пользователь/делегат/policy с полномочием | принятая версия result/criteria; исключения и срок | просмотр результата = принятие |
| **Closure** | `OPEN → CLOSURE_PROPOSED → CLOSED / CLOSED_WITH_RESIDUE / TERMINATED_WITH_RESIDUE / REOPENED` | владелец Work/authorized closer | решение, причина, остатки, получатели обязательств | закрытое окно = закрытая работа |
| **AppDock health** | platform-specific readiness/degraded/error | внешний AppDock | platform own receipts, health, activation | готовая платформа = завершённая аналитика |

**Сокращение физики:** Work, Run, Job и OperationRun в простой одношаговой работе могут жить в **одной физической записи с разными смысловыми ключами**; не обязательны четыре таблицы или четыре объекта Python. Однако планирование нескольких Jobs и многократные Attempts требуют сохранения идентичности каждого occurrence.

### 4.2. Admission и реально начавшееся действие

1. `SUBMITTED` означает лишь поступление запроса на рассматриваемую границу.
2. `ADMITTED` означает верифицированное право и зарегистрированное обязательство обработать либо явно отклонить запрос.
3. `QUEUED/CLAIMED` означает выделение очереди/worker, но ещё **не факт входа в handler**.
4. `START_CONFIRMED` возникает по отдельному подтверждению worker *после фактического начала* и может отсутствовать при crash между start и ACK. В последнем случае вывод должен быть ограничен доступными фактами — `start_uncertain`, а при наличии эффектов отдельный `effect_unknown`.
5. Запрос к внешнему сервису после durable effect intent требует собственной подтверждаемой границы. Именно здесь ACK может потеряться при фактическом выполнении действия.

**Нюанс:** в локальном однопроцессном режиме можно объединить `CLAIMED` и `START_REQUESTED` в представление, сохранив **разницу в свидетельствах**. В распределённом контуре преждевременное их объединение создаёт риск phantom runs.

### 4.3. Запрошенная отмена, остановка и эффект

Рекомендуемая последовательность:

```text
CancelRequested(actor, reason, target run/job, revision)
 → admission cancel authority
 → set cooperative cancel token / signal
 → next safe point observes token
 → execution stops *if possible*
 → inspect completed/pending effects
 → confirmed cancellation outcome OR partial/unknown outcome
 → user-facing status + possible residual work
```

**Неинвариант:** `cancel_requested ⇒ cancelled`. Правильный инвариант: подтверждённая cancellation содержит границу уже совершённых эффектов и основание, почему дальнейшая попытка прекращена. Если функция не поддерживает отмену или irreversible commit начался, система вправе честно сказать «остановка запрошена; эффект может завершиться». Принудительное убийство worker — отдельное разрешённое действие с повышенным риском `UNKNOWN`.

### 4.4. Timeout, failed и UNKNOWN

Техническая ошибка и знание об эффекте ортогональны:

| Наблюдение | Execution observation | Effect conclusion | Правильный следующий шаг |
|---|---|---|---|
| Исключение до любого effect boundary, доказано по коду/логике | `FAILED` | `NOT_APPLIED` | безопасный новый Attempt при прочих условиях |
| Timeout во время сетевого `PUT`, без ответа и lookup | `TIMED_OUT` | `UNKNOWN` | reconciliation, запрет слепого повтора |
| Удалены 3 из 5 файлов; ошибка на четвёртом | `FAILED` или `PARTIAL` | `PARTIAL` | пообъектный receipt, восстановление/компенсация |
| Worker убит после send, до durable ACK | `INTERRUPTED/LOST` | `UNKNOWN` | inspect external target/key; fence старый worker |
| Объект существует с ожидаемым digest и версия совпадает | `FAILED/TIMED_OUT` как историческое наблюдение | `CONFIRMED` после reconciliation | новая доказательная запись, разрешение дальнейшего Work |
| Объекта нет, но backend лишь временно недоступен | `TIMED_OUT` | `UNKNOWN`, не `NOT_APPLIED` | повторная проверка/эскалация |

**Никакого стирания прошлого:** reconciliation добавляет новое утверждение со ссылкой на прежний `UNKNOWN`, а не тайно переписывает `Attempt` как изначально successful. Текущий эффективный статус может обновиться; история наблюдений должна остаться.

### 4.5. Partial, предупреждение и зрелый смысл успеха

`PARTIAL` полезен лишь при описанном **множестве ожидаемых единиц**, их критичности и известном фактическом покрытии. «Файлов было 10, скачано 8» — количественный partial; «скачано 8, два из них критичные» — потенциально failure по продуктовым критериям. `WARNING` — attention severity, а не отдельный объективный исход. `SUCCEEDED_WITH_WARNINGS` может означать завершённый в рамках policy Run с сохранёнными диагностическими замечаниями; потребитель должен видеть уровень полноты данных.

### 4.6. Семантика изменения критериев во времени

**GAP.** Нужно решить, что делать, если после admission меняются source freshness, ACL, план, обязательные версии справочников, target path и сами критерии Work. Предпочтительная гипотеза — **прикрепить к Run immutable effective snapshot**; новые требования порождают новое решение/перепланирование или явную revalidation, а не меняют задним числом контекст завершённых Attempts.

## 5. Кто владеет истиной: матрица ответственности

### 5.1. Логическая ответственность

| Смысл/переход | Source of truth | Исполнитель / поставщик фактов | Проекция / потребитель | Status |
|---|---|---|---|---|
| Официальные источники и domain semantics | издатель источника для публикации; `stratbox` для интерпретации/методики | core operations, source adapters | Python/UI/машина | **CURRENT** частично |
| Capability definition, Request/Result, effect declaration | core для domain use case; application для curated Scenario and machine-safe admission view | registry/descriptor provider | Windows/API | **CURRENT** фрагментарно; унификация **TARGET** |
| Admission, Work identity, Run plan snapshot | единый Strategy Box application authority в управляемом scope | ingress/policy evaluator | все управляемые клиенты | **TARGET HYPOTHESIS** |
| Job queue, ресурсный допуск, Attempt identity | тот же application authority | JobManager/executor | UI/automation | **TARGET HYPOTHESIS** |
| Физический факт начала, output, exit | worker/операционный executor как свидетель | executor adapter + callbacks | authority | **CURRENT** внутри Qt, общие receipts **GAP** |
| Право на изменение, approval, отмену | policy owner / grant authority в Strategy Box | application evaluator (проверка текущей ревизии) | клиентские action menus | **TARGET HYPOTHESIS** |
| Физическое действие / транспортный результат | фактическая внешняя система в пределах наблюдаемости | `FileStore`/network/other adapter | effect reconciler | **CURRENT** IO; verified receipts **GAP** |
| Аналитическое claim, метод, validation | `stratbox` domain owner, external authoritative data publishers | core + специальные validators | Work assessment | **CURRENT** неоднородно |
| Artifact identity, acceptance of publication, ACL/retention | Strategy Box application/Artifact catalog | publisher + storage adapter | UI, downstream runs | **TARGET HYPOTHESIS** |
| Сырые bytes, object stat/digest, storage guarantees | конкретный хранилищный backend/adapter | FS service / external API | publisher | **CURRENT** bytes; гарантия по профилям **UNKNOWN** |
| Work acceptance, closure, exception waiver | уполномоченный пользователь или явно установленная policy | application command handler | чаты, внешние consumers | **TARGET HYPOTHESIS** |
| Node readiness, activation, installation, managed dirs | AppDock в его подтверждённом контракте | platform processes | Strategy Box adapter | **CURRENT** локальная граница |
| View, chat, inspector, progress, notification | downstream projection из authoritative scope | Windows/будущие interfaces | человек | **CURRENT** локальные, shared **NOT APPLICABLE** |

**Спор о расположении:** «кто хранит байты» и «кто определяет семантику» — разные вопросы. AppDock может предоставить managed directory или storage provider, но это не даёт ему право утверждать, что `Work.accepted=true`; Windows может показывать кнопку «Принять», но его Widget не является policy authority; FileStore может вернуть успешный `rename`, но он не превращается в владельца определения артефакта.

### 5.2. Два runtime и три режима

- **P0 / Python:** нет обязательного application authority; `stratbox` отвечает за свои операции, caller — за orchestration и effectful usage. Доказательная семантика операций общая, долговременная Work необязательна.
- **P1 / локальный управляемый Windows:** application authority может быть in-process и иметь единственного writer. Закрытие GUI по продуктовой policy обычно завершает вычисление, но **не отменяет уже совершённых эффектов**; пользовательская история и незавершённые разборы переживают закрытие, если durability-уровень принят.
- **P3 / будущий shared node:** один authority и durable state на стороне host; Windows/Android/Web становятся клиентами; закрытие клиента меняет session/presence, **не** Job state; worker продолжает в рамках разрешённой host policy. Такой профиль не подтверждён в CURRENT.

**CONFLICT, требующий разведения по профилю:** «закрытие приложения останавливает вычисление» (локальный режим) и «работа продолжает идти при закрытом клиенте» (host). Это не несовместимые требования к одной среде — это два класса размещения с разными contract-level guarantees.

### 5.3. AppDock-интеграция

Действующий AppDock концептуально ведёт узел, установку, активацию, рабочую среду, readiness, диагностику и внешние actions. `stratbox-windows` использует versioned Activation Context и сохраняет runtime-state projection. В целевом контуре Strategy Box отправляет в AppDock **ограниченный, безопасный сигнал о проблеме/готовности продукта** со ссылками на локальную диагностику. Сообщать платформе «Job завершён», не имея собственного application receipt, недопустимо. Свежие API общей problem registry/remote authority требуют проверки **по прямому owner**, поэтому **UNKNOWN**.

## 6. Сквозные инварианты (кандидаты для Product admission)

В таблице «обязателен» означает **архитектурно предложенный контракт для выбранного управляемого профиля**, а не действующую норму продукта.

| Код | Предлагаемый инвариант | Активирован в | Как нарушается сегодня / тест |
|---|---|---|---|
| **INV-01** | В каждом authoritative scope ровно один владелец принятия переходов Work/Run/Job, даже при нескольких readers/executors. | P1, P3 | два клиента независимо объявляют Job completed |
| **INV-02** | Every effectful attempt имеет durable intent *до* потенциального внешнего эффекта либо честно помечен как unmanaged. | управляемые effects | crash между send и записью intention |
| **INV-03** | `request accepted` не утверждает `execution started`; `cancel requested` не утверждает `stopped`. | P1+ | phantom started/cancelled cases |
| **INV-04** | Attempt identity никогда не переиспользуется для повторного физического выполнения. | retries/worker handoff | duplicate attempt overwrites log/history |
| **INV-05** | `UNKNOWN` сохраняется, пока независимое допустимое основание не установит эффект; исключение и пустой список этого не делают. | effectful adapter | fail→false; timeout→no effect |
| **INV-06** | Разрешение действия и его цель проверяются по актуальному scope **перед существенным эффектом**. | sensitive/destructive | revoked grant всё ещё позволяет `rmtree` |
| **INV-07** | Повтор не создаёт дополнительного недопустимого эффекта: idempotency key + digest + resource scope или inspect-before-retry. | effectful retries | двойной publish/download/delete |
| **INV-08** | Locked resource и worker lease — разные ограничения; устаревший исполнитель теряет право публикации через fencing/compare-revision. | concurrency | worker A ожил после takeover B |
| **INV-09** | Вычисление, эффект, artifact publication, assurance, acceptance и closure — отдельные квалифицированные факты. | любой managed result | Job success ⇒ Work closed |
| **INV-10** | Публикация артефакта означает проверенные bytes + управляемый visible catalog/manifest; путь и суффикс недостаточны. | managed artifact | запись в catalog до фактического rename |
| **INV-11** | Неуспех catalog commit не уничтожает единственный восстановимый verified staging объект без безопасной политики. | публикация | GC удалил sole copy при unknown |
| **INV-12** | Работа закрыта лишь по критериям/компетенции; остаточные обязательства имеют owner, reason, follow-up. | managed Work | «Сценарий зелёный», но источник старый |
| **INV-13** | Разрешённая диагностическая видимость уже, чем полный операторский лог; информация других пользователей scope-filtered. | shared/user data | traceback с путями/секретами виден всем |
| **INV-14** | Record of history монотонно сохраняет существенные наблюдения; новые evidence меняют current assessment, не подменяют старый факт. | P1+ | reconciliation удаляет старый timeout |
| **INV-15** | Проекция может быть восстановлена из авторитетных записей; её утрата не означает утраты Work. | P1+ | corrupt `cases.json` очищает историю |
| **INV-16** | Выводы о данных связаны с source/registry/method/parameter identities и честным scope uncertainty. | анализ | SORS claim усилен при export |
| **INV-17** | Редкое низкорисковое вычисление не обязано создавать глобальный ledger/approval DAG. | P0/P1 | рост затрат на каждую простую функцию |
| **INV-18** | При несовпадении фактических гарантий backend профиль снижает обещаемую надёжность либо запрещает эффект. | любой IO | предполагается atomic rename без теста |

**Строгость по риску:** запрет на потерю/удвоение важного эффекта обязателен только там, где операция влияет на реальное состояние; для чистого dataframe-transform достаточны детерминизм/проверка источников и report об ошибке. Так переносимость и ресурсная соразмерность сохраняются.

## 7. Долговременное состояние и границы атомарности

### 7.1. Какие факты должны переживать сбой

**Минимальный durable spine при P1:** `work_id` (если отдельная Work есть), `run_id`, intent origin/principal, admitted request digest, immutable effective params/definition/binding/version; принятие/отказ admission; Job/Attempt identities; transition sequence + happened/recorded times; effect intents/target/precondition/idempotency; receipts или explicit UNKNOWN; артефактный publish intent/manifest/digest; terminal disposition; review/acceptance/closure decisions; ссылка на доступные logs/diagnostics и residual obligations. Прогресс по процентам и heartbeat можно потерять или переиздать, если это не является основанием решений.

**Сохранность vs продолжение:** долговременный audit не требует оживления мёртвого Python stack frame. После crash authority строит правдивую картину `INTERRUPTED/OUTCOME_UNKNOWN`, предлагает проверку/новый Run. Verified checkpoints для отдельных крупных стадий допускают scoped reuse только после проверки source/config/version invariants.

### 7.2. Атомарные границы, которые существуют физически

| Граница | Возможная реальная гарантия | Чего она не гарантирует |
|---|---|---|
| In-memory function call | локальный return или exception | долговременный факт; отсутствие внешнего эффекта |
| Одна durable запись с atomic replace/append и fsync | целостность одного journal record при доказанных FS условиях | согласованность remote effects и нескольких отдельных файлов |
| Локальная файловая `rename/replace` в той же FS | возможная atomic visibility при проверенной платформенной семантике | durable flush без fsync; remote share; copy+delete fallback |
| Транзакция local DB | согласованность её records | бинарный output-файл и внешний сервис в той же транзакции |
| Object/storage backend publish | подтверждение через backend-specific receipt | произвольный downstream consumer получил и принял результат |
| Перенос нескольких файлов | максимум staged manifest + barrier/версионный указатель | магическую межфайловую атомарность без общей транзакционной системы |
| AppDock state projection | обновление platform view | предметный commit и аналитическую correctness |

**Вывод:** сквозной «exactly once» нельзя обещать для произвольных неидемпотентных внешних действий. Реальный достижимый набор: exactly-once *admission в локальном authoritative scope* при поддержке idempotency; at-least-once попытки для безопасных шагов; at-most-once dispatch при определённых ограничениях; idempotent or reconcilable effect; single-visible-generation artifact publication при доказанных backend capabilities. Эти утверждения имеют разные области.

### 7.3. Рекомендуемый минимальный журнал, без выбора СУБД

**TARGET HYPOTHESIS — логический persistence protocol:**

1. В одном authoritative scope только один writer; для UI — read projections с revision.
2. Запрос проверяется по `(actor scope, command kind, idempotency key, payload digest)`; одинаковый ключ и digest возвращают прежний admission result, конфликтующий digest отвергается.
3. До effect boundary фиксируется durable intent и ограничение ресурса/версии; после эффекта фиксируется receipt или `UNKNOWN`.
4. Запись события/состояния имеет monotonic sequence, schema version, checksum/length framing и causation refs; читатель не принимает partial tail за валидные данные.
5. Snapshot пишется через temporary file → flush/fsync по подтверждённым возможностям → replace; у него `last_applied_sequence` и integrity; при corrupt snapshot восстанавливаем из проверенного журнала либо выдаём явную аварийную диагностику.
6. `FILE_WRITE_FAILED` до effect intent — отказ допуска; после effect — возможный UNKNOWN и аварийная граница дальнейших действий. Потеря лога не должна незаметно переводить опасную операцию в «обычный success».
7. Compaction, retention и backup не уничтожают активные effect intents, unclosed obligations и необходимую ссылочную доказательность; restore проверяется фактически.

**Открыто:** достаточно ли append-only файловой реализации, какой уровень fsync, необходим ли журнал для всех user messages, RPO/RTO, crash-consistency сети/USB/SMB, схема миграции от существующих пяти JSON. Эти вопросы требуют proof на реальных deployment paths. SQLite остаётся допустимым локальным backend, а не необходимым семантическим объектом.

### 7.4. Поведение при повреждении состояния

- Повреждён client-side view/preferences → допустимый безопасный reset UI с диагностикой; canonical Work state остаётся.
- Повреждён snapshot, но journal цел → rebuild, report integrity incident, сохранить invalid snapshot для разбора по policy.
- Повреждён journal tail → recover до последней подтверждённой границы, после неё **UNKNOWN for affected work**; не очищать все данные «ради старта».
- Нарушена консистентность binding/manifest → freeze опасных effects, read-only/degraded mode, operator-assisted reconciliation; secure recovery не равен автоматическому retry.
- Непроверенная резервная копия → статус «backup exists / restore UNKNOWN», а не «recovery guaranteed».

## 8. Внешние эффекты: классификация, повтор, reconciliation

### 8.1. Классы операций — минимальная политика

| Effect class | Примеры | Replay/Retry по умолчанию | Проверка и граница полномочий |
|---|---|---|---|
| `PURE` | parse, normalize, расчет на immutable snapshots | допустим при одинаковом basis; кэш можно переиспользовать | source/method/params identity, input hash |
| `READ_EXTERNAL` | HTTP GET, чтение каталога/CSV | допустим после оценки quota, изменчивости, приватности | provenance/freshness и API constraints |
| `WRITE_STAGED` | временные bytes нового XLSX | повтор на новый staging key, cleanup по policy | digest/manifest, quarantine partial |
| `PUBLISH_IDEMPOTENT` | immutable generation в управляемом каталоге | same key+digest → reconcile / no duplicate | namespace, ACL, revision, verified receipt |
| `MUTATE_REVERSIBLE` | переименовать/переместить на backend с проверенной семантикой | по precondition и before/after evidence | resource lock, version, обратимый путь |
| `DESTRUCTIVE/IRREVERSIBLE` | удаление, overwrite единственной копии, внешняя необратимая запись | blind retry запрещён; explicit approval/revalidation | plan/target set/revalidate/effect ledger + recovery |
| `UNVERIFIABLE_EXTERNAL` | внешний endpoint без ключа/lookup и плохим ACK | после неизвестного исхода автоматический retry запрещён | manual reconciliation/exception path; может блокировать capability |

**CONSOLIDATED RESEARCH.** Нужны *разные* команды `ReplayRun`, `RetryAttempt`, `ResumeFromCheckpoint`, `ReconcileEffect`, `RebuildArtifact`, `ReassessResult`. Они могут жить за одной кнопкой меню с уточнением, но логически не взаимозаменяемы.

### 8.2. Протокол effect boundary

```text
(a) validate planned target/resource scope, current grants and preconditions
(b) durable EffectIntent(effect_id, plan_rev, target, key, expected version)
(c) execute one physical effect attempt, record observed adapter response
(d) obtain backend-specific verification receipt (or assign UNKNOWN)
(e) reconcile objective postcondition and compare against intention
(f) append authoritative effect disposition (with proof reference)
(g) continue/publish/close only if resulting guards permit
```

При lease takeover новый worker обязан предъявить fencing generation; старый executor, даже живой, не имеет права подтвердить публикацию старой ревизии. Если backend не поддерживает fencing/CAS и двух конкурирующих writer нельзя исключить, **scope ограничивают single-worker профилем** вместо имитации распределённого safety.

### 8.3. Reconciliation и сила отрицательного evidence

Отсутствие объекта на момент проверки доказывает отсутствие эффекта **только** при достаточной видимости: проверен правильный namespace, актуальные права, backend доступен, истёк разумный propagation lag, нет eventual consistency или известен её horizon, нет alias/move. Ошибка `listdir` или недостаток прав не равны пустому каталогу. Для remote сервисов подходят authoritative operation lookup по idempotency key, status endpoint, receipt, version stamp. Иначе `UNKNOWN` сохраняется с owner и сроком дальнейшего разбора.

### 8.4. Компенсация и восстановление — разные понятия

`Compensation` создаёт **новый** эффект, корректирующий прежний; она не стирает факт старого действия и может сама завершиться `UNKNOWN`. `Rollback` допустим лишь в настоящей транзакционной границе. `Repair` исправляет обнаруженное состояние, `Reconciliation` устанавливает факт, `Retry` совершает новую попытку. Удаление частичного каталога до доказательства целостности нового архива запрещено.

## 9. Доказательность результата и приёмка

### 9.1. Пять отдельных утверждений и нужные основания

| Утверждение | Сильное свидетельство | Недостаточно |
|---|---|---|
| **Операция выполнялась** | accepted run/attempt identity, start/exit evidence, captured handler result с версией кода/params | `case_created`, кнопка «Запуск» |
| **Внешнее действие совершилось** | owner/backend receipt и проверенное postcondition, version/target proof | исключение отсутствовало; лог «upload complete» |
| **Аналитический результат корректен в пределах** | schema/units/domain constraints, source hashes, registry/method versions, method-specific tests/solver certificates, оговорки | зеленый Job; workbook открылся |
| **Артефакт сохранён и опубликован** | проверенный digest/размер bytes, immutable generation, successful catalog-visible commit, правильный ACL/access | `outputs=(path,)`, `Path.exists`, имя `.xlsx` |
| **Work закрыта корректно** | оценка по pinned acceptance criteria, полномочие, явное решение, остаточные обязанности | `OperationResult.ok`; пользователь открыл файл |

Важно сохранять **степень доказательства**. `source downloaded` не значит `official statistics correct in reality`; `solver feasible` не значит вывод «официально опубликован»; SORS weak-selection факты не усиливаются до `STRICT_OFFICIAL` при отображении в Excel. Эти различия уже подтверждены предметными исследованиями core/SORS.

### 9.2. Evidence, event, log, diagnostic, problem — не синонимы

| Вид записи | Задача | Обязательная связь | Можно ли использовать как доказательство? |
|---|---|---|---|
| **Domain evidence** | Обосновать конкретное claim о данных/выводе | source/method/result IDs, scope | Да, в пределах метода и условий |
| **Effect receipt** | Зафиксировать наблюдение физического эффекта | effect/attempt/target/key/verification | Да, при достаточной силе производителя/проверки |
| **State-transition event** | Обосновать решение application authority | aggregate ID, sequence, actor, causation, prior revision | Да — о факте зарегистрированного перехода, но не о физическом мире само по себе |
| **Telemetry progress** | Показывать ход выполнения | attempt/run ID, sampling | Обычно нет — может теряться, агрегироваться, запаздывать |
| **Technical log** | Диагностика и расследование | correlation/attempt IDs, timestamp | Иногда подтверждает наблюдение; один log line не устанавливает успех |
| **Problem/incident** | Сообщать о нарушении сервиса/угрозе другим | problem ID, affected scope, safe summary | Свидетельство сбоя, но не автоматическое изменение всех Job статусов |
| **Acceptance record** | Факт утверждения/отклонения компетентным actor | Work/result/criteria/evidence revision | Да — об акте принятия, не об абсолютной истинности данных |

**Точечное предупреждение:** «доказательство» здесь **отношение между claim, источником, процедурой проверки и условиями**, а не любой JSON с названием `evidence`. Проверяемость должна быть достаточной к цене ошибки, не тотальной.

### 9.3. Результат и пользовательское действие

Рекомендуемый минимум `WorkResultAssessment` (может быть записью Work, не новой таблицей):

- `subject` — Run/result/artifact generation, которые оценены;
- `criteria_revision` — какие требования должны быть выполнены;
- `observed_outcomes` — computation, effects, published artifacts, coverage/quality;
- `grounds` — ссылки на validation, receipts и доказательства;
- `assessor` — человек либо допущенная policy;
- `decision` — accepted/rejected/conditional/inconclusive;
- `limitations` — missing data, assumptions, license, freshness, uncertainty;
- `residual_obligations` — кто, что, до какого условия должен исправить/проверить.

**Acceptance ≠ approval до выполнения.** Approval разрешает рискованный шаг и привязана к exact plan revision; Acceptance оценивает получившийся результат. Автоматическая acceptance допустима при заранее явно согласованных и тестируемых критериях. Work может корректно завершиться с «анализ опроверг гипотезу», «известных оснований недостаточно» или «операция обоснованно заблокирована» — если это допустимый outcome исходной постановки.

### 9.4. Closure и остаточные обязательства

Одна фраза «Готово» недостаточна, если внешний эффект неизвестен, а данные могли измениться. Предлагаемые closure dispositions:

- `CLOSED_ACCEPTED` — принятое исполнение и закрытые обязательные последствия;
- `CLOSED_WITH_RESIDUE` — принятый ограниченный результат, явно переданный остаток;
- `TERMINATED` — работа обоснованно прекращена без требуемого результата;
- `BLOCKED/OPEN_RECONCILIATION` — закрытие преждевременно, пока есть существенный неизвестный эффект;
- `REOPENED` — новый scope вследствие дефекта, изменённых оснований или уполномоченного решения, с lineage к прошлому закрытию.

**Отдельная развилка:** в каких случаях допускается `CLOSED_WITH_RESIDUE` при `effect_unknown`? Для опасного unresolved shared effect — обычно нет; в изолированной низкорисковой задаче возможен формально переданный owner/monitoring obligation. Решение требуется по risk classes и требованиям бизнеса.

## 10. Матрица отказов, неопределённых исходов, повторения и восстановления

Обозначения: **R** — новый Run; **A** — новый Attempt в рамках прежней логической OperationRun; **REC** — reconciliation без нового физического эффекта; **H** — ручная проверка/решение; **STOP** — запрет автоматического повторения до разрешения неопределённости. Это *проектная политика*, не существующий scheduler.

| № | Точка отказа | Что достоверно известно | Чего нельзя заключать | Допустимое восстановление | Нужный инвариант |
|---|---|---|---|---|---|
| F01 | Запрос принят в UI, процесс умер до durable admission | только пользовательское намерение, если оно сохранилось | Run допущен/запущен | безопасный повтор submit с тем же key; новый Work лишь после admission | 01,03,15 |
| F02 | Запись admission зафиксирована, worker ещё не забрал Job | durable запрос, Job ждёт | расчёт начался | restart dispatcher, dispatch same Job с новой attempt identity | 03,04 |
| F03 | Worker начал вычисление, но стартовый ACK потерян | worker мог работать | он точно не начал / обязательно завершился | classify `start_uncertain`, inspect worker/outputs; новый Attempt по policy | 03,05 |
| F04 | Сбой внутри чистого parse/расчёта, внешних эффектов нет | attempt failure + input snapshot | Work завершена | A/R; повтор при pinned versions | 04,16 |
| F05 | Часть источников скачалась, сеть оборвалась | известны hashes успешных файлов | полный batch обновлён | revalidate cached successes, докачать missing, explicit PARTIAL | 09,16 |
| F06 | HTTP request породил внешний effect, ACK потерялся | request был послан | effect отсутствует или есть | REC через operation key/remote lookup, иначе STOP+H | 02,05,07 |
| F07 | Сбой записи staging до закрытия | неполные bytes | опубликованный artifact существует | quarantine, restore old generation, новый staging | 10,11 |
| F08 | Bytes записаны, digest верифицирован, crash до publish | verified candidate | пользовательский artifact опубликован | REC/revalidate path + digest, завершить publish по ревизии | 10,11 |
| F09 | Remote finalize совершился, ACK потерялся | effect intent, нет подтверждения | ни success, ни definite failed | REC: authoritative stat/generation, digest; иначе UNKNOWN | 05,10,18 |
| F10 | Bytes committed, catalog commit не состоялся | физическая копия может существовать | объект виден/доступен через каталог | reconcile orphaned materialization, commit либо repair/quarantine | 10,11,15 |
| F11 | Catalog committed, UI не получил event | durable artifact record существует | публикацию надо повторить | re-read authoritative projection с revision | 01,10,15 |
| F12 | `rmtree` удалил часть target set, затем ошибка | частичные receipts | операция «просто failed без эффектов» | STOP, plan actual residue, repair/compensate на новом Work/Attempt | 02,05,06 |
| F13 | Concurrent writer B публикует после worker A с устаревшим lease | A имеет старый intent | A вправе overwrite B | fence A; compare version; COW generation, conflict | 08,10 |
| F14 | User нажал Cancel после необратимого шага | CancelRequested, некоторый effect уже мог быть | ничего не изменилось | finish/confirm current effect; cancel remaining work; PARTIAL/UNKNOWN | 03,05,09 |
| F15 | UI закрыт при локальном worker | потеря UI-сессии, исполнение по local policy | все effects отменились | graceful stop→bounded wait→classify; restate durable Work | 03,05,15 |
| F16 | Клиент отключился от будущего host | потерян клиентский канал | host Job остановлен | reconnect/read authoritative state; без blind retry | 01,03 |
| F17 | Повреждён один из пяти JSON history files | локальный файл повреждён | вся Work отсутствует | будущий журнал → rebuild; CURRENT: уязвимость к silent empty | 14,15 |
| F18 | Система истории не может фиксировать effect intent | невозможность гарантировать audit | опасный эффект безопасен | reject/stop hazardous operation, деградация в read-only | 02,18 |
| F19 | Регулятор обновил архив между plan и fetch | изменился source snapshot | старый вывод автоматически неверен/новый эквивалентен | pinned fetch + source-freshness assessment / re-run | 16 |
| F20 | Смена ОКВЭД/банковского registry между расчётом и экспортом | версии различаются | workbook повторяет прежнее значение/смысл | запрет misleading export; rebuild/reassess с fixed registry versions | 09,16 |
| F21 | Проверка SORS обнаружила недостаточную доказательность | результат имеет слабый tier / open bounds | точное официальное число получено | publish qualified result, criterion may reject or accept limited | 09,12,16 |
| F22 | Внешняя платформа сообщила degraded node health | platform readiness изменена | аналитический Job failed или Work закрыта | route platform problem, freeze affected action, restore/read state | 01,09,18 |
| F23 | Изменились права между планированием и `delete` | ранее plan approved | старый grant продолжает действовать | reauthorize exact target+plan rev; deny effect | 06 |
| F24 | Поздний receipt уточнил `UNKNOWN` как `CONFIRMED` | новый proof получен | исторический timeout никогда не происходил | append reconciled disposition; rerun acceptance guards | 05,14 |

### 10.1. Специальный случай: опасная операция над каталогом

Целевой безопасный путь:

```text
scan + immutable target listing
 → plan(expected source identities, hashes/size, destination, preconditions)
 → review/authorization bound to plan digest
 → revalidate just before effect
 → copy into new staging namespace
 → verify complete target set and content
 → publish destination (or explicit weaker backend profile)
 → only then separately authorize destructive source cleanup
 → per-object receipts + verify source disposition
 → Work assessment/closure or explicit residue
```

FRG уже реализует **полезный** pattern `plan → inspect → apply` (**CURRENT**), но это ещё не обещание общей транзакционности: filesystem и внешние эффекты требуют проверки реальных backend guarantees. Нельзя превращать failed copy/move в автоматическое удаление исходника; нельзя интерпретировать «каталог пуст» после ошибки доступа как evidence отсутствия.

### 10.2. Восстановление при изменении основания

Если между исходным Run и восстановлением изменилась версия источника, метод, registry, target, permissions, plan или storage provider, система должна выбрать **новую правдивую траекторию**: revalidate/adjust plan, создать новый Run, разрешить только обоснованное reuse verified subresults либо остановить с уточнением. «Resume старый Job» корректно только если доказана сохранность всех необходимых условий и checkpoints. Это пересечение EWM с EKM/EOM, а не задача одного scheduler.

## 11. Реестр противоречий, вариаций исследований и реальных gaps

В этом реестре **CONFLICT** ставится только при несовместимости договоров/обещаний в одной области. Разные физические варианты, пока не принятые, обозначены `OPEN VARIANT`, а историческое опережение исследований над кодом — `RESEARCH → CURRENT GAP`.

| ID | Стороны / прямое основание | Квалификация | Разрешение или открытый вопрос |
|---|---|---|---|
| C01 | Windows Case `success/failed` на основе `OperationResult.ok` ↔ исследования разделяют execution/effect/assurance/acceptance | **CONFLICT** текущей user semantics с предполагаемой целевой полнотой; код как факт не «ошибочен» сам по себе | не использовать Case status как универсальную истину; создать qualified projection |
| C02 | `ArtifactRecord.from_path(outputs)` ↔ staged publish требует verified bytes + catalog commit | **CONFLICT** утверждения «создан» с сильным смыслом managed artifact | разделить `output reference` и `published artifact`; сохранение current metadata для migration |
| C03 | 5 JSON projections + silent corrupt→[] ↔ durable Work/history/fault recovery | **GAP** относительно целевой долговечности; CURRENT docstring не обещает DB-grade | единый authoritative journal или иной transaction-backed record; честный migration |
| C04 | Enum `cancelled`/`queued` + background kinds ↔ runtime без cancel/scheduler | **DECLARED CAPABILITY GAP** | либо пока маркировать preview, либо реализовать переходы до обещания UX |
| C05 | Research-03/09 предлагает headless authority ↔ Research-02 предлагает начать in-process ExecutionService | **OPEN VARIANT**, не логический конфликт | logical authority fixed as recommendation; физика выбирается профилем/тестом |
| C06 | SQLite как близкий вариант в ранних исследованиях ↔ темы 03/08 от 10.10 предлагают допустимый file journal и AppDock-selected backend | **RESOLVED RESEARCH VARIATION** | не закреплять DB сейчас; сначала capability/durability contract и failure tests |
| C07 | Локальное закрытие прерывает вычисление ↔ будущая host работа после отключения клиента | **SCOPE DISTINCTION** | explicit local/host lifecycle profile; client disconnect не cancellation |
| C08 | Operation/Scenario/Scheme/Composition/Cascade как отдельные имена в исследованиях 01–03 ↔ минимальная модель без лишних owners | **RESEARCH NOMENCLATURE TENSION** | semantic definition vs machine projection vs UI projection; не требовать таблицу на термин |
| C09 | Канонический `Work → Run → Job → OperationRun → Attempt` ↔ прямой Python Request→Result | **SCOPE DISTINCTION** | shared domain semantics; managed lifecycle optional in P0 |
| C10 | AppDock управляет узлом, действиями и результатами ↔ Strategy Box owns analytic Work/Job truth | **BOUNDARY RISK** | AppDock stores/provides platform state; Strategy Box decides domain transitions; versioned adapter |
| C11 | Core Result/Failure типизирован у ряда доменов ↔ Windows `OperationResult.ok` стирает nuance | **GAP / semantic information loss** | preserve domain qualified result; UI projection only after evaluation |
| C12 | User-authorized command ↔ potentially long-lived machine executor and changed grants | **GAP** | plan-bound approvals, pre-effect reauthorization, actor provenance |
| C13 | Worker heartbeat/timeout ↔ inference «нет эффекта» | **SEMANTIC CONFLICT** если использовать timeout как negative effect proof | separate UNKNOWN + reconciliation |
| C14 | Runtime/bootstrap imports Qt `ScenarioCoordinator` ↔ Android/shared application-neutral architecture | **CURRENT STRUCTURAL CONFLICT** | extract orchestration boundary, leave Qt signals adapter |
| C15 | Windows package `stratbox==0.2.1` и manifest core `0.2.1` ↔ core current `0.8.0` | **CURRENT DECLARED CONTRACT DRIFT** | согласовать package graph и проверить install smoke; backward compatibility не цель |
| C16 | Manifest v4.0 ↔ Windows smoke test ожидает v3.0 | **CURRENT TEST/CONTRACT CONFLICT** по базовому срезу | скорректировать test/owner; verify runtime graph, не считать red тест зелёным |
| C17 | Stage 3 MADAR EWM/knowledge conclusions ↔ отсутствие в Strategy Box accepted HOW | **RESEARCH → PRODUCT GAP**, не нормативный конфликт | специальное admission, апробация, отказ от механического копирования терминов |
| C18 | Внутренние доменные доказательства SORS ↔ общий lightweight provenance | **CONTROLLED SPECIALIZATION**, не конфликт | общий минимальный envelope + специализированные ledgers без потери tier |
| C19 | «Любой path root — безопасный sandbox» ↔ текущий LocalFileStore path normalization не гарантирует containment | **CURRENT SAFETY GAP** | separate authorized namespace/path confinement before remote/shared exposures |
| C20 | «Общий чат и уведомления для всех» ↔ ACL/защита чужих данных/ошибок | **PRODUCT POLICY CONFLICT** при unrestricted visibility | per-recipient sanitized projection и scope filtered events |
| C21 | Availability `supports_artifacts/presence=true` в manifest ↔ реальные shared/remote функции отсутствуют | **CAPABILITY READINESS AMBIGUITY** | ограничивать толкование manifest конкретным платформенным контрактом, не обещать full collaboration |
| C22 | Source evidence `strict official` ↔ слабый derived/selected result | **POTENTIAL EPISTEMIC CONFLICT** | preserve claim scope/tier/provenance, запрещать label strengthening |
| C23 | Дополнительные `Assessment`, `Acceptance`, `Closure` как смысл ↔ риск множества классов/таблиц | **COST TENSION** | разные проверяемые assertions, допускается единое физическое WorkResult record |
| C24 | Принятая/непринятая `docs/` + свежие Research ↔ прочтение кандидатных файлов как обязательного продукта | **SOURCE-STATUS CONFLICT** | соблюдать `PUBLICATION-MANIFEST.md`, admission gate и статусные метки |

### 11.1. Самые существенные незакрытые границы

**GAP-G1 — admission:** где фиксируется единственный durable момент принятия нового Work/Run, включая duplicate requests и отказ.

**GAP-G2 — effect ownership:** какой адаптер способен подтвердить конкретный backend effect и с какой силой; когда состояние остаётся UNKNOWN и кто обязан разрешить его.

**GAP-G3 — result bridge:** как доменный `Request→Result` сохраняет qualification/partial/evidence при помещении в пользовательский Run.

**GAP-G4 — publish barrier:** как скоординировать filesystem bytes, digest/manifest и видимую каталожную запись без обещания распределённой транзакции.

**GAP-G5 — authority boundary:** кто юридически/операционно может запускать, удалять, публиковать, отменять и принимать, включая scope и активную ревизию grant.

**GAP-G6 — history and recovery:** какое долговременное подмножество фактов и capability storage гарантирует для local P1 и будущего P3.

**GAP-G7 — closure semantics:** какие Work остаются open/blocked при confirmed Job success, при частичных источниках и после `UNKNOWN`.

**GAP-G8 — user/client consistency:** как превращать authoritative state в per-user thread/chat/notification без утечки логов и прав на недоступные артефакты.

## 12. Минимальные и развитые архитектурные варианты

### 12.1. Сопоставление альтернатив

| Вариант | Как устроен | Сильные стороны | Ограничения и риски | Ресурс/эксплуатация | Условие выбора |
|---|---|---|---|---|---|
| **A. Развивать существующий Qt Windows** | Case JSON, `QThread` orchestration, локальные handlers | минимум переделки, текущий UX | семантика authority спрятана в UI, плохая Android переносимость, crash/durability gaps, нет shared scope | самый дешёвый краткосрочно; дороже при росте | только узкий прототип/низкий риск |
| **B. Платформенно-нейтральная application logic внутри Windows package** | независимые от Qt Work/Run/ExecutionService, один local writer, persistence port, Qt bridge | малый переход, одна truth locality, будущий reuse, без сервера | закрытие app обычно останавливает worker; P3 недоступен без нового deployment | **низкая–средняя**; вероятный стартовый профиль | P1: личный управляемый desktop |
| **C. Отдельный локальный executor process** | UI обращается к локальному исполнителю и authority (возможно один процесс) | живёт дольше GUI, process isolation, независимые log/crash | lifecycle, IPC, upgrade/fencing, security, дополнительный daemon | **средняя** | фон при закрытом окне, тяжёлые/crash-prone операции |
| **D. Самостоятельный headless application authority** | единый endpoint/steward Work/Job/state для клиентов; workers как adapters | P3 shared-node, Android/Web clients, central ACL, background | требует authenticated API, durable store, scheduling, recovery, schema/version lifecycle | **средняя–высокая**, оправдана общим узлом | подтверждён multi-user/host requirement |
| **E. Распределённая queue/worker architecture** | partitioned stores, multiple worker hosts, messaging, leases/fencing, reconciler | горизонтальное масштабирование, независимые отказные области | сетевые partition, split-brain, consistency, высокие ops затраты; сложная гарантия effects | **высокая** | измеренные capacity/availability цели не выполняются D |

**Исследовательское предпочтение:** **B → C/D по фактической потребности**, при устойчивых семантических контрактах с самого начала. Переход B→D — не автоматическое создание нового репозитория, а физическое вынесение того же logical authority в другой process locality. Вариант E — **NOT APPLICABLE** для текущего local-only продукта.

### 12.2. Модульные швы, у которых есть самостоятельная ценность

```text
[stratbox: domain Operation / source / validation / provenance]
                              ↑ Request / Result / Diagnostics / Effect declaration
[application authority: Work, Admission, Plan, Run, Job, Attempt, Effect, Assessment]
                 ├── [ExecutionBackend port] → local thread/process/host worker
                 ├── [PersistencePort] → tested file journal / DB adapter
                 ├── [ArtifactPublicationPort] → FileStore-backed staged publish
                 ├── [AuthorizationPort] → local/shared permission context
                 └── [PlatformAdapter] → verified AppDock bindings/problems
                              ↓ access-filtered snapshots/events
             [Windows Qt] / [future Android] / [future Web/AI]
```

**Это не требование создать шесть самостоятельных сервисов.** Ports могут быть компактными интерфейсами внутри одной Python application-библиотеки. Domain `stratbox` остаётся напрямую импортируемым в Colab/Notebook. Windows/UI не получает полномочий определять доменную evidence tier. Физическое расположение общей application-библиотеки между репозиториями остаётся открытым.

### 12.3. Выбор способа исполнения

- Для IO-bound загрузок и Excel-формирования `thread` может быть достаточен, если handler безопасно отменяется и отсутствие heartbeat диагностируемо.
- Для CPU/памяти тяжёлых SORS расчётов полезна process isolation, resource budgets и независимый kill — **после** разделения effectful этапов.
- Process boundary сама по себе не обеспечивает durable effect receipts и не делает операцию idempotent.
- Scheduler, автоматизация и AI не создают второй путь truth; это **разные инициаторы одной admission/Run-модели**.
- `Job` следует материализовать как отдельную schedulable единицу лишь при нескольких независимых шагах, ресурсных claims, переносе worker или retry. Один простой Run может содержать один embedded Job record.

## 13. Сквозные проверочные сценарии: положительные и отрицательные

Ниже — **проектные тест-векторы**, а не результаты проведённых испытаний. Каждый проверяет конкретную цепочку утверждений и критерий подтверждения целостности.

| Test | Сценарий | Условия / ожидаемое наблюдение | Что подтверждает |
|---|---|---|---|
| T01 | Python direct pure parse | без GUI/AppDock, typed Result/Failure с честным provenance | P0 независимость core |
| T02 | Один Windows export XLSX | admit→Attempt→computed Result→digest→publish→assess→case projection | happy path сквозной модели |
| T03 | Одно Work, два последовательных Runs | разные run IDs, unchanged work objective, разные revisions outcomes | Work не Run |
| T04 | Double-click submit | тот же idempotency key/digest возвращает тот же admission | отсутствие двойного эффекта |
| T05 | Same key, changed params | конфликт до запуска | защита от key collision |
| T06 | Crash перед worker start | recorded admission, no invented started flag | граница принятие/начало |
| T07 | Cancel before effect | stop receipt, effect definitely not applied | cancel подтверждён, безопасен |
| T08 | Cancel during remote publish | status cancel requested, effect UNKNOWN/confirmed по факту | отсутствие ложного cancelled |
| T09 | Worker died during pure computation | interrupted, new Attempt eligible; Work open | disposable computation |
| T10 | Lost publish ACK | UNKNOWN, remote lookup, no blind duplicate | effect reconciliation |
| T11 | Partial multi-file export | no complete published collection; allowed partial explicitly marked | bundle atomicity policy |
| T12 | Crash between bytes and catalog | bytes remain recoverable; no false published entry | commit barrier |
| T13 | Corrupt snapshot | journal replay or explicit failure, no silent empty history | durable recovery |
| T14 | Corrupt journal tail | stop at verified sequence, UNKNOWN affected effects | fail-closed integrity |
| T15 | Two writes same artifact generation | only one commit; other conflict/serialized | compare revision / fencing |
| T16 | Worker A resumes after takeover | A forbidden to publish stale generation | lease fencing |
| T17 | Revoked delete grant after plan | revalidation prevents delete | policy currentness |
| T18 | Invalid Data root / degraded startup | UI diagnostics available, effectful Job rejected not lost | platform/application separation |
| T19 | AppDock health degraded mid-run | platform problem distinct from domain Job status | separate truths |
| T20 | User A accesses User B case | ACL filtered info; sensitive log absent | privacy/control |
| T21 | Domain source reports 404/timeouts | `unavailable` distinct from «official publication absent» | domain negative evidence |
| T22 | Source changed after Run | old result remains versioned; new assessment/currentness changes | reproducibility |
| T23 | SORS weak-tier result exports | tier, bounds, assumptions preserved | claim strength invariant |
| T24 | Result valid, user rejects | successful execution + failed acceptance + open Work | assessment vs execution |
| T25 | Invalid workbook digest | quarantined, unpublished; previous generation intact | artifact correctness |
| T26 | Successful Job with missing required file | Job outcome qualified/review needed; Work not auto-closed | Work closure guard |
| T27 | Future host: Windows disconnected | host Run state progresses; reconnect reads authoritative state | remote client semantics |
| T28 | Future scheduled/AI launch | same admission/effect policy, no elevated implicit grant | initiator independence |
| T29 | Reopen after changed requirements | successor revision/new Run linked, prior closure retained | governed change |
| T30 | Recovery backup | restore test checks Work/effect/catalog consistency, not mere copy existence | actual continuity evidence |

### 13.1. Один полный аналитический путь: эскроу/отчётность

**Исходная цель:** сформировать историю по нескольким официальным публикациям регулятора и передать пользователю проверенный XLSX.

1. **Intent/Work:** пользователь выбирает период, источники, формат, полноту и критерий приемки. Если это разовая личная операция без дальнейшего поручения, Work может физически совпасть с Run-scope; для длительного аналитического поручения Work остаётся отдельной.
2. **Capability/Plan:** разрешается версионированный source catalog, parser, build history, export; фиксируются target path, cache policy, overwrite, workspace ACL, source snapshots/ожидаемые artifacts. `Scenario` выбирается UI, конкретный `ExecutionPlan` закрепляет effective параметры.
3. **Admission:** проверить право писать в target, достаточно места/зависимостей, текущие риски, idempotency. Work/Run/Job identity становится durable до исполнения.
4. **Attempt 1 — Download:** один источник недоступен. Это failure конкретного fetch либо partial batch, но **не утверждение об отсутствии регуляторной статистики**. Сохраняются download evidence, hashes для успешных источников.
5. **Attempt 2 — Parse/build:** домен нормализует только известные snapshots, сохраняет coverage, schema warnings; доменный результат может быть qualified partial.
6. **Artifact:** Excel собран в staging; digest/size сверены, проверены обязательные листы и schema. При аварии здесь Work ещё не имеет опубликованного файла.
7. **Publish:** локатор получает новую неизменяемую generation; backend подтверждает commit и catalogue visibility. Если ACK потерян, идет reconciliation; пользовательский чат показывает «Проверяем сохранение», а не «Готово».
8. **Assessment:** criteria «все обязательные месяцы / источники / показатели» могут запретить принятие частичного XLSX; альтернативно допустима явная conditional acceptance с ограничениями.
9. **Closure:** пользователь подтверждает достаточность или оставляет Work в review; остаток по отсутствующим месяцам назначается и сохраняется. AppDock видит platform health, а не решает пригодность банковских показателей.

**Контрпример:** все шаги по отдельности вернули `ok=True`, но источники относятся к разным версиям методики, а целевой файл перезаписан другим worker. Отдельные «зелёные» локальные тесты не доказывают целостность всей цепочки. Именно поэтому нужны pinned plan, provenance, publish revision и Work assessment.

### 13.2. Недопустимые состояния при end-to-end replay

- `Run.SUCCEEDED`, но обязательный effect `UNKNOWN`, без оговорки и приёмки исключения.
- `Artifact.PUBLISHED`, когда bytes отсутствуют или digest не соответствует immutable manifest.
- `Work.CLOSED_ACCEPTED`, когда принят только план, а actual result отсутствует.
- `Attempt.CANCELLED`, когда известно лишь о нажатой кнопке Cancel.
- `Job.FAILED`, означающий `external_not_applied` только на основании timeout.
- Shared UI A показывает закрытые логи B без разрешения.
- Старый worker подтверждает overwrite после выдачи нового fencing token.
- Re-run выдает результаты со старым source identifier, но новым содержимым без новой provenance.
- Повреждённый snapshot превращает доказанную незавершённую Work в «никаких заданий нет».

## 14. Что уже достаточно исследовано, что требует принятия, проверки и новой науки

### 14.1. Достаточно проработанные смысловые положения — не повторять с нуля

| Тема | Уровень зрелости Research | Что осталось вместо нового теоретического исследования |
|---|---|---|
| Work vs Thread vs Run vs Case | **CONSOLIDATED RESEARCH, high confidence**: самостоятельные назначения, владение и кардинальности разобраны в 03/02, 03/04, 04/01–02, 04/11 | определить user-facing Work/Thread UX, вариант физической записи; принять vocabulary |
| Operation vs Scenario/Scheme/Composition | **CONSOLIDATED RESEARCH**: core-capability, curated UI и machine representation различимы | утвердить minimum descriptor, испытать 2–3 реальные операции/составной граф |
| Run/Job/OperationRun/Attempt | **CONSOLIDATED RESEARCH**: рабочие и исполнительные идентичности независимы от файлов | выбрать минимальную persistence схему; проверить repeat/failure/race |
| Cancellation requested vs confirmed | **CONSOLIDATED RESEARCH**: невозможность честного «cancelled» без stop/effect boundary | внедрить cancellation checkpoints в репрезентативных handlers и fault tests |
| Uncertain effect, idempotency, reconciliation | **CONSOLIDATED RESEARCH**: timeout не доказывает отсутствие внешнего эффекта | backend-specific capability contract, receipts, lookup tests, запрет blind retry |
| Staged artifact publish | **CONSOLIDATED RESEARCH** + [подробный кандидат LDD](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/ldd/artifacts/staged-publication.md) | проверить реальную FS семантику, разработать admission для manifest-generation |
| Provenance/evidence/claim validity | **CONSOLIDATED RESEARCH**, предметный пример SORS **CURRENT** | выбрать маленький общий envelope, не теряя специализированные tiers и сертификаты |
| AppDock vs Strategy Box ownership | **CONSOLIDATED RESEARCH** + версии локальных contracts **CURRENT** | уточнить текущие platform capabilities и согласовать двусторонний health/problem contract |
| Local vs headless/shared execution | **CONSOLIDATED RESEARCH** на уровне logical authority | принять deployment profile по продуктовой потребности и операционным бюджетам |
| Logging/events/progress | **CONSOLIDATED RESEARCH**: разные назначения и safe projections | тестировать потери диагностического sink, correlation, ACL;
| State owner before storage choice | **CONSOLIDATED RESEARCH** и `docs/architecture` candidate | принять контракт durability и реализационный backend по результатам тестов |
| Proportional assurance | MADAR `spec/` + Stage 3 B9, **сильная методологическая опора** | продуктовые risk classes, бюджеты и критерии достаточности |

### 14.2. Нужна преимущественно проверка на реальных отказах

1. **Filesystem:** можно ли безопасно написать временный объект, выполнить flush/close, проверить digest и опубликовать одним видимым шагом на поддерживаемых локальных/managed paths; реальное поведение `rename/replace`, `fsync`, failure-before/after-commit, cross-device и network latency.
2. **Persistence:** хватает ли single-writer file journal при фактической интенсивности; что происходит при потере питания, частичном append, конкурирующем приложении, backup/restore и upgrade schema.
3. **Executor:** безопасность Qt→neutral service separation, корреляция attempts, контролируемая остановка IO/CPU задач, отсутствие ложного «успеха» после ошибок callback/persistence.
4. **Core adapters:** какие операции честно возвращают `not found`, `unavailable`, `permission denied`, `partial`, `unknown` и как эти семантики сохраняются в application.
5. **Publication:** обнаружение leftover staging, catalog orphan, lost ACK и race двух поколений одного артефакта.
6. **User workflow:** различает ли пользователь «работа завершена» и «отчёт сформирован, но требует проверки», какие остаточные обязательства реально полезны, не перегружает ли сложная терминология.

### 14.3. Действительно открытые исследовательские вопросы

**RQ-01 — уровень Work identity.** Требуется ли каждый раз устойчивый Work для атомарного сценария или достаточно ephemeral Run с optional Work wrapper? Теория различий уже есть, **не хватает UX/retention evidence**.

**RQ-02 — честный negative effect proof в конкретных FileStore/HTTP backends.** Нет универсального правила «объект отсутствует», достаточного при eventual consistency и временной недоступности. Нужны отдельные backend capability trials.

**RQ-03 — минимальный сквозной publication barrier.** Согласовать метаданные и байты без распределённой транзакции, особенно для bundle нескольких файлов, чужого изменяемого workspace и будущей команды.

**RQ-04 — полномочия на принятие/закрытие.** Пользователь, поставивший запрос, руководитель, назначенный reviewer, автоматическая policy и машинный инициатор имеют разные права. Нужны конкретные пользовательские роли, а не только общие слова.

**RQ-05 — migration существующей истории.** Как сохранить текущие Case/Events/Artifacts/Assignments и обнаружить имеющиеся bytes, когда старые `ArtifactRecord` не имеют verified digest/commit semantics? Риск ложного усиления legacy records особенно высок.

**RQ-06 — shared-node boundary.** Конкретный AppDock host/remote/permissions/storage contract и способность безопасного routing/challenge пока не подтверждены текущим local manifest; требуется отдельное испытание интеграции.

**RQ-07 — data/scientific acceptance profiles.** Разным доменам нужны разные полнота, freshness, tier и допустимые partial outcomes. Нужна малая representative matrix, а не универсальный quality score.

**RQ-08 — economics и доступность сложной модели.** Можно ли ограничиться одним execution ledger и минимальными notes в чатах, чтобы не перегрузить медленные ПК и аналитиков? Требуется профилирование CPU/memory/IO и короткий usability trial.

## 15. Реестр открытых Product Decisions и необходимых доказательств

Исследование намеренно **не принимает** нижеперечисленные решения. Варианты — жизнеспособные гипотезы, последствия требуют сравнения. Префикс `PD-T12` — локальная навигация этого Research, **не** официальный идентификатор продукта.

| PD | Решение | Варианты | Последствия / trade-off | Необходимое основание до принятия |
|---|---|---|---|---|
| PD-T12-01 | Явный Work для однократного Run | обязательный Work; optional Work; embedded Work-in-Run | постоянный Work упрощает acceptance, увеличивает объём и UI | 3 representative journeys + retention semantics |
| PD-T12-02 | Где живёт application authority | in-process shared logic; local process; headless host | изоляция/фон vs lifecycle/IPC/ops | P1/P3 потребность, crash/UX тест |
| PD-T12-03 | Durable backend | single-writer journal + snapshots; SQLite; иной provided provider | простота и наблюдаемость vs транзакции/миграции | fault injection + реальный AppDock data binding |
| PD-T12-04 | Профиль закрытия окна | stop local worker; minimize-to-tray; detach from host | поведение отмены/ресурсы/ожидания пользователя | UX and lifecycle scenarios |
| PD-T12-05 | Подмножество состояний для UI | 4–6 headline labels + details; подробные FSM labels | доступность против точности | user trial на partial/unknown |
| PD-T12-06 | Semantics of cancel | cooperative only; separate forced kill; admin escalation | отзывчивость и опасность unknown | effectful/CPU execution trials |
| PD-T12-07 | Retry defaults | только PURE/reads; allow approved idempotent publishes; wider with reconciliation | производительность vs дублированные эффекты | adapter matrix и error classifications |
| PD-T12-08 | Managed artifact publication | single-file generation; content-addressed immutable; directory bundle manifest | целостность/память/место/удобство | реалистичные XLSX/ZIP/bundle failure tests |
| PD-T12-09 | Acceptance | manual default; auto if criteria; conditional acceptance | нагрузка на пользователя vs возможность преждевременного закрытия | 4 domain scenarios, authority policy |
| PD-T12-10 | Кто может закрыть с остатком | Work owner; manager; delegate; auto policy | безопасность shared consequences | risk & residual obligation policy |
| PD-T12-11 | Granularity Job | 1 Job на Run; Job по эффектным/ресурсным boundaries | простота vs recovery/parallelism | FRG, collector, SORS and export probes |
| PD-T12-12 | Version semantics | explicit semantic revision; package build only; digest both | воспроизводимость vs maintenance overhead | re-run two versions + schema migration |
| PD-T12-13 | Shared artifact catalog | local per node; centrally managed host; federated | ACL consistency/latency/retention | current AppDock capability, node trial |
| PD-T12-14 | Notifications для команды | только affected shared resource; все ошибки; configurable | внимание пользователей, чувствительность информации | incident UX + privacy matrix |
| PD-T12-15 | Log/evidence retention | bounded detailed logs + durable essential refs; full permanent trace | disk footprint, privacy, reproducibility | real sizes, recovery/legal requirements |
| PD-T12-16 | AI/automation authority | scoped delegated permissions; per-action approval; read-only initially | UX vs blast radius | threat model, actor origin audit, abuse tests |
| PD-T12-17 | Offline client writes (P3) | read-only cache; limited offline queue; full sync | causal consistency/split brain | actual mobile/offline consumer |
| PD-T12-18 | Data migration | import legacy as unverified; reverify files; leave archival | сохранность истории vs ложная подтверждённость | sample real histories & preserved files |
| PD-T12-19 | Resource budgets | simple global concurrency; per-operation quotas; claim scheduler | простота vs saturation/starvation | measurements on target PCs/host |
| PD-T12-20 | Versioned AppDock contract | local-only baseline; conditional host/storage API | границы возможности и ответственности | current platform owner contract+E2E |

**Приоритет принятия:** сначала PD-01/02/03/07/08/09/18 как единый вертикальный slice, затем PD-04/05/06/11/12/15/19; P3-only решения после возникновения доказанного совместного профиля. Это **предлагаемая последовательность исследования/решений**, а не распоряжение на разработку.

## 16. Применение MADAR: методологическая проверка, без копирования онтологии

### 16.1. Нормативная опора `spec/` и кандидаты Stage 3

- **Действующий MADAR `spec/core/05-state-data-time-execution.md`:** durable state owner, commit semantics, data identity, retry/effect/reconciliation, migration и гарантия, соразмерная действительной платформе. Это **методологический критерий анализа**, а не готовая схема классов Strategy Box.
- **`spec/core/09-reliability-operations-observability-recovery.md`:** failure-mode, containment, degraded mode, capacity, наблюдаемость, проверенное восстановление; fallback добавляет собственные failure modes.
- **`spec/core/10-verification-validation-testing-assurance.md`:** claim → appropriate evidence → evaluation, пропорциональность, различие verification/validation/assurance, bounded evidence and independence.
- **`spec/core/11-human-ai-governance-engineering.md`:** stewardship, scope authority, AI как actor с ограниченными полномочиями, а не новый владелец прав.

Stage 3 **A3** поддерживает различие Commission/Work, execution, effects, result, acceptance и closure; **A5** — durable truth, actor-independent handoff и recovery; **A6** — claim/grounds/inference/reliance; **A2** — system boundaries and identity. **A8** уточняет, что typed semantic relations не превращаются автоматически в универсальную transitive closure.

Stage 3 **B3** требует проверять composition и причинный эффект как самостоятельные claims; **B4** — целостность доказательств, freshness и независимость; **B5** — полномочие на акт отдельно от сообщения, наличия роли или UI action; **B7** — изменения условий, миграция, revalidation и bounded closure; **B9** — достаточность, цена ошибок и экономичность метода. **A1/A4/A7 и B1/B2/B6/B8** просмотрены как смежные исследования конституции, участия, синтеза, требований, моделей, feasibility и доверенных границ; пересказ их полного содержания не требуется для этой конкретной предметной вертикали.

**Источник статусов:** MADAR `spec/` — current Editor's Draft; Stage 3 — non-normative Research. Этот анализ не объявляет положения A/B принятыми нормами даже при сильной исследовательской согласованности.

### 16.2. Семантическая проверка на EOM/EWM/EKM

| Ось | Что должна защитить в Strategy Box | Пример некорректного переноса |
|---|---|---|
| **EOM / object** | идентичность предметных datasets, operations, планов, артефактов и их реальные границы | раз `file path` одинаков, значит content и logical artifact тот же |
| **EWM / work** | цель и обязательство, разрешённый план, наблюдаемые эффекты, приёмка/закрытие | раз вызов закончился, значит Work завершена |
| **EKM / knowledge** | claim, grounds, неопределённость, релевантность, возможные defeaters | раз Excel создан, значит основание и вывод проверены |
| **Cross-cutting trust** | разрешение эффекта, опыт отказов, восстановление, защищённая информация | лог клиента является authority event |
| **Proportionality** | достаточная, но умеренная цена доказательств/ресурсов | для каждого расчёта создавать отдельный evidence service и approvals |

**Практический критерий:** если две сущности позволяют независимые вопросы, последствия или права — семантически различать их полезно. Если они всегда изменяются одной транзакцией и имеют одинаковый lifecycle — возможно их совместное физическое хранение. Методологические блоки EWM/EOM/EKM **не нужно** превращать в пакеты, таблицы и классы продукта.

## 17. Предложенная последовательность дальнейшей проверки (не кодовый план)

**Шаг 1 — утвердить тонкую семантику вертикального случая.** Выбрать одну реальную операцию без опасных эффектов и одну с управляемой файловой публикацией; согласовать admission/Run/Attempt/Result/Artifact/Assessment критерии. Выделить authority как логическую границу — процесс пока не выбирать.

**Шаг 2 — доказать файловую истину.** Написать conformance tests для LocalFileStore и реальных разрешённых backend variants: path containment, status distinctions, temp+verify+publish, wrong-digest, lost ACK, partial failure, multi-file artifact manifest. Систему безопасности не основывать на path normalization без boundary check.

**Шаг 3 — доказать долговременный минимальный учёт.** Определить typed state transition records, idempotency и corrupt-tail recovery; оценить single-writer журнал по RPO/RTO и объёму. Текущий JSON import должен сохранять записи как *legacy unverified*, а не как Published/Accepted.

**Шаг 4 — отделить Qt coordination.** Проверить application orchestration без UI, controlled cancellation, retries и recovery; оставить существующий semantic chat projector consumer. Не добавлять Android или host только ради архитектурного теста — достаточно headless unit/integration harness.

**Шаг 5 — оценить Work acceptance и UI.** В чате показывать минимум: «ожидает/выполняется/готов результат/нужна проверка/ошибка/исход неизвестен» с drill-down на технические и доказательные сведения. Убедиться, что UX не принуждает принимать неподтверждённые последствия.

**Шаг 6 — пересмотреть P3.** После появившейся потребности общего узла проверить authentication, host-bound storage, changes feed, worker lifecycle, artifact ACL и shared authority. Только тогда принимать headless process/deployment и более сложную инфраструктуру.

### 17.1. Минимальные exit criteria архитектурного proof-of-concept

1. Один сквозной тест связывает Work (если применима), pinned plan, Run, Attempt, domain Result, artifact digest, effect receipt, assessment, closure — с correlation по идентификаторам.
2. Ни один loss-of-ACK/timeout тест не превращает неизвестный внешний эффект в безусловный success или definite failed.
3. Повторное нажатие запуска/двойная доставка команды сохраняет idempotency semantics.
4. Аварийное прерывание сохраняет прежние опубликованные артефакты и достаточный record для честной разборки незавершённого effect.
5. Исполнительная логика запускается без Qt; GUI не является owner переходов в будущем shared профиле.
6. Прямой `stratbox` Python API остаётся самостоятельным способом использования доменных операций.
7. Артефакт с неправильным digest, невалидной schema либо неполной публикацией отсутствует в списке **подтверждённо опубликованных**.
8. Пользователь может отклонить математически валидный результат по своим заранее зафиксированным критериям; это не переписывает вычислительный факт.
9. У любой невыполненной существенной обязанности после закрытия есть scope, owner, срок/условие и понятная видимость.
10. Отдельно испытаны нагрузка и восстановление на целевых ресурсных ограничениях. Проверки не требуют новой службы до появления отдельного потребителя.

## 18. Область неопределённости и ограничения данного Research

**CURRENT подтверждено статически**, но не доказан эксплуатационный green-status. Не запускались единый Windows AppDock application graph, долгие SORS workloads, interruption/fault injection, сценарии с реально потерянным ACK, проверка file journal на отказном носителе, независимая приемка результата, совместное выполнение несколькими участниками.

**UNKNOWN:** какие именно atomic/durable guarantees дают все допустимые файловые/сетевые адаптеры; точная доступность будущих host/storage/collaboration interfaces AppDock; производительность и usability альтернатив B–D; нормативная модель управления Work acceptance; policies retention/security для разных продуктов.

**NOT APPLICABLE CURRENT:** remote multi-worker consensus, global distributed transactions, Kubernetes/external workflow-engine requirements, Android host executor, federated shared artifact catalog и обязательный zero-downtime online migration. Эти вопросы вновь актуализируются только при включении соответствующей функции и контракта.

**Граница публичности:** описание закрытых реализаций расширений не использовано в составе выводов и ссылок; публичная модель ограничена нейтральным `FileStore`, `SecretProvider`, runtime/capability interfaces и правилами effects. Конкретные защищённые окружения должны тестироваться отдельно с учётом их доступа и санкционированного контекста.

## 19. Реестр исследованных входов и проверяемые маршруты

### 19.1. Прямые implementation owners

- [`stratbox` main](https://github.com/ForestTiger-GH/stratbox/tree/928da3d768eb5932853a9035d683ed83a23f5c12): `AGENTS.md`, `_mw/AGENTS.md`, `src/stratbox/`, `pyproject.toml`, `docs/`, `tests/`; изменения после базового `beb3e484` не затронули runtime/tests/package owner.
- [`stratbox-windows` main](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b): `src/stratbox_windows/application/{scenarios,cases,operations,artifacts,history,background}/`, `runtime/`, `presentation/qt_desktop/scenario_coordinator.py`, `appdock/manifest.json`.
- [`AppDock` main](https://github.com/ForestTiger-GH/AppDock/tree/a4d87c643e620e54e04083d4d0b8d867513e7065): внешняя платформа, текущая интеграционная граница; дополнительно приложенный базовый документ `AppDock — описание продукта и проекта` (11 страниц), как продуктовая рамка, **не** доказательство доступности каждого будущего API.

**Особо важные исходники:**

- [Windows `scenarios/runner.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py)
- [Windows `operations/execution/runner.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/execution/runner.py)
- [Windows `history/persistence.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py)
- [Windows `cases/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/cases/models.py)
- [Windows `artifacts/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/artifacts/models.py)
- [Windows `scenario_coordinator.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py)
- [Windows `appdock/manifest.json`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json)

### 19.2. Strategy Box Research 02 и 03

- [02-base-study — каталог](https://github.com/ForestTiger-GH/stratbox/tree/928da3d768eb5932853a9035d683ed83a23f5c12/_mw/epochs-001-strategy-box-development/research/02-base-study). В особенности исследования core/surface, execution control, commands/scenarios/cascades, background processes, files/artifacts, observability, single-node multiuser, machine schemes, core/application boundary.
- [03-consolidation-research — каталог](https://github.com/ForestTiger-GH/stratbox/tree/928da3d768eb5932853a9035d683ed83a23f5c12/_mw/epochs-001-strategy-box-development/research/03-consolidation-research). Темы 02 canonical semantics, 04 Work→Execution, 05 State/Persistence, 06 Automation, 08 Trust/Safety, 09 Whole-System — ключевые.
- [03/02 Canonical Semantic Model](https://github.com/ForestTiger-GH/stratbox/blob/928da3d768eb5932853a9035d683ed83a23f5c12/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_02_canonical_semantic_model_2026-10-08.md)
- [03/04 Work to Execution](https://github.com/ForestTiger-GH/stratbox/blob/928da3d768eb5932853a9035d683ed83a23f5c12/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_04_work_to_execution_consolidated_research_2026-10-09.md)
- [03/05 State/Persistence/Collaboration](https://github.com/ForestTiger-GH/stratbox/blob/928da3d768eb5932853a9035d683ed83a23f5c12/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_05_state_persistence_collaboration_consolidated_research_2026-10-09.md)
- [03/08 Trust/Safety](https://github.com/ForestTiger-GH/stratbox/blob/928da3d768eb5932853a9035d683ed83a23f5c12/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md)
- [03/09 Whole-System](https://github.com/ForestTiger-GH/stratbox/blob/928da3d768eb5932853a9035d683ed83a23f5c12/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_09_whole_system_target_architecture_2026-10-09.md)

### 19.3. Отдельные исследования 04, темы 01–11

**Все существующие 11 темы учтены как Research, а не Product admission.** Ссылки ведут на единый [каталог 04-ai-raised-topics](https://github.com/ForestTiger-GH/stratbox/tree/928da3d768eb5932853a9035d683ed83a23f5c12/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics). Разделение по текущему исследовательскому вкладу:

| Тема | Предмет | Использование в теме 12 |
|---|---|---|
| 01 | Ontology операций/сценариев | Operation, Composition, Scenario, Scheme, effective definition |
| 02 | Задания и execution control | durable accounting, cancellation, retry/unknown, checkpoints |
| 03 | State/persistence/recovery | single authority, single-writer journal/DB-agnostic persistence, AppDock roots |
| 04 | Artifact lifecycle | production vs verification vs publish/ACL, immutable generations |
| 05 | Authority/security/multiuser | grants, actor identity, destructive actions, access-filtered reads |
| 06 | Machine interfaces/capability catalog | agent capability ≠ grant, machine projection and admission |
| 07 | Cross-platform applications | Qt-neutral semantics, clients vs execution authority |
| 08 | Observability/diagnostics | progress/event/log/problem separation; uncertain effects; safe projections |
| 09 | Source versions/reproducibility | source identity/freshness/registry snapshots; reproducible results |
| 10 | Responsibility/integration contracts | core/application/AppDock boundary, host options, owner-of-truth |
| 11 | MADAR alignment | EOM/EWM/EKM, methodology status and proportional evidence |

### 19.4. Действующие/кандидатные `docs/`

- [`docs/PUBLICATION-MANIFEST.md`](https://github.com/ForestTiger-GH/stratbox/blob/928da3d768eb5932853a9035d683ed83a23f5c12/docs/PUBLICATION-MANIFEST.md): ограниченный publication status, незавершённость admission и verification.
- [`docs/current-how/windows-application.md`](https://github.com/ForestTiger-GH/stratbox/blob/928da3d768eb5932853a9035d683ed83a23f5c12/docs/current-how/windows-application.md): ограниченные CURRENT code-backed наблюдения.
- [`docs/how/execution/execution-and-effects.md`](https://github.com/ForestTiger-GH/stratbox/blob/928da3d768eb5932853a9035d683ed83a23f5c12/docs/how/execution/execution-and-effects.md): **candidate** HOW.
- [`docs/ldd/artifacts/staged-publication.md`](https://github.com/ForestTiger-GH/stratbox/blob/928da3d768eb5932853a9035d683ed83a23f5c12/docs/ldd/artifacts/staged-publication.md): **candidate** LDD.
- [`docs/architecture/responsibility-allocation.md`](https://github.com/ForestTiger-GH/stratbox/blob/928da3d768eb5932853a9035d683ed83a23f5c12/docs/architecture/responsibility-allocation.md): **candidate** ownership allocation.
- [`docs/what/README.md`](https://github.com/ForestTiger-GH/stratbox/blob/928da3d768eb5932853a9035d683ed83a23f5c12/docs/what/README.md): Target WHAT — mixed accepted boundaries / unadmitted candidate mechanisms.

### 19.5. MADAR: действующий owner и Stage 3

- [MADAR `spec/`](https://github.com/ForestTiger-GH/MADAR/tree/7029b47676659161d9f54b4def8f0c1aa979b614/spec), [manifest](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/spec/manifest.yaml).
- [Stage 3 Development Inputs A1–A8 и B1–B9](https://github.com/ForestTiger-GH/MADAR/tree/7029b47676659161d9f54b4def8f0c1aa979b614/_mw/research/05_consolidation-input-research/results).
- [A3 — Commissioned Work, Execution, Effects, Results, Acceptance and Closure](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/_mw/research/05_consolidation-input-research/results/A3_Commissioned_Work_Execution_Effects_Results_Acceptance_and_Closure_2026-10-02.md).
- [A5 — Durable Work State, Artifact Ownership, Recovery and Handoff](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/_mw/research/05_consolidation-input-research/results/A5_Durable_Work_State_Artifact_Ownership_Workspaces_Recovery_and_Handoff_2026-10-04.md).
- [A6 — Knowledge Claims, Grounds, Uncertainty, Reliance](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/_mw/research/05_consolidation-input-research/results/A6_Engineering_Knowledge_Claims_Grounds_Uncertainty_Validity_and_Reliance_2026-10-05.md).
- [B3 — Structure, Composition, State, Time, Causality and Effects](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/_mw/research/05_consolidation-input-research/results/B3_Structure_Composition_State_Time_Causality_and_Effects_2026-10-07.md).
- [B4 — Evidence, Assurance, Independence, Freshness and Bounded Reliance](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/_mw/research/05_consolidation-input-research/results/B4_Evidence_Assurance_Independence_Freshness_and_Bounded_Reliance_2026-10-07.md).
- [B5 — Authority, Participation, Interaction and Institutional Coordination](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/_mw/research/05_consolidation-input-research/results/B5_Authority_Participation_Interaction_and_Institutional_Coordination_2026-10-08.md).
- [B7 — Governed Change, Continuity and Recovery](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/_mw/research/05_consolidation-input-research/results/B7_Governing_Change_Continuity_Recovery_Migration_and_Bounded_Closure_2026-10-09.md).
- [B9 — Proportionality, Sufficient Context, Resource-Bounded Work](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/_mw/research/05_consolidation-input-research/results/B9_Proportionality_Sufficient_Context_Resource_Bounded_Work_and_Method_Economics_2026-10-10.md).
- [MADAR consolidation state](https://github.com/ForestTiger-GH/MADAR/blob/7029b47676659161d9f54b4def8f0c1aa979b614/_mw/consolidation/STATE.md): Stage 3 активен; будущий Product ещё не заменил `spec/`.

---

## 20. Заключение

Strategy Box **не нуждается в новой «тотальной» онтологии ради полноты схемы**. Он нуждается в доказанной непрерывности конкретной пользовательской работы — от того, *кто и зачем поручил*, через то, *что разрешили и что реально исполняли*, к тому, *какие физические последствия произошли, какие аналитические выводы оправданы, какие файлы подтверждённо опубликованы и кто на каком основании признал результат достаточным*.

Сегодня устойчиво определены и достаточно исследованы **смысловые границы**, но не все **переходы, receipts и владельцы долговременной истины**. Ближайшая ценность — один небольшой проверенный локальный контур end-to-end с честным `UNKNOWN`, стабильными идентификаторами, versioned plan, safe artifact publication и ясным разделением Work/Run/Attempt/Acceptance. После него появится проверяемая основа для background/host/multiuser/Android без миграции смысла и без преждевременного комплекса служб.

**Итоговый критерий:** если приложение может после внезапного отключения честно ответить «что мне поручили, что действительно запускалось, что могло изменить мир, что уже доказано, что только предполагается, какие файлы безопасны и что ещё должен сделать человек», — сквозная модель начинает работать. Если вместо этого единственным ответом остаётся `success/failed` и путь к файлу, архитектурная целостность пока не достигнута.
