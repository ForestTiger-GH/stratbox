# Strategy Box / stratbox-windows — исследование анимаций, motion-системы и динамического поведения интерфейса

**Ветка исследований:** 02 / interface & product surface  
**Дата:** 2026-10-07  
**Фокус:** преимущественно `stratbox-windows`, с обязательной переносимостью motion-семантики на будущие поверхности Strategy Box, включая Android.  
**Статус:** Research Result. Документ формулирует целевую motion-доктрину, требования, токены, сценарии поведения и архитектурные рекомендации; сам по себе не меняет код.

---

# 0. Краткий вывод

Strategy Box действительно нужен motion, но **не как визуальное украшение**. Для экономико-финансовой рабочей системы анимация должна прежде всего отвечать на пять вопросов пользователя:

1. **Система приняла моё действие?**
2. **Что именно сейчас изменилось?**
3. **Куда переместился мой контекст?**
4. **Идёт ли вычисление и на каком оно этапе?**
5. **Где появился результат и что с ним можно сделать дальше?**

Главная целевая формула:

> **много очень маленьких анимаций, почти ни одной большой.**

Пользователь должен ощущать интерфейс живым, связным и тщательно настроенным, но при обычной работе не должен постоянно замечать сам факт наличия анимационной системы.

Для Strategy Box рекомендуется сформировать отдельную **Motion System** наравне с типографикой, цветами, spacing и iconography. Она должна быть platform-neutral на уровне смысла и токенов и иметь отдельные реализации для Windows и будущего Android.

Базовая модель:

```text
semantic event
    ↓
MotionRole
    ↓
MotionSpec
    ├─ duration
    ├─ easing
    ├─ distance
    ├─ opacity
    ├─ scale
    ├─ repetition policy
    └─ reduced-motion fallback
    ↓
platform adapter
    ├─ Qt / Windows
    └─ Android frontend
```

То есть `scenario_started` не должен означать «в этом Qt-widget вручную запустить такую-то анимацию». Он должен означать: **показать стандартный motion-переход Strategy Box из submitted в running**. Конкретный frontend воспроизводит один и тот же смысл собственными средствами.

## 0.1. Рекомендуемый характер motion

Целевое ощущение:

- тихое;
- быстрое;
- точное;
- гладкое;
- без пружинности и игрового bounce;
- с очень небольшими перемещениями;
- с мягкими fade/slide/crossfade;
- с отлично настроенной прокруткой;
- с редкими connected transitions там, где они реально помогают сохранить контекст;
- с низкоамплитудными живыми индикаторами длительных процессов;
- с минимальными микроэффектами кнопок и выбора;
- без animation tax — действие никогда не ждёт окончания красивого перехода.

## 0.2. Базовые временные токены

Вместо десятков произвольных значений по коду:

```text
instant      0 ms
xfast       80 ms
fast       160 ms
normal     240 ms
slow       320 ms
emphasis   480 ms   ← редко
ambient   1400–1800 ms loop ← только процесс / ожидание
```

Это намеренно близко к Fluent-классам 83 / 167 / 250 / 333 мс, но округлено до понятной общей шкалы Strategy Box.

## 0.3. Три стандартные кривые

```text
enter / settle     cubic-bezier(0, 0, 0, 1)
exit               cubic-bezier(1, 0, 1, 1)
move / continuity  cubic-bezier(0.55, 0.55, 0, 1)
```

Основной принцип: **быстрый старт, мягкая посадка**. Overshoot, elastic и bounce в основной системе отсутствуют.

## 0.4. Основные виды анимаций

Всего Strategy Box фактически нужен небольшой словарь:

1. `fade`;
2. `fade + translate 4–12 px`;
3. `small scale 0.985 → 1`;
4. `connected resize/move` для выбранного объекта;
5. `smooth programmatic scroll`;
6. `progress fill`;
7. `soft process sheen` / moving gradient;
8. `icon state morph/rotation` в нескольких специальных местах;
9. `highlight settle` после появления или обновления данных.

Этого достаточно почти для всего приложения.

## 0.5. Самая характерная анимация Strategy Box

В качестве фирменного, но функционального эффекта лучше всего подходит **тихий движущийся градиент процесса**.

Он не должен заливать весь экран. Его место:

- тонкая верхняя/нижняя process-line внутри карточки запуска;
- небольшой accent segment в status pill;
- тонкий border sheen у активного run;
- маленький индикатор AI/tool execution;
- при необходимости — indeterminate progress strip.

Градиент:

- использует один accent hue + прозрачность;
- не меняет цвета радугой;
- имеет очень низкий contrast delta;
- проходит слева направо примерно за 1.4–1.8 с;
- не вспыхивает;
- исчезает сразу после завершения работы;
- выключается или заменяется статическим состоянием при Reduced Motion.

Такой эффект хорошо соответствует желаемому «ChatGPT-like» ощущению, но получает собственную семантику Strategy Box: **движется вычисление, а не просто “что-то красиво светится”**.

## 0.6. Главный запрет

В интерфейсе одновременно могут существовать десятки running objects. Поэтому анимация должна иметь **бюджет внимания**.

Если на экране 18 фоновых задач, нельзя дать каждой яркий независимый spinner/shimmer. Нужны:

- спокойные локальные статусы;
- aggregation;
- анимация только актуального/выбранного объекта;
- общая activity-индикация для группы.

Иначе рабочая финансовая поверхность превращается в новогоднюю гирлянду.

---

# 1. Рамка исследования и источники

## 1.1. Внутренние материалы Strategy Box

Исследование продолжает предыдущую вторую ветку и опирается прежде всего на:

- `stratbox-windows_current_state_full_research_2026-10-06.md`;
- `stratbox_windows_interface_requirements_research_2026-10-07.md`;
- `stratbox_base_study_current_state_2026-10-06.md`;
- `AppDock - Базовое описание.docx`.

Фактическая текущая desktop-поверхность уже содержит:

- левую навигацию;
- workspace Explorer;
- каталог сценариев;
- каскады;
- scenario-chat;
- cases/events;
- логи;
- артефакты;
- right inspector;
- параметры;
- runtime/node state;
- фоновые процессы как концепцию;
- presence/participants как концепцию;
- поручения;
- будущую семантику AI actor.

Предыдущее интерфейсное исследование предложило упростить верхнеуровневую IA до:

```text
Работа
Проводник
Сценарии
Запуски
```

Эта motion-работа исходит именно из этой целевой модели.

## 1.2. Внешние официальные источники

Для сверки использованы:

### Microsoft / Fluent / Windows

- Motion in Windows — принципы connected, consistent, responsive, delightful, resourceful;
- Timing and easing — системные значения длительностей и Fluent easing;
- Page transitions — различие page refresh / drill / horizontal sibling navigation;
- Connected animation — сохранение контекста между представлениями;
- Progress controls — determinate/indeterminate и modal/modeless semantics.

### Apple Human Interface Guidelines

- Motion — purposeful motion, brevity, precision, interruptibility;
- Accessibility / Reduce Motion — замена пространственных переходов fades и снижение постоянного/периферийного движения.

### Android / Material

- Material motion рассматривается как часть design-token системы: easing и duration должны быть формализованы и передаваемы разработке как tokens, а motion используется для направления внимания, сигнала действий и feedback.

### Qt / PySide

- `QPropertyAnimation`;
- `QEasingCurve`;
- `QParallelAnimationGroup`;
- `QSequentialAnimationGroup`;
- `QScroller`;
- Qt accessibility motion preference в новых версиях Qt.

### Accessibility

- WCAG 2.3.1 / 2.3.2 — ограничения на flashing;
- WCAG 2.3.3 — interaction-triggered motion должно быть отключаемым, если движение не является функционально необходимым.

## 1.3. Что не является источником факта

Пользовательская ссылка на ChatGPT в этой теме используется как **эстетический и поведенческий ориентир**, прежде всего:

- мягкое состояние ongoing work;
- спокойные gradient accents;
- плавная timeline-прокрутка;
- отсутствие тяжёлой «корпоративной» анимации.

Документ не утверждает наличие какого-либо конкретного публичного motion-spec ChatGPT.

---

# 2. Почему motion особенно важен именно для Strategy Box

## 2.1. Это приложение с большим количеством невидимой работы

В обычном текстовом редакторе нажатие клавиши сразу создаёт видимый результат. В Strategy Box значительная часть действий происходит вне поля зрения пользователя:

```text
выбрать scenario
→ проверить параметры
→ создать case
→ поставить в очередь
→ запустить operation
→ получить/прочитать данные
→ выполнить вычисление
→ сформировать artifact
→ записать лог
→ обновить history
→ показать результат
```

Если UI просто прыгает из одного статического состояния в другое, пользователь постоянно задаётся вопросами:

- кнопка сработала?
- приложение зависло?
- операция ещё работает?
- почему карточка переехала?
- откуда появился этот файл?
- это новый результат или старый?
- какое действие вызвало открывшуюся панель?

Motion способен превратить разрозненные состояния в понятную причинно-следственную цепочку.

## 2.2. Экономико-финансовая система требует сдержанности

Слишком выразительная анимация здесь особенно вредна по четырём причинам.

### Длительные рабочие сессии

Аналитик может проводить в приложении часы. То, что эффектно смотрится 30 секунд на демо, через несколько часов раздражает.

### Высокая информационная плотность

Таблицы, логи, файлы, статусы, результаты и параметры уже несут много информации. Motion конкурирует с содержанием за внимание.

### Доверие

Избыточный bounce, glow, overshoot и игровые success-эффекты снижают ощущение серьёзного инструмента.

### Параллельные процессы

Будущее приложение способно показывать одновременно несколько вычислений. Слишком активная анимация масштабируется очень плохо.

## 2.3. Значит, цель — «calm computing»

Motion Strategy Box должен создавать ощущение:

