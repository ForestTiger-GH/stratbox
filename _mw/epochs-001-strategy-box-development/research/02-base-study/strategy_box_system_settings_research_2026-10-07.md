# Strategy Box — системные настройки, пользовательские предпочтения и управление плагинами

**Research branch:** вторая ветка исследований Strategy Box / `02-base-study`  
**Дата:** 2026-10-07  
**Объекты:** `stratbox`, `stratbox-windows`, граница с AppDock  
**Статус:** Research Result — целевая модель настроек; код и репозитории не изменялись  
**Принцип совместимости:** обратная совместимость с текущей моделью настроек не требуется; целевая схема может заменить существующую целиком.

---

# 0. Краткий вывод

Настройки Strategy Box стоит проектировать как **маленький, строго отфильтрованный слой устойчивых пользовательских предпочтений**, а не как место, куда попадает всё, что приложение умеет запомнить или показать.

Текущий `stratbox-windows` уже хранит много состояния: размер окна, выбранный режим, состояние инспектора, последний сценарий, фильтр чата, выбранного участника, значения форм сценариев и т. п. Большая часть этого **не является настройками**. Это автоматически сохраняемое состояние интерфейса, recents или drafts. Пользователь не должен вручную выбирать «какая вкладка инспектора открывается при старте» или «какой режим слева считать стартовым»: приложение должно просто восстановить последнее разумное состояние.

Целевая пользовательская поверхность настроек получается компактной:

```text
Настройки Strategy Box
├── Внешний вид
│   ├── Тема: Системная / Светлая / Тёмная
│   └── Акцент: Strategy Box / Windows / Свой цвет
│
├── Артефакты и отчёты
│   ├── Профиль оформления по умолчанию
│   └── Автор файлов: "Strategy Box" по умолчанию
│
├── Плагины
│   ├── установленные / доступные приложению плагины
│   ├── состояние и совместимость
│   ├── включение optional-плагинов, если политика это разрешает
│   ├── стандартизированная конфигурация
│   └── диагностика / переход к управлению установкой в AppDock
│
└── Уведомления                    ← только после появления реальных OS/background notifications
    ├── завершение своих запусков
    ├── ошибки своих запусков
    ├── фоновые события
    └── общие проблемы узла / поручения
```

При этом раздел **«Уведомления» не должен появляться раньше самой функции уведомлений**. Настройки должны следовать за работающими возможностями продукта, а не рекламировать будущие каркасы.

Самое важное уточнение по плагинам:

> **Плагины не меняют интерфейс `stratbox-windows`.**

Внешний вид shell, typography, layout, навигация, QSS/tokens, иконки, density и motion принадлежат самому приложению. Плагин не получает API для внедрения QSS, произвольных Qt-widget, своих вкладок, собственного sidebar, замены шрифтов shell или перекрашивания интерфейса.

Плагины относятся к бизнес-возможностям Strategy Box прямо или косвенно. Они могут, например, добавлять разрешённые business capabilities, источники, операции, форматы, шаблоны или профили формирования отчётов. Если плагин предоставляет профиль оформления **артефактов**, этот профиль может появиться в настройке «Артефакты и отчёты». Это не является кастомизацией интерфейса приложения.

Для Office-артефактов идея с авторством технически нормальна и переносима: XLSX, DOCX и PPTX имеют стандартизированные core properties `creator/author`. Для Strategy Box разумный дефолт — **`Strategy Box`**, а фактический пользователь/agent, создавший результат, отдельно сохраняется в provenance. Эти две сущности нельзя смешивать.

---

# 1. Задача исследования

Нужно определить:

1. какие настройки действительно нужны пользователю Strategy Box;
2. что уже существует в `stratbox-windows` и является полезным;
3. какие текущие опции выглядят как временный или мусорный UI;
4. что должно сохраняться автоматически и вообще не показываться в Settings;
5. какие параметры принадлежат AppDock или managed policy;
6. какие параметры относятся к конкретному сценарию, а не ко всему приложению;
7. как устроить настройку артефактов и их metadata;
8. как управлять плагинами из интерфейса без превращения plugin API в UI-extension API;
9. как сделать модель переносимой на будущий `stratbox-android`;
10. как сделать settings schema маленькой, versioned и пригодной для managed environment.

Главная цель — не собрать максимальное число потенциальных переключателей, а, наоборот, **доказать право каждого параметра находиться в Settings**.

---

# 2. Фактическое текущее состояние

## 2.1. Текущий Settings dialog

На актуальном `main` `stratbox-windows` Settings dialog содержит три вкладки:

```text
Пользовательские
Рабочие
Системные
```

### Пользовательские

UI позволяет выбирать:

- открывать ли правую панель при запуске;
- стартовый режим слева;
- стартовую вкладку правой панели.

### Рабочие

Фактически это почти полностью информационная страница:

- workspace schema;
- workspace root;
- Data root selector;
- status;
- открыть workspace;
- скопировать путь.

### Системные

Также в основном информационная поверхность:

- run mode;
- launch origin;
- node;
- session;
- user;
- host;
- source commit;
- кнопка копирования диагностики.

То есть две из трёх вкладок сегодня по сути **не настройки**, а status/diagnostics surfaces.

## 2.2. Что реально хранится в `AppUserConfig`

Текущий конфиг включает:

```text
last_workspace_schema
last_scenario_id
scenario_form_values

window.width
window.height

shell.selected_mode
shell.left_panel_width
shell.right_inspector_open
shell.right_inspector_width
shell.right_inspector_tab

chat.filter_mode
chat.selected_author_id
```

Это хороший пример того, почему нельзя считать любой persisted field «настройкой».

Здесь смешаны минимум четыре разных класса данных:

```text
1. устойчивые preference
2. layout state
3. recents/navigation state
4. scenario drafts
```

Целевой redesign должен развести их физически и семантически.

---

# 3. Базовый критерий: что вообще является настройкой

Полезно ввести простой тест.

Параметр достоин раздела Settings, если одновременно выполняются условия:

1. **Он отражает устойчивое предпочтение пользователя**, а не текущий контекст.
2. **Он влияет на поведение приложения в нескольких сессиях или сценариях.**
3. **Пользователь способен осмысленно выбрать значение заранее.**
4. **Параметр меняется редко.**
5. **Его нельзя надёжно вывести автоматически из последнего состояния или системной среды.**
6. **Он не является обычной командой рабочего процесса.**
7. **Он не относится только к одному конкретному run/scenario.**
8. **Он не должен быть policy, которую пользователь не вправе менять.**

Если хотя бы несколько пунктов не выполняются, настройке почти наверняка место в другом слое.

Эта модель совпадает с современной Windows guidance: settings предназначены для сравнительно устойчивых предпочтений, должны иметь разумные defaults, быть минимальными и по возможности применяться сразу. Команды обычного рабочего процесса в Settings помещать не следует.

---

# 4. Пять разных сущностей, которые нельзя смешивать

## 4.1. `UserSettings`

То, что пользователь сознательно выбирает в Settings.

Примеры:

- light/dark/system;
- accent source;
- default artifact formatting profile;
- file author label;
- notification preference.

## 4.2. `SurfaceState`

То, что приложение автоматически запоминает и восстанавливает.

Примеры:

- window geometry;
- ширина панелей;
- текущий mode;
- открыта ли правая панель;
- выбранная вкладка inspector;
- текущий filter;
- scroll position, если это реально полезно.

