# stratbox-windows: текущее устройство, фактическая архитектура и потенциал развития

**Дата среза:** 2026-10-06  
**Репозиторий:** `ForestTiger-GH/stratbox-windows`  
**Ветка:** `main`  
**Текущий HEAD:** `959e9c4ce1441124af5111c1e025041714e04d3b`  
**Версия Python-пакета / world:** `0.1.0`  
**Метод:** статический разбор актуального дерева репозитория сверху вниз и снизу вверх, разбор manifest/runtime contracts, application/runtime/presentation слоёв, тестов и истории последних коммитов; дополнительно использовано базовое описание AppDock и официальная документация Qt for Python для оценки переносимости и Android-потенциала.

---

## 0. Краткий итог

`stratbox-windows` сейчас уже является не «тонким окном над stratbox», а отдельным application/surface-слоем Strategy Box. Он содержит собственную модель рабочего пространства, runtime-контекст, сценарии, кейсы выполнения, историю, артефакты, логи, поручения, участников, фоновые процессы как концепцию, AppDock boundary и полноценный PySide6/Qt desktop UI. При этом предметная банковская/макроэкономическая логика в целом удерживается во внешнем `stratbox`, что является правильной архитектурной границей.

Фактически продукт строится по цепочке:

```text
AppDock / standalone-dev activation
        ↓
AppDock adapter / __main__
        ↓
AppContext + paths + workspace + session state
        ↓
OperationRegistry
        ↓
ScenarioRegistry
        ↓
AppRuntime
        ↓
Qt shell
        ↓
ScenarioCoordinator → QThread → ScenarioWorker
        ↓
ScenarioRunner → OperationRunner → handler
        ↓
external stratbox core
        ↓
outputs / logs / artifacts / events / cases
        ↓
JSON history + runtime-state projection
        ↓
scenario-chat UI / inspector / workspace explorer
```

Текущий desktop UX уже достаточно оформлен. Слева есть шесть режимов: Проводник, Сценарии, Каскады, Фоновые процессы, Участники, Поручения. В центре — сценарный «чат» с фильтрами и композером запуска. Справа — инспектор кейса, логов, артефактов и параметров. Есть настройки, диагностика и экран узла.

При этом готовность разных подсистем неодинакова. Реально выполняются операции и сценарии, ведутся кейсы, логи, артефакты, локальная история, работа с workspace и AppDock runtime-state. «Фоновые процессы», presence/участники, поручения и AI actor уже существуют в модели и UI, однако пока преимущественно как локальные каркасы. Реального scheduler/daemon, сетевой синхронизации участников, полноценного collaboration backend и AI-runtime в `stratbox-windows` сейчас нет.

Наиболее важный технический вывод: архитектурное направление в целом правильное, но репозиторий находится на переходной стадии между быстро собранным рабочим desktop-прототипом и устойчивым продуктовым surface. Это видно по нескольким следам: устаревшие контрактные тесты, расхождение документации с manifest, закоммиченные `.tmp` и `.pyc`, отсутствие CI/release pipeline, частично декларативные функции без executor-части и Qt-зависимость внутри runtime bootstrap.

Для будущего `stratbox-android` текущая база уже полезна: `application` в основном отделён от Qt, сценарии и operation specs описаны декларативно, presentation semantics частично вынесены в `presentation/common`, OS-действия вынесены в adapter. Однако повторно используемое ядро surface пока недостаточно чистое: `runtime.bootstrap` создаёт Qt `ScenarioCoordinator`, а часть orchestration остаётся внутри `presentation/qt_desktop`. До Android логично довести эту границу до конца.

---

# I. Срез репозитория как артефакта

## 1. Масштаб текущего дерева

По актуальному `main`:

- всего tracked-файлов: **198**;
- общий размер tracked-файлов: примерно **1.83 МБ**;
- Python-файлов: **149**;
- объём `.py`: примерно **421 КБ**;
- SVG-ресурсов: **23**;
- QSS stylesheet: **1**, около 10 КБ;
- PNG: **1**, около 1.34 МБ;
- test-файлов: **10**, около 23.5 КБ Python-кода.

Основные Python-области по размеру:

| Область | Python-файлы | Примерный объём |
|---|---:|---:|
| `application` | 63 | 134 КБ |
| `presentation` | 52 | 159 КБ |
| `runtime` | 11 | 61 КБ |
| `adapters` | 8 | 33 КБ |
| `tests` | 10 | 23.5 КБ |
| `scripts` | 3 | 6.9 КБ |

Это важная пропорция: `stratbox-windows` уже не маленькая оболочка. Application + runtime + adapters составляют сопоставимый объём с presentation. То есть значимая часть продукта живёт между UI и core.

Большая часть физического размера репозитория приходится на `chat_history_background.png` (~1.34 МБ), поэтому общий размер не отражает объём кода.

## 2. Текущее дерево верхнего уровня

```text
stratbox-windows/
├── README.md
├── pyproject.toml
├── appdock/
│   └── manifest.json
├── docs/
│   ├── architecture.md
│   ├── development.md
│   └── appdock-integration.md
├── scripts/
│   ├── check_appdock_contract.py
│   ├── check_internal_imports.py
│   └── check_release_integrity.py
├── src/stratbox_windows/
│   ├── __main__.py
│   ├── adapters/
│   ├── application/
│   ├── presentation/
│   ├── resources/
│   └── runtime/
├── tests/
└── .tmp/                     ← сейчас ошибочно tracked
```

Внутри `src/stratbox_windows` структура уже достаточно дисциплинирована и близка к clean/hexagonal-style разделению: boundary adapters, application use cases, runtime composition, presentation semantics и конкретный desktop frontend.

---

# II. Верхнеуровневое назначение и границы

## 3. Что такое `stratbox-windows` сейчас

По README и архитектуре репозитория его заявленная роль — **Windows desktop surface Strategy Box**, запускаемый в AppDock-managed среде. `stratbox-windows` отвечает за продуктовую поверхность, а `stratbox` — за библиотечное предметное ядро.

Текущая граница в целом выглядит так:

```text
stratbox
  предметные модели, расчёты, collectors, exporters, FileStore и т. п.
        ↑
        │ Python dependency
        │
stratbox-windows
  сценарии, orchestration, runtime state, workspace UX,
  desktop UI, cases/events/artifacts/logs, AppDock surface
        ↑
        │ activation / installation / session surfaces
        │
AppDock
  productization, installation, managed runtime, node/session/data binding
```

Это правильная фундаментальная идея. Windows-репозиторий не копирует core и не держит бизнес-алгоритмы у себя. Например, desktop handler загрузчика файлов ЦБ только собирает пользовательский request и вызывает реализацию из `stratbox`.

## 4. Зависимости пакета

`pyproject.toml` требует:

- Python `>=3.10`;
- `stratbox==0.2.1`;
- `PySide6>=6.6`;
- `pytest>=8.0` в test-extra.

Пакет экспортирует console script:

```text
stratbox-windows → stratbox_windows.__main__:main
```

В AppDock graph desktop package и core package ставятся в один managed Python environment. Core должен устанавливаться раньше desktop surface.

---

# III. Запуск сверху вниз

## 5. AppDock manifest

`appdock/manifest.json` на текущем `main` имеет `contract_version = 4.0`.

Он объявляет:

- world id: `stratbox`;
- world name: `Strategy Box`;
- world version: `0.1.0`;
- default surface: `desktop`;
- entry view: `scenario_chat`;
- дополнительно объявленный view: `workspace`;
- Data profile: `data_enabled`;
- поддержка artifacts и presence;
- внешний core source;
- два Python package bindings в одном environment;
- desktop activation как `python_module`;
- foreground launch;
- local locality;
- Windows как platform constraint;
- диагностику через тот же entrypoint с `--diagnose`.

То есть manifest уже описывает `stratbox-windows` как локальную интерактивную surface AppDock, а не как самостоятельный installer/launcher.

## 6. AppDock entrypoint

Канонический AppDock entrypoint:

```text
stratbox_windows.adapters.appdock.entry
```

Он делает две вещи:

1. загружает и строго валидирует Activation Context;
2. проверяет runtime graph: наличие core и desktop Python bindings, их package IDs и общий environment.

После этого управление передаётся обычному `stratbox_windows.__main__.main(...)` с `launch_origin='appdock'`.

Очень хорошая деталь: entrypoint не модифицирует `sys.path`. Репозиторий явно ушёл от временного package-mount подхода к нормальной установке Python distributions в managed environment.

## 7. Основной `__main__`

CLI поддерживает три режима:

```text
GUI startup
--diagnose
--no-gui
```

Для development предусмотрен:

```text
--standalone-dev-root <path>
```

Обычный production startup без Activation Context запрещён. Если AppDock context отсутствует и dev-root явно не передан, приложение завершает запуск управляемой ошибкой.

Последовательность обычного запуска:

```text
parse args
↓
build_app_context
↓
build_operation_registry
↓
если diagnose/no-gui → system.diagnostics
иначе
↓
import Qt frontend
↓
run_gui(context)
```

Startup errors (`AppConfigError`, `AppError`, missing core) переводятся в управляемое сообщение и exit code 2 вместо необработанного traceback.

---

# IV. Runtime-слой

## 8. `AppContext` как центральный runtime object

`runtime/context.py` собирает единый `AppContext`, которым пользуются GUI и service commands.

Он содержит:

- filesystem paths;
- user config;
- workspace registry и выбранную schema;
- Activation Context;
- AppDock session client;
- session snapshot;
- run mode и launch origin;
- Data root selector;
- resolved workspace root;
- data/workspace status;
- degraded launch flag;
- `FileStore` из core;
- version information;
- logger;
- node/session/user/host identity;
- session state;
- user state;
- active-session projection;
- health snapshot.

Это по сути composition root уровня приложения.

## 9. Режимы запуска

Фактически доступны два режима:

```text
appdock_managed
standalone_dev
```

При этом `runtime/paths.py` содержит ещё `standalone_user_profile` и функцию построения пользовательского standalone storage, однако через текущий `build_app_context()` этот путь недостижим: `_resolve_run_contract()` разрешает только AppDock context либо `--standalone-dev-root`.

Это хороший пример «задела, который существует в коде, но сейчас не является доступной продуктовой функцией».

## 10. Runtime filesystem

Для AppDock-managed режима app-owned storage формируется поверх managed system root.

В нём создаются:

```text
app.json
logs/
logs/operations/
cache/
runtime/
runtime/history/
```

История хранит отдельные JSON-проекции:

```text
cases.json
events.json
artifacts.json
logs.json
assignments.json
```

В standalone-dev это оказывается под:

```text
<dev-root>/.stratbox_windows/system/
```

Именно такой runtime state сейчас случайно оказался tracked в `.tmp/dev-workspace/...`.

## 11. Session/runtime state

`runtime/session_runtime.py` реализует собственный client к JSON surfaces, опубликованным AppDock.

Он умеет читать:

- user state;
- session state;
- active-session projection;
- health snapshot;
- runtime state.

И обновлять runtime projection Strategy Box:

- active view;
- selected object;
- active job;
- последний operation/scenario/case;
- outputs;
- recent artifacts;
- workspace schema/root;
- selected Data root;
- clean shutdown;
- heartbeat/update timestamps.

Это уже полноценный «провод» между desktop surface и внешним управляющим runtime.

## 12. Degraded mode

Если Data root не доступен, контекст может подняться в degraded mode. AppDock preflight допускает успешную диагностику при отсутствии workspace, если degraded launch разрешён.

После запуска surface остаётся доступна, но операции, требующие workspace/FileStore, возвращают контролируемую ошибку.

Такой режим полезен архитектурно: UI и диагностика не зависят от полного наличия данных.

---

# V. Workspace и Data

## 13. Workspace schema

Встроена одна схема `default`:

```text
root_mode = derived_from_selector
workspace_dirname = "Strategy Box Data"
required_dirs = input, output
auto_create_workspace_root = true
auto_create_required_dirs = true
readonly = false
```

То есть пользователь/AppDock выбирает business/data root, а Strategy Box создаёт внутри него собственный рабочий каталог:

```text
<selector>/Strategy Box Data/
├── input/
└── output/
```

Есть отдельная логика для system drive, позволяющая использовать user profile вместо размещения workspace в корне системного диска.

## 14. Workspace resolver