> система постоянно живая и отзывчивая, но не требует на себя смотреть.

Это ближе к хорошему системному UI, чем к маркетинговой web-анимации.

---

# 3. Motion-доктрина Strategy Box

## 3.1. Motion всегда должен иметь семантическую причину

Допустимые причины:

- подтверждение input;
- изменение состояния;
- появление/исчезновение объекта;
- перенос контекста;
- иерархическая навигация;
- процесс выполнения;
- изменение прогресса;
- связь source → destination;
- привлечение внимания к важному новому состоянию.

Недостаточная причина:

> «так красивее».

## 3.2. Motion следует за data/state model

Правильная последовательность:

```text
state changed
→ presentation model changed
→ motion interprets transition
```

Неправильная:

```text
user clicked
→ widget запустил animation
→ somewhere business state eventually changes
```

Motion не должен становиться второй скрытой state machine.

## 3.3. Пользовательский input получает feedback немедленно

Целевой принцип:

- нажатие кнопки визуально подтверждается почти мгновенно;
- action запускается сразу;
- длинная анимация никогда не откладывает работу;
- если операция долгая, короткая micro-animation переходит в persistent progress state.

Например:

```text
click "Запустить"
0–80 ms       press feedback
0–160 ms      создаётся run card
~160 ms       появляется running state
дальше        уже работает persistent process indicator
```

Пользователю не нужно ждать красивой 600-ms отправки карточки прежде чем backend начнёт работу.

## 3.4. Motion сохраняет continuity

Если объект существует до и после действия, интерфейс по возможности показывает его как **тот же объект**.

Примеры:

- scenario card → parameters view;
- run card → inspector;
- artifact chip → preview;
- selected file → details pane;
- compact running task → expanded case.

Это снижает mental remapping.

## 3.5. Частота использования обратно пропорциональна выразительности

Чем чаще действие, тем меньше motion.

```text
1000 раз/день  selection / hover       → почти только color/fade
100 раз/день   switch context          → micro transition
20 раз/день    open inspector          → small spatial transition
5 раз/день     launch scenario         → richer state handoff
редко          first result / recovery → допускается чуть больше emphasis
```

## 3.6. Motion должен быть прерываемым

Пользователь не обязан ждать.

Во время transition он может:

- нажать назад;
- выбрать другой объект;
- свернуть inspector;
- сменить surface;
- отменить запуск;
- продолжить scroll.

Animation manager должен корректно завершать/reverse/replace текущую анимацию, а не блокировать input.

## 3.7. Пространственные эффекты минимальны

Запрещён базовый язык типа:

- окно прилетает издалека;
- карточка вылетает на 200 px;
- страница уезжает целиком;
- zoom всей поверхности;
- parallax background;
- карточки висят в 3D.

Стандартная амплитуда Strategy Box — **4–12 px**.

## 3.8. Отдых — часть motion

После перехода интерфейс должен становиться полностью спокойным.

Постоянно двигаются только объекты, для которых это несёт актуальную информацию:

- running;
- indeterminate loading;
- streaming;
- active transfer.

Success, warning, error, selected, unread — после короткой реакции становятся статическими.

---

# 4. Кросс-платформенная модель: одинаковый язык, разные механизмы

## 4.1. Что именно должно быть одинаковым

Между Windows и Android должны совпадать:

- названия MotionRole;
- durations;
- базовые easing-кривые;
- логика направления;
- состояние до/после;
- reduced-motion mapping;
- semantic meaning;
- порядок событий;
- общий характер визуального движения.

Например:

```text
PANEL_REVEAL
Windows: fade + 10 px translate, 160 ms, enter easing
Android: fade + 10 dp translate, 160 ms, enter easing
```

## 4.2. Что не нужно насильно делать пиксельно одинаковым

У платформ есть разные input physics.

Особенно:

- wheel scrolling desktop;
- touch kinetic scrolling Android;
- hover отсутствует на touch;
- pointer press и touch press различаются;
- native overscroll semantics различаются.

Поэтому принцип:

> **одинаковая motion-семантика, platform-native input physics.**

Программные переходы — унифицировать. Физическую реакцию прямого input — по возможности оставлять платформе.

## 4.3. Motion Contract должен жить выше конкретного UI toolkit

Целевая логика:

```text
presentation/common/motion/
├── roles
├── tokens
├── policy
├── state_transitions
└── reduced_motion

presentation/qt_desktop/motion/
└── QtMotionAdapter

future android presentation
└── AndroidMotionAdapter
```

Это особенно соответствует уже выбранному направлению, где `presentation/common` должен содержать platform-neutral semantics.

## 4.4. MotionRole вместо magic numbers

Нельзя допустить:

```text
widget_a: 170 ms
widget_b: 190 ms
widget_c: 250 ms
```

Нужно:

```text
BUTTON_PRESS
PANEL_REVEAL
CONTENT_REPLACE
CONNECTED_DRILL
ITEM_INSERT
STATUS_CHANGE
PROCESS_AMBIENT
PROGRAMMATIC_SCROLL
```

Каждый role маппится на один spec.

---

# 5. Базовые motion tokens

# 5.1. Duration scale

Рекомендуемая шкала:

| Token | Значение | Назначение |
|---|---:|---|
| `motion.instant` | 0 ms | reduced/off, structural snap |
| `motion.xfast` | 80 ms | press, focus, tiny opacity change |
| `motion.fast` | 160 ms | hover settle, item insertion, close |
| `motion.normal` | 240 ms | panel reveal, content replacement |
| `motion.slow` | 320 ms | larger structural transition |
| `motion.emphasis` | 480 ms | редкое meaningful connected transition |
| `motion.ambient.fast` | 1400 ms | compact ongoing process loop |
| `motion.ambient.normal` | 1800 ms | soft shimmer / breathing process |

`480 ms` — не новая норма. Это потолок для редких переходов, где нужно провести взгляд между двумя состояниями.

## 5.2. Почему не 600–1000 ms для обычной навигации

Такие durations:

- делают интерфейс «тяжёлым»;
- повышают ощущение latency;
- заставляют ждать повторяющиеся действия;
- особенно раздражают keyboard-first пользователей.

Длинными могут быть **ambient loops**, потому что они не блокируют действие.

## 5.3. Easing scale

### Enter / settle

```text
cubic-bezier(0, 0, 0, 1)
```

Быстро приходит и мягко останавливается.

Использование:

- появление panels;
- insertion;
- selected object expansion;
- incoming content.

### Exit

```text
cubic-bezier(1, 0, 1, 1)
```

Быстро освобождает место.

Использование:

- panel dismiss;
- удаление transient surface;
- исчезновение toast;
- outgoing layer.

### Move / continuity

```text
cubic-bezier(0.55, 0.55, 0, 1)
```

Для движения существующего объекта между двумя положениями.

### Linear

Только там, где это семантически оправдано:

- continuous process sheen;
- determinate progress interpolation очень короткого участка;
- вращение индикатора.

Обычные пространственные переходы linear быть не должны.

## 5.4. Distance tokens

```text
motion.distance.xs = 2 px/dp
motion.distance.sm = 4 px/dp
motion.distance.md = 8 px/dp
motion.distance.lg = 12 px/dp
motion.distance.xl = 16 px/dp
```

Почти весь продукт должен жить внутри `4–12`.

`16` — уже крупное движение для панели.

## 5.5. Scale tokens

```text
press      1.000 → 0.985
release    0.985 → 1.000
soft-enter 0.990 → 1.000
```

Никаких `0.8 → 1.0` для обычных UI objects.

## 5.6. Opacity

Standard fade:

```text
0 → 1
1 → 0
```

Subtle update highlight:

```text
background accent 0.10 → 0.00
```

Ambient pulse, если вообще используется:

```text
0.65 ↔ 1.0
```

Но постоянный opacity pulse следует применять крайне редко: мягкий travelling gradient обычно лучше.

## 5.7. Stagger

Для группы из 2–5 элементов возможен stagger `20–30 ms`.

Пример:

- открывается inspector;
- title появляется первым;
- status + metadata почти одновременно;
- action row на 20–30 ms позже.

Для больших списков stagger запрещён. 50 строк не должны «сыпаться лесенкой».

---

# 6. Motion budget

## 6.1. На одном экране должен быть ограниченный объём постоянного движения

Предлагается правило:

> не больше одного визуально заметного ambient motion cluster на одну крупную рабочую область.

Например:

- chat: active run card;
- right inspector: статический status;
- bottom panel: activity glyph;

Если в списке 20 running jobs, каждая строка не должна иметь большой spinner.

## 6.2. Aggregation

При большом числе процессов:

```text
3 выполняются
```

может иметь один общий animated status icon, тогда как отдельные строки показывают спокойные state dots / mini progress.

## 6.3. Offscreen pausing

Ambient animations:

- не рендерятся для невидимых virtualized items;
- ставятся на pause при свёрнутом окне;
- по возможности снижаются при неактивном приложении;
- не продолжают бессмысленно потреблять CPU/GPU в background.

---

# 7. Единая таблица motion states

| State | Основной визуальный язык | Постоянное движение? |
|---|---|---|
| idle | static | нет |
| hover | fast color/fill transition | нет |
| pressed | tiny scale + shade | нет |
| selected | fill/border settle | нет |
| prepared | item insertion | нет |
| queued | static queue icon + optional tiny flow indicator | минимально |
| running unknown | soft process sheen / indeterminate strip | да |
| running known | determinate progress fill | только при update |
| waiting user | one-time attention transition + static | нет |
| waiting external | very subtle process state | ограниченно |
| success | one-time check/status settle | нет |
| warning | one-time accent transition | нет |
| error | one-time accent transition | нет |
| cancelled | short fade to neutral | нет |
| disabled | static | нет |
| offline | static state + optional reconnect activity | только при reconnect |

