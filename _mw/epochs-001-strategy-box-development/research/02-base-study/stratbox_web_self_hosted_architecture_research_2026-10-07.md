# Strategy Box: web/self-hosted режим, server host и браузерная поверхность

**Research branch:** вторая ветка исследований Strategy Box  
**Дата:** 2026-10-07  
**Область:** `stratbox` + будущий `stratbox-host` + `stratbox-web` + `stratbox-windows` + граница AppDock  
**Статус:** Research Result — целевая архитектура и требования; документ сам по себе не меняет код, публичные контракты или репозитории.

---

## 0. Краткий вывод

Strategy Box в web-режиме лучше проектировать **не как перенос Windows-приложения в браузер**, а как разделение продукта на постоянный server-side host и несколько клиентских поверхностей.

Целевая модель:

```text
                        Internet / LAN / VPN
                               │
                               ▼
                     HTTPS reverse proxy
                               │
                         box.example.com
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
        stratbox-web                  Strategy Box API
        browser client                      │
                                            ▼
                                     stratbox-host
                             ┌───────────────┼────────────────┐
                             │               │                │
                             ▼               ▼                ▼
                        app state        job manager      file/artifact
                        + users          + workers        services
                             │               │                │
                             └───────────────┼────────────────┘
                                             ▼
                                          stratbox
                                       business core
```

Главные выводы исследования:

1. **Новый самостоятельный host действительно нужен.** Условия, при которых прежнее исследование допускало не выносить node runtime из `stratbox-windows`, теперь возникли: runtime должен жить без открытого desktop-клиента, принимать браузерные/мобильные подключения, выполнять фоновые jobs и хранить общую многопользовательскую истину. Это уже отдельный lifecycle.

2. Оптимальное имя — **`stratbox-host`**, а не `stratbox-linux-host`. Linux должен быть главным deployment target, но не архитектурной идентичностью. Тот же host в будущем сможет работать на Windows Server, мини-ПК, VM или контейнере.

3. **`stratbox-web` логично сделать отдельной browser surface**, аналогичной по роли `stratbox-windows` и будущему `stratbox-android`. Она не должна владеть jobs, files, users или business logic; она отображает и изменяет состояние через API host-а.

4. `stratbox` остаётся **чистым предметным core**. Web/auth/users/sessions/HTTP/database/presence не должны попадать в него.

5. `stratbox-host` становится **canonical application runtime Strategy Box**: scenario/cascade planning, jobs, cases, events, shared state, user-facing artifacts, collaboration state, permissions, persistence и execution backends.

6. `stratbox-windows` со временем должен стать **клиентом host contract**, а не владельцем канонической истории. В локальной установке он может подключаться к локальному host на том же узле; в remote-режиме — к удалённому host. Это резко уменьшает архитектурную разницу между Windows, Web и Android.

7. Для браузера визуальная и смысловая модель может быть практически той же, что в Windows, однако реализация UI будет другой. Qt Widgets не является браузерной технологией. Общими должны быть **семантика экранов, operation/scenario descriptors, API contracts и state models**, а не код виджетов.

8. Для файлового пространства целевой вариант — **не выбирать между полностью общей и полностью персональной комнатой**, а ввести несколько логических scope:

```text
node_shared     — общая рабочая комната узла
personal        — личная комната пользователя
run             — изолированная область конкретного Case/Job
system          — внутреннее пространство runtime, пользователю напрямую не показывается
```

9. В browser/web deployment **физические пути сервера не должны быть пользовательским API**. Клиент работает с `WorkspaceRef`, `ArtifactRef`, `FileRef`, `case_id`, `artifact_id`. Host сам разрешает их в local FileStore/path.

10. Для web-host режима нужен **настоящий shared transactional store**. Пять JSON-файлов текущего desktop runtime развивать в сетевую многопользовательскую БД не стоит.

11. Для одного локального узла SQLite может оставаться хорошим embedded store при условии, что файл БД находится на локальном диске host-а и к нему обращается только server runtime. Для web-сервера с несколькими server workers, высокой конкурентной записью или перспективой горизонтального масштабирования PostgreSQL является более естественным production store. Архитектура должна скрывать выбор за `StateStore`/repository boundary.

12. В первой зрелой web-версии **REST/HTTP + Server-Sent Events (SSE)** достаточно почти для всего. Команды (`run`, `cancel`, `assign`, `approve`) идут обычными HTTP-запросами; status/events/progress — по SSE. WebSocket стоит добавлять только там, где реально появляется двусторонний low-latency use case.

13. Предпочтительная browser-auth архитектура — **Backend-for-Frontend session model**: браузер не хранит access/refresh tokens; host выполняет OIDC/OAuth flow и выдаёт защищённую `HttpOnly + Secure + SameSite` session cookie. Production deployments должны уметь подключать внешний OIDC IdP. Локальные аккаунты нужны только для полностью автономных/air-gapped поставок и несут отдельный security surface.

14. Внешнее опубликование host-а должно быть **fail-closed**. Если процесс слушает не loopback-интерфейс, но authentication/TLS-facing deployment не настроены, запуск должен завершаться ошибкой, а не создавать открытый сервис.

15. Нельзя отдавать workspace как обычную static directory. Files/artifacts скачиваются через авторизованный handler, upload проверяется, а webroot и рабочие данные физически разделены.

16. Браузер закрывается — **job продолжает работу**. Это один из главных критериев правильного разделения host/client.

17. AppDock естественно остаётся внешней платформой node lifecycle: установка, запуск host service, secrets, health, remote attachment, upgrade/recovery. Strategy Box Host владеет application-level состоянием и authorization внутри продукта.

Итоговая формула:

> **`stratbox` считает; `stratbox-host` живёт и исполняет; `stratbox-web` показывает в браузере; `stratbox-windows` показывает на Windows; AppDock разворачивает, связывает и контролирует узел.**

---

# I. Исходная архитектурная позиция

## 1. Что уже есть и почему web-режим не начинается с нуля

Текущий `stratbox` уже отделён от UI и содержит предметную business logic, нейтральные infrastructure contracts, FileStore/IO, источники, модели, вычисления и формирование артефактов.

Текущий `stratbox-windows` уже содержит важную application-семантику, которая пригодна для web:

- operation/scenario descriptors;
- cases;
- events;
- logs;
- artifacts;
- assignments;
- presence models;
- background-process vocabulary;
- workspace semantics;
- runtime state;
- AppDock identity/node/session context;
- scenario-chat projection.

Прежнее исследование многопользовательской работы уже пришло к принципу:

> узел — единая рабочая среда; пользовательские клиенты — проекции одного общего операционного состояния узла.

Web-режим превращает этот принцип из возможного дальнейшего развития в прямое системное требование.

## 2. Проверка актуальности исходного среза

Базовый полный research `stratbox` был сделан на commit:

```text
e968853572676d8e5d963607d1f0cb50ff8f20b7
```

На момент данного исследования текущий `main` уже находится на:

```text
705b0b80f0948675b461cd5b358dd8b861fa6da2
```

Между ними 20 commits. Проверка compare показывает, что изменения затронули прежде всего `AGENTS.md`, README и Research Corpus второй ветки. В `src/stratbox` и тестах между этими двумя точками изменений нет. Поэтому технический срез core от 2026-10-06 остаётся применимым к текущему коду.

`stratbox-windows/main` по-прежнему находится на:

```text
959e9c4ce1441124af5111c1e025041714e04d3b
```

То есть его полный срез от 2026-10-06 также остаётся технически актуальным.

## 3. Связь с AppDock

Базовая модель AppDock уже прямо предусматривает:

- отдельный host — компьютер, mini-PC или server;
- тяжёлые операции рядом с данными;
- remote connection к рабочей среде;
- published environment;
- роли и permissions;
- browser как вход в опубликованный рабочий мир;
- server/self-hosted products.

Следовательно, web-host Strategy Box не требует менять философию AppDock. Он является конкретным продуктом, который естественно использует уже заложенную node/host/remote модель.

---

# II. Что именно означает «Strategy Box в web-режиме»

## 4. Это не remote desktop