Resolver различает:

- Data root selector;
- итоговый workspace root;
- status selector;
- status workspace;
- resolution mode;
- source description.

Он умеет:

- проверять существование и directory-тип;
- создавать workspace;
- создавать обязательные каталоги;
- определять доступность;
- формировать диагностическое описание.

## 15. FileStore

Если workspace доступен, через внешний core создаётся `FileStore`. Все предметные операции, требующие данных, получают его через `OperationContext`.

Это хорошая граница: UI/operation handler работает с абстракцией хранилища core, а не реализует файловую бизнес-инфраструктуру сам.

## 16. Workspace Explorer

В UI есть отдельный файловый проводник.

Текущая реализация:

- local filesystem provider;
- start root ограничен workspace;
- навигация вниз/вверх внутри workspace;
- сортировка по имени или типу;
- directories first;
- типизация файлов: Excel, CSV, JSON, text, PDF, image, archive и т. п.;
- double-click open;
- context menu;
- копирование пути;
- собственные SVG icons.

Интерфейс provider оформлен Protocol-типом (`ExplorerProvider`), но фактически существует только `LocalWorkspaceExplorerProvider`.

Это хороший extension seam для будущих AppDock/network/artifact providers.

---

# VI. Application layer снизу вверх

## 17. Operation model

Базовой атомарной единицей является `OperationSpec`.

В spec уже заложены:

- `id`, title, description;
- handler как строковая ссылка `module:function`;
- group/kind/tags/search aliases;
- enabled;
- requires workspace;
- parameter specs;
- fixed hidden values;
- icon/order/group order;
- submit label;
- repeat support;
- result preview kind;
- dangerous flag;
- visibility policy;
- stage title;
- expected artifact kinds;
- log visibility;
- `ai_visibility`.

Последний набор полей показывает, что модель операций проектируется шире текущего GUI: уже предусмотрены опасные операции, visibility-policy, типы результата и структурированная видимость для AI.

## 18. Формы параметров

`OperationParamSpec` поддерживает:

```text
text
int
bool
select
path_dir
path_file
```

Также есть:

- default;
- required;
- options;
- basic/advanced section;
- placeholder;
- min/max.

Qt parameters panel строится из этих specs, поэтому форма сценария уже частично schema-driven.

Это один из наиболее ценных элементов для будущего Android: такую декларативную schema можно рендерить любым frontend.

## 19. Реально зарегистрированные операции

На текущем `main` всего три operation specs.

### 19.1 `cbr_file_collector.collect`

Пользовательское название: **Загрузчик исходных файлов ЦБ**.

Функция:

- вызывает core collector Банка России;
- умеет сохранить ZIP либо каталог файлов;
- пользователь выбирает target directory;
- есть overwrite;
- retries и continue-on-error задаются внутри registry;
- результатом становятся основной файл/каталог и operation log.

Дефолтный каталог:

```text
<workspace>/output/cbr_file_collector
```

### 19.2 `escrow.history.export`

Пользовательское название: **История счетов эскроу**.

Функция:

- строит историю ежемесячных публикаций ЦБ;
- сохраняет XLSX либо ZIP;
- использует локальный source cache;
- поддерживает refresh;
- отдаёт подробные metadata: число источников, дат, показателей, регионов, строк и ошибок.

Дефолтный output:

```text
<workspace>/output/escrow
```

Cache:

```text
<workspace>/input/escrow_sources
```

### 19.3 `system.diagnostics`

Проверяет:

- workspace resolution;
- чтение/запись;
- обязательные каталоги;
- наличие runtime dependencies;
- импорт ключевых модулей;
- Python/version/run mode;
- node/session/user/host;
- health/session state.

Эта операция не требует workspace и используется также как AppDock preflight.

## 20. Operation registry сейчас hardcoded

Все operations перечислены непосредственно в `build_operation_registry()`.

Для трёх функций это удобно. При десятках банковских и макроопераций такой подход станет центральным bottleneck:

- один большой registry-файл;
- ручное импортное знание обо всех формах;
- ручная регистрация handler refs;
- сложнее modular ownership и extension packs.

По мере роста логично перейти к декларативным descriptors либо модульным registry providers, сохранив единый итоговый `OperationRegistry`.

---

# VII. Scenario layer

## 21. Atomic scenarios

Каждая enabled operation автоматически превращается в atomic scenario:

```text
scenario.atomic.<operation_id>
```

То есть operation — внутренняя атомарная единица, а scenario — пользовательская рабочая единица.

Это сильное решение: UI не обязан объяснять пользователю техническую модель handler/operation.

## 22. Composite scenarios

Кроме atomic scenarios зарегистрирован один настоящий composite:

### `scenario.cbr.full_update` — «Обновление данных Банка России»

Он состоит из двух последовательных шагов:

1. загрузка исходных файлов ЦБ;
2. построение истории счетов эскроу.

Scenario имеет собственную user-facing форму и через `params_map` раскладывает параметры по операциям.

Это уже основа workflow engine, пусть пока минимального.

## 23. Модель сценария

`ScenarioSpec` поддерживает:

- kinds: `atomic`, `composite`, `background`, `assignment`;
- список steps;
- params;
- error policy;
- repeat;
- `supports_background`;
- visibility policy;
- expected artifacts.

Фактически сейчас registry генерирует atomic + один composite. `background` и `assignment` как scenario kinds пока являются возможностью модели, а не полноценными пользовательскими сценариями.

---

# VIII. Execution engine

## 24. Scenario execution

`run_scenario()`:

1. переводит case в `running`;
2. публикует `case_started` event;
3. идёт по steps по порядку;
4. для каждого step создаёт `step_started`;
5. маппит scenario params → operation params;
6. вызывает `run_operation()`;
7. создаёт LogRecord;
8. превращает output paths в ArtifactRecord;
9. публикует step success/failure event;
10. применяет fail-fast policy;
11. завершает case;
12. публикует финальный event.

С точки зрения архитектуры это уже небольшой последовательный workflow runner.

## 25. Operation execution

`run_operation()`:

- разрешает параметры;
- создаёт отдельный file logger;
- строит `OperationContext`;
- проверяет наличие workspace;
- динамически импортирует handler;
- нормализует result;
- перехватывает exception;
- возвращает `OperationResult` вместо выброса ошибки в GUI.

