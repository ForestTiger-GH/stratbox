# Strategy Box / stratbox-windows — исследование интерфейса, UX-архитектуры и требований

**Ветка исследований:** 02 / interface & product surface  
**Дата:** 2026-10-07  
**Фокус:** преимущественно Windows desktop surface Strategy Box; требования к интерфейсу, информационной архитектуре, сценариям, каскадам, Проводнику, логам, истории, совместной работе и будущему AI-взаимодействию.  
**Статус:** Research Result. Документ формулирует целевую UX-модель и требования; сам по себе не меняет код.

---

# 0. Краткий вывод

Strategy Box следует проектировать не как «GUI к Python-скриптам» и не как «корпоративный мессенджер с кнопками». Наиболее естественная модель — **аналитическая рабочая платформа с разговорным центром управления**, где три разных способа работы соединяются в одной оболочке:

1. **Платформа / workbench** — рабочее пространство, файлы, история, объекты, состояние среды, артефакты и навигация.
2. **Мессенджер / timeline** — человеческий способ видеть, обсуждать и продолжать работу: сообщения, действия пользователей, AI, уведомления, результаты и решения в хронологическом контексте.
3. **Control plane вычислений** — выбор сценариев, параметры, запуск, очередь, прогресс, логи, ошибки, повторы, каскады, фоновые выполнения и результаты.

Главный UX-принцип: **эти три модели должны пересекаться, но не дублировать друг друга**. Пользователь должен всегда понимать, где он находится, что выбрано, что сейчас выполняется и где появился результат.

Текущая архитектура `stratbox-windows` уже движется в правильную сторону: есть трёхзонная desktop-композиция, сценарный чат, Проводник, сценарии/каскады, кейсы, события, логи, артефакты, участники, поручения, фоновые процессы и правый инспектор. Однако текущая навигационная модель перегружает верхний уровень: часть сущностей является полноценными рабочими поверхностями, а часть — лишь состояниями или атрибутами других сущностей.

**Целевая верхнеуровневая IA:**

```text
Strategy Box
├── Работа       ← диалоги / история / AI / совместная работа / события
├── Проводник    ← workspace / файлы / результаты / lineage
├── Сценарии     ← атомарные сценарии + каскады + пресеты
└── Запуски      ← активные / очередь / фоновые / завершённые / ошибки
```

Всё остальное становится контекстом этих четырёх поверхностей:

```text
Каскад        = тип сценария
Фоновая задача = режим / тип запуска
Участник      = участник диалога, запуска или узла
Поручение     = action item внутри работы / запуска / артефакта
Лог           = техническая поверхность запуска
Артефакт      = результат запуска
Узел          = runtime context / service surface
Диагностика   = служебное действие / health surface
AI            = actor + orchestrator в рабочем диалоге, а не отдельное приложение
```

Это позволяет сохранить интерфейс лёгким даже при росте функций в разы.

---

# 1. Источники и рамка исследования

## 1.1. Внутренние материалы

В качестве исходной фактической базы использованы проектные исследования:

- `stratbox-windows_current_state_full_research_2026-10-06.md`;
- `stratbox_base_study_current_state_2026-10-06.md`;
- `AppDock - Базовое описание.docx`.

Ключевая граница сохраняется: `stratbox` остаётся предметным core, `stratbox-windows` владеет application/surface-слоем, AppDock — жизненным циклом и управляемой средой.

## 1.2. Внешние референсы

Проверены актуальные официальные руководства и продуктовые паттерны:

- Microsoft Windows App / WinUI: NavigationView, TreeView, BreadcrumbBar, CommandBar, InfoBar, List/Details, responsive breakpoints;
- Fluent 2: layout, typography, color, design tokens, toolbar;
- Windows 11 File Explorer: navigation pane, tabs, content pane, details pane, toolbar, search, Quick Access;
- Apple Human Interface Guidelines: sidebars, split views, toolbars, panels/inspectors, search, progress, lists/tables, context menus, keyboard;
- Visual Studio Code UX Guidelines: Activity Bar, sidebars, panel, status bar, notifications, Quick Pick / command-style interactions;
- GitHub Actions: run → job → step → logs, searchable logs and artifacts;
- OpenAI ChatGPT desktop: global mode switcher, unified Recents, Projects, sidebar search and cross-device continuation.

Исследование использует эти продукты как **паттерны поведения**, а не как визуальные шаблоны для буквального копирования.

---

# 2. Что Strategy Box должен ощущаться как продукт

## 2.1. Не dashboard

Strategy Box не следует превращать в dashboard из десятков карточек. Dashboard хорош для наблюдения за KPI, но здесь пользователь должен:

- находить данные и файлы;
- выбирать вычислительную операцию;
- задавать параметры;
- запускать действие;
- следить за прогрессом;
- видеть результат;
- понимать ошибку;
- продолжать работу с результатом;
- возвращаться к прошлой работе;
- взаимодействовать с другими людьми и AI.

Для этого нужен **workbench**, а не витрина.

## 2.2. Не IDE

VS Code и другие IDE дают полезные паттерны — activity rail, contextual sidebar, bottom panel, command palette, status bar, логические панели. Но Strategy Box не должен требовать от аналитика ощущения, что он работает в среде разработчика.

От IDE стоит взять:

- ясные зоны интерфейса;
- быстрый keyboard-first доступ;
- collapsible panels;
- прозрачный runtime state;
- прогресс, логи, diagnostics;
- command palette;
- связь «объект → детали → действия».

Не стоит брать:

- чрезмерную плотность;
- бесконечные табы редакторов;
- техническую терминологию по умолчанию;
- постоянный терминал/console как центральный элемент.

## 2.3. Не обычный мессенджер

Мессенджер даёт лучший паттерн истории совместной работы: chronological timeline, actors, unread state, attachments, mentions, replies. Но сценарий расчёта имеет структурированное состояние и строгий lifecycle.

Поэтому «чат» Strategy Box должен показывать **не только сообщения**, а события работы:

```text
пользователь написал
→ AI предложил действие
→ пользователь подтвердил параметры
→ сценарий запущен
→ шаг 1 завершён
→ шаг 2 дал предупреждение
→ создан Excel
→ пользователь оставил комментарий
→ результат назначен коллеге на проверку
```

Именно это делает чат «сценарным».

## 2.4. Наиболее точная метафора

> **Strategy Box — рабочий стол аналитических операций, где история работы представлена как диалог, а вычисления — как прозрачные управляемые запуски.**

---

# 3. Базовая UX-доктрина

## 3.1. Один главный объект в каждый момент

На экране всегда должен существовать очевидный **active object**:

- диалог;
- файл/папка;
- сценарий;
- запуск;
- артефакт.

Левый контекст помогает выбрать объект, центр показывает его основное содержимое, правый инспектор — свойства и secondary actions.

