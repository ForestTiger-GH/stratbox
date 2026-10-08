# Strategy Box — тема 00: Corpus Map & Open Questions

**Ветка:** `03-consolidation-research`  
**Тема программы:** `00 — Corpus Map & Open Questions`  
**Дата:** 2026-10-08  
**Статус:** Research Synthesis — консолидирующее исследование; не Product Decision, не Target WHAT/HOW и не изменение кода  
**Основной корпус:** `02-base-study`  
**Исторический источник:** `01-old-notes`  

---

## 0. Executive summary

Третья ветка Strategy Box действительно нужна: вторая ветка уже перестала быть набором независимых заметок и превратилась в большой взаимозависимый корпус, в котором почти все крупные темы описаны несколькими документами с разных сторон. На текущем `main` в `02-base-study` находится **27 содержательных исследований** общим объёмом около **2,06 MiB Markdown-текста**, не считая README. Корпус был создан в основном 6–8 октября 2026 года и уже охватывает current-state core и Windows surface, execution, scenarios, background jobs, artifacts, sources/registries, multi-user, web/self-hosted, settings, design/motion, extensions, automation/AI и целевую смысловую архитектуру.

Главный результат темы 00: **корпус в целом сходится значительно сильнее, чем кажется по количеству документов**, однако несколько ключевых понятий и физических границ ещё не стабилизированы. Большинство расхождений относится не к фундаментальным принципам, а к терминологии, уровню абстракции или к тому, где именно физически разместить уже достаточно хорошо определённую ответственность.

К устойчивому ядру второй ветки можно отнести следующие выводы.

1. `stratbox` остаётся самостоятельной domain/business library: внешние источники, предметные преобразования, canonical data, расчёты, validation, provenance и domain artifacts должны быть доступны без GUI, AppDock и внешней когнитивной системы.
2. Strategy Box нужен отдельный **platform-neutral application/execution owner** над `stratbox`: Work/Jobs, orchestration, planning, background execution, durable state, collaboration, permissions, artifacts metadata и client projections не должны принадлежать Qt/Windows-процессу.
3. Windows, Web и Android должны быть поверхностями одной application semantics. Qt является renderer/adapter, а не владельцем product truth.
4. AppDock — внешний operational substrate: installation, node/environment lifecycle, activation, health, host/service lifecycle, remote boundary и platform observability. Он не должен становиться владельцем банковской бизнес-логики, пользовательских аналитических сценариев или предметного scheduler Strategy Box.
5. Foreground, background, scheduled, remote и AI-triggered execution должны проходить через **один execution spine**, а не через отдельные движки.
6. `FileStore` — нижняя физическая абстракция. `Artifact`, `SourceSnapshot`, `Dataset`, provenance и workspace semantics должны жить выше файлового пути.
7. Path, UI message, log line и DataFrame не могут быть устойчивой идентичностью системных объектов.
8. Current code уже доказывает ценность typed Request/Result, stable IDs, raw-source preservation, validation, provenance и plan/apply для destructive effects; эти patterns следует унифицировать, а не заменять новым универсальным framework.
9. Ошибка transport/backend не должна маскироваться как пустой результат, `False` или успешный terminal outcome. `UNKNOWN` — самостоятельное допустимое состояние.
10. Публичные core/surface должны знать только нейтральные extension contracts. Устройство конкретных закрытых environment-specific расширений остаётся вне публичных материалов.
11. UI settings, surface state, draft/recent state, runtime binding и managed policy — разные классы состояния.
12. Чат/Thread, Work, execution и artifact history должны быть разделены. Чат — контекст взаимодействия; Work — долговечная смысловая единица; execution — конкретная реализация работы.

Самые крупные нерешённые вопросы сосредоточены в четырёх местах.

**Первое — каноническая онтология execution/work.** В корпусе последовательно использовались `Command`, `Operation`, `Scenario`, `Cascade`, `Machine Scheme`, `Capability`, `Work`, `Case`, `Job`, `Run`, `Attempt`, `Thread`. Поздние исследования сильно сблизили значения, но окончательная непротиворечивая модель ещё не зафиксирована. Это центральная задача темы 02 и затем темы 04.

**Второе — логическая и физическая граница application runtime.** Корпус устойчиво требует headless/platform-neutral owner, но физические варианты `stratbox-core`, `stratbox-host` и комбинация package + service пока не сведены в одно решение. Сам факт отдельной ответственности уже устойчив; число репозиториев/packages/processes — **UNKNOWN / TARGET-HYPOTHESIS**.

**Третье — durable persistence и state authority.** Локальные JSON текущего Windows-прототипа признаны недостаточными. Для local/single-node исследований сходятся на транзакционном node-local store; для web/server — на полноценной server DB. Но точная storage topology, migrations, backup/recovery, retention, indexing и offline/reconnect ещё требуют отдельного сведения.

**Четвёртое — граница Work/Knowledge/Result/Artifact.** Поздние смысловые исследования требуют сильнее отделять data, observation, claim, evidence, result, acceptance, artifact и knowledge. Это направление устойчиво, однако точная минимальная semantic model намеренно ещё не материализована в schema/classes.

Тема 00 поэтому не должна принимать финальные архитектурные решения за темы 01–09. Её результат — **карта корпуса, register конфликтов и белых пятен, а также маршрутизация каждого исследовательского тезиса в дальнейшую консолидацию**.

---

# 1. Метод, границы и provenance

## 1.1. Что было изучено

Исследование начато с актуальной программы третьей ветки и README `03-consolidation-research`. Затем проверен полный каталог `02-base-study`, включающий 27 исследований. Для исторической сверки просмотрены четыре документа `01-old-notes`.

Фактическое implementation-state дополнительно проверялось по текущим owners:

- `ForestTiger-GH/stratbox`, `main`;
- `ForestTiger-GH/stratbox-windows`, `main`;
- внешняя продуктовая граница AppDock — по базовому описанию продукта и тем местам исследований, где она нужна для ownership.

Внешние методологические материалы использовались только как смысловая линза. В этом файле сознательно **не описывается структура MADAR, MADARAII или mandat-репозиториев**. Допустима только общая ссылка на выводы MADAR-методологии, уже применённые к Strategy Box.

Конкретные внутренние реализации закрытых корпоративных расширений также сознательно исключены. Здесь рассматривается только общий публичный extension/capability contract.

## 1.2. Проверка свежести current-state исследований

Базовое исследование `stratbox` от 2026-10-06 было выполнено на commit:

```text
e968853572676d8e5d963607d1f0cb50ff8f20b7
```

Текущий `stratbox/main` на момент этой консолидации:

```text
ea1dc8b933d5a07cd5b24d40720af7a430029280
```

Сравнение между ними показывает 31 commit, но изменения сосредоточены в README/AGENTS/workspace/Research. В diff-list **нет изменений `src/` или `tests/`**. Следовательно, current-state выводы по фактическому core остаются репрезентативными.

`stratbox-windows/main` по-прежнему находится на:

```text
959e9c4ce1441124af5111c1e025041714e04d3b
```

То есть ровно на том implementation snapshot, который исследовался 2026-10-06.

Это позволяет использовать два baseline-файла второй ветки как фактическую опору, а остальные документы трактовать прежде всего как тематические и целевые исследования поверх неё.

## 1.3. Классификация утверждений

В этом synthesis используется следующая дисциплина.

| Метка | Смысл |
|---|---|
| **CURRENT** | подтверждено текущим кодом/документацией implementation owner |
| **CONSOLIDATED** | несколько исследований независимо сходятся, фактических противоречий нет |
| **TARGET-HYPOTHESIS** | сильное предлагаемое направление, но Product Decision отсутствует |
| **CONFLICT** | существуют реально несовместимые позиции или термины |
| **SUPERSEDED** | более поздний материал явно уточнил или вытеснил ранний |
| **UNKNOWN** | корпус недостаточен либо вопрос сознательно отложен |

Важно: хронология помогает определить supersession, но более поздний файл автоматически не считается «истиной». При каждом расхождении учитываются scope, слой и фактический baseline.

---

# 2. Фактический baseline Strategy Box, который не следует повторно исследовать в теме 00

## 2.1. `stratbox`

**CURRENT.** `stratbox` версии `0.8.0` является библиотечным аналитическим ядром с нейтральной инфраструктурой и несколькими доменами макроэкономических/банковских данных. Core отделён от UI и AppDock. Внутри уже существуют FileStore, IO API, network/secrets/style contracts, registries, domain pipelines и крупная специализированная подсистема SORS restoration.

**CURRENT.** Архитектура неравномерна: лучшие домены уже используют typed Request/Result, stable IDs, validation и provenance, а часть API остаётся dict/DataFrame/convenience-oriented. Tests сильно концентрированы в SORS/forms/industries; FRG/escrow/collector и общая инфраструктура покрыты слабее. CI отсутствует.

**CURRENT.** Public packaging/documentation всё ещё содержит environment-specific coupling, которое следует удалить при реализации нейтрального extension contract. В этом synthesis такие закрытые детали не раскрываются.

## 2.2. `stratbox-windows`

**CURRENT.** `stratbox-windows` версии `0.1.0` — отдельный Windows application/surface. В нём уже есть operation/scenario descriptors, cases, events, artifacts, logs, workspace explorer, local preferences/history, AppDock activation/runtime state и Qt desktop UI.

**CURRENT.** Execution всё ещё привязан к desktop process: один active scenario, Qt `QThread`, отсутствие реального cancellation, local JSON history. Background/presence/assignments в значительной части являются semantic/UI scaffolds, а не зрелыми node-wide services.

**CURRENT.** Manifest локальный, foreground и Windows-only. Web/Android/remote execution — target directions, не текущие функции.

**CURRENT CONFLICT.** `stratbox-windows` по-прежнему требует старую core-версию `0.2.1`, тогда как актуальный `stratbox` имеет `0.8.0`; AppDock manifest также указывает старую core package version. Это реальный implementation drift.

