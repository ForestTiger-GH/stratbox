# Причинная наблюдаемость исполнения: события, прогресс, логи и достоверный исход

**Область:** факты об исполнении аналитических операций, степень наблюдаемости прогресса, диагностическая сохранность, конкурирующие процессы, эффекты и согласование с внешней управляющей платформой. **Статус:** научно-инженерные выводы с прямой кодовой иллюстрацией и кандидатами технических контрактов; устойчивого общего JobManager, общей многопользовательской истории, полной платформенной регистрации проблем или UI-конформанс-теста в исследованном baseline **нет**. Смежные Science: [сохранность и восстановление](../state-and-recovery/authority-durability-and-recovery.md), [операции и исполнения](../capabilities/definitions-plans-and-execution-truth.md), [неизвестный исход](../trust-and-assurance/uncertain-outcome-vs-observed-error.md) и [совместно наблюдаемые проблемы](../collaboration/shared-conditions-and-log-access.md).

## 1. Наблюдаемость — система связанных, но разных фактов

Обычный журнал Python не может самостоятельно ответить: кто поставил задание, в каком пользовательском контексте оно принято, какой шаг исполняется, закончился ли внешний эффект, какие bytes опубликованы и действительно ли ошибка принадлежит общему узлу. Чат тоже не должен превращаться в нескончаемый поток stack traces. Необходимы разные **источники истины** с устойчивыми причинными связями.

| Класс | Вопрос пользователя или оператора | Чья это истина | Как выглядит |
| --- | --- | --- | --- |
| **ChatMessage / Thread** | Что обсуждали, кто просил, к какой работе вернуться? | Application conversation authority | Персонально или совместно видимая лента по правам |
| **ExecutionEvent** | Что было принято, начато, выполнено, прервано? | Execution authority и достоверные producer receipts | Короткое durable событие и проверяемый outcome |
| **ProgressUpdate** | Что делается именно сейчас? | Worker/domain producer, может устареть | Коалесцируемое текущие состояние, phase/count/heartbeat |
| **DiagnosticFinding** | Почему данные или вывод не соответствуют ожиданию? | Domain validator/source/solver | Typed problem с контекстом результата/математическими доказательствами |
| **ProblemOccurrence / Condition** | Какой отказ наблюдён, где, кто затронут? | Producer/diagnostic owner; внешний recorder только если подтвердил запись | Отдельные occurrences и агрегированное impact-состояние |
| **TechnicalLog / Evidence** | Чем подтверждается цепочка exception/IO/process? | Execution host/platform | Защищённый физический файл/ссылка, не публичный текст |
| **Metrics / Audit** | Какова нагрузка и был ли соблюдён контроль полномочий? | Monitor/policy owner | Агрегаты и отдельные записи о действиях, не синонимы ленты |

**Разные evidence planes** могут физически лежать в одних каталогах, но их запись, retention, доступ и recovery отличаются. Доменная СУБД не возникает из одного log JSONL, а platform health не вычисляет истинность банковского отчёта.

## 2. Чат, запуск, работа, попытка и trace не один идентификатор

Устойчивые сущности полезно различать даже при первой локальной версии:

- `node_id` — внешний managed context.
- `participant_id/actor_ref` — устойчивая связь действия с участником; `nickname/display` меняются и могут совпадать.
- `session_id` — конкретный вход/устройство, один participant может иметь несколько sessions.
- `thread_id` — долгоживущий пользовательский разговор, чей заголовок может измениться без изменения ID.
- `message_id` — отдельное сообщение.
- `run_id` — один принятый эпизод выполнения. В одном Thread может одновременно существовать несколько Run.
- `job_id` — очередь/исполнительная единица при наличии JobManager; не требуется при отсутствии такого owner.
- `step_id` определяет часть definition, `step_run_id` — её конкретный экземпляр в одном исполнении.
- `attempt_id` — одна попытка физического действия; при retry меняется независимо от step/operation name.
- `event_id` — уникальный факт для повторной доставки и дедупликации.
- `problem_ref` — полученная ссылка на запись от конкретного recorder; нельзя фабриковать при ошибке платформы.
- `artifact_id/version` — опубликованный результат, а не равный ему абсолютный путь.
- `trace_id/span_id` — опциональная распределённая причинная цепочка, не равная `thread_id`.

В пользовательском интерфейсе может быть достаточно одного короткого `run_ref`. Полные идентификаторы — для диагностики. Сам user actor-kind `ai` или отображаемое имя не дают права запускать чужие операции, читать чужие логи или отменять job.

