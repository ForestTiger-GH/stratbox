# Strategy Box — консолидирующее исследование 07: Product Surface Architecture

**Дата:** 2026-10-09  
**Программа:** третья ветка консолидирующих исследований Strategy Box, тема **07 — Product Surface Architecture**  
**Статус:** **Research Synthesis / Consolidation Result**. Исследовательский результат; не Product Decision, не утверждённый Target WHAT/HOW, не описание уже внедрённого API и не изменение кода.  
**Основная база:** тематический корпус `02-base-study` и результаты сквозных исследований 00–05; `01-old-notes` — исторический источник, а не текущая норма.  
**Проверка реализации:** публичный `stratbox-windows` — срез `main` на commit `959e9c4ce1441124af5111c1e025041714e04d3b`; для текущего `stratbox` использованы baseline `e968853572676d8e5d963607d1f0cb50ff8f20b7` и проверка сохранности `src/`/`tests/` в исследовании темы 04 на commit `6c3714078791eabd64927b143aa1e5f4a76f9b88`.  
**Граница публикации:** исключительно общие, нейтральные extension/capability contracts. Устройство и сведения о конкретных закрытых корпоративных расширениях исключены. Использованы смысловые правила доказательности и MADAR-методологии без описания структуры внешних методологических проектов.  
**Размещение:** файл создан для передачи в чат; в репозиториях изменений не выполнялось.

---

## 0. Executive synthesis

**[CONSOLIDATED]** Strategy Box следует развивать как **один аналитический продукт с единым смысловым и прикладным состоянием, представляемым несколькими нативными клиентами**. Windows, Web, Android и узкие будущие поверхности не становятся отдельными системами Work, исполнения, артефактов, прав или истории. Они получают разрешённые проекции одной application authority и представляют их подходящим своему устройству способом.

```text
                              Strategy Box application authority
                    Thread / Work / Run / Jobs / capabilities / artifacts
                    collaboration / permissions / projections / events
                                           │
                          query / command / subscription contracts
                                           │
                     canonical semantic surface projections + actions
                                           │
             ┌─────────────────┬────────────┼─────────────┬────────────────┐
             ▼                 ▼            ▼             ▼                ▼
       Windows desktop       Web        Android       narrow client    future surface
         Qt renderer     browser UI    native UI      notifications      other
             │                 │            │             │                │
       local desktop       responsive    touch-first   bounded actions    fit to role
       integrations       security       OS services

   Ниже application authority: stratbox (аналитическая семантика и операции).
   Снаружи: AppDock (установка, управляемая среда, узел, платформа, lifecycle).
```

Эта схема описывает **логические ответственности**, а не утверждает готовность server/API или необходимость немедленно создавать отдельный пакет для каждой рамки.

### Двенадцать главных результатов

1. **[CURRENT]** Сегодня материально существует Windows surface: Qt/PySide6, трёхзонная оболочка, сценарная лента, Проводник, каталоги операций и сценариев, инспектор, локальные cases/events/logs/artifacts, настройки и AppDock activation. Web/Android — пока проектные направления, а не работающие implementation surfaces.
2. **[CONSOLIDATED]** Семантические объекты интерфейса должны соответствовать общей онтологии: `Thread` — контекст взаимодействия, `Work` — долговечная задача, `Run` — эпизод исполнения, `Job` — исполнительная единица, `Artifact` — самостоятельный результат, `Scenario` — повторяемое пользовательское определение, `Scheme` — машинно-читаемая композиция. `Case` текущего Windows — переходная модель карточки исполнения, а не канонический владелец всей работы.
3. **[CONSOLIDATED]** «Scenario chat» как центральная *технология* интерфейса уступает место **Work/Thread-first пользовательской поверхности**. Сценарии сохраняют отдельный каталог и быстрый выбор, но больше не обязаны быть началом любого действия.
4. **[CONSOLIDATED]** Устойчивый общий информационный каркас: **Работа**, **Проводник**, **Сценарии**, **Запуски**. Каскады, фоновые процессы, участники, поручения, уведомления и логи являются контекстами или специализированными проекциями, а не автоматически равноправными корневыми разделами.
5. **[TARGET-HYPOTHESIS]** Четыре названия следует считать **логическими рабочими направлениями**, а не обязательными четырьмя вкладками на экране телефона, в web/mobile companion или узком виджете. Каждая поверхность выбирает свой navigation pattern и набор видимых entry points.
6. **[CONSOLIDATED]** `presentation/common` должен описывать **семантику экранов и действий**, а не копию геометрии Qt: сущности, коллекции, выбранный объект, состояния, доступные actions, notices, текстовые роли, структуру форм и порядок навигации. Qt Widgets, HTML/CSS, Compose/Qt Quick и ОС реализуют собственные renderers/adapters.
7. **[CONSOLIDATED]** Клиентский UI не является источником durable truth. Work, Job, permissions, read cursors, assignments и артефакты принадлежат application authority. На клиенте живут безопасные drafts, layout state, временные проекции и device-specific preferences.
8. **[CONSOLIDATED]** Одни и те же события исполнения имеют две основные проекции: **карточки в контексте Work/Thread** и **операционный список Запусков**. Нет второго фонового execution engine и второй системы истории.
9. **[CONSOLIDATED]** Проводник должен объединить разрешённые workspace objects и артефакты, сохраняя различие изменяемого файла и зафиксированного результата. Для Web/Android идентичность объекта — `FileRef`/`ArtifactRef`, а не физический путь на хосте.
10. **[CONSOLIDATED]** `InterfaceTheme`, `ArtifactStyleSet`, пользовательские Settings, SurfaceState и ManagedPolicy являются отдельными понятиями. Плагины могут давать бизнес-возможности и данные оформления артефактов, но не произвольно менять shell, navigation, QSS/CSS или widgets.
11. **[CONSOLIDATED]** Дизайн строится как **семантические токены → адаптеры → нативный рендеринг**, motion — как переход по подтверждённым состояниям. Доступность, Reduced Motion, high contrast и системные text scaling — обязательные свойства поверхностей, а не позднее визуальное украшение.
12. **[UNKNOWN]** Открыты точная физическая упаковка shared semantics, UI toolkit Android, объём offline-функций, правила кросс-девайсных drafts, схемы deep links, search/indexing, SLA обновления projections, UX первой версии AI и граница desktop full-client ↔ mobile companion. Эти решения требуют пилота и Product Decision, а не вывода по аналогии.

**Основной тезис:** *одинаковым должен быть смысл работы, права и результат; одинаковой геометрии, поведения ввода и наборов открытых панелей от Windows, браузера и телефона требовать не следует.*

---

# 1. Метод, границы доказательности и корпус

## 1.1. Точный scope темы 07

По [P] исследование охватывает Work/chat, Explorer, catalogue, runs, inspector, artifacts, settings, notifications, presence, assignments, design tokens, themes, motion, accessibility и адаптивное поведение. Важнее всего ответить, **какую единую семантическую систему все эти поверхности представляют**.

Проведены четыре прохода: (а) верхнеуровневая модель ответственности; (б) фактологическая сверка Windows; (в) сведение UX/visual/motion/settings с уже согласованными data, execution, state и collaboration; (г) сквозные контрольные пользовательские пути для Windows/Web/Android, с поиском конфликтов и локальных UNKNOWN.

## 1.2. Порядок доверия к источникам

1. Текущий код и manifest **implementation owner** — для утверждений о наличии функциональности.
2. Документация прямого owner — для заявленных контрактов, с проверкой против кода при расхождении.
3. Консолидированные темы 00–05 — для уже выверенных отношений `Thread/Work/Run`, данных, артефактов и state ownership.
4. Тематические работы второй ветки — для конкретных UX-паттернов, целевых требований, вариантов реализации и конфликтов.
5. Исторические заметки — для понимания исходных намерений, не в качестве актуального Product.
6. Официальные внешние источники — для платформенных стандартов и проверки отдельных технических допущений. Они не заменяют решения о Strategy Box.

**Метки:** `CURRENT` — прямое наблюдение/датированный baseline; `CONSOLIDATED` — устойчивый междокументный вывод; `TARGET-HYPOTHESIS` — предложенный вариант; `CONFLICT` — несовместимые предложения; `SUPERSEDED` — вытеснённое раннее решение; `UNKNOWN` — требуются данные или эксперимент.

## 1.3. Основные опорные исследования

Прежде всего использованы [B-WIN], [B-CORE], [B-UX], [B-VISUAL], [B-MOTION], [B-SET], [B-STYLE], [B-WEB], [B-MULTI], [B-BG], [B-AI-UI], [B-OBS], [B-EXEC], [B-CMD], [B-ART], [B-PORT], [B-PROTOS-B], [B-EXT], а также [R00]–[R05]. Ряд работ второй ветки читается как **исходная целевая гипотеза**, если последующее сквозное исследование уточнило термины. Все сокращения и прямые ссылки собраны в §28.

## 1.4. Ограничение уверенности

Прямо проверены выбранные `stratbox-windows` файлы `appdock/manifest.json`, `pyproject.toml`, `application/scenarios/models.py`, `application/scenarios/runner.py`, `application/history/persistence.py`, `application/background/store.py`, `runtime/bootstrap.py`, `runtime/config.py`, `presentation/common/scenario_chat/projector.py`, `presentation/qt_desktop/scenario_coordinator.py`, `presentation/qt_desktop/dialogs/settings_dialog.py`. Это выборочная **статическая проверка**, не новая регрессия всего UI. Полный набор UI E2E/a11y/performance испытаний здесь **не запускался**. Нет оснований утверждать наличие уже работающего Web/Android/host API. Псевдосхемы ниже являются кандидатами контрактов.

---

# 2. Current Truth: фактическая продуктовая поверхность

## 2.1. Windows surface как действующий frontend

**[CURRENT]** `stratbox-windows` — PySide6/Qt desktop application с AppDock Connector Manifest `4.0`, `default_surface_id = desktop`, `entry_view = scenario_chat`, declared view `workspace`, Windows-only local foreground activation. В manifest объявлены возможности artifacts/presence; это **декларации интеграционной поверхности**, которые нельзя принимать за доказательство работающей сетевой presence.

В корневом `pyproject.toml`: Python `>=3.10`, PySide6 `>=6.6`, версия desktop package `0.1.0`; зависимость на более ранний `stratbox==0.2.1` при baseline core `0.8.0`. Это явный **current contract/version drift**, требующий самостоятельной проверки установки перед следующей implementation фазой [W-MANIFEST] [W-PROJECT].

**Визуальная композиция:** слева mode rail/список и Проводник, в центре scenario-chat и composer, справа контекстный inspector, в служебных частях node/runtime diagnostics. Шесть сегодняшних mode rail entry: Проводник, Сценарии, Каскады, Фоновые, Участники, Поручения [B-WIN].

**Реальные операции:** catalog содержит два предметных вызова core (загрузка исходных файлов ЦБ и экспорт истории эскроу) и `system.diagnostics`; atomic scenarios строятся по операциям, плюс один составной каскад. Сценарный runner последовательно выполняет steps, создаёт событийную историю, записи логов, артефакты и user-facing `ScenarioRunCase` [B-WIN] [W-SCENARIO].

**Параметры:** декларативная модель на `OperationParamSpec`, формы преимущественно text/int/bool/select/path; имеются default, required, basic/advanced, min/max. Это хороший задел переноса **семантики параметров**, но не готовая внешняя переносимая schema с версией, сложной валидацией, accessibility и nested forms.

**Асинхронность:** `ScenarioCoordinator` использует Qt `QThread`, разрешает один одновременный запуск, реального cancellation token/JobManager нет. `runtime.bootstrap` создаёт coordinator из слоя Qt. Следовательно, runtime не полностью frontend-neutral. Шаблон `QThread` пригоден как временный desktop local adapter, а не долгоживущий execution authority [W-BOOT] [W-COORD].

## 2.2. Что уже существует как semantic UI, но пока не как полноценный сервис