## 3.2. Постоянный shell, меняющийся контекст

Оболочка не должна перестраиваться при каждом переходе. Пользователь должен выучить один ритм:

```text
Activity rail → Context sidebar → Main surface → Inspector
```

Это сочетает:

- Windows/Fluent NavigationView;
- Apple split-view;
- ChatGPT sidebar + main conversation;
- VS Code activity bar + contextual sidebar.

## 3.3. Progressive disclosure

Обычный пользователь видит:

- понятное название;
- статус;
- основные параметры;
- главный результат;
- следующую доступную команду.

Технические детали раскрываются по запросу:

- raw params;
- operation ID;
- source paths;
- полные timestamps;
- stack trace;
- raw logs;
- runtime metadata;
- provenance.

Система должна быть глубокой, интерфейс — спокойным.

## 3.4. Action before configuration

Пользователь приходит выполнить работу, а не настраивать платформу. Поэтому:

- основные сценарии должны запускаться с разумными defaults;
- advanced parameters свёрнуты;
- настройки среды находятся вне основного flow;
- diagnostics появляются контекстно при проблеме.

## 3.5. Status is content

В вычислительной системе статус — не декор.

Для каждого запуска пользователь должен видеть:

- queued / preparing / running / waiting / succeeded / warning / failed / cancelled;
- текущий этап;
- время начала;
- прогресс, если он измерим;
- что именно система сейчас делает;
- можно ли отменить;
- где лог;
- где результат.

---

# 4. Целевая информационная архитектура

## 4.1. Почему текущие шесть режимов стоит свернуть

Сегодня в левом rail присутствуют Проводник, Сценарии, Каскады, Фоновые, Участники, Поручения. Эта схема хорошо демонстрирует возможности, но долгосрочно смешивает разные уровни абстракции.

Сравнение:

| Сущность | Природа | Должна быть top-level? |
|---|---|---|
| Проводник | полноценная рабочая поверхность | да |
| Сценарии | каталог исполняемых возможностей | да |
| Каскады | разновидность ScenarioSpec | нет, внутри Сценариев |
| Фоновые | execution mode / queue state | нет, внутри Запусков |
| Участники | actors текущего контекста | нет, contextual |
| Поручения | task objects / inbox | обычно нет, contextual + global filter |

Если каждую будущую capability превращать в кнопку rail, interface entropy будет расти линейно с функциональностью.

## 4.2. Четыре устойчивые поверхности

### 1. Работа

Главная / default surface.

Содержит:

- историю диалогов;
- scenario-chat timeline;
- людей и AI;
- сообщения;
- run cards;
- approvals;
- assignments;
- уведомления;
- artifacts.

### 2. Проводник

Работа с workspace и результатами в Windows-подобной модели.

### 3. Сценарии

Каталог capability:

- атомарные;
- каскады;
- избранные;
- недавние;
- пресеты;
- поиск.

### 4. Запуски

Operational control plane:

- выполняются;
- очередь;
- ожидают пользователя;
- фоновые;
- завершены;
- ошибки;
- отменены.

## 4.3. Служебный слой

Верхний user/node menu:

- Узел;
- Состояние среды;
- Диагностика;
- Настройки;
- О приложении;
- Выход.

Служебные сущности не конкурируют с рабочей навигацией.

---

# 5. Целевая shell-композиция Windows

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Title bar / global search / command / node state / user                    │
├──────┬──────────────────────┬────────────────────────────┬──────────────────┤
│ Rail │ Context sidebar      │ Main surface               │ Inspector        │
│      │                      │                            │                  │
│ Work │ recent threads       │ scenario chat              │ selected object  │
│ Files│ folder tree          │ file list/content          │ details/preview  │
│ Scen │ categories/search    │ scenario catalogue/detail  │ params/history   │
│ Runs │ filters/queue        │ runs table/timeline        │ run details      │
│      │                      │                            │                  │
├──────┴──────────────────────┴────────────────────────────┴──────────────────┤
│ Optional execution panel: Output / Logs / Problems                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ Status bar: workspace · node · background jobs · warnings · version        │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 5.1. Activity rail

Назначение: только переключение между четырьмя главными режимами.

Требования:

- компактный icon + tooltip режим;
- selected state очень очевидный;
- label появляется при expanded state;
- badge допустим только для meaningful state: running jobs, unread work, errors;
- Settings не следует делать равноправным рабочим пунктом; он остаётся в footer/user menu;
- порядок стабилен и не меняется динамически.

## 5.2. Context sidebar

Sidebar меняет содержимое вместе с выбранным top-level mode.

### Работа

- New thread;
- Search;
- Pinned;
- Recent;
- фильтры;
- список диалогов.

### Проводник

- Quick access;
- Workspace root;
- Input;
- Output;
- Results/Artifacts;
- favorites;
- дерево каталогов.

### Сценарии

- Search;
- Favorites;
- Recent;
- категории;
- Atomic / Cascades selector.

### Запуски

- Running;
- Waiting;
- Background;
- Completed;
- Failed;
- фильтры по пользователю, сценарию, времени.

## 5.3. Main surface

Main surface всегда получает максимальную площадь. Она не должна быть зажата постоянными техническими панелями.

## 5.4. Inspector

Inspector — contextual details, а не ещё один навигатор.

Он должен:

- автоматически обновляться при выборе объекта;
- быть закрываемым;
- хранить последнее состояние;
- иметь width limits;
- уходить в overlay/drawer на более узком окне.

Типовые вкладки:

```text
Обзор | Параметры | Артефакты | История
```

Для запуска:

```text
Обзор | Шаги | Артефакты | Диагностика
```

Raw logs лучше открывать в bottom execution panel, потому что им нужна горизонтальная ширина.

---

# 6. Проводник: максимально знакомый Windows-паттерн

Проводник Strategy Box — зона, где особенно важна мышечная память Windows. Здесь «оригинальность» интерфейса скорее вредна.

## 6.1. Что повторять у Windows File Explorer

Следует воспроизвести семантику:

```text
Tabs (опционально позже)
Navigation pane
Toolbar / command bar
Back / Forward / Up / Refresh
Breadcrumb path
Search
Content pane
Details/List/Icon views
Optional details/preview pane
Context menus
Keyboard navigation
```

Не требуется пиксельно копировать Explorer. Требуется, чтобы действия ощущались знакомо.

## 6.2. Верхняя строка Проводника

```text
←  →  ↑   [Workspace > output > escrow]            [Search]
New  Open  Refresh  Sort  View  More
```

Порядок действий:

- navigation controls;
- breadcrumb;
- search;
- context actions.

Breadcrumb должен быть настоящей навигацией, а не декоративным path label.

## 6.3. Navigation tree

- chevrons expand/collapse;
- folder icons;
- persistent selection;
- current folder automatically раскрывается в tree по настройке;
- roots отделены группами;
- максимум два уровня специальных virtual sections до реального дерева.

