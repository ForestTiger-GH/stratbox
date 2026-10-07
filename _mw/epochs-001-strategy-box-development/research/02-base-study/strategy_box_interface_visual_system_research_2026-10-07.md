# Strategy Box — стилистическая система интерфейса и параметры визуального языка

**Ветка исследований:** 02 / interface style study  
**Дата:** 2026-10-07  
**Объект:** Strategy Box / `stratbox-windows`  
**Статус:** Research Result / целевая дизайн-спецификация. Код и репозитории этим документом не изменяются.

---

## 0. Краткий вывод

Для Strategy Box наиболее естественна визуальная модель **Calm Operational Premium**: спокойное профессиональное desktop-приложение, которое по ощущениям находится между современной системной Windows-программой, рабочей платформой и мессенджером, но не выглядит ни «корпоративной формой 2008 года», ни глянцевым sci-fi dashboard.

Визуальная система должна строиться вокруг пяти принципов:

1. **Нейтральная рабочая поверхность.** Основная площадь интерфейса — светлая или тёмная нейтральная база с очень небольшим количеством насыщенного цвета.
2. **Цвет — преимущественно действие и состояние.** Яркий акцент нужен для primary-action, selection, focus, progress и редких специальных состояний. Он не должен окрашивать всё приложение.
3. **Типографика компактная, но не мелкая.** Базовый размер 13 px для desktop Strategy Box выглядит уместно; главный текст стоит сделать тёмно-серым, а не абсолютным чёрным.
4. **Воздух формируется системой отступов, а не огромными карточками.** Основная сетка — 4 px; типовые расстояния — 8, 12, 16, 24 и 32 px.
5. **Светлая и тёмная темы должны быть одной семантической системой.** Тема меняет токены, а компоненты остаются теми же.

Главное изменение относительно текущего состояния — перейти от большого набора hardcoded QSS-цветов к **design token architecture**: primitive tokens → semantic tokens → component tokens → Qt/QSS renderer.

Это одновременно решает:

- светлую и тёмную темы;
- пользовательский accent color;
- Windows/system theme;
- будущий Android frontend;
- повышенную контрастность;
- единое управление плотностью, радиусами, отступами и motion;
- снижение визуального шума.

При этом текущий интерфейс уже находится довольно близко к нужному направлению: `Segoe UI`/`Inter`, 13 px, спокойный светлый фон, мягкая палитра, scenario-chat, динамическая ширина сообщений, плавная прокрутка и отдельный inspector. Нужен не новый дизайн с нуля, а **систематизация, упрощение и доведение до единого визуального языка**.

---

# I. Исходная рамка

## 1. Что учитывалось

Исследование опирается на:

- актуальное исследование `stratbox-windows` от 2026-10-06;
- фактический текущий `main` репозитория `ForestTiger-GH/stratbox-windows`;
- текущий `app.qss`;
- `strategy_palette.py`;
- shell, scenario-chat, settings, mode rail и workspace UI;
- архитектурную границу `stratbox` ↔ application surface;
- базовую модель AppDock;
- предыдущие решения по интерфейсу Strategy Box;
- приложенные варианты логотипа;
- актуальные рекомендации Fluent / Windows;
- актуальные рекомендации Apple HIG для light/dark color semantics;
- WCAG 2.2 по контрастности текста и UI-components.

Документ описывает **целевой интерфейс**, а не только текущее состояние.

---

## 2. Что уже есть в текущем UI

В текущем `app.qss` уже заложена достаточно разумная база:

```text
base background       #F4F7FA
surface               #FFFFFF
primary text          #111827
secondary text        #6B7280
font                  Segoe UI / Inter
base font size        13 px
```

Также уже используются:

- мягкий teal для active-selection;
- отдельный primary Run button;
- отдельный secondary/details accent;
- status chips;
- incoming/outgoing case bubbles;
- отдельные success/running/error поверхности;
- белая левая shell-панель;
- белый inspector;
- нейтральный центральный фон;
- динамическая ширина bubble;
- плавная прокрутка сценарной ленты.

Текущий `ModeRail`:

```text
width            96 px
button           96 × 84 px
icon             34 × 34 px
```

Scenario chat уже использует:

```text
outer margins    28 / 24 px
row spacing      12 px
smooth scroll    160–180 ms
wheel animation  120 ms
```

Это подтверждает, что выбранное ранее направление было правильным. Проблема сейчас в другом: значения распределены по QSS и виджетам как **локальные решения**, а не как единая система.

---

# II. Характер интерфейса Strategy Box

## 3. Ключевое ощущение

Strategy Box должен восприниматься как:

> **спокойный профессиональный инструмент, в котором сложная аналитическая работа выглядит простой и управляемой.**

Подходящие ассоциации:

- Windows 11 / Fluent — системность и понятность;
- ChatGPT / современные messenger-like surfaces — мягкая лента и диалоговая работа;
- профессиональные IDE/data tools — высокая информационная плотность;
- Apple — аккуратная иерархия и отсутствие лишних линий;
- хорошие банковские desktop tools — серьёзность и предсказуемость.

Неподходящие ассоциации:

- неоновый cyberpunk;
- стеклянный sci-fi launcher;
- dashboard с десятками цветных карточек;
- тяжёлый «корпоративный портал»;
- oversized mobile UI на desktop;
- чёрный фон + кислотные линии;
- бесконечные pill-buttons.

---

## 4. Визуальная иерархия

