# Strategy Box: многопользовательская работа в рамках единого узла

**Research branch:** вторая ветка исследований Strategy Box  
**Дата:** 2026-10-07  
**Область:** `stratbox` + `stratbox-windows` + граница AppDock  
**Статус:** Research Result — анализ текущего состояния и целевая архитектура; документ сам по себе не меняет код или продуктовые контракты.

---

## 0. Краткий вывод

В Strategy Box уже существует значительная часть **семантики многопользовательской работы**, хотя реального общего collaboration/runtime слоя пока почти нет. `stratbox-windows` уже умеет показывать участников, различать авторов кейсов, строить входящие и исходящие карточки в сценарном чате, хранить поручения, связывать кейсы с логами и артефактами, показывать фоновые уведомления и держать идентичность `node/session/user/host`. AppDock, со своей стороны, уже имеет модель узла, пользовательских сессий и общую проекцию активных сессий узла. Значит, архитектурно мы стартуем не с пустого места.

Главная проблема текущего состояния — **истина остаётся локальной внутри каждого процесса `stratbox-windows`**. Кейсы, события, поручения, логи и артефакты живут в in-memory stores и затем сохраняются в локальные JSON-проекции. `PresenceService` знает наверняка только о текущем пользователе. Ограничение «один сценарий одновременно» действует только внутри одного GUI-процесса. Если два пользователя откроют Strategy Box на одном узле, каждый экземпляр приложения сможет построить собственную историю и собственное представление о том, что сейчас происходит. Это ещё не многопользовательская система.

Целевая модель должна быть другой:

> **узел — единая рабочая среда; пользовательские клиенты — проекции одного общего операционного состояния узла.**

При этом многопользовательская работа в Strategy Box прежде всего должна быть **информативной и координационной**, а не превращаться в редактор совместного текста. Пользователю важно видеть, кто находится на узле, что запущено, кем запущено, что стоит в очереди, где возникла ошибка, какие артефакты появились, кому поручена проверка, какие фоновые процессы активны и какие действия сейчас допустимы. Для большинства аналитических сценариев этого достаточно, чтобы совместная работа ощущалась живой, понятной и безопасной.

Целевая цепочка выглядит так:

```text
Windows client A ─┐
Windows client B ─┼─ AppDock identity / sessions / access
Android client ───┘                 │
                                    ↓
                         Strategy Box node runtime
                         ├─ shared cases/timeline
                         ├─ node-wide job queue
                         ├─ presence projection
                         ├─ assignments/approvals
                         ├─ artifacts/log index
                         ├─ notifications/read state
                         └─ shared app persistence
                                    │
                                    ↓
                         Execution backend / workers
                                    │
                                    ↓
                               stratbox core
```

При этом границы ответственности должны остаться строгими:

- **AppDock** владеет идентичностью узла, lifecycle пользовательских сессий, active-session picture, access/capability vocabulary, node health, платформенными проблемами и будущим remote attach/transport;
- **Strategy Box application runtime** владеет кейсами, jobs, сценарной timeline, app-level events, поручениями, app-level уведомлениями, фоновыми сценариями и metadata артефактов;
- **`stratbox` core** владеет предметными операциями, результатами, diagnostics/provenance и не знает про пользователей, presence, GUI или collaboration;
- **Windows/Android UI** отображают общее состояние, держат только локальные preference/draft/navigation state и не являются источником истины.

Самый важный следующий шаг — не расширять ещё сильнее визуальные каркасы «Участники» и «Поручения», а создать **общий node-scoped application state и node-wide execution coordination**. После этого большая часть уже существующего UX начнёт работать по-настоящему.

---

# I. Рамка исследования

## 1. Что именно означает «многопользовательская работа в рамках единого узла»

В этом исследовании под единым узлом понимается одна управляемая среда Strategy Box, в которой находятся данные, установленный продукт, runtime state, история выполнения, фоновые задачи и доступные surfaces. К одному узлу могут одновременно подключаться несколько пользовательских сессий — локальных или, в будущем, удалённых.

Ключевая мысль: **узел остаётся один, пользовательских точек входа может быть несколько**.

Например:

```text
Узел OFFICE-SB-01
├─ пользователь A / Windows session
├─ пользователь B / Windows session
├─ пользователь A / Android companion session
└─ background/system actor
```

Все они должны видеть одну и ту же объективную картину выполнения Strategy Box, но разные пользовательские проекции:

- пользователь A видит свои непрочитанные события;
- пользователь B — свои;
- оба видят один и тот же запущенный case;
- право остановить case может быть только у автора и оператора;
- технический traceback может быть доступен оператору, но не каждому участнику;
- Android может видеть состояние и артефакты, но тяжёлая работа остаётся на узле.

## 2. Что в scope

В scope входят:

- присутствие и список участников узла;
- несколько одновременных пользовательских сессий;
- общий сценарный timeline;
- общие cases/events/jobs;
- node-wide очередь выполнения;
- конкурентный запуск и конфликты ресурсов;
- фоновые сценарии;
- поручения, ownership и approvals;
- общие артефакты и связь с логами;
- per-user unread/notifications;
- права и capability-based actions;
- отображение node-wide и user-local ошибок;
- reconnect/offline/stale session;
- подготовка общей семантики к Windows + Android + remote clients;
- безопасное участие будущих AI actors.

## 3. Что сознательно не является целью

Целевая модель не должна автоматически превращать Strategy Box в:

- универсальный корпоративный мессенджер;
- аналог Google Docs с одновременным редактированием каждой таблицы;
- систему общего файлового редактирования без locking/versioning;
- отдельную IAM-платформу;
- второй AppDock внутри Strategy Box;
- распределённый cluster scheduler для десятков узлов.

Первый зрелый многопользовательский контур должен решать **операционную осведомлённость, координацию и безопасное совместное использование одного узла**.

---

# II. Источники и фактический срез

## 4. Использованные материалы

Исследование опирается на:

1. полный research-срез `stratbox-windows` от 2026-10-06;
2. полный research-срез `stratbox` core от 2026-10-06;
3. базовое описание AppDock;
4. актуальный `main` `ForestTiger-GH/stratbox-windows`, дополнительно перепроверенный 2026-10-07;
5. актуальную архитектуру AppDock, включая Node, Sessions, Access, Execution и Observability domains;
6. официальную документацию SQLite по transaction isolation и WAL — только для оценки локального shared-state storage.

На момент дополнительной проверки `stratbox-windows/main` по-прежнему указывает на commit:

```text
959e9c4ce1441124af5111c1e025041714e04d3b
```

Поэтому базовый research-срез от 2026-10-06 остаётся репрезентативным для текущего кода.

## 5. Иерархия фактов

В документе различаются три уровня:

- **реализовано сейчас** — подтверждено текущим кодом;
- **архитектурный задел** — модели/поля/UI уже существуют, но backend-механика отсутствует;
- **целевая рекомендация** — предлагаемая следующая архитектура.

Это особенно важно для presence, background, assignments, remote execution и AI: пользовательская семантика там уже заметна, но реальная инфраструктура значительно слабее UI.

---

# III. Что уже реализовано в `stratbox-windows`

## 6. Уже есть правильная пользовательская информационная архитектура

Desktop surface уже построена вокруг шести режимов:

```text
Проводник
Сценарии
Каскады
Фоновые процессы
Участники
Поручения
```

Центральный сценарный чат уже показывает:

- cases;
- системные уведомления;
- background notices;
- assignment notices;
- автора;
- текущее состояние;
- этап выполнения;
- параметры;
- артефакты;
- время.

Есть фильтры «Все», «Мои», «В работе», «Успешные», «Ошибки», «Непрочитанные».

Это очень важный вывод: **основной UX многопользовательской работы уже придуман в правильном направлении**. Его не нужно заменять отдельным «collaboration center». Нужно сделать существующие поверхности проекциями общего node state.

## 7. Case уже имеет автора

`ScenarioRunCase` уже хранит:

```text
case_id
scenario_id / scenario_title
params
status
created_at / started_at / finished_at
author_id / author_label
current_stage
steps
outputs
message
unread
```