Предлагаемые virtual roots:

```text
Quick access
Workspace
  input
  output
Artifacts
```

Ниже — реальное дерево файловой системы.

## 6.4. Content pane

Default view для аналитического продукта — **Details**, а не tiles.

Базовые столбцы:

- Name;
- Type;
- Modified;
- Size.

Опциональные Strategy Box columns:

- Scenario;
- Run;
- Created by;
- Status / provenance.

Эти дополнительные колонки включаются через View settings, чтобы не разрушать знакомую файловую модель.

## 6.5. Details / Preview

Правая pane внутри Explorer может отображать:

- metadata;
- preview;
- originating scenario/run;
- source/provenance;
- связанные artifacts;
- Open / Reveal / Copy path.

Если общий App Inspector уже открыт, отдельный Explorer preview не должен создавать четвёртую постоянную колонку. Нужно использовать тот же Inspector с mode-specific content.

## 6.6. Context menu

Windows-подобный порядок:

```text
Open
Open with...
Reveal / Show in Explorer
Copy path
────────
Rename
Copy / Move (если поддерживается)
────────
Delete (если разрешено)
────────
Properties / Details
```

Strategy-specific commands можно добавить отдельной группой:

```text
Use as scenario input
Open originating run
Show lineage
```

## 6.7. Опасные файловые операции

Если интерфейс разрешает destructive operations:

- не скрывать их в автоматических fallback;
- явно показывать target;
- для массовых действий показывать plan;
- для необратимых действий давать confirmation;
- после выполнения показывать factual result, а не optimistic toast.

## 6.8. Keyboard behavior

Минимум:

- Enter — open;
- Backspace / Alt+Left — back;
- Alt+Right — forward;
- Alt+Up — parent;
- F2 — rename, если разрешено;
- Ctrl+L — focus path;
- Ctrl+F — local search;
- Ctrl+C — copy object/path по контексту;
- Delete — только при разрешённой модели удаления;
- F6 / Shift+F6 — cycle major panes.

---

# 7. Сценарии и каскады

## 7.1. Scenario — не «скрипт»

В пользовательском интерфейсе основное слово — **Сценарий**.

Термины module/function/handler/operation ID остаются technical details.

Scenario card/list item показывает:

- название;
- короткое назначение;
- category;
- тип: atomic / cascade;
- requires network / workspace при необходимости;
- expected outputs;
- last run status/time;
- favorite marker.

## 7.2. Atomic и Cascade — один каталог

Вместо двух top-level кнопок:

```text
Сценарии
[Все] [Атомарные] [Каскады] [Избранные]
```

Почему:

- пользователь ищет «что сделать», а не «какой engine class использовать»;
- поиск должен находить оба типа;
- favorite/recent работают одинаково;
- future scenario types не потребуют новых navigation buttons.

## 7.3. List first, cards second

При небольшом каталоге карточки выглядят хорошо. При десятках/сотнях сценариев они становятся медленными для scanning.

Целевая модель:

- compact list/table — default;
- cards — optional browse view;
- быстрый поиск — основной discovery mechanism.

## 7.4. Scenario detail

Main detail:

```text
Название
Описание
Expected result
Inputs / outputs
Последний запуск

[Run]
```

Inspector:

- Parameters;
- Advanced;
- Presets;
- History;
- Permissions / requirements.

## 7.5. Parameter forms

Параметры должны строиться declaratively из specs.

Правила:

- basic first;
- advanced collapsed;
- reasonable defaults;
- inline validation;
- error рядом с полем;
- path picker с текущим workspace;
- enum → select;
- dates → date control;
- boolean → switch/checkbox;
- числа → numeric input;
- derived/locked values показывать как readonly summary, а не editable control.

## 7.6. Presets

Для повторяемой аналитики важны user presets:

```text
«Ежемесячное обновление»
«Только новые файлы»
«Полный rebuild»
```

Preset хранит только параметры, а не копию сценария.

## 7.7. Cascade representation

Основной вид каскада — **вертикальный список шагов**, а не flowchart.

```text
1  Collect sources
2  Validate
3  Build dataset
4  Export workbook
```

Для branching/parallel workflow позже можно добавить graph view как secondary visualization.

В обычной работе пользователь чаще хочет понять:

- что пойдёт первым;
- где сейчас процесс;
- на каком шаге ошибка;
- что можно повторить.

Для этого step list эффективнее DAG.

---

# 8. Запуски как отдельный control plane

## 8.1. Почему нужен отдельный режим «Запуски»

Messenger timeline отлично отвечает на вопрос «что происходило в контексте работы». Он хуже подходит для вопроса «что прямо сейчас выполняется во всей системе».

Поэтому нужен operational list.

## 8.2. Состояния запуска

Рекомендуемый общий vocabulary:

```text
queued
preparing
running
waiting_user
paused
succeeded
succeeded_with_warnings
failed
cancelled
blocked
unavailable
```

В UI — русские labels.

Каждый статус имеет:

- icon;
- text;
- semantic color;
- accessibility label.

Цвет никогда не является единственным сигналом.

## 8.3. Runs table

Столбцы:

- Scenario;
- Status;
- Stage;
- Started;
- Duration;
- Author;
- Mode (foreground/background/remote в будущем);
- Artifacts.

Default sorting:

1. running/waiting;
2. newest first.

## 8.4. Active run row

Живой запуск показывает:

- current stage;
- determinate progress, когда реальный denominator известен;
- elapsed time;
- Cancel/Pause только если engine действительно поддерживает безопасное действие;
- link/open chat;
- link/open log.

Никогда не рисовать fake progress от 0 до 100 по времени.

## 8.5. Background execution

«Фоновый процесс» перестаёт быть отдельным продуктовым миром.

Он отображается в Runs как:

```text
Mode: Background
Trigger: schedule / event / manual
Next run: ...
```

Для recurring automation можно иметь отдельный secondary view «Автоматизации», когда такой engine реально появится.

---

# 9. Scenario Chat — центральная поверхность Strategy Box

Это наиболее важная часть всей концепции.

## 9.1. Критический сдвиг модели: Dialog ≠ Run

Текущая ранняя модель близка к «один case = один scenario run». Для будущего взаимодействия пользователей и AI этого станет мало.

Целевая модель должна разделить:

```text
Dialog / Work Thread
    ├── human messages
    ├── AI messages
    ├── run #1
    ├── artifact
    ├── comment
    ├── assignment
    ├── run #2
    └── decision / approval
```

**Run** — отдельное выполнение сценария.  
**Dialog** — долгоживущий контекст совместной работы.

Это один из важнейших архитектурных выводов данного исследования.

Пример:

```text
Диалог: «ЦБ — обновление на октябрь»

Дима: Обнови данные и собери итоговую выгрузку.
AI: Предлагаю запустить каскад «Обновление ЦБ» с параметрами ...
[Run proposal]
Дима: Запустить.
[Run #184 · Running · 2/4]
System: Источник X изменил схему.
AI: Второй шаг остановился. Могу повторить с новым parser profile после проверки.
Дима: Повтори.
[Run #185 · Success]
[Artifact: cbr_2026_10.xlsx]
Коллега: Проверил, можно использовать.
```

Это уже полноценный «messenger + compute» без притворства, что вычисление является обычным сообщением.

## 9.2. Типы элементов timeline

### Human message

Обычный conversational block.

### AI message

Визуально близок к human message, но actor явно обозначен.

### Run card

Структурированная карточка:

- scenario;
- params summary;
- status;
- stage/progress;
- duration;
- outputs;
- actions.

### Artifact card

- icon/type;
- filename/title;
- source run;
- open/reveal/download-like internal action;
- preview if useful.

### System event

Компактная строка, по умолчанию свёрнута:

```text
14:32 · Run #184 started
14:33 · Step «Download» completed
```

### Warning/error

Inline callout, связанный с run/step, а не отдельный красный «чат-пузырь».

### Assignment / approval

Action card с assignee/status/due date в будущем.

## 9.3. Что не превращать в сообщения

Не следует спамить timeline:

- каждым log line;
- heartbeat;
- техническими retry;
- каждым внутренним state mutation;
- background polling.

Timeline — история **значимых событий**, raw log — отдельная поверхность.

## 9.4. History sidebar

ChatGPT-подобный паттерн подходит почти идеально:

```text
Search
New work
Pinned
Today
Yesterday
Previous 7 days
...
```

Дополнительные filters:

- Mine;
- Shared;
- Running;
- Has errors;
- Has unread;
- Has assignment.

Поддержать:

- pin;
- rename;
- archive;
- sort by last activity;
- optional manual ordering later.

## 9.5. Composer

Composer не должен становиться формой из десяти контролов.

Целевая модель:

```text
[ + ] [context chips]  Write / ask / command...                    [Send]
```

Внутри одного composer доступны modes/tools:

- Message;
- Ask AI;
- Run scenario;
- Attach artifact/file;
- Mention user.

Для запуска сценария composer вставляет structured run draft:

```text
Run: Escrow history
Period: 2026-01 ... 2026-09
Output: XLSX
[Edit parameters] [Run]
```

Сложные параметры открываются в inspector или lightweight sheet.

## 9.6. AI внутри чата

AI не должен получать отдельную «AI вкладку». Он естественно живёт в том же рабочем контексте.

AI умеет:

- объяснять данные;
- находить сценарий;
- предлагать параметры;
- сравнивать runs;
- читать structured status;
- объяснять ошибку;
- предлагать следующий шаг;
- запускать разрешённые операции после policy/approval;
- работать с artifacts.

Критический UX-принцип:

> **текст AI и действие AI — разные визуальные сущности.**

Если AI собирается запустить вычисление, пользователь видит action proposal:

```text
AI proposes
Scenario: ...
Parameters: ...
Writes: ...
Network: yes
Expected outputs: ...
Risk: safe / destructive

[Run] [Edit] [Reject]
```

После запуска proposal превращается в обычный Run object.

## 9.7. Люди и совместная работа

Participants отображаются:

- avatars в header диалога;
- actor names в timeline;
- filter «Mine / All»;
- mentions;
- assignment actions.

Отдельный global экран «Участники» нужен только при развитом team-management. На ранних и средних стадиях он создаёт лишний top-level mode.

---

# 10. Логи: как сделать техническую глубину понятной

## 10.1. Три уровня observability

### Уровень 1 — обычный пользователь

В run card:

```text
Running · Step 2 of 4 · Parsing workbook
```

### Уровень 2 — diagnostic summary

В Inspector:

```text
Steps
✓ Discover sources     2.1 s
✓ Download             8.4 s
! Parse                warning
○ Export
```

### Уровень 3 — raw log

В отдельном execution panel:

```text
Output | Logs | Problems
```

## 10.2. Почему raw log лучше в bottom panel

Лог требует горизонтального пространства, поиска и иногда длинных строк. Узкий right inspector для него плох.

VS Code-подобная нижняя панель здесь оправдана, если:

- по умолчанию закрыта;
- открывается по «View log»;
- remembers height;
- не является главным способом работы.

## 10.3. Log viewer requirements

- monospace;
- line timestamps optional;
- severity marker;
- search;
- filters: info/warning/error/debug;
- wrap toggle;
- auto-scroll toggle;
- copy line / copy selection;
- copy technical details;
- «show only failed step»;
- «open log file»;
- export/copy path;
- line virtualization для больших логов;
- live append без freezing UI.

## 10.4. Ошибка

Главный error presentation:

```text
Не удалось построить workbook
Step: Export
Cause: output file is locked

[Повторить] [Выбрать другой файл] [Открыть лог]
```

Stack trace — под «Technical details».

Ошибка должна объяснять **что делать дальше**, если система это знает.

## 10.5. Notifications

Не показывать toast на каждое успешное действие.

Toast / notification нужен, когда:

- background run завершился и пользователь находится в другом контексте;
- требуется решение;
- произошла ошибка вне текущего экрана;
- изменилось глобальное состояние среды.

Все остальные события остаются inline.

---

# 11. Inspector

Inspector — один из наиболее ценных паттернов Apple/Windows для Strategy Box.

## 11.1. Принцип

Выбирается объект — inspector показывает его свойства.

Не нужно открывать отдельные dialogs для каждого файла/run/scenario.

## 11.2. Для Scenario

- Overview;
- Parameters;
- Presets;
- Last runs;
- Inputs/outputs.

## 11.3. Для Run

- status;
- author;
- start/end/duration;
- steps;
- params;
- artifacts;
- warnings;
- provenance;
- rerun/cancel actions.

## 11.4. Для File/Artifact

- type;
- path;
- size;
- modified;
- originating run;
- source lineage;
- preview;
- open/reveal.

## 11.5. Для Dialog

- participants;
- pinned artifacts;
- linked runs;
- assignments;
- created/updated.

---

# 12. Служебные панели, узел и диагностика

## 12.1. Node state должен быть видим, но тихо

Bottom status bar:

```text
Workspace: Ready   Node: Local   Jobs: 2   ⚠ 1
```

Click → popover / drawer:

- node identity;
- data availability;
- health;
- session;
- environment;
- refresh;
- diagnostics.

## 12.2. Degraded state

Если workspace недоступен, приложение не должно выглядеть «сломавшимся».

Показывается persistent inline InfoBar:

```text
Workspace unavailable. Scenarios requiring data are temporarily disabled.
[Reconnect] [Diagnostics]
```

При этом:

- история открывается;
- настройки доступны;
- диагностика доступна;
- сценарии, не требующие workspace, могут работать.

## 12.3. Settings

Разделение текущих настроек на User / Workspace / System логично сохранить.

Целевые группы:

### Appearance

- Theme: System/Light/Dark;
- Density: Comfortable/Compact;
- Reduced motion;
- font scaling через OS.

### Work

- startup mode;
- recent/history preferences;
- default scenario behavior;
- log verbosity for user surface.

### Workspace

- active root/schema;
- safe file behavior;
- cache/result policies.

### System

- diagnostics;
- runtime info;
- version/build;
- experimental flags, если они реально нужны.

---

# 13. Global search и command palette

Strategy Box быстро перерастёт обычную navigation hierarchy. Нужен один быстрый способ найти всё.

## 13.1. Global search

Search results categories:

- Dialogs;
- Scenarios;
- Runs;
- Files;
- Artifacts;
- Commands.

Search field может находиться в title bar.

## 13.2. Command palette

Shortcut:

```text
Ctrl+Shift+P
```

Примеры:

```text
> Run scenario...
> Open workspace...
> Show running jobs
> Diagnostics
> Toggle inspector
> Toggle execution panel
> Change theme
```

Для сценариев можно использовать Quick Pick-подобный launcher:

```text
Ctrl+P / Ctrl+K
Search scenarios, files, runs...
```

Не следует создавать десятки toolbar buttons, если действие легче найти через palette/context menu.

---

# 14. Visual language

## 14.1. Общий стиль

Требуемое ощущение:

- современный;
- лёгкий;
- тихий;
- профессиональный;
- desktop-native;
- без «корпоративного портала 2014»;
- без gaming/control-room aesthetics;
- без перегруженных dashboard cards.

## 14.2. Windows как host language

На Windows стоит использовать:

- Segoe UI Variable / system font;
- Windows-like control sizes;
- familiar icon metaphors;
- native window chrome / integrated title area;
- system accent;
- light/dark/high contrast;
- restrained Mica/Acrylic-like depth там, где технически устойчиво.

Не следует строить собственную «экзотическую» тему поверх Windows.

## 14.3. Что взять у Apple

Не внешний macOS skin, а дисциплину:

- большие спокойные content areas;
- sidebar + content + inspector;
- минимум разделителей;
- whitespace для hierarchy;
- toolbar только с частыми actions;
- secondary details в inspector;
- адаптивное скрытие панелей.

## 14.4. Что взять у ChatGPT

- conversation-first center;
- спокойная типографика;
- unified recent history;
- search по истории;
- pinned work;
- contextual composer;
- минимум визуальных рамок вокруг каждого элемента;
- AI as participant in work, а не отдельная «магическая кнопка».

## 14.5. Spacing

Предлагаемая token scale:

```text
4  8  12  16  24  32  48
```

Плотные списки используют 4/8/12.  
Основные content sections — 16/24.  
Крупные empty-state / onboarding — 32/48.

## 14.6. Radius

- small controls: 4–6;
- inputs/buttons: 6–8;
- cards/callouts: 8–12;
- избегать чрезмерно «пузырчатого» UI.

## 14.7. Borders vs surfaces

Основная иерархия строится через:

- surface tone;
- spacing;
- selection fill;
- subtle separator.

Не через рамку вокруг каждого блока.

## 14.8. Status colors

Использовать semantic tokens:

- success;
- warning;
- danger;
- info;
- neutral.

Цвет бренда не должен подменять status semantics.

---

# 15. Typography

Предлагаемая scale:

```text
12  metadata / captions
13–14  compact rows / secondary text
14–15  body / primary lists
16–18  section / selected object title
20–24  page title
```

Правила:

- основной текст left-aligned;
- line-height свободнее, чем в IDE;
- uppercase почти не используется;
- labels короткие;
- secondary metadata light/neutral, но с доступным contrast;
- моноширинный шрифт только для logs/IDs/paths/code.

---

# 16. Responsive и adaptive behavior

Desktop surface должна проектироваться по **ширине окна**, а не по разрешению монитора.

Рекомендуемые режимы:

## Large: ≥ 1400 logical px

```text
rail + sidebar + main + inspector
```

Inspector может быть 320–400 px.

## Standard desktop: 1008–1399

```text
rail + sidebar + main
inspector collapsible/overlay
```

## Medium: 641–1007

```text
compact rail + main
sidebar overlay
inspector drawer
```

## Small: ≤ 640

```text
single-pane stack
```

Это уже почти модель будущего mobile surface.

Панели должны иметь sensible min/max sizes. Пользовательские размеры сохраняются.

---

# 17. Переиспользование для будущего Android

Ключевое правило: **копировать semantic surface, не desktop layout**.

Общее между Windows и Android:

```text
navigation destinations
scenario definitions
run states
thread/timeline model
message/run/artifact event models
parameter form schema
inspector/detail projections
search semantics
status vocabulary
permissions/action availability
```

Windows:

```text
rail + sidebar + main + inspector + bottom panel
```

Android:

```text
bottom navigation / compact navigation
single main surface
bottom sheets / detail pages
system notifications
```

В Android логично оставить 4–5 destinations:

```text
Работа | Сценарии | Запуски | Файлы | Ещё
```

Desktop-specific widgets и Qt signals не должны определять application semantics.

---

# 18. Object model, который должен видеть UX

## Workspace

Контейнер файлов и локального рабочего контекста.

## Scenario

Повторяемое описание действия.

## Cascade

Scenario, состоящий из нескольких шагов/operations.

## Dialog / Work Thread

Долгоживущий контекст совместной работы.

## Run

Конкретное исполнение Scenario.

## Step

Стадия Run.

## Event

Значимое изменение состояния или событие timeline.

## Artifact

Результат Run.

## Log

Техническое свидетельство execution.

## Participant

Actor: user / AI / system / host user.

## Assignment

Action item, привязанный к thread/run/artifact.

## Node

Среда, в которой выполняется работа.

Эта модель должна быть стабильной и одинаково читаться Windows/Android/remote surface.

---

# 19. UI states: обязательная матрица

Каждая крупная поверхность должна иметь явные состояния.

## Empty

Объяснить, что здесь появится и какое первое действие доступно.

## Loading

Skeleton/indicator без layout jump.

## Ready

Normal state.

## Running

Progress + current activity.

## Partial

Часть данных есть, часть завершилась с предупреждениями.

## Waiting for user

Ясное actionable state.

## Error

Причина + recovery action.

## Degraded

Поверхность доступна частично.

## Offline / unavailable

Понятное описание, что недоступно и что сохранено локально.

## Permission denied

Объяснить недоступное действие без раскрытия лишней инфраструктурной информации.

---

# 20. Performance и responsiveness requirements

Это интерфейс вычислительной платформы; perceived performance критичнее декоративной анимации.