| Область | CURRENT | В чём ограничение |
|---|---|---|
| Scenario chat | semantic projector и Qt widgets | привязан к `ScenarioRunCase`, нет общей Thread/Work authority |
| Events | kinds для запусков, системы и фона | нет общего durable sequence/subscription |
| Artifacts | records с path/kind/case/operation/author | нет надёжной ArtifactRef/catalog/materialization модели |
| Logs | app log + operation log + связь с case | ещё не единый structured diagnostics API |
| History | пять JSON-проекций | запись/восстановление не транзакционные; нет общей node authority |
| Background | registry, in-memory enabled/status/UI | нет scheduler/worker |
| Presence | локальные участники и авторы cases | нет network-wide realtime presence |
| Assignments | локальные записи, автоматический follow-up | нет remote delivery/ack/ACL и независимого lifecycle |
| Preferences | один user config | смешаны settings, layout, recents, drafts |
| Explorer | provider abstraction + local FS implementation | нет server-backed FileRef/ArtifactRef navigation |
| AI actor | словарь actor kind, metadata | нет AI executor/authorization flow |

Эти каркасы можно сохранять **на уровне идей и UX**, но до реального backend надо либо честно маркировать их ограниченность, либо убрать из основного позиционирования. Особенно нежелательна возможность «включить фон» без реально действующего scheduler.

## 2.3. Текущий Settings и visual layer

**[CURRENT]** Dialog содержит вкладки «Пользовательские», «Рабочие», «Системные». Пользователь может задавать открытие inspector, стартовый режим и стартовую вкладку; рабочие/системные вкладки преимущественно показывают сведения о runtime. В `AppUserConfig` одновременно лежат окно, навигация, фильтр чата, remembered scenario и значения форм. Цветовая система зафиксирована в Qt styles/resources как текущие hardcoded tokens/правила, без зрелого общего token compiler [W-SET] [W-CONFIG] [B-VISUAL].

## 2.4. AppDock: действительный и будущий внешний контур

**[CURRENT / DOCUMENTED INTENT]** По product baseline [A] AppDock отвечает за упаковку/установку, управляемую среду, узел, запуск, preflight, состояние, platform health, результаты как platform handoff, восстановление и будущие host/remote способы подключения. У `stratbox-windows` уже есть manifest, strict activation consumer, managed roots, session/health/runtime projections. Это не означает, что в Strategy Box сегодня реализованы remote execution, Android attachment или полноценный web server.

**[CONSOLIDATED]** Strategy Box owner отвечает за смысл Work, Jobs, предметные разрешения, user-facing app state и presentation projections. AppDock остаётся внешним platform/lifecycle owner. Surface adapter показывает платформенное состояние, но не дублирует его truth.

## 2.5. Не выдавать за CURRENT

Не существуют как подтверждённые функции текущего Windows baseline: долговечный `Thread/Work` с текстовыми сообщениями и несколькими Run, node-wide JobManager, remote execution, resumption после потери UI, shared per-user read state, полнофункциональная task automation, готовый web client, готовый Android client, пользовательский multi-node web server, production AI actor. Их описания ниже — проектные.

---

# 3. Семантическая модель поверхностей: что именно переносить

## 3.1. Три уровня между truth и pixels

```text
Authoritative application/domain state
    │ immutable query snapshot + revision / cursor
    ▼
Canonical product projection (semantic view models)
    │ view capabilities + permitted semantic actions
    ▼
Platform adapter (navigation, input, dialogs, local integration)
    │ native presentation components + adaptive layout
    ▼
Rendered surface
```

**Первый уровень** отвечает, *что истинно и доступно*; **второй** — *что текущему пользователю полезно увидеть и сделать*; **третий** — *как это отобразить на конкретном устройстве*. Совпадение всех трёх уровней в одном Qt widget допустимо для прототипа, но препятствует настоящему Web/Android reuse.

## 3.2. Минимальные переносимые сущности presentation

| Объект | Нейтральная семантика | Что разрешено адаптеру |
|---|---|---|
| `SurfaceContext` | principal/node/session, device capabilities, locale, policy, connection status | OS capabilities and layout |
| `NavigationDestination` | `work`, `explorer`, `scenarios`, `runs`, deep-link identity | rail, tabs, drawer, bottom navigation |
| `SelectionRef` | тип/ID/версия выбранного сущностного объекта | side inspector vs pushed details |
| `ThreadView` | сообщения, связанные Works/Artifacts, участники | timeline direction/layout/virtualization |
| `WorkView` | цель, статус, pending decisions, связанные Runs/Outputs | cards, dedicated detail, timeline anchors |
| `RunView` | status, steps, progress, actions, artifacts, diagnostics | row/table, card, compact progress |
| `ScenarioView` | назначение, параметры, eligibility, expected outputs | list/detail, wizard, native form |
| `WorkspaceView` | scoped FileRefs, materializations, navigation and permitted actions | tree/table vs hierarchical mobile list |
| `ArtifactView` | ID, version, kind, lineage, preview/download capabilities | OS file associations/shares |
| `InspectorView` | typed panels for selected object | docked, floating, full-screen, bottom sheet |
| `NotificationView` | actionable information for principal | inbox, toast, native push |
| `ActionDescriptor` | exact action ID, availability, reasons, risk, confirmation/approval | menu/buttons/keyboard/swipe |
| `UIState` | selection, active filters, drafts, scroll/navigation position | local persistence and navigation stack |

**[TARGET-HYPOTHESIS]** Эти названия — предложенный переносимый surface vocabulary. Не следует создавать десяток классов, если несколько видов можно представить одним типизированным object projection. Порог материализации: отдельная идентичность, lifecycle, потребитель или проверяемый контракт.

## 3.3. Presentation *не владеет* данными и семантикой

Клиент может перевести status `waiting_for_approval` в понятный текст, сгруппировать по дню, скрыть низкоприоритетные шаги и адаптировать список к ширине экрана. Он **не вправе**:

- делать `unknown` визуально равным `failed` или `empty`;
- считать транспортный HTTP 200 доказательством успешного Work;
- подменять доказательность аналитической цифры своим цветом/словами;
- выводить авторизацию из скрытой кнопки;
- превращать progress animation в фиктивные 0–100%;
- считать `unread` общим полем события для всех пользователей;
- называть текущий path постоянной artifact identity.

## 3.4. Одинаковое смысловое ядро ≠ одинаковый экран

Windows может одновременно показывать дерево файлов, чат и inspector. Android compact показывает один контекст за раз и использует back stack. Web адаптируется от широкого монитора до узкого браузерного окна и защищает boundary загрузки файлов. Узкий клиент может показывать только «3 активных Run / 1 требует ответа» и разрешённую команду открытия подробностей.

Критерием эквивалентности является **одинаковый смысл разрешённых actions и одинаковый authoritative outcome**, а не pixel-perfect совпадение.

---

# 4. Product information architecture: один каталог направлений, разные входы

## 4.1. Четыре логические рабочие поверхности

| Направление | Пользовательский вопрос | Главный объект | Что не переносить в него |
|---|---|---|---|
| **Работа** | Над чем я работаю и к чему вернуться? | Thread → Work → decisions/context | всю очередь узла, сырой системный лог |
| **Проводник** | Какие исходные, рабочие и итоговые объекты мне доступны? | WorkspaceObject / Artifact | смысл завершения Work |
| **Сценарии** | Что система умеет делать и как запустить повторяемую задачу? | Scenario/Capability | собственное исполнение/отдельная job history |
| **Запуски** | Что сейчас исполняется, стоит в очереди или требует действия? | Run/Job | второй чат и отдельную семантику фона |

**[CONSOLIDATED]** Это лучше текущих шести равноправных режимов Windows. Оно совпадает с [B-UX] и последующей Work-centric онтологией [R02], [R04]. При этом «четыре направления» — не окончательная навигация: на большом desktop есть rail; на Android они могут выглядеть как 3–4 destination, bottom navigation или toolbar overflow; в узкой companion-поставке каталог сценариев может быть доступен только через поиск.

## 4.2. Главный экран не должен жёстко стартовать со «Сценария»

**[SUPERSEDED]** Правило `entry_view = scenario_chat` отражает исходную стадию продукта. После появления долгого общения и Work объектом возвращения становится текущий **Thread** или актуальная **Работа**. Сценарий служит способом её исполнения, а не единственным корнем продукта.

**[TARGET-HYPOTHESIS]** Default home: «Работа» с последними Threads, pinned items, нуждающимися в ответе Works и компактным индикатором выполняющихся Jobs. Если пользователь возвращается в активный контекст, восстанавливается прежняя открытая работа, если права и актуальность snapshot позволяют. Первый старт получает empty state с явным «Создать работу» и «Запустить сценарий».

## 4.3. Верхнеуровневая и контекстная навигация

```
WORK              EXPLORER         SCENARIOS         RUNS
  ├─ Thread list    ├─ scopes        ├─ catalog         ├─ active / queue
  ├─ Thread detail  ├─ folders       ├─ favorites       ├─ awaiting action
  ├─ Work detail    ├─ search        ├─ scenario detail ├─ recent / history
  ├─ Work links     ├─ artifact lib  ├─ presets         ├─ automations*
  └─ decisions      └─ lineage       └─ run draft       └─ problems/logs

* Automation management only once actual automation exists; it is not another engine.
```

### Важные правила IA

- Каскад — вид композиции сценария/схемы, а не обязательный отдельный корневой режим.
- Background/scheduled — способ запуска и атрибут Job/Automation, а не самостоятельная сущность «раздел Фоновые».
- Участник показывается возле контекста (чат, Work, Run, узел); отдельная справочная страница допускается позднее, если есть самостоятельный administrative use case.
- Поручения и approvals видны как actionable cards в Work и как глобальный фильтр «Требуют ответа»; отдельный task center возможен при объёме.
- «Узел», «Диагностика», «О программе», настройки — служебный контур, обычно в account/system menu.
- AI становится участником и инициатором действия через те же объекты Work/Scenario/Run; отдельный корневой «AI-мир» необоснован.

## 4.4. Глобальный поиск: единый вход, разные источники индекса

**[TARGET-HYPOTHESIS]** Поиск нужен сквозной: Threads, Works, Scenarios, Runs, Files/Artifacts, в будущем dataset/catalog items. UI предоставляет один search overlay/command palette с раздельными типами результата, понятным объектом и правами на действие. **Индексация** принадлежит application/domain services и файловому provider, а не локальному widget; индекс должен учитывать ACL и stale data. Пустой результат отличается от offline/permission/index-not-ready.

**[UNKNOWN]** Единая физическая полнотекстовая БД, поисковый язык, ranker и объём индексируемого содержимого файлов не исследованы нагрузочным пилотом. Первый поиск можно сделать несколькими авторизованными provider queries.

## 4.5. Контекстное меню и command palette — два входа в одни действия

Например, «Открыть исходный Run» может быть доступно из Artifact inspector, из командной палитры и через deep link, но это **один action ID**, прошедший одну проверку полномочий. Меню не должно повторно кодировать бизнес-логику или правила безопасного удаления.

---

# 5. Work и Thread: целевая разговорная рабочая поверхность

## 5.1. Структура контекста

```text
Thread (общение, контекст, участники)
 ├─ Message by human
 ├─ Work A (цель, обязательства, acceptance)
 │   ├─ Run A1 (scenario/scheme)
 │   ├─ Run A2 (повтор/продолжение)
 │   ├─ Artifact X
 │   └─ Assignment / Approval
 ├─ Message by AI / human
 ├─ Work B (иная цель в той же беседе)
 └─ Pinned artifact / attachment / reference
```

**[CONSOLIDATED]** Thread может содержать несколько Work, Work — несколько Runs; Thread остаётся контекстом, а Work — самостоятельной долговечной задачей. Одну Work можно открыть по ссылке даже после архивирования исходного Thread, если права сохраняются. Сообщение не обязано быть запуском; Run не обязан иметь отправленное текстовое сообщение [R02] [R04] [B-AI-UI].

## 5.2. Timeline как проекция, а не поток всего подряд

В ленту попадают **пользовательски значимые** элементы:

- human/AI message;
- открытие или принятие Work;
- предложение действия и решение пользователя;
- Run card с реальным статусом;
- уведомление о существенном блокирующем событии;
- артефакт с lineage;
- просьба о проверке/подтверждении;
- формальное завершение/принятие Work.

Не выводить в timeline каждый heartbeat, retry, log line, polling event или внутренний state mutation. Эти данные принадлежат progress panel, technical log и диагностике. Лента должна оставаться читаемой спустя месяцы.