Есть несколько очень разных способов «открыть приложение через браузер»:

```text
A. транслировать Windows GUI по RDP/VNC/WebRTC;
B. запускать Qt через необычный browser runtime;
C. построить настоящий browser client над server API.
```

Для Strategy Box целевым вариантом должен быть **C**.

Remote desktop может оставаться аварийным/административным инструментом, но он не создаёт web-продукт. Он наследует Windows UI, Windows lifecycle, Windows filesystem semantics и фактически даёт пользователю удалённый экран, а не браузерную поверхность.

## 5. Browser client должен быть thin stateful client

Браузер отвечает за:

- navigation;
- rendering;
- forms;
- local non-sensitive preferences;
- отображение live state;
- отправку user commands;
- uploads/downloads;
- reconnect UX.

Browser client **не отвечает** за:

- выполнение `stratbox` операций;
- хранение канонической истории;
- постоянный scheduler;
- фоновые jobs;
- доступ к серверному filesystem;
- хранение secrets;
- проверку authorization;
- recovery запущенных jobs.

## 6. Закрытие вкладки не должно влиять на run

Это обязательный acceptance criterion:

```text
User presses Run
→ host creates Case + Job
→ browser closes
→ Job continues
→ artifact is created
→ user reopens URL
→ case and result are reconstructed from server state
```

Если закрытие вкладки прерывает расчёт, архитектура всё ещё является «GUI-driven execution», а не host runtime.

---

# III. Целевая карта репозиториев

## 7. Рекомендуемая схема

```text
ForestTiger-GH/
│
├─ stratbox
│   └─ business/domain core
│
├─ stratbox-host
│   └─ headless application runtime / API / execution / persistence
│
├─ stratbox-windows
│   └─ Windows desktop client/surface
│
├─ stratbox-web
│   └─ browser client/surface
│
└─ stratbox-android            # future
    └─ Android client/surface
```

## 8. Почему `stratbox-host`, а не `stratbox-linux-host`

Linux, вероятно, станет главным production OS для self-hosted режима, однако platform name здесь мешает архитектуре.

Host является понятием уровня продукта:

```text
process/service
+ application runtime
+ job engine
+ shared state
+ API
```

Он может быть запущен:

- на Linux server;
- на Windows Server;
- на mini-PC;
- в VM;
- в OCI container;
- локально рядом с Windows client.

Название `stratbox-linux-host` искусственно связывает application architecture с одной deployment platform.

## 9. Почему нужен отдельный `stratbox-web`

Web surface имеет собственный lifecycle и собственный technology stack:

- HTML/CSS;
- browser routing;
- responsive layout;
- upload/download UX;
- SSE/WebSocket client;
- browser authentication flow;
- accessibility;
- CSP-compatible asset loading;
- browser-specific caching/service-worker policy.

Это та же категория продукта, что `stratbox-windows`, а не часть host runtime.

## 10. Можно ли сначала держать frontend внутри `stratbox-host`

Технически да: server может отдавать скомпилированные static assets `/web`.

Но source ownership лучше разделить сразу:

```text
stratbox-web source
     ↓ build
static bundle
     ↓ release packaging
stratbox-host serves bundle
```

Так сохраняются чистые границы, при этом deployment остаётся одним пакетом/узлом.

---

# IV. Главная архитектурная перестройка относительно текущего Windows runtime

## 11. Сейчас canonical application truth слишком близка к Windows process

Сегодня часть истины хранится в `stratbox-windows`:

- CaseStore;
- EventStore;
- AssignmentStore;
- HistoryPersistenceService;
- background state;
- local presence;
- single-process execution coordination.

Для web/multi-user это должен перестать быть source of truth.

## 12. Целевая ownership модель

```text
stratbox
    owns:
    domain operations
    canonical data/result contracts
    diagnostics/provenance

stratbox-host
    owns:
    scenario/cascade catalog projection
    planning
    cases
    jobs
    events
    shared persistence
    artifacts index
    assignments/approvals
    background triggers
    authorization
    user-facing collaboration state
    execution backends

stratbox-windows / stratbox-web / stratbox-android
    own:
    rendering
    navigation
    local drafts
    device-local non-sensitive preferences
    client reconnect state
```

## 13. Windows должен подключаться к тому же host contract

Целевая схема Windows:

```text
stratbox-windows
        ↓
StrategyBoxClient
        ↓
LocalHostTransport / RemoteHttpTransport
        ↓
stratbox-host
```

В local desktop installation AppDock может стартовать host на loopback или local IPC.

В remote mode Windows получает URL/node endpoint и работает с удалённым узлом.

Это лучше, чем сохранять две независимые execution architectures — Windows-local и Web-server.

---

# V. `stratbox-host` как новый центральный application runtime

## 14. Состав host-а

Минимальная целевая декомпозиция:

```text
stratbox_host/
│
├─ api/
│  ├─ http/
│  ├─ events/
│  ├─ auth/
│  └─ schemas/
│
├─ application/
│  ├─ catalog/
│  ├─ cases/
│  ├─ jobs/
│  ├─ events/
│  ├─ artifacts/
│  ├─ workspaces/
│  ├─ assignments/
│  ├─ approvals/
│  ├─ presence/
│  ├─ notifications/
│  ├─ background/
│  └─ settings/
│
├─ execution/
│  ├─ planner/
│  ├─ scheduler/
│  ├─ workers/
│  ├─ leases/
│  └─ cancellation/
│
├─ persistence/
│  ├─ repositories/
│  ├─ migrations/
│  └─ transactions/
│
├─ storage/
│  ├─ file_refs/
│  ├─ artifact_store/
│  └─ uploads/
│
├─ security/
│  ├─ principals/
│  ├─ authorization/
│  ├─ sessions/
│  └─ audit/
│
├─ adapters/
│  ├─ appdock/
│  ├─ stratbox_core/
│  └─ identity/
│
└─ runtime/
   ├─ config/
   ├─ health/
   └─ lifecycle/
```

Не все каталоги надо создавать в первый commit. Это карта ownership, а не требование создать пустые packages.

## 15. Host не должен превращаться во второй `stratbox`

Host знает **как выполнить** operation и как управлять её lifecycle.

Core знает **что означает** предметная операция и как получить результат.

Запрещённое смешение:

```text
stratbox-host:
    calculate_bank_metric(...)
    parse_cbr_form_802(...)
```

Правильное:

```text
stratbox-host:
    resolve operation descriptor
    validate application permissions
    submit job
    call stratbox operation
    persist result metadata
    publish events/artifacts
```

---

# VI. Web API contract

## 16. API должен быть полноценным product contract

Web frontend, Windows remote client и Android в будущем должны использовать одну семантику.

API — не набор случайных UI endpoints.

Базовая ресурсная модель:

```text
/api/v1/me
/api/v1/node
/api/v1/catalog/scenarios
/api/v1/catalog/cascades
/api/v1/cases
/api/v1/jobs
/api/v1/events
/api/v1/artifacts
/api/v1/workspaces
/api/v1/files
/api/v1/assignments
/api/v1/approvals
/api/v1/background
/api/v1/notifications
/api/v1/settings
/api/v1/health
```

## 17. Mutations должны быть commands

Примеры:

```text
POST /api/v1/scenarios/{id}/runs
POST /api/v1/cascades/{id}/runs
POST /api/v1/jobs/{id}/cancel
POST /api/v1/assignments
POST /api/v1/approvals/{id}/approve
POST /api/v1/artifacts/{id}/publish
```

Server повторно проверяет:

- current principal;
- capability;
- target object;
- current revision/status;
- params;
- resource constraints.

UI disabled button никогда не является security control.

## 18. Idempotency

Каждая mutation, которая может быть безопасно повторена клиентом после сетевого сбоя, должна принимать idempotency key.

```text
Idempotency-Key: <uuid>
```

Пример:

```text
client sends run
network breaks before response
client retries same request
host returns existing Case/Job
```

В противном случае browser/mobile reconnect будет создавать двойные запуски.

## 19. Optimistic concurrency

Для изменяемых shared objects:

```text
assignment revision = 7
background config revision = 12
```

