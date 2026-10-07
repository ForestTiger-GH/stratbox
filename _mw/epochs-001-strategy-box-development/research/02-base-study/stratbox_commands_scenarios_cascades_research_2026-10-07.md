# Strategy Box — команды, сценарии, каскады и единая модель запуска

**Ветка исследования:** 02-base-study / вторая ветка исследований Strategy Box  
**Дата:** 2026-10-07  
**Объекты:** `stratbox`, `stratbox-windows`, граница с AppDock  
**Статус:** исследовательский материал; код и репозитории не изменялись

---

## 0. Краткий вывод

Для Strategy Box естественно складывается трехуровневая модель:

```text
Command
  ↓
Scenario
  ↓
Cascade
```

где:

- **Command** — технически атомарная или почти атомарная единица исполнения: получить сетевой ресурс, скачать конкретный source snapshot, прочитать XLSX, распарсить файл, выполнить преобразование, записать артефакт и т. п.;
- **Scenario** — минимальная **пользовательская смысловая операция**: «обновить данные по счетам эскроу», «обновить форму 0409802», «собрать историю отраслевого кредитования»;
- **Cascade** — композиция нескольких сценариев ради более крупной цели: «обновить все данные Банка России», «выполнить ежемесячное обновление макроэкономической и банковской статистики».

В текущем `stratbox-windows` уже есть почти все исходные части, но фактически реализовано только два слоя:

```text
OperationSpec
  ↓ auto-wrap
ScenarioSpec.atomic

OperationSpec + OperationSpec
  ↓
ScenarioSpec.composite
```

То есть текущий `composite scenario` уже фактически является будущим каскадом. Одновременно каждая enabled operation автоматически превращается в пользовательский atomic scenario. Для маленького каталога это удобно, но при росте системы станет архитектурной ловушкой: технические операции начнут засорять пользовательский каталог, а сценарии и каскады останутся смешаны в одной модели.

Целевая архитектура должна сделать четыре вещи.

Во-первых, **операции/commands перестают автоматически становиться пользовательскими сценариями**. Сценарий создается только тогда, когда существует отдельная пользовательская задача.

Во-вторых, **CascadeSpec становится самостоятельным типом**, содержащим ссылки на ScenarioSpec, а не набор низкоуровневых команд. Один сценарий может входить в сколько угодно каскадов без копирования определения.

В-третьих, перед исполнением Scenario или Cascade должен строиться **ExecutionPlan**. Именно planner раскрывает сценарии в команды, строит граф зависимостей, объединяет безопасно эквивалентные команды, выделяет общие ресурсы, параллелит независимые узлы и фиксирует итоговый план запуска.

В-четвертых, UI должен быть **scenario-first / cascade-first**. Низкоуровневые команды обычный оператор напрямую не выбирает. Они видны как техническая детализация выбранного сценария или фактического запуска. ИИ получает тот же управляемый каталог; доступ к command-level планированию может быть отдельной capability, а не обходом сценарной модели.

Самый важный практический результат исследования:

> **Дедупликацию общих шагов нельзя решать простым правилом «одинаковый command_id выполняется один раз». Нужен planner, который различает идентичность операции, параметры, входы, окружение, freshness, эффекты, idempotency и область допустимого reuse.**

Это позволяет одновременно получить более быстрое выполнение и сохранить корректность.

---

# I. Исходное состояние Strategy Box

## 1. Что уже существует в `stratbox-windows`

Актуальная модель desktop surface уже scenario-first.

Текущий `OperationSpec` содержит stable ID, handler, группировку, tags/search aliases, параметры, fixed values, признаки опасности, тип результата, visibility, logging и AI visibility. Это сильная база для будущего command registry.

Текущий `ScenarioSpec` содержит id/title/description, kind, group, steps, params, порядок, expected artifacts, error policy, repeat/background flags и visibility policy. `ScenarioStepSpec` уже умеет ссылаться на operation, маппить параметры, задавать overrides, required и order.

### 1.1. Автоматическая генерация atomic scenarios

Сейчас каждая enabled operation автоматически получает:

```text
scenario.atomic.<operation_id>
```

Поэтому `OperationSpec` и atomic `ScenarioSpec` почти взаимно однозначны.

В ранней версии это удобно. В зрелой системе это лишает архитектуру возможности иметь десятки внутренних технических commands, которые никогда не должны появляться в основном пользовательском каталоге.

### 1.2. Текущий composite scenario

Сейчас существует один настоящий составной сценарий:

```text
scenario.cbr.full_update
«Обновление данных Банка России»
```

Он последовательно запускает:

```text
cbr_file_collector.collect
escrow.history.export
```

и маппит user-facing параметры на operation-specific параметры.

Это уже маленький workflow engine. С точки зрения желаемой трехуровневой модели этот объект лучше считать **первым прототипом Cascade**, а не сложным Scenario.

### 1.3. Текущий runner

`run_scenario()` сегодня создает/обновляет case, проходит steps последовательно, строит operation params, вызывает `run_operation()`, фиксирует step status, создает log/artifact records, публикует events, применяет error policy и завершает case.

Это хороший execution skeleton, но он исполняет уже заранее линейный список steps. Отдельного compilation/planning phase пока нет.

### 1.4. Текущее ограничение исполнения

Qt `ScenarioCoordinator` допускает только один активный scenario, запускает его в `QThread`, не имеет cancellation API, очереди, графа параллельных работ и coalescing/dedup между работами.

Это нормально для нынешнего масштаба, но несовместимо с будущими каскадами из десятков сценариев.

---

## 2. Что уже существует в UI

Текущая информационная архитектура уже содержит:

```text
Проводник
Сценарии
Каскады
Фоновые
Участники
Поручения
```

При этом:

- панель **Сценарии** показывает `ScenarioSpec.kind == atomic`;
- панель **Каскады** показывает `ScenarioSpec.kind == composite`;
- нижний `BottomScenarioComposer` показывает выбранный scenario, число его steps, краткие параметры, кнопку деталей и запуск;
- параметры строятся декларативно из spec;
- case/log/artifact/details живут в правом inspector;
- execution history показывается в сценарном чате.

