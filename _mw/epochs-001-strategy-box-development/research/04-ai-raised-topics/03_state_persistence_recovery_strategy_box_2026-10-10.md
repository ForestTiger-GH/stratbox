# 03. Strategy Box — состояние, сохранность и восстановление

**Дата:** 10 октября 2026 года  
**Тип:** самостоятельное исследование / архитектурное предложение  
**Источник темы:** `Strategy_Box_Research_Topics(2).docx`, тема 03, стр. 2  
**Актуальные code baselines:** `ForestTiger-GH/stratbox@beb3e4842614b153ba0c0ccc1e33ae4d50698821`; `ForestTiger-GH/stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b`; `ForestTiger-GH/AppDock@a4d87c643e620e54e04083d4d0b8d867513e7065` (контракты интеграции, не продуктовый код Strategy Box)  
**Статус вывода:** исследовательский, продуктовые решения о СУБД, RPO/RTO, составе долговечной истории и конфигурации хоста ещё предстоят.  
**Изменения:** отсутствуют; документ создан вне репозиториев.  
**Публичность:** только нейтральные сведения о публичных компонентах и внешнем контракте AppDock. Описание закрытых реализаций расширений исключено.

> **Главный результат.** Для Strategy Box следует зафиксировать **классы состояния, владельцев, модель подтверждения записи и восстановления до выбора физической СУБД**. AppDock должен предоставлять управляемое размещение и, в будущем, проверяемые storage/data-plane capabilities; Strategy Box определяет предметные записи и переходы состояний. На ближайшем этапе вполне допустим файловый вариант **без SQLite**, при условии одного владельца записи, атомарных файлов и явного ограничения гарантий. SQLite — кандидат следующего шага, а не обязательная отправная точка. Для совместного узла пользователи общаются с единым application authority; они не открывают общую БД или JSON напрямую.

---

## 0. Постановка и точное чтение комментария разработчика

В приложенном DOCX тема 03 сформулирована как исследование классов состояния — **настроек, рабочих областей, заданий, истории, результатов и системных индексов** — с сопоставлением локального режима, общего узла и вероятного удалённого доступа **без преждевременного выбора СУБД**. Наводящие вопросы: что сохраняется долговременно, что можно пересчитать или загрузить заново; где находятся границы атомарности, резервирования и восстановления.

Из комментария разработчика следуют три особенно важных положения:

1. **[ПОТРЕБНОСТЬ]** Приоритет — небольшой, технологически понятный и надёжный контур, который избавит продукт от регулярных проблем потери/повреждения рабочего состояния.
2. **[ПОЖЕЛАНИЕ]** Решение должно расти без разрушительной перестройки модели. Это не требование сразу внедрить серверную БД, распределённый журнал или полную автоматическую реконструкцию всего исполнения.
3. **[ОТКРЫТО]** Конкретный движок хранения и распределение реализации с AppDock требуют самостоятельной инженерной проверки. Замечание об атомарности отсылает к теме 02: прерывание обычно завершает выполняемый процесс, а действия с важными файлами должны иметь короткую и безопасную границу публикации.

**Дополнительное уточнение от 10.10.2026:** SQLite или альтернативное хранилище должны **предоставляться/конфигурироваться через AppDock** (возможно будущий Data plane); в ближайшей версии может понадобиться **переходный вариант без SQLite**. Это уточнение меняет приоритет: сначала нейтральный persistence contract, управляемые каталоги и минимальные гарантии, затем backend по зрелости AppDock и реальной потребности.

### 0.1. Что принято, что предложено

| Статус | Положение |
|---|---|
| **Факт текущей реализации** | Windows history сохраняется в пяти JSON; настройки — в `app.json`; есть файловая рабочая область и отдельные AppDock session/runtime projections. |
| **Установленная продуктовая потребность** | Сохранять жизненно важные данные и пользовательский контекст, без ложных «успешных» состояний и без регулярной потери истории при сбоях. |
| **Установленное архитектурное ограничение** | AppDock остаётся внешним владельцем installation/node/session и предоставляемой среды; `stratbox` — независимым аналитическим ядром; UI — клиентом продуктового состояния. |
| **Пожелание разработчика** | Простота сейчас, расширяемость позже; закрытие приложения обычно прекращает локальное выполнение, но позволяет видеть незавершённое и предложить повтор. |
| **Целевое предложение этого исследования** | Единый логический StateStore/authority, файловый backend без SQLite на первом этапе, позднее AppDock-managed SQLite/серверный backend при подтверждённых capabilities. |
| **Нерешённое решение** | Где будет работать постоянный state-owner на хосте, какое API AppDock реально предоставит, сроки общей многопользовательской истории, RPO/RTO, срок хранения. |

### 0.2. Важное ограничение исследования

Технические конструкции в этом документе — **варианты будущих контрактов**, а не описание уже готовой функции AppDock, backend-а или существующей общей БД. Статические проверки текущего кода не доказывают поведение конкретной установленной сборки при внезапном отключении питания. Такое поведение должно подтверждаться испытаниями на файловой системе и ОС целевой поставки.

---

## 1. Краткий ответ: минимально достаточная модель

Смысловая архитектура должна выглядеть так:

```text
AppDock
  ├─ установка / узел / активация / сеансы / средовые каталоги
  ├─ DataBinding и размещение рабочих файлов
  └─ [БУДУЩЕЕ] provider contract для надёжного state storage
                │
                │ versioned activation / capability boundary
                ▼
Strategy Box application authority (логический, один на область состояния)
  ├─ приём пользовательских изменений / ревизии / идемпотентность
  ├─ Work, чат, Run/Job, история, поручения, каталог результатов
  ├─ product state + validation + recovery/reconciliation
  ├─ StateStore Port  ─────► AtomicFiles / SQLite / PostgreSQL adapter
  └─ Artifact/FileStore Port ─► AppDock-bound Data root / storage backend
                ▲
                │ commands, snapshots, notifications
      Windows / Web / Android / разрешённый агент

stratbox core ── операции, доменная семантика и provenance, без зависимости от GUI/AppDock
```

Смысл слова **authority**: есть одна принимающая сторона, имеющая право записать окончательный факт об объекте. Ею может быть модуль в локальном процессе Windows для начальной одиночной установки; для общего узла — отдельный постоянно работающий process/service на хосте. **Это не означает обязательный отдельный репозиторий или микросервис.**

Важное различение: **AppDock выбирает и предоставляет среду**, а **Strategy Box владеет своим прикладным содержанием**. Подключаемая БД не должна превращаться в «БД AppDock со всеми таблицами Strategy Box»: платформа предоставляет capability или обслуживаемое хранилище, приложение описывает записи, схемы и правила.

---

## 2. Холодный вход и проверка текущей реализации

### 2.1. `stratbox`: границы владельца

Актуальные [`README.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/README.md), [`AGENTS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/AGENTS.md), [`_mw/AGENTS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/AGENTS.md) требуют держать core вне пользовательского lifecycle. Он предоставляет `FileStore`, файловые IO API, операции макроэкономических/банковских данных, справочники и provenance вычислений. Он **пока не является общим владельцем чатов, запусков и участников**.

Рабочий корпус из трёх исследовательских веток указан в [`_mw`](https://github.com/ForestTiger-GH/stratbox/tree/main/_mw/epochs-001-strategy-box-development/research). `01-old-notes` — исторические гипотезы, `02-base-study` — фактические baseline и тематические исследования, `03-consolidation-research` — исследовательские своды, которые сами по себе не принимают Product Decision.

Новый [`docs/README.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/README.md) по состоянию на 09.10 обозначает корпус как `PARTIAL / UNDER CONSOLIDATION`. [`docs/architecture/responsibility-allocation.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/architecture/responsibility-allocation.md) считает shared application authority, persistence и права **кандидатными** решениями; [`docs/how/operations/diagnosis-and-recovery.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/how/operations/diagnosis-and-recovery.md) не устанавливает RPO/RTO. Это существенная граница достоверности.

### 2.2. `stratbox-windows`: текущие байты и слабые места

Основные проверенные пути:

- [`application/history/persistence.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/history/persistence.py): `HistoryPersistenceService` сохраняет `cases.json`, `events.json`, `artifacts.json`, `logs.json`, `assignments.json` отдельно через `Path.write_text`. Общего атомарного commit и блокировок нет; ошибка чтения JSON возвращает `[]`, отдельная неверная запись пропускается. В результате повреждение хранения может отобразиться как **отсутствие истории**.
- [`runtime/config.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/config.py) и [`runtime/user_preferences.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/user_preferences.py): размеры/панели/фильтр/выбранный сценарий/черновики параметров лежат в `app.json`, прямой JSON write. При невалидном JSON конфигурации, в отличие от истории, возникает `AppConfigError`.
- [`runtime/paths.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/paths.py): формирует `logs/`, `logs/operations/`, `cache/`, `runtime/` внутри managed system area. Начальный managed root берётся из AppDock Activation Context; есть dev root и заготовка user-profile mode.
- [`runtime/session_runtime.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/session_runtime.py): читает session/user/health, записывает AppDock-facing runtime projections. Это **состояние платформенной интеграции**, а не shared job database.
- [`runtime/context.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/context.py): строит `AppContext`, резолвит Data root/workspace, поддерживает degraded launch, получает FileStore; normal startup без AppDock разрешён только как явный development mode.
- [`application/background/store.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/background/store.py): в основном in-memory state; scheduler / durable job execution отсутствуют.
- [`runtime/bootstrap.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/bootstrap.py): приложение сейчас собирает state stores и Qt coordinator, что связывает lifetime authority с desktop GUI.