Operation log naming связывает:

```text
case + step + operation
```

Это удобно для воспроизводимости.

## 26. Асинхронность GUI

Долгий scenario запускается через Qt `QThread`:

```text
ScenarioCoordinator
    ↓
QThread
    ↓
ScenarioWorker
    ↓
run_scenario(...)
```

GUI получает signals:

- case_updated;
- event_appended;
- artifacts_created;
- log_created;
- finished.

Тем самым тяжёлая работа не блокирует Qt event loop.

## 27. Ограничение: один активный scenario

`ScenarioCoordinator` допускает только один одновременный run. Если сценарий уже идёт, новый не принимается.

Это осознанно простой executor, но в будущем для фоновых обновлений, очередей, remote host и нескольких независимых задач потребуется job manager.

## 28. Cancellation пока отсутствует

Case model содержит `cancelled`, однако coordinator/worker не имеют cancellation token, interrupt request или cooperative cancellation API.

То есть status предусмотрен, а реальный cancel path пока отсутствует.

---

# IX. Кейсы, события, логи и артефакты

## 29. Case как центральный пользовательский объект

`ScenarioRunCase` хранит:

- case id;
- scenario id/title;
- params;
- status;
- author;
- timestamps;
- current stage;
- список step runs;
- outputs;
- message;
- unread.

Это хорошая модель для «сценарного чата»: один запуск превращается в независимую сущность с жизненным циклом.

## 30. Events

Поддерживаются события:

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

Actor kinds:

```text
user
host_user
ai
system
background
```

Наличие `ai` и `host_user` сегодня следует воспринимать как semantic readiness. Реального AI или multi-host interaction layer в этом репозитории пока нет.

## 31. Artifacts

Artifact metadata хранит:

- id;
- name/path;
- kind;
- author;
- scenario/case/operation linkage;
- log linkage;
- timestamp.

Типы:

```text
file, folder, excel, zip, log, report, dataset, unknown
```

Реальный kind определяется в основном по path/suffix.

## 32. Logs

Есть два уровня:

- application log;
- per-operation file log.

Operation log затем оформляется как LogRecord и связывается с case/scenario/operation/step.

## 33. Persistence

`HistoryPersistenceService` сохраняет последние проекции в пять JSON-файлов.

Плюсы:

- просто;
- прозрачно;
- легко отлаживать;
- подходит для ранней desktop-версии.

Ограничения:

- запись не атомарна через temp+replace;
- нет locking;
- нет schema version у history files;
- повреждённый JSON тихо превращается в пустую историю;
- нет transactional consistency между пятью файлами;
- нет ограничения размера/history retention.

Поэтому этот storage годится как «recent local context», что прямо соответствует docstring, но его не стоит превращать в долгосрочную event database без отдельного redesign.

---

# X. UI: фактическая поверхность

## 34. Общая композиция окна

Главное окно состоит из трёх зон:

```text
┌──────────────────┬──────────────────────────────┬──────────────────┐
│ Mode rail +      │ Top filters                 │ Right inspector  │
│ Left panel       │                              │                  │
│                  │ Scenario chat               │ Case             │
│                  │                              │ Logs             │
│                  │ Background strip            │ Artifacts        │
│                  │                              │ Parameters       │
│                  │ Bottom scenario composer     │                  │
└──────────────────┴──────────────────────────────┴──────────────────┘
```

Right drawer анимируется и хранит open/tab state.

## 35. Mode rail

Шесть режимов:

1. **Проводник** — workspace files;
2. **Сценарии** — atomic scenarios;
3. **Каскады** — composite scenario blocks;
4. **Фоновые** — background processes;
5. **Участники** — presence;
6. **Поручения** — assignments.

Это уже продуктовая IA, которая масштабируется гораздо дальше текущих двух бизнес-операций.

## 36. Центральный scenario chat

Центр отображает:

- scenario cases;
- системные уведомления;
- background notices;
- assignment notices;
- artifacts внутри case cards;
- текущий stage/status;
- параметры;
- автора;
- время.

Фильтры:

```text
Все
Мои
В работе
Успешные
Ошибки
Непрочитанные
```

Projector специально отделён в `presentation/common`, а Qt widgets получают уже semantic `ScenarioChatMessage`.

Это один из лучших заделов под будущий Android-клиент.

## 37. Scenario composer

Нижний composer показывает выбранный scenario и позволяет запустить его. Параметры живут в правом inspector и строятся по specs.

Во время исполнения composer блокируется через busy state.

## 38. Right Inspector

Вкладки:

- **Кейс**;
- **Логи**;
- **Артефакты**;
- **Параметры**.

При выборе case логи и артефакты фильтруются по case id.

## 39. User menu

Через top-right avatar доступны:

- Узел;
- Настройки;
- Обновить состояние;
- Диагностика;
- Выход.

## 40. Настройки

Settings dialog уже разделён на:

- пользовательские;
- рабочие;
- системные.

Пользовательские настройки сохраняют:

- размер окна;
- стартовый mode;
- right inspector open/tab;
- chat filter;
- выбранного participant;
- последний scenario;
- значения forms по scenarios.

## 41. Node view

Отдельный Node dialog отображает AppDock/runtime сведения. Сам факт наличия такой поверхности показывает, что desktop UI проектируется как клиент внутри управляемого узла, а не как обычное автономное окно.

---

# XI. Background processes

## 42. Что объявлено

Registry содержит три процесса:

- мониторинг публикаций Банка России;
- проверка консистентности workspace;
- фоновое обновление cache.

Модель хранит:

- enabled;
- status;
- last/next run;
- last result/error.

UI умеет включать/выключать процесс и показывает состояние.

## 43. Что реально работает

На текущем `main` `BackgroundProcessStore` — это in-memory state machine. Он умеет менять флаги и статусы, но scheduler/executor отсутствует.

Нет:

- таймерного scheduler;
- event watcher;
- thread/process worker;
- trigger persistence;
- восстановления enabled state после restart;
- реального вызова business operations.

Следовательно, этот раздел UI сейчас является **готовым UX/domain scaffold**, а не готовой фоновой автоматизацией.

---

# XII. Presence / участники

## 44. Что реализовано