То есть UI уже почти находится в правильной продуктовой форме. Главная проблема — внутренняя семантика моделей пока не соответствует названиям UI.

---

## 3. Что уже существует в `stratbox`

В core постепенно возникает отдельное понятие **предметной операции**: устойчивый use case с stable ID, Request/Result, side-effect profile, требованиями к network/storage и типами артефактов.

Это важное различие. Сейчас слово `operation` используется на двух близких, но не идентичных уровнях:

- в core — как будущий канонический предметный use case;
- в surface — как исполнительный handler, автоматически превращаемый в scenario.

Перед масштабированием это нужно привести к одной системе понятий.

---

# II. Целевая терминология

## 4. Не три названия одного и того же, а три разные ответственности

### 4.1. Command

**Command** — минимальная управляемая исполнительная единица.

Это не обязательно одна Python-функция и не обязательно одна системная команда. Это шаг, для которого можно отдельно определить входы, выходы, эффекты, ресурсы, timeout, retry, cancellation, idempotency, dedup/reuse и observability.

Примеры:

```text
cbr.network.ensure_access
source.fetch
xlsx.read
cbr.escrow.parse
dataset.validate
artifact.xlsx.write
workspace.file.copy
```

Command — в первую очередь объект **машинного исполнения**.

### 4.2. Scenario

**Scenario** — минимальная единица, которую оператор осмысленно выбирает ради результата.

Например:

```text
Обновить историю счетов эскроу
Обновить форму 0409802
Собрать отраслевую статистику ЦБ
Обновить справочник банков
Выполнить диагностику Strategy Box
```

Scenario может содержать одну command, десять commands, ветвление, параллельные steps, resource prerequisites, проверки и export. Количество внутренних commands не определяет, является ли объект «атомарным» для пользователя.

### 4.3. Cascade

**Cascade** — композиция Scenario.

Например:

```text
Обновить все данные Банка России
Ежемесячное обновление макроэкономической и банковской статистики
Подготовить полный набор данных для банковского обзора
```

Cascade не владеет сценариями. Он **ссылается** на них.

```text
Scenario A
 ├─ входит в Cascade X
 ├─ входит в Cascade Y
 └─ запускается самостоятельно
```

Это many-to-many relationship.

### 4.4. Run / Case

Определение и запуск — разные сущности:

```text
ScenarioSpec / CascadeSpec = что можно выполнить
Run / Case                  = конкретное выполнение
```

Текущий `ScenarioRunCase` уже почти подходит как универсальная user-facing execution instance. В будущем разумно либо обобщить имя, либо добавить `target_kind = scenario|cascade`.

### 4.5. ExecutionPlan

Это новая центральная сущность:

```text
Scenario/Cascade request
        ↓
Planner
        ↓
ExecutionPlan
        ↓
Executor
```

ExecutionPlan является конкретной, полностью разрешенной и зафиксированной версией будущего исполнения.

---

# III. Важная классификация commands

## 5. Не все «атомарные команды» одинаковы

Пользовательские примеры хорошо показывают, почему простой список commands быстро станет неправильным.

### «Подключиться к сайту ЦБ»

Это чаще всего не отдельная бизнес-команда, а **resource acquisition / capability prerequisite**.

Лучше моделировать ее как:

```text
ResourceRequirement:
    network_profile = cbr
```

или как internal command `cbr.network.ensure_access`, который planner автоматически поднимает в общий prerequisite и выполняет максимум один раз на нужную execution scope.

Пользователь не должен видеть «подключиться к сайту ЦБ» как отдельный сценарий.

### «Загрузить XLSX»

Это хороший command:

```text
source.fetch
```

с параметрами source_id, URL, freshness/cache policy, expected content type и validation.

### «Открыть файл»

Для большинства случаев это вообще не command аналитического workflow, а **surface action над Artifact**:

```text
artifact.open
artifact.reveal
artifact.copy_path
```

Такие действия должны жить рядом с артефактом и выполняться desktop/mobile adapter-ом. Иначе headless/remote cascade внезапно получит бессмысленный шаг «открыть файл на экране».

### Вывод

Нужны минимум четыре класса действий:

```text
1. resource acquisition / readiness
2. data/work commands
3. side-effect / commit commands
4. surface actions
```

UI и planner должны относиться к ним по-разному.

---

# IV. Целевая модель Command

## 6. CommandSpec

Пример целевого контракта:

```python
CommandSpec(
    id="source.fetch",
    title="Получить источник",
    owner="sources",
    input_schema=...,
    output_schema=...,
    effect_class="network_read",
    cacheable=True,
    resource_requirements=("network:cbr",),
    concurrency_keys=("source:{source_id}",),
    dedup_policy="equivalent_invocation",
    cache_scope="execution_or_snapshot",
    idempotency="qualified",
    retry_policy="network_read_default",
    timeout_policy="source_fetch_default",
    cancellation="cooperative",
    ui_visibility="internal",
    ai_visibility="planner",
    observability="structured",
)
```

Не каждое поле должно быть строкой именно такой формы. Важна семантика.

---

## 7. Поля, без которых безопасная оптимизация невозможна

Planner не сможет корректно объединять одинаковые команды, пока spec не сообщает:

- **Identity:** `command_id`, `command_version`;
- **Inputs:** canonical params, input artifact/content identities, environment-sensitive inputs;
- **Effects:** `pure`, `read_only`, `network_read`, `local_write`, `remote_write`, `external_effect`, `destructive`, `surface_action`;
- **Idempotency:** область, в которой повтор эквивалентен, а не просто bool;
- **Reuse/dedup:** `never`, `within_execution`, `within_node_session`, `persistent_cache`, `resource_singleton`;
- **Freshness:** `allow_cached`, `prefer_cached`, `require_fresh`, `require_snapshot_id`, `max_age`;
- **Concurrency:** `parallel_safe`, `serial_by_source`, `serial_by_destination`, `exclusive_resource`;
- **Cancellation:** `immediate`, `cooperative`, `after_safe_point`, `not_cancellable`.

---

