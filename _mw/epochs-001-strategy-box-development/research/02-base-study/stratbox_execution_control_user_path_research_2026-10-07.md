# Strategy Box — пользовательский путь, параметры, управление выполнением, отмена, совместная работа и AI-доступ к операциям

**Дата исследования:** 2026-10-07  
**Ветка исследований:** вторая ветка Strategy Box  
**Контур:** `stratbox` + `stratbox-windows` + граница AppDock  
**Статус:** исследовательский материал; код и репозитории не изменялись

---

## 0. Краткий вывод

В текущем Strategy Box уже есть большая часть правильных кирпичиков: атомарные operations, пользовательские scenarios, composite-сценарий с mapping параметров, кейсы запусков, события, автор запуска, логи, артефакты, локальная история, schema-driven формы параметров, сохранение пользовательских значений сценариев, actor kinds `user / host_user / ai / system / background` и задел под background/presence. При этом исполнительный слой пока остаётся ранним: один активный сценарий, один `QThread`, отсутствует реальная отмена, presence локален, фоновые процессы не исполняются, а authoritative state запуска живёт внутри desktop-процесса.

Главный архитектурный вывод этого исследования: дальнейшее развитие стоит строить вокруг **единого execution-control spine**, а не вокруг отдельных UI-функций. Сценарий, каскад, фоновая задача, запуск другим пользователем и AI-вызов должны приходить в один и тот же `ExecutionService / JobManager`. Он создаёт case, разрешает эффективные параметры, ставит работу в очередь, владеет cancellation token, публикует события и терминальный результат. Windows UI, будущий Android, AppDock remote surface и AI становятся разными клиентами одной и той же модели.

Пользовательской единицей следует оставить **scenario**, а не operation. Operation — атомарная машинно-исполняемая возможность. Atomic operation автоматически может иметь scenario-обёртку, но composite/cascade должен иметь собственную короткую форму параметров и сам раскладывать их по шагам. Пользователю нельзя показывать объединённый «мешок» из десятков параметров внутренних операций.

Параметры стоит развить из текущего `default + remembered value` в полноценную систему профилей. Нужны: рекомендованный default, пользовательский auto-profile, именованные presets, в будущем shared node presets, launch-time overrides и жёсткие policy/fixed values. Каждое поле должно знать, можно ли его запоминать, является ли оно чувствительным, какова его область действия, где оно показывается и можно ли переопределять его внутри каскада. При каждом запуске case обязан сохранять **снимок фактически разрешённых параметров**, независимо от того, как позже изменится пользовательский профиль.

Отмена должна быть **кооперативной**. `QThread.terminate()` и похожие способы нельзя считать штатной остановкой. Запрос отмены проходит через `case → scenario runner → step → operation runner → stratbox operation`, проверяется на безопасных точках и приводит к терминальному `cancelled`. Для операций, которые пока не умеют останавливаться внутри, допустим режим `after_step`: UI сразу показывает «Отмена запрошена», а текущий атомарный шаг заканчивается и следующие уже не стартуют. Принудительное завершение процесса — отдельная аварийная команда, результат которой лучше считать `outcome_unknown`, а не «успешно отменено».

Многопользовательское управление требует смены authoritative owner. Когда один пользователь запускает задачу, а второй видит её и может отменить, case уже не может быть просто локальным JSON объекта первого клиента. Источник истины должен жить на **узле исполнения**. Клиенты получают общую проекцию job/case и отправляют управляющие команды на узел. AppDock естественно владеет node/session identity, remote transport, permissions и жизненным циклом, а Strategy Box — семантикой scenario/operation/case.

Для AI особенно важно не открывать произвольные Python-функции или shell. Ему следует открыть **каталог канонических operations** с typed input/output schema, side-effect metadata, cancellation capability, permission и approval policy. AI запускает operation тем же путём, что пользователь; получает `case_id`, события, диагностику и артефакты. Для сложного поручения AI может собрать временный ad-hoc cascade из разрешённых operations, но такой план остаётся явным, журналируемым и при необходимости требует подтверждения.

---

# I. Что уже есть в текущем Strategy Box

## 1. Сценарий уже является правильной пользовательской единицей

В `stratbox-windows` атомарная operation автоматически превращается в atomic scenario вида:

```text
scenario.atomic.<operation_id>
```

Composite scenario хранит собственный набор параметров и `params_map`, который переводит пользовательские поля сценария в параметры конкретных внутренних operations. Это принципиально правильная граница:

```text
operation = атомарная исполнимая возможность
scenario  = пользовательский use case
case      = конкретный запуск scenario
step      = конкретный шаг scenario внутри case
```

Сейчас один composite — «Обновление данных Банка России» — уже показывает правильную модель: пользователь видит несколько параметров верхнего уровня, а runner раскладывает их по двум операциям.

Это следует сохранить и усилить. Масштабирование каталога должно идти через богатые scenarios, а не через превращение интерфейса в форму каждой низкоуровневой функции.

## 2. Формы параметров уже schema-driven

Текущий `OperationParamSpec`, используемый и сценариями, поддерживает:

```text
text
int
bool
select
path_dir
path_file
```

и metadata:

```text
default
required
options
section = basic | advanced
placeholder
min_value
max_value
description
```

Qt-панель строится из этих specs. Это один из лучших текущих seams для будущего Android: смысл формы уже можно отделить от конкретных Qt widgets.

Сейчас почти все реальные параметры простые, а большая часть технических параметров операций спрятана в `fixed_param_values`. Это уже правильный UX-инстинкт: человек не должен выбирать retry/backoff/technical policy при каждом запуске.

## 3. Пользовательские параметры уже сохраняются на диск

Активная `ScenarioParametersPanel` при выборе scenario читает:

```text
PreferencesService.load_scenario_values(scenario.id)
```

а при сборе формы записывает:

```text
PreferencesService.save_scenario_values(scenario.id, params)
```

В `AppUserConfig` есть:

```text
scenario_form_values: dict[scenario_id, values]
last_scenario_id
```

Значения лежат в пользовательском app config. Более того, панель вызывает `collect_params()` при изменении полей, то есть в текущей реализации значения фактически могут сохраняться очень часто, вплоть до изменений формы.

Это подтверждает, что нужный пользователю принцип уже частично реализован: «настроил один раз — при следующем открытии вижу своё».

Ограничение: сейчас это просто словарь значений без версии schema, provenance, distinction между recommended default / user override / run snapshot и без поля persistence policy.

## 4. Кейсы уже готовы к чату и авторству

`ScenarioRunCase` хранит:

```text
case_id
scenario_id
scenario_title
params
status
author_id
author_label
started_at / finished_at
current_stage
steps
outputs
message
```

Current `CaseStatus` уже содержит `cancelled`, хотя реального пути в этот статус пока нет.

События уже различают actor kinds:

```text
user
host_user
ai
system
background
```

Это очень полезный задел: будущий общий чат узла не требует менять базовую семантику автора, достаточно сделать события и cases реально общими между клиентами.

## 5. Реальная отмена отсутствует

Текущий `ScenarioCoordinator`:

- допускает один активный scenario;
- создаёт `QThread` и `ScenarioWorker`;
- не имеет `cancel()`;
- не имеет cancellation token;
- `ScenarioWorker` просто вызывает `run_scenario()` до завершения;
- step statuses не содержат `cancelled` или `cancel_requested`.

То есть `CaseStatus.cancelled` сейчас является semantic placeholder, а не рабочим lifecycle.

## 6. Presence пока локален

`PresenceService`:

- создаёт текущего пользователя;
- добавляет авторов уже известных cases;
- считает текущего пользователя online;
- не имеет сетевого provider/polling/subscription;
- не получает общий список участников от узла.

Значит, UI уже способен **показать** многопользовательскую модель, но пока не существует общей authoritative collaboration plane.

## 7. AppDock уже содержит полезную модель отмены задач

В актуальном AppDock task runtime уже есть паттерн, который стоит использовать как архитектурный ориентир Strategy Box:

```text
TaskIdentity
TaskHandle
threading.Event cancel_event
TaskStarted
TaskProgress
TaskCompleted
TaskFailed
TaskCancelled
```

`TaskHandle.cancel()` устанавливает `cancel_event`. Worker получает этот event и сам должен на него реагировать. Reporter гарантирует ровно один terminal event.

Особенно важная деталь Shell: при закрытии во время activation он сначала просит отмену, ограниченно ждёт worker, затем пытается забрать уже зафиксированное terminal-событие. Если успех или ошибка уже были committed, они остаются истиной; поздний click «закрыть» не переписывает их в `cancelled`.

Это сильный принцип для Strategy Box:

> **terminal truth wins over late control requests**.

AppDock Observability также уже различает cancellation и failure: штатная отмена сама по себе не должна создавать искусственную проблему/ошибку.

---

# II. Целевая модель управления

## 8. Один execution-control spine для всех способов запуска

Предлагаемая базовая схема:

```text
Windows UI
Android UI
Background trigger
Другой пользователь
AI agent
     │
     ▼
ExecutionCommand
     │
     ▼
StrategyBoxExecutionService
     │
     ├── ParameterResolver
     ├── Permission / ActionAvailability
     ├── JobManager / Queue
     ├── CaseStore
     ├── EventStore
     └── ExecutionBackend
            │
            ├── LocalExecutionBackend
            └── RemoteNodeExecutionBackend (через AppDock)
                       │
                       ▼
                 ScenarioRunner
                       │
                       ▼
                 OperationRunner
                       │
                       ▼
                   stratbox
```

Ключевая идея: UI больше не владеет выполнением. UI отправляет команду и получает проекцию состояния.

Это решает сразу пять задач:

1. отмена перестаёт быть Qt-функцией;
2. background работает тем же engine;
3. другой пользователь может управлять тем же case;
4. Android не требуется переносить Qt orchestration;
5. AI использует тот же контролируемый канал.

## 9. Разделить business operations и control commands

Чтобы терминология не расползалась, полезно зафиксировать два разных класса сущностей.

### Business operation

Каноническая атомарная предметная возможность:

```text
cbr.files.collect
escrow.history.build
frg.scan
frg.cleanup.execute
sors.restore
...
```

Она отвечает на вопрос **«что можно выполнить»**.

### Control command

Команда системе исполнения:

```text
StartScenario
CancelCase
RetryCase
ResumeCase          # только для явно resumable сценариев
ForceTerminateJob   # аварийное действие
```

Она отвечает на вопрос **«что сделать с исполнением»**.

AI не должен путать эти два слоя. Он выбирает business operation/scenario, а запуск/отмена проходят через control plane.

---

# III. Как пользователь должен вызывать сценарий или каскад

## 10. Основной пользовательский путь

Целевой путь обычного ручного запуска:

```text
1. Пользователь находит scenario
   ↓
2. Видит короткое описание + основные параметры
   ↓
3. Получает уже заполненные разумные значения
   ↓
4. При необходимости раскрывает «Дополнительно»
   ↓
5. Нажимает «Запустить»
   ↓
6. ExecutionService создаёт case немедленно
   ↓
7. Case появляется в чате как queued/running
   ↓
8. Пользователь видит stage/progress/artifacts/logs
   ↓
9. Может запросить отмену
   ↓
10. Получает terminal result
```

На момент нажатия «Запустить» пользователь должен видеть прежде всего **смысл запуска**, а не внутреннее устройство pipeline.

## 11. Пути входа в запуск

Со временем один и тот же scenario должен запускаться из разных мест, без появления разных execution implementations:

| Путь | Что происходит |
|---|---|
| Каталог «Сценарии» | обычный ручной запуск |
| «Каскады» | запуск composite scenario |
| Поиск / command palette | быстрый выбор scenario |
| Recent / Favorites | повтор часто используемого scenario |
| Case → «Повторить» | новый запуск со снимком прежних параметров |
| Artifact → context action | scenario получает context override из выбранного артефакта |
| Background process | trigger создаёт обычный case |
| Assignment | действие пользователя может создать запуск |
| Remote user | команда приходит через узел |
| AI | tool invocation создаёт тот же case |

Это должны быть **разные entry points**, а не разные runners.

## 12. Composer должен быть «быстрым», инспектор — «полным»

Текущий нижний composer уже хорошо подходит как quick-launch surface. Его стоит развить так:

```text
┌───────────────────────────────────────────────────────┐
│ Обновление данных Банка России                       │
│ 5 шагов · Мои настройки                              │
│ Период: текущий · Каталог: …/output/cbr              │
│                                      [Настроить] [▶] │
└───────────────────────────────────────────────────────┘
```

В quick composer достаточно 2–4 наиболее важных параметров или их краткой сводки.

Полная форма остаётся в инспекторе:

```text
Основные
  Период
  Результат
  Каталог

Дополнительно
  Обновить кэш
  Политика частичных ошибок
  ...

[Сбросить] [Профиль: Мои настройки ▾]
```

Чем больше параметров появится у core, тем важнее эта двухуровневая модель.

---

# IV. Как не утонуть в параметрах