## 2.3. AppDock boundary

**CONSOLIDATED.** AppDock рассматривается как внешняя платформа, управляющая установкой, рабочей средой/узлом, activation, lifecycle, health, recovery, host/remote boundary и безопасным предоставлением действий. Strategy Box должен отдавать ему readiness, state/projections и безопасные capability/action boundaries, не передавая предметное владение банковской логикой.

---

# 3. Карта корпуса `02-base-study`

## 3.1. Общая группировка

Корпус естественно распадается на семь перекрывающихся групп.

| Группа | Главная ответственность | Основные исследования |
|---|---|---|
| Baseline | Что существует сейчас | core current state; Windows current state |
| Data / Knowledge | sources, registries, FileStore, formats, artifacts, provenance, epistemics | artifact layer; formats; registry/source governance; epistemic architecture |
| Capability / Execution | operation, scenario, cascade, scheme, plan, job, automation | commands/scenarios; machine schemes; execution control; background jobs; automation/AI |
| State / Collaboration | durable state, multi-user, host, observability | multi-user; web/self-hosted; observability; settings |
| Surfaces / Design | Windows IA, themes, motion, artifact styling, portability | interface requirements; visual system; motion; customization; portability |
| Extension / External cognition | generic plugin contract, machine-facing boundary, AI readiness | extension contract; external cognition boundary/foundation/readiness/chat |
| Cross-system target | whole-product semantics and ownership | target decomposition; target epistemic architecture; target core/design note |

Эти группы нельзя превращать в архитектурные silos: третья ветка специально построена как сквозная, поэтому один и тот же документ часто уходит сразу в несколько тем 01–09.

---

# 4. Per-research corpus map

Ниже каждый файл второй ветки рассматривается по программе темы 00: основные сущности, current findings, target propositions, overlaps/conflicts, superseded material, UNKNOWN и destination.

## 4.1. `stratbox_base_study_current_state_2026-10-06.md`

**Основные сущности:** `stratbox`, FileStore, IO API, source/download, registries, canonical data, domain operations, Result, provenance, SORS, FRG.

**Current findings:** главный фактический baseline core. Подтверждает разделение core/surface, зрелость нескольких доменов, неравномерность public contracts, test gaps, stale registries, отсутствие CI и неполный optional-dependency contract.

**Target propositions:** унификация operations; source snapshot/provenance contract; registry lifecycle; build-data/export separation; structured diagnostics/events; operation registry после стабилизации contracts.

**Dependencies / overlap:** является базой почти всех последующих исследований.

**Conflict:** нет содержательного конфликта с поздними исследованиями; поздние работы преимущественно уточняют target model.

**Superseded:** отдельные конкретные package suggestions из baseline следует считать менее сильными, чем поздняя system-level консолидация.

**UNKNOWN:** точная будущая semantic operation model, unified source model, common result envelope.

**Destination:** 01, 02, 03, 06, 08, 09.

---

## 4.2. `stratbox-windows_current_state_full_research_2026-10-06.md`

**Основные сущности:** AppContext, OperationSpec, ScenarioSpec, ScenarioRunCase, Event, ArtifactRecord, LogRecord, assignments, presence, background processes, runtime state, workspace, Qt coordinator.

**Current findings:** главный фактический baseline Windows surface. Реально работают операции, сценарии, cases/events/logs/artifacts, local history и AppDock activation; background/presence/assignments лишь частично реализованы.

**Target propositions:** platform-neutral orchestration, job manager, cancellation, shared presentation semantics, future remote/mobile/AI, persistence interface.

**Conflict:** current `Case` используется как run-like object, тогда как поздние исследования вводят Work/Job/Run/Attempt и уменьшают семантическую нагрузку Case.

**Superseded:** Qt coordinator как возможный долгосрочный execution owner; local JSON как durable truth; six-mode top-level IA как target.

**UNKNOWN:** точная судьба `Case`, перенос shared layers в отдельный package/repo, persistence boundary.

**Destination:** 01, 02, 04, 05, 07, 08, 09.

---

## 4.3. `stratbox_file_artifact_layer_research_2026-10-06.md`

**Основные сущности:** FileStore, Blob/Content layer, Artifact, ArtifactManifest, ArtifactCatalog, Workspace, SourceSnapshot, lineage/provenance.

**Current findings:** текущие outputs преимущественно path-oriented; FileStore является правильным нижним contract, но artifact identity ещё слишком слаба.

**Target propositions:** immutable managed artifacts, stable ArtifactRef, SHA-256 content identity, manifest, run-centric lineage, отдельный workspace mutable layer, локальный catalog.

**Overlap:** сильное пересечение с source governance, automation/AI, multi-user, web/self-hosted, settings/artifact style.

**Conflict:** не с другими исследованиями, а с методологическим принципом «не создавать преждевременные abstractions»: именно рекомендация немедленно ввести CAS остаётся **TARGET-HYPOTHESIS**, а не consensus Product Decision.

**UNKNOWN:** какие outputs обязаны быть managed immutable artifacts, а какие остаются workspace files; retention; materialization policy; catalog backend profiles.

**Destination:** 02, 03, 05, 08, 09.

---

## 4.4. `strategy_box_automation_ai_research_2026-10-06.md`

**Основные сущности:** Operation, Scenario, Automation, Job, Case, AgentRun, Trigger, scheduler, approvals, capability catalog.

**Current findings:** semantic foundation уже существует, реальный scheduler/agent runtime отсутствует.

**Target propositions:** один Job/Case engine, structured trigger/scheduler semantics, conversational router как первый AI layer, bounded agent поверх canonical capabilities, artifact IDs/lineage.

**Conflict:** ранняя physical ownership-схема помещает Scheduler/JobManager в AppDock host runtime. Более позднее исследование background jobs переносит предметные Automation/Job semantics в Strategy Box headless host и оставляет AppDock владельцем service lifecycle. Это **SUPERSEDED/CLARIFIED**.

**Superseded:** «AppDock как владелец предметного scheduler Strategy Box».

**UNKNOWN:** machine-facing transport/API, approval policy, exact host packaging.

**Destination:** 04, 05, 06, 08.

---

## 4.5. `stratbox_commands_scenarios_cascades_research_2026-10-07.md`

**Основные сущности:** Command, Scenario, Cascade, ExecutionPlan, planner, Command DAG, resources, deduplication.

**Current findings:** Windows имеет OperationSpec + atomic/composite ScenarioSpec; composite scenario фактически выполняет роль раннего cascade.

**Target propositions:** Command как техническая единица, Scenario как user-meaningful task, Cascade как composition of scenarios; explicit ExecutionPlan до запуска; user UI scenario/cascade-first.

**Overlap:** machine schemes, external-cognition readiness, execution control, background jobs.

**Conflict:** поздние исследования чаще используют **Operation** как canonical machine-callable unit и `Machine Scheme` как reusable composition. Поэтому `Command` и `Cascade` ещё не являются стабилизированными canonical terms.

**Superseded:** automatic wrapping каждой operation в user-facing scenario — устойчиво отвергнуто последующими исследованиями.

**UNKNOWN:** останется ли `Command` отдельной публичной сущностью либо станет internal mechanism/building block; отношение Cascade ↔ Machine Scheme.

**Destination:** 02, 04, 06, 07.

---

## 4.6. `stratbox_execution_control_user_path_research_2026-10-07.md`

**Основные сущности:** scenario invocation, parameter profile, Case/Job, cancellation, retry, resource conflicts, user path, frontend-neutral execution service.

**Current findings:** текущий runner прячет слишком много execution semantics в Qt/client; cancellation отсутствует; параметры смешивают defaults, remembered UI values и run snapshot.

**Target propositions:** frontend-neutral execution service; JobManager; cooperative cancellation; immutable run parameter snapshot; resource coordination; shared multi-user execution truth.

**Overlap:** observability, background jobs, multi-user, automation/AI.

**Conflict:** термин `Case` местами ещё используется как основная пользовательская execution entity, тогда как более поздние Work-oriented документы выделяют Work отдельно.

**Superseded:** desktop process как единственный execution owner; late cancel rewriting terminal success; generic force-kill semantics.

**UNKNOWN:** exact Work/Case split, effect reconciliation policy, resource locking granularity.

**Destination:** 02, 04, 05, 08.

---

## 4.7. `stratbox_filestore_file_formats_research_2026-10-07.md`

**Основные сущности:** FileStore, FormatRegistry, detection, codecs, semantic adapters, materialization, XBRL/SDMX families.

**Current findings:** core IO surface уже широк, но dependency/install contract и форматная semantics неоднородны; Windows имеет собственные extension mappings.

**Target propositions:** format-agnostic FileStore; единый FormatRegistry; explicit detection; certified codecs; semantic adapters above codecs; unknown format как нормальное состояние.

**Overlap:** artifact layer, portability, registries/sources.

**Conflict:** существенного нет.

**Superseded:** generic write support для форматов, где semantics ненадёжна; extension-only detection; duplicated format maps in clients.

**UNKNOWN:** exact P0 codec scope, backend choices для специализированных families, materialization/caching rules.

**Destination:** 03, 08, 09.

---

## 4.8. `stratbox_business_segments_portability_reuse_architecture_research_2026-10-07.md`

**Основные сущности:** building block, technical service, domain service, canonical operation, Scenario, ExecutionContext, provider contract, Result, progress/cancellation/artifacts.

**Current findings:** бизнес-код уже переносим между Jupyter/Colab/application в разной степени; environment flags и app-owned product semantics местами протекают в core.

**Target propositions:** uniform exterior / variable interior; capability-driven applicability; neutral ExecutionContext; generic operation adapter in surfaces; curated reusable building-block API.

**Overlap:** machine schemes, plugin contract, core baseline, execution control.