В интерфейсе должны существовать четыре визуальных уровня.

### Уровень 1 — рабочая среда

Это canvas приложения.

Он максимально спокойный и почти бесцветный.

### Уровень 2 — функциональные поверхности

Например:

- левый shell;
- inspector;
- composer;
- диалог;
- рабочая таблица;
- case bubble.

Их разделяет:

- небольшой тон;
- граница;
- иногда elevation.

### Уровень 3 — интерактивность

Здесь появляется accent color:

- выбранный режим;
- primary action;
- focus;
- selection;
- ссылка;
- active progress.

### Уровень 4 — исключение

Здесь появляется semantic color:

- ошибка;
- предупреждение;
- успех;
- destructive action.

Главное правило:

> Чем больше площадь элемента, тем меньше насыщенного цвета он должен содержать.

---

# III. Логотип и бренд

## 5. Что даёт приложенный логотип

Визуальный центр логотипа — прозрачный куб с яркой синей внутренней поверхностью и светящейся кромкой.

Основная цветовая зона куба находится примерно в диапазоне:

```text
cobalt / electric blue
≈ #2F6FEF — #4388F3
```

В расширенном тёмном варианте присутствуют:

- cyan;
- electric blue;
- violet;
- немного тёплого orange/pink glow.

Это хороший **brand asset**, но плохая готовая UI palette.

Если перенести такую насыщенность на:

- кнопки;
- карточки;
- selection;
- фон;
- навигацию,

интерфейс быстро начнёт «рябить».

---

## 6. Как использовать логотип

### В самом логотипе

Куб можно оставить насыщенным и почти без изменений.

Это место, где визуальная энергия уместна.

### В основном интерфейсе

Берётся **приглушённый производный Strategy Blue**, а не наиболее яркий пиксель логотипа.

Целевой primary accent для светлой темы:

```text
Strategy Blue 500 = #316BE5
```

Это всё ещё явно синий бренд, но уже рабочий.

### Где допустим полный electric gradient

- splash / startup;
- About;
- app icon;
- маленький brand mark;
- progress/running accent;
- редкий hero state;
- onboarding.

### Где его быть не должно

- весь левый sidebar;
- все кнопки;
- таблицы;
- каждый заголовок;
- все bubbles;
- весь inspector.

---

## 7. Wordmark

В рабочем shell лучше использовать спокойный wordmark:

```text
Strategy Box
```

без тяжёлого bold.

Рекомендация:

```text
16 px
weight 500
letter spacing 0
```

В светлой теме:

```text
#20242B
```

В тёмной:

```text
#F2F4F7
```

Рядом может стоять компактный куб 22–28 px.

Полный большой логотип нужен только на специальных surface, а не постоянно в рабочей навигации.

---

# IV. Design-token architecture

## 8. Почему QSS с hex-кодами недостаточно

Текущий QSS содержит много прямых значений:

```text
#F4F7FA
#111827
#6B7280
#3D777B
#C7A27A
#E5ECF2
...
```

Это работает для одной темы.

При появлении:

- dark mode;
- system theme;
- custom accent;
- high contrast;
- Android;
- альтернативной density,

такой подход начинает быстро разрастаться.

Целевая модель:

```text
Primitive Tokens
       ↓
Semantic Tokens
       ↓
Component Tokens
       ↓
Renderer
       ├── Qt/QSS
       └── future Android
```

---

## 9. Primitive tokens

Primitive — это сырые значения.

Например:

```text
blue.050
blue.100
blue.200
...
blue.900

gray.000
gray.025
...
gray.950

space.1
space.2
space.3
...

radius.sm
radius.md
radius.lg
```

Компонент никогда не должен напрямую говорить:

```text
background = #F5F7FA
```

Он должен говорить:

```text
background = surface.canvas
```

---

## 10. Semantic tokens

Пример:

```text
surface.canvas
surface.primary
surface.secondary
surface.elevated
surface.hover
surface.selected

text.primary
text.secondary
text.muted
text.disabled

border.subtle
border.default
border.strong

accent.default
accent.hover
accent.pressed
accent.soft
accent.focus

status.success.*
status.warning.*
status.error.*
status.info.*
```

Тогда light/dark/custom меняют значения токенов, а компонент остаётся прежним.

---

# V. Типографика

## 11. Основной шрифт

Для Windows:

```text
Segoe UI Variable
```

Fallback:

```text
Segoe UI
Inter
system sans-serif
```

`Segoe UI Variable` предпочтительнее обычного `Segoe UI`, если доступен в системе.

Никаких собственных font-файлов ради интерфейса Strategy Box не требуется.

---

## 12. Размер базового текста

Текущий размер 13 px стоит сохранить как основной desktop размер.

Он удачно балансирует:

- компактность;
- читаемость;
- плотность данных;
- Windows-like ощущение.

Главный принцип:

> Не увеличивать весь интерфейс до web/mobile масштаба 15–16 px.

Strategy Box — desktop productivity tool.

---

## 13. Типографическая шкала

Рекомендуемая шкала:

| Роль | Размер | Weight | Line height |
|---|---:|---:|---:|
| Micro / technical | 11 px | 500 | 15 px |
| Meta / hint | 12 px | 400–500 | 17 px |
| Body | 13 px | 400 | 19 px |
| Body strong | 13 px | 600 | 19 px |
| Item title | 14 px | 600 | 20 px |
| Case title | 15 px | 600 | 21 px |
| Panel title | 16 px | 600 | 22 px |
| Section/page title | 18–20 px | 600 | 24–28 px |
| Dialog hero title | 22–24 px | 600 | 30–32 px |

