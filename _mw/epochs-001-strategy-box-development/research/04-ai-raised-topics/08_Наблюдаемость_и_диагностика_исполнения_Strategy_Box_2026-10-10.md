# 08. Наблюдаемость и диагностика исполнения Strategy Box

**Дата исследования:** 10 октября 2026 года  
**Источник постановки:** `Strategy_Box_Research_Topics(2).docx`, тема **08 — «Наблюдаемость и диагностика исполнения»**, включая наводящие вопросы и комментарий разработчика.  
**Статус:** самостоятельный исследовательский результат. Целевая модель и примеры контрактов — рекомендации, а не утверждённые Product Decisions или описание уже реализованной функциональности.  
**Срезы реализации:** `stratbox@main` (проверка актуальных исходных файлов и корпуса знаний 10.10.2026); `stratbox-windows@main`, дерево `959e9c4ce1441124af5111c1e025041714e04d3b`; `AppDock@main`, дерево `a4d87c643e620e54e04083d4d0b8d867513e7065`.  
**Изменения:** репозитории, продуктовый код и соседние исследования не изменялись.  
**Граница публичности:** публичные рекомендации оперируют нейтральными контрактами расширений; детали закрытых реализаций в настоящий документ не включены.

---

## 0. Резюме и архитектурное предложение

**Основной вывод:** наблюдаемость Strategy Box следует строить как **связанную систему фактов о выполнении**, а не как один общий журнал, который затем пытаются превратить в чат, индикатор прогресса, отчёт об ошибке и узловое оповещение. Связность достигается устойчивыми идентификаторами, минимальными типизированными событиями, отдельным файловым техническим журналом, безопасными проекциями и ясной ответственностью за состояние. Для первой реализации полноценная СУБД и OpenTelemetry-инфраструктура **не требуются**.

Важное дополнительное уточнение разработчика в ходе настоящего исследования: **выбор и размещение SQLite либо другого будущего хранилища должны проходить через AppDock**. На ближайшем этапе допустимо простое файловое хранение. Это меняет рекомендацию относительно части исследований 7–9 октября, где SQLite предлагалась как ближайшая физическая реализация. Здесь она становится **одним из поздних адаптеров**, а текущий кандидат — минимальный append-only журнал плюс проверяемые снимки состояния в AppDock-предоставленном пространстве.

Рекомендуемый путь:

```text
                 Strategy Box, нейтральные операции (stratbox)
                    │  result + domain diagnostic + progress
                    ▼
         Общая прикладная execution-authority Strategy Box
         ├─ Threads / chats           ─ пользовательское обсуждение
         ├─ Runs / Jobs / Attempts     ─ фактическое исполнение
         ├─ Domain events              ─ существенные переходы
         ├─ Problem summaries          ─ понятная причина/исход
         └─ Visibility projections     ─ для конкретного зрителя
                    │
          StoragePort / DiagnosticsPort / PlatformBridge
                    │
                    ▼
        AppDock binding / session / node / managed directories
         ├─ CURRENT: предоставленные roots + activation references
         ├─ NEAR TERM: single-writer file journal / snapshots / logs
         └─ LATER: выбранный AppDock storage provider и platform problems
                    │
                    ▼
     Windows / будущие Web, Android, AI ─ разные представления фактов
```

**Семь решений высокой уверенности:**

1. **`chat_id` нужен**, потому что чатов много, их создают разные пользователи, а лента должна воспроизводиться после перезапуска. **Но `chat_id` недостаточно:** несколько одновременных запусков в одном или разных чатах требуют независимых `run_id`, `job_id`, `step_run_id`, `attempt_id` и `event_id`.
2. **Сообщения в чате — полезная проекция истории**, но не исчерпывающий технический лог и не единственная доказательная запись о выполнении. В чате важны стадия, исход, автор, время, артефакты и действия; в файле — диагностические свидетельства.
3. **Общее пространство чатов** означает общий источник истины на узле и поток изменений для клиентов, а не синхронизацию пяти локальных JSON-файлов между компьютерами.
4. **Ошибку, её последствия и уведомление следует разделить:** индивидуальная неудача запуска не должна автоматически превращаться в тревогу для всей команды. Общая проблема с ресурсом узла — подходящий кандидат для уведомления.
5. **AppDock выбирает физическую инфраструктуру и передаёт binding**, Strategy Box определяет собственную схему событий, смысл состояния и условия публикации результатов. Платформа не должна знать предметную структуру чатов или рассчитывать аналитические статусы.
6. **Сейчас достаточно файлового решения**, но только с однозначным писателем, защищёнными корнями, ограниченными логами, восстановлением после повреждения и честным `UNKNOWN` при невозможности установить результат.
7. **AppDock observability зрелее локальной диагностики Strategy Box, но неполон:** его типы и целевая модель полезны для проектирования границы; полноценный продуктовый SDK, удалённая работа, fleet/incident и ряд sinks нельзя считать готовыми.

### Степени утверждений

В документе используются следующие статусы:

- **CURRENT** — подтверждено действующим исходным кодом, контрактом или точным current-документом; если тесты здесь не исполнялись, это особо отмечается.
- **DEVELOPER** — прямой замысел или предпочтение разработчика; это важнейший продуктовый ввод, но ещё не реализованный контракт.
- **RESEARCH** — вывод из сопоставления материалов, технической документации и сценариев отказа.
- **TARGET** — предлагаемая структура, интерфейс или правило, требующие решения о внедрении.
- **OPEN** — фактический технический или продуктовый выбор пока отсутствует.

**Важно о нумерации:** «тема 08» в исходном DOCX — **наблюдаемость и диагностика**. Файл третьей ветки исследований с названием `03 Topic 08 Trust, Safety & System Qualities` посвящён **другому, более широкому предмету**. Он рассматривается только как смежный источник, а не подменяет постановку текущей темы.

---

## 1. Что именно заказал разработчик

### 1.1. Полная смысловая реконструкция постановки

Исходная тема требует связать **прогресс, события, логи, ошибки и последствия отказов** от предметной операции до UI и платформенной интеграции. Наводящие вопросы указывают два проектных центра: (1) причинная связь одного действия со всеми техническими попытками, шагами, файлами и ошибками; (2) правило, **какие сведения хранятся локально, передаются AppDock и видны другим**.

Комментарий разработчика даёт более конкретный продуктовый маршрут:

| Положение из комментария | Семантика | Статус | Следствие |
|---|---|---|---|
| Развёртывание и системные каталоги через AppDock | AppDock является физическим координатором среды, есть разделение системных, user и data областей | **DEVELOPER**; текущий AppDock подтверждает часть каталогов | Все пути должны приходить из binding, без жёстко заданной машины/каталога |
| На хосте операционное состояние подключённых участников находится на стороне хоста | Общая истина принадлежит узлу, клиенту — вторичные локальные сведения | **DEVELOPER**, будущий host не CURRENT | Общая история/статусы должны иметь одного authority writer |
| Действие связывается с никнеймом, датой и конкретным чатом | Пользователь должен понимать, **кто, когда и где** запустил операцию | **DEVELOPER** | Ввести `actor_ref`, время, `thread_id`, связанный `run_id` |
| Сообщения в чатах фактически являются «условными логами» | История действий должна быть видима прямо в рабочем общении | **DEVELOPER**, не требование хранить traceback в чате | Разделить chat timeline и protected technical log |
| Базовый ID чата | Чат как продолжительный контекст и контейнер пользовательской истории | **DEVELOPER** | `thread_id` / `chat_id` является устойчивой идентичностью, но не ID попытки |
| Несколько одновременных чатов и одновременные команды | Реальная конкуренция задач, в том числе параллельные активные задачи | **DEVELOPER**; нынешний Windows не выполняет | Нужна execution-authority с несколькими runs и resource policy |
| Все участники одного узла видят все чаты друг друга | Пользовательская концепция единого командного пространства | **DEVELOPER** | Реплицировать отфильтрованную shared timeline, видимую по правам узла |
| Новый чат создаётся под именем «Новый чат», переименование через `⋯` | Конкретный UX по умолчанию | **DEVELOPER** | Поле названия chat metadata, отдельный event rename |
| AppDock пока pre-alpha | Обещания AppDock нужно сверять с current implementation | **DEVELOPER + CURRENT** | Не строить критическую сохранность на незавершённом SDK |
| СУБД/провайдер storage поступает через AppDock; сейчас возможны файлы | AppDock владеет физическим binding, Strategy Box — своей семантикой | **DEVELOPER (дополнение 10.10)** | Переходный `FileStateBackend`, затем provider-neutral storage adapter |

Отдельное смежное пожелание из материалов по ошибкам/участникам: пользователям полезно видеть, у кого сломался конкретный сценарий и затронула ли проблема общий узел. Это **не означает**, что каждому необходимо видеть чужой traceback, абсолютные пути, параметры или секреты.

### 1.2. Установленное, предполагаемое и открытое

**Достаточно определены продуктово:** разделение user/system/data; связь с чатом, автором и временем; параллельные чаты; общий просмотр чатов на узле; понятные статусы; минимальный UX; перспективная роль AppDock в storage и observability.

**Пожелания без точной гарантии:** степень долговечности истории; полноценный live progress с процентами; сообщение другим пользователям при сбое; будущая AI-переписка; восстановление и автоматические повторы; работа хоста после закрытия desktop UI.

**Технически открыты:** единый исполнительный процесс и его lifecycle; физический формат event journal; durable transaction guarantees; доставка событий; версия contracts AppDock, через которую выдаётся будущий storage provider; доступ к защищённым логам; политика повторов/отмены; retention; разрешения и масштаб реальной shared-node поставки.

---

## 2. Метод и корпус доказательств

### 2.1. Холодный вход и владельцы

Прочитаны актуальные [`stratbox/README.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/README.md), [`stratbox/AGENTS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/AGENTS.md) и [`stratbox/_mw/AGENTS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/AGENTS.md). Они фиксируют разграничение **core / application surfaces / внешняя платформа**, единый `_mw` как рабочую исследовательскую область и новое `docs/` как Knowledge Product. Новое `docs/` содержит как ограниченные подтверждённые факты, так и **кандидатные** целевые решения; статус документа всегда важнее привлекательности предлагаемой схемы.

Из корпуса прочитаны и сопоставлены:

- [Первое исследование observability (02-base-study, 07.10)](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_observability_errors_logs_research_2026-10-07.md).
- [Многопользовательская работа одного узла](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md).
- [Фоновые процессы, чаты и job manager](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md).
- [Execution control / user path](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_execution_control_user_path_research_2026-10-07.md).
- [03: Work-to-execution](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_04_work_to_execution_consolidated_research_2026-10-09.md).
- [03: State/persistence/collaboration](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_05_state_persistence_collaboration_consolidated_research_2026-10-09.md).
- [03: Trust/safety/system qualities](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_03_Topic_08_Trust_Safety_System_Qualities_2026-10-09.md) — смежный широкий синтез.
- [03: Whole-system architecture](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_09_whole_system_target_architecture_2026-10-09.md).
- [Базовый bounded Research extraction](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/consolidation/reconciliation/BASE-STUDY-OBSERVABILITY.md).
- [Подтверждённый Windows current HOW](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/current-how/windows-application.md), [диагностика и восстановление — кандидат HOW](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/how/operations/diagnosis-and-recovery.md), [научное различение UNKNOWN](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/science/trust-and-assurance/uncertain-outcome-vs-observed-error.md), [кандидатный responsibility allocation](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/architecture/responsibility-allocation.md).

Исторические заметки `research/01-old-notes` и `docs_old/` использованы только для происхождения идей; они не отменяют прямые факты текущего кода. Связанные PROTOS/AI-модели учитываются **только на внешней границе вызова**: ИИ является актором с теми же `run_id`, правами, безопасными event projections и result statuses. Устройство другого проекта здесь не конкретизируется.

Внешняя платформа исследована по [`AppDock observability TARGET_MODEL`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/observability/TARGET_MODEL.md), [`IMPLEMENTATION_STATUS`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/observability/IMPLEMENTATION_STATUS.md), [`activation_and_launch`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/activation_and_launch.md), [`root_model`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/root_model.md), [ADR directory authority](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/adr/ADR-platform-directory-authority.md) и прямым контрактам исполнения/activation. Эти материалы принадлежат AppDock: **проект Strategy Box не вправе объявлять их плановые функции текущими возможностями своей поставки**.

### 2.2. Ограничение метода

Проведена прямая статическая проверка значимых файлов и contracts, плюс сопоставление предыдущих исследований. Это **не** end-to-end test установленного приложения, не stress test нескольких клиентов и не проверка поставки на реальном AppDock-хосте. Численные бюджеты и готовность будущих модулей ниже обозначаются кандидатами. Конкретные сохранённые данные пользователей и приватные инфраструктурные реализации не исследовались в открытом репозитории.

---

## 3. CURRENT: реальная наблюдаемость `stratbox`

`stratbox` остаётся Python-библиотекой. Её зрелые домены уже умеют отдавать содержательные ошибки/предупреждения и audit/provenance-материалы, но **единого execution telemetry envelope для всех доменов сейчас нет**. Это подтверждено базовым исследованием, а в актуальном [`docs/what/strategy-box/qualities-and-constraints.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/what/strategy-box/qualities-and-constraints.md) единый observability contract прямо помечен как требующий дальнейшего решения.