Именно `Case` логично оставить центральным пользовательским объектом запуска.

С точки зрения будущего multi-user UX это уже даёт естественные формулировки:

```text
«Обновление данных ЦБ»
Запустил: Иван Петров
Статус: выполняется
Этап: загрузка источников
```

Вместо технической схемы «thread/process/task id» пользователь видит понятный рабочий объект.

## 8. Events уже имеют actor semantics

Существуют event kinds:

```text
case_prepared
case_started
case_completed
case_failed
step_started
step_completed
step_failed
artifact_created
system_notice
background_notice
assignment_notice
```

И actor kinds:

```text
user
host_user
ai
system
background
```

То есть модель уже допускает события от:

- текущего пользователя;
- другого пользователя узла;
- фоновой системы;
- AI actor;
- системного runtime.

Это сильный семантический фундамент для общей timeline.

## 9. Scenario Chat уже различает «свои» и «чужие» сообщения

`presentation/common/scenario_chat/projector.py` размещает:

- кейсы текущего пользователя как `outgoing`;
- кейсы других пользователей как `incoming`;
- system/background/AI events как `incoming`.

Это особенно ценно для будущего Android, потому что семантика проекции уже находится вне конкретных Qt widgets.

## 10. Presence model уже существует

`ParticipantRecord` содержит:

```text
participant_id
display_name
is_online
host_name
last_seen_label
run_count
accent_color
```

`PresenceService` при старте создаёт текущего пользователя и способен зарегистрировать автора найденного case.

Сейчас у этого есть серьёзное ограничение: новый участник, обнаруженный из истории кейсов, помечается offline. Только текущий пользователь гарантированно online. Сетевого/узлового provider-а присутствия нет.

Следовательно, **presence UI существует, presence truth отсутствует**.

## 11. Поручения уже оформлены как самостоятельная сущность

`AssignmentRecord` содержит:

```text
assignment_id
title
status = active/completed/cancelled
assignee_id
author_id
description
scenario_id
case_id
artifact_id
created_at
completed_at
```

Это почти готовая семантика shared task/hand-off внутри узла.

Однако текущий `AssignmentStore` — обычный process-local dict, а persistence — локальный JSON. Remote delivery, notifications, deadline, comments и server-side ownership отсутствуют.

## 12. Background UI и state vocabulary уже есть

`BackgroundProcessState` уже понимает:

```text
enabled
status = disabled/idle/running/warning/error
last_run_at
next_run_at
last_result
last_error
```

Но `BackgroundProcessStore` сейчас только меняет значения в памяти. Scheduler, timer/event trigger и executor отсутствуют.

Здесь особенно важно избежать неправильного следующего шага: background engine не должен становиться второй системой выполнения рядом со scenarios. Фоновый процесс должен **запускать тот же scenario/job engine**, только другим trigger-ом и actor-ом.

## 13. Artifacts уже first-class metadata

`ArtifactRecord` связывает результат с:

- автором;
- scenario;
- case;
- operation;
- log;
- временем создания.

Это естественная shared-сущность. В многопользовательской системе артефакт должен существовать один раз и появляться у всех участников, которым разрешено его видеть.

## 14. Logs уже связаны с execution graph

`LogRecord` связывает лог с:

```text
case_id
scenario_id
operation_id
step_id
```

Это хорошая основа для общего Inspector: участник открывает case и сразу видит именно его логи.

Но текущая модель хранит прежде всего файловый `path`. Для remote/mobile/multi-user contract этого недостаточно: shared слой должен оперировать `log_id/log_ref`, а локальный host adapter уже разрешает ссылку в физический путь.

## 15. Текущая persistence — сознательно локальная

`HistoryPersistenceService` сохраняет пять отдельных файлов:

```text
cases.json
events.json
artifacts.json
logs.json
assignments.json
```

Сам код прямо описывает это как lightweight recent history, а не database-grade durability.

В текущем виде отсутствуют:

- atomic multi-object transaction;
- locking;
- schema version для history files;
- consistency между пятью файлами;
- retention;
- явная ошибка при повреждении — повреждённый JSON может превратиться в пустую историю.

Для одного desktop-процесса это было разумно. Для многопользовательской истины — уже нет.

## 16. Ограничение «один сценарий» сейчас локальное, а не узловое

`ScenarioCoordinator` имеет один `QThread` и один `_active_case`. Новый `submit()` при busy-state отклоняется.

Это означает:

```text
Client A -> максимум 1 scenario
Client B -> максимум 1 scenario
```

но не:

```text
Node -> максимум 1 конфликтующий scenario
```

Два пользователя на одном узле смогут одновременно запустить две операции, которые оба GUI считают допустимыми. Node-wide coordination пока отсутствует.

---

# IV. Что уже даёт AppDock

## 17. Узел уже является правильным верхнеуровневым объектом

В продуктовой модели AppDock узел — это рабочая среда продукта, где живут состояние, действия, результаты, история, readiness, логи и будущая удалённая работа.

Для Strategy Box это очень удачное совпадение: collaboration не нужно строить вокруг абстрактной «комнаты». Естественная область совместной работы — **Node**.

## 18. Sessions уже являются отдельным authority

В актуальной AppDock architecture `Sessions` отвечает за lifecycle пользовательского участия.

`SessionState` уже содержит:

```text
session_id
user_id
account_name
host_name
node_id
started_at_utc
attach_mode
status / lifecycle_state
last_updated_at_utc
world_id
active_surface_id
runtime_state_ref
app_pid
...
```

То есть продукту уже не требуется самостоятельно изобретать идентичность «кто сейчас открыл приложение».

## 19. Уже существует shared ActiveSessionsStore

В AppDock есть `ActiveSessionsStore`, который хранит на уровне узла отдельную atomic JSON projection для каждой активной сессии:

```text
<active_sessions_dir>/<session_id>.json
```

`ActiveSessionProjection` содержит:

```text
session_id
node_id
user_id
account_name
host_name
started_at_utc
last_state_change_at_utc
lifecycle_state
effective_data_root_path
degraded_launch
active_surface_id
app_pid
```

Это фундаментально важный факт: **AppDock уже имеет инфраструктурную форму, в которой несколько сессий одного узла могут сосуществовать одновременно**.

Пробел находится на стороне product boundary: `stratbox-windows` получает ссылку только на свою active-session projection и не имеет публичного provider-а безопасного списка/потока всех активных сессий узла.

## 20. Runtime state уже имеет heartbeat

Strategy Box session client читает и обновляет per-session runtime state, где уже есть:

```text
heartbeat_utc
resumable
clean_shutdown
active_view
selected_object
active_job
warnings
```

Это естественная основа для вычисляемого presence.

Однако presence не следует реализовывать прямым обходом внутренних каталогов AppDock из `stratbox-windows`. Нужна публичная boundary уровня AppDock, например:

```text
NodeParticipationProvider
NodeActiveSessionsReader
PresenceSnapshotProvider
```

Точное имя вторично. Важна граница: продукт получает безопасную typed projection, а физическая структура AppDock остаётся внутренней.

## 21. Access уже выделен в отдельный domain, но пока минимален

В AppDock присутствует vocabulary:

```text
Role(role_id)
CapabilityGrant(capability_id, granted)
SubjectIdentity(subject_id, role_name)
```

Это правильное направление, однако текущая форма ещё очень тонкая. Для Strategy Box стоит проектировать capability-based UX уже сейчас, но считать зрелое централизованное enforcement следующим уровнем AppDock integration, а не уже готовой функцией.

## 22. Observability уже идёт к canonical problems и audience-safe projection

AppDock Observability отделяет:

- внутреннюю техническую ошибку;
- canonical `ProblemOccurrence/ProblemRef`;
- node/session relation;
- безопасное объяснение для конкретной аудитории.

Это очень полезно для multi-user Strategy Box: одна ошибка узла не должна превращаться в пять разных traceback-ов у пяти пользователей. Должно существовать **одно подтверждённое узловое problem occurrence**, которое получает несколько безопасных пользовательских проекций.