**Порядок совместной ленты** определяется подтверждённым монотонным `sequence` authority, а не сортировкой по локальным часам разных устройств. Для event полезны `occurred_at_utc`, время получения у authority и `causation_event_id` (если применим). Sequence нужен даже если два пользователя создали чаты «Новый чат» одновременно; заголовок не identity. Внешний producer может принести собственный ID, но canonical event получает ID/sequence после admission.

## 3. Прямые пределы текущего Windows и core

[Scenario runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) последовательно вызывает steps, формирует `case_started` / `step_started` / success/failure, LogRecord и ArtifactRecord. Это рабочая модель локального исполнения, **не** доказательство долгой node-wide authority. [Qt coordinator](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) содержит одну пару `_thread`, `_active_case` и отклоняет второй submit при busy; так что параллельные чаты и одновременные команды в одной поставке пока **пожелание**, а не current capability.

[Operation execution runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/execution/runner.py) открывает `logging.FileHandler` по имени вида `case__step__operation.log`, ловит exception, помещает `str(exc)` в пользовательский `OperationResult.details` и сообщение. Это две прямые границы риска: текст исключения может содержать чувствительный путь/URL, а повторная попытка с тем же case/step/operation будет использовать прежнюю filename без `attempt_id`, потенциально смешав физические доказательства. Даже без подтверждённой утечки в эксплуатации статическая семантика уже требует safe boundary. [Runtime logging](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/logging.py) использует обычный FileHandler без гарантированных rotation/retention policies.

[HistoryPersistenceService](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) отдельно сохраняет cases/events/artifacts/logs/assignments и при ошибке восстановления возвращает пустую коллекцию. Это наблюдение кодового пути, **не** зарегистрированный реальный инцидент. [Session runtime](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/session_runtime.py) передаёт последнюю/активную проекцию в platform state; одно `active_job` непригодно как список всех параллельных Jobs.

В core предметные failures различаются: collector, escrow, cbr_forms, industries, FRG и SORS возвращают разную степень audit/validation. Богатый SORS proof ledger нельзя свести к `error: str` без потери доказательной информации. Общий minimal `ProgressSink` и `DiagnosticSink` или один typed callback с категориями — **кандидатный reusable порт**; core должен оставаться callable из notebook/Python без Chat/Qt/platform зависимостей. Инициируемая core доменная ошибка и её user-facing доступное объяснение принадлежат разным слоям.

## 4. События, прогресс и статус как три независимые роли

Ограниченный набор значимых событий на практике достаточен для causal journal, если их смысл точен: `thread.created`, `thread.renamed`, `message.created`, `run.submitted`, `run.admitted`, `run.started`, `step.started`, `step.completed`, `artifact.published`, `problem.recorded`, `condition.raised/cleared`, `run.completed`, `run.recovery_required`, `run.reconciled`. Это **пример будущей taxonomy**, не гарантия текущего runtime.

Lifecycle `prepared → admitted/queued → running → finalizing → terminal` отличается от outcome `SUCCESS | PARTIAL | CANCELLED | FAILURE | UNKNOWN`; отдельно существует `ready/degraded/unavailable/unknown` health. `PARTIAL` может означать 8/10 обработанных ресурсов при видимых ошибках; `UNKNOWN` — невозможность подтвердить эффект; `CANCELLED` требует реального согласованного прекращения, а не нажатой кнопки. `SUCCESS` Python-кода **не** равно опубликованному Excel с подтверждёнными bytes.

Прогресс допускает три формы:
1. **Подтверждённая стадия:** «загрузка», «проверка», «расчёт», «сохранение».
2. **Счётчик `current/total` с units**, когда denominator реально известен. `8/10 files` не равны «80% оставшегося времени».
3. **Неопределённая активность:** stage+spinner+last activity, без выдуманного процента и ETA.

Высокочастотные progress ticks полезно коалесцировать и ограничивать по скорости UI; они не должны заполнять долговечный journal. Terminal/effect events терять при throttling или trace sampling нельзя. Составной прогресс допустимо агрегировать по фиксированному плану только при доказанных весах/denominator, а не по числу кнопок.

Нейтральное событие может иметь `event_id`, `event_type`, `schema_version`, `node/thread/run/job/attempt/step` refs, `sequence`, UTC timestamps, causation, `safe_summary_code`, typed safe payload. Это **семантический эскиз**, не действующая Python dataclass; canonical envelope перед внешней передачей проходит разрешённую projection. `schema_version` события Strategy Box нельзя смешивать с version manifest внешней платформы.

## 5. Ошибки: raw exception, outcome, Problem и condition

