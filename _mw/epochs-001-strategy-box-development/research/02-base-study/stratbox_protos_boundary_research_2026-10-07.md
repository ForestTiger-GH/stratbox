# Strategy Box ↔ PROTOS: граница архитектуры, runtime, design и когнитивно-компилируемых бизнес-возможностей

**Дата:** 2026-10-07  
**Статус:** исследовательский материал второй ветки Strategy Box; архитектурное предложение, не изменение репозиториев  
**Предмет:** как развивать Strategy Box как самостоятельный продукт, полностью совместимый с будущим PROTOS, не реализуя внутри Strategy Box части PROTOS раньше времени и не смешивая семантическое владение двух проектов.

---

# 0. Executive conclusion

Исходная интуиция в значительной части верна, но её нужно разрезать на несколько разных утверждений.

Да, значительная часть бизнес-логики `stratbox` может рассматриваться с точки зрения PROTOS как **материализованная или скомпилированная когнитивная способность**: то, что при первом решении новой задачи могло бы быть найдено сильным когнитивным контуром с участием LLM, а после стабилизации — превращено в точную процедуру, код, правило, таблицу, конечный автомат, специализированный solver или другой дешёвый fast path.

Но отсюда **не следует**, что этот код является частью самого PROTOS runtime.

Это разные вещи:

```text
PROTOS architecture/runtime
    организует cognition, Work, solver selection, learning,
    evidence, Authority, resource adaptation, compilation

Strategy Box domain capability
    знает, что такое конкретная банковская/макроэкономическая операция,
    источник, показатель, форма, валидация, преобразование и артефакт

compiled cognitive artifact / fast path
    может быть создан PROTOS
    и затем исполняться внутри Strategy Box или вызываться PROTOS
```

Самое важное различие:

> **Происхождение реализации, семантическое владение и runtime исполнения — три независимые оси.**

PROTOS может когда-нибудь **синтезировать** функцию для Strategy Box. Это не делает семантическим владельцем функции PROTOS. Если функция реализует правила формы Банка России, банковскую нормализацию, восстановление показателей, формирование конкретной аналитической витрины или другую предметную способность Strategy Box, её доменным владельцем остаётся Strategy Box.

Поэтому целевая архитектура должна строиться вокруг следующей формулы:

> **Strategy Box — самостоятельный детерминированный domain/product host. PROTOS — опционально подключаемая когнитивная система, которая может наблюдать Strategy Box, выбирать и компоновать его способности, рассуждать там, где требуется неопределённость, и со временем предлагать новые способности.**

Strategy Box должен быть полностью работоспособен:

- без PROTOS;
- без LLM;
- без когнитивной памяти PROTOS;
- без learning plane PROTOS;
- без PROTOS UI;
- без PROTOS scheduler/controller.

При подключении PROTOS продукт должен получить **дополнительного интеллектуального участника**, а не новый фундамент, без которого перестаёт работать базовая система.

Главная практическая рекомендация:

> **Готовить Strategy Box к PROTOS надо не реализацией PROTOS внутри Strategy Box, а максимально чистой, типизированной, наблюдаемой и управляемой внешней границей Strategy Box.**

То есть сделать Strategy Box хорошим **host world / capability domain**, а не ранней копией cognitive operating system.

---

# 1. Почему путаница закономерно возникла

Свежие исследования `stratbox`, `stratbox-windows` и исследования PROTOS сходятся на похожей лексике.

В `stratbox` уже естественно возникают:

- typed Request/Result;
- operation contracts;
- source descriptors;
- canonical data;
- provenance;
- validation;
- deterministic transformations;
- specialized optimization/solver logic;
- registries;
- runtime providers;
- structured diagnostics;
- artifacts.

В `stratbox-windows` возникают:

- operation registry;
- scenarios;
- cases;
- jobs;
- events;
- logs;
- artifacts;
- status;
- background processes;
- assignments;
- presence;
- machine-readable forms;
- `ai_visibility`;
- runtime state;
- execution orchestration.

А PROTOS исследуется как система, в которой существуют:

- bounded Work;
- solver-independent cognitive operations;
- heterogeneous solvers;
- reusable skills;
- deterministic algorithms;
- cognitive schemas / semantic constructs;
- skill compilation;
- compiled fast paths;
- durable state;
- resource/capability routing;
- evidence;
- Authority;
- learning;
- host embedding.

Лексически это выглядит почти одинаково. Отсюда легко сделать ложный вывод:

```text
если Strategy Box имеет operations + runtime + state + artifacts,
а PROTOS тоже будет иметь operations + runtime + state + artifacts,
значит Strategy Box строит PROTOS.
```

Но одинаковая **форма механизма** ещё не означает одинакового **семантического владельца**.

Операционная система имеет scheduler, база данных имеет scheduler, GUI framework имеет scheduler, workflow engine имеет scheduler. Это четыре разных scheduler с разной областью ответственности.

То же самое здесь:

```text
Strategy Box runtime
    lifecycle конкретного продукта и его операций

PROTOS runtime
    lifecycle когнитивной работы и cognitive execution

AppDock runtime
    lifecycle установленного мира/узла/процесса/среды
```

Путаницу создаёт именно перегруженное слово **runtime**.

---

# 2. Три независимые оси: кто создал, кто владеет, кто исполняет

Для дальнейшей архитектуры полезно формально разделить три вопроса.

## 2.1. Provenance / generation — кто создал реализацию

Код может быть создан:

- человеком;
- человеком с LLM;
- PROTOS;
- другим агентом;
- генератором;
- компилятором;
- комбинацией методов.

Это история происхождения. Она важна для provenance, assurance и обучения, но **не определяет semantic ownership**.

## 2.2. Semantic ownership — кто определяет правильный смысл

Например:

```text
"как интерпретировать строку формы 0409802"
"что является корректным результатом восстановления SORS"
"что означает REGN"
"какой source snapshot допустим"
"как устроен артефакт Strategy Box"
```

Это вопросы Strategy Box и его доменов.

PROTOS не должен становиться владельцем этих истин только потому, что его solver когда-нибудь помог написать код.

## 2.3. Execution ownership — кто управляет конкретным исполнением

Одна и та же способность может исполняться:

- прямо библиотекой `stratbox`;
- из `stratbox-windows`;
- из будущего web/android клиента;
- фоновым job manager;
- удалённым host;
- PROTOS;
- тестом;
- CLI;
- другим приложением.

Исполнитель выбирает **когда** вызвать capability, но это также не делает его владельцем доменной семантики.

Итого:

```text
generated by PROTOS
≠ owned by PROTOS
≠ executed inside PROTOS runtime
```

Эта формула должна стать базовым предохранителем архитектуры.

---

# 3. Насколько корректно считать бизнес-код Strategy Box когнитивными схемами

## 3.1. Сильная версия утверждения слишком широка

Фраза:

> «вся бизнес-часть `stratbox` — машинная реализация когнитивных схем»

полезна как интеллектуальная перспектива, но слишком сильна как строгая архитектурная классификация.

В `stratbox` есть несколько разных типов вещей:

```text
domain semantics
domain data models
exact invariants
source adapters
parsers
normalizers
deterministic calculations
optimization solvers
validators
artifact builders
presentation rules
infrastructure contracts
```

Некоторые из них действительно очень близки к **compiled cognition**. Другие являются обычной детерминированной частью предметного мира, которую когнитивная система использует как инструмент.

Лучше использовать более точную формулу:

> **`stratbox` является библиотекой предметных capabilities. Многие из этих capabilities могут рассматриваться PROTOS как скомпилированные/материализованные реализации устойчивых когнитивных процедур.**

## 3.2. Пример: получение официального файла

Операция:

```text
найти источник
→ скачать
→ проверить допустимость payload
→ сохранить raw
→ вернуть structured result
```

Для PROTOS это может быть capability/tool. Если задача ранее решалась человеком через браузер и рассуждение, то стабильная реализация действительно представляет **компиляцию ранее когнитивной работы** в deterministic path.

Но HTTP, checksum, cache и file IO сами по себе не являются «частями интеллекта PROTOS». Это механизмы host-системы.

## 3.3. Пример: нормализация банковских названий

Здесь связь сильнее.

```text
"ПАО Сбербанк"
"Сбер"
"Сбербанк России"
→ canonical identity
```