# V. Scenario как пользовательская смысловая единица

## 8. Сценарий больше не должен иметь kind=atomic/composite

В целевой модели `ScenarioSpec` сам по себе уже означает пользовательский сценарий. Количество commands внутри него — внутренняя реализация.

Поэтому `kind = atomic | composite` лучше удалить.

То же касается `kind = background | assignment`, потому что background и assignment описывают **как/почему запущен сценарий**, а не что это за сценарий.

Один и тот же сценарий может запускаться вручную, по расписанию, в фоне, по поручению, AI, локально или на host. Это не семь разных ScenarioSpec.

---

## 9. Целевой ScenarioSpec

```python
ScenarioSpec(
    id="cbr.escrow.update",
    title="Обновить данные по счетам эскроу",
    description="...",
    group="Банк России",
    tags=("эскроу", "ежемесячные", "строительство"),
    params=(...),
    graph=ScenarioGraph(...),
    outcome=ScenarioOutcomeSpec(
        artifacts=("dataset", "xlsx"),
        summary="...",
    ),
    execution_capabilities=("foreground", "background", "remote"),
    permissions=...,
    ai_visibility="standard",
    ui_visibility="catalog",
)
```

---

## 10. Сценарий может быть DAG, а не списком

Даже простой сценарий «обновить эскроу» естественно раскладывается так:

```text
             ┌─ fetch source A ─ parse A ─┐
ensure cbr ──┼─ fetch source B ─ parse B ─┼─ build history ─ validate ─ export
             └─ fetch source C ─ parse C ─┘
```

Graph дает параллельные downloads, fan-in, общие prerequisites, planner optimization и точную progress модель. Для простого сценария linear graph остается обычным частным случаем.

---

# VI. Cascade как самостоятельная сущность

## 11. Почему CascadeSpec нужен отдельно

Текущий `ScenarioSpec(kind='composite')` объединяет два смысла:

1. сценарий может иметь несколько внутренних steps;
2. пользователь может запускать набор самостоятельных сценариев.

Это разные вещи.

```text
Scenario:
    «Обновить счета эскроу»
        ├─ discover
        ├─ fetch
        ├─ parse
        ├─ build history
        └─ export

Cascade:
    «Обновить все данные Банка России»
        ├─ Scenario «Счета эскроу»
        ├─ Scenario «Формы отчетности»
        ├─ Scenario «Отраслевая статистика»
        └─ Scenario «Справочник банков»
```

Если оба уровня представить одним `ScenarioSpec`, сложно показывать каталог, понимать принадлежность, переиспользовать сценарии, строить AI tools, сохранять progress и дедуплицировать общие commands.

---

## 12. Целевой CascadeSpec

```python
CascadeSpec(
    id="cbr.all.update",
    title="Обновить все данные Банка России",
    description="...",
    group="Банк России",
    tags=("полное обновление",),
    members=(
        ScenarioRef(scenario_id="cbr.escrow.update", params_map={...}),
        ScenarioRef(scenario_id="cbr.forms.update", params_map={...}),
        ScenarioRef(scenario_id="cbr.industries.update", params_map={...}),
    ),
    dependency_policy=...,
    failure_policy="continue_independent",
    optimization_policy="safe",
)
```

---

## 13. Один Scenario — много Cascade

Cascade membership нельзя записывать внутрь Scenario как единственного `parent`.

Правильная модель:

```text
ScenarioRegistry
CascadeRegistry
```

и ссылки по stable ID.

Например, `cbr.escrow.update` может одновременно входить в `cbr.all.update`, `monthly.macrobanks.update` и `banking_review.data.refresh` без копирования ScenarioSpec.

---

# VII. Как формировать большие каскады

## 14. Два способа membership

### 14.1. Explicit membership

Для управляемых производственных каскадов:

```text
scenario A
scenario B
scenario C
```

Плюсы: предсказуемость, auditability, а изменение списка является явным изменением CascadeSpec. Это должен быть режим по умолчанию.

### 14.2. Selector membership

Для семантики вроде «все текущие сценарии Банка России» может быть полезен selector:

```text
group == "Банк России"
tag contains "source_update"
enabled == true
```

Но selector должен разрешаться **до запуска**. Run сохраняет exact resolved set, и именно он становится частью immutable ExecutionPlan.

Так «все данные ЦБ» остается живой коллекцией, но каждый фактический запуск воспроизводим.

---

# VIII. Planner — центральный новый слой

## 15. Почему dedup должен быть частью planning phase

Нельзя оптимизировать execution «на лету», просто увидев уже выполненный command_id. Сначала нужно знать весь предполагаемый граф.

Целевой pipeline:

```text
Scenario/Cascade selection
        ↓
resolve parameters
        ↓
expand Cascade → Scenario invocations
        ↓
expand Scenario → Command invocations
        ↓
resolve resources
        ↓
canonicalize invocation identity
        ↓
deduplicate safely equivalent work
        ↓
build dependencies
        ↓
parallelization / ordering
        ↓
approval gates
        ↓
ExecutionPlan
        ↓
execute
```

---

## 16. CommandInvocation

Definition и invocation нужно разделять:

```text
CommandSpec       = тип действия
CommandInvocation = конкретное действие с конкретными входами
```

Пример:

```python
CommandInvocation(
    invocation_id="...",
    command_id="source.fetch",
    params={
        "source_id": "cbr.escrow.2026-09",
        "refresh": False,
    },
    input_refs=(...),
    environment_ref="node-...",
)
```

---

# IX. Дедупликация: что можно объединять

## 17. Базовый принцип

Две invocations можно объединить только если доказано, что:

```text
A и B означают один логический work result
и один результат A допустим как результат B
и совместное исполнение не меняет разрешенные эффекты.
```

Это сильнее, чем `command_id A == command_id B`.

---

## 18. Equivalence key

Для dedup planner строит **execution equivalence key**. Условно в него входят:

```text
command version
+ canonicalized semantic inputs
+ relevant environment identity
+ source/snapshot identity
+ freshness requirement
+ effect destination
+ security/permission scope
```

Не каждое поле участвует в каждом command.

---