**Conflict:** уровни `building block → domain service → operation` совместимы с machine-scheme research, но терминология требует сведения в теме 02.

**Superseded:** direct environment-specific branching как target; app layer, заново описывающий domain meaning.

**UNKNOWN:** какие building blocks достойны curated public exposure; где проходит threshold operation vs internal service.

**Destination:** 01, 02, 04, 06, 08.

---

## 4.9. `stratbox_business_logic_machine_schemes_architecture_research_2026-10-07.md`

**Основные сущности:** Mechanism, Building Block, Domain Service, Canonical Operation, Machine Scheme, ExecutionPlan, Capability Envelope, typed ports, effects, pre/postconditions.

**Current findings:** многие домены уже близки к machine-readable contracts, но единый ABI отсутствует.

**Target propositions:** semantic capability отдельно от implementation; typed OperationSpec; Scheme как typed graph; applicability/effects/idempotency/concurrency/cancellation/failure/provenance обязательны; plan/apply для effects.

**Overlap:** commands/scenarios, external-cognition readiness, portability.

**Conflict:** неясно, является ли Scenario product-facing projection Machine Scheme, отдельной authored workflow definition или соседней сущностью. Corpus использует все три варианта.

**Superseded:** DataFrame/dict как единственная внешняя machine boundary; giant mutable context.

**UNKNOWN:** richness Scheme IR; placement of branching/conditions; registry naming; formal external ABI.

**Destination:** 02, 04, 06, 08.

---

## 4.10. `stratbox_registry_source_governance_research_2026-10-07.md`

**Основные сущности:** RegistryDescriptor/Snapshot/Status, SourceDescriptor/Snapshot, reference registry, source catalog, domain registry, freshness, hashes.

**Current findings:** reference data, source catalogs и domain rule registries уже существуют, но называются одинаково и управляются по-разному; часть packaged snapshots устарела; mtime используется там, где нужна explicit identity.

**Target propositions:** `registries` как owner общих reference data; отдельный source catalog; explicit manifest/snapshot ID/hash; Git-authoring + immutable runtime; geography registry; runtime provenance.

**Overlap:** core baseline, Data→Knowledge, artifact/provenance, background source watchers.

**Conflict:** нет; выбор package topology для `sources` остаётся гипотезой до реального consumer.

**Superseded:** mtime как semantic selector; legacy compatibility registry как архитектурный механизм.

**UNKNOWN:** packaged multi-version history, automated updater admission, source status surface.

**Destination:** 03, 05, 08.

---

## 4.11. `stratbox_observability_errors_logs_research_2026-10-07.md`

**Основные сущности:** Case, Job, OperationRun, Attempt, Progress, Diagnostic, terminal outcome, ProblemRef, log/evidence, Condition.

**Current findings:** current core и Windows неоднородно обращаются с exceptions/errors; logs связаны с runs, но не являются единой structured observability model.

**Target propositions:** one execution causal chain; terminal outcomes SUCCESS/PARTIAL/CANCELLED/FAILURE/UNKNOWN; structured progress; physical redacted logs as evidence; AppDock canonical node/platform problem boundary; shared conditions instead of broadcasting raw errors.

**Overlap:** execution control, background jobs, multi-user, AppDock boundary.

**Conflict:** `Case — пользовательская цель` в этом документе позднее переосмысливается Work-oriented исследованиями; problem ownership между Strategy Box domain issue и AppDock platform problem требует точной boundary в теме 08.

**Superseded:** raw traceback as user state; `str(exception)` API; log manager as state truth; timeout==failure.

**UNKNOWN:** exact ProblemDraft→platform bridge contract; retention/support bundle; remote reconciliation timeout.

**Destination:** 04, 05, 08.

---

## 4.12. `stratbox_single_node_multiuser_research_2026-10-07.md`

**Основные сущности:** shared node state, Participant, Session, NodeJob, ResourceLease/Claim, read cursor, Assignment, Notification, shared persistence.

**Current findings:** каждый Windows client сейчас строит собственную local application truth; общий Data root сам по себе не делает систему multi-user.

**Target propositions:** node-authoritative state; clients as projections; resource-level coordination; run-scoped outputs; user-specific read cursors; node-local transactional storage; AppDock identity/session/access integration.

**Overlap:** web/self-hosted, background jobs, observability, settings.

**Conflict:** SQLite vs PostgreSQL не является реальным конфликтом: SQLite предлагается для local single-node authority, PostgreSQL — для server/web profile.

**Superseded:** five JSON files as shared truth; per-client scheduler; shared `unread: bool`; GUI busy flag as node lock.

**UNKNOWN:** collaboration backend API, locking semantics for external/manual file edits, notification rules, multi-device offline behavior.

**Destination:** 04, 05, 07, 08.

---

## 4.13. `stratbox_web_self_hosted_architecture_research_2026-10-07.md`

**Основные сущности:** headless host, browser client, API commands, snapshots/events, authn/authz, server persistence, remote execution.

**Current findings:** web-mode невозможно корректно построить поверх current Windows-owned runtime; нужен долгоживущий server-side owner.

**Target propositions:** `stratbox-host` как headless application runtime; Windows/Web/Android как clients; server API; SSE first; OIDC/capability-first authorization; PostgreSQL server profile, SQLite embedded profile.

**Overlap:** multi-user, background jobs, target core architecture, surfaces.

**Conflict:** с `stratbox_target_core_design_architecture` по физическому имени/границе runtime owner (`stratbox-core` vs `stratbox-host`). Логическая необходимость application runtime не конфликтует; конфликт касается materialization.

**Superseded:** Windows process as canonical runtime; browser closing affecting job; direct filesystem access from thin clients.

**UNKNOWN:** package/repository/process split; API versioning; exact remote/offline model; authentication integration profile.

**Destination:** 01, 05, 07, 08, 09.

---

## 4.14. `Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md`

**Основные сущности:** ChatThread, Work, Case, Job, Attempt, AutomationSpec, TriggerSpec, ExecutionPolicy, JobManager, scheduler, resource leases, transactional truth.

**Current findings:** current BackgroundProcessStore — UI/in-memory scaffold; Qt thread cannot own durable background execution.

**Target propositions:** background is execution mode, not scenario type; one execution spine; headless Strategy Box host owns product scheduler/jobs; AppDock owns host/service lifecycle; Task Center and chat are two projections of the same jobs/automations.

**Overlap:** automation/AI, execution control, multi-user, web/self-hosted, observability.

**Conflict:** explicitly resolves earlier ambiguity about scheduler ownership in favour of Strategy Box application host, not AppDock business scheduling.

**Superseded:** `Scenario.kind=background`; enabled background state as active job; separate background engine; Qt as long-running executor.

**UNKNOWN:** first-release chat sync, holiday calendar provider, host-on-laptop UX, automation sharing, resource budgets, non-atomic FileStore publication, saved automation revalidation after spec updates.

**Destination:** 04, 05, 06, 07, 08, 09.

---

## 4.15. `strategy_box_system_settings_research_2026-10-07.md`

**Основные сущности:** UserSettings, SurfaceState, Recent/DraftState, ManagedPolicy, RunParameters, InterfaceTheme, Artifact defaults, generic plugin settings, notifications.

**Current findings:** current preferences store mixes window geometry, navigation, drafts and settings.

**Target propositions:** very small user settings layer; automatic restoration of surface state; separate draft store; appearance + artifact defaults + generic plugin config; notifications only after actual feature exists.

**Overlap:** visual system, artifact style sets, plugin contract, multi-user/persistence.

**Conflict:** no major contradiction. Exact placement of optional extension activation between application policy and AppDock deployment remains a boundary question.

**Superseded:** “Рабочие”/“Системные” tabs filled with runtime info; manual settings for paths/log level/update channel; UI plugins.

**UNKNOWN:** cross-device preference sync, workspace-level defaults, managed policy precedence.

**Destination:** 05, 06, 07, 08.

---

## 4.16. `strategy_box_interface_visual_system_research_2026-10-07.md`

**Основные сущности:** design tokens, theme, accent, typography, spacing, semantic status colors, component tokens.

**Current findings:** existing UI already approximates desired style but uses hardcoded QSS values.

**Target propositions:** platform-neutral token architecture; system/light/dark; limited accent customization; accessible semantic colors; desktop-specific density retained.

**Overlap:** interface requirements, motion, settings, artifact style sets.

**Conflict:** separate `stratbox-design` repository is not required by this document itself; tokens are a logical responsibility, physical owner unresolved.

**Superseded:** direct per-component color customization; pixel-copy of desktop to Android.

**UNKNOWN:** exact token packaging/owner, accessibility/high-contrast implementation, Android renderer.

**Destination:** 07, 08, 09.

---

## 4.17. `stratbox_windows_motion_animation_research_2026-10-07.md`

**Основные сущности:** MotionRole, MotionSpec, tokens, reduced motion, semantic events, platform adapters.

**Current findings:** current UI has animations but no central motion contract.

**Target propositions:** calm semantic motion; many small transitions, no large decorative animation; motion follows state; platform-neutral roles with native input physics.

**Overlap:** visual system, interface requirements, Android portability.

**Conflict:** none.

**Superseded:** widget-specific magic durations as architecture; animation delaying truth.

**UNKNOWN:** exact shared motion contract owner, toolkit mappings, performance budgets.

**Destination:** 07, 08.

---

## 4.18. `stratbox_windows_interface_requirements_research_2026-10-07.md`

**Основные сущности:** Work surface, Explorer, Scenarios, Runs, scenario chat/timeline, inspector, IA, progressive disclosure.

**Current findings:** current UI has a strong three-zone shell but top-level navigation mixes surfaces with attributes/states.

**Target propositions:** four primary surfaces — Work, Explorer, Scenarios, Runs; collaboration/background/logs as contextual projections; scenario chat becomes conversational work surface; runs become dedicated control plane.