| Группа | Текущая способность | Почему этого мало для общего execution UI |
|---|---|---|
| Сбор исходных файлов | структурированные failures и сведения о полученных исходниках | разные ошибки загрузки не получают общей causal identity |
| Escrow | partial collection, warnings, metadata результата | нет единообразной последовательности streaming progress |
| Формы ЦБ | typed data/validation и экспорт | этапы и output-коммиты внешнему клиенту описаны неодинаково |
| SORS restoration | богатая доказательная диагностика: conflicts, ledgers, solver rounds | предметное свидетельство нельзя без потери смысла сводить к `error: str` |
| FRG | планы файловых действий, safety semantics и локальные статусы | результаты опасных действий требуют separate receipt/unknown |
| `base.ioapi` / network / filestore | низкоуровневые bytes / HTTP results, местами exceptions | нет общего safe/logging policy на границе внешнего приложения |

**Вывод:** библиотеке нужны **два небольших нейтральных порта**: optional `ProgressSink` и `DiagnosticSink` либо единый typed callback с двумя категориями. Аргументы обычных публичных функций не следует перегружать `AppDock`-контекстом, chat IDs или Qt. Идеальная минимальная сигнатура операции — предметный `Request`, optional execution context/callback и предметный `Result`, с возможностью корректного вызова из Jupyter/Colab без внешнего приложения.

Важен **разделяемый ownership**: core создаёт предметный факт (`SOURCE_SCHEMA_CHANGED`, `VALIDATION_INCOMPLETE`, `SOLVER_INFEASIBLE`), вызывающая сторона связывает его с `run/attempt` и превращает в представление для пользователя; AppDock получает только те платформенные сведения, которые подтверждены и допустимы его текущим контрактом.

---

## 4. CURRENT: `stratbox-windows` — подробная сверка исходников

### 4.1. Реальный жизненный цикл операции

| Прямой файл | Подтверждённое действие | Архитектурный пробел |
|---|---|---|
| [`application/scenarios/runner.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/scenarios/runner.py) | синхронно исполняет steps по `order`, пишет `case_started`, `step_started`, success/failure, формирует artifact/log metadata | нет независимых run/attempt IDs, real streaming progress и проверки post-effect receipt |
| [`application/operations/execution/runner.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/operations/execution/runner.py) | создаёт per-operation FileHandler, вызывает handler, ловит exception, возвращает `OperationResult(ok, message, outputs, details)` | `str(exc)` попадает в result, stdout/traceback может дублироваться, нет `PARTIAL/UNKNOWN` |
| [`presentation/qt_desktop/scenario_coordinator.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) | запускает worker в `QThread`, содержит один `_thread`, `_worker`, `_active_case`; второй submit при busy отклоняется | **одна выполняющаяся задача на весь coordinator** против параллельных чатов |
| [`application/cases/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/cases/models.py) | `ScenarioRunCase`: UUID, scenario, author, params, started/finished, stage, steps, outputs, `unread` | case одновременно играет роль карточки/запуска; chat ID отсутствует, `unread` глобален |
| [`application/events/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/events/models.py) | UUID event, created_at, actor, case/scenario/operation, artifact/log links, message body | `thread_id`, `run_id`, `attempt_id`, sequence/cursor отсутствуют |
| [`application/logs/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/logs/models.py) | `LogRecord` с физическим `path` и case/step/operation link | OS-absolute locator внутри переносимой модели |
| [`runtime/logging.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/logging.py) | `app.log`, Python FileHandler | нет rotation, retention, contextual IDs, структурированного безопасного вывода |
| [`application/history/persistence.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/history/persistence.py) | пять JSON collections для cases/events/artifacts/logs/assignments; restore | перезапись отдельных файлов; повреждение JSON становится `[]`; нет общей транзакции |
| [`runtime/paths.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/paths.py) | создаёт `logs/operations`, `cache`, `runtime`, знает AppDock managed paths | размещает app-owned state в выбранном managed system root, но без storage-provider contract |
| [`adapters/appdock/surface_state.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/adapters/appdock/surface_state.py) | пишет last operation/case, last output/log, active_job и прочую runtime projection | формат в основном single active/last; не полноценная node-wide реестровая картина |
| [`presentation/common/scenario_chat/projector.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/presentation/common/scenario_chat/projector.py) | строит «своё/чужое» расположение карточек и статусы | есть projector, но shared network authority пока отсутствует |

Текущие операции и сценарии доступны через GUI; это **рабочий локальный прототип**, а не нулевая реализация. Идентификаторы `case_id`, `event_id`, `log_id` и `artifact_id` существуют. Повторно придумывать их смысл не требуется; необходимо **исправить границы и дополнить связи**.

### 4.2. Конкретные режимы сбоя текущего кода

**A. Утечка текста исключения.** `run_operation()` выполняет `message=f'Operation failed: {exc}'` и `details={'error': str(exc), ...}`. Исключение сторонней библиотеки может включать внутренний путь, URL, идентификатор доступа и иное содержимое. Это затем попадает в case/event/UI. Исправление: raw exception → restricted technical log; пользователь → stable code и подготовленный safe summary.

**B. Ложная пустая история.** При любой ошибке чтения или JSON decoding `_load_list()` возвращает `[]`. Успешно пустая история и повреждённая история становятся одинаковы. Это подтверждение кода, **не свидетельство уже произошедшей потери**. Для будущей authority такое поведение недопустимо; для best-effort cache оно допустимо только с явным статусом деградации.

**C. Одинаковое имя operation log при повторе.** Путь логирования строится как `{case}__{step}__{operation}.log` без `attempt_id`; FileHandler открывается по умолчанию в append mode. Ретрай внутри того же case/step может смешивать записи разных попыток. Дополнительно logger handlers глобально заменяются по имени, что особенно неприятно при добавлении конкуренции. Потребуется отдельная identity попытки и контролируемый lifecycle логгеров.

**D. Успех после внутреннего исключения на стадии завершения.** `ScenarioRunner` предполагает, что `run_operation` вернёт нормализованный результат, а callbacks работают. Исключение callback/persistence/проекции после внешнего эффекта не всегда равно ошибке самого предметного расчёта. Нужны изолированные failure domains и `UNKNOWN`/reconciliation, а не тотальная трактовка «неуспех операции».

**E. Параллелизм физически запрещён.** `ScenarioCoordinator.submit` поднимает `RuntimeError('A scenario is already running')`, когда занят. Тема 08 требует исправить **модель исполнения** до построения нового списка чатов.

**F. Потенциальная путаница session state и аналитического job.** `AppSurfaceStateService.update_runtime(active_job=...)` публикует скаляр; при нескольких параллельных Runs один `active_job` не может быть authoritative каталогом всех jobs. Он может оставаться лишь `focused_job_id` для активной UI-сессии, а все jobs должны храниться у authority.

**G. Текущее `unread` в Case/Event — общее поле.** Для нескольких пользователей нужен отдельный read cursor / per-participant receipt. «Я прочитал чат» не должно снимать уведомление у всех.

### 4.3. Чего в Windows CURRENT нет

Ниже перечислены именно **неподтверждённые функции**, несмотря на существование одноимённых UI-элементов: долговременный node-wide JobManager, устойчивый concurrent executor, job-level cancellation, настоящий сетевой shared timeline, реальный background scheduler, remote host execution, синхронизированный presence, доступ к AppDock problem recorder через готовый public product SDK, Web/Android surfaces. Их следует проектировать как будущие, без mock-успеха.

---

## 5. CURRENT: AppDock и граница ответственности

### 5.1. Что документировано и подтверждается реализацией

**AppDock current**, по проверенным материалам, различает:

- **Install/Node/System root** для managed state, logs, cache, sessions и health;
- **Data root** для прикладных рабочих файлов с отдельным жизненным циклом;
- **user/private system directory** как предоставляемую каталоговую возможность;
- **Activation Context** для передачи точной геометрии и ссылок текущей session;
- **Node/Session** как отдельные platform state owners;
- **observability public contracts** (`ContextEnvelope`, `ProblemDefinition`, `ProblemDraft`, `ProblemOccurrence`, `ProblemRef`, `DiagnosticReport`, `EvidenceRef`, `Recorder`);
- **OperationCompletion** с результатами `SUCCESS`, `PARTIAL`, `CANCELLED`, `FAILURE`, `UNKNOWN` и типизированное `OperationProgressEvent`.

Прямые ссылки: [AppDock `root_model.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/root_model.md), [directory-authority ADR](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/adr/ADR-platform-directory-authority.md), [Activation Context contract](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/contracts/runtime/activation_context.py), [observability public contract package](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/observability/public/__init__.py), [execution result contracts](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/execution/results/operation_results.py).

`AppDock` уже различает событие, `ProblemOccurrence`, текущее `Condition` и будущий `Incident` как разные значения. **Но** наличие Python-классов `Recorder` и `ProblemRef` ещё не доказывает существование готовой стабильной внешней API-точки для регистрации проблем произвольного стороннего приложения.

### 5.2. Проверенная зрелость observability в AppDock