## 19. Пример безопасного dedup

Два сценария требуют:

```text
source.fetch(
    source_id="cbr.index",
    freshness="require_fresh"
)
```

в рамках одного cascade run.

Planner может построить:

```text
fetch cbr.index
      ↙       ↘
Scenario A   Scenario B
```

а не два downloads.

---

## 20. Пример частично совместимых требований freshness

Scenario A требует `allow_cached`, Scenario B — `require_fresh`.

Иногда одна fresh fetch может удовлетворить обоих. Но это должно быть формализовано как отношение:

```text
require_fresh satisfies allow_cached
```

а не как случайный выбор «более строгого значения».

Planner может использовать monotonic policy resolution только для параметров, где CommandSpec явно объявляет такую семантику.

---

## 21. Пример, который нельзя дедуплицировать автоматически

```text
artifact.write(target="A.xlsx")
artifact.write(target="B.xlsx")
```

Одинаковый command_id и одинаковые данные не означают один эффект: destinations разные.

Можно дедуплицировать upstream computation, но две записи остаются отдельными commands.

---

## 22. Destructive/external effects

Для:

```text
remove
publish
send
rename
external mutation
```

дедуп по умолчанию должен быть выключен.

Повторяемость разрешается только при отдельном idempotency contract.

---

## 23. «Открыть файл»

Два запроса «открыть один и тот же файл» не нужно включать в data planner.

Это surface action. Его поведение определяется текущим client/frontend, а не dedup workflow engine.

---

# X. Общие подключения и ресурсы

## 24. Shared resources вместо повторяющихся setup-команд

Если десять commands требуют доступ к одному источнику, лучше моделировать:

```text
resource: network:cbr
```

а не вставлять десять раз `connect_to_cbr()`.

Planner строит:

```text
acquire network:cbr
        ↓
 ┌──────┼───────┐
 cmd A  cmd B   cmd C
```

Resource может иметь scope, lifecycle, health check, max concurrency, idle timeout и cleanup.

Это быстрее и делает failure semantics яснее.

---

# XI. Параллельное исполнение

## 25. Cascade не должен быть просто длинным for-loop

После раскрытия и dedup planner уже имеет DAG. Независимые nodes можно запускать параллельно.

Например:

```text
                   ┌─ escrow update ──────────┐
shared CBR access ─┼─ forms update ───────────┼─ cascade summary
                   └─ industries update ──────┘
```

Внутри каждого scenario также возможен parallelism.

---

## 26. Ограничения concurrency

Нужны scopes:

```text
global max workers
per-host limit
per-source limit
per-domain limit
per-destination serialization
exclusive resource locks
```

Особенно полезно для внешних статистических сайтов: быстрая система не должна превращаться в агрессивный downloader.

---

# XII. Retry, cancellation, resume

## 27. Retry принадлежит command policy

Retry нельзя независимо задавать на нескольких вложенных слоях:

```text
HTTP layer = 3 attempts
Command = 3 attempts
Scenario = 3 attempts
Cascade = 3 attempts
```

Это создает скрытое усиление. Нужен один governing retry contract на конкретный effect boundary.

---

## 28. Cancellation

Cancellation cascade должна распространяться вниз:

```text
Cascade Run
  ↓ cancel
Scenario Runs
  ↓
Command Invocations
```

При этом command сообщает более точный результат:

```text
cancelled_before_start
cancelled_at_safe_point
completed_before_cancel
cannot_cancel
unknown_external_effect
```

Простого статуса `cancelled` недостаточно для операций с внешними эффектами.

---

## 29. Resume

После crash/restart planner не должен «просто снова запустить всё».

Execution history должна знать:

```text
completed reusable nodes
failed nodes
unknown nodes
non-repeatable nodes
expired cached results
```

Новый plan решает, что можно reuse, что повторить, а что сначала reconcile.

---

# XIII. ExecutionPlan как first-class object

## 30. Что хранить в плане

Минимум:

```text
plan_id
target_kind
target_id
target_version

resolved scenario invocations
resolved command invocations

dependency graph
dedup groups
resource requirements
parallel groups

resolved parameters
freshness decisions
cache/reuse decisions

effect summary
approval requirements

planner version
created_at
plan_hash
```

После старта immutable snapshot плана связывается с Case.

---

## 31. Пользовательский preview

Для крупного каскада полезно показывать:

```text
Обновление всех данных Банка России

8 сценариев
34 исходных command invocations
27 задач после оптимизации
3 общих источника будут загружены один раз
до 4 независимых веток одновременно
ожидаемые результаты: 11 артефактов
```

Это понятнее, чем показывать пользователю 34 низкоуровневые команды.

---

# XIV. Что оператор должен видеть

## 32. Команды не должны иметь основного каталога

Для обычного оператора основная IA:

```text
Сценарии
Каскады
```

Commands доступны через:

```text
Scenario → Подробнее → План выполнения
Case → Технические детали → Commands
```

Это соответствует продуктовой идее AppDock: пользователь выбирает понятное действие, а система сама знает внутренние шаги.

---

## 33. Где commands все-таки полезны человеку

Command-level view нужен при диагностике, ошибке, анализе производительности, разработке, preview сложного cascade, расследовании partial/unknown result и для advanced operator.

То есть commands скрыты по умолчанию, но никогда не являются «невидимой магией».

---

# XV. Каталог сценариев

## 34. Группировка по смыслу

Сценарии нужно группировать по устойчивому предметному owner/domain:

```text
Банк России
Росстат
Банковская отчетность
Макроэкономика
Справочники
Система
```

Внутри — сценарии.

Не стоит строить слишком глубокое дерево. По мере роста оно станет тяжелее поиска. Вместо этого использовать:

```text
canonical group
+ tags
+ search aliases
+ favorites
+ recent
```

---

## 35. Сценарий может иметь несколько смысловых тегов

Например:

```text
«Обновить счета эскроу»

group: Банк России
tags:
  строительство
  проектное финансирование
  ежемесячные
  ипотека
```

Поиск сможет находить сценарий по любому смыслу без дублирования записи.

---

# XVI. Каталог каскадов