`PresenceService` при старте создаёт текущего пользователя и затем регистрирует авторов завершённых cases.

Для participant хранится:

- display name;
- online flag;
- host;
- last seen;
- run count;
- deterministic accent color.

Chat projector умеет incoming/outgoing placement разных авторов.

## 45. Текущая граница

Никакого сетевого participant registry, polling или subscription в `PresenceService` нет.

`is_online` для текущего пользователя поддерживается локально. Другие участники могут появиться из case metadata, но полноценное real-time presence пока отсутствует.

То есть surface уже умеет **показывать** многопользовательскую модель, но сама не умеет **получать** её из collaboration backend.

---

# XIII. Поручения

## 46. Модель

Assignment содержит:

- active/completed/cancelled status;
- assignee;
- author;
- description;
- scenario/case/artifact links;
- timestamps.

## 47. Автоматическое создание

При создании нового case MainWindow автоматически создаёт локальное поручение:

> проверить результат запущенного сценария.

Это демонстрирует intended workflow «запуск → результат → human follow-up».

## 48. Ограничение

Assignments сейчас локальны и сохраняются в JSON history. Нет remote delivery, notification backend, SLA/deadlines, comments или server-side ownership.

Поэтому это ещё один хорошо оформленный domain/UI scaffold для будущей совместной работы.

---

# XIV. AppDock integration: текущее состояние

## 49. Что интегрировано реально

На уровне `stratbox-windows` уже есть:

- Connector manifest;
- package graph;
- строгий Activation Context consumer;
- runtime package validation;
- managed filesystem paths;
- node/session/user/host identity;
- Data root handoff;
- health snapshot;
- runtime state projection;
- diagnostics/preflight;
- clean/unclean shutdown projection.

Это достаточно глубокая интеграция. AppDock для приложения уже является runtime contract, а не просто launcher.

## 50. Что пока не реализовано в surface

Manifest прямо задаёт:

```text
locality = local
launch_mode = foreground
platform = windows
```

Поэтому удалённый host execution, remote attachment, mobile control и task delegation сейчас не являются функцией `stratbox-windows`.

Базовая архитектура AppDock, напротив, описывает future host/remote/mobile/AI направления. Для Strategy Box это естественный последующий слой, но важно не путать архитектурный потенциал AppDock с текущим состоянием desktop surface.

---

# XV. Desktop-host abstraction

## 51. PlatformServices

OS-specific действия вынесены в `adapters/desktop_host`:

- открыть path;
- reveal path;
- copy text.

Интересно, что `open_path/reveal_path` уже имеют Windows branch и `xdg-open` fallback.

То есть код фактически немного шире Windows, хотя manifest ограничивает surface Windows.

Это хороший задел для Linux desktop-host, но clipboard всё равно зависит от Qt.

---

# XVI. Presentation portability и Android

## 52. Что уже можно переиспользовать

Для будущего `stratbox-android` потенциально пригодны почти без изменений:

- operation/scenario models;
- operation form specs;
- scenario runner;
- cases/events/artifacts/logs models;
- assignment models;
- workspace schemas/resolution logic;
- history semantics;
- scenario-chat semantic models/projector;
- часть AppDock runtime contracts, если mobile AppDock surface использует совместимый handoff;
- generic status/visibility vocabulary.

## 53. Что сейчас мешает прямому повторному использованию

Главная архитектурная утечка:

```text
runtime.bootstrap
    ↓ imports
presentation.qt_desktop.scenario_coordinator
```

То есть runtime composition уже зависит от Qt presentation layer.

Для Android/другого frontend лучше получить:

```text
application/orchestration/
    ScenarioCoordinatorProtocol
    ScenarioExecutionService
    JobManager

presentation/qt_desktop/
    QtScenarioBridge / Qt signals adapter

presentation/android/
    Android bridge
```

Тогда `AppRuntime` сможет собираться без Qt.

## 54. `presentation/common` пока слишком узкий

Сейчас туда вынесены главным образом scenario-chat models/projector.

Именно этот слой логично расширять:

- semantic screen models;
- navigation state;
- filters;
- case inspector models;
- artifact/log projections;
- assignment/presence projections;
- operation form view-model;
- action availability;
- status labels;
- platform-neutral formatting.

Тогда Windows и Android будут рендерить один смысл разными UI toolkit-слоями.

## 55. Нужно ли обязательно писать Android заново другим toolkit

Нет. PySide6 уже имеет официальный Android deployment tool (`pyside6-android-deploy`) и Qt поддерживает APK/AAB packaging. Однако официальный Qt for Python путь для Android заметно сложнее desktop deployment и на опубликованной документации `pyside6-android-deploy` требует Unix host для сборки.

Практический вывод для Alta Veritas: наличие Android deployment у PySide6 полезно как вариант, но архитектуру всё равно стоит строить так, чтобы shared часть не зависела от Qt Widgets. Это оставляет свободу выбрать PySide/Qt Quick, нативный Android frontend или другой toolkit позже.

---

# XVII. Качество и тесты

## 56. Тестовый набор

Сейчас есть 10 test-файлов:

- contract tests AppDock entry/runtime contracts;
- smoke test внешней core dependency;
- smoke repository contract;
- unit paths;
- unit scenario-chat projector;
- unit workspace explorer;
- unit workspace registry;
- unit workspace resolver.

Покрытие архитектурных границ есть, но оно узкое относительно 149 Python-файлов.

Почти нет прямого тестирования:

- scenario execution;
- operation runner error paths;
- history persistence;
- preferences;
- background state;
- assignments;
- presence;
- UI coordinators;
- AppSurfaceStateService;
- full runtime bootstrap.

## 57. Критическое расхождение manifest и tests

Текущий `manifest.json`:

```text
contract_version = 4.0
package_requirement
```

А `tests/smoke/test_repository_contract.py` всё ещё утверждает:

```text
contract_version == 3.0
package_identity
```

Следовательно, этот smoke test по текущему дереву обязан падать минимум в нескольких местах.

Это не гипотеза о runtime, а прямое логическое несовпадение checked-in файлов.

## 58. Документация тоже частично отстала

Есть несколько разных версий формулировок:

- manifest фактически `4.0`;
- README в одном месте называет Connector Manifest `3.0`;
- `docs/appdock-integration.md` также говорит про Connector `3.0`;
- одновременно activation contract действительно `4.0`, а Activation Context — `3.0`.

Из-за наличия нескольких независимых contract versions формулировки особенно важно сделать однозначными:

```text
Connector Manifest contract: 4.0
Surface Activation contract: 4.0
Activation Context contract: 3.0
Strategy Box runtime_state contract: 1.x
```

Сейчас они местами смешиваются.

---

# XVIII. Hygiene репозитория

## 59. `.tmp` попал в Git

Документация прямо говорит, что `.tmp/` не должен попадать в Git.

Однако `.gitignore` вообще не содержит `.tmp/`, и в текущем дереве tracked:

```text
.tmp/dev-workspace/.stratbox_windows/system/app.json
.tmp/dev-workspace/.stratbox_windows/system/runtime/history/*.json
```

Это нужно исправить.

## 60. `__pycache__` и `.pyc` попали в Git

В `src/stratbox_windows/application/logs/__pycache__` tracked восемь `.pyc` для Python 3.11 и 3.12.

Причина хорошо читается в `.gitignore`:

```text
__pycache__/
*.py[cod]
...
!src/stratbox_windows/application/logs/
!src/stratbox_windows/application/logs/**
```

Последнее широкое negation-rule повторно включает всё под `application/logs`, включая bytecode.

Следует заменить эту схему более узким исключением либо повторно re-ignore `__pycache__`/`*.pyc` после negation.

## 61. Последние «SORS» commits не содержат SORS-кода

История `main` показывает:

- `2026-08-03` — `New SORS method`;
- `2026-08-05` — `Add SORS-SME optimization method`.

Фактические изменения первого — только четыре `.pyc`; второго — `.tmp` runtime state и ещё четыре `.pyc`.

Ни SORS, ни SORS-SME source-файлов в текущем `stratbox-windows` нет.

Поэтому эти commit titles нельзя использовать как доказательство наличия функциональности. Скорее всего, нужный source-код был реализован в другом checkout/repository, но в этот репозиторий попали только generated files.

Это сильный аргумент в пользу pre-commit/release integrity checks.

## 62. Последняя реальная разработка surface

Основная последовательность истории выглядит так:

- конец июня 2026 — реализация `stratbox-windows` и интенсивные UI updates;
- 27 июня — правка activation contract;
- июль — дальнейшие UI updates и несколько AppDock adaptation commits;
- 30 июля — последняя содержательная AppDock adaptation;
- 3–5 августа — generated-file commits с SORS titles.

На дату исследования последнему commit 62 дня.

## 63. Branch/release состояние

Сейчас:

- только `main`;
- GitHub issues отсутствуют;
- releases отсутствуют;
- отдельного CI workflow в дереве нет.

Для раннего private-style development это нормально, но для public product surface следующая стадия должна включать CI и reproducible release checks.

---

# XIX. Архитектурные сильные стороны

## 64. Core действительно вынесен наружу

Самая важная удачная граница уже сделана: `stratbox-windows` не превращается обратно в monolith.

Handler-ы вызывают core, а desktop repo занимается surface orchestration.

## 65. Scenario-first UX

Пользователь видит scenarios/cases, а не Python functions. Это масштабируемая модель для аналитического продукта.

## 66. Декларативные specs

Operation и scenario specs задают metadata, forms, visibility и workflow structure. Это фундамент для альтернативных frontend-ов.

## 67. Semantic projector

Вынос scenario-chat projector в `presentation/common` — конкретный пример правильной shared presentation architecture.

## 68. Managed runtime state

Связь с AppDock state достаточно структурирована: session/user/node/health/runtime projections уже присутствуют.

## 69. Хорошая observability база

Case → step → operation → log → artifact → event связи позволяют строить прозрачный execution history.

## 70. Degraded mode

Приложение может поднять UI/diagnostics даже при проблеме Data, вместо полного startup failure.

---

# XX. Главные слабые места и архитектурные долги

## 71. P0 — синхронизировать contracts/tests/docs

Сейчас source of truth расходится с тестами и текстовой документацией.

Это нужно исправить первым, потому что contract tests должны ловить drift, а сейчас сами являются drift.

## 72. P0 — очистить tracked generated state

Удалить из index:

- `.tmp/`;
- `__pycache__/`;
- `.pyc`.

Исправить `.gitignore` так, чтобы проблема не повторялась.

## 73. P0 — убрать публично-репозиторные локальные детали

`docs/development.md` содержит локально-специфичный шаг установки внутреннего расширения. По публичной архитектурной границе `stratbox-windows` такой материал лучше удалить из открытого документа и держать во внутренней инструкции окружения.

То же правило стоит применять к любым internal-only runtime flags: публичный Windows surface должен оперировать нейтральным публичным contract vocabulary.

## 74. P1 — runtime bootstrap не полностью frontend-neutral

`runtime.bootstrap` импортирует Qt `ScenarioCoordinator`.

Это главный structural blocker для clean Android reuse.

## 75. P1 — background UX опережает engine

Пользователь может включить процесс, но ничего реально не запускается.

Лучше либо явно маркировать функции experimental/preview, либо реализовать background scheduler прежде чем расширять UI.

## 76. P1 — presence опережает transport

UI выглядит готовым к multi-user, но сервис локальный.

Следующий уровень — provider/API boundary, чтобы presence мог получать participants из AppDock/remote service.

## 77. P1 — assignments опережают collaboration backend

Локальные assignments уже полезны, но для командной функции нужен внешний persistence/notification layer.

## 78. P1 — отсутствует cancellation/job control

Для аналитических загрузок и долгих расчётов это станет необходимо довольно быстро.

## 79. P1 — history persistence требует atomicity

Минимальный upgrade:

```text
write temp
fsync/close
replace target atomically
optional previous backup
schema_version
retention
```

## 80. P2 — registry scalability

Hardcoded operation registry должен эволюционировать до modular provider model до того, как функций станет десятки.

## 81. P2 — version provenance

`runtime/version.py` получает commit через локальный `.git`.

В sealed/materialized deployment `.git` может отсутствовать. Для managed launch лучше считать revision из Activation Context/source metadata основной provenance, а Git probing — dev fallback.