## 5.3. Composer: свободное сообщение и структурированное действие

**[TARGET-HYPOTHESIS]** Один компактный composer: ввод текста, прикрепление File/Artifact, выбор сценария, упоминание участника, запрос к AI (при наличии). Выбор сценария вставляет **структурированный RunDraft**, который может открыть форму параметров; raw prose остаётся сообщением. Пользователь видит границу:

```text
«Проанализируй данные ...»      → message / proposal / Work intent
[Scenario: Escrow history]     → structured run draft
[Run]                          → авторизованная execution command
```

Наличие AI-варианта не означает, что любое сообщение автоматически запускает вычисление. UI обязан различать *намерение, рекомендацию, план, подтверждение и реально принятый запуск*.

## 5.4. Предложение AI — не совершённое действие

```text
Предложение
Сценарий: Обновление источников
Параметры: период, охват, выходной формат
Эффекты: сеть, запись новых файлов
Проверка: может потребоваться подтверждение
[Посмотреть план] [Запустить] [Отклонить]
```

Система отображает только разрешённые для данного principal действия. Approval получает durable identity/revision; изменение плана после approval требует повторного решения, если меняет эффект/объект. После запуска появляется обычная Run card — исполнитель AI получает ровно те же observability/recovery semantics, что человек [R04] [R05].

## 5.5. Параллельная работа

Один Thread может иметь несколько активных Works; один Work может иметь независимые Runs/Jobs. Поэтому **глобальная блокировка composer и «один busy на весь UI» — переходное ограничение**, которое следует убрать с переходом к node runtime. Busy state относится к конкретной опасной или конкурирующей операции, а не к целому приложению.

## 5.6. Возвращение к работе

У Thread/Work нужны стабильные deep links, pinned state, last meaningful activity, возможно archived state. Пользователь после входа с другого устройства получает разрешённый серверный контекст, курсор последних событий и актуальную карточку выполнения. Draft личного текста может остаться на исходном устройстве, если cross-device drafts не реализованы. UI обязан ясно отделять restored server truth от local unsent draft.

## 5.7. Предлагаемый desktop layout

```text
┌────────────┬──────────────────┬────────────────────────────────┬───────────────────┐
│ Product    │ Threads          │ Current Thread / Work          │ Context Inspector │
│ rail       │ Search/Pinned    │ Messages / work/run cards       │ Work / Run /      │
│            │ Recent           │                                 │ Artifacts /       │
│            │                 │ Composer                        │ Participants      │
└────────────┴──────────────────┴────────────────────────────────┴───────────────────┘
       нижняя раскрываемая diagnostic panel только по запросу/состоянию
```

Не каждый экран требует четырёх одновременно видимых колонок: на средней ширине скрывается вторичный список или inspector; на узкой — один detail и возвращаемая навигация.

---

# 6. Проводник и Artifact Library: две семантики в одной навигации

## 6.1. Не смешивать физический файл и managed Artifact

**WorkspaceObject/FileRef** — объект изменяемого файлового пространства, доступный через provider/ACL. **Artifact/ArtifactRef** — устойчивый итог с manifest, происхождением и возможными несколькими materializations. Артефакт может быть представлен файлом, папкой, таблицей, preview или ссылкой. Наличие одного файла в `output/` не доказывает, что он зафиксирован как managed artifact [R03].

## 6.2. Навигационные области

**[TARGET-HYPOTHESIS]** В Проводнике могут появиться:

- «Общее пространство узла» (разрешённые shared data);
- «Мои файлы» (personal scope);
- «Результаты» или «Библиотека артефактов» (managed artifact index);
- «Для текущей работы» (Working Set, ссылки из Work);
- «Исходные данные» (если есть соответствующий domain/provider);
- временные run-owned areas показываются только через относящиеся к ним Runs/Artifacts, пока нет обоснованного отдельного UI.

`system` area не становится обычной пользовательской папкой. Это предотвращает подмену «Проводника» техническим файловым менеджером runtime.

## 6.3. Desktop и web/mobile различаются

- **Windows:** tree, breadcrumb, list/details, multi-select, keyboard navigation, drag/drop только для поддерживаемых эффектов, открыть файл локальным приложением.
- **Web:** server-backed pagination, upload/download через авторизованные endpoints, preview по capabilities, browser permissions, без доверия прямым физическим server paths.
- **Android:** scoped picker, иерархический список/поиск, системные `share/open with`, безопасный ограниченный кеш, короткие действия; сложные bulk-операции вторичны.

## 6.4. Identity, path и action

```text
FileRef:       (scope, object_id, revision?, display_path)
ArtifactRef:   (artifact_id, artifact_version, materialization_id?)
```

Сервер проверяет реальный path/root и access policy при каждом действии. Перемещение файла меняет location, но не обязано менять user-facing identity managed artifact. Сам raw path становится display/diagnostic attribute, не универсальным API.

## 6.5. Отображение lineage и provenance

Artifact inspector должен по возможности отвечать: **что это**, **откуда**, **какой Run создал**, **какие исходные/версии данных использованы**, **какой стиль/metadata context применён**, **актуален ли результат**, **можно ли доверять утверждению**. Свернутый consumer-view не должен заваливать пользователя evidence-техническими деталями, но должен корректно передавать warning/UNKNOWN [R03].

## 6.6. Destructive file actions

Удаление/перенос/cleanup выводится как action с правами, областью влияния и при необходимости dry-run/plan. UI не определяет успешность по исчезновению строки: canonical outcome возвращает action service. Если есть partial/unknown effect, это отдельный экран восстановления/повторной проверки [B-UX] [R04].

---

# 7. Каталог сценариев и capability discovery

## 7.1. Сценарий — потребительский продуктовый use case

UI говорит о назначении («История счетов эскроу»), ожидаемом результате, требованиях и параметрах. Machine-readable `OperationDefinition` и `Scheme` остаются ниже; техническая функция не обязана иметь отдельную карточку. Автоматическая обёртка каждой Operation в Scenario как **универсальное целевое правило** вытеснена поздней моделью: curated scenario допускает несколько steps и может ссылаться на один/несколько capabilities [R02].

## 7.2. Один каталог, несколько типов композиции

Atomic и composite/cascade относятся к одному семантическому каталогу. При достаточном масштабе отдельный filter «Каскады», grouping, favorites, recent, tags; **отдельная top-level кнопка только ради типа сценария** не нужна. Machine Scheme может быть скрыта от человека или представлена через упрощённый сценарий.

## 7.3. Форма параметров — platform-neutral schema

Поле должно описывать: stable ID, тип/единицу/формат, label/help, required, defaults, диапазон/enum, eligibility, sensitive flag, validation code, зависимости полей, input/output reference picker, предупреждение о side effects. Renderer выбирает native component (Qt/date picker/browser select/Android dialog) и accessibility semantics. `secret`-значения вводятся через отдельный разрешённый flow, а не бесконтрольно сохраняются в drafts.

**Важное различие:** default ≠ remembered draft ≠ reusable preset ≠ effective run snapshot ≠ policy override. Итог перед запуском показывает **что именно будет выполнено сейчас**, включая значения, принятые по умолчанию и принудительные managed constraints [B-SET] [R04].

## 7.4. Состояния пригодности

`available`, `unavailable`, `needs_configuration`, `needs_data`, `requires_approval`, `blocked_by_policy`, `unknown` — разные причины. Не использовать одну disabled-кнопку без пояснения. При отсутствии сети старый кешированный catalog не становится доказательством текущей доступности.

## 7.5. Параметры и UX сложных сценариев

Basic параметры показываются сразу; Advanced раскрываются по необходимости. Высокорисковый шаг имеет отдельную confirmation с эффектами и выбранными объектами; сложный многошаговый план показывается вертикальным списком с важнейшими зависимостями, DAG — дополнительное техническое представление по запросу. Пресет хранит параметры, а не копию всей схемы.

---

# 8. Запуски — самостоятельная operational projection

## 8.1. Runs control plane

Запуски показывают всю разрешённую область текущего узла: свои/командные/активные, очередь, ожидающие пользователя, ошибки, completed, автоматизации при их наличии. Один и тот же Run связан с Work, исходным Trigger/Automation, executor, artifacts и диагностикой.

```text
Сценарий / работа | Статус | Шаг | Инициатор | Режим | Начало | Результат
```

Рекомендуемая сортировка: требующие действия и активные выше; затем актуальные последние. В компактной ширине таблица превращается в список с теми же identity/действиями.

## 8.2. Run card и Job detail — разные масштабы

Карточка в чате отвечает: «что с моей работой?». Run detail отвечает: «какие Jobs/Steps выполнялись, какой outcome, что проверить и где результат?». При технически сложных планах inspector или отдельная страница может раскрыть `Job → OperationRun → Attempt`, но обычному пользователю не нужно видеть эти слова везде.

## 8.3. Прогресс

- Реальные этапы и натуральные единицы (`3/12 файлов`, `обработано 200 МБ`) предпочтительнее выдуманного процента.
- `progress=100%` соответствует проверенному завершению соответствующей стадии; не равняется acceptance Work.
- `queued`, `waiting_user`, `running`, `paused`, `reconciling`, `succeeded`, `partial`, `failed`, `cancelled`, `outcome_unknown` различаются.
- Сбой соединения клиента отображается как `connection_lost/stale`, а не как `job_failed`.

## 8.4. Actions на запуске

`Cancel` показывается только при поддержке cooperative cancellation и права. `Retry` — только при известной policy/effect state; при `outcome_unknown` UI предлагает «Проверить состояние» вместо слепого повторения. `Open artifact`, `Inspect logs`, `Assign review`, `Approve` имеют отдельную авторизацию и причины недоступности [R04].

## 8.5. Background execution и automation

**[CONSOLIDATED]** Фоновость — режим исполнения; **AutomationSpec** — persistent definition trigger/policy; **Job** — конкретный результат срабатывания. «Включено» у автоматизации не равно «Сейчас выполняется». Задание продолжает жить после закрытия клиента, пока узловой runtime работает. Отключение правила не обязано отменять уже принятый Job.

## 8.6. Не создавать дубли истории

Run list и Thread timeline имеют ссылки на один `run_id`, одни artifacts и одни authoritative events. Удаление/скрытие карточки в thread-view не стирает execution history. Фильтры «В работе», «Ошибки», «Запланировано» — projections, а не новые backend stores.

---

# 9. Контекстный Inspector, search, preview и technical depth

## 9.1. Inspector следует выбранной семантической сущности

| Выделен объект | Основные поля | Действия |
|---|---|---|
| Thread | участники, связанные Works, pinned references | share, archive, reopen |
| Work | цель, статус/принятие, Runs, требования, output summary | продолжить, назначить, принять |
| Run | шаги, параметры, outcome, duration, artifacts, diagnostics | открыть, отменить*, проверить*, повторить* |
| Scenario | назначение, input schema, preset, expected outputs, last runs | запустить / открыть план |
| File | путь в scope, тип, размер, provenance if available | open/reveal/copy/preview |
| Artifact | version, style, source/Run lineage, materializations | preview/download/open origin |
| Node | platform health, workspace binding, access status | diagnostics/open platform tool |

`*` — лишь если backend/permission/effect semantics допускают действие.

## 9.2. Не привязывать Inspector к правой колонке

Действующий Qt right panel — удобная реализация desktop. Semantic `InspectorView` должна работать также как web drawer, mobile detail screen/bottom sheet, narrow read-only summary. Поля и действия могут сокращаться по плотности, но смысл сохраняется.

## 9.3. Raw logs: отдельная техническая глубина

Трёхступенчатый подход: (1) user summary в карточке; (2) список steps/warnings в inspector; (3) виртуализированная log/problem panel с фильтрами/поиском. На широком desktop лог может раскрываться снизу; в web — отдельная route/panel; Android — облегчённый redacted просмотр или external support flow. Сырые логи нельзя отправлять всем участникам чата и объявлять источником истинного `Job.status` [B-OBS].

## 9.4. Preview — разрешённая проекция, а не открытый файловый endpoint

Для изображений, PDF, Excel/csv previews сервер должен отдавать безопасно обработанный контент с scope/size/ACL/format ограничениями. Client не получит физический server path. Web download и Android share должны проверяться на момент действия, а не только при первоначальном рендере кнопки.

