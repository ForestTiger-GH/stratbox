# Strategy Box — консолидирующее исследование 08
# Trust, Safety & System Qualities

**Дата:** 2026-10-09  
**Программа:** `03-consolidation-research`, тема `08 — Trust, Safety & System Qualities`  
**Тип:** самостоятельный Research Synthesis; не Product Decision, не нормативная спецификация готовой реализации  
**Основной корпус:** `02-base-study` (27 тематических исследований), консолидации `00–06` третьей ветки, выборочные проверки актуального кода implementation owners  
**Исторические материалы:** `01-old-notes` только как источник происхождения идей; исторические положения не используются как CURRENT  
**Публичная граница:** анализируются только нейтральные extension contracts; детали любых закрытых реализаций за пределами этого документа  
**Изменения репозиториев:** не выполнялись.

---

## 0. Executive synthesis

**[CONSOLIDATED]** Strategy Box нужен **единый проверяемый набор сквозных свойств**, действующий одинаково для операций аналитического `stratbox`, application runtime, Work/Run/Job, файлов и артефактов, общей работы, фоновых автоматизаций, Windows/Web/Android, удалённых workers и внешней границы AppDock. Эти свойства нельзя получить добавлением одного `try/except`, журнала или экрана диагностики: они возникают из контрактов, согласованной authority-модели и проверяемых правил перехода состояния.

**Главная архитектурная формула:**

```text
Идентичность + полномочие + versioned binding + immutable plan
                      ↓
       проверка применимости и допустимости эффектов
                      ↓
       durable admission + idempotency + resource claims
                      ↓
          execution + structured causal events
                      ↓
       effect receipts + validation + reconciliation
                      ↓
        один подтверждённый terminal outcome
                      ↓
        опубликованный результат + provenance
                      ↓
       восстановимая authority / безопасная projection
```

Здесь каждая стрелка — потенциальная граница отказа, а не только этап happy path. Надёжная система заранее определяет, что происходит при сбое **между** этапами.

### 0.1. Двенадцать основных результатов

1. **[CONSOLIDATED] Truth before convenience.** Ошибка доступа, повреждение данных и неопределённый результат не должны превращаться в пустую таблицу, `False`, `[]`, `ok=True` или успешную карточку чата.
2. **[CONSOLIDATED] Разделить пять истин:** состояние исполнения, действительность эффекта, достоверность аналитического содержания, приемку Work и операционное здоровье узла. У них могут быть разные статусы.
3. **[CONSOLIDATED] Один execution spine.** Foreground, background, scheduled, remote, API и AI различаются происхождением/режимом, а не качеством гарантий.
4. **[CONSOLIDATED] Durable authority находится вне UI.** Закрытие клиента, потеря WebSocket/SSE или Android-сессии не означают завершения или отмены Job.
5. **[CONSOLIDATED] Effect truth требует подтверждения.** Timeout после внешней мутации не является доказательством ни успеха, ни отсутствия эффекта. Нужны `EffectIntent`, `EffectReceipt`, проверка фактического результата и допустимое `OUTCOME_UNKNOWN`.
6. **[CONSOLIDATED] Destructive safety — отдельная политика.** Удаление, массовая очистка, rename/move, публикация поверх существующего результата и действия с внешним состоянием требуют plan/apply, ограничений области, безопасного commit и явной обработки частичного исхода.
7. **[CONSOLIDATED] Наблюдаемость причинная и многослойная.** Domain events, progress, diagnostics, immutable problems, technical logs, evidence, audit, conditions и метрики не являются взаимозаменяемыми объектами.
8. **[CONSOLIDATED] Authorize at effect boundary.** Обнаруженная capability, установленное расширение и роль пользователя сами по себе не дают права выполнить эффект. Авторизация и актуальность approval проверяются в момент admission и перед существенным действием.
9. **[CONSOLIDATED] Concurrency координируется по ресурсам.** UI-флаг `busy` и «один сценарий одновременно» не решают конфликты нескольких клиентов/worker. Нужны resource claims, leases, revision checks и fencing.
10. **[CONSOLIDATED] Версия — часть смысла.** Изменение исходной публикации, справочника, schema, operation definition, runtime binding или формата способно изменить воспроизводимый результат даже при прежних пользовательских параметрах.
11. **[TARGET-HYPOTHESIS] Минимальная физическая опора** — транзакционная authority, журнал событий/outbox, staging+atomic publication, разграниченные managed bytes и metadata; выбор конкретной СУБД/процесса зависит от deployment profile.
12. **[CONSOLIDATED] Надёжность должна иметь acceptance gates.** Тестами надо доказывать отрицательные сценарии: отключение сети, повтор запросов, падение между коммитами, устаревшую lease, повреждение JSON/БД, partial output, отозванное право, рассинхронизацию версий и перегрузку.

### 0.2. Самые важные находки, подтверждённые кодом

| Факт | Статус | Почему важно |
|---|---|---|
| Core `stratbox` — версия `0.8.0`; `stratbox-windows` объявляет `stratbox==0.2.1`, AppDock-манифест Windows ссылается на `0.2.1` | **CURRENT / подтверждено прямым code probe** | Package/installation contract drift; рабочая совместимость без E2E не доказана |
| В `stratbox-windows` реальный Connector Manifest `4.0`, а checked-in smoke test ожидает `3.0` и прежнюю форму package metadata | **CURRENT / подтверждено прямым code probe** | Репозиторный smoke test логически расходится с поставкой |
| `LocalFileStore.listdir()` возвращает `[]` для `not exists` и `not directory` | **CURRENT / подтверждено прямым code probe** | Empty, missing и wrong-type оказываются неразличимы на этой операции |
| `LocalFileStore._abs()` принимает абсолютные пути и не доказывает containment при заданном `root` | **CURRENT / подтверждено прямым code probe** | `root` — удобство относительных путей, **не security sandbox**; server/API boundary обязан отдельно ограничивать пространство |
| Runtime core использует динамическое discovery внешних providers и при ошибке загрузки может переходить к local provider, сигнализируя через `print` | **CURRENT / подтверждено нейтральным public runtime code** | Для управляемых профилей нужен явный fail-open/fail-closed policy; сам факт fallback следует показывать безопасной диагностикой |
| Core `FileStore.copy()` по умолчанию использует whole-object `read_bytes→write_bytes` | **CURRENT / подтверждено** | Размер файла может напрямую определять пик памяти; частичный write не имеет общего commit/abort protocol |
| Windows реализует case/event/log/artifact history и Qt-thread execution, однако durable job manager, общий background scheduler и реальная cooperative cancellation отсутствуют в baseline | **CURRENT / подтверждено research baseline 2026-10-06; нового запуска GUI не проводилось** | UI уже показывает понятия, которых пока нет как независимых execution guarantees |
| Windows сохраняет history в локальных JSON-проекциях; baseline фиксирует отсутствие атомарного межфайлового commit и строгой обработки повреждений | **CURRENT / baseline** | Локальная история не может быть общей durable truth для нескольких пользователей |

**Предел фактической проверки.** На `2026-10-09` connector сравнил `stratbox` baseline `e968853…` с `main`: 41 последующий commit, **изменений `src/`, `tests/` и `pyproject.toml` нет** в возвращённом перечне файлов; `stratbox-windows` baseline `959e9c4…` и `main` совпадают. Выполнен выборочный source probe, **не** запуск полного test suite, не нагрузочный тест, не Windows runtime/E2E и не аудит действующего продакшен-развёртывания. Сведения об AppDock разделены на его опубликованную **целевую модель** и конкретные implementation-status записи: наличие цели не доказывает её полную эксплуатационную готовность.

### 0.3. Пять разных статусов, которые нельзя смешивать

| Ось | Пример статуса | Источник истины |
|---|---|---|
| **Execution** | Job `SUCCEEDED` / `FAILED` / `OUTCOME_UNKNOWN` | application execution authority |
| **Effect** | publication `STAGED` / `COMMITTED` / `VERIFIED` / `UNKNOWN` | owner эффекта + подтверждающие receipts |
| **Domain qualification** | данные валидны, неполны, устарели, доказательная сила ограничена | `stratbox` domain validation/provenance |
| **Work acceptance** | задача принята, на проверке, отклонена или закрыта с ограничениями | product Work owner / разрешённый assessor |
| **Operational health** | backend offline, node degraded, источник не отвечает | соответствующий service/owner + platform health projection |

Успешный XLSX-export не доказывает корректность экономического коэффициента; `404` при получении источника не означает нулевой показатель; ошибка telemetry сама по себе не означает сбой расчёта. И наоборот: успешное завершение worker не даёт оснований считать Work принятой.

---

## 1. Предмет, метод и источники истины

### 1.1. Точная постановка темы 08

Программа перечисляет 15 осей: `Reliability`, `Error semantics`, `Observability`, `Security`, `Effect safety`, `Concurrency`, `Idempotency`, `Persistence`, `Versioning`, `Performance`, `Portability`, `Testability`, `Operability`, `Accessibility`, `Resource use`. Её специальная задача — выявить **system-wide invariants**. Настоящий файл проходит все 15 осей, а не заменяет их одним разделом про ошибки или AppDock.

### 1.2. Иерархия доказательности

1. **CURRENT:** конкретный текущий код/metadata прямого implementation owner либо чётко помеченный baseline с commit SHA.
2. **CONSOLIDATED:** согласованное исследовательское правило, поддержанное несколькими независимыми частями корпуса и не противоречащее фактической границе.
3. **TARGET-HYPOTHESIS:** целевая модель, которую нужно утвердить/испробовать; illustrative contracts в этом файле не являются текущим публичным ABI.
4. **CONFLICT:** несовместимые решения или неразрешённая граница; при кажущемся конфликте сначала проверяется различие scope.
5. **SUPERSEDED:** прежнее предложение уступило более позднему, лучше обоснованному.
6. **UNKNOWN:** данных недостаточно; нельзя превращать в `FALSE`, дописывать догадкой или уверенным утверждением.

**Сверка:** `02-base-study` рассмотрен целиком через карту 27 исследований темы 00, затем напрямую проверены ключевые исследования по наблюдаемости, execution, multi-user, фоновым процессам, web/self-hosted, storage/artifacts, форматам, registries, settings, расширениям, визуальной системе и accessibility; согласованы результаты `03-consolidation` по смысловой модели, данным, исполнению, persistence и extensions. Методологический принцип доказательности применяется к аналитическим утверждениям, без описания устройства внешних методологических проектов.

### 1.3. Что эта тема определяет, а что оставляет другим

Она определяет требования к наблюдаемому поведению системы при ошибке, риске, неодновременном доступе, повреждении, восстановлении и перегрузке. Она **не переименовывает** уже сведённые сущности `Work`, `Run`, `Job`, `OperationRun`, `Attempt`, `Artifact`, `SourceSnapshot` и не выбирает раньше времени единый physical deployment topology. Она вправе потребовать ресурсный lock, уникальность terminal outcome или contract-version gate, но не обязана этим решением порождать новый репозиторий.

### 1.4. Ownership как основа надёжности

| Responsibility | Логический owner | За что он отвечает |
|---|---|---|
| Источники, обработка, validation, математические bounds, subject semantics | `stratbox` domain/core | корректность доменного Result, данные, provenance, typed domain failure |
| Admission, Work/Run/Job/Attempt, план, effect coordination, concurrency, idempotency, product authorization | Strategy Box platform-neutral application authority | durable execution truth; фоновые, интерактивные и удалённые runs |
| Artifact catalog, Work/Run linkage, logical publishing и provenance | product artifact/knowledge authority; bytes — через storage adapter | логическая идентичность результатов, согласованность ссылок |
| Пользователи/гранты/поручения/прочтения/уведомления | product collaboration & authorization owner с platform identity | объектные права и shared-node state |
| Окна, навигация, индикация статусов, доступность | Windows/Web/Android surface owners | безопасные read-model projections и UX управления |
| Установка, activation, node/environment, host/service lifecycle, базовый platform health, platform problems | **AppDock** | управление средой и платформенными операциями, без подмены предметных результатов |
| Generic extension metadata/provider contracts | public `stratbox`/application contracts; конкретная реализация — её owner | discovery, activation policy, version, capability, conformance |
| Доступ к секретам/host identity/OS permissions | соответствующий trusted platform/provider owner | только разрешённые данные и операции; без передачи сырого секрета клиентам |

**CONFLICT RESOLVED:** ранний тезис «AppDock владеет расписанием банковских обновлений» уступает единой модели: AppDock управляет запуском и жизненным циклом платформенного service/host, **Strategy Box владеет AutomationSpec, occurrence, Job и предметным расписанием**. Это не два scheduler для одной задачи.

---

## 2. Карта доверия и модель угроз

### 2.1. Неодинаковые доверенные границы