В [`IMPLEMENTATION_STATUS.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/observability/IMPLEMENTATION_STATUS.md) верхний authoritative handoff на текущем дереве фиксирует: **Milestone 5E — source implementation complete, native Windows certification pending**. Он описывает регистрацию безопасных проблем при activation, Node/Session `ProblemRef`, защиту task transport от raw exceptions. **Следующий 6A emergency/bootstrap sink ещё не реализован/не допущен до завершения gate 5E**. Semantic Events, Audit, Support, Incident, Agent/Remote и дополнительные внешние product bindings остаются будущими волнами.

Следовательно, нельзя в ближайшем Windows-клиенте требовать от AppDock того, что у него пока существует только как `TARGET_MODEL` или отложенный milestone. Strategy Box должен уметь **самостоятельно фиксировать собственную локальную диагностику** в выделенном пространстве, а мост к платформе включать по реальному capability negotiation.

### 5.3. Текущий deployment profile

[`stratbox-windows/appdock/manifest.json`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/appdock/manifest.json) фиксирует `Connector 4.0`, интерактивную Windows surface, `launch_mode=foreground`, `locality=local` и `--diagnose` как declared diagnostics. Версия Activation Context — отдельная `3.0`, а не версия manifest. Это не включает production shared host, remote, web и Android.

Два различия, которые нельзя упустить:

1. **Платформа выделяет место/способ существования продукта**, но продукт знает, какие состояния и события действительно значимы. Передать directory root — не значит предоставить готовую транзакционную БД.
2. **Платформенный `Node health` не является исходом аналитического расчёта**. Node может быть здоров при некорректном CSV; расчёт может закончиться успешно при деградировавшей телеметрии. Эти факты должны сохраняться отдельно.

---

## 6. Главная логическая модель: чат, запуск, попытка и диагностический факт

### 6.1. Чат ≠ выполнение

В комментарии разработчика чат назван «условным логом» неслучайно: на пользовательском уровне именно лента объясняет, **что происходило**. Но полноценное исполнение содержит значительно больше событий, чем нужно выводить в ленту. Важно разделить три уровня:

1. **Командное общение / Thread.** Долговечный контейнер сообщений, обсуждений, запусков, результатов, ссылок на артефакты, упоминаний участников и, в будущем, общения с ИИ.
2. **Исполнение / Run–Job–Attempt.** Отдельная сущность со своим жизненным циклом, ресурсами, попытками, отменами и подтверждениями эффектов. Несколько запусков могут жить в одном чате; один запуск может быть связан с Work, automation и другим контекстом.
3. **Техническая диагностика / Events–Logs–Evidence.** Сведения, по которым оператор установит цепочку причин и неполное состояние, но которые не обязаны быть сообщениями чата.

Предлагаемая минимальная связь:

```text
Node N
  ├── Thread A: «Новый чат» → «Отчётность банков»
  │     ├── human message
  │     ├── Run R1: cbr.forms.build       ── Job J1 ── Attempt A1
  │     └── Run R2: escrow.history        ── Job J2 ── Attempt A2
  ├── Thread B: «Новый чат»
  │     └── Run R3: cbr.files.collect     ── Job J3 ── Attempt A3
  └── Shared node notices
        └── Condition C1: data storage unavailable
```

`R1`, `R2` и `R3` могут выполняться одновременно. В зависимости от фактических ресурсов `J2` может ожидать освобождения единственного output destination, а `J1` и `J3` продолжат независимую работу.

**Не следует** делать `chat_id` универсальным `trace_id`: две несвязанные операции в одном чате имеют разные causal traces. Чат — контекст пользовательского общения, trace — цепочка одного исполнения. В будущем один Work может охватывать несколько чатов, а один чат — несколько Work; поэтому связи должны быть внешними идентификаторами, а не скрытыми тождествами.

### 6.2. Минимальный словарь идентификаторов

| ID | Обозначает | Когда создаётся | Scope / правило |
|---|---|---|---|
| `node_id` | конкретный managed узел | AppDock | авторитетный platform binding |
| `participant_id` | участника данного узла | identity/session owner | устойчивый ID; `nickname` — изменяемый display label |
| `session_id` | конкретное подключение/activation | AppDock | один участник может иметь несколько сессий |
| `thread_id` (`chat_id`) | чат/обсуждение | application authority | UUID/ULID, не зависит от названия |
| `message_id` | отдельное человеческое/AI/системное сообщение | chat owner | append-only identity; edit как отдельная версия |
| `work_id` | продолжительная предметная цель, если введена | work owner | не обязательна для простого запуска v1 |
| `run_id` | один эпизод исполнения сценария | admission в application authority | отдельный для каждого запуска, даже в одном чате |
| `job_id` | планируемая исполнительная единица | JobManager | может отличаться от run при составном графе |
| `operation_name` | тип предметной способности | operation registry | стабильное имя, **не identity вызова** |
| `operation_run_id` | конкретное применение операции | execution authority | часть Run/Job, допускает несколько однотипных шагов |
| `step_id` | шаг в definition | scenario definition | повторное исполнение шага использует тот же `step_id` |
| `step_run_id` | конкретное исполнение шага | run planner | связывает лог/артефакт/результат именно с запуском |
| `attempt_id` | одна попытка физического действия | executor | меняется при retry |
| `event_id` | отдельный диагностический/lifecycle факт | event producer | доставка с at-least-once, дедупликация по ID |
| `problem_id` / `problem_ref` | конкретное событие сбоя, подтверждённое владельцем | problem recorder | не путать с `problem_code` |
| `artifact_id` / `artifact_version` | результат и его опубликованная версия | artifact owner | путь — locator, не identity |
| `trace_id` / `span_id` | распределённая причинная трасса | tracer, когда включён | необязательны на первом локальном этапе |

**Практический v1:** обязательно материализовать `thread_id`, `run_id`, `attempt_id`, `event_id`, `actor_ref`, `node_id` (где доступен), `occurred_at_utc`. `job_id` и `operation_run_id` можно создавать сразу при фактическом наличии JobManager/нескольких шагов, но их смысл нельзя замещать строковым `operation_name`. Не требуется выпускать 15 отдельных persistent-таблиц: ID может присутствовать в записи события.

### 6.3. Actor, никнейм и реальная идентичность

Замысел разработчика — простой ввод имени, а не тяжёлая корпоративная IAM-система. Для доверенной локальной команды это разумный UX. Но одинаковые никнеймы, случайные переименования и сессии на двух устройствах создают двусмысленность. Минимальное разделение:

```text
actor_ref       stable participant identity within node
actor_display   «Алексей»              # меняется
session_ref     installation/session-bound reference
origin          user | background | api | ai | system
on_behalf_of    participant_ref?        # агент или отложенная задача
```

Никнейм допускается **как отображаемое авторство**, но не как единственное полномочие на удаление файлов, просмотр technical logs или отмену чужого Job. В будущем Web/remote слой обязан установить более сильную identity boundary; это отдельная тема безопасности, однако observability не должна потерять первоначальную identity событий.

### 6.4. Время, порядок и конкурентность

Каждая запись содержит `occurred_at_utc` с timezone и `recorded_at_utc`/`observed_at_utc`, если событие пришло с другого устройства. Часы разных машин могут расходиться. **Порядок чата определяет узловой монотонный `sequence`**, назначаемый единым writer при принятии события, а не сортировка только по UTC timestamp. Для одного физического writer достаточно возрастающего sequence в durable journal, восстановимого после restart.

В приложении показывать локальное время пользователя; в логе сохранять UTC. При одновременных событиях от двух исполнителей causal order строится по `causation_event_id` и per-run порядку, а не по предположению, что события двух машин строго синхронны.

---

## 7. События, прогресс, результат, проблемы, технические логи: разные предметы

### 7.1. Шесть разных классов наблюдаемости

| Класс | Пользовательский вопрос | Источник истины | Хранение/доступ |
|---|---|---|---|
| `ChatMessage` | что обсуждали и какие действия инициировали? | conversation owner | общая лента по правам |
| `ExecutionEvent` | что действительно началось/завершилось? | execution authority | durability повышена, реплеится |
| `ProgressUpdate` | что происходит прямо сейчас? | executor/core | volatile/coalesced, checkpoint при существенной стадии |
| `DiagnosticFinding` | почему входные данные/расчёт вызывают сомнение? | domain owner | рядом с result/provenance, выборочная UI projection |
| `ProblemOccurrence` | какой отказ произошёл, где и какие последствия? | owner обнаруженного сбоя; platform recorder при доступности | durable typed record/ref + безопасные проекции |
| `TechnicalLog` / `Evidence` | что произошло на уровне API, файлов, exception и процесса? | локальный execution/platform owner | физический защищённый журнал, обоснованный доступ |

Дополнительно возможны **metrics** и **audit**. Metrics агрегируют нагрузку, длительность, ошибочность и состояние sinks; аудит фиксирует совершённые действия, полномочия и подтверждения. Ни то ни другое нельзя считать просто ещё одним видом UI event.

### 7.2. Предлагаемый маленький набор durable событий

На старте нужен **не всеобъемлющий Event Framework**, а 10–15 устойчивых фактов с ясной семантикой:

```text
thread.created / thread.renamed
message.created
run.submitted / run.admitted / run.started
step.started / step.completed
run.completed
artifact.published
problem.recorded / condition.raised / condition.cleared
run.recovery_required / run.reconciled
```

События `run.completed` содержат **явный outcome** (success/partial/cancelled/failure/unknown). `step.completed` также не означает `run.completed`. Progress heartbeat (`42/100`, «анализирую XLSX») **не обязан** материализоваться в journal каждый раз, иначе быстрые operations производят гигантские ленты. Достаточно последнего progress snapshot, а исторически значимые milestones могут превращаться в durable stage events.

### 7.3. Прогресс: процент — не всегда смысловая истина

Три степени прогресса:

1. **Стадия** — «Загрузка источников», «Проверка», «Расчёт», «Сохранение файла». Всегда возможна, если операция сообщает известный этап.
2. **Определённый числовой прогресс** — `current/total` с единицей измерения (файлы, шаги, строки, попытки), если denominator реально известен. Важно не путать «выполнено 8 из 10 шагов» с «готово 80% времени».
3. **Неопределённая активность** — spinner + этап + время с последнего подтверждения. Не следует искусственно вычислять процент или ETA из количества сообщений.

Прогресс составного сценария можно агрегировать по его **зафиксированному плану**, но доли stages должны быть явно объявлены и проверены на репрезентативной нагрузке. Без этого используем stage count и статусы отдельных шагов. Ограничить поток UI updates (например, коалесцировать частые изменения) и обязательно доставлять terminal event; telemetry может пропускаться без изменения итоговой истины.

### 7.4. Контракт нейтрального события — эскиз

Ниже **пример семантики, не действующий API**. Поля audience-sensitive присутствуют в **внутреннем canonical event**; наружу отправляется только server-side подготовленная projection.

```json
{
  "schema_version": 1,
  "event_id": "evt_01...",
  "sequence": 1442,
  "event_type": "run.stage_changed",
  "occurred_at_utc": "2026-10-10T00:11:24.173Z",
  "observed_at_utc": "2026-10-10T00:11:24.190Z",
  "node_id": "node-...",
  "thread_id": "thread-...",
  "run_id": "run-...",
  "job_id": "job-...",
  "step_run_id": "step-run-...",
  "attempt_id": "attempt-...",
  "actor_ref": "participant-...",
  "origin": "user",
  "causation_event_id": "evt_00...",
  "phase": "validate",
  "progress": {"mode": "indeterminate", "label": "Проверка источников"},
  "safe_summary_code": "run.validation.started"
}
```

`schema_version` — версия **контракта события Strategy Box**, а не версия AppDock. `sequence` назначает принимающий authority writer, а внешний worker может принести свой `producer_event_id`. Domain detail не сериализуется в один универсальный `dict[str,Any]` без ограничений: для важных видов событий задаются payload schemas.

### 7.5. Две оси исполнения и отдельная ось здоровья

**Lifecycle:** `prepared → admitted/queued → running → finalizing → terminal`; дополнительно `waiting_input`, `cancelling`, `reconciliation_pending` там, где подтверждены соответствующие механизмы.  
**Terminal outcome:** `SUCCESS | PARTIAL | CANCELLED | FAILURE | UNKNOWN`.  
**Node/diagnostics health:** `ready | degraded | unavailable | unknown` с отдельными owner-ами.

Почему это важно:

- `cancel_requested` не равно `CANCELLED`: worker мог уже опубликовать файл;
- `timeout` после write не равно `FAILURE` исходного эффекта: результат может быть `UNKNOWN`;
- `PARTIAL` может означать 8/10 успешно полученных файлов при двух известных сбоях; нужна ясная область применимости результата;
- `diagnostics degraded` при успешном расчёте — не повод менять расчёт на failure;
- `SUCCESS` выполнения Python не доказывает успешной **публикации** последнего файла или правильности экономической интерпретации.

### 7.6. Ошибки и их последствия

Предлагается двухуровневая модель:

```text
DomainFailure / ValidationFinding / StorageFailure
     │ (stable code, structured safe facts)
     ▼
ExecutionBoundary
     ├── run outcome = FAILURE / PARTIAL / UNKNOWN
     ├── optional local ProblemRecord (interim)
     ├── platform ProblemDraft → AppDock ProblemRef (when capability available)
     ├── localized user-facing summary
     └── restricted evidence refs
```

Событие/проблему должен **регистрировать один определённый owner**; другие consumer-ы ссылаются на запись. Если AppDock recorder не ответил, нельзя фабриковать подтверждённый platform `ProblemRef`. Допустимый переходный вариант — application `local_problem_ref` с явным `registration_status=local_only`; после доказанной передачи возможен mapping к платформенной ссылке. **Эти два ID нельзя объявлять взаимозаменяемыми** или выдавать неподтверждённую запись за зарегистрированную на платформе.

Пример разделения:

```text
safe UI:  Не удалось получить публикацию Банка России.
          Попробуйте позже или откройте диагностику.
          Код: source.transport.unavailable

technical evidence: HTTPS connect timeout, host/path, adapter details,
                    full exception chain, attempt timing, redacted headers

shared node:        Не отправлять уведомление всей команде,
                    пока проблема не затронула общий ресурс/сервис.
```

---

## 8. AppDock control plane / data plane / operational state: точное разграничение

Это важнейшее дополнение, появившееся после уточнения разработчика.

### 8.1. Термины следует определить локально

Слова **control plane** и **data plane** здесь используются как **архитектурная классификация ответственности Strategy Box**, а не как утверждение, что в AppDock уже существует готовый продуктовый интерфейс именно с такими именами.

**Control plane**: определяет *где* и *как* продукт существует — world/deployment profile, Node, managed roots, назначенный storage provider, lifecycle, identity/session, допустимые endpoints, capabilities и политику запуска. Эту часть в целевой схеме задаёт AppDock.

**Data plane**: реальные байты источников, промежуточных аналитических наборов, таблиц, отчётов и артефактов, которые читает/пишет предметный код. AppDock выдаёт путь или access handle для Data; semantics datasets и результатов принадлежит Strategy Box.

**Operational state plane**: *какие чаты и запуски существуют, что принято к выполнению, что завершено и что ещё неизвестно*. Это отдельная смысловая область — промежуточная между платформенным control и прикладным data. Её runtime authority принадлежит приложению Strategy Box (в границах соответствующего узла). AppDock выдаёт **физическую возможность хранения**. Описание и миграция схемы прикладной истории не становятся платформенными обязанностями автоматически.

**Diagnostics/evidence plane**: физические app logs, crash details, безопасные problem references, узловые health snapshots. Здесь распределённая ответственность: приложение владеет своими raw logs/domain evidence, AppDock — собственными platform incidents/problems и разрешённой передачей их refs.

### 8.2. Матрица размещения

| Данные | Семантический owner | Кто выбирает физическую площадку | Рекомендуемый root сейчас | Перспектива |
|---|---|---|---|---|
| `thread`, `message`, `run`, `job`, status, cursors | Strategy Box application authority | AppDock binding | AppDock-managed **system/user state**, не Data | AppDock-provided `StateStore` provider |
| технические app/worker logs | producer и application diagnostic owner | AppDock managed directories | `system/logs` или выделенная `user_private_system_dir/logs` по профилю | platform evidence integration |
| platform problem journal | AppDock observability | AppDock | AppDock-owned Node scope | platform Recorder / query |
| источники, кеши аналитики, XLSX/PDF/CSV и результаты | core + artifact owner | AppDock DataBinding | выбранное `Data root` / workspace | иной data/object provider при наличии |
| пользовательские визуальные предпочтения | client/application settings owner | AppDock user binding | per-user small config | sync/capability-limited |
| temp/cache, которые можно пересоздать | producer | AppDock runtime/cache | соответствующие временные корни | managed cache provider |
| installed packages/runtime/bin | AppDock Deployment/Runtime | AppDock | package/install/runtime roots | платформенный lifecycle |

**Критическое правило:** наличие файла `jobs.json` в `Data root` — плохой дефолт. Пользователь может переносить или очищать каталог рабочих данных; исчезновение Excel не должно стирать историю о том, почему он был создан. В то же время хранение больших XLSX внутри user/system state создаст проблемы с жизненным циклом и резервированием. Поэтому **метаданные исполнения и байты артефактов имеют разные bindings**.

### 8.3. Кто выбирает SQLite и кто создаёт таблицы

На целевом этапе AppDock Studio/WorldDefinition или подтверждённый managed runtime profile должны выбирать **класс физического state backend**: файловый, SQLite, внешний серверный provider и т.п. AppDock отвечает за provision, credentials, directory/connection authority, lifecycle, backup-capability declaration и передачу binding. Strategy Box получает строго типизированную возможность `StateStorageBinding` и строит поверх неё **свою** сериализацию/схему — таблицы, записи, индексы, domain migrations.

То есть **AppDock предоставляет storage как capability, а не «базу данных Strategy Box как свой домен»**. Платформа не должна принудительно вводить таблицы `runs`, `messages`, `artifacts`; приложение, в свою очередь, не должно без разрешения выбирать `C:\...\state.db`, открывать произвольный порт или самостоятельно устанавливать сервис БД в managed-контуре.

Существует и другой дизайн: AppDock мог бы предоставить уже нормализованную transactional key-value/document/event API, скрывая provider вообще. Это более сильная абстракция, но её нельзя обещать до появления versioned real contract. См. сравнительный анализ ниже.

### 8.4. Текущий минимум handshake без новой платформенной функции

**CURRENT совместимый маршрут:** использовать предоставленные AppDock `workspace.system_root` / `provided_system_dirs` и refs, прошедшие проверку Activation Context. Создать app-scoped path *внутри разрешённого root*, а не запрашивать пока несуществующий AppDock `create_database()`.

```text
AppDock Activation Context
    ├─ node_id / session_id / user identity
    ├─ managed system root / optional provided user-private root
    └─ Data root (separately)
           ↓
Strategy Box Adapter: resolve verified app-owned state root
           ↓
FileStateBackend(root, schema_version=1)
           ├─ write/append/read/recover
           └─ no ambient HOME lookup / hard-coded Windows paths
```

**Замечание по текущему `stratbox-windows`:** [`runtime/paths.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/paths.py) приоритетно использует `install_root_system_dir`, затем `workspace.system_root`. Это наблюдаемый код, а не нормативное решение для всех будущих профилей. Чтобы гарантировать сохранность состояния при update/uninstall, необходимо проверить фактический lifecycle и ownership конкретного provided root; при необходимости явно договориться об отдельном AppDock user/state root.