## 36. Каскады группируются по цели, а не по ownership сценариев

Естественные классы:

### По источнику

```text
Все данные Банка России
Все данные Росстата
```

### По периодическому процессу

```text
Ежемесячное макрообновление
Ежеквартальное банковское обновление
```

### По конечному аналитическому продукту

```text
Обновить данные банковского обзора
Подготовить данные к квартальному анализу
```

Одни и те же Scenario могут входить во все три типа.

---

# XVII. Нижняя панель запуска

## 37. Что сейчас хорошо

Текущий `BottomScenarioComposer` уже делает правильные вещи: находится в постоянном месте, показывает выбранный сценарий, дает краткую сводку, отдельный доступ к параметрам и явную кнопку запуска.

Его стоит развивать, а не заменять тяжелой toolbar-системой.

---

## 38. Целевая форма: Universal Launch Bar

Предлагаемая компактная форма:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ [Сценарий]  Обновить счета эскроу                         [⋯] [▶] │
│ Банк России · параметры по умолчанию · последний запуск: успешно   │
└─────────────────────────────────────────────────────────────────────┘
```

Для cascade:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ [Каскад]  Обновить все данные Банка России                [⋯] [▶] │
│ 8 сценариев · 27 задач после оптимизации · 11 артефактов            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 39. Выбор через саму панель

Клик по названию либо `Ctrl+K` открывает единый selector:

```text
Поиск сценария или каскада…

Недавние
  Обновить счета эскроу
  Ежемесячное макрообновление

Закрепленные
  Обновить все данные Банка России

Сценарии
  ...

Каскады
  ...
```

Обычные Commands туда не попадают.

---

## 40. Почему единый selector лучше двух разных launcher-ов

Оператор чаще думает «что я хочу сейчас сделать?», а не «это формально Scenario или Cascade?». Поэтому единая поисковая точка быстрее.

При этом badge `Сценарий` / `Каскад` всегда сохраняет ясность типа объекта.

---

## 41. Поиск

Полезны fuzzy search, search aliases, tags, source/domain filters, recent, favorites и keyboard navigation.

Это подтверждается зрелыми launcher/IDE паттернами: VS Code Command Palette, JetBrains Search Everywhere/Run Anything и Raycast Root Search используют один быстрый searchable entry point и контекстные действия вместо длинной иерархии меню.

Strategy Box не должен превращаться в универсальный OS launcher. Здесь нужен только тот же UX-принцип для ограниченного каталога рабочих сценариев.

---

## 42. Параметры

Основные параметры остаются в right inspector.

В самой нижней панели показывается только compact summary:

```text
период: сентябрь 2026 · refresh: да · …
```

Это сохраняет панель узкой.

---

## 43. Preview plan

Кнопка `⋯` открывает inspector.

Для Scenario:

```text
Параметры
Ожидаемые результаты
План выполнения
Последний запуск
```

Для Cascade:

```text
Параметры
Сценарии
Оптимизированный план
Ожидаемые результаты
Последний запуск
```

---

# XVIII. Что происходит с панелью во время запуска

## 44. Запуск не должен полностью блокировать launcher

Сегодня при busy composer блокируется, потому что executor допускает только один run.

После введения JobManager это ограничение стоит снять. Панель может показывать текущий выбранный action, а отдельный compact indicator — например `3 выполняются · 1 в очереди` — ведет в Jobs/active cases.

---

## 45. Крупный active cascade

Для текущего выбранного active case можно показывать:

```text
Обновление данных Банка России
5 / 8 сценариев · 62%
Сейчас: формы 0409802
[Открыть] [Отменить]
```

Детальное execution tree остается в case inspector.

---

# XIX. Как показывать выполнение каскада в чате

## 46. Case должен оставаться одной пользовательской сущностью

Не нужно создавать в основном чате двадцать независимых сообщений по каждому command.

Лучше:

```text
Case: «Обновить все данные Банка России»
    status
    progress
    текущий scenario
    summary
    artifacts
```

При раскрытии:

```text
Scenario 1 ✓
Scenario 2 ✓
Scenario 3 running
Scenario 4 queued
```

Еще глубже:

```text
Command nodes
```

Это progressive disclosure.

---

# XX. ИИ-контур

## 47. AI не нужен shell-доступ к commands

Правильный путь:

```text
AI
 ↓
read catalog
 ↓
select Scenario/Cascade
 ↓
plan
 ↓
request execution
 ↓
Case ID
 ↓
observe status/events/artifacts
```

То есть AI использует ту же semantic surface, что человек.

---

## 48. AI API уровня пользователя

Минимальный набор:

```text
list_scenarios()
get_scenario(id)

list_cascades()
get_cascade(id)

plan_execution(target, params)
execute_plan(plan_id)

get_case(case_id)
cancel_case(case_id)

list_artifacts(case_id)
```

Этого достаточно для большинства задач.

---

## 49. Planner-level AI

Для более сильного агента можно отдельно разрешить:

```text
list_commands()
inspect_command()
build_ephemeral_plan()
```

Но это отдельная capability.

Такой агент может сказать: «Для этой задачи готового сценария нет. Я собрал временный план из разрешенных commands».

Перед запуском система валидирует plan, проверяет права, применяет effect policy, показывает preview и при необходимости требует подтверждение.

---

## 50. ИИ не должен обходить Scenario/Cascade Registry

Если AI может напрямую вызвать arbitrary handler string, вся управляемая архитектура теряет смысл.

Для AI command catalog должен быть таким же registry-controlled объектом, как для executor.

---

## 51. Сохранение AI-сборок

Нужно различать:

```text
ephemeral plan
saved personal scenario
published shared scenario
```

AI может собирать ephemeral plan в рамках разрешений.

Превращение такого плана в устойчивый общий ScenarioSpec — отдельное действие с валидацией.

---

# XXI. Background execution

## 52. Background — способ запуска, а не тип сценария

Текущий:

```text
ScenarioKind = atomic | composite | background | assignment
```

лучше заменить ортогональными контрактами:

```text
ScenarioSpec
CascadeSpec
TriggerSpec
ExecutionPolicy
Assignment
```

Например:

```text
Scenario: cbr.escrow.update