**Overlap:** chat/work research, background jobs, visual/motion, settings.

**Conflict:** “Scenario Chat — central surface” is transitional relative to later `Thread/Work` semantics; scenario should no longer be the sole semantic center.

**Superseded:** six equal top-level modes; separate cascade world; separate background execution world; AI as separate section.

**UNKNOWN:** final navigation after canonical Work/Thread model; mobile IA; search/global command model.

**Destination:** 04, 05, 07.

---

## 4.19. `strategy_box_customization_artifact_style_sets_research_2026-10-07.md`

**Основные сущности:** ArtifactStyleSet, ResolvedArtifactStyleSet, InterfaceTheme, ArtifactMetadataContext, templates/assets, format projections.

**Current findings:** Excel styles-as-data already exist, but model is narrow and format-specific.

**Target propositions:** one effective cross-format ArtifactStyleSet per execution context; style independent from UI theme and metadata; validated/compiled declarative resource; plugins/packages may contribute generic style resources without altering shell UI.

**Overlap:** settings, visual system, artifacts, generic extension model.

**Conflict:** terminology `report profile` vs `ArtifactStyleSet` needs consolidation, but concepts are compatible.

**Superseded:** independent XLSX/DOCX/PPTX theme selection inside one standard run; style as UI skin.

**UNKNOWN:** minimal v1 cross-format role set, template/style separation details, workspace policy precedence.

**Destination:** 03, 06, 07, 08.

---

## 4.20. `stratbox_corporate_plugin_contract_research_2026-10-07.md`

**Основные сущности:** generic extension/plugin ID, versioned API, discovery, activation, capability declaration/binding, conformance, health/readiness.

**Current findings:** public core needs a cleaner environment-neutral extension boundary. Конкретные закрытые implementation details намеренно исключены из настоящего synthesis.

**Target propositions:** discovery separated from activation; explicit binding; fail-closed managed mode; versioned generic plugin API; structured health/errors; conformance suite; no named private coupling in public core/surface.

**Overlap:** portability, settings, machine capabilities, observability.

**Conflict:** none at semantic level. UI management vs AppDock installation boundary needs future finalization.

**Superseded:** implicit “installed means active”; first-wins provider selection; direct import of environment-specific package names from public core.

**UNKNOWN:** exact public API versioning, capability namespace, activation/policy owner, certification profile.

**Destination:** 01, 06, 08, 09.

---

## 4.21. `stratbox_protos_boundary_research_2026-10-07.md`

**Основные сущности:** Strategy Box domain capability, application runtime, external cognitive runtime, compiled fast path, machine-facing boundary.

**Current findings:** Strategy Box remains fully meaningful without any external cognitive system; core business logic must retain domain ownership.

**Target propositions:** external cognitive systems consume curated Strategy Box capabilities, do not own product/domain truth; clean typed observable boundary; separate product runtime from cognitive runtime.

**Overlap:** automation/AI, machine schemes, target semantic decomposition.

**Conflict:** rejects using a universal “design” or “cognitive runtime” layer as owner of unrelated Strategy Box semantics; this weakens physical assertions made in some earlier architecture notes.

**Superseded:** idea that Strategy Box runtime is merely a future cognitive runtime fragment; AI-first product architecture.

**UNKNOWN:** future admission of generated capabilities, exact external-control transport, long-term compilation lifecycle.

**Destination:** 01, 02, 06, 09.

---

## 4.22. `stratbox_protos_foundation_research_2026-10-07.md`

**Основные сущности:** Work Candidate, durable Work, JobManager, Trigger, Authority, revision/freshness fences, artifact/evidence/provenance, external cognitive participant.

**Current findings:** current Cases and operation/scenario contracts are useful seeds, but durable work/state and job control are insufficient.

**Target propositions:** Strategy Box as stable host; cognition optional and replaceable; one JobManager; durable Work; persistence port; effect/authority gateway; bounded context projection.

**Overlap:** execution, multi-user, background, machine readiness.

**Conflict:** `Case already close to Work` is later refined by stronger Work/Case separation. Direction remains useful, identity does not.

**Superseded:** text message as task state; agent classes as fundamental persistence model; separate AI execution stack.

**UNKNOWN:** Work admission semantics, durable Work threshold, authority granularity, context projection model.

**Destination:** 01, 02, 04, 05, 06, 08.

---

## 4.23. `stratbox_protos_business_code_readiness_research_2026-10-07.md`

**Основные сущности:** Capability Definition, Machine Scheme Definition, Activation Binding, ExecutionPlan, Run/Activation State, Capability Envelope, validity/deoptimization.

**Current findings:** API transport alone insufficient for machine reasoning; business code lacks a uniform semantic capability contract.

**Target propositions:** typed semantic capability descriptors; curated registry; effects/idempotency/concurrency/cancellation/recovery/resources/artifacts/provenance; Scheme IR kept small; machine projection derived from canonical Strategy Box semantics.

**Overlap:** machine schemes, portability, automation/AI.

**Conflict:** terminology around Run/Activation vs Job/Attempt remains unsettled; should not be fixed here.

**Superseded:** “AI can understand Python implementation”; tool-only integration; PROTOS-specific schema as canonical Strategy Box truth.

**UNKNOWN:** exact first Scheme IR; admission lifecycle; deoptimization semantics; future external projection.

**Destination:** 02, 04, 06, 08.

---

## 4.24. `stratbox_protos_chat_work_schemes_ui_research_2026-10-07.md`

**Основные сущности:** Thread/Chat, Message, Work, Run, Scheme, CognitiveActivation, Artifact, memory scopes.

**Current findings:** scenario-centric chat model becomes insufficient once free-form long-lived work and multiple concurrent tasks are allowed.

**Target propositions:** user surface becomes thread/chat-centric, internal semantics Work-centric; one Thread can contain many Work; Work can have multiple executions; artifacts return to first-class UI position.

**Overlap:** interface requirements, background jobs, Work semantics, multi-user.

**Conflict:** uses `Run` as central execution instance where other documents use `Job`; external cognitive activation adds another execution term. This is a genuine ontology consolidation task.

**Superseded:** `Chat = Case = execution history`; scenario as sole top-level user object.

**UNKNOWN:** exact Thread↔Work relation, concurrency UX, memory scopes, actor/activation persistence.

**Destination:** 02, 04, 05, 07.

---

## 4.25. `stratbox_madar_target_decomposition_research_2026-10-07.md`

**Основные сущности:** Work, Commission/intent, Result, Acceptance, Closure, knowledge, execution, authority/effects; physical owners as implementation carriers.

**Current findings:** current Strategy Box mixes user work, execution, artifacts and chat more than target semantics allow.

**Target propositions:** responsibility→owner→contract→physical boundary; durable bounded Work; execution separate from Work; acceptance separate from successful computation; one semantic owner can have multiple projections.

**Overlap:** almost entire corpus; acts as high-level semantic synthesis.

**Conflict:** intentionally leaves physical repository count open and therefore softens earlier assertions that specific new repos must exist. It also treats current Case model as insufficiently decomposed.

**Superseded:** mapping semantic responsibilities one-to-one to repositories; treating current package boundaries as architectural truth.

**UNKNOWN:** physical repo count; threshold for independent Work; which Results require Acceptance; richness of Scheme IR; immutable artifact threshold; reconciliation after UNKNOWN effects.

**Destination:** 01, 02, 04, 05, 08, 09.

---

## 4.26. `Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md`

**Основные сущности:** Source, Snapshot, Observation, semantic definition, Claim, Evidence, Result, Basis, Knowledge, currentness, uncertainty, Work/Decision boundary.

**Current findings:** current pipelines often jump too quickly from source/file/DataFrame to artifact without a shared semantic layer describing what is known, inferred, current and applicable.

**Target propositions:** source≠fact; data≠observation≠evidence≠claim; canonical≠true; model output≠fact; artifact≠result; UNKNOWN is valid; historical truth and current reliance differ; representation cannot strengthen meaning.

**Overlap:** Data→Knowledge, registries/sources, artifacts, Work semantics, trust/safety.

**Conflict:** no direct contradiction; this document deliberately pushes abstraction higher than most implementation studies. It should inform canonical semantics, not be copied wholesale into runtime classes.

**Superseded:** “source → dataframe → xlsx” as sufficient product epistemics; “latest file” as full currentness model.

**UNKNOWN:** exact minimal semantic contracts, knowledge storage model, currentness/revalidation implementation, which claims/results warrant explicit acceptance.

**Destination:** 02, 03, 04, 05, 08, 09.

---

## 4.27. `stratbox_target_core_design_architecture_2026-10-07.md`

**Основные сущности:** `stratbox`, common application runtime, design system, Windows/Web/Android surfaces, AppDock.

**Current findings:** Windows already contains application semantics and presentation/common that should move above Qt; core and surfaces are distinct.

**Target propositions:** separate logical owners for domain truth, product/application truth, visual truth and platform rendering; proposes physical components named `stratbox-core` and `stratbox-design`.

**Overlap:** web/self-hosted, visual/motion, portability, target decomposition.

**Conflict:** later research and the third-branch program explicitly warn against creating repositories/packages from a diagram alone. `stratbox-host` also appears as a stronger candidate for long-lived runtime process. Therefore the **logical separation is CONSOLIDATED, physical repo map is TARGET-HYPOTHESIS / partly SUPERSEDED**.

**Superseded:** assertion that a standalone `stratbox-design` repository is already the target. Design-token and presentation ownership remain valid; physical repository is open.

**UNKNOWN:** whether application semantics become `stratbox-core`, live inside `stratbox-host`, or split package/process; whether shared design/presentation semantics need separate distribution.

**Destination:** 01, 07, 09.

---

# 5. Исторический корпус `01-old-notes`: что сохранилось и что вытеснено

Исторические notes полезны как provenance, но не как current authority.