---

# V. Главный архитектурный разрыв

## 23. Сейчас каждый клиент фактически строит собственный маленький мир

Текущая схема:

```text
Client A
├─ CaseStore A
├─ EventStore A
├─ ArtifactStore A
├─ LogStore A
├─ AssignmentStore A
└─ history/*.json A

Client B
├─ CaseStore B
├─ EventStore B
├─ ArtifactStore B
├─ LogStore B
├─ AssignmentStore B
└─ history/*.json B
```

Даже если оба работают с одним Data root, application state остаётся разным.

Целевая схема:

```text
                    ┌─ Client A projection
Shared node state ──┼─ Client B projection
                    └─ Android projection
```

## 24. UI не должен владеть общей истиной

Это ключевой архитектурный закон.

Qt main window может:

- выбрать фильтр;
- открыть inspector;
- выбрать case;
- держать draft формы;
- хранить размер окна.

Но Qt main window не должен определять:

- какие cases существуют;
- кто online;
- какой job running;
- завершено ли поручение;
- создан ли артефакт;
- была ли ошибка узла.

То же самое относится к будущему Android UI.

## 25. Общий Data root сам по себе не решает collaboration

Нельзя считать, что совместный workspace автоматически означает совместное приложение.

Общий файловый каталог не даёт:

- упорядоченную timeline;
- identity автора;
- queue;
- cancellation ownership;
- read receipts;
- transaction safety;
- node-wide locks;
- assignment state;
- notification routing.

Поэтому shared application state должен существовать отдельно от business data files.

---

# VI. Целевая модель одного узла

## 26. Узел как единый operational world

Целевой Strategy Box Node должен предоставлять одну общую операционную картину:

```text
Node
├─ participants / sessions
├─ cases
├─ jobs / queue
├─ activity events
├─ background triggers
├─ assignments / approvals
├─ artifacts
├─ log references
├─ app-level problems/notifications
├─ read cursors
└─ resource claims
```

Клиенты только получают snapshot, слушают изменения и отправляют команды.

## 27. Participant и Session — разные сущности

Это принципиально.

Один человек может иметь несколько сессий:

```text
User A
├─ Windows desktop / office PC
└─ Android companion / phone
```

Поэтому UI «Участники» должен агрегировать данные по `user_id`, а сессии показывать как детали.

Рекомендуемая модель:

```text
Participant
├─ user_id
├─ display_name
├─ presence_status
├─ last_seen_at
├─ active_session_count
├─ active_job_count
└─ sessions[]
```

`Session`:

```text
session_id
surface_id
host/device label
attach_mode
started_at
last_heartbeat
lifecycle
active_job_id?
```

## 28. Presence лучше вычислять, а не хранить как произвольный bool

Текущий `is_online: bool` удобен для UI, но как authority слаб.

Целевая логика:

```text
active AppDock session
+ свежий runtime heartbeat
+ lifecycle != ended
→ online

active session, heartbeat устарел
→ stale / connection lost

active sessions отсутствуют
→ offline
```

Конкретный TTL следует сделать configurable и подобрать эксплуатационно; его не стоит превращать в зашитую бизнес-семантику.

## 29. Presence — ephemeral projection

Presence не должен превращаться в огромный audit trail «кто в какую секунду был online».

Долговременно полезны:

- user/session identity;
- авторство действий;
- started/ended lifecycle;
- last seen в разумном retention.

А каждое heartbeat-событие хранить в общей timeline не нужно.

---

# VII. Общий Scenario Timeline

## 30. Сценарный чат уже является правильной формой общей timeline

Strategy Box не нужен отдельный чат «привет, коллеги» как центральный элемент. Пользовательская ценность уже находится в operational messages:

```text
Иван запустил «Обновление данных ЦБ»
Сценарий поставлен в очередь
Запущен этап «Загрузка источников»
Создан artifact ...xlsx
Сценарий завершён с замечаниями
Марии назначена проверка результата
На узле возникла проблема с Data root
```

Это и есть естественная collaboration timeline аналитического инструмента.

## 31. События должны быть append-only

Рекомендуется ввести node-level последовательность:

```text
node_seq = 1001
node_seq = 1002
node_seq = 1003
...
```

Каждое подтверждённое событие получает монотонный номер от authoritative node runtime.

Плюсы:

- стабильный порядок между несколькими процессами;
- reconnect «дай всё после seq=1003»;
- простой unread cursor;
- обнаружение пропусков;
- детерминированная синхронизация Windows/Android.

`created_at` остаётся полезным для UI, но не должен быть единственной основой порядка.

## 32. Snapshot + event stream

Классическая целевая схема клиента:

```text
1. GET collaboration snapshot
2. snapshot.last_seq = 1034
3. render current projections
4. subscribe/poll events after 1034
5. apply 1035, 1036, ...
6. при gap → refetch snapshot
```

Это намного устойчивее, чем многократно перечитывать пять shared JSON-файлов.

## 33. Case — shared object, UI card — projection

Case должен существовать один раз в общем node state.

Клиенты могут по-разному его отображать, но не должны иметь собственные версии статуса.

Например:

```text
case_id = c123
status = running
owner = user-A
job_id = j456
revision = 7
```

Client A может пометить карточку прочитанной, Client B — оставить непрочитанной. Сам `Case.status` от этого не меняется.

---

# VIII. Критическая правка: unread должен стать per-user

## 34. Текущая модель `unread: bool` не подходит для multi-user

Сейчас `ScenarioRunCase` и `OperationalEvent` несут общий `unread`.

В многопользовательской системе это создаёт ошибочную семантику:

```text
User A открыл case → unread=False
User B внезапно тоже считает его прочитанным
```

## 35. Целевая модель — Read Cursor / Receipt

Для обычной timeline достаточно:

```text
UserReadCursor
├─ node_id
├─ user_id
└─ last_seen_seq
```

Тогда событие непрочитано для пользователя, если:

```text
event.node_seq > cursor.last_seen_seq
```

Для адресных сущностей — поручений, mentions, approvals — можно дополнительно иметь отдельный receipt:

```text
NotificationReceipt
notification_id
user_id
seen_at
acted_at?
```

Таким образом «Непрочитанные» становится действительно персональным фильтром.

---

# IX. Node-wide execution и очередь

## 36. Case и Job стоит разделить

Пользовательский `Case` — рабочий объект сценария.

`Job` — исполнительный объект узла.

```text
Case
  «что хотел пользователь и что он видит»
        │
        └── job_id
                ↓
Job
  «где стоит в очереди, кто исполняет, cancellation, lease, retry»
```

Это позволит не засорять case-модель низкоуровневыми execution details.

## 37. Все виды запуска должны идти через один Job Manager

Одинаковый путь должны использовать:

- ручной запуск пользователем;
- composite scenario;
- background trigger;
- assignment-driven run;
- AI actor;
- remote Android command.

```text
Submit scenario
    ↓
validate access + params
    ↓
create Case
    ↓
create Job
    ↓
Node Job Manager
    ↓
ExecutionBackend
    ↓
ScenarioRunner / stratbox operation
```

Не должно быть отдельного executor для фоновых процессов и ещё одного для remote tasks.

## 38. Node-wide concurrency policy вместо одного глобального busy-флага

Простой вариант «на узле всегда только один job» безопасен, но быстро станет неудобным.

Лучше операции/сценарии декларируют политику:

```text
parallel
serial_per_resource
exclusive_node
```

И resource claims:

```text
read:source:cbr
write:dataset:escrow
write:path:output/escrow
exclusive:workspace_cleanup
```

Тогда два независимых read-only расчёта смогут выполняться параллельно, а две записи в один dataset — корректно сериализуются.

## 39. Расширение Operation/Scenario descriptors

Уже существующие specs естественно дополнить:

```text
required_capabilities
concurrency_mode
resource_claims
cancellable
idempotency_policy
dangerous
requires_confirmation
visibility_policy
parameter_visibility
artifact_policy
```

Это лучше, чем зашивать concurrency в конкретный UI handler.

## 40. Queue — общая и видимая