Когда повторяемая семантическая интерпретация стабилизируется в rules/aliases/registry, это почти идеальный пример:

```text
expensive semantic interpretation
→ stable rule set
→ deterministic lookup/normalization
```

С точки зрения PROTOS это хороший compiled skill / fast path. Но canonical bank identity принадлежит предметной модели Strategy Box.

## 3.4. Пример: SORS restoration

Подсистема содержит математическую модель, bounds, evidence, provenance, fixed-point logic, optimization, acceptance, conflicts и result ledgers.

С позиции PROTOS она выглядит как **specialized solver** с сильным Capability Envelope.

PROTOS не должен воспроизводить эту математику внутри общего cognitive runtime. Ему достаточно уметь определить:

```text
для этого класса Work существует специализированный solver Strategy Box
→ известны входы
→ известны гарантии
→ известны ограничения
→ известен результат
→ известна evidence/provenance поверхность
```

Это именно тот случай, где хороший PROTOS становится сильнее за счёт внешнего специализированного домена.

## 3.5. Пример: Excel export

Формирование workbook обычно уже находится ниже уровня cognition.

PROTOS может решить:

```text
нужен такой вид результата
```

а Strategy Box выполняет:

```text
canonical data
→ semantic workbook structure
→ style/preset
→ XLSX artifact
```

Это capability продукта. Сам Excel writer не нужно объявлять когнитивной схемой только потому, что он может быть вызван когнитивной системой.

---

# 4. «Дистилляция» или что-то другое

Слово **distillation** частично подходит, но в ML оно имеет более узкое техническое значение.

## 4.1. Где «дистилляция» точна

Если большая модель или сложная система выступает teacher, а её поведение используется для обучения:

- маленькой модели;
- classifier;
- reranker;
- compact neural policy;

то это действительно **knowledge distillation**.

## 4.2. Где лучше другое слово

Если повторяемое рассуждение превращается в:

- Python function;
- SQL;
- rule;
- lookup table;
- FSM;
- graph relation;
- validator;
- deterministic pipeline;
- materialized cache;
- decision table;

то точнее говорить:

- **skill compilation**;
- **cognitive compilation**;
- **cognitive lowering**;
- **materialization**;
- **specialization**;
- **program synthesis**;
- иногда — **partial evaluation**.

Для Strategy Box особенно удачны два выражения:

> **compiled domain capability**

и

> **materialized cognitive procedure**.

## 4.3. «Сигнал → обработка → ответ» недостаточно

Предельно дешёвая процедура должна хранить больше, чем три шага.

Безопасная материализация выглядит скорее так:

```text
identity
input contract
applicability / preconditions
version
source/registry dependencies
transformation
invariants
postconditions
output contract
failure semantics
provenance
validity envelope
tests
fallback / deoptimization path
```

Ключевой вопрос:

> «При каких условиях система обязана перестать доверять этому fast path и вернуться к более общей cognition?»

Для статистических источников, схем отчётности и регуляторных данных это особенно важно: semantics и source schemas меняются со временем.


# 5. Главный вывод по runtime: термин смешал три разных системы

## 5.1. AppDock runtime

AppDock владеет:

- установкой;
- узлом;
- activation;
- managed environment;
- process/lifecycle;
- health;
- system storage;
- remote/host lifecycle;
- product packaging;
- recovery;
- внешним безопасным доступом к действиям.

Это **operational/runtime substrate** продукта.

Strategy Box не должен дублировать этот слой.

## 5.2. Strategy Box host/application runtime

Strategy Box всё равно нужен собственный runtime в узком смысле.

Он владеет:

- созданием application context;
- запуском конкретной domain operation;
- case/job lifecycle;
- mapping параметров;
- progress;
- cancellation;
- domain errors;
- артефактами;
- локальным состоянием приложения;
- привязкой операции к workspace;
- background execution именно Strategy Box;
- projection в UI.

Это нормальный **host runtime** продукта. Он существует даже если PROTOS никогда не будет подключён.

## 5.3. PROTOS cognitive runtime

PROTOS runtime должен владеть другим уровнем:

- bounded cognitive Work;
- cognitive controller;
- выбором следующего cognitive operation;
- solver resolution;
- resource/capability routing;
- working/durable cognitive state;
- memory;
- context construction;
- evidence reasoning общего уровня;
- uncertainty handling;
- skill retrieval;
- skill compilation;
- learning lifecycle;
- model/solver management;
- escalation/deoptimization;
- generic Authority/effect reasoning;
- cognitive observability.

Это уже действительно когнитивная «операционная система».

## 5.4. Почему Strategy Box runtime не становится PROTOS runtime

Проверочный вопрос:

> Если убрать из системы PROTOS полностью, нужен ли этот механизм Strategy Box для работы пользователя?

Если да — скорее всего, это Strategy Box runtime.

Например:

```text
запустить экспорт escrow
показать progress
сохранить case
привязать XLSX artifact
показать ошибку
повторить операцию
отменить job
```

Это нужно обычному desktop-приложению без всякого ИИ. Следовательно, такой runtime не является ошибочно реализованным PROTOS.

А вот:

```text
самому понять цель пользователя
динамически декомпозировать её
выбрать среди неизвестного числа solvers
решить, достаточно ли evidence
сформировать новый reusable skill
скомпилировать его в fast path
обучить малую модель
управлять cognitive memory
```

— это уже территория PROTOS.

---

# 6. Практическое предложение: убрать перегрузку слова runtime

Проблема во многом семантическая.

## 6.1. В `stratbox`

Текущий низкоуровневый `runtime`, если его фактическая роль состоит прежде всего в разрешении environment providers, лучше концептуально называть точнее:

```text
environment
providers
composition
execution_context
```

Переименование имеет смысл только после проверки фактического состава package. Но само архитектурное правило полезно уже сейчас: **не называть runtime всё, что находится между domain и environment**.

## 6.2. В client layer

Вместо абстрактного «Strategy Box Runtime» полезнее различать:

```text
AppContext
ApplicationExecution
JobManager
ScenarioExecution
SessionState
```

или собирательно:

> **Strategy Box application runtime**.

Слово `application` сразу показывает границу.

## 6.3. Зарезервировать термин

Полезно сознательно использовать:

> **PROTOS cognitive runtime**

только для будущей когнитивной системы.

Это резко уменьшит концептуальную путаницу.

---

# 7. Workflow engine ≠ cognitive controller

Это потенциально самое опасное место будущего смешения.

## 7.1. Strategy Box workflow

```text
scenario
→ known steps
→ known parameter mapping
→ known operations
→ known error policy
→ artifacts
```

Даже если появляются:

- conditions;
- branching;
- retries;
- parallel steps;
- background schedule;
- resume;

это всё ещё обычный workflow engine, пока правила известны заранее.

Он принадлежит Strategy Box.

## 7.2. PROTOS cognition

```text
goal
→ interpret situation
→ identify uncertainty
→ choose/retrieve/create method
→ decide next cognitive operation
→ select solver
→ obtain/verify evidence
→ potentially revise plan
→ stop/escalate/learn
```

Это qualitatively другой класс управления.

## 7.3. Красная линия

Strategy Box начинает незаконно «строить PROTOS», если его workflow engine получает такие обязанности:

- универсальная goal decomposition;
- solver-independent reasoning;
- general planning across arbitrary domains;
- persistent cognitive memory;
- automatic skill creation;
- generic evidence reasoning;
- model routing;
- online learning;
- generic cognitive budget allocation;
- self-modifying method selection.

До этой линии scenario engine — нормальная часть Strategy Box.

---

# 8. Что означает `stratbox-core` с этой точки зрения

Лучше всего считать `stratbox` **domain capability core**, а не runtime.

Его основная ценность:

```text
источники
→ raw preservation
→ parsing
→ canonical semantics
→ validation
→ domain calculations / reconstruction
→ views
→ artifacts
```

Плюс нейтральные инфраструктурные contracts, без которых эти capability невозможно переносимо исполнить.

Это не cognitive OS.

Это **специализированный мир знаний и операций**, который будущий cognitive OS сможет использовать.

Самая удачная формула:

> **`stratbox` — domain capability substrate Strategy Box.**

Для обычного пользователя это бизнес-ядро. Для PROTOS это внешний специализированный capability domain. Обе интерпретации совместимы.