## 13. Параметры следует делить не на два, а на несколько смысловых классов

Текущих `basic / advanced` скоро будет мало. Полезна следующая модель видимости:

```text
hidden       — пользователь никогда не меняет
basic        — основные 2–6 параметров
advanced     — редкие, но понятные настройки
expert       — технические настройки для опытного пользователя
contextual   — пришли из выбранного артефакта/кейса/узла
```

При этом `visibility` и `persistence` — разные свойства. Например, advanced parameter может запоминаться, а contextual — обычно нет.

## 14. Расширенный ParameterSpec

Целевая нейтральная schema поля может содержать:

```python
ParameterSpec(
    name="period",
    value_type="period",
    title="Период",
    description="...",
    required=True,
    default=DynamicDefault("current_month"),
    visibility="basic",
    remember=True,
    persistence_scope="user",
    sensitive=False,
    overridable=True,
    validation=...,
    visible_if=...,
    options_provider=...,
)
```

Полезные новые свойства:

| Свойство | Зачем |
|---|---|
| `remember` | сохранять ли пользовательское значение |
| `persistence_scope` | `none / session / user / node` |
| `sensitive` | запретить plain-text persistence/logging |
| `dynamic_default` | текущий месяц, workspace path и т. п. |
| `visible_if` | условные поля |
| `enabled_if` | зависимость доступности |
| `options_provider` | динамические options |
| `semantic_type` | period, bank, artifact, region и т. п. |
| `overridable` | может ли cascade переопределять поле шага |
| `reset_policy` | что значит «сбросить» |
| `redaction_policy` | как поле попадает в case/log/AI context |

## 15. Типы полей, которых почти наверняка не хватит

Помимо текущих шести, разумно предусмотреть frontend-neutral semantic types:

```text
float / decimal
date
datetime
period
multi_select
range
artifact_ref
scenario_ref
bank_ref / entity_ref
secret_ref
list / tags
```

Не требуется сразу делать все widgets. Важно, чтобы data contract позволял расширение без переделки execution model.

## 16. Default — это не одно значение

Система должна различать минимум четыре вида «значения по умолчанию»:

```text
1. Built-in recommended default
2. Node/product default
3. User remembered value
4. Context-derived value
```

Пример:

```text
period
  built-in default     = текущий месяц
  user remembered      = отсутствует
  context-derived      = месяц выбранного файла
  launch edit          = 2026-07
```

Для конкретного запуска фактическим становится `2026-07`, но это не обязано менять permanent user profile, если значение пришло из artifact context.

## 17. Рекомендуемый порядок разрешения параметров

Предлагаемый precedence:

```text
Spec defaults
    ↓
Node / product defaults
    ↓
Selected profile (user или named preset)
    ↓
Context injection
    ↓
Launch-time edits
    ↓
Step params_map / step override
    ↓
Policy-enforced / fixed values
```

Последний слой всегда побеждает. Именно здесь остаётся нынешний смысл `fixed_param_values`.

## 18. Профили параметров

Вместо одного бесформенного `scenario_form_values` стоит ввести `ParameterProfile`.

Пример:

```json
{
  "contract_version": "1.0",
  "profile_id": "user-default:scenario.cbr.full_update",
  "scenario_id": "scenario.cbr.full_update",
  "scenario_schema_digest": "...",
  "owner_scope": "user",
  "owner_id": "user-123",
  "name": "Мои настройки",
  "values": {
    "target_dir": "D:/Strategy Box/output",
    "refresh_sources": false
  },
  "updated_at": "2026-10-07T16:00:00+03:00"
}
```

Нужны три уровня профилей:

### A. Auto-profile пользователя

«Мои настройки». Обновляется автоматически при изменении запоминаемых полей.

### B. Именованные presets пользователя

Например:

```text
Ежемесячное обновление
Полная пересборка
Только свежие источники
```

Они изменяются только явной командой «Сохранить профиль».

### C. Shared/node presets

Будущий уровень для команды. Например хост задаёт общий preset «Боевой контур». Его изменение требует отдельного разрешения.

Важно: изменения личного профиля пользователя A **не должны автоматически менять** настройки пользователя B.

## 19. Autosave параметров

Пользовательское ожидание «я уже настроил — покажи так же в следующий раз» разумно реализовать через autosave, но текущую запись на каждое изменение поля стоит сделать аккуратнее.

Целевая механика:

```text
field changed
    ↓
local model updated immediately
    ↓
validation
    ↓
debounce 300–800 ms
    ↓
atomic profile write
```

Плюсы:

- нет десятков disk writes при наборе текста;
- закрытие окна почти не теряет изменения;
- профиль всегда остаётся самостоятельным объектом;
- можно показывать индикатор «Сохранено» только при необходимости.

## 20. Профиль и снимок запуска — разные вещи

Case должен сохранять **effective parameter snapshot**, уже после разрешения defaults/profile/context/fixed policy.

```text
profile today:          refresh=false
run #1 snapshot:        refresh=false
user changes profile:   refresh=true
run #1 remains:         refresh=false
run #2 snapshot:        refresh=true
```

Это критично для воспроизводимости и audit trail.

Для чувствительных полей case хранит redacted representation или `secret_ref`, а не секрет.

## 21. Изменение schema сценария

Профиль должен быть связан со schema digest/version.

При изменении сценария:

```text
старые известные поля      → сохранить
новые поля                 → получить новые defaults
удалённые поля             → удалить из active profile
устаревший enum value      → показать warning и сбросить к допустимому default
изменившийся тип           → явная migration или сброс
```

Проекту обратная совместимость не требуется, поэтому лучше делать строгую migration текущего локального profile format, а не поддерживать бесконечно старые формы.

---

# V. Как настраивать каскады

## 22. Каскад не должен показывать union всех внутренних параметров

Главная ошибка, которой стоит избежать:

```text
operation A = 12 params
operation B = 9 params
operation C = 14 params
--------------------------------
cascade UI = 35 params
```

Это технически честно и продуктово плохо.

Каскад обязан иметь **собственную семантическую форму**:

```text
Период
Каталог результата
Полнота обновления
Обновить исходники?
```

А затем через mapping/overrides распределять это по шагам.

Текущий `ScenarioStepSpec.params_map` уже является правильной основой.

## 23. Step overrides — только по запросу пользователя

Для продвинутого режима можно добавить:

```text
[Настроить шаги]

1. Загрузка исходников ЦБ       Использует настройки каскада
2. Нормализация                 Использует настройки каскада
3. Экспорт                      [Переопределено: XLSX]
```