Пользователь не должен настраивать это в Settings.

## 4.3. `RecentState / DraftState`

Контекст продолжения работы:

- last scenario;
- last artifact;
- recent workspace location;
- сохранённые значения формы сценария;
- незапущенный draft параметров.

Это может храниться долго, но всё равно не является settings.

## 4.4. `ManagedPolicy`

Решения среды/AppDock/организации:

- обязательные plugin bindings;
- разрешённые plugins;
- Data binding;
- ограничения storage/network;
- forced artifact profile;
- запрет отдельных capabilities;
- retention/security policy;
- update/install policy.

Пользователь может видеть такие значения и причину блокировки, но не обязан иметь возможность менять их.

## 4.5. `RunParameters`

Параметры конкретной операции/сценария:

- период;
- набор данных;
- refresh;
- overwrite;
- выходной формат;
- scope;
- целевой каталог, если он вообще является частью операции;
- optimization mode;
- конкретный template для одного запуска.

Это живёт в scenario form/preset, а не в глобальных настройках.

---

# 5. Что из текущих «настроек» следует удалить из Settings

## 5.1. «Открывать правую панель при запуске»

Удалить как явную настройку.

Правильное поведение:

```text
пользователь закрыл inspector
→ приложение запомнило
→ следующий запуск восстановил
```

Нет смысла иметь отдельный preference, который может противоречить фактическому последнему состоянию.

## 5.2. «Стартовый режим слева»

Удалить.

Приложение должно восстановить последнюю рабочую поверхность либо использовать продуктовый default при первом запуске.

Если когда-нибудь появится режим «всегда открывать Home», это должно быть доказано реальным спросом, а не добавлено заранее.

## 5.3. «Стартовая вкладка правой панели»

Удалить.

Это тот же layout/navigation state.

## 5.4. Размер окна

Оставить persistence, убрать из semantic settings.

## 5.5. Ширина панелей

Оставить persistence, убрать из semantic settings.

## 5.6. Chat filter

Запоминать автоматически. Не делать настройкой.

## 5.7. Selected participant

Это navigation state.

## 5.8. Last scenario

Это recents/context restoration.

## 5.9. Scenario form values

Это scenario draft/defaults per scenario.

Их стоит хранить отдельно от user settings, потому что они могут содержать чувствительные параметры и имеют другой lifecycle.

## 5.10. `last_workspace_schema`

В текущем продукте schema одна. Значение выглядит как исторический архитектурный задел и не должно появляться в UI.

Если в будущем реально появятся разные workspace models, выбор должен происходить в рабочем контексте, а не превращаться автоматически в глобальную настройку.

---

# 6. Что убрать из Settings целиком

## 6.1. Текущую вкладку «Рабочие»

Её содержимое относится к workspace information/actions.

Лучшее размещение:

```text
Проводник / Workspace info
или
Узел / Data
```

Там уместны:

- путь;
- состояние;
- доступность;
- открыть;
- скопировать путь;
- возможно сменить Data binding через AppDock.

Это не preferences.

## 6.2. Текущую вкладку «Системные»

Информация о run mode/node/session/host/version относится к:

```text
Узел
Диагностика
О приложении
```

Settings не должен превращаться в inspector runtime state.

## 6.3. Кнопку «Скопировать диагностику»

Оставить в отдельной Diagnostics surface.

---

# 7. Целевая информационная архитектура Settings

На первом полноценном релизе Settings стоит держать **максимум три постоянных раздела**:

```text
Внешний вид
Артефакты и отчёты
Плагины
```

Четвёртый раздел появляется по capability:

```text
Уведомления
```

когда реально существует notification backend.

Не нужны постоянные разделы:

```text
Общие
Поведение
Система
Рабочая среда
Дополнительно
Сеть
Обновления
Хранилище
Аккаунт
Безопасность
AI
Фоновые процессы
```

пока за ними нет нескольких устойчивых пользовательских предпочтений.

Пустая taxonomy ради «солидности» интерфейса только создаёт шум.

---

# 8. Раздел «Внешний вид»

После уточнения требований этот раздел стоит сделать ещё проще, чем предлагалось в отдельном visual research.

## 8.1. Тема

```text
Тема
(•) Как в системе
( ) Светлая
( ) Тёмная
```

Default:

```text
Как в системе
```

Изменение применяется сразу.

## 8.2. Акцент

```text
Акцент
(•) Strategy Box
( ) Windows
( ) Свой цвет
```

При custom выбирается один исходный цвет.

Theme engine самостоятельно строит доступные hover/pressed/focus/soft/text variants и сохраняет контраст.

## 8.3. Чего здесь не должно быть

Не нужны отдельные пользовательские настройки:

- фон каждой панели;
- цвет bubbles;
- цвет success/error;
- border color;
- radius;
- spacing;
- base font size;
- font family shell;
- icon pack;
- layout style;
- animation speed;
- sidebar width;
- bubble shape;
- arbitrary CSS/QSS.

Интерфейс Strategy Box — цельная продуктовая система, а не skinning framework.

## 8.4. Density

На первом целевом варианте я бы **не выводил density в Settings**.

Причины:

- интерфейс уже является desktop productivity UI;
- две density создают удвоенную площадь визуального тестирования;
- пользовательская ценность пока не доказана;
- размеры и плотность сильнее влияют на целостность layout, чем цвет.

Если после реального использования появится устойчивый спрос, `Comfortable / Compact` можно добавить позже как четвёртую настройку Appearance.

## 8.5. Motion

`reduce motion` лучше в первую очередь наследовать из системной accessibility setting.

Отдельный toggle имеет смысл только если Qt/Windows bridge надёжно поддерживает системный сигнал недостаточно хорошо или пользователи явно просят отдельное override.

---

# 9. Жёсткий запрет на UI-плагины

Целевая архитектура должна иметь явный invariant:

```text
plugin capability
    ≠
UI skin / UI extension
```

Плагин не имеет права:

- заменять theme приложения;
- подмешивать QSS/CSS;
- менять shell font;
- менять mode rail;
- переопределять app icons;
- добавлять произвольные Qt widgets;
- создавать собственный root navigation item;
- заменять Settings UI;
- передавать executable presentation code в frontend;
- регистрировать arbitrary menu actions вне стандартизированного action contract;
- менять composition главного окна.

Это особенно важно для будущего Android. Если business plugin способен внедрять Qt presentation, он автоматически становится Windows-only и разрушает переносимость product semantics.

---

# 10. Что плагины всё-таки могут дать пользовательской поверхности

Плагины относятся к бизнес-логике или supporting business infrastructure.

Их contribution может быть **декларативно представлен** приложением.

Например:

```text
PluginDescriptor
├── операции / scenarios / sources
├── business capabilities
├── format handlers
├── artifact/report profiles
├── templates
├── health/readiness
└── settings schema
```

При этом сам `stratbox-windows` решает, как это визуализировать.

Плагин передаёт данные и contracts, приложение рендерит стандартные элементы.

---

# 11. Раздел «Плагины»

Это должна быть не developer console, а понятный control surface.

## 11.1. Верхний список

Каждый plugin card показывает минимум:

```text
Название
Версия
Статус
Краткое назначение
```

Статусы:

```text
Готов
Отключён
Требует настройки
Требует авторизации
Несовместим
Недоступен
Ошибка
Требуется перезапуск
```

Технические package IDs можно показывать в Details, а не в основной строке.

## 11.2. Enable / disable