Mutation передаёт expected revision или `If-Match`/ETag.

При конфликте:

```text
409 Conflict
+ current representation
```

Это лучше silent last-write-wins.

## 20. Ошибки API

Пользовательский API не должен отдавать raw traceback.

Целевой envelope:

```json
{
  "error": {
    "code": "workspace.permission_denied",
    "message": "Нет доступа к выбранному рабочему пространству.",
    "problem_id": "p_...",
    "retryable": false
  }
}
```

Технический exception уходит в structured logs и связывается с `problem_id`.

---

# VII. Live updates: SSE сначала, WebSocket по необходимости

## 21. Основной поток Strategy Box по природе server → client

Почти все realtime события:

- case created;
- job queued;
- job started;
- progress changed;
- artifact created;
- warning;
- failure;
- assignment;
- notification;
- presence changed;
- background run.

идут от host к UI.

Поэтому в первой зрелой реализации достаточно:

```text
HTTP commands + SSE event stream
```

## 22. Почему SSE хороший default

SSE:

- встроен в браузер через `EventSource`;
- автоматически поддерживает long-lived server push;
- проще проксируется;
- легко сочетается с append-only event sequence;
- подходит для `after_seq` reconnect model.

Целевая схема:

```text
GET /api/v1/events/stream?after=1034
```

Server выдаёт:

```text
id: 1035
event: case.updated
data: {...}
```

## 23. Snapshot + stream

Клиент не должен строить всё состояние из бесконечного event log.

```text
GET /api/v1/snapshot
→ last_seq = 1034
→ current cases/jobs/presence/assignments/etc.

then

GET /api/v1/events/stream?after=1034
```

При gap — новый snapshot.

## 24. Когда понадобится WebSocket

WebSocket оправдан, если появится реальный двусторонний realtime use case:

- interactive collaborative editing;
- high-frequency terminal-like stream;
- bidirectional control channel;
- very dynamic presence/typing/live collaboration.

Для обычных Strategy Box commands WebSocket усложнит security и observability без большого выигрыша.

---

# VIII. Authentication: кто подключается к URL

## 25. Web-host без authentication допустим только на loopback dev

Если host доступен:

```text
0.0.0.0
LAN address
public domain
VPN network
```

он обязан иметь authentication boundary.

Процесс не должен по умолчанию публиковать открытый Strategy Box.

## 26. Preferred production model — OIDC

Для компании/команды Strategy Box не должен заново изобретать корпоративную identity platform.

Целевой путь:

```text
browser
  ↓
stratbox-host /auth/login
  ↓
OIDC Provider
  ↓
Authorization Code Flow + PKCE
  ↓
callback to host
  ↓
server-side session
  ↓
HttpOnly session cookie
```

Плюсы:

- central MFA;
- account lifecycle;
- SSO;
- group claims;
- отсутствие пароля Strategy Box;
- меньше собственного auth code.

## 27. Browser tokens не должны жить в `localStorage`

Для first-party self-hosted UI лучше использовать Backend-for-Frontend pattern:

```text
OIDC tokens
    live server-side

browser
    sees only opaque session cookie
```

Session cookie:

```text
Secure
HttpOnly
SameSite=Strict (или Lax при обоснованном login/navigation UX)
Path=/
предпочтительно __Host- prefix
```

Это снижает последствия XSS по сравнению с долгоживущим access/refresh token в browser storage.

## 28. Local accounts

Полностью автономная поставка может требовать локальные аккаунты.

Это стоит считать отдельным IdentityProvider implementation, а не основной архитектурой.

Минимальные требования:

- password hashing современным memory-hard KDF;
- MFA support хотя бы для admin/operator;
- rate limiting;
- password reset/bootstrap flow;
- session revocation;
- audit login/security events;
- отсутствие default credentials.

Первый admin должен создаваться одноразовым bootstrap mechanism, после чего bootstrap secret инвалидируется.

## 29. Principal identity

В application layer нужен устойчивый объект:

```text
Principal
├─ principal_id
├─ kind = user|service|ai|system
├─ issuer
├─ external_subject?
├─ display_name
├─ status
└─ capability grants / role refs
```

Email/login/display name не должны становиться primary key.

---

# IX. Authorization: что пользователю разрешено

## 30. Authentication и authorization разделяются

OIDC отвечает:

> кто это?

Strategy Box authorization отвечает:

> что этому principal разрешено внутри данного узла?

## 31. Capability-first model

Ранее предложенный vocabulary хорошо подходит и для web:

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
artifact.read
artifact.write
artifact.publish
logs.view.summary
logs.view.technical
workspace.read
workspace.write.shared
workspace.write.personal
dangerous.execute
approval.grant
node.health.view
settings.manage.node
users.manage
```

Roles — удобные bundles:

```text
viewer
analyst
operator
admin
```

Runtime принимает решение по effective capabilities.

## 32. Deny by default

Любой новый API route/resource/action должен по умолчанию быть закрыт, пока explicit permission не разрешит доступ.

Проверка выполняется на **каждом запросе и каждой mutation**, независимо от того, скрыта ли кнопка в frontend.

## 33. Object-level authorization

Недостаточно проверить только `artifact.read`.

Нужно проверить:

```text
can principal P read artifact A?
```

учитывая:

- workspace scope;
- visibility;
- ownership;
- shared membership;
- case access;
- sensitivity.

Это особенно важно при personal files.

---

# X. Session security и browser boundary

## 34. HTTPS обязателен для всей authenticated session

Authentication page, API, SSE, artifact download — всё должно идти через TLS.

HTTP может существовать только как redirect to HTTPS на внешнем edge.

## 35. CSRF

При cookie session state-changing requests требуют CSRF protection.

Рекомендуется одновременно:

- SameSite cookie;
- anti-CSRF token для mutations;
- проверка `Origin`/`Sec-Fetch-Site` где применимо;
- запрет state mutation через GET.

## 36. Same-origin deployment

Лучший первый вариант:

```text
https://box.example.com/
https://box.example.com/api/v1/...
```

То есть web static assets и API имеют один origin.

Плюсы:

- CORS вообще не нужен;
- проще cookies;
- проще CSP;
- меньше misconfiguration surface.

CORS следует включать только если реально появляется отдельный trusted origin.

## 37. CSP и browser security headers

Web surface должен поставляться с restrictive security headers:

- Content-Security-Policy;
- HSTS;
- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy`;
- `frame-ancestors`/anti-clickjacking;
- `Permissions-Policy` с отключением ненужных browser capabilities.

По возможности frontend не должен требовать `unsafe-inline`/`unsafe-eval`.

## 38. Host header / origin allowlist

Host должен знать свои allowed public origins/hosts.

Нельзя автоматически доверять любому `Host`/`X-Forwarded-*`.

Если reverse proxy используется перед приложением, список trusted proxy networks задаётся явно.

---

# XI. Domain, reverse proxy и публикация URL

## 39. Production topology

```text
DNS
 box.example.com
        │
        ▼
TLS edge / reverse proxy
 Caddy / nginx / equivalent
        │
        ▼
127.0.0.1:host-port
 stratbox-host
```

Backend port сам по себе не публикуется наружу.

## 40. Почему reverse proxy лучше встроенного public TLS

Он отделяет:

- certificate lifecycle;
- ACME;
- HTTP→HTTPS redirect;
- request size limits;
- connection limits;
- trusted proxy handling;
- optional WAF/network policy;
- access logs.

Для simple self-hosted deployment Caddy удобен автоматическим HTTPS, но architecture не должна зависеть от конкретного proxy.

## 41. Public URL — системная конфигурация deployment

Host должен знать canonical external base URL:

```text
https://box.example.com
```

Он используется для:

- OIDC redirect URI;
- absolute links;
- artifact links;
- security validation;
- notification deep links.

Это **system/deployment setting**, а не пользовательская настройка UI.

---

# XII. Persistence: пользователи, сообщения, кейсы и состояние

## 42. Что нуждается в transactional DB

Минимальный web-host store:

```text
principals
identity_links
sessions
roles
capability_grants

cases
case_steps
jobs
job_attempts
resource_leases

events
read_cursors
notifications
notification_receipts

artifacts
artifact_versions
logs

assignments
approvals
background_processes

workspaces
workspace_memberships
settings
```

## 43. Что не должно храниться в DB как blob по умолчанию

В файловом/object store остаются:

- Excel;
- CSV;
- ZIP;
- PDF;
- datasets;
- raw sources;
- physical operation logs;
- large previews;
- uploads;
- caches.

DB хранит metadata, relationships, hashes, provenance и storage refs.

## 44. SQLite или PostgreSQL

### SQLite подходит, если одновременно выполняются условия

```text
один host machine
один authoritative runtime/service
DB находится на local disk
не нужна высокая concurrent write throughput
клиенты никогда не открывают DB напрямую
```

Это хороший embedded profile для небольшого self-hosted узла.

### PostgreSQL предпочтительнее, если

```text
несколько server processes/workers активно пишут metadata
высокая multi-user concurrency
нужна зрелая DB administration/backup/monitoring
планируется horizontal scaling
нужна server-side row security как дополнительный defense-in-depth
```

## 45. Целевая архитектурная рекомендация

Сделать persistence boundary так, чтобы application model от DB engine не зависела.

Для первой web production deployment разумно выбрать **PostgreSQL как canonical server store**, а SQLite оставить:

- для local embedded host;
- development;
- лёгких single-node installations.

При этом нельзя превращать поддержку двух DB в матрицу разного поведения. Semantics, migrations и tests должны быть одинаковыми на уровне repositories.

## 46. Чего точно нельзя делать

```text
network share/SMB
    └─ shared state.sqlite
        ├─ client A opens directly
        └─ client B opens directly
```

Удалённые клиенты общаются с server API, а DB engine живёт рядом с DB storage.

---

# XIII. Файловая комната: решаем главный продуктовый вопрос

## 47. «Всё общее» и «всё личное» — оба варианта слишком грубые

Полностью shared workspace создаёт проблемы:

- случайное раскрытие пользовательских загрузок;
- конфликты имён;
- перезапись;
- шум;
- сложнее безопасные черновики;
- сложнее user-specific inputs.

Полностью personal workspace тоже плох:

- общие datasets дублируются;
- коллеги не видят результат;
- фоновые jobs теряют естественный общий контекст;
- collaboration превращается в пересылку файлов.

## 48. Целевая multi-scope модель

```text
Node
│
├─ Shared Workspace
│  ├─ input/
│  ├─ datasets/
│  ├─ output/
│  └─ published/
│
├─ Personal Workspace: user-A
│  ├─ uploads/
│  ├─ drafts/
│  └─ output/
│
├─ Personal Workspace: user-B
│  └─ ...
│
├─ Run Workspace: case-123
│  ├─ input_refs/
│  ├─ work/
│  └─ output/
│
└─ System Workspace
   ├─ cache/
   ├─ temp/
   ├─ logs/
   └─ runtime/
```

## 49. Shared workspace

Назначение:

- общие официальные source snapshots;
- канонические datasets;
- team-visible inputs;
- опубликованные результаты;
- stable output aliases.

Запись туда требует более сильной capability, чем чтение.

## 50. Personal workspace

Назначение:

- пользовательские uploads;
- временные исследования;
- private drafts;
- personal exports;
- staging перед публикацией.

По умолчанию виден только владельцу и admin/operator при специальном праве.

## 51. Run workspace

Каждый case/job получает isolated namespace:

```text
run/<case_id>/...
```

Плюсы:

- меньше collision;
- проще cleanup;
- проще audit/lineage;
- проще повторный run;
- partial result не маскируется под stable published output.

После success артефакт может быть **опубликован** в Shared/Personal scope атомарным действием.

## 52. System workspace

Browser никогда не должен видеть его как обычный Explorer root.

Там живут:

- DB;
- cache;
- temp;
- secrets references;
- internal logs;
- worker state;
- migrations/backups metadata.

## 53. Физическая структура не является API

Клиент видит:

```text
WorkspaceRef(scope="shared", id="...")
FileRef(file_id="...")
ArtifactRef(artifact_id="...")
```

а не:

```text
/srv/stratbox/data/users/123/...
C:\Strategy Box Data\...
```

Это критично для Windows/Web/Android portability.

---

# XIV. Workspace Explorer в браузере

## 54. Browser Explorer должен быть server-backed

Операции:

```text
list directory
read metadata
upload
create folder
rename
move/copy
remove
preview
publish
```

идут через host API и проверяются authorization layer.

## 55. Direct filesystem mount браузеру не нужен

Browser sandbox всё равно не даёт нормального универсального direct access к server filesystem.

Это плюс: мы вынуждены построить правильную logical FileStore boundary.

## 56. Server-side path traversal protection

Любой path-like input:

- normalizes server-side;
- разрешается только внутри выбранного workspace root;
- запрещает `..` escape;
- запрещает symlink escape, если symlinks поддерживаются;
- destructive operations используют explicit resource ID/ref, а не свободный absolute path.

---

# XV. Uploads

## 57. Upload — security boundary

Любой пользовательский upload считается недоверенным.

Минимальные controls:

- разрешённые типы определяются operation/use case;
- extension не является единственной проверкой;
- server-generated storage name;
- оригинальное имя хранится как metadata;
- size limit;
- quota;
- archive expansion limits;
- ZIP/XML bomb protection;
- malware scanning, где это требуется deployment policy;
- parsing в worker с resource limits;
- upload storage вне webroot.

## 58. Upload lifecycle

```text
browser upload
→ quarantine/staging
→ validate type/size/content
→ optional malware/CDR checks
→ create FileRef
→ move into personal/shared workspace
→ event/audit record
```

## 59. Нельзя доверять `Content-Type`

Browser-supplied MIME — лишь hint.

Для critical parsers host проверяет actual format/signature и даёт parser-у только допустимые inputs.

---

# XVI. Artifacts и downloads

## 60. Artifact становится сетевой сущностью

Целевой `ArtifactRef`:

```text
artifact_id
name
kind
mime_type
size
content_hash
producer_case_id
producer_job_id
created_by
created_at
workspace_scope
storage_ref
visibility
provenance_ref
preview_capabilities
```

## 61. Download

```text
GET /api/v1/artifacts/{id}/content
```

Server:

1. authenticates;
2. authorizes object-level access;
3. открывает storage ref;
4. ставит безопасный `Content-Type`;
5. ставит `Content-Disposition`;
6. stream-ит файл;
7. пишет audit/security event по необходимости.

## 62. Preview

Preview не должен означать «отдать произвольный файл как active content внутри authenticated origin».

Безопаснее:

- server-generated table preview;
- image preview;
- text preview с escaping;
- PDF через безопасный isolated viewer/policy;
- unsupported/active types — download only.

Если позже понадобится богатый preview untrusted HTML/SVG, разумен отдельный cookie-less artifact origin/sandbox.

---

# XVII. Jobs и background execution

## 63. Browser request не должен выполнять тяжёлый сценарий в request thread

Правильный ответ на запуск:

```text
POST /runs
→ validate
→ create Case
→ create Job
→ enqueue
→ HTTP 202 / representation
```

Дальше worker выполняет работу независимо от HTTP connection.

## 64. Один Job Manager для всех запусков

Через него идут:

- manual web run;
- Windows run;
- Android run;
- scheduled/background run;
- assignment action;
- AI-initiated run;
- retry/resume.

## 65. Worker isolation

Минимально тяжёлые операции должны исполняться вне web request process.

Это может быть:

- child process;
- managed worker pool;
- отдельный service process.

Причины:

- CPU-heavy work не блокирует API;
- crash parser-а не убивает web host;
- легче cancellation;
- resource limits;
- clearer logs;
- future multi-worker scaling.

## 66. Job lifecycle

```text
queued
waiting_resource
running
waiting_approval
succeeded
failed
cancel_requested
cancelled
interrupted
outcome_unknown
```

Состояния `interrupted`/`outcome_unknown` важны для crash-safe semantics.

## 67. Resource leases

Host координирует записи:

```text
read:dataset:x
write:dataset:y
exclusive:workspace_cleanup
```

Два браузера не должны создать две независимые локальные правды о конфликте.

## 68. Cancellation

Cancel — server command, а не убийство browser task.

```text
POST /jobs/{id}/cancel
→ authorization
→ cancellation requested
→ worker safe point
→ cleanup
→ terminal result
```

---

# XVIII. Events, messages и сценарный чат

## 69. Web UI может выглядеть почти как Windows scenario chat

Смысл интерфейса сохраняется:

- cases;
- system notices;
- background notices;
- assignment notices;
- artifacts;
- authors;
- current stages;
- unread filters.

## 70. Scenario timeline должна быть общей

Case/event существует один раз на host.

UI карточки — projection.

## 71. Event order

Host выдаёт монотонный `node_seq`.

```text
1034 case.started
1035 step.started
1036 artifact.created
```

Timestamp нужен для отображения, sequence — для consistency/reconnect.

## 72. Unread — per user

Вместо общего `unread=true/false`:

```text
user_read_cursors
notifications receipts
```

Один пользователь не может «прочитать» событие за всех остальных.

## 73. Comments/real chat

Если позже появятся свободные комментарии пользователей, их следует добавлять как отдельный `Comment`/event kind.

Не стоит превращать Strategy Box в общий messenger. Центральная timeline остаётся operational.

---

# XIX. Users, presence и sessions

## 74. User record должен быть минимальным

Strategy Box хранит только то, что требуется продукту:

```text
principal_id
identity provider link
name/avatar metadata при необходимости
status
role/capabilities
preferences
created/last seen timestamps
```

Он не должен копировать весь corporate directory.

## 75. Presence — ephemeral projection

Online определяется через:

```text
active session
+ fresh heartbeat / SSE connection
+ session lifecycle
```

Heartbeats не превращаются в бесконечный permanent audit trail.

## 76. Multiple sessions

Один пользователь может иметь:

```text
Chrome laptop
Windows desktop client
Android
```

Все sessions принадлежат одному principal.

Logout/revoke session должен закрывать соответствующие live connections.

---

# XX. User preferences и настройки web

## 77. Настройки делятся по scope

```text
Deployment/System
Node
Workspace
User
Device/Browser
```

### Deployment/System

- public base URL;
- DB connection;
- identity provider;
- TLS/proxy trust;
- storage roots;
- worker configuration;
- secrets.

Не показываются обычному пользователю как «настройки приложения».

### Node

- background policies;
- retention;
- shared workspace policy;
- artifact limits;
- operation availability;
- admin-controlled defaults.

### User

- theme;
- accent;
- default landing mode;
- notification preferences;
- default artifact format/presentation preferences;
- preferred workspace where applicable.

### Device/Browser

- panel width;
- last open inspector tab;
- transient drafts;
- last filters.

## 78. Что хранить в browser local storage

Только non-sensitive presentation convenience.

Не хранить:

- session ID;
- access token;
- refresh token;
- passwords;
- secrets;
- sensitive case contents.

---

# XXI. Observability и audit в web mode

## 79. Возникает новый слой — HTTP/security observability

К уже исследованным:

- core diagnostics;
- job logs;
- cases/events;
- AppDock node health;

добавляются:

- HTTP request outcomes;
- authentication events;
- authorization denials;
- session lifecycle;
- upload/download security events;
- rate limit events;
- proxy/TLS failures;
- API validation errors;
- SSE connection/reconnect state.

## 80. Correlation identity

Каждый request/run должен быть связан через IDs:

```text
request_id
principal_id
session_id (не secret value)
case_id
job_id
operation_id
problem_id
artifact_id
```

## 81. Что нельзя писать в логи

- raw session cookie;
- access/refresh token;
- password;
- encryption key;
- DB connection secret;
- secret operation params;
- чувствительное file content;
- целые request bodies по умолчанию.

## 82. Audit trail

Отдельно полезно фиксировать high-risk actions:

- login/logout;
- role/capability changes;
- user administration;
- dangerous operations;
- approvals;
- artifact publication/deletion;
- shared workspace deletion/move;
- security setting changes;
- backup/restore actions.

Audit и debug log — разные сущности.

---

# XXII. Security model: основные угрозы

## 83. Account takeover

Controls:

- OIDC/MFA;
- secure sessions;
- session rotation/revocation;
- rate limiting;
- step-up auth для sensitive admin actions;
- audit.

## 84. Broken access control

Controls:

- deny-by-default;
- object-level authorization;
- server-side checks;
- automated authorization tests;
- no trust in frontend flags.

## 85. CSRF

Controls:

- SameSite;
- CSRF token;
- Origin checks;
- state change only via unsafe HTTP methods with CSRF validation.

## 86. XSS

Controls:

- framework escaping;
- sanitize any rich text;
- strict CSP;
- no untrusted HTML artifact served into main origin;
- no auth tokens in localStorage.

## 87. Malicious uploads

Controls:

- allowlist;
- file signature/type validation;
- size and decompression limits;
- quarantine;
- safe parsers;
- worker isolation;
- antivirus/CDR where required.

## 88. Path traversal / filesystem escape

Controls:

- logical IDs;
- canonical root resolution;
- no arbitrary absolute server paths from client;
- symlink policy;
- authorization + guards.

## 89. DoS / resource exhaustion

Controls:

- rate limits;
- max request/upload size;
- job queue limits;
- per-user concurrent job quotas;
- worker CPU/memory/time limits where practical;
- log retention;
- disk quotas;
- cancellation;
- health monitoring.

## 90. Supply-chain/plugin risk

Server-side extensions execute with meaningful authority.

Нужны:

- trusted package sources;
- pinned versions/hashes;
- compatibility contract;
- capability declarations;
- no arbitrary remote plugin install from web UI by ordinary user;
- restart/reload policy;
- audit of install/enable/disable.

Browser-side arbitrary JavaScript plugins особенно опасны из-за XSS/security model; их лучше не вводить как первый extension mechanism.

---

# XXIII. Web plugins и extensibility

## 91. Не надо давать plugin-у unrestricted frontend JavaScript сразу

Безопасный первый слой расширения:

- operation/scenario descriptors;
- declarative forms;
- theme/style tokens;
- artifact render hints;
- settings schema;
- server-side adapters;
- safe metadata panels.

## 92. Если появятся true frontend plugins

Они должны иметь отдельную security model:

- signed/trusted bundles;
- versioned frontend API;
- CSP integration;
- explicit capabilities;
- isolation/sandbox where possible;
- disable-by-default.

Это отдельный зрелый этап, а не prerequisite web host-а.

---

# XXIV. Устойчивость и recovery

## 93. Process crash

Host restart должен:

1. открыть state store;
2. проверить schema;
3. найти jobs в non-terminal state;
4. сопоставить worker leases;
5. пометить потерянные executions как interrupted;
6. применить recovery policy;
7. восстановить SSE snapshot state;
8. продолжить background scheduler.

## 94. Database failure

Нельзя silently fallback на пустую историю.

UI получает:

```text
Node degraded
Shared state unavailable
Read-only diagnostic surface available
```

## 95. Artifact write

Целевой паттерн:

```text
temp/run-scoped write
→ fsync/close where relevant
→ validate
→ hash
→ atomic publish/move
→ DB artifact record commit
```

Если последний шаг не прошёл, reconciler должен уметь найти orphaned temp/artifact objects.

## 96. Backups

Минимальный backup set:

- state DB;
- node configuration без plaintext secrets;
- artifact/shared workspace store;
- manifests/hashes;
- migrations/version info.

Backup должен быть:

- не на том же единственном диске;
- по возможности encrypted;
- проверяемым restore-test;
- versioned.

## 97. Upgrade

Перед migration:

- readiness check;
- backup/checkpoint;
- stop accepting new jobs;
- wait/cancel according policy;
- schema migration;
- application upgrade;
- post-upgrade health check;
- rollback/recovery route.

AppDock естественно подходит как внешний owner этого lifecycle.

---

# XXV. Health и readiness

## 98. Нужны минимум два health смысла