Но step override должен быть opt-in. Основной путь остаётся коротким.

## 24. Наследование параметров каскада

Удобная модель:

```text
cascade params
    ↓
params_map
    ↓
operation params
    ↓
step override
    ↓
fixed/policy values
```

UI при желании может показать «откуда взялось значение»:

```text
Каталог результата
D:/Strategy Box/output
Источник: Мои настройки
```

Это особенно полезно, когда появятся node-level presets и AI/context injection.

---

# VI. Отмена выполнения

## 25. Почему отмена должна быть cooperative

Текущий Strategy Box использует `QThread`. Qt прямо описывает `requestInterruption()` как advisory request: выполняющийся код должен сам проверять запрос и корректно завершаться. Python threads также нельзя штатно уничтожить/остановить/приостановить снаружи.

Следовательно, нормальная отмена не может быть реализована как:

```text
нажали кнопку
→ убили thread
→ поставили case.status = cancelled
```

Правильная схема:

```text
нажали «Отменить»
→ control command accepted
→ cancellation requested
→ worker/operation увидел token в safe point
→ cleanup / rollback if explicitly supported
→ terminal cancellation committed
→ case = cancelled
```

## 26. Новый state machine case

Предлагаемый lifecycle:

```text
prepared
   ↓
queued
   ↓
running ───────────────→ success
   │                    warning
   │                    failed
   │
   └→ cancel_requested
          ↓
      cancelling
          ↓
      cancelled
```

Отдельный terminal state нужен для аварийного завершения, при котором итог неизвестен:

```text
outcome_unknown
```

Такой state лучше, чем ложное `cancelled`, если процесс убит посреди записи/изменения данных.

## 27. Step state machine тоже нужно расширить

Сейчас step не умеет быть cancelled. Целевая модель:

```text
pending
queued
running
success
warning
failed
cancel_requested
cancelled
skipped
```

Для шагов, которые ещё не стартовали после запроса отмены, обычно достаточно `skipped` с причиной `scenario_cancelled`.

## 28. CancellationToken как нейтральный контракт

Не стоит пробрасывать `QThread` в core. Нужен platform-neutral интерфейс:

```python
class CancellationToken(Protocol):
    def is_cancel_requested(self) -> bool: ...
    def raise_if_cancelled(self) -> None: ...
```

Далее:

```text
JobManager
  owns CancellationSource
        ↓
ScenarioRunner
        ↓
OperationRunner
        ↓
OperationExecutionContext
        ↓
stratbox operation
```

Qt bridge только вызывает `source.cancel()`.

Remote backend вызывает ту же command на host.

## 29. Safe points

Операции должны проверять token там, где остановка не разрушает инварианты.

Примеры:

```text
до network request
после network request
между retry attempts
между файлами
между датами/периодами
между шагами transform
до создания final artifact
до destructive commit
после безопасного commit
```

Слишком частый polling не нужен. Важнее правильно выбрать границы.

## 30. Для каждой operation нужен cancel capability

В descriptor стоит добавить:

```text
cancel_mode =
  immediate_cooperative
  safe_points
  after_step
  unsupported
```

Это позволяет UI честно говорить пользователю, что произойдёт.

Пример:

```text
Скачивание 120 файлов
Отмена возможна между файлами

Большой Excel export
Остановка будет выполнена после завершения текущей записи
```

## 31. Отмена queued job

Это самый простой случай:

```text
queued
→ CancelCase
→ cancelled
```

Worker вообще не стартует.

## 32. Отмена composite scenario

Базовый UX должен предлагать **отмену всего case**.

После запроса:

```text
текущий step
  → останавливается в safe point
  → или заканчивается, если cancel_mode=after_step

следующие steps
  → не запускаются
  → skipped / scenario_cancelled
```

Отмена отдельного шага внутри каскада сложнее. Её стоит разрешать только если ScenarioSpec явно говорит, что step optional и его пропуск не ломает downstream semantics.

## 33. Stop не означает rollback

Это важно явно зафиксировать в продукте.

```text
Cancel = прекратить дальнейшее выполнение безопасным способом
Rollback = вернуть уже совершённые изменения
```

Rollback должен существовать только у операций, которые действительно имеют компенсационную семантику.

UI не должен обещать «всё отменено», если часть файлов уже успешно скачана или часть артефактов уже создана.

## 34. Артефакты при отмене

Рекомендуемая политика:

```text
temporary artifact
   ↓
complete write
   ↓
validate
   ↓
atomic publish / rename
```

Если cancellation приходит до publish, temp можно удалить.

Если артефакт уже published, он остаётся и case фиксирует, что был создан до отмены.

Для крупных результатов стоит добавить metadata:

```text
complete
partial
abandoned
```

## 35. Network cancellation

`requests`/обычный blocking HTTP нельзя «магически» оборвать через Python thread event. Поэтому нужна комбинация:

- коротких разумных connect/read timeouts;
- проверки token между retries;
- при streaming — проверки между chunks;
- закрытия response/session там, где это безопасно.

Для долгих атомарных вызовов, которые невозможно сделать cooperative, UI должен честно показывать `after_step`.

## 36. Force terminate

Штатная кнопка «Отменить» и аварийная «Принудительно остановить» — разные операции.

Принудительный stop допустим только если job исполняется в изолированном child process/process group, который можно уничтожить как единицу.

После force termination:

```text
case.status = outcome_unknown
```

затем запускается recovery/diagnostics.

Не следует использовать `QThread.terminate()` как продуктовую отмену.

## 37. Terminal truth выигрывает гонку

Если одновременно происходят:

```text
worker завершил success
и
пользователь нажал Cancel
```

нужен один authoritative terminal transition.

Правило из уже реализованной модели AppDock стоит сохранить:

> После того как terminal outcome committed, поздний control request не меняет его.

Cancel command в таком случае отвечает:

```text
already_terminal
current_status = success
```

---

# VII. Интерфейс отмены

## 38. Case card в чате

Running case должен сразу содержать action area:

```text
┌─────────────────────────────────────────────┐
│ ● Обновление данных Банка России            │
│   Запустил: Дмитрий                         │
│   Шаг 2/5 · Нормализация                    │
│   17:42 · 3 мин.                            │
│                                             │
│   [Открыть детали]              [Отменить] │
└─────────────────────────────────────────────┘
```

После click:

```text
Отмена запрошена Дмитрием
Остановка после безопасной точки…
```

Кнопка становится disabled, чтобы двойной click не создавал две логики.

## 39. Когда спрашивать подтверждение

Не стоит подтверждать каждую обычную отмену отдельным modal — это быстро раздражает.