`700` стоит использовать редко.

Сейчас UI местами использует слишком много `700`. Для более «благородного» вида лучше чаще использовать `600`, а иногда `500`.

---

## 14. Цвет текста

Пользовательская гипотеза про «не совсем чёрный» правильная.

### Light

Основной:

```text
#20242B
```

Вместо:

```text
#000000
```

или почти-black `#111827` во всех местах.

Secondary:

```text
#5E6673
```

Muted, но всё ещё readable:

```text
#667085
```

Disabled:

```text
#98A2B3
```

Disabled не используется для обычной важной информации.

### Dark

Primary:

```text
#F2F4F7
```

Secondary:

```text
#B7BEC8
```

Muted:

```text
#8D96A3
```

Disabled:

```text
#66707D
```

---

## 15. Mono font

Monospace нужен только там, где реально помогает:

- пути;
- IDs;
- технические коды;
- raw logs;
- stacktrace;
- command fragments.

Рекомендация:

```text
Cascadia Mono
Consolas
monospace
```

Размер:

```text
12–12.5 px
```

Остальной UI остаётся sans-serif.

---

# VI. Светлая тема

## 16. Базовая palette

### Surfaces

| Token | Value | Назначение |
|---|---|---|
| `surface.canvas` | `#F5F7FA` | общий фон |
| `surface.primary` | `#FFFFFF` | панели |
| `surface.secondary` | `#F8FAFC` | мягкая поверхность |
| `surface.tertiary` | `#F1F4F8` | secondary blocks |
| `surface.hover` | `#F3F6FA` | hover |
| `surface.selected` | `#EEF4FF` | selected |
| `surface.elevated` | `#FFFFFF` | dialog/drawer |

### Text

| Token | Value |
|---|---|
| `text.primary` | `#20242B` |
| `text.secondary` | `#5E6673` |
| `text.muted` | `#667085` |
| `text.disabled` | `#98A2B3` |

### Borders

| Token | Value |
|---|---|
| `border.subtle` | `#E4E8EE` |
| `border.default` | `#D4DAE3` |
| `border.strong` | `#B4BDC9` |
| `border.control` | `#8A94A3` |

`border.control` нужен там, где сама граница является основным признаком поля ввода.

---

## 17. Strategy Blue

Целевая базовая шкала:

| Token | Value |
|---|---|
| `accent.050` | `#F2F6FF` |
| `accent.100` | `#E5EDFF` |
| `accent.200` | `#C9D9FF` |
| `accent.300` | `#A6C0FF` |
| `accent.400` | `#79A0F7` |
| `accent.500` | `#316BE5` |
| `accent.600` | `#2B62D5` |
| `accent.700` | `#2456BC` |
| `accent.800` | `#1D469B` |
| `accent.900` | `#173879` |

Primary button:

```text
background  accent.500
foreground  #FFFFFF
hover       accent.600
pressed     accent.700
```

Для маленького accent text на светлом фоне лучше использовать `accent.600` или темнее.

---

# VII. Тёмная тема

## 18. Не использовать абсолютный black

Тёмная тема должна быть:

```text
dark graphite
```

а не:

```text
#000000
```

Чистый black даёт слишком жёсткий контраст и делает небольшие светлые поверхности визуально «вырезанными».

---

## 19. Dark palette

### Surfaces

| Token | Value |
|---|---|
| `surface.canvas` | `#111318` |
| `surface.primary` | `#181B21` |
| `surface.secondary` | `#1E222A` |
| `surface.tertiary` | `#242932` |
| `surface.hover` | `#272D36` |
| `surface.selected` | `#1B2A46` |
| `surface.elevated` | `#242932` |

### Text

| Token | Value |
|---|---|
| `text.primary` | `#F2F4F7` |
| `text.secondary` | `#B7BEC8` |
| `text.muted` | `#8D96A3` |
| `text.disabled` | `#66707D` |

### Borders

| Token | Value |
|---|---|
| `border.subtle` | `#2D333D` |
| `border.default` | `#3A424E` |
| `border.strong` | `#4D5765` |
| `border.control` | `#667281` |

---

## 20. Accent в dark mode

Нельзя просто взять light accent и оставить его без изменения.

Целевой dark accent:

```text
accent.default = #7EA8FF
accent.hover   = #91B5FF
accent.pressed = #6D98F4
accent.soft    = #1B2A46
accent.text    = #B9CFFF
```

На яркой синей primary-button поверхности предпочтителен:

```text
foreground = #0E2148
```

а не обязательно белый.

Это выглядит современно и сохраняет высокий контраст.

---

# VIII. Semantic colors

## 21. Цвет статуса не равен brand color

Semantic colors всегда независимы от пользовательского accent.

### Light

```text
success bg    #EAF7F0
success text  #176B4A

warning bg    #FFF4D6
warning text  #8A5A00

error bg      #FFF1F0
error text    #B42318

info bg       #EEF4FF
info text     #245BBE
```

### Dark

```text
success bg    #163629
success text  #8ED7B5

warning bg    #3A2C12
warning text  #F5CA6B

error bg      #3A1D1D
error text    #FFAAA3

info bg       #1B2A46
info text     #AFC8FF
```

---

## 22. Цвет не должен быть единственным признаком состояния