---

# 8. Главная оболочка приложения

## 8.1. Переключение top-level surfaces

Целевые поверхности:

```text
Работа
Проводник
Сценарии
Запуски
```

Это sibling navigation. Пользователь не «проваливается внутрь» и не должен чувствовать длинный горизонтальный перелёт.

Рекомендуемый transition:

```text
old main content:
  opacity 1 → 0
  translateY 0 → -4 px
  80–120 ms

new main content:
  opacity 0 → 1
  translateY 6 px → 0
  160–240 ms
```

Sidebar может сменить контекст почти одновременно.

Так создаётся ощущение «перезапуска рабочей поверхности», близкое к Fluent page refresh, но очень компактное.

## 8.2. Activity rail

Icon state:

- hover: 80–100 ms fill/background;
- selected indicator: 160 ms move/resize;
- click press: 80 ms scale/background;
- no bounce;
- no icon flying.

Лучший эффект — **один active indicator**, который визуально переезжает между rail items, а не исчезает и появляется заново. Это создаёт continuity.

## 8.3. Context sidebar

При переключении surface:

- контейнер sidebar не ездит;
- меняется только его content;
- old content fast fade;
- new content fade + `4 px` translate;
- resize sidebar width выполняется только если действительно нужна другая сохранённая ширина.

Постоянное движение всей левой зоны будет слишком тяжёлым.

## 8.4. Right inspector

Inspector — один из немногих объектов, где spatial transition полезен.

Open:

```text
opacity 0 → 1
translateX 12 px → 0
160–240 ms enter
```

Close:

```text
opacity 1 → 0
translateX 0 → 8 px
120–160 ms exit
```

Если панель реально меняет ширину центральной области, layout transition должен быть коротким и тщательно benchmark-иться: Qt Widgets может вызывать relayout большого дерева на каждом кадре.

## 8.5. Bottom panel

Логи/детали runtime не должны «вылетать» на половину экрана.

Open:

- bottom panel height transition;
- content fade;
- 160–240 ms;
- focus остаётся у прежнего объекта, если пользователь не инициировал keyboard navigation внутрь панели.

Resize drag пользователем — **без easing**: панель должна следовать указателю напрямую.

---

# 9. Проводник / Explorer

## 9.1. Главный принцип

Explorer обязан ощущаться близко к Windows File Explorer. Поэтому motion должен поддерживать знакомую spatial logic, а не переизобретать файловый браузер.

## 9.2. Открытие папки

При double-click / Enter:

- breadcrumb обновляется;
- список current folder заменяется через short crossfade;
- возможен `translateY 4 px` для incoming content;
- selected state не переносится на случайный новый item.

Duration: `160 ms`.

## 9.3. Back / Forward / Up

Можно дать направление:

- deeper → content `+4..8 px` к пользователю/вверх;
- back → обратное минимальное движение;
- Up → `-4 px` vertical cue.

Но направление должно быть едва заметным. Проводник не должен превращаться в мобильный carousel.

## 9.4. Tree expand / collapse

Лучше анимировать:

- chevron rotation `90°` за `120–160 ms`;
- изменение высоты блока очень коротко либо оставить native/model transition.

Полноценная анимация каждой строки дерева может быть дорогой и мешает быстрому keyboard navigation.

## 9.5. Selection

- background/fill transition `80 ms`;
- focus ring появляется почти сразу;
- keyboard selection не должна ждать animation completion.

## 9.6. Rename

Переход label → inline editor:

- `80–120 ms` crossfade;
- text geometry остаётся на месте;
- никакого zoom.

После подтверждения:

- editor → label;
- brief highlight settle `160 ms`.

## 9.7. Новый файл / artifact появляется в папке

Если приложение само знает, что именно создало artifact:

- строка вставляется с fade + `4 px`;
- background soft highlight держится ~`320–480 ms` и исчезает;
- если пользователь находится в другой папке — не перехватывать навигацию.

## 9.8. Copy / move / delete

Длительные операции используют progress semantics.

Удаление не должно сопровождаться «улётом в корзину». Достаточно:

```text
selected row
→ opacity 1 → 0
→ neighboring rows settle
160 ms
```

После irreversible/destructive operation результат важнее декоративного motion.

---

# 10. Сценарии: каталог и выбор

## 10.1. Scenario card hover

Desktop hover:

- background/tint `80–120 ms`;
- border/elevation `120 ms`;
- icon может сместиться максимум на `1–2 px`, но лучше вообще без spatial movement.

Не делать карточки «подпрыгивающими».

## 10.2. Selection

Выбранный scenario получает:

- active border/fill;
- connected highlight к parameters area, если она рядом;
- `160 ms`.

## 10.3. Открытие scenario details

Если details заменяют центр:

- selected card остаётся spatial anchor;
- details fade + small translate;
- при возможности часть header (icon/title) визуально продолжается в details.

Это подходящее место для connected-animation semantics.

## 10.4. Atomic vs composite/cascade

Каскад — тип scenario, поэтому сам motion не должен менять язык.

Различие появляется внутри execution visualization:

```text
atomic     one step
cascade    ordered step rail
```

## 10.5. Фильтрация/search

Результаты фильтра:

- не анимировать каждую карточку отдельно;
- update списка через `80–120 ms` opacity/position settle;
- search field feedback мгновенный.

Large result sets должны prioritise performance.

---

# 11. Параметры сценария

## 11.1. Basic / Advanced

Раскрытие Advanced parameters:

- chevron rotates `120 ms`;
- content height/reveal `160–240 ms`;
- opacity `0 → 1`;
- focus не прыгает.

## 11.2. Conditional fields

Если параметр A делает видимым B:

- новый field появляется непосредственно под логически связанным control;
- `160 ms fade + 4 px`;
- окружающая форма плавно перестраивается;
- screen reader получает state change независимо от animation.

## 11.3. Validation

Ошибка параметра:

- border/color transition `80–120 ms`;
- helper text insertion `160 ms`;
- **никакого shake**.

Shake ассоциируется с consumer/mobile patterns и создаёт лишнее движение. В деловом продукте лучше точная визуальная коррекция.

---

# 12. Самая важная последовательность: запуск сценария

Это должен стать один из наиболее тщательно выверенных motion-flows продукта.

# 12.1. Состояние до запуска

```text
Scenario selected
Parameters valid
CTA: Запустить
```

Кнопка спокойная.

## 12.2. Press

`0–80 ms`:

- button scale `1 → 0.985`;
- fill немного темнеет/светлеет;
- click принимается сразу.

## 12.3. Release / accepted

`80–160 ms`:

- button возвращается `0.985 → 1`;
- icon может кратко перейти из play/send в accepted mark;
- form больше не выглядит «неотправленной».

## 12.4. Run card insertion

В Working timeline появляется новый run object:

```text
opacity 0 → 1
translateY 8 px → 0
160–240 ms
```

Это визуальный handoff:

> параметры перестали быть просто формой и стали конкретным запуском.

## 12.5. `prepared → queued`

Если есть очередь:

- status label crossfade;
- tiny queue icon state;
- карточка статична.

Queued не требует постоянного shimmer, если реально ничего не исполняется.

## 12.6. `queued → running`

Здесь включается фирменный process motion:

- появляется thin process rail / border sheen;
- текущий step получает active marker;
- status `Выполняется`;
- если progress unknown — soft travelling gradient;
- если известен — determinate fill.

## 12.7. Во время исполнения

Карточка не должна постоянно менять размеры.

Обновляются только:

- current stage label;
- progress;
- elapsed time текстом;
- step list при раскрытии;
- новые artifacts/log notices.

## 12.8. Success

Sequence:

1. process sheen останавливается;
2. progress доходит до 100%, если determinate;
3. success icon/check появляется `120–160 ms`;
4. background/border возвращается в resting state `240 ms`;
5. artifact insertion выполняется отдельно.

Никакого confetti.

## 12.9. Warning

Same geometry.

- process motion прекращается;
- status tint меняется;
- warning icon appears;
- one-time highlight settle;
- card остаётся легко читаемой.

## 12.10. Error

Ошибка — прежде всего новое actionable state.

Рекомендуется:

```text
process stops immediately
error surface fades in 120–160 ms
recovery actions appear 160 ms
```

Не рекомендуется:

- shake;
- красная вспышка;
- пульсирующий красный border;
- полноэкранный error animation.

## 12.11. Cancel

Cancellation transition:

- running motion прекращается;
- status → `Остановка…` при cooperative cancellation;
- затем → `Отменено`;
- accent постепенно нейтрализуется.

Это важно: если cancel не моментальный, нельзя мгновенно показать `cancelled`, пока backend ещё работает.

---

# 13. Process sheen / gradient — подробная спецификация

# 13.1. Зачем

Indeterminate progress часто выглядит либо как spinner, либо как стандартная бегущая полоска. Для Strategy Box можно сделать более характерный и спокойный вариант, вдохновлённый современными assistant-интерфейсами.

## 13.2. Geometry

Предпочтительно:

- высота 2–3 px для progress rail;
- либо 1 px animated accent segment по border;
- не более 8–12% площади карточки должно визуально участвовать в эффекте.

Не использовать большой animated gradient background всей карточки.

## 13.3. Gradient

Пример семантики:

```text
transparent
→ accent at ~6% opacity
→ accent at ~16–22% opacity
→ accent at ~6%
→ transparent
```

Конкретные значения зависят от light/dark theme и контраста.

## 13.4. Цвет

Один semantic accent.

Не использовать:

- rainbow;
- hue rotation;
- RGB wave;
- многократную смену фирменных цветов.

## 13.5. Скорость

```text
1400–1800 ms / pass
```

Слишком быстро = нервно.  
Слишком медленно = кажется декоративным background.

## 13.6. Loop

Loop seamless, без заметной паузы/скачка.