Toggle показывается только если plugin:

- optional;
- policy разрешает user activation;
- его отключение безопасно для текущего runtime profile.

Если plugin required:

```text
Включён · управляется средой
```

с пояснением, почему control disabled.

## 11.3. Installation lifecycle

`stratbox-windows` не должен самостоятельно выполнять:

```text
pip install
pip uninstall
pip upgrade
```

Установка/обновление/удаление distributions относится к AppDock/deployment layer.

В Settings допустимы действия:

```text
Управлять установкой
Проверить обновление
Открыть в AppDock
```

если соответствующая AppDock capability существует.

То есть Strategy Box остаётся control surface, а package manager не дублируется.

## 11.4. Plugin settings

Plugin может объявить versioned declarative schema:

```text
string
integer
boolean
choice
enum
path/reference
secret_ref
duration
```

Но не произвольный widget factory.

Приложение строит стандартную форму само.

## 11.5. Scope каждой plugin setting

Plugin descriptor обязан указать scope:

```text
USER
WORKSPACE
NODE
MANAGED_ONLY
```

Это предотвращает ситуацию, когда user preference случайно используется как общая node policy.

## 11.6. Sensitivity

Каждое поле:

```text
PUBLIC
PRIVATE
SECRET_REFERENCE
```

Raw secret value не хранится в `stratbox-windows` settings вообще.

## 11.7. Validation

Settings UI должен уметь показать:

- invalid value;
- missing required config;
- policy conflict;
- auth required;
- restart required.

Изменение settings, которое нельзя применить hot, не должно притворяться применённым.

---

# 12. Plugin management и будущий operation/scenario catalogue

Пользователь должен чувствовать плагины через доступные функции, а не через техническую архитектуру.

После activation plugin contributions могут появиться в:

- каталоге сценариев;
- доступных источниках;
- форматах импорта/экспорта;
- artifact/report profiles;
- специализированных business commands.

При disable они исчезают из новых запусков, но история старых cases/artifacts остаётся читаемой.

Это важный lifecycle rule:

```text
plugin unavailable now
≠
historical result disappears
```

В provenance старого артефакта хранится identity/version contribution, использованного при создании.

---

# 13. Раздел «Артефакты и отчёты»

Это второй действительно важный новый settings surface.

Нужно различать:

```text
UI appearance
и
artifact/report appearance
```

Первое принадлежит `stratbox-windows`.

Второе относится к бизнес-результату и может использовать profiles, в том числе предоставленные plugin capabilities.

---

# 14. Профиль оформления артефактов

Вместо десятков отдельных settings вида:

```text
шрифт
цвет заголовка
цвет таблицы
толщина границы
формат процентов
chart palette
```

нужен один основной selection:

```text
Профиль оформления
[ Strategy Box Standard ▼ ]
```

В список входят:

- встроенные профили Strategy Box;
- дополнительные profiles, предоставленные active plugins;
- возможно пользовательские validated profiles в будущем.

Каждый profile имеет stable ID и version.

Пример semantic model:

```text
ReportProfile
  profile_id
  version
  title
  provider_id
  fonts
  semantic_palette
  number_formats
  table_roles
  chart_roles
  metadata_defaults
  overridable_tokens
```

Сценарий использует selected profile только как **default**.

Конкретный run обязан зафиксировать resolved profile identity в provenance.

---

# 15. Цвета и шрифты, предоставленные плагином

После пользовательского уточнения это трактуется только как business/reporting capability.

Плагин может поставить:

- допустимые report font families;
- semantic palette;
- branded header styles;
- number formats;
- chart theme;
- document templates.

Эти ресурсы применяются к generated artifacts.

Они **не применяются** к shell `stratbox-windows`.

Таким образом возможно:

```text
Strategy Box UI
  → всегда собственный visual system

Excel/PPTX/DOCX artifact
  → Strategy Box Standard
  или
  → профиль, предоставленный active business plugin
```

Это сохраняет одновременно единый продуктовый UI и адаптируемую бизнес-отчётность.

---

# 16. Нужен ли отдельный выбор font и color для артефактов

По умолчанию — нет.

Лучший UX:

```text
Профиль = целостный набор решений
```

Если профиль разрешает overrides, в Settings можно раскрыть вторичный блок:

```text
Дополнительные параметры
  Шрифт: [по профилю]
  Акцент отчёта: [по профилю]
```

Но controls появляются только если active profile объявляет эти свойства `overridable`.

Это лучше универсального color picker/font picker, потому что:

- корпоративный шаблон может требовать fixed font;
- не каждый installed font корректно переносим;
- произвольные цвета ломают контраст;
- разные formats имеют разные ограничения;
- reproducibility становится хуже.

---

# 17. Автор файла

Идея полезная и технически хорошо ложится на Office formats.

Целевая setting:

```text
Автор файлов
[ Strategy Box ]
```

Default:

```text
Strategy Box
```

## 17.1. Куда применять

XLSX:

```text
workbook.properties.creator
```

DOCX:

```text
document.core_properties.author
```

PPTX:

```text
presentation.core_properties.author
```

При появлении PDF writer аналогичный metadata field может использоваться, если выбранный backend его поддерживает.

## 17.2. Не путать с provenance actor

Важное различие:

```text
Office Author = display/document metadata
Run Actor     = канонический факт provenance
```

Пользователь может поставить:

```text
Автор файлов = "Strategy Box"
```

но provenance всё равно знает:

```text
кто запустил сценарий
какой node/agent выполнил run
какая версия operation использовалась
```

Никогда нельзя строить audit trail из editable Office author field.

## 17.3. Почему default не должен быть OS username

Это даёт:

- одинаковое поведение Windows/Android/remote;
- меньше случайной персональной информации в файлах;
- воспроизводимые artifacts;
- предсказуемый корпоративный output.

---

# 18. Какие metadata должны быть settings, а какие — автоматикой

### User setting

```text
creator/author display label
```

### Автоматически из operation/artifact

```text
title
subject
category
keywords
created_at
modified_at
artifact ID
run ID
source/provenance reference
```

Пользователь не должен вручную задавать глобальные `title`, `subject` или `keywords`: они зависят от конкретного результата.

---

# 19. Default artifact profile как default, а не скрытая глобальная магия

Предположим в Settings выбрано:

```text
Профиль = Report A
Автор = Strategy Box
```

При запуске сценария runtime формирует explicit resolved settings:

```text
artifact_format.profile_id = report-a
artifact_format.profile_version = 3
artifact_metadata.creator = Strategy Box
```

И передаёт их в export layer.

В provenance сохраняются именно resolved values.

Это важно: изменение Settings через месяц не должно менять смысл старого run.

---

# 20. Workspace / Data — почему это не Settings

Текущий Strategy Box работает внутри AppDock-managed среды, где Data root является частью platform/runtime binding.

Поэтому Strategy Box Settings не должен дублировать:

- выбор системного диска;
- mount/network binding;
- physical storage provider;
- host path;
- node attachment;
- managed workspace root.

Целевая UX-модель:

```text
Проводник / Узел
  Data: доступно
  Workspace: ...
  [Открыть]
  [Скопировать путь]
  [Изменить в AppDock]   ← если capability доступна
```

Это status + action, а не preference.

---

# 21. Default output directory

Не рекомендую добавлять глобальную настройку «Папка сохранения».

Причина: разные operations создают разные классы результатов, а artifact layer должен уметь самостоятельно организовать outputs.