Например:

```text
✓ Успешно
! Предупреждение
× Ошибка
● Выполняется
```

То есть status =

```text
icon + label + color
```

а не просто зелёный/красный фон.

---

# IX. Отступы и ритм

## 23. Базовая сетка

База:

```text
4 px
```

Рабочая шкала:

```text
2
4
6
8
12
16
20
24
32
40
48
```

Основные значения:

```text
8   — маленький внутренний gap
12  — стандартный compact gap
16  — стандартный padding
24  — section separation
32  — крупный section separation
```

---

## 24. Правило воздуха

Воздух нужен между **смысловыми группами**, а не между каждым элементом.

Хорошо:

```text
label
4
control

12

label
4
control

24

next section
```

Плохо:

```text
каждый элемент
24 px
каждый следующий элемент
24 px
```

Второй подход раздувает desktop UI.

---

# X. Размеры основных областей

## 25. Shell

Рекомендация:

```text
brand header height      52–56 px
top bar                  48–52 px
mode rail width          88–96 px
left contextual panel    240–300 px
right inspector          360–420 px
center minimum useful    ~560 px
```

Текущий rail 96 px можно сохранить.

Он уже соответствует выбранному ранее крупному rail с иконками.

---

## 26. Main window

Целевой комфортный размер:

```text
minimum:
1120 × 700

recommended:
1360 × 820+

large:
1600 × 900+
```

Интерфейс должен gracefully перестраиваться до minimum, а не просто обрезаться.

---

# XI. Радиусы

## 27. Радиусы должны иметь иерархию

Рекомендуемая шкала:

```text
radius.xs   4 px
radius.sm   6 px
radius.md   8 px
radius.lg   12 px
radius.xl   14–16 px
radius.pill 999 px
```

---

## 28. Где какой radius

```text
input / standard button     8 px
small toolbar control       6–8 px
panel card                  10–12 px
composer                    14 px
case bubble                 14 px
notice bubble               10–12 px
dialog                      12–14 px
status chip                 pill
avatar                      circle
```

Сейчас case bubble 18 px немного уходит в «chat toy» эстетику.

Для Strategy Box лучше слегка уменьшить.

---

## 29. Не закруглять всё

Особенно:

- таблицы;
- splitter boundaries;
- mode rail;
- full-height sidebar;
- headers;
- workspace grid.

У структуры приложения должна оставаться архитектурная жёсткость.

---

# XII. Borders, elevation и materials

## 30. Borders

Большинство разделений:

```text
1 px
```

Цвет:

```text
border.subtle
```

Границы нужны:

- между shell areas;
- вокруг input;
- вокруг selected/raised cards;
- внутри таблиц только там, где они помогают читать.

Границы не нужны:

- вокруг каждого текста;
- вокруг каждой карточки;
- вокруг каждого item в sidebar.

---

## 31. Shadows

Default:

```text
none
```

или почти незаметно.

Shadow допустим для:

- popup;
- dropdown;
- dialog;
- floating composer;
- right drawer при overlay mode.

Не следует делать постоянные тени у case bubbles и sidebar cards.

---

## 32. Mica / Acrylic / glass

Для Windows возможны Mica/Acrylic-like материалы, но Strategy Box не должен зависеть от них визуально.

Правильная роль:

- optional shell/chrome material;
- menus/flyouts;
- transient overlays.

Рабочий content layer остаётся матовым.

Так интерфейс:

- лучше читается;
- проще переносится на Android;
- меньше зависит от версии Windows;
- выглядит спокойнее.

---

# XIII. Buttons

## 33. Стандартные размеры

Desktop:

```text
small button       28–30 px
standard button    32–36 px
primary action     36–40 px
large icon action  44–46 px
```

Текущий круглый Run 46 px можно сохранить.

Он является главным действием и должен быть заметнее обычных controls.

---

## 34. Primary action

На одном локальном контексте обычно один явный primary action.

Например:

```text
Запустить
```

или круглая run-action.

Остальные:

```text
secondary / ghost
```

Так глаз сразу видит главное.

---

## 35. Details button

Текущий тёплый brown/tan accent для Details можно заменить на более нейтральную схему.

Рекомендуемый вариант:

```text
details = neutral icon button
```

В активном состоянии:

```text
accent.soft + accent.text
```

Причина: постоянное наличие второго насыщенного цвета рядом с primary action создаёт конкуренцию.

Тёплый orange лучше оставить для warning / special attention.

---

# XIV. Inputs и forms

## 36. Высота

```text
text input     32–34 px
combo          32–34 px
checkbox row   28–32 px
path input     34–36 px
```

---

## 37. Field style

Light:

```text
surface       #FFFFFF
border        border.control/default
text          text.primary
placeholder   text.muted
```

Focus:

```text
border   accent.500
ring     2 px accent with low-alpha outer halo
```

Dark:

```text
surface.secondary
```

с отдельной видимой границей.

---

## 38. Advanced parameters

Для Strategy Box особенно важно progressive disclosure.

В форме сценария:

```text
Основные параметры
...
Дополнительно ▾
```

Не стоит одновременно показывать весь technical configuration.

---

# XV. Scenario chat

## 39. Что должно оставаться

Сценарная лента — один из наиболее сильных элементов концепции.

Нужно сохранять:

- incoming слева;
- own runs справа;
- cases как крупные сообщения;
- system notices как меньшие сообщения;
- avatars;
- status;
- artifacts внутри run;
- smooth scroll;
- new messages button;
- отсутствие auto-jump, если пользователь читает историю.