Подтверждение полезно, когда:

```text
операция destructive
остановка может оставить partial state
пользователь отменяет чужой важный job
force terminate
```

Обычный cancellable read/download scenario можно отменять одним click с коротким undo-like grace period только если архитектура реально поддерживает delayed cancel; иначе лучше просто показать `cancel_requested`.

## 40. Причина отмены

Не следует делать обязательной. Полезный optional field для командной среды:

```text
Причина: неверный период
```

Она попадает в event timeline, но не блокирует быстрый stop.

---

# VIII. Многопользовательское управление

## 41. Локальный JSON больше не может быть authoritative truth

Для сценария пользователя A, который пользователь B должен увидеть и отменить, необходим общий owner состояния.

Текущая модель:

```text
Desktop A
  └─ local case store
```

Целевая:

```text
                ┌─ Windows A
Node authority ─┼─ Windows B
                └─ Android C
```

Case, job state и control commands принадлежат node-side ExecutionService.

Клиенты держат только projection/cache.

## 42. Где проходит граница Strategy Box / AppDock

### Strategy Box владеет

```text
scenario semantics
operation semantics
parameter resolution
case / step state
job resource requirements
artifacts domain metadata
cancel semantics конкретной operation
```

### AppDock владеет

```text
node identity
session identity
user identity
remote connection
transport
permissions / capabilities
host lifecycle
process isolation
общий runtime / observability transport
```

Так граница остаётся чистой: AppDock не знает банковский смысл сценария, Strategy Box не строит собственный VPN/session system.

## 43. Команды между пользователями

Пользователь B должен отправлять на узел не локальное изменение case, а typed command:

```json
{
  "command": "cancel_case",
  "case_id": "...",
  "actor_id": "user-b",
  "expected_revision": 17,
  "reason": "неверный период"
}
```

Ответ:

```text
accepted
already_terminal
not_permitted
not_found
cancel_unsupported
conflict_revision
```

Это делает race conditions предсказуемыми.

## 44. Revision / optimistic concurrency

У case стоит иметь монотонный `revision`.

Каждый state change:

```text
revision 17 → 18
```

Клиент, который пытается управлять старой проекцией, получает новый state вместо того, чтобы молча перезаписать его.

Особенно важно для:

- двойной отмены;
- отмены после завершения;
- двух host users;
- retry одновременно с cancel.

## 45. Права

Не следует зашивать «host всегда может всё» непосредственно в кнопки UI. Нужен capability result от policy layer.

Минимальный набор:

```text
scenario.start
case.view
case.view.params
case.view.logs
case.cancel.own
case.cancel.any
case.retry
case.force_terminate
preset.manage.shared
operation.invoke.ai
```

Пример default policy:

| Actor | Own job | Other job |
|---|---:|---:|
| обычный пользователь | cancel | view |
| host/operator | cancel | cancel |
| observer | view | view |
| AI | по policy | по policy |

Конкретная policy должна жить на уровне AppDock/node authorization, а Strategy Box получает `ActionAvailability`.

## 46. UI не должен сам вычислять permissions

Frontend получает:

```json
{
  "case_id": "...",
  "actions": {
    "cancel": {"allowed": true},
    "retry": {"allowed": false, "reason": "case is running"},
    "force_terminate": {"allowed": false, "reason": "host role required"}
  }
}
```

Windows и Android тогда показывают одинаковую семантику.

## 47. Чат как общий execution timeline

Если host запускает scenario, остальные участники узла должны видеть один и тот же case message:

```text
16:41  Алексей запустил «Обновление данных ЦБ»
16:42  Шаг 1/5: загрузка
16:44  Шаг 2/5: нормализация
16:45  Дмитрий запросил отмену
16:45  Система: отмена подтверждена
16:45  Case cancelled
```

Это естественно ложится на существующие `OperationalEvent` и `actor_kind`.

Понадобятся новые event kinds:

```text
case_queued
case_cancel_requested
case_cancelled
case_cancel_rejected
case_retry_requested
case_retried
step_cancelled
permission_notice
```

## 48. Preferences между пользователями нельзя смешивать

Очень важное разделение:

```text
execution state      → общий на node
user preferences     → личные
shared preset        → общий, отдельная сущность
```

Если пользователь A изменил свой `target_dir` или формат результата, пользователь B не должен внезапно увидеть это как свой default.

---

# IX. Очередь, параллельность и ресурсные конфликты

## 49. Ограничение «один scenario» стоит заменить JobManager

Сегодня `ScenarioCoordinator.is_busy` блокирует второй запуск полностью.

Целевая архитектура должна поддерживать множество jobs, но с явными concurrency rules.

## 50. Scenario/operation должны объявлять resource claims

Пример:

```text
read:  workspace/input
write: workspace/output/escrow
lock:  cache:cbr
network: cbr.ru
```

На этой основе JobManager решает, можно ли запускать jobs параллельно.

## 51. Concurrency policy

Полезные режимы:

```text
parallel
queue
exclusive
coalesce_same_input
replace_previous
```

Примеры:

- два read-only аналитических расчёта — `parallel`;
- две записи в один cache — `exclusive/queue`;
- два одинаковых background refresh с одинаковым fingerprint — `coalesce_same_input`;
- live preview, где новый запуск делает старый ненужным — `replace_previous`.

## 52. Input fingerprint

AppDock уже использует fingerprint входа в `TaskIdentity`. Strategy Box полезно применить тот же принцип на уровне case/job:

```text
scenario_id
+ effective params
+ relevant source/profile version
→ input_fingerprint
```

Это помогает:

- coalescing;
- deduplication;
- traceability;
- reproducibility;
- AI repeated calls.

---

# X. Что делать при закрытии UI

## 53. Закрыть окно и отменить job — разные действия

В host/remote архитектуре закрытие Windows или Android клиента **не должно автоматически отменять** job.

Правильная модель:

```text
client disconnected
job continues on node
client reconnects
sees same case
```

Это особенно важно для долгих SORS/выгрузок/background задач.

## 54. Локальный режим

Даже local execution желательно постепенно вынести в отдельный application service/process, чтобы Qt window не являлся owner работы.

Тогда поведение local и remote становится одинаковым.

До этого перехода при закрытии UI с active job нужна явная политика:

```text
Дождаться завершения
Запросить отмену
Закрыть после завершения
```

Но это временный компромисс. Идеальная модель — job переживает UI.

---

# XI. Retry, resume, repeat и прочие способы управления

## 55. Repeat

`supports_repeat` уже существует. Repeat должен создавать **новый case**.

Варианты:

```text
Повторить с текущими сохранёнными настройками
Повторить с параметрами этого case
```

Это разные вещи и их стоит различать.

## 56. Retry после ошибки

Базовый безопасный вариант:

```text
Retry = новый case с parameter snapshot исходного case
```

То есть старый failure остаётся неизменным.

## 57. Resume from failed step

Это можно разрешать только когда scenario явно имеет:

```text
supports_resume = true
```

и каждый предыдущий step дал валидный reusable output/checkpoint.

По умолчанию никакого «продолжить с места падения» быть не должно: слишком легко повторно использовать частично испорченный state.

## 58. Pause

Общий Pause пока лучше **не вводить**.

Pause имеет смысл только для checkpointable workloads. Для network/download/file operations псевдопауза часто превращается в скрытое удержание ресурсов.

Если когда-нибудь появится:

```text
pause_mode = checkpoint
```

он должен быть explicit capability конкретной operation.

---

# XII. Разделение machine contract и presentation contract

## 59. Текущий OperationSpec смешивает несколько типов metadata

Сейчас в одном объекте находятся:

```text
handler
params
requires_workspace
опасность
AI visibility
icon
order
group
title
submit_label
```

При росте системы полезно разделить два слоя.

## 60. `stratbox` — machine-readable OperationDescriptor

Core должен постепенно стать owner канонических операций, как уже было предложено в предыдущем исследовании core.

Пример:

```python
OperationDescriptor(
    id="escrow.history.build",
    request_schema=...,
    result_schema=...,
    read_only=False,
    destructive=False,
    idempotent=True,
    open_world=True,
    network_required=True,
    storage_required=True,
    cancel_mode="safe_points",
    artifact_kinds=("excel",),
    side_effects=("network_read", "artifact_write"),
)
```

Это machine contract для Windows, Android, background и AI.

## 61. `stratbox-windows` — presentation overlay

Surface добавляет:

```text
русское title/description
group/icon/order
basic/advanced/expert grouping
submit label
UX hints
scenario composition
```

Таким образом core не превращается в UI package, а surface не вынужден вручную описывать техническую природу каждой operation.

## 62. Схемы Request/Result лучше использовать как primary truth

В долгосрочной цели parameter schema operation лучше выводить из typed Request model, а UI metadata накладывать поверх неё.

Это даст:

- единый validation contract;
- JSON schema для AI;
- меньше дублирования;
- одни и те же типы в Windows/Android/API.

Если использовать JSON Schema, нужно помнить: keyword `default` сам по себе является annotation и не вставляет отсутствующее значение автоматически. Strategy Box всё равно нужен собственный explicit `ParameterResolver`.

---

# XIII. AI-доступ к отдельным операциям

## 63. Это правильное направление, если открыть именно канонические operations

Идея пользователя дать AI доступ не только к scenarios/cascades, но и к отдельным operations особенно полезна для:

- диагностики ошибки;
- частичного повторения pipeline;
- сложного ad-hoc поручения;
- формирования нового временного плана;
- получения промежуточного артефакта;
- безопасного repair без полного большого сценария.

Но AI нельзя открывать все Python functions.

Граница:

```text
private implementation function  ≠ AI tool
canonical OperationDescriptor    = потенциальный AI tool
```

## 64. AI policy на operation

Текущий `ai_visibility` стоит превратить в более строгую модель:

```text
hidden
inspect_only
propose
execute
execute_with_approval
```

Отдельно разрешение пользователя/роли может ещё сильнее сузить доступ.

## 65. Side-effect annotations

Для AI особенно полезны machine-readable hints, похожие на уже устоявшийся подход MCP tools:

```text
read_only
destructive
idempotent
open_world
```

К ним Strategy Box стоит добавить:

```text
requires_network
requires_workspace
cancel_mode
estimated_cost_class
approval_policy
required_permissions
artifact_kinds
supports_partial
```

Важно: annotations — metadata, а не security boundary. Реальное permission enforcement выполняет ExecutionService/AppDock policy.

## 66. AI execution flow

```text
AI
 ↓
query allowed operations
 ↓
select operation
 ↓
construct typed request
 ↓
validate
 ↓
approval? ── yes → user confirmation
 ↓
StartOperation / temporary atomic scenario
 ↓
case_id
 ↓
status/events/artifacts
 ↓
optional CancelCase
```

AI всегда оставляет тот же audit trail, что и человек:

```text
actor_kind = ai
agent/session identity
operation id
resolved params (redacted)
case id
outputs
terminal state
```

## 67. AI не должен получать секреты

Если parameter marked `sensitive`, AI получает максимум opaque ref:

```text
secret_ref = "credential:cbr_internal"
```

Он может выбрать разрешённую ссылку, но не прочитать underlying value.

## 68. Ad-hoc cascade от AI

Для сложного поручения AI может собрать временный plan:

```text
step 1: operation A
step 2: operation B
step 3: operation C
```

Такой plan компилируется в ephemeral `ScenarioSpec` / `ExecutionPlan` и проходит те же проверки:

- операции разрешены;
- параметры валидны;
- ресурсные конфликты разрешимы;
- destructive actions требуют approval;
- plan snapshot сохраняется в case;
- каждый step имеет audit trail.

Это гораздо безопаснее, чем давать агенту shell и просить его импровизировать с файлами.

## 69. AI как помощник при ошибке

Перспективный UX:

```text
Case failed
  ↓
[Разобрать с AI]
  ↓
AI видит:
  safe diagnostics
  operation descriptors
  current artifacts
  problem refs
  allowed repair operations
  ↓
предлагает 1–3 действия
  ↓
пользователь подтверждает
```

AI тогда становится consumer наблюдаемости и controlled operations, а не параллельным runtime.

---

# XIV. Связь с Observability

## 70. Cancellation — это событие управления, а не ошибка

Нужно сохранять distinction:

```text
user requested cancellation   → control event
worker confirmed cancellation → terminal cancelled
cleanup failed                → technical failure/problem
force terminated              → outcome_unknown + diagnostics
```

Это хорошо совпадает с текущей AppDock Observability моделью, где cancellation не создаёт synthetic problem occurrence.

## 71. Case и ProblemRef

Если operation завершилась технической ошибкой, case должен содержать safe reference на проблему, а UI — показывать пользовательское объяснение.

Если case отменён штатно:

```text
problem_ref = null
```

Но event timeline всё равно содержит, кто и когда запросил отмену.

## 72. Control actions тоже должны быть наблюдаемыми

Полезно журналировать:

```text
start requested
queued
started
cancel requested
cancel acknowledged
retry requested
force terminate requested
permission denied
terminal outcome
```