Лучший порядок:

```text
canonical artifact storage
→ workspace materialization/export
→ пользователь при необходимости выбирает export destination
```

Если конкретной операции действительно нужен target directory, это её parameter/preset.

Глобальный «все файлы всегда сюда» быстро станет источником путаницы.

---

# 22. Фоновые процессы — не Settings

Включение конкретного background scenario относится к рабочей поверхности Automation/Запуски.

Почему:

- пользователь может часто включать/выключать задачи;
- там нужны статус, last run, next run, error;
- это operational workflow, а не preference.

Settings может содержать только **как уведомлять** о фоновых процессах.

---

# 23. Раздел «Уведомления»

Создавать его стоит только вместе с реальным notification service.

Минимальная модель:

```text
Системные уведомления
[x] Завершение моих длительных запусков
[x] Ошибки моих запусков
[x] Поручения и действия, требующие внимания
[x] Общие проблемы узла
[ ] Обычные успешные фоновые обновления
```

При этом есть два уровня:

```text
in-app visibility
OS notification
```

Критические ошибки и system conditions продолжают отображаться внутри приложения независимо от notification preference.

Preference управляет только внешним/дополнительным уведомлением.

Не нужны:

- собственная громкость;
- выбор звука;
- позиция toast;
- длительность toast.

Это задача ОС.

---

# 24. Что делать с ошибками/логами/diagnostics в Settings

Не делать отдельный раздел «Логи».

Logging policy — system/engineering concern.

Пользовательские действия:

```text
Открыть диагностику
Скопировать отчёт
Открыть папку логов, если разрешено
```

должны находиться в Diagnostics surface.

Settings не должен содержать:

- log level DEBUG/INFO;
- telemetry endpoint;
- path к логам;
- rotation size;
- retention days;
- crash dump policy.

Это developer/managed configuration.

---

# 25. Update settings — не Strategy Box

`stratbox-windows` запускается через AppDock-managed lifecycle.

Следовательно, Strategy Box не должен иметь собственные controls:

```text
Проверять обновления автоматически
Канал обновлений
Скачивать обновления
Обновить plugin wheel
Версия Python runtime
```

Этим владеет AppDock/deployment layer.

При необходимости Strategy Box показывает read-only:

```text
Версия приложения
Версия core
Статус обновления
[Управлять в AppDock]
```

в About/Node, а не в Settings.

---

# 26. Network / proxy / certificates — не пользовательские settings Strategy Box

В managed corporate environment это policy/capability plugin/AppDock configuration.

Пользователь не должен выбирать:

- gateway URL;
- proxy;
- TLS mode;
- certificate path;
- private endpoint;
- authentication backend.

В plugin settings могут отображаться **безопасные абстрактные параметры**, если они действительно являются user choice, например account/profile selection.

Секреты и infrastructure topology не переходят в generic Settings.

---

# 27. AI settings — пока не нужны

Пока AI-runtime не стал реальной product capability, отдельный раздел `AI` создаст пустую архитектуру.

В будущем legitimate settings могут быть, например:

```text
AI confirmation policy
allowed default actions
notification behavior
```

но только после того, как authority/permission model стабилизирован.

Model/provider/token/temp и подобные technical controls не должны автоматически становиться end-user settings Strategy Box.

---

# 28. Язык приложения

Не добавлять настройку языка до появления реальной локализации минимум на второй язык.

Пустой selector с единственным «Русский» — шум.

Когда localization появится, language станет полноценным persistent preference и может образовать небольшой раздел «Язык и регион» только при наличии дополнительных настроек, например date/number locale.

---

# 29. Региональные форматы и единицы

Для аналитического продукта особенно важно не смешивать presentation preference с semantics данных.

Например:

```text
млрд руб.
USD
проценты
даты
```

обычно задаются domain/report semantics.

Глобальные настройки «десятичный разделитель», «валюта» или «единица измерения» могут исказить официальный источник.

Поэтому локаль интерфейса и units бизнес-данных должны оставаться разными слоями.

---

# 30. Целевая storage architecture настроек

Текущий единый `app.json` стоит разделить концептуально минимум на три файла/хранилища.

```text
settings/
  user_settings.json

state/
  surface_state.json
  recent_state.json
  scenario_drafts.json

plugins/
  plugin_settings.json       # либо namespaced per-plugin records
```

Managed policy приходит отдельно из runtime/AppDock context.

Точная физическая структура может быть другой; главное — semantic separation.

---

# 31. Предлагаемые platform-neutral models

```python
@dataclass(frozen=True)
class AppearanceSettings:
    theme_mode: Literal["system", "light", "dark"] = "system"
    accent_source: Literal["strategy", "system", "custom"] = "strategy"
    custom_accent: str | None = None


@dataclass(frozen=True)
class ArtifactDefaults:
    report_profile_id: str = "strategy.standard"
    creator_label: str = "Strategy Box"


@dataclass(frozen=True)
class NotificationSettings:
    own_run_completed: bool = True
    own_run_failed: bool = True
    assignments: bool = True
    node_problems: bool = True
    routine_background_success: bool = False


@dataclass(frozen=True)
class UserSettings:
    schema_version: int
    appearance: AppearanceSettings
    artifacts: ArtifactDefaults
    notifications: NotificationSettings | None
```

`plugins` я бы не помещал прямо внутрь этой dataclass как произвольный `dict[str, Any]`.

Для них нужен отдельный namespaced versioned config store.

---

# 32. Platform-neutral SurfaceState

Отдельно:

```python
@dataclass
class SurfaceState:
    window_geometry: ...
    selected_mode: ...
    left_panel_width: ...
    right_inspector_open: ...
    right_inspector_width: ...
    right_inspector_tab: ...
    chat_filter: ...
    selected_case: ...
```

Эта модель:

- изменяется часто;
- автоматически сохраняется;
- может быть сброшена без потери пользовательских preferences;
- не отображается как settings form.

---

# 33. Scenario drafts — отдельный storage

Сегодня `scenario_form_values` лежат рядом с window configuration.

Лучше:

```text
ScenarioDraftStore
  scenario_id
  schema_version
  saved_at
  fields
```

Плюсы:

- можно применить sensitivity policy;
- легко чистить stale drafts;
- можно мигрировать форму независимо от глобальных settings;
- secret fields можно вообще не persist;
- Android/Windows смогут использовать одинаковую semantics.

---

# 34. Precedence и effective settings

Нужна формальная resolution model.

Для обычной user setting:

```text
Product Default
      ↓
Workspace Default, если применимо
      ↓
User Preference
      ↓
Managed Policy constraints / forced value
      ↓
Effective Setting
```

Для конкретного run:

```text
Effective Setting
      ↓
Scenario preset/default
      ↓
Explicit run parameter
      ↓
Managed Policy validation
      ↓
Resolved Run Configuration
```

Policy всегда имеет право ограничить allowed values или forced value.

UI обязан показывать причину:

```text
"Управляется средой"
```

а не просто disabled control без объяснения.

---

# 35. Scope artifact defaults

Artifact profile потенциально имеет три уровня:

```text
product default
workspace/team default
user default
```

Но конкретный run фиксирует resolved profile.

Пример:

```text
product: strategy.standard
workspace: reporting.standard-2026
user: reporting.standard-2026
run: reporting.standard-2026 @ v4
```

Если workspace policy требует один corporate profile, user selector может стать read-only.

---

# 36. Plugin settings schema