Целевые UX-ориентиры:

- click/selection feedback — практически мгновенно;
- открытие локальной панели — без ощутимой задержки;
- никакая аналитическая операция не блокирует UI thread;
- прогресс обновляется достаточно часто, чтобы интерфейс ощущался живым, без flood;
- file list и runs list используют model/view virtualization;
- raw log viewer способен работать с очень большими логами без полной перерисовки;
- history загружается incremental/lazy;
- preview тяжёлого artifact не блокирует основной shell.

Для реализации на Qt особенно важно:

- `QAbstractItemModel`/`QTableView` для крупных списков;
- `QPlainTextEdit` или специализированный model-based viewer для logs;
- worker threads/process backend без UI object leakage;
- throttled progress events;
- lazy thumbnails/previews.

---

# 21. Accessibility

Минимальные требования:

- полноценная keyboard navigation;
- правильный focus order;
- visible focus state;
- screen reader names/roles;
- tooltips для icon-only actions;
- contrast >= WCAG expectations;
- status не кодируется только цветом;
- high contrast theme;
- light/dark/system mode;
- reduced motion;
- scaling 125/150/200%;
- hit targets не становятся микроскопическими в compact density;
- drag-and-drop всегда имеет keyboard/menu alternative.

---

# 22. Security / enterprise UX

Для банковского/корпоративного применения UI должен отражать доверие и контроль без постоянных страшных диалогов.

## 22.1. Risk classes действий

### Safe read-only

Запускается сразу.

### Side-effect write

Показывается понятный target/output.

### Destructive

Требует явного confirmation с объектом и последствиями.

### Elevated / external

Показывает, что будет использовано/отправлено, и policy-controlled approval.

## 22.2. AI actions

AI получает тот же action policy, что и человек.

AI не должен:

- скрывать точные параметры запуска;
- запускать destructive operation из обычного текста;
- изображать успех до фактического result;
- маскировать ошибку красивым summary.

## 22.3. Logs

- redaction secrets;
- безопасное copy technical details;
- distinction user-facing vs diagnostic logs;
- audit actor/run linkage.

---

# 23. Keyboard-first режим для опытных пользователей

Рекомендуемые shortcuts:

```text
Ctrl+N          New work/dialog
Ctrl+P          Quick open
Ctrl+Shift+P    Command palette
Ctrl+F          Search in current surface
Ctrl+Shift+F    Global search
Ctrl+L          Focus path / location in Explorer
Alt+Left        Back
Alt+Right       Forward
Alt+Up          Parent in Explorer
Ctrl+,          Settings
Esc             Close overlay / cancel transient mode
F6              Cycle major panes
```

Scenario-specific shortcuts следует добавлять только после появления устойчивых частых действий.

---

# 24. Motion

Motion должен объяснять структуру:

- inspector slide 120–180 ms;
- sidebar expand/collapse;
- run status transitions;
- subtle progress;
- artifact insertion.

Не использовать:

- bouncing;
- decorative parallax;
- длинные page transitions;
- animation, которая задерживает action.

Reduced motion полностью поддерживается.

---

# 25. Empty states и onboarding

## Первый запуск

Не wizard на 8 экранов.

Main surface:

```text
Strategy Box готов к работе

[Открыть сценарии]
[Открыть workspace]
[Запустить диагностику]
```

При наличии recent context — сразу восстановить его.

## Empty chat

Показать:

- 3–5 recent/favorite scenarios;
- «Ask AI» only when capability реально подключена;
- examples based on available operations.

## Empty runs

```text
Здесь появятся активные и прошлые запуски.
[Выбрать сценарий]
```

---

# 26. Артефакты как first-class output

Artifact должен быть больше, чем path.

Целевая metadata:

```text
artifact_id
name
type
path/location
created_at
created_by
scenario_id
run_id
step_id
size/hash when available
preview_kind
provenance/lineage
```

UX возможности:

- Open;
- Reveal;
- Pin to thread;
- Copy path;
- Show originating run;
- Use as input to scenario;
- compare versions later.

Artifact chaining — один из сильнейших будущих паттернов Strategy Box.

---

# 27. Поручения и approvals

Не выделять отдельный rail mode на ранней стадии.

Поручение отображается:

- в thread timeline;
- в run/artifact inspector;
- в global Work filter «Assigned to me»;
- в notification, если действительно требует внимания.

Будущий task center оправдан, когда появятся:

- десятки активных поручений;
- deadlines;
- SLA;
- team queues;
- comments;
- approvals.

До этого отдельный экран создаёт пустую архитектуру.

---

# 28. Participants / presence

Presence — ambient information.

Header thread:

```text
[avatar] [avatar] +2
```

Popover:

- name;
- online/recent;
- host/device при необходимости;
- role.

Не следует постоянно занимать отдельную колонку списком людей, если collaboration не является основной задачей данного момента.

---

# 29. Как смешать Microsoft, Apple и ChatGPT без визуальной каши

## Microsoft даёт каркас поведения

- NavigationView;
- File Explorer familiarity;
- command bars;
- adaptive desktop controls;
- system theme;
- Windows interaction expectations.

## Apple даёт дисциплину композиции

- sidebar/content/inspector;
- whitespace;
- contextual toolbars;
- quiet panels;
- resize/hide/show.

## ChatGPT даёт центр взаимодействия

- conversation as primary surface;
- recents/history;
- one composer;
- contextual tools;
- AI integrated into work.

## VS Code даёт operational depth

- activity rail;
- contextual sidebar;
- bottom panel;
- status bar;
- command palette;
- logs/problems separation.

## Итог Strategy Box

Не «50/50 Microsoft + Apple».  
Не «ChatGPT с зелёными кнопками».  
А собственный продуктовый язык:

> **Windows-native shell + Apple-like spatial discipline + ChatGPT-like work timeline + VS Code-like execution transparency.**

---

# 30. Что стоит изменить относительно текущей surface

## P0 — информационная архитектура

1. Свести top-level navigation к четырём durable modes.
2. Перенести Cascades внутрь Scenarios.
3. Перенести Background внутрь Runs.
4. Participants сделать contextual.
5. Assignments сделать contextual/global-filtered.
6. Node/Diagnostics оставить служебными surfaces.

## P0 — отделить Dialog от Run

Ввести долгоживущий WorkThread/Dialog, который может содержать много runs, сообщений, artifacts и assignments.

## P0 — привести Explorer к Windows mental model

- breadcrumb;
- command bar;
- search;
- navigation tree;
- details view;
- standard context menu;
- familiar keyboard behavior.

## P1 — operational panel

Добавить optional bottom panel для raw logs / problems.

## P1 — unified search

Один global search + command palette.

## P1 — design tokens

Убрать ad-hoc styling. Ввести semantic tokens для:

- surface;
- text;
- accent;
- status;
- spacing;
- radius;
- typography;
- elevation;
- motion.

## P1 — adaptive shell

Inspector/sidebar должны корректно collapse/overlay на narrow window.

## P2 — collaboration

Доводить presence/assignments только вместе с настоящим backend contract.

## P2 — AI

Добавлять AI через action proposals и existing scenario/run contracts, а не через shell/terminal access.

---

# 31. Acceptance criteria для интерфейса

## Navigation

- пользователь всегда видит выбранный top-level mode;
- Back/Forward работают предсказуемо;
- selection persists при работе с inspector;
- pane resize сохраняется;
- narrow mode не ломает функциональность.

## Scenario run

- типовой сценарий можно найти через search или catalog;
- basic run не требует знания operation IDs;
- параметры валидируются до запуска;
- run появляется в timeline и Runs сразу;
- progress не блокирует UI;
- result открывается одним действием.

## Error

- видно failed step;
- виден human-readable cause;
- доступен recovery action;
- raw log доступен, но не навязан;
- failed run остаётся в истории.

## Explorer

- Windows user узнаёт модель за секунды;
- path всегда понятен;
- back/up/search работают привычно;
- Details view удобен для больших каталогов;
- Strategy metadata доступна без разрушения файлового интерфейса.

## Chat / Work

- timeline содержит только meaningful events;
- AI/human/system/run visually distinguishable;
- run card не выглядит как обычное сообщение;
- история searchable;
- thread может содержать несколько запусков.

## Accessibility

- все ключевые flows доступны keyboard-only;
- status различим без цвета;
- high contrast не ломает hierarchy;
- scaling не обрезает controls.

---

# 32. Предлагаемый первый target screen