При этом raw secrets и технические exception details остаются в локальных инженерных логах, а shared chat получает safe projection.

---

# XV. Рекомендуемые contracts

## 73. CaseRecord

```python
CaseRecord(
    case_id,
    scenario_id,
    scenario_revision,
    input_fingerprint,
    parameter_snapshot,
    author,
    execution_node_id,
    status,
    revision,
    queued_at,
    started_at,
    finished_at,
    current_step_id,
    cancel_request,
    terminal_outcome,
    problem_ref,
    artifacts,
)
```

## 74. CancelRequest

```python
CancelRequest(
    requested_by,
    requested_at,
    reason=None,
    mode="normal",
)
```

## 75. OperationExecutionContext

```python
OperationExecutionContext(
    case_id,
    step_id,
    actor,
    cancellation_token,
    progress_sink,
    diagnostics_sink,
    artifact_sink,
    workspace,
    provenance,
)
```

Core получает platform-neutral object. Никакого Qt внутри.

## 76. ActionAvailability

```python
ActionAvailability(
    action="cancel",
    allowed=True,
    reason=None,
    requires_confirmation=False,
)
```

Одинаковый объект использует Windows, Android и AI gateway.

## 77. ExecutionCommandResult

```text
accepted
rejected
already_terminal
conflict
not_permitted
unsupported
```

Control command должен возвращать control outcome, а не менять client state напрямую.

---

# XVI. Persistence

## 78. Пользовательские настройки лучше отделить от истории запусков

Сегодня `app.json` одновременно постепенно становится местом surface preferences и form values. По мере роста лучше разделить:

```text
config/
  user_preferences.json
  parameter_profiles.json

runtime/
  execution.db / execution state
  logs/
  temp/
```

История cases/events/artifacts — runtime data. Профили параметров — user configuration.

## 79. Atomic write

Parameter profile и preferences надо писать:

```text
temp file
→ flush/close
→ atomic replace
```

Для важного shared state нужен storage с транзакционной семантикой.

## 80. SQLite как естественный local node store

Для shared execution state один локальный SQLite backend выглядит значительно надёжнее пяти независимых JSON-файлов:

- транзакции;
- case + events consistent;
- индексы;
- history retention;
- concurrent readers;
- revision checks;
- хорошая переносимость Windows/Linux host.

Это не обязательный публичный contract. Можно ввести `ExecutionStateStore` и начать с `SQLiteExecutionStateStore`.

На Android клиенту собственная база execution truth не нужна: он получает remote projection и может иметь только cache.

---

# XVII. Cross-platform слой для будущего Android

## 81. Что должно быть frontend-neutral

Общие сегменты `stratbox-windows`, которые стоит довести до чистого состояния до появления Android:

```text
application/operations
application/scenarios
application/execution
application/jobs
application/cases
application/events
application/artifacts
application/presence contracts
application/permissions
application/parameter_profiles
presentation/common
runtime state contracts
```

Они не должны импортировать PySide6.

## 82. Qt должен стать bridge, а не owner orchestration

Целевая структура:

```text
application/execution/
  service.py
  job_manager.py
  cancellation.py
  commands.py
  states.py

adapters/execution/
  local.py
  appdock_remote.py

presentation/qt_desktop/
  execution_bridge.py
```

`execution_bridge.py` только переводит callbacks/events в Qt signals.

Android затем получает свой bridge, не переписывая execution semantics.

---

# XVIII. Что стоит сделать с текущим UI

## 83. Сценарии и каскады

Сохранить существующую IA, но сделать сценарный composer центром запуска.

Добавить в него:

```text
active preset
2–4 ключевых параметра
индикатор изменённых настроек
queue/running state
Cancel action после запуска
```

## 84. Правая вкладка «Параметры»

Развить её до:

```text
Профиль: Мои настройки ▾

Основные параметры
...

Дополнительно ▸
...

Настройки шагов ▸    # только composite

[Сбросить изменения]
[Сохранить как профиль]
```

## 85. Case inspector

Добавить:

```text
Кто запустил
На каком узле
Снимок параметров
Профиль-источник
Input fingerprint
Current step
Cancel capability
Кто запросил cancel
Terminal reason
```

## 86. Chat filters

К текущим фильтрам полезно добавить:

```text
Отменённые
Запущенные другими
Требуют внимания
```

При большом числе background cases лучше не смешивать каждое progress event в центральный чат; case card обновляется на месте, а детальный event stream живёт в inspector.

---

# XIX. Что не стоит делать

## 87. Не показывать пользователю все параметры операций

Composite scenario — это продуктовая абстракция, а не dump внутренних функций.

## 88. Не сохранять secrets в parameter profile

Только references / credentials handles.

## 89. Не считать thread termination отменой

Это аварийная остановка с неизвестным итогом.

## 90. Не хранить shared case truth в клиентах

Multi-user требует node authority.

## 91. Не делать отдельный background engine

Background — такой же scenario/job, только другой trigger и presentation.

## 92. Не делать отдельный AI runner

AI — ещё один actor/client общего ExecutionService.

## 93. Не давать AI произвольные функции

Только канонические operations с contract metadata.

## 94. Не синхронизировать личные remembered values между пользователями автоматически

Для этого существует отдельный shared preset.

## 95. Не вводить общий Pause до появления реальных checkpointable operations

Cancel/retry/resume гораздо важнее.

---

# XX. Приоритетная архитектура по репозиториям

## 96. `stratbox`

Целевые изменения:

```text
1. Канонические typed operations / operation descriptors.
2. Request → Result для всех устойчивых use cases.
3. Neutral OperationExecutionContext.
4. CancellationToken / progress hooks.
5. Side-effect/capability metadata.
6. Machine-readable input/output schema.
7. Никакого UI или AppDock-specific orchestration.
```

## 97. `stratbox-windows`

Целевые изменения:

```text
1. Application-level ExecutionService / JobManager.
2. Scenario registry и composition.
3. ParameterProfile system.
4. Case/event/artifact semantic model.
5. Cancellation state machine.
6. ActionAvailability / permission projection.
7. Local + remote ExecutionBackend adapters.
8. Presentation/common без Qt.
9. Qt только frontend/bridge.
```

## 98. AppDock boundary

Целевая роль:

```text
node/session/user identity
permissions
remote transport
host/service lifecycle
process management
shared control channel
observability/problem references
```

Strategy Box не должен дублировать эти платформенные функции.

---

# XXI. Roadmap без обратной совместимости

## 99. Этап A — execution semantics

Сначала выпрямить фундамент:

1. Ввести frontend-neutral `ExecutionService`.
2. Перенести orchestration из `ScenarioCoordinator` в application layer.
3. Ввести `JobRecord`, `CancellationToken`, terminal-state rules.
4. Расширить case/step statuses.
5. Добавить control commands `start/cancel/retry`.
6. Qt coordinator превратить в adapter.

Это главный архитектурный шаг. Всё остальное становится проще после него.

## 100. Этап B — параметры

1. Ввести `ParameterProfile`.
2. Разделить recommended defaults / remembered values / launch snapshot.
3. Добавить per-field persistence policy.
4. Сделать atomic + debounced save.
5. Добавить Reset / named presets.
6. Добавить schema digest/migration.
7. Для composite — step overrides в advanced UI.

## 101. Этап C — cancellation

1. Cancel queued case.
2. Cancel между steps.
3. Пробросить token в OperationRunner.
4. Добавить token в первые долгие core operations.
5. Добавить `cancel_mode` в descriptor.
6. Temp→publish для крупных артефактов.
7. Отдельно реализовать force termination только через process isolation.

## 102. Этап D — JobManager / background

1. Очередь.
2. Несколько jobs.
3. Resource locks.
4. Background registry запускает обычные scenarios.
5. Перезапуск приложения восстанавливает job state там, где owner-процесс продолжает жить.

## 103. Этап E — multi-user node

1. `ExecutionBackend` abstraction.
2. Node-side authoritative CaseStore.
3. Event subscription.
4. AppDock identity/permission bridge.
5. Remote `CancelCase`.
6. Presence provider.
7. Shared presets отдельно от user profiles.

## 104. Этап F — AI

1. Machine operation registry.
2. JSON-like input/output schema.
3. AI policy + approval policy.
4. AI actor audit.
5. Diagnostic operations.
6. Ad-hoc execution plans из разрешённых operations.

---

# XXII. Минимальный test plan

## 105. Параметры

Проверить:

```text
spec default
user remembered override
named preset
context injection
launch override
fixed value wins
reset clears override
schema changed
old enum invalid
secret never persisted
A user values != B user values
run snapshot не меняется после изменения profile
```

## 106. Cancellation

Обязательные cases:

```text
cancel queued
cancel between steps
cancel cooperative operation
cancel after terminal success
cancel after terminal failure
double cancel
cancel by unauthorized user
cancel own job
cancel other job by host
cancel during retry
cancel before artifact publish
cancel after artifact publish
cleanup failure after cancel
force terminate → outcome_unknown
```

## 107. Multi-user

```text
A starts → B sees same case
B cancels → A sees cancel_requested
A and B cancel concurrently
case terminal transition occurs once
stale expected_revision is rejected
shared chat preserves actor identity
```

## 108. AI

```text
hidden operation absent from tool list
read-only operation executes
approval operation cannot execute without approval
destructive operation filtered by permission
same AI run has actor audit
secret values are redacted
AI cancel obeys same permissions
ad-hoc plan cannot reference unknown operation
```

---

# XXIII. Итоговая целевая пользовательская модель

После этого цикла Strategy Box должен восприниматься пользователем так:

> Я выбираю понятный сценарий. Большинство настроек уже выставлено разумно и помнит мои предпочтения. Каскад не заставляет меня настраивать каждую внутреннюю операцию. После запуска появляется живой кейс в общем чате узла. Я вижу, кто его запустил, что сейчас выполняется, какие результаты уже появились и можно ли безопасно остановить работу. Если я или другой уполномоченный пользователь нажимаем «Отменить», система не убивает процесс вслепую, а переводит задачу в управляемую остановку и честно показывает итог. Закрытие клиентского приложения не уничтожает работу узла. Те же cases доступны с другого Windows-клиента и в будущем с Android. AI работает через тот же каталог разрешённых операций и оставляет тот же audit trail, что человек.

Это естественное развитие уже заложенных в `stratbox-windows` идей. Основная работа состоит не в добавлении ещё одной панели, а в переносе **execution ownership** из Qt desktop-процесса в нейтральный application/node service и в формализации параметров как first-class contract.

---

# XXIV. Самые важные решения в 15 тезисах

1. Пользовательская единица — **scenario**, атомарная машинная единица — **operation**.
2. Composite scenario имеет собственную короткую форму и маппит параметры по steps.
3. Основная масса параметров должна иметь smart defaults; технические policy-values остаются скрытыми.
4. Пользовательские значения сохраняются как `ParameterProfile`, а не просто случайный словарь формы.
5. Case хранит immutable snapshot фактически использованных параметров.
6. Личные profiles и shared presets — разные сущности.
7. Cancellation — cooperative protocol, а не убийство thread.
8. `cancel_requested` и terminal `cancelled` должны быть разными состояниями.
9. Уже committed success/failure нельзя переписать поздним cancel request.
10. Force termination даёт `outcome_unknown`, пока восстановление не докажет состояние.
11. Shared multi-user case truth живёт на execution node, а не в локальном клиентском JSON.
12. Право отменять чужой job приходит из capability/permission layer AppDock.
13. Background, remote user и AI используют тот же JobManager.
14. AI получает только канонические operations с typed schema и side-effect metadata, а не произвольный Python/shell.
15. `stratbox-windows` нужно довести до frontend-neutral application layer, чтобы те же semantics легли в будущий Android без повторного проектирования.

---

# XXV. Источники и база исследования

## Внутренние материалы проекта

- `stratbox-windows_current_state_full_research_2026-10-06.md`
- `stratbox_base_study_current_state_2026-10-06.md`
- `AppDock - Базовое описание.docx`
- актуальный `ForestTiger-GH/stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b`
- актуальный исследованный `ForestTiger-GH/stratbox@e968853572676d8e5d963607d1f0cb50ff8f20b7`
- актуальный `ForestTiger-GH/AppDock` main, включая task-runtime и Observability/cancellation changes, merge `a4d87c643e620e54e04083d4d0b8d867513e7065`

## Внешние технические источники

- Qt `QThread`: https://doc.qt.io/qt-6/qthread.html
- Python `threading`: https://docs.python.org/3/library/threading.html
- Python `concurrent.futures`: https://docs.python.org/3/library/concurrent.futures.html
- Python `asyncio` task cancellation: https://docs.python.org/3/library/asyncio-task.html
- JSON Schema annotations/default: https://json-schema.org/understanding-json-schema/reference/annotations
- Model Context Protocol tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`): https://ts.sdk.modelcontextprotocol.io/v2/api/%40modelcontextprotocol/server/server/mcp.html