---

## 40. Bubble geometry

Case:

```text
min width    300–320 px
max width    700–760 px
padding      14 × 12 px
radius       14 px
```

Notice:

```text
min width    220 px
max width    560–620 px
padding      12 × 9 px
radius       10–12 px
```

Текущая адаптивная логика 64–84% available width в зависимости от окна в целом разумна.

---

## 41. Bubble colors

Основная поверхность case должна оставаться почти нейтральной.

Outgoing:

```text
очень слабый accent tint
```

Incoming:

```text
surface.primary
```

Статус не должен полностью перекрашивать bubble.

Лучше:

```text
status chip
+ left/top micro-indicator
+ небольшой border tint
```

---

## 42. Running state

Именно здесь уместен фирменный gradient.

Вместо заливки всей карточки:

```text
1–2 px animated top edge
```

или:

```text
small progress glow
```

Gradient:

```text
Strategy Blue → blue-violet → cyan-blue
```

Амплитуда должна быть небольшой.

Скорость:

```text
~1.8–2.4 s per cycle
```

Эта анимация сообщает «операция живёт», а не просто украшает экран.

---

## 43. Completed state

После завершения gradient исчезает.

Case становится статичным.

Таким образом motion также несёт семантическое значение.

---

# XVI. Status chips

## 44. Размер

```text
font     11 px / 600
height   ~22–24 px
padding  4 × 8 px
```

Pill допустим, потому что chip — компактная семантическая метка.

---

## 45. Не делать chips основным декоративным элементом

Если каждый второй label превращается в pill, интерфейс начинает выглядеть как issue tracker.

Chips только для:

- state;
- filter;
- compact category;
- short metadata where useful.

---

# XVII. Workspace explorer

## 46. Визуальный характер

Explorer должен быть ближе к Windows Explorer / IDE, чем к dashboard.

Здесь нужна меньшая декоративность:

- белая/тёмная таблица;
- плотные строки;
- ясные icons;
- subtle hover;
- selection tint;
- минимальное количество rounded cards.

---

## 47. Row metrics

Default:

```text
row height     34–36 px
header         32–34 px
icon           16–18 px
horizontal pad 10–12 px
```

Compact mode:

```text
row height     30–32 px
```

---

## 48. Selection

Selection:

```text
accent.soft
```

Text:

```text
accent.700
```

в light;

в dark:

```text
accent.text
```

Focused selection получает дополнительный focus indicator.

---

# XVIII. Mode rail

## 49. Геометрия

Текущий rail:

```text
96 px
```

логичен.

Button:

```text
96 × 80–84 px
```

Icon:

```text
30–34 px
```

Caption:

```text
11 px / 600
```

---

## 50. Active tile

Ранее выбранное решение следует сохранить:

- полный прямоугольный tile;
- без rounded corners;
- без отдельной border-card;
- мягкая заливка;
- активная иконка + label.

Light:

```text
background   accent.100-ish
foreground   accent.700
```

Dark:

```text
background   accent.soft
foreground   accent.text
```

---

# XIX. Right inspector

## 51. Роль

Inspector — secondary context, поэтому он должен визуально уступать центральной сцене.

Рекомендация:

```text
width    360–420 px
surface  primary
border   1 px subtle
```

---

## 52. Tabs

Tabs лучше сделать компактными:

```text
height        30–32 px
radius        8 px
font          12 px / 500
```

Активный tab:

```text
accent.soft
```

Вместо тяжёлой outlined-button формы можно использовать segmented-like navigation.

---

# XX. Dialogs

## 53. Размеры и структура

Settings:

```text
760 × 560
```

сейчас выглядит разумно.

Но содержимое лучше организовать не обычными tab pages с длинным вертикальным списком, а:

```text
left settings navigation
+
right settings page
```

или компактными categories.

При небольшом числе настроек текущие tabs тоже допустимы.

---

# XXI. Appearance settings

## 54. Новая секция «Внешний вид»

В пользовательских настройках должна появиться отдельная surface:

```text
Внешний вид
```

---

## 55. Theme

Контрол:

```text
Тема
○ Как в системе
○ Светлая
○ Тёмная
```

Default:

```text
Как в системе
```

Windows guidance также предполагает системную тему как естественный baseline.

---

## 56. Accent

```text
Акцент
○ Strategy Blue
○ Цвет Windows
○ Свой цвет
```

Default:

```text
Strategy Blue
```

`Цвет Windows` особенно хорошо вписывается в desktop-продукт.

---

## 57. Custom accent

Пользователь выбирает один базовый цвет.

Он **не задаёт вручную**:

- hover;
- pressed;
- focus;
- dark variant;
- selection background.

Эти значения вычисляет theme engine.

Это принципиально важно.

Иначе пользователь легко создаст нечитаемый интерфейс.

---

## 58. Что разрешено персонализировать

Целевой набор:

```text
Theme
Accent source
Custom accent
Density
Motion preference
```

Опционально:

```text
Neutral temperature:
- Cool
- Neutral
```

Но это уже second-order feature.

---

## 59. Что не стоит отдавать пользователю

Не нужно давать отдельные color pickers для:

- canvas;
- text;
- border;
- warning;
- error;
- success;
- sidebar;
- bubble.

Такая свобода ломает:

- контраст;
- дизайн;
- статусную семантику;
- поддержку.