```text
Ненадёжный Internet/source/archive
                │ validation + content constraints
                ▼
        Data acquisition / parse
                │ semantic qualification
                ▼
        Neutral domain operations
                │ typed Request/Result/effects
                ▼
Product command/authorization boundary ← human / automation / AI
                │ durable admission + version binding
                ▼
       Job execution / workspace/files
                │ intent / staged bytes / receipts
                ▼
         Committed artifacts / state
                │ ACL-filtered projections
                ▼
       Windows / Web / Android clients
                │ platform activation/session
                ▼
               AppDock
```

Исходные веб-страницы, таблицы, ZIP, PDF и загруженные пользовательские файлы — **data**, а не инструкции на выполнение. Плагины и AI не должны повышать свои полномочия текстом содержимого или принадлежностью к одной рабочей среде.

### 2.2. Основные угрозы и ошибочные допущения

| Угроза | Нарушаемая гарантия | Противодействие |
|---|---|---|
| Неверный XLSX/DBF/schema, HTML вместо файла, пересмотр задним числом | analytical integrity | content/schema validation, source snapshot, vintage/version, domain qualification |
| ZIP slip, архивная бомба, XML entity expansion, macro-bearing file | boundary safety, ресурсная изоляция | path containment, entry-count/expanded-size/ratio budgets, safe XML, никакого исполнения макросов при read |
| Произвольный/абсолютный путь, symlink/junction escape | workspace isolation | canonical path resolution на authority, explicit root grant, no-follow или безопасная проверка после resolution |
| Удалённый `timeout` после write | двойной эффект | idempotency key, effect receipt, reconciliation, запрет blind retry |
| Два worker публикуют один файл после истечения lease | lost update / destructive corruption | resource lock + fencing generation + conditional commit |
| Некорректная ACL-filtered subscription | утечка чужих Work/путей/логов | server-side object authorization, per-audience projections/cursors |
| Секрет в параметрах, логах, support bundle или crash dump | credential leak | typed sensitivity/redaction, secret handles, allowlisted diagnostics |
| Ненадёжный Python extension в том же процессе | arbitrary code with process authority | trusted managed activation, provenance/signature/review; отдельная process sandbox для untrusted plugins при появлении продукта |
| AI/Automation от имени устаревшего пользователя | privilege persistence | delegated grant scope/time, revalidation on occurrence and effect |
| Диск полон, state database corrupt, потеря логов | recovery/observability | protective degraded mode, emergency sink, health gates, tested restore |
| Структурная усталость UI: contrast/motion/status only by color | user action safety | keyboard, visible focus, accessible labels, reduced motion и ясные outcomes |

### 2.3. Assurance levels, а не абстрактный «безопасно»

**[TARGET-HYPOTHESIS]** Capability/Operation должны объявлять `assurance_profile`: проверено на unit fixtures, integration fixtures, real source snapshot, bounded production-like workload, destructive fault injection, remote idempotency, access-control matrix. Отдельно фиксируются `tested_environment`, `known_limits`, `last_verified_at`, `contract_digest`. Это полезнее единственного `trusted=true` и предотвращает ошибку «возможность видна в каталоге ⇒ она гарантированно исполнима».

**[UNKNOWN]** Обязательный уровень assurance для каждого класса операций ещё должен быть выбран как Product/Engineering policy, с разными требованиями к read-only, analytics, publication и destructive operations.

---

## 3. Error semantics: точность исхода и природа UNKNOWN

### 3.1. Не одна ось status

**[CONSOLIDATED]** Нужны независимые поля:

- `lifecycle`: `PREPARED | QUEUED | WAITING_RESOURCE | RUNNING | WAITING_INPUT | CANCELLING | FINALIZING | TERMINAL`;
- `terminal_outcome`: `SUCCEEDED | PARTIAL | FAILED | CANCELLED | OUTCOME_UNKNOWN` — только для terminal execution;
- `effect_status`: `NONE | PREPARED | COMMITTED | VERIFIED | PARTIAL | UNKNOWN | COMPENSATED`;
- `availability/health`: `READY | DEGRADED | UNAVAILABLE | UNKNOWN`;
- `domain_qualification`: completeness, validity, freshness, semantic comparability, epistemic support;
- `attention`: `needs_approval`, `unresolved_problem`, `reconciliation_pending`, `stale_projection`.

Это **концептуальный target vocabulary**. Названия в текущем коде отличаются, а `UNKNOWN` в трёх разных полях не означает одну и ту же сущность.

### 3.2. Чёткая классификация отказа

| Класс | Типичный случай | Retry policy |
|---|---|---|
| `NotFound` | объект действительно отсутствует | retry только после изменения ожидаемого состояния |
| `WrongType/InvalidPath/OutOfScope` | каталог вместо файла, выход из workspace | отказ; исправление ввода/разрешения |
| `AuthenticationRequired/PermissionDenied` | не было учётных данных / прав | credential/approval flow, не бесконечные повторы |
| `Unavailable/Timeout/RateLimited` | сервер временно недоступен | bounded retry с backoff, если side effects доказуемо отсутствуют/безопасны |
| `DependencyMissing/Unsupported` | нет codec/provider/capability | config/install intervention, не retry той же попытки |
| `Corrupt/HashMismatch/SchemaMismatch` | повреждение bytes, новый физический формат | quarantine/diagnostics; не молчаливое использование |
| `ValidationFailed/Ambiguous/InsufficientEvidence` | доменный смысл/полнота недостаточны | вернуть квалифицированный Result или отказ по policy |
| `Conflict/RevisionMismatch/ResourceBusy` | конкурирующая мутация | refresh projection, revise/replan, controlled retry |
| `PartialFailure` | часть шагов/файлов сохранена, другие нет | явная неполнота и effect receipts |
| `OutcomeUnknown` | эффект мог состояться до потери ACK | reconciliation; blind retry запрещён |
| `InternalFault` | нарушение инварианта/неожиданный bug | bounded crash capture и owner fix |

**Критическое отличие:** `NotFound` — установленный факт об объекте; `SourceUnavailable` — факт о попытке доступа; `ObservationMissing` — предметная семантика значения. Их нельзя объединять в `None`.

### 3.3. Terminal truth и последовательность переходов

1. Для одного `Job` допускается **не более одного** committed terminal outcome; при корректном terminal завершении — ровно один.
2. `cancel_requested` — управляющее событие, **не** terminal cancellation.
3. Late cancel после committed `SUCCEEDED` не меняет итог.
4. `timeout` измеряет предел ожидания caller, не обязательно доказанный исход worker/effect.
5. `PARTIAL` допустим, когда operation **явно разрешает** partial и перечисляет выполненные/невыполненные postconditions; partial **не** равен «ошибка потерялась».
6. `OUTCOME_UNKNOWN` допускает позднее reconciliation: обновлять требуется запись о выясненном факте/уточнении, сохраняя историю прежнего неизвестного наблюдения. Политика изменения terminal snapshot либо отдельный reconciliation record — **OPEN DESIGN CHOICE**; запрещено молча переписывать forensic history.
7. `run succeeded` ≠ `result accepted` ≠ `claim proved`.

### 3.4. Причинная модель диагностики

Идентификаторы нельзя перегружать:

```text
WorkId       цель и долгоживущий смысл
RunId        конкретный эпизод выполнения Work
JobId        schedulable unit
OperationRunId  invocation конкретной semantic operation
AttemptId    одна фактическая попытка на backend
EffectId/ReceiptId конкретное внешнее воздействие/подтверждение
ProblemRef   зарегистрированная проблема
ArtifactRef  опубликованный результат
TraceId      опциональная корреляция distributed tracing
```

Связи `caused_by`, `parent_run`, `retry_of`, `reconciles`, `triggered_by`, `produced` должны быть явными. W3C `traceparent` полезен как транспортный стандарт для distributed tracing, но не заменяет бизнес-идентификаторы Work/Run/Artifact.

### 3.5. Пример safe result envelope (не действующий API)

```json
{
  "contract": "strategy-box.operation-result/v1-candidate",
  "operation_run_id": "opr-…",
  "lifecycle": "TERMINAL",
  "terminal_outcome": "PARTIAL",
  "effect_status": "VERIFIED",
  "warnings": [{"code": "source.period_unavailable", "scope": "2026-09"}],
  "failures": [],
  "artifact_refs": ["artifact-…"],
  "provenance_ref": "prov-…",
  "problem_refs": [],
  "qualification": {"completeness": "PARTIAL", "freshness": "KNOWN"}
}
```

*Важная деталь:* `failures=[]` при `PARTIAL` может быть корректным, если неполнота вызвана не аварией, а предметным отсутствием части ожидаемых официальных публикаций. Полнота фиксируется отдельно от fault taxonomy.

---
## 4. Reliability, effect safety и восстановление

### 4.1. Классы эффекта

**[TARGET-HYPOTHESIS]** Каждая canonical Operation объявляет эффект, а каждый Run фиксирует фактически обнаруженный эффект:

| Effect class | Допустимый default | Как доказывается итог |
|---|---|---|
| `PURE/READ_ONLY` | параллельное чтение в пределах квоты; bounded retry | входной snapshot, вычисленный Result, absence of mutations |
| `CACHE_WRITE` | повторение при известном content key | hash/cached record; может очищаться отдельно |
| `STAGED_WRITE` | staging в приватном run-space; безопасный abort | temp bytes, digest, финальный manifest/pointer |
| `IDEMPOTENT_WRITE` | повтор с тем же key и тем же immutable request | условная запись либо provider receipt |
| `EXTERNAL_MUTATION` | explicit intent, receipt/reconcile | внешний operation ID, состояние по authority |
| `DESTRUCTIVE` | plan/apply + grant/approval + resource lock | before/after inventory, postcondition, audit |

**Конфликт разрешён:** «все write операции допускают автоматический retry» — неверно; retry policy зависит не только от HTTP status, но и от **эффектов операции**. Объявление `retryable` без effect classification недостаточно.

### 4.2. Стандарт destructive path

```text
[1] Preflight: authority, root/grants, content identity, scheme/version
     ↓
[2] Dry plan: точные resource refs, expected revisions, operations
     ↓
[3] Review / approval при требуемой категории эффекта
     ↓
[4] Acquire resource lock + worker fencing generation
     ↓
[5] Revalidate target, versions and approval just before apply
     ↓
[6] EffectIntent durable record; staging/copy with verify
     ↓
[7] Commit/publish; capture EffectReceipt
     ↓
[8] Verify postcondition; release lock; audit
     ↓
[9] SUCCESS/PARTIAL/UNKNOWN/FAILURE с честной фиксацией
```

FRG уже предоставляет полезный current pattern `build cleanup plan → inspect → apply`, но он должен стать более универсальным для любых разрушительных операций. Plan — самостоятельная сущность с digest и ожидаемыми объектами; approval относится именно к согласованному plan/revision. Одно общее «разрешаю удалять» не подтверждает, что пользователь одобрил вновь пересчитанный список из 5 000 файлов.

**Safety requirements:**

- запрещены операции над корнем разрешённого пространства, `..`-выход, symlink/junction escape и небезопасные UNC/URL-преобразования;
- операции с каталогом/набором файлов допускают **частичный физический эффект**, однако никогда не выдают неподтверждённый полный успех;
- staged copy не удаляет source до завершения полной верификации; fail-safe исход сохраняет source;
- overwrite требует ожидаемой версии цели или отдельной политики, предотвращающей lost update;
- rollback объявляется только для операций, у которых действительно существует обратимый postcondition; `cancel` сам по себе не откатывает внешнюю операцию;
- для внешних систем без транзакционного API используется saga/compensation **только если** компенсация корректна предметно и проверяема;
- retry после `UNKNOWN` требует reconciliation, а не «попробовать ещё раз».

### 4.3. Конкретный дефект класса FileStore на CURRENT baseline

В публичном `LocalFileStore`:

```python
# CURRENT illustration (семантика)
if not p.exists() or not p.is_dir():
    return []
```

Значения «пустая директория», «нет пути» и «есть файл вместо директории» смешиваются. Это **подтверждённый локальный дефект семантики ответа**; network permission errors могут продолжать выбрасываться, поэтому некорректно утверждать, что **все** ошибки backend тотально глушатся. Правильный нейтральный контракт `listdir` должен определять, что `[]` — доказуемо пустой каталог, а отсутствие/неверный тип/ошибка доступа — разные типизированные результаты или исключения.

Второй факт: `_abs()` добавляет заданный `root` к относительному пути, но не устанавливает безопасную root boundary. Он принимает абсолютный path и не проверяет, что конечный путь остаётся внутри разрешённого пространства. В **библиотеке общего назначения** это не обязано быть нарушением, если вызывающий намеренно имеет unrestricted filesystem authority. В server-backed Explorer, HTTP API и AI tool **нельзя** использовать этот helper как готовый sandbox. Product authority должна принимать не произвольный OS path, а разрешённый `WorkspaceRef/ArtifactRef` и проводить path resolution под собственной политикой.

### 4.4. Managed artifact: публикация в два смысловых шага

**[TARGET-HYPOTHESIS]** Надёжная публикация файлового результата:

```text
create ArtifactIntent
    ↓
write under run-scoped staging
    ↓
close and fsync where applicable
    ↓
verify size + digest + schema/content validation
    ↓
publish immutable content/manifest atomically where possible
    ↓
commit ArtifactVersion + catalog linkage + event/outbox
    ↓
make visible to authorized clients
```

Это **не** распределённая транзакция между arbitrary FileStore и SQL. Нужен восстанавливаемый протокол: `STAGED`, `BYTES_PUBLISHED`, `CATALOG_COMMITTED`, `ABANDONED`, `RECONCILIATION_REQUIRED`. Если bytes есть, но catalog update оборвался, reconciler использует intent/manifest и либо завершает, либо карантинирует публикацию. Если каталог ссылается на отсутствующие bytes — artifact остаётся недоступным/повреждённым и не отображается как подтверждённый.

Content-addressed storage, dedup SHA-256 и неизменяемые manifests — сильные идеи второй ветки, но **не Product Decision** и не обязательный стартовый технологический стек. Первой гарантией является *atomic logical publication with verifiable bytes*, а CAS — возможная оптимизация.

### 4.5. Recovery — не просто повторение процесса

При перезапуске service после crash:

1. проверить node identity, storage root, schema/migration journal, transactional integrity;
2. обеспечить единственность active recovery authority;
3. восстановить незавершённые outbox/events и pending commands;
4. найти Jobs с устаревшим heartbeat/lease; определить, жив ли worker на самом деле;
5. проверить EffectIntents, receipts, staging, files и внешние destinations;
6. обновить fencing generation, чтобы старые workers не могли публиковать **управляемые** результаты;
7. безопасные операции перезапускать с **новым AttemptId** и причинной связью;
8. unknown external/destructive effects оставить в reconciliation, автоматический duplicate блокировать;
9. проверить dependency graph и Work/Run terminal aggregates;
10. учесть missed scheduler occurrences по сохранённой misfire policy;
11. опубликовать health/diagnostics и восстановленные read projections;
12. разрешить новые mutating requests только после прохождения hard readiness gates.

**Тонкое место:** lease expiry не убивает старый процесс. Fencing на уровне внутреннего artifact publish защищает собственную authority; это не волшебная защита от неотменяемого внешнего API. Для внешней стороны нужны её idempotency/reconciliation contract либо отказ от автоматических повторов.

### 4.6. Три разных восстановления

- **UI reconnect:** восстановить snapshot и event cursor, сохранить действующий Job; не создавать новый run.
- **Worker retry/resume:** продолжить execution только по checkpoint/effect policy; сохранить Attempt lineage.
- **Product disaster recovery:** восстановить согласованный набор DB + published artifact bytes + manifests + required sources/registries + schema identity + policy references. Не приравнивать это к копированию одной папки.

**[UNKNOWN]** Целевые RPO/RTO, величина допустимой потери telemetry, поддержка crash-consistent versus application-consistent backup и требование multi-node HA зависят от выбранного deployment/класса данных. Их нужно утвердить измеримыми профилями, а не придумывать проценты доступности.

---

## 5. Observability, propagation и problem ownership

### 5.1. Шесть слоёв, шесть назначений

| Объект | Что фиксирует | Durable? | Кто читает |
|---|---|---|---|
| `DomainEvent` | факт перехода Work/Run/Job/Artifact/Automation | durable по policy | projections, audit-causal analysis |
| `ProgressEvent` | стадия, completed/total, единица, timestamp | может быть sampled/coalesced; latest snapshot сохраняется | UI, operator, AI caller |
| `DiagnosticFinding` | проверка готовности/схемы/источника/инварианта | snapshots/reports с lifetime | диагностика, preflight |
| `ProblemOccurrence/Ref` | конкретная зарегистрированная проблема с кодом и ссылками | durable where admitted | оператор, affected user, platform bridge |
| `TechnicalLog/EvidenceRef` | детали исполнения, stack, параметры среды после redaction | bounded rotating files/objects | developer, support, forensic |
| `AuditRecord` | кто и с каким правом запросил/одобрил/выполнил эффект | append-only/controlled retention | authority/security/enterprise |

`Condition` — вычисляемое текущее состояние («источник недоступен», «публикация требует сверки»), которое может связывать несколько ProblemOccurrences. `Incident` нужен позднее только для оперативной группировки проблем, а не как обязательный объект при каждой ошибке. `Metrics` и distributed trace — дополнительная телеметрия, не authority.

### 5.2. Строгое разграничение Strategy Box ↔ AppDock

**[CONSOLIDATED]** `stratbox` сообщает domain diagnostics и typed operation failures, не импортируя AppDock и не создавая platform problem state. Product execution owner коррелирует Work/Run/Job/Attempt и фиксирует собственное execution truth. На границе интеграции adapter может представить диагностическое событие по публичному protocol AppDock. AppDock владеет платформенным occurrence/health/session/node linkage **только для принятой в его observability контур регистрации**. Нельзя считать каждую предметную validation warning платформенной аварией.

```text
Domain failure or platform-facing product fault
      ↓ structured product diagnostic / failure
Product adapter selects reportable platform issue
      ↓ safe ProblemDraft + causal Context
AppDock registration boundary
      ├─ confirmed ProblemRef
      ├─ NOT_WRITTEN
      └─ OUTCOME_UNKNOWN
      ↓
Product stores confirmed ref or explicit registration uncertainty
      ↓
User-facing problem/condition projection with permitted actions
```

**Важное уточнение provenance:** AppDock в своей исследованной документации имеет целевую модель `ProblemDefinition/ProblemDraft/ProblemOccurrence/ProblemRef`, один Recorder и независимую регистрацию с `NOT_WRITTEN/OUTCOME_UNKNOWN`; implementation-status фиксирует завершённые milestones некоторых read-side и registration flows. Это **не основание** объявить любое произвольное product→AppDock problem bridge уже реализованным для Strategy Box. Версия cross-product bridge, ownership map и доступность API — **UNKNOWN**, требует совместного contract test.

### 5.3. Одна физическая ошибка — несколько логических отображений

При аварии файлового backend, затронувшей три Run, допустимы:

- одна `SharedCondition` для текущей недоступности общего ресурса;
- один/несколько `ProblemOccurrence` по правилам определений и causal grouping;
- три affected `Job`/`OperationRun` с собственными outcomes/attempts;
- различающиеся уведомления для owner/participant/operator;
- персональные статусы прочтения;
- отдельные technical logs/evidence с controlled access.

Это **не** означает «разослать traceback всех пользователей всем». Audience определяется объектной ACL, областью влияния и возможностью реального действия. Анонимизированная operational condition — хороший способ предупредить соседних пользователей узла, не раскрывая им чужие пути, параметры, имена файлов и содержимое отчётов.

### 5.4. Structured progress и частота обновлений

`ProgressEvent` должен нести не только проценты:

```json
{
  "job_id": "job-…",
  "operation_run_id": "opr-…",
  "stage": "validate_sources",
  "completed": 18,
  "total": 41,
  "unit": "source",
  "message_code": "sources.validation.in_progress",
  "at_utc": "2026-10-09T12:00:00Z",
  "seq": 157
}
```

`total` может быть неизвестным, и тогда UI использует indeterminate state, явно без фиктивных «93%». Producers должны ограничивать частоту/объём progress событий, а read projections — coalesce их так, чтобы большая операция не заваливала transactional store тысячами transient redraw. Recovery требует как минимум последнего stage/checkpoint и terminal fact, но не сохранения каждой точечки анимации.

### 5.5. Physical logs: состав и границы

Рекомендуемые независимые потоки:

1. **bootstrap/emergency**: доступен до полной инициализации продукта; bounded и максимально safe;
2. **process/application**: startup, configuration, service health, unexpected exceptions;
3. **per-attempt technical logs**: связываются с конкретным Job/OperationRun/Attempt, используют stable IDs;
4. **audit/effect evidence**: durable records для grant/approve/execute/revoke/publish/delete, отдельная retention policy.

Требования: structured timestamp UTC, level, component, correlation IDs, safe error code, redaction policy version, bounded size, rotation, atomic/append semantics, retention/cleanup, permissions для каталога и support bundle. Логи **не** должны сами владеть Job state. Абсолютный OS path к лог-файлу — локальный implementation detail, а в cross-device projection передаётся `LogRef`, разрешаемый авторизованным сервисом.

**Непрерывность:** если UI или logger падает, сам worker не должен терять сведения о последней committed стадии. Если записать warning-лог невозможно, это отдельный health finding. Если обязательный audit/effect receipt записать невозможно, destructive action блокируется до восстановления audit boundary; это пример осознанного fail-closed. Если недоступен необязательный debug sink, допустим degrade без остановки read-only вычисления.

### 5.6. Privacy и право на диагностическую информацию

Минимальный набор ролей аудитории:

- **пользователь**: безопасное объяснение, затронутый объект, следующий допустимый шаг, свой progress, собственные artifacts;
- **оператор**: условия узла, агрегированная готовность, redacted causal references, разрешённые repair actions;
- **разработчик**: technical evidence при явной технической авторизации;
- **AI consumer**: структурированная safe диагностика и разрешённый remediation action, без raw secret/path/stack;
- **forensic**: расширенные свидетельства при отдельной политике доступа/учёта обращения.

Секреты, bearer tokens, переменные окружения с credentials, частные абсолютные пути, тело пользовательских выгрузок, cookie, query-параметры с токенами, строки из source document и произвольные exception messages нельзя автоматически отправлять в UI или общий incident feed. Redaction применяется **до** экспорта через trust boundary; downstream UI не должен быть единственным фильтром.

### 5.7. Support bundle, diagnostics и repair

**Диагностика** — read-only verified inspection, с собственным отчётом о полноте проверок (`COMPLETE/PARTIAL/UNKNOWN`). **Repair** — явная команда владельца с эффектами, approval и audit. «Проверить и поправить всё» без отдельного consent нарушает safety semantics.

`SupportBundle` может включать: product/contract versions, sanitized readiness snapshot, selected ProblemRefs/definitions, causal events, bounded technical logs, package/source hashes, failed test/diagnostic codes, OS/Python/platform profile в безопасном виде, manifest своих файлов и срок хранения. По умолчанию исключаются исходные банковские файлы, пользовательские артефакты, секреты и полный dump среды. Перед экспортом — preview policy и redaction report. Support bundle сам является артефактом с audit trail.

### 5.8. Operational SLO/SLI без выдуманных значений

Предлагаемые **метрики, а не установленные SLA**:

| SLI | Формула/наблюдение | Почему полезна |
|---|---|---|
| completed job reliability | terminal verified / admitted within policy window | различает реальный успех и незакрытые unknown |
| unknown-outcome backlog | count/age unresolved `OUTCOME_UNKNOWN` | сигнал проблем reconciliation |
| artifact publication integrity | digest+manifest verifications / publication attempts | проверка надёжности результатов |
| recovery completion | successfully reconciled active jobs after restart | способность восстановиться |
| event delivery lag | now − committed event time на разрешённой projection | реальная свежесть чата/Task Center |
| resource queue delay | started − accepted, по классам | fairness и ёмкость worker pool |
| storage pressure | bytes free / quota / projected staging growth | предупреждение DiskFull |
| log/audit pipeline health | sink errors, backlog, drops, denied writes | наблюдаемость самой наблюдаемости |
| source freshness compliance | snapshots satisfying configured policy | корректность обновления данных |
| UI feedback latency | interaction→ack / projection event→visible update | performance и качество взаимодействия |

Не задавать «99.99% uptime», RPO/RTO или конкретные пороги p95 до определения профилей: локальный ноутбук, корпоративный shared node и self-hosted server имеют различные режимы ожидания и бюджет.

---

## 6. Identity, authorization и доверие к расширениям

### 6.1. Identity, actor и authority — три разные вещи

`Principal` — субъект полномочий; `Actor` — инициатор конкретного действия (человек/automation/AI/system); `Session` — временный канал; `Node` — рабочая среда/область authority. `User` и экранное имя не являются техническим доказательством прав. Сессионный токен также не даёт одинаковый доступ ко всем ресурсам узла.

Право на эффект — отношение:

```text
Principal × Action × Resource/Scope × EffectClass × Time × PolicyRevision
                         + optional Approval/Delegation
```

**Требование:** различать `DISCOVERABLE`, `AVAILABLE`, `APPLICABLE`, `AUTHORIZED`, `APPROVED`, `EXECUTABLE_NOW`. UI получает server-computed `ActionAvailability` и показывает причину запрета. Но UI disabled button — лишь подсказка; enforcement принадлежит command boundary и, если нужно, effect boundary.

### 6.2. Минимальный capability-based permission vocabulary (кандидат)

```text
work.view.own / work.view.shared
work.create / work.accept / work.close
scenario.run
job.cancel.own / job.cancel.any
artifact.read / artifact.publish / artifact.delete
workspace.read / workspace.write.own / workspace.write.shared
logs.read.summary / logs.read.technical
assignment.create / assignment.manage
approval.grant
node.health.view / node.repair
settings.manage.user / settings.manage.node
automation.create / automation.manage
```