---

# 10. Уведомления, presence, поручения и approvals

## 10.1. Event ≠ Notification ≠ Problem

- `DomainEvent` — зафиксированное изменение работы/исполнения.
- `Notification` — адресная, человеко-ориентированная доставка или inbox projection.
- `Problem/Condition` — состояние неисправности или ограничения, имеющее owner и политику эскалации.
- `RawLog` — диагностическое evidence.

UI не вправе слить их в красную ленту событий. AppDock отвечает за проблемы platform/node уровня, Strategy Box — за предметные проблемы и user-facing действия. При необходимости возможен bridge с sanitization и correlation, без дублирования владельца причины.

## 10.2. Значимое событие должно доставляться адресно

Правило уведомления зависит от severity, ownership, task relation, assignee, user preferences, delivery channel и ACL. Примеры: завершение своего фона, блокирующее согласование, поручение коллеге, переход на ограниченный режим узла. Нельзя массово транслировать чужие секретные ошибки. Нескольким участникам можно показать агрегированное состояние общей проблемы без исходного traceback.

## 10.3. Presence — статус с TTL, а не список «навсегда online»

Surface может показывать «в сети», «недавно был», число active sessions, роль в Work. Authoritative input поступает из управляемых sessions/heartbeat; presence вычисляется как ограниченная по времени проекция. Историческое авторство Run не доказывает текущий online status [B-MULTI] [R05].

## 10.4. Assignments и approvals

Assignment — product object со своим состоянием; Approval — отдельный разрешённый decision. Они видны в Work, в global inbox и на узких поверхностях как bounded actions. Для мобильного approval нужен защищённый подтверждающий экран с effect summary и server-side revalidation; пуш-уведомление само по себе не должно осуществлять destructive command.

## 10.5. Badge budget

Значки с числом/цветом применяются по **одной доминирующей причине**: реально непрочитанные адресные уведомления, pending approvals или ошибки, требующие внимания. Не делать badge на каждом пункте навигации без функциональной пользы; предупреждение о нескольких десятках running jobs лучше агрегировать.

---
# 11. Settings: маленький слой предпочтений, а не зеркало состояния

## 11.1. Пять категорий вместо одной общей «настройки»

**[CONSOLIDATED]** Из [B-SET], [R02], [R05] следует строгая классификация:

| Категория | Пример | Владелец | User-facing Settings? |
|---|---|---|---|
| `UserSettings` | тема, акцент, default artifact style, автор metadata, уведомления | application settings/user scope | да, если реально используется |
| `SurfaceState` | размер окна, rail, inspector, scroll, выбранный route | клиентское устройство | нет; автоматическое восстановление |
| `RecentState / DraftState` | недописанный текст, значения формы, выбранный сценарий | клиент/пользователь; scope определяется отдельно | не отдельная общая настройка |
| `RunParameters` | период, источник, формат, refresh, target | конкретный Run/Scenario | в форме запуска/пресете |
| `ManagedPolicy / Deployment` | обновления, node binding, разрешения, принудительные ограничения | AppDock / application policy owner согласно ответственности | только отображение effective policy с объяснением |

Это исправляет текущую смесь `AppUserConfig`. Даже если настройки, черновики и layout физически помещаются в один небольшой файл, **их семантика и методы обновления должны быть разделены**.

## 11.2. Минимальный целевой Settings

```text
Настройки
  Внешний вид
    Тема: Системная / Светлая / Тёмная
    Акцент: Strategy Box / Системный / Пользовательский

  Артефакты и отчёты
    Набор оформления по умолчанию
    Отображаемый автор файла (дефолт Strategy Box)

  Расширения
    Доступные нейтральные capabilities / providers
    Совместимость и effective state
    Разрешённая конфигурация и диагностика

  Уведомления                 [только после реализации delivery]
    Собственные результаты / ошибки
    Поручения / согласования
    Важные общие состояния узла
```

Пункт Reduced Motion в первую очередь следует системной настройке accessibility; при доказанной потребности может иметь override. Density можно добавить как двухуровневое desktop preference, если стандартная OS density не удовлетворяет целевые таблицы. Font scaling — через платформу/доступность, без произвольной пользовательской замены shell font.

## 11.3. Что удалить или переместить из текущего Settings

- «Открывать правую панель при запуске», «Стартовый режим», «Стартовая вкладка»: автоматическое восстановление SurfaceState.
- Размеры и ширины панелей: локальный layout state.
- Последний сценарий/фильтр чата/значения форм: recents/drafts.
- Пути, Data root, node/session/host: Проводник или Node/Diagnostics view.
- Запуск диагностики: команда service view.
- Глобальный «уровень логирования» без определённого user-facing use case: техническая или managed policy.
- Включение background: операционная команда Automation, а не preference.
- Обновление продукта, installation policy: внешний lifecycle owner.

## 11.4. Extension visibility не равна extension authority

UI может показывать `installed`, `available`, `active`, `blocked`, `incompatible`, `requires_configuration`, `unhealthy`. **Установленное расширение не обязательно активировано**. Кнопка «Включить» появляется лишь если конкретный neutral capability contract допускает пользовательскую активацию; возможна передача в AppDock или в административный интерфейс. Недопустимо обещать произвольную загрузку новых Qt widgets/JS/CSS из пакетов как стандартный plugin API.

## 11.5. ArtifactStyleSet и InterfaceTheme принципиально различны

- `InterfaceTheme` управляет shell и компонентами Windows/Web/Android.
- `ArtifactStyleSet` управляет визуальными правилами создаваемых XLSX/DOCX/PPTX/PDF и версии набора.
- `ArtifactMetadata` включает display author/creator, title, source/provenance и др.; фактический actor/run фиксируются независимо от поля `creator`.

**[TARGET-HYPOTHESIS]** При обычном запуске разрешается **один effective ArtifactStyleSet**, с внутренними format projections; не стоит независимо собирать несогласованную смесь шрифтов и цветов для каждого формата. Это выбор presentation policy артефакта, а не смена интерфейсной темы [B-STYLE], [R03].

---

# 12. Design system: единый смысл, разные технические носители

## 12.1. Целевая визуальная доктрина

**[CONSOLIDATED]** Исследования сходятся на спокойном, плотном, профессиональном инструменте («Calm Operational Premium»). Он не должен становиться dashboard с десятками декоративных карточек или виртуальным мессенджером без аналитической глубины. Принципы: содержание выше украшения, минимум насыщенного цвета, ясная иерархия, длинные рабочие сессии, читаемость русскоязычных данных, контролируемые состояния.

## 12.2. Token layers

```text
brand primitives (scale/colors/font families)
          ↓
semantic tokens (text / surface / border / accent / status)
          ↓
component tokens (button / input / pane / row / chat card)
          ↓
platform renderer (Qt/QSS | CSS | Android/other)
```

Код бизнес-домена и schema операций не должен зависеть от `#316BE5`, `QColor` или web CSS class. Смысловые роли (`status.error`, `text.muted`, `surface.selected`) остаются стабильными, а platform renderer вычисляет конкретные ресурсы для светлой, тёмной и повышенной контрастности.

**Пример кандидата semantic token set (не утверждённый API):**

```yaml
surface: [canvas, primary, secondary, elevated, hover, selected]
text: [primary, secondary, muted, disabled, on_accent]
border: [subtle, default, strong, focus]
accent: [default, hover, pressed, soft, focus]
status: [success, warning, error, info, running, unknown]
space: [4, 8, 12, 16, 24, 32, 48]
radius: [small, medium, large]
typography: [body, label, caption, heading, code, data]
motion: [instant, xfast, fast, normal, slow, emphasis]
```

## 12.3. Цвет и бренд

Исследование [B-VISUAL] предлагает приглушённый синий акцент (`Strategy Blue`, ориентировочно `#316BE5` для light) при сохранении насыщенного оригинального логотипа для icon/splash. Нейтральный canvas преобладает над яркой палитрой. **Цвет статуса не является brand color:** ошибка, предупреждение, неизвестное состояние, выбор и running имеют разные смысловые роли. Все такие значения — **дизайн-кандидаты**, а не факт утверждённых бренд-стандартов.

## 12.4. Типографика, плотность, макет

Windows research использует около 13 px основного текста, Segoe UI Variable/Segoe UI fallback, сетку 4 px и стандартные отступы 8/12/16/24/32. Это разумная **desktop baseline hypothesis**, но Android/Web не должны наследовать буквальные размеры: поддержка системного text scaling, browser zoom и touch target обязательна. Две density variants `comfortable/compact` допустимы на desktop при проверенной потребности; mobile density задаётся собственными ergonomics.

## 12.5. Light / dark / high contrast

- По умолчанию System, с принудительно выбираемыми Light/Dark.
- High contrast и OS accessibility preference выше эстетического «пользовательского accent».
- Все токены проходят контрастные проверки в конкретном компоненте, не только таблицу hex-кодов.
- Ширина line, focus outline, text selection и disabled состояний проверяется независимо от цвета фона.
- Смена темы не должна менять права, порядок бизнес-действий и семантику состояния.

## 12.6. Где жить design tokens

**[CONSOLIDATED]** Нужен общий дизайн-словарь/контракт. **[UNKNOWN]** Отдельный `stratbox-design` репозиторий не доказан: пока один основной desktop consumer, логично расположить source tokens рядом с application/shared presentation contracts с независимой платформенной сборкой. Отдельная физическая поставка оправдана при нескольких независимых consumers, отдельном release cadence, тестовом контракте и стабильных exports. Нельзя физически выделять репозиторий только ради красивого дерева.

---

# 13. Motion как визуализация причинной связи

## 13.1. Motion — результат состояния, а не источник состояния

```text
authoritative state change
      ↓
new semantic view model
      ↓
MotionRole / transition policy
      ↓
platform-native animation or reduced-motion alternative
```

Анимация объясняет принятие действия, изменение контекста, состояние процесса, появление результата. Она не создаёт состояние Job и не блокирует операцию до завершения красивого перехода [B-MOTION].

## 13.2. Словарь ролей

- `feedback.press`: мгновенный отклик на действие;
- `navigation.context_change`: небольшое сохранение continuity;
- `inspector.open/close`: мягкий сдвиг/opacity;
- `work.new_item`: появление смысловой карточки;
- `run.progress`: спокoйная индикация реальной работы;
- `artifact.available`: короткое highlight settle;
- `error.attention`: ограниченное подчёркивание фактической проблемы;
- `list.reorder`: restrained move только при осмысленном изменении.

**[TARGET-HYPOTHESIS]** Семантические токены длительности из [B-MOTION]: 0 / 80 / 160 / 240 / 320 / 480 мс; типовые перемещения 4–12 px. Это guideline, подлежащее калибровке на реальном desktop и Android. Не закреплять значения как «межплатформенные пиксели/миллисекунды без права адаптации».

## 13.3. Attention budget

При 18 активных Jobs на экране нельзя заставить 18 карточек постоянно мерцать. Постоянный motion только там, где действительно есть ongoing процесс; для групп — агрегированный статус. `success`, `error`, `unread` после краткой реакции остаются статическими. User может продолжать взаимодействие во время transition.

## 13.4. Reduced Motion и accessibility

Respect system `Reduced Motion`: пространственные переходы сокращаются/заменяются статикой или fade, постоянные shimmer отключаются. Семантические статусы сохраняются текстом/иконкой. W3C WCAG 2.2 2.3.3 (`Animation from Interactions`) описывает отключение несущественного motion по предпочтению пользователя; официальный guidance допускает `prefers-reduced-motion` для web [X-W3C].

## 13.5. Не смешивать motion с фактическим прогрессом

Реальное вычисление не становится завершённым из-за того, что progress bar доехал до края. UI обновляется по typed events и terminal outcome. При отсутствии честного denominator используем indeterminate state/stage label.

---

# 14. Платформенная архитектура Windows

## 14.1. Что сохранить из действующего приложения

**[CONSOLIDATED]** Сохраняем: трёхзонную композицию, глубокий inspector, scenario/run cards, workspace explorer, application-level models, декларативные forms, Qt как зрелую Windows presentation technology, AppDock-managed activation, локальную интеграцию открытия файлов. Все эти элементы полезны **как surface**, а не как ownership исполнения.