Фактическое исключение содержит техническую цепочку, иногда секреты и инфраструктурные имена. Оно может быть полезно в restricted evidence, но пользовательская карточка должна получать **устойчивый код** и подготовленное safe summary. Domain validation may be a finding without crashed worker. Сбой файлового sink не должен превращать успешный domain result в ложную неудачу; при обязательном аудите destructive effect отсутствие пригодного журнала может, напротив, быть причиной *отказать до effect*, согласно утверждённой политике.

Поток квалификации:

```text
DomainFailure / ValidationFinding / TransportFailure / StorageFailure
    → execution boundary determines Result and effect status
    → durable application event / optional local problem
    → platform ProblemDraft only if real recorder port exists
    → actual confirmed ProblemRef or explicit local-only/pending status
    → audience-safe summary and separately restricted evidence
```

Регистрация на платформе может завершиться неизвестно или отказом. Нельзя изготовить `ProblemRef`, будто внешний journal записан; можно сохранить `local_problem_ref` и `registration_status` для последующей сверки. AppDock `ProblemRef` — не то же, что HTTP [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html), который описывает конкретный HTTP response.

Случаи требующие иной записи:
- Ошибка сети до получения bytes: `FETCH_FAILED` и понятный пользовательский code.
- Загрузили HTML вместо XLSX: format validation failure, не пустой dataset.
- Упала запись event journal до подтверждения admission: Job не принят.
- Worker умер после потенциального network/output effect: `UNKNOWN/reconciliation_required`.
- Не сработало средство записи технического лога при успешном расчёте: результат сохранил success, diagnostics degraded (если аудит не блокирует).
- Нет доступа к обязательным техническим доказательствам опасного действия: запуск потенциально блокируется *до* effect.
- История повреждена: quarantine/read-only/diagnostics, не пустая «истинная» база.

## 6. Один state authority, два пространства данных и конкуренция

Смысловая граница:
- **External control/runtime:** installation, package, Node/Session, root capability, process launch и platform health.
- **Analytical data:** CSV/XLSX, source snapshots, outputs, cache и staged artifacts, с отдельным управляемым Data root.
- **Product operational state:** Chat/Thread, accepted Run/Job, terminal outcome, read cursors и shared notices — owned by application authority в разрешённом системном storage.
- **Diagnostics/evidence:** app technical logs, per-attempt trace, crash evidence и platform-owned problem journal, с двумя owners и управляемым мостом.

**Выбор физического места хранения через платформу** (в рамках действующего managed root или будущего capability) не делает платформу автором Python/SQL схемы чатов. `StateStorageBinding` с типом `file_directory/sqlite/service`, locality, scope, atomic replace, flush, backup и retention может быть полезен в будущем — **на исследованном AppDock не подтверждён universal provider такого вида**. Внешняя платформа уже предоставляет roots/activation, которые можно честно проверять и использовать в переходном локальном профиле.

При одновременном выполнении двух независимых задач можно иметь несколько workers и **одного сериализующего state writer**. Разные чаты — не разные write-lock namespaces: два Runs одного чата могут быть параллельны, два Runs разных чатов могут конфликтовать по одному output path. Ресурсные claims `read/write/exclusive` и run-scoped staging должны обслуживать реальные файлы/ресурсы, а не правило «одна работа на чат».

**Физические альтернативы для малого state:**

| Подход | Преимущество | Недостаток | Правильный статус |
| --- | --- | --- | --- |
| Независимые пять JSON | Уже в codebase | Silent corruption, нет общей revision | Current / недостаточно для G2 |
| **Один versioned atomic snapshot** | Один файл, один commit, проще восстановление для малого объёма | Целая перезапись, нет естественного append history, single writer; durability profile нужен | Кандидат позднего Research по persistence |
| **Append-only JSONL + проверяемые snapshots** | Естественный causal sequence, ревизии, потенциальный replay | Торванный хвост, checksum framing, compaction, history growth, собственная recovery complexity | Кандидат позднего Research по observability |
| SQLite host-local WAL | Транзакции и queries, зрелый механизм | Не готов внешний SQL-binding, нельзя shared WAL напрямую между компьютерами | Поздний candidate |
| PostgreSQL/service | Серверная нагрузка и управление | Эксплуатационная цена; пока нет SLA | Для подтверждённого профиля |
| Полный event sourcing / telemetry stack | Replay/централизованная диагностика в зрелой системе | Тяжёлая архитектура, сохранение sensitive данных, новые failure domains | Не исходное обязательство |