Стабильные capability names и Roles-bundles не отменяют **object-level ACL**. Нужна проверка конкретного Work, Artifact, workspace-root, audience и sensitivity, включая inherited permissions. Нельзя считать «пользователь участник узла» эквивалентом доступа ко всем его объектам.

### 6.3. Approval является versioned binding, а не вечной кнопкой

Approval record должен связывать actor/grantor, запрошенный scope и конкретный `plan_digest`, resource identities и expected revisions, сумму/масштаб действия при наличии, deadline/expiration, permission version, reason и сохранённую decision. Если в плане поменялись целевые папки или версия содержимого — прежняя approval теряет применимость. Для delegated automation/AI эффекта проверка повторяется при occurrence и перед actual apply.

**Open question:** минимальный формат approval и policy для local single-user без корпоративного identity provider. Концептуальное правило остаётся единым, а отдельные deployment profiles могут автоматически удовлетворять низкорисковые approvals явно определённой policy.

### 6.4. Плагины: discovery, activation, trust

В системе возможны generic contributions к storage, sources, formats, report styles, operations, health и configurable providers. Здесь важны **только публичные нейтральные требования**:

- Installed ≠ discovered ≠ compatible ≠ selected ≠ bound ≠ ready.
- Entry point/manifest — способ обнаружения, **не** доверенная санкция исполнения.
- Каждый contribution имеет stable ID/version, expected core/application API versions, permissions/effects, capabilities и conformance profile.
- Изменение активного provider во время Run не меняет задним числом immutable `ActivationBinding`.
- Отсутствие требуемого provider не должно тайно заменяться другим, меняя destination или уровень гарантий.
- In-process Python extensions обладают полномочиями процесса: descriptor с declared effects сам по себе **не является sandbox**.
- Unknown/untrusted third-party executable contributions требуют отдельной process/OS isolation и новой модели доступов, либо отсутствуют как поддерживаемая возможность.
- Удаление/отключение extension прекращает **новые** invocations, но не стирает provenance/manifest уже опубликованных результатов.
- UI skin, произвольное выполнение widgets и внедрение навигации через business provider следует считать **другой, более опасной моделью расширений**; если в первом цикле она не нужна, не открывать такой ABI.

**[CONFLICT/UNKNOWN]** Должно ли локальное окружение допускать автоматическую смену provider при ошибке? Для интерактивного разработческого профиля fallback может быть полезен. Для управляемого shared/data-sensitive профиля замена backend без подтверждённой политики должна останавливаться с `NOT_READY`/`CONFIGURATION_ERROR` и указанием безопасного исправления. Это policy-переключение, не новая реализация корпоративного плагина.

### 6.5. Web/remote boundary

При появлении server-backed Web нужны как отдельные проверяемые controls: HTTPS и доверенная session model; server-side authn/authz на **каждом** endpoint; CSRF для cookie-based mutations; защита от XSS/инъекций при визуализации внешних источников; CSP и security headers; origin/host allowlist; upload validation/limits/quarantine; signed/authorized artifact download; rate limiting/quotas; закрытие технических endpoints; запрет unrestricted filesystem traversal; auditing privileged mutations.

Точные протоколы (OIDC, local accounts, reverse proxy, SSE, WebSocket) являются **deployment/architecture choice**, но принципы isolation и авторизации сохраняются. Для Web baseline полезно использовать OWASP ASVS 5.0 как проверяемый каталог security requirements, не заявляя, что Strategy Box уже прошёл ASVS audit.

### 6.6. AI: capability consumer, а не привилегированный администратор

Разрешённый AI actor получает только отфильтрованные `CapabilityDefinition/OperationDefinition`, `ActionAvailability`, safe results, ProblemRef и approved artifacts. Любой proposed plan проверяется тем же admission, resource claims, effect policy и approval, что ручной запуск. Промпт в извлечённом PDF, HTML, таблице, комментарии или логе не может стать command authority. Сырые секреты не передаются в агентский context. AI action остаётся связанной с underlying Principal/delegation и следом аудита.

---

## 7. Concurrency, idempotency и distributed execution

### 7.1. Четыре независимо управляемые конкуренции

1. **State concurrency:** две команды меняют Work, Assignment, Automation или Artifact metadata → `expected_revision`/CAS и транзакция.
2. **Resource concurrency:** два Jobs пишут в один output, используют один non-thread-safe registry/cache/file → `resource_claims`/lock.
3. **Execution custody:** два workers считают один Job после failover → worker lease + heartbeat + fencing generation.
4. **Publication concurrency:** два завершённых Jobs пытаются опубликовать одну destination version → conditional publish/manifest hash и artifact version identity.

Один глобальный mutex на весь Strategy Box уменьшает число ошибок ценой отказа от параллельного чтения и неспособности работать нескольким пользователям. Более узкий resource coordination достигает той же safety для конфликтующих effects при лучшем throughput.

### 7.2. ResourceClaim и ResourceLease (проектный контракт)

```json
{
  "job_id": "job-…",
  "claims": [
    {"resource": "source:cbr.forms.802@2026-07-01", "mode": "READ"},
    {"resource": "workspace-output:report-monthly", "mode": "WRITE"}
  ],
  "lease": {"worker_id": "worker-…", "generation": 12},
  "expected_artifact_revision": 7
}
```

`resource` — нормализованная identity, а не произвольная строка пользовательского пути без canonicalization. `READ` совместим с `READ`; `WRITE/DESTRUCTIVE` требуют собственной conflict policy. Доступность resource и авторизация не следуют из получения lock. При acquisition нескольких ресурсов необходим устойчивый порядок для минимизации deadlock; при долгих Jobs — bounded wait, cancellation, fairness и user-visible queue position/stage без обещания точного ETA.

### 7.3. WorkerLease ≠ ResourceLock

WorkerLease отвечает «кто сейчас вправе менять Job custody», ResourceLock — «кто вправе изменять конкретный target». Expired lease допускает появление **зомби-worker**. Смена `lease_generation` и проверка generation во всех собственных commit/publish boundaries прекращает право старого исполнителя публиковать canonical success. Внешний сервис без fencing по-прежнему может принять старый запрос; для него требуется отдельная idempotency/effect policy.

### 7.4. Idempotency: четыре разных смысла повтора

| Действие | Семантика | Identity |
|---|---|---|
| Дважды нажать «Запуск» до ответа | повторение **одной** команды | same principal/scope/idempotency key и digest запроса |
| Retry после transient failure | новая Attempt **той же** OperationRun при разрешённой policy | `retry_of`, attempt number, effect status |
| Repeat scenario | **новый Run**, иногда новая Work в зависимости от intent | new RunId, свежий intent/binding as requested |
| Reuse verified result | отсутствие нового вычисления при доказанной эквивалентности и freshness | content/result identity, provenance, applicability |

Нельзя делать dedup только по `operation_id + JSON parameters`. В identity могут входить source/registry snapshots, semantic definition revision, effective authority, output destination/effects, policy, time scope. `JOIN` одинаковых read-only источников не означает автоматическое объединение **разных** destructive effects или публикаций в разные каталоги.

**Новый важный нюанс:** если пришёл тот же idempotency key **с другим** request digest, возвращается explicit `CONFLICT`, а не старый успешный response от чужого запроса.

### 7.5. Exactly-once — ограниченная гарантия

Внутри transactional authority достижима **at-most-once command acceptance** на identity key и exactly-one terminal commit по Job. Доставка событий и worker execution обычно допускают повторы (at-least-once). Для внешнего side effect не следует обещать global exactly-once, пока upstream/downstream не поддерживают сопоставимую idempotency/receipt semantics. Целевая гарантия формулируется осторожнее: **безопасное принятие команды, защищённая публикация собственных результатов, обнаружение неопределённых эффектов и доказуемая сверка**.

### 7.6. Schedule/DST/misfire тоже quality gates

Одно расписание хранит civil time rule, timezone, revision, resolved UTC occurrence и unique occurrence key. После DST/reboot/sleep policy должна решать `skip | coalesce | run_latest | bounded_catchup` и overlap `queue | skip | coalesce | allow_parallel_if_safe`. Repeated hour и nonexistent local hour должны иметь явную policy. `enabled` лишь означает активацию определения Automation, а не `Job.running`.

При scheduler restart нельзя создавать вторую occurrence того же логического срока. Время устройства клиента не является scheduler authority. Каждый occurrence заново проверяет актуальные grants и версии capabilities.

---

## 8. Persistence, migrations, versioning, supply chain

### 8.1. Durable state и projection

**[CONSOLIDATED]** Жизненно важные Work/Run/Job/Attempt, command keys, resource leases, artifact catalog, effect intents, automation cursors, approvals/ACL и audit должны иметь transactional consistency в своей authority. Windows JSON-проекции текущего baseline подходят для локальных recent-state/preferences, но **не** заменяют shared transactional model. UI хранит geometry, drafts и навигацию как local preferences, а не как исполнение.

Предпочтительная логическая модель: небольшие domain repositories + transaction/unit-of-work, append-only causal event records и outbox, read projections. Для single-node может подойти SQLite, для server/multi-writer — PostgreSQL либо равнозначный backend. Это **совместимые профили**, а не два конкурирующих определения Work.

### 8.2. Минимальные transactional invariants

- атомарная проверка `expected_revision`, прав, state transition и вставка event/outbox;
- `UNIQUE(job_id)` для записи terminal outcome; уникальность пары `(job_id, kind)` недостаточна: она позволила бы несколько разных terminal kinds;
- уникальность `(authority_scope, idempotency_key)` + контроль request digest;
- уникальность `automation_revision + trigger_id + occurrence_key`;
- последовательность domain event identity и gap-aware API cursor;
- foreign-key/referential integrity для подтверждённых refs;
- orphan/staging garbage collection отдельно от committed artifacts;
- atomic write/rename маленьких preference files при отсутствии общей DB;
- при повреждённом persisted state — explicit `CORRUPT/DEGRADED` и read-only диагностика, не silent empty reset.

### 8.3. ACL-filtered event feed: важный белый пробел

Глобальная последовательность событий `node_seq` полезна для внутренней диагностики, но публичный поток, в котором клиент получает только разрешённые записи, **может раскрыть наличие чужой активности через gaps/частоту**. Для строгого multi-tenant privacy нужен per-audience cursor или серверный opaque cursor с безопасной семантикой пропусков и подпиской на изменения ACL. Клиент не должен делать собственную фильтрацию уже доставленных секретных событий.

**[UNKNOWN]** Точная модель `cursor`, когда доступ отозван между Snapshot и event replay; поведение при смене audience/permissions; searchable index ACL filtering и ретроактивность прав на старые артефакты. Это архитектурные security вопросы, а не просто техника SSE.

### 8.4. Version vector вместо одного номера пакета

Для воспроизводимости необходимо различать:

| Version axis | Что именно меняет |
|---|---|
| Product/API | публичную схему команд и surface projections |
| Core distribution | реализации доменных алгоритмов и IO |
| Canonical Operation/Capability | семантический контракт, pre/postconditions и effects |
| Execution plan + activation binding | конкретный состав шагов, providers, resources, parameters |
| Persistence schema | формат durable records, миграции и rollback admissibility |
| Artifact/manifest | внешний формат refs и опубликованных результатов |
| SourceSnapshot | физические bytes/vintage/схема исходной публикации |
| RegistrySnapshot | официальные/курируемые reference values и effective dates |
| Format/codec | декодирование/запись и quality guarantees |
| Platform activation | версию AppDock connector, activation context, runtime bindings |
| Extension/Provider contract | совместимость generic capability contributions |
| Algorithm/Solver | численные методы, solver version, tolerance/assumption tier |
| Design/projection | визуальное представление; по умолчанию не должна менять экономический смысл |

Совпадение версии Python-пакета само по себе не доказывает сохранность экономического смысла или установленной execution graph. Изменение банковского справочника или ОКВЭД способно менять identity и результаты; оно должно отражаться в provenance, а не только в release notes.

### 8.5. CURRENT contract drift — P0 release blocker

- `stratbox` package `0.8.0` и `stratbox-windows` pinned `stratbox==0.2.1`;
- Connector Manifest Windows `4.0`, однако smoke test ожидает `3.0`, `package_identity` вместо `package_requirement`;
- Windows baseline содержит закоммиченные временные `.tmp` и `.pyc`, а CI/release test gates неполны;
- Runtime и docs version terminology смешивает Connector Manifest, Surface Activation и Activation Context; их **нужно версионировать и документировать раздельно**.

**Рекомендуемое действие:** зафиксировать coherent release tuple `(core, application, surface, AppDock connector/activation, storage schema, Operation API)` и тестировать **устанавливаемые wheel/build artifacts**, а не только импорты исходной папки. Тот факт, что reverse compatibility проекту не нужна, **не** освобождает от детектирования несовместимости уже сохранённого состояния и уже установленной поставки.

### 8.6. Schema migration без обязательства backward-compatible API