Пользователь должен видеть:

```text
Выполняется: 2
В очереди: 3
```

У case в очереди полезно показывать причину:

```text
Ожидает завершения «Обновление эскроу»,
которое использует тот же dataset.
```

Это очень сильная UX-функция: система объясняет ожидание вместо ощущения «кнопка не работает».

## 41. Cancellation должна быть cooperative и permissioned

Статус `cancelled` уже существует, но реального cancel path сейчас нет.

Целевой механизм:

```text
cancel requested
→ worker receives cancellation token
→ safe checkpoint
→ cleanup/abort
→ authoritative terminal state
```

Права:

- автор — остановить свой job, если операция cancellable;
- оператор — остановить любой разрешённый job;
- viewer — только наблюдать.

Если после destructive boundary точное состояние неизвестно, job не должен ложно становиться `cancelled/success`; нужен `unknown/interrupted` outcome.

## 42. Idempotency обязательна для reconnect и mobile

Команда клиента должна иметь `command_id`/idempotency key.

Если сеть оборвалась после submit, Android/Windows может повторить запрос. Узел должен вернуть уже созданный case/job, а не выполнить операцию второй раз.

---

# X. Workspace и конфликты ресурсов

## 43. Главная опасность — не два пользователя, а две записи в один ресурс

Многопользовательская система может безопасно выполнять много задач параллельно, пока они независимы.

Конфликт появляется, если:

- две операции пишут один output;
- одна очищает каталог, другая читает его;
- два процесса обновляют один cache;
- один background refresh совпадает с manual refresh;
- пользователь запускает destructive cleanup во время другого job.

## 44. Нужны resource leases/claims

Рекомендуемая сущность:

```text
ResourceLease
├─ lease_id
├─ resource_key
├─ mode = read/write/exclusive
├─ job_id
├─ acquired_at
└─ expires/recovery metadata
```

Это не должно превращаться в distributed lock manager. В рамках одного узла достаточно локальной authority.

## 45. Run-scoped output paths

Чтобы резко уменьшить collision risk, артефакты лучше сначала писать в run-scoped namespace:

```text
output/<operation>/<case_id>/...
```

После успешного завершения при необходимости публиковать stable alias/current result атомарно.

Так два запуска не будут незаметно перетирать друг друга.

## 46. Внешнее ручное редактирование файлов имеет другие гарантии

Strategy Box способен координировать **свои собственные операции**.

Если пользователь открыл XLSX во внешнем Excel и вручную изменяет его, application runtime не знает полной истины. Поэтому Explorer не должен создавать иллюзию универсальной distributed file locking.

Достаточно:

- хорошо координировать app-managed writes;
- показывать предупреждение при известных конфликтах;
- использовать atomic publication;
- по возможности хранить content hash/version metadata.

---

# XI. Shared persistence

## 47. Пять JSON-файлов не стоит развивать в shared database

Можно было бы добавить lock-файлы и продолжить совместно писать `cases.json`, `events.json` и т. д. Это приведёт к сложной системе частичных блокировок и race conditions.

С учётом правила проекта «обратная совместимость не нужна» лучше сделать чистый переход к настоящему node-scoped transactional store.

## 48. Практичный вариант для одного узла — SQLite

Для node-local metadata SQLite подходит очень хорошо:

- несколько процессов могут читать одну БД;
- транзакции дают атомарность;
- один writer сериализуется движком;
- WAL позволяет readers и writer работать параллельно;
- нет отдельного server deployment.

Критическое ограничение: WAL рассчитан на процессы **одного хоста** и не должен использоваться как SQLite-файл на сетевой шаре.

Следовательно:

> shared Strategy Box metadata DB должна жить в AppDock-provided **node-local app/system storage**, а не в пользовательском Data root и не в SMB/network share.

Удалённые Windows/Android клиенты обращаются к ней через node runtime/API/bridge, а не открывают файл БД напрямую.

## 49. Пример схемы shared store

Минимально:

```text
events
cases
case_steps
jobs
artifacts
logs
assignments
background_processes
resource_leases
read_cursors
notification_receipts
```

Опционально позже:

```text
comments
approvals
watchers
artifact_versions
```

## 50. Что хранить в БД, а что в файлах

В БД:

- identity/ref;
- lifecycle/status;
- связи;
- безопасные display metadata;
- event sequence;
- assignment state;
- artifact metadata;
- log references;
- resource claims;
- read cursors.

В файлах:

- большие артефакты;
- физические логи;
- datasets;
- exports;
- caches.

БД хранит ссылки/identity, а не гигантские Excel/ZIP blobs.

## 51. Обязательные storage свойства

Новая persistence должна иметь:

- schema version;
- explicit migration/current-schema policy;
- foreign keys;
- transactions;
- busy timeout;
- crash-safe commits;
- explicit corruption/inaccessible state;
- backup/recovery policy;
- retention;
- no silent fallback to empty state.

Последний пункт особенно важен: повреждённое общее состояние нельзя трактовать как «на узле просто нет кейсов».

---

# XII. Shared-state API вместо прямого доступа UI к БД

## 52. Нужна transport-neutral application boundary

Даже если первая реализация работает в одном процессе или через SQLite, UI не должен импортировать SQLite repository напрямую.

Рекомендуемый contract family:

```text
CollaborationReader
CollaborationCommandPort
ActivitySubscription
JobControlPort
PresenceReader
```

Либо более предметные names. Главное — отделить семантику от транспорта.

## 53. Windows и Android должны использовать одинаковые contracts

```text
presentation/common
        ↓
application client contracts
        ↓
local IPC / in-process adapter   ← Windows local
remote AppDock bridge/API        ← Android / remote
        ↓
Strategy Box node runtime
```

Это позволит не копировать Qt-specific runtime в Android.

## 54. Нужен ли отдельный новый репозиторий node-runtime прямо сейчас

Не обязательно.

На ближайшем этапе чистую общую логику можно разместить в toolkit-neutral слоях `stratbox-windows`:

```text
application/
runtime/
presentation/common/
adapters/
```

с жёстким запретом зависимости на Qt внутри shared orchestration.

Если позже node-side lifecycle станет самостоятельным — например, runtime должен жить без открытого desktop-клиента, обслуживать Android и выполнять background jobs круглосуточно — тогда появится естественная причина вынести его в отдельный shared package/repository.

Создавать четвёртый репозиторий раньше этой необходимости не требуется.

---

# XIII. Background processes как node-scoped automation

## 55. Background process принадлежит узлу, а не пользователю

Если «мониторинг публикаций ЦБ» включил пользователь A, второй экземпляр Strategy Box не должен запускать ещё один такой мониторинг.

Должно существовать одно node-wide состояние:

```text
process_id
configured/enabled
trigger
last_run
next_run
last_result
last_error
managed_by
```

## 56. Background trigger создаёт обычный Job

```text
schedule/event trigger
        ↓
background actor
        ↓
submit scenario command
        ↓
Node Job Manager
        ↓
обычные Case/Event/Artifact механизмы
```

Тогда:

- background execution видно в том же сценарном чате;
- конкуренция с manual run решается теми же resource claims;
- ошибки маршрутизируются тем же notification engine;
- артефакты имеют тот же lineage.

## 57. Управление background должно быть capability-based

Обычный viewer может видеть, что процесс работает.

Оператор может:

- включать/выключать;
- запускать сейчас;
- менять разрешённые trigger settings;
- повторять failed run.

---

# XIV. Assignments, ownership и approvals

## 58. Поручения — главный lightweight collaboration primitive

Для Strategy Box поручения гораздо полезнее общего мессенджера.

Примеры:

```text
«Проверь выгрузку по эскроу» → Мария
«Подтверди удаление старого набора» → Оператор
«Разбери ошибку источника» → Иван
```

## 59. Assignment должен стать shared node object

Рекомендуемые поля:

```text
assignment_id
kind
status
assignee_id
author_id
title
description
case_id?
artifact_id?
problem_ref?
due_at?
created_at
completed_at
revision
```

## 60. Автоматическое «проверить результат» стоит сделать политикой, а не всегда создавать