## 14.2. Что необходимо отделить до масштабирования

**[TARGET-HYPOTHESIS]** `runtime.bootstrap` не должен импортировать `presentation.qt_desktop.*`; `ScenarioCoordinator` становится Qt bridge над frontend-neutral execution client/command service. История, authority и Job scheduler уходят из lifetime окна. UI получает view models, отправляет команды и подписывается на изменения. Локальный процесс может содержать in-process adapter в dev/embedded варианте, но публичные семантические контракты остаются одинаковыми.

```text
Qt Shell / Qt ViewAdapters
      │                ▲
      │ actions        │ typed projections
      ▼                │
Surface Application Client
      │ command/query/subscription
      ▼
Strategy Box application authority
      │
stratbox operation execution (headless)
```

## 14.3. Desktop window behavior

- Desktop rail с компактными четырьмя logical destinations.
- Secondary list — Threads, Scenario filters, Workspace folders или Runs, в зависимости от destination.
- Центральная основная поверхность остаётся главным фокусом.
- Right inspector — опциональная вторичная глубина.
- Bottom technical panel — по запросу, без постоянного отъёма вертикального пространства.
- Размеры, widths, последний selection/filter автоматически восстанавливаются с осторожностью по отношению к stale/denied objects.

## 14.4. Keyboard и productivity

Потребуются: command palette, поиск, navigation назад/вперёд, focus management, hotkeys без конфликта с OS/Qt, tab/focus order, usable таблицы, virtualized long lists. Сочетания клавиш привязываются к **semantic action IDs**, а не к методам widgets. Пользовательский remapping допустим позже при реальном спросе.

## 14.5. Локальный режим без сервера — только как архитектурный профиль

Если требуется offline/simple desktop, можно запускать тот же application authority как локальный lightweight service/встроенный process. Однако если обещаны долговечные Jobs, фон и несколько клиентов, authority должна переживать закрытие окна. **[UNKNOWN]** Какая минимальная поставка используется в раннем Windows release: embedded runtime, local host service или два SKU. Наличие выбора не оправдывает разные схемы Work/Run.

---

# 15. Web surface: полноценный клиент, не картинка Windows

## 15.1. Базовая модель

**[TARGET-HYPOTHESIS]** `stratbox-web` — browser client поверх headless Strategy Box application authority. В исследовании [B-WEB] наиболее естественный транспорт: authenticated REST/HTTP команды и queries + Server-Sent Events для обновлений server→client; WebSocket добавлять, если появится настоящий двусторонний низколатентный use case. MDN подтверждает семантику SSE `id`/`retry` и восстановления потока [X-SSE].

## 15.2. Snapshot + stream

1. Клиент делает разрешённый query `snapshot` с revision/cursor.
2. Рисует последнее подтверждённое состояние.
3. Подписывается на последующие события, обрабатывает order/deduplication.
4. При пропуске/expired cursor получает новый snapshot.
5. При offline показывает `stale` и отдельно cached timestamp.
6. Мутации идут отдельными авторизованными commands с `idempotency_key`/`expected_revision`.

**Граница:** это контрактный кандидат из [R05], а не утверждение о существующем endpoint.

## 15.3. Адаптивная геометрия

- Wide: left navigation + list + center + right inspector.
- Medium: один secondary panel видим по выбору, inspector выезжает.
- Narrow: root destinations через compact navigation, list→detail вместо постоянных колонок, forms/inspector в sheets/routes.
- Browser zoom и изменение окна не должны терять выбранный Work или Run и нарушать keyboard focus.

## 15.4. Browser security и локальные файлы

Web клиент не видит файловую систему host напрямую, `download` идёт через авторизованный endpoint и short-lived binding; upload имеет проверки размера/типа/quota/scan policy. Нельзя публиковать workspace как static webroot. При authentication browser state, CSRF, secure cookies, CSP, token storage применяются server-side security owner; front-end не выбирает свою authority. Веб-таблица может открывать XLSX preview, но не обязана давать прямой редактируемый доступ к исходному файлу.

## 15.5. Web является пригодным без AI

Отсутствие когнитивного исполнителя не ломает интерфейс: пользователь может выбрать Scenario, открыть Work, просмотреть Runs и артефакты. AI-компоненты добавляют новый допустимый actor/entry point, но не определяют возможность пользоваться продуктом.

---

# 16. Android: общий смысл при mobile-first взаимодействии

## 16.1. Что переносить из Windows буквально, а что — по контракту

**Копировать смысл / семантические contracts:** Thread/Work/Run/Artifact refs, статусные модели, validation errors, forms descriptors, catalog, notifications, action availability, permission decisions, semantic design tokens, motion roles.

**Реализовать заново как mobile adaptation:** navigation stack, touch targets, bottom sheets, gesture semantics, virtualized lists, Android permission/intent handling, file picker, share sheet, OS notifications, biometric/re-auth where required, background/connectivity restrictions, layout and font scaling.

**Не переносить:** Qt Widgets class hierarchy, Windows paths/Explorer action, desktop QSS, raw local DB truth, QThread job ownership, абсолютные пиксельные размеры desktop panes.

## 16.2. Предпочтительный первый Android scope

**[TARGET-HYPOTHESIS]** Начать как **companion с полноценным product truth**, а не копию desktop:

1. Работы/Threads, status и короткая timeline.
2. Активные и ожидающие решения Runs.
3. Подтверждение/отклонение разрешённых actions.
4. Артефакты: preview/download/share по ACL.
5. Короткие parameter forms и запуск безопасных сценариев.
6. Push/in-app уведомления о важных пользовательских состояниях.
7. Состояние узла/подключения, diagnostics summary.

Полноценный Explorer, сложные bulk file operations, graph workflow editor, большие лог-панели и тяжёлое offline editing — **возможные расширения**, а не обязательный первый релиз. Android должен управлять удалённой/узловой работой, а тяжёлый расчёт может оставаться на host.

## 16.3. Адаптация к размеру окна, не к названию устройства

Android Developers рассматривает адаптивную компоновку через window size classes (compact, medium, expanded, large, extra large) и независимую ширину/высоту [X-ANDROID]. Следовательно, Android phone landscape, foldable и tablet могут получать более сложную компоновку, чем narrow desktop browser; единого правила «Android = один столбец» недостаточно.

## 16.4. Android toolkit остаётся открытым

**[UNKNOWN]** PySide6 имеет официальный Android deployment tool, но этот факт не доказывает пригодность Qt Widgets для желаемого mobile UX; официальная документация описывает отдельный deployment process/APK/AAB и ограничения сборочной среды [X-QT]. Выбор между Qt Quick/QML, native Android UI или иным renderer должен происходить после prototype spike по accessibility, navigation, performance, packaging, file sharing, push и жизненному циклу. Принцип: *никакой выбор toolkit не должен менять application semantic contracts*.

## 16.5. Mobile offline

Мобильный offline cache может содержать безопасно сохранённые списки, уже доступные артефакты и пользовательские drafts. Он **не является authority** для общего Run/job состояния. Pending dangerous commands в автономной очереди по умолчанию не отправляются без повторного подтверждения/проверки effective plan после reconnect. Офлайн-экран сообщает время последней синхронизации и явно отличает `stale` от server-side `failed`.

---

# 17. Narrow surfaces и сервисные представления

## 17.1. Минимальный surface-capability profile

Виджет, системное уведомление, tray, wear companion, embedded panel, CLI/notification bridge могут поддерживать только часть функций:

```text
read compact node status
read assigned work summary
read bounded run status
open deep link to full client
approve simple action only when secure and authorized
```

Узкий клиент не обязан иметь Explorer, полную историю, composer, global search или редактирование Work.

## 17.2. Модель omissions

Отсутствие визуального элемента **не означает отсутствие объекта или разрешения**. UI capabilities/profile формируют доступные маршруты; policy определяет допустимые действия; renderer выбирает компактное представление. Если узкая поверхность не способна показать обязательные effect details, она должна открыть полноразмерный клиент вместо рискованного однокнопочного подтверждения.

## 17.3. Notification-first interfaces

Push содержит минимальный безопасный контекст и deep link; читатель уведомления не должен получать в lock-screen конфиденциальный source text, параметры или сырой лог. Device settings и application notification preferences учитываются совместно.

---

# 18. Surface contracts: кандидат минимального протокола

Все примеры **концептуальны; указанные типы/endpoints/поля не существуют как утверждённый продуктовый API**.

## 18.1. Разделение трёх API

1. **Application contract:** query/command/subscription, авторизация, revisions, outcomes, Work/Run/artifacts.
2. **Presentation semantics:** typed view projections и action descriptors.
3. **Platform adapter contract:** открыть файл/preview, открыть URL, share, clipboard, dialogs, notifications, window focus, locally persist drafts.

Это ограничивает соблазн сделать один огромный `AppContext` со всеми Services и Qt/OS объектами.

## 18.2. Кандидат projection envelope

```json
{
  "contract_version": "candidate-1",
  "view_kind": "work.detail",
  "object_ref": {"kind": "work", "id": "work-123"},
  "revision": 17,
  "cursor": "opaque-commit-cursor",
  "as_of": "2026-10-09T12:00:00Z",
  "freshness": "current",
  "scope": "node",
  "data": {
    "title": "Обновление данных",
    "status": "awaiting_review",
    "linked_runs": ["run-456"],
    "artifacts": ["artifact-789"]
  },
  "available_actions": [
    {"id": "work.accept", "available": true, "risk": "acknowledgement"},
    {"id": "run.retry", "available": false, "reason_code": "effect_state_unknown"}
  ]
}
```

Это пример разделения **authority, projection и availability**. `revision/cursor` принадлежат серверной модели; `freshness` отражает клиентский статус синхронизации. UI не делает выводы о правах из `available_actions` без повторной проверки при команде.

## 18.3. Кандидат команды

```json
{
  "command_id": "run.request",
  "target_ref": {"kind": "scenario", "id": "scenario.escrow.history"},
  "work_id": "work-123",
  "idempotency_key": "opaque-request-id",
  "expected_revision": 17,
  "parameters": {"format": "xlsx", "refresh": false},
  "effect_acknowledgement": null
}
```

Server отвечает `accepted/rejected/conflict/needs_approval/unknown` с correlation/request identity. Для некорректного `expected_revision` клиент должен перезагрузить актуальный plan, а не молча повторять со старым набором эффектов.

## 18.4. ActionDescriptor

Рекомендуемые смысловые поля:

```text
id                    stable user-action semantic name
label / explanation   локализуемая presentation string / message key
subject_ref           объект, к которому применено действие
visibility            eligible for this projection
availability          yes/no/unknown
reason_code           почему сейчас запрещено/недоступно
risk_class            read/write/destructive/external_effect
confirmation          none/summary/approval/re-auth
parameter_schema_ref  ссылка на форму, если нужно
requires_online       может ли быть выполнено при отсутствии сети
revision_guard        текущие условия применимости
```

Это **не новая capability authority**. ActionDescriptor — user-facing проекция уже авторизованного действия, а не собственный алгоритм проверки политик.

## 18.5. Event / navigation / deep link

Stable route должен опираться на `kind + id + optional revision`, а не на GUI index/route number. Кандидат логической схемы:

```text
strategybox://work/<work_id>
strategybox://run/<run_id>
strategybox://artifact/<artifact_id>?version=...
```

Платформенные URI должны выбираться отдельным security/product решением: universal links/deep links, scheme registration, origin validation, node routing, expiry, authentication, object ACL. **Конкретная URI-грамматика выше иллюстративна.**

## 18.6. View projection и reusable component

Shared код может использовать неизменяемые JSON/dataclass models и чистые проекторы, а renderer создавать native components из них. В частности, `ScenarioChatProjector` текущего Windows — доказанный задел, но его надо переподчинить модели Thread/Work, вместо переименования одного `ScenarioRunCase` в `Work` [W-PROJECTOR].

---

# 19. Connection, consistency, sync и local client state

## 19.1. Три явно различаемых состояния данных

| Состояние | Пример | UI обязан сказать |
|---|---|---|
| `current` | получен свежий snapshot/event stream | текущее подтверждённое состояние |
| `stale` | сеть пропала; доступен cache | состояние по времени последней связи |
| `unknown` | нет достоверного snapshot / сервер не подтвердил эффект | статус ещё неизвестен, требуется проверка |