## 5.1. `О приложении Strategy Box.md`

Исторически предполагался отдельный launcher, который сам управляет Git checkout, virtualenv, обновлением repository и запускает UI из `stratbox`.

**SUPERSEDED.** Современная архитектура разделила responsibilities:

```text
AppDock → installation / managed environment / activation / lifecycle
stratbox → domain library
stratbox-windows → Windows application/surface
```

Полезный остаток старой идеи — требование простого пользовательского запуска, понятного bootstrap status и recovery. Реализация через собственный launcher больше не является target.

## 5.2. `Интерфейс Strategy Box.md`

Историческая записка уже содержала messenger-like scenario interface, explorer, background processes, participants, assignments, settings и AppDock integration.

**PARTIALLY PRESERVED.** Эти идеи материализовались в current Windows UI.

**PARTIALLY SUPERSEDED.** Главная рабочая единица больше не должна автоматически быть Scenario; поздние исследования вводят Thread/Work/Runs и отделяют top-level surfaces от attributes/states. Six-mode navigation также заменена более компактной target IA.

## 5.3. `Рефактор бизнес-логики Stratbox.md`

Главная идея — универсальная бизнес-логика как устойчивые предметные operations, пригодные для Jupyter/Colab/application — полностью подтверждена второй веткой.

**CONSOLIDATED.** Особенно устойчивы plan/apply для destructive effects, typed Request/Result, separation domain vs app projection и FRG как pilot нормализации operations.

## 5.4. `Патч stratbox Май 2026.md`

Это исторический implementation journal. Он полезен для происхождения отдельных доменов и решений, но современные baseline-исследования уже точнее отражают current state.

**SUPERSEDED AS CURRENT DESCRIPTION**, но сохраняет provenance.

---

# 6. Канонические понятия: состояние консолидации перед темой 02

Тема 00 не должна окончательно определять онтологию, но обязана показать, где уже есть convergence, а где термины конфликтуют.

| Термин | Current implementation | Состояние Research | Предварительный статус |
|---|---|---|---|
| `SourceDescriptor` | локальные source registries/descriptors | устойчиво повторяется | **CONSOLIDATED concept** |
| `SourceSnapshot` | частично implicit download result/raw file | устойчиво требуется для provenance | **CONSOLIDATED concept** |
| `RegistrySnapshot` | нет общего contract | устойчиво требуется | **CONSOLIDATED direction** |
| `Artifact` | path-oriented metadata в Windows | stable ID/manifest/lineage во многих исследованиях | **CONSOLIDATED direction** |
| `Result` | domain-specific results + OperationResult | должен быть semantic outcome, не file | **CONSOLIDATED concept, schema open** |
| `Capability` | implicit operations/providers | semantic ability + descriptors | **CONSOLIDATED direction** |
| `Operation` | реально существует в Windows и core APIs | canonical machine-callable domain use case | **strong convergence** |
| `Command` | first-class current object отсутствует | technical execution unit в одном исследовании | **CONFLICT / optional term** |
| `Scenario` | current `ScenarioSpec` | user/product workflow definition | **strong convergence** |
| `Cascade` | current composite scenario | separate scenario-composition in one line of research | **open relation to Scheme** |
| `Machine Scheme` | отсутствует current | reusable typed composition/cognitive fast path | **TARGET-HYPOTHESIS, likely needed** |
| `ExecutionPlan` | отсутствует first-class | immutable resolved plan before run | **strong convergence** |
| `Thread/Chat` | UI chat exists, no strong durable semantic object | interaction/context container | **strong target direction** |
| `Work` | first-class current object absent | durable bounded semantic work unit | **strong convergence, exact threshold open** |
| `Case` | current run-like object | user goal, Work projection, or case wrapper in different docs | **genuine conflict** |
| `Job` | no mature current owner | execution unit under Work/Case | **strong convergence** |
| `Run` | used inconsistently | execution occurrence / scheme activation in different docs | **genuine conflict** |
| `OperationRun` | observability proposal | invocation of one operation inside Job | **target candidate** |
| `Attempt` | absent current | retry-specific execution attempt | **strong convergence** |
| `Automation` | scaffold only | durable trigger rule that creates execution | **strong convergence** |
| `Trigger` | absent current | schedule/event/data condition | **strong convergence** |
| `Actor/User/Principal/Session` | partly available via AppDock context | need explicit separation | **CONSOLIDATED direction** |
| `Node` | AppDock concept/current integration | common authority boundary for shared state | **CONSOLIDATED boundary** |
| `Surface` | Windows current, Web/Android future | projection of shared semantics | **CONSOLIDATED concept** |
| `Plugin/Extension` | current extension seams exist | generic versioned capability contribution | **CONSOLIDATED direction** |

Главные semantic conflicts для темы 02: `Command vs Operation`, `Scenario vs Scheme vs Cascade`, `Work vs Case`, `Job vs Run`, `Result vs Artifact`, а также relation между capability definition и executable operation binding.

---

# 7. Устойчивые системные выводы второй ветки

Ниже — тезисы, которые уже можно считать **CONSOLIDATED Research**, хотя они ещё не Product Decisions.

## 7.1. Responsibility before repository

Логическая ответственность определяется раньше package/repository/process. Один semantic owner может иметь несколько projections и физических реализаций. Эта линия поддерживается поздними системными исследованиями и самой программой третьей ветки.

## 7.2. Domain core остаётся headless и independently useful

`stratbox` не должен зависеть от UI, AppDock, Windows, Web, Android или внешней cognition для обычных direct Python/Jupyter use cases.

## 7.3. Application runtime существует как самостоятельная ответственность

Нужен owner для Work/Jobs, orchestration, execution planning, durable state, automations, collaboration projections и client API. Current Windows process не является подходящим долгосрочным owner.

## 7.4. Один execution spine

Manual, foreground, background, schedule, remote, API и AI-triggered запускают одну execution model. Специальные `background engine` и `AI runner` создают архитектурный разрыв.

## 7.5. Durable truth отделена от UI projections

Window state, chat cards и local caches не являются authoritative shared state. Durable execution/work truth должна переживать клиент, restart и смену поверхности.

## 7.6. Artifact выше файла

Физический path является location/materialization detail. Логический результат должен иметь stable identity, metadata, provenance и lifecycle.

## 7.7. Raw source и canonical data различаются

Raw snapshot следует сохранять и адресовать отдельно; parsing/normalization/derived calculation не должны стирать provenance.

## 7.8. Currentness и version identity first-class

`latest` во время исполнения недостаточно. Sources, registries, operations/schemes и saved automations требуют pinned/revalidated revisions.

## 7.9. Errors/UNKNOWN являются данными управления

Expected domain failure, unsupported, permission denied, stale, connectivity loss и unknown effect нельзя схлопывать в generic exception/False/[]/success.

## 7.10. Destructive effects требуют plan/verification

FRG и storage research независимо приходят к plan→inspect→apply, safe commit, resource claims и запрету молчаливого partial success.

## 7.11. External cognition использует canonical capabilities

AI/external cognitive systems не получают privileged обход через shell/Python/filesystem. Они используют те же semantic operations/schemes, policies, approvals, artifacts и audit trail.

## 7.12. Public extension architecture остаётся generic

Public repositories описывают versioned neutral capability contracts и generic extension lifecycle. Environment-specific закрытые реализации не становятся частью публичной product semantics.

## 7.13. Surface semantics выше toolkit

Windows/Android/Web должны использовать общие object/state/action semantics. QThread/QSS/hover/touch/OS open-path остаются adapters.

## 7.14. Settings — не свалка состояния

UserSettings, SurfaceState, Draft/Recent state, Runtime Binding, ManagedPolicy, Automation state и RunParameters имеют разные owners/lifecycles.

## 7.15. Epistemic honesty важнее удобной projection

Source, observation, canonical data, evidence, claim, model output, result, artifact и decision не должны автоматически сливаться. Representation не должна усиливать степень доказанности.

---

# 8. Conflict register

## C1. `Command` vs `Operation`

**Статус:** **CONFLICT / terminology**.

Один документ предлагает `Command` как low-level executable unit и `Scenario` как user operation. Другие исследования устойчиво используют `Operation` как canonical machine-callable domain use case, а low-level mechanics оставляют internal building blocks/services.

**Причина:** разные уровни абстракции, а не разные цели.

**Что делать:** не фиксировать `Command` до темы 02. Вероятный вариант — сохранить `Operation` как канонический use case, а technical command/mechanism оставить internal, если появится реальный consumer.

**Destination:** 02, 04, 06.

## C2. `Scenario` vs `Cascade` vs `Machine Scheme`

**Статус:** **CONFLICT / semantic layering**.

- Scenario стабильно означает authored product workflow/use case.
- Cascade предложен как композиция scenarios.
- Machine Scheme предложен как typed reusable machine composition/fast path.

Неясно, нужны ли Cascade и Scheme одновременно как distinct canonical objects либо Cascade — product projection Scheme.

**Destination:** 02, 04, 06.

## C3. `Work` vs `Case`

**Статус:** **genuine conflict, moving toward resolution**.

Current code: Case ≈ scenario run container.  
Observability: Case ≈ user goal, Job ≈ execution.  
Cognitive/semantic research: Work = durable bounded semantic unit; Case либо projection, либо transitional term.

**Consolidated direction:** Work не должен исчезать вместе с конкретным execution. Current `ScenarioRunCase` не способен быть полной semantic model.

**Destination:** 02, 04, 05.

## C4. `Job` vs `Run`

**Статус:** **CONFLICT / naming**.

Некоторые исследования используют Job как durable executable unit, Run как specific execution/activation; другие почти наоборот. Attempt обычно стабильно означает retry attempt.

**Destination:** 02, 04, 08.

## C5. `stratbox-core` vs `stratbox-host`

