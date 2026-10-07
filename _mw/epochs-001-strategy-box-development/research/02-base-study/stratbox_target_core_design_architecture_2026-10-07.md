# Strategy Box: целевая архитектура core/runtime, business logic и общего design layer

**Дата:** 2026-10-07  
**Статус:** Research / Architecture Note  
**Контекст:** вторая ветка исследований Strategy Box  
**Основание:** текущее устройство `stratbox`, `stratbox-windows`, предыдущие исследования по web/self-hosted режиму, multi-user/runtime, AppDock и текущий разбор общих слоёв клиентов.

---

## 0. Краткий вывод

Целевая архитектура Strategy Box естественно раскладывается на несколько самостоятельных слоёв.

```text
                         AppDock
             universal platform / node layer
      install • lifecycle • host • connection • health
                           │
                           ▼
                    stratbox-core
              Strategy Box product runtime
                           │
                           ▼
                       stratbox
                 pure business/domain logic
```

И отдельно пользовательские поверхности:

```text
                    stratbox-core
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
 stratbox-windows    stratbox-web   stratbox-android
          │              │              │
          └──────────────┼──────────────┘
                         │
                  stratbox-design
              common visual language
```

Главные роли:

- `stratbox` — чистая предметная и data/business logic;
- `stratbox-core` — общий product/application runtime Strategy Box;
- `stratbox-design` — единый дизайн-язык и design system продукта;
- `stratbox-windows`, `stratbox-web`, `stratbox-android` — три клиентские поверхности;
- AppDock — универсальная внешняя платформа установки, запуска, узла, host/remote, lifecycle и health.

Это позволяет использовать одну и ту же бизнес-логику как внутри корпоративного контура через Jupyter/Airflow/Python, так и снаружи через полноценные пользовательские клиенты Strategy Box.

---

# 1. `stratbox` — Domain Library

`stratbox` следует оставить максимально чистой библиотекой предметной логики.

Его задача — знать, **как работать с банковскими, макроэкономическими и другими данными**, а не то, каким интерфейсом пользуется пользователь и в каком приложении запускается операция.

Концептуально:

```text
stratbox
│
├── CBR
├── Rosstat
├── banking
├── macro
├── parsers
├── collectors
├── transformations
├── calculations
├── registries
├── provenance
├── FileStore contracts
├── exporters
└── artifact generation
```

`stratbox` не должен зависеть от:

- Windows UI;
- Web;
- Android;
- Qt;
- браузера;
- product runtime;
- scenario chat;
- Cases / Jobs как продуктовых сущностей;
- AppDock lifecycle.

Правильная модель — один и тот же `stratbox` может вызываться из разных окружений.

Внутри корпоративного контура:

```text
Jupyter / Airflow / Python
           │
           ▼
        stratbox
           │
           ▼
infrastructure adapters / corporate environment
```

Во внешнем продукте:

```text
Windows / Web / Android
          │
          ▼
     stratbox-core
          │
          ▼
       stratbox
```

Таким образом, предметная логика остаётся одной и той же, а пользовательский продукт является отдельной надстройкой.

---

# 2. `stratbox-core` — Strategy Box Runtime Core

Второй слой — общий продуктовый runtime Strategy Box.

Именно сюда естественно вынести значительную часть логики, которая сейчас исторически находится внутри `stratbox-windows`.

Текущее `stratbox-windows` уже содержит намного больше, чем desktop UI:

- scenarios;
- operations;
- cases;
- events;
- artifacts;
- logs;
- assignments;
- presence;
- background processes;
- workspace state;
- runtime state;
- orchestration;
- execution coordination;
- history;
- AppDock integration.

Поэтому фактически Windows-репозиторий уже частично содержит прототип будущего общего runtime.

Целевой `stratbox-core` можно представить так:

```text
stratbox-core
│
├── commands
├── scenarios
├── cascades
│
├── planning
├── execution
├── jobs
├── cases
│
├── events
├── artifacts
├── logs
│
├── workspaces
├── background
├── assignments
├── approvals
├── presence
├── notifications
│
├── user/application state
├── settings contracts
├── permissions/capabilities
│
├── persistence
├── scheduling
├── observability
│
├── API / event stream
│
├── adapters/
│   ├── appdock
│   ├── storage
│   ├── identity
│   └── execution
│
└── integration/
    └── stratbox
```

`stratbox-core` отвечает на вопросы:

- какой Scenario был запущен;
- какой Case создан;
- какой Job выполняется;
- какие Commands входят в план;
- какой сейчас статус;
- какие Events произошли;
- какие Artifacts получены;
- что доступно пользователю;
- можно ли Cancel / Retry / Approve;
- что выполняется в background;
- какие assignments существуют;
- как выглядит общее runtime-state продукта.

`stratbox` при этом отвечает на другой класс вопросов:

- как скачать данные;
- как их распарсить;
- как рассчитать показатель;
- как проверить результат;
- как построить Excel / CSV / JSON / другой артефакт.

Именно это разделение следует считать фундаментальным.

---

# 3. AppDock и `stratbox-core` — разные уровни

`stratbox-core` не заменяет AppDock.

Граница:

```text
AppDock
    universal platform runtime

stratbox-core
    application runtime конкретного продукта Strategy Box

stratbox
    business/domain library
```

AppDock отвечает за универсальные платформенные задачи:

- установка;
- обновление;
- запуск;
- остановка;
- node lifecycle;
- host;
- remote connection;
- environment;
- health;
- recovery;
- platform-level session/runtime integration;
- поставку и управление приложением.

`stratbox-core` отвечает за продуктовую семантику Strategy Box:

- Scenario;
- Cascade;
- Case;
- Job;
- Artifact;
- Assignment;
- background execution;
- Strategy Box workspace;
- product-level permissions;
- product state.

AppDock не должен знать устройство внутренней продуктовой модели Strategy Box.

А `stratbox-core` не должен превращаться в собственную универсальную платформу установки и lifecycle.

---

# 4. Три клиента

Над общим runtime появляются три пользовательские поверхности:

```text
stratbox-windows
stratbox-web
stratbox-android
```

Они представляют один и тот же Strategy Box, но используют разные платформенные технологии.

Например:

```text
Windows
    Qt / PySide / desktop OS integration

Web
    HTML / CSS / TypeScript / browser APIs

Android
    native / Compose / Qt Quick / другой mobile toolkit
```

Клиенты должны различаться способом rendering и платформенной интеграцией, но воспринимать одинаковые сущности и состояния Strategy Box.

---

# 5. Общий клиентский смысл

Между runtime и конкретным UI существует общий семантический слой.

Например, все клиенты должны одинаково понимать:

```text
Scenario
Cascade
Case
Job
Artifact
Participant
Assignment
Notification

RUNNING
WAITING_APPROVAL
FAILED
SUCCEEDED

can_cancel
can_retry
can_open
can_approve
```

И одинаково интерпретировать:

- Scenario Chat;
- Case Inspector;
- Artifact list;
- filters;
- unread state;
- available actions;
- author;
- severity;
- progress;
- lifecycle state.

Текущий `stratbox-windows` уже содержит зародыш такого подхода:

```text
presentation/common/
    scenario_chat/
        models.py
        projector.py
```

То есть Case/Event сначала превращается в семантическую модель сообщения, и только затем Qt занимается отрисовкой.

Это правильная архитектурная идея.

Целевая цепочка:

```text
stratbox-core state
        │
        ▼
client contract / SDK
        │
        ▼
semantic presentation model
        │
        ▼
platform rendering
```

Например:

```text
Case
 ↓
CaseCardModel
 ↓
 ┌──────── Qt widget
 ├──────── Web component
 └──────── Android component
```

`CaseCardModel` описывает смысл:

```text
title
subtitle
status
progress
actions
artifacts
author
timestamp
severity
read state
```

А конкретный frontend уже решает, как это нарисовать.

---

# 6. Отдельный `stratbox-client-core` пока не нужен

Физически создавать единый client runtime package для всех трёх клиентов сейчас преждевременно.

Причина — разные технические среды:

- Windows — Python/Qt;
- Web — TypeScript/Browser;
- Android — возможно Kotlin/Compose, Qt Quick или другой toolkit.

Python-пакет общего client runtime всё равно не сможет напрямую использоваться Web-клиентом.

Поэтому правильнее держать канонические контракты в `stratbox-core`:

```text
stratbox-core
    canonical schemas
    API
    event protocol
    action vocabulary
    statuses
    capabilities
    view-neutral DTOs
```

И уже из этого получать платформенные SDK:

```text
Python SDK      → stratbox-windows
TypeScript SDK  → stratbox-web
Android SDK     → stratbox-android
```