Целевой declarative contract может содержать:

```text
PluginSettingSpec
  id
  title
  description
  value_type
  scope
  default
  required
  allowed_values
  sensitivity
  restart_requirement
  visibility
```

Типы controls определяет app:

```text
bool      → Toggle
small enum → Radio / Combo
string    → Text field
integer   → Numeric field
ref       → Selector
secret_ref → Secure reference selector
```

Plugin не передаёт widget class.

---

# 37. Plugin settings versioning

Каждый plugin config имеет:

```text
plugin_id
plugin_distribution_version
config_schema_version
values
```

При несовместимости:

```text
CONFIG_MIGRATION_REQUIRED
```

С учётом отсутствия требования backward compatibility core не обязан хранить бесконечные migration adapters.

Но пользователь должен получить понятное сообщение, а managed deployment может materialize новый config заранее.

---

# 38. Plugin installation и activation — разные понятия

```text
Installed
    пакет присутствует в runtime

Available
    descriptor совместим

Selected
    runtime/profile разрешил plugin

Configured
    обязательные settings заполнены

Ready
    health/readiness пройдены
```

Settings UI должен отражать именно эту state machine.

Один toggle «Plugin on/off» слишком слаб для реальной системы.

---

# 39. Если установлено несколько plugins

Settings page не должна скрывать конфликты.

Например:

```text
Два provider-а претендуют на один singleton capability
```

Целевой UI:

```text
Конфликт конфигурации
Выберите provider для capability X
```

если policy разрешает user selection.

Если binding задаётся managed profile, UI просто показывает resolved owner.

Никакого «первый найденный plugin побеждает».

---

# 40. Plugins и профили отчётности

Reporting profiles — хороший пример multi-contribution capability.

Несколько plugins могут добавить profiles:

```text
strategy.standard
example.reporting.green
example.reporting.board
```

IDs должны быть namespaced.

Коллизия ID — ошибка, а не silent override.

Пользователь выбирает профиль в `Артефакты и отчёты`, а не внутри `Плагины`.

В Plugin details лишь видно:

```text
Предоставляет профили отчётности: 2
```

Это важный UX-принцип:

> Пользователь выбирает бизнес-опцию там, где она используется; plugin page управляет самим расширением.

---

# 41. Настройки форматов Office

Нужен общий neutral `DocumentMetadataDefaults` / `ArtifactFormattingContext`.

Пример:

```text
creator
profile_id
language
application_name
```

Export adapter формата преобразует semantic metadata в physical properties.

### XLSX

Уже существует поддержка `creator`, `title`, `subject`, `category`, `keywords`, `description` через `workbook.properties`.

### DOCX

Current writer пока простой, но `python-docx` поддерживает read/write core properties, включая `author`.

### PPTX

`python-pptx` также поддерживает `core_properties.author` и другие Dublin Core properties.

Следовательно, общий default creator действительно можно сделать кросс-форматным.

---

# 42. Что не делать на уровне форматов

Не добавлять в Settings отдельные:

```text
Excel author
Word author
PowerPoint author
```

Нужен один semantic field:

```text
Artifact creator label
```

А adapters маппят его на конкретный формат.

То же касается профиля оформления: пользователь выбирает report profile, а не отдельные `xlsx_theme`, `pptx_theme`, `docx_theme`, если profiles могут выразить cross-format intent.

---

# 43. Settings и provenance

Любая setting, которая меняет содержимое или оформление артефакта, должна попадать в reproducibility metadata.

Минимум:

```text
report_profile_id
report_profile_version
creator_label
plugin contribution identities
relevant export settings
```

Appearance UI settings в provenance результата не нужны, потому что они не влияют на artifact semantics.

---

# 44. Settings и Android

Settings schema должна находиться в platform-neutral слое.

```text
application/settings/
  models.py
  service.py
  resolution.py
  policy.py

presentation/common/settings/
  projections.py
```

Windows:

```text
presentation/qt_desktop/settings/
```

Android:

```text
presentation/android/settings/
```

Обе surface получают один и тот же semantic model.

Platform differences:

- `accent_source=system` резолвится через Windows или Android adapter;
- system theme приходит из platform adapter;
- notification permissions различаются;
- open AppDock action различается.

Но сами setting IDs остаются общими.

---

# 45. Что синхронизировать между устройствами

Если AppDock/account layer в будущем поддержит cross-device preferences, синхронизировать разумно:

```text
appearance.theme_mode
appearance.accent_source
appearance.custom_accent
artifacts.report_profile_id
artifacts.creator_label
notification semantic preferences
optional plugin user selections, если plugin присутствует на обоих runtimes
```

Не синхронизировать:

```text
window size
panel widths
selected tab
scroll position
local path
selected participant
local notification permission state
```

Это device/surface state.

---

# 46. Первый запуск

Хорошие defaults позволяют практически обойтись без setup wizard.

Целевой first launch:

```text
Theme       = system
Accent      = Strategy Box
Report      = Strategy Box Standard
File author = Strategy Box
Notifications = sane defaults if capability exists
Plugins     = managed/runtime resolved
```

Пользователь сразу работает.

Если plugin требует configuration/auth, это показывается как конкретная readiness task, а не как длинный onboarding wizard всего приложения.

---

# 47. Reset

Settings page должна иметь один безопасный action:

```text
Сбросить пользовательские настройки
```

Он сбрасывает только `UserSettings`.

Отдельно возможно:

```text
Сбросить расположение интерфейса
```

в Diagnostics/advanced recovery, потому что это `SurfaceState`.

Нельзя одной кнопкой удалять:

- history;
- artifacts;
- plugin config;
- workspace;
- logs;
- managed policy.

---

# 48. Search in settings

При трёх-четырёх разделах отдельный search не нужен.

Поиск settings становится оправданным только при десятках plugin schemas или очень крупном продукте.

Даже тогда он должен искать и built-in, и plugin-declared settings через unified semantic index.

На текущем масштабе search bar только усложнит UI.

---

# 49. Apply / Save / Cancel

Для простых settings предпочтительна модель immediate apply:

- theme;
- accent;
- notifications;
- creator label после focus loss;
- report profile.

Кнопка глобального `Сохранить` не нужна.

Для plugin config, который требует restart или validation, допускается scoped action:

```text
Применить настройки плагина
```

потому что там изменение может быть транзакционным и связано с readiness.

То есть не нужно искусственно подгонять все settings под один interaction model.

---

# 50. Settings navigation

Предпочтительная desktop-композиция:

```text
┌────────────────────────────────────────────────────┐
│ Настройки                                          │
├────────────────┬───────────────────────────────────┤
│ Внешний вид    │                                   │
│ Артефакты      │  выбранная страница               │
│ Плагины        │                                   │
│ Уведомления*   │                                   │
│                │                                   │
│──────────────  │                                   │
│ О приложении   │                                   │
└────────────────┴───────────────────────────────────┘
```

`О приложении` может находиться внизу как informational destination, хотя семантически это не settings.

`Узел` и `Диагностика` лучше оставить отдельными действиями из user menu, потому что это operational surfaces.

---

# 51. About

About содержит:

- Strategy Box version;
- core version;
- build/revision;
- copyright/license;
- links/help if needed.

Не смешивать с System Settings.

---

# 52. Системные сведения

Node/session/host/runtime state должны оставаться в Node view.

Преимущество:

```text
Settings = "что я предпочитаю"
Node     = "где и как я сейчас работаю"
Diagnostics = "что происходит и всё ли исправно"
```