**[TARGET-HYPOTHESIS]** При обновлении persisted schema:

1. заранее выполнить inspect current version и план изменения;
2. сформировать consistent backup/checkpoint с identity;
3. получить exclusive migration lock;
4. выполнить versioned миграцию атомарно либо с возобновляемым journal;
5. подтвердить post-migration integrity, FK, sample read, release tuple;
6. обновить schema identity и только затем допустить mutating traffic;
7. при несовместимости — controlled refusal/diagnostic mode, без импровизированного старого reader.

Отказ от поддержки **старого интерфейса** позволяет чисто заменить API, но хранимые Work/Artifacts/Provenance не могут быть забыты «потому что структура изменилась». Возможны явный одноразовый converter/export, архивирование прежнего состояния или controlled reset **только если** Product Decision допускает потерю этих данных и имеется проверенная резервная копия.

SQLite online backup API — подтверждённый официальный способ получить согласованный снимок живой БД; копирование открытого `.sqlite` без учёта WAL нельзя принимать за доказанно корректную recovery procedure.

### 8.7. Source/registry freshness и воспроизводимость

Current core содержит packaged bank/OKVED snapshots, которые на исследованном срезе старше актуальных официальных публикаций. Это не доказывает ошибочность каждой строки: **freshness status** относится к конкретному use case/period/authority. Историческое воспроизведение обязано уметь **законно закрепить старую** registry revision. Новая оценка текущего рынка требует revalidation.

`SourceSnapshot` и `RegistrySnapshot` необходимо отличать от изменяемого `latest` alias. Если run уже начал работу, отсутствие pinned snapshot/transform version допускает тихую смену смысловой основы в середине расчёта. Для математической реконструкции особенно критичны версии solver, tolerance, assumption tier, crosswalk и идентичность исходных публикаций.

### 8.8. Managed supply-chain и package integrity

**[TARGET-HYPOTHESIS]** Release pipeline сохраняет dependency lock/BOM, hashes distributions, source revision, build provenance, тесты installation/entrypoint/ABI, подписи либо другие аттестации доверенной поставки в тех профилях, где это требуется. Реальная policy для закрытых/внутренних managed packages задаётся владельцем deployment. При обнаружении несовместимого/недоверенного пакета — controlled activation failure, а не неконтролируемый import/auto-install на рабочем компьютере.

---
## 9. Performance, portability, accessibility и ресурсные ограничения

### 9.1. Производительность — часть корректности, а не только UX

Для аналитического продукта недостаточно, чтобы алгоритм возвращал верное значение при неограниченной памяти и времени. Он должен иметь определённый resource profile. Даже read-only операция, потребляющая весь RAM узла, может разрушить устойчивость соседних Jobs. Производительность также влияет на безопасность: зависший UI или бессрочная очередь побуждают пользователя повторять запуск, создавая дублирующие эффекты.

**[CURRENT]** Core уже имеет специализированные performance tests и budgets в подсистеме SORS, но это **локальный тестовый контур**, не общая ресурсная политика Strategy Box. `FileStore.read_bytes/write_bytes/copy` существуют как whole-object операции; в Windows long operation вынесена в Qt worker thread, однако приложение допускает один одновременный GUI-scenario и не реализует resource-aware job pool. Существующие model/view элементы UI не подтверждают общую гарантию виртуализации больших историй и логов.

### 9.2. Ресурсный контракт Operation

**[TARGET-HYPOTHESIS]** OperationDefinition/CapabilityEnvelope заявляют:

```text
estimated_runtime_class
peak_memory_class / known_bound
scratch_disk_requirement
network_payload/read-write budget
max_concurrency / exclusive_resources
streaming_available / seek_required
parallelism controls
interruptibility / cancellation safe points
cost_estimate_confidence
input_size / topology / solver sensitivity
```

Run допускается после preflight по Node budgets; при недостатке ресурса возвращается структурированный `QUEUEABLE | RESOURCE_INSUFFICIENT | RESOURCE_ESTIMATE_UNKNOWN`, а не «возможно, получится». Estimates — условные и версиионно-зависимые, особенно для разреженных LP/solver workflows, Excel exports и больших ZIP/PDF. Отсутствие estimate не должно автоматически означать «0 CPU, 0 RAM».

### 9.3. Сквозные performance-бюджеты: что измерять

| Контур | Измерение/ограничение | Рекомендуемый механизм |
|---|---|---|
| Core/source fetch | bytes downloaded, connection timeout, retry count, transport backoff | shared HTTP session/timeout contract, bounded source validation |
| Codec/format import | compressed/expanded size, number of entries, RAM multiplier | streaming, archive quotas, detection and validation before expansion |
| SORS/math | input topology, nonzero matrix elements, solver iterations, memory/time | deterministic benchmark fixtures, solver version, optional topology cache |
| Artifact writer | buffered bytes, spill-to-disk, temp disk consumption, commit latency | streaming/staged writes, abort, digest verification |
| JobManager | queue wait, running count, active claims, worker memory | resource-aware admission, bounded pools, backpressure |
| Persistence | transaction latency, WAL/storage growth, event backlog | indexes, retention, controlled checkpoint/vacuum |
| Event stream | events/sec and bytes/client, lag, dropped/coalesced progress | bounded buffers, snapshot+cursor protocol |
| Explorer/history/log | row counts, initial render, incremental fetch, scroll latency | virtualization and paged queries |
| Preview | max preview bytes, time and format safety | sandboxed/bounded preview, no unsolicited heavy conversion |
| Android/Web | bandwidth, battery/background quotas, offline cache size | thin projections, conditional fetch, avoid heavy local computation |

**[UNKNOWN]** Фиксированные p95 latency budgets, минимальные hardware profiles, max upload size, допустимая частота progress, размер in-memory cache и persistence cap. Это должен установить отдельный measurement baseline на медленном целевом ПК, типовом Windows-узле и server/host профиле. Механическое перенесение любых красивых миллисекунд из motion research в operational SLA ошибочно.

### 9.4. Stream/seek и большой FileStore

Нельзя считать `open_read()` автоматически streaming, если конкретный backend буферизует весь файл до выдачи `BytesIO`. Контракт должен явно различать:

- `streaming_read`, `streaming_write`, `range_read`, `seek`, `atomic_replace`, `multipart_upload` как optional provider capabilities;
- корректное `begin_write → write → verify → commit` или `abort`;
- fallback через temporary local materialization с quota/cleanup, только когда это разрешено;
- `MemoryBudgetExceeded`/`StreamUnavailable` как truthful failures.

Специализированные Excel-инструменты могут нуждаться в seekable file и потенциально больших temporary files; автоматический «универсальный» stream не устраняет constraints формата. Требуется capability-dependent choice, а не обманчивая универсальная функция.

### 9.5. Windows/Web/Android: одинаковая семантика, разные бюджеты

Общие сущности Work, Scenario, Job, Problem, Artifact, availability и authority должны быть платформенно-нейтральными. Windows может использовать Qt renderer, Web — безопасные server-backed projections, Android — companion/компактное управление. В тяжёлых расчётах mobile предпочтительно поручает исполнение authorized host, вместо попытки держать solver или большие файлы в фоне телефона.

`runtime.bootstrap`, использующий Qt-specific coordinator в baseline, — известная граница portability. Общая orchestration/control logic должна быть импортируема без PySide6; Qt callbacks/signals — presentation bridge. Параметры форм и state projection сериализуются versioned contracts, а не передаются через классы widgets.

**Offline/reconnect:** клиент вправе кэшировать ранее разрешённые projections с `observed_at`/staleness indicator. Offline UI не создаёт ложные terminal outcomes. Mutating commands offline требуют explicit queueability, expiration, повторной authz и idempotency upon reconnect; destructive commands по умолчанию не выполняются из автономной offline очереди.

### 9.6. Accessibility — гарантия отсутствия ошибочных действий

Минимальная целевая программа доступности:

- последовательная клавиатурная навигация, focus order и **видимый focus ring**;
- каждое значимое действие, иконка, progress и статус имеют label/semantic role;
- предупреждение и ошибка выражены текстом/формой, не только красным/зелёным;
- контраст текста/контролов и high-contrast mode проверяются по принятому WCAG-profile;
- screen reader получает результат запуска, стадию и безопасное объяснение проблемы без чтения гигантского технического traceback;
- reduced-motion preference убирает бесконечные декоративные движения, заменяя running-indicator статическим доступным эквивалентом;
- resize/scaling и density не делают кнопки `Cancel`, `Confirm`, `Delete` микроскопическими;
- drag-and-drop имеет keyboard/menu alternative;
- фокус/scroll position сохраняются при live updates; автопрокрутка чата не перехватывает пользователя, читающего историю;
- modal approval traps, shortcuts для опасных действий и destructive confirmation тестируются отдельно;
- интерфейс сообщает о неопределённом исходе **явно и спокойно**: «Связь потеряна, уточняем, завершилась ли операция», без ложного «Не удалось» при неизвестном эффекте.

**[CONSOLIDATED]** Motion следует semantic state, не создаёт новое состояние. Анимация успеха до transactional commit — нарушение truth-first UX. `reduced motion` не имеет права скрыть сам факт pending/retry/unknown.

### 9.7. Internationalization/localization и время

Хотя в исходном списке осей нет отдельного I18N, он является сквозным quality white spot. Stable problem codes, `unit`, period/zone semantics, timestamps UTC и localized message templates должны быть разделены. Пользовательские русские названия банков/форм остаются domain data, а `ProblemCode` и terminal state не локализуются для хранения. В интерфейсе UTC timestamp показывается в зоне пользователя с указанием контекста; cadence и DST schedule рассчитываются по сохранённой зоне Automation, а не по устройству, открывшему карточку.

**[UNKNOWN]** Обязательные UI locales, политика перевода банковских названий, форматы дат/чисел и screen reader platforms будущего Android/Web. Это требует product profile, а не преждевременного многоязычного framework.

---

## 10. System-wide invariants: кандидатная «конституция» качества

Ниже — **исследовательские требования** с идентификаторами `SB-Q-*`. Это не действующие policy IDs и не утверждённая продуктовая спецификация. Каждому соответствует проверяемое нарушение; так можно переносить их в contract tests без разночтений. Поля `Evidence` отсылают к журналу источников в конце документа.

### 10.1. Semantic & truth (T)

| ID | Invariant | Пример негативной проверки |
|---|---|---|
| **SB-Q-T01** | Ошибка транспорта не становится успешным пустым результатом | backend timeout during `listdir` → typed failure, не `[]` |
| **SB-Q-T02** | `NotFound`, `PermissionDenied`, `Unavailable`, `Unsupported`, `WrongType` различаются | matrix для FileStore/HTTP/codec |
| **SB-Q-T03** | Execution, effect, domain qualification и Work acceptance имеют разные статусы | successful export + invalid comparability → Work awaiting review |
| **SB-Q-T04** | Семантическое `UNKNOWN` не заменяется default `0/False/empty` | отсутствует официальное значение → missingness, не zero |
| **SB-Q-T05** | Representation не повышает provenance/evidence tier | UI не показывает слабую реконструкцию как официальный факт |
| **SB-Q-T06** | Terminal outcome Job коммитится не больше одного раза | конкурентные cancel/success → один terminal record |
| **SB-Q-T07** | `PARTIAL` возможен только при явном policy и residual ledger | один файл из пяти не записан → нет global success |
| **SB-Q-T08** | Определение операции, binding, invocation и Attempt имеют разные ID | repeat/retry не теряют историю |

### 10.2. Effects & concurrency (E)

| ID | Invariant | Проверка |
|---|---|---|
| **SB-Q-E01** | Destructive plan идентифицирует точный scope, revision и postconditions | изменённый plan после approval отклоняется |
| **SB-Q-E02** | Source не удаляется после неуспешного copy/verify | fault injection в N-й файл каталога |
| **SB-Q-E03** | Частичное физическое удаление не возвращает подтверждённый full success | один `remove` denied → PARTIAL/FAILURE с receipts |
| **SB-Q-E04** | Команда повторяется безопасно по key + request digest | duplicate Submit не создаёт второй Job |
| **SB-Q-E05** | Та же idempotency identity с другим request digest отклоняется | key collision → conflict |
| **SB-Q-E06** | Timeout после необратимого эффекта не вызывает blind retry | delayed ACK simulation |
| **SB-Q-E07** | Expired worker не публикует под старой fencing generation | zombie-worker races |
| **SB-Q-E08** | Resource conflicts координируются вне UI и без глобальной сериализации | concurrent READ разрешены; конфликтующие WRITE блокируются |
| **SB-Q-E09** | Cancel request и terminal cancellation — разные факты | cancel после commit не меняет success |
| **SB-Q-E10** | Один logical schedule occurrence не рождает два effectful Runs | crash between enqueue/ack/restart |
| **SB-Q-E11** | Удалённый executor не получает больший authority, чем разрешённый binding | policy revocation during run |
| **SB-Q-E12** | Неизвестный внешний эффект оставляет reconciliation evidence | network partition before ACK |