## 82. P2 — standalone user-profile path сейчас мёртвый

Либо удалить неиспользуемый режим, либо сделать его официальным startup mode. С учётом общего правила проекта «делать сразу в идеал» лучше избегать промежуточного мёртвого пути.

---

# XXI. Потенциал развития, уже заложенный в код

## 83. Рост каталога аналитических функций

OperationSpec + ScenarioSpec позволяют без переделки UI добавлять:

- новые CBR collectors;
- банковские выгрузки;
- RAS/IFRS pipelines;
- macro datasets;
- report builders;
- transformations;
- multi-step update cascades.

Главное — сохранить бизнес-реализацию в `stratbox`, а в `stratbox-windows` оставить UX schema + orchestration adapter.

## 84. Полноценный workflow engine

Composite scenario уже доказывает архитектуру.

Следующие естественные возможности:

- branching;
- optional steps;
- continue-with-warnings;
- retries per step;
- conditions;
- parallel independent steps;
- checkpoints;
- restart/resume;
- step-level cancellation.

## 85. Background automation

Существующий registry/UI можно довести до реального runtime:

```text
BackgroundProcessSpec
↓
TriggerSpec (schedule/event/manual)
↓
BackgroundJobManager
↓
Scenario/Operation runner
↓
Events + artifacts
```

Тогда background процессы будут теми же сценариями, а не отдельной параллельной системой.

## 86. Remote host execution

AppDock концептуально уже предусматривает host и удалённую рабочую среду. Для Strategy Box это особенно естественно: тяжёлые загрузки/расчёты можно выполнять рядом с Data, а Windows/Android surface оставлять управляющим клиентом.

Для этого operation/scenario API уже почти подходит. Нужно отделить local executor от executor interface:

```text
ExecutionBackend
├── LocalExecutionBackend
└── RemoteNodeExecutionBackend
```

## 87. Mobile companion / Android

При правильном выделении common layer мобильный клиент сможет показывать:

- running cases;
- scenario catalogue;
- parameters;
- approvals;
- status/health;
- artifacts;
- logs summary;
- assignments;
- notifications;
- lightweight scenario launch.

Тяжёлая файловая работа может оставаться на host.

## 88. AI agent surface

В модели уже есть:

- `actor_kind='ai'`;
- `ai_visibility` operation field;
- structured operation specs;
- cases/events/artifacts;
- runtime state;
- action boundaries.

Этого достаточно, чтобы в будущем дать AI не shell-доступ, а безопасный каталог разрешённых operations/scenarios.

Правильная форма:

```text
AI agent
↓
query available scenarios
↓
validate params
↓
request execution
↓
case id
↓
status/events/artifacts
```

Это хорошо совпадает с общим AppDock подходом «разрешённые действия вместо полного доступа к компьютеру».

## 89. Artifact-centric workflow

Артефакты уже являются first-class entities. Дальше можно добавить:

- preview metadata;
- lineage;
- content hash;
- source URLs;
- retention;
- favorite/pin;
- share/export;
- downstream action suggestions;
- artifact → scenario chaining.

## 90. Collaboration

Presence + assignments + author metadata + incoming/outgoing chat layout дают основу для:

- shared node/session;
- user-to-user assignments;
- comments;
- approvals;
- remote case ownership;
- audit trail;
- team timeline.

Но transport/storage следует реализовать отдельно от UI models.

---

# XXII. Как я бы привёл архитектуру к целевой форме

## 91. Целевая схема слоёв

```text
stratbox-windows
│
├── contracts/
│   └── platform-neutral surface contracts
│
├── application/
│   ├── operations/
│   ├── scenarios/
│   ├── orchestration/
│   ├── jobs/
│   ├── cases/
│   ├── artifacts/
│   ├── assignments/
│   ├── presence/
│   └── workspace/
│
├── runtime/
│   ├── context
│   ├── state
│   ├── paths
│   └── composition without Qt
│
├── adapters/
│   ├── appdock/
│   ├── desktop_host/
│   ├── local_execution/
│   └── persistence/
│
├── presentation/
│   ├── common/
│   │   ├── scenario_chat
│   │   ├── case_inspector
│   │   ├── workspace
│   │   ├── forms
│   │   ├── presence
│   │   └── assignments
│   └── qt_desktop/
│
└── resources/
```

Ключевой принцип: `runtime/application/presentation/common` должны импортироваться без PySide6.

## 92. Что копировать потом в `stratbox-android`

Если сохраняется модель отдельных репозиториев, стандартные сегменты следует сделать изоморфными:

```text
application/
presentation/common/
adapters/appdock/contract models
runtime state semantics
```

А platform-specific слои различать:

```text
stratbox-windows:
  presentation/qt_desktop
  adapters/desktop_host

stratbox-android:
  presentation/android
  adapters/android_host
```

Ещё лучше — когда shared semantics стабилизируются, вынести их в отдельный общий package. Но на текущей стадии сначала полезнее добиться чистой границы внутри `stratbox-windows`, чтобы преждевременно не создавать четвёртый репозиторий.

---

# XXIII. Приоритетный roadmap

## Этап 1 — привести текущий репозиторий в консистентное состояние

1. Синхронизировать manifest/tests/docs по четырём contract versions.
2. Удалить `.tmp` и `.pyc` из Git.
3. Исправить `.gitignore`.
4. Убрать локально-внутренние детали из публичной документации/конфигурационных деклараций.
5. Добавить CI: release integrity + internal imports + pytest + manifest check.
6. Зафиксировать clean baseline commit.

## Этап 2 — завершить separation для будущего Android

1. Перенести execution coordination из Qt layer в application orchestration.
2. Оставить Qt signals как adapter.
3. Расширить `presentation/common`.
4. Ввести platform service protocols.
5. Ввести persistence interface.
6. Сделать runtime bootstrap без импорта Qt.

## Этап 3 — довести существующие каркасы до функций

1. Background Job Manager.
2. Cooperative cancellation.
3. Retry/resume semantics.
4. Real presence provider.
5. Remote assignments provider.
6. Artifact metadata/lineage.

## Этап 4 — масштабировать аналитику

1. Modular operation providers.
2. Больше atomic operations из `stratbox`.
3. Composite workflows.
4. Declarative catalog metadata.
5. Search/categories/favorites/recent.