Общее `offline` относится к доступности транспорта клиента, а не к факту исполнения Job. Нельзя «закрыть» spinner с error только из-за отсутствия SSE [R05].

## 19.2. Один принцип обновления для всех клиентов

`load snapshot → subscribe from cursor → apply event → detect gap → resync` применим к Qt/web/Android. Физическое подключение разное: локальный IPC/HTTP, browser SSE, mobile push+fetch. В клиенте — одна семантика cursor/freshness/revision, но network adapters платформенно отличаются.

## 19.3. Per-user read receipts

Общая timeline immutable; отдельные read cursors/receipts принадлежат principal и scope. Переход «прочитано» на Android при необходимости меняет состояние в Windows после синхронизации. Локальное выделение элемента или scroll на экране не обязаны сами по себе составлять долговечное «прочтение»; требуется продуктовая политика соответствующего события.

## 19.4. Draft persistence

- Неотправленное сообщение — local draft, либо явно включённый encrypted server draft.
- Незапущенные параметры — run draft/preset, с версией scenario schema.
- Переключение окна не должно стереть пользовательский ввод.
- Применение новой policy/spec после перерыва требует revalidation черновика.
- Sensitives/секреты не хранятся по умолчанию в plaintext drafts и не выводятся в UI history.

## 19.5. Multi-device selection

Открытый на устройстве A инспектор не должен принудительно переключать выбор на устройстве B. Cross-device sync относится к shared Work/Thread truth; ширина панелей, текущий scroll и focus остаются device-specific. Возможность «продолжить с того же места» реализуется через stable object link/context, а не копирование всех локальных пиксельных состояний.

---

# 20. Accessibility, localization и эргономика

## 20.1. Доступность является системным контрактом

Человек с клавиатурой, screen reader, увеличенным шрифтом, высоким контрастом или Reduced Motion должен иметь доступ к тем же **разрешённым actions и status meanings**. Поверхность может иначе располагать элементы, но не должна скрывать критическое подтверждение только за drag/hover/gesture.

## 20.2. Критерии

- Label/accessibility name для каждой interactive action; icon-only controls получают описательные названия.
- Focus order следует смысловой структуре, а не случайному tab order создания widgets.
- Focus не оказывается скрытым за inspector, sticky toolbar или overlay; WCAG 2.2 2.4.11 задаёт критерий Focus Not Obscured (Minimum) для web [X-FOCUS].
- Статус отображается текстом и символом, не исключительно оттенком.
- Keyboard и touch имеют эквивалент для meaningful action.
- Длинные таблицы и логи предоставляют navigation/search/filter без зависаний.
- Уведомления о прогрессе не спамят screen reader каждым числом/heartbeat.
- Контраст измеряется по фактическим render states, включая disabled/focus/high contrast.
- OS/browser font scaling и zoom допускают reflow/адаптацию.
- Все motion transitions имеют reduced альтернативу.

## 20.3. Локализация

Русский — основной текущий язык, но display labels не должны быть object IDs. Вводится MessageKey/catalog с локализацией текста и единиц, даты/времени с timezone/locale, сортировка по локали, корректный перенос больших русских слов и сокращений. Numeric formats/даты в артефактах — domain/reporting issue и не автоматически равны пользовательскому locale. Смешанный RU/EN контент банков и источников должен отображаться без искажения идентичности.

## 20.4. Доступная адаптация сложных форм

Параметры содержат inline error с field association, error summary при submit, подсказки с keyboard access; в mobile — последовательное чтение, понятные единицы/границы, отмена без потери draft. Ошибки `network`, `validation`, `permission`, `source_unavailable` должны иметь разные user-facing тексты/следующие действия.

---

# 21. Ownership: кто отвечает за что

| Ответственность | Логический owner | Windows | Web | Android | Внешняя граница |
|---|---|---|---|---|---|
| Domain definitions, calculations, evidence | `stratbox` | через service | через service | через service | нет прямого UI-владения |
| Work/Thread/Run/Job truth | Strategy Box application authority | query/command | query/command | query/command | AppDock manages runtime lifecycle |
| Scenario/Capability definitions | domain + application catalog | projection | projection | projection | generic extensions provide declared capabilities |
| Product permissions/approvals | application authority | indicator/action | indicator/action | indicator/action | platform identity/session handoff |
| Physical user workspace / bytes | FileStore / managed storage | local/server adapter | server provider | remote provider | platform data roots |
| Artifact catalog/user lineage | application authority + domain manifest | cards/inspector | cards/preview | cards/share | storage bytes, no UI truth |
| Node/session/install/host health | AppDock | node view | platform status | node status | external owner |
| UI theme tokens | shared semantic design owner | Qt mapping | CSS mapping | native mapping | system accessibility overrides |
| Navigation/layout/focus | client renderer | desktop | responsive browser | mobile | device OS |
| Local draft/recent/layout | local client/profile store | yes | browser client | app storage | encrypted/safe policies |
| Notifications delivery | product rules + platform transport | OS/app | browser/app | OS push/app | permission/OS delivery |
| Artifact style defaults | application user settings + domain rendering | selection | selection | selection | generic style providers |

**[CONSOLIDATED]** Один смысловой owner может иметь несколько физических модулей/процессов. Решение о `stratbox-host`, `stratbox-core`, `stratbox-design` и дополнительном common package принимает следующее проектирование по lifecycle/consumer needs. Этот документ фиксирует **responsibility**, а не автоматическую карту новых репозиториев [R01].

---

# 22. Conflict register: реальные и кажущиеся расхождения

| ID | Источники/напряжение | Разрешение и статус |
|---|---|---|
| **C07-01** | Текущий «Scenario chat» vs поздний `Thread/Work` | **SUPERSEDED как target:** сценарный чат — действующий baseline; Work/Thread-first — сильное консолидированное направление [B-WIN][B-AI-UI][R02]. |
| **C07-02** | Шесть mode rail entries vs четыре направления | **CONSOLIDATED:** Work/Explorer/Scenarios/Runs; остальные — contextual projections. 4 root nav buttons на каждом устройстве — **TARGET**, не invariant [B-UX]. |
| **C07-03** | «Scenario = автоматическая оболочка Operation» | **SUPERSEDED:** в current code это так; целевой сценарий curated/use-case, не обязательная карточка каждой операции [W-SCENARIO][R02]. |
| **C07-04** | `Case` как центр всей работы vs `Work/Run` | **CONSOLIDATED:** legacy Case — текущий UI execution record; самостоятельный Work живёт дольше Runs; дублирующая durable Case без lifecycle не обоснована [R02][R04]. |
| **C07-05** | Фоновые процессы отдельным разделом vs единый execution spine | **CONSOLIDATED:** background — execution mode, automation — definition; управляется через Runs/Automations [B-BG][R04]. |
| **C07-06** | `stratbox-windows` владеет runtime vs headless authority | **CONSOLIDATED по логике:** execution/state owner отдельно от Qt; **UNKNOWN физически:** новый process/package/repo профиль [B-WEB][R01][R05]. |
| **C07-07** | `stratbox-design` как отдельный repo | **UNKNOWN:** logical design tokens нужны, отдельный repo не доказан [B-VISUAL][R01]. |
| **C07-08** | Две конкурирующие темы для UI и артефактов | **CONSOLIDATED:** `InterfaceTheme` ≠ `ArtifactStyleSet` ≠ `ArtifactMetadata` [B-SET][B-STYLE]. |
| **C07-09** | Плагины меняют интерфейс vs расширяют product capabilities | **CONSOLIDATED:** generic capability/style resources да; произвольная замена shell/QSS/Qt navigation — нет [B-SET][B-EXT]. |
| **C07-10** | Desktop 13 px/трёхпанельная модель vs мобильный масштаб | **ложный конфликт:** единые смысловые токены; разные density, input metrics и navigation [B-VISUAL][X-ANDROID]. |
| **C07-11** | Web: REST+SSE vs WebSocket | **не основной конфликт:** SSE — хороший first candidate; WebSocket — conditional. Ни один transport ещё не утверждён как общий mandatory ABI [B-WEB][X-SSE]. |
| **C07-12** | Windows/Android: PySide reuse vs native Android | **UNKNOWN:** переносимая семантика устойчива; toolkit определит spike [B-WIN][X-QT]. |
| **C07-13** | Настройки «Рабочие/Системные» vs minimalist settings | **SUPERSEDED как target:** текущие информационные вкладки переносятся в Проводник/Узел/Diagnostics [W-SET][B-SET]. |
| **C07-14** | AppDock владеет пользователями/сессией vs Strategy Box collaboration | **разные scopes, не конфликт:** platform identity/session/lifecycle vs product Thread/Work/assignment/read cursors [A][R05]. |
| **C07-15** | UI показывает optimistic success vs durable unknown outcome | **CONSOLIDATED:** UI отображает серверный outcome, транспортный сбой означает stale/unknown, retry только после reconciliation [R04][R05]. |
| **C07-16** | «Участники» как top-level screen vs presence contextual | **TARGET-HYPOTHESIS:** контекстный presence в первом релизе; отдельный people directory оправдан только самостоятельными team use cases [B-MULTI][B-UX]. |
| **C07-17** | CAS/file-centric артефакты vs быстрый workspace Explorer | **разные abstraction levels:** stable ArtifactRef и mutable WorkspaceObject могут одновременно отображаться в одной surface [R03]. |
| **C07-18** | Буквальная одинаковая навигация на всех устройствах | **SUPERSEDED:** semantic destination/effects общие; геометрия и native behaviors отличаются [B-UX][X-ANDROID]. |

---

# 23. Новые локальные белые пятна, выявленные поверх корпуса

## 23.1. Surface projection authority

**[UNKNOWN / NEEDS DESIGN]** Где именно собирается final view projection — полностью server-side, client-side из типизированных domain snapshots или смешанно? Рекомендация: сервер формирует identity, ACL, action eligibility, ordering/cursor и canonical status; клиент допускает чистые локальные группировки/фильтры/локализованные labels. Нужен контракт, чтобы одна action availability не расходилась между Qt/Web/Android.

## 23.2. Deep linking и node routing

**[UNKNOWN]** Нужен универсальный реестр route kinds и policy: один ли link на Work работает на разных узлах, как вычисляется нужный node/tenant, как выглядит отказ при отсутствующем доступе, что показывать при удалённой/архивной сущности, какие ссылки разрешены во внешних notifications.

## 23.3. Global search authority

**[UNKNOWN]** Будет ли единый index (Work/Thread/Artifact/File) или федерация catalog providers? Требуются ACL-aware result set, stale/partial/timeout semantics, ограничение трафика Android и быстрый desktop keyboard-first UX. Тема 05 задаёт source of truth, но ещё не готовую search architecture.

## 23.4. Thread/Work inbox и notification taxonomy

**[UNKNOWN]** Точные приоритеты: когда Work попадает в «Требует моего ответа», как считать unread message vs assigned review vs blocked Job, как coalesce duplicates, как отключать шум фона без скрытия опасных состояний. Нужно продуктово определить триггеры и delivery audiences.

## 23.5. Artifact preview в узких клиентах

**[UNKNOWN]** Минимальный список форматов/лимитов preview, server-side rendering policy, watermark/redaction, large-file slicing и работа с управляемыми источниками. Не следует заявлять «Excel preview» на Android до прототипа реальных workbook sizes.

## 23.6. Multi-window и tabs

**[UNKNOWN]** Desktop может иметь несколько окон на один node/Thread, browser — несколько tabs, Android — split-screen. Нужно решить кроссоконную политику drafts/revisions/selection, исключить самоповтор команды при одновременном submit. Один процесс Qt не равен одной active Work.

## 23.7. First-release AI без магических обещаний

**[UNKNOWN]** Что именно вводится первым — conversational catalogue search, explanation, drafting, планирование или разрешённый agent executor. UX должен уметь честно сказать «AI unavailable», сохранив привычный manual path.

## 23.8. Информационная плотность и hardware budgets

**[UNKNOWN]** Нужны базовые профили слабых рабочих ПК, RAM/CPU budgets UI, виртуализация на 1k/10k/100k rows, ограничения Web reconnection, Android network/battery. Motion/dark theme не являются оправданием существенного роста latency.