```text
/livez
    process жив

/readyz
    способен обслуживать работу
```

Readiness проверяет:

- state DB;
- workspace/storage;
- core import/runtime;
- required extensions;
- job manager;
- migrations;
- identity integration where required.

## 99. Application health не равен HTTP 200

Host может быть жив, но degraded:

```text
API reachable
DB OK
shared workspace unavailable
source gateway unavailable
worker pool degraded
```

Эти компоненты должны попадать в structured health model и AppDock projection.

---

# XXVI. Browser UI

## 100. Интерфейс может быть очень похож на Windows

Смысловая IA переносится почти напрямую:

```text
Проводник
Сценарии
Каскады
Фоновые
Участники
Поручения

center: scenario timeline
right: case/log/artifact/params inspector
```

## 101. Но реализация не должна пытаться быть pixel-identical Qt port

Web имеет другие возможности:

- URL routes;
- tabs/history;
- responsive layout;
- drag/drop upload;
- browser downloads;
- deep links;
- keyboard shortcuts;
- web accessibility;
- reconnect/offline indicators.

Нужно сохранять design language и interaction semantics, а не копировать ограничения desktop toolkit.

## 102. URL routing

Полезные routes:

```text
/app/scenarios
/app/cascades
/app/files
/app/background
/app/participants
/app/assignments
/app/cases/{case_id}
/app/artifacts/{artifact_id}
/app/settings
/app/node
```

Deep link должен работать после login.

## 103. Stale/offline UI

Если SSE/API connection пропала:

- последний snapshot остаётся видимым;
- появляется явная метка «соединение потеряно / данные могут быть устаревшими»;
- shared mutations блокируются;
- reconnect идёт автоматически;
- после reconnect применяется delta или новый snapshot.

Не нужен сложный offline-first merge.

---

# XXVII. Frontend technology

## 104. Требования важнее конкретного framework

Frontend должен поддерживать:

- TypeScript;
- generated API types;
- accessible components;
- virtualized long timelines/file lists;
- SSE;
- robust form validation;
- CSP-friendly build;
- theme tokens;
- responsive layout;
- testability.

## 105. Практичный default

Для отдельного `stratbox-web` рационален современный TypeScript SPA stack. React является самым консервативным default по ecosystem/tooling, но architecture должна быть framework-neutral на уровне API contracts и design tokens.

Не стоит переносить Python/Qt runtime в browser ради «общего языка» — это даст больше ограничений, чем реального reuse.

---

# XXVIII. Backend technology

## 106. Python ASGI естественно соответствует текущей системе

Поскольку core Python-native, host также логично оставить Python service.

Практичная реализация:

```text
ASGI application
+ typed validation schemas
+ HTTP REST
+ SSE
+ async network I/O
+ worker processes for heavy work
```

FastAPI/Starlette-class stack хорошо подходит по форме, однако architecture не должна зависеть от framework-specific models в application/domain слоях.

## 107. Web server process и worker process — разные ответственности

```text
API process
    handles HTTP/auth/state commands

Worker pool
    executes long stratbox work
```

Если operation CPU-heavy, async function сама по себе проблему не решает; нужен process isolation/executor.

---

# XXIX. Deployment profiles

## 108. Local desktop profile

```text
Windows PC
AppDock
 ├─ local stratbox-host (loopback/IPC)
 └─ stratbox-windows
       ↓
      host
```

Пользователь может вообще не замечать наличие host service.

## 109. Self-hosted web profile

```text
Linux server / mini-PC
AppDock or system service
 ├─ stratbox-host
 ├─ DB
 ├─ workspace/artifacts
 └─ reverse proxy/web bundle

users
 └─ https://box.example.com
```

## 110. Remote Windows profile

```text
Windows client
stratbox-windows
     ↓ HTTPS
remote stratbox-host
```

В этом режиме Windows Explorer отображает server workspace через File API, а не пытается напрямую монтировать server path.

## 111. Android profile

```text
stratbox-android
    ↓ same API
stratbox-host
```

Большая часть тяжелых operations остаётся на host.

---

# XXX. AppDock integration

## 112. AppDock должен управлять host lifecycle, а не app data semantics

AppDock responsibility:

- install/update;
- runtime environment;
- service lifecycle;
- node identity;
- secrets injection;
- Data root/storage handoff;
- remote exposure/attachment;
- host-level health;
- recovery tooling;
- support bundle boundary.

Strategy Box Host responsibility:

- users within product context;
- app authorization;
- cases/jobs/events;
- scenario execution;
- artifacts metadata;
- workspaces semantics;
- assignments;
- background automation;
- app-level audit.

## 113. Host как first-class surface/service

Будущий AppDock manifest Strategy Box должен уметь объявить:

```text
background/service component = stratbox-host
web surface endpoint
health/preflight
persistent node storage
Data workspace binding
capabilities
```

Windows surface становится ещё одним client component того же world/node.

---

# XXXI. Data isolation и privacy

## 114. Shared по умолчанию только для действительно общих сущностей

Shared:

- case status;
- job status;
- node health;
- team artifacts marked shared;
- shared datasets;
- assignments according visibility;
- safe operational events.

Personal/private:

- personal uploads;
- drafts;
- hidden operation params;
- session details;
- personal notification state;
- private artifacts.

Technical restricted:

- full stack traces;
- internal paths;
- security events;
- raw secrets provenance;
- admin configuration.

## 115. Parameter sensitivity

Operation parameter descriptors должны уметь объявлять:

```text
public
masked
private
secret
technical
```

Shared case history никогда не сериализует `secret` raw value.

---

# XXXII. Retention

## 116. У разных данных разный lifecycle

### Long-lived

- Case summary;
- final status;
- artifacts metadata;
- provenance;
- important audit events.

### Medium-lived

- detailed events;
- operation logs;
- previews;
- job attempts.

### Short-lived

- temp workspace;
- upload quarantine;
- worker scratch;
- presence heartbeat state.

## 117. Retention — node policy

Пользователь не должен случайно выключить обязательный audit/log retention через обычный Settings UI.

---

# XXXIII. Search, indexing и history size

## 118. JSON history перестаёт масштабироваться раньше, чем UI

Server DB позволяет нормальные queries:

```text
cases by user/status/date/scenario
artifacts by type/case/source
failures by problem code
assignments by assignee/status
```

## 119. Full-text search

На первом этапе достаточно indexed structured fields и filenames/titles.

Полный поиск по содержимому документов можно добавить отдельным subsystem позже. Он не является prerequisite web mode.

---

# XXXIV. API versioning и compatibility

## 120. Обратная совместимость сейчас проекту не нужна, но contract identity всё равно нужна

Причина не legacy, а независимые release cycles:

```text
host version
web version
windows version
android version
```

Даже если каждый major update допускает breaking changes, client должен уметь понять incompatibility.

Минимально:

```text
/api/v1/meta
api_contract_version
host_version
min_client_contract
capabilities
```

## 121. Generated client schemas

Лучше иметь один machine-readable API schema и генерировать types/client stubs для web/Android/Windows, чем копировать JSON models вручную.

---

# XXXV. Нужен ли message broker

## 122. В первой single-node версии — скорее нет

Не стоит сразу добавлять Redis/RabbitMQ/Kafka только потому, что продукт стал server-side.

Для одного узла достаточно:

```text
transactional DB
+ durable jobs table
+ worker leases
+ append-only events
+ in-process/subprocess wakeups
```

## 123. Когда broker становится оправдан

- несколько host instances;
- очень много workers;
- separate services;
- высокой частоты событий;
- потребность в reliable cross-process pub/sub beyond DB polling/notifications.

До этого broker создаёт эксплуатационный вес без нужной ценности.

---

# XXXVI. Нужна ли контейнеризация

## 124. Контейнер — deployment method, не архитектурный prerequisite

Host должен уметь запускаться как нормальный service process.

Варианты упаковки:

- AppDock-managed Python environment/service;
- systemd service;
- OCI container/compose.

Core contracts от этого не меняются.

## 125. Для self-hosted users контейнер может быть удобен

Особенно если web profile включает PostgreSQL + reverse proxy.