Таким образом, общий смысл один, хотя физическая реализация клиента может отличаться.

---

# 7. `stratbox-design` — отдельный общий дизайн-слой

Отдельно от runtime и application semantics возникает второй общий слой — **единый визуальный язык Strategy Box**.

Его имеет смысл оформить отдельным репозиторием:

```text
stratbox-design
```

Это лучше, чем `stratbox-ui`, потому что речь идёт не о готовых Qt/React/Android компонентах, а о общей дизайн-системе.

Целевая структура:

```text
stratbox-design
│
├── tokens/
│   ├── colors
│   ├── typography
│   ├── spacing
│   ├── radius
│   ├── strokes
│   ├── elevation
│   ├── opacity
│   └── density
│
├── motion/
│   ├── durations
│   ├── easing
│   ├── enter
│   ├── exit
│   ├── movement
│   └── reduced-motion
│
├── icons/
│
├── components/
│   ├── button
│   ├── chip
│   ├── card
│   ├── scenario-message
│   ├── artifact-row
│   ├── inspector
│   ├── composer
│   └── navigation-rail
│
├── patterns/
│   ├── scenario-chat
│   ├── workspace
│   ├── inspector
│   ├── settings
│   └── notifications
│
├── themes/
│   ├── light
│   └── dark
│
└── assets/
```

Это должен быть source of truth для того, как Strategy Box выглядит и ощущается на разных платформах.

---

# 8. Почему этот слой уже фактически существует

Текущий `stratbox-windows` уже содержит элементы будущей design system:

```text
presentation/qt_desktop/theme/
resources/styles/app.qss
resources/icons/
presentation/qt_desktop/components/
```

Есть:

- собственная палитра;
- avatar gradients;
- status colors;
- background colors;
- border colors;
- hover states;
- selected states;
- border radius;
- размеры;
- typography;
- собственные SVG icons;
- повторяемые component patterns.

Сейчас большая часть этого зашита непосредственно в QSS и Qt implementation.

Например, вместо:

```text
background: #E6F3F4
```

целевая система должна оперировать семантическим токеном:

```text
color.surface.selected
```

А уже платформы преобразуют его:

```text
Strategy Box token
        │
        ├── Qt/QSS       → concrete color
        ├── CSS variable → concrete color
        └── Android      → concrete color
```

---

# 9. Design Tokens

`stratbox-design` должен строиться вокруг semantic design tokens.

Например:

```text
color.surface.base
color.surface.raised
color.surface.selected

color.text.primary
color.text.secondary
color.text.muted

color.status.running
color.status.success
color.status.warning
color.status.error

space.xs
space.sm
space.md
space.lg

radius.sm
radius.md
radius.lg

font.body
font.caption
font.heading

motion.fast
motion.normal
motion.slow
```

Важно различать:

```text
primitive token
    teal-500

semantic token
    color.action.primary
```

Клиенты должны зависеть преимущественно от semantic tokens.

Это позволит:

- менять тему;
- добавлять light/dark;
- добавлять организационные style bundles;
- менять branding;
- создавать accessibility profiles;
- менять typography;
- переиспользовать систему между Windows/Web/Android.

---

# 10. Общий motion language

Анимации тоже должны иметь общий semantic layer.

Не следует пытаться делить между платформами конкретный код:

```text
QPropertyAnimation
CSS transition
Compose animation
```

Общим должен быть язык motion:

```text
motion.fast
motion.normal
motion.slow

ease.standard
ease.enter
ease.exit

panel.enter
panel.exit
message.appear
artifact.publish
status.transition
drawer.open
selection.change
```

`stratbox-design` задаёт:

- назначение;
- длительность;
- easing;
- direction;
- допустимость motion;
- reduced-motion behaviour.

А платформы реализуют это своими средствами.

Поэтому Windows/Web/Android должны быть **визуально родственными**, но не обязаны быть пиксельно идентичными.

---

# 11. Общие component contracts

Общими должны быть anatomy и состояния компонентов, а не конкретный код widget.

Например:

```text
ScenarioMessage

anatomy:
    avatar
    author
    timestamp
    title
    status
    body
    stage
    progress
    artifacts
    actions

states:
    prepared
    queued
    running
    warning
    success
    failed

placement:
    incoming
    outgoing
    system

motion:
    appear
    status_change
    artifact_attach
```

После этого существуют платформенные реализации:

```text
QtScenarioMessage
WebScenarioMessage
AndroidScenarioMessage
```

