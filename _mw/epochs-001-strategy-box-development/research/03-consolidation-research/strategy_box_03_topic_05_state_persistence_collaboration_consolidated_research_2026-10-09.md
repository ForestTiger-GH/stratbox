# Strategy Box — консолидирующее исследование 05: State, Persistence & Collaboration

**Дата:** 2026-10-09  
**Программа:** третья исследовательская ветка `03-consolidation-research`, тема **05 — State, Persistence & Collaboration**  
**Статус:** **Research Synthesis / Consolidation Result**. Не является Product Decision, утверждённой целевой спецификацией API или изменением реализации.  
**Основной корпус:** исследования `02-base-study`; согласование с результатами тем 00–04 третьей ветки. `01-old-notes` — только исторический источник.  
**Фактические baseline:** `stratbox-windows` `main`, commit `959e9c4ce1441124af5111c1e025041714e04d3b` (реализация 2026-08-05; непосредственная выборочная проверка файлов 2026-10-09); `stratbox` — исследование commit `e9688535` от 2026-10-06 и контрольный `6c371407` от 2026-10-09 согласно теме 04. Дополнительно проверены публичные контракты AppDock (`main`) и официальная документация SQLite.  
**Граница публикации:** документ пригоден для открытого исследовательского контура Strategy Box: исключительно нейтральные extension contracts, без сведений об устройстве закрытых реализаций. Методологические идеи доказательности используются без описания структуры сторонних исследовательских систем.  
**Изменения в репозиториях:** отсутствуют. Файл создан для передачи в чат.

---

## 0. Executive synthesis

### 0.1. Центральный вывод

**[CONSOLIDATED]** Источник достоверного длительно живущего состояния Strategy Box должен находиться в **platform-neutral application/runtime authority конкретного узла или соответствующей серверной области**, доступной через один command/query/subscription contract. Windows, Web и Android — клиенты этого состояния. Открытое окно, Qt-поток, локальная JSON-история и файловый проводник не должны определять, существует ли Work, идёт ли Job и кому поручена проверка результата.

Это не означает, что *вся* истина должна лежать в одной SQL-базе. Истина разбита по ответственностям:

1. **AppDock** — узел, установка и активация среды, platform session lifecycle, средовые roots, доступность хоста и платформенная диагностика.
2. **Strategy Box application/runtime** — Work, Thread, Run/Job/Attempt, события продукта, задания, автоматизации, разрешения на продуктовые действия, уведомления, пользовательский каталог артефактов и их связи.
3. **`stratbox`** — предметная семантика банковских/макроэкономических данных, определения источников и операций, provenance вычисления, валидация, аналитический результат и его доказательные основания.
4. **FileStore / managed object storage** — физические байты, immutability, checksums и материализации; storage не определяет сам пользовательский lifecycle Work.
5. **Поверхности** — локальные drafts, layout, краткоживущие projections и безопасные кэши.

**[TARGET-HYPOTHESIS]** Для первой зрелой реализации достаточно *одного node authority service* и одного транзакционного metadata store (SQLite на локальном диске одиночного узла), а также отдельных управляемых файловых областей и маленьких атомарно сохраняемых файлов настроек/локальных drafts. Для нагруженного web/self-hosted профиля — тот же семантический контракт с серверным transactional store (основной кандидат PostgreSQL). Создавать различные онтологии для двух СУБД, вводить полный event sourcing, строить обязательный CAS для каждого файла или новый репозиторий для каждого слоя оснований пока нет.

### 0.2. Десять устойчивых положений

| № | Положение | Статус |
|---|---|---|
| 1 | Durable Work/Job state не зависит от жизни Windows/Web/Android surface | **CONSOLIDATED** |
| 2 | Текущая Windows history — пять локальных JSON-проекций, без общей транзакции и строгой обработки повреждений | **CURRENT** |
| 3 | `AppDock.Session` и `StrategyBox.Run` — разные lifecycle: один не заменяет другой | **CONSOLIDATED** |
| 4 | Персональное прочтение, подтверждения и предпочтения не мутируют общие события | **CONSOLIDATED** |
| 5 | Любая shared mutation идёт через authority, проверку прав, revision и транзакционный commit | **TARGET-HYPOTHESIS**, сильная межисследовательская поддержка |
| 6 | События предоставляют причинную историю; актуальная таблица состояния нужна для удобных команд и запросов | **CONSOLIDATED**, выбор физической модели остаётся целевым |
| 7 | Artifact manifest, user artifact catalog и physical materialization — три разных ответственности | **CONSOLIDATED** |
| 8 | Offline surface может показывать последнее известное состояние, но обязана сообщать о его устаревании | **CONSOLIDATED** |
| 9 | Crash recovery требует reconciliation и проверки эффектов, а не автоматической замены `running` на `failed` | **CONSOLIDATED** |
| 10 | Persisted schema обязана эволюционировать управляемо, даже если проект не поддерживает старые публичные runtime API | **CONSOLIDATED** |

### 0.3. Главный архитектурный разрыв

**[CURRENT]** `stratbox-windows` хранит cases/events/artifacts/logs/assignments локально, в памяти и в пяти JSON-файлах. `unread` записан внутри общего объекта case/event; `BackgroundProcessStore` имеет только память процесса; `PresenceService` строит локальный список участников. Часть AppDock runtime-state существует отдельно в JSON-surface. Наличие в интерфейсе «Участников», «Фоновых» или «Поручений» сегодня не доказывает существования общей многопользовательской истины или scheduler. Подтверждения: [W-HISTORY], [W-CASE], [W-PRESENCE], [W-BACKGROUND], [B-WINDOWS].

**[TARGET-HYPOTHESIS]** Выход — не синхронизировать эти JSON между устройствами, а создать **единый authority над изменениями**. Клиент получает согласованный snapshot с cursor, следит за разрешёнными изменениями и отправляет команды с `expected_revision` и `idempotency_key`.

### 0.4. Не стоит смешивать три значения слова «состояние»

- **Authoritative state** — факт, от которого зависит юридически/операционно значимое решение: назначение, прогресс задания, result acceptance, publishing, permissions, schedule occurrence.
- **Recoverable projection** — рассчитанная из авторитетных данных карточка, счётчик, очередь для интерфейса, поисковый индекс, прогресс, presence aggregate.
- **Local convenience state** — размер окна, фильтр, выбранная вкладка, незапущенный черновик.

Для каждого из них нужны разные длительность жизни, режим записи, требования к восстановлению и права доступа. Превратить все три в одну «системную БД» — такая же архитектурная ошибка, как оставлять всё в `app.json`.

---

## 1. Метод, область исследования и дисциплина утверждений

### 1.1. Точный охват темы

По [PROGRAM] и [R00] тема 05 включает: `configuration`, `preferences`, `surface state`, `draft state`, `thread/work/execution/automation state`, `artifact metadata`, `provenance`, `user state`, `presence`, `read cursors`, `assignments`, `node-local`, `shared-node` и `host state`. Для каждого типа должны быть определены **owner, scope, lifetime, persistence, schema version, concurrency, recovery, projection**.

Учитываются особенности действий из темы 04 (состояния Run/Job, retries, effects, cancellation), данных и артефактов из темы 03, семантика темы 02, а также предшествующие исследования 02-base-study по multi-user, web/self-hosted, settings, observability, automation и файлам. Без этого persistence-проектирование создаст фальшивые сущности или потеряет важные связи.

### 1.2. Классы выводов

- **CURRENT** — подтверждённый факт о проверенной реализации и указанном срезе.
- **CONSOLIDATED** — устойчивый смысловой вывод из нескольких источников, пока ещё не равный утверждённому Product Decision.
- **TARGET-HYPOTHESIS** — предложенный контракт/решение, требующий согласования, реализации или пилота.
- **CONFLICT** — несовместимые трактовки, не сводимые к различию масштаба.
- **SUPERSEDED** — прежнее допущение, вытесненное текущим кодом или более точным исследовательским выводом.
- **UNKNOWN** — материала недостаточно, выбор необходимо проверить.

SQL, JSON и API-фрагменты ниже — **иллюстративные target contracts**, не описания готовой реализации. Требование «без обратной совместимости» относится к проектированию новой публичной архитектуры; оно не разрешает незаметно уничтожать существующую ценную историю пользователя.

### 1.3. Границы ownership

Применяется порядок **responsibility → owner → contract → physical carrier**. `stratbox-host`, `stratbox-core`, общий application package и отдельный сервер — возможные физические носители, а не заранее принятые репозитории. Сложность темы 05 сама по себе не требует создавать новый репозиторий. [R01], [R04].

---

## 2. Текущее состояние: факты и проверка кода

### 2.1. `stratbox-windows`: пять JSON-проекций, фактически локальный state

**[CURRENT]** `HistoryPersistenceService` находится в `src/stratbox_windows/application/history/persistence.py`. Он записывает `cases.json`, `events.json`, `artifacts.json`, `logs.json`, `assignments.json` в app-owned `runtime/history/`. При сохранении вызываются пять отдельных `_save_list`, использующих прямой `Path.write_text(json.dumps(...))`; общего атомарного commit нет. Загрузка `_load_list` возвращает `[]`, если файл отсутствует, повреждён, имеет неподходящий тип; отдельные невалидные записи в `_decode_*` пропускаются. Это даёт пользовательскую *видимость пустой истории* после сбоя чтения. Смысл сервиса даже в docstring ограничен «recent context», без претензии на database-grade durability. [W-HISTORY].

**[CURRENT]** `ScenarioCaseStore`, `OperationalEventStore`, `ArtifactStore`, `LogStore`, `AssignmentStore` — in-memory коллекции с `replace_all`, `add/upsert` и запросами. Актуальный порядок событий в модели основан преимущественно на timestamp, не на глобальном commit sequence. Shared-state transactions, ACL и optimistic revisions в этих stores отсутствуют. [W-CASE], [W-EVENT].

**[CURRENT]** `ScenarioRunCase` включает `case_id`, `scenario_id`, параметры, статус, timestamps, author, step runs, outputs, message и `unread: bool`. `OperationalEvent` также хранит `unread: bool`. Рядом существуют `EventKind` и `ActorKind`, пригодные для будущей общей истории; `unread` же имеет неправильную область ответственности для двух пользователей. [W-CASE], [W-EVENT], [B-MULTI].

**[CURRENT]** В GUI long-running scenarios идут через Qt coordinator/QThread; одновременно принимается один сценарий. Модель cancellation-status есть, но реального общего cancellation protocol нет. Это ограничение **локального приложения**, а не права всей будущей node queue. [B-WINDOWS], [R04].

### 2.2. Конфигурация и черновики

**[CURRENT]** `AppUserConfig` объединяет `window`, `shell`, `chat`, `last_scenario_id`, `last_workspace_schema` и `scenario_form_values`. `PreferencesService` сохраняет всё это одним `save_user_config()` прямой записью JSON. Запись неатомарна, явной версии пользовательской схемы нет. Важный нюанс: `load_user_config()` в отличие от загрузки истории **выбрасывает `AppConfigError` при невалидном JSON**, а не молча сбрасывает данные. Смешивать эти два error-path нельзя. [W-CONFIG], [W-PREF], [B-SETTINGS].

**[CURRENT]** `runtime/session_runtime.py` содержит AppDock-facing session/user/runtime-state модели и версии контрактов; пишет runtime JSON surfaces. Эти данные описывают связь с платформой и текущим запуском, но не образуют Work/Job store. [W-SESSION].

### 2.3. Presence, поручения, автоматизации

**[CURRENT]** `PresenceService` создаёт запись текущего пользователя, отмечает authors из cases и рассчитывает локальный список. `is_online=True` текущему пользователю не является ответом общего сервера на вопрос о других сессиях. Нет общесистемного presence subscription. [W-PRESENCE].

**[CURRENT]** `AssignmentStore` — локальная mutable collection, фактические поручения сохраняются в пятом JSON-файле. Нет общей доставки и согласования конкурентных изменений. [W-ASSIGN].

**[CURRENT]** `BackgroundProcessStore` хранит спецификации и включённость в памяти, а методы `set_enabled`, `mark_running`, `mark_result`, `mark_error` только меняют state objects. Никакого durable schedule occurrence или actor, выполняющего процесс после закрытия GUI, этот класс не даёт. [W-BACKGROUND].

### 2.4. `stratbox` и AppDock — что важно именно для хранения