### 10.3. Durable state & artifacts (D)

| ID | Invariant | Проверка |
|---|---|---|
| **SB-Q-D01** | UI не владеет durable Work/Job truth | закрытие Windows/Web, reconnect |
| **SB-Q-D02** | Committed artifact ссылается на верифицированные bytes/manifest | mismatch digest → quarantine |
| **SB-Q-D03** | Неполная staged запись не публикуется как completed artifact | disk full during XLSX writer |
| **SB-Q-D04** | Path/name/mtime не являются полной artifact/source identity | одинаковый filename с новыми bytes |
| **SB-Q-D05** | Broken/corrupt durable state не превращается в пустой новый store | truncated JSON/DB fault → degraded |
| **SB-Q-D06** | State transition + event/outbox commit атомарны в scope authority | crash between two logical updates |
| **SB-Q-D07** | Persisted schema несовместимость видна до mutating work | upgrade with old schema version |
| **SB-Q-D08** | Backup содержит полный согласованный recoverability set | restore DB без artifact bytes → explicit failure |
| **SB-Q-D09** | Retention не удаляет ещё referenced published bytes | GC under shared artifact references |
| **SB-Q-D10** | Source/registry/algorithm versions доступны из существенного Result | reproduce historical report |

### 10.4. Security & audience (S)

| ID | Invariant | Проверка |
|---|---|---|
| **SB-Q-S01** | Effective permission проверяется в authority, не в UI | forged API command despite disabled button |
| **SB-Q-S02** | Approval связана с конкретным plan/effect/scope/version | changed destructive targets → new approval |
| **SB-Q-S03** | AI/Automation не наследует бессрочные или неограниченные grants | revoke permission then fire occurrence |
| **SB-Q-S04** | Client не получает чужие raw logs, paths, artifacts и secret data | two-user ACL/fetch subscription matrix |
| **SB-Q-S05** | Provider discovery не равен trusted activation | malicious descriptor cannot self-activate |
| **SB-Q-S06** | Публичные core/surface не зависят от конкретных закрытых реализаций | static dependency/import scan |
| **SB-Q-S07** | Untrusted source content никогда не становится executable instruction | prompt injection in PDF/HTML metadata |
| **SB-Q-S08** | User-controlled filesystem references не выходят за разрешённый namespace | `../`, absolute, symlink/junction escape |
| **SB-Q-S09** | Обязательная audit/effect запись предшествует destructive commit | unavailable audit sink → action denied |
| **SB-Q-S10** | Опубликованная projection фильтруется до transport | event feed с чужими объектами и cursor |

### 10.5. Observability, operability, UX (O)

| ID | Invariant | Проверка |
|---|---|---|
| **SB-Q-O01** | Каждый Job/Attempt имеет восстанавливаемую причинную цепочку | inspect failures after worker crash |
| **SB-Q-O02** | Raw exception/traceback — evidence, а не durable product state | serializable state schema rejects exception |
| **SB-Q-O03** | Confirmed ProblemRef не выдумывается при failed/unknown recorder | simulated recorder timeout |
| **SB-Q-O04** | Общий сбой показывается affected users через safe Condition | shared backend outage; privacy matrix |
| **SB-Q-O05** | Diagnostic check не скрытно исполняет Repair | offline diagnostics must be read-only |
| **SB-Q-O06** | Потеря telemetry отмечается отдельно от business terminal truth | log sink crash during successful read |
| **SB-Q-O07** | User status объясняется доступным текстом, не только цветом/анимацией | screen reader/reduced motion mode |
| **SB-Q-O08** | Progress не объявляет выдуманную полноту | unknown total, stalled stage |
| **SB-Q-O09** | Contract drift ловится release test до distribution | manifest/tests/package tuple mismatch |
| **SB-Q-O10** | Система безопасно деградирует при storage/config/health failure | DB unavailable; diagnostic-only boot |

**Итого:** 50 кандидатных инвариантов (T=8, E=12, D=10, S=10, O=10). Их использование требует последующего Product admission. На этом этапе они образуют проверяемую исследовательскую матрицу; новые инварианты предлагается добавлять только при реальном пропуске, а не по аналогии ради симметрии.

---

## 11. Реестр пересечений, конфликтов и superseded решений

| ID | Исходное расхождение | Консолидированный вердикт | Статус |
|---|---|---|---|
| C08-01 | `Case` как long-lived Work vs Case как запущенный scenario | Current `ScenarioRunCase` похож на Run projection; Work — отдельное смысловое обязательство | **SUPERSEDED** для идеи одного универсального Case |
| C08-02 | Один GUI worker vs shared durable JobManager | Первый — prototype, второй — target authority | **CURRENT/TARGET**, не два равноправных дизайна |
| C08-03 | AppDock Scheduler vs Strategy Box scheduler | AppDock: lifecycle/platform; Strategy Box: domain automation/occurrences | **RESOLVED** |
| C08-04 | SQLite vs PostgreSQL | Профили физической поставки под одним semantic persistence port | **SCOPE DIFFERENCE** |
| C08-05 | `[]` для missing path vs «empty is only empty» | Требуется truthful error model и корректировка нейтрального FileStore contract | **REAL CURRENT GAP** |
| C08-06 | `warning` как run status vs terminal outcome + diagnostics | Трёхосевая модель lifecycle/disposition/attention | **SUPERSEDED** |
| C08-07 | Timeout = failed vs UNKNOWN | Caller observation не доказывает effect; нужен reconciliation | **SUPERSEDED** |
| C08-08 | Retry/Repeat/Resume как одна кнопка | Разные identity и эффектная семантика | **RESOLVED** |
| C08-09 | Path-oriented artifacts vs immutable managed ArtifactRef | Physical path полезен для workspace; managed identity должна быть логической | **CONSOLIDATED**, CAS всё ещё гипотеза |
| C08-10 | Manifest truth vs DB catalog truth | Manifest удостоверяет content/provenance; DB — lifecycle, ACL, owner, refs; reconciliation связывает | **RESOLVED-CONCEPTUAL** |
| C08-11 | Logs vs events vs platform problems | Разные authority/evidence/projection layers | **RESOLVED-CONCEPTUAL** |
| C08-12 | Self-hosted auth или trust on local LAN | Loopback-only dev может быть особым профилем; network publication требует реального authn/authz | **SCOPE DIFFERENCE**, auth profile открыт |
| C08-13 | Установленное расширение автоматически активно | Installed/discovered/selected/bound/ready — разные стадии | **SUPERSEDED** |
| C08-14 | Data from same source «очевидно сопоставимы» | Требуется measure/perimeter/period/vintage/registry/evidence qualification | **SUPERSEDED** |
| C08-15 | Программное снятие общей блокировки при lease expiry | Lease expiry сам по себе не завершает старого worker; нужен fencing для own commits | **RESOLVED** |
| C08-16 | Обратная совместимость не нужна → schema migration тоже не нужна | API можно заменить; сохранённое state требует явной migrator/archive/reset policy | **FALSE INFERENCE / CLARIFIED** |
| C08-17 | Один global node cursor vs приватные event streams | Внутренний sequence полезен; наружный cursor не должен раскрывать чужие изменения | **NEW WHITE SPOT** |
| C08-18 | Высокое число tests в core ⇒ вся система хорошо покрыта | Тесты сосредоточены в SORS/forms/industries, другие сегменты существенно слабее | **REAL CURRENT GAP** |
| C08-19 | Web/Android следует копировать Qt runtime | Shared semantics переносится, Qt — desktop renderer/bridge | **SUPERSEDED** |
| C08-20 | Platform problem автоматически фиксирует каждую банковскую ошибку | Platform bridge принимает только reportable issues, domain result остаётся у domain owner | **BOUNDARY REFINEMENT** |

### 11.1. Устаревшие привычки, которые нужно исключить из целевого качества

- `str(exception)` в сериализуемом пользовательском состоянии;
- лог-файл как единственный источник состояния Job;
- «дважды нажал → две независимые мутации»;
- `except: pass` в destructive loops и публикации артефактов;
- `mtime` как единственный источник identity/source freshness;
- unbounded file buffering без resource profile;
- fallback к иному пространству хранения без явной policy;
- UI-level `busy` как межпользовательский lock;
- `unread: bool` как global shared truth;
- выключение фонового процесса как доказательство отмены running Job;
- автоматическая смена версий/definitions посреди Run;
- выдача raw logs или «всё зелёное» при неизвестном исходе;
- набор пустых новых репозиториев/пакетов только ради архитектурной картинки.

---
## 12. Риск-регистр и решения ближайшего цикла

**Критичность** здесь — аналитическая оценка влияния на архитектурный risk, а не доказательство эксплуатации уязвимости. `P0` означает блокировать переход к shared/managed production profile до устранения; `P1` — закрыть в первом качественном vertical slice; `P2` — оптимизировать после измерений.

| Риск | Вероятность/ущерб в предполагаемом масштабе | Severity | Доказательная основа | Владелец / минимальный шаг |
|---|---|---|---|---|
| R08-01. Windows и core имеют несовпадающие dependency versions | очень высокий шанс несовместимой сборки; фактический runtime результат неизвестен | **P0** | CURRENT pyproject/manifest | packaging owners: coherent release tuple; install smoke |
| R08-02. Windows manifest tests и текущий manifest расходятся | deterministic test regression | **P0** | CURRENT checked-in code | surface owner: contract tests/docs sync |
| R08-03. `listdir()` смешивает missing и empty | ложные upstream решения о существовании/полноте | **P0/P1** | CURRENT core code | FileStore contract owner: typed error semantics + negative tests |
| R08-04. `LocalFileStore(root)` ошибочно принять за sandbox | path escape при будущей remote/AI exposure | **P0 для Web/AI path API** | CURRENT code + trust-boundary inference | application/file API: secure root resolution/ACL |
| R08-05. Приватная локальная JSON history подменяет shared truth | гонки, потеря истории, пустые записи после corruption | **P0 для multi-user** | baseline Windows | application state owner: transactional pilot |
| R08-06. Background UI активирует state без реального engine | ложные ожидания пользователя | **P1** | baseline Windows | surface/application: preview label или реальная engine integration |
| R08-07. Нет cooperative cancellation | пользователь не контролирует долгий Job, риск опасного force kill | **P1** | baseline Windows | execution owner: token, safe points, terminal race tests |
| R08-08. Whole-object IO и нерегулируемый memory budget | OOM при больших артефактах/источниках | **P1** | core FileStore и artifact research | core/storage: streaming, staging, budgets |
| R08-09. Не зафиксированы effect receipts и reconcile | дубль внешних действий после timeout | **P0 для destructive/remote** | execution synthesis | execution + provider contracts |
| R08-10. Операции не имеют unified resource claims | конфликт output/cache на shared node | **P0 для multi-writer** | execution/multiuser | application JobManager + lock/fencing |
| R08-11. Нет единого version/freshness lifecycle для registries | скрытая смена смысловой основы отчёта | **P1** | current core snapshots | `stratbox` registries/sources |
| R08-12. Публичный generic extension loader может fail-open в неверном профиле | незаметно другой provider/destination | **P0 для managed data-sensitive** | CURRENT neutral runtime behavior | runtime owner: explicit activation policy |
| R08-13. Technical logs/Problem bridge смешиваются с пользовательскими ошибками | leaks, удвоенные problems, непонятный recovery | **P1** | observability + AppDock target | application↔AppDock contract tests |
| R08-14. Отсутствует единый security ACL/cursor semantics | multi-user data exposure при Web/remote | **P0 для Web** | multi-user/Web/05 synthesis | product authz + API surface |
| R08-15. Нет consistency-tested backup/restore | irreversible loss Work↔Artifact linkage | **P0 для durable host** | 05 synthesis | application backup set + AppDock lifecycle integration |
| R08-16. Тестовое покрытие неравномерно | скрытые fallback/destructive regressions | **P1** | core/windows research | repo CI, fault injection |
| R08-17. UI/accessibility/performance не имеют формального acceptance profile | ошибочные действия, недоступность, медленные списки | **P2, P1 для критических действий** | interface/motion research | shared presentation + platform UX owners |
| R08-18. Не определены resource budgets/SLI для разных узлов | starvation, scheduler misfires, заморозка UI | **P1 для headless** | resource white spot | runtime/operations owner: hardware baselines |

**Уточнение относительно приватных расширений:** конкретные реализации и их дефекты в этом публично-переносимом файле сознательно **не описываются**. Все записи касаются neutral contracts и текущего открытого core/surface. Private conformance audits проводятся отдельно в разрешённой среде и не копируются в public docs.

---

## 13. Fault-injection и acceptance: программа испытаний

### 13.1. Пирамида испытаний