Но animation должен иметь lifecycle, привязанный к state:

```text
running starts → loop starts
running ends   → finish/fade current pass → stop
```

При критическом error допускается stop сразу.

## 13.7. Несколько running объектов

Правило:

- selected/current run — full process sheen;
- прочие видимые running rows — tiny static/determinate status либо очень слабый mini indicator;
- collapsed group — один aggregated animated marker.

## 13.8. Reduced Motion

Gradient loop отключается.

Замена:

- static accent rail;
- label `Выполняется`;
- status icon;
- determinate progress updates, если доступны.

---

# 14. Determinate progress

## 14.1. Предпочитать determinate, когда это честно возможно

Если engine знает:

- число шагов;
- число файлов;
- число периодов;
- количество entities;
- долю completed work;

лучше дать determinate progress.

## 14.2. Не симулировать точность

Нельзя показывать `73%`, если система на самом деле не знает прогресс.

Вместо этого:

```text
Шаг 2 из 4
Обрабатываются 18 файлов
```

может быть честнее.

## 14.3. Progress должен быть монотонным

Одна operation/case progress line не должна:

- прыгать назад;
- сбрасываться на 0 при новом step;
- случайно менять scale.

Если нужно step-level progress, он показывается отдельно.

## 14.4. Visual interpolation

Backend может присылать progress редко:

```text
31 → 39 → 52
```

UI может плавно интерполировать между полученными значениями за `120–240 ms`, но не должен предсказывать progress дальше фактического значения.

---

# 15. Каскад / composite scenario

## 15.1. Step rail

Раскрытый composite run может показывать вертикальную цепочку:

```text
✓ Загрузка источников
● Нормализация
○ Расчёт
○ Экспорт
```

## 15.2. Active step

Active marker:

- не пульсирует ярко;
- может иметь tiny moving accent / rotating short arc;
- label статичен;
- при переходе active marker плавно перемещается к следующему step `160–240 ms`.

## 15.3. Step completion

```text
active → completed
```

- motion line settles;
- icon morph/fade to check;
- next step activates.

Эта последовательность визуально объясняет pipeline намного лучше, чем отдельные notifications.

## 15.4. Parallel steps

В будущем при parallel execution не нужно устраивать race animation.

Показывать:

- несколько simultaneous active markers;
- общий aggregate progress;
- спокойную структуру.

---

# 16. Scenario chat / Работа

## 16.1. Message insertion

Новые human/AI messages:

```text
opacity 0 → 1
translateY 4–6 px → 0
160 ms
```

В enterprise surface bubble не должна «влетать» сбоку.

## 16.2. Run card insertion

Run card немного выразительнее обычного текста:

```text
8 px / 200 ms
```

потому что создаётся новый operational object.

## 16.3. System events

Системные notices:

- mostly fade;
- 80–160 ms;
- без движения всего timeline.

## 16.4. Incoming collaboration event

Если пользователь находится внизу timeline:

- event inserts;
- scroll softly keeps bottom anchor.

Если пользователь читает историю выше:

- timeline **не прыгает**;
- появляется `Новая активность ↓`;
- click выполняет smooth scroll.

Это критически важнее красивой bubble-animation.

## 16.5. Loading older history

При подгрузке сверху:

- scroll anchor сохраняется;
- новые старые элементы добавляются без visual jump;
- tiny top loader может fade out после окончания.

## 16.6. Editing / update existing message

Если content обновился:

- geometry не должна мигать;
- changed block можно кратко подсветить `240–480 ms`;
- no re-entry animation whole bubble.

---

# 17. Будущий AI внутри Work Thread

## 17.1. AI — actor, а не отдельный «магический экран»

Motion AI должен использовать тот же язык, что и остальное приложение.

## 17.2. Thinking / preparing

Вместо трёх больших скачущих dots:

- compact AI status row;
- soft gradient line / moving accent;
- текст `Анализирует…`, `Готовит запуск…`, `Проверяет результат…`.

Это более органично для Strategy Box.

## 17.3. Streaming answer

Не нужно искусственно имитировать человека посимвольным typewriter-effect.

Правильнее:

- текст появляется chunked/streaming по мере поступления;
- layout стабилизируется мягко;
- caret/active indicator минимальный;
- auto-scroll obeys user position.

## 17.4. AI tool/scenario call

Когда AI предлагает или запускает разрешённый Scenario:

```text
AI message
→ tool/scenario card appears
→ approval state (если нужен)
→ running state
→ result artifact
```

Motion должен визуально связать эти объекты, чтобы пользователь понимал причинность.

## 17.5. Approval

При необходимости подтверждения:

- card получает brief attention highlight;
- continuous blinking запрещён;
- buttons появляются без dramatic modal transition.

## 17.6. AI завершил работу

Running sheen прекращается, появляется result state. Не нужно отдельной «AI success animation» — успех сценария и успех обычной операции имеют один язык.

---

# 18. Smooth scrolling

# 18.1. Разделить direct и programmatic scroll

### Direct user scroll

Wheel/touchpad/touch scroll должен оставаться максимально platform-native.

На Windows:

- не накладывать дополнительную собственную 500-ms инерцию поверх wheel/touchpad;
- уважать системное поведение.

На Android:

- использовать native kinetic touch physics.

### Programmatic scroll

Когда приложение само ведёт к объекту:

- `scroll to active run`;
- `jump to new activity`;
- `scroll to validation error`;
- `reveal selected log line`;

использовать единую Strategy Box animation.

## 18.2. Duration programmatic scroll

Зависит от расстояния, но должен иметь cap.

Рекомендуемая модель:

```text
small  < 0.5 viewport  → 160 ms
medium < 1.5 viewport  → 240 ms
large                   → 320 ms max
```

Не анимировать 5 экранов текста 1.5 секунды.

Для далёкой цели можно сделать быстрый jump + короткий settle/highlight у destination.

## 18.3. Auto-scroll в chat/log

Только если пользователь уже находится близко к tail.

Threshold может быть условно `1–2 line heights` / небольшая зона у конца.

Если пользователь ушёл вверх:

- follow mode отключается;
- показывается new activity indicator.

## 18.4. QScroller

Qt `QScroller` предоставляет kinetic scrolling и platform-optimized defaults. Для touch/gesture surfaces его целесообразно использовать осторожно, особенно потому что Qt прямо рекомендует не перенастраивать физику без необходимости.

Для desktop wheel не следует насильно заменять native scroll QScroller-моделью.

---

# 19. Logs

## 19.1. Log — поток, а не чат

Главная цель — readability и performance.

## 19.2. Append line

При редких строках:

- `80 ms fade` допустим.

При высокочастотном stream:

- строки вставляются без animation;
- можно анимировать только group/status marker.

Иначе получим огромный render cost и визуальное дрожание.

## 19.3. Follow tail

Если follow enabled и пользователь в tail:

- scroll плавно удерживает конец;
- лучше обновлять в throttled batches, например визуально не чаще нескольких раз в секунду для большого потока.

## 19.4. User scroll up

Follow автоматически приостанавливается.

Появляется compact chip:

```text
↓ 127 новых строк
```

Chip появляется `160 ms fade + 4 px`.

## 19.5. Warning / error line

Новая важная line может получить one-time background highlight:

```text
accent 12% → 0%
480–800 ms
```

Но никакого мигающего красного.

## 19.6. Search highlight

Search result navigation:

- programmatic scroll;
- current line gets short static/settling highlight;
- next/previous не должен заставлять весь log reanimate.

---

# 20. Артефакты

## 20.1. Artifact creation

Artifact — важный milestone.

При появлении:

```text
artifact chip/card
opacity 0 → 1
translateY 4 px → 0
160–240 ms
```

Если несколько artifacts создаются одним шагом, они появляются группой, без длинного cascade.

## 20.2. Artifact open

Если preview открывается в inspector/main surface, можно использовать connected transition:

- selected artifact остаётся визуальным anchor;
- preview header/icon morph/continues;
- `240–320 ms`;
- остальной content crossfades.

## 20.3. Reveal in Explorer

Очень полезный motion:

```text
artifact action: "Показать в Проводнике"
→ switch surface
→ folder opens
→ file row receives short highlight settle
```

Пользователь сразу понимает, куда объект попал.

## 20.4. Artifact lineage

Если позже будет source/result graph, edges не должны постоянно течь/пульсировать. Motion нужен только при:

- построении нового relation;
- hover/focus trace;
- переходе source → output.

---

# 21. Запуски / Runs surface

## 21.1. Списки running/queued/history

List row motion минимален.

- status change: `120–160 ms` color/icon transition;
- row reorder: `160–240 ms` positional settle, только если reorder действительно помогает понять изменение;
- сортировка пользователем может snap/crossfade large list вместо анимации каждой строки.

## 21.2. Queue

Queued item не должен имитировать running.

Можно показать:

- position number;
- статический clock/queue glyph;
- estimated/relative state;
- tiny moving dot только если есть реальная активность диспетчера, но это необязательно.

## 21.3. Background execution

Фон не означает постоянный яркий animation.

Если задача свернута:

- state icon;
- mini progress;
- общий activity aggregate.

При открытии details появляется normal run visualization.

## 21.4. Completion while user elsewhere

Возможны:

- subtle toast;
- badge increment;
- nonintrusive status transition.

Surface пользователя не переключается автоматически.

---

# 22. Кнопки, toggles, icon buttons

# 22.1. Hover

```text
background/fill 80–120 ms
border 80–120 ms
```

Без spatial movement.

## 22.2. Press

```text
scale 1 → 0.985
80 ms
```

Для очень маленьких icon buttons можно отказаться от scale и использовать только fill, если geometry выглядит дёргано.

## 22.3. Release

```text
scale 0.985 → 1
120–160 ms
```

## 22.4. Focus

Keyboard focus ring:

- появляется сразу либо до 80 ms;
- never slowly fades for 300 ms;
- accessibility > decorative smoothness.

## 22.5. Toggle

Thumb:

- direct motion 160 ms;
- background color synchronised;
- no bounce.

## 22.6. Icon state morph

Хорошие кандидаты:

```text
play → stop
chevron right → down
pin off → pin on
bookmark off → on
expand → collapse
```

Иконка может morph/crossfade `120–160 ms`.

## 22.7. Refresh

Не нужно крутить refresh icon целую минуту.

При ручном click:

- icon делает короткую реакцию;
- если operation длится, состояние переходит в standard process indicator.

---

# 23. Search и Command Palette

## 23.1. Open

Command/search overlay:

```text
opacity 0 → 1
translateY -4 px → 0
160 ms
```

Backdrop — очень лёгкий fade. Blur animation нежелательна: expensive и хуже для Reduce Motion/Reduce Transparency.

## 23.2. Results update

Результаты меняются быстро.

- no per-row entrance cascade;
- selected row indicator moves `80–120 ms`;
- content changes nearly instant.

## 23.3. Close

`120–160 ms`, но `Esc` должен логически закрыть overlay сразу: animation лишь визуально завершает dismiss.

---

# 24. Dialogs, confirmations, approvals

## 24.1. Modal появление

- fade + scale `0.99 → 1`;
- `160–240 ms`;
- backdrop fade `120 ms`.

No 3D zoom.

## 24.2. Critical destructive confirmation

Не использовать aggressive animation для запугивания.

Риск сообщается:

- wording;
- icon;
- button hierarchy;
- color;
- confirmation semantics.

Animation одинаковая с обычным dialog.

## 24.3. AI/user approval

Approval card лучше встроить в work context, а не каждый раз открывать modal. Brief highlight достаточно.

---

# 25. Notifications / toasts / badges

## 25.1. Toast

Desktop toast внутри приложения:

```text
opacity 0 → 1
translateY 8 px → 0
160–240 ms
```

Dismiss `120–160 ms`.

## 25.2. Badge

Число unread меняется через tiny crossfade/scale `80–120 ms`.

Не делать bouncing badge при каждом событии.

## 25.3. Repeated background events

Группировать. 25 готовых runs → один notification, а не 25 fly-ins.

---

# 26. Node / runtime / diagnostics

## 26.1. Health state transitions

`ready → degraded → unavailable` отображаются:

- icon/color;
- short status crossfade;
- one-time highlight.

Постоянный красный pulse не нужен.

## 26.2. Health check running

Можно использовать standard small process indicator.

## 26.3. Reconnect

Reconnect attempt:

- subtle rotating/flow glyph;
- status text;
- once connected, state settles.

Если попытки идут долго, motion должен оставаться очень тихим.

---

# 27. Empty states и first-run

## 27.1. Empty state не нужно оживлять постоянно

Static illustration/icon/text.

При первом появлении допустим `240 ms fade`.

## 27.2. First scenario success

Не требуется celebration.

Хороший эффект:

- artifact appears;
- success status;
- next action becomes visible;
- всё это соединено smooth transitions.

Для профессионального продукта этого достаточно.

---

# 28. Startup и perceived performance

## 28.1. Пороговые классы

### < 100 ms

Никакого loader.

### 100–400 ms

Local subtle feedback:

- button busy state;
- small inline progress indicator.

### 400 ms–2 s

Показать:

- stable shell;
- process line/spinner в relevant area;
- короткий текст состояния.

### > 2 s

Нужна structured progress surface:

- что происходит;
- stage;
- возможно cancel/retry;
- progress if known.

## 28.2. Shell-first

Лучше показать рабочую оболочку раньше и догружать части, чем держать splash screen.

Motion помогает сделать progressive availability спокойной:

```text
shell ready
→ sidebar content
→ history
→ artifacts
```

Но этот stagger должен отражать реальный loading, а не быть декоративной постановкой.

## 28.3. Skeletons

Использовать умеренно.

Подходят для:

- history card shapes;
- inspector metadata placeholders;
- list results.

Не подходят как постоянный shimmer всего интерфейса.

Если skeleton shimmer используется:

- медленный;
- low contrast;
- один direction;
- disabled under Reduced Motion.

---

# 29. Responsive layout и motion

## 29.1. Window resize

Прямое изменение размера окна — **без собственной delayed animation**.

UI следует за window geometry сразу.

## 29.2. Breakpoint transition

Когда layout меняется структурно:

```text
3 panes → 2 panes
2 panes → 1 pane
```

не нужно анимировать весь интерфейс 500 ms.

Лучше:

- fade outgoing secondary pane;
- retain active object;
- reposition main content quickly;
- 160–240 ms max.

## 29.3. Android compact surface

При переходах внутри mobile navigation motion semantics могут использовать больше whole-screen movement, потому что экран физически один. Но durations/easing/state meaning сохраняются.

Desktop и mobile не обязаны иметь одну геометрию, они должны иметь один **характер**.

---

# 30. Light / Dark / High Contrast

Motion tokens не зависят от темы.

Меняется только визуальный amplitude:

- gradient alpha;
- border contrast;
- highlight background;
- shadow usage.

High Contrast:

- не полагаться на subtle gradient как единственный running indicator;
- status text/icon остаются обязательными;
- decorative sheen может быть полностью выключен.

---

# 31. Reduced Motion — обязательный first-class mode

## 31.1. Это не «отключить всё CSS animation»

Motion иногда объясняет причинность. При reduced mode важный transition лучше заменить менее пространственным, а не обязательно уничтожить.

## 31.2. Mapping

| Default | Reduced Motion |
|---|---|
| slide + fade | short fade |
| connected move | crossfade + destination highlight |
| scale press | fill/color feedback |
| panel translate | fade / near-instant reveal |
| process sheen | static process rail + text |
| spinner | static status / minimally animated essential indicator |
| smooth long scroll | fast jump + destination highlight |
| animated blur/depth | no blur animation |

## 31.3. Настройка

Предлагается:

```text
Motion: System default
        Reduced
        Off / Minimal
```

Можно даже ограничиться:

```text
System default
Reduce animations
```

чтобы не создавать лишнюю настройку.

## 31.4. Qt

Новые версии Qt предоставляют platform accessibility motion preference через `QAccessibilityHints::motionPreference` (начиная с новых веток Qt 6).

Текущий `stratbox-windows` исторически заявлял PySide6 от более ранней версии, поэтому архитектура не должна напрямую зависеть от наличия конкретного API.

Целевая абстракция:

```text
MotionPreferenceProvider
├── QtAccessibilityProvider   (когда доступен)
├── Windows platform fallback
└── User preference override
```

## 31.5. Flashing

В Strategy Box в принципе нет продуктовой причины использовать flashing.

Требование:

> не проектировать визуальный feedback, приближающийся к повторяющимся ярким вспышкам; особенно исключить >3 flash/sec.

---

# 32. Accessibility beyond Reduced Motion

## 32.1. Motion никогда не является единственным carrier информации

Running:

- motion + text + icon/state.

Error:

- color + icon + label.

New item:

- insertion motion + actual list state.

## 32.2. Screen reader

Animation lifecycle не должен создавать ложные repeated announcements.

Например, shimmer loop не должен каждые 1.6 секунды менять accessibility tree.

## 32.3. Focus

Motion не должен уводить focus.

## 32.4. Keyboard

Keyboard navigation должна оставаться быстрее любой transition.

Rapid arrow keys по списку:

- active indicator может прерывать текущую анимацию и переходить к последнему target;
- очередь из десяти animation не накапливается.

---

# 33. Motion и производительность Qt desktop

## 33.1. Главная опасность — animation layout properties

В Qt Widgets постоянная animation `width/height/geometry` крупного дерева может вызывать layout/repaint на каждом кадре.

Поэтому:

- animate geometry только небольших контейнеров;
- benchmark inspector/sidebar transitions;
- большие списки не должны пересчитываться 60 раз/сек;
- по возможности использовать opacity/paint/transform-like effects вокруг стабильной geometry.

## 33.2. `QGraphicsOpacityEffect`

Удобен, но массовое применение к большим сложным widgets может быть дорогим. Его следует benchmark-ить, а не оборачивать им весь UI.

## 33.3. Shared animation clock

Ambient process effects лучше синхронизировать через общий animation/timer source, чем создавать десятки независимых timers.

## 33.4. Visible-only

Virtualized/offscreen rows не анимируются.

## 33.5. Progress event throttling

Core/runtime может генерировать очень частые progress events. Presentation layer должен:

- coalesce updates;
- не пересобирать UI на каждый байт/строку;
- визуально обновляться с разумной частотой;
- интерполировать последнюю подтверждённую величину.

## 33.6. Target frame rate

Цель — стабильные 60 fps на обычном современном desktop hardware.

Если это невозможно, правильная degradation strategy:

> уменьшать объём/сложность motion, а не сохранять всё движение на дёрганом frame rate.

---

# 34. Реализация на PySide6 / Qt

## 34.1. Базовые инструменты

### `QPropertyAnimation`

Для:

- opacity wrappers;
- geometry небольших объектов;
- custom numeric properties;
- indicator position/scale.

### `QEasingCurve`

Позволяет использовать общую Strategy Box easing policy, включая custom cubic Bezier.

### `QParallelAnimationGroup`

Для синхронных transition components:

```text
panel translate
+ panel opacity
+ main surface settle
```

### `QSequentialAnimationGroup`

Для короткой choreographed sequence:

```text
press
→ release
→ accepted state
```

Но sequence не должна блокировать backend action.

### `QScroller`

Для kinetic/programmatic scrolling там, где это соответствует input mode.

## 34.2. Не создавать animation прямо из бизнес handler

Неправильно:

```text
operation completed
→ handler knows QWidget
→ starts fade
```

Правильно:

```text
operation result
→ app state changes
→ presentation projector emits semantic transition
→ Qt motion adapter renders it
```

## 34.3. Возможный motion service

Концептуально:

```text
MotionService
  play(role, target, context)
  transition(role, from_state, to_state)
  scroll(role, target_position)
  cancel(scope)
  set_policy(full/reduced/off)
```

Сам интерфейс компонентов не должен знать точные milliseconds.

---

# 35. Cross-platform token package

## 35.1. Что хранить в shared layer

```text
MotionDuration
MotionEasing
MotionDistance
MotionRole
MotionPolicy
MotionTransitionSpec
ReducedMotionFallback
```

## 35.2. Пример conceptual descriptor

```text
PANEL_REVEAL:
  duration: fast
  easing: enter
  opacity: 0 → 1
  translate_x: +12 → 0
  reduced:
    duration: xfast
    opacity: 0 → 1
    translate_x: 0
```

## 35.3. Android потом просто реализует тот же descriptor

Это намного лучше, чем копировать Qt animation code и вручную имитировать его в другом toolkit.

---

# 36. Motion roles — предлагаемый полный каталог

```text
MICRO_HOVER
MICRO_PRESS
MICRO_RELEASE
FOCUS_APPEAR
SELECTION_MOVE

CONTENT_ENTER
CONTENT_EXIT
CONTENT_REPLACE
ITEM_INSERT
ITEM_REMOVE
ITEM_UPDATE_HIGHLIGHT

NAV_TOP_LEVEL
NAV_DRILL_IN
NAV_DRILL_OUT
CONNECTED_OBJECT

SIDEBAR_CONTENT_SWITCH
INSPECTOR_REVEAL
INSPECTOR_DISMISS
BOTTOM_PANEL_REVEAL
BOTTOM_PANEL_DISMISS

EXPAND
COLLAPSE
ADVANCED_REVEAL

RUN_SUBMIT
RUN_INSERT
RUN_QUEUED
RUN_START
RUN_PROGRESS
RUN_WAITING
RUN_SUCCESS
RUN_WARNING
RUN_ERROR
RUN_CANCEL

STEP_START
STEP_COMPLETE
STEP_ERROR

PROCESS_INDETERMINATE
PROCESS_DETERMINATE
STREAM_ACTIVE

MESSAGE_INSERT
SYSTEM_EVENT_INSERT
NEW_ACTIVITY_BADGE

ARTIFACT_INSERT
ARTIFACT_REVEAL
ARTIFACT_CONNECTED_OPEN

PROGRAMMATIC_SCROLL_SHORT
PROGRAMMATIC_SCROLL_MEDIUM
PROGRAMMATIC_SCROLL_LONG
DESTINATION_HIGHLIGHT

TOAST_ENTER
TOAST_EXIT
DIALOG_ENTER
DIALOG_EXIT

SEARCH_OVERLAY_ENTER
SEARCH_OVERLAY_EXIT

HEALTH_STATE_CHANGE
RECONNECT_ACTIVE
```

Этого набора достаточно для системного покрытия приложения без component-specific хаоса.

---

# 37. Motion matrix по основным компонентам

| Компонент | Event | Motion | Duration |
|---|---|---|---:|
| Rail | hover | fill fade | 80 ms |
| Rail | active change | indicator move | 160 ms |
| Sidebar | context change | fade + 4px | 160 ms |
| Main | top-level navigation | fade + 6px | 160–240 ms |
| Inspector | open | fade + 12px | 160–240 ms |
| Inspector | close | fade + 8px | 120–160 ms |
| Bottom panel | open | reveal + fade | 160–240 ms |
| Button | press | scale 0.985 | 80 ms |
| Button | release | scale 1 | 120 ms |
| Toggle | state | thumb move | 160 ms |
| Tree | expand | chevron rotation | 120–160 ms |
| List | selection | background | 80 ms |
| Form | advanced | reveal | 160–240 ms |
| Scenario | submit | press + handoff | 80 + 160 ms |
| Run | insert | fade + 8px | 160–240 ms |
| Run | running | process sheen | 1.4–1.8 s loop |
| Run | success | settle/check | 160–240 ms |
| Run | error | state transition | 120–160 ms |
| Step | next active | marker move | 160–240 ms |
| Message | insert | fade + 4px | 160 ms |
| Artifact | create | fade + 4px | 160–240 ms |
| Log | important line | highlight settle | 480–800 ms |
| Toast | enter | fade + 8px | 160–240 ms |
| Dialog | enter | fade + scale .99 | 160–240 ms |
| Program scroll | short | smooth scroll | 160 ms |
| Program scroll | medium | smooth scroll | 240 ms |
| Program scroll | long | capped scroll | 320 ms |

---

# 38. Что делать с animation при очень быстрых действиях

## 38.1. Rapid navigation

Пользователь быстро кликает:

```text
Работа → Проводник → Сценарии
```

Не нужно проигрывать три transitions последовательно.

Правило:

> animation always targets latest requested state.

Текущая animation прерывается/перенаправляется.

## 38.2. Rapid list selection

Active highlight следует за последним selection. Intermediate animation frames не являются событиями.

## 38.3. Repeated expand/collapse

Transition может reverse from current progress.

Это ощущается намного качественнее, чем snap после попытки повторного клика.

---

# 39. Что делать при смене данных во время анимации

UI state является source of truth.

Если run успел перейти:

```text
queued → running → success
```

быстрее, чем закончилась queued-to-running animation, presentation не обязана проиграть всё кино.

Она может:

- cancel obsolete transition;
- быстро settle в success;
- показать финальный state.

Анимация никогда не должна задерживать truth.

---

# 40. Отдельный вопрос: scrolling должен ощущаться «дорого»

Плавность мессенджера очень сильно определяется не fancy transitions, а качеством scrolling.

## 40.1. Требования

- отсутствие micro-jank;
- stable item heights по возможности;
- lazy loading без jump;
- correct anchoring при prepend history;
- programmatic scroll с коротким easing;
- no forced auto-scroll when user reads older content;
- scrollbars update predictably;
- selection remains visible.

## 40.2. Почему это важнее десяти button animations

Пользователь прокручивает timeline/log/files сотни раз. Даже 5% jank воспринимается сильнее, чем отсутствие красивого hover.

Поэтому motion roadmap должен сначала обеспечить scroll physics/performance, затем декоративные microinteractions.

---

# 41. Motion и таблицы

Strategy Box со временем почти наверняка получит больше tabular previews.

## 41.1. Не анимировать cells при обычном обновлении

Изменение чисел:

- static replacement;
- при важном live update возможен background highlight settle.

## 41.2. Sort

Не нужно визуально возить тысячи строк на новые позиции.

- list/table changes;
- selected row сохраняется или явно сбрасывается;
- small content crossfade допустим.

## 41.3. Filter

Same: fast update, no per-row cascade.

## 41.4. New data

Если пришла одна новая row:

- insertion highlight допустим.

Если refresh заменил 10k rows:

- один global update state, не 10k анимаций.

---

# 42. Charts — будущая motion policy

Хотя текущий фокус не charts, motion system должна заранее задать правило.

## 42.1. Initial render

Не обязателен fancy draw-on effect.

## 42.2. Data update

Если ось/series identity сохраняется, можно smoothly interpolate values `240–320 ms`.

## 42.3. Period switch

Crossfade/interpolate, если это помогает comparison.

## 42.4. Avoid

- perpetual moving charts;
- bouncing bars;
- dramatic zoom;
- animation, которая искажает восприятие финансовых значений.

---

# 43. Microinteractions, которые стоит добавить даже при очень минимальном дизайне

1. hover/focus transition кнопок;
2. pressed state;
3. active rail indicator move;
4. chevron rotate;
5. inspector reveal;
6. advanced parameters reveal;
7. new run insertion;
8. process sheen;
9. progress interpolation;
10. step marker transition;
11. artifact insertion;
12. destination highlight;
13. new activity badge;
14. toast reveal;
15. smooth programmatic scroll;
16. follow-tail chip;
17. status pill state transition;
18. toggle thumb motion;
19. connected artifact → preview;
20. brief update highlight for changed content.

Вот именно это и есть модель «минимально, но много».

Ни одна из этих анимаций сама по себе почти не заметна, но вместе они создают качество.

---

# 44. Motion, который не стоит добавлять

## 44.1. Bounce everywhere

Нет.

## 44.2. Springs by default

Нет. Если когда-нибудь и использовать spring, только для direct touch physics на mobile, где это native behavior.

## 44.3. Decorative parallax

Нет.

## 44.4. Large-scale zoom

Нет.

## 44.5. Animated background

Нет.

## 44.6. Hue cycling

Нет.

## 44.7. Constant glowing selected item

Нет.

## 44.8. Pulsating red errors

Нет.

## 44.9. Confetti / fireworks on success

Нет.

## 44.10. Typewriter imitation for AI

Не требуется. Реальный streaming достаточно живой.

## 44.11. Fancy startup logo animation

Минимально либо совсем не нужно. Быстрый shell полезнее.

## 44.12. Animation for every table update

Нет.

---

# 45. Motion personality Strategy Box

Можно сформулировать пять слов:

> **precise · calm · connected · responsive · computational**

### Precise

Движение ровно настолько большое и долгое, сколько нужно.

### Calm

После события всё возвращается в покой.

### Connected

Объекты продолжают существовать между состояниями.

### Responsive

Input feedback возникает сразу.

### Computational

Ongoing work имеет собственный узнаваемый motion-language: thin gradient rails, progress, stages.

---

# 46. Визуальная идентичность процесса

Вместо brand animation ради brand animation лучше сделать **брендом поведение вычисления**.

Три узнаваемых элемента:

1. **process sheen**;
2. **step handoff**;
3. **result settle**.

Пользователь со временем без чтения текста понимает:

```text
тихий движущийся акцент = система работает
маркер перешёл ниже     = следующий шаг
акцент исчез + result   = завершено
```

Это полезная идентичность.

---

# 47. Взаимодействие motion с sound/haptics

Windows desktop Strategy Box не нуждается в системных звуках на каждое действие.

В будущем Android:

- light haptic на explicit submit/approval может быть уместен;
- success/error haptics только для важных direct user actions;
- background task completion — через notification policy, не постоянный haptic.

Motion semantics должны оставаться понятными и без sound/haptics.

---

# 48. Motion и multi-user collaboration

## 48.1. Presence

Online/offline participant:

- tiny state crossfade;
- никакой постоянной пульсации online-dot.

## 48.2. Someone is working

Если в будущем нужен live collaboration indicator:

- small avatar/activity glyph;
- activity motion only while meaningful action occurs;
- no avatar bobbing.

## 48.3. Assignment

Новое поручение:

- insert + one-time highlight;
- badge update;
- no persistent animation after read.

---

# 49. Motion и remote execution

Remote execution делает особенно важным различие состояний:

```text
submitted locally
transmitted
accepted by node
queued remotely
running remotely
result transferring
completed
```

Не обязательно показывать каждое как отдельную animation, но UI должен иметь transition model.

Potential visual semantics:

- local accepted → card insert;
- remote acknowledged → status settle;
- running → process motion;
- result transfer → determinate/indeterminate transfer bar;
- complete → artifact insertion.

Motion помогает скрыть network latency без сокрытия state truth.

---

# 50. Motion и AppDock boundary

Strategy Box не должен рисовать системную сложность AppDock как бесконечный набор технических spinners.

AppDock/runtime состояние проецируется в понятные states:

```text
готово
подготовка
нужна авторизация
недоступно
восстановление
```

Каждый использует общий motion language.

---

# 51. Архитектурное предложение: MotionPolicy

MotionPolicy определяет runtime behavior.

```text
FULL
REDUCED
OFF/MINIMAL
```

Возможно пользовательски показывать только:

```text
Use system setting
Reduce animations
```

а три внутренних режима оставить implementation detail.

Policy влияет на:

- translation distances;
- scale;
- ambient loops;
- scroll animation;
- connected transitions;
- blur/depth;
- decorative effects.

Не влияет на:

- final states;
- progress numbers;
- status labels;
- accessibility semantics.

---

# 52. Motion testability

Motion часто превращается в source flaky tests. Этого нужно избежать архитектурой.

## 52.1. Deterministic motion clock

Желательно иметь возможность в tests:

- поставить duration = 0;
- либо управлять virtual animation time.

## 52.2. State tests отдельно от visual tests

Business/presentation state tests не должны ждать реальные 240 ms.

## 52.3. Motion contract tests

Проверять:

- каждому role задан spec;
- reduced fallback существует;
- обычная animation не превышает установленный максимум;
- ambient roles являются whitelist;
- no forbidden bounce/spring in core theme.

## 52.4. Interaction torture tests

Обязательно тестировать:

- rapid nav clicks;
- 20 быстрых selections;
- open/close inspector repeatedly;
- resize during transition;
- minimize while shimmer runs;
- 20 simultaneous running cases;
- logs 100k lines;
- new activity while scrolled up;
- cancel while transition still plays;
- success arriving immediately after run start;
- reduced-motion change at runtime.

---

# 53. Performance acceptance criteria

Рекомендуемые продуктовые критерии:

## 53.1. Input

- visual feedback < 50–80 ms;
- backend action не waits for animation.

## 53.2. Structural transitions

- typical ≤ 240 ms;
- rare ≤ 320 ms;
- emphasis ≤ 480 ms only with reason.

## 53.3. Frame pacing

- stable 60 fps target;
- no visible frame drops on standard navigation;
- large logs/lists remain scrollable while background animation active.

## 53.4. CPU

Idle application with no running tasks should иметь практически нулевую motion activity.

## 53.5. Background

Inactive/minimized surface pauses nonessential loops.

---

# 54. Motion acceptance criteria UX

Пользователь после первого дня работы должен без подсказок различать:

- object selected;
- action accepted;
- operation queued;
- operation running;
- operation waiting for user;
- operation succeeded;
- operation failed;
- result appeared;
- new unseen activity exists.

При этом он не должен уметь назвать 15 разных animations — они должны восприниматься как единая система.

---

# 55. Приоритет реализации

## Phase 0 — Motion foundation

1. Motion tokens.
2. Motion roles.
3. MotionPolicy.
4. Reduced Motion mapping.
5. Qt adapter.
6. Shared easing implementation.
7. Animation cancellation/re-targeting rules.

## Phase 1 — core microinteractions

1. buttons;
2. rail selection;
3. hover/focus;
4. expand/collapse;
5. inspector;
6. sidebar content change;
7. bottom panel;
8. toast/dialog.

## Phase 2 — scrolling quality

1. chat anchoring;
2. log follow-tail;
3. programmatic scroll;
4. history prepend;
5. destination highlight;
6. QScroller/native input policy.

## Phase 3 — execution motion

1. run submit;
2. run card insertion;
3. queued/running transition;
4. process sheen;
5. determinate progress;
6. step transitions;
7. cancel;
8. success/warning/error settle.

## Phase 4 — artifacts / Explorer continuity

1. artifact insert;
2. reveal in Explorer;
3. preview connected transition;
4. file-created highlight;
5. folder navigation.

## Phase 5 — AI/collaboration

1. thinking/tool activity;
2. AI streaming behavior;
3. approval transition;
4. participant activity;
5. assignments/unread.

## Phase 6 — Android conformance

1. implement same MotionRole mapping;
2. platform-native direct scroll/touch physics;
3. compare visual recordings Windows vs Android;
4. tune only platform implementation, not semantics.

---

# 56. Что реализовать первым как demonstrator

Если нужно быстро проверить направление, достаточно одного end-to-end prototype:

```text
Scenario selected
→ parameters revealed
→ press Run
→ new run card inserts
→ soft process gradient starts
→ step 1 complete
→ step marker moves
→ artifact appears
→ run settles to success
→ click artifact
→ connected transition to preview
→ Reveal in Explorer
→ file destination highlight
```

Если эта цепочка ощущается цельно, motion-language практически найден.

---

# 57. Motion storyboard: запуск сценария

```text
T+0 ms
User presses "Запустить"

T+0..80
button pressed state

T+20
backend submit already dispatched

T+80..160
button release
composer/form stays stable

T+80..240
run card inserted into Work timeline

T+160
status = queued/preparing

T+200...
status = running
process sheen starts

step event
active marker settles to current step

artifact event
artifact chip fades into run card / timeline

completion
process sheen completes/fades
success icon settles
result actions enable
```

Backend timeline и visual timeline связаны, но visual animation никогда не задерживает backend.

---

# 58. Motion storyboard: ошибка

```text
running
process sheen active

error event arrives

0 ms
stop active progress semantics

0..120 ms
status color/icon transitions to error

80..240 ms
error summary + Retry / Open log appear

optional 240..640 ms
very subtle error-row background highlight settles

rest
fully static actionable error state
```

Главное — после 0.5 секунды интерфейс уже спокоен.

---

# 59. Motion storyboard: новый результат в Проводнике

```text
run completes
artifact created

Work surface:
artifact chip inserts

user clicks "Показать в Проводнике"

main surface changes
folder content appears
programmatic scroll to file if necessary
file row receives 480 ms highlight settle

rest
```

Это один из лучших вариантов применить motion для причинности.

---

# 60. Motion storyboard: AI предлагает scenario

```text
AI answer streams
↓
scenario suggestion card inserts
↓
user opens parameters
↓
parameters reveal
↓
user approves / launches
↓
card transitions to real run object
↓
standard execution motion
```

AI не получает отдельной universe of animations. После запуска он входит в обычную систему Strategy Box.

---

# 61. Motion storyboard: пользователь читает старую историю

```text
user is 4 screens above bottom
↓
new event arrives
↓
NO auto-scroll
↓
"3 новых события ↓" appears
↓
user clicks
↓
smooth scroll capped at 320 ms
↓
destination group gets brief highlight
```

Это качественный messenger behavior и обязательная часть продукта.

---

# 62. Visual density: motion in compact mode

В будущем может появиться compact density.

Motion timing остаётся тем же, но:

- distances можно снизить на 20–30%;
- shadows/elevation меньше;
- insertion uses mostly fade;
- process rail остаётся 2 px.

Motion не должен ломать high-density layout.

---

# 63. Touch vs mouse

## Mouse

- hover exists;
- press tiny;
- no large ripple;
- wheel native.

## Touch

- no hover;
- press feedback должен быть яснее;
- touch ripple/highlight возможен через platform-native implementation;
- scroll kinetic;
- larger direct-manipulation response.

Но `RUN_START`, `PANEL_REVEAL`, `STATUS_CHANGE` остаются одними и теми же semantic roles.

---

# 64. Почему не нужно буквально копировать Apple

Apple полезен как ориентир:

- continuity;
- transition hierarchy;
- precise motion;
- high-quality scrolling;
- Reduce Motion.

Но desktop Strategy Box:

- плотнее;
- более keyboard-first;
- содержит technical logs;
- показывает долгие computations;
- имеет Windows Explorer-like surface.

Поэтому целевой продукт ближе к:

> **Windows operational semantics + Apple precision + messenger-quality scrolling + assistant-like process feedback.**

---

# 65. Почему не нужно буквально копировать ChatGPT

ChatGPT полезен как ориентир спокойствия и ongoing-work feedback.

Strategy Box отличается:

- operations имеют строгий lifecycle;
- есть queue;
- есть step semantics;
- есть artifacts;
- есть logs;
- есть files;
- есть reproducibility/audit expectations.