Сейчас новый case автоматически создаёт локальное поручение на проверку результата.

В реальной работе это может быстро превратиться в шум.

Лучше scenario descriptor явно говорит:

```text
review_policy = none / optional / required
```

И только действительно review-required сценарии создают assignment автоматически.

## 61. Approval можно построить рядом с Assignment

Dangerous operations уже имеют семантический задел.

Целевая схема:

```text
User A submits dangerous action
→ Case = waiting_for_approval
→ ApprovalRequest / Assignment to operator
→ operator approves/rejects
→ Job enters queue or case terminates
```

Это хорошо масштабируется на удалённый Android: пользователь получает компактное подтверждение, не открывая desktop.

---

# XV. Artifacts как общий результат работы

## 62. Shared artifact должен ссылаться на producer, а не только на path

Текущая path-oriented модель достаточна для local desktop, но target contract лучше сделать таким:

```text
ArtifactRef
├─ artifact_id
├─ display_name
├─ kind
├─ producer_case_id
├─ producer_job_id
├─ created_by
├─ created_at
├─ content_hash?
├─ size?
├─ provenance_ref?
├─ storage_ref
└─ visibility
```

Физический local path — деталь host adapter.

## 63. Это особенно важно для Android

Android не сможет открыть:

```text
C:\Users\...\Strategy Box Data\output\x.xlsx
```

как локальный путь.

Но сможет получить:

```text
artifact_id = a123
name = report.xlsx
preview available
open/download action allowed
```

## 64. Lineage должен стать видимым

Из любого артефакта полезно уметь ответить:

- кто создал;
- каким case;
- какой operation;
- из каких sources/inputs;
- когда;
- был ли run успешным/с предупреждениями;
- какой log относится к нему.

Это одновременно collaboration, auditability и UX.

---

# XVI. Logs: общий индекс, ограниченная техническая детализация

## 65. Лог не должен автоматически быть общедоступным текстом

Многопользовательский timeline должен показывать безопасное описание:

```text
«Этап загрузки завершился ошибкой авторизации.»
```

а полный лог может содержать:

- пути;
- URL;
- environment details;
- stack trace;
- потенциально чувствительные значения.

Поэтому access разделяется:

```text
logs.view.summary
logs.view.technical
```

## 66. Shared event хранит `log_ref`, не traceback

Timeline/event:

```text
status = error
problem_ref = ...
log_ref = ...
safe_summary = ...
```

Технический лог остаётся физическим evidence и открывается только при разрешении.

---

# XVII. Ошибки и уведомления между пользователями

## 67. Пользователям действительно полезно видеть проблемы друг друга — но только релевантные

Идея «у одного пользователя ошибка — предупредить остальных на узле» правильная, если ввести scope.

Нельзя делать broadcast любой ошибки всем.

## 68. Рекомендуемая классификация audience scope

### Personal

Примеры:

- неверный пользовательский параметр;
- локальная форма не прошла validation;
- user-specific authentication requirement.

Показывается автору; оператору — только при необходимости.

### Case-scoped

Пример: конкретный общий расчёт завершился ошибкой.

Видно в shared case timeline. Push-уведомление получают автор, watchers/assignee и заинтересованные участники.

### Resource-scoped

Пример: dataset заблокирован другим job или source cache повреждён.

Уведомляются пользователи, действия которых реально затронуты.

### Node-scoped

Примеры:

- Data root недоступен;
- runtime degraded;
- критический platform problem;
- общая зависимость узла не готова.

Это релевантно всем активным участникам узла.

### Security-sensitive

Показывается только минимальная безопасная формулировка аудитории с соответствующей capability.

## 69. Одна проблема — одно occurrence

Если Data root узла упал и подключено пять пользователей, система не должна регистрировать пять логически одинаковых platform incidents.

Цель:

```text
1 canonical ProblemOccurrence
→ ProblemRef
→ node health
→ несколько audience projections/notifications
```

Это уменьшает шум и облегчает диагностику.

## 70. Core errors должны оставаться structured

`stratbox` уже движется к envelope:

```text
status
warnings
failures
metrics
artifacts
diagnostics
provenance
```

Правильный принцип: core генерирует structured facts/diagnostics, а application layer решает:

- превратить ли это в case warning;
- создать ли app event;
- создать ли node notification;
- кому это показать.

Core не должен знать, сколько пользователей подключено.

---

# XVIII. Notification model

## 71. Timeline и notification — разные вещи

Не каждое событие timeline должно всплывать toast-ом.

Например:

```text
step_started
```

видно при открытом case, но не требует notification.

А:

```text
assignment assigned to me
approval required
my case failed
node became unavailable
```

должно привлекать внимание.

## 72. Рекомендуемая сущность Notification

```text
notification_id
user_id
kind
severity
source_type
source_id
created_at
seen_at?
actioned_at?
safe_title
safe_body
```

Она может быть projection, а не отдельной domain truth.

## 73. Deduplication

Для node-wide problem всем пользователям создаётся собственное receipt/notification представление, но source occurrence один.

Повторяющийся warning не должен спамить при каждом heartbeat/poll.

---

# XIX. Права и capability model

## 74. UI visibility и authorization — разные уровни

Скрыть кнопку в Qt недостаточно.

Node-side command handler обязан повторно проверить capability.

## 75. Практичный initial capability vocabulary

Например:

```text
presence.view
cases.view
scenario.run
job.cancel.own
job.cancel.any
background.view
background.manage
assignment.create
assignment.complete.own
assignment.manage
artifact.open
artifact.publish
logs.view.summary
logs.view.technical
workspace.read
workspace.mutate
dangerous.execute
approval.grant
node.health.view
```

Coarse roles могут быть:

```text
viewer
analyst
operator
admin
```

Но решение о действии лучше принимать по capability, а role использовать как удобную группу grants.

## 76. OperationSpec должен объявлять security envelope

Целевая metadata:

```text
required_capabilities = (...)
dangerous = true/false
requires_confirmation = ...
visibility_policy = ...
```

Тогда Windows, Android и AI получают одинаковую доступность действий из одного descriptor.

---

# XX. Параметры и конфиденциальность shared case

## 77. Нельзя автоматически показывать всем raw params

Сейчас case сохраняет `params`, а scenario chat умеет строить их summary.

В multi-user мире параметры могут содержать:

- локальные пути;
- user-specific выборы;
- идентификаторы;
- технические настройки;
- в будущем — чувствительные значения.

## 78. Нужна parameter visibility/sensitivity metadata

Например:

```text
public
masked
private_to_actor
secret
technical
```

Case timeline получает только заранее безопасную projection.

Execution layer при этом может иметь полный validated request в закрытом execution record.

Это особенно важно для AI и remote users.

---

# XXI. Reconnect, stale clients и consistency

## 79. Клиент должен быть disposable

Закрытие Windows GUI не должно уничтожать case или job, если работа реально исполняется node-side.

Целевая модель:

```text
GUI process died
→ session becomes stale/ended
→ node job continues
→ другой client видит выполнение
→ пользователь переподключается
→ snapshot восстанавливает case
```

## 80. Reconnect через cursor

Клиент хранит только локальный:

```text
last_applied_seq
```

После reconnect:

```text
server last_seq = 1500
client last_seq = 1470
→ fetch 1471..1500
```

Если history window уже очищено или найден gap — refetch snapshot.

## 81. Optimistic updates требуют revision

Для assignment/background settings можно использовать:

```text
object.revision
command.expected_revision
```

Если два пользователя одновременно меняют одно поручение, второй получает conflict и свежую версию вместо silent last-write-wins.

## 82. Offline mode должен быть честным

Если client потерял связь с node runtime:

- последние данные можно оставить на экране со штампом «состояние устарело»;
- submit/cancel/shared mutations блокируются;
- локальные UI preferences/drafts продолжают работать;
- нельзя создавать локальную «теневую» timeline с последующей магической merge-попыткой.

Для аналитического инструмента явная stale state безопаснее сложного offline-first collaboration.

---

# XXII. Recovery и сбои execution