**Unit/property:** чистые state machines, URL/path/format guards, scalar time/period logic, semantic validation, resource compatibility, idempotency key equality, provenance invariants.  
**Contract:** каждый FileStore/Provider/ExecutionBackend/ArtifactStore/DB adapter выполняет единый battery tests, включая отрицательные случаи.  
**Integration:** one node, transactional persistence, outbox, worker, storage, AppDock adapter, permissions, two-client projections.  
**E2E:** инсталляция из готового build, запуск сценария, результаты/логи/уведомления, crash/restart/reconnect и изменение прав.  
**Fault injection:** отключение сети, corrupt files, SIGKILL/forced worker stop, crash around commit/ACK, WAL pressure, storage full, invalid manifests.  
**Performance:** официальные representative snapshots (изолированные от внешних недетерминированных изменений), large file fixtures, solver/matrix benchmarks, low-end hardware and mobile projections.  
**Security/accessibility:** path traversal, principal impersonation, ACL leakage, prompt injection, hazardous confirmation, keyboard/screen-reader/reduced-motion tests.

### 13.2. Обязательные failure scenarios

| Test ID | Инъекция | Ожидаемое доказанное свойство |
|---|---|---|
| F01 | `listdir` на пустом существующем каталоге | `[]` как корректный successful empty |
| F02 | `listdir` на отсутствующем каталоге | `NotFound`, не `[]` |
| F03 | `listdir` на файле вместо каталога | `WrongType`, не `[]` |
| F04 | network/permission failure при получении источника | distinct typed failure; без «данных нет» |
| F05 | HTML/страница ошибки вместо XLSX | source validation rejects payload |
| F06 | повреждённый ZIP, `../` entry, большой expansion ratio | controlled rejection; no path escape; bounded resource use |
| F07 | путь `../`, absolute path, symlink/junction escape | authorized workspace confinement; platform-specific matrix |
| F08 | падение на N-м файле copy-tree | source untouched; partial target quarantined; no success |
| F09 | отказ `remove` посреди recursive cleanup | per-object residuals; no false complete |
| F10 | exception во время формирования XLSX в write stream | `abort`/staged cleanup, incomplete artifact not visible |
| F11 | disk full после bytes publish, до DB catalog commit | reconciler identifies orphan intent/bytes |
| F12 | DB commit есть, artifact bytes повреждены | digest failure and explicit damaged status |
| F13 | два Submit с одним key/digest | один Run/Job в соответствующем scope |
| F14 | тот же key, другой request digest | conflict, не reuse результата |
| F15 | ACK потерян после успешной remote публикации | `UNKNOWN`, compare receipt, no blind retry |
| F16 | два worker с разными fencing generation | старый не публикует state/result |
| F17 | два пользователя одновременно удаляют/переименовывают один target | serializable/revision conflict semantics |
| F18 | crash между Run→Job и outbox append | transactional consistency and recoverable event |
| F19 | corrupt persisted JSON/state DB | diagnostic-only degraded mode, no empty reset |
| F20 | upgrade with unknown schema version | refusal/migration gate; old state preserved |
| F21 | recovery restore without blob set | integrity failure with missing refs, not green |
| F22 | user revokes grant while automation queued | denied at execution/effect boundary |
| F23 | AI proposes unauthorized destructive plan | reject or await approval; no direct execution |
| F24 | event stream contains records of another user | server filters before transport; safe cursor semantics |
| F25 | client closes while Job runs | Job continues on authority; reconnect same IDs |
| F26 | cancel races with terminal success | one terminal record; cancel does not overwrite success |
| F27 | scheduler restarts at due occurrence boundary | no duplicate occurrence/effect under same key |
| F28 | repeated DST hour / missing local hour | deterministic occurrence policy & test fixtures |
| F29 | required audit sink unavailable | destructive command denied before effect |
| F30 | optional debug log sink unavailable | health degradation; read-only Job can finish honestly |
| F31 | large source file with whole-object codec fallback | budget gate / spill-to-disk; controlled failure instead of OOM |
| F32 | source snapshot changes under same filename | new version detected; historic Result pinned |
| F33 | screen-reader/reduced-motion on running/error/cancelled | full semantic explanation without animation/color |
| F34 | mixed distribution versions in AppDock managed env | activation release tuple rejection, clear diagnostics |
| F35 | Report contains analytically incomparable IFRS/RAS perimeter | Domain qualification prevents unqualified conclusion |
| F36 | telemetry recorder reports `OUTCOME_UNKNOWN` | no invented confirmed ProblemRef, safe recovery path |

### 13.3. Результат теста тоже требует provenance

Каждый gate report хранит:

```text
assertion_id → test_case_ids → implementation revision → environment profile
→ fixture/source digest → runner dependency versions → result → evidence/log ref
```

**[CURRENT LIMITATION]** В этой работе не запускались перечисленные tests. Они — **проектная acceptance matrix**. На core baseline отмечено 132 test functions с сильным перекосом в математический SORS/forms/industries; на Windows baseline — около 10 test files, с документированным противоречием manifest-теста. Количество тестов не доказывает их прохождение или достаточность negative-case coverage.

### 13.4. Первый вертикальный certification slice

Для начала реальной проверки всей архитектуры вместо «пишем весь framework» использовать **три типа операций**:

1. **Read-only source check:** получить `SourceSnapshot` или честную ошибку, с identity/version/progress и recovery после сетевого отказа.
2. **Reproducible XLSX export:** закреплённые dataset/registry revisions, bounded staging, artifact publication/digest, cancel/failure recovery, Work/Run/Job causal chain.
3. **Approval-gated cleanup:** scan→plan→approve→revalidate→apply, resource lock/fencing, inject failure in N-th delete/copy, receipts и неизменность source при сбое.

К каждому slice добавить два одновременно подключённых клиента (при shared-node режиме), перезапуск worker и Web/API command spoof tests. Это рано обнаружит дефекты ownership и несовместимые projection contracts, которые изолированный desktop smoke не увидит.

---

## 14. Decision / Gap Register темы 08

| ID | Вопрос | Вывод/направление | Статус |
|---|---|---|---|
| G08-01 | Единый terminal outcome | Один committed outcome per Job; effect/domain/Work отдельно | **CONSOLIDATED** |
| G08-02 | Какая physical persistence | SQLite embedded vs PostgreSQL server / equivalent | **TARGET-PROFILES; thresholds UNKNOWN** |
| G08-03 | Где выполняется headless JobManager | Logical application owner определён; отдельный package/repo/service — открыто | **TARGET / UNKNOWN physical** |
| G08-04 | Какая схема problem bridge в AppDock | Typed safe adapter, confirmed ref vs write uncertainty | **TARGET; connector contract UNKNOWN** |
| G08-05 | Как менять `OUTCOME_UNKNOWN` после reconciliation | Append-only conclusion vs update terminal projection | **DESIGN CHOICE** |
| G08-06 | Ровно один terminal outcome vs повторное выяснение эффекта | Разделить irreversible observed record и new resolution evidence | **CONCEPTUALLY RESOLVED; schema UNKNOWN** |
| G08-07 | Ключ ресурса и granularity lock | Стабильная нормализованная identity, reader/writer/fencing | **TARGET; pilot needed** |
| G08-08 | Generic `LocalFileStore.root` security | Не трактовать как sandbox; secure workspace authority | **CURRENT GAP for remote exposure** |
| G08-09 | Гарантия публикации FileStore | Staging+verify+commit; actual atomicity by backend capability | **TARGET; backend conformance needed** |
| G08-10 | Модель backup | DB+manifests+bytes+mandatory source provenance consistency | **CONSOLIDATED; RPO/RTO UNKNOWN** |
| G08-11 | Audit retention и обязательность | Mandatory before dangerous effects; physical sink policy | **TARGET; enterprise rules UNKNOWN** |
| G08-12 | Общий `ProblemCode` registry | Namespace-by-owner, stable code/version, no one giant enum | **CONSOLIDATED; formal schema UNKNOWN** |
| G08-13 | User notification of shared errors | Shared Condition + audience/ACL, not raw traceback broadcast | **CONSOLIDATED; rules UNKNOWN** |
| G08-14 | ACL-filtered global event cursor | opaque/audience-safe cursors и корректный ACL change replay | **OPEN SECURITY DESIGN** |
| G08-15 | Trusted vs untrusted extensions | Trusted managed in-process only; sandbox requires separate process policy | **CONSOLIDATED; untrusted support UNKNOWN** |
| G08-16 | Central task/resource quotas | profile-based resource budget and admission; no fixed numbers yet | **TARGET; benchmark needed** |
| G08-17 | Actual cancellation | cooperative safe points + effect-boundary semantics | **TARGET; CURRENT engine absent** |
| G08-18 | Web authentication | Authn/authz mandatory in network profile, method profile-specific | **CONSOLIDATED; exact protocol CHOICE** |
| G08-19 | Offline command queue | only explicit safe queueable effects with revalidation | **TARGET; offline scope UNKNOWN** |
| G08-20 | Managed artifact CAS | logical immutable publication needed, physical CAS optional | **TARGET CHOICE** |
| G08-21 | Zero data loss for old state vs no backward compatibility | explicit migrations/archive/controlled reset | **CONSOLIDATED principle** |
| G08-22 | Hardware/SLO class | define local low-end / managed workstation / shared host profiles | **UNKNOWN measured values** |
| G08-23 | Accessibility verification | keyboard, focus, screen reader, contrast, reduced motion, no color-only state | **CONSOLIDATED target; implementation status UNKNOWN** |
| G08-24 | Contract drift | current Windows/core versions and test↔manifest mismatch require P0 fix | **CURRENT verified** |
| G08-25 | Domains with weak tests | FRG, escrow, collector, base, Windows execution/storage | **CURRENT baseline; close P1** |
| G08-26 | Release/restore attestation | installed wheel/manifest/versions/source revisions; real restore drill | **TARGET; supply-chain profile UNKNOWN** |

### 14.1. Нужные отдельные Product Decisions

1. **Deployment assurance profiles:** что гарантируется локальному analyst, shared node и Web-host, в том числе RPO/RTO, quota, service lifecycle.
2. **Risk grading for effects:** какие операции требуют обязательной approval/двухфакторного подтверждения/операторской роли; какой аудит является блокирующим.
3. **Persistence/recovery contract:** минимальная authoritative schema, миграция, backup set, recovery readiness gates.
4. **Execution command API v1:** stable IDs, command idempotency scope/digest, terminal/effect semantics, cancel/unknown policy.
5. **Log/privacy & support policy:** retention, redact, audience, export consent, obligatory crash evidence.
6. **Cross-owner AppDock problem integration:** какие проблемы считаются платформенными, какой transport/contract и кто регистрирует occurrence.
7. **Extension trust policy:** managed trusted only vs изолированные untrusted; правила fallback и закрепления versions.
8. **Verification baseline:** реальные representative datasets, машина low-end класса, load profiles, владельцы CI gates и требование green release.

Эти решения нельзя заменить красивым названием директории `stratbox-host` или новым классовым diagram.

---

## 15. Целевая последовательность инженерных работ без обратной совместимости

### Gate A. Немедленная корректность открытых owners

- синхронизировать core/surface/package requirements и проверять installed build graph;
- устранить рассогласование Connector Manifest / tests / docs;
- очистить generated tracked state и закрыть release-integrity gaps;
- исправить семантику `LocalFileStore.listdir`, добавить negative tests для NotFound/WrongType/Permission;
- убрать неявную трактовку provider fallback как безопасной настройки всех deployment profiles;
- зафиксировать neutral public boundary и запрет внешних implementation-specific imports;
- включить build/test/import/contract matrix в CI.

**Acceptance:** coherent install of ready artifacts; negative FileStore tests; clean git packaging; no false-green smoke tests.

### Gate B. Выполнение с доказуемым состоянием

- объединить execution semantics, разделить Work/Run/Job/OperationRun/Attempt;
- immutable plan/binding/request snapshot;
- single terminal write + effect classification;
- first transactional repository + event/outbox;
- idempotent command admission;
- cooperative cancel and timeout/reconciliation states.

**Acceptance:** duplicate submit, crash at commit, late cancel and partial export fault tests pass.

### Gate C. Managed file/artifact safety

- secure WorkspaceRef path resolution;
- staging + verify + commit/abort in file publication;
- destructive plan/apply with guards and approval;
- artifact manifest digest, version, Work/Run provenance;
- reconcile orphan bytes and damaged catalog references;
- initial resource claims/locks/fencing.

**Acceptance:** failed copy-tree never deletes good source; no partial XLSX marked published; zombie worker cannot override new version.

### Gate D. Observability, support, readiness

- typed diagnostic/result/progress contracts;
- bounded physical logs with redaction and evidence refs;
- AppDock-safe problem bridge after explicit owner contract;
- user-safe SharedCondition notifications;
- diagnostic vs repair distinction;
- self-health, emergency logger and tested support bundle.

**Acceptance:** UI displays causal status, technical evidence remains restricted, recorder failure is reported correctly, read-only jobs survive optional logging loss.

### Gate E. Shared node / remote / automation

- authority outside UI; multiple clients read same consistent projections;
- product authorization + revision/ACL-filtered event stream;
- durable AutomationSpec/occurrence/DST/misfire;
- remote worker custody/lease/fencing + external effect reconciliation;
- backup/restore and schema migration drills;
- separate host lifecycle integration through AppDock.