Эта семантическая ясность особенно важна перед появлением remote hosts.

---

# 53. Managed settings UX

Если setting принудительно задана политикой:

```text
Профиль оформления
[ Corporate Standard ] 🔒
Управляется рабочей средой
```

Если allowed values ограничены:

```text
доступны только значения A / B
```

Нельзя silently менять user preference в config и потом игнорировать его.

Service должен различать:

```text
stored_user_value
effective_value
policy_source
```

---

# 54. SettingsService

Целевой service:

```text
SettingsService
  load_user_settings()
  update_user_setting(...)
  resolve_effective_settings(...)
  reset_user_settings()
  get_setting_state(id)
```

`SettingState`:

```text
value
source
editable
allowed_values
reason
restart_required
```

Presentation не должна сама вычислять policy precedence.

---

# 55. Persistence requirements

Current `save_user_config()` пишет JSON напрямую.

Для полноценной версии нужно минимум:

- versioned schema;
- atomic temp → replace;
- validation before commit;
- rollback/default on invalid config с явным diagnostic;
- separation от scenario drafts;
- no secret values;
- predictable serialization.

Settings меняются редко, поэтому сложная embedded database здесь не нужна.

Обычный небольшой JSON вполне подходит при нормальной atomicity/versioning.

---

# 56. Schema evolution

Пример:

```json
{
  "schema": "strategy-box.user-settings/v1",
  "appearance": {
    "theme_mode": "system",
    "accent_source": "strategy",
    "custom_accent": null
  },
  "artifacts": {
    "report_profile_id": "strategy.standard",
    "creator_label": "Strategy Box"
  }
}
```

При major redesign, с учётом правила отсутствия backward compatibility, можно перейти на новую schema и сохранить только явно полезные user values через одноразовый controlled migration.

Не нужно навечно поддерживать historical aliases текущего `AppUserConfig`.

---

# 57. Что делать с текущим `AppUserConfig`

Я бы заменил его на три owner-а:

```text
UserSettingsStore
SurfaceStateStore
ScenarioDraftStore
```

Плюс plugin configuration service.

`PreferencesService` в нынешнем виде фактически является смешанным state writer. Его стоит разделить:

```text
SettingsService
SurfaceStateService
ScenarioDraftService
```

Это важнее, чем просто добавить новые поля в существующий JSON.

---

# 58. Архитектура целевого settings слоя

```text
stratbox-windows
│
├─ application/
│  ├─ settings/
│  │  ├─ models.py
│  │  ├─ service.py
│  │  ├─ policy.py
│  │  ├─ resolution.py
│  │  └─ store.py
│  │
│  ├─ surface_state/
│  │  ├─ models.py
│  │  └─ store.py
│  │
│  ├─ scenario_drafts/
│  │  ├─ models.py
│  │  └─ store.py
│  │
│  └─ plugins/
│     ├─ catalogue.py
│     ├─ configuration.py
│     ├─ activation.py
│     └─ projections.py
│
├─ presentation/
│  ├─ common/settings/
│  └─ qt_desktop/settings/
│
└─ adapters/
   ├─ settings_persistence/
   ├─ platform_appearance/
   └─ appdock_policy/
```

Физические имена можно упростить, но обязанности стоит сохранить.

---

# 59. Граница с `stratbox` core

`stratbox` не должен знать UI settings.

Core получает только resolved business configuration, нужную конкретной operation/export.

Например:

```text
ArtifactFormattingContext
  report_profile_id
  creator_label
```

Core также владеет contracts для report profiles и plugin capabilities, если это business-layer concern.

`stratbox-windows` владеет user preference и выбором default.

---

# 60. Где должен жить reporting profile

Semantic contract и builtin profiles логично держать в core/reporting layer, потому что ими пользуются exporters независимо от frontend.

User selection:

```text
stratbox-windows settings
```

Resolved profile:

```text
stratbox reporting/export operation
```

Plugin contribution:

```text
stratbox plugin capability
```

Так Windows UI остаётся свободным от concrete formatting implementation.

---

# 61. Какие settings могут принадлежать workspace

Workspace-scoped settings следует вводить только там, где **несколько пользователей реально должны получать одинаковое business behavior**.

Хорошие кандидаты в будущем:

- default report profile;
- standard artifact naming policy;
- approved business plugin selection, если это не AppDock policy;
- shared scenario presets.

Плохие кандидаты:

- theme;
- accent;
- window layout;
- notification preference.

Workspace preference не должен перекрашивать UI другого пользователя.

---

# 62. Shared settings и collaboration

Если команда работает в одном узле, UI должен различать:

```text
Личное
Рабочая среда
Управляется системой
```

Но это не означает, что Settings обязательно нужны три top-level вкладки.

Лучше у конкретного control показывать scope:

```text
Профиль отчёта
Corporate Standard
Рабочая среда
```

или в отдельной details строке.

Таким образом taxonomy settings остаётся по смыслу, а не по technical storage scope.

---

# 63. Plugin settings и shared scope

Пример plugin setting:

```text
Источник данных: Profile A
scope = WORKSPACE
```

UI показывает:

```text
Изменение повлияет на пользователей этой рабочей среды
```

и, при необходимости, требует authority/approval.

То есть plugin schema должна уметь объявить scope, но plugin не определяет authorization самовольно. Authority приходит из application/AppDock policy.

---

# 64. Что считать «системной настройкой»

Термин лучше использовать аккуратно.

Для пользователя Settings — это единая поверхность.

Внутри архитектуры есть:

```text
User Preference
Workspace Configuration
Managed Policy
Runtime State
System Information
```

«Системные настройки» как отдельная мусорная корзина почти всегда вредны.

Каждому параметру нужен конкретный owner.

---

# 65. Антинастройки: список того, что специально не нужно добавлять

1. «Запоминать размер окна» — просто всегда запоминать.
2. «Запоминать последнюю вкладку» — просто всегда запоминать.
3. «Стартовая страница» — восстановить last context.
4. «Количество последних сценариев» — product default.
5. «Автоматически создавать input/output» — workspace contract.
6. «Показывать advanced parameters» — UI state / scenario-specific.
7. «Log level» — diagnostics/developer.
8. «Очистка истории через N дней» — managed retention policy, если появится.
9. «Количество параллельных задач» — executor policy.
10. «Retries по умолчанию» — operation/scenario policy.
11. «Proxy» — managed/network capability.
12. «Путь к cache» — runtime implementation.
13. «Путь к logs» — runtime implementation.
14. «Update channel» — AppDock.
15. «Python environment» — AppDock.
16. «Core version» — information.
17. «Node ID» — information.
18. «Workspace root» — runtime binding/status.
19. «Формат каждого типа файлов» — scenario/export parameter.
20. «Цвет каждого элемента интерфейса» — design system.
21. «Шрифт UI» — design system.
22. «Plugin can inject UI» — запрещённая extension model.

---

# 66. Принцип progressive disclosure

Settings должны показывать только применимые controls.

Примеры:

- custom accent field виден только при `Accent = Свой`;
- plugin config раскрывается только для выбранного plugin;
- override font показывается только если report profile разрешает override;
- notifications page отсутствует без notification capability;
- managed-only setting не показывается обычному пользователю, если от неё нет полезной информации.

Это помогает держать интерфейс маленьким даже при росте системы.

---

# 67. User-facing labels

Нужно избегать architecture vocabulary.