## 83. Worker crash не равен обычному `failed`

Если worker завершился неожиданно, система может не знать, успел ли он записать часть файлов.

Нужно различать:

```text
failed          — операция доказанно завершилась ошибкой
cancelled       — cooperative cancellation подтверждён
interrupted     — worker исчез
outcome_unknown — могла пройти необратимая граница, финал не доказан
```

## 84. Job lease/custody

Node Job Manager должен знать, какой worker владеет running job.

При исчезновении worker:

1. lease истекает/worker death обнаруживается;
2. job перестаёт считаться running;
3. recovery policy определяет retry/resume/manual review;
4. case получает понятное событие.

Автоматический retry разрешён только для операций, где это безопасно и явно объявлено.

---

# XXIII. Android и remote participation

## 85. Multi-user architecture одновременно решает Android

Если Windows UI остаётся владельцем cases и history, Android придётся копировать слишком много локальной логики.

Если node runtime владеет shared truth, Android становится обычным клиентом:

```text
snapshot
+ events
+ commands
+ artifact actions
```

## 86. На Android не требуется полный desktop

Наиболее ценные mobile surfaces:

- кто online;
- running/queued cases;
- node health;
- ошибки;
- поручения;
- approvals;
- background status;
- артефакты/preview;
- lightweight launch разрешённых сценариев;
- notifications.

Тяжёлая работа остаётся на host node.

## 87. Shared presentation semantics нужно расширять

Сейчас `presentation/common` сильнее всего развит для scenario chat.

Дальше туда логично вынести toolkit-neutral projections:

```text
ParticipantViewModel
CaseInspectorViewModel
JobQueueViewModel
AssignmentViewModel
ArtifactViewModel
NodeStatusViewModel
NotificationViewModel
OperationFormViewModel
```

Qt и Android рендерят один смысл разными компонентами.

---

# XXIV. AI как ещё один actor, а не особая всесильная система

## 88. AI уже присутствует в actor vocabulary

Это хороший задел.

Целевая AI participation:

```text
AI session/subject
→ получает разрешённый scenario catalog
→ submit command
→ обычный Case + Job
→ обычные Events
→ обычные Artifacts
→ полный audit actor identity
```

AI не должен:

- напрямую писать shared SQLite;
- напрямую обходить workspace вне разрешённого operation;
- миновать capability checks;
- получать секреты из shared timeline.

Таким образом multi-user human architecture естественно становится multi-actor architecture.

---

# XXV. Предлагаемая ownership matrix

| Сущность / истина | Владелец | Что видит Strategy Box UI |
|---|---|---|
| Node identity/topology | AppDock Node | безопасная projection |
| User/subject identity | AppDock Identity/runtime | user id/display identity |
| Session lifecycle | AppDock Sessions | список/aggregate presence |
| Active sessions | AppDock Sessions | presence projection |
| Roles/capabilities | AppDock Access / policy layer | разрешённые actions |
| Node health/platform problem | AppDock Node + Observability | safe status/problem ref |
| Scenario definition | Strategy Box application descriptors | каталог сценариев |
| Domain calculation | `stratbox` core | typed result/diagnostics |
| Case | Strategy Box node runtime | shared card |
| Job/queue | Strategy Box execution/application runtime, поверх platform execution boundary | status/queue position/control |
| App activity event | Strategy Box node runtime | timeline |
| Background trigger | Strategy Box node runtime | status/settings |
| Assignment/approval | Strategy Box node runtime | shared task |
| Artifact metadata | Strategy Box node runtime | artifact ref/actions |
| Physical artifact bytes | workspace/FileStore/host storage | через artifact action |
| Technical logs | host/node storage | permissioned log ref |
| Read/unread | per-user Strategy Box state | personal filter |
| Window/filter/form drafts | client-local UI preferences | только текущий клиент |

Главный принцип:

> **ни один слой не должен дублировать чужую authority только ради удобства UI.**

---

# XXVI. Возможная контрактная форма

## 89. Collaboration snapshot

Примерно:

```text
NodeCollaborationSnapshot
├─ node_id
├─ generated_at
├─ last_seq
├─ current_actor
├─ participants[]
├─ cases[]
├─ jobs[]
├─ background_processes[]
├─ assignments[]
├─ recent_artifacts[]
├─ active_problem_refs[]
└─ my_read_state
```

Важно: это read model, а не новый owner всей системы.

## 90. Activity event

```text
NodeActivityEvent
├─ event_id
├─ node_seq
├─ created_at
├─ kind
├─ severity
├─ actor_ref
├─ subject_ref
├─ case_id?
├─ job_id?
├─ assignment_id?
├─ artifact_refs[]
├─ problem_ref?
└─ safe_payload
```

## 91. Command envelope

```text
NodeCommand
├─ command_id
├─ actor/session context
├─ kind
├─ target_ref
├─ expected_revision?
└─ payload
```

Ответ:

```text
CommandResult
├─ accepted/rejected
├─ authoritative_ref
├─ revision
├─ emitted_seq
├─ safe_problem?
└─ retryability
```

## 92. Job model

```text
NodeJob
├─ job_id
├─ case_id
├─ scenario_id
├─ submitted_by
├─ submitted_session_id
├─ status
├─ queue_position?
├─ execution_backend
├─ resource_claims[]
├─ worker_ref?
├─ cancellation_state
├─ created/started/finished
└─ terminal_outcome
```

---

# XXVII. UX целевой версии

## 93. Верхняя панель

Полезно показывать компактно:

```text
[Node: готов]  [● ● ● +2  5 online]  [2 выполняются · 1 в очереди]
```

По клику:

- health узла;
- список участников;
- job queue.

## 94. Участники

Каждая строка:

```text
● Иван Петров
  online · 2 сессии · выполняет 1 сценарий
```

При раскрытии:

```text
Windows desktop — OFFICE-PC — online
Android companion — phone — online
```

Точные host names и технические details можно ограничивать capability/policy.

## 95. Scenario Chat

Карточка case:

```text
Иван Петров · 14:31
Обновление данных Банка России
Выполняется · Этап 2/4

[Смотреть] [Подписаться] [Остановить — если разрешено]
```

Если ожидание ресурса:

```text
В очереди
Ожидает освобождения dataset escrow_history.
```

## 96. Повторный запуск уже активной операции

Если пользователь пытается запустить конфликтующий update, UX лучше делает так:

```text
Такое обновление уже выполняет Мария.

[Смотреть текущий запуск]
[Поставить после него]
[Отмена]
```

а не просто выдаёт «busy».

## 97. Background strip

Показывает node-wide процессы:

```text
Мониторинг публикаций ЦБ    работает · след. проверка ...
Обновление cache            ошибка · 16:10
```

Одно и то же состояние видят все участники.

## 98. Right Inspector

Tabs можно развить до:

```text
Кейс
Ход выполнения
Артефакты
Поручения
Логи
Активность
```

Полный технический лог показывается только при capability.

## 99. Notification examples

Хорошие:

```text
«Ваш сценарий завершён с замечаниями.»
«Вам назначена проверка результата.»
«Узел потерял доступ к Data root; новые сценарии временно недоступны.»
«Операция, которую вы ожидали, завершилась — ваш case запущен.»
```

Плохие:

```text
«step 3 started»
«heartbeat updated»
«participant X changed active_view»
```

Последние относятся к внутренней телеметрии, а не к вниманию пользователя.

---

# XXVIII. Что хранить локально у пользователя

## 100. Personal preferences остаются client-local

Например:

- размер окна;
- выбранный режим;
- открытый inspector;
- last selected tab;
- локальные form drafts;
- плотность интерфейса;
- muted notification settings.

## 101. Shared state нельзя складывать в personal preferences

Например, нельзя там хранить authoritative:

- assignment completed;
- background enabled;
- case status;
- shared read state другого пользователя;
- job queue.

Это типичная граница, которую стоит закрепить отдельными tests.

---

# XXIX. Что делать с текущими JSON history files

## 102. Рекомендация: чистый cut-over

Так как обратная совместимость не требуется, не стоит строить постоянный dual-write:

```text
SQLite + старые JSON одновременно
```

Это создаст две истины.

Лучше:

1. ввести новый shared store;
2. переключить application stores на него;
3. удалить runtime dependency от старых JSON history;
4. при необходимости оставить отдельный одноразовый development importer, который не является production compatibility layer;
5. убрать старые files после clean cut-over.

---

# XXX. Основные риски

## 103. Слишком рано сделать отдельный collaboration server

Можно случайно построить мини-Slack вместо аналитического инструмента.

Контрмера: начинать с cases/jobs/presence/assignments, а comments добавлять только когда появится явный use case.

## 104. Сделать SQLite shared через сетевой Data root

Это архитектурно опасная ловушка.

Контрмера: metadata DB только node-local; remote clients через runtime boundary.

## 105. Оставить execution в GUI

Тогда закрытие GUI будет убивать jobs, а Android никогда не станет полноценным companion.

Контрмера: вынести job ownership из Qt coordinator в toolkit-neutral node/application runtime.

## 106. Broadcast всех ошибок всем

Это создаст шум и раскроет лишние details.

Контрмера: error scope + audience-safe projection + capabilities.

## 107. Глобально запретить параллельность

Безопасно, но плохо масштабируется.

Контрмера: resource claims и declarative concurrency policy.

## 108. Пытаться синхронизировать UI state

Не нужно делиться тем, какая вкладка открыта у коллеги.

Контрмера: разделить operational shared state и personal client state.

## 109. Хранить `unread` внутри общего event

Ломает per-user UX.

Контрмера: read cursor/receipt.

## 110. Публиковать raw paths и stack traces в shared timeline

Плохо для remote/mobile/security.

Контрмера: refs + safe projection.

---

# XXXI. Что точно не стоит делать

1. Не превращать пять JSON history-файлов в «сетевую базу данных» с самодельными lock-файлами.
2. Не размещать SQLite/WAL на SMB/Data root.
3. Не запускать background scheduler отдельно в каждом GUI-процессе.
4. Не считать текущий `ScenarioCoordinator.is_busy` node-wide lock.
5. Не хранить online/offline как единственную authority вместо session + heartbeat.
6. Не хранить `unread` на общем Case/Event.
7. Не давать UI прямой authority над общим состоянием.
8. Не давать Android прямой доступ к node filesystem или DB.
9. Не давать AI обходить operation/scenario boundary.
10. Не делать raw traceback частью shared event.
11. Не дублировать AppDock identity/session/access truth внутри Strategy Box.
12. Не вводить отдельную execution stack для background, manual и remote runs.
13. Не делать один глобальный lock на весь узел, когда достаточно resource-level coordination.
14. Не добавлять полноценный free-form team chat до появления реальной потребности.

---

# XXXII. Поэтапный roadmap

## Этап 0 — зафиксировать архитектурные границы

Перед новым кодом оформить короткие contracts/ADR:

- AppDock vs Strategy Box ownership;
- Participant vs Session;
- Case vs Job;
- shared vs personal state;
- artifact/log refs;
- no Qt in shared orchestration.

## Этап 1 — platform-neutral shared contracts

Добавить модели:

- `ActorRef` / `SessionRef`;
- `NodeActivityEvent`;
- `NodeJob`;
- `ResourceClaim`;
- `UserReadCursor`;
- shared `Assignment` revision;
- safe artifact/log refs.

Перестать считать `case.unread/event.unread` общей истиной.

## Этап 2 — node-scoped Strategy Box persistence

Ввести SQLite-backed repository/transaction boundary в AppDock-provided node-local storage.

Перевести туда:

- cases;
- events;
- jobs;
- artifacts metadata;
- logs metadata;
- assignments;
- background state;
- read cursors.

Сделать clean cut-over с JSON history.

## Этап 3 — настоящий presence provider

Со стороны AppDock предоставить публичную безопасную read boundary активных сессий узла.

Strategy Box:

- агрегирует sessions по user;
- вычисляет online/stale/offline;
- показывает multiple sessions;
- обновляет participant panel;
- перестаёт выводить presence из истории cases.

## Этап 4 — Node Job Manager

Вынести orchestration из Qt:

```text
ScenarioCoordinatorProtocol
NodeJobManager
ExecutionBackend
LocalExecutionBackend
```

Добавить:

- queue;
- cancellation;
- resource claims;
- idempotency;
- recovery/worker custody.

Qt остаётся signal/event adapter.

## Этап 5 — background на общем executor

Заменить in-memory illusion на:

```text
Trigger → submit shared job
```

Background state становится node-wide и восстанавливается после restart.

## Этап 6 — notifications + problem routing

Добавить:

- personal/case/resource/node scopes;
- notification receipts;
- AppDock ProblemRef projection для node/platform problems;
- deduplication;
- permissioned technical details.

## Этап 7 — shared assignments и approvals

Добавить:

- remote/shared assignments;
- notifications;
- due date при необходимости;
- approvals;
- optional comments/mentions только вокруг case/artifact/assignment.

## Этап 8 — transport abstraction / remote client

Стабилизировать:

```text
snapshot
subscription/poll events
commands
artifact actions
```

После этого Android может использовать тот же application semantics.

## Этап 9 — AI actor

Подключать AI только после того, как:

- capabilities;
- jobs;
- safe params;
- audit actors;
- approvals;
- cancellation

уже работают для людей.

---

# XXXIII. Acceptance criteria

## 111. Два клиента видят одну истину

Если пользователь A запускает scenario, пользователь B без ручной синхронизации получает тот же case и его актуальный status.

## 112. Unread персонален

A читает event. У B он остаётся непрочитанным.

## 113. Same-user multi-session агрегируется

Один user на Windows + Android отображается как один participant с двумя sessions.

## 114. Конфликтующие jobs не повреждают данные

Два пользователя запускают write в один resource. Один выполняется, второй становится queued/waiting. Ни один artifact не перетирается частично.

## 115. Независимые jobs могут выполняться параллельно

Read-only или независимые resource claims не блокируют весь узел.

## 116. Duplicate submit не запускает работу дважды

Повтор одного `command_id` возвращает существующий case/job.

## 117. Background выполняется один раз на узел

Два открытых desktop clients не создают два одинаковых background run.

## 118. Client crash не теряет shared job

Закрытие/авария GUI не удаляет node-owned execution.

## 119. Worker crash виден как отдельный lifecycle outcome

Система не выдаёт ложный success/cancelled.

## 120. Reconnect детерминированно догоняет timeline

Client с последним `node_seq` применяет пропущенные события или получает свежий snapshot.

## 121. Corrupt shared store не превращается в «пустую историю»

Startup/read возвращает явный degraded/problem state.

## 122. Permission enforcement server-side

Скрытая кнопка не является единственной защитой. Неразрешённая команда отклоняется authoritative layer.

## 123. Ошибка правильной аудитории

Personal validation error видит только actor; node-wide problem видят все затронутые участники; technical traceback ограничен capability.

## 124. Artifact lineage стабилен

Артефакт однозначно связан с producer case/job/operation и доступен нескольким clients через identity/ref.

## 125. Android/common contracts не импортируют Qt

Shared application/presentation contracts должны импортироваться и тестироваться без PySide6.

---

# XXXIV. Матрица зрелости

| Область | Сейчас | Целевая форма | Приоритет |
|---|---|---|---|
| Multi-user UI semantics | сильный каркас | общий live state | P0/P1 |
| Case authoring | реализовано локально | shared case owner | P0 |
| Events | реализовано локально | append-only node sequence | P0 |
| Presence | локальная имитация | AppDock session-derived | P0/P1 |
| AppDock active sessions | инфраструктурная база есть | публичный product provider | P1 |
| Shared persistence | отсутствует | node-local transactional store | P0 |
| Job queue | отсутствует | node-wide Job Manager | P0/P1 |
| Concurrency control | process-local busy | resource claims | P1 |
| Cancellation | status есть | cooperative node-wide | P1 |
| Background | UI/state scaffold | trigger → common job engine | P1 |
| Assignments | local scaffold | shared + notifications | P1/P2 |
| Read/unread | общий bool | per-user cursor | P0 |
| Artifacts | хорошая local metadata | shared refs + lineage | P1 |
| Logs | local path refs | safe summary + permissioned log refs | P1 |
| Error fanout | отсутствует | scoped audience routing | P1 |
| Roles/capabilities | platform vocabulary минимальна | enforced capability model | P1/P2 |
| Remote execution | задел | ExecutionBackend/AppDock transport | P2 |
| Android | потенциально | shared client contracts | P2 |
| AI actor | semantic scaffold | permissioned standard actor | P3 |