**Acceptance:** session reconnect without duplicate Run; two-user ACL/isolation; scheduler restart without double occurrence; verified restore with artifact bytes.

### Gate F. Performance, accessibility и release certification

- измеряемые SLI/budgets на целевых машинах;
- streaming and memory-bound format operations;
- perf gates on representative SORS/financial-source fixtures;
- UI virtualization, bounded logs/previews, reduced-motion and keyboard/a11y certification;
- security threat model and ASVS-aligned Web requirements;
- release tuple attestation, install/update/rollback/restore E2E.

**Acceptance:** стабильное поведение на согласованном hardware profile, сохранение доступности под нагрузкой, безопасная деградация и формально подтверждённая portability semantics.

**Приоритет:** A закрывает подтверждённые текущие проблемы. B и C делают систему корректной. D делает её объяснимой. E и F позволяют масштабировать продукт и пользователей. Порядок допускает параллельную разработку, но зависимости при приёмке сохраняются.

---

## 16. Provenance: карта существенных выводов к источникам

Ссылки в этой секции указывают на **источники Strategy Box**, а не на произвольную методологическую аналогию. В следующем списке `[P]` обозначает программу/рамку, `[C]` — консолидации, `[R]` — тематические исследования, `[I]` — implementation/source, `[A]` — AppDock boundary, `[E]` — внешний стандарт. Части документа, обозначенные TARGET-HYPOTHESIS, **не превращаются в CURRENT** из-за наличия ссылки.

### 16.1. Исходная программа и консолидированный корпус

- **[P00]** [Программа третьей ветки: тема 08 и требования к system-wide invariants](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/strategy_box_03_consolidation_research_program.md).
- **[C00]** [Corpus Map & Open Questions](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_00_corpus_map_open_questions_2026-10-08.md): inventory 27 исследований, conflicts, superseded, initial invariants, implementation gaps.
- **[C01]** [System Model](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_01_System_Model_consolidated_research_2026-10-08.md): semantic owners и AppDock boundary.
- **[C02]** [Canonical Semantic Model](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_02_canonical_semantic_model_2026-10-08.md): Identity/Capability/Work/Run/Job/Attempt, отличия analytical result и artifact, различные UNKNOWN.
- **[C03]** [Data → Knowledge Architecture](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_03_data_to_knowledge_consolidated_research_2026-10-08.md): source/registry/claim/provenance, artifact publication, data uncertainty.
- **[C04]** [Work → Execution Architecture](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_04_work_to_execution_consolidated_research_2026-10-09.md): execution spine, EffectReceipt, idempotency, leases, cancel, unknown, crash recovery.
- **[C05]** [State, Persistence & Collaboration](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_05_state_persistence_collaboration_consolidated_research_2026-10-09.md): transactional authority, migrations, event outbox, ACL cursor, backup/restore.
- **[C06]** [Capability, Extension & Automation](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_06_capability_extension_automation_consolidated_research_2026-10-09.md): activation, trusted code, resource profiles, schedule/permission, extension contract.

### 16.2. Базовый implementation research и тематические проработки

- **[R01]** [Current-state core](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_base_study_current_state_2026-10-06.md): версии/контракты, доменная зрелость, IO, 132 test functions, registries, SORS.
- **[R02]** [Current-state Windows](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md): Qt runner, cases, history, AppDock manifest, cancel/background gaps.
- **[R03]** [Observability, errors, logs](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_observability_errors_logs_research_2026-10-07.md): typed outcomes, PhysicalLog, Problem, shared conditions, support bundle, fault injection.
- **[R04]** [Execution control/user path](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_execution_control_user_path_research_2026-10-07.md): permissions, cancellation, resource claims, safe points, parameter snapshots.
- **[R05]** [Background jobs/processes](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md): scheduler ownership, misfires, one execution spine, acceptance criteria.
- **[R06]** [Single-node multi-user](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md): node authority, read cursors, resource leases, ACL concerns.
- **[R07]** [Web/self-hosted](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md): browser boundary, HTTP security, worker separation, DB, access control.
- **[R08]** [File/artifact layer](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md): FileStore vs Artifact, staging, immutable manifests, failure/recovery, storage tests.
- **[R09]** [FileStore/file formats](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md): safe codecs, archive/XML security, stream capabilities, unsupported/corrupt taxonomy.
- **[R10]** [Registries/source governance](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_registry_source_governance_research_2026-10-07.md): snapshot/version/freshness, hash, conflicts and registry audit.
- **[R11]** [Settings/user preferences](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_system_settings_research_2026-10-07.md): UI state vs managed policy; plugin settings; diagnostics separation.
- **[R12]** [Artifact styles/customization](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md): trusted declarative style profiles and separation from frontend code.
- **[R13]** [Interface requirements](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_windows_interface_requirements_research_2026-10-07.md): keyboard/focus/contrast, log virtualization, responsiveness.
- **[R14]** [Motion](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_windows_motion_animation_research_2026-10-07.md): semantic motion, reduced motion, no fake progress.
- **[R15]** [Visual system](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_interface_visual_system_research_2026-10-07.md): status color/accessibility, contrast, adaptive behaviour.
- **[R16]** [Business-code portability](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_segments_portability_reuse_architecture_research_2026-10-07.md): neutral execution context, reusable operations, effect boundaries.
- **[R17]** [Machine schemes/contracts](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_logic_machine_schemes_architecture_research_2026-10-07.md): typed pre/postconditions, capability envelope, fail/cancel/idempotency contracts.
- **[R18]** [Generic extension conformance](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_corporate_plugin_contract_research_2026-10-07.md): публичный нейтральный контракт provider/errors/security/health и негативных испытаний; без ссылок на устройство любых конкретных закрытых реализаций.

Остальные тематические материалы полного корпуса учтены на уровне [C00] и тематически сведены в [C01–C06]. В этом документе они используются только для уточнения доказательности, действий AI и прав пользователя; **никакие сведения об устройстве внешних методологических репозиториев здесь не приводятся**.

### 16.3. Выборочно проверенный CURRENT source

- **[I01]** [`stratbox/pyproject.toml`](https://github.com/ForestTiger-GH/stratbox/blob/main/pyproject.toml) — версия core и packaging requirements.
- **[I02]** [`stratbox/base/filestore/base.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/filestore/base.py) — нейтральный transport Protocol и whole-object default copy.
- **[I03]** [`stratbox/base/filestore/local.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/filestore/local.py) — missing/empty semantics и root path behavior.
- **[I04]** [`stratbox/base/runtime.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/runtime.py) — общее discovery/fallback behavior в публичном core (без сведений о конкретных реализациях).
- **[I05]** [`stratbox-windows/pyproject.toml`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/pyproject.toml) — pinned core dependency.
- **[I06]** [`stratbox-windows/appdock/manifest.json`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/appdock/manifest.json) — current Connector Manifest и runtime graph.
- **[I07]** [`stratbox-windows/tests/smoke/test_repository_contract.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/tests/smoke/test_repository_contract.py) — устаревшее ожидание `3.0`/package identity.
- **[I08]** [`stratbox-windows/__main__.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/__main__.py) — запуск/diagnostics/preflight/controlled startup errors.

Сверка версий: GitHub comparison `stratbox@e968853…→main` и `stratbox-windows@959e9c4…→main`, выполненная `2026-10-09` через подключённый репозиторий. Вывод по code freshness ограничен изменениями, показанными comparison; он не удостоверяет фактический installed environment каждого узла.

### 16.4. AppDock и внешние стандарты

- **[A01]** `AppDock — Базовое описание.docx` (приложенный документ): product/node/installation/state/recovery/remote граница; внутренний проектный файл, не публичная веб-ссылка.
- **[A02]** [AppDock observability target model](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/observability/TARGET_MODEL.md): различия Event/Problem/Condition/Incident, Recorder, Result/ProblemRef и privacy. *Внешний implementation owner; ссылка может требовать отдельного доступа.*
- **[A03]** [AppDock observability implementation status](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/observability/IMPLEMENTATION_STATUS.md): реализованные/certified отдельные milestones; не универсальное свидетельство интеграции Strategy Box. *Внешний implementation owner; может требовать отдельного доступа.*
- **[E01]** [OWASP ASVS 5.0](https://owasp.org/projects/asvs/): независимая проверяемая методика web/application security; не сертификат продукта.
- **[E02]** [SQLite Online Backup API](https://sqlite.org/backup.html): официальная документация про согласованный backup работающей БД.
- **[E03]** [W3C Trace Context](https://www.w3.org/TR/trace-context/): межсервисный distributed trace; не подменяет Work/Run/Problem identity.

### 16.5. Claim → provenance matrix

| Существенное утверждение | Primary evidence | Характер вывода |
|---|---|---|
| Версионный drift core↔Windows и manifest↔test | [I01], [I05], [I06], [I07] | CURRENT, прямой source probe |
| `listdir()` не различает missing и empty | [I02], [I03] | CURRENT, прямой source probe |
| `LocalFileStore.root` не является sandbox | [I03], [R07] | CURRENT fact + security inference |
| Статусы/Job/Attempt/cancel и UNKNOWN должны быть типизированы | [C02], [C04], [R03], [R04] | CONSOLIDATED target; не current API |
| Работа должна жить вне Qt-процесса | [R02], [R05], [R06], [C01], [C05] | CONSOLIDATED; physical host choice OPEN |
| Один scheduler в Strategy Box, AppDock lifecycle отдельно | [R05], [C01], [C04], [A01] | CONSOLIDATED ownership |
| Managed Artifact отличается от файла/пути | [R08], [C03], [C05] | CONSOLIDATED; CAS implementation OPEN |
| Registry/source vintage влияет на воспроизводимость | [R01], [R10], [C03] | CURRENT gap + target contract |
| Resource locking + fencing необходимо при multi-writer | [R04], [R06], [C04], [C05] | TARGET-HYPOTHESIS, safety rationale |
| SQLite/PostgreSQL — физические profiles одного contract | [R07], [C05] | RESOLVED scope difference |
| AppDock ProblemRef/Recorder и Strategy Box issue distinct | [A02], [A03], [R03], [C01] | External target + bounded implementation evidence |
| Web/AI authorization и trust boundary | [R07], [C06], [E01] | TARGET-HYPOTHESIS/security requirement |
| Streaming/format bomb/XML/macros safety | [I02], [R08], [R09] | CURRENT capabilities + target safeguards |
| Accessibility/reduced motion | [R13], [R14], [R15] | TARGET-HYPOTHESIS; product a11y certification UNKNOWN |
| 50 инвариантов и failure matrix | [P00], [C00], [C02–C06], [R01–R18], выборочный code probe | авторская системная консолидация темы 08 |

---

## 17. Итоговая формула готовности Strategy Box

**[CONSOLIDATED]** У Strategy Box уже есть хорошая техническая и смысловая основа: самостоятельный банковско-макроэкономический core, типизированные результаты отдельных доменов, развитый доказательный контур специализированных вычислений, работающие desktop-сценарии с case/event/artifact/log связями и явная платформа узла. **Это ещё не равнозначно надёжной многоузловой, многопользовательской, автоматически восстанавливаемой системе.**

Системная готовность определяется не числом галочек `supports_*` в metadata и не красотой интерфейса. Проверяется возможность ответить на десять вопросов после **любого существенного сбоя**:

1. **Что хотели сделать?** — Work/intent и подтверждённый plan.
2. **Кто имел право?** — Principal, delegation, policy/approval revision.
3. **Что действительно было запущено?** — Run/Job/OperationRun/Attempt с versions/bindings.
4. **Какие данные и справочники использовались?** — Source/Registry snapshots, hashes, timestamps.
5. **Что реально успело измениться?** — effect intents/receipts и верифицируемое состояние.
6. **Какой исход доказан?** — typed terminal outcome с отдельным `UNKNOWN`, если требуется.
7. **Где доказательства?** — durable events, provenance, manifest, permitted logs/evidence refs.
8. **Кто затронут?** — audience/ACL, safe Condition, уведомления и независимое прочтение.
9. **Как безопасно продолжить?** — retry/resume/reconcile/repair с idempotency и новыми Attempt IDs.
10. **Можно ли повторить и проверить результат?** — stable definitions/versions, published artifacts и acceptance requirements.

Если ответы не восстановимы из независимой от UI authority, сценарий пока нельзя считать production-ready лишь потому, что он однажды успешно создал Excel-файл.

**Research conclusion:** следующая фаза должна превратить эти инварианты из кандидатных исследовательских правил в небольшой, версионированный, проверяемый набор Product/Engineering acceptance contracts. Приоритет — устранить CURRENT version/error gaps, затем доказать на трёх вертикальных сценариях безопасность состояния, эффектов, восстановления и полномочий. Именно на таком фундаменте Windows/Web/Android и будущие интеллектуальные потребители смогут разделять одну систему, не размножая несовместимые правила качества.

---

**End of Research Synthesis — Topic 08.**