### 8.5. Кандидат будущего `StateStorageBinding`

**Это минимальная форма обсуждения с AppDock, а не предлагаемый к немедленному добавлению контракт в его репозиторий:**

```yaml
binding_version: 1
binding_id: strategy_box_state
scope: node                     # local_user | node | installation
storage_kind: file_directory    # later: sqlite | service | document_store
location_ref: appdock-managed-opaque-ref
capabilities:
  read: true
  append: true
  atomic_replace: true
  single_writer: required
  transaction: false
  durable_flush: declared
  local_filesystem: true
policies:
  backup_owner: appdock_or_deployment_profile
  retention_profile: app_default
  on_uninstall: preserve_or_confirm
```

**Почему `location_ref` лучше абсолютного пути в публичных моделях:** приложение может разрешить физический путь только локальным адаптером; клиент Android/Web получает ссылку на объект/API, не путь на диске хоста. Будущая SQLite-вариация предоставляет либо разрешённый local database path, либо ограниченный connection handle/endpoint. Приложение обязано сверять capabilities перед обещанием атомарности.

### 8.6. Принцип единственного писателя

Независимо от SQLite, PostgreSQL или файла, для общего узла нужен **один логический authority writer** на приём событий и переходов статуса. На первоначальном desktop это один application process с сериализованной очередью записей. На host — headless узловой runtime/service, к которому обращаются клиенты. Даже если файл технически доступен по SMB/NFS, каждый Windows/Web/Android клиент **не должен открывать его для конкурентной записи**.

Это одновременно решает:

- единый порядок событий и `sequence`;
- безопасное распределение `run_id` и `attempt_id`;
- дублирующиеся submit после reconnect;
- завершение и восстановление jobs;
- независимость от конкретной физической СУБД.

Политика «один writer» — смысловой контракт и может сохраняться даже при переходе к СУБД, которая допускает несколько физических writers.

---

## 9. Переходное файловое хранилище вместо немедленной SQLite

### 9.1. Рекомендуемая физическая схема v0

Следующая раскладка **логическая**; физическая корневая директория и политика сохранения выделяются AppDock. Это приложение **не** должно захардкоживать приведённое имя каталога или считать `Data root` подходящим местом для state.

```text
<app_state_binding>/
  manifest.json             # version, node binding, writer identity/epoch
  journal/
    000001.events.jsonl     # append-only, complete event records
    000002.events.jsonl
  snapshots/
    state.v1.json           # latest verified projection, replace atomically
    state.v1.previous.json  # optional last verified version
  jobs/
    <run-id>/               # optional per-run receipt/manifest refs
  indexes/
    recent.json             # reconstructible optimization; optional

<app_logs_binding>/
  app/
    <process-or-session-id>.log
  operations/
    <run-id>/<attempt-id>.jsonl
  crashes/
    <process-or-session-id>.fatal.log
```

Для первых нескольких операций **можно ещё проще**: единый `events.jsonl` + один `snapshot.json` + отдельные operation log files. Сегментацию и indexes вводить при первых подтверждённых объёмах/потребностях; главное — уже иметь schema version, writer, sequence и recovery. **Не создавать 15 новых директорий, пока нет потребителей.**

### 9.2. Почему append-only JSONL лучше пяти переписываемых JSON-файлов

**Плюсы:**

- человечески читаемо, доступно без SQLite/DB migration tools;
- каждое значимое изменение сохраняется как новый факт, не требует переписывать всю историю;
- replay восстанавливает snapshot, обнаруживая незакрытые runs;
- видно каузальную последовательность и источник изменений;
- легко построить export/migration в иной storage provider;
- подходит под существующую Python/Qt технологию.

**Минусы и границы:**

- запись нескольких связанных файлов **не становится транзакцией**;
- append может оборваться на части JSON-строки;
- файловая система, flush/fsync и AV/OS hooks влияют на durability;
- один journal writer должен быть строго обеспечен;
- выборка/полнотекстовый поиск хуже БД;
- клиентам по сети давать прямую запись нельзя;
- частое сохранение огромных снапшотов ухудшает latency;
- journal eventually растёт и требует segment rotation/compaction.

Правильный вывод: JSONL достаточен как **ограниченная начальная authority для одного writer**, а не как вечная distributed database.

### 9.3. Схема commit/replay без ложной атомарности

Предлагаемый bounded write-path:

1. Проверить событие по строгой схеме, размеру, разрешениям и ссылкам.
2. Под execution-authority выделить новый `sequence` и `event_id` (для повторной доставки сохранять тот же ID).
3. **Одной защищённой записью** добавить весь компактный JSON + завершающий newline в активный сегмент (при необходимости сериализованным writer queue). Не обещать crash-atomic append на каждом backend.
4. Выполнить `flush`/`fsync` в точках требуемой durability. Если нужно сообщить клиенту «принято к долговечному исполнению», acknowledgment должен следовать только после выполнения принятой guarantees.
5. Публиковать событие в UI/subscribers после установленной точки приёма, либо честно различать `accepted_in_memory` и `durably_admitted`.
6. Периодически создавать snapshot во временном файле в **той же разрешённой файловой области**, записать checksum/schema/version/last_sequence, flush, затем `os.replace` только если конкретная файловая система поддерживает требуемый atomic replace; после этого сохранить evidence для recovery.
7. На restart проверить manifest/segment sequence/snapshot checksum, воспроизвести journal после последнего snapshot; завершённую неполную строку не «додумывать» и не объявлять подтверждённым событием. Tail corruption — отдельный диагностический факт.

**Очень важная оговорка:** `os.replace` даёт полезную атомарность переключения имени в пределах поддерживаемой файловой системы, **но само по себе не гарантирует crash durability** на любой платформе/storage backend. Сохранность требует отдельной проверки fsync/directory/handle semantics и fault-injection на выбранном AppDock binding. При network filesystem эти свойства нельзя просто предполагать.

### 9.4. Отчего нельзя «просто читать и писать JSON в нескольких клиентах»

При конкурентной записи из двух приложений получатся lost updates (`run_A` стёр `run_B`), перекрытия имен/IDs, непредсказуемый порядок и возможные разрывы записи. `thread.lock` внутри одного GUI защищает только тот GUI, не другие процессы и не сетевых клиентов. Изоляция writers должна находиться **в узловом application authority**; чтение клиентам предоставляется через read model/query/subscription.

### 9.5. Правила retention и компактизации

Разделить **долговечную значимую историю** и **объёмные технические свидетельства**:

- факты `run.started`, `run.completed`, `artifact.published`, `problem.recorded` сохранять согласно сроку product history;
- частые progress ticks в долговременный журнал не писать;
- текстовые/JSONL operation logs ограничивать размером и возрастом;
- snapshot/cache можно перестроить из canonical journal;
- history/archive pruning делать только по выбранной retention policy и проверенному snapshot/export; иначе «компактизация» уничтожит единственную истину.

**Численные сроки retention и объёмы здесь НЕ утверждаются**: они зависят от deployment profile, доли пользователей, банковских данных и корпоративных требований. На пилоте полезны конфигурируемые лимиты и событие `retention.pruned`, но значения принимать после измерения.

### 9.6. Как перейти к SQLite позже

Когда AppDock реально предоставит типизированный storage backend:

```text
FileStateBackend(events + snapshots)
         │ export versioned event/snapshot manifest
         ▼
Migration verifier (count / IDs / state digest / sample replay)
         ▼
AppDock-provided SQLite/other binding
         ▼
SQLiteStateBackend / ServiceStateBackend
         │ atomic import + cursor validation
         ▼
Node read/write authority switches only after verified completion
```

Схему и migrations определяет application owner. AppDock предоставляет новый binding и владеет provisioning/backup policy. **Не требовать поддержку старых API**: достаточно один раз корректно импортировать подлежащие сохранению пользовательские данные; программные compatibility shims можно не сохранять.

### 9.7. Почему SQLite не нужна немедленно

Наиболее дорогой риск текущего прототипа — неверная семантика статуса и отсутствующий single writer, а не недостаток SQL. SQLite автоматически даёт транзакции и query, **но не устраняет** неправильный lifecycle, смешение чата с попыткой, передачу secrets в лог или неопределённость внешнего эффекта. Внедрение её раньше определения binding с AppDock создаст инфраструктурный долг и спор об owner-ах.

Позднее SQLite будет сильным кандидатом для **локального файла на одном host**: документированная WAL-изоляция разрешает одновременных readers и writer, но действует ограничение одной машины и одного writer в момент времени; WAL **не работает поверх сетевой ФС между разными машинами** [EXT-7][EXT-8]. Поэтому host SQLite + API clients — допустимая комбинация; «SQLite в общем сетевом каталоге, в который пишут все клиенты» — нет.

---

## 10. Сопоставление альтернатив

### 10.1. Storage (главная развилка с учётом AppDock)

| Подход | Преимущества | Ограничения/риски | Решение для Strategy Box |
|---|---|---|---|
| Пять JSON-проекций, как сейчас | минимум кода, человекочитаемые файлы | перезапись, split-brain, silent corruption, невозможно безопасно разделять writers | оставить только как временную local UI projection; заменить authority |
| **Один append-only journal + проверяемые snapshots** | простота, причинная история, переносимый API, не требует СУБД | write/recovery tests, поиск дорог, single writer | **лучший переходный вариант** |
| SQLite, выданная AppDock в локальном node scope | транзакции, query, конкурентное чтение, зрелая встроенная технология | AppDock binding пока не определён; не network-file DB; migration/backup semantics | сильный будущий provider |
| PostgreSQL/серверное хранилище в host plane | высокие требования multi-client, ACL, администрирование, concurrent writes | значительное операционное усложнение | рассматривать при реальной удалённой нагрузке/сервисной архитектуре |
| AppDock-provided transactional storage API | строгая инверсия зависимости, сменяемые реализации, lifecycle у платформы | такого стабильного провайдера пока не подтверждено; риск чрезмерной общей абстракции | целевая опция, обсуждать как отдельный платформенный контракт |
| Прямые общие файлы с сетевыми locks | быстро начать collaboration без сервиса | recovery, locking/network partitions, доступ к raw state, races | **отклонить** как модель authority |

### 10.2. Наблюдаемость и трассировка

| Подход | Сильная сторона | Недостаток | Рекомендация |
|---|---|---|---|
| Только Python `logging` | простая диагностика кода | не определяет outcome, shared UI, problem semantics | обязательно как **technical sink**, недостаточно в одиночку |
| Domain `Result` + progress callback | работает в Colab/Jupyter, предметно точно | не хранит durable jobs и shared state | обязательный минимальный порт core |
| Event journal + projections | прозрачный lifecycle, replay, общий UI | требует authority и конвенций событий | основной application слой |
| Полный OTel + Collector/Tempo/Loki/Jaeger | стандартный экспорт traces/logs/metrics, масштабируется | лишняя сложность пилота, сбор чувствительных данных, зависимость от deployment | **не включать как prerequisite**; оставить optional exporter |
| AppDock canonical ProblemOccurrence | общий платформенный словарь и product-safe ошибки | external product registration пока требует реального SDK/контракта | использовать после подтверждённого capability negotiation |
| Каждому клиенту свой локальный log/DB + синхронизация | автономность одного клиента | разные версии истины, конфликты, ложные уведомления | разрешить только вторичную клиентскую диагностику |

### 10.3. Конкурентное исполнение

| Подход | Плюсы | Почему принять или отвергнуть |
|---|---|---|
| Один Qt `QThread`/один scenario | уже работает, просто | **не соответствует** параллельным чатам; не headless |
| ThreadPool для операций + serialized state writer | минимальный путь для I/O-bound сценариев | GIL, CPU-heavy блокировки, shared mutable state | **пилот v1** при ограниченных ресурсах |
| ProcessPool/subprocess workers + single authority | изоляция CPU-heavy и аварий библиотек | сериализация, запуск, cancellation, memory overhead | добавить адресно для тяжёлых операций |
| Distributed queue/Celery-класс | worker fleets, retry scheduling | broker, эксплуатация, policy burden | не оправдан до реального host/multi-node профиля |

**Связь с исследованиями фона:** фоновые триггеры, user actions, AI invocations и scheduled tasks в перспективе должны приводить к тому же `Run/Job`. Отдельный «бэкграундовый мир» с собственными статусами и логикой ошибок избыточен.

---

## 11. Физические логи, падения процессов и диагностика, которая переживает ошибку

### 11.1. Четыре уровня записи

**1. Product events:** короткая durable запись «какой запуск, стадия, статус, что произошло». Не сохраняет traceback и секреты. Образует общий timeline.

**2. Technical application log:** проблемы настройки, загрузки modules, exceptions, производительность, IO, переходы/адаптеры; доступен локальному оператору/диагностике. Он может содержать ограниченно чувствительные факты, потому требует правильных permissions и очистки перед пересылкой.

**3. Per-attempt operation log:** детальная хронология конкретной попытки операции. Должен содержать `run_id`, `attempt_id`, `step_run_id`, `operation_name`, `event_id` и, при наличии, platform `problem_ref`. Никогда не полагаться только на имя файла как идентификатор. Успешный результат может ссылаться на журнал, но не должен обязательно публиковать его содержимое всем.

**4. Crash/emergency evidence:** критические падения, повреждение state, невозможность открыть обычный log sink. Хранится отдельно и не зависит от нормального Qt UI. Потеря обычного логгера должна быть наблюдаемым дефектом, но не должна вызывать бесконечную рекурсию записи ошибки о невозможности записать ошибку.

### 11.2. Минимальный structured log record

```json
{
  "schema_version": 1,
  "occurred_at_utc": "2026-10-10T00:11:24.173Z",
  "level": "ERROR",
  "component": "stratbox.application.execution",
  "code": "operation.unexpected_exception",
  "node_id": "node-...",
  "process_id": 2448,
  "thread_id": "thread-...",
  "run_id": "run-...",
  "attempt_id": "attempt-...",
  "operation_name": "escrow.history.export",
  "event_id": "evt_...",
  "safe_message": "Ошибка выполнения операции",
  "evidence": {"exception_type": "TimeoutError", "traceback_ref": "local-log-ref"},
  "visibility": "technical_restricted"
}
```

Raw stack/URL/private paths могут храниться отдельным protected evidence payload при наличии причинной необходимости. `safe_message` — только подготовленный текст. **Параметры операции нельзя сериализовать целиком через `str(params)`**: для них требуется `OperationParamSpec` с классификацией `public`, `private`, `secret`, отдельными правилами `display/log/persist`.

### 11.3. Ротация и одновременное логирование

В Python стандартные `RotatingFileHandler` и `TimedRotatingFileHandler` подходят для одного пишущего процесса. Но официальный **Logging Cookbook** прямо отмечает: стандартный `FileHandler` не даёт безопасной записи **несколькими процессами в один файл**, хотя поддерживает потоки одного процесса [EXT-4]. Поэтому:

- в ближайшем варианте одна очередь лог-записей и один writer на физический журнал;
- при subprocess workers — отдельные per-worker/per-attempt logs или Queue/Socket logging к одному центральному писателю;
- log files именуются уникальной попыткой или процессом, а не только типом операции;
- файловые границы и retention отражаются в metadata; удалённому клиенту отдаётся log **reference / sanitized excerpt**, а не абсолютный путь;
- `log_ref` разрешается физическим adapter на стороне узла.

### 11.4. Fatal exception: что реально можно поймать

Предлагаемый минимальный механизм для Windows/Python:

1. Инициализировать отдельный открытый crash-log file handle **до запуска тяжёлых модулей и Qt**.
2. Включить `faulthandler.enable(file=...)`, если позволяет runtime; логический факт ошибки сохранять через обычный application logging, пока интерпретатор жив.
3. Обработать boundary-level `sys.excepthook`, `threading.excepthook`, Qt worker errors и startup exceptions, передавая их в контролируемый technical sink; hooks не являются гарантией при process kill/power loss.
4. AppDock/process supervisor, если текущий профиль действительно предоставляет supervision, должен сопоставлять process exit/heartbeat и ранее записанное terminal outcome. При полном crash *без последнего события* делать `reconciliation_required`, а не писать «сценарий отменён».
5. При следующем старте искать attempts с `started` без terminal receipt; показывать пользователю «Выполнение прервалось. Итог требует проверки» и открывать read-only диагностику.

Официальный `faulthandler` может писать traceback при фатальных сигналах и Windows exceptions, однако даже он **не гарантирует** данные после отключения питания, убийства процесса или критического отказа среды [EXT-5]. Важно удерживать файловый descriptor открытым: переиспользование/rotation целевого файла может направить fatal output не туда.

### 11.5. Различать сбой исполнения и сбой самого log sink

| Ситуация | Что должен делать продукт |
|---|---|
| Операция успешна, logger временно недоступен | Сохранить success, отдельно выставить `diagnostics_degraded`, если требуемая гарантия логов допускает |
| Не получается подтвердить **обязательный** журнал опасной операции до её начала | Заблокировать опасный эффект до выполнения, показать понятную причину |
| Worker умер, неизвестно совершена ли запись файла | `OUTCOME_UNKNOWN`, проверить output/effect receipt |
| Не хватает места для journal admission | Не принимать новый durable Job как принятый; разрешить диагностику и очистку по политике |
| Передача platform problem не удалась | Сохранить `local_problem_ref`, registration status `not_written/unknown` в своей области; не выдумывать platform ref |
| Нечитаемая история | Degraded/read-only/recovery, а не новая пустая authority на её месте |

Какие категории действий требуют **обязательного аудита**, а какие best-effort logging — продуктово открыто. В пилоте достаточно консервативного запрета на необратимые file operations без подтверждения разрешений и результата; полнота audit policy будет зависеть от юридического/организационного контура.

---

## 12. Пользовательский чат и визуальная диагностика

### 12.1. Все чаты команды — но правильные владельцы

**DEVELOPER:** в пределах доверенного узла каждый участник должен видеть общие чаты, включая новые, созданные коллегами. Для этой цели нужны:

```text
Node Chat Directory
  ├─ thread_id
  ├─ title
  ├─ created_by / created_at
  ├─ last_activity_sequence
  ├─ active_run_count
  ├─ unread cursor per participant
  └─ access/visibility profile
```

Название по умолчанию **«Новый чат»**; рядом — меню `⋯`, где пользователь сможет переименовать чат. Переименование меняет metadata, **сохраняет thread ID и историю**. При создании чата первый meaningful message или запуск получает определённую запись. Параллельные названия «Новый чат» допустимы: identity не зависит от заголовка. Удаление/архивирование чатов и права на них — отдельный продуктовый вопрос.

**Поток событий для клиентов:** после node-wide admission событие `thread.created` появляется у остальных подключённых клиентов (через будущую subscription API). При reconnect клиент запрашивает snapshot + события после последнего `sequence`; запоздалые и дублированные события обрабатываются по `event_id`/sequence.

### 12.2. Вид в списке чатов

| Состояние | Минимальное отображение | Что считать источником |
|---|---|---|
| Один активный run | «Выполняется», индикатор | подтверждённый Job/Run lifecycle |
| Несколько активных runs | «Выполняются 2», компактная иконка | агрегат узловой authority, а не Qt busy flag |
| Задача в очереди | «В очереди» | accepted job state |
| Последний run завершён | статус последнего завершения + время | durable terminal event |
| Есть проблема/unknown | жёлтая или красная метка с объяснением | typed outcome/problem projection |
| Чат другой команды/автора | никнейм/аватар | actor display из participant registry |
| Есть непрочитанные | счётчик/точка | `read_cursor(node, participant, thread)` |