Персонализация должна быть **ограниченной, но выразительной**.

---

# XXII. Accent generation

## 60. Семантическая генерация

Из custom accent строится ramp.

Лучше использовать perceptual color space:

```text
OKLCH
```

а не простое RGB darken/lighten.

Для каждой темы вычисляются:

```text
accent.soft
accent.default
accent.hover
accent.pressed
accent.text
accent.focus
```

---

## 61. Автоматическая проверка

Theme engine обязан проверять минимум:

```text
normal text            >= 4.5:1
large text             >= 3:1
UI required indicator  >= 3:1
focus indicator        >= 3:1
```

Если пользовательский цвет не проходит:

- UI не отклоняет выбор;
- theme engine выбирает более тёмную/светлую производную для конкретной semantic role.

Таким образом брендовый input и accessible output разделены.

---

# XXIII. Contrast и accessibility

## 62. Текст

Для обычного небольшого текста:

```text
4.5:1 minimum
```

Для крупных текстов допустим ниже, но Strategy Box почти весь состоит из small desktop text, поэтому 4.5:1 — основной practical target.

---

## 63. UI components

Для значимых visual cues:

```text
3:1 minimum
```

Это касается:

- border input, если он определяет сам control;
- focus ring;
- icon без текста;
- selection indicator;
- graphical status cue.

---

## 64. Secondary text

`text.secondary` должен оставаться readable.

Очень светлый gray подходит только:

- disabled;
- декоративным подписям;
- второстепенной информации, которую можно не читать.

Meta-information в рабочих интерфейсах часто оказывается важной, поэтому делать её `#999` на белом фоне не следует.

---

## 65. High contrast

Если Windows включил Contrast Theme:

> пользовательский accent Strategy Box должен уступить системной accessibility palette.

Нужно поддерживать отдельный system/high-contrast mapping.

Это особенно важно, потому что полностью hardcoded QSS может подавить системную тему.

---

# XXIV. Motion

## 66. Общая логика

Motion Strategy Box:

```text
quiet but alive
```

Не:

```text
static
```

и не:

```text
cinematic
```

---

## 67. Durations

Целевая шкала хорошо совпадает с Fluent:

```text
83 ms   micro fade / immediate feedback
120 ms  hover/short transition
167 ms  standard fast transition
200 ms  drawer/panel
250 ms  major transition
```

Текущие 160–180 ms в chat scroll удачны.

---

## 68. Правила

Hover:

```text
80–120 ms
```

Selection:

```text
120–167 ms
```

Drawer:

```text
180–220 ms
```

Dialog entrance:

```text
180–250 ms
```

Scroll-to-new:

```text
160–180 ms
```

---

## 69. Reduced motion

Appearance/runtime должен уважать system reduced-motion preference.

При reduced motion:

- drawer меняется практически мгновенно или коротким fade;
- gradient-running заменяется static indicator;
- scroll animation сокращается;
- decorative transitions отключаются.

---

# XXV. Progress

## 70. Long operations

Strategy Box часто работает с длинными операциями.

Поэтому progress должен быть не modal spinner, а persistent activity state.

Правильные варианты:

- stage text;
- progress line;
- moving gradient edge;
- status chip;
- background process indicator.

---

## 71. Spinner

Spinner нужен только там, где:

- операция короткая;
- процент неизвестен;
- контекст не требует полноценного case.

Для больших аналитических runs лучше case-progress.

---

# XXVI. Icons

## 72. Стиль

Icons должны быть:

- monochrome;
- outline/regular;
- одинаковой optical weight;
- без 3D;
- без разноцветных glyphs.

Файл-иконки могут иметь немного semantic color, если это реально помогает быстро различать Excel/PDF/archive.

---

## 73. Размеры

```text
toolbar        16 px
standard       18–20 px
navigation     30–34 px
empty-state    32–48 px
```

---

## 74. Active icon

Не нужно рисовать отдельный яркий визуальный объект.

Достаточно:

```text
foreground = accent
```

и active tile background.

---

# XXVII. Density

## 75. Два режима

Для desktop Strategy Box логично иметь:

```text
Compact
Comfortable
```

Default:

```text
Comfortable
```

Но Comfortable здесь всё ещё desktop-density.

---

## 76. Что меняется

### Comfortable

```text
control       34–36
table row      36
section gap    24
panel padding  16
```

### Compact

```text
control       30–32
table row      30–32
section gap    16–20
panel padding  12
```

Typography в Compact почти не уменьшается.

Меняются прежде всего:

- padding;
- row height;
- gaps.

---

# XXVIII. Responsive desktop behavior

## 77. Широкий экран

При ширине > 1450 px:

- left context panel открыта;
- inspector может быть открыт;
- center остаётся широким;
- bubbles не растягиваются бесконечно.

---

## 78. Средний экран

~1150–1450 px:

- inspector push-layout;
- left panel normal;
- center adapts;
- meta может сокращаться.

---

## 79. Узкий desktop

< 1150 px:

- contextual panel можно сворачивать;
- inspector переходит в overlay;
- rail остаётся;
- главный scenario surface сохраняется.

Это лучше, чем сжимать center до нечитаемого состояния.

---

# XXIX. Theme architecture в `stratbox-windows`

## 80. Предлагаемая структура

```text
presentation/
  common/
    appearance/
      models.py
      tokens.py
      semantics.py

  qt_desktop/
    theme/
      primitives.py
      strategy_blue.py
      light.py
      dark.py
      contrast.py
      accent.py
      renderer.py
      qss_template.qss
```