**[CURRENT]** `stratbox` содержит FileStore/IO, доменные pipelines, данные и специализированные модели provenance. Он не является общим shared Work/Thread/Job collaboration service. Core способен выдавать доменные результаты без UI — архитектурно это сохраняется. [B-CORE], [R03].

**[CURRENT]** В AppDock существуют отдельные domain owners узла и сессий, `ActiveSessionsStore` сохраняет per-session JSON projections атомарной записью, а observability имеет собственную модель `ProblemOccurrence/ProblemRef`. AppDock прямо разграничивает Node и Sessions, а problem journal ещё не является универсально подключённой системой для всех прикладных ошибок. Наличие платформенной активности не подтверждает ни сохранность Strategy Box Work, ни delivery всех его продуктовых событий. [A-NODE], [A-SESSIONS], [A-ACTIVE], [A-OBS].

### 2.5. Таблица разрыва

| Область | Current | Что отсутствует для mature shared state |
|---|---|---|
| История запусков | отдельные локальные JSON | атомарность, схема, shared authority, conflict detection |
| Work/Thread | текущие Case/чат-проекции | долговременная Work identity и независимое отношение Thread ↔ Work |
| Job | Qt one-active scenario | node JobManager, durable queue, worker leases |
| Automation | registry/in-memory flags | persisted spec/revision, occurrence, scheduler cursor |
| Presence | локальный список участников | session-based provider, TTL/stale semantics |
| Assignments | локальные записи | ACL, revision, receipts, shared notifications |
| Read/unread | bool в Case/Event | per-principal cursors и адресные receipts |
| Artifact | path-linked metadata | manifest/identity/lineage, publish coordination, retention |
| Settings | один app.json | scope split, atomic writes, managed overrides |
| Problems | технические logs и platform bridge | typed refs, audience-safe product propagation |
| Remote client | потенциальная роль | snapshot+event transport, stale and reconnect |

**Граница достоверности:** таблица — code/baseline snapshot, не результат запуска интеграционных тестов в данном исследовании.

---

## 3. Единая карта состояния Strategy Box

### 3.1. Оси классификации

Каждая хранимая сущность должна иметь набор независимых атрибутов:

- **Owner** — кто утверждает истинность записи и принимает команды.
- **Authority scope** — deployment, node, workspace, team/Work, principal, session, surface/device, Run.
- **Identity** — стабильный ID и parent scope; абсолютный path не заменяет identity.
- **Lifetime** — процесс, сессия, Work, политика retention, неизменяемая история.
- **Mutability** — immutable snapshot, revisioned aggregate, append-only event или regenerable projection.
- **Persistence** — БД, atomic small file, managed blob, memory-only, external platform surface.
- **Concurrency** — single-owner, optimistic concurrency, unique occurrence, lease/fencing, read only.
- **Recovery** — authoritative reload, evidence reconciliation, recreate from source, reset-as-convenience.
- **Projection** — что вправе видеть конкретный клиент и при какой задержке/степени свежести.

### 3.2. Матрица scope / owner / lifetime / storage / recovery

| Состояние | Канонический owner | Scope и длительность | Предпочтительный persistence profile | Concurrency / recovery |
|---|---|---|---|---|
| Install/Node identity, roots, platform health | AppDock | node/install; до удаления среды | AppDock-owned state | platform lifecycle; только безопасная projection |
| User identity/Session lifecycle | AppDock identity/sessions | principal/session | platform store | platform commands; heartbeat/stale |
| Strategy Box product capability grants | app authority в рамках platform identity/policy | principal × resource × action, policy revision | shared transactional store | authorize at mutation, deny by default |
| UserSettings | application settings owner | principal, долгоживущие | atomic JSON или user-scoped records | validated update; conflict if cross-device |
| ManagedPolicy | AppDock/deployment либо явный product admin-owner | deployment/node/workspace | authoritative policy source | forced/allowed constraints; revision |
| SurfaceState | конкретная surface | device × user; resettable | local atomic small file | local last-write acceptable |
| RecentState/DraftState | surface/application draft service | user × device/Thread/Scenario | local atomic JSON; sensitive excluded | versioned form, cleanup stale |
| Thread и сообщения | application collaboration owner | node/team/private conversation; retained | transactional DB | ACL, message order, edit history |
| Work + requirements + closure | application Work owner | node/workspace/team; длительный | transactional DB | revisioned, not tied to current UI |
| Work↔Thread memberships | application collaboration owner | many-to-many, permission-filtered | transactional DB | link/unlink command, revision |
| Run/Plan/Binding | application execution owner | Work/Run; immutable execution snapshot | transactional DB + version refs | new Run for changed plan; recovery |
| Job/OperationRun/Attempt | application execution owner | Run/Job; до terminal+retention | transactional DB | transactional transition; worker custody |
| Effect intent/receipt | application execution/effect owner | Run/Job/effect key; retained for audit | transactional records and evidence refs | dedup, reconcile UNKNOWN |
| Automation/Trigger/Occurrence | application automation owner | node/workspace/owner | transactional DB | unique occurrence, revision, misfire |
| Activity/Event log | application event owner | node/authorized streams; append-only | transactional journal + outbox | ordered commit, replay/projection rebuild |
| Artifact user catalog/link/ACL | application artifact owner | node/workspace/Work | transactional DB | publish status, revision, retention |
| Artifact content manifest | artifact/content owner with core provenance | artifact/version, durable | immutable file/object | hash+manifest verify; reindex |
| SourceSnapshot/DatasetVersion/evidence | `stratbox` domain semantics; runtime stores refs | source/dataset/reproducibility horizon | domain manifest/managed bytes + refs | immutable identity, provenance checks |
| User read cursor | app collaboration owner | principal × feed/Thread/Work | transactional DB | monotonic advance, per-user |
| Notification/receipt | app notification owner | target principal; until TTL/action | transactional DB | unique dedup, per-user ack |
| Assignment/Approval | app collaboration/authority owner | shared, actor-scoped | transactional DB | revision/permission, expiry |
| Presence | AppDock sessions → app-derived projection | node × user, короткоживущее | cache/projection; minimal session history | TTL, stale status, no heartbeat event spam |
| ProblemRef/product problem linkage | app domain link; platform ProblemOccurrence owner — AppDock | run/step/node | DB refs + platform journal | reference exact occurrence, no text cloning |
| Logs and telemetry | operation/node observability owners | run/process; separate retention | managed files/journals; DB refs | redaction, rotation, support bundle |
| Search index/UI materialized view | application read projection | node/scope, regenerable | embedded index/FTS or DB query | reindex from authority, never own facts |

**[CONSOLIDATED]** Одна и та же физическая БД вправе обслуживать несколько строк матрицы; совпадение носителя не объединяет их смысловые owners. И наоборот, `Artifact` может иметь canonical identity и два разных долговременных носителя — metadata DB и immutable manifest — без противоречия, если разделены их поля и порядок commit.

### 3.3. Последовательность выбора механизма хранения

```
Есть ли самостоятельный business lifecycle и shared mutation?
  → да: transactional authority / revisions / constraints
  → нет: можно ли строго восстановить из authority?
       → да: projection/cache с rebuild contract
       → нет: имеет ли объект стабильное переносимое содержимое?
            → да: immutable managed object + manifest
            → нет: это редкий small configuration либо device draft?
                 → atomic small file; sensitivity/version policy
```

Эта эвристика полезнее правила «всё в SQLite» и предотвращает разрастание модели.

---
## 4. Целевая authority model: одно изменение — один принимающий владелец

### 4.1. Узел как область консистентности, а не просто папка

**[TARGET-HYPOTHESIS]** У каждого node deployment есть стабильный `node_id`, связанный с AppDock identity. Strategy Box application runtime получает его через доверенный contract и создаёт собственную **product store identity** (`store_id`, `node_id`, `schema_version`, `generation`, `created_at`). Это защищает от случайной подмены/копирования рабочей БД в чужой node, а также от двойного запуска двух independent authorities на одной базе.

Одновременно активен **один логический writer/command authority** на authoritative scope. Он может использовать несколько worker processes, но только через централизованное принятие commands и transactional store. Это правило не означает «один Job за раз». Worker-физика и authority-логика различаются.

Веб-сервер, Qt-приложение, Android и автоматизация обращаются к одному service contract; он отвечает за identities, permission checks, validation, idempotency, state mutations и событие commit. AppDock может управлять жизненным циклом процесса, но не принимает за приложение решение, считать ли банковский расчёт завершённым и принятым.

### 4.2. Необходимые единицы записи

**Work aggregate:** цель, requirements, owner, visibility, acceptance/closure, links на Runs/Threads.  
**Run aggregate:** конкретная попытка достижения Work с immutable request+plan/binding snapshot.  
**Job aggregate:** schedulable единица с состоянием, execution custody, resource claims, transitions.  
**Automation aggregate:** definition+revision+trigger cursor+activation policy.  
**Assignment aggregate:** assignee, creator, review target, state, due/expiry, authority.  
**Artifact aggregate:** логический объект, опубликованные версии, Work/Run links, статус retention.  
**Thread aggregate:** сообщения, связи, разрешённая аудитория, пользовательские feed cursors.

**[CONSOLIDATED]** Эти агрегаты могут иметь отдельные таблицы только при реальном самостоятельном жизненном цикле; не нужно создавать class/table на каждое слово из темы 02. Для первого pilot рационально начать с Work/Run/Job/events/artifacts и постепенно добавить назначения и automation, а не внедрять полностью пустую онтологию.

### 4.3. `Thread`, `Work`, `Case`, `Job`: устранение двусмысленности

| Термин | Смысл и lifecycle | Чего он не заменяет |
|---|---|---|
| `Thread` | контекст сообщений, обсуждений, ссылок и активности | Work, Job, security principal |
| `Work` | долговременное обязательство добиться/оценить результат; может пережить несколько запусков | отдельный Run |
| `Run` | конкретный эпизод выполнения Work по фиксированному плану | постоянную Work identity |
| `Job` | единица очереди/исполнения в Run | человеческое поручение |
| `Attempt` | фактическая попытка конкретного исполнения с собственным custody/effect trace | новый Work |
| `Case` | **CURRENT:** запись запуска; **TARGET:** UI-словарь/переходная проекция; first-class Case требует отдельного доказательства | не вводить рядом с Work и Run просто ради старого названия |
| `Assignment` | человеческое обязательство/запрос решения | worker Job |

**[TARGET-HYPOTHESIS]** `work_threads(work_id, thread_id, visibility_policy, added_at)` позволяет одной работе появляться в разных обсуждениях с разной аудиторией. Содержимое private Thread не становится общедоступным только из-за ссылки на shared Work. Команда `ArchiveThread` не вызывает `CancelRun`, а `DeleteThread` не стирает evidence работы.

### 4.4. Семантика “долговременная работа” должна оставаться экономной

Не каждый click, tool call или diagnostic probe должен создавать Work. `Work` появляется, когда есть намерение/результат, к которому возвращаются, который надо принять либо который требует независимого жизненного цикла. Одношаговый диагностический вызов может иметь Run/Job без отдельной долгоживущей Work, **если эта упрощённая форма предусмотрена единым execution contract**; иначе система раздует пустые Work records. Действия с аудитом и эффектами всё равно получают identities. Это открытая продуктовая развилка, а не утверждение CURRENT. [R02], [R04].

---

## 5. Persistence architecture: физический выбор без раздвоения смысла

### 5.1. Рекомендуемые deployment profiles

| Профиль | Writer authority | Metadata store | Клиенты | Главный trade-off |
|---|---|---|---|---|
| Локальный Windows/малый headless node | один локальный headless application service | **SQLite на локальном диске узла**, WAL при проверке файловой среды | desktop через in-process/IPC/loopback adapter | простая поставка, ограниченная write concurrency |
| Малый self-hosted Web | один application service | тот же SQLite local-node либо PostgreSQL | browser/Windows/Android через API | выбор определяется реальной нагрузкой и операционными требованиями |
| Нагруженный server/multi-worker | единый логический command authority с распределёнными executors | PostgreSQL или равнозначный server transactional store | все surfaces | deployment/backup/operations сложнее |
| Временный standalone development | локальный service/in-process facade | ephemeral SQLite | development UI и тесты | никогда не считать dev state production truth |

**CONFLICT, разрешённый как scope difference:** `02-base-study` по multi-user рекомендует SQLite для одного узла, web/self-hosted — PostgreSQL для серьёзного web production. Противоречия нет, если semantic API один и DB engine является profile choice. **UNKNOWN:** критерии нагрузки, начиная с которых переходить на PostgreSQL, нуждаются в измерении и тестовом deployment, а не в произвольном числе пользователей. [B-MULTI], [B-WEB].