Плохо:

```text
Runtime Provider Binding
Surface Preference
Artifact Style Capability
Extension Contract v1
```

Хорошо:

```text
Плагины
Профиль оформления
Автор файлов
Тема
Акцент
```

Технические IDs доступны в Details/Diagnostics.

---

# 68. First-class diagnostics links

Plugin card может иметь:

```text
Проверить
Подробнее
```

Result:

```text
Готов к работе
или
Требуется авторизация
или
Ошибка конфигурации
```

Кнопка не должна показывать traceback напрямую. Подробности идут через общую observability/diagnostics model.

---

# 69. Не делать plugin marketplace внутри Strategy Box сейчас

`Плагины` ≠ marketplace.

На текущем горизонте нужны:

- inventory;
- activation;
- configuration;
- health;
- installation handoff to AppDock.

Discovery marketplace, рейтинги, screenshots, публичный каталог и purchase flows не нужны.

Это резко снижает сложность и риск.

---

# 70. Настройки и безопасность

Settings persistence не должна содержать:

- passwords;
- tokens;
- private keys;
- session cookies;
- full sensitive URLs;
- credentials inside paths;
- arbitrary plugin blobs без schema.

Plugin config хранит только safe values и `SecretRef`/auth-profile references.

UI masked field ещё не делает секрет безопасно сохранённым.

---

# 71. Настройки и observability

Изменение значимой business setting может генерировать audit event, например:

```text
workspace report profile changed
plugin activated/deactivated
managed plugin config changed
```

Изменение purely personal appearance:

```text
theme/accent
```

не требует operational audit trail.

Это ещё одна причина разделять scopes.

---

# 72. Settings и operation catalogue

Operation/Scenario specs могут ссылаться на defaults из settings через semantic key:

```text
artifact.profile = settings.artifacts.report_profile_id
artifact.creator = settings.artifacts.creator_label
```

Но конкретные handlers не должны сами читать `app.json`.

Правильная цепочка:

```text
UI / Scenario launcher
        ↓
SettingsService resolves defaults
        ↓
Execution request receives explicit values/context
        ↓
stratbox operation
```

Так headless/remote/AI execution может сформировать тот же context без Qt.

---

# 73. Settings и remote execution

Если scenario выполняется на другом host:

- UI appearance не передаётся;
- notification preference остаётся на client;
- artifact profile и creator должны передаваться как run configuration;
- plugin capability selection должен быть разрешён на execution node;
- local plugin state клиента не считается доказательством plugin availability на host.

Это критично для будущей AppDock remote model.

---

# 74. Settings и AI execution

AI, запускающий разрешённый scenario, должен получать effective artifact defaults, но не менять persistent user settings без отдельного authorized action.

Правило:

```text
use setting
≠
modify setting
```

Изменение глобального default — отдельная управляемая команда.

---

# 75. Потенциальный Settings API

В platform-neutral application layer:

```python
settings.get("appearance.theme_mode")
settings.set("appearance.theme_mode", "dark")
settings.describe("artifacts.report_profile_id")
settings.resolve(context=...)
```

Но generic string-key API не должен заменять typed models внутри business code.

Он полезен для presentation/schema rendering, а application logic работает через typed projections.

---

# 76. Validation theme/accent

Theme setting должна проверяться до persistence.

Custom accent:

- syntactically valid color;
- semantic ramp генерируется автоматически;
- contrast-sensitive tokens корректируются theme engine;
- status colors остаются независимыми;
- plugin не получает доступ к этой palette.

---

# 77. Validation artifact author

`creator_label`:

- строка;
- разумный max length, например 128/255 chars;
- trim whitespace;
- empty → fallback `Strategy Box`;
- control characters запрещены.

Не подставлять автоматически email/UPN без явного требования пользователя.

---

# 78. Validation report profile

При выборе profile:

```text
profile exists
provider ready
profile compatible with requested artifact format
policy allows profile
```

Если previously selected plugin profile исчез:

```text
fallback не должен происходить молча
```

Лучшее поведение:

- пометить сохранённый preference unavailable;
- effective value временно перейти на Strategy Box Standard;
- показать ненавязчивое предупреждение в Settings;
- новый run сохраняет фактически использованный fallback profile.

---

# 79. Не делать profile fallback частью private magic

Resolution всегда machine-readable:

```text
requested_profile
resolved_profile
resolution_reason
provider
```

Это важно для воспроизводимости.

---

# 80. Migration с текущего состояния

Так как backward compatibility не нужна, миграцию лучше сделать чисто.

## Шаг 1

Ввести новые stores:

```text
UserSettingsStore
SurfaceStateStore
ScenarioDraftStore
```

## Шаг 2

Однократно прочитать старый `app.json`.

## Шаг 3

Перенести только:

```text
window/layout → SurfaceState
last scenario/filter/etc → Recent/SurfaceState
scenario values → ScenarioDraftStore
```

## Шаг 4

Создать новые UserSettings из defaults:

```text
theme=system
accent=strategy
profile=strategy.standard
creator=Strategy Box
```

Старых явных UI preferences про «стартовую вкладку» не переносить как settings.

## Шаг 5

Удалить old mixed config contract.

---

# 81. Что потребуется изменить в текущем SettingsDialog

Вместо tab-based `Пользовательские / Рабочие / Системные`:

```text
left navigation + settings page
```

Или даже простой небольшой dialog с vertical sections, пока pages всего три.

Важнее структура semantics, чем конкретный widget.

### Удалить

- open right panel at startup;
- start mode;
- start inspector tab;
- workspace status page;
- system status page.

### Добавить

- Appearance;
- Artifacts;
- Plugins;
- Notifications when real.

### Ссылками оставить

- Node;
- Diagnostics;
- About.

---

# 82. Что потребуется изменить в `PreferencesService`

Текущий сервис переименовать/разделить.

Он сейчас обслуживает и preference, и surface state, и scenario values.

Целевые обязанности:

```text
SettingsService
  persistent intentional preferences

SurfaceStateService
  shell/window/navigation restoration

ScenarioDraftService
  remembered form values
```

Это один из основных архитектурных результатов исследования.

---

# 83. Что потребуется от `stratbox`

Core должен получить/нормализовать:

1. общий reporting profile contract;
2. built-in Strategy Box profile;
3. artifact formatting context;
4. document metadata context;
5. plugin capability contributions для report profiles/templates;
6. format adapters, применяющие semantic metadata;
7. provenance capture resolved profile identity.

При этом core не должен читать desktop preference store.

---

# 84. Что потребуется от plugin contract

General plugin contract стоит дополнить безопасными business contributions:

```text
report_profiles
report_templates
operation providers
source/data capabilities
format capabilities
settings_schema
health
```

И одновременно явно запретить:

```text
surface_theme
QSS
Qt widgets
shell fonts
navigation injection
arbitrary UI code
```

Это лучше сделать contract-level rule, а не только convention.

---

# 85. Что потребуется от AppDock boundary

Strategy Box-side integration достаточно минимальна:

- получить managed policy;
- получить plugin installation/availability state;
- вызвать внешнее управление plugin packages;
- получить node/session identity;
- получить Data binding;
- при необходимости получить cross-device user preferences service.

Strategy Box не должен копировать package manager или system settings AppDock.

---

# 86. Тестовая стратегия

## User settings

- defaults;
- serialization;
- atomic persistence;
- invalid schema;
- reset;
- managed forced value;
- allowed-values restriction.