Поэтому soft gradient должен быть частью structured run state, а не универсальным индикатором «AI думает».

---

# 66. Почему не нужно буквально копировать мессенджеры

Messenger scrolling/insertion patterns полезны.

Но scenario cards:

- крупнее сообщений;
- имеют status;
- могут жить минуты/часы;
- получают progress;
- создают artifacts.

Значит execution object должен быть устойчивой карточкой, а не bubble, которая постоянно перестраивается.

---

# 67. Почему не нужно превращать interface в IDE

IDE-подобные панели и logs — полезны.

Но IDE часто позволяет очень плотный быстрый UI почти без motion. Strategy Box может быть чуть мягче и объясняюще, потому что его пользователь не обязан мыслить как разработчик.

Motion должен превращать technical state в понятный workflow.

---

# 68. Минимальный Motion Design System как deliverable

В проекте стоит завести отдельный документ/модуль примерно такого содержания:

```text
MOTION.md

1. Principles
2. Roles
3. Tokens
4. Curves
5. Reduced Motion
6. State mappings
7. Component mappings
8. Performance rules
9. Accessibility rules
10. QA examples
```

И machine-readable часть:

```text
motion_tokens.py / motion_tokens.json
```

или equivalent shared constants.

Это защищает продукт от постепенного превращения motion в набор случайных локальных решений.

---

# 69. Рекомендуемые настройки по умолчанию

```text
Motion profile: System
Process animations: On
Smooth programmatic scrolling: On
Reduce animations: inherited from OS
```

Не стоит давать пользователю sliders вида:

```text
animation speed: 73%
shimmer intensity: 42%
```

Это design system responsibility.

---

# 70. Telemetry / usability research

Если позже появится продуктовая телеметрия, полезно измерять не «нравится ли анимация», а последствия:

- повторные клики по Run в первые 500 ms — возможно feedback неясен;
- частые premature cancel — progress unclear;
- users manually open logs слишком часто — status summary недостаточен;
- new-activity pill ignored — placement/animation ineffective;
- users disable motion — система слишком активна.

Motion качество измеряется поведением, а не красотой demo.

---

# 71. Критерии code review для каждой новой animation

Перед добавлением animation разработчик должен ответить:

1. Какое изменение состояния она объясняет?
2. Часто ли это действие происходит?
3. Можно ли сделать эффект меньше?
4. Нужна ли spatial motion или достаточно fade/color?
5. Блокирует ли animation input/action?
6. Что происходит при rapid repeated input?
7. Что происходит при Reduce Motion?
8. Есть ли non-motion carrier информации?
9. Сколько таких animations может быть одновременно?
10. Как animation ведёт себя offscreen/minimized?
11. Не вызывает ли она layout/repaint bottleneck?
12. Есть ли motion role/token или снова magic number?

Если на первый вопрос нет ясного ответа — animation не нужна.

---

# 72. P0 / P1 / P2 приоритеты

## P0 — до расширения анимаций

- единые tokens;
- MotionPolicy;
- reduced motion;
- cancellation/retargeting;
- performance rules;
- scroll anchoring.

## P1 — наиболее полезный продуктовый motion

- run submit/insert;
- running process sheen;
- determinate progress;
- step transitions;
- inspector;
- artifact insertion;
- smooth programmatic scroll;
- new activity indicator.

## P2 — polish

- connected artifact preview;
- icon morphs;
- subtle list reorders;
- AI-specific activity nuance;
- collaboration activity.

---

# 73. Итоговая motion-концепция по поверхности

```text
┌ Rail ┐  selected indicator quietly moves
│      │
├ Context sidebar ─ content crossfades / 4px settles
│
├ Main Work timeline
│   human/AI messages insert softly
│   run card appears
│   thin process gradient shows computation
│   step marker advances
│   artifact appears
│
├ Inspector ─ 12px / fade contextual reveal
│
└ Bottom panel ─ short reveal; raw logs stay calm
```

В статике такой интерфейс выглядит почти неподвижным.

Во время работы он живёт ровно там, где меняется состояние.

Это и есть правильная цель.

---

# 74. Итоговые тезисы

1. Motion Strategy Box должен стать **системой**, а не набором widget effects.
2. Основная эстетика — «много микроанимаций, почти нет больших».
3. Animation всегда отражает state/causality/navigation.
4. Input feedback — практически мгновенный.
5. Стандартные durations: 80 / 160 / 240 / 320 ms.
6. 480 ms — только редкий emphasis.
7. Ambient loops допустимы только для реального ongoing work.
8. Главный фирменный эффект — low-contrast process sheen/gradient.
9. Gradient живёт в узкой process surface, а не на всём фоне.
10. Bounce/spring/parallax/confetti/hue-cycling в основном языке отсутствуют.
11. Структурные переходы используют small fade/translate.
12. Connected motion используется только для сохранения object continuity.
13. Scrolling quality важнее декоративных transitions.
14. Direct user scroll остаётся platform-native.
15. Programmatic scroll унифицирован и capped примерно 320 ms.
16. Chat никогда не auto-scroll, если пользователь читает историю выше.
17. Logs при высокой частоте обновляются без per-line animation.
18. Progress по возможности determinate и всегда честный.
19. Progress не сбрасывается и не идёт назад.
20. Run lifecycle имеет единый motion storyboard.
21. Error быстро приходит в спокойное actionable state.
22. Success не сопровождается celebration-анимацией.
23. Artifacts получают one-time insertion и destination transitions.
24. AI использует тот же execution motion language, что человек.
25. Windows и Android используют одни semantic MotionRole/tokens.
26. Input physics может оставаться platform-native.
27. Reduced Motion — обязательный first-class mode.
28. Motion никогда не является единственным carrier статуса.
29. Неактивные/offscreen loops должны останавливаться.
30. Animation не может задерживать truth или backend action.
31. Rapid input retargets animation к последнему состоянию.
32. Layout-heavy Qt animations требуют benchmark.
33. Large tables/lists почти не анимируются на уровне строк.
34. Idle приложение должно быть визуально и вычислительно спокойным.
35. Лучший критерий качества: пользователь понимает процессы, почти не замечая самих анимаций.

---

# 75. Финальная формула

Strategy Box не нужен «анимированный интерфейс».

Ему нужен **интерфейс, в котором движение является грамматикой изменения состояния**.

Целевой опыт можно сформулировать так:

> Нажатие ощущается немедленно. Панели появляются мягко. Контекст никогда не теряется. Скролл идеально удерживает взгляд. Запуск сценария естественно превращается в живой run-object. Пока идёт вычисление, тихий градиент показывает, что система работает. Шаги спокойно сменяют друг друга. Результат возникает там, где его ожидаешь. После завершения всё снова становится неподвижным.

Для финансово-аналитического приложения это оптимальный баланс между современностью, минимализмом, понятностью и профессиональной сдержанностью.

---

# 76. Внешние источники

Дата обращения: 2026-10-07.

## Microsoft / Windows

1. Microsoft Learn — **Motion in Windows**  
   https://learn.microsoft.com/en-us/windows/apps/design/motion/

2. Microsoft Learn — **Timing and easing**  
   https://learn.microsoft.com/en-us/windows/apps/design/motion/timing-and-easing

3. Microsoft Learn — **Page transitions**  
   https://learn.microsoft.com/en-us/windows/apps/develop/motion/page-transitions

4. Microsoft Learn — **Connected animation**  
   https://learn.microsoft.com/en-us/windows/apps/develop/motion/connected-animation

5. Microsoft Learn — **Motion in practice**  
   https://learn.microsoft.com/en-ca/windows/apps/design/motion/motion-in-practice

6. Microsoft Learn — **Progress controls**  
   https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/progress-controls

## Apple

7. Apple Human Interface Guidelines — **Motion**  
   https://developer.apple.com/design/human-interface-guidelines/motion

8. Apple Human Interface Guidelines — **Accessibility**  
   https://developer.apple.com/design/human-interface-guidelines/accessibility

9. Apple Developer — **Reduced Motion evaluation criteria**  
   https://developer.apple.com/help/app-store-connect/manage-app-accessibility/reduced-motion-evaluation-criteria

## Android / Material

10. Android Developers — **Material Design 3 theming / Motion**  
    https://developer.android.com/codelabs/m3-design-theming

11. Android Developers — **Animation resources / Material motion examples**  
    https://developer.android.com/develop/ui/views/animations/additional-resources

## Qt / PySide

12. Qt for Python — **QEasingCurve**  
    https://doc.qt.io/qtforpython-6/PySide6/QtCore/QEasingCurve.html

13. Qt for Python — **QPropertyAnimation**  
    https://doc.qt.io/qtforpython-6.10/PySide6/QtCore/QPropertyAnimation.html

14. Qt for Python — **QParallelAnimationGroup**  
    https://doc.qt.io/qtforpython-6/PySide6/QtCore/QParallelAnimationGroup.html

15. Qt for Python — **QSequentialAnimationGroup**  
    https://doc.qt.io/qtforpython-6/PySide6/QtCore/QSequentialAnimationGroup.html

16. Qt for Python — **QScroller**  
    https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QScroller.html

17. Qt — **QAccessibilityHints / motionPreference**  
    https://doc.qt.io/qt-6.12/qaccessibilityhints.html

## Accessibility

18. W3C WAI — **WCAG 2.2: Three Flashes or Below Threshold**  
    https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold

19. W3C WAI — **WCAG 2.2 Quick Reference / Animation from Interactions**  
    https://www.w3.org/WAI/WCAG22/quickref/

---

# 77. Связанные внутренние исследования

- `stratbox-windows_current_state_full_research_2026-10-06.md`
- `stratbox_windows_interface_requirements_research_2026-10-07.md`
- `stratbox_base_study_current_state_2026-10-06.md`
- `AppDock - Базовое описание.docx`