Цвет **не может** быть единственным носителем состояния: использовать короткую надпись, tooltip и пиктограмму с доступным текстовым названием. Это согласуется с будущими Web/Android/accessibility требованиями.

### 12.3. Внутри чата: событие vs сообщение

Для действия пользователя:

```text
[10:13] Аналитик Иван · запустил «История счетов эскроу»
        [Выполняется · Проверка источников]
        [Задача: R-123]

[10:15] Система · готово 8 из 10 источников
        2 источника пропущены с замечаниями

[10:16] Система · Выполнено с замечаниями
        Результат: escrow_2026.xlsx
        [Открыть] [Показать результат] [Диагностика]
```

Пример именно **UX**, а не реальные данные. Progress card должна **обновляться по run ID**, а не добавлять отдельное chat message каждую секунду. Durable terminal message публикуется один раз. Пользовательские и AI-реплики живут отдельно от system run card. При смене выбранного чата выполняющийся Job продолжает работу.

### 12.4. Инспектор запуска

Рекомендуемая минимальная группировка:

- **Обзор:** сценарий, автор, дата, длительность, узел, текущая стадия, terminal outcome; при UNKNOWN — явное предупреждение об уровне подтверждения.
- **Шаги:** список executed/pending/skipped этапов с коротким reason code; при нескольких attempts — сворачиваемая история.
- **Результаты:** только подтверждённые artifacts и основные показатели (files count, rows, snapshot time, validation warnings).
- **Диагностика:** безопасное описание и код проблемы, «скопировать ID», допустимое действие (`Повторить`, `Проверить`, `Открыть состояние узла`) по actual permission.
- **Технический журнал:** опциональная панель с ограниченным tail, где каждый просмотр проверяет текущий доступ к логу; удалённые клиенты не читают arbitrary paths.

Не нужно одновременно показывать пользователю 12 UUID. В обычной карточке достаточен короткий `run_ref`; полный ID и `problem_ref` доступны через детали/копирование для техподдержки.

### 12.5. Центр задач и фоновых процессов

Независимо от чатов полезен маленький агрегированный экран «Выполнения» / «Фоновые процессы»: `running / queued / requires_attention / recent`. Пользователь видит сценарий, автора, прогресс, ресурс, кнопку перехода в исходный чат. **Отдельный executor для фоновых задач создавать не нужно:** экран агрегирует те же Runs и Jobs.

В ближайшей версии экран должен показывать только реально исполнимые фоновые функции. Декларация `enabled=true` при отсутствии scheduler не должна визуально подтверждаться как работающий фоновый процесс.

---

## 13. Видимость чужих ошибок и узловые предупреждения

### 13.1. Правило «общие чаты» не равно «общие raw logs»

Наличие общей команды и узнаваемых никнеймов существенно упрощает социальные сценарии, но не защищает от случайного вывода токена, пароля, внутреннего пути или данных другого пользователя в traceback. Поэтому три уровня:

**A. Shared timeline:** факт запуска, его автор и исход, краткий предметный результат и опубликованный артефакт. Доступно участникам по фактической политике чата/узла.

**B. Shared condition:** узловая проблема, которая затронула общий ресурс, например недоступный общий Data root; сообщение показывается всем участникам области воздействия.

**C. Restricted technical evidence:** полные логи, исключения, network URL, параметры, machine paths, support bundle — доступны только авторизованному диагностическому owner, локальному оператору или делегированной поддержке.