Trigger:
    schedule = monthly

ExecutionPolicy:
    mode = background
    backend = host
```

Тот же Scenario можно вручную запустить foreground.

---

## 53. BackgroundProcessSpec

Существующий background registry естественно эволюционирует до:

```text
AutomationSpec(
    id=...,
    target_kind="scenario|cascade",
    target_id=...,
    trigger=...,
    params=...,
    concurrency_policy=...,
)
```

Тогда background runtime не является второй системой workflows.

---

# XXII. Повторный запуск одной и той же работы

## 54. Cross-run coalescing

Если scheduled cascade уже выполняется и пользователь нажал тот же cascade еще раз, нельзя автоматически запускать второй идентичный каскад.

Нужна concurrency policy:

```text
allow_parallel
queue
skip_if_running
join_existing
replace_pending
```

Для source update часто хорошо подходит `join_existing` или `skip_if_running`, но это должно быть свойством конкретной automation/execution policy.

---

# XXIII. Observability и план исполнения

## 55. ExecutionPlan должен стать частью причинной цепочки

Предыдущее observability-направление Strategy Box/AppDock требует сохранять причинность, operation context, результаты, логи и evidence.

Новая цепочка должна выглядеть:

```text
user/AI intent
   ↓
selected Scenario/Cascade
   ↓
ExecutionPlan
   ↓
Case
   ↓
Scenario invocations
   ↓
Command invocations / attempts
   ↓
Artifacts / effects / logs
```

Тогда по ошибке всегда можно ответить:

```text
кто инициировал;
что выбрал;
какой exact plan получился;
что planner объединил;
что реально выполнялось;
какая attempt упала;
какие эффекты успели произойти;
какие результаты уже валидны.
```

---

## 56. Dedup должен быть наблюдаемым

Если planner объединил две invocations, это следует сохранять как факт:

```text
command node N17
requested by:
  Scenario A / step 2
  Scenario B / step 1

dedup reason:
  equivalent invocation

result reused by:
  ...
```

Иначе техническая оптимизация разрушит объяснимость.

---

## 57. Retry attempt не равен новой logical command

Нужно различать:

```text
Logical Command Invocation
    ├─ Attempt 1
    ├─ Attempt 2
    └─ Attempt 3
```

Это важно и для истории, и для метрик, и для ошибок.

---

# XXIV. Граница Strategy Box и AppDock

## 58. Что должно принадлежать Strategy Box

Strategy Box должен владеть:

- CommandSpec, ScenarioSpec, CascadeSpec;
- предметной каталогизацией;
- command/scenario/cascade planner;
- parameter semantics;
- result/artifact semantics;
- domain progress;
- internal execution graph;
- safe optimization rules;
- case-level domain state.

---

## 59. Что должен видеть AppDock

AppDock естественно получает более грубую управляемую поверхность:

```text
доступные Actions
running jobs
status/progress
health
artifacts
logs/evidence references
warnings
cancel/diagnostics/recovery capabilities
```

Для AppDock actions логично публиковать Scenario, Cascade и сервисные high-level actions, а не каждую внутреннюю Command.

Это сохраняет принцип «действия вместо команд» и не связывает платформу с внутренней бизнес-декомпозицией Strategy Box.

---

# XXV. Android и platform-neutral architecture

## 60. Почему новая модель хорошо переносится

Следующие части должны быть Qt-free:

```text
commands/
scenarios/
cascades/
planning/
jobs/
cases/
presentation/common projections
```

Windows UI только рендерит их.

Android потом получает тот же `ScenarioRegistry`, `CascadeRegistry`, `ExecutionPlanSummary`, Case projection и LaunchBar model — со своим UI.

---

## 61. Что особенно важно не привязывать к desktop

Не переносить внутрь Scenario/Command:

```text
open file in Explorer
reveal in folder
desktop dialog
QThread
Qt Signal
Windows path UI
```

Это adapters/presentation.

---

# XXVI. Целевая структура `stratbox-windows`

## 62. Возможная структура

```text
application/
  commands/
    models.py
    registry.py
    invocation.py

  scenarios/
    models.py
    registry.py

  cascades/
    models.py
    registry.py

  planning/
    planner.py
    graph.py
    equivalence.py
    resources.py
    policies.py

  execution/
    job_manager.py
    backend.py
    local_backend.py
    cancellation.py

  cases/
  events/
  artifacts/
  logs/

  automation/
    triggers.py
    registry.py

presentation/
  common/
    launch_bar/
    catalogs/
    execution_plan/
    case_inspector/

  qt_desktop/
```

Названия могут меняться. Важны границы.

---

# XXVII. Где должна жить бизнес-логика

## 63. Core сохраняет предметные операции

`stratbox` продолжает владеть source acquisition logic, parsing, canonical models, validation, reconstruction и export.

`stratbox-windows` владеет тем, что доступно пользователю, как это объединяется в Scenario/Cascade, как запускается, показывается и отслеживается.

При этом хороший command в surface часто будет тонкой адаптацией устойчивой core operation.

---

# XXVIII. Изменение текущих моделей

## 64. OperationSpec

Текущий `OperationSpec` можно либо переименовать в `CommandSpec`, либо оставить с четкой семантикой technical executable atom.

С учетом отсутствия требования обратной совместимости **переименование в CommandSpec выглядит яснее**, если слово operation в core окончательно закрепляется за предметными use cases.

---

## 65. ScenarioSpec

Удалить смысл:

```text
kind = atomic|composite|background|assignment
```

Добавить graph/commands, category/tags, capabilities и outcome spec.

---

## 66. CascadeSpec

Новая самостоятельная модель:

```text
members
scenario parameter mappings
dependency constraints
membership mode
failure policy
optimization policy
```

---

## 67. ScenarioRunCase

Обобщить модель, чтобы она могла представлять запуск Scenario или Cascade. Внутри Cascade case хранить child scenario runs.

---

# XXIX. Failure policy

## 68. Cascade failure semantics

Одного `fail_fast` недостаточно.

Нужны как минимум:

```text
fail_fast
continue_independent
continue_all_safe
```

- `fail_fast` останавливает новые downstream work после первой существенной ошибки;
- `continue_independent` оставляет независимые ветки в работе, dependent branches блокирует;
- `continue_all_safe` продолжает все steps, чьи preconditions остаются выполнены.

Это естественно работает только поверх DAG.

---

# XXX. Общая модель результата Cascade

## 69. Cascade result не равен «все success или failed»

Возможные итоговые состояния:

```text
success
warning
partial_success
failed
cancelled
unknown
```

Например:

```text
8 сценариев
6 успешно
1 failed
1 skipped due dependency
```

Пользователь должен видеть содержательный partial result.

---

# XXXI. Кэш и дедуп — разные вещи

## 70. Важно не смешивать

**Dedup:** две части одного execution plan требуют эквивалентную работу — выполняем ее один раз.

**Cache reuse:** нужный результат уже был получен раньше — возможно не выполняем command сейчас.

Это разные решения и разные доказательства.

Planner должен фиксировать:

```text
executed_now
deduplicated_within_plan
reused_from_cache
reused_from_previous_case
```

---

# XXXII. Артефакты и lineage

## 71. Общий command result можно переиспользовать

Если один fetch/parse node используется несколькими scenarios, его артефакт/data reference имеет несколько downstream consumers.

```text
source snapshot
    ↓