Но AppDock уже решает значительную часть installation/lifecycle задач, поэтому двойная обязательная оркестрация может быть лишней.

---

# XXXVII. Что делать с local Windows mode

## 126. Не сохранять две архитектуры навсегда

Плохая конечная схема:

```text
Windows:
  local JSON state + Qt executor

Web:
  server DB + host executor
```

Это быстро породит два продукта.

## 127. Лучше convergence через host

Даже local desktop можно постепенно перевести на:

```text
AppDock starts local host
Windows connects locally
```

Для пользователя это всё ещё desktop application, но application runtime один.

## 128. Допустимый переходный этап

На короткое время Windows может поддерживать:

```text
LocalExecutionBackend
RemoteHostExecutionBackend
```

Но целевой owner cases/jobs/history — host.

---

# XXXVIII. Web и browser filesystem UX

## 129. «Открыть файл» меняет смысл

Desktop:

```text
open_path(local path)
reveal_in_explorer(local path)
```

Web:

```text
preview artifact
browser download
copy share link
open file metadata
```

Поэтому surface action должен зависеть от client capabilities.

## 130. Нельзя заставлять generic Scenario содержать desktop action

`open Excel file` не должен быть шагом server workflow.

Workflow создаёт Artifact; surface решает, какие действия доступны над Artifact.

---

# XXXIX. Сценарии и каскады в web host

## 131. Host усиливает ранее предложенную Command → Scenario → Cascade architecture

```text
Cascade/Scenario request
        ↓
Planner
        ↓
ExecutionPlan
        ↓
Job Manager
        ↓
Workers
        ↓
Commands / stratbox operations
```

## 132. План можно показывать в UI до запуска

Web удобно показывает:

- какие scenarios входят;
- что будет загружено;
- какие outputs появятся;
- destructive actions;
- required approval;
- estimated scope/known resource conflicts.

Это повышает прозрачность.

---

# XL. Authorization для background и AI

## 133. Background actor

Фоновый процесс не должен «наследовать права последнего пользователя».

У него собственный service principal/capability envelope.

## 134. AI actor

Будущий AI также получает:

- отдельный principal;
- limited capabilities;
- operation/scenario catalog;
- no raw filesystem/shell by default;
- approvals для dangerous actions;
- полный audit trail.

Web host делает такую модель намного естественнее.

---

# XLI. Source access и browser

## 135. Browser не должен сам ходить к Банку России и другим source sites

Все downloads выполняются host/core side.

Причины:

- CORS;
- network policy;
- proxy/gateway rules;
- reproducibility;
- caching;
- secrets;
- source validation;
- provenance.

Browser получает только application result/progress.

---

# XLII. Security baseline

## 136. Рекомендуемый verification baseline

Для web-host security requirements разумно использовать OWASP ASVS 5.0 как контрольный checklist, адаптированный к реальному risk level Strategy Box.

Минимально покрыть разделы:

- frontend security;
- APIs;
- file handling;
- authentication;
- session management;
- authorization;
- OAuth/OIDC;
- secure communication;
- data protection;
- logging/error handling.

Это лучше собственного неформального списка «поставили HTTPS — значит безопасно».

---

# XLIII. Рекомендуемые acceptance criteria web-host MVP

## 137. Deployment

- host устанавливается на server без Windows GUI;
- запускается как persistent service;
- reverse proxy публикует HTTPS URL;
- external bind без auth запрещён;
- health/readiness доступны AppDock/operator.

## 138. Authentication

- OIDC login работает;
- session cookie HttpOnly/Secure/SameSite;
- logout реально инвалидирует server session;
- revoked user теряет доступ;
- auth/security events логируются.

## 139. Authorization

- viewer не запускает scenario;
- analyst запускает разрешённый scenario;
- own/any cancellation различаются;
- personal artifact другого пользователя недоступен;
- shared artifact доступен согласно policy;
- technical logs доступны только соответствующей capability.

## 140. Execution

- запуск возвращает Case/Job;
- browser можно закрыть;
- job продолжает работу;
- после reconnect state восстанавливается;
- duplicate retry с одним idempotency key не создаёт второй run;
- cancellation cooperative;
- worker crash даёт interrupted/unknown, а не false success.

## 141. Realtime

- snapshot + SSE;
- reconnect after seq;
- gap detection;
- unread per user.

## 142. Files

- shared/personal/run scopes;
- upload limits;
- path traversal tests;
- artifact download authorization;
- physical server path не попадает в public API;
- server workspace не является static webroot.

## 143. Reliability

- DB transactionality;
- migrations;
- backup;
- restore test;
- app restart recovery;
- artifact atomic publication;
- disk-full behavior понятен и диагностируем.

---

# XLIV. Anti-patterns, которые стоит запретить архитектурно

## 144. Запускать web server внутри Qt process

Web host должен жить независимо от desktop UI.

## 145. Хранить shared state в JSON files

JSON может остаться export/debug format, но не authoritative multi-user database.

## 146. Давать браузеру server filesystem path

Использовать refs/IDs.

## 147. Публиковать `/workspace` как static directory

Все file access проходит через authorization handler.

## 148. Хранить access token в localStorage

Использовать server-side session/BFF.

## 149. Делать frontend authorization единственной защитой

Server проверяет каждое действие.

## 150. Привязывать host к Linux в domain model

Linux — deployment, host — application runtime.

## 151. Запускать background engine отдельно от обычного Job Manager

Один execution path.

## 152. Broadcast всех ошибок всем пользователям

Ошибки имеют personal/case/resource/node/security scope.

## 153. Отдавать stack trace пользователю

Safe problem projection + restricted technical log.

## 154. Создавать WebSocket «потому что realtime»

SSE достаточно, пока не появился реальный bidirectional use case.

## 155. Добавлять Kubernetes/Redis/Kafka заранее

Single-node architecture должна оставаться эксплуатационно лёгкой.

---

# XLV. Предлагаемая последовательность разработки

## Этап 1 — canonical host contracts

1. Зафиксировать ownership: host владеет Case/Job/Event/Artifact shared truth.
2. Вынести toolkit-neutral models из Windows ownership.
3. Ввести `StrategyBoxClient` contract.
4. Ввести `ExecutionBackend`/host boundary.
5. Стабилизировать Scenario/Cascade/Job/Case semantics.

## Этап 2 — headless local host

1. Создать `stratbox-host`.
2. API без public exposure, loopback only.
3. Transactional state store.
4. Job Manager + worker process.
5. Snapshot/events API.
6. Перевести Windows на local host mode.

Это самый важный промежуточный milestone: host architecture проверяется до internet security surface.

## Этап 3 — web surface

1. Создать `stratbox-web`.
2. Scenario timeline.
3. Catalog/forms.
4. Case inspector.
5. Artifacts/log summaries.
6. Workspace Explorer.
7. SSE reconnect.
8. Responsive shell.

## Этап 4 — authentication + external publication

1. OIDC/BFF.
2. Sessions.
3. Capabilities.
4. reverse proxy/TLS.
5. CSRF/CSP/security headers.
6. rate limits.
7. audit.
8. allowed hosts/proxy trust.

Только после этого host разрешается слушать внешний interface.

## Этап 5 — shared/personal files

1. Workspace scopes.
2. Upload pipeline.
3. artifact IDs/download handlers.
4. publish/move semantics.
5. quotas/retention.
6. lineage.

## Этап 6 — node automation/collaboration

1. background scheduler;
2. assignments;
3. approvals;
4. real presence;
5. notifications;
6. resource leases;
7. retries/resume.

## Этап 7 — remote Windows и Android

1. remote host profile для `stratbox-windows`;
2. client generated contracts;
3. Android surface;
4. notification/deep-link flows.

---

# XLVI. Предлагаемый минимальный первый release topology

## 156. Что я бы сделал без лишней инфраструктуры

```text
1 Linux host
1 stratbox-host service
1 PostgreSQL instance
1 local artifact/workspace filesystem
1 reverse proxy
1 stratbox-web static bundle
N browser users
N worker processes
```

Без:

- Kubernetes;
- Redis;
- Kafka;
- distributed object store;
- separate microservices;
- browser plugins;
- multi-node clustering.

Это уже полноценный надёжный self-hosted product, но сохраняет сравнительно низкую эксплуатационную сложность.

## 157. Embedded small-node variant

Для mini-PC/personal local host возможен более лёгкий профиль:

```text
stratbox-host
SQLite local DB
local filesystem
Caddy/internal TLS or localhost
```

Но browser clients всё равно работают через API; SQLite никогда не открывается по network share.

---

# XLVII. Итоговый выбор по файловой комнате

## 158. Моя рекомендация

Не выбирать один из двух вариантов пользователя.

Целевая модель:

```text
Shared Node Room
    общие datasets, inputs, published artifacts

Personal Room
    private uploads, drafts, personal exports

Run Room
    isolated execution workspace per Case/Job

System Room
    runtime-owned state/cache/log/temp
```

Это даёт:

- совместную работу без тотального раскрытия файлов;
- безопасные пользовательские черновики;
- меньше конфликтов;
- чистый artifact publication workflow;
- удобный Android/Web contract;
- понятные permissions;
- хорошую основу для future project/team spaces без перелома базовой модели.

---

# XLVIII. Итоговый выбор по репозиториям

## 159. Рекомендуемая конечная форма

```text
stratbox
    domain/business core

stratbox-host
    canonical headless runtime + API + persistence + execution

stratbox-windows
    Windows client

stratbox-web
    Browser client

stratbox-android
    Android client later
```

## 160. Почему теперь вынос host-а оправдан

В предыдущем исследовании single-node multi-user было разумно не создавать новый repository, пока runtime мог оставаться частью local desktop lifecycle.

Текущая постановка меняет это условие принципиально:

- host ставится на server;
- работает 24/7;
- обслуживает browser;
- продолжает jobs без UI;
- хранит shared truth;
- управляет пользователями/sessions;
- становится network security boundary;
- в будущем обслуживает Windows/Android remote clients.

Это самостоятельный deployable component с отдельным lifecycle. Значит, **`stratbox-host` теперь не преждевременное дробление, а естественная архитектурная граница**.

---

# XLIX. Самые важные решения в компактной форме

| Вопрос | Рекомендация |
|---|---|
| Как открыть Strategy Box по URL | отдельный persistent `stratbox-host` + `stratbox-web` |
| Нужен ли Linux-specific repo | нет; `stratbox-host`, Linux как deployment target |
| Должен ли web UI повторять Windows | по смыслу и design language — да; по технологии — нет |
| Где остаётся business logic | `stratbox` |
| Кто владеет Case/Job/Event shared truth | `stratbox-host` |
| Что делает Windows | client/surface, локальный или remote |
| Что делает browser | client/surface |
| Как получать live progress | SSE + snapshot/cursor; WebSocket позже при реальной необходимости |
| Как авторизовывать пользователей | OIDC preferred + server-side session/BFF |
| Где хранить токены в browser | нигде; opaque HttpOnly session cookie |
| Как хранить users/cases/messages | transactional DB |
| Где хранить Excel/ZIP/datasets | FileStore/artifact store, DB хранит refs/metadata |
| SQLite | embedded single-node local DB допустим |
| PostgreSQL | canonical production web-host store предпочтителен |
| Как устроить workspace | shared + personal + run + system scopes |
| Можно ли отдавать server path | нет, только refs/IDs |
| Можно ли публиковать workspace static | нет |
| Что происходит при закрытии browser | job продолжает работу |
| Кто управляет background jobs | тот же Node Job Manager |
| Как обновлять users в UI | server snapshot/events/presence projection |
| Как интегрировать AppDock | AppDock owns deployment/node lifecycle; host owns app runtime |

---

# L. Источники и внешняя сверка

## 161. Внутренние материалы Strategy Box

Использованы и сопоставлены:

- `stratbox_base_study_current_state_2026-10-06.md`;
- `stratbox-windows_current_state_full_research_2026-10-06.md`;
- `stratbox_single_node_multiuser_research_2026-10-07.md`;
- `stratbox_file_artifact_layer_research_2026-10-06.md`;
- `stratbox_execution_control_user_path_research_2026-10-07.md`;
- `stratbox_observability_errors_logs_research_2026-10-07.md`;
- `stratbox_commands_scenarios_cascades_research_2026-10-07.md`;
- `strategy_box_system_settings_research_2026-10-07.md`;
- AppDock — базовое описание продукта и проекта.

Актуальный GitHub `stratbox/main` дополнительно проверен 2026-10-07. Срез core source относительно исследования 2026-10-06 не изменился; новые commits добавили/перенесли исследовательские материалы и инструкции.

## 162. Внешние authoritative sources

### OWASP

- OWASP ASVS project, current stable 5.0.0:  
  https://owasp.org/projects/asvs

- OWASP Session Management Cheat Sheet:  
  https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html

- OWASP Authentication Cheat Sheet:  
  https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html

- OWASP Authorization Cheat Sheet:  
  https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html

- OWASP CSRF Prevention Cheat Sheet:  
  https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html

- OWASP File Upload Cheat Sheet:  
  https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

- OWASP Logging Cheat Sheet:  
  https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html

- OWASP REST Security Cheat Sheet:  
  https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html

- OWASP WebSocket Security Cheat Sheet:  
  https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html

- OWASP HTTP Headers Cheat Sheet:  
  https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html

### OAuth / OpenID Connect

- OpenID Connect Core 1.0:  
  https://openid.net/specs/openid-connect-core-1_0.html

- RFC 9700 — Best Current Practice for OAuth 2.0 Security:  
  https://www.rfc-editor.org/rfc/rfc9700.html

- RFC 10017 — OAuth 2.0 for Browser-Based Applications:  
  https://www.rfc-editor.org/rfc/rfc10017.html

### Browser APIs / Web Security

- MDN — Server-Sent Events / EventSource:  
  https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

- MDN — WebSocket API:  
  https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API

- MDN — Content Security Policy:  
  https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy

### Storage

- SQLite — Appropriate Uses For SQLite:  
  https://www.sqlite.org/whentouse.html

- SQLite — SQLite Over a Network, Caveats and Considerations:  
  https://www.sqlite.org/useovernet.html

- PostgreSQL — Row Security Policies:  
  https://www.postgresql.org/docs/current/ddl-rowsecurity.html

- PostgreSQL — Transaction isolation:  
  https://www.postgresql.org/docs/current/sql-set-transaction.html

### Reverse proxy / TLS edge example

- Caddy reverse proxy documentation:  
  https://caddyserver.com/docs/caddyfile/directives/reverse_proxy

---

# LI. Финальный вывод

Web/self-hosted режим не требует отдельной версии бизнес-логики Strategy Box. Он требует **правильного владельца application runtime**.

Сейчас часть этой роли исторически находится в `stratbox-windows`, потому что desktop был единственной реальной поверхностью. Как только появляется требование:

```text
поставить Strategy Box на сервер
→ открыть URL
→ подключить нескольких пользователей
→ закрыть browser и оставить jobs работать
→ подключить Windows/Android к тому же узлу
```

application runtime становится самостоятельным server product.

Поэтому лучший следующий архитектурный ход — **выделить `stratbox-host` как канонический headless runtime**, а браузер оформить как `stratbox-web` client. При этом текущие хорошие идеи Windows — scenario chat, cases, artifacts, assignments, presence, operation forms, workspace semantics — не выбрасываются. Наоборот, они становятся platform-neutral semantics, которые получают настоящего общего владельца.

Самая важная практическая формула будущего продукта:

```text
                ┌─ stratbox-windows
                ├─ stratbox-web
stratbox-host ──┼─ stratbox-android
                └─ future AI/client surfaces
       │
       ▼
   stratbox core
```

А для пользователя это выглядит просто:

> У него есть один Strategy Box-узел с данными, историей, пользователями и выполняемыми задачами. Открыть его можно локально из Windows-приложения или удалённо по защищённому URL. Все клиенты видят одну и ту же объективную картину работы, а права, личные файлы и пользовательское состояние остаются разделёнными.