Это соответствует принципам [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) и [NIST SP 800-92](https://csrc.nist.gov/pubs/sp/800/92/final), но конкретная политика доступа должна быть принята для поставки Strategy Box.

### 13.2. Простая матрица scope

| Вид сбоя | Пример | В чате | Пуш другим участникам | Технический лог |
|---|---|---|---|---|
| Personal | автор ввёл неверный параметр | карточка run, видимая по политике чата | **нет** | локальный per-attempt |
| Case/Thread | конкретный сценарий завершён с ошибкой | да, с safe code | по умолчанию нет отдельного alert | локальный protected |
| Shared resource | host Data root недоступен | impacted runs | **да**, по охвату затронутых сессий | на host; platform health если поддерживается |
| Node/system | state writer не может зафиксировать новые jobs | safe node condition | **да**, общий баннер | emergency/platform logs |
| External source | один сайт ЦБ недоступен | соответствующие Runs | возможно при повторяемости для нескольких задач | per-attempt network evidence |
| Security-sensitive | зафиксирован отказ разрешения | минимум фактов для автора | только соответствующему operator scope | restricted audit/evidence |

**Не следует** уведомлять всех при каждой ошибке парсера. Это создаст шум и быстро уничтожит ценность уведомлений.

### 13.3. Condition — состояние, а Problem — occurrence

Один и тот же gateway может породить 30 отдельных неуспешных attempts. Для UI команды полезнее **один актуальный Condition** `external_source_unavailable`, привязанный к affected scope и времени, и счётчик связанных occurrences. Condition очищается только после реального health-check или успешного действия owner, а не потому, что пользователь скрыл баннер.

```text
Problem P1 (attempt A1) ─┐
Problem P2 (attempt A2) ─┼─> Condition C1 (resource R, node N)
Problem P3 (attempt A3) ─┘          └─> Warning for affected participants
```

Это целевой pattern. Пока AppDock platform Condition interface не реализован полностью, application authority может хранить маленькую локальную `shared_warning`/condition projection с явным owner и lifecycle, **не называя её платформенным зарегистрированным Incident**.

### 13.4. Дедупликация и предотвращение alarm fatigue

Для группировки пригоден `fingerprint = (problem_code, affected_resource_ref, node_scope, schema_version)`; избегать fingerprint по полному тексту исключения и пользовательскому имени. Группировать **интервал одинакового ресурса/проблемы**, хранить first/last seen, count, last successful probe и close reason. При изменении impact/severity condition может быть обновлён отдельным событием. Повторное получение `event_id` не должно увеличивать count.

**Важное противоречие:** дедупликация shared alerts должна сохранять отдельные attempts для диагностики. Нельзя «сэкономить» события исполнения путём их физического удаления при группировке предупреждений.

### 13.5. Ошибка у другого пользователя: кому принадлежит лог

По замыслу разработчика логи действий участника, исполнявшихся локально, остаются на его устройстве; для host execution — на хосте. Это логически соответствует **месту фактического исполнения**, но требует различать:

- *origin device*: откуда отправили запрос;
- *execution node*: где шёл Python/worker;
- *state authority node*: где durable Run/Job;
- *log custody*: где физически находятся evidence bytes;
- *viewer device*: где человек открыл chat projection.

Наличие локального клиента **не даёт** ему права читать `C:\...` хоста. Shared событие должно содержать `log_ref`, а host/owner решает, какую часть журнала показать. Если файл удалён/недоступен, ссылка в UI должна стать «Журнал недоступен», не формируя ложный traceback.

---

## 14. Причинная связность при параллельности и внешних эффектах

### 14.1. Четыре независимые конкуренции

1. **Разные чаты:** самостоятельные Runs могут выполняться одновременно — это прямое требование.
2. **Один чат:** несколько запусков тоже могут пересекаться, если пользователь не запретил этого.
3. **Один output file/Data resource:** одновременная запись требует ресурсных claims/lock/unique output paths; иначе даже разные чаты конфликтуют.
4. **Одно shared state:** единственный authority writer должен сериализовать принятие событий и переходы статусов независимо от числа workers.

Не стоит управлять ресурсами правилом «один активный Run на чат» — чат не является ни файлом, ни CPU, ни сетевой квотой.

### 14.2. Минимальная политика для первого concurrent JobManager

**TARGET v1:** ограниченный пул workers; одна очередь admission; per-run immutable execution context; независимые loggers; output paths с run-scoped staging; resources с явным `read/write/exclusive` profile. При невозможности выдать resource claim — `queued/waiting_resource`, а не `failed` и не silent overwrite.

`OperationSpec` со временем должен декларировать хотя бы `requires_workspace`, `mutates_data`, `resource_keys`, `supports_cancel`, `retry_policy`, `expected_artifacts`. Две операции, пишущие в общий canonical workbook, должны либо иметь разные версии output, либо получать exclusive claim на финальную публикацию.

### 14.3. Effect truth и доказательства

Сценарий «операция записывает Excel» состоит из разных фактов:

```text
1) output planned
2) stage bytes written
3) stage bytes verified
4) publish intent
5) commit/rename attempted
6) published artifact observed/verified
7) artifact published event
8) Run terminal outcome
```

Если процесс упал между 5 и 6, **`UNKNOWN`** относится к результату публикации, даже если computational core уже завершился. На рестарте нужно проверить staged/published object, digest, commit marker/receipt и только после reconciliation выставить подтверждённое состояние. Простое повторное скачивание/удаление файла опасно.

Для read-only download без побочных эффектов retry может быть автоматическим. Для публикации поверх existing output или удаления файлов retry требует idempotency и scope validation. `cancel_requested` до effect и после commit имеют разные последствия.

### 14.4. AppDock process termination vs semantic result

AppDock способен наблюдать факт окончания дочернего процесса и причину (`exit`, timeout, killed) в реализованном process-supervision контуре. Это **не равнозначно** аналитическому `run.completed`: процесс мог вызвать внешний эффект и умереть до записи receipt. Сторона исполнения отвечает за подтверждение domain output; платформа сообщает, что произошло с процессом/сессией. Не следует автоматически выставлять `CANCELLED` только потому, что пользователь закрыл окно.

### 14.5. Таймлайн сквозной корреляции (пример)

```text
10:00:00  thread T created [N / user U]
10:00:05  run R admitted [scenario S, thread T]
10:00:05  job J started [attempt A1, trace optional]
10:00:06  step W1 started [source fetch]
10:00:08  progress 5/12 sources [volatile]
10:00:11  step W1 partial [2 unavailable, validation records]
10:00:12  step W2 started [compute]
10:00:16  artifact stage created [staging-45]
10:00:17  publish intent written
10:00:17  connection to output store lost
10:00:18  job J outcome UNKNOWN [effect status requires verification]
10:02:40  resource online, reconciliation scheduled
10:02:42  artifact digest verified, committed object found
10:02:43  publication verified
10:02:44  run R reconciled [domain result PARTIAL due to missing sources]
```

Это иллюстрация **почему** журнал должен содержать отдельные события intent, effect receipt и reconciliation, а не только последний текст `Operation failed: ...`.

---

## 15. Внешние стандарты, научные работы и применимость

### 15.1. Google Dapper (Sigelman et al., 2010)

Исследование Google Dapper [EXT-1] показывает пользу дешёвой сквозной **причинной корреляции** между частями системы. Из него для Strategy Box следует прежде всего не требование немедленно развернуть distributed tracing backend, а нужда связывать `run → job → attempt → external call → artifact` так, чтобы инженер мог ответить «почему это завершилось так». Полноценный sampling и trace storage оправданы только при распределённой реальной нагрузке. Для значимых terminal/effect events sampling **недопустим**: они нужны полностью и должны храниться независимо от sampling будущих traces.

**Альтернатива:** сделать все сообщения в чате «логом» без причинных IDs. Такая система удобна для просмотра, но плохо работает при параллельных jobs и retry; её отвергаем как инженерную authority.

### 15.2. OpenTelemetry Logs Data Model

Стандарт OTel [EXT-2] различает `Timestamp` и `ObservedTimestamp`, `TraceId`, `SpanId`, `Severity`, `Body`, `Attributes`, `Resource` и scope. Это хороший **reference schema** для технического лога; он не навязывает хранить chat messages и предметные результаты в OTel. Разработать маленький Strategy Box event/log envelope с совместимыми именами и при необходимости добавить exporter позднее — минимально достаточный путь.

### 15.3. W3C Trace Context и запрет утечек через baggage

W3C [EXT-3] описывает `traceparent`/`tracestate` для переноса причинной трассы через HTTP. При переходе на будущие remote tools, MCP или A2A полезно передавать trace context через **разрешённую границу**. Однако внешним публичным статистическим источникам нет нужды знать внутренние `node_id`, `participant_id`, `chat_id`, secret tokens; автоматическая отправка таких данных в tracing baggage может нарушить границу доверия. OTel специально предупреждает об этом [EXT-11].

### 15.4. CloudEvents

CloudEvents [EXT-6] формализует `id`, `source`, `type`, `specversion`, а `time` и `subject` — как полезные необязательные атрибуты. Его vocabulary подходит для **внешнего события** при будущих подписках, но внутренний event journal может быть проще. Реализация CloudEvents 1.0 целиком ради двух локальных чатов избыточна. Если понадобится event export, сделать deterministic mapping из canonical Strategy Box event.

### 15.5. RFC 9457 Problem Details

RFC 9457 [EXT-12] применим к будущим **HTTP Web API**: стабильные machine-readable `type`, `instance` и пользовательская `detail`, а не сырой traceback в ответе сервера. Он **не заменяет** AppDock `ProblemRef`: HTTP Problem Details — формат ответа на HTTP-запрос, платформенная проблема — зарегистрированное диагностическое событие, которое может существовать после завершения HTTP-сессии. Между ними потребуется adapter.

### 15.6. Python logging + faulthandler

Стандартная библиотека [EXT-4][EXT-5] даёт почти всё необходимое для первой физической диагностики: file/rotation/queue handlers, context filters и fatal dump. Преимущество — отсутствие новых тяжёлых зависимостей. Недостаток — сама Python logging system не создаёт transactional execution authority, не обеспечивает end-to-end сохранность событий и не обладает межпользовательскими правами.

### 15.7. OWASP и NIST

OWASP [EXT-9] прямо рекомендует удалять или маскировать access tokens, credentials, session identifiers, чувствительные персональные/коммерческие данные, а также аккуратно обращаться с paths/network names. NIST SP 800-92 [EXT-10] систематизирует log management и retention. Для Strategy Box это прежде всего аргумент в пользу **разных аудитории и физического хранения** user notice и raw evidence. Не стоит строить на этом оправдание сложной SIEM-системы до появления реального эксплуатационного запроса.

### 15.8. SRE «four golden signals» и метрики

Google SRE [EXT-13] предлагает latency, traffic, errors, saturation как полезный минимальный набор мониторинга сервисов. Для Strategy Box их аналогами могут стать:

- **latency:** duration операций по типу, включая отдельно failed и successful;
- **traffic:** submitted/started runs и downloads по времени;
- **errors:** доля failures/partials/unknown с раздельными denominators;
- **saturation:** активные workers, очередь, время ожидания resource claim, свободное место state/log root.

При малом числе операций достаточно **локально агрегируемого JSON diagnostics snapshot**; Prometheus/Grafana, remote collector и алерты по минутным SLO пока избыточны. Метрики не должны содержать `run_id`/`user_id` как высококардинальные labels: OTel прямо предупреждает об увеличении стоимости хранения из-за таких атрибутов [EXT-14].

### 15.9. SQLite WAL и практические границы

Официальная документация SQLite [EXT-7][EXT-8] обеспечивает два важных факта: одновременно читающие и пишущий могут работать в WAL на одной машине; network-filesystem deployment WAL между разными хостами не поддерживается. Это подтверждает, что **будущая база на host + API для клиентов** осмысленна, а общая открываемая SQLite БД на SMB share — плохая архитектура. При этом рекомендация пользователя использовать сейчас файловую переходную реализацию полностью согласуется с этими ограничениями.

### 15.10. Что стандарты не решают за Strategy Box

Ни один из перечисленных стандартов не определяет:

- кто владеет аналитическим исходом `PARTIAL` и правдой о публикации XLSX;
- должно ли пользовательское имя быть только display или strong identity;
- какая стадия считается 50% выполнения конкретного эконометрического расчёта;
- как ввести общие чаты в AppDock host-профиле;
- кому и как показывать чужие ошибки;
- должен ли процесс продолжаться после закрытия Windows surface;
- какой AppDock storage binding действительно предоставляется installed runtime.

Это **предметные Product/engineering решения**, которые и составляют полезность настоящего исследования.

---

## 16. Минимальная реализация и этапы развития

### 16.1. Этап 0 — исправить честность CURRENT (без новой инфраструктуры)

**Рекомендуется первым** в отдельной будущей задаче разработки:

1. Убрать raw `str(exc)` из persisted case/event/GUI. Ввести stable safe error code и protected exception log.
2. Добавить `thread_id` и `run_id`; разнести `operation_name` и identity попытки. Сохранить соответствие прежней карточки Case одному Run в UI projection.
3. Сделать `LogRef` вместо OS-absolute `path` в переносимой application model; physical locator — только adapter.
4. Ввести конечные `SUCCESS/PARTIAL/CANCELLED/FAILURE/UNKNOWN` (или эквивалентную строго отделённую outcome-модель), **не смешивать warning с lifecycle**.
5. Добавить rotating/bounded logs и строгий log writer lifecycle. Исправить operation log name на per-attempt.
6. Убрать молчаливое `corrupt history → []`, заменить typed `HISTORY_CORRUPT` и безопасным восстановлением.
7. Привести тесты/manifest/version drift к актуальным contracts, чтобы дальнейшая интеграция давала достоверный сигнал.

Стадия не требует SQLite или нового AppDock SDK. Однако новая durable модель должна быть оформлена так, чтобы старые persisted files либо безопасно импортировались, либо явно считались необязательной recent projection; их значение решает product owner.

### 16.2. Этап 1 — переходная файловая execution-authority

- AppDock-resolved state/log roots;
- один writer сериализованных events;
- `events.jsonl` с ID, UTC, sequence, schema version;
- checksummed snapshot + replay;
- диспетчер нескольких активных Runs с bounded workers;
- resource claims для записи;
- per-user/read cursor если включён shared profile;
- простая local-only ProblemRecord + безопасный UI error code;
- `--diagnose` проверяет writer, состояние журналов и доступность roots.

**Граница:** эта стадия поддерживает один локальный process authority и несколько чатов. Она ещё не обещает доставку событий на другой компьютер через AppDock, независимое выполнение после kill GUI или сервисный Web API. Их надо проверять только по реально появившимся владельцам.

### 16.3. Этап 2 — отделение headless authority от Qt

- вынести JobManager, case/run stores и event publication из `presentation/qt_desktop` в Qt-neutral application runtime;
- Windows становится клиентом, подписывается на состояние;
- добавить отдельное штатное завершение/отмену процесса и запуск из background с тем же execution spine;
- приложение может использовать AppDock для host lifecycle **только после фактического подтверждения capability**; иначе выбрать отдельный честно объявленный режим собственного процесса;
- real-time API может первоначально быть простой локальной очередью/IPC, без сети.

Важно: **новый репозиторий для runtime необязателен**. Сначала можно выделить пакет и процесс в существующей application architecture, а физическую repo topology решить позже, после появления ещё одного потребителя.

### 16.4. Этап 3 — реальные shared-node chat и AppDock problem integration

- узловой shared event authority и server-side authorization;
- snapshot + cursor-based subscriptions;
- все чаты участников узла видимы согласно политике;
- узловые warning conditions и safe projections;
- подключение AppDock Recorder только по подтверждённому versioned SDK/port;
- reconciliation над внезапно пропавшим worker / неизвестным effect;
- per-user unread и scopes;
- защищённая выдача restricted logs/support bundles.

Эта стадия возможна **с файловым backend**, если один owner сервиса сериализует запись; СУБД не является формальным prerequisite. Для большого числа клиентов и запросов storage станет performance/operability развилкой.

### 16.5. Этап 4 — backend через AppDock и переносимость клиентов

- AppDock предоставляет typed file/SQLite/server binding;
- application authority проверяет capabilities, выполняет schema migration и contract tests;
- Windows/Web/Android используют одинаковые `thread/run/progress/problem` read models, но свою разметку UI;
- remote/AI/automation проходят тот же permissioned submit и корреляцию;
- OTel/CloudEvents exporters по необходимости и по профилю развёртывания;
- исторические JSONL данные мигрируют один раз с проверкой IDs/outcomes/cursors.

---

## 17. Acceptance criteria и негативные сценарии

В этой таблице приведены **проверяемые тестовые обещания, предлагаемые к утверждению**. Они ещё не подтверждены прогоном в поставке.

| ID | Ситуация | Ожидаемое наблюдаемое поведение | Что доказывается |
|---|---|---|---|
| O-01 | одновременно запущены R1 в Thread A и R2 в Thread B | обе карточки `running`, разные IDs/attempt logs; UI остаётся отзывчивым | параллельность не привязана к одному Qt coordinator |
| O-02 | два Runs одновременно в одном чате | две независимые карточки/terminal outcomes, общий чат сохраняет порядок событий | `thread_id ≠ run_id` |
| O-03 | повторная доставка одного submit после reconnect | одно принятие Job по idempotency key; повтор получает существующий Run | отсутствие duplicate effect |
| O-04 | повтор операции после failure | новый `attempt_id`; старый log сохранён | история попыток не перезаписывается |
| O-05 | worker завис/пропал после внешней записи | `reconciliation_pending/UNKNOWN`, отсутствие ложного `FAILURE`/`SUCCESS` | effect truth |
| O-06 | пользователь закрыл GUI при работающем Job | исход соответствует реальному lifecycle выбранного профиля; отсутствие выдуманного completion | явная foreground/headless семантика |
| O-07 | telemetry queue переполнена | промежуточный progress коалесцирован, terminal events и durable state не потеряны | control ≠ telemetry |
| O-08 | повреждена последняя неполная строка JSONL | recovery видит torn tail, исключает её из confirmed events, выдаёт diagnosis | честность file journal |
| O-09 | повреждён snapshot, journal цел | snapshot перестраивается с verified last_sequence, recovery записан | snapshot не единственная истина |
| O-10 | повреждены и journal, и snapshot | app запускает read-only diagnostics или отказывает в приёме новых jobs, показывает проблему | нет silent empty reset |
| O-11 | диск заполнен до durable submit | Job не объявлен admitted; UI отображает `storage_unavailable` | durable admission |
| O-12 | log sink упал после успешного domain result | business outcome остаётся истинным, `diagnostics_degraded` отдельно | независимость осей |
| O-13 | общий Data root пропал у host | affected workers/clients получают один shared condition и свои impacted run IDs | узловое оповещение по воздействию |
| O-14 | один пользователь ошибся с параметром | в его Run safe failure, нет всеобщего аварийного баннера | scope visibility |
| O-15 | исключение содержит SECRET-SENTINEL/token/path | sentinels отсутствуют в общей ленте, API и support summary; protected log проверен по отдельной политике | redaction |
| O-16 | пользователь U1 прочёл Thread A | unread U1 снимается, unread U2 остаётся | per-user cursor |
| O-17 | переименование «Новый чат» | ID и Run links неизменны, остальные видят новое название | mutable title vs stable identity |
| O-18 | два человека создают «Новый чат» одновременно | разные IDs, общая директория отображает оба | identity не равна названию |
| O-19 | artifact output переименован/удалён вручную | ссылка становится «файл отсутствует», история выполнения сохраняется | log/history ≠ физический файл |
| O-20 | AppDock ProblemRecorder недоступен | local problem сохраняет `local_only`, platform ref не выдумывается | capability honesty |
| O-21 | AppDock меняет физический root/binding | новый запуск получает новое location, сохранённое состояние мигрирует/восстанавливается по явной политике | отсутствие hard-coded state path |
| O-22 | Web/Android читает технический `log_ref` без разрешения | отказ доступа до разрешения physical path, никакого absolute path в JSON | security boundary |
| O-23 | новый SQLite binding вместо files | проверка совпадения run IDs, terminal outcomes, cursor order и artifacts; old file authority становится read-only | provider portability |
| O-24 | приложение перезапущено и запрашивает «активные задания» | незавершённые Runs отмечены на проверку, stale heartbeat не выдаётся как running без подтверждения | recovery truth |
| O-25 | timestamp двух клиентов перепутан из-за skew | event order следует node sequence, UTC остаётся диагностическим | causal order |
| O-26 | файл логов достиг retention quota | ротация/cleanup по policy, UI видит пропавший older log, terminal history сохранена | отделение истории от evidence |
| O-27 | одновременно пишутся разные outputs | независимые параллельные commits; один и тот же destination блокируется/версионируется | ресурсная конкуренция |
| O-28 | падает AppDock platform health, но Excel уже опубликован | artifact/Run success не исчезает; platform state отдельно degraded | разные authorities |

### 17.1. Проверки, которые особенно нельзя пропустить

Для настоящей готовности file backend важнее **fault injection**, чем большое число обычных unit tests. В обязательной матрице должны быть: kill процесса после durable submit, после открытия файла, между snapshot write и replace, при fsync failure, при разрыве host connection, при частично записанном output, после выполнения эффекта, но до записи `run.completed`. Для каждой точки следует зафиксировать, что из прежних фактов можно доказать, и какую честную реакцию увидит пользователь.

Нельзя объявлять «восстанавливается после падения» только потому, что после обычного restart отображается прежняя история. Восстановление возможно разной степени: read-only diagnostics, восстановление UI projection, подтверждение конечного эффекта, автоматическое продолжение работы. Для первой версии требуется **прежде всего исключение ложной истины**.

---

## 18. Decision register: что нужно решить отдельно

| Приоритет | Вопрос | Рекомендация исследования | Статус |
|---|---|---|---|
| **P0** | Будут ли поддерживаться независимые одновременные команды в разных чатах? | да; это прямое требование разработчика | DEVELOPER / implementation gap |
| **P0** | Что является главным ID? | чат — `thread_id`, исполнение — `run_id`, попытка — `attempt_id`; ни один не подменяет другого | TARGET strong |
| **P0** | Кто владеет операционным состоянием? | Strategy Box application authority, размещённая через AppDock binding; на общем узле один authority writer | TARGET strong |
| **P0** | Нужно ли вводить SQLite сразу? | **нет**; transitional file journal/atomic snapshots допустим и предпочтителен сейчас | DEVELOPER clarification + TARGET |
| **P0** | Где разместить state vs data? | managed system/user state vs Data workspace; оба получены через AppDock | TARGET strong |
| **P0** | Может ли thread content быть полным technical log? | нет: chat UI — safe projection, technical logs отдельно | TARGET strong |
| **P0** | Что делать с exception text? | не выводить raw exception в shared/persisted UI; restricted evidence | TARGET strong |
| **P1** | Кто управляет terminal outcome после падения GUI? | durable execution authority; текущий foreground profile следует честно закрывать/перепроверять | OPEN profile |
| **P1** | Когда node-wide notifications разрешены? | только scoped shared conditions/impact | TARGET strong, policy OPEN |
| **P1** | Что служит гарантом directory/state root lifecycle при update/uninstall? | AppDock explicit storage binding/ownership policy | OPEN с внешним owner |
| **P1** | Как AppDock выдаст SQLite/иной backend в будущем? | typed `StateStorageBinding`, capability negotiation, внешний versioned contract | OPEN platform design |
| **P1** | Кто может открывать чужие raw logs? | отдельное permission, server-side check | OPEN access policy |
| **P1** | Как часто обновлять progress и за сколько хранить? | измерить; volatile/coalesced progress, durable terminal | OPEN budgets |
| **P1** | Что требуется для automatic retry? | операция объявляет idempotency/effect class; unknown требует reconciliation | TARGET strong |
| **P2** | Использовать OTel/CloudEvents/metrics exporters? | расширение по спросу, не prerequisite | TARGET defer |
| **P2** | Достаточно ли одного продукта для host execution? | сначала выделить headless application authority, repo splitting позже | OPEN packaging |
| **P2** | Требуется ли Incident-модель? | нет до подтверждённой межузловой/операторской работы | TARGET defer |

### 18.1. Что может противоречить друг другу

**«Любое закрытие программы завершает выполнение» vs «фоновые задачи продолжают работать».** Это не обязательно конфликт требований, если явно назвать два профиля: local foreground (закрытие завершает/отменяет попытки с unknown reconciliation) и host service (закрытие окна лишь отключает клиентскую сессию, Jobs остаются у узла). AppDock пока не даёт гарантированного полнофункционального host execution; границу надо сохранить как проектную.

**«Все видят все чаты» vs «никакой приватности»**. Общий просмотр product-safe истории не требует публикации технических файлов, секретов или произвольных параметров. Visibility policy — фильтр перед отправкой чужому клиенту, а не опциональное украшение UI.

**«AppDock владеет проблемой» vs «AppDock pre-alpha»**. Зависимость от платформенной Problem/Recorder допустима только при реальной поддержке. Переходный local problem record — честная собственная защита приложения. Позднее bridge передаёт записи с idempotent mapping; не допускаются две конкурирующие авторитетные регистрации одного и того же сбоя.

**«AppDock выбирает storage» vs «Strategy Box нужна быстрая реализация»**. AppDock уже предоставляет managed roots; это достаточный начальный storage binding. Разрабатывать собственный глобальный выбор произвольных путей в приложении не требуется.

**«Без обратной совместимости» vs «не терять историю пользователей»**. Никакие устаревшие Python APIs сохранять необязательно; существующие durable данные — самостоятельная ценность. При смене persistence формата нужна одноразовая проверяемая миграция или явное решение, что старые records были лишь disposable cache.

---

## 19. Итоговая целевая схема по владельцам

```text
  EXTERNAL / NOTEBOOK / API / AI             STRATEGY BOX CLIENT
  invoke canonical Operation                Windows / Web / Android
           │                                    │
           ▼                                    ▼
  stratbox (business core)               Chat/Run read models
  ├─ domain Result                        user events, labels,
  ├─ ProgressSink                         stage/progress, artifacts
  ├─ DiagnosticFinding                           │
  └─ provenance                                  │ safe subscribe/query
           │                                    │
           └────────────────┬───────────────────┘
                            ▼
                   APPLICATION AUTHORITY
             ┌───────────────────────────────┐
             │ Thread / Run / Job / Attempt  │
             │ one admission & state writer  │
             │ event journal & snapshots     │
             │ resource effects / recovery   │
             │ audience-safe projections     │
             └───────────────┬───────────────┘
                             │
                 neutral platform adapter
                             │
           ┌─────────────────┴────────────────────┐
           ▼                                      ▼
   APPDOCK CONTROL / RUNTIME              APPDOCK DATA BINDING
   ├─ World/Node/Session                  ├─ source files
   ├─ install & system roots               ├─ output/artifact bytes
   ├─ state/log location binding           └─ data/file provider
   ├─ storage capabilities
   ├─ platform health/problems
   └─ future host/process services
           │
           ▼
   interim FileStateBackend
   later SQLite/Service backend through AppDock
```

**Практически это означает:** core не должен импортировать UI или AppDock; future common application слой должен читать typed platform binding и управлять Run/Job; Windows/Android/Web получают одни и те же *смысловые* проекции; AppDock остаётся внешней платформой со своими версионированными contracts и отдельным lifecycle. Файл/SQLite — сменяемая физическая реализация, а не архитектурная сущность уровня пользовательского сценария.

---

## 20. Перечень проверяемых источников

### 20.1. Первичные исходники репозиториев

**Strategy Box / common corpus:**

- [Core entrypoint и архитектурные границы](https://github.com/ForestTiger-GH/stratbox/blob/main/README.md); [паспорт Work/research](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/AGENTS.md).
- [Current HOW: Windows application](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/current-how/windows-application.md).
- [Candidate HOW: diagnosis/recovery](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/how/operations/diagnosis-and-recovery.md).
- [Reasoning on UNKNOWN vs confirmed failure](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/science/trust-and-assurance/uncertain-outcome-vs-observed-error.md).
- [Current vs candidate qualities](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/what/strategy-box/qualities-and-constraints.md).

**Windows implementation:**

- [Scenario execution runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py).
- [Operation execution/error handling](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/execution/runner.py).
- [Qt ScenarioCoordinator](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py).
- [Case](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/cases/models.py); [Events](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/events/models.py); [Logs](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/logs/models.py).
- [History persistence](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py); [runtime logging](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/logging.py); [paths](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/paths.py).
- [AppDock surface state bridge](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/adapters/appdock/surface_state.py); [manifest](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json).

**AppDock:**

- [Observability target](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/observability/TARGET_MODEL.md); [implementation status](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/observability/IMPLEMENTATION_STATUS.md) — различайте целевой дизайн и подтверждённое исполнение milestones.
- [AppDock platform directory authority ADR](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/adr/ADR-platform-directory-authority.md); [root model](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/root_model.md).
- [Activation and launch](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/activation_and_launch.md); [Activation Context contract](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/contracts/runtime/activation_context.py).
- [Problem contract surface](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/observability/public/__init__.py); [OperationCompletion and ProgressEvent](https://github.com/ForestTiger-GH/AppDock/blob/main/src/appdock/domains/execution/results/operation_results.py).
- [Current operational scope / explicitly deferred host and remote](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/implementation/current_operational_scope.md).

Ссылки на приватные репозитории проверяемы авторизованным участником GitHub; их доступность другим читателям зависит от прав. В публичный код Strategy Box нельзя переносить скрытые детали реализации смежных закрытых систем.

### 20.2. Независимые внешние первоисточники

**[EXT-1]** Sigelman, B. H. et al. (2010), *Dapper, a Large-Scale Distributed Systems Tracing Infrastructure*, Google Research. https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/

**[EXT-2]** OpenTelemetry Specification, *Logs Data Model*. https://opentelemetry.io/docs/specs/otel/logs/data-model/

**[EXT-3]** W3C Recommendation, *Trace Context*. https://www.w3.org/TR/trace-context/

**[EXT-4]** Python Software Foundation, *Logging Cookbook: Logging to a single file from multiple processes*. https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes

**[EXT-5]** Python Software Foundation, *faulthandler*. https://docs.python.org/3/library/faulthandler.html

**[EXT-6]** CNCF, *CloudEvents Specification v1.0*. https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md

**[EXT-7]** SQLite, *Write-Ahead Logging*. https://www.sqlite.org/wal.html

**[EXT-8]** SQLite, *Isolation In SQLite*. https://www.sqlite.org/isolation.html

**[EXT-9]** OWASP, *Logging Cheat Sheet*. https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html

**[EXT-10]** NIST, *SP 800-92 Guide to Computer Security Log Management*. https://csrc.nist.gov/pubs/sp/800/92/final

**[EXT-11]** OpenTelemetry, *Context propagation security best practices*. https://opentelemetry.io/docs/concepts/context-propagation/

**[EXT-12]** IETF, *RFC 9457 Problem Details for HTTP APIs*. https://www.rfc-editor.org/rfc/rfc9457.html

**[EXT-13]** Google, *Site Reliability Engineering: Monitoring Distributed Systems*. https://sre.google/sre-book/monitoring-distributed-systems/

**[EXT-14]** OpenTelemetry, *Metrics cardinality limits*. https://opentelemetry.io/docs/specs/otel/metrics/sdk/

Источники сравниваются как технические спецификации, научная статья, практические руководства и документы эксплуатации. Их применение к Strategy Box является архитектурной интерпретацией, а не утверждением, что текущая поставка уже соответствует каждому пункту стандартов.

---

## 21. Окончательный вывод исследования

**Наблюдаемость Strategy Box нужно начинать с сохранения правды о конкретном исполнении, а не с технологии хранения и не с красивого экрана логов.**

Самое экономное и расширяемое решение выглядит так: устойчивый **ID чата** для командной истории; отдельные **ID запусков и попыток** для параллельной работы; типизированные короткие события для timeline; защищённые физические логи и evidence; пять однозначных вариантов исхода; безопасные уведомления для других участников **только при релевантном общем воздействии**. Общий Job/Run owner и serial writer должны существовать независимо от количества окон и чатов.

Уточнение разработчика относительно AppDock даёт однозначный порядок: **сначала file-backed state в уже предоставляемых AppDock managed roots, затем — при реальной потребности и готовности внешнего контракта — SQLite или другой storage provider через AppDock**. Внутренняя предметная схема состояния Strategy Box остаётся за Strategy Box; AppDock выбирает provision/binding и владеет платформенным lifecycle. Общие аналитические файлы, результаты и артефакты размещаются через отдельный Data binding.

Главный ближайший эффект — можно достоверно ответить на пять вопросов: **кто** запустил действие, **в каком чате**, **что реально выполняется сейчас**, **что случилось при отказе** и **какой результат подтверждён**, даже когда одновременно работают разные чаты и появляется ограниченный общий узловой доступ.

**Research завершён как проектная позиция; реализационные решения, fault-injection и совместимость с конкретным релизом AppDock остаются отдельными gates.**