---

# 9. Где должен жить operation registry

Свежий анализ `stratbox` правильно предлагает со временем получить реестр канонических domain operations.

Это не PROTOS runtime.

## 9.1. Почему реестр нужен Strategy Box сам по себе

Он нужен:

- Windows-клиенту;
- web-клиенту;
- Android;
- CLI;
- background jobs;
- tests;
- automation;
- AppDock actions;
- будущему PROTOS.

Следовательно, это собственный контракт Strategy Box.

## 9.2. Что должен описывать operation descriptor

Минимально:

```text
operation_id
version
domain
semantic purpose

request_type
result_type

side_effect_class
read/write/destructive
idempotency
cancellation
retry semantics

workspace requirements
network requirements
source dependencies
registry dependencies

expected artifacts
diagnostic model
provenance support

estimated resource class
expected duration class

availability
capability requirements
```

Для PROTOS позже могут быть полезны дополнительные поля:

```text
determinism class
confidence/evidence semantics
applicability envelope
known limitations
verification mode
cost hints
```

Но Strategy Box не обязан сегодня использовать PROTOS-терминологию для собственных descriptors.

## 9.3. Главное правило

Operation registry описывает:

> **что умеет Strategy Box**

а не:

> **как PROTOS должен думать**.

---

# 10. `ScenarioSpec` и пользовательские workflows также остаются Strategy Box

PROTOS может сам компоновать operations, но это не делает заранее определённые сценарии ненужными.

Напротив, они полезны как:

- human-facing workflow;
- approved path;
- cheap deterministic path;
- repeatable automation;
- baseline;
- testable behavior;
- fallback при отсутствии AI.

Если PROTOS видит готовый сценарий:

```text
"обновить данные Банка России"
```

ему выгоднее вызвать этот проверенный workflow, чем каждый раз заново изобретать последовательность операций.

Это хорошо соответствует принципу Least Cognition.

То есть готовый `ScenarioSpec` в будущем можно рассматривать как ещё один вид reusable compiled skill. Но его продуктовый владелец остаётся Strategy Box.

---

# 11. Что делать с блоком design

Слово `design` ещё более перегружено, чем `runtime`.

Нужно разделить как минимум четыре разных смысла.

## 11.1. Product/UX design Strategy Box

Сюда относятся:

- структура интерфейса;
- scenario chat;
- режимы;
- inspector;
- navigation;
- operation forms;
- status rendering;
- mobile/desktop presentation semantics.

Это Strategy Box.

PROTOS UI когда-нибудь может выглядеть вообще иначе.

## 11.2. Artifact presentation design

Сюда относятся:

- Excel styles;
- typography;
- colors;
- chart palettes;
- document metadata;
- авторство;
- report presets;
- artifact formatting policy.

Это также Strategy Box и его extension surface.

PROTOS может выбрать preset или предложить оформление, но не должен владеть корпоративной или продуктовой визуальной политикой.

## 11.3. Realization Design

Это engineering function:

```text
semantic target
→ architecture/design commitments
→ code/runtime realization
```

Она существует в любом сложном проекте, включая Strategy Box и PROTOS. Но это не runtime subsystem.

Наличие design-документов в Strategy Box не означает, что Strategy Box реализует PROTOS.

## 11.4. Cognitive presentation / PROTOS UI

Когда будет исследован PROTOS UI, у него могут появиться универсальные поверхности:

- Work;
- evidence;
- uncertainty;
- memory;
- solver;
- Authority;
- cognitive trace;
- learning;
- capability envelope.

Их не надо заранее внедрять в Strategy Box.

Strategy Box должен показывать только то, что нужно его пользователю.

---

# 12. Не надо строить универсальный PROTOS UI внутри `stratbox-windows`

Свежий `stratbox-windows` уже естественно выращивает platform-neutral presentation semantics. Это правильно, потому что нужен будущий Android.

Но из этого нельзя делать следующий скачок:

```text
shared presentation semantics Strategy Box
→ universal PROTOS UI
```

Правильная граница:

```text
Strategy Box presentation/common
    semantic UI-модель именно Strategy Box

stratbox-windows
    desktop rendering

future stratbox-android
    mobile rendering

future PROTOS UI
    отдельный продуктовый слой PROTOS
```

Если когда-нибудь выяснится, что несколько приложений реально используют один и тот же универсальный cognitive UI contract, его можно вынести после появления доказанной общей семантики.

До этого преждевременное обобщение создаст ложную связь проектов.

---

# 13. Трёхслойная модель: AppDock — Strategy Box — PROTOS

Наиболее чистая целевая схема выглядит так:

```text
┌────────────────────────────────────────────────────────────┐
│ PROTOS                                                     │
│ cognitive Work · solver routing · memory · evidence        │
│ learning · skill compilation · resource adaptation         │
└───────────────────────┬────────────────────────────────────┘
                        │ optional cognitive integration
                        │
┌───────────────────────▼────────────────────────────────────┐
│ STRATEGY BOX                                               │
│ domain semantics · sources · operations · scenarios        │
│ validations · domain solvers · artifacts · app semantics   │
│ machine capability boundary                               │
└───────────────────────┬────────────────────────────────────┘
                        │ managed product/runtime boundary
                        │
┌───────────────────────▼────────────────────────────────────┐
│ APPDOCK                                                    │
│ install · node · activation · environment · lifecycle      │
│ host/remote · health · recovery · permissions/effects      │
└────────────────────────────────────────────────────────────┘
```

На практике UI-клиенты Strategy Box располагаются рядом с продуктовым слоем:

```text
stratbox-windows
stratbox-web
stratbox-android
```

Они не становятся PROTOS UI.

---

# 14. Матрица ownership

| Область | Strategy Box | AppDock | PROTOS |
|---|---|---|---|
| банковская/макро семантика | **владеет** | нет | использует |
| source schemas / parsing | **владеет** | нет | вызывает |
| canonical datasets | **владеет** | storage/lifecycle косвенно | использует |
| domain validation | **владеет** | нет | учитывает |
| specialized domain solver | **владеет** | исполняет среду | выбирает/вызывает |
| operation catalog | **владеет** | может публиковать action surface | discovery consumer |
| predefined scenarios | **владеет** | может запускать | может выбирать |
| cases/artifacts domain links | **владеет** | может хранить/runtime-project | наблюдает |
| UI Strategy Box | **владеет** | запускает surface | участник |
| product preferences | **владеет** | отдельные platform prefs | нет |
| installation/node/process | нет | **владеет** | наблюдает/запрашивает |
| remote host lifecycle | нет | **владеет** | использует |
| cognitive Work | нет | transport/surface возможно | **владеет** |
| generic cognitive memory | нет | storage mechanism возможно | **владеет** |
| solver routing | только локальный technical dispatch | нет | **владеет** |
| general planning | нет | нет | **владеет** |
| skill compilation | принимает результат | нет | **владеет** |
| model learning/training | нет | deployment mechanism возможно | **владеет** |
| generic evidence reasoning | нет | нет | **владеет** |
| domain evidence checks | **владеет** | нет | использует |
| generic Authority reasoning | product permissions | host grants | cognition-side policy |

Такой ownership позволяет системам сотрудничать без взаимного поглощения.


# 15. Как PROTOS должен «видеть» Strategy Box

Не как Python package tree. Не как доступ к shell. Не как возможность импортировать внутренние функции. И не как текстовое описание репозитория.

PROTOS должен видеть **machine-facing capability surface**.

Условно:

```text
discover_capabilities()
describe_capability(id)

invoke(id, request)
get_status(run_id)
cancel(run_id)

subscribe_events(run_id)
get_artifacts(run_id)
get_diagnostics(run_id)

read_product_state(scope)
```

Exact API сегодня фиксировать рано. Важнее семантика границы.

PROTOS получает:

- каталог допустимых действий;
- typed inputs;
- typed outputs;
- side-effect profile;
- статус;
- события;
- артефакты;
- ошибки;
- provenance;
- limits.

А Strategy Box сохраняет право решать:

- допустим ли request;
- валиден ли parameter;
- есть ли workspace;
- разрешён ли destructive action;
- какой domain invariant действует;
- завершилась ли операция успешно;
- какой artifact является продуктовым результатом.

---