parsed dataset
   ↙ ↘
 S1   S2
```

Это стоит отражать в artifact metadata.

---

# XXXIII. Favorites, Recent и персонализация

## 72. Каталог будет расти

При 50–100 сценариях дерево становится менее важным, чем:

```text
Recent
Pinned/Favorites
Recommended in current context
Search
```

Это особенно важно для нижней launcher bar.

Можно сохранять локально recent scenario IDs, recent cascade IDs, favorites и last parameter values без изменения shared definitions.

---

# XXXIV. Контекстные сценарии

## 73. Launch Bar может учитывать текущий объект

Если выбран artifact `escrow_history.xlsx`, selector может выше ранжировать:

```text
Открыть результат
Повторить сценарий
Обновить исходники
Собрать архив
```

Но это ranking/action suggestion поверх того же registry, а не отдельная архитектура.

---

# XXXV. Что делать с текущими левыми меню

## 74. Сохранить общую IA

Текущие отдельные пункты `Сценарии` и `Каскады` логичны и их стоит сохранить.

Но `AtomicScenariosPanel` переименовать концептуально в `ScenariosPanel`, а `ScenarioBlocksPanel` — в `CascadesPanel`.

---

## 75. Панель сценариев

Лучше:

```text
Поиск

Недавние
Закрепленные

Банк России
  ...
Росстат
  ...
Банковская отчетность
  ...
Система
  ...
```

Группы можно сворачивать.

---

## 76. Панель каскадов

Карточка:

```text
Обновить все данные Банка России
8 сценариев
Последний запуск: сегодня, успешно
```

Подробное раскрытие — по click.

---

# XXXVI. Что не стоит делать

## 77. Антипаттерны

- Не показывать все commands в основной навигации — интерфейс быстро превратится в IDE/админку.
- Не делать один giant ScenarioSpec для всех уровней — Scenario и Cascade имеют разные семантические роли.
- Не дедуплицировать по command_id — параметры и эффекты имеют значение.
- Не превращать background в отдельный workflow engine — Background должен запускать тот же Scenario/Cascade.
- Не прятать optimizer — plan optimization должна оставлять audit trail.
- Не делать Cascade копией списка commands — Cascade должен ссылаться на Scenario.
- Не привязывать Scenario к одному Cascade — membership many-to-many.
- Не смешивать «open file» с data workflow — это UI/platform action.
- Не разрешать AI обходить registry — AI должен пользоваться теми же contracts и permissions.

---

# XXXVII. Последовательность реализации

## 78. Этап 1 — исправить семантическую модель

1. Зафиксировать термины Command / Scenario / Cascade.
2. Отвязать automatic `OperationSpec → atomic Scenario`.
3. Убрать `atomic/composite/background/assignment` из ScenarioKind.
4. Ввести самостоятельный CascadeSpec/CascadeRegistry.
5. Перенести текущий `scenario.cbr.full_update` в Cascade.

---

## 79. Этап 2 — Command contract

1. Расширить executable spec effects metadata.
2. Ввести resource requirements.
3. Ввести idempotency/dedup/cache policy.
4. Ввести concurrency keys.
5. Ввести retry/cancellation policy.
6. Развести internal UI visibility и AI visibility.

---

## 80. Этап 3 — Planner

1. Expand Cascade → Scenario invocations.
2. Expand Scenario → Command graph.
3. Canonicalize params.
4. Resolve resources.
5. Build equivalence keys.
6. Safe in-plan dedup.
7. Build DAG.
8. Parallel groups.
9. Produce immutable ExecutionPlan.

---

## 81. Этап 4 — JobManager

Заменить single-active `ScenarioCoordinator` на platform-neutral:

```text
JobManager
ExecutionBackend
LocalExecutionBackend
```

Qt получает только bridge/signals.

Добавить queue, parallel jobs, cancel, progress и resume.

---

## 82. Этап 5 — UI

1. `ScenariosPanel`.
2. `CascadesPanel`.
3. Universal Launch Bar.
4. Ctrl+K searchable selector.
5. recent/favorites.
6. plan preview.
7. execution-plan drill-down.
8. jobs indicator.

---

## 83. Этап 6 — Background

Перевести текущий background scaffold на:

```text
AutomationSpec → Scenario/Cascade
```

с scheduler/trigger и concurrency policy.

---

## 84. Этап 7 — AI

Сначала:

```text
scenario/cascade catalog tools
plan
execute
observe
cancel
```

Затем, при необходимости:

```text
planner-level command access
ephemeral custom plans
```

---

# XXXVIII. Предлагаемые конкретные решения

## 85. Решения, которые стоит зафиксировать уже сейчас

| Вопрос | Рекомендация |
|---|---|
| Видны ли commands в основном UI? | Нет |
| Может ли Scenario содержать несколько commands? | Да, всегда |
| Может ли один Scenario входить в несколько Cascade? | Да |
| Является ли Cascade разновидностью Scenario? | Нет |
| Background — тип Scenario? | Нет |
| Assignment — тип Scenario? | Нет |
| Нужно ли строить ExecutionPlan до запуска? | Да |
| Можно ли дедуплицировать по command_id? | Нет |
| Где выполняется dedup? | Planner |
| Нужно ли сохранять dedup decisions? | Да |
| Может ли planner параллелить commands? | Да, по dependencies/policies |
| Может ли AI видеть commands? | Только отдельной capability |
| Что публиковать AppDock как actions? | Scenario/Cascade и сервисные high-level actions |
| Должен ли Android знать Qt/Windows details? | Нет |

---

# XXXIX. Референсы из внешних систем

## 86. Dagster

Dagster полезен как подтверждение двух идей:

1. зависимости удобно описывать графом, а не только последовательностью;
2. пользователь может выбирать высокоуровневый набор целей, а orchestrator строит downstream/upstream execution graph.

Strategy Box не должен копировать asset model Dagster, потому что здесь user-facing Scenario важнее asset-first модели. Но DAG planning и явные dependency edges применимы напрямую.

---

## 87. Temporal

Temporal полезен прежде всего границей:

```text
Workflow = composite logic
Activity = operation on external world
```

и строгим отношением к event history, retries, idempotency, cancellation и child workflows.

Особенно полезный вывод: reliable orchestration не превращает любой external effect в exactly-once; idempotency и dedup требуют явной идентичности и effect contract.

Strategy Box может использовать тот же принцип без внедрения Temporal как технологии.

---

## 88. VS Code / JetBrains / Raycast

Эти интерфейсы независимо сходятся к pattern:

```text
one search entry
fuzzy matching
recent
scoped categories
actions for selected item
keyboard-first path
```

Для Strategy Box это сильный аргумент в пользу Universal Launch Bar/Palette вместо увеличения числа toolbar buttons.

---

# XL. Связь с предыдущим исследованием наблюдаемости

## 89. Почему новая модель особенно хорошо стыкуется с observability

Предыдущее направление исследования требует сохранять operation context, причинность, физические логи, ошибки, active jobs, состояния, evidence и cross-user warnings на уровне узла.

Command/Scenario/Cascade модель дает естественные scopes:

```text
node
  └─ case
      └─ scenario invocation
          └─ command invocation
              └─ attempt