**Важно:** тексты о persistence и observability расходятся в предпочтении snapshot-only vs append journal. Это сохраняемый конфликт **между двумя предварительными дизайнами**. Из обоих надёжно следует single-authority, честная запись, no shared-file multiwriter, fault injection; **выбор backend или гарантии его append/crash atomicity не принят**. Пользовательскому приложению не требуется ждать появления SQLite, но утверждать файловую сохранность без проверки target FS нельзя. Read-only аварийный режим корректнее ложного пустого restart.

[SQLite WAL](https://www.sqlite.org/wal.html) и [isolation](https://www.sqlite.org/isolation.html) допускают многократное чтение и писателя на одном host, но нельзя открыть WAL-базу по network FS разными хостами как общую authority. **Host-local DB + authenticated API clients** — иной, условно жизнеспособный режим.

## 7. Физические журналы и fatal evidence

Различаются **четыре уровня физического следа**: product events; технический app log; per-attempt log; emergency/crash evidence. Они не взаимозаменяемы по retention и пользовательской аудитории.

Минимальный structured technical record содержит `schema_version`, UTC, severity, component, stable code, node/process/session/run/step/attempt/event refs, prepared safe summary, restricted `traceback_ref` и diagnostic log scope. Вместо полного `str(params)` следует отдельно маркировать параметры по `public/private/secret` и действиям `display/log/persist`. Весь параметрический dict не надо копировать в UI или exception report.

Standard `logging.FileHandler` и `RotatingFileHandler` полезны в **одном процессе**, но многопроцессная конкурентная запись в один файл не гарантирована: официальный [Python Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes) рекомендует централизованную очередь/Socket listener или отдельные process files. У каждого Run/Attempt — уникальный лог и bounded rotation/retention. На клиент отдавать `log_ref` + правомерный sanitised tail, а не абсолютный путь хоста.

Вариант аварийного path: подготовить отдельный дескриптор файла до тяжёлой инициализации, включить [`faulthandler`](https://docs.python.org/3/library/faulthandler.html) и boundary `sys.excepthook` / `threading.excepthook` / Qt worker handlers. Это улучшает шанс получить evidence, **не гарантирует** файлы после process kill или отключения питания. `faulthandler` file descriptor нужно держать открытым; rotation/reuse FD требует осторожности. При следующем запуске сверять незавершённые attempts с process/effect receipts; отсутствие последнего сообщения не доказывает отмену.

Сбой самого log sink — отдельный failure domain. Не нужно рекурсивно писать failure of log about failure of log в тот же неработающий sink; предусмотреть минимальный emergency channel и безопасную деградацию.

## 8. Чем внешний AppDock действительно может помочь

Внешняя платформа управляет roots, activation, пакетом, Node/Session, process status и own problem semantics. В точном обследованном [`IMPLEMENTATION_STATUS` @ a4d87c6](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/observability/IMPLEMENTATION_STATUS.md) **Milestone 5E source implementation complete, Windows certification pending**, а следующий 6A emergency sink ещё не был принят к исполнению. В этом baseline нельзя называть общим работающим SDK будущий recorder внешних продуктов или полный semantic event/incident/fleet service только по наличию Python типов. Подтверждённый `ProblemRef` возникает там, где owner действительно его вернул, а не по предположению приложения.

Платформа может знать, что process завершился, timeout или child killed. Это не делает её владельцем `run.completed` и не подтверждает, опубликован ли файл между `write` и потерянным acknowledgement. Точно так же успешная core операция не обязана менять platform Node health на ready. Обе модели обязаны сохранять независимость.

Прежде чем рекомендовать новый platform SDK, нужны exact contract version/feature detection, permission to record, error semantics и тест installed Windows profile. До этого application-local diagnostic trace остаётся собственным надёжным минимумом.

## 9. Внешние методические аналоги и отрицательный результат

[Google Dapper](https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/) иллюстрирует ценность причинной корреляции; для локального Strategy Box это аргумент за `run→attempt→effect`, не за немедленный distributed tracing cluster. [OpenTelemetry Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/) предлагает timestamp/observed timestamp, severity, resources и optional trace IDs; [W3C Trace Context](https://www.w3.org/TR/trace-context/) — перенос trace IDs через доверенные HTTP границы. Внешним публичным сайтам **не нужно** раскрывать `thread_id`/пользователя/узел в tracing baggage. [CloudEvents](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md) — потенциальный adapter для внешних событий, не обязательный внутренний journal schema.

[OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) и [NIST SP 800-92](https://csrc.nist.gov/pubs/sp/800/92/final) поддерживают раздельную обработку sensitive log evidence и security/retention governance. [Google SRE four golden signals](https://sre.google/sre-book/monitoring-distributed-systems/) дают полезные условные агрегаты: latency, число admitted/running requests, ошибки с различением partial/unknown и загрузка workers/queue/storage. Однако отдельный high-cardinality `run_id/user_id` в metrics labels создаст нагрузку; лучше trace/log reference. Prometheus/Jaeger/OTel collector без реального host use case лишняя опора.

**Неоднозначность стандартов:** ни один внешний формат не решает Product-политику общего чата, точность progress %, ответственность за Run outcome, показ traceback, размещение файлов, приоритет исправления текущего локального runner и соответствие AppDock version. Научные аналоги задают вопросы и объясняют границы, а не заменяют решения.

## 10. Проверочная матрица достоверности исполнения

Следующие проверки — **кандидатные тесты**, а не выполненный run:

| Сценарий | Обязательное различие |
| --- | --- |
| Два Runs в двух чатах и два в одном чате | Отдельные Run/Attempt, chat только связывает, UI не блокируется |
| Дублированный submit после reconnect | Тот же admitted Run по idempotency, без двойного external effect |
| Retry после ошибки | Новый Attempt ID и отдельный физический лог |
| Worker исчез после remote write | UNKNOWN и evidence reconciliation |
| Закрыли GUI | Факт продолжающегося host Job или interruption зависит от реального профиля |
| Telemetry queue переполнена | Progress может быть coalesced, terminal и effect events сохраняются |
| JSONL torn tail | Не принимается как confirmed event; diagnostics |
| Snapshot повреждён, journal цел | Возможна проверяемая реконструкция без false reset |
| Повреждены journal и snapshot | Read-only/diagnostics вместо новой пустой authority |
| Нет диска до durable submit | Job не объявляется принятым |
| Sink логов упал после успешного расчёта | Business outcome остаётся success, diagnostics degraded |
| Общий Data root пропал | Узловое condition, affected Run refs; scope по влиянию |
| Пользователь ввёл неверный параметр | Safe локальная ошибка, без общей аварийной тревоги |
| Exception содержит secret-sentinel | Нет sentinel в shared UI и support summary |
| Прочтение чужого общего чата | Per-user read cursor сохраняет другому unread |
| Два чата с одинаковым названием | Title не является identity |
| Artifact вручную удалён | Исторический Run остаётся, locator недоступен |
| Platform recorder unavailable | Только local problem, platform ref не фабрикуется |
| Меняется разрешённый root | Migration/provision contract, не hardcoded path |
| Android клиент запрашивает log без прав | Отказ до разрешения физического пути |
| Файлы → SQLite | Verified import IDs, sequence, outcome, pointers; old source read-only |
| Reopen после crash | Nonterminal Run проходит reconcile, stale heartbeat не live |
| Устройства расходятся по времени | Canonical event sequence отделён от wall clocks |
| Log retention сработал | Старый лог может отсутствовать, durable outcome остаётся |
| Конкурентные writers одного output | Lock/unique staged destination; независимые outputs параллельны |
| Platform health unavailable при успешном XLSX | Run success и platform degraded не смешиваются |

Для claim crash durability нужны **fault injection** на границах journal append, fsync, snapshot replace, effect commit, lost ACK и последующего reopen с проверкой фактов; обычный чистый restart недостаточен. Должны быть проверены реакция UI, реальные bytes, журнальные IDs, user access и восстановление. Численные срок retention, размер логов и допустимая concurrent нагрузка остаются Product/Operations Decisions.

## 11. Основные неразрешённые выборы

Что должно жить после GUI crash и в каком profile? Кто является node execution authority? Какое storage API реально предоставляет платформа сейчас и впоследствии? Кто имеет право читать raw logs и чужую историю? Когда общая ошибка превращается в предупреждение? Какие операции требуют обязательного аудита/подтверждения до эффекта? Когда считать stage progress измеримым, какой terminal event сохранять? Кто ведёт одноразовую migration из старых пяти JSON? Где метаданные независимых Run, кто обновляет read cursor, нужен ли full incident management?

Проверяемые code/protocol decisions, утверждённые requirements и независимые installed tests способны сузить альтернативы. Пока они отсутствуют, все предлагаемые интерфейсы и порядки этапов остаются **квалифицированными гипотезами**, а не production-ready contract.

**Негативный вывод:** невозможно объявить наблюдаемость «готовой» наличием панельки логов, QR/ID-карточки или Python FileHandler. Точно так же полный event framework, SQLite, OTel или Web API без корректных Product outcome/effect и permission semantics будут избыточной инфраструктурой поверх неопределённой истины.