# 16. Главный принцип будущей интеграции: host sovereignty

Самая безопасная модель:

> **PROTOS может предлагать, выбирать и инициировать работу, но Strategy Box остаётся владельцем своего мира.**

Например:

```text
PROTOS:
    "Нужно обновить историю эскроу."

Strategy Box:
    "Вот capability, вот request schema, вот availability."

PROTOS:
    invoke(...)

Strategy Box:
    validates
    executes
    records case
    produces artifacts
    emits events
```

PROTOS не должен напрямую менять внутренний runtime state, обходить operation contracts или писать во внутреннее application storage.

Это и есть **Cognitive Integration Boundary** применительно к Strategy Box.

Очень важно, что host sovereignty не означает «ИИ только советует». Если у PROTOS есть соответствующая Authority, он может инициировать реальные effects через разрешённую product boundary. Но commit эффекта всё равно проходит через владельца того состояния, которое изменяется.

---

# 17. Как должен выглядеть PROTOS-generated capability

Самая интересная часть вопроса — будущая способность PROTOS создавать новые коды.

## 17.1. Неправильная модель

```text
PROTOS придумал код
→ сразу записал его в stratbox
→ следующий run использует новый код
```

Это скрытое self-modification и сильное смешение проектов.

## 17.2. Правильная модель

```text
новая задача
→ PROTOS решает её дорогим способом
→ паттерн повторяется
→ формируется candidate reusable capability
→ synthesis / lowering
→ code/rule/FSM/small model/etc.
→ tests + applicability envelope
→ domain validation
→ security/side-effect review
→ admission
→ versioned artifact/package
→ Strategy Box discovers capability
```

То есть PROTOS может стать **фабрикой кандидатов**, но Strategy Box принимает только сертифицированный продуктовый artifact.

## 17.3. Скомпилированная способность должна уметь жить без PROTOS

Это лучший тест реальной компиляции.

Если для каждого исполнения всё равно нужен тот же большой cognitive runtime и та же дорогая reasoning path, capability фактически не был скомпилирован до автономного дешёвого пути.

Хороший compiled capability должен иметь:

```text
stable identity
versioned contract
bounded applicability
own tests
known failure semantics
provenance
revalidation triggers
```

После admission он становится обычной способностью Strategy Box, независимо от того, кто его когда-то синтезировал.

---

# 18. Куда сохранять такие способности

Не обязательно внутрь основного `stratbox`.

Есть минимум три класса.

## 18.1. Core capability

Действительно фундаментальная предметная функция, которую после review стоит принять в `stratbox`.

## 18.2. Product extension

Дополнительный generic capability pack, который устанавливается независимо.

Это естественно сочетается с будущей plugin architecture.

## 18.3. Local/private generated capability

Способность конкретного пользователя или окружения, которая живёт как отдельный versioned extension artifact.

Это особенно важно для будущего PROTOS:

```text
learned/generated
≠ automatically public/core
```

PROTOS должен уметь создать локальный capability без загрязнения upstream Strategy Box.

---

# 19. Почему plugin architecture здесь особенно полезна

Plugin boundary становится мостом между:

```text
stable public Strategy Box
и
evolving/generated capabilities
```

При этом plugin system должна владеть только extension lifecycle:

- discovery;
- identity;
- compatibility;
- capabilities;
- version;
- trust;
- failure isolation;
- enable/disable;
- retirement.

Она не должна знать, был ли plugin:

- написан человеком;
- сгенерирован AI;
- создан PROTOS;
- скачан;
- поставлен организацией.

Это provenance metadata, а не основа plugin semantics.

Таким образом будущий PROTOS-generated code сможет войти в Strategy Box тем же путём, что и обычное расширение.

Это архитектурно гораздо чище, чем делать специальный `protos_generated/` внутри core.

---

# 20. Что Strategy Box обязан построить сам, даже если PROTOS появится завтра

## 20.1. Typed domain operations

Без них продукт сам неполноценен.

## 20.2. Deterministic operation executor

Кто-то должен реально вызвать domain code и вернуть результат.

## 20.3. Product job lifecycle

Нужны как минимум:

```text
prepared
running
completed
failed
cancelled
```

плюс progress и, где semantics это допускает, retry/resume.

## 20.4. Cancellation и error semantics

PROTOS не должен компенсировать плохой локальный runtime.

## 20.5. Artifact model

Файлы и результаты — часть Strategy Box.

## 20.6. Provenance domain level

Источник, версии справочников, параметры, hashes и прочее принадлежат продукту.

## 20.7. Structured diagnostics

PROTOS сможет использовать diagnostics только если они уже существуют как нормальный продуктовый contract.

## 20.8. Health/readiness

Это необходимо пользователю, AppDock и внешнему cognitive consumer.

## 20.9. Scenario engine

Предопределённые проверенные workflows должны работать без AI.

## 20.10. Background execution для продуктовых задач

Проверка обновлений данных или scheduled export — обычная продуктовая автоматизация.

## 20.11. Machine-readable capability discovery

Это полезно не только PROTOS, но и всем клиентам.

## 20.12. Stable host boundary

Это самое важное условие будущего подключения PROTOS.

---

# 21. Что Strategy Box не должен строить ради будущего PROTOS

Здесь нужно проводить жёсткую границу.

Не следует добавлять в Strategy Box:

- универсальный cognitive controller;
- general-purpose planner;
- universal semantic router;
- generic long-term AI memory;
- generic episodic/procedural cognitive memory;
- model registry как cognitive solver fabric;
- universal model selection;
- generic prompt compiler;
- universal cognitive schema resolver;
- automatic skill compiler;
- training/finetuning lifecycle;
- generic self-improvement loop;
- generic epistemic engine;
- universal uncertainty controller;
- cross-domain Work kernel;
- generic multi-agent coordinator;
- universal PROTOS UI;
- global cognitive scheduler;
- model-size/resource cognition governor.

Если такая функция нужна **только потому, что PROTOS когда-нибудь будет существовать**, её сейчас не надо реализовывать в Strategy Box.

---

# 22. Пять тестов для каждого нового крупного механизма

Перед добавлением архитектурной функции полезно прогонять её через пять вопросов.

## Test A — product necessity

> Нужна ли эта функция Strategy Box пользователю без PROTOS?

Если да — сильный аргумент, что она принадлежит продукту.

## Test B — domain ownership

> Содержит ли функция банковскую, макроэкономическую, source, validation или artifact semantics Strategy Box?

Если да — Strategy Box является владельцем.

## Test C — generic cognition

> Имеет ли функция тот же смысл для произвольного другого продукта без изменений?

Если да, надо проверить, не строим ли мы PROTOS или другую общую платформу.

## Test D — host lifecycle

> Это про install, node, process, remote, environment, recovery?

Вероятный владелец — AppDock.

## Test E — cognitive adaptation

> Это про reasoning, solver selection, cognitive memory, learning или compilation нового навыка?

Вероятный владелец — PROTOS.

---

# 23. Где именно проходит граница для текущего `stratbox-windows`

## 23.1. Оставить и развивать

```text
application/
    operations
    scenarios
    orchestration/execution
    jobs
    cases
    artifacts
    assignments
    presence semantics
    workspace

presentation/common/
    Strategy Box view models

adapters/
    AppDock
    desktop host
    persistence
```

Это product/client architecture.

## 23.2. Особенно важно довести

- Qt-free application orchestration;
- JobManager;
- cooperative cancellation;
- background execution;
- atomic persistence;
- common client semantics;
- modular operation providers;
- artifact lineage;
- machine-readable actions.

Всё это требуется Strategy Box независимо от PROTOS.

## 23.3. Не расширять в сторону

```text
application/cognition/
application/general_agent/
application/learning/
application/semantic_memory/
application/solver_router/
```

Такие каталоги были бы сильным предупреждением об утечке PROTOS внутрь клиента.

---

# 24. Что делать с AI actor, который уже заложен в UI

Текущая модель `actor_kind='ai'` полезна.

Но она должна означать:

> «событие или действие совершено внешним или локальным AI actor»

а не:

> «`stratbox-windows` сам является cognitive runtime».

AI actor может быть:

- PROTOS;
- простым LLM assistant;
- автоматизацией;
- внешним агентом.

UI должен знать только:

```text
actor identity
actor kind
authorized action
event
result
```