**Вывод о текущей реализации:** пользователь уже получает историю после штатного перезапуска, но **долговременная корректная консистентность не гарантирована**; последовательно обновлённые пять файлов могут описывать разные моменты времени. Простая замена `write_text` на atomic replace уменьшит риск повреждения каждого файла, но **сама по себе не сделает запись пяти файлов общей транзакцией**.

### 2.3. Что реально есть в AppDock сейчас

Актуальные источники AppDock:

- [`docs/architecture/root_model.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/root_model.md): различает **Install root**, **System/Node root**, **Runtime root**, **Package root** и **Data root**. System/Node root рассчитан на конфигурацию, состояние, логи, кэш, staging и session records. Data root — прикладные данные мира с отдельным lifecycle.
- [`src/appdock/domains/distribution/deployment/profiles/data_binding.py`](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/distribution/deployment/profiles/data_binding.py): знает `platform_managed_data`, `inside_install_tree_default`, `user_selected_external_data_root` — **профили расположения**, а не встроенный SQL engine.
- [`src/appdock/domains/node/roots/data_locator.py`](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/node/roots/data_locator.py): текущий DataLocator v2 поддерживает `local_drive` и `local_path`; доступность проверяется как существование пути. Отсюда нельзя вывести наличие транзакций, атомарности сетевого backend-а и независимого DB-сервиса.
- [`src/appdock/contracts/runtime/activation_context.py`](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/contracts/runtime/activation_context.py) и [его JSON Schema](https://github.com/ForestTiger-GH/AppDock/blob/main/specs/schemas/runtime/activation_context.schema.json): в Activation Context v3 есть roots, `data_root_path/status`, `provided_system_dirs`, references на platform state; **универсального SQL/StateStore descriptor здесь пока нет**.
- [`src/appdock/foundation/atomic_json.py`](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/foundation/atomic_json.py): реально реализован атомарный writer `temp → flush/fsync → os.replace → fsync_directory` для AppDock-owned JSON. Существующая полезная практика, **но не автоматически гарантия для всех storage providers, ОС и файловых систем**.
- [`src/appdock/domains/sessions/README.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/sessions/README.md) и [`src/appdock/domains/node/README.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/node/README.md): платформа владеет session/node жизненным циклом, не содержимым аналитического Work.

**Самое существенное уточнение:** слово **Data plane** сейчас лучше считать **целевым названием контрактной роли**, а не подтверждённым готовым AppDock storage service. Можно сегодня корректно интегрироваться через managed roots, не ожидая будущей платформенной СУБД. Актуальный AppDock — pre-alpha/формирующаяся платформа; описание полного потенциала не является доказательством реализации.

### 2.4. Корпус ранее выполненных исследований

Тема непосредственно пересекается с большим сводом [`03-consolidation-research / State, Persistence & Collaboration`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_05_state_persistence_collaboration_consolidated_research_2026-10-09.md). Тот материал рекомендует node authority и SQLite на локальном диске как стартовую гипотезу. **Настоящее исследование уточняет её в свете прямого комментария разработчика:** SQLite пока необязателен, provision/configuration остаётся за AppDock boundary, переходный файловый backend допустим при более узких возможностях.

Также изучены тематические источники:

- [`single-node multiuser`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md) — shared authority, персональные read state, конфликтные записи;
- [`system settings`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_system_settings_research_2026-10-07.md) — разделение preferences / policy / drafts;
- [`background jobs`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md) — durable definitions, occurrence и execution;
- [`execution control`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_execution_control_user_path_research_2026-10-07.md) — interruption, attempts, user path;
- [`artifacts`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md) — физический файл vs каталог результата;
- [`FileStore and formats`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md) — backend capabilities;
- [`web/self-hosted`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md) — хост, server/API, storage profiles;
- [`observability`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_observability_errors_logs_research_2026-10-07.md) — диагностические события, платформенная корреляция.

Предыдущие предложения используются как гипотезы; спорные вопросы перепроверены по коду и внешним документам. Описания старой product monolith-модели из [`01-old-notes`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/01-old-notes/README.md) не принимаются за современные требования.

---

## 3. Классификация состояния: что именно нужно хранить

При выборе носителя полезно сначала задать **шесть независимых атрибутов**:

1. **Owner:** AppDock, Strategy Box application, core, surface или фактический storage provider.
2. **Scope:** installation/node; пользователь; устройство; workspace; чат; Run/Job; источник/артефакт.
3. **Truth:** авторитетная запись, вычисляемая проекция, кэш или эфемерное состояние.
4. **Lifetime:** миллисекунды, до конца процесса, до завершения работы, до удаления среды, по retention policy.
5. **Concurrency:** один writer, конкурентные команды через authority, shared read, immutable object.
6. **Recovery:** взять проверенную запись, повторить computation, перезагрузить источник, reconcile эффект или сбросить удобство UI.

### 3.1. Расширенная матрица классов

| Класс | Кто владеет смыслом | Долговечность | Предлагаемый носитель первого этапа | Реакция после потери |
|---|---|---|---|---|
| Installation/version/Node identity | AppDock | Обязательно до удаления узла | AppDock-owned | Платформенное восстановление, Strategy Box читает snapshot |
| Node/session/health/runtime projections | AppDock | По platform lifecycle | AppDock-owned files/API | Перечитать/обновить, не объявлять domain Job успешным |
| Runtime capabilities, выделенные roots | AppDock | На срок activation/deployment | Versioned handoff | Preflight; degraded/unavailable при нарушении |
| Декларация product policy / разрешения | Deployment/App authority | Долговечно | Авторитетный policy owner; позднее shared store | Fail closed для опасных действий |
| User preferences: тема, масштаб, формат | Application/surface | Желательно | Atomic per-user JSON | Restore defaults с предупреждением при повреждении |
| Layout: открытая панель, фильтр | Surface | Опционально | Atomic JSON либо memory | Безопасный reset |
| Черновики введённых параметров | User/application | Желательно, не всегда | Atomic per-user JSON | Отметить потерю, предложить повторный ввод |
| Active editor cursor, hover, transient selection | Surface | Не нужно | RAM | Сброс |
| Workspace settings и links на Data root | Application + AppDock locator | Обязательно для активного узла | AppDock binding + небольшая app record | Проверить актуальность пути, не «чинить» чужие файлы молча |
| Chat/Thread identity, название | Application authority | Долговечно | Atomic state doc / позже transactional store | Показать восстановленную историю; при ошибке read-only |
| Сообщения, история команд, пользовательский timeline | Application authority | Долговечно в заданном сроке | Single-writer durable state / event records | Восстановить до последнего доказанного commit |
| Work/Case/run definitions и immutable request snapshots | Application authority | Долговечно | Там же | Не восстанавливать команду только из текста чата |
| Job/Attempt статус, outcome, след эффекта | Application authority | Долговечно для принятого задания | Там же | Reconciliation, не объявлять бегущим/failed без проверки |
| Background schedule definition | Application authority | После реализации scheduler — долговечно | Там же | Не создавать пропущенный запуск вслепую |
| Background next-run preview | Projection | Можно пересчитать | RAM | Рассчитать из schedule+time zone |
| Assignment/acknowledgement | Application authority | Долговечно для shared feature | Там же | Восстановить по accepted revision |
| User-specific unread/read cursor | Per-user application state | Желательно | Per-user record, позднее shared transactional | Пересчитать unread на основании собственного cursor |
| Presence/online indicators | AppDock sessions → app projection | Коротко | RAM/TTL | Сделать `stale/offline`, не воспроизводить старое online |
| Artifact catalog entry | Application authority | По retention | StateStore metadata | Reconcile с реальными bytes |
| Готовые файлы-артефакты | Data plane/backend | Пока нужны пользователю | Управляемая Data area | Проверить фактическое наличие; не восстановлять удалённое экспертом автоматически |
| Staged incomplete file | Storage adapter | Коротко до finalization | Staging | Quarantine/cleanup по доказательствам |
| Source snapshot, raw bytes, registry assets | Core/file store | По provenance/retention | Файлы + лёгкий manifest | Повторная загрузка допустима, если старую версию не требовалось фиксировать |
| Semantic domain results в RAM | Core | В рамках выполнения | RAM | Пересчитать при наличии исходников/метода |
| Cache парсеров, pivots, search index | Derived | Нет постоянной гарантии | Cache/Data/system согласно типу | Инвалидация и перестроение |
| Operation technical logs | Application diagnostics | Ограниченная retention | Files в AppDock-managed system | Аналитический outcome остаётся отдельным; лог может отсутствовать |
| Platform ProblemRef и crash evidence | AppDock | По platform policy | AppDock-owned | Ссылка на подтверждённый occurrence; не дублировать чувствительный dump |
| Diagnostic counters, UI previews | Projection | Не обязательно | RAM/cache | Восстановить вычислением |
| Backup receipts, restore epoch, migration version | Владельцы соответствующих состояний | Обязательно для управляемой процедуры | System/Node operational store | Запретить старому writer писать после restore |

**Правило:** в постоянное хранилище попадает только то, что невозможно безопасно восстановить из более авторитетного источника или потеря чего нарушит понятную пользователю историю. «Хранить всё навсегда» приведёт к непредсказуемому росту и тяжёлому сопровождению.

### 3.2. Принцип «история чата — не журнал истины исполнения»

История сообщений действительно удобна как человекочитаемый протокол выполненных и начатых действий. Однако для восстановления не хватает только текста сообщений. Нужны минимум `command_id`, `run_id`, `status`, `created_at`, `started_at`, `terminal_at`, `operation_id/version`, безопасные resolved parameters и ссылки на effects/artifacts. Иначе после сбоя нельзя различить «команда отображалась в чате» и «команда была принята к исполнению».

**Предложение:** сообщения являются проекцией записей запуска и заметок пользователя. При сериализации мы можем хранить компактный объект Run вместе с UI message; отдельный полноформатный event-sourcing engine пока не требуется.

---

## 4. Матрица гарантий сохранности и восстановления

### 4.1. Четыре уровня гарантий

| Класс | Значение | Требуемый минимум | Примеры |
|---|---|---|---|
| **G0 — ephemeral** | потеря допустима | сброс без системной ошибки | hover, progress redraw |
| **G1 — recoverable** | восстановление из известной истины | invalidation + честный recompute | search index, cache, presence |
| **G2 — durable record** | подтверждённая запись должна переживать нормальный restart/сбой процесса в пределах задокументированных допущений | atomic visible commit, writer ownership, corruption detection, backup по политике | preferences, чат, accepted Run, assignment |
| **G3 — effect-coupled** | необходимо согласовывать запись со внешним файловым/сетевым эффектом | intent + подтверждение bytes/receipt + reconciliation / unknown | публикация артефакта, разрушительные операции, удалённое действие |

**G2 не означает безусловную сохранность при потере диска и не означает RPO=0 при любой аварии питания.** Приложение должно различать подтверждённый atomic commit на исправной локальной файловой системе, завершение OS write без fsync и наличие независимого backup. Гарантии зависят от backend capabilities, настроек синхронизации и эксплуатационного профиля.

### 4.2. Главная таблица гарантий по категориям

| Категория | Гарантия | Атомарность | Резервирование | Рестарт / отказ | UI-поведение |
|---|---|---|---|---|---|
| Тема/окно/фильтр | G1–G2 | Один JSON snapshot | Не обязательно; export предпочтений по желанию | Reset допустим | «Часть настроек сброшена» |
| Чаты и принятые команды | G2 | Один state transaction / сериализованный commit | Да, по выбранной политике | Вернуть подтверждённые записи | Не заменять исчезновение «пустым чатом» |
| Run/Job с эффектами | G3 | Commit намерения и статуса; эффекты отдельно | Да + reconciliation evidence | `INTERRUPTED/OUTCOME_UNKNOWN` по фактам | Предложить осторожный retry |
| User permissions | G2 | Revisioned update | Да | Без валидной policy опасный запуск закрыт | Предупреждение об ограниченном режиме |
| Бинарный результат | G3 | Staging → verify → publish barrier | По политике владельца файлов | Проверить файл/manifest | Ссылка активна после подтверждённого publish |
| Справочники/source snapshots | G1–G2 | Versioned manifest/bytes | Для неизменяемых ценных версий | Re-download лишь при допустимой смене версии | Показывать свежесть/неопределённость |
| Кэш/поиск | G1 | Build into new generation | Не нужно | Rebuild | Возможен задержанный поиск |
| Технические логи | G1–G2 | Append/rotation | По support policy | Глубина истории ограничена | Отсутствие старого лога — не отсутствие Run |

---

## 5. AppDock Data plane: ключевой контракт, а не название папки

### 5.1. Два разных потока хранения

**А. Operational/Product State Plane** — состояние приложения: Run, история, назначения, revision, object access и backup index. Оно должно жить в AppDock-предоставленной **защищённой системной области узла** либо в AppDock-провиженированном сервисном хранилище. Важно, чтобы место позволяло гарантировать заявленную запись; пользовательская Data folder может быть сетевой, перемещаемой и свободно редактируемой экспертом.

**Б. Analytical Data Plane** — рабочие файлы и результаты: скачанные источники, XLSX, CSV, датасеты, артефакты. Здесь логичен `Data root / FileStore`, предоставленный через AppDock. Пользователь вправе управлять своими файлами; политика Strategy Box не должна пытаться «вернуть» всё, что человек сознательно удалил или переименовал.

Эти плоскости могут находиться на одном физическом диске при простой установке. **Смешивать их гарантии и ownership из-за совпадения пути нельзя.**

### 5.2. Что AppDock предоставляет уже сегодня и чего пока нет

| Возможность | По проверенному текущему коду AppDock | Как использовать Strategy Box |
|---|---|---|
| Выделение/описание roots | Реально есть | Получать пути через Activation Context, не угадывать C:\\ или `%APPDATA%` |
| DataBinding профили | Реально есть | Выделять Data для пользовательских артефактов |
| Provided system directories | Контракт реально есть | Размещать operational state при валидном binding |
| Atomic JSON helper внутри AppDock | Реально есть как внутренний implementation helper | Учесть семантику, но **не импортировать его как публичный SDK без версии/контракта** |
| Session/node state | Реально есть | Читать платформенную проекцию, не применять как хранилище Run |
| Готовый транзакционный SQL-provider для продуктов | **Не обнаружен в проверенных public activation/data-binding контрактах** | Не объявлять обязательной текущей зависимостью |
| General-purpose durable StateStore service / DB endpoint | **Целевой контракт, не подтверждённый готовый API** | Проектировать адаптер и процедуру capability negotiation |

### 5.3. Предлагаемая двухступенчатая интеграция

**Уровень I: размещение.** AppDock выбирает и передаёт разрешённые roots, ownership scope, user/node locality, режим read/write. Strategy Box создаёт свою внутреннюю структуру *только внутри выделенного namespace*. На этой стадии AppDock ничего не обязан знать про SQLite, таблицы, `Run` и `Thread`.

**Уровень II: provider capability (в будущем).** AppDock поставляет descriptor готового storage endpoint-а либо утверждённый bundle с ограничениями: поддерживаемые транзакции, атомарный replace, local/remote semantics, durability tier, back-up facilities, credential reference, quotas и version. Strategy Box выбирает подходящий StateStoreAdapter и проверяет его conformance до запуска.

Условный пример **будущего** дескриптора (формат не принадлежит текущему AppDock API):

```json
{
  "contract_version": "candidate-1",
  "binding_id": "product-state-primary",
  "owner_scope": "node:strategy-box",
  "storage_class": "managed_local_files",
  "state_backend": "atomic_snapshot",
  "locator_ref": "appdock-provided-private-system-dir",
  "capabilities": {
    "single_writer_required": true,
    "atomic_replace": true,
    "durable_flush": "verified_by_provider_profile",
    "network_shared_file_io": false,
    "backup": "application_coordinated"
  },
  "generation": 1
}
```

В последующем `state_backend` может стать `sqlite_local`, `postgres_service` или иным. Пример **не означает**, что AppDock сегодня сериализует этот JSON или поддерживает перечисленные поля.

### 5.4. Кто за что отвечает при провиженировании БД

| Решение/действие | AppDock | Strategy Box |
|---|---|---|
| Где размещается storage и как он запускается | Основной owner deployment | Запрашивает необходимый профиль |
| Какой backend разрешён в конкретной сборке | Provisioning/policy owner | Проверяет совместимость и выбирает адаптер |
| Учётные данные, OS user и доступ к endpoint | Предоставление безопасных references / platform policy | Использование по принципу минимальных прав |
| Структура таблиц, JSON schema, инварианты Work/Run | — | Единственный semantic owner |
| Запись, транзакции, optimistic revisions | Физическая гарантия provider-а | Логическая гарантия StateStore и command admission |
| Резервирование физического backend-а | Provider-side механизм и lifecycle | Согласование restore boundary с artifacts/Jobs |
| Retention, кто видит чат, как отображается incomplete job | — | Product policy / application authority |
| Migration application schema | Порядок provisioning, остановка старого процесса | Schema upgrade, проверка данных, fail-safe cutover |
| Health node/storage | Platform owner | Readiness собственной схемы и application state |

**Ключевое решение:** внешний AppDock предоставляет *операционную способность хранить*, а не переносит внутрь себя предметную модель Strategy Box. Это позволяет платформе меняться без переписывания аналитических сущностей.

### 5.5. Host и non-host

В локальном режиме application authority может работать внутри одного процесса Windows и писать в AppDock-issued private root. В host-режиме **единственный writer находится на хосте**, вместе с его StateStore. Пользователи/устройства направляют команды через авторизованный product API и получают read projections. Data root может быть настроен отдельно. Нельзя «пробросить базу» как путь к файлу SQLite по SMB между клиентами и назвать это multiuser backend.

Если платформа предоставит готовый hosted PostgreSQL, соединяется с ним **host authority**, а не каждый графический клиент. Внешние потребители не получают непосредственного SQL-доступа к канонической истории.

---

## 6. Альтернативы хранения: сравнение без преждевременного выбора

| Вариант | Что хорошо | Что плохо | Применимость |
|---|---|---|---|
| **A. In-memory only** | нулевая конфигурация, максимальная простота | потеря истории при закрытии/сбое | Только G0/G1, неприемлемо для важного чата |
| **B. Текущие 5 JSON с прямой перезаписью** | прозрачно, уже работает | torn writes, межфайловый рассинхрон, silent data loss | Считать техническим долгом |
| **C. Один атомарный JSON snapshot** | минимальная стоимость, единая граница commit | полный rewrite, один writer, слаб для длинной истории и частых shared mutations | **Предпочтителен ближайший переходный этап без SQLite** |
| **D. Append-only журнал + snapshots** | причина изменений, компактные записи, восстановление | CRC/length/rotation, compaction и recovery значительно сложнее | Следующий файловый шаг лишь при реальном росте истории и частоты записи |
| **E. SQLite local DB** | ACID transactions, индексирование, много связанных сущностей, библиотека в Python | локальная FS, locking/backup/WAL, migration, нельзя выдавать raw DB удалённым клиентам | **Сильный кандидат зрелого single-node authority**, когда AppDock binding/эксплуатация готовы |
| **F. PostgreSQL service** | клиент-сервер, concurrency, развитые backup/PITR, ops tooling | сервер, администрирование, network/security, стоимость | Общий узел с требованием постоянной доступности/операционных гарантий, если простое решение уже недостаточно |
| **G. Document store (например managed NoSQL)** | гибкие документы, свой ecosystem | гарантия транзакций зависит от product; потребуются API/ops и дисциплина schema | Альтернатива при уже существующем provider-е, не цель проекта сама по себе |
| **H. Полный event sourcing/distributed log** | подробная причинность, replay, audit | сложный evolution, projections, recovery, storage management | Избыточен на текущем этапе |

### 6.1. Почему один атомарный JSON предпочтительнее пяти

Проблема текущей истории — разные файлы обновляются по очереди. Например, после `case_completed` могли сохраниться новые `cases.json`, но старые `artifacts.json`. На экране появится завершённый расчёт без результата. Атомарная запись **одного согласованного состояния** позволяет всей группе низкообъёмных сущностей продвигаться единым revision:

```text
revision 41: cases + events + artifact refs + assignment refs
    │ build valid candidate in memory
    │ serialize to temporary file in same verified filesystem
    │ flush + fsync temporary
    │ os.replace(temp, authoritative state.json)
    │ durable directory sync where supported and required
    ▼
revision 42 accepted
```

Если процесс аварийно завершится до replace, останется revision 41; после — revision 42. Но файловый профиль обязан пройти проверку на конкретной FS. Не следует ожидать одновременной атомарности `state.json` и созданного внешнего XLSX: для него действует отдельный протокол публикации.

**Важная мера упрощения:** сначала достаточно **одного небольшого канонического файла на область authority** плюс независимых файлов user preferences и логов. Не надо сразу строить журнал, snapshot index, десятки таблиц и репликацию. Если история достигнет объёмов, при которых сериализация на каждое изменение становится дорогой, появится проверяемое основание для SQLite или журналируемого backend-а.

### 6.2. Когда нужен append-only файловый журнал

Если один JSON начинает часто переписываться и содержит тысячи или десятки тысяч событий, возможен `event segments + periodic snapshot` в private System root. Требуется **один писатель**, монотонные sequence, bounded record framing (length + digest/checksum), fsync commitment, `generation`, игнорирование *только неполного хвоста*, запрет молчаливого пропуска повреждения середины и детерминированный rebuild. Snapshot — проекция **одного журнала**, а не вторая конкурирующая истина. Compaction допускается лишь после подтверждённого snapshot+backup.

Это серьёзное усложнение. Если появится потребность в такой инфраструктуре, обычно разумнее сравнить её стоимость с SQLite, который уже предоставляет journal/transactions. Файловый event log полезен как строго ограниченный переходный механизм, а не самоцель.

### 6.3. Что говорят внешние первоисточники о SQLite

SQLite обеспечивает изоляцию commit-ов и сериализует записи; в WAL-режиме позволяет параллельные чтения и запись с **одним активным writer**. При этом WAL не предназначен для прямого доступа к одному файлу БД с разных компьютеров через сетевую файловую систему. Правильная альтернатива — SQLite и database engine живут на одном хосте, удалённые клиенты общаются с приложением по API, либо используется полноценная client/server database. [SQLite WAL](https://www.sqlite.org/wal.html), [SQLite over a network](https://www.sqlite.org/useovernet.html), [SQLite isolation](https://www.sqlite.org/isolation.html).

Режим `synchronous=NORMAL` в WAL сохраняет атомарность/согласованность, но допускает потерю последних подтверждённых транзакций после power loss. Для строгой заявленной durability потребуется изучить `FULL`, реальную FS и операционную цену; просто написать `journal_mode=WAL` недостаточно. [SQLite PRAGMA](https://www.sqlite.org/pragma.html).

**Суждение:** SQLite технически вполне подходит для локального узла, **но приоритет внедрения определяется границей AppDock provisioning и зрелостью приложения, а не размером SQL-файла**.

### 6.4. Самостоятельная научная проверка: crash consistency не сводится к `rename()`

Результаты исследования **Pillai et al., OSDI 2014, «All File Systems Are Not Created Equal»** важны именно для решения «обойтись пока файлами»: авторы показали, что корректность пользовательских протоколов записи сильно зависит от *persistence properties* конкретной файловой системы; проверили шесть распространённых Linux file systems и выявили уязвимости crash recovery в реальных приложениях. Практический вывод для Strategy Box: даже когда код использует разумные `fsync → rename`, **нужно сертифицировать целевые пары ОС/FS и inject сбои в точках commit**; описание общего Python API не заменяет доказательство сохранности. [Исходная научная публикация USENIX](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai), [публикация лаборатории](https://research.cs.wisc.edu/adsl/Publications/alice-osdi14.html).

Работа **«Specifying and Checking File System Crash-Consistency Models» (ASPLOS 2016)** формально отмечает, что POSIX-интерфейс не определяет все возможные результаты после аварии; предлагаются модели и litmus tests, включая экспериментальную проверку ext4. Для Strategy Box следствие ещё уже: **не выводить гарантию power-loss recovery из имени функции**, а описать и испытать её на фактическом storage profile. [DOI первоисточника](https://doi.org/10.1145/2872362.2872406).

Наконец, **NIST SP 800-34 Rev. 1** разделяет `RPO` (до какой точки времени можно вернуть данные) и `RTO` (как долго допустима недоступность). Это подтверждает необходимость задавать требования **по классам состояния и реальному business impact**. Утверждение «у нас атомарный JSON» является техническим механизмом, но не определяет ни допустимую потерю при уничтожении диска, ни время восстановления; числовые обязательства остаются продуктовым/эксплуатационным решением. [NIST SP 800-34 Rev. 1](https://csrc.nist.gov/pubs/sp/800/34/r1/upd1/final).

**Критерий сопоставления альтернатив по научным источникам:** файловый backend выигрывает минимальной сложностью, **если** он ограничен одним writer-ом, одним проверяемым commit object и конкретной файловой системой. SQL engine выигрывает, когда возникает несколько связанных атомарных изменений, конкуренция, индексы и эксплуатационные требования. Научные работы не указывают «SQLite обязателен»; они требуют явной модели отказов и доказательств.

---

## 7. Целевой `StateStore` contract: небольшой и нейтральный

Логический интерфейс надо проектировать от операций, а не от методов конкретной библиотеки SQL. На уровне приложения достаточно:

```text
StateStore (illustrative port)
  load(scope_id) -> VersionedState | Corrupt | Unavailable
  commit(scope_id, expected_revision, mutation_id, changes) ->
      Committed(revision) | Conflict(actual_revision) | Failed | Unknown
  snapshot(scope_id) -> ValidatedSnapshot
  health() -> StateStoreHealth
  checkpoint_or_backup(...) -> Receipt | Unavailable
  close()
```

Для первого файлового backend-а `changes` могут быть применены к единому документу в памяти. Для SQL адаптера — разложены по реляционным таблицам внутри одной транзакции. **Реляционную семантику не надо подменять «универсальным JSON query engine».** Порт описывает жизненный цикл операции и гарантии; backend вправе иметь внутреннюю оптимизированную схему.

Обязательные общие поля authoritative commit:

```text
schema_version
node_id / authority_scope_id
store_generation  # меняется при управляемом restore или clone
revision          # монотонна внутри authority scope
mutation_id       # идемпотентность команды
committed_at_utc
writer_id
state_payload / affected record ids
checksum_or_integrity_marker
```

Для принятого Run минимум: `run_id`, `chat_id`, `initiator_id`, `operation_id`, `request_snapshot`, `status`, `created_at`, `started_at`, `finished_at`, `attempt refs`, `output refs`. Все дополнительные тонкости позднее можно вводить внутри доменной модели, если есть реальная нужда. Нет оснований с первого дня создавать универсальную распределённую event ontology.

### 7.1. Идемпотентность и оптимистическая конкурентность

Если пользователь дважды нажал «Запустить» или клиент повторил запрос после сетевого timeout, `mutation_id/idempotency_key` должен позволять вернуть **тот же** подтверждённый результат admission, а не породить второй Run. Если два устройства переименовали один чат, `expected_revision` предотвращает молчаливое затирание чужих изменений. Для начального одиночного клиента эта дисциплина почти бесплатна: поля существуют, отдельного conflict UI ещё не требуется.

Для shared profile единственный owner сериализует изменения разных чатов; **параллельное выполнение разных операций не означает параллельную запись в один JSON без координации**. Несколько вычислительных worker-ов могут исполнять расчёты, но короткий commit в StateStore проходит через один state owner/транзакционную дисциплину.

### 7.2. Незрелый AppDock: graceful fallback без скрытого принятия риска

Запуск допускается по следующей схеме:

1. AppDock передаёт объявленный profile/capabilities (сегодня — проверенные managed roots; в будущем — storage descriptor).
2. Strategy Box выполняет storage preflight: права, свободное место, тип/локальность, атомарный replace, возможность flush, lock test, чтение тестовой generation, при необходимости recovery test.
3. Если требуемый profile подтверждён, приложение запускает соответствующий StateStoreAdapter.
4. При отсутствующем optional Data root разрешён UI `degraded`, просмотр локальных данных/диагностика; **запись в отсутствующее authoritative store блокируется**.
5. При невозможности подтвердить атомарность можно разрешить ограниченный **single-user temporary/prototype profile** с явным предупреждением и запретом обещаний G2/G3. Для важной истории лучше отказывать в записи, чем создавать видимость надёжности.

**Необязательный SQLite ≠ необязательная проверка сохранности.**

---

## 8. Атомарность: что именно считается «записано»

### 8.1. Три разных границы

**Атомарность записи одного small state file:** при поддержке соответствующей локальной FS — `temp (same dir) → flush/fsync → replace → sync directory`. Она предотвращает частично видимый JSON, но не гарантирует согласование с другими файлами и внешней сетью.

**Атомарность принятия команды:** новая история/Run/effect intent должны получить **один логический revision/commit**. В переходном single-snapshot backend-е это одна атомарно заменяемая запись; в SQL — транзакция. Ошибка commit означает, что пользователь не должен получить подтверждение принятого Run как факт.

**Атомарность физического результата:** XLSX, ZIP, удалённый download или destructive operation требуют отдельной `staging → verification → publish` процедуры. Нельзя использовать обычный `close()` сетевого stream как безусловное подтверждение публикации, если backend способен выполнить частичную запись. См. [кандидатное LDD по staged publication](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/ldd/artifacts/staged-publication.md).

### 8.2. Почему «быстрая запись» недостаточна

Сокращение окна записи полезно, но важнее *видимая точка commit*. Файл может записываться очень быстро, но внезапное отключение питания оставить его неполным; замена file path может быть атомарна, но external side effect уже произошёл; создание metadata может завершиться, пока XLSX ещё не финализирован. Гарантии должны вытекать из подтверждённой техники, а не предположения об отсутствии сбоев в доли секунды.

Официальный Python описывает `os.replace` как атомарный при успешном выполнении при соответствующих условиях ОС, предупреждает о разных файловых системах. SQLite подробно документирует требования к `fsync`, journaling и сохранности при сбоях. [Python os.replace](https://docs.python.org/3/library/os.html#os.replace), [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html).

### 8.3. Crash window для записи state

| Точка аварии | После рестарта | Разрешённая реакция |
|---|---|---|
| До записи temp | Старая revision | Продолжить со старой revision |
| Посреди записи temp | Старая revision + мусор temp | Ignorable/quarantined temp после проверки имени/владельца |
| После fsync temp, до replace | Старая revision | Старый state действует; orphan temp удалить по правилам |
| После replace, до подтверждения caller | Новая или старая revision в зависимости от доказанной durability | При повторе проверить `mutation_id`, не исполнять дублирующий effect |
| Во время directory sync/сбоя питания | Зависит от ОС/FS и объявленного profile | Не утверждать 100% guarantee без fault test |
| После подтверждённого commit | Принятая revision при соблюдении профиля | При повреждении — recovery path, read-only и alert |

---

## 9. Задания, закрытие приложения и восстановление процесса

### 9.1. Не стоит автоматически «возобновлять» всё

Комментарий разработчика к теме 02 предусматривает простой режим: при закрытии приложения или обрыве **текущий локальный расчёт обычно прекращается**. Это совместимо с долговечным хранением **факта запуска**, даже если сам job после старта не переживает закрытие GUI.

Для первого этапа достаточно:

```text
Accepted/Prepared -> Running -> Succeeded / Failed
                             -> Interrupted / OutcomeUnknown
```

У завершённых операций сохраняются result refs; у незавершённых — причина, насколько она известна, последнее достоверное действие и возможность повторить. UI показывает предупреждающий значок с подсказкой. Восстановление «с того же байта» и универсальные checkpoints сейчас не нужны.

### 9.2. Что происходит после crash

1. При startup прочитать **последний целостный** authoritative state.
2. Найти Run/Job, оставшиеся в нетерминальном состоянии.
3. Сверить worker/process identity и подтверждённые receipts при наличии.
4. При одиночном GUI без независимого executor-а — отметить запуск `interrupted` только если доказано прекращение worker-а и нет неоднозначного внешнего эффекта; иначе `outcome_unknown`.
5. Не повторять автоматически destructive/download/publish operation с неизвестным исходом.
6. Подсветить пользователю статус и предложить проверку результата/повтор, когда это безопасно.

**`Failed` и `Interrupted` — разные факты.** `Failed` означает доказанную неудачу операции; `Interrupted` — завершение исполняющего процесса; `OutcomeUnknown` — возможный внешний эффект без достоверного ответа. Автоматически переводить каждое старое `running` в `failed` удобно для UI, но неправильно для реальности.

### 9.3. Будущий host/background режим

Когда появится AppDock-managed persistent host process, исполнитель и state-owner работают независимо от Windows/Web/Android окна. Тогда выход пользователя из интерфейса прекращает только client session; Job продолжает жить на host. Достаточно той же семантической модели Run/Job, но возникает необходимость хранить scheduler definitions, attempts, leases, worker identities и выполнить reconciliation при перезапуске host-а. Не стоит строить сегодня отдельный «второй мир фоновых задач».

---

## 10. Чаты, многопользовательский узел и конкурентная работа

### 10.1. Сложность не в количестве клиентов, а в числе пишущих authority

Один Windows desktop может писать атомарный JSON. Десять подключённых UI тоже могут работать с файловым StateStore, **если все изменения выполняет один хостовый authority**, а клиенты вызывают его API. Два независимых клиента, которые напрямую редактируют `state.json` через общий каталог, — другой и небезопасный режим. Им потребовались бы межхостовые locks, fencing, consistency и восстановление после split brain; ради Strategy Box это избыточно.

**Первое правило многопользовательского профиля: один authoritative writer на узел, много читателей через API.** Этот writer может сериализовать мутации в короткую queue. Вычисления параллельны, commit состояния короткий и управляемый.

### 10.2. Общие чаты и персональные признаки

Разработчик ожидает, что участники общего узла видят чаты и запуски друг друга. Значит `chat_id`, название, сообщения и Run records живут у **host authority**. А `unread`, последний выбранный чат, ширина панели и фильтр являются **персональными** данными. Хранить `unread: bool` в общей записи Case неправильно: один пользователь прочитал — второй ещё нет. Для будущего server profile нужен `read_cursor` per principal, либо per-message acknowledgement при усложнении UX.

При удалённом web-доступе обязательно применяются разрешения на чтение/изменение на уровне API. Знакомство участников между собой не заменяет authorisation при публичном URL. В текущем local-only profile минимальная политика проще.

### 10.3. Reconnect и stale state

Клиент получает `snapshot(revision/cursor)`; при связи — разрешённые changes, при пропуске sequence — новый snapshot. Если связь потеряна, интерфейс честно показывает «последнее известное состояние» и блокирует действия, для которых нужен свежий authority. Не требуется сразу офлайн-редактирование с merge/CRDT.

Для разных поверхностей (Windows, web, Android) одинаковыми должны быть semantic models, permissions и состояния, а не конкретные Qt-виджеты.

---

## 11. Артефакты: связь физического файла и метаданных

У продукта есть два вида результата: вычисленная таблица/сообщение в чате и файл в рабочем каталоге. Для файла необходимо различать `calculated result`, `staging bytes`, `verified published file` и `artifact catalog record`.

Минимальная публикация:

```text
Run accepted (durable)
   -> compute
   -> write temporary artifact into permitted Data root
   -> close/flush as supported
   -> verify file exists + required size/hash/format
   -> publish to final locator via supported mechanism
   -> record artifact commit/locator in application StateStore
   -> show actionable artifact link in chat
```

**Кросс-хранилищной атомарной транзакции тут обычно нет.** Если файл появился, но metadata commit не прошёл, recovery видит unindexed/orphan object; если metadata есть, но файла нет, карточка не должна показывать успешное открытие. Для малого MVP допустим один pending publish marker и повторная сверка после старта, без сложной CAS-инфраструктуры.

Особое требование разработчика из темы 04: если эксперт самостоятельно перенёс/переименовал/удалил файл, Strategy Box **не обязан искать и возвращать его**. Достаточно проверки при действии и пометки «Файл не найден». Это сокращает необходимость в постоянном file watcher, версии файловой системы и глобальном индексе содержимого. Но удаление файла не должно уничтожать саму запись чата о ранее выполненной операции.

### 11.1. Три степени доказуемости внешнего storage

- **Local atomic replace supported:** можно иметь сильную publication visibility внутри одного volume при успешной проверке.
- **Remote store с подтверждённым conditional put/generation:** использовать native commit/ETag механизм, если provider действительно его предоставляет.
- **Backend без гарантий:** staging, проверка после записи, недвусмысленный `UNKNOWN` при потере ответа; не симулировать ACID поверх обычного копирования файлов.

Внимание: абстракция `FileStore` в core не обязана уметь всё перечисленное. Нужен capability query / narrowly optional `atomic_publish` contract, а не предположение, будто `rename` во всех реализациях атомарен.

---

## 12. Резервирование, восстановление и перенос между версиями

### 12.1. Важное различение

**Crash recovery** восстанавливает согласованный state после прерывания процесса. **Backup recovery** возвращает состояние после потери/повреждения носителя или ошибочного удаления. **Application reconciliation** сверяет записанную историю с внешними effects и файлами. Это разные механизмы; один atomic JSON writer не заменяет резервирование.

### 12.2. Что должно входить в backup set

Обязательная область резервирования определяется принятым профилем, но для полноценного восстановления истории должна включать:

1. Canonical application state и его `schema_version/generation`.
2. Необходимые managed artifact bytes и manifests **в той мере, в какой продукт отвечает за них**, либо явно отмеченные ссылки на внешнюю пользовательскую Data папку.
3. Необходимые domain snapshots/versioned resources, которые нельзя достоверно скачать в той же версии повторно.
4. Настройки и policies, которые пользователь не сможет восстановить из AppDock без потери смысла.
5. Backup receipt: revision/snapshot hash, список manifest refs, создано кем/когда, область coverage.

Логи полного traceback, кэш, UI position, search indexes обычно можно исключить. Если Data root находится на пользовательском внешнем диске, важно **не создавать ложное впечатление, что backup системного StateStore автоматически резервирует и сами файлы**.

### 12.3. Как делать согласованный backup двух плоскостей

Предлагаемый процесс:

```text
acquire backup barrier or record stable authority revision
  -> capture committed metadata snapshot/revision
  -> identify required immutable artifacts/manifests
  -> copy/verify bytes or record explicitly external/unmanaged refs
  -> emit BackupReceipt(revision, hashes, coverage, timestamp)
  -> release barrier / resume ordinary mutations
```

На раннем файловом backend-е допустимо коротко остановить mutating commands и получить согласованный snapshot. При SQL можно использовать нативный online backup механизмы, но они дают согласованную **БД**, а согласованность с внешними файлами всё равно требует manifest/barrier. [SQLite backup API](https://www.sqlite.org/backup.html); [PostgreSQL PITR](https://www.postgresql.org/docs/current/continuous-archiving.html).

### 12.4. Процедура восстановления

1. Остановить старый writer/приём мутаций (через AppDock lifecycle и application guard).
2. Проверить источник backup, список файлов, hashes, schema version и полноту заявленного coverage.
3. Восстановить в отдельную staging area (никогда не перетирать единственную рабочую копию с ходу).
4. Проверить внутреннюю integrity, referential links, доступность нужных artifacts.
5. Опубликовать новую **store generation / restore epoch**; старые sessions/writers/leases лишаются права записывать в восстановленную область.
6. Пересчитать derived indexes, пометить stale sessions/presence, reconcile незавершённые effects.
7. Поднять API/UI и выполнить end-to-end smoke на реальном аналитическом сценарии.

Важно: **клон backup нельзя одновременно запускать рядом с оригиналом с тем же `node_id/store_generation` и той же возможностью записи**, иначе возникнет раздвоение власти. При переносе узла нужно либо явно переназначить authority identity, либо проводить управляемый takeover, согласованный с AppDock.

### 12.5. Schema version: отсутствие обратной совместимости ≠ потеря пользовательских данных

Можно свободно менять API и внутренние структуры без поддержки старого кода. Но важная пользовательская история может уже существовать. Поэтому при переходе `5 JSON → atomic state` или `atomic state → SQLite` нужна **однократная проверяемая миграция**:

- inventory/backup старых файлов;
- strict import и report о malformed records;
- mapping old IDs к canonical IDs;
- проверка количества записей и ссылок;
- quarantine спорных элементов без молчаливого удаления;
- full read-back новой записи;
- атомарный cutover и отсутствие второго активного writer-а;
- старые файлы как временный архив с явным retention.

Постоянный dual-write на два backend-а **не рекомендуется**: он создаёт две конкурирующие истины и удваивает риск расхождения.

---

## 13. Recovery failure matrix: проверочные сценарии

| № | Сбой | Риск нынешнего состояния | Требуемое целевое поведение | Минимальный тест |
|---|---|---|---|---|
| 1 | Kill посреди `cases.json` | усечённый JSON, затем пустая история | старый или новый валидный state, явная ошибка corruption | kill перед/после replace |
| 2 | Сбой между `cases` и `artifacts` | case/result mismatch | единый commit или reconcile pending | fault injection между write этапами |
| 3 | Disk full при config update | повреждение app.json | предыдущий валидный конфиг, error surfaced | quota/disk-full |
| 4 | Invalid JSON при загрузке history | silent empty state | quarantine + diagnostic; read-only/restore | malformed fixtures |
| 5 | Два параллельных запуска в разных чатах | race/last-write-wins | unique IDs, serial commit, корректный статус каждого | concurrent write test |
| 6 | Два UI переименуют чат | lost update | expected_revision conflict | stale command simulation |
| 7 | GUI closed while job running | нет ясного terminal event | interrupted/unknown recovery marker | force close and reopen |
| 8 | Сетевой запрос принят, ACK потерян | дублирующий Run при повторе | idempotency key lookup | drop response after commit |
| 9 | XLSX записан частично | видимый испорченный файл | staging hidden, no committed artifact | abort writer midway |
| 10 | Файл финализирован, DB/state commit падает | orphan bytes | reconcile/retention, без ложного completed | stop before catalog commit |
| 11 | Metadata опубликованы, файл вручную удалён | битая ссылка | «Файл не найден», сохранённая история | user removes file |
| 12 | Data root недоступен | ошибочное «нет файлов» | backend unavailable; degraded readonly UI | disconnect mount |
| 13 | Worker ещё жив, UI перезапущен | некорректный failed | host mode reconnect; GUI-only mode explicitly terminated | restart client vs host |
| 14 | Восстановление старого backup | stale worker commits | store_generation/fencing rejects writer | restore while stale client retries |
| 15 | Backup БД без artifacts | неполная реставрация | coverage warning, links unresolved | simulated missing blobs |
| 16 | AppDock Activation Context несовместим | неправильный root/write | fail preflight with supported contract list | wrong version/locator |
| 17 | Storage расположен на SMB/NFS | atomicity/locking assumption invalid | capability fail/alternate provider; не SQLite WAL direct share | network FS test |
| 18 | Два пользователя отмечают chat read | `unread` в общей записи стирает чужой статус | per-user read cursor | independent cursors |
| 19 | Corrupt event journal middle | silent skipped records | stop/quarantine, signal loss; tail-only truncation by rules | byte flip middle/tail |
| 20 | Миграция schema аварийно прервана | полуразрушенный state | old authority remains until verified cutover | crash at each migration phase |

Обязательная философия тестов: **продукт не должен заявлять успешный commit или восстановление, если его нельзя подтвердить**. Результат теста должен проверять и фактическую FS/DB, и карточку пользователя.

---

## 14. Что следует делать сначала: практический маршрут

### Этап 0 — контракт без миграции в БД (ближайший)

1. Установить для каждого типа состояния owner, truth, lifecycle, recovery и privacy/retention; выделить **authoritative** от **surface convenience**.
2. Сформировать маленький `StateStore`/`StateStorageBinding` port вне Qt и вне `stratbox` core. Логически он принадлежит application level; текущая физическая реализация может находиться в `stratbox-windows`, пока нет второго потребителя.
3. Переписать `HistoryPersistenceService`: вместо пяти независимо записываемых файлов — один согласованный versioned state snapshot для критичной части либо строгий importer из них в единый document; запрещена silent empty recovery.
4. Добавить `AtomicFilesStateStore` с проверкой AppDock-issued private system path, temp/replace/fsync и **одним writer-ом**.
5. Отделить `app.json` удобств UI от durable execution state; сохранить настройки и черновики индивидуальными atomic small files.
6. При старте проверить сохранённую generation/last revision и отдельно пометить interrupted/unknown accepted runs.
7. Зафиксировать явный градиент поддержки: local standalone single-writer **поддерживается**; shared direct file writes **запрещены**; remote DB пока **не объявляется**.
8. Добавить fault-injection и import/read-back smoke.

**Выход этапа:** можно пользоваться desktop без SQLite и значительно снизить риск потери истории. Общий хост/синхронизация пользователей ещё не обещаются.

### Этап 1 — интеграция с AppDock как явной storage capability

1. Совместно с владельцем AppDock закрепить stable contract: system/private roots, storage locality, atomic/flush guarantees, owner scope, backup hooks, service endpoint, version, generation.
2. Развести `DataBinding` пользовательских файлов и `StateBinding` product metadata; по умолчанию использовать private System/Node root для StateStore.
3. Формализовать self-test/conformance provider-а на Windows и затем на Linux-host; запрет silent fallback на несертифицированный remote filesystem.
4. Согласовать, кто и когда создаёт managed state backend, как запускается/останавливается service, кто владеет backup/restore и миграцией.
5. Настроить platform health visibility: `ready`, `degraded`, `unavailable`, `corrupt`, `recovery_required` в безопасной пользовательской форме.

**Выход этапа:** Strategy Box знает, **что гарантирует платформа**, но всё ещё может работать на простом файловом backend-е.

### Этап 2 — host authority и один настоящий shared profile

1. Вынести authoritative application service из Qt lifecycle; не вводить отдельный репозиторий до доказанного самостоятельного lifecycle.
2. Поднять локальный IPC или loopback API в desktop mode; затем host API для других устройств.
3. Реализовать single-writer state mutations + idempotency + revision и read-only snapshot.
4. Подключить второй тестовый клиент, проверить две параллельные операции и конфликтные user edits.
5. Для фоновых задач добавлять durable job/scheduler лишь при появлении реального executor-а, не по наличию UI-карточки.
6. Если атомарный JSON становится узким местом по размеру/параллельности, измерить нагрузку и выбрать SQLite или иной AppDock-provisioned backend.

**Выход этапа:** многопользовательская семантика перестаёт быть локальным UI-каркасом; physical backend выбран по доказательствам, а не заранее.

### Этап 3 — production recovery и зрелые базы (условный)

- Когда AppDock готов к DB provision, подключить `SQLiteStateStore` на *локальном диске authority* или `PostgresStateStore` через service endpoint.
- Встроить schema migrations, backup/restore receipts, testable integrity checks, artifact reconciliation.
- Принять RPO/RTO/retention на уровне реального профиля эксплуатации.
- Для SQLite: официальная online backup API, WAL/checkpoint/`synchronous` conformance; для PostgreSQL: managed backup/PITR и защищённое соединение.
- При необходимости масштабирования client API сохраняет предметную семантику; backend можно заменить через управляемую одноразовую миграцию, а не вечный compatibility layer.

---

## 15. Архитектурные противоречия и их разрешение

### 15.1. «Всё через AppDock» vs «AppDock ещё не готов»

**Разрешение:** разделить *AppDock как источник разрешённого root/capability* и *AppDock как будущий host managed database*. Первое реализуемо сейчас; второе откладывается до появления стабильного версионированного API. Не надо хардкодить SQLite в Windows, но и не надо блокировать исправление пяти JSON в ожидании SQL-as-a-service.

### 15.2. «Всё состояние на хосте» vs «у пользователя свои настройки»

**Разрешение:** shared authority state — на host, surface layout и персональные черновики — у клиента либо в user scope, если нужна кросс-девайсная синхронизация. Физические каталоги AppDock различаются по владельцу. При подключении хоста второстепенные локальные файлы не становятся второй shared truth.

### 15.3. «Закрытие завершает процессы» vs «история долговечна»

**Разрешение:** процесс расчёта может завершиться, но **запись о принятии и незавершённом исходе сохраняется**. В будущем persistent host разделит lifecycle клиента и job. Это развитие одной модели, а не смена смысла статусов.

### 15.4. «Рабочая папка — вся наша Data» vs «история должна быть надёжной»

**Разрешение:** Data root хранит аналитические файлы; Operational State Store — в управляемой private System area/DB capability. Ссылки соединяют две плоскости. Пользовательское переименование XLSX не требует системного поиска, но не должно стирать запись о Run.

### 15.5. «Без обратной совместимости» vs «нужны миграции»

**Разрешение:** избегаем старых публичных методов API и legacy runtime adapters, но сохраняем **ценные пользовательские данные** через отдельную одноразовую import/cutover процедуру. Это разные задачи.

### 15.6. «SQLite надёжен» vs «SQLite по AppDock Data share»

**Разрешение:** SQLite — engine локального authority с выделенной AppDock private state area, либо используется вообще другой AppDock provisioned service. Назвать общий network share «data plane» недостаточно, чтобы WAL стал совместимым с распределённым доступом. [SQLite WAL](https://www.sqlite.org/wal.html), [SQLite over network](https://www.sqlite.org/useovernet.html).

### 15.7. «События = история» vs «нужен event sourcing»

**Разрешение:** причинную и пользовательскую историю можно хранить как компактную часть канонического состояния, а позже как SQL event records. Полный replay-everything architecture не требуется. Для передачи уведомлений после commit можно в будущем добавить transactional outbox, но сама отправка в сеть не является частью локальной DB transaction. [Transactional outbox pattern](https://microservices.io/patterns/data/transactional-outbox.html).

---

## 16. Открытые вопросы / Product Decisions

| ID | Вопрос | Предлагаемый default | Когда решение обязательно |
|---|---|---|---|
| **Q03-01** | Какой authoritative state scope у первой поставки? | Один локальный узел, один writer | До переписывания persistence |
| **Q03-02** | Какой AppDock binding используется для product metadata? | Private System/Node root, отдельно от Data root | До выбора путей/миграции |
| **Q03-03** | Должен ли AppDock сам provision DB engine? | Future optional provider; сейчас managed dirs | Совместный контракт с AppDock |
| **Q03-04** | Срок жизни пользовательских чатов и команд? | Долговечно до заданного retention/user deletion | Перед production shared mode |
| **Q03-05** | Какие параметры сценария можно persist? | Только non-secret, валидированные; sensitive исключить | До сохранения shared runs |
| **Q03-06** | Crash UI автоматически прекращает задание? | Да в GUI-only, нет в future host mode | Перед разделением executor |
| **Q03-07** | RPO/RTO на уровне классов? | Не обещать цифры без измерений; provisional backup schedule после пилота | Перед эксплуатационной поставкой |
| **Q03-08** | Кто запускает backup и владеет restore? | AppDock life-cycle/provision + app consistency barrier | Перед первым backup UX |
| **Q03-09** | Какой shared data access? | Host API; direct SQLite/JSON по сети запрещены | До подключения второго клиента |
| **Q03-10** | Когда переходить с JSON на SQLite? | При реальном размере/частоте/отношениях данных и зрелом AppDock DB binding | После profiler/load/fault tests |
| **Q03-11** | Нужно ли сохранять всю версию скачанных источников? | Только явно значимые snapshots; дата+hash/provenance по возможности | В контексте source policy |
| **Q03-12** | Как обрабатывается user deletion of artifacts? | Не искать/восстанавливать; помечать missing | До artifact UI actions |
| **Q03-13** | Нужны ли immutable audit records? | Минимальные события операций; отдельный аудит при опасных/внешних действиях | Перед AI/remote/destructive functions |
| **Q03-14** | Multi-node/HA требует consensus? | Нет на первых этапах: один узел authority | Только при реальном HA SLA |
| **Q03-15** | Кто управляет clone/restore generation? | Совместный AppDock lifecycle + app store fencing | Перед полноценным restore/import |
| **Q03-16** | Можно ли использовать network-mounted user folder для prefs? | Только G1/G2 по подтверждённой FS; иначе local user system root | При платформенных профилях |

---

## 17. Проверяемые критерии готовности

Рекомендуемый **минимум для выпуска переходного файлового этапа**:

- [ ] **F1**: имеется одна authoritative версия состояния чатов/кейсов/артефактных ссылок на область узла; пять JSON больше не являются независимыми production authorities.
- [ ] **F2**: любой accepted Run получает durable `run_id` и `mutation_id`; reopen показывает его даже после аварийного завершения процесса.
- [ ] **F3**: fault-injection на каждой фазе atomic replace оставляет валидную старую или новую revision; при corruption возникает диагностическая ошибка, не пустой feed.
- [ ] **F4**: один writer ownership проверяется; второй competing writer не может незаметно затирать состояние.
- [ ] **F5**: AppDock-owned private root выбирается по Activation Context, произвольный Data root не используется как «системная БД».
- [ ] **F6**: завершённый шаг с незавершённой публикацией файла не получает ложную карточку committed artifact.
- [ ] **F7**: interrupted/unknown status видны в чате; повтор опасного действия требует проверки.
- [ ] **F8**: повреждённые/невалидные записи сохраняются как evidence/quarantine и видны в диагностике, а не игнорируются.
- [ ] **F9**: есть round-trip backup/restore на контрольном наборе history+artifact refs и механизм увеличения store generation.
- [ ] **F10**: local Windows user preferences разделены от shared authority; reset второстепенных настроек не уничтожает историю.
- [ ] **F11**: volume tests (размер истории, скорость записи, startup rebuild) показывают, что atomic JSON оправдан; лимиты задокументированы.
- [ ] **F12**: ни интерфейс, ни core не импортируют private AppDock implementation для storage; используются согласованные внешние boundaries.

Для **допуска общего узла** дополнительно нужны second-client tests: два одновременных чата, revision conflicts, idempotent duplicate submit, reconnect/stale cursor, изоляция персонального read-state, host backup while clients active, потеря host/сети и безопасное восстановление write authority.

---

## 18. Итоговый выбор и последовательность принятия решений

**Вывод №1 — не делать SQL предпосылкой правильной архитектуры.** Минимальная система сохранности может состоять из одного владельца записи, одного атомарного versioned state document, независимых user preferences и управляемых файлов результатов. Это уже исправляет самые опасные особенности текущего Windows JSON persistence.

**Вывод №2 — AppDock определяет эксплуатационное предоставление storage.** Действующий AppDock умеет давать roots/DataBinding и хранить собственное состояние; подтверждённого общего SQL-provider contract пока нет. Первая реализация использует предоставленные каталоги; будущие SQLite/PostgreSQL подключаются по явно согласованной capability, без изменения предметной семантики Strategy Box.

**Вывод №3 — не класть StateStore в пользовательский Data root только потому, что он называется Data.** Каноническая история должна иметь private, контролируемый, проверенный storage; рабочие XLSX/CSV остаются в пользовательской Data area. Связи между ними проверяются при фактическом действии.

**Вывод №4 — один authority на узел важнее движка базы данных.** Для host/multiuser несколько клиентов не должны напрямую менять JSON или SQLite. Они обращаются к единому owner через API. В противном случае даже PostgreSQL не исправит двусмысленную ответственность за статусы Run и права пользователей.

**Вывод №5 — цель восстановления сейчас скромная и полезная.** После аварии вернуть согласованную историю, честно обозначить незавершённые/неизвестные действия и позволить безопасно повторить. Автоматическое продолжение всех расчётов, распределённый event sourcing, HA, сложный CAS, полная миграция файлов и долговечные фоновые очереди — отдельные поздние задачи с самостоятельными критериями.

**Практическая рекомендация:** принять **три решения прежде кода**: (а) первый профиль `single-node / single-writer / atomic-files`; (б) путь metadata только из AppDock private system binding, Data root — для аналитических файлов; (в) минимальный persistence port с revision/idempotency/corruption semantics. После этого выполнить один сквозной пилот `запуск сценария → история → авария → восстановление → проверка файла` на фактической Windows-поставке. По результатам измерений и зрелости AppDock вернуться к вопросу SQLite.

---

## 19. Список первоисточников и степень доказательности

### 19.1. Точная постановка

- `Strategy_Box_Research_Topics(2).docx`, тема 03, с. 2; примыкающие комментарии к темам 02/04/07/08/10 используются только для проверки смежных ограничений.
- `AppDock - Базовое описание.docx` — концептуальное описание платформы; положения о будущих host/remote/recovery *не считаются доказательством реализованного API*.

### 19.2. Репозитории (актуальная проверка по GitHub `main`)

- [`stratbox` README](https://github.com/ForestTiger-GH/stratbox/blob/main/README.md), [`AGENTS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/AGENTS.md), [`_mw/AGENTS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/AGENTS.md) — authority/research/product boundaries.
- [`stratbox` docs current HOW](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/current-how/windows-application.md), [responsibility allocation](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/architecture/responsibility-allocation.md), [artifact LDD](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/ldd/artifacts/staged-publication.md) — current, candidate и limitations.
- [`stratbox` consolidation topic 05](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_05_state_persistence_collaboration_consolidated_research_2026-10-09.md) — ранее сформированная общая карта состояния и альтернатив.
- [`stratbox-windows` persistence](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/history/persistence.py), [config](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/config.py), [paths](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/paths.py), [session-runtime](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/session_runtime.py) — проверенный актуальный код.
- [`AppDock` root model](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/root_model.md), [data binding](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/distribution/deployment/profiles/data_binding.py), [DataLocator](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/node/roots/data_locator.py), [Activation Context v3](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/contracts/runtime/activation_context.py), [atomic_json](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/foundation/atomic_json.py) — действующие platform owners; GitHub-репозиторий AppDock приватен, ссылки работают для участников с доступом.

### 19.3. Самостоятельная внешняя техническая проверка

| Первоисточник | Применимость и ограничение |
|---|---|
| [SQLite: Atomic Commit](https://www.sqlite.org/atomiccommit.html) | Объясняет, почему надёжность commit требует журналирования, flush и оговорок о файловой системе; не доказывает свойства любой конкретной AppDock-поставки. |
| [SQLite: WAL](https://www.sqlite.org/wal.html) | Reader/writer concurrency, one writer и ограничение network filesystem. |
| [SQLite: over a network](https://www.sqlite.org/useovernet.html) | Почему SQL engine должен жить рядом с файлом либо нужно client/server решение. |
| [SQLite: Isolation](https://www.sqlite.org/isolation.html) | Разница между транзакциями и совместным чтением. |
| [SQLite: PRAGMA synchronous](https://www.sqlite.org/pragma.html) | Различия гарантии power-loss durability между NORMAL/FULL в WAL. |
| [SQLite: Backup API](https://www.sqlite.org/backup.html) | Согласованный backup работающей БД; не заменяет backup внешних artifacts. |
| [SQLite: corruption cases](https://www.sqlite.org/howtocorrupt.html) | File locking, network FS, external filesystem corruption и небезопасное копирование. |
| [Python: os.replace](https://docs.python.org/3/library/os.html#os.replace) | Atomic replace при поддерживаемых предпосылках; разные FS и platform issues. |
| [PostgreSQL: continuous archiving / PITR](https://www.postgresql.org/docs/current/continuous-archiving.html) | Возможности зрелого server deployment, цена сопровождения и WAL-backed recovery. |
| [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html) | Согласование DB commit и последующей рассылки событий; не требуется в полном виде в single-process прототипе. |
| [Fowler/Joshi: Write-Ahead Log](https://martinfowler.com/articles/patterns-of-distributed-systems/write-ahead-log.html) | Принцип журнала подтверждённых изменений и восстановления; не повод сразу строить распределённую систему. |
| [Fowler/Joshi: Singular Update Queue](https://martinfowler.com/articles/patterns-of-distributed-systems/singular-update-queue.html) | Обоснование одного короткого writer-path при множестве клиентов/worker-ов. |
| [Pillai et al., OSDI 2014: All File Systems Are Not Created Equal](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai) | Экспериментальные доказательства зависимости crash consistency от конкретной ФС, необходимость fault injection. |
| [Specifying and Checking File System Crash-Consistency Models, ASPLOS 2016](https://doi.org/10.1145/2872362.2872406) | Формальная модель состояний ФС после аварии, litmus tests, граница POSIX guarantees. |
| [NIST SP 800-34 Rev. 1](https://csrc.nist.gov/pubs/sp/800/34/r1/upd1/final) | Раздельное определение RPO/RTO и процедуры contingency planning. |

### 19.4. Что исследование **не** подтверждает

- Работающий общий StateStore/SQL Data plane в нынешнем AppDock.
- Производительность и power-failure guarantees на конкретных Windows/Linux volumes без испытаний.
- Наличие готового host API, удалённого исполнения и многопользовательской синхронизации в текущем `stratbox-windows`.
- Принятые бизнесом сроки хранения, гарантированное RPO/RTO, действующие регламенты backup и доступных сторонних managed DB.

**Итоговый статус:** достаточная архитектурная база для пилота `AtomicFilesStateStore` и согласования AppDock storage boundary; недостаточная для объявления зрелой multiuser/HA/managed-SQL платформы.