**Статус:** **TARGET-HYPOTHESIS / physicalization conflict**.

Логическая application responsibility устойчива. Одни исследования называют её `stratbox-core`; web/background исследования выделяют `stratbox-host` как long-lived service/runtime.

Возможная синтезирующая модель:

```text
application semantics package
        ↓
headless host/service process
```

но это пока не решение.

**Destination:** 01, 05, 09.

## C6. Отдельный `stratbox-design`

**Статус:** **PARTLY SUPERSEDED**.

Logical design system/tokens/motion/presentation semantics нужны. Отдельный repository был предложен в одной архитектурной записке, но поздние исследования и программа третьей ветки специально запрещают физические границы без реальной необходимости.

**Destination:** 01, 07, 09.

## C7. Scheduler owner: AppDock или Strategy Box

**Статус:** **RESOLVED BY LATER RESEARCH**.

Раннее automation research помещало scheduler/job manager в AppDock node/host runtime. Более поздние web/background исследования чётче разделяют:

```text
AppDock: process/service/node lifecycle, readiness, remote/platform boundary
Strategy Box application host: product Automation/Trigger/Job semantics
```

Эту позднюю модель следует считать текущим consolidated research direction.

**Destination:** 01, 04, 06, 09.

## C8. SQLite vs PostgreSQL

**Статус:** **NOT A CONFLICT**.

SQLite/WAL — local single-node/embedded authority на локальном диске; PostgreSQL — server/web/multi-client deployment. Нужен единый persistence port и одинаковая semantics/migrations.

**Destination:** 05, 08.

## C9. Scenario-first UI vs Thread/Work-first UI

**Статус:** **EVOLUTION / PARTLY SUPERSEDED**.

Current app закономерно scenario-first. Поздние исследования показывают, что при free-form work/AI/background/multi-tasking пользовательский контекст становится Thread/Work-centric, а Scenario — capability/workflow selection inside it.

**Destination:** 02, 04, 07.

## C10. Immediate CAS vs minimal architecture

**Статус:** **TARGET-HYPOTHESIS**.

Artifact research рекомендует сразу небольшой content-addressed layer. Общая программа требует избегать premature infrastructure. Требуется pilot и workload evidence.

**Destination:** 03, 05, 08.

---

# 9. Superseded register

| Ранняя идея | Статус | Чем вытеснена |
|---|---|---|
| UI и launcher внутри/рядом с `stratbox` | **SUPERSEDED** | separate `stratbox-windows` + AppDock-managed lifecycle |
| AppDock владеет предметным scheduler Strategy Box | **SUPERSEDED** | AppDock lifecycle; Strategy Box host owns product automations/jobs |
| Каждый Operation автоматически становится Scenario | **SUPERSEDED** | curated user scenarios, canonical operations remain machine/domain layer |
| `Scenario.kind=background` как отдельный execution type | **SUPERSEDED** | background = activation/execution mode |
| Один Qt `QThread` как execution owner | **SUPERSEDED target** | frontend-neutral JobManager/headless owner |
| Local JSON history как durable/shared truth | **SUPERSEDED target** | transactional node/server persistence |
| Six equal top-level Windows modes | **SUPERSEDED target** | Work/Explorer/Scenarios/Runs-style IA |
| Chat/Scenario/Case как одна сущность | **SUPERSEDED** | Thread, Work, Job/Run, artifacts separated |
| Path как artifact identity | **SUPERSEDED** | ArtifactRef/manifest/content identity direction |
| mtime как registry freshness/selection identity | **SUPERSEDED** | explicit manifest/snapshot/hash |
| “latest” lookup during run as reproducibility | **SUPERSEDED** | pinned snapshot/revision + revalidation |
| Raw traceback/exception as user-visible error contract | **SUPERSEDED** | structured failure/problem + evidence refs |
| Retry как generic `N times` | **SUPERSEDED** | effect/idempotency-aware retry policy |
| Timeout/connectivity loss == failure | **SUPERSEDED** | UNKNOWN/reconciliation |
| Plugin installed == active | **SUPERSEDED** | discovery ≠ activation, explicit binding/policy |
| UI plugin can inject arbitrary shell widgets/styles | **REJECTED** | app-owned interface theme/presentation; extensions contribute bounded capabilities/resources |
| Separate AI-only operations/scenarios | **REJECTED** | same canonical capabilities for human/automation/AI |
| Separate background engine | **REJECTED** | one execution spine |
| `stratbox-design` as already-decided separate repo | **SUPERSEDED AS PHYSICAL DECISION** | logical design responsibility retained; physical boundary open |

---

# 10. UNKNOWN / White Spot Register

Ниже собраны вопросы, которые третья ветка должна активно разрешать. Они сгруппированы по системной ответственности, а не по исходным файлам.

## 10.1. Semantics and ontology

| Вопрос | Почему открыт | Destination |
|---|---|---|
| Canonical relation `Capability → Operation → Scenario → Scheme/Cascade` | термины наложились в разных исследованиях | 02, 06 |
| Нужен ли first-class `Command` | current consumer отсутствует | 02, 04 |
| `Work` vs `Case` | current Case run-like; target Work durable | 02, 04, 05 |
| `Job` vs `Run` | разная терминология | 02, 04 |
| Exact meaning of `Attempt` / `OperationRun` | нужна единая execution state machine | 02, 04, 08 |
| Result vs Artifact | направление ясно, schema нет | 02, 03 |
| Dataset/Observation/Claim/Evidence boundaries | semantic target есть, минимальный runtime contract нет | 02, 03 |
| Which Results require Acceptance | зависит от Work/authority semantics | 02, 04, 08 |
| Threshold for independent durable Work | ещё нет use-case rule | 02, 04, 05 |

## 10.2. Logical/physical ownership

| Вопрос | Почему открыт | Destination |
|---|---|---|
| `stratbox-core` package нужен ли вообще | logical owner нужен, physical split не доказан | 01, 09 |
| `stratbox-host` — repo/package/process? | web/background требуют long-lived runtime | 01, 05, 09 |
| Shared application client package | Windows/Android reuse растёт, но отдельный repo может быть преждевременным | 01, 07, 09 |
| Separate design package/repo | logical tokens нужны, physical owner не доказан | 01, 07, 09 |
| Artifact service/catalog physical owner | core vs application host boundary требует уточнения | 01, 03, 05 |

## 10.3. Persistence and state

| Вопрос | Почему открыт | Destination |
|---|---|---|
| Canonical durable state schema | current JSON непригоден, target models ещё меняются | 05 |
| Migration strategy | saved Work/Automation/Artifacts должны переживать upgrades | 05, 08 |
| Local DB vs server DB profile contract | engines понятны, abstraction/conformance нет | 05, 08 |
| Atomic multi-entity transactions | jobs/events/artifacts/assignments связаны | 05, 08 |
| Backup/recovery boundary | AppDock и Strategy Box responsibilities не сведены | 05, 08 |
| Retention | logs/artifacts/history/notifications имеют разные lifecycles | 05, 08 |
| Search/indexing | Work/artifacts/history должны быть discoverable | 05, 07 |
| Offline/reconnect semantics | особенно для Android/Web/remote | 05, 07, 08 |

## 10.4. Execution and reliability

| Вопрос | Почему открыт | Destination |
|---|---|---|
| Exact execution state machine | statuses scattered across studies | 04, 08 |
| Resource claim vocabulary | files/cache/source/output vs generic resources | 04, 08 |
| Effect reconciliation after UNKNOWN | destructive/remote operations require per-effect rules | 04, 08 |
| Idempotency identity | operation/scheme/job/request scopes need alignment | 04, 08 |
| Resume/checkpoint semantics | cannot be generic step index | 04, 08 |
| Cancellation capability matrix | not every operation is cancellable | 04, 08 |
| Worker/process isolation | required for hard cancellation and long work | 04, 08 |
| Resource budgets | CPU/RAM/network/storage depend on device profile | 08 |
| Business-day calendar provider | needed by scheduler; owner unresolved | 06, 08 |

## 10.5. Data → Knowledge

| Вопрос | Почему открыт | Destination |
|---|---|---|
| Minimal SourceSnapshot contract | proposed repeatedly, not yet canonical | 03 |
| Registry version lifecycle | updater/admission/history unresolved | 03, 08 |
| Geography ownership | several domains have local topology | 03 |
| Artifact immutability threshold | not every file should be managed artifact | 03, 05 |
| CAS necessity | promising, not yet validated by pilot | 03, 08 |
| Canonical dataset identity | needed for lineage/search, currently domain-local | 03 |
| Claim/evidence storage | target epistemics outpaces implementation | 03, 05 |
| Currentness/revalidation | version identity exists conceptually, mechanism open | 03, 08 |
| Artifact retention/materialization | client/host/storage implications | 03, 05, 08 |

## 10.6. Extension / capability architecture

| Вопрос | Почему открыт | Destination |
|---|---|---|
| Plugin API v1 exact scope | principles defined, types not fixed | 06, 08 |
| Capability namespace/IDs | machine discovery needs stability | 02, 06 |
| Discovery/activation policy owner | AppDock deployment vs Strategy Box activation | 06, 09 |
| Conformance/certification surface | direction clear, harness absent | 06, 08 |
| Scheme admission lifecycle | future generated/third-party schemes need governance | 06, 08 |
| Exact Scheme IR | minimum nodes/conditions/loops still open | 02, 06 |
| External AI/cognitive transport | MCP/API/local call are adapters, canonical semantics separate | 06 |

## 10.7. Collaboration / authority

| Вопрос | Почему открыт | Destination |
|---|---|---|
| Principal/User/Actor/Session model | identity layers not fully canonical | 02, 05 |
| Permission/effect model | must cover cancel/retry/destructive/AI/remote | 05, 08 |
| Shared vs personal Work visibility | node collaboration without accidental publicness | 05, 07 |
| Automation sharing/journals | owner/watchers/audience unresolved | 05, 06 |
| Notification semantics | audience/severity/ack/push rules | 05, 07, 08 |
| Assignments/approvals | current local scaffold, durable multi-user semantics open | 05, 07 |
| Presence provider | UI model exists, authoritative source absent | 05, 07 |