Это сохраняет независимость.

---

# 25. PROTOS должен подключаться сбоку, а не находиться под `stratbox`

Хорошая логическая топология:

```text
Strategy Box process/API
        ↕
neutral integration boundary
        ↕
PROTOS adapter
        ↕
PROTOS runtime
```

Варианты deployment:

```text
same process
local sidecar
local shared daemon
remote service
AppDock-managed node
```

Но physical placement не должна менять смысл.

Самый вероятный безопасный первый профиль — **host-attached sidecar или отдельный local service**, потому что:

- Strategy Box не получает model/runtime dependencies;
- PROTOS обновляется независимо;
- resources изолируются;
- можно отключить PROTOS без поломки продукта;
- легче управлять permissions;
- Windows, web и Android потенциально могут обращаться к одному cognitive service.

Однако фиксировать deployment сейчас рано. Нужен прежде всего стабильный logical contract.

---

# 26. Где должен жить будущий адаптер

Самое чистое направление:

```text
Strategy Box
    ничего не импортирует из PROTOS

PROTOS
    имеет adapter/provider для Strategy Box
```

То есть dependency arrow:

```text
PROTOS adapter → Strategy Box public machine API
```

а не:

```text
Strategy Box → PROTOS package
```

Это гарантирует реальную независимость проектов.

Если понадобится отдельный integration package, условная форма:

```text
protos-stratbox-adapter
```

логически ближе к PROTOS integration ecosystem, чем к `stratbox` core.

Strategy Box со своей стороны предоставляет только нейтральный host contract.

---

# 27. Возможная нейтральная machine API Strategy Box

Это не финальная спецификация, а целевая форма.

## Discovery

```text
list_operations
get_operation_descriptor

list_scenarios
get_scenario_descriptor

list_artifact_kinds
get_product_capabilities
```

## Execution

```text
prepare
invoke
cancel
retry
resume
```

## Observation

```text
get_case
get_job
get_progress
subscribe_events
get_logs
get_diagnostics
get_artifacts
```

## State

```text
get_workspace_state
get_source_state
get_health
```

Product-specific destructive действия должны проходить собственные проверки Strategy Box. AppDock при этом может оставаться внешним владельцем более широких environment grants/permissions.

---

# 28. Как PROTOS использует эту границу

Условный цикл:

```text
User goal
    ↓
PROTOS Work
    ↓
capability discovery
    ↓
"Strategy Box умеет X, Y, Z"
    ↓
solver / method selection
    ↓
invoke Strategy Box operation
    ↓
structured events/results
    ↓
PROTOS evidence/update
    ↓
next cognition or stop
```

Если готовой capability нет:

```text
PROTOS reasoning
    ↓
temporary solution
    ↓
repeat / evidence of stability
    ↓
candidate compilation
    ↓
new extension candidate
    ↓
Strategy Box admission
```

Так две архитектуры стыкуются естественно.


# 29. Следствие для observability

Недавнее направление по логам, ошибкам и наблюдаемости становится ещё более правильным.

Strategy Box должен публиковать structured events не потому, что «это PROTOS runtime», а потому что хорошая внешняя наблюдаемость позволяет:

- UI показать выполнение;
- AppDock диагностировать узел;
- другому пользователю увидеть проблему;
- automation реагировать;
- PROTOS понимать состояние host world.

Один и тот же event stream может иметь несколько consumers.

Это идеальный пример reusable boundary без смешения ownership.

Особенно важно сохранять различие:

```text
domain event
application execution event
AppDock node/process event
cognitive event
```

Они могут коррелироваться одним `case_id`/`run_id`/causal chain, но не должны сливаться в одну бесформенную таблицу «событий вообще».

---

# 30. Следствие для настроек

Системные настройки Strategy Box также не должны превращаться в настройки PROTOS.

Правильное разделение:

```text
Strategy Box settings
    product behavior
    workspace
    artifacts
    presentation
    operation defaults
    notification UX
    installed extensions

AppDock settings
    environment
    node
    host
    installation
    remote
    product lifecycle

PROTOS settings
    cognitive profile
    solvers
    memory
    learning
    resource policies
    cognitive privacy/Authority
```

Если PROTOS подключён, Strategy Box может показать минимальный integration status:

```text
Cognitive system: connected
status / capabilities / last activity
```

но не обязан копировать весь PROTOS Settings UI.

---

# 31. Следствие для плагинов

Будущая generic plugin architecture Strategy Box становится одним из главных мостов к PROTOS.

Но следует разделять два типа расширения.

## 31.1. Strategy Box domain/infrastructure extension

Добавляет capability Strategy Box:

- source adapter;
- parser;
- operation;
- artifact formatter;
- style pack;
- integration adapter.

## 31.2. PROTOS cognitive extension

Может добавлять:

- skill;
- solver;
- learned model;
- cognitive schema/construct;
- verifier;
- router.

Strategy Box не должен превращать свой plugin API в универсальный cognitive plugin API.

Если PROTOS-generated extension нужен Strategy Box, он должен быть упакован как **Strategy Box extension**, соблюдающий Strategy Box contract.

---

# 32. «Архитектурная начинка PROTOS» — более точная формулировка

Исходную мысль:

> бизнес-код Strategy Box с точки зрения PROTOS — архитектурная/инфраструктурная начинка PROTOS

лучше уточнить.

Точнее:

> **Бизнес-код Strategy Box может стать частью capability ecology, которой пользуется PROTOS, и часть этого кода может представлять скомпилированные cognitive artifacts. Но он не является foundational architecture/infrastructure PROTOS.**

PROTOS infrastructure — это то, что позволяет разным capabilities существовать, обнаруживаться, комбинироваться, проверяться, выбираться, обучаться и исполняться.

Strategy Box capabilities — это **содержимое/способности**, живущие поверх или рядом с этим фундаментом.

Аналогия:

```text
операционная система
≠
все программы, которые на ней работают

но
программы являются частью экосистемы возможностей ОС
```

PROTOS как cognitive operating environment может использовать Strategy Box так же, как ОС использует приложения и службы, не поглощая их semantic ownership.

---

# 33. Более глубокая аналогия: PROTOS как compiler + runtime + learning system, Strategy Box как domain library

Условно:

```text
PROTOS
    cognitive compiler
    cognitive runtime
    solver fabric
    learning plane

Strategy Box
    domain standard library
    domain specialized solvers
    domain I/O
    domain artifacts
```

Но даже эта аналогия неполна, потому что Strategy Box одновременно остаётся полноценным standalone application.

Поэтому лучше:

```text
Strategy Box = самостоятельный продукт
               + externally addressable capability domain
```

Это двойная идентичность, и она полезна.

---

# 34. Стратегически важное правило: same shape ≠ same owner

Strategy Box и PROTOS оба могут иметь:

- Work-like entities;
- status;
- events;
- jobs;
- operations;
- artifacts;
- registries;
- diagnostics;
- plugins;
- runtime;
- state.

Нельзя автоматически объединять их.

Пример:

```text
PROTOS Work
    "подготовить анализ ликвидности банка"

может вызвать

Strategy Box Scenario
    "обновить набор форм"

который создаёт

Strategy Box Job
    "скачать 101"

который AppDock запускает
в конкретном managed process.
```

Здесь одновременно существуют четыре lifecycle:

```text
cognitive Work
product Scenario/Case
technical Job/Operation
process/node lifecycle
```

Попытка слить их в один `runtime object` сделает архитектуру хуже.

---

# 35. Что в свежем `stratbox` особенно хорошо соответствует будущему PROTOS

## 35.1. Request → Result

Это позволяет PROTOS обращаться к capability без знания внутренней функции.

## 35.2. Stable IDs

Это будущие anchors для capability discovery.

## 35.3. Canonical data раньше presentation

Это позволяет cognition работать с семантическим результатом, а не Excel.

## 35.4. Structured errors

AI может понять failure class и корректно решить, повторять ли действие, менять параметры или эскалировать.

## 35.5. Provenance

PROTOS получает evidence-rich result вместо непрозрачного файла.

## 35.6. Source snapshots

Cognition может рассуждать о freshness и изменениях источника.

## 35.7. Domain validation

Generic cognition не обязана заново проверять специальные предметные правила.

## 35.8. Artifact-first result

Результат становится наблюдаемым продуктовым объектом.