Названия примерные; важна граница ответственности.

---

## 81. Platform-neutral preference model

Например:

```text
AppearancePreferences
  theme_mode
  accent_source
  custom_accent
  density
  reduce_motion
```

Эта модель не должна зависеть от Qt.

Именно её потом сможет использовать `stratbox-android`.

---

## 82. Qt renderer

Qt-specific слой получает:

```text
ThemeTokens
```

и формирует:

```text
QPalette
+
QSS
+
runtime component parameters
```

После изменения темы:

```text
apply → repolish
```

без обязательного перезапуска приложения.

---

## 83. Не хранить размеры в нескольких местах

Сейчас часть значений находится:

- в QSS;
- в Python widgets;
- в fixedSize;
- в margins.

Целевой theme/density layer должен владеть хотя бы semantic metrics:

```text
rail_width
top_bar_height
control_height
panel_padding
chat_gap
bubble_radius
```

---

# XXX. Связь с будущим Android

## 84. Что должно быть общим

Общая часть:

```text
semantic colors
typography roles
spacing roles
radius roles
status semantics
appearance preferences
motion preference
component intent
```

---

## 85. Что нельзя копировать

Android не должен копировать:

```text
QSS
96 px navigation rail
Windows titlebar patterns
desktop hover
desktop pointer-specific states
```

То есть переносится **design language**, а не desktop pixels.

---

## 86. Единый бренд

Windows и Android должны иметь одинаковые:

- Strategy Blue;
- semantic status colors;
- типографические роли;
- logo handling;
- visual hierarchy;
- run/case semantics.

Но размеры адаптируются к platform conventions.

---

# XXXI. Что изменить в текущем UI

## 87. Сохранить

Сохранить стоит:

- 13 px desktop base;
- Segoe UI / Inter direction;
- трёхзонную shell-модель;
- rail;
- messenger-like scenario feed;
- динамическую ширину bubbles;
- smooth scroll;
- new messages button;
- inspector;
- muted canvas;
- status chips;
- scenario composer;
- current information density.

---

## 88. Изменить

### 88.1. Primary text

```text
#111827
→
#20242B
```

Сдвиг небольшой, но интерфейс становится визуально мягче.

### 88.2. Current teal accent

```text
#3D777B / #0F6F78
```

лучше заменить brand-derived Strategy Blue.

Teal был хорошим прототипным calm accent, но приложенный logo задаёт более сильную identity.

### 88.3. Details tan

Убрать как постоянный второй action color.

### 88.4. Bubble radius

```text
18
→
14
```

### 88.5. Heavy bold

Часть `700`:

```text
→ 600 / 500
```

### 88.6. Hardcoded palette

Перевести на semantic tokens.

### 88.7. Settings

Добавить `Внешний вид`.

### 88.8. Dark theme

Сделать полноценной, а не инверсией light.

---

# XXXII. Что не нужно менять

## 89. Не увеличивать всё

Не нужно превращать:

```text
13 px → 15/16 px
32 px controls → 44 px
```

в desktop.

Это снизит плотность и заставит пользователя больше скроллить.

---

## 90. Не делать центр белой карточкой

Основная scenario scene лучше живёт на canvas.

Bubble и composer уже создают достаточный слой.

---

## 91. Не делать sidebars стеклянными

Это добавит визуальную сложность без практической пользы.

---

## 92. Не раскрашивать каждую сущность

Scenario, user, status, artifact, source, operation не должны одновременно иметь собственные яркие цвета.

Нужны разные icon/label semantics при общей neutral palette.

---

# XXXIII. Appearance panel — целевая форма

## 93. Экран

```text
Внешний вид

Тема
[ Как в системе ▼ ]

Акцент
[ Strategy Blue ] [ Windows ] [ Свой ]

Свой цвет
[ ■ #316BE5 ]

Плотность интерфейса
( ) Удобная
( ) Компактная

Движение
[x] Следовать настройкам системы

Предпросмотр
┌───────────────────────────────┐
│ Strategy Box                  │
│ ● Выполняется                 │
│         [ Запустить ]         │
└───────────────────────────────┘
```

---

## 94. Live preview

Изменение theme/accent должно применяться сразу.

Кнопка `Сохранить` для appearance предпочтительно не нужна.

Если выбор оказался неудачным, пользователь просто выбирает другой.

---

## 95. Reset

Нужна одна команда:

```text
Восстановить оформление по умолчанию
```

Она сбрасывает:

- theme → system;
- accent → Strategy Blue;
- density → comfortable;
- motion → system.

---

# XXXIV. Acceptance criteria

## 96. Светлая тема

Готова, если:

- нет pure black в normal body text;
- primary text легко читается;
- accent встречается редко;
- primary action виден сразу;
- фон не ослепляет;
- sidebar и inspector отделены без тяжёлых теней;
- таблицы выглядят спокойно;
- bubbles читаются как рабочие кейсы, а не social messenger.

---

## 97. Dark theme

Готова, если:

- нет чистого `#000000` canvas;
- white не используется как единственный foreground tone повсеместно;
- surfaces различимы без тяжёлых borders;
- accent адаптирован;
- status colors сохраняют смысл;
- logo не светится слишком агрессивно рядом с UI;
- таблицы и logs читаются длительное время.

---

## 98. Custom accent

Готов, если:

- пользователь выбирает один цвет;
- light/dark variants генерируются автоматически;
- text contrast сохраняется;
- focus заметен;
- status colors не перекрашиваются;
- logo не перекрашивается;
- theme переключается без restart.

---

## 99. Motion

Готов, если:

- основные transition ≤ ~250 ms;
- частые transition ≤ ~167 ms;
- long-running gradient не отвлекает;
- reduced motion реально отключает decorative movement;
- scrolling остаётся плавным.

---

# XXXV. Приоритет реализации

## 100. P0 — дизайн-токены

Сначала:

1. primitive colors;
2. semantic colors;
3. typography;
4. spacing;
5. radius;
6. component states.

Без этого dark/custom theme превратятся в дублированный QSS.

---

## 101. P0 — light theme cleanup

Сделать целевую светлую тему первой.

Это позволит проверить дизайн-систему на текущем UI без одновременной сложности dark mode.

---

## 102. P1 — dark theme

После stabilizing tokens.

---

## 103. P1 — Appearance preferences

Добавить:

- system/light/dark;
- Strategy/Windows/custom accent;
- density;
- motion.

---

## 104. P1 — accent engine

Автоматическая генерация accessible accent variants.

---

## 105. P2 — contrast theme

Интеграция с Windows accessibility mode.

---

## 106. P2 — micro-motion polish

После того как layout и color system стабилизированы.

---

# XXXVI. Целевая система в одной таблице

| Область | Целевое решение |
|---|---|
| Общий стиль | Calm Operational Premium |
| Base font | Segoe UI Variable / Segoe UI / Inter |
| Base size | 13 px |
| Primary text light | `#20242B` |
| Primary text dark | `#F2F4F7` |
| Canvas light | `#F5F7FA` |
| Canvas dark | `#111318` |
| Surface light | `#FFFFFF` |
| Surface dark | `#181B21` |
| Default accent | Strategy Blue |
| Accent light | `#316BE5` |
| Accent dark | `#7EA8FF` |
| Grid | 4 px |
| Standard gap | 8 / 12 / 16 px |
| Section gap | 24 px |
| Control radius | 8 px |
| Card radius | 10–12 px |
| Case radius | 14 px |
| Main control height | 32–36 px |
| Primary Run | 44–46 px |
| Rail | 88–96 px |
| Icon navigation | 30–34 px |
| Standard motion | 167 ms |
| Drawer motion | ~200 ms |
| Theme | System / Light / Dark |
| Accent | Strategy / Windows / Custom |
| Density | Comfortable / Compact |
| Status | Semantic colors, independent from accent |

---

# XXXVII. Финальный тезис

Целевой Strategy Box не должен доказывать современность количеством эффектов.

Современность здесь создают:

- точные пропорции;
- спокойная палитра;
- качественная типографика;
- правильные отступы;
- понятная иерархия;
- быстрые микроанимации;
- живые execution states;
- аккуратный бренд;
- адаптация к пользователю;
- отсутствие визуального мусора.

Логотип может быть ярким.

Рабочая поверхность — спокойной.

Primary action — заметным.

Состояние выполнения — живым.

Всё остальное должно помогать пользователю видеть работу, а не дизайн.

---

# XXXVIII. Источники и стандарты

## Project sources

**P1.** `stratbox-windows_current_state_full_research_2026-10-06.md` — текущая архитектура surface, scenario-chat, settings, explorer, inspector, portability.

**P2.** Актуальный `ForestTiger-GH/stratbox-windows@main` — `app.qss`, `strategy_palette.py`, scenario-chat widgets, mode rail, settings dialog.

**P3.** `AppDock — Базовое описание.docx` — managed application/product surface context.

**P4.** Приложенные варианты логотипа Strategy Box.

**P5.** Предыдущие решения по Strategy Box UI — calm operational premium, scenario-first chat, крупный monochrome mode rail, smooth messenger scrolling, минимальный motion с полезными микроинтеракциями.

## External guidance

**W1.** Microsoft Fluent 2 — Design tokens.  
Ключевая идея: global tokens + semantic/alias tokens; theming через token layer.

**W2.** Microsoft Fluent 2 — Layout.  
Ключевая идея: 4 px spacing system и whitespace как инструмент иерархии.

**W3.** Microsoft Fluent 2 — Typography.  
Ключевая идея: ограниченная type scale, sentence case, contrast-first typography.

**W4.** Microsoft Learn — Color in Windows.  
Ключевая идея: light/dark, accent используется sparingly, color показывает interactivity/state.

**W5.** Microsoft Learn — Theming in Windows apps.  
Ключевая идея: system/light/dark theme, system or brand accent, accent ramp.

**W6.** Microsoft Learn — Guidelines for app settings.  
Ключевая идея: theme — пользовательская настройка, предпочтителен system setting, изменения должны отражаться сразу.

**W7.** Microsoft Learn — Timing and easing / Motion in Windows.  
Ключевая идея: 83/167/250 ms как основные Fluent duration classes; motion быстрый и функциональный.

**W8.** W3C WCAG 2.2 — Contrast Minimum / Non-text Contrast.  
Ключевая идея: 4.5:1 normal text; 3:1 large text и required UI/graphic cues.

**W9.** Apple Human Interface Guidelines — Dark Mode / Color.  
Ключевая идея: dark theme не является простой инверсией; semantic colors, отдельные light/dark variants, ограниченное использование цвета.

---

**Конец исследования.**