## Surface state

- save/restore;
- corruption recovery;
- reset layout;
- no impact on user settings.

## Appearance

- system/light/dark;
- system/custom accent;
- contrast generation;
- plugin cannot affect appearance.

## Artifacts

- creator default Strategy Box;
- XLSX creator;
- DOCX author;
- PPTX author;
- profile resolution;
- missing profile behavior;
- provenance records exact resolved profile.

## Plugins

- installed/selected/ready state;
- optional enable/disable;
- required locked plugin;
- invalid config;
- secret field never persisted;
- declarative schema rendering;
- no arbitrary UI contribution;
- restart required state.

---

# 87. Acceptance criteria

Settings redesign можно считать завершённым, если:

1. Settings содержит только устойчивые preferences.
2. Размер окна и panel state больше не представлены как user settings.
3. Workspace/system info вынесены в Workspace/Node/Diagnostics.
4. Appearance имеет максимум Theme + Accent в первой версии.
5. Plugin не может модифицировать application visual system.
6. Plugins управляются через отдельную standard surface.
7. Plugin config declarative и versioned.
8. Package installation остаётся внешним deployment concern.
9. Artifact profile выбирается отдельно от UI theme.
10. File creator default = `Strategy Box`.
11. Actual run actor остаётся отдельным provenance fact.
12. XLSX/DOCX/PPTX adapters способны применить общую author metadata.
13. UI и Android используют одну semantic settings model.
14. Secrets отсутствуют в persisted settings.
15. Managed policy может lock/limit setting с видимой причиной.
16. Settings изменения применяются сразу там, где это безопасно.
17. Нет generic «Advanced/System» dumping ground.

---

# 88. Приоритетная последовательность реализации

## P0 — разделить state и settings

1. `UserSettingsStore`.
2. `SurfaceStateStore`.
3. `ScenarioDraftStore`.
4. убрать semantic overload текущего `PreferencesService`.

## P0 — Appearance

5. theme tokens/system-light-dark.
6. Strategy/system/custom accent.
7. новый Appearance page.

## P1 — Artifact defaults

8. `ArtifactDefaults`.
9. default creator `Strategy Box`.
10. общий document metadata context.
11. reporting profile contract.
12. builtin `strategy.standard`.
13. provenance resolved formatting.

## P1 — Plugins

14. plugin catalogue/state projections.
15. declarative config schema.
16. standard Plugin Settings UI.
17. managed/optional activation semantics.
18. AppDock package-management handoff.

## P2 — cross-format reporting

19. DOCX/PPTX metadata integration.
20. cross-format report profile semantics.
21. template contributions.

## P2 — Notifications

22. реализовать notification service.
23. только после этого добавить Settings page.

## P3 — cross-device

24. shared semantic settings model.
25. optional preference sync через platform/account layer.

---

# 89. Итоговая целевая таблица

| Параметр / функция | Где живёт | Показывать в Settings | Default / правило |
|---|---|---:|---|
| Theme | UserSettings | да | System |
| UI accent | UserSettings | да | Strategy Box |
| UI font | Product design | нет | app-owned |
| UI density | Product design, возможно future pref | пока нет | единая |
| Reduce motion | OS/platform | обычно нет | follow system |
| Window size | SurfaceState | нет | auto restore |
| Panel widths | SurfaceState | нет | auto restore |
| Inspector open/tab | SurfaceState | нет | auto restore |
| Selected mode | SurfaceState | нет | auto restore |
| Chat filter | SurfaceState | нет | auto restore |
| Selected participant | SurfaceState | нет | auto restore |
| Last scenario | RecentState | нет | auto restore |
| Scenario form values | ScenarioDraftStore | нет | per scenario |
| Workspace root | AppDock/runtime binding | нет | managed/status |
| Data root | AppDock/runtime binding | нет | managed/status |
| Log level | runtime policy | нет | managed |
| Update channel | AppDock | нет | managed |
| Plugin installation | AppDock/deployment | handoff | external |
| Plugin activation | Plugin/Application policy | да, если optional | explicit |
| Plugin config | PluginConfigStore | да | schema-driven |
| Plugin secret | Secret provider | reference only | never raw |
| Report profile | User/workspace default | да | Strategy Box Standard |
| Report font/palette | ReportProfile | обычно нет отдельно | profile-owned |
| Artifact creator label | UserSettings | да | Strategy Box |
| Actual run author/actor | Provenance | нет | automatic |
| Artifact output format | Scenario/run parameter | нет global | operation-specific |
| Background enabled state | Automation/Jobs | нет | operational |
| Notification preferences | UserSettings | после реализации | sane defaults |
| Node/session/host | Runtime state | нет | Node view |
| Diagnostics | Diagnostics surface | нет | action |
| App/core version | About/Node | нет | information |

---

# 90. Финальный тезис

Хорошая settings architecture для Strategy Box выглядит почти удивительно маленькой.

Это признак качества, а не недостатка функций.

Пользователь должен открывать Settings, когда хочет ответить на четыре вопроса:

```text
Как выглядит мой Strategy Box?
Как по умолчанию выглядят создаваемые им результаты?
Какие business plugins доступны и как они настроены?
Как меня уведомлять о важной работе?
```

Всё остальное должно находиться там, где пользователь с ним реально работает:

```text
workspace → в Проводнике
node/runtime → в Узле
ошибки → в Запусках/Диагностике
background jobs → в Запусках/Автоматизации
scenario parameters → в сценарии
updates/install → в AppDock
layout → восстанавливается автоматически
```

И центральное правило по plugins:

> **Плагин расширяет то, что Strategy Box умеет делать, но не то, как выглядит само приложение.**

Это сохраняет `stratbox-windows` единым продуктом, делает будущий `stratbox-android` реалистичным, оставляет business extensions мощными и одновременно не превращает Settings в бесконечный склад случайных параметров.

---

# 91. Проверенные источники и материалы

## Внутренние материалы Strategy Box

- `stratbox-windows_current_state_full_research_2026-10-06.md`;
- `stratbox_base_study_current_state_2026-10-06.md`;
- `strategy_box_interface_visual_system_research_2026-10-07.md`;
- `stratbox_windows_interface_requirements_research_2026-10-07.md`;
- `stratbox_file_artifact_layer_research_2026-10-06.md`;
- `stratbox_observability_errors_logs_research_2026-10-07.md`;
- `stratbox_corporate_plugin_contract_research_2026-10-07.md` как общий neutral plugin-contract research;
- актуальный `main` `ForestTiger-GH/stratbox-windows`, включая `settings_dialog.py`, `runtime/config.py`, `runtime/user_preferences.py`, theme layer и artifact models;
- актуальный `main` `ForestTiger-GH/stratbox`, включая runtime provider boundary, Excel styles и IO adapters.

## Внешняя техническая сверка

- Microsoft Learn — Guidelines for app settings, актуальная редакция 2026: settings должны быть простыми, редкими, с разумными defaults и immediate apply; обычные workflow commands не относятся к settings.
- Microsoft Learn — Theming in Windows apps / Theme Resources: system/light/dark, system accent и high-contrast behavior.
- Python Packaging User Guide — Entry points specification: стандартный mechanism discovery installed plugin contributions.
- `openpyxl` — document core properties, включая `creator`.
- `python-docx` — Open XML core properties, включая `author`.
- `python-pptx` — presentation core properties, включая `author`.

---

**Конец исследования.**