## 35.9. Extension boundaries

Future generated capabilities можно подключать без изменения core.

---

# 36. Что в свежем `stratbox-windows` особенно хорошо соответствует будущему PROTOS

## 36.1. Scenario-first UX

PROTOS сможет выбирать высокоуровневые capabilities, а пользователь — понимать те же сущности.

## 36.2. Machine-readable parameter specs

AI может строить корректный request вместо имитации UI clicks.

## 36.3. Case/event/log/artifact linkage

Это почти готовая observation surface.

## 36.4. `ai_visibility`

Есть естественная точка контроля: какие capabilities вообще можно показывать AI.

## 36.5. Actor kinds

Можно представить внешнего cognitive actor, не встраивая его внутрь UI.

## 36.6. Runtime state projection

PROTOS может получать bounded snapshot текущего состояния.

## 36.7. Execution backend abstraction как естественный следующий шаг

Local/remote execution остаётся продуктовой инфраструктурой и хорошо отделяется от cognitive decision.

---

# 37. Что следует пересмотреть в архитектурных исследованиях Strategy Box

## 37.1. Не называть generic application runtime «ядром PROTOS»

Это создаст ложное ownership.

## 37.2. Не переносить operations/scenarios в PROTOS

Они принадлежат Strategy Box; PROTOS их discovers/uses.

## 37.3. Не проектировать общий design layer как будущий PROTOS UI

Shared Strategy Box presentation нужен для Windows/Android.

## 37.4. Не строить cognition ради machine-readability

Machine-readable API — это просто хороший API.

## 37.5. Отдельно ввести понятие future cognitive integration boundary

Пока как архитектурный контракт, без зависимости от PROTOS.

---

# 38. Предлагаемый target для `stratbox`

```text
stratbox
│
├─ base / infrastructure contracts
│   ├─ filestore
│   ├─ net
│   ├─ io
│   ├─ environment/providers
│   └─ diagnostics
│
├─ sources
├─ registries
├─ domains
│   └─ macrobanks
│
├─ operations
│   ├─ contracts
│   ├─ descriptors
│   └─ registry
│
├─ provenance
├─ artifacts
│
└─ extensions
    └─ neutral capability discovery
```

Здесь нет:

```text
cognitive runtime
learning
LLM
agent memory
PROTOS-specific API
```

Это правильный target.

Важно: физические каталоги не нужно создавать заранее только ради красивой схемы. Материализовать их стоит по мере появления реальных owners/consumers. Здесь показана semantic target map.

---

# 39. Предлагаемый target для универсальной части клиентов Strategy Box

Пока внутри `stratbox-windows`, до появления доказанной необходимости отдельного package:

```text
application/
    operations/
    scenarios/
    execution/
    jobs/
    cases/
    artifacts/
    background/
    assignments/
    presence/
    workspace/

presentation/common/
    scenario_chat/
    forms/
    case_inspector/
    artifacts/
    jobs/
    settings/

runtime/
    app_context/
    session_state/
    bootstrap/
```

При этом `runtime` можно позднее переименовать или разнести на более конкретные owners.

Ключевое правило:

```text
никакого Qt в application/common
никакого PROTOS в application/common
```

Тогда те же semantic blocks сможет повторно использовать Android.

---

# 40. Будущий PROTOS adapter

Когда PROTOS будет достаточно материален, можно создать отдельный adapter.

Он будет маппить:

```text
Strategy Box OperationDescriptor
    ↔ PROTOS Capability/Solver description

Strategy Box Result
    ↔ PROTOS observation/evidence candidate

Strategy Box Case/Event
    ↔ PROTOS Work observation

Strategy Box destructive capability
    ↔ PROTOS effect proposal + applicable grant

Strategy Box artifact
    ↔ PROTOS external artifact/reference
```

Именно adapter должен знать обе семантики.

Ни PROTOS core, ни Strategy Box core не должны напрямую знать внутреннюю модель друг друга.

---

# 41. Три режима работы Strategy Box в будущем

## Mode 1 — Standalone

```text
human
→ Strategy Box UI
→ scenario
→ operations
→ artifacts
```

Никакого AI. Это обязательный baseline.

## Mode 2 — PROTOS-assisted

```text
human
→ PROTOS
→ existing Strategy Box capabilities
→ result
→ further cognition
```

Strategy Box остаётся неизменным host.

## Mode 3 — PROTOS-evolving

```text
human/problem
→ PROTOS discovers missing capability
→ solves
→ validates repeated pattern
→ compiles candidate
→ Strategy Box extension admission
→ future runs use deterministic capability
```

Это самый интересный долгосрочный режим.

Но он должен строиться поверх первых двух, а не вместо них.

---

# 42. Почему эта модель решает обе исходные цели

## Цель 1. Strategy Box независим, но полностью совместим с PROTOS

Решение:

- zero hard dependency;
- typed machine API;
- operation/capability registry;
- structured events;
- artifacts;
- provenance;
- stable extension model;
- external adapter.

Получается полная совместимость без зависимости.

## Цель 2. Не реализовать куски PROTOS внутри Strategy Box

Решение:

- ограничить Strategy Box product/domain responsibilities;
- не добавлять general cognition;
- отдать installation/host lifecycle AppDock;
- отдать cognitive lifecycle PROTOS;
- оставить в Strategy Box только собственный application/domain execution.

---

# 43. Самая полезная архитектурная формула

Вместо:

```text
Strategy Box сейчас вручную строит кусок будущего PROTOS runtime
```

лучше считать:

```text
Strategy Box сейчас вручную строит
собственный domain capability system,

который по счастливому совпадению
имеет правильную форму
для будущего включения в cognitive ecology PROTOS.
```

Это существенно другое утверждение.

И именно оно снимает основное противоречие.

---

# 44. Принцип «не предугадывать PROTOS»

PROTOS ещё исследуется.

Если Strategy Box начнёт копировать текущие exploratory concepts:

- schema;
- Work;
- capability;
- solver;
- Authority;
- memory;
- cognitive events;

то через несколько месяцев можно получить зависимость от устаревшей версии идей.

Лучше сделать фундаментальные свойства, полезные сами по себе:

```text
stable identities
typed contracts
explicit failures
explicit effects
versioning
provenance
observability
cancellation
capability discovery
extension isolation
state ownership
```

Любой зрелый PROTOS сможет состыковаться с такой системой.

---

# 45. Принцип «готовить к PROTOS через инженерную правильность»

Самый сильный итог исследования можно сформулировать ещё жёстче:

> **PROTOS-готовность Strategy Box почти полностью совпадает с хорошей software architecture даже без знания PROTOS.**

То есть:

- explicit ownership;
- ports/adapters;
- no hidden globals;
- typed boundaries;
- durable IDs;
- deterministic operations;
- structured errors;
- observable lifecycle;
- machine-readable capability discovery;
- permissioned effects;
- versioned extensions;
- provenance.

Если всё это есть, внешний cognitive system подключается естественно.

Если этого нет, специальный `PROTOSIntegrationManager` систему не спасёт.


# 46. Рекомендуемые архитектурные решения прямо сейчас

## P0. Зафиксировать ownership statement

В архитектуре Strategy Box стоит закрепить принцип примерно такого содержания:

> Strategy Box owns its domain and product semantics. External automation and cognitive systems may consume Strategy Box capabilities through stable machine-facing contracts but do not own Strategy Box state or domain truth.

В публичных репозиториях это можно формулировать generic-языком про external automation/AI systems, без зависимости от конкретного PROTOS.

## P0. Развести три runtime vocabulary

Явно различать:

```text
AppDock operational runtime
Strategy Box application/execution runtime
external cognitive runtime
```

## P0. Не создавать `design` как универсальный системный слой

Использовать точные названия:

- `presentation`;
- `styles`;
- `themes`;
- `artifact_formatting`;
- `realization design` в engineering documentation.

## P0. Довести core operations

Целевая минимальная форма:

```text
Request
→ Operation
→ Result
  + status
  + failures/warnings
  + metrics
  + artifacts
  + diagnostics
  + provenance
```

При этом богатые domain results не должны насильно сводиться к одному generic object.

## P1. Перенести canonical operation discovery ближе к `stratbox`

Client не должен быть единственным владельцем знания, какие domain capabilities существуют.