## Этап 5 — remote/mobile/AI

1. ExecutionBackend abstraction.
2. Remote-node backend через AppDock.
3. Android companion/full client.
4. Permissioned AI scenario API.
5. Approvals and notifications.

---

# XXIV. Что сейчас уже является продуктом, а что — обещанием архитектуры

| Подсистема | Статус | Комментарий |
|---|---|---|
| AppDock local activation | **реализовано** | manifest, entry, strict context, runtime graph |
| App context / paths | **реализовано** | managed + dev runtime |
| Data/workspace resolution | **реализовано** | degraded mode, auto-create |
| Workspace explorer | **реализовано** | local filesystem provider |
| Operation catalogue | **реализовано** | 3 operations, hardcoded registry |
| CBR file collector | **реализовано** | вызывает core |
| Escrow history export | **реализовано** | вызывает core |
| Diagnostics | **реализовано** | workspace/dependencies/runtime |
| Atomic scenarios | **реализовано** | auto-generated |
| Composite scenario | **реализовано** | 1 CBR cascade |
| Async GUI execution | **реализовано** | QThread, 1 job at once |
| Cases/events | **реализовано** | lifecycle + chat projection |
| Logs/artifacts | **реализовано** | linked to runs |
| Local history persistence | **реализовано, простое** | JSON projections |
| Preferences | **реализовано** | JSON user config |
| Background process UI/model | **каркас** | scheduler/executor отсутствует |
| Presence UI/model | **частично** | local projection, без network presence |
| Assignments | **частично** | local persistence, auto-generated |
| AI actor semantics | **каркас** | execution agent отсутствует |
| Cancellation | **модель есть, engine нет** | `cancelled` status без cancel API |
| Remote execution | **потенциал** | manifest сейчас local |
| Android | **потенциал** | common layer частичный |
| Production CI/releases | **нет** | scripts есть, pipeline отсутствует |

---

# XXV. Итоговая оценка

`stratbox-windows` уже имеет вполне различимую архитектуру самостоятельной product surface. Самая важная работа была сделана правильно: desktop repo отделён от бизнес-core, operations формализованы, сценарии стали пользовательской единицей, execution превращается в cases/events/artifacts, workspace отделён от Data selector, AppDock handoff оформлен контрактом, а UI строится вокруг состояния и сценариев, а не вокруг прямых Python-команд.

Главная проблема сейчас — не отсутствие архитектуры, а **несоответствие зрелости разных уровней**. UI и domain vocabulary уже описывают продукт следующего поколения — фоновые задачи, участников, поручения, AI actors, узлы, remote-подобные состояния — тогда как engine некоторых этих функций остаётся локальным и минимальным. Это нормально для стадии прототипа, но следующий цикл разработки лучше направить не на добавление ещё большего числа визуальных концепций, а на превращение уже существующих контрактов в реальные application services.

Вторая важная проблема — инженерная дисциплина repository baseline. Текущий `main` содержит generated runtime state и bytecode, последние два commit titles не соответствуют содержимому, а manifest/tests/docs разошлись по contract vocabulary. Всё это исправляется относительно дёшево и даст гораздо более надёжную основу перед расширением функциональности.

С точки зрения будущего `stratbox-android`, `stratbox-windows` уже движется в правильном направлении, но разделение нужно довести до конца: **никакого Qt внутри общего runtime/application orchestration**. Если сделать `application + presentation/common + platform contracts` полностью toolkit-neutral, Android-клиент сможет наследовать практически всю семантику Strategy Box, меняя только rendering, OS integration и часть AppDock/mobile handoff.

Иными словами, текущий репозиторий уже содержит не просто Windows GUI. В нём сформировался прототип универсального Strategy Box client runtime. Следующий качественный скачок — признать это явно в архитектуре и очистить границы так, чтобы Windows стал первой реализацией клиента, а не владельцем общей логики клиента.

---

# XXVI. Источники и проверенные материалы

## Репозиторий `stratbox-windows`

Исследованы актуальные файлы `main`, включая:

- `README.md`;
- `pyproject.toml`;
- `appdock/manifest.json`;
- `docs/architecture.md`;
- `docs/development.md`;
- `docs/appdock-integration.md`;
- `scripts/check_release_integrity.py`;
- `scripts/check_internal_imports.py`;
- `scripts/check_appdock_contract.py`;
- `src/stratbox_windows/__main__.py`;
- `adapters/appdock/*`;
- `adapters/desktop_host/*`;
- `runtime/*`;
- `application/operations/*`;
- `application/scenarios/*`;
- `application/workspace/*`;
- `application/cases/*`;
- `application/events/*`;
- `application/artifacts/*`;
- `application/logs/*`;
- `application/history/*`;
- `application/background/*`;
- `application/presence/*`;
- `application/assignments/*`;
- `presentation/common/*`;
- `presentation/qt_desktop/*`;
- tests и последние commits.

GitHub repository: `https://github.com/ForestTiger-GH/stratbox-windows`

## AppDock

Использован предоставленный документ **«AppDock — Базовое описание»** как внешний контекст для оценки будущих host/remote/mobile/AI направлений. Эти направления в тексте исследования явно отделены от фактически реализованных функций `stratbox-windows`.

## Qt / PySide6

Для проверки portability использована официальная документация Qt for Python:

- Qt for Python — Deployment: `https://doc.qt.io/qtforpython-6/deployment/index.html`
- `pyside6-deploy`: `https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html`
- `pyside6-android-deploy`: `https://doc.qt.io/qtforpython-6.8/deployment/deployment-pyside6-android-deploy.html`
- Qt 6 Android deployment: `https://doc.qt.io/qt-6/deployment-android.html`

---

# XXVII. Ограничения исследования

Исследование основано на статическом разборе текущего `main`, GitHub metadata/history и контрактов. Полный checkout репозитория в локальный execution container получить не удалось из-за отсутствия прямого сетевого доступа из container environment, поэтому `pytest` и GUI не запускались локально.

При этом отмеченное расхождение `manifest.json` и `tests/smoke/test_repository_contract.py` установлено прямым сравнением checked-in source и не требует выполнения тестов: утверждения теста противоречат текущим значениям manifest.