## 10.8. Product surfaces

| Вопрос | Почему открыт | Destination |
|---|---|---|
| Final Work/Thread navigation | current scenario-centric UI will change after ontology | 07 |
| Mobile IA | Android should not shrink desktop | 07 |
| Surface contract package | shared semantics exist, physical owner open | 01, 07, 09 |
| Accessibility | themes/motion consider it, full contract absent | 07, 08 |
| Localization | largely unresearched | 07, 08 |
| Global search / command discovery | not consolidated | 07 |
| Artifact preview strategy | formats/remote/mobile vary | 03, 07 |

## 10.9. Operability / engineering governance

| Вопрос | Почему открыт | Destination |
|---|---|---|
| Contract/version compatibility policy | project rejects legacy shims, but persisted definitions still need revalidation | 08 |
| CI across repos | baseline lacks mature automation | 08 |
| Contract tests between core/surface/AppDock | version drift already real | 08 |
| Support bundle | logs/evidence/redaction boundaries not implemented | 08 |
| Performance benchmarks | only some subsystems have gates | 08 |
| Schema compatibility test matrix | needed for persisted Work/Automation/artifacts | 08 |

---

# 11. Apparent conflicts that are actually scope differences

## 11.1. SQLite vs PostgreSQL

Это не architectural fork. Embedded/local node может использовать SQLite на локальном диске; server/web host — PostgreSQL. Главное требование: одинаковые application semantics, repositories и migrations.

## 11.2. Windows vs Web vs Android

Нет конфликта «какой frontend главный». Windows — текущая реализация; Web и Android — будущие surfaces. Shared semantics должны быть platform-neutral, rendering — platform-specific.

## 11.3. FileStore vs Artifact Store

FileStore не заменяется Artifact layer. Они принадлежат разным уровням:

```text
physical bytes/paths
→ managed content
→ artifact identity/manifest
→ semantic result/provenance
```

## 11.4. AppDock observability vs Strategy Box observability

Core/application должны генерировать structured domain/execution diagnostics. AppDock остаётся owner platform/node problem institution. Это layered integration, а не два конкурирующих error systems.

## 11.5. Generic extension vs settings

AppDock может управлять installation/deployment; Strategy Box может отображать compatible extensions и разрешённую application-level activation/configuration. Эти функции не обязаны жить в одном UI/owner.

---

# 12. Dependency map между будущими исследованиями 01–09

Программа третьей ветки правильно задаёт порядок: последующие темы реально зависят от результатов предыдущих.

```text
00 Corpus Map
   ↓
01 System Model / Ownership
   ↓
02 Canonical Semantic Model
   ├───────────────┐
   ↓               ↓
03 Data→Knowledge  04 Work→Execution
   │               │
   └──────┬────────┘
          ↓
05 State / Persistence / Collaboration
          ↓
06 Capabilities / Extensions / Automation
          ↓
07 Product Surfaces
          ↓
08 Trust / Safety / System Qualities
          ↓
09 Whole-System Target Architecture
```

На практике 06–08 будут давать обратные ограничения на 02–05. Это нормально: порядок задаёт initial dependency, а не запрещает итерацию.

---

# 13. Consolidation destination по каждому файлу

| Research | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Core current state | ● | ● | ● |  |  | ● |  | ● | ● |
| Windows current state | ● | ● |  | ● | ● |  | ● | ● | ● |
| File/artifact layer |  | ● | ● |  | ● |  |  | ● | ● |
| Automation/AI |  |  |  | ● | ● | ● |  | ● |  |
| Commands/scenarios/cascades |  | ● |  | ● |  | ● | ● |  |  |
| Execution control/user path |  | ● |  | ● | ● |  |  | ● |  |
| FileStore/formats |  |  | ● |  |  |  |  | ● | ● |
| Portability/reuse | ● | ● |  | ● |  | ● |  | ● |  |
| Machine schemes |  | ● |  | ● |  | ● |  | ● |  |
| Registry/source governance |  |  | ● |  | ● |  |  | ● |  |
| Observability/errors/logs |  |  |  | ● | ● |  |  | ● |  |
| Single-node multi-user |  |  |  | ● | ● |  | ● | ● |  |
| Web/self-hosted | ● |  |  |  | ● |  | ● | ● | ● |
| Background jobs/processes |  |  |  | ● | ● | ● | ● | ● | ● |
| System settings |  |  |  |  | ● | ● | ● | ● |  |
| Interface visual system |  |  |  |  |  |  | ● | ● | ● |
| Motion/animation |  |  |  |  |  |  | ● | ● |  |
| Interface requirements |  |  |  | ● | ● |  | ● |  |  |
| Artifact style sets |  |  | ● |  |  | ● | ● | ● |  |
| Generic corporate extension contract | ● |  |  |  |  | ● |  | ● | ● |
| External cognition boundary | ● | ● |  |  |  | ● |  |  | ● |
| External cognition foundation | ● | ● |  | ● | ● | ● |  | ● |  |
| Business-code machine readiness |  | ● |  | ● |  | ● |  | ● |  |
| Chat/Work/Schemes UI |  | ● |  | ● | ● |  | ● |  |  |
| Target semantic decomposition | ● | ● |  | ● | ● |  |  | ● | ● |
| Target epistemic architecture |  | ● | ● | ● | ● |  |  | ● | ● |
| Target core/design architecture | ● |  |  |  |  |  | ● |  | ● |

`●` означает, что документ является существенным input, а не что весь его текст должен быть перенесён в соответствующий synthesis.

---

# 14. Что именно должна решить каждая следующая тема

## 14.1. Тема 01 — Strategy Box System Model

Должна зафиксировать logical responsibilities и ownership boundaries, не создавая автоматически новые repos. Основной unresolved block: relation domain library ↔ application semantics ↔ headless host/process ↔ clients ↔ AppDock.

Нужно особенно осторожно разобрать `stratbox-core`/`stratbox-host` и решить, является ли это двумя физическими компонентами, package+process одной системы или временными исследовательскими названиями.

## 14.2. Тема 02 — Canonical Semantic Model

Это самый важный следующий шаг. Здесь следует снять конфликт:

```text
Capability
Operation / Command
Scenario
Cascade / Scheme
ExecutionPlan
Thread
Work
Case
Job
Run
OperationRun
Attempt
Result
Artifact
Automation
Trigger
Actor / Principal / Session / Node
```

Без этого темы 04–06 будут продолжать использовать разные слова для одних объектов.

## 14.3. Тема 03 — Data → Knowledge

Нужно соединить FileStore/formats/sources/registries/artifacts с эпистемическими distinctions:

```text
SourceDescriptor
→ SourceSnapshot
→ Observation/Dataset
→ semantic definition
→ derived/inference
→ evidence/claim/result
→ artifact projection
→ lineage/currentness
```

Ключевой unresolved: минимальная модель без превращения Strategy Box в тяжёлую knowledge graph platform.

## 14.4. Тема 04 — Work → Execution

Нужно построить единую state machine и ответить, что именно порождает что:

```text
Intent/Work
→ capability/workflow selection
→ ExecutionPlan
→ Job/Run
→ OperationRun
→ Attempt
→ terminal outcome
```

Здесь же — cancellation, retry, resume, progress, resource claims, idempotency.

## 14.5. Тема 05 — State / Persistence / Collaboration

Должна определить durable truth: scopes, lifetimes, DB profiles, schema migration, recovery, user state, shared node state, read cursors, notification/assignment/presence projections, artifact metadata and Work persistence.

## 14.6. Тема 06 — Capability / Extension / Automation

Должна свести operation registry, scenarios/schemes, generic extensions, automation/trigger, execution backends и external AI exposure в одну capability architecture. Никакой отдельной AI-only capability universe.

## 14.7. Тема 07 — Product Surface Architecture

Должна проектировать Windows/Web/Android после stabilizing Work/Execution semantics. Иначе surface снова начнёт владеть терминами, которые ещё меняются.

## 14.8. Тема 08 — Trust / Safety / System Qualities

Должна превратить повторяющиеся локальные правила в system-wide invariants: error truth, unknown effects, destructive safety, idempotency, concurrency, migrations, compatibility, observability, security, accessibility, resource budgets, tests.

## 14.9. Тема 09 — Whole-System Target Architecture

Должна материализовать logical/physical architecture только после тем 01–08. Если к тому моменту остаётся вопрос `stratbox-core` vs `stratbox-host`, он фиксируется как unresolved decision, а не замазывается новой схемой.

---

# 15. Предварительные system-wide invariants, уже поддержанные корпусом

Это ещё не финальный набор темы 08, но следующие инварианты повторяются достаточно часто, чтобы считать их сильными candidate invariants.

1. Transport/backend failure не маскируется как empty result.
2. UI не является authority durable Work/Job state.
3. Closing a client не является cancellation.
4. Foreground/background/scheduled/remote/AI execution использует один execution model.
5. Late cancel request не переписывает уже committed terminal success.
6. Unknown external effect остаётся UNKNOWN до reconciliation.
7. Retry допускается только при определённой idempotency/effect semantics.
8. Destructive action не может молча завершиться частично.
9. Path не является artifact identity.
10. Committed managed artifact не мутирует незаметно; изменение создаёт новую identity/version.
11. Source snapshot и canonical/derived result имеют разную identity.
12. Registry/source version участвует в provenance.
13. Representation/UI не имеет права усиливать semantic confidence/evidence.
14. Public core не знает concrete private environment implementation.
15. Installed extension не означает active extension.
16. Machine/AI actor не получает больше authority, чем разрешено capability/policy layer.
17. Raw logs/tracebacks являются evidence, а не пользовательской state truth.
18. Shared node state не хранит персональный unread как global field.
19. Resource conflicts координируются на уровне ресурсов, а не глобальным “one job at a time”.
20. Platform-specific UI toolkit не владеет application execution semantics.