`stratbox-windows` должен адаптировать domain operation descriptor к своему UI, а не заново объявлять смысл операции как единственную каноническую истину.

## P1. Довести application execution

Нужны:

- JobManager;
- cancellation;
- bounded concurrency;
- retry/resume только там, где semantics определены;
- correlation/causality;
- structured result propagation.

## P1. Сделать structured event surface

Один продуктовый источник событий для:

- UI;
- logs/observability;
- AppDock projection;
- future external cognitive consumer.

## P1. Формализовать extension admission

Generated capability должен входить как обычный versioned extension, проходящий те же trust/compatibility/validation правила, что и capability, написанный человеком.

## P2. Подготовить neutral external-control contract

Без слова PROTOS в public API и без зависимости от PROTOS package.

---

# 47. Какие переименования стоит рассмотреть

Это не обязательный patch без отдельного code review, но полезная семантическая очистка.

## `stratbox.base.runtime`

Если его фактическая роль — provider/environment resolution, возможны более точные названия:

```text
base.environment
base.providers
base.composition
```

`runtime` слишком широк и невольно провоцирует текущую концептуальную путаницу.

## `stratbox_windows.runtime`

Можно оставить, если документация жёстко говорит:

> application runtime of Strategy Box client

Либо позднее разнести:

```text
app_context
session
bootstrap
state
```

## `design`

Избегать общего package `design`.

Использовать:

```text
presentation
styles
themes
artifact_formatting
```

для product-design concerns.

---

# 48. Критерий готовности Strategy Box к подключению PROTOS

PROTOS можно будет подключить без архитектурного рефакторинга, если внешний adapter сможет:

1. обнаружить domain capabilities;
2. понять typed input/output;
3. определить availability;
4. узнать side-effect class;
5. безопасно вызвать operation/scenario;
6. получить case/job identity;
7. наблюдать progress/events;
8. получить structured failure;
9. отменить там, где cancellation поддерживается;
10. получить artifact;
11. получить provenance;
12. увидеть health/readiness;
13. работать без прямого доступа к внутренним файлам состояния;
14. не обходить AppDock/product Authority boundaries;
15. отключиться без нарушения standalone работы Strategy Box.

Если это выполняется — совместимость практически достигнута независимо от конкретной внутренней архитектуры будущего PROTOS.

---

# 49. Критерий того, что Strategy Box начал слишком далеко заходить в PROTOS

Архитектуру надо остановить и пересмотреть, если в Strategy Box появляется один из симптомов:

- universal `CognitiveController`;
- persistent AI memory общего назначения;
- automatic solver selection между LLM/model/code/human;
- generic learned skill lifecycle;
- training artifacts;
- general cognitive Work;
- cross-domain reasoning planner;
- self-generated reusable skills без product admission;
- generic evidence engine;
- resource-aware cognition scheduler;
- PROTOS-specific concepts становятся обязательны для обычного run;
- Strategy Box перестаёт полноценно работать без AI runtime.

Это явные boundary alarms.

---

# 50. Отдельный вопрос: может ли Strategy Box сам эволюционировать без PROTOS

Да, и это важная проверка независимости.

Strategy Box может получать новые функции через обычный software lifecycle:

```text
research
→ domain design
→ implementation
→ tests
→ release
```

Позднее PROTOS добавит альтернативный upstream path:

```text
observed repeated cognitive work
→ candidate skill
→ compilation
→ evaluation
→ product admission
→ release/extension
```

Оба пути сходятся **до product admission**, а после admission исполнителю всё равно, кто был автором capability.

Это архитектурно сильнее любой специальной AI-generated ветки исполнения.

---

# 51. Отдельный вопрос: должен ли runtime Strategy Box быть «частью огромного runtime PROTOS»

На уровне физической реализации — нет необходимости.

На уровне будущей экологии PROTOS может включать Strategy Box application runtime как **external execution substrate**, примерно так же как он может использовать:

- SQL engine;
- browser;
- optimization solver;
- local application;
- AppDock node;
- human specialist.

Но это composition relationship, а не repository ownership.

Более точная формула:

```text
PROTOS cognitive runtime
    orchestrates / reasons over

Strategy Box application runtime
    executes Strategy Box product work
```

Ни один из них не обязан физически содержать другой.

---

# 52. Отдельный вопрос: может ли PROTOS когда-нибудь заменить часть Strategy Box runtime

Технически — возможно, но это не должно быть целью текущей архитектуры.

Например, будущий PROTOS может иметь универсальный job/work substrate, достаточно зрелый для исполнения некоторых Strategy Box scenarios. Но даже тогда решение о migration должно приниматься по фактической выгоде:

- уменьшается ли дублирование;
- сохраняется ли standalone mode;
- не появляется ли hard dependency;
- сохраняются ли domain lifecycle semantics;
- не размывается ли ownership;
- есть ли реальные другие consumers общего механизма.

До появления такого готового PROTOS runtime копировать его предполагаемую форму бессмысленно.

И даже после появления возможен лучший вариант: оставить локальный Strategy Box executor как автономный профиль, а PROTOS использовать как внешний orchestrator.

---

# 53. Важное следствие для Android и web

Будущие клиенты усиливают правильность предложенной границы.

Если operations/scenarios/cases/artifacts являются Strategy Box semantics, то:

```text
Windows
Web
Android
PROTOS adapter
CLI
```

становятся разными consumers одной и той же product capability model.

Тогда Windows больше не является владельцем универсального client runtime, а становится первой реализацией product surface.

При этом PROTOS также не становится владельцем этой модели: он ещё один consumer с особой когнитивной ролью.

---

# 54. Recommended target dependency geometry

```text
                        ┌──────────────────┐
                        │      PROTOS      │
                        │ cognitive system │
                        └────────┬─────────┘
                                 │
                         optional adapter
                                 │
                                 ▼
┌───────────────┐       ┌──────────────────┐       ┌───────────────┐
│ Windows UI    │──────▶│  Strategy Box    │◀──────│ Android UI    │
└───────────────┘       │ product contracts │       └───────────────┘
                        │ + domain core      │
┌───────────────┐       └────────┬─────────┘       ┌───────────────┐
│ Web / CLI     │───────────────▶│◀───────────────│ automation    │
└───────────────┘                │                 └───────────────┘
                                 │
                           environment / node
                                 │
                                 ▼
                        ┌──────────────────┐
                        │     AppDock      │
                        └──────────────────┘
```

Dependency principle:

```text
clients depend on Strategy Box contracts
PROTOS adapter depends on Strategy Box contracts
Strategy Box does not depend on clients
Strategy Box does not depend on PROTOS
product integration depends on AppDock contracts where required
```

---

# 55. Semantic invariants, которые стоит сохранить независимо от реализации

## Invariant 1 — standalone completeness

Strategy Box выполняет весь свой declared product scope без PROTOS.

## Invariant 2 — domain sovereignty

Банковская/макроэкономическая истина, domain validation и product artifact semantics принадлежат Strategy Box.

## Invariant 3 — external cognition is bounded

AI видит только опубликованные capabilities/state surfaces.

## Invariant 4 — effects have owners

Никакой cognitive confidence не заменяет product/host permission и validation.

## Invariant 5 — generated code is candidate before admission

Происхождение от PROTOS не даёт автоматического trust.

## Invariant 6 — compiled skill can deopt

При нарушении applicability/freshness/validity fast path должен отказать или потребовать более общий путь, а не молча продолжать.

## Invariant 7 — AppDock is not duplicated

Installation/node/process/remote/recovery semantics остаются снаружи Strategy Box.

## Invariant 8 — UI semantics stay product-specific

Shared Windows/Android presentation не становится universal cognitive UI по умолчанию.

## Invariant 9 — no hidden reverse dependency

Наличие PROTOS adapter не должно приводить к импорту PROTOS из `stratbox` или клиентских common layers.

## Invariant 10 — same words do not collapse lifecycles

`Work`, `job`, `scenario`, `case`, `process`, `event`, `artifact` сохраняют собственные scopes.

---

# 56. Target sequence of work

## Stage A — semantic cleanup

1. Зафиксировать ownership map Strategy Box / AppDock / external cognition.
2. Развести runtime vocabulary.
3. Уточнить `design` vocabulary.
4. Зафиксировать standalone completeness как invariant.