Наиболее полезный эталонный экран для следующей переработки:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Strategy Box     [ Search or run anything... ]        Local · Ready   [D]   │
├────┬───────────────────────┬───────────────────────────────┬─────────────────┤
│ 💬 │ Работа                │ ЦБ — октябрь                 │ Контекст         │
│ 📁 │ + Новый диалог        │                               │                 │
│ ▶  │ Search                │ Дима  13:02                  │ Участники       │
│ ◉  │                       │ Обнови данные...             │ Artifacts       │
│    │ Pinned                │                               │ Assignments     │
│    │ • Ежемесячный ЦБ      │ AI  13:02                    │                 │
│    │                       │ Предлагаю запустить...       │                 │
│    │ Today                 │ [Run proposal]               │                 │
│    │ • ЦБ — октябрь        │                               │                 │
│    │ • Escrow              │ [Run #185 Running 2/4]       │                 │
│    │                       │ ███████░░░ Parse             │                 │
│    │                       │                               │                 │
│    │                       │ [ + ] Message / Ask / Run... │                 │
├────┴───────────────────────┴───────────────────────────────┴─────────────────┤
│ Output | Logs | Problems                                    (collapsed)     │
├──────────────────────────────────────────────────────────────────────────────┤
│ Workspace Ready   Node Local   1 running   0 errors               v0.x     │
└──────────────────────────────────────────────────────────────────────────────┘
```

Этот экран одновременно демонстрирует:

- platform shell;
- ChatGPT-like history;
- collaboration;
- AI;
- script/run control;
- inspectability;
- runtime state.

Если эта поверхность получается простой и естественной, остальная IA складывается вокруг неё.

---

# 33. Второй target screen: Проводник

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Strategy Box     [ Global search ]                         Local · Ready      │
├────┬───────────────────────┬───────────────────────────────┬─────────────────┤
│ 💬 │ Quick access          │ ← → ↑  Workspace > output    │ Details         │
│ 📁 │                       │ [Search output]               │                 │
│ ▶  │ Workspace             │ New  Refresh  Sort  View ... │ escrow.xlsx     │
│ ◉  │  ▾ input              │                               │ Excel workbook  │
│    │  ▾ output             │ Name         Modified   Size │                 │
│    │     escrow            │ escrow.xlsx  13:05      4 MB │ From run #185   │
│    │     cbr               │ cbr.zip      12:42     20 MB │                 │
│    │  artifacts            │                               │ [Open]          │
│    │                       │                               │ [Show run]      │
├────┴───────────────────────┴───────────────────────────────┴─────────────────┤
│ Workspace Ready   Node Local   0 running                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

Пользователь должен почти мгновенно считать этот экран как знакомый файловый менеджер, при этом Strategy Box добавляет lineage и связь с вычислениями.

---

# 34. Третий target screen: Сценарии

```text
Сценарии
[Search scenarios...]   [All] [Atomic] [Cascades] [Favorites]

Название                         Тип       Последний запуск    Статус
Обновление данных ЦБ             Cascade   Сегодня 13:05       Success
История счетов эскроу            Atomic    Вчера 09:12         Success
Загрузчик исходных файлов ЦБ     Atomic    Сегодня 12:40       Warning

─────────────────────────────────────────────────────────────
Selected: Обновление данных ЦБ

Получает официальные источники, проверяет данные и формирует outputs.

Steps
1 Collect sources
2 Validate
3 Build history
4 Export

[Run]   [Parameters]   ☆ Favorite
```

---

# 35. Технические последствия для `stratbox-windows`

Этот Research не является code plan, но UX-требования подразумевают несколько architecture changes.

## 35.1. Thread model

Нужна platform-neutral сущность наподобие:

```text
WorkThread
ThreadMessage
ThreadEventRef
ThreadRunRef
ThreadArtifactRef
```

Она отделяет collaboration context от `ScenarioRunCase`.

## 35.2. Unified execution model

Foreground/background/remote должны различаться execution mode/backend, а не отдельными пользовательскими subsystems.

## 35.3. Presentation/common

Следует расширить platform-neutral projections:

```text
NavigationState
WorkThreadViewModel
RunListViewModel
ScenarioCatalogViewModel
ExplorerItemViewModel
InspectorModel
StatusBarModel
GlobalSearchResult
ActionAvailability
```

## 35.4. Qt-specific layer

Qt layer отвечает за:

- widgets;
- painting;
- splitters/drawers;
- keyboard focus;
- drag/drop;
- animations;
- Qt model adapters.

Он не должен владеть semantics run/thread/scenario.

## 35.5. Logs

Raw log surface должна быть отдельным projection/service, а не текстом, который UI собирает из случайных файлов.

## 35.6. Search

По мере роста потребуется единый searchable index над metadata, но первая версия может агрегировать registries/services без отдельной БД.

---

# 36. Что не стоит делать

1. Не добавлять новый rail item на каждую новую capability.
2. Не строить dashboard-first home.
3. Не превращать scenario chat в поток технических логов.
4. Не показывать raw traceback обычному пользователю первым экраном ошибки.
5. Не делать отдельный AI-раздел.
6. Не делать отдельный «каскадный мир» рядом со сценариями.
7. Не делать background automation параллельной системой execution.
8. Не копировать Windows Explorer пиксельно — копировать его mental model.
9. Не копировать macOS visual chrome на Windows.
10. Не использовать modal dialogs для обычной навигации и статусов.
11. Не скрывать destructive behavior за innocuous action labels.
12. Не использовать цвет как единственный индикатор состояния.
13. Не проектировать Android как уменьшенную desktop-копию.
14. Не связывать shared presentation semantics с Qt Widgets.
15. Не сохранять текущие сущности только ради обратной совместимости, если они мешают целевой модели.

---

# 37. Рекомендуемая последовательность UX-разработки

## Stage 1 — shell и design system

- 4 top-level modes;
- rail/context sidebar/main/inspector;
- design tokens;
- light/dark/system;
- status bar;
- adaptive collapse;
- keyboard navigation.

## Stage 2 — Explorer

- Windows-like toolbar;
- breadcrumb;
- search;
- tree;
- details table;
- inspector integration;
- context menus.

## Stage 3 — Work / Scenario Chat

- WorkThread model;
- unified recent history;
- human/system/run/artifact timeline;
- composer;
- unread/pin/search.

## Stage 4 — Runs

- global runs list;
- progress;
- steps;
- cancellation contract;
- bottom logs/problems panel;
- retry/rerun.

## Stage 5 — Scenario catalog

- search;
- atomic/cascade filters;
- presets;
- parameter form refinement;
- favorite/recent.

## Stage 6 — Collaboration

- participants provider;
- assignments;
- approvals;
- shared work threads.

## Stage 7 — AI

- AI actor;
- context access;
- scenario discovery;
- action proposal cards;
- permissioned execution;
- artifact interpretation.

---

# 38. Финальная продуктовая формула

У Strategy Box есть риск пойти по одному из трёх неправильных путей:

```text
слишком platform → тяжёлый корпоративный комбайн
слишком messenger → красивые сообщения без контроля вычислений
слишком script-control → IDE для аналитиков
```

Целевой баланс иной:

```text
ПЛАТФОРМА
  даёт структуру, workspace, объекты, состояние и историю

МЕССЕНДЖЕР
  даёт человеческий контекст, совместную работу и AI

CONTROL PLANE
  даёт прозрачные сценарии, параметры, запуски, прогресс, логи и результаты
```

В Windows это должно выражаться через **стабильную многопанельную оболочку**, знакомый файловый UX, спокойную chat-centered main surface и строгую execution model.

Самый важный принцип на будущее:

> **Strategy Box должен скрывать техническую сложность, но никогда не скрывать состояние работы.**

Пользователь не обязан знать Python-модули, внутренние handlers и транспорт. Но он всегда должен понимать:

- что он попросил сделать;
- что система реально запустила;
- где это выполняется;
- на каком этапе находится;
- кто инициировал действие;
- что получилось;
- где лежит результат;
- что произошло при ошибке;
- что можно сделать дальше.

Именно эта прозрачность позволяет объединить минимализм ChatGPT, нативность Windows, пространственную дисциплину Apple и вычислительную глубину профессиональных developer tools без превращения Strategy Box ни в чат, ни в IDE, ни в dashboard.

---

# 39. Источники

## Внутренние

- `stratbox-windows_current_state_full_research_2026-10-06.md`
- `stratbox_base_study_current_state_2026-10-06.md`
- `AppDock - Базовое описание.docx`

## Microsoft / Fluent / Windows

- NavigationView — https://learn.microsoft.com/en-us/windows/apps/design/controls/navigationview
- Tree view — https://learn.microsoft.com/en-us/windows/apps/design/controls/tree-view
- BreadcrumbBar — https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/breadcrumbbar
- Command bar — https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/command-bar
- InfoBar — https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/infobar
- List/details — https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/list-details
- Navigation basics — https://learn.microsoft.com/en-us/windows/apps/design/basics/navigation-basics
- Responsive design — https://learn.microsoft.com/en-us/windows/apps/design/layout/responsive-design
- Screen sizes and breakpoints — https://learn.microsoft.com/en-us/windows/apps/design/layout/screen-sizes-and-breakpoints-for-responsive-design
- File Explorer in Windows — https://support.microsoft.com/en-us/windows/experience/fileexplorer/file-explorer-in-windows
- Fluent 2 Layout — https://fluent2.microsoft.design/layout
- Fluent 2 Typography — https://fluent2.microsoft.design/typography
- Fluent 2 Color — https://fluent2.microsoft.design/color
- Fluent 2 Design Tokens — https://fluent2.microsoft.design/design-tokens
- Fluent 2 Toolbar — https://fluent2.microsoft.design/components/web/react/core/toolbar/usage

## Apple HIG

- Sidebars — https://developer.apple.com/design/human-interface-guidelines/sidebars
- Split views — https://developer.apple.com/design/human-interface-guidelines/split-views
- Toolbars — https://developer.apple.com/design/human-interface-guidelines/toolbars
- Panels — https://developer.apple.com/design/human-interface-guidelines/panels
- Searching — https://developer.apple.com/design/human-interface-guidelines/searching
- Search fields — https://developer.apple.com/design/human-interface-guidelines/search-fields
- Progress indicators — https://developer.apple.com/design/human-interface-guidelines/progress-indicators
- Lists and tables — https://developer.apple.com/design/human-interface-guidelines/lists-and-tables
- Context menus — https://developer.apple.com/design/human-interface-guidelines/context-menus
- Keyboards — https://developer.apple.com/design/human-interface-guidelines/keyboards
- Designing for macOS — https://developer.apple.com/design/human-interface-guidelines/designing-for-macos

## VS Code / GitHub

- VS Code UX overview — https://code.visualstudio.com/api/ux-guidelines/overview
- Activity Bar — https://code.visualstudio.com/api/ux-guidelines/activity-bar
- Sidebars — https://code.visualstudio.com/api/ux-guidelines/sidebars
- Panel — https://code.visualstudio.com/api/ux-guidelines/panel
- Status Bar — https://code.visualstudio.com/api/ux-guidelines/status-bar
- Notifications — https://code.visualstudio.com/api/ux-guidelines/notifications
- Quick Picks — https://code.visualstudio.com/api/ux-guidelines/quick-picks
- GitHub Actions workflow logs — https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs

## OpenAI / ChatGPT

- ChatGPT release notes — https://help.openai.com/en/articles/6825453-chatgpt-release-notes
- Moving to the new ChatGPT desktop app — https://help.openai.com/en/articles/20001276-moving-to-the-new-chatgpt-desktop-app
- Finding chats, projects, and files — https://help.openai.com/en/articles/10056348-finding-your-chats-projects-and-files-in-chatgpt
- Projects in ChatGPT — https://help.openai.com/en/articles/10169521-projects-in-chatgpt