Они реализуют один component contract.

---

# 12. Где проходит граница `stratbox-core` / `stratbox-design`

Пример:

`stratbox-core` сообщает:

```text
status = running
progress = 0.62
severity = normal
available_actions = [cancel]
```

`stratbox-design` определяет:

```text
running → status.running semantic color
progress → соответствующий presentation pattern
Cancel → secondary/destructive action
running → success → соответствующий transition
```

Конкретная поверхность реализует это:

```text
Windows
    QWidget / QSS / Qt animation

Web
    DOM / CSS / TypeScript animation

Android
    mobile/native rendering
```

Общая формула:

```text
DATA / STATE       → stratbox-core
MEANING            → stratbox-core contracts
LOOK & FEEL        → stratbox-design
RENDERING          → concrete client
BUSINESS WORK      → stratbox
PLATFORM HOSTING   → AppDock
```

---

# 13. Themes

Тема должна быть не произвольным QSS/CSS-файлом, а bundle значений design tokens.

Например:

```text
theme
│
├── identity
├── colors
├── typography
├── density
├── radius
├── motion
├── icons
└── optional artifact_style
```

Клиенту не важно, откуда тема появилась:

```text
built-in
user-installed extension
organization-provided extension
```

Он получает валидный Theme Bundle.

Это заметно безопаснее и переносимее, чем разрешать расширениям вставлять произвольный CSS, JavaScript или QSS.

---

# 14. Artifact style следует отделять от UI theme

Оформление артефактов связано с UI-темой, но является отдельным контрактом.

Причина: `stratbox` должен уметь работать там, где Strategy Box UI вообще отсутствует — например в Jupyter или Airflow.

Поэтому:

```text
stratbox-design
      │
      │ optional style values
      ▼
ArtifactStyle / ReportTheme contract
      │
      ▼
stratbox exporters
```

`stratbox` должен знать только нейтральные контракты вроде:

```text
ReportTheme
ExcelStyleSet
DocumentStyleSet
ArtifactMetadataDefaults
```

Конкретные значения передаются снаружи.

Например:

```text
Airflow
    → stratbox
    → default / injected report style
```

или:

```text
Strategy Box
    → selected design theme
    → artifact style projection
    → stratbox exporter
```

Так сохраняется независимость бизнес-библиотеки.

---

# 15. Целевая карта репозиториев

| Репозиторий | Роль |
|---|---|
| `stratbox` | Чистая business/data/domain logic, пригодная для Jupyter, Airflow, Python и Strategy Box |
| `stratbox-core` | Общий product/application runtime Strategy Box |
| `stratbox-design` | Общий дизайн-язык, tokens, motion, icons, component/pattern contracts |
| `stratbox-windows` | Windows rendering + desktop OS integration |
| `stratbox-web` | Browser rendering + browser integration |
| `stratbox-android` | Android rendering + mobile integration |
| AppDock | Универсальная установка, node/host, lifecycle, connection, health и platform management |

---

# 16. Как текущий `stratbox-windows` раскладывается в целевую схему

Текущее дерево уже позволяет увидеть будущую миграцию:

```text
CURRENT stratbox-windows
│
├── application/
│       └──────────────→ stratbox-core
│
├── runtime/
│       └──────────────→ stratbox-core
│
├── presentation/common/
│       ├─ semantic projections → stratbox-core contracts
│       └─ visual semantics     → stratbox-design
│
├── presentation/qt_desktop/
│       └──────────────→ remains in stratbox-windows
│
├── resources/icons/
│       └──────────────→ mostly stratbox-design
│
├── resources/styles/
│       ├─ semantic values      → stratbox-design
│       └─ Qt realization      → stratbox-windows
│
└── adapters/desktop_host/
        └──────────────→ stratbox-windows
```

Это не означает механическое перемещение каждого файла.

Сначала нужно определить ownership каждого понятия и contract boundary, затем провести перенос.

---

# 17. Что остаётся платформенным

Даже при наличии `stratbox-design` и общего runtime клиенты сохраняют важную собственную часть.

## Windows

```text
Qt widgets
desktop windowing
system tray
file open/reveal
clipboard
native dialogs
desktop shortcuts
window state
desktop notifications
Qt animation implementation
```

## Web

```text
browser routing
DOM
CSS
web accessibility
browser storage
downloads/uploads
responsive layout
PWA behaviour
browser notifications
web animation implementation
```