## Stage B — finish Strategy Box contracts

1. Нормализовать Request/Result domain operations.
2. Создать canonical operation descriptors.
3. Добавить structured failures/diagnostics/provenance.
4. Укрепить source/registry identities.
5. Довести artifact contract.

## Stage C — finish application execution

1. Qt-neutral orchestration.
2. JobManager.
3. Cancellation.
4. Background execution.
5. Bounded concurrency.
6. Atomic history/state persistence.
7. Structured event stream.

## Stage D — extension architecture

1. Generic discovery.
2. Capability identity/version.
3. Compatibility/trust.
4. Enable/disable/retirement.
5. Isolation/failure semantics.
6. Admission test suite.

## Stage E — neutral machine boundary

1. Capability discovery.
2. Invocation.
3. Observation.
4. Cancellation.
5. Artifact access.
6. Health/readiness.
7. Permission/effect boundary.

Этот этап можно спроектировать без PROTOS-specific dependency.

## Stage F — только когда PROTOS станет достаточно материальным

1. Исследовать actual PROTOS integration contract.
2. Создать отдельный adapter.
3. Сопоставить operation descriptors с PROTOS capabilities.
4. Добавить cognitive actor identity/Authority mapping.
5. Провести end-to-end assisted scenario.
6. Проверить отключение PROTOS и полный standalone fallback.

## Stage G — long-term generated capability loop

Только после появления зрелого learning/compilation lifecycle PROTOS:

```text
observe
→ propose
→ compile
→ verify
→ admit
→ deploy as extension
→ monitor validity
→ retire/recompile
```

---

# 57. Итоговая модель понятий

## Strategy Box domain capability

Устойчивая предметная способность продукта.

## Cognitive schema / construct

Семантический способ организации cognition/work, который может иметь разные реализации.

## Compiled cognitive artifact

Дешёвая materialized реализация устойчивой cognitive procedure.

## Strategy Box operation

Machine-callable domain use case.

## Strategy Box scenario

Предопределённая продуктовая композиция operations.

## Strategy Box application runtime

Исполнитель product jobs/scenarios/cases.

## PROTOS cognitive runtime

Система управления cognition, solvers, Work, memory, learning и compilation.

## AppDock runtime

Система управления установленным product world/node/environment/process lifecycle.

## Cognitive Integration Boundary

Граница, через которую PROTOS или другой cognitive actor видит Strategy Box как bounded external capability world.

---

# 58. Финальный вывод

Опасение о возможном смешении обосновано, но текущая архитектура ещё не находится в ловушке.

Наоборот, свежие исследования показывают, что Strategy Box уже складывается в форму, которая очень хорошо подходит для будущего PROTOS:

```text
typed operations
structured results
domain solvers
scenarios
events
artifacts
provenance
runtime state
extensions
AppDock boundary
```

Нужно сделать один важный интеллектуальный поворот.

Не считать:

> «мы случайно строим PROTOS внутри Strategy Box».

Считать:

> **«мы строим хороший самостоятельный domain host, который будущий PROTOS сможет использовать как богатый внешний мир возможностей».**

А бизнес-код Strategy Box можно одновременно интерпретировать на втором уровне:

> **часть его операций действительно похожа на то, во что PROTOS в зрелом состоянии мог бы компилировать повторяемую когнитивную работу.**

Эти два утверждения не противоречат друг другу.

Strategy Box владеет результатом компиляции как предметной способностью.

PROTOS владеет общим механизмом, который умеет:

- понять, когда такая способность нужна;
- найти её;
- выбрать её;
- проверить её применимость;
- использовать;
- эскалировать при выходе за validity envelope;
- со временем предложить новую.

Именно такая граница одновременно обеспечивает:

- полную независимость проектов;
- отсутствие преждевременной реализации PROTOS;
- возможность подключить PROTOS позднее;
- сохранение standalone Strategy Box;
- эффективную будущую skill compilation;
- хороший путь к Windows/Web/Android;
- чистую интеграцию с AppDock.

Если свести весь документ к одной формуле:

> **Strategy Box должен быть PROTOS-ready host, а не partial PROTOS.**

---

# 59. Источниковая база исследования

## Свежие материалы Strategy Box

### `stratbox_base_study_current_state_2026-10-06.md`

Исследование текущего `ForestTiger-GH/stratbox`, ветка `main`, исследованный commit `e968853572676d8e5d963607d1f0cb50ff8f20b7`, package `0.8.0`.

Особенно использованы выводы о:

- separation core/surface;
- domain capability character core;
- FileStore/runtime provider boundary;
- Request/Result contracts;
- operation registry;
- diagnostics/provenance;
- AppDock boundary.

### `stratbox-windows_current_state_full_research_2026-10-06.md`

Исследование `ForestTiger-GH/stratbox-windows`, `main`, HEAD `959e9c4ce1441124af5111c1e025041714e04d3b`.

Особенно использованы:

- application/runtime/presentation decomposition;
- OperationSpec/ScenarioSpec;
- execution engine;
- cases/events/logs/artifacts;
- `ai_visibility`;
- Android portability analysis;
- Qt-neutral target;
- future ExecutionBackend/AI action surface.

### `AppDock — Базовое описание.docx`

Использовано для разграничения:

- installation/node/environment ownership;
- product lifecycle;
- external app boundary;
- host/remote direction;
- bounded AI actions.

### Свежие исследования второй ветки Strategy Box

Учтены направления текущего цикла по:

- наблюдаемости, ошибкам и логам;
- будущим требованиям к generic extensions/plugins;
- системным настройкам и product surface.

Они используются как target context, но настоящий документ не делает их автоматически реализованным состоянием кода.

## PROTOS

Проверен `ForestTiger-GH/PROTOS`, ветка `main`.

Текущий HEAD на момент исследования: `3a10879625a4b5d1e9253bfe1b700229eac244a1` от 2026-09-23.

Ключевые материалы:

- `knowledge-product/target-what/TARGET-WHAT.md`;
- `_mw/epochs/002-capability-architecture-and-evolution/research/01-first-ideas/results/PROTOS_Composable_Logical_Cognitive_Schemas_Architecture_2026-09-16.md`;
- `_mw/epochs/002-capability-architecture-and-evolution/research/01-first-ideas/results/PROTOS_From_Schemas_to_Semantic_Construct_Fabric_2026-09-16.md`;
- `_mw/epochs/002-capability-architecture-and-evolution/research/01-first-ideas/results/PROTOS_Cognitive_Microexecution_Relation_Algebra_and_Compiled_Fast_Paths_2026-09-16.md`;
- `_mw/epochs/002-capability-architecture-and-evolution/research/01-first-ideas/results/PROTOS_Microcognition_Algorithmic_Fast_Paths_Scale_Invariant_Cognitive_Execution_2026-09-15.md`;
- `_mw/epochs/002-capability-architecture-and-evolution/research/01-first-ideas/results/PROTOS_Embedded_Cognitive_Systems_Host_Integration_2026-09-16.md`;
- `_mw/epochs/002-capability-architecture-and-evolution/research/01-first-ideas/results/PROTOS_Cognitive_Operating_Environment_Architecture_Infrastructure_and_Computational_Economy_2026-09-17.md`;
- `_mw/epochs/002-capability-architecture-and-evolution/research/01-first-ideas/results/PROTOS_Adaptive_Cognitive_Execution_Physiology_2026-09-23.md`;
- `knowledge-product/science/02-COMPUTE-SOLVERS-AND-SCALING.md`;
- `knowledge-product/consolidated/PROTOS-COMPLETE-KNOWLEDGE-PRODUCT.md`.

### Статус PROTOS-источников

Важное ограничение: значительная часть перечисленных файлов `research/01-first-ideas/results` прямо маркирована как research/development input, а не действующая нормативная спецификация.

Они использовались для проверки архитектурного направления: cognitive schemas, skill compilation, fast paths, host embedding, progressive execution.

`TARGET-WHAT.md` имеет более высокий статус candidate commitment surface и особенно важен здесь потому, что прямо различает:

```text
complete training-ready PROTOS
и
deterministic workflow/runtime,
который может быть PROTOS-compatible infrastructure,
но сам по себе не является полным PROTOS Product.
```

Это различие напрямую поддерживает главный вывод настоящего исследования.