## 23.9. Cross-device drafts и офлайн-команды

**[UNKNOWN]** Синхронизировать ли незавершённые тексты между устройствами, где хранить чувствительные значения, шифровать ли локальные drafts, какие commands разрешать при offline и как предотвращать повтор destructive effects.

## 23.10. Accessibility baseline и языки

**[UNKNOWN]** Нужно зафиксировать acceptance scope WCAG/desktop assistive technology, support matrix Windows screen readers/browsers/Android TalkBack, локаль RU/EN, font scaling и тестовое покрытие. Для Web рекомендована ориентировка на WCAG 2.2 AA как целевой engineering bar, но фактическое соответствие ещё не проверено.

## 23.11. Shared component source

**[UNKNOWN]** Нужен ли отдельный reusable package с `presentation/common` после появления Web и Android или достаточно единого serialized contract и отдельных client implementations? У Python Qt, JS browser и Android native разная модель кода; **source sharing** не всегда равно **semantic sharing**. Сначала lockstep conformance fixtures и reference protocol, потом package split.

## 23.12. UI error/condition ownership

**[UNKNOWN]** Как пользователь видит одновременно runtime health AppDock, provider availability, доменную ошибку и warning аналитической валидации, не получая несколько дублирующих banners? Требуется priority/aggregation policy, preserving original authority/correlation.

---

# 24. Candidate Target Model: минимальная целевая архитектура

```text
STRATEGY BOX — LOGICAL

stratbox (domain owner)
    ├─ canonical operations & source/registry semantics
    ├─ validation, domain result, evidence & provenance
    └─ domain artifact renderers
                 ▲
                 │ typed capability/result contracts
                 │
Strategy Box application authority (headless-capable)
    ├─ Thread / Work / Run / Job lifecycle
    ├─ scenario catalogue / plan & execution binding
    ├─ commands, queries, events, ACL and subscriptions
    ├─ user-facing artifact catalogue and collaboration
    ├─ notifications, user settings and policy resolution
    └─ surface semantic projections (read models, action descriptors)
                 ▲
                 │ stable surface contract
                 │
     ┌───────────┼──────────────┬─────────────┐
     ▼           ▼              ▼             ▼
 Windows client  Web client     Android       narrow companion
 Qt renderer     HTML/CSS       native/tbd    OS/bounded
 OS adapters     browser        Android OS    capabilities

AppDock — external environment/node/install/activation/host lifecycle/platform health
```

**[CONSOLIDATED]** Это логическая архитектура, достаточная для выбора UI и контрактов. **[TARGET-HYPOTHESIS]** В физической реализации отдельный headless host вероятен и полезен; но он не обязан означать отдельный монолитный репозиторий наряду с `stratbox`, `stratbox-windows`, `stratbox-web` и `stratbox-android`. По [R01] сначала responsibility и contract, потом repository.

## 24.1. Минимальная contract set для v1

1. `SurfaceContext` + actor/node/locale/capabilities.
2. `NavigationDestination` + stable object refs.
3. `Thread/Work/Run/Scenario/Artifact` разрешённые summary/detail projections.
4. `ActionDescriptor`/typed command request/result.
5. `Snapshot` + `cursor/revision` + `subscription` semantics.
6. `InputFormSpec`/validation with effective parameters.
7. `Notification/Problem` user summary.
8. Semantic design tokens, motion roles, accessibility state.
9. `PlatformServices` ports для native integrations.
10. Explicit `freshness/offline/unknown` на каждом server-backed view.

**Антицель:** полный универсальный UI DSL со всеми Qt widgets/HTML elements/mobile gestures. Нужен уровень смысловых представлений, а не сериализация каждого пикселя.

---

# 25. Сквозные пользовательские проверки (walkthroughs)

## 25.1. Пользователь запускает отчёт в Windows и открывает Android

1. В Windows открывает Work, выбирает сценарий и параметры.
2. UI показывает разрешённый план/эффекты; submit создаёт idempotent Run request.
3. Node authority принимает Run/Jobs; Windows получает `run_id` и отображает real progress.
4. Windows закрывается: Job продолжается в host, если node/runtime остаётся включён.
5. Android авторизуется, получает Thread/Work snapshot и active Run status.
6. После исполнения появляется ArtifactRef; Android открывает preview или share action.
7. В Windows при возвращении виден тот же Work/Run/Artifact, а не локальная альтернативная история.

**Acceptance:** нет второго Job, `run_id` одинаков, закрытие UI не меняет outcome, статус связи честно отделён от статуса выполнения.

## 25.2. Коллега видит проблему на общем узле

1. Job блокируется из-за общего source/data condition.
2. Domain Problem создаётся с owner/correlation; platform problem передаётся через внешний owner только при соответствующей границе.
3. Authorized participants получают short actionable summary, без исходных секретов и raw traceback.
4. Назначенный участник открывает Work, видит связанные Runs/Artifacts и доступные действия.
5. Состояние исправления синхронизируется на других surfaces.

**Acceptance:** адресность, ACL, дедупликация и один owner причины.

## 25.3. Пользователь изменяет настройки оформления

1. На Windows выбирает Theme=Dark, Accent=Strategy Blue.
2. Изменяется только UI theme/OS adaptation, не артефакты и не Work state.
3. В «Артефакты и отчёты» выбирает допустимый effective ArtifactStyleSet.
4. Следующий Run получает versioned style reference в effective parameters/result manifest.
5. Исторические файлы не меняются ретроспективно; Android может иметь собственный system theme.

**Acceptance:** никакая смена UI темы не перерисовывает существующий XLSX и не меняет identity результата.

## 25.4. Web disconnect во время неизвестного внешнего эффекта

1. Пользователь отправил разрешённый Run command с idempotency key.
2. Browser теряет связь до ack.
3. UI показывает `submission_outcome_unknown` и предлагает «Проверить».
4. Reconnect выясняет receipt/Run identity по idempotency key.
5. Только если гарантированно отсутствует effect/accepted Run, разрешён новый submit; blind duplicate запрещён.

**Acceptance:** отсутствие ложного failed или повторного destructive effect.

## 25.5. Неподдерживаемое действие на мобильной узкой поверхности

1. Пользователь получает push «требуется подтверждение массового изменения».
2. Push открывает secure Work/Run detail, а не совершает действие.
3. Если экран не вмещает полный effect summary, клиент предлагает «Открыть на компьютере» или отдельный mobile confirmation wizard.
4. После подтверждения server revalidates scope/plan/version.

**Acceptance:** уменьшенная поверхность не уменьшает требуемый safety контекст.

## 25.6. Explorer: один объект, несколько видов

1. В Проводнике Windows доступен workspace file.
2. Run создаёт из него версионированный Artifact с provenance.
3. В Web Artifact Library показывается ArtifactRef и разрешённый download.
4. Исходный файл workspace редактируется; старый committed Artifact не превращается молча в «новую версию».

**Acceptance:** источник, рабочий файл и published artifact различаются в UI и навигации.

---

# 26. Проверяемые invariants и acceptance matrix

## 26.1. Семантические

- [ ] Один Work может содержать несколько Runs, один Thread — несколько Works; UI отображает это без дублирования объекта.
- [ ] Один Run имеет одну identity на Windows/Web/Android; смена UI не создаёт второй Run.
- [ ] Формы параметров и action eligibility выводятся из общего descriptor/contract, а не переписываются тремя независимыми валидаторами.
- [ ] Определение операции отделено от пользовательского сценария и факта запуска.
- [ ] ArtifactRef и Workspace FileRef отличимы даже при одинаковом имени файла.
- [ ] UI не повышает epistemic confidence, success level и не выдумывает progress.

## 26.2. Состояние и связь

- [ ] Surface закрывается, authoritative Job живёт по policy узла.
- [ ] Offline/stale/unknown визуально и семантически различаются.
- [ ] При reconnect consumer правильно обрабатывает пропущенные/повторные события.
- [ ] `expected_revision`/idempotency защита работает при multi-tab и multi-device submit.
- [ ] Per-user unread и notification receipts не мутируют общую timeline.
- [ ] Фоновая automation enabled и текущий running Job не смешиваются.

## 26.3. Ownership и безопасность

- [ ] Qt/web/mobile код не содержит вычислительную банковскую бизнес-логику.
- [ ] Core не импортирует UI toolkit/platform services.
- [ ] UI не делает policy из видимости кнопки: server revalidates action.
- [ ] Web/mobile не получает физические server storage paths как доверенное API.
- [ ] Подтверждение destructive effect показывает scope/объекты и проходит server-side проверку.
- [ ] Generic plugin API не даёт права произвольного override shell/navigation.
- [ ] Публичные артефакты/исходники свободны от сведений о конкретных закрытых реализациях.

## 26.4. UX и accessibility

- [ ] Переход по work/run/artifact deep link открывает один смысловой объект на разных поверхностях.
- [ ] На desktop средних размеров перестройка колонок не уничтожает введённый draft.
- [ ] На мобильном компактном экране основные действия доступны без hover и мелких icon-only targets.
- [ ] Клавиатурная навигация, screen reader, focus, status labels, high contrast и Reduced Motion испытаны.
- [ ] Список 10 тыс. событий/файлов отображается виртуализированно, без UI freeze (число — пилотный test fixture, performance budget утверждается отдельно).
- [ ] Dark/system theme не меняет смысл статуса/permissions.
- [ ] Ошибки и UNKNOWN имеют понятные action-oriented тексты и способ открыть подробную диагностику.

## 26.5. Contract and implementation tests

Предлагаемый testing pyramid:

1. **Contract tests:** сериализация/ref/revision/action/result/schema fixture, согласованность labels/status across surfaces.
2. **Projection tests:** deterministic Thread/Work/Run/Artifact view from shared fixtures, permission/redaction variants.
3. **Qt adapter tests:** keyboard, inspector selection, theme tokens, cancel/draft preservation.
4. **Web integration/E2E:** auth/ACL/CSRF, SSE reconnect, multi-tab conflict, download/upload controls.
5. **Android E2E:** phone/tablet/foldable window classes, lifecycle, notifications, TalkBack, file-share security, degraded/offline.
6. **Cross-client tests:** Windows submit → Web observe → Android approve → Windows review; same IDs and outcomes.
7. **Performance/a11y checks:** memory, frame budget, UI responsiveness, pagination/virtualization, contrast/zoom/Reduced Motion.

Эти acceptance criteria — **предложения для будущего инженерного допуска**; в рамках исследования тесты не запускались.

---

# 27. Последовательность перехода от baseline к целевой surface architecture

## Этап 0 — привести действующий Windows baseline в честное состояние

1. Синхронизировать manifest, dependency versions, tests и docs.
2. Удалить tracked generated/runtime мусор, исправить ignore rules.
3. Убрать из публичных материалов любые environment-specific детали, оставив generic extension vocabulary.
4. Отделить реально доступные функции от preview-панелей Background/Presence/Assignments.
5. Добавить CI contract checks и initial Qt accessibility smoke.

**Польза:** текущая программа остаётся используемой, а UI больше не обещает незапущенный backend.

## Этап 1 — нормализовать product semantics внутри Windows

1. Принять minimal Thread/Work/Run/Artifact view models на уровне research→Product.
2. Вынести `presentation/common` semantic projectors для Run, inspector, scenario form, explorer, notifications.
3. Убрать Qt import из `runtime.bootstrap` и сформировать отдельный Qt bridge.
4. Перевести mode rail на Work/Explorer/Scenarios/Runs, удержав aliases/redirects по необходимости миграции данных, а не обратной совместимости API.
5. Разделить Settings, SurfaceState, DraftState, ManagedPolicy.
6. Ввести prototype design token resolver вместо hardcoded QSS colors.

## Этап 2 — authority и один execution contract

1. Реализовать headless-capable product authority с устойчивыми Work/Run/Job состояниями.
2. Согласовать command/query/subscription, refs/revisions/idempotency/freshness.
3. Подключить Windows как consumer; локальная history становится migration/export источником, а не durable truth.
4. Реализовать eligible actions, shared artifacts metadata, read receipts и нормальный presence/notifications scope.
5. Добавить reconciliation/reconnect и controlled job actions.