---

# XXXV. Предлагаемая целевая структура shared частей `stratbox-windows`

Это не требование немедленно переименовать весь repository tree, а логическая форма ownership:

```text
stratbox_windows/
│
├─ application/
│  ├─ collaboration/
│  │  ├─ contracts.py
│  │  ├─ events.py
│  │  ├─ read_state.py
│  │  └─ commands.py
│  ├─ jobs/
│  │  ├─ models.py
│  │  ├─ policies.py
│  │  └─ runtime.py
│  ├─ cases/
│  ├─ assignments/
│  ├─ artifacts/
│  ├─ background/
│  ├─ presence/
│  └─ scenarios/
│
├─ runtime/
│  ├─ node_runtime.py
│  ├─ collaboration_runtime.py
│  └─ composition.py        # без Qt
│
├─ adapters/
│  ├─ appdock/
│  │  ├─ sessions.py
│  │  ├─ access.py
│  │  └─ problems.py
│  ├─ persistence/
│  │  └─ sqlite_shared_state.py
│  ├─ execution/
│  │  └─ local_backend.py
│  └─ desktop_host/
│
├─ presentation/
│  ├─ common/
│  │  ├─ scenario_chat/
│  │  ├─ participants/
│  │  ├─ jobs/
│  │  ├─ assignments/
│  │  ├─ artifacts/
│  │  └─ notifications/
│  └─ qt_desktop/
│
└─ resources/
```

Ключевой критерий: весь `application + runtime + presentation/common` должен быть импортируем без Qt.

---

# XXXVI. Сквозной пользовательский сценарий целевой системы

## 126. Два пользователя на одном узле

Представим пользователей A и B.

### Шаг 1 — подключение

AppDock создаёт две sessions одного node.

Strategy Box получает shared collaboration snapshot:

```text
participants: A online, B online
jobs: none
cases: recent 12
node health: ready
```

Оба UI показывают `2 online`.

### Шаг 2 — A запускает обновление

A нажимает «Обновление данных ЦБ».

Клиент отправляет command:

```text
command_id = x
scenario_id = ...
actor = A/session-A
```

Node runtime:

1. проверяет capability;
2. валидирует params;
3. создаёт Case;
4. создаёт Job;
5. резервирует ресурсы/или ставит в queue;
6. выдаёт события.

Оба клиента мгновенно получают один и тот же case.

### Шаг 3 — B наблюдает

У B карточка incoming:

```text
A запустил «Обновление данных ЦБ»
Выполняется · загрузка источников
```

B ничего не «копирует» к себе. Он видит projection общей истины.

### Шаг 4 — B запускает конфликтующую операцию

Runtime определяет пересечение resource claim.

B получает:

```text
Case создан
Status: queued
Reason: ожидает dataset lock
```

UI предлагает смотреть активный run или оставить второй в очереди.

### Шаг 5 — первый run создаёт артефакт

Artifact metadata попадает в shared store.

Оба UI получают `artifact_created`.

A может открыть файл локально; B — тоже, если есть доступ. Android получает artifact action/preview, а не raw Windows path.

### Шаг 6 — ошибка узла

Data root становится недоступен.

AppDock фиксирует node-wide problem и safe ProblemRef.

Strategy Box создаёт/получает node-scoped notification projection.

A и B видят одно и то же узловое предупреждение, но технические подробности доступны только оператору.

### Шаг 7 — Android

A уходит от ПК, открывает Android companion.

Новая session агрегируется к тому же participant A. Android получает snapshot и видит ongoing case без специальной миграции desktop state.

Это и есть цель правильной multi-user architecture.

---

# XXXVII. Главные решения, которые стоит зафиксировать

1. **Collaboration scope = Node.**
2. **Participant ≠ Session.**
3. **Case ≠ Job.**
4. **Shared operational state принадлежит node runtime, а не UI process.**
5. **AppDock владеет node/session/identity/access/platform-problem truth.**
6. **Strategy Box владеет app-level cases/jobs/events/assignments/artifacts metadata.**
7. **`stratbox` core остаётся user-agnostic.**
8. **Scenario Chat становится общей operational timeline, а не универсальным мессенджером.**
9. **Unread/read state всегда per-user.**
10. **Background/manual/AI/remote запускаются через один Job Manager.**
11. **Concurrency управляется resource claims, а не одним global busy flag.**
12. **Shared metadata store — node-local transactional storage; не Data root.**
13. **Remote/mobile не открывают DB/files напрямую; только contracts/actions.**
14. **Raw paths, params, logs и tracebacks не публикуются в shared timeline без policy.**
15. **Node-wide problems deduplicate и fan-out через audience-safe projections.**
16. **Qt остаётся presentation adapter, shared runtime не зависит от Qt.**
17. **Обратную совместимость со старой JSON-history архитектурой не строить.**

---

# XXXVIII. Итог

Текущий Strategy Box уже содержит почти весь **язык** будущей многопользовательской системы: участники, авторы, cases, incoming/outgoing timeline, поручения, фоновые actors, logs, artifacts, node/session identity и runtime heartbeat. AppDock уже содержит ещё один критический фундамент — несколько активных session projections одного узла и отдельные domains identity/access/sessions/observability.

Поэтому следующий цикл не должен начинаться с очередной UI-функции. Главный качественный скачок даст **перенос общей операционной истины из отдельных GUI-процессов в node-scoped runtime**.

После этого существующие части начинают складываться почти автоматически:

```text
AppDock sessions
    → настоящее presence

shared node state
    → общий scenario chat
    → общие assignments
    → общие artifacts
    → per-user unread

Node Job Manager
    → реальный background
    → безопасная конкуренция
    → cancellation
    → remote execution

safe event/problem projection
    → понятные предупреждения другим пользователям

transport-neutral contracts
    → Android
    → AI actors
```

Самый важный продуктовый результат такой архитектуры — пользователь перестаёт воспринимать Strategy Box как «моё отдельное окно, в котором что-то запускается». Он начинает видеть **живой узел**, где работают люди и фоновые процессы, где понятно, кто что сделал, что происходит сейчас, что ждёт очереди, где возникла проблема и какой результат уже получен.

Именно для Strategy Box эта форма многопользовательской работы выглядит оптимальной: минимум лишней социальной механики, максимум прозрачности, координации и ощущения общей рабочей среды.

---

# XXXIX. Проверенные источники

## Внутренние материалы проекта

- `stratbox-windows_current_state_full_research_2026-10-06.md` — фактическая архитектура desktop surface, cases/events/artifacts/logs, presence, assignments, background, AppDock boundary и Android-потенциал.
- `stratbox_base_study_current_state_2026-10-06.md` — граница core, operation/result architecture, structured diagnostics/provenance.
- `AppDock - Базовое описание.docx` — продуктовая модель узла, host/remote work, roles/permissions, controlled participation.

## Актуальный код

- `ForestTiger-GH/stratbox-windows`, `main`, повторно проверен 2026-10-07.
- `ForestTiger-GH/AppDock`, актуальный `main` — Node, Sessions, Access, Execution, Observability contracts и shared active-session projection.

## Внешняя техническая сверка

- SQLite Isolation: https://sqlite.org/isolation.html
- SQLite Write-Ahead Logging: https://sqlite.org/wal.html

SQLite использован здесь только как конкретная рекомендация node-local transactional metadata storage. Выбор реализации можно заменить другим embedded/server store без изменения основной модели ownership, events, jobs и client contracts.