```

Поэтому ошибки можно агрегировать вверх без потери первичной причины.

Например:

```text
Attempt failed
  ↓
Command failed
  ↓
Scenario partial
  ↓
Cascade warning
  ↓
Node warning projection
```

Это существенно лучше одного плоского log stream.

---

# XLI. Итоговая целевая схема

## 90. Полная модель

```text
                       Operator / AI
                             │
                  ┌──────────┴──────────┐
                  │                     │
            ScenarioRegistry       CascadeRegistry
                  │                     │
                  └──────────┬──────────┘
                             │
                         Planner
                             │
                    immutable ExecutionPlan
                             │
                     ┌───────┴────────┐
                     │                │
                Resource graph    Command DAG
                     │                │
                     └───────┬────────┘
                             │
                        JobManager
                             │
                     ExecutionBackend
                             │
                  ┌──────────┴──────────┐
                  │                     │
               local                  remote
                  │                     │
                  └──────────┬──────────┘
                             │
                           Case
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
        Events              Logs             Artifacts
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                      Observability/AppDock
```

---

# XLII. Финальный вывод

Текущая Strategy Box уже подошла к правильному интерфейсному образу: оператор работает со **сценариями**, отдельно видит **каскады**, а execution history становится **кейсами** в сценарном чате. Менять эту продуктовую идею не требуется.

Изменить нужно внутреннюю семантику.

Сегодня:

```text
Operation ≈ Atomic Scenario
Composite Scenario ≈ Cascade
```

Целевая система:

```text
Command
   ↓
Scenario
   ↓
Cascade
   ↓
ExecutionPlan
   ↓
Case / Job
```

Главный новый компонент — не еще одна менюшка, а **planner**.

Именно planner позволяет одному сценарию входить в разные каскады, безопасно объединять повторяющиеся commands, использовать единое подключение/ресурс, не скачивать один source дважды, параллелить независимые ветки, строить понятный progress, корректно retry/cancel/resume, давать человеку и AI одну и ту же управляемую поверхность и сохранять точный причинный/observability trail.

UI при этом может остаться очень простым:

```text
Сценарии
Каскады

+ единая нижняя Launch Bar
+ search palette
+ параметры/план в inspector
+ commands только в technical drill-down
```

Это дает правильный баланс между простотой пользовательского интерфейса и достаточно мощным orchestration engine под ним.

---

# XLIII. Использованные материалы

## Внутренние материалы проекта

- `stratbox_base_study_current_state_2026-10-06.md`
- `stratbox-windows_current_state_full_research_2026-10-06.md`
- `AppDock — Базовое описание.docx`
- предыдущее исследовательское направление по AppDock/Strategy Box observability
- актуальный `main` репозитория `ForestTiger-GH/stratbox-windows`, повторно проверенный 2026-10-07: operation catalog models/registry; scenario models/registry/runner; runtime bootstrap; Qt ScenarioCoordinator; ModeRail; Scenarios/Cascades panels; BottomScenarioComposer; right inspector; case models.

## Внешняя сверка

Актуальные на 2026-10-07 официальные материалы:

- Dagster Docs — asset dependencies, DAG/selection и execution UI;
- Temporal Documentation — Tasks, Activities, Workflows, Child Workflows, retries/idempotency/cancellation;
- Visual Studio Code Documentation — Command Palette / Quick Open;
- JetBrains IntelliJ IDEA Documentation — Search Everywhere / Run Anything;
- Raycast Manual — Root Search, Search Bar, Action Panel, Quicklinks.

Внешние системы использованы как сравнительные паттерны, а не как готовая архитектура для копирования.