## Android

```text
mobile navigation
touch ergonomics
system intents
share sheets
push notifications
back gesture
small-screen layout
mobile lifecycle
Android animation implementation
```

Один продукт не означает идентичный UI.

---

# 18. Важный принцип: общая система, разные адаптации

Цель:

```text
same meaning
same visual language
same product vocabulary
same component anatomy
same states
same motion principles
```

Но:

```text
different platform rendering
different interaction affordances
different layout adaptation
different OS integration
```

То есть Strategy Box должен ощущаться одним продуктом, сохраняя естественность каждой платформы.

---

# 19. Название `stratbox-core`

Архитектурно название `stratbox-core` подходит, но появляется терминологическая неоднозначность, потому что сам `stratbox` уже часто называется core.

Можно закрепить официальную терминологию:

```text
stratbox
= Domain Library / Business Core

stratbox-core
= Strategy Box Runtime Core / Application Core
```

Альтернативное название:

```text
stratbox-runtime
```

Оно более однозначно по назначению.

На текущем этапе важнее зафиксировать ответственность слоя, чем окончательно выбрать имя.

---

# 20. Итоговая архитектура

Полная картина:

```text
                              AppDock
        ┌─────────────────────────────────────────────────┐
        │ install / update / node / host / remote / health│
        │ lifecycle / environment / recovery              │
        └───────────────────────┬─────────────────────────┘
                                │
                                ▼
                         stratbox-core
        ┌─────────────────────────────────────────────────┐
        │ Commands / Scenarios / Cascades                 │
        │ Cases / Jobs / Events / Artifacts               │
        │ Background / Assignments / Presence             │
        │ State / Persistence / API / Scheduling          │
        │ Permissions / Observability                     │
        └───────────────────────┬─────────────────────────┘
                                │
                                ▼
                            stratbox
        ┌─────────────────────────────────────────────────┐
        │ sources / data / parsing / calculation          │
        │ validation / provenance / exporters             │
        │ business and domain logic                       │
        └─────────────────────────────────────────────────┘


                    ┌─────────────────────────┐
                    │     stratbox-design     │
                    │ tokens / motion / icons │
                    │ themes / components     │
                    │ patterns / style specs  │
                    └────────────┬────────────┘
                                 │
               ┌─────────────────┼─────────────────┐
               │                 │                 │
               ▼                 ▼                 ▼
       stratbox-windows     stratbox-web     stratbox-android
       Qt/Desktop           Browser          Mobile
```

При этом `stratbox` остаётся независимой библиотекой и может использоваться напрямую:

```text
Jupyter ─┐
Airflow ─┼────→ stratbox
Python ──┘
```

без обязательного участия `stratbox-core`, клиентов или AppDock.

---

# 21. Главный архитектурный вывод

Strategy Box целесообразно рассматривать не как набор нескольких приложений, а как одну систему с несколькими слоями и поверхностями.

```text
Business truth     → stratbox
Product truth      → stratbox-core
Visual truth       → stratbox-design
Platform rendering → windows / web / android
Platform hosting   → AppDock
```

Именно это разделение позволяет одновременно получить:

- чистую бизнес-библиотеку;
- одинаковую продуктовую логику на всех клиентах;
- единый внешний язык;
- независимую платформенную реализацию;
- повторное использование между Windows/Web/Android;
- использование `stratbox` внутри корпоративной инфраструктуры;
- отсутствие дублирования runtime;
- отсутствие дублирования дизайн-решений;
- независимое развитие AppDock как универсальной платформы.

---

## Источники и фактическая база

Архитектурная записка опирается на:

- `stratbox_base_study_current_state_2026-10-06.md`;
- `stratbox-windows_current_state_full_research_2026-10-06.md`;
- предыдущие исследования текущей ветки по web/self-hosted режиму, multi-user/runtime, execution, artifacts, observability и settings;
- `AppDock - Базовое описание.docx`;
- актуальную структуру `ForestTiger-GH/stratbox-windows`, включая:
  - `application/`;
  - `runtime/`;
  - `presentation/common/`;
  - `presentation/qt_desktop/`;
  - `presentation/qt_desktop/theme/`;
  - `resources/icons/`;
  - `resources/styles/app.qss`.

При дальнейшем переносе в публичные репозитории следует сохранять установленную границу конфиденциальности и не раскрывать устройство закрытых корпоративных расширений.