**Важный порядок:** сначала data/state/command contracts, потом масштабирование UI на другие устройства. Иначе получится красивая копия проблемы Windows.

## Этап 3 — Web как первый независимый consumer

1. Выделить browser app с теми же canonical refs/action IDs.
2. Сделать responsive Work/Explorer/Scenarios/Runs.
3. Реализовать auth/ACL, safe files, server-backed search/preview и snapshots/events.
4. Запустить cross-client conformance suite.
5. Проверить конфликт двух открытых вкладок, offline/reconnect и background job independence.

Web рано выявит скрытые Qt/path/state зависимости.

## Этап 4 — Android companion и adaptive client

1. Прототип двух renderer candidates по одним fixtures.
2. Реализовать Work/Run/notifications/Artifact и action approvals.
3. Проверить Android lifecycle, screen reader, window size classes, background restrictions, file sharing.
4. Добавить ограниченный Scenario launch и компактный Explorer по мере доказанной пользы.
5. Расширить functionality без размножения core и JobManager.

## Этап 5 — refinement и narrow surfaces

1. Продвинутый full-text search, artifact preview, saved filters.
2. Shared UI tokens as package, только если consumer/release complexity этого требует.
3. Richer data/knowledge inspection, proof/evidence projections и multi-user collaboration.
4. Узкие OS surfaces, tray, notifications и future device profiles на bounded capabilities.

## Зависимости соседних исследований

Тема 07 фиксирует UI-level потребности, но **не подменяет**: тему 04 (execution FSM и idempotency), тему 05 (transactional state/permissions/cursors), тему 06 (capability/extension/automation ABI), тему 08 (системные safety/a11y/recovery quality gates), тему 09 (итоговая physical architecture). Любое дальнейшее решение, меняющее эти уровни, требует согласованной проверки соответствующего owner.

---

# 28. Provenance ledger / первичные источники

Далее перечислены только публичные Strategy Box и общие внешние источники. Путь к исследованию используется как **research provenance**, а не как утверждение о размещении реализации. Для фактов о коде источником является собственный implementation owner.

## 28.1. Программа и governance

- **[P]** [Программа третьей ветки](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/strategy_box_03_consolidation_research_program.md) — содержание и последовательность темы 07.
- [README: консолидация](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/README.md) — правила синтеза и границы решений.
- [README: второй корпус](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/README.md) — приоритет implementation owners.

## 28.2. Контрольные консолидированные исследования

- **[R00]** [00 — Corpus Map & Open Questions](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_00_corpus_map_open_questions_2026-10-08.md): source inventory/conflicts/superseded.
- **[R01]** [01 — System Model](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_01_System_Model_consolidated_research_2026-10-08.md): ownership, physical/logical division.
- **[R02]** [02 — Canonical Semantic Model](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_02_canonical_semantic_model_2026-10-08.md): Thread/Work/Run/Job/Artifact distinction.
- **[R03]** [03 — Data → Knowledge](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_03_data_to_knowledge_consolidated_research_2026-10-08.md): SourceSnapshot/Dataset/Artifact/lineage, style boundaries.
- **[R04]** [04 — Work → Execution](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_04_work_to_execution_consolidated_research_2026-10-09.md): one execution spine, outcome, retry/unknown.
- **[R05]** [05 — State, Persistence & Collaboration](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_05_state_persistence_collaboration_consolidated_research_2026-10-09.md): node authority, snapshots/cursors/read receipts.

## 28.3. Основные исследования `02-base-study`

- **[B-WIN]** [Windows current-state baseline, 2026-10-06](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md): UI, Qt, scenarios, history, background/presence skeleton, AppDock.
- **[B-CORE]** [stratbox core current-state baseline](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_base_study_current_state_2026-10-06.md): domain/neutral architecture.
- **[B-UX]** [Интерфейс и UX Strategy Box](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_windows_interface_requirements_research_2026-10-07.md): IA, explorer, Work, logs, inspector, global search.
- **[B-VISUAL]** [Визуальная система](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_interface_visual_system_research_2026-10-07.md): tokens, colors, typography, density, high contrast.
- **[B-MOTION]** [Motion / Animation](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_windows_motion_animation_research_2026-10-07.md): state-driven animation, Reduced Motion, timing.
- **[B-SET]** [Системные настройки](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_system_settings_research_2026-10-07.md): Settings vs state/drafts/policy, generic plugins.
- **[B-STYLE]** [Наборы оформления артефактов](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md): ArtifactStyleSet/InterfaceTheme/Metadata separation.
- **[B-WEB]** [Web/self-hosted architecture](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md): browser/client-host boundary, responsive, auth, API.
- **[B-MULTI]** [Единый узел и multi-user](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md): participants, read cursors, shared node state.
- **[B-BG]** [Фоновые задачи и процессы](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md): background/automation projections.
- **[B-AI-UI]** [Chat / Work / cognitive schemes UI](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_chat_work_schemes_ui_research_2026-10-07.md): Thread/Work distinction, AI action proposals and parallel work.
- **[B-OBS]** [Observability/errors/logs](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_observability_errors_logs_research_2026-10-07.md): causal execution/user errors/problems/logs.
- **[B-EXEC]** [Execution control/user path](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_execution_control_user_path_research_2026-10-07.md): execution controls, forms, cancellation.
- **[B-CMD]** [Команды/сценарии/каскады](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md): prior semantics; later terms refined.
- **[B-ART]** [Файлово-артефактный слой](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_file_artifact_layer_research_2026-10-06.md): Artifact identity/catalog/materialization.
- **[B-PORT]** [Переносимость бизнес-сегментов](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_segments_portability_reuse_architecture_research_2026-10-07.md): shared neutral contracts and domain reuse.
- **[B-PROTOS-B]** [Разделение внешнего cognitive layer и Strategy Box](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_boundary_research_2026-10-07.md): capability/action boundary (только продуктовые выводы).
- **[B-EXT]** [Общий контракт корпоративных расширений](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_corporate_plugin_contract_research_2026-10-07.md): neutral plugin/capability/status vocabulary; без конкретных реализаций.

**История:** `01-old-notes` использовался исключительно для выявления вытесненных предпосылок (например, UI внутри core и сценарий как единственный корень). Исторические заметки не использовались для фактов о действующем коде.

## 28.4. Прямо проверенный публичный implementation owner

- **[W-MANIFEST]** [`stratbox-windows/appdock/manifest.json`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json): local Windows foreground surface, activation/views/capabilities.
- **[W-PROJECT]** [`stratbox-windows/pyproject.toml`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/pyproject.toml): version and dependencies (в документе рассматриваются только публичные части этого контракта).
- **[W-SCENARIO]** [`application/scenarios/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/models.py), [`runner.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py): current ScenarioSpec and execution.
- **[W-BOOT]** [`runtime/bootstrap.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py): Qt coordinator composition leakage.
- **[W-COORD]** [`presentation/qt_desktop/scenario_coordinator.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py): QThread coordination.
- **[W-PROJECTOR]** [`presentation/common/scenario_chat/projector.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/common/scenario_chat/projector.py): existing semantic projection.
- **[W-SET]** [`settings_dialog.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/dialogs/settings_dialog.py): current user/work/system UI.
- **[W-CONFIG]** [`runtime/config.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/config.py): mixed persisted config.
- [History persistence](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py): local JSON projections.
- [Background state store](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/store.py): current in-memory model.

## 28.5. AppDock boundary

- **[A]** «AppDock — описание продукта и проекта» (проектный источник, предоставлен в материалах ChatGPT; §§7, 12–14, 19–23). Служит подтверждением назначения узла, lifecycle, действий, результатов, remote/host и ролей; не свидетельствует о реализации каждого целевого режима.

## 28.6. Внешние технические источники

- **[X-ANDROID]** [Android Developers — Use window size classes](https://developer.android.com/develop/adaptive-apps/guides/use-window-size-classes): responsive/adaptive layouts по доступному окну.
- **[X-SSE]** [MDN — Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events): EventSource, event ID и reconnect semantics.
- **[X-QT]** [Qt for Python — pyside6-android-deploy](https://doc.qt.io/qtforpython-6.8/deployment/deployment-pyside6-android-deploy.html): Android packaging possibilities and limitations; не доказательство пригодности текущего Widgets UI.
- **[X-W3C]** [W3C Understanding WCAG 2.2 SC 2.3.3 — Animation from Interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions): Reduced Motion and unnecessary interaction animation.
- **[X-FOCUS]** [W3C Understanding WCAG 2.2 SC 2.4.11 — Focus Not Obscured (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum): видимость keyboard focus для web.

---

# 29. Decision / Gap Register темы 07

| Предмет | Статус после исследования | Следующий owner/проверка |
|---|---|---|
| One semantics, multiple native surfaces | **CONSOLIDATED** | application/Product contracts |
| Windows current three-zone Qt UI | **CURRENT** | Windows implementation owner |
| Work/Thread-first semantic center | **CONSOLIDATED direction** | Product acceptance of navigation and object UX |
| Four logical directions Work/Explorer/Scenarios/Runs | **CONSOLIDATED, not literal tabs invariant** | responsive prototypes |
| Separate Qt from runtime composition | **STRONG TARGET-HYPOTHESIS** | Windows refactor + import tests |
| One authority, clients as projections | **CONSOLIDATED** | application runtime / persistence |
| Web via host API | **STRONG TARGET-HYPOTHESIS** | server/web contract pilot |
| REST+SSE first | **TARGET-HYPOTHESIS** | reconnect/multiuser performance probe |
| Android companion first | **TARGET-HYPOTHESIS** | mobile usage/prototype |
| Android native toolkit choice | **UNKNOWN** | QtQuick/native spike |
| Semantic design tokens and motion roles | **CONSOLIDATED** | style contract and a11y acceptance |
| Separate `stratbox-design` repo | **UNKNOWN / not required** | consumer/release analysis |
| InterfaceTheme separate from ArtifactStyleSet | **CONSOLIDATED** | design + reporting contracts |
| Minimal Settings vs SurfaceState/Draft | **CONSOLIDATED** | settings redesign |
| Extension contributions do not mutate shell | **CONSOLIDATED** | neutral extension ABI/security |
| Shared source package for 3 clients | **UNKNOWN** | language/toolchain conformance probe |
| Offline drafts and cached read-only views | **STRONG TARGET-HYPOTHESIS** | mobile/web security and sync probe |
| Offline queued commands | **UNKNOWN; risky effects blocked by default** | effect/idempotency policy |
| Global search backend and ranking | **UNKNOWN** | index workload/prototype |
| Notification taxonomy and audience | **UNKNOWN** | collaboration/product policy |
| Artifact previews on mobile | **UNKNOWN** | format/rendering resource pilots |
| Real A11y/performance compliance | **NOT VERIFIED** | cross-platform E2E + audits |

---

# 30. Итоговая позиция

**[CONSOLIDATED]** Strategy Box уже накопил достаточно продуктовой и архитектурной семантики, чтобы перестать проектировать Windows, Web и Android как независимые UX-вселенные. Их общий предмет — не widget, не sidebar и не кнопка запуска, а **долговечная работа, доступная способность, управляемое исполнение, проверяемый результат и совместная история**.

Наиболее экономичная следующая архитектурная траектория:

```text
определить один semantic product contract
          ↓
сделать Windows consumer чистых application projections
          ↓
отделить durable authority от жизни GUI
          ↓
проверить границы через независимый Web consumer
          ↓
ввести Android как адаптивную companion/full-client surface
          ↓
добавлять узкие клиенты без нового Work/Execution world
```

Два ограничения особенно важны. **Первое:** нельзя переносить в Android сам Qt-owned execution lifecycle под лозунгом «переиспользуем код»; переносить надо models/contracts и проверенный смысл действий. **Второе:** нельзя строить для браузера и телефона облегчённую параллельную backend-модель, которая отличается от Windows статусами, идентичностями артефактов или правами: такой путь создаст три продукта вместо одного.

**Результат темы 07 — исследовательская рамка и набор проверяемых решений/UNKNOWN.** Финальные Product Decisions, контракты выпуска, реализация и performance/a11y certification остаются отдельными следующими действиями.

---

**Конец Research Synthesis — Topic 07.**