**Внешняя проверка:** официальная [документация SQLite WAL](https://www.sqlite.org/wal.html) подтверждает одновременное чтение/запись с одним writer, а также принципиальное ограничение: WAL **не работает через сетевую файловую систему между хостами**. Прямое открытие metadata SQLite с Windows и Android через SMB исключено. SQLite backup должен выполняться через online backup API / корректный snapshot, а не копированием live `.db` отдельно от WAL/sidecar-файлов ([SQLite Backup API](https://www.sqlite.org/backup.html)).

### 5.2. Границы физической памяти

```
AppDock-managed node system root            (platform owner)
  ├─ node/session/activation/health surfaces
  └─ Strategy Box application-owned area    (product owner)
       ├─ metadata store                    ← transactional truth
       ├─ manifests/                        ← immutable content/provenance
       ├─ artifacts/                        ← managed published bytes
       ├─ staging/                          ← uncommitted writes
       ├─ logs/                             ← bounded technical evidence
       ├─ snapshots/backups/                ← controlled retention; off-node copy
       └─ runtime/                          ← cache, process state, projections

Selected Data root / Workspace              (data owner/policy)
  ├─ input/
  ├─ output/
  └─ user-managed files

Client profile/device                        (surface owner)
  ├─ user settings / allowed sync projection
  ├─ window/layout state
  └─ drafts / reconnect cursor / safe cache
```

Это **логическая раскладка**, а не требование к точным каталогам AppDock или уже существующим именам. Managed artifact area и user workspace могут физически находиться на разных устройствах. Размещение под AppDock roots не передаёт AppDock право менять семантику Work.

### 5.3. Минимальный `PersistencePort`

**[TARGET-HYPOTHESIS]** Не создавать универсальный `Store[T]` с десятками невидимых side effects. Полезнее небольшие предметные порты: `WorkRepository`, `ExecutionRepository`, `AutomationRepository`, `CollaborationRepository`, `ArtifactCatalogRepository`, объединённые `UnitOfWork/Transaction` для межагрегатного commit. Дополнительно: `EventReader`, `OutboxPublisher`, `SchemaManager`, `BackupCoordinator`, `ReconciliationReader`.

Физический SQLite- или PostgreSQL-adapter обязан удовлетворять одному набору контрактных тестов: atomic transitions, unique IDs, CAS/revisions, ordered event publication, foreign keys/relationships, recovery и ровно одна terminal outcome. SQL dialect leakage в UI/operation descriptions запрещается.

### 5.4. SQL tables + append-only domain events — предпочтительный старт

**[TARGET-HYPOTHESIS]** Для Strategy Box рациональнее **transactional aggregate tables плюс append-only application events и outbox**, чем mandatory event-sourcing для каждой сущности. Текущий status Job, actor grant и owner Work являются легко запрашиваемыми current facts; события отвечают «когда и почему произошло изменение». При обычном event-sourcing потребовались бы elaborate replay/upcasting, snapshot policy и контроль сложной event-schema migration до появления измеримой пользы.

Важно не утверждать, что вся таблица/модель пересобирается из event log, если в событиях не сохранены полные semantic deltas. **Контракт восстановления должен быть конкретным для каждой projection.** Immutable event history содержит неизменяемые facts, а состояние ACL или snapshot может поддерживаться по действующей версионированной модели; они обязаны согласовываться одной транзакцией.

### 5.5. Event log, outbox и payload version

Предлагаемые поля:

```text
product_event:
  event_id, node_id, node_seq, aggregate_type, aggregate_id,
  aggregate_revision, event_type, event_schema_version,
  occurred_at_utc, committed_at_utc,
  actor_principal_id, actor_kind, session_ref?,
  work_id?, run_id?, job_id?, correlation_id, causation_id,
  audience_class, safe_payload, private_payload_ref?

outbox_delivery:
  delivery_id, event_id, destination, delivery_state,
  attempt_count, next_retry_at, last_error_ref
```

**`event_schema_version` — версия формата одного события**, не версия Work объекта; `node_seq` — порядок authoritative commit в конкретном узле, не универсальные распределённые часы. Outbox delivery — at-least-once с дедупликацией потребителей по `event_id`, без обещания exactly-once по сети.

В отличие от timeline-everything, не следует записывать heartbeat каждой session или тысячные проценты progress как обязательные durable domain events. Можно хранить краткоживущий progress snapshot и значимые transitions с отдельной telemetry retention.

---

## 6. Предлагаемая минимальная схема данных (концептуально)

### 6.1. Первичные ключи и обязательные связи

Ниже модель **logical tables**, не окончательная SQL-миграция. Внутренние первичные ключи могут быть UUID/ULID/иным устойчивым типом; публичные IDs всегда scoped и opaque.

| Группа | Logical records | Основной invariant |
|---|---|---|
| Identity references | `product_store`, `principals_ref`, `grants`, `workspace_memberships` | платформа передаёт principal, продукт контролирует доступ к объектам |
| Work | `works`, `work_requirements`, `work_thread_links`, `work_acceptances` | acceptance не следует автоматически из Job success |
| Conversation | `threads`, `thread_messages`, `thread_links` | только authorized audience видит message |
| Execution | `runs`, `execution_plans`, `jobs`, `operation_runs`, `attempts`, `effects` | Run ↔ immutable plan, Job ↔ unique terminal outcome |
| Control | `idempotency_requests`, `resource_claims`, `worker_leases`, `control_commands` | повторная доставка не создаёт второй эффект |
| Automation | `automations`, `triggers`, `trigger_occurrences` | occurrence уникальна в пределах revision и trigger |
| Activity | `events`, `event_outbox`, `projection_checkpoints` | событие и state transition коммитятся вместе |
| Collaboration | `assignments`, `approvals`, `read_cursors`, `notifications`, `notification_receipts` | персональный read state не изменяет shared event |
| Artifacts | `artifacts`, `artifact_versions`, `artifact_links`, `materializations`, `retention_holds` | публикация имеет content identity и producer/run ref |
| Diagnostics | `problem_links`, `log_refs`, `repair_actions` | ProblemRef указывает на подтверждённую запись у своего owner |
| Operations metadata | `schema_versions`, `migrations`, `backup_receipts`, `recovery_epochs` | повреждение или неизвестная версия не равны empty state |

### 6.2. Пример минимальных ограничений

```sql
-- TARGET EXAMPLE; database-neutral semantics, not final DDL.
UNIQUE(node_id, command_scope, idempotency_key)
UNIQUE(automation_id, automation_revision, trigger_id, occurrence_key)
UNIQUE(job_id, terminal_outcome_kind)  -- logically: at most ONE terminal record total per job
UNIQUE(node_id, node_seq)
UNIQUE(event_id)
UNIQUE(artifact_id, version_id)
UNIQUE(principal_id, feed_id)          -- read cursor
UNIQUE(principal_id, notification_id) -- notification receipt
```

Строка про terminal outcome обозначает **логическое ограничение**; простой составной UNIQUE по `job_id, terminal_outcome_kind` сам по себе разрешил бы разные terminal kinds для одного Job. Физическая реализация должна использовать уникальность по `job_id` в отдельной `job_terminal_outcomes` таблице либо атомарный guard/partial index. Аналогично resource leases требуют fencing generation и сопоставления с владельцем Job — уникального `resource_key` недостаточно для безопасной работы при «зомби»-worker.

### 6.3. Два примера записей

```json
{
  "kind": "Work",
  "work_id": "w_opaque",
  "node_id": "n_opaque",
  "revision": 6,
  "status": "IN_REVIEW",
  "owner_principal_id": "p_opaque",
  "visibility_policy_ref": "acl_opaque",
  "current_result_ref": "result_opaque",
  "latest_run_id": "run_opaque",
  "created_at_utc": "2026-10-09T10:30:00Z",
  "updated_at_utc": "2026-10-09T10:42:00Z"
}
```

```json
{
  "kind": "UserFeedReadCursor",
  "node_id": "n_opaque",
  "principal_id": "p_opaque",
  "feed_id": "work:opaque-or-personal-feed",
  "last_seen_feed_seq": 73,
  "updated_at_utc": "2026-10-09T10:43:00Z"
}
```

Иллюстративные timestamps/IDs здесь не являются наблюдаемыми фактами. Версии domain definitions и schema должны храниться отдельно от id и user-facing title.

### 6.4. Почему schema не следует начинать с `cases` как единого объекта

Старый Case объединяет параметры, статус, автора, steps, outputs и unread. Для простого GUI это хорошо; для долгого Work и нескольких запусков нарушает lifecycle. Если проектировать БД как копию `cases.json`, сложные связи снова окажутся JSON blobs или будут дублироваться. **Сначала нормализовать смысловые IDs темы 02, потом tables.** [R02], [R04].

---

## 7. Транзакции, конкурентность и command admission

### 7.1. Canonical mutation path

```text
Client/Automation/AI → Command with principal + expected_revision + idempotency_key
  → authenticate platform identity / bind trusted actor
  → authorize product action for object/scope
  → validate definition+schema+parameters+capability availability
  → begin transaction
  → re-check revision/current state/resource conditions
  → insert/update authoritative records
  → append domain event + outbox entry
  → commit
  → return new revision / refs / safe outcome
  → async clients consume notifications
```

**[TARGET-HYPOTHESIS]** Identity, authorization, expected revision, resource conflict и idempotency проверяются на application service boundary. Успешная UI-анимация или HTTP 200 до commit не является подтверждением эффекта.

### 7.2. Revision и optimistic concurrency

Пример: два клиента видят `assignment.revision=4`; один принимает поручение и сохраняет `revision=5`, второй отправляет действие с `expected_revision=4` — получает `CONFLICT` вместе с safe current projection. Молчаливый last-write-wins недопустим для общего Work/Assignment, но приемлем для несущественной локальной ширины панели.

При повторном `StartRun` с тем же key система возвращает **тот же подтверждённый Run/Job receipt** или явное состояние неопределённости admission, не порождая скрыто вторую операцию. Область idempotency key включает principal/target scope, тип команды и назначение, а не только произвольную строку.

### 7.3. Workers и ресурсы

- **Resource claim** — право на конкретный output/source/cache/compute slot; долгоживущий claim сохраняется и проверяется по правилам конкуренции.
- **Worker lease** — временная custody текущего Job/Attempt; содержит `owner`, `expires_at`, `generation`.
- **Fencing token** — монотонное поколение, которое writer/receiving boundary проверяет при новом эффекте; одного heartbeat TTL недостаточно, чтобы остановить старый worker.
- **Reconciliation** — связывает durable state с тем, что реально успел сделать worker, особенно если операция затрагивала внешний ресурс.

Требование «один authority, несколько workers» не создаёт иллюзии, что SQLite автоматически защищает внешнюю запись в CSV или удалённое хранилище. Для неё нужны effect-specific guards, staging, receipts либо эксклюзивные capabilities. [R04], [B-BACKGROUND].

### 7.4. Terminal transitions

**[CONSOLIDATED]** Один Job имеет **ровно один committed terminal outcome**. `CancelRequested` — событие управления, не terminal state. Timeout ожидания ответа — не всегда доказанное `FAILED`; внешний эффект после разрыва может требовать `OUTCOME_UNKNOWN` и reconciliation. Успешный Job/Run не автоматически означает `WorkAccepted` или доказанный банковский Claim. Эти различия имеют прямое отношение к выбору storage tables, а не только к UX. [R03], [R04].

### 7.5. Честность атомарности при работе с файлами

SQL transaction не может атомарно охватить обычную файловую запись и внешнюю сетевую операцию. Нельзя обещать «всё одна транзакция» при генерации XLSX. Вместо этого используется **saga/commit protocol** с durable intent, staging, проверкой digest, publishing и последующей DB finalization; при crash обнаруживаются незавершённые записи и orphan bytes. Подробнее — §11.

---
## 8. События, пользовательские проекции и согласованность между устройствами

### 8.1. Snapshot + changes: один протокол для всех surfaces

**[TARGET-HYPOTHESIS]** При подключении клиент выполняет:

```text
1. Attach/authenticate and fetch authorized snapshot at consistent cursor C
2. Render shared Work/Run/Job/Artifact/Assignment projections
3. Subscribe or poll changes after cursor C
4. Apply authorized changes in committed order and update local checkpoint
5. If cursor expired / schema incompatible / integrity check fails → fetch snapshot again
6. Shared command mutations always go to authority
```

Для Web естественен HTTP commands + SSE; Windows локально может использовать IPC/loopback/in-process adapter, Android — HTTP/push/wake+fetch. **Транспорт не меняет семантику состояния.** WebSocket имеет смысл только при реальной необходимости двухстороннего постоянного канала. SSE/polling — transport choice, не источник истины. [B-MULTI], [B-WEB], [B-BACKGROUND].

### 8.2. Важное доисследование: безопасный cursor при фильтрации доступа

Вторая ветка предлагает глобальный `node_seq`. Это полезно для node-internal cause order, но возникает скрытый риск: **персонализированный stream не обязан содержать каждый `node_seq`**. Пользователь с правом видеть события 101 и 104 закономерно не увидит приватные 102–103. Клиенту нельзя считать эти пропуски повреждением и нельзя давать API раскрывать, что скрытые события вообще существуют.

**[TARGET-HYPOTHESIS]** Ввести два уровня:

- `node_seq` — внутренний глобальный committed order (видим только authority и разрешённым техническим consumers);
- **opaque `feed_cursor`** — позиция в authorized projection/stream, которую выдаёт сервер (либо безопасный watermark и доказанная процедура cursor advancement).

`GET /activity?cursor=opaque` возвращает authorised items + `next_cursor` и `snapshot_revision`; клиент не вычисляет сквозную числовую последовательность скрытых node events. Для отдельного Work/Thread допустим видимый `feed_seq` при устойчивой audience policy. При отзыве/grant прав authority пересобирает eligibility, выдает новый feed generation или явно инвалидирует cursor. Эту схему необходимо пилотировать: она закрывает одновременно корректность reconnect и возможную side-channel утечку через gaps.

### 8.3. Подписка, обработка дублей и stale state

- Snapshot сам по себе может устареть между чтением и subscribe: protocol обязан защищать от потери событий на этой границе (`snapshot_cursor` фиксируется в той же consistent read либо сервер хранит catch-up log).
- SSE/HTTP события могут повторяться; client projector применяет `event_id`/revision идемпотентно.
- Change record содержит только заранее разрешённые поля; клиент не получает raw secrets/paths/tracebacks и не полагается на скрытие элементов интерфейса.
- При недоступности node UI явно показывает «последнее достоверное обновление: ...» и *не меняет* серверный `RUNNING` на `FAILED`.
- Mutating controls блокируются либо переходят в явно поддержанный, idempotent draft-queue protocol. Для начальной реализации **запрет offline shared mutations** надёжнее offline-first merge.
- Reconnect по старому cursor после retention compaction приводит к controlled `RESYNC_REQUIRED` и новому authorized snapshot.

### 8.4. Projections не равны authority

Сценарный чат, центр задач, вкладка «Фоновые», badge непрочитанного, глобальный поиск, таблица участников и карточка артефакта — *несколько views над одной моделью*. Они не должны независимо вычислять статус Job, наличие опубликованного результата или ACL. Product service может выдавать готовые summary projections и допустимые actions. Различия Windows/Web/Android касаются geometry, interactivity и local state.

---

## 9. Пользователи, участники и совместная работа

### 9.1. Principal, User, Actor, Session, Participant

**[CONSOLIDATED]** Их нельзя слить в `author_name`:

- `Principal` — субъект авторизации и grants; может быть пользователь, service actor или machine identity.
- `User` — человек с одной или несколькими platform sessions и пользовательскими preferences.
- `Actor` — кто инициировал конкретный effect/transition: person, automation, agent, system; сохраняется trace цепочки делегирования.
- `Session` — факт platform attachment с отдельным lifecycle, device/surface, heartbeat; AppDock authority.
- `Participant` — отображаемый в UI человек/роль, агрегированная из разрешённых данных пользователя и сессий.

Один человек может работать одновременно в Windows и Android; у него одна product identity, две platform sessions, возможно несколько активных Work. Не следует путать `session_id` с `job_id`. Закрытие одной session не закрывает Work и не отменяет Job.

### 9.2. Presence: вычисляемая, ограниченная во времени проекция

**[TARGET-HYPOTHESIS]** Основой online/stale/offline является разрешённая агрегированная информация AppDock Sessions + heartbeat и фактический lifecycle. Heartbeat сам по себе не доказательство наличия реального пользователя у клавиатуры. Пользователь с двумя устройствами считается одним участником; детальный список sessions раскрывается только при соответствующей permission.

```
active platform sessions + fresh heartbeat + permitted visibility → online
session exists but heartbeat stale                            → stale
no active permitted sessions                                  → offline
```

**UNKNOWN:** конкретные heartbeat TTL и offline grace зависят от условий сети и платформы; нельзя жёстко зашивать «30 секунд = offline» в доменную модель. В долгосрочном хранилище сохраняется существенная session audit/last-seen в рамках retention, но не каждое heartbeat событие. [B-MULTI], [A-SESSIONS].

### 9.3. Общая работа не обязана быть общей для всех

**[CONSOLIDATED]** Scope visibility отдельно от owner: `private`, `shared_team/workspace`, `node_visible`, ограниченный invited access. Один узел может обслуживать разные Work с несовпадающими ACL. `node-wide execution authority` означает общую очередь и ресурсы, **а не автоматическое право всех видеть все параметры и результаты**.

Именно здесь решается важный конфликт исследований: сценарный «общий чат» хорош как product timeline, однако raw params, private messages, редактируемые files и технические логи нельзя показывать каждому подключившемуся к узлу. Система строит персонализированную safe projection и проверяет object-level authorization при каждом API-запросе.

### 9.4. Work ↔ Thread и shared activity

**[TARGET-HYPOTHESIS]** Входное сообщение, описание Work, план, запуск, artifact и ревью связаны IDs и causal refs. Thread может показывать:

```text
Поступила задача → Work создана → Run согласован → Job стартовал
→ Опубликован Artifact → Назначено ревью → Work принята
```

Эта лента может отображаться нескольким участникам с разными правами. Сообщения чата не должны становиться authoritative status records. Система имеет один `Work.status` и может строить на его основе тысячи карточек и комментариев. Много-ко-многим `Work↔Thread` не допускает случайного расширения доступа: permission на Thread и сам Work проверяются одновременно, а приватные поля скрываются.

### 9.5. Прочтение: per-principal cursor и адресные receipts

**[CONSOLIDATED]** `unread: bool` в shared Case/Event необходимо заменить персональным read state. Для обычной activity достаточно `ReadCursor(principal, feed, sequence)` с монотонным продвижением. Для assignment, mention, approval и high-impact notification нужен отдельный `NotificationReceipt` (`delivered/seen/acknowledged/acted`).

Белое пятно второй ветки: *один node-wide cursor может ошибочно отметить прочитанными сообщения разных Threads*. Поэтому **[TARGET-HYPOTHESIS]** scopes для cursors — минимум global activity feed и per-Thread/per-Work where appropriate; выбор определяется UX-проекцией. Advance cursor допустим только до фактически выданной/увиденной позиции и не должен расширяться просто потому, что пользователь открыл другую вкладку. Read state является персональным, даже если Work shared.

### 9.6. Assignments и Approvals

`Assignment` — shared task с author, assignee, target Work/Run/Artifact, deadline, status, comments/decision refs, revision. Оно не является scheduled Job. `Approval` — разрешение строго определённого эффекта/плана с `requested_by`, `approved_by`, `scope`, `effect_summary`, `plan_digest`, `expires_at`, `decision`.

**[TARGET-HYPOTHESIS]** Approval действителен только для конкретного immutable plan/effect intent и заданной audience/authority. Изменился существенный input digest или output destination — требуется новое решение либо повторная валидация. Автоматическое поручение «проверить результат» полезно как configurable policy, а не обязанность каждой операции. [B-MULTI], [B-AUTO], [R04].

### 9.7. Notifications ≠ Event log ≠ Problem

| Сущность | Канонический смысл | Хранение |
|---|---|---|
| Domain Event | значимое произошедшее изменение | durable ordered journal |
| Notification | индивидуальная причина привлечь внимание | per-user generated record/projection + receipt |
| Problem | подтверждённый диагностический occurrence | точный `ProblemRef` у platform problem owner либо product typed failure |
| Telemetry | измерения работы и технические события | ограниченный журнал/метрики |
| Assignment | действие/решение, которое ожидают от человека | shared transactional aggregate |

Одна node-wide проблема может породить личные notifications многим пользователям, но должна иметь **одну общую occurrence identity**, dedup/grouping и безопасное audience mapping. Ошибка одного пользователя, затрагивающая его приватный источник, не автоматически публикуется всему узлу. Подробности безопасного ProblemRef и application/runtime mapping — [B-OBS], [A-OBS].

### 9.8. Политика аудитории

Предлагаемая минимальная модель:

| Scope | Пример | Кто получает |
|---|---|---|
| Personal | ошибка пользовательского черновика | конкретный principal |
| Work-scoped | завершение совместной Work | участники Work по ACL |
| Resource-scoped | недоступен общий Data root | участники, реально использующие ресурс |
| Node-scoped | отказ product job service | уполномоченные участники узла |
| Security-sensitive | подозрение на access bypass | ответственные операторы/администраторы |

UI-safe title/body формируются отдельно от raw failure. Персональные квитанции «видел/отреагировал» не переписывают сам ProblemOccurrence.

---

## 10. Автоматизации и фоновые задания: durable definition отдельно от execution

### 10.1. Три жизненных цикла

**[CONSOLIDATED]** (1) Automation definition живёт неделями/месяцами, (2) trigger occurrence фиксирует конкретный срабатывающий момент, (3) созданный Run/Job исполняется минуты/часы и имеет собственные retries/terminal outcome. `enabled` у Automation — стабильная настройка процесса, а не Qt checkbox; текущий `BackgroundProcessStore.enabled` не имеет долговременной общей authority. [B-BACKGROUND].

### 10.2. Какие данные надо хранить

```text
Automation:
  automation_id, owner_principal_id, scope, revision, enabled,
  scenario/scheme definition ref, schedule/trigger definition,
  effective policy ref, created_at, updated_at, last_evaluated_at,
  next_due_at, overlap/misfire/retry policy

TriggerOccurrence:
  occurrence_id, automation_id, automation_revision, trigger_id,
  logical_due_time, evaluation_snapshot, idempotency_key,
  admitted_run_id?, status, evaluated_at

Job:
  job_id, run_id, state, custody, attempt references,
  resource claims, terminal result, safe output refs
```

`next_due_at` — пересчитываемый cursor/projection, но **admitted occurrence** — durable факт. Повторный старт scheduler после reboot не должен повторно сформировать Job на один и тот же occurrence.

### 10.3. Time zone, DST, missed runs и изменения schedule

Automation spec сохраняет явную timezone и calendar semantics, а occurrence — UTC instant и локальную календарную интерпретацию. При daylight-saving ambiguous/nonexistent times применяются документированные `misfire/overlap` правила. После простоя scheduler вычисляет пропуски и создаёт только разрешённые occurrences. Отключение automation не уничтожает уже исполняемый Job без отдельной отмены.

При изменении расписания создаётся новая `automation_revision`. Пропущенные occurrences старой revision не смешиваются с новым расписанием. Внешнее изменение permissions или утрата секрета меняют возможность исполнения; сохранённый `enabled=true` не даёт бессрочного административного bypass.

### 10.4. Секреты и конфигурация задач

Run snapshot хранит только **secrets references** либо безопасную opaque credential binding, не plaintext значения. Фоновый процесс не может зависнуть в скрытом `getpass()`; если требуется interactive auth, Job переходит в явное `WAITING_INPUT/AUTH_REQUIRED` согласно execution contract с notification/TTL. В случае недоступности platform secret store — typed failure/blocked state, а не пустой dataset.

---

## 11. Артефакты, аналитическое знание и согласованность DB ↔ blobs

### 11.1. Разделение четырёх объектов

- `AnalyticalResult` — предметная интерпретация, quality/evidence и данные; её смысл определяет core.
- `Artifact` — логическая опубликованная единица с ID, версиями, producer/Run/Work links и пользовательскими правилами доступа.
- `ArtifactManifest` — immutable описание содержания, provenance, parts/sha256 и правил воспроизводимости.
- `Materialization` — физические байты в конкретном managed storage locator; в одном случае может быть несколько копий/экспортов.

**[CONSOLIDATED]** Ячейка каталога не становится источником банковского числового факта; семантика Claim/Evidence остаётся у domain owner. И наоборот, domain code не решает, кому разрешено открыть артефакт, когда истекает retention и на какие Work его показывать. [R03], [B-ARTIFACT].

### 11.2. Транзакционно-подобная публикация

**[TARGET-HYPOTHESIS]** Для управляемых результатов:

```text
1. Record effect intent / reserve artifact identity (DB transaction)
2. Generate bytes under run-scoped staging location
3. Close output safely, validate format, digest and expected metadata
4. Write immutable manifest bound to source/registry/plan/Run IDs
5. Publish bytes+manifest into managed area where possible atomically
6. In DB transaction mark ArtifactVersion PUBLISHED, create links/events/outbox
7. If crash occurs between 5 and 6, reconciliation discovers orphan publication
```

При ошибке на шагах 2–4 source и прежний опубликованный artifact остаются нетронутыми; неполный output помечается `ABANDONED`/`FAILED` и очищается отдельно по retention. При ошибке шага 6 физический объект не становится видимым *по каталогу* до reconciliation. Прямая запись в пользовательский внешний путь может иметь худшие гарантии и должна объявлять их operation effect contract. Проверить, поддерживает ли конкретный storage backend atomic move/copy, надо отдельно; FileStore abstraction не гарантирует POSIX-транзакцию.

### 11.3. Не превратить manifest и DB в две конкурирующие истины

Здесь остаётся тонкость из [B-ARTIFACT]: один документ предлагал «immutable manifest — portable truth», а другое исследование закрепляет «application catalog — canonical user state». Это разные поля истины, если сформулировать так:

1. **Manifest authoritative** для `content digest`, immutable parts, producer input/provenance и формата конкретной artifact version.
2. **Application DB authoritative** для `visibility`, Work links, pin/favorite, retention hold, user-facing lifecycle, soft delete, permission changes и notification states.
3. **Physical object** подтверждает существование байтов, но сам по себе не даёт ни разрешения на скачивание, ни юридически значимого статуса Work.

Пересборка DB из manifests может восстановить **content catalog subset**, но не обязана восстанавливать ACL/read receipts/Assignments, если эти сведения сохранились только в DB. Поэтому тезис «БД всегда полностью восстанавливается из manifest» в общей архитектуре был бы ложным. Нужен согласованный backup set.

### 11.4. Кэш и воспроизводимость

SourceSnapshot/RegistrySnapshot с устойчивым digest используются для доказательной репродукции. Cache нужен как performance layer, но **если только cache содержит последнюю сохранившуюся копию raw source, он де-факто стал обязательным воспроизводимым input**. Такая ситуация должна обнаруживаться и приводить к pin/archive policy либо маркировке degraded reproducibility. Удаление обычного cache не удаляет Work/Artifact identity и не должно притворяться потерей исходной официальной публикации.

### 11.5. Где проходит metadata ownership

```
stratbox:   source identity, dataset versions, model assumptions,
            validation, claim/evidence/provenance semantics
    ↓ typed result + manifest refs
application runtime: artifact ID, publisher, ACL, versions,
                     Work/Run links, status, retention, search
    ↓ storage binding
FileStore / object store: verified byte objects, hashes, reads
    ↓ safe projection
Windows/Web/Android: artifact views, previews, downloads
```

Физические файлы workspace могут оставаться обычными изменяемыми файлами пользователя: не каждый `.xlsx` автоматически становится managed Artifact. Это должно определяться явной publication/import operation и user intent, а не магическим scanning каталога.

---

## 12. Settings, policy, draft и поверхность: отдельные контракты

### 12.1. Почему «системные настройки» — ложный общий контейнер

**[CONSOLIDATED]** Исследование [B-SETTINGS] убедительно разделяет устойчивое предпочтение, переменный UI state, черновик, managed policy и параметры конкретного Run. Они должны иметь разные owners, даже если для простоты хранятся рядом в профиле пользователя.

| Тип | Примеры | Sync? | Persistence |
|---|---|---|---|
| `UserSettings` | тема, акцент, default reporting profile, подпись автора, semantic notification choice | опционально между устройствами | validated versioned atomic JSON либо user-scoped DB record |
| `SurfaceState` | размер окна, активная вкладка, положение панели, scroll | обычно нет | local small file/cache |
| `DraftState` | ещё не запущенные параметры сценария, черновик сообщения | opt-in и sensitivity-aware | local atomic file; secret fields excluded |
| `RecentState` | последний открытый Work/Artifact, фильтр | локально, resettable | surface local |
| `ManagedPolicy` | разрешённые действия, output limits, retention, update/bindings | приходит от authoritative policy owner | deployment/node/workspace profile |
| `RunParameters` | даты, источники, refresh, optimization mode, output target | фиксируются в immutable Run snapshot | execution DB; safe public projection |
| `AutomationSettings` | trigger, timezone, overlap/misfire, enabled | shared within allowed scope | automation aggregate DB |

### 12.2. Effective settings resolution

```
Product default
  → relevant Workspace default
  → User preference
  → Managed policy constraints/forced values
  = effective setting

Effective setting + Scenario/preset + explicit invocation params
  → managed validation + immutable Run snapshot
```

Это не следует реализовывать просто объединением JSON-документов с непредсказуемым precedence. `SettingsService` возвращает `value, source, editable, allowed_values, reason, restart_required`. UI показывает «управляется средой», а не бессмысленно disabled control.

### 12.3. Атомарность маленьких файлов

У `UserSettings`, `SurfaceState` и отдельных drafts небольшой размер, редкая shared конкуренция и независимый lifecycle. **[TARGET-HYPOTHESIS]** Для первого Windows профиля достаточно `write temp → flush/fsync по политике → atomic replace` с schema validation и recoverable backup. При невалидном config должен быть явный diagnostic и безопасный fallback только для resettable preference; повреждение Work/Job DB нельзя лечить той же логикой.

### 12.4. Переносимость предпочтений, а не всего интерфейса

Sync-worthy: theme preference, accent, reporting profile, notification semantic opt-in.  
Device-only: geometry, scroll, clipboard, last open inspector, local paths, runtime OS notification permission.  
Optional per-Work sync: только явно разделяемый draft с ACL и version, а не молчаливая реплика локального черновика.  

Если две платформы одновременно меняют одну user setting, она должна иметь `updated_at + revision / device identity` либо явную политику conflict resolution. Последний timestamp по локальным часам без server order — слабая гарантия. Для простых cosmetic settings можно принять server-defined last-write-wins, а для autorun/retention/policy — только revisioned commands.

### 12.5. Граница конфигурации расширений

Нейтральные plugin settings должны быть scoped, namespaced и versioned, с declared schema и visibility (`user`, `node`, `workspace`, `managed`). Конкретные закрытые реализации не являются частью этой публичной модели. Discovery и activation пакетов не равны ordinary preferences; управление установкой и разрешённостью расширения следует согласовать с платформенным deployment owner и продуктовым capability owner. [B-SETTINGS].

---
## 13. Crash safety, recovery, backup и обновление приложения

### 13.1. Почему durable ≠ автоматически recoverable

Данные могут лежать на диске, но быть логически неразрешимыми: Job говорит `RUNNING`, процесс умер; опубликованный файл существует, а DB transaction не прошла; два источника версии индекса расходятся; очередь триггеров потеряла cursor; миграция завершилась частично. **[CONSOLIDATED]** Durable storage требует системного recovery protocol и тестов, а не только `sqlite3.connect()` и записи файла. [R04], [B-BACKGROUND], [B-WEB].

### 13.2. Классы восстановления

| Ситуация | Обязательная реакция |
|---|---|
| Клиент/Qt crash, узел и job живы | отметить client session stale; Job продолжает; reconnect по ID |
| Worker пропал, нет внешних эффектов | detect custody loss, new Attempt/retry по policy |
| Worker пропал после потенциального destructive effect | `OUTCOME_UNKNOWN`, проверить receipts/ресурсы, запрет слепого retry |
| DB недоступна/повреждена | product `DEGRADED`/diagnostic-only; ни пустая история, ни destructive commands |
| Event outbox недоставлен | retry delivery with same event identity; consumer dedup |
| Artifact staging incomplete | mark abandoned, preserve published version, controlled cleanup |
| Artifact bytes опубликованы, DB index не обновился | reconciler сверяет manifest и intent, финализирует либо карантинирует |
| Manifest не совпал с digest | integrity error; запрет выдачи как validated artifact |
| Source/registry revision изменилась | проверить совместимость checkpoint; новый Run/replan при изменении semantics |
| AppDock переактивировал среду | validate store identity/schema; resume/reconcile product state по отдельным правилам |
| Node физически выключен | фоновые Jobs не выполняются; после старта misfire/recovery policy |

### 13.3. Recovery startup sequence

**[TARGET-HYPOTHESIS]**

```
1. AppDock активирует узел / инициирует product service startup
2. Strategy Box service проверяет node/store identity и exclusive authority
3. Открывает transactional store в read-only/diagnostic mode при ошибке
4. Валидирует schema_version, migration journal, integrity, ключевые constraints
5. Восстанавливает/проверяет outbox и последние committed transitions
6. Сопоставляет active Jobs с worker/process custody, leases и fencing
7. Проверяет pending effects, staging, artifact manifests и remote receipts
8. Безопасные jobs возобновляет по new Attempt; опасные unknown блокирует
9. Восстанавливает automation occurrences и учитывает допустимые misfires
10. Пересобирает read projections и optional search index
11. Публикует readiness, unresolved problems и safe snapshot клиентам
12. После выполнения hard gates разрешает новые mutating commands
```

`last_heartbeat_at` не доказательство того, что старый worker физически прекратился. Lease expiration не гарантирует stop его сетевых запросов. Recovery supervisor должен учитывать реальные процессы, fencing policy и внешние приемники эффектов.

### 13.4. Backup: что входит и кто владелец

**Состав backup set:** согласованная DB snapshot, immutable artifact manifests и опубликованные managed bytes, metadata о размещении, применённые schema migrations, encryption/key recovery **references** без plaintext secrets, recoverable configuration и те raw SourceSnapshots, которые объявлены обязательными для воспроизводимости. FileStore scratch и regenerable cache исключаются по policy. Technical logs могут иметь самостоятельный ограниченный backup/retention режим.

**Ownership:** AppDock orchestrates platform stop/start/upgrade and may furnish backup/recovery *mechanics*; **Strategy Box application определяет набор, логическую согласованность, процедуры freeze/checkpoint, schema/readiness gates и validation**. Нельзя предполагать, что AppDock автоматически знает все связи Run↔Artifact↔manifest. [B-WEB], [A-NODE].

**SQLite:** online backup API либо иной документированный consistent snapshot; контроль WAL/checkpoint состояния, проверка результата; копирование одного открытого `.sqlite` как обычного файла ненадёжно. **PostgreSQL:** применять согласованный серверный механизм резервного копирования выбранного deployment; файловый backup DB и artifact store должен иметь единый **backup epoch/manifest**, указывающий, какие published objects включены. [SQLite Backup API](https://www.sqlite.org/backup.html).

**Minimum acceptance:** backup encrypted где требуется, периодически копируется вне единственной точки отказа, содержит hashes/manifest, а восстановление регулярно тестируется на **новой** среде. Сам факт создания архивного файла ещё не доказывает восстановимость.

### 13.5. Миграции persisted schema и отказ от legacy compatibility

Здесь особенно важно различить два контракта.

1. **Runtime/API backward compatibility:** проект вправе сделать чистый breaking change, удалить старые wrappers, aliases и legacy handling.
2. **Сохранность пользовательской ценности:** если Work, artifacts, automation history и receipt должны пережить upgrade, persisted records нуждаются в явной **one-time migration** или контролируемом export/import. Нельзя выдавать silent reset за принцип «legacy не поддерживается».

**[TARGET-HYPOTHESIS]** Схема имеет `schema_epoch + version`, миграция — immutable ID, checksum, `from/to`, preconditions, backup receipt, applied_at, verification status. Перед migration service прекращает новые mutable admissions, дожидается безопасной точки/останавливает допустимые Jobs, создаёт backup epoch, применяет migration в транзакции где возможно, проверяет invariants, затем публикует новую readiness. В случае отказа открывает диагностический режим и использует restore/forward-fix процедуру. Держать вечные ветки кода для старых сериализаций не нужно; **последовательность migration steps** и тестовые старые fixtures нужно сохранять, пока поддерживаются соответствующие upgrade paths.

**Разовый импорт старых пяти JSON** при желании может стать *development/data migration utility* с валидацией, quarantine неверных записей, журналом и summary; это не параллельный production history backend. Cut-over должен иметь одну authority и дату. [B-MULTI], [B-SETTINGS], [B-WINDOWS].

### 13.6. Восстановление несовместимой версии

Бинарник с неизвестной новой `schema_epoch` **не открывает store на запись**. Новый binary с древней schema, для которой нет проверенного migration path, не «угадывает» поля. В обоих случаях система сообщает `UNSUPPORTED_STORE_SCHEMA` и даёт администратору backup/upgrade/export path. Compatibility матрица относится к **данным**, а не к обязанностям поддерживать старые исполнители одновременно.

---

## 14. Retention, удаление, поиск и ресурсы

### 14.1. Retention scopes

**[TARGET-HYPOTHESIS]** Нужны отдельные правила для:

- Work/Run/Job и terminal outcomes (операционная история);
- thread messages, comments (collaboration content);
- activity events, control/effect receipts (audit-causal evidence);
- artifacts, artifact versions, published bytes;
- SourceSnapshots, registry assets, model/evidence refs;
- user notifications, receipts/read cursors;
- technical logs/trace, telemetry, support evidence;
- cache/staging/temp;
- platform session state (AppDock policy).

Один `history_days=30` на всё создаст нарушение причинных ссылок. Retention учитывает links, active jobs, pins, archive/hold, legal/enterprise policy (если присутствует). Удаление Work не обязано немедленно физически уничтожить artifact с другими authorized consumers; удаление artifact materialization не должно убивать весь Work audit. Для регулируемых окружений срок хранения и правила стирания определяются внешней политикой, **не придумываются в этом документе**.

### 14.2. Двухэтапное удаление и tombstones

```
request deletion → authorize/verify holds/refs
  → create tombstone and remove from ordinary projections
  → bounded grace/recovery period where permitted
  → garbage collection of unreferenced materializations
  → retain minimal redacted audit/effect proof according to policy
```

`Delete` означает разное для attachment, Thread link, published artifact и underlying source. API обязан называть именно target и effect. Прямой recursive delete через FileStore без plan/validation для ценного artifact store недопустим. [B-ARTIFACT], [R04].

### 14.3. Search and indexing

Work/Thread/Artifact поиск должен использовать **authorization-filtered query** поверх application truth. На первом этапе достаточно DB indexes по status, owner, created_at, scenario/domain, artifact kind, source_id, tags; полнотекстовый индекс добавлять после реальных запросов, с bounded indexing и reindex contract. Не индексировать secret params, raw traceback или чужой private content в общем поиске. Гибкий semantic/vector search — следующая опция, не часть базовой authority.

### 14.4. Quotas и обслуживание базы

Хранение миллионов progress events и крупных JSON blobs в общей таблице рано превратит desktop-приложение в обслуживаемый сервер. Нужно разделить durable event importance и telemetry frequency; предусмотреть event compaction boundary, архивирование, outbox cleanup после подтверждения, checkpoint/size мониторинг и alerts на disk pressure. **SQLite WAL может увеличиваться при долгих readers/неудачном checkpoint**, поэтому мониторить рост WAL и использовать короткие read transactions ([SQLite WAL](https://www.sqlite.org/wal.html)).

Ресурсная политика `max_artifact_bytes`, staging capacity, maximum concurrent writers, log retention и upload caps принадлежит managed policy/operations, а не случайному пользовательскому файлу настроек.

---

## 15. Границы безопасности и корректность прав

### 15.1. Authentication и authorization — два разных решения

AppDock сообщает доверенную платформенную user/session/node identity и границы attach. Strategy Box application **сам проверяет** `view_work`, `start_run`, `cancel_job`, `read_artifact`, `assign_review`, `approve_effect`, `manage_automation`, `view_technical_logs` по объекту, ресурсу и действующей policy. Coarse roles полезны как bundles, однако авторизуются конкретные действия. Кнопка, скрытая в интерфейсе, не является проверкой прав. [B-MULTI], [B-WEB], [R04].

### 15.2. Данные параметров и artefact refs

Run сохраняет complete validated parameters **с sensitivity annotations**, но безопасная client projection скрывает `secret`, `private_to_actor` и технические значения. Публичный artifact ID не создаёт разрешение читать его байты; его разрешение проверяется при preview/download/reveal, в том числе после изменения ACL. Materialization locator с реальным файловым путём — серверная деталь, а не доверенная часть client authorization.

### 15.3. External AI и делегированные actions

AI, автоматизация и external API выступают как actors в том же command path: authority checks, effect classification, bounded permissions, explicit approval и provenance delegation chain. Их state/actions должны быть объяснимы через Work/Run/Job/Attempt, а не храниться в отдельной AI-only timeline с другой системой прав. Лог модели или prompt не превращается в достоверный banking Claim; read/write limits и безопасность данных сохраняются. [B-AUTO], [R02], [R04].

### 15.4. Problem redaction и cross-user warnings

Платформенная диагностическая проблема может иметь подтверждённую immutable occurrence с `ProblemRef`, но product ACL решает, кто увидит её безопасную summary и возможные действия. Ссылка на error occurrence может храниться долго, подробное сырое evidence — по самостоятельному ограниченному retention. При регистрации проблем из Strategy Box нельзя автоматически считать, что AppDock уже подключил generic recorder ко всем типам прикладных ошибок; текущая реализация платформенной observability развивается поэтапно. [A-OBS], [B-OBS].

---

## 16. Конфликты и локальные белые пятна, обнаруженные консолидацией

### 16.1. Реестр конфликтов и разногласий

| ID | Исходное расхождение | Вердикт | Статус |
|---|---|---|---|
| C05-01 | SQLite для узла vs PostgreSQL для Web | scope/profile difference; один semantic port | **RESOLVED-CONCEPTUAL / UNKNOWN thresholds** |
| C05-02 | `Case` как общая запись vs `Work` + `Run` | current Case run-like; Work более длителен | **SUPERSEDED** как target dual authority |
| C05-03 | Хранить историю в нескольких JSON vs transactional DB | JSON — текущий prototype; shared authoritative state требует транзакций | **SUPERSEDED** для shared state |
| C05-04 | Manifest — portable truth vs DB — canonical artifact catalog | различить content/provenance и user lifecycle/access | **RESOLVED-CONCEPTUAL** |
| C05-05 | «Один node-wide seq» vs personal streams | internal seq допустим; public feed cursor должен учитывать ACL | **NEW WHITE SPOT / TARGET-HYPOTHESIS** |
| C05-06 | `unread: bool` vs per-user cursors | single bool неверен для multi-user | **SUPERSEDED** в target |
| C05-07 | Presence как таблица bool vs AppDock session-derived | presence — ephemeral projection, sessions — authority | **RESOLVED-CONCEPTUAL** |
| C05-08 | Настройки и формы в `app.json` vs Settings/Drafts/Surface/Policy | split по жизненному циклу | **SUPERSEDED** |
| C05-09 | Полная event sourcing platform vs SQL+events+outbox | full event sourcing не доказан workload'ом | **TARGET-HYPOTHESIS** |
| C05-10 | Новый `stratbox-host` repo прямо сейчас vs logic first | сначала logical owner; headless процесс нужен по lifecycle, repo отложен | **CONSOLIDATED / PHYSICAL UNKNOWN** |
| C05-11 | AppDock как владелец всего состояния узла vs собственное product Work store | разные authority scopes | **RESOLVED-CONCEPTUAL** |
| C05-12 | “Не нужна обратная совместимость” vs state migrations | runtime shims не нужны; данные нуждаются в controlled upgrade/retention | **RESOLVED-CONCEPTUAL** |
| C05-13 | Чат-first UI vs durable Work | чат — context/projection; Work живёт отдельно | **RESOLVED-CONCEPTUAL** |
| C05-14 | Global artifact CAS сразу vs минимальный managed store | CAS — опция по workload, immutability/provenance обязательнее | **DEFERRED** |

### 16.2. Новые белые пятна (не решены механическим сведением)

**WS05-A — Authorized feed cursor.** Как выдавать incrementally filtered stream, не раскрывая наличие скрытых node events и корректно реагируя на изменение ACL? Нужен API/projection pilot с двумя пользователями и разными правами.

**WS05-B — Cross-store artifact backup epoch.** Как доказать консистентность DB backup с внешними bytes, когда публикация и backup идут одновременно? Требуется manifest/epoch verification и restore-drill.

**WS05-C — Store generation / accidental clone.** Как обрабатывать восстановление копии node store с прежним node ID, чтобы две активные среды не исполняли расписание и эффекты дважды? Нужны clone/restore admission semantics и fencing.

**WS05-D — External manual edits.** Как authority реагирует на изменение артефакта/исходного файла пользователем вне сервиса? Immutable managed object защищён, workspace mutable; внешний edit требует нового import/version/fingerprint, но UI disclosure и watcher правила открыты.

**WS05-E — Per-Work privacy in shared Thread.** Как разрешить отображение безопасной части карточки Work без доступа к исходным чатам, черновикам и параметрам? Нужна object-level field projection и tests против escalation.

**WS05-F — Restore of read receipts after compaction.** Какие cursor/receipt остаются валидными при удалении старого event segment или отзыве разрешений? Нужны generation invalidation и resync rules.

**WS05-G — Independent failure of collaboration vs job store.** Нужна ли единая транзакция, если UI messages/assignments и job effects живут в разных persistence adapters? Для первой реализации предпочтительна одна DB; необходимость physical split отсутствует.

**WS05-H — Multi-process authority election.** Как обеспечить, что две копии product service после AppDock restart одновременно не считают себя scheduler leader? Начальная модель может ограничиться эксклюзивным single-node lease/process guard; при multi-worker необходима durable election/claims модель.

**WS05-I — Data retention & erasure.** Кто и по каким правилам удаляет персональные сообщения, logs, analytics artifacts и audit evidence при конфликте требований? Policy зависит от юрисдикции/deployment; конкретные сроки UNKNOWN.

**WS05-J — Secrets rotation & long-running Work.** Как rebind immutable plan snapshot на актуальные secret references и сертификаты после ротации, не меняя доказательную семантику Run? Нужен разделённый credential binding и explicit error path.

**WS05-K — Time zone/calendar restore.** Как пересчитать `next_due_at` после обновления time zone database/business calendar, сохраняя принятые прошлые occurrences? Нужны версионные schedule evaluation semantics.

**WS05-L — External ProblemRef lifecycle.** Что показывать при stale/deleted/unavailable platform problem occurrence, сохраняя собственную причинную product запись? Нужен bounded safe fallback с честным статусом `PROBLEM_REF_UNAVAILABLE`.

### 16.3. Что *не* следует считать реальным конфликтом

- `UserSettings` в JSON и Work в SQL: разные требования к атомарности и конкуренции.
- Work accessible from multiple Threads и private Thread messages: решается relation+ACL, а не global share.
- AppDock heartbeat и application Job progress: разные факты и cadence.
- FileStore path и Artifact ID: физический locator и логическая identity.
- Изменяемый Workspace и immutable managed Artifact: разные зоны, обе нужны.
- Отдельный user read cursor и shared event log: персональная projection поверх общей истории.

---
## 17. Сквозные acceptance traces: проверка модели на реальных действиях

### Trace 1. Пользователь создаёт аналитическую Work и закрывает Windows

1. Windows создаёт `WorkCandidate`, приложение принимает `Work` и возвращает `work_id`/revision.
2. Пользователь выбирает сценарий, создаётся Run с immutable params и plan ref.
3. В транзакции фиксируются Job+event+outbox; Job берёт worker.
4. Windows внезапно закрывается; AppDock Session прекращается, но product Job остаётся `RUNNING`.
5. Android подключается к тому же node identity и получает authorized Work/Run/Job snapshot.
6. Фактический Job завершает выполнение; Artifact публикуется и связывается с Run.
7. Windows переподключается и видит тот же `job_id`, единственный terminal outcome и актуальный результат.

**Проверяемый invariant:** client session lifecycle не является Job lifecycle. **CURRENT:** шаги 4–7 как общая runtime-функция ещё не реализованы.

### Trace 2. Два пользователя читают одну ленту

1. User A и User B видят shared Work с event 501.
2. A открывает событие и продвигает свой read cursor.
3. B остаётся с непрочитанным событием.
4. Между видимыми событиями возникают события private Work третьего пользователя.
5. Оба клиента получают корректные разрешённые feeds; gaps внутренних `node_seq` не раскрывают private activity.
6. Изменение ACL инвалидирует affected stream cursor; клиент получает безопасный refresh.

**Проверяемый invariant:** unread персонален; глобальное событие immutable; permission filtering применяется до отдачи payload.

### Trace 3. Два одновременных изменения одного поручения

1. Два клиента загружают assignment revision 10.
2. A подтверждает выполнение, получает revision 11.
3. B пытается переназначить исходную revision 10.
4. Service возвращает `CONFLICT`, не перезаписывает решение A.
5. B может получить новую projection и принять сознательное follow-up решение.

**Проверяемый invariant:** ни один потерянный update не превращается в незаметное last-write-wins.

### Trace 4. Scheduler после отключения узла

1. Automation запланирована раз в день с timezone, revision и misfire policy.
2. В 08:00 Job для occurrence `O1` принят в DB, но узел выключается до запуска worker.
3. После старта service проверяет occurrence `O1`, job custody и его эффекты.
4. Новый scheduler evaluation *не создаёт* второй occurrence `O1`.
5. По policy `O1` исполняется/пропускается с документированным результатом; следующие due instants вычисляются корректно.

**Проверяемый invariant:** расписание и факт срабатывания хранятся отдельно от исполнения.

### Trace 5. Авария между файловой публикацией и DB commit

1. XLSX построен в staging, validated, digest вычислен.
2. Artifact manifest и bytes опубликованы, но процесс умирает до DB commit.
3. При restart обнаруживается pending intent + published object.
4. Reconciliation сверяет digest, producer и effect receipt.
5. Artifact version финализируется один раз либо помечается orphan/quarantined с reason.

**Проверяемый invariant:** публикация не создаёт два расходящихся «успешных» результата.

### Trace 6. Потеря сети во время destructive action

1. User имеет разрешённый cleanup plan, подтверждение привязано к digest плана.
2. Worker начинает удаление и теряет связь с storage.
3. Клиент получает timeout; authority сохраняет effect intent и статус `OUTCOME_UNKNOWN`.
4. Retry блокируется до проверки resource state/receipts.
5. После reconciliation system фиксирует доказанный outcome или требует ручного вмешательства.

**Проверяемый invariant:** сетевой timeout не превращает неизвестный эффект в безопасно повторяемый.

### Trace 7. Невалидная БД после аварии

1. Service не может пройти integrity/schema checks.
2. Продукт публикует `DEGRADED_SHARED_STATE`, диагностическую поверхность и safe error.
3. Новые mutating commands/Jobs запрещаются.
4. AppDock platform lifecycle остаётся доступным; verified backup/repair plan восстанавливает product metadata store.
5. После проверки jobs/effects/artifact manifests authority вновь открывает новые команды.

**Проверяемый invariant:** corrupt DB никогда не означает «на узле просто нет истории».

### Trace 8. Заменён официальный источник, старый отчёт остаётся

1. Work завершена на SourceSnapshot `S1`, RegistrySnapshot `R1`; Artifact `A1` опубликован.
2. Официальная публикация изменена; появляется `S2` с новой content identity.
3. Старый Artifact остаётся доступным с lineage `S1/R1` и обозначением актуальности.
4. Новый Run использует `S2` и создаёт отдельный результат; прежнее утверждение может потребовать revalidation.

**Проверяемый invariant:** свежесть и аналитическая истинность не переписываются задним числом из-за обновлённой папки cache. [R03].

### Trace 9. Restore клона узла

1. Administrator восстанавливает backup Strategy Box в другую среду.
2. Store содержит прежнюю `node_id` и `generation`.
3. До запуска scheduler service требует explicit restore mode: replace original, sandbox clone или controlled re-identification.
4. При sandbox clone старые effect-capable automations disabled/rebound; actor/credentials/access переоцениваются.
5. Система не исполняет одну и ту же внешнюю доставку на двух клонированных узлах без разрешённой процедуры.

**Проверяемый invariant:** backup restore не создаёт скрытого второго authority. **UNKNOWN:** точная процедура re-identification зависит от AppDock node identity и требует joint contract.

---

## 18. Минимальные system-wide invariants темы 05

| ID | Инвариант | Как тестировать |
|---|---|---|
| ST-01 | Поверхность никогда не является owner durable Work/Job/Artifact lifecycle | убить GUI при активном Job; reconnect |
| ST-02 | Work/Run/Job/Attempt имеют разные identities и неизменяемые causal links | schema/FK/contract tests |
| ST-03 | Любой shared mutation проходит service authorization и revision guard | race/property tests |
| ST-04 | Подтверждённая команда имеет один логический idempotent admission result | duplicate request/reconnect tests |
| ST-05 | Job имеет не более одного committed terminal outcome | concurrent cancel/complete fault tests |
| ST-06 | Повреждённая state DB не превращается в empty state | corrupt/missing/incompatible fixtures |
| ST-07 | Event и authoritative transition фиксируются в одной transaction boundary | forced rollback/outbox tests |
| ST-08 | Retained event payload не раскрывает секреты или private data неавторизованному читателю | principal projection/ACL matrix |
| ST-09 | Personal read cursors/receipts независимы между пользователями | two-user UX tests |
| ST-10 | Presence строится из valid session evidence, а не произвольного локального bool | multi-session stale/TTL tests |
| ST-11 | Node-wide scheduler создаёт не более одного Job на одну admitted occurrence | crash/restart/misfire tests |
| ST-12 | Неизвестный внешний эффект не получает автоматический повтор | effect/failure injection |
| ST-13 | Published artifact имеет stable identity, manifest, producer Run ref и verified content | staging/crash/orphan tests |
| ST-14 | File bytes, metadata and manifests имеют проверяемую backup/restore boundary | restore drill + checksums |
| ST-15 | БД доступна удалённым clients только через service API; SQLite WAL локален | deployment conformance checks |
| ST-16 | Managed policy и user preferences не совпадают по authority | forced-setting tests |
| ST-17 | Изменение устаревших persisted schemas идёт через explicit migration/blocked startup | upgrade fixtures |
| ST-18 | Отсутствие соединения у клиента не изменяет серверный terminal/job status | partition tests |
| ST-19 | Удаление/retention учитывает references, holds и разграничивает logical/physical effects | GC/retention tests |
| ST-20 | Поиск/stream/cursor не раскрывают existence чужих объектов | adversarial ACL tests |
| ST-21 | Разделение owners `stratbox` / application / AppDock не нарушается при восстановлении | boundary/import/contract tests |
| ST-22 | Создание нового репозитория/процесса объясняется lifecycle и consumers, а не именем сущности | architecture review acceptance |

---

## 19. Консолидированная целевая модель — logical и physical отдельно

### 19.1. Logical architecture

```text
                           Strategy Box
┌────────────────────────────────────────────────────────────────────┐
│ Surface clients (Windows / Web / Android)                          │
│ layout / drafts / safe projections / commands / authorized cursors │
└───────────────────────────────┬────────────────────────────────────┘
                                │ typed commands, queries, changes
┌───────────────────────────────▼────────────────────────────────────┐
│ Strategy Box application authority                                 │
│ Identity binding / Product authorization / Work / Thread           │
│ Run/Job/Automation / Collaboration / Artifact Catalog              │
│ Transactions / Event+Outbox / Reconciliation / Read projections     │
└─────────────────┬──────────────────────────────┬───────────────────┘
                  │                              │
       ┌──────────▼─────────┐           ┌────────▼─────────────────┐
       │ Transactional state│           │ Managed artifact/content│
       │ + event/outbox     │           │ manifests/staging/logs  │
       └────────────────────┘           └─────────┬────────────────┘
                  │                               │
       ┌──────────▼───────────────────────────────▼────────────────┐
       │ stratbox domain core: operations, source/registry,         │
       │ validation, analytics, evidence and result provenance     │
       └───────────────────────────────────────────────────────────┘

External platform boundary: AppDock manages Node/Session/activation,
product runtime lifecycle, environment roots and platform Problems;
Strategy Box references those facts via public contracts.
```

Диаграмма отражает **направления ответственности**, не реальный import graph. Domain operations вызываются application executor; storage портом пользуются оба через строго очерченные контракты.

### 19.2. Candidate physical implementation для ближайшего цикла

1. **`stratbox` остаётся независимым core**, без Qt, без самостоятельной shared Work DB и без AppDock lifecycle logic.
2. **Platform-neutral application semantics и persistence adapters** сначала могут развиваться внутри текущего application/runtime codebase с жёстким отсутствием imports из Qt; shared код ориентирован на будущий Android/Web.
3. **Headless application service/process** становится обязательной физической границей, когда Jobs должны переживать закрытие окон. Он может быть thin executable в текущей поставке; отдельный repository/package — пока **UNKNOWN**, решается после появления реальных host/remote consumers.
4. **SQLite** — реализация первичного metadata store на node-local AppDock-managed диске; приложение держит один command authority, допускает параллельных reader/worker processes через service.
5. **AppDock** запускает/диагностирует/восстанавливает среду по собственным contracts и принимает безопасные ссылки на product state/problems, не копируя Work DB как собственный домен.
6. **Windows** получает client facade вместо прямого `HistoryPersistenceService`; Qt coordinator превращается в presentation adapter.
7. **Web/Android** используют те же IDs, semantics, error/authorization contracts, но собственные renderers и connection-specific state.

Альтернатива `stratbox-host` как отдельного репозитория сохраняется в реестре решений, **не считается выбранной**. Встроенное in-process выполнение допустимо только для осознанного dev/lightweight profile и должно честно заявлять отсутствие гарантий фонового переживания закрытия UI.

---

## 20. Приоритетный roadmap, без поддержки старых runtime API

### Этап 0 — зафиксировать semantic contract

- Принять Work/Run/Job/Attempt/Artifact/Thread/Assignment definitions тем 02–04 как исходную *working model*; закрыть жизненный цикл `Case`.
- Определить какие mutation commands существуют в первом вертикальном пилоте, их effects и scopes.
- Зафиксировать authority/ACL и минимальный набор persisted fields; **не создавать пустые сущности ради полного словаря**.
- Зафиксировать non-goals первой реализации: full event sourcing, global CAS, полноценный offline-first, обязательный PostgreSQL, микросервисная физическая нарезка.

### Этап 1 — работающий shared Work/Run/Job spine

- Toolkit-neutral application service; убрать runtime→Qt dependency.
- SQLite transactional metadata store на локальном node disk.
- Persistent Work/Run/Job+event/outbox, revisions, idempotency, schema version.
- Одно IPC/HTTP/in-process client contract и простой авторизованный snapshot.
- Конкретный сценарий из core проходит «submit → execute → terminal outcome → artifact link» независимо от GUI.
- Создать migration/cut-over procedure для текущей JSON-history, не держать вторую production truth.

### Этап 2 — recovery и artifact boundary

- Job custody, worker lease/fencing, safe retry и effect receipt.
- Staging/manifest/DB finalization + orphan reconciliation.
- Backup/restore и fault-injection проверки от падения в каждом commit window.
- System health `degraded/ready`, запрет mutating commands при повреждённой authority.

### Этап 3 — multi-user collaboration

- Principal/sessions integration через AppDock public boundary; per-object capability checks.
- Work/Thread associations, assignments/approvals, per-user read cursors.
- Authorized snapshot+change stream, notification receipts, presence projection.
- Multi-device tests: Windows+second client (может быть тестовый HTTP consumer, не полноценный Android).

### Этап 4 — automation и host/service maturity

- Durable automation specs/triggers/occurrences/scheduler cursor.
- Missing runs, misfire/DST/overlap/idempotent wake-up.
- Headless persistent service, reconnect после UI exit, remote attachment.
- Оценить реальные профили SQLite и необходимость PostgreSQL на уровне workload.

### Этап 5 — migration, retention, search, service operability

- Migrator with fixtures, contract tests, backup receipts.
- ACL-aware search, retention/tombstone/GC, export/import/restore validation.
- Bounded log/notification storage, disk/DB quotas, health monitoring.
- Подготовить одинаковый semantic contract для Web/Android adapters.

**Ритм внедрения:** один end-to-end pilot с реальным аналитическим сценарием и двумя clients должен пройти tests и crash drills **до** массового переноса остальных функций и UI. Одновременно с архитектурой БД следует очистить current `app.json` от смешения Settings/SurfaceState/Drafts, но не отвлекаться на второстепенную визуальную кастомизацию.

---

## 21. Decision / Gap Register

| Решение | Предпочтительное направление | Статус / чей следующий шаг |
|---|---|---|
| Authority scope | node-scoped headless Strategy Box application runtime | **CONSOLIDATED logical**, Product Decision требуется |
| Persistent state baseline | SQLite local-node, не Data root/network share | **TARGET-HYPOTHESIS**, engineering pilot |
| Server profile | PostgreSQL при доказанной нагрузке/операционных требованиях | **TARGET-HYPOTHESIS**, deployment measurement |
| Event architecture | relational current truth + append-only facts + outbox | **TARGET-HYPOTHESIS**, implementation probe |
| Work↔Thread mapping | Work long-lived, many-to-many authorized association | **CONSOLIDATED semantic**, ACL pilot |
| UI Case | projection/run-like old model; отдельный canonical Case пока не вводить | **TARGET-HYPOTHESIS**, Product naming |
| Personal unread | authorized per-feed read cursor + receipts | **CONSOLIDATED**, stream implementation |
| Cursor security | opaque authorized feed cursor, не raw node_seq | **NEW TARGET-HYPOTHESIS**, security/API pilot |
| Artifact ownership | manifest content truth + application catalog lifecycle truth | **CONSOLIDATED**, commit reconciliation needed |
| Policy/config | Settings vs Draft/Surface vs Policy vs Run snapshots | **CONSOLIDATED**, implementation split |
| Recoverability | explicit migration, backup/restore, unknown-effect reconciliation | **CONSOLIDATED**, acceptance tests |
| Physical `stratbox-host` package/repo | отложить до lifecycle/consumer proof | **UNKNOWN**, architectural governance |
| Full CAS/object store | опционально; не prerequisite | **DEFERRED**, real workload pilot |
| Persisted claim/evidence schema | domain-defined, lightweight refs; no giant global ClaimStore yet | **UNKNOWN**, domain pilot |
| Retention/erasure policy | per data class/ACL/holds | **EXTERNAL DEPENDENCY**, deployment/legal policy |
| Notification delivery | event-derived per-principal receipts + transport adapters | **TARGET-HYPOTHESIS**, product UX tests |
| Presence TTL | session-derived, configurable | **UNKNOWN**, network experiments |
| Store clone/restore semantics | explicit restore epoch + generation/fencing | **NEW WHITE SPOT**, joint AppDock/application contract |
| DB+artifact consistent backup | common backup epoch and manifest | **NEW WHITE SPOT**, restore proof |
| Schema upgrade discipline | one-time controlled migration, no permanent legacy runtime | **CONSOLIDATED**, implementation policy |
| Access control granularity | per-object capabilities + safe field projections | **CONSOLIDATED**, authorization tests |

**Степень зрелости:** архитектурная семантика состояния определена достаточно для ограниченного пилота. Форматы API, layout таблиц, выбор физического host-пакета и эксплуатационные пределы СУБД **ещё не являются утверждёнными решениями**.

---
## 22. Provenance ledger: исходные исследования, код и внешняя проверка

**Правило чтения:** ссылки на материалы `02-base-study` и темы 00–04 подтверждают **происхождение и степень согласованности исследовательских выводов**, но не превращают предложение в реализованный API. `CURRENT` основан на непосредственной проверке указанных code paths и/или dated implementation baseline. Официальная SQLite-документация использована только для технических свойств СУБД.

### 22.1. Программа, рамка и предшествующая консолидация

| Ключ | Источник | Какие выводы поддерживает |
|---|---|---|
| **[PROGRAM]** | [Программа 03 — тема 05](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/strategy_box_03_consolidation_research_program.md) | scope, список state classes, исследовательская дисциплина |
| **[R00]** | [Тема 00 — Corpus Map & Open Questions](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_00_corpus_map_open_questions_2026-10-08.md), §§7–11, 14.5, 15–17 | границы, конфликт SQL engines, пробелы persistence, legacy статус |
| **[R01]** | [Тема 01 — Strategy Box System Model](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_01_System_Model_consolidated_research_2026-10-08.md) | logical/physical ownership, минимальная система ответственности |
| **[R02]** | [Тема 02 — Canonical Semantic Model](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_02_canonical_semantic_model_2026-10-08.md), executive synthesis, §19.3 | Work/Run/Job/Thread/Artifact/Principal различения и IDs |
| **[R03]** | [Тема 03 — Data → Knowledge Architecture](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_03_data_to_knowledge_consolidated_research_2026-10-08.md), executive synthesis | SourceSnapshot/provenance vs Artifact, content vs metadata ownership |
| **[R04]** | [Тема 04 — Work → Execution Architecture](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_04_work_to_execution_consolidated_research_2026-10-09.md), §§6–12, 14–15 | executions, transitions, effects, idempotency, job recovery, multi-user |

### 22.2. Основной тематический корпус `02-base-study`

| Ключ | Источник | Главные пересечения с темой 05 |
|---|---|---|
| **[B-CORE]** | [Текущее состояние `stratbox`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_base_study_current_state_2026-10-06.md) | FileStore, neutral domain owner, provenance, request/result |
| **[B-WINDOWS]** | [Текущее состояние `stratbox-windows`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md) | GUI/runtime, local JSON, preferences, presence, assignments, background |
| **[B-MULTI]** | [Многопользовательская работа одного узла](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md), §§VI–XXVI | shared state, read cursors, sessions, ACL, SQLite, notifications, reconnect |
| **[B-WEB]** | [Web/self-hosted/host архитектура](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md), §§IV, VI, XII, XIX–XX, XXIV | headless authority, DB profiles, sessions, web persistence, backup, remote |
| **[B-BACKGROUND]** | [Фоновые задачи и процессы](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md), §§III, VII–XII | automation lifecycle, trigger occurrence, scheduler durability, job leases |
| **[B-SETTINGS]** | [Системные настройки и preferences](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_system_settings_research_2026-10-07.md), §§3–5, 30–35, 45, 54–58 | settings/surface/drafts/policy separation, migrations, user sync |
| **[B-OBS]** | [Observability, ошибки и логи](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_observability_errors_logs_research_2026-10-07.md), §§14–23, 26–29 | product log refs, technical evidence, ProblemRef bridge, notification scope |
| **[B-ARTIFACT]** | [Файловый и артефактный слой](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md), §§II, XI–XVII | artifact IDs, manifests, physical bytes, lifecycle, catalog/SQLite, CAS alternatives |
| **[B-AUTO]** | [Автоматизация и ИИ](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md), §§III–VI, XIV–XIX | scheduler, AgentRun, effect approvals, AI actor/credentials |
| **[B-EXEC]** | [Управление исполнением и путь пользователя](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_execution_control_user_path_research_2026-10-07.md), §§IV, VI, VIII–XI | drafts vs run snapshot, cancel, revisions, shared state, retries |
| **[B-SOURCE]** | [Governance источников и справочников](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_registry_source_governance_research_2026-10-07.md) | source freshness, registry versions, materialized resources |
| **[B-IO]** | [FileStore и файловые форматы](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md) | physical storage semantics, safety/streaming, paths |
| **[B-STYLE]** | [Кастомизация артефактов и style sets](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md) | user/report defaults, stable style identity/version/provenance |
| **[B-TARGET]** | [Целевая архитектура core](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_target_core_design_architecture_2026-10-07.md) | domain/application ownership и нейтральный operation contract |
| **[B-UI]** | [Требования к Windows-интерфейсу](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_windows_interface_requirements_research_2026-10-07.md) | projection/state/UI portability |

В более периферийных исследованиях второй ветки (визуальная система, motion, переносимость бизнес-сегментов, machine schemes и внешний когнитивный контур) для темы 05 существенны главным образом общие принципы: renderer не владеет shared semantic state, machine/external actors не обходят продуктовые полномочия, идентичности definitions и reproducibility остаются versioned. Дополнительная детализация их предметных подсистем здесь сознательно не повторяется.

### 22.3. Непосредственно проверенные code paths implementation owners

| Ключ | Публичный файл / контракт | Подтверждённый факт |
|---|---|---|
| **[W-HISTORY]** | [`application/history/persistence.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/history/persistence.py) | пять файлов, separate writes, `[]` on parse error/invalid entries |
| **[W-CONFIG]** | [`runtime/config.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/config.py) | объединённый `AppUserConfig`, direct write, invalid JSON raises error |
| **[W-PREF]** | [`runtime/user_preferences.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/user_preferences.py) | values/form drafts и layout сохраняются вместе |
| **[W-SESSION]** | [`runtime/session_runtime.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/session_runtime.py) | platform session/runtime state JSON surfaces, version validation |
| **[W-CASE]** | [`application/cases/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/cases/models.py), [`store.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/cases/store.py) | run-like Case, `unread`, local collection |
| **[W-EVENT]** | [`application/events/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/events/models.py), [`store.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/events/store.py) | event kinds/actor semantics, timestamp sorting, `unread` |
| **[W-PRESENCE]** | [`application/presence/service.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/presence/service.py) | локальная participant projection |
| **[W-BACKGROUND]** | [`application/background/store.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/background/store.py) | in-memory enabled/status, no durable scheduler |
| **[W-ASSIGN]** | [`application/assignments/store.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/assignments/store.py) | local assignment collection |
| **[A-NODE]** | [AppDock Node owner](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/node/README.md) | node identity/layout/topology/health owner, separate lifecycle |
| **[A-SESSIONS]** | [AppDock Sessions owner](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/sessions/README.md) | platform session lifecycle and continuity |
| **[A-ACTIVE]** | [AppDock ActiveSessionsStore](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/sessions/active/active_sessions.py) | shared active session projection with atomic JSON writes |
| **[A-OBS]** | [AppDock Observability boundary](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/observability/README.md) | ProblemOccurrence/Ref ownership and declared rollout limits |

### 22.4. Внешние технические первоисточники

1. [SQLite — Write-Ahead Logging](https://www.sqlite.org/wal.html): reader/writer concurrency, one writer, host-local shared-memory requirement, WAL/checkpoint risks.
2. [SQLite — Online Backup API](https://www.sqlite.org/backup.html): согласованный backup работающей SQLite DB и ограничения file-level копирования.

### 22.5. Исторический материал и степень проверки

`01-old-notes` учтён **только как история проектных предположений**. Прежние схемы, предполагавшие, что GUI является владельцем основной бизнес-логики и всех запусков, не имеют CURRENT-статуса: текущая реализация уже разделяет core и Windows surface, а целевая consolidation отделяет ещё и headless application authority. Исторические заметки не использованы для объявления фактов о новых contracts.

**Ограничение верификации:** исследования `02-base-study` являются вторичным корпусом; проведена выборочная повторная проверка актуальных файлов Windows/AppDock и сверка со свежей темой 04. Полный end-to-end запуск Windows/AppDock, SQL pilot, multi-user network test и fault-injection suite **не выполнялись**. Поэтому все новые таблицы, API, migrations, auth scopes и performance claims здесь маркированы TARGET/UNKNOWN, а не CURRENT.

---

## 23. Финальный исследовательский вывод

В рамках темы 05 наиболее важное решение — **сделать авторитетное состояние независимым от пользовательского представления и от физического файла**. Это создаёт общий фундамент для Work и долгих вычислений, нескольких пользователей и устройств, безопасной автоматизации, воспроизводимых артефактов и восстановления после аварий.

Текущий Strategy Box уже располагает удачными кирпичами — domain core, operation/scenario semantics, cases/events/artifact refs, AppDock integration и исследовательски проработанной node collaboration моделью. **Проблема состоит не в полном отсутствии состояния, а в его локальности, смешении scopes и недостаточной согласованности записи.** Пять JSON проекций, Qt-owned execution и per-object `unread` были разумными для desktop-prototype, но превращать их в распределённую модель через файлы и lock-файлы нецелесообразно.

Предпочтительное направление: один transport-neutral application authority, ограниченный transactional store, immutable execution/artifact refs, outbox и per-user projections; SQLite в local node profile и server DB по реальной потребности. AppDock продолжает владеть жизненным циклом узла и сессий; `stratbox` — предметными данными и доказательностью; Windows/Web/Android — интерфейсами. Неразрешённые вопросы (authorized cursors, backup epochs, restore clones, migrations, retention) явно сохранены как проверяемые инженерные задачи.

**Следующий конструктивный шаг — не создавать ещё одну серию абстракций, а реализовать один проверяемый сквозной сценарий с durable Work/Job, двумя клиентами, отказом процесса и восстановлением результата.** После этого уже можно принимать решения о физических репозиториях, реальном серверном профиле и объёме общей БД.