---

# 16. Current implementation gaps, которые уже требуют Product/Engineering attention независимо от target architecture

Эти пункты не являются speculative target questions; они подтверждены current baseline.

## 16.1. Version drift core ↔ Windows

Windows package и AppDock manifest всё ещё фиксируют старую core package version, тогда как current core значительно ушёл вперёд. Это прямой contract risk.

## 16.2. Public/private boundary hygiene

Public packaging/runtime metadata всё ещё содержит environment-specific coupling. Целевой generic extension contract исследован, но cleanup ещё не выполнен.

## 16.3. Windows contract/docs/tests drift

Current baseline фиксирует несовпадение manifest contract и части tests/docs.

## 16.4. Generated files tracked in Windows repository

`.tmp`, `__pycache__`/`.pyc` и связанные hygiene problems остаются в baseline snapshot.

## 16.5. Test/CI imbalance

Core имеет сильные tests в нескольких mature domains, но системное покрытие uneven; Windows coverage узкое; CI/release automation недостаточна.

## 16.6. Registries freshness

Packaged bank/classifier snapshots требуют formal update/freshness lifecycle.

## 16.7. FileStore error semantics

Current ecosystem содержит места, где exception/empty/not-found/unavailable смешиваются. Это нарушает будущие Work/Job/Artifact semantics и требует раннего исправления.

## 16.8. Current background/presence/assignments UI ahead of backend

Surface показывает будущие concepts раньше, чем существует authoritative node runtime. Следующая implementation phase должна либо довести engine, либо маркировать функции как preview, чтобы UI не обещал лишнего.

---

# 17. Decision / Gap Register темы 00

| Объект | Статус темы 00 | Комментарий |
|---|---|---|
| `stratbox` как independent domain library | **Устойчиво** | подтверждено current code и всем поздним corpus |
| platform-neutral application owner | **Устойчиво** | физическое размещение открыто |
| headless durable execution runtime | **Вероятная target direction** | особенно усилено Web/background research |
| `stratbox-host` как отдельный repo | **UNKNOWN / Target** | responsibility доказана, repo — нет |
| `stratbox-core` как отдельный repo | **UNKNOWN / Target** | может оказаться package semantics, а не repo |
| separate design repo | **Не подтверждено** | logical design system yes; physical repo open |
| canonical Operation | **Устойчиво** | exact descriptor schema open |
| first-class Command | **Conflict/Open** | возможно internal technical term |
| Scenario | **Устойчиво** | product workflow/use case |
| Cascade | **Open** | relation to Scheme unresolved |
| Machine Scheme | **Вероятная target direction** | exact IR open |
| ExecutionPlan | **Устойчивое направление** | exact schema open |
| Thread/Chat | **Устойчивое направление** | interaction context, not execution truth |
| Work | **Устойчивое направление** | exact admission/boundary open |
| Case | **Conflict** | current implementation term overloaded |
| Job | **Устойчивое направление** | relation to Run needs canonical naming |
| Run | **Conflict** | used differently across corpus |
| Attempt | **Устойчивое направление** | retry-level execution identity |
| Artifact as stable logical entity | **Устойчиво** | CAS/catalog implementation open |
| CAS immediately | **Target hypothesis** | pilot required |
| SourceSnapshot / RegistrySnapshot | **Устойчиво** | schemas open |
| one execution spine | **Устойчиво** | system-wide invariant candidate |
| Strategy Box owns product scheduler | **Устойчиво после уточнения** | AppDock owns service lifecycle |
| SQLite embedded / PostgreSQL server | **Compatible profiles** | persistence port/migrations open |
| generic public extension protocol | **Устойчиво** | v1 contract open |
| private implementation details in public repos | **Запрещено** | boundary invariant |
| Windows/Web/Android shared semantics | **Устойчиво** | physical shared package open |
| AI as capability consumer, not new core | **Устойчиво** | transport/admission open |
| epistemic distinctions | **Устойчивое target direction** | minimal runtime model open |

---

# 18. Рекомендуемый старт темы 01 после этой карты

Следующее исследование не должно начинаться с рисования новых repositories. Оно должно взять только устойчивые logical responsibilities:

```text
Strategy Box
├─ domain/business capability ownership
├─ product/application semantics
├─ execution/work ownership
├─ data/knowledge ownership
├─ artifact ownership
├─ user/collaboration state
├─ surface semantics
└─ external platform boundary
```

Для каждой ответственности следует ответить:

```text
что является truth;
кто имеет authority её менять;
какие contracts она публикует;
какие другие owners от неё зависят;
должна ли она жить без UI;
должна ли переживать client restart;
нужен ли отдельный lifecycle/process;
```

Только после этого допустимо обсуждать `stratbox-core`, `stratbox-host`, shared client package или design package как физические решения.

---

# 19. Финальный вывод

Корпус второй ветки уже достаточно зрел, чтобы перестать добавлять новые локальные концепции без общей semantic проверки. Его проблема теперь не в недостатке идей, а в **избыточном количестве пересекающихся языков для почти одной и той же будущей системы**.

Важнейший результат темы 00 можно сформулировать так:

> **Strategy Box уже имеет устойчивый архитектурный позвоночник, но ещё не имеет единого канонического словаря и окончательной физической нарезки. Следующая стадия должна консолидировать смысл, ownership и state/execution contracts, а не увеличивать число abstractions и репозиториев.**

На уровне research уже просматривается одна система:

```text
external sources / registries
        ↓
raw snapshots → canonical data → evidence / results
        ↓
canonical capabilities / operations
        ↓
scenario / scheme selection
        ↓
durable Work
        ↓
resolved ExecutionPlan
        ↓
Job / OperationRun / Attempt
        ↓
progress / diagnostics / terminal outcome
        ↓
Artifacts + provenance
        ↓
shared durable state
        ↓
Windows / Web / Android projections
        ↓
AppDock-managed node / lifecycle / remote boundary
```

Но несколько названий внутри этой схемы всё ещё provisional. Именно поэтому тема 02 должна предшествовать финальной архитектуре, а тема 01 должна сначала определить responsibilities, не package names.

Тема 00 считается закрытой, если этот файл используется как вход для 01–09 и при каждом следующем synthesis соблюдаются три правила:

1. не возвращать superseded решения без новой фактической причины;
2. не превращать target hypothesis в current fact;
3. каждый новый объект обязан либо закрывать один из перечисленных UNKNOWN, либо быть доказан новым implementation/use-case probe.

---

# 20. Source ledger Strategy Box

## Program / branch control

- `_mw/epochs-001-strategy-box-development/research/strategy_box_03_consolidation_research_program.md`
- `_mw/epochs-001-strategy-box-development/research/03-consolidation-research/README.md`
- `_mw/epochs-001-strategy-box-development/research/02-base-study/README.md`

## `02-base-study`

- `Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md`
- `Strategy_Box_target_MADAR_epistemic_architecture_research_2026-10-07.md`
- `stratbox-windows_current_state_full_research_2026-10-06.md`
- `stratbox_base_study_current_state_2026-10-06.md`
- `stratbox_business_logic_machine_schemes_architecture_research_2026-10-07.md`
- `stratbox_business_segments_portability_reuse_architecture_research_2026-10-07.md`
- `stratbox_commands_scenarios_cascades_research_2026-10-07.md`
- `stratbox_corporate_plugin_contract_research_2026-10-07.md`
- `stratbox_execution_control_user_path_research_2026-10-07.md`
- `stratbox_file_artifact_layer_research_2026-10-06.md`
- `stratbox_filestore_file_formats_research_2026-10-07.md`
- `stratbox_madar_target_decomposition_research_2026-10-07.md`
- `stratbox_observability_errors_logs_research_2026-10-07.md`
- `stratbox_protos_boundary_research_2026-10-07.md`
- `stratbox_protos_business_code_readiness_research_2026-10-07.md`
- `stratbox_protos_chat_work_schemes_ui_research_2026-10-07.md`
- `stratbox_protos_foundation_research_2026-10-07.md`
- `stratbox_registry_source_governance_research_2026-10-07.md`
- `stratbox_single_node_multiuser_research_2026-10-07.md`
- `stratbox_target_core_design_architecture_2026-10-07.md`
- `stratbox_web_self_hosted_architecture_research_2026-10-07.md`
- `stratbox_windows_interface_requirements_research_2026-10-07.md`
- `stratbox_windows_motion_animation_research_2026-10-07.md`
- `strategy_box_automation_ai_research_2026-10-06.md`
- `strategy_box_customization_artifact_style_sets_research_2026-10-07.md`
- `strategy_box_interface_visual_system_research_2026-10-07.md`
- `strategy_box_system_settings_research_2026-10-07.md`

## `01-old-notes` — historical only

- `Интерфейс Strategy Box.md`
- `О приложении Strategy Box.md`
- `Патч stratbox Май 2026.md`
- `Рефактор бизнес-логики Stratbox.md`

## Implementation verification

- `ForestTiger-GH/stratbox`, `main`; current HEAD `ea1dc8b933d5a07cd5b24d40720af7a430029280` at the time of research.
- baseline implementation commit `e968853572676d8e5d963607d1f0cb50ff8f20b7`; subsequent compared changes do not modify `src/` or `tests/`.
- `ForestTiger-GH/stratbox-windows`, `main`; current HEAD `959e9c4ce1441124af5111c1e025041714e04d3b`, matching the baseline research snapshot.
- AppDock product description used only for the external platform boundary; detailed external-project internals are outside this file.

---

**End of Research Synthesis — Topic 00.**
