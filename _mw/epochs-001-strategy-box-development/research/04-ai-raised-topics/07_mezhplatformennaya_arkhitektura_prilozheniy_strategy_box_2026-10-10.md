# 07. Межплатформенная архитектура приложений Strategy Box

**Дата исследования:** 10 октября 2026 года  
**Статус:** самостоятельное архитектурное исследование / предложения к Product & Architecture Decisions; **не реализация и не утверждённая спецификация**.  
**Постановка:** тема 07 из `Strategy_Box_Research_Topics(2).docx`, включая наводящие вопросы и комментарий разработчика.  
**Область:** `stratbox` (аналитическое ядро), `stratbox-windows` (существующая пользовательская поверхность), потенциальные Web/Android-клиенты и интеграционная граница AppDock.  
**Режим работы:** чтение предоставленного DOCX, текущих публичных `main`-веток и релевантного Research-корпуса, сопоставление с опубликованными стандартами и техническими источниками. Продуктовый код и репозитории не изменялись.  
**Примечание о достоверности:** проверены исходники и декларации репозиториев; сборка Web/Android, тесты на устройствах, реальное развёртывание хоста, измерение задержек и внешние security-аудиты здесь не проводились.

---

## 0. Резюме и ключевая архитектурная позиция

**Основная рекомендация:** Strategy Box должен иметь **одну предметную логику и одну логическую прикладную модель** для Windows, браузера и Android. Клиенты имеют собственные визуальные реализации и OS-адаптеры. В совместном режиме состояние заданий, доступных действий, артефактов и истории принадлежит исполняющему узлу, а не одному из открытых окон. Конкретная упаковка этой прикладной модели в модуль, процесс либо отдельный репозиторий — самостоятельное решение, зависящее от реального жизненного цикла.

При этом нельзя отождествлять *единый продукт*, *общий исходный код* и *одинаковые пиксели*. Это три разных цели. Первая обязательна; вторая желательна, если обеспечивает экономию сопровождения; третья часто мешает удобству на телефоне. **Одинаковые данные, возможности, статусы и правила действия важнее идентичной верстки.**

Короткая целевая схема:

```text
                       Strategy Box clients
           ┌────────────────┬───────────────┬─────────────────┐
           │ Windows        │ Web           │ Android         │
           │ Qt desktop     │ browser UI    │ mobile UI       │
           └────────┬───────┴───────┬───────┴────────┬────────┘
                    │               │                │
            platform adapters + typed semantic application contract
                    │               │                │
                    └───────────────┼────────────────┘
                                    ▼
                 Strategy Box application authority (logical)
                scenarios, runs/jobs, user actions, state,
                permissions, artifacts, subscriptions, history
                                    │
                                    ▼
                         stratbox Python core
                sources / statistics / analytics / export
                                    │
                                    ▼
                      storage / network providers

          AppDock is OUTSIDE these domain responsibilities:
            assembly, installation, node/runtime bindings,
            activation, packaging, managed lifecycle
```

**Приоритеты:**

1. **P0 — очистить границу:** application/use-case и presentation semantics должны импортироваться без Qt и без привязки к локальному Windows path. Полезный имеющийся `presentation/common` сохранить, но расширять после определения его владельца.
2. **P0 — принять единое значение действия и его результата:** на разных клиентах один запуск получает одну идентичность; статусы, права, частичные ошибки и реальный результат вычисления совпадают. Даже отличный Web UI бесполезен, если его `success` расходится с Windows.
3. **P0 для публичного Web — минимальная, но настоящая безопасность:** предварительно созданные учётные записи возможны; пароли в исходниках/манифесте или открытый неавторизованный API — нет. Защита публичного домена начинается с первой версии, а самостоятельная регистрация через почту может ждать.
4. **P1 — Web как самостоятельный клиент:** его необходимость выражена разработчиком сильнее, чем раньше. Он должен входить через домен к удалённой или локальной хостовой authority, видеть общие работы, статусы, запускать разрешённые операции и получать результаты.
5. **P1 — Android сначала как полноценный удалённый управляющий клиент:** просмотр, уведомления, лёгкий запуск, параметры, результаты и подтверждения. Установка аналитического Python-ядра и большого каталога данных на телефон на первом этапе **не нужна**.
6. **P1 — AppDock определяет форму поставки, Strategy Box — смысл действий:** manifest/source authoring и Studio влияют на роли узлов/поверхностей, однако авторитетные сведения о работе и доступе должны проверяться в runtime, в момент реального действия.
7. **P2 — toolkit и физический shared package выбирать после вертикального прототипа.** Qt/Flutter/React Native/Kotlin имеют разные достоинства; из факта существования PySide6 desktop не следует выбор PySide6 для Android.

**Критическое различие:** исследование и новый публичный `docs/` Strategy Box уже фиксируют согласованные архитектурные *кандидаты*, но Web/Android приложения и общая server-side authority пока **не установлены как действующая реализация**. Это должно оставаться явно видимым в плане развития.

## 1. Постановка темы: намерение разработчика и степень обязательности

### 1.1. Буквальная предметная рамка

Тема 07 требует выявить переносимые части прикладной логики между Windows и будущими клиентами, включая Android, и отделить **смысловые сценарии, состояния и правила применения** от Qt, файловой системы, визуальных компонентов и возможностей платформы. Два прямых вопроса: (1) какие модули сделать нейтральными, (2) какие режимы мобильной работы действительно потребуются.

Комментарий разработчика уточняет исходную постановку. Сводить его только к Android было бы ошибкой: **Web назван прямо и обязательно**, причём Web вместе с Android могут со временем оказаться более востребованными, чем Windows.

### 1.2. Классификация требований

| Положение | Источник | Статус для данного исследования | Архитектурное следствие |
|---|---|---|---|
| Нужен веб-интерфейс | Прямой ответ разработчика | **Установленное продуктовое намерение** | Проектировать отдельный browser consumer, а не только переносимость Windows→Android |
| Android-приложение желательно и практически ожидается | Ответ разработчика | **Сильное направление**, сроки и релизный scope открыты | Отдельный mobile profile и прототип, без раннего обещания full feature parity |
| В идеале два новых репозитория | «Предполагаю» | **Пожелание об организации кода**, а не обязательство создавать сейчас | Оценить, когда repo начинает иметь код, tests и собственный lifecycle |
| Внешний вход через сайт/домен | «Пока предпочтительный вариант» | **Предпочтительная поставка** | Нужны URL, TLS, browser auth, reverse-proxy/ingress и размещение API |
| Минимальная авторизация, возможно заранее созданные логины и пароли | Прямой ответ | **Продуктовое ограничение на сложность** | Не строить регистрацию и почтовую систему на MVP; базовые safeguards обязательны |
| Общая визуальная начинка при различающейся верстке | Прямой ответ | **Установленное UX-направление** | Общие design tokens, смысловые компоненты, action schemas; разные layouts |
| Android прежде всего подключается к хосту | Прямой ответ | **Установленное начальное поведение** | Remote API и авторитетное исполнение на узле, мобильный клиент без Python-ядра |
| Локальное исполнение на телефоне возможно позже | «Гипотетически» | **Необязательная опция будущего** | Сохранить `ExecutionBackend` boundary, не реализовывать mobile runtime заранее |
| Тип сборки и роли host/client пробрасываются AppDock | Прямой ответ | **Целевая интеграционная гипотеза** | Развести source manifest, resolved product definition, activation и наблюдаемый runtime mode |
| AppDock меняется и незрел | Прямой ответ; внешний project owner | **Действительное ограничение** | Contract-version adapters; не закладывать отсутствующий remote SDK как готовый |

**Результат различения:** обязательна продуктовая способность входить через Web и проектировать Android как удалённого клиента. Создание репозиториев именно сегодня, выбор Flutter/Qt/Kotlin, схема БД, офлайн-исполнение и конкретный механизм host bootstrap **пока не утверждены**.

### 1.3. Несовпадающие цели, которые важно не спутать

- **Доступность из разных мест** требует сетевого контракта и устойчивой authority.
- **Переносимость исходников** требует чистых импортных границ и общих DTO.
- **Общность UX** требует design system, совместимых action IDs, доступности и смысловых моделей.
- **Единая история команды** требует persistence, identity, permissions и согласования конкурентных изменений.
- **Универсальная сборка** требует корректной AppDock source/deployment/activation декларации.

Каждая задача имеет собственный проверяемый контракт. Один toolkit, один manifest или одна общая папка самостоятельно не решают остальные задачи.

## 2. Источники, холодный вход и границы достоверности

### 2.1. Текущие direct owners

Холодный вход выполнен по [`stratbox/README.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/README.md), [`AGENTS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/AGENTS.md) и [`_mw/AGENTS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/AGENTS.md). Они согласованно задают важное правило: `stratbox` — библиотечное core без UI и AppDock-интерналов; Windows surface живёт отдельно, Research в `_mw` не превращается в продуктовую истину.

Для текущего приложения проверены [`stratbox-windows/README.md`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/README.md), [`docs/architecture.md`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/docs/architecture.md), [`pyproject.toml`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/pyproject.toml), [`appdock/manifest.json`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/appdock/manifest.json), runtime и execution source-файлы. На момент проверки репозитории `ForestTiger-GH/stratbox-web` и `ForestTiger-GH/stratbox-android` не обнаружены по этим именам. Это **не доказательство** отсутствия экспериментальной работы в иных ветках или локальных каталогах.

Релевантный опубликованный корпус `docs/` прочитан как **кандидатная** модель, а не как уже выполненная Product admission: [Current HOW Windows](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/current-how/windows-application.md), [Future surfaces](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/what/components/future-surfaces.md), [Dependency direction](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/architecture/dependency-direction.md), [Responsibility allocation](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/architecture/responsibility-allocation.md), [Semantic target](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/what/strategy-box/semantic-target.md) и [Quality constraints](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/what/strategy-box/qualities-and-constraints.md).

### 2.2. Предыдущий исследовательский корпус

Релевантны:

- [`02-base-study`: переносимость бизнес-сегментов](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_segments_portability_reuse_architecture_research_2026-10-07.md);
- [`02-base-study`: Web/self-hosted](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md);
- [`02-base-study`: интерфейсные требования](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_windows_interface_requirements_research_2026-10-07.md);
- [`02-base-study`: визуальная система](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_interface_visual_system_research_2026-10-07.md);
- [`02-base-study`: общие настройки](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_system_settings_research_2026-10-07.md);
- [`03-consolidation-research`: тема 07, Product Surface Architecture](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_07_product_surface_architecture_consolidated_research_2026-10-09.md);
- [`03-consolidation-research`: State/Persistence/Collaboration](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_05_state_persistence_collaboration_consolidated_research_2026-10-09.md).

`01-old-notes` использованы как исторические гипотезы, главным образом для отсечения давно вытесненной идеи UI внутри предметного ядра. **Данное исследование не является пересказом темы 07 из третьей ветки:** оно проверяет её на новую постановку разработчика, анализирует физическую повторную используемость, строит матрицу транспортных границ и уточняет минимальный план с альтернативами.

### 2.3. Внешняя платформа

Учитывается предоставленное описание «AppDock — описание продукта и проекта» (узел, managed System/Node/Data, установка, результат, remote/host, agent/capability). Дополнительно проверены верхнеуровневые принципы текущего владельца [`AppDock`](https://github.com/ForestTiger-GH/AppDock) (доступ к репозиторию может требовать разрешений): source manifest как авторитетная частичная декларация, authoring/build, подтверждённая WorldDefinition, release/deployment/runtime truth. **Это разграничение существенно точнее, чем предположение «всё находится в одном JSON manifest».** По внешнему проекту фиксируется только интеграционная поверхность, без переноса его внутренних деталей в публичный код Strategy Box.

Внешние научные/нормативные опоры перечислены в главе 17 с прямыми URL. Их выводы применены к конкретным архитектурным решениям, а не использованы как декларация превосходства отдельного фреймворка.

## 3. Текущее состояние: что действительно работает

### 3.1. Core: переносимость доменных расчётов уже существует

`stratbox` — Python-пакет, сегодня версии `0.8.0` по [`pyproject.toml`](https://github.com/ForestTiger-GH/stratbox/blob/main/pyproject.toml). Домены, parsers, экспортёры, FileStore и другие общие возможности живут вне Windows surface. Важное преимущество: один банковский расчёт уже может быть вызван из ноутбука или обычного Python, ему не нужен Qt desktop. Здесь переносимость означает **повторное использование доменных вычислений на сервере**, а не обязанность исполнять CPython внутри browser/Android.

Старые и новые домены неравномерны: typed Request/Result уже широко применяются, но общий канонический operation contract и registry остаются целевыми работами. Следовательно, интерфейсный слой должен видеть стабильные прикладные use cases, а не динамически произвольные Python-функции.

### 3.2. Windows: значимая application-логика уже отделена, но граница протекает

Текущий `stratbox-windows` версии `0.1.0` по [`pyproject.toml`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/pyproject.toml) содержит:

| Слой | Прямое наблюдение | Что из этого переносимо |
|---|---|---|
| `application/operations/catalog` | OperationSpec, параметры, registry | Семантика descriptor; Python handler ref — **только server/local adapter** |
| `application/scenarios` | Atomic/composite ScenarioSpec, упорядоченные steps, runner | Смысл композиции и правила запуска, если устранить привязки к AppContext/локальному исполнению |
| `application/cases`, `events`, `artifacts`, `logs` | Case, steps, event, artifact/log records | Статусный словарь и идентичности; текущий `path` не годится как универсальная идентичность файла |
| `application/history` | Пять JSON snapshot-файлов | **Только формат текущего local recent history**; это не shared canonical store |
| `application/background` | Registry/UI-store фонов | Декларация, не настоящий scheduler/executor |
| `application/presence`, `assignments` | Локальная модель пользователей и поручений | Семантическая отправная точка, не сетевой shared service |
| `presentation/common/scenario_chat` | Projector: case/event→семантическое сообщение | Действительно ценный Qt-free пример, но сегодня его модели связаны с текущим case model |
| `presentation/qt_desktop` | Виджеты, QSS, signals/QThread, dialogs, host services | Платформенные адаптеры; исходники UI нельзя механически переносить на Web |
| `runtime/context`, `runtime/bootstrap` | Activation, paths, composition | Contract-mapping пригоден для повторного проектирования; bootstrap **сегодня импортирует Qt** |

Это видно непосредственно в [`runtime/bootstrap.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/bootstrap.py): после создания stores и prefs функция `build_runtime()` импортирует `ScenarioCoordinator` из `presentation.qt_desktop`. В [`scenario_coordinator.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) один активный сценарий управляется через `QObject/QThread`. Нельзя выдать такую конструкцию за уже headless application service.

[`scenarios/runner.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/scenarios/runner.py) выполняет шаги последовательно, формирует события, записи логов и артефактов; при `fail_fast` останавливает композицию. Он ценен как прототип **семантики**, но не предоставляет network admission, durable job execution и независимости от закрытия окна.

Текущий [`presentation/common/scenario_chat/projector.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/presentation/common/scenario_chat/projector.py) уже умеет создавать `ScenarioChatMessage` из case/event, выставлять status labels, авторов и placement. Это фактический эксперимент в сторону platform-neutral projection. Однако projector принимает Python stores/classes и генерирует presentation labels, а не транспортный JSON. Для TypeScript/Kotlin его исходник напрямую непереносим.

### 3.3. Три особенно опасные границы

1. **Исполнение привязано к окну.** При одном `QThread`/coordinator процесс является владельцем работы. Его закрытие не даёт гарантии, что сервер продолжит Job. Это недопустимо для обещанного Android/Web запуска на хосте.
2. **История привязана к локальным JSON.** [`HistoryPersistenceService`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/history/persistence.py) пишет пять файлов напрямую, без единой транзакции; ошибки чтения трактует как пустые списки. При нескольких клиентских писателях это не источник истины, а источник расхождений/потери истории.
3. **Файловые пути пересекают границу.** Сейчас результат часто представлен локальным `path`, а управление файлами — локальным файловым explorer. Браузер не знает `C:\...`; Android не имеет права открывать произвольный путь на диске host. Нужны typed file/artifact references и отдельный разрешённый download/preview API.

### 3.4. AppDock интеграция — текущие факты, а не ожидания

В публичном [`stratbox-windows/appdock/manifest.json`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/appdock/manifest.json) указан Connector `contract_version=4.0`, единственный `desktop` surface, `launch_mode=foreground`, `locality=local`, Windows constraint, Python bindings и diagnostics. Нет web/mobile surface, remote job transport или host daemon как работающей декларации. В [`adapters/appdock/entry.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/adapters/appdock/entry.py) проверяются desktop surface и совместная runtime environment для core и клиента.

**Точный version drift:** публичный core — `0.8.0`, а Windows [`pyproject.toml`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/pyproject.toml) требует `stratbox==0.2.1`; manifest в package requirement также закрепляет `0.2.1`. Кроме того, [`README.md`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/README.md) местами называет Connector `3.0`, тогда как manifest `4.0`. Это конкретные случаи, из-за которых нельзя предполагать беспроблемную воспроизводимую установку без проверки resolved package graph и актуализации контрактов.

### 3.5. Состояние новых поверхностей

Отдельных подтверждённых `stratbox-web`/`stratbox-android` в проверенных именах нет. Нет подтверждённой Strategy Box host API, на которую мог бы подключаться мобильный клиент. Указания о будущих Web/Android в [`docs/what/components/future-surfaces.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/what/components/future-surfaces.md) прямо помечены как conditional. Это важно при постановке сроков: начать с публичной клиентской оболочки без реального authority/API означало бы создать демо, а не продукт.

## 4. Базовая архитектурная развилка: где находится прикладная истина

### 4.1. Вариант A — всё остаётся в Windows, Web/Android пробрасывают его экран или запросы

**Достоинство:** наименьший объём начальной переработки. **Цена:** Windows GUI должен быть постоянно запущен, тяжёлая логика и shared state остаются desktop-owned, браузер превращается в тонкий RDP/remote-control, сбой окна рвёт исполнение, авторизация прибивается к окну. При многопользовательской работе появляются гонки и конкурирующие локальные истории. **Отклонить как целевую архитектуру**; допустим только одноразовый локальный prototype или демонстрация.

### 4.2. Вариант B — независимые прикладные реализации в Windows, Web и Android

**Достоинство:** быстрый старт отдельных команд с удобными для каждой платформы фреймворками. **Цена:** три разных набора permission logic, parameter validation, lifecycle, error mapping и артефактных ссылок. Дублируются даже те правила, которые внешне кажутся UI-мелочами. Требование разработчика об общности компонентов нарушается семантически. **Отклонить.**

### 4.3. Вариант C — одна логическая Strategy Box application authority и несколько thin clients

**Достоинства:** единый owner истории и выполнения, право продолжать Job после закрытия браузера, общие контролируемые действия, единые ID и статусы, предсказуемое подключение с телефона. **Издержки:** нужен небольшой headless runtime/API, доступные сетевые адреса, user sessions, durable state, проверки доступа, восстановление subscriptions и отдельное поддержание клиента.

**Рекомендация:** выбрать C как долгосрочную semantic architecture, **без автоматического утверждения физического микросервиса прямо сейчас**. В local Windows profile authority сначала может быть in-process/headless module; при первом действительно доступном Web/Android-host понадобится процесс с отдельным lifecycle. Это экономнее, чем строить микросервисную систему заранее, и честнее, чем называть Qt-worker «хостом».

### 4.4. Почему это не равно «обязательно создать stratbox-host сегодня»

В [`02-base-study` Web/self-hosted](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md) обоснован отдельный будущий `stratbox-host` с длительным lifecycle. В более поздних [`docs/architecture/responsibility-allocation.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/architecture/responsibility-allocation.md) физический owner application authority отмечен **открытым**: модуль, процесс или самостоятельная поставка. Противоречия в самом принципе нет: logical authority одна; место её кода не обязано быть новым repository с первого коммита.

**Условие выделения репозитория `stratbox-host`:** одновременно появились (а) собственный headless entry point и release, (б) persistence+authorization+Job API, (в) независимое от Desktop process управление жизненным циклом и (г) самостоятельные тесты/ответственный владелец. Пока этого набора нет, репозиторий с README и заглушками добавляет административную сложность, а не архитектурную ценность. Когда эти условия соблюдены — самостоятельный `stratbox-host` рационален и платформенно-нейтрален; называть его `-linux` не следует.

## 5. Матрица переносимости: что общее, а что является адаптером

Обозначения: **C** — единая *каноническая* реализация на сервере/в application owner; **S** — общий *семантический контракт*, локальная реализация по языку/платформе; **A** — платформенный адаптер; **N** — в первом релизе отсутствует.

| Модуль / ответственность | Windows | Web | Android 1.0 | Вид повторного использования | Нельзя делать |
|---|---|---|---|---|---|
| Банковская/макроаналитика и статистика | Local или host | Host | Host | **C:** `stratbox` | Дублировать pandas/solver на фронте |
| Operation IDs, вход/выход, side effects | Общий contract | Общий contract | Общий contract | **C/S:** canonical descriptor+DTO | Генерировать имена операций из названий кнопок |
| Scenario/cascade planning, validation | Application authority | Application authority | Application authority | **C** | Три реализации plan/apply |
| Job admission, execution, cancellation | Local/host authority | Host authority | Host authority | **C** | Считать UI worker authoritative Job |
| Work/Run/Job/Attempt statuses | Тот же смысл | Тот же смысл | Тот же смысл | **S** | Превращать disconnect в job failure |
| Actor identity, permissions, risk approval | Server/local authority | Server authority | Server authority | **C** | Доверять `allowed` из client JSON |
| Chat/Work projection | Qt bridge | JS projection | Mobile projection | **S**, частично общая реализация | Передавать Qt objects по сети |
| Forms metadata и validation codes | Schema driven | Schema driven | Short forms | **S** | Считать HTML/Qt widget общим контрактом |
| Общие design tokens, icon semantics | Qt mapping/QSS | CSS variables | Compose/theme mapping | **S** | Копировать QSS в CSS «один в один» |
| Workspace / Artifact identity | Logical refs | Logical refs | Logical refs | **S/C** | Отдавать абсолютные host paths |
| Filesystem navigation | Native explorer | Authorized listing API | Authorized picker/download | **A** | Давать browser прямой FileStore |
| File open/reveal/share | Shell APIs | Browser APIs | Android intents | **A** | Общий `open_path(C:\...)` |
| Notifications | OS/tray | In-app/browser optional | Android notifications | **A/S** | Считать notification источником статуса |
| Clipboard, drag-drop, hotkeys | Qt/OS | DOM/browser | Android intents/gestures | **A** | Единые клавиши/gestures на всех формах |
| Local preference storage | Desktop app | Browser storage | Mobile storage | **A/S** | Синхронизировать геометрию Windows на телефон |
| Public login/session | Native session broker | Browser session | Mobile auth adapter | **A/C** | Hardcoded plaintext credentials |
| Background UI execution | Qt bridge | No local executor | No local executor | **N/A** | Фоновый browser/phone timer как Job owner |
| Offline heavy analytical execution | Optional local Windows | N | N | **Future N** | Тащить весь Python core в APK |
| Platform activation/deployment | AppDock adapter | AppDock boundary by supported profile | AppDock boundary by supported profile | **A** | Считать manifest runtime authority/ACL |

### 5.1. Классы кода в исходном проекте

**Тип I — чистые семантические модели.** Stable enum/status, reference types, results, progress, effective actions, schema validation errors, presentation tokens. Их можно держать как Python dataclasses на сервере, JSON Schema/OpenAPI как переносимую спецификацию, TypeScript/Kotlin models как сгенерированные или тестируемые отображения.

**Тип II — application use cases.** `prepare_scenario`, `validate_params`, `submit_run`, `cancel_run`, `get_job`, `list_artifacts`, `approve_action`; имеют единую авторитетную реализацию. Клиентские SDK только вызывают их.

**Тип III — read projections.** Pure mapping from authorized application DTO to `ScenarioChatMessage`, `RunCard`, `ArtifactRow`, `InspectorView`. Повторное использование может быть исходным Python-кодом в desktop и на сервере; в браузере — shared data fixtures и contract tests (либо общий TS-код Web/Android, если будет выбран TypeScript stack).

**Тип IV — platform bridges.** Qt signals, DOM event handling, CSS, Android Activity lifecycle, file chooser, `Intent.ACTION_VIEW`, Keychain/Keystore, push, share sheet. Функции могут реализовывать одинаковые порты, но иметь разные модули и исходники.

**Тип V — deployment/activation adapter.** Читает версионированный внешний контекст, переводит в `NodeCapabilities`, `ApplicationEndpoints`, `AppIdentity`, `DataBindings`; затем application не импортирует сторонний SDK в каждом use case.

### 5.2. Что нельзя называть платформенно-нейтральным

- Python-класс, который импортирует PySide6 только по ленивому пути, **всё равно платформенно-зависим**, если headless/Android package не может собрать application без Qt.
- `OperationSpec` с `handler='stratbox_windows...:function'` пригоден для server/local Python, но его `handler` нельзя отдавать веб-клиенту как исполняемую инструкцию.
- `Path` и `QDateTime` внутри API-схемы ломают межъязыковой контракт.
- Единый JSON `AppContext` с пользовательским токеном, путями и настоящими секретами нельзя пересылать клиентам. Shared DTO должны проходить отдельную безопасную селекцию.
- «Общая компонента» в Figma или наборе SVG — это общность внешнего дизайна, но не общность lifecycle/permissions.

## 6. Матрица клиентских профилей и реальных пользовательских задач

### 6.1. Какие профили нужны

| Поведение | Windows local | Windows remote | Browser desktop/tablet | Android phone | Android tablet |
|---|---|---|---|---|---|
| Перечень узлов/соединение | локальный контекст | да | да/выбранный endpoint | да | да |
| Просмотр чатов/работ/истории | да | да | да | да, compact | да |
| Запуск сценария с несколькими параметрами | да | да | да | выборочно | да |
| Отмена/повтор, если поддерживает сервер | да | да | да | подтверждённые случаи | да |
| Статусы/прогресс нескольких Jobs | да | да | да | да | да |
| Артефакты | открытие/reveal | preview/download | preview/download | preview/share | preview/download |
| Workspace файловый проводник | полный | разрешённый | разрешённый | облегчённый/позже | расширенный |
| Конструктор сложных каскадов | возможно | возможно | возможно | N первого этапа | позднее |
| Системная диагностика и логи | полно | ограничено ролью | кратко+по правам | кратко | кратко+детали |
| Локальные вычисления без хоста | возможны | N | N | N | N |
| Офлайн чтение и drafts | необязательно | частично | опционально | позднее/ограниченно | позднее |
| Офлайн очередь опасных запусков | N | N | N | N | N |

**Вывод по Android:** первый релиз разумно определять **выполняемыми сценариями пользователя**, а не процентом портированных экранов: выбрать работу, увидеть статусы, запустить разрешённую команду с небольшим набором параметров, получить/открыть результат, увидеть предупреждение, подтвердить допустимое действие. Располагая этими возможностями, Android является реальным клиентом Strategy Box, хотя в нём нет сложного Excel preview, полного файлового менеджера и model-building UX.

### 6.2. Нюанс Web: это не Android в большом окне

Browser interface нужен и на рабочем ПК. Там пользователь захочет привычные трёхколоночные рабочие области, большие таблицы, сравнение результатов, клавиатуру, drag/drop файлов и быстрый просмотр артефактов. Mobile Web может быть компактным, но основной Web нельзя свести к status companion. Направления Work/Chats, Scenarios, Runs, Artifacts/Workspace доступны по единым `kind/id`; их расположение зависит от ширины окна, а не названия платформы.

### 6.3. Что делать с веб-версией на телефоне

Адаптивный Web/PWA рационально выпустить **раньше** отдельного Android APK как минимально дорогой способ проверить remote API, мобильную эргономику и реальный спрос. Однако PWA не гарантирует равноценность native Android по глубокой интеграции с OS, push, background и policy/security возможностей. MDN документирует service worker caching и ограничения фоновой работы (см. §17). **PWA — первый самостоятельный мобильный доступ; Android native — решение по действительно нужным native задачам**, а не обязательный дубликат всех Web screens.

## 7. Дизайн-система: одинаковая начинка при разных представлениях

### 7.1. Четыре уровня визуальной общности

1. **Semantic roles:** `danger`, `warning`, `success`, `pending`, `stale`, `unknown`, `muted`, `selected`, `action.primary`, `artifact.preview`.
2. **Design tokens:** цвет/контраст, типографика, плотность, spacing, radii, icon families, elevation/motion roles. Хранить платформенно-нейтральные значения и mode/theme variants, а не QSS stylesheet как эталон.
3. **Semantic components:** `RunCard`, `ScenarioForm`, `WorkTimeline`, `ErrorSummary`, `ArtifactChip`, `NodeStatus`, `ApprovalAction`. Контракт определяет состояние и доступные действия.
4. **Renderer compositions:** Qt Widgets, web HTML/CSS, Android Compose/Qt Quick/React Native. Эти уровни владеют touch/keyboard/navigation/layout и платформенной доступностью.

Пример токенов как **предложение**, а не существующий API:

```json
{
  "schema_version": "candidate-1",
  "color.status.running": "#2164A8",
  "color.status.warning": "#946200",
  "space.control.compact": 8,
  "type.body.role": "ui-body",
  "motion.progress.role": "indeterminate",
  "icon.artifact.excel": "table-sheet"
}
```

Отдельные значения здесь **иллюстративные**, без требования использовать указанные цвета. В реальном дизайне цвет не заменяет текстовый статус, а контраст проверяется для всех тем.

### 7.2. Один RunCard — три адаптации

**Windows:** строка/карточка в чате с раскрытием Inspector, контекстным меню, hover и клавиатурными shortcuts. **Web:** тот же статус и действия, но нативные ссылки/focus/ARIA, адаптивная ширина и доступная навигация клавиатурой. **Android:** короткая карточка и раскрываемый экран, крупные touch targets, bottom sheet для вторичных действий. `Run.id`, `status`, `progress`, `author`, `artifacts`, `available_actions` при этом одни.

### 7.3. Почему прямой перенос Qt в браузер не является хорошим решением

Qt Widgets создаёт настольные контролы, а браузер живёт DOM/focus/link/security моделью. Remote desktop/streaming Qt даст визуальное сходство, но потеряет естественный Web UX, адаптивность, screen reader compatibility, нормальную многовкладочность и оптимальную работу по медленной сети. Web должен уметь открывать deep link `.../runs/<id>` и рендерить DTO. Временная web-обёртка над desktop экраном допускается только как эксперимент, не как целевой surface.

### 7.4. Accessibility и «косметические» адаптеры

WCAG 2.2, клавиатурный фокус, масштабирование, screen reader semantics, target sizes, reduced motion — часть качества продукта, а не декоративный факультатив. Android adaptive window size classes ориентированы на **фактическое окно**, включая foldables/desktop mode; это лучше жёсткого branching `if platform == android`. Конкретные источники: [W3C WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/), [Android window size classes](https://developer.android.com/develop/adaptive-apps/guides/use-window-size-classes).

## 8. Сопоставление технологических вариантов Web и Android

### 8.1. Честный набор альтернатив

| Вариант | Общий исходный UI-код | Сильные стороны | Основной риск | Вывод для Strategy Box |
|---|---|---|---|---|
| **Web React/TypeScript + Android Kotlin/Jetpack Compose** | Низкий; DTO/tokens/tests общие | Нативные platform patterns; зрелый web DOM; глубокий Android lifecycle | Два UI stack, две группы компонентов | **Надёжный default** при приоритете качества поверх буквального shared UI |
| **React/TypeScript Web + React Native/Expo Android (RN Web optional)** | Высокий в state/hooks/части components | Общий TS, модели, form logic, привычный mobile stack; Expo Web | Web desktop data-grid/DOM semantics могут потребовать web-only renderer; RN Web не идентичен native | **Приоритетный прототип**, если важна экономия двух клиентских команд |
| **Flutter Web + Flutter Android** | Очень высокий в Dart UI | Один renderer/design system и responsive widgets; strong native mobile story | Canvas-first web, отдельный a11y bridge, меньше естественных DOM affordances; возможно избыточно для отчётного Web | Интересен при mobile-first, нуждается в a11y/perf spike |
| **PySide6/Qt Quick Android + отдельный Web** | Повторное использование Python logic частично; UI нет | Сохраняет знакомый Python/Qt stack; Qt for Python поддерживает Android deployment | CPython/wheels/toolchain, Android lifecycle, отсутствие прямого переноса Widgets, отдельный browser | Экспериментальный кандидат для Android, **не обещание cheap code reuse** |
| **Адаптивный Web/PWA без native Android на старте** | Один Web UI | Самый быстрый доступ с ПК/телефона; единый browser client; установка из браузера | Native notifications/background/share и OS policy по браузерам неодинаковы | **Рациональный первый выпуск**, затем Android по доказанным задачам |
| **Qt desktop через remote control/WebAssembly** | Внешнее сходство с Windows | Небольшой начальный перенос presentation | Browser-native semantics и независимость сильно ограничены | Не выбирать как целевую платформу |

Источники для оценок: [Qt for Python Android deployment](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-android-deploy.html) (APK/AAB и Unix-host toolchain); [Expo universal Web](https://docs.expo.dev/workflow/web/) (React Native for Web); [Flutter Web accessibility](https://docs.flutter.dev/ui/accessibility/web-accessibility) (canvas renderer и semantics DOM); [Flutter Web FAQ](https://docs.flutter.dev/platform-integration/web/faq) (сферы применимости). Возможность сборки показывает наличие механизма, но **не** проверяет производительность, accessibility и fit для Strategy Box.

### 8.2. Почему я не рекомендую немедленно унифицировать все три интерфейса на одном toolkit

Windows сегодня — работающий Qt surface, включая набор устоявшихся виджетов и рабочие файлы. Переход на Flutter/React только ради shared source означал бы полную переписывание Windows без доказанного выигрыша. Пользовательское требование — общие **компоненты по смыслу**, а не один runtime. Лучше сохранить Qt для Windows, предоставить Web независимый рендерер и решить Android после API prototype.

**Два реалистичных пути:** (A) Web React/TS + Android Compose — наименьший риск качеству каждой поверхности; (B) Web React/TS + Android RN/Expo — больше shared TS/source, если реальные экранные модели позволяют. Выбор между ними можно принять по двум прототипам одного и того же ScenarioForm+RunTimeline. Полноценный Web MVP в обоих случаях будет полезен независимо от выбора Android toolkit.

### 8.3. Когда Flutter выигрывает

Если после проверки пользователи в основном работают на мобильном устройстве, важны строгая визуальная согласованность анимация/brand-компоненты и нативные режимы, а browser становится преимущественно app-like canvas surface, Flutter может значительно сократить раздвоение UI. Но для отчётного, табличного и клавиатурно-насыщенного интерфейса Web ограничения доступа к DOM и семантике следует проверять практически; объявлять Flutter «заведомо хуже» было бы некорректно.

### 8.4. Что делать с существующими Python dataclasses

Python модели допустимо оставить internal implementation. Для внешних клиентов нужен **языконезависимый контракт**: схемы типов (JSON Schema/OpenAPI), стабильные enum/status, IDs и эталонные test fixtures. Если Windows локально вызывает Python classes, а Web/Android получают JSON, должны существовать contract tests: `serialize(parse(x))`, schema validation, отсутствие platform-only полей, единые error codes. Не нужно создавать универсальный генератор всех Python classes; выделить только реально используемые external DTO.

## 9. Минимальный общий прикладной контракт

### 9.1. Два интерфейса, которые нельзя смешивать

- **Domain/Operation API** — `stratbox`, Request/Result, вычисления, источники, normalizers и exporter. Работает в Python/Jupyter и вызывается application host.
- **Product Application API** — Strategy Box, идентичности работ/запусков, сценарные планы, права, история, результаты, действия, подписки, стабильные статусы. Может обслуживать Windows local или удалённых клиентов.

Третий интерфейс **Platform Integration Adapter** принадлежит границе AppDock; он поставляет проверенные сведения Node/Data/runtime/activation и managed lifecycle. Нельзя заменять Product API непосредственным вызовом неограниченного AppDock endpoint.

### 9.2. Малый набор контрактов для MVP

| Contract | Минимальная задача | Owner truth |
|---|---|---|
| `GET /capabilities` | Показать разрешённые функции | Host authority |
| `GET /scenarios/{id}/form` | Отдать семантическую схему входа | Application + core definitions |
| `POST /runs` | Подать команду на запуск с idempotency key | Application |
| `GET /runs/{id}` | Получить исход, progress, допустимые действия | Application |
| `GET /events?cursor=...` | Получить изменения после snapshot | Application |
| `GET /artifacts/{id}` | Метаданные результата и безопасность доступа | Application |
| `GET /artifacts/{id}/content` | Скачать авторизованные bytes | Application→FileStore |
| `GET /session` / `POST /logout` | Auth/session identity | Auth adapter + application |
| `GET /node/capabilities` | Активные возможности узла | AppDock adapter→Application-safe projection |

Все endpoint paths выше — **иллюстративный design candidate**, а не существующее API. Для первой версии можно объединить или переименовать endpoints, но их смысл должен сохраниться.

### 9.3. Предлагаемый DTO `RunProjection`

```json
{
  "contract_version": "candidate-1",
  "run_id": "run-001",
  "scenario_id": "escrow.history.export",
  "node_id": "node-001",
  "author": {"id": "user-002", "display_name": "Аналитик"},
  "revision": 17,
  "as_of": "2026-10-10T00:00:00Z",
  "status": "running",
  "progress": {"stage": "fetch", "current": 3, "total": 8},
  "artifact_refs": [],
  "available_actions": [{"id": "run.cancel", "available": true}],
  "diagnostic_summary": null
}
```

`as_of` — время server snapshot; `revision` — защита от гонок; `display_name` — UI label, не security principal. `available_actions` — подсказка для интерфейса, **не окончательное разрешение**: при `POST /runs/{id}/cancel` сервер повторно проверяет полномочия и состояние.

### 9.4. Рецепт поступления команды

```text
UI submit with idempotency key
         ↓
API authenticates and authorizes principal
         ↓
validate parameters + current capability + effects
         ↓
create durable Run/Job and return accepted identity
         ↓
executor runs on host, independently of browser/window
         ↓
write result / publish artifacts / record terminal outcome
         ↓
clients observe by snapshot + event subscription
```

В ответе на `submit` различать `accepted`, `rejected`, `needs_approval`, `conflict`, `unknown outcome`; HTTP timeout сам по себе не означает, что операция не стартовала. Серверный ключ идемпотентности должен устранять случайный второй запуск после повторного клика/сетевого retry.

### 9.5. Частота обновлений: REST + SSE или WebSocket

Базовое предложение: **HTTP queries/commands + SSE** для событий `run_started`, `progress`, `run_finished`, `artifact_published`, `problem`. SSE имеет `id` и `retry` для reconnect, поддерживается в браузерах: [MDN EventSource](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events). WebSocket оправдан, если возникнут действительно двусторонние high-frequency потребности: interactive terminal, совместное редактирование, потоковый кооперативный control. В остальных случаях его обязательный протокол reconnect/heartbeat/ordering увеличивает сложность без соразмерной пользы.

**Защита от пропусков:** `GET snapshot` с `revision/cursor` → subscribe «после cursor» → deduplicate события → gap/expired cursor → refetch snapshot. Heartbeat/stream disconnect никогда не должен переводить Job в `failed`; он переводит только client sync в `stale`/`unknown`.

### 9.6. Контракты ошибок

Принять [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html) как ориентир для transport-level ошибок: `type`, `title`, `status`, `detail`, `instance` плюс `error_code`, `correlation_id`, `retryable` при необходимости. Предметные ошибки остаются типизированными внутри Result. Не путать:

- `not_found` — объект действительно отсутствует;
- `not_allowed` — текущий principal не имеет доступа;
- `offline/stale` — клиент потерял связь;
- `rejected` — действие не принято;
- `failed` — принятое выполнение закончилось ошибкой;
- `unknown_effect` — команда могла породить внешний эффект; требуется сверка;
- `partial` — завершилась только часть шагов, эффектов или выгрузок.

Это особенно важно при разных клиентах: красивые общие иконки бесполезны, если Android называет сетевой обрыв «отменой».

## 10. Публичный Web, авторизация и минимально достаточная безопасность

### 10.1. Где возникает непреодолимый минимум

Разработчик прямо просит не тратить месяцы на безопасность, и это рационально для малой ранней команды. Однако **домен, доступный из Интернета, меняет доверительную границу**. Никнейм для внутреннего командного чата может быть свободным display label, но никнейм **не удостоверяет личность**, когда URL открыт извне. У каждого HTTP action должен быть проверенный principal.

Существенное различие:

- **Предварительно созданные учётные записи** — хороший минимальный продуктовый выбор.
- **Логин/пароль захардкожены в приложении, frontend JS или Git-репозитории** — плохой security implementation. Для публичного домена его следует исключить уже в MVP.

### 10.2. Минимальный auth-профиль (реальный MVP)

1. Оператор создаёт 2–20 учетных записей в конфигурации/SQLite host или через CLI `create-user`. Регистрации через сайт и почтового восстановления пока нет.
2. Пароли хранятся только как медленные salted hashes — предпочтительно Argon2id (OWASP). Секреты/ключи сеансов — отдельно от исходников и source manifest.
3. HTTPS для всего домена, TLS termination в reverse proxy/ingress либо подтверждённом платформенном адаптере.
4. После логина server-side session или подписанный session mechanism, в браузере secure cookies `HttpOnly`, `Secure`, `SameSite`; для state-changing actions — CSRF-защита и origin validation.
5. Rate limit на логин, ограничение brute-force, отзыв/истечение сеанса, logout, серверная проверка object-level доступа к каждому Run/Artifact.
6. По умолчанию API слушает `127.0.0.1` или приватный trusted interface; public binding возможен только при валидированном auth+TLS-facing deployment.
7. Логи доступа, failed logins и опасные действия доступны оператору, но private токены, пароли и технические секреты не отображаются в общих чатах.

Основания: [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [OWASP CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html). Это маленький стандартный слой; можно использовать зрелую библиотеку аутентификации, а не писать security-движок самостоятельно.

### 10.3. Почему пока не требуется сложный IAM/OIDC

Для небольшого self-hosted узла с известными участниками создание собственного почтового подтверждения, password-reset сервиса, MFA платформы и учётного сервера добавляет множество новых failure modes. Self-service registration сегодня не требуется разработчиком. В будущем при корпоративном или публичном росте рекомендуется адаптер готового внешнего OIDC identity provider, без смены внутреннего `PrincipalId`. Нельзя превращать первый MVP в identity SaaS.

**Отдельно:** если доступ организован *только* через доверенный корпоративный ingress или VPN, он всё равно должен передавать проверяемую identity; наличие VPN не делает клиента автоматически полномочным запускать любую операцию.

### 10.4. Разделить три идентичности

- `principal_id` — доказанное основание авторизации на сервере;
- `participant_id/display_name` — видимость в чатах, поручениях, цвет/аватар;
- `device_id/session_id` — устройство, browser tab/client session, подключение и диагностический контекст.

Идентичность `run.author` записывается сервером по principal, а не принимается от произвольного поля `author_id` из browser POST. Это минимально важное изменение относительно нынешней локальной «доверенной команды».

### 10.5. Общее пространство чатов vs разграничение данных

Пользовательский замысел: участники одного узла видят общие работы/чаты, ошибки и кто запустил задачу. Это совместимо с простым membership scope `node_member`: внутри узла все видят разрешённую shared timeline. Но **общий чат ≠ открытый raw log/filesystem**. Artifact, техническая трасса, credentials и hidden runtime paths требуют отдельных фильтров/ссылок. На MVP достаточно ролей `operator/admin` и `member` плюс права на отдельные рискованные действия, а также постоянной проверки membership. Если вообще все члены узла имеют одинаковые полномочия, это должно быть **явно принято как продуктовая политика**.

## 11. Как AppDock должен определять host/client роли, не поглощая Strategy Box

### 11.1. Четыре разных этапа

**Этап 1 — Source manifest (`appdock/manifest.json`).** Репозиторий декларирует поддерживаемые surfaces, typed activation, зависимости/требования и частичные authoring defaults. Это *исходная авторитетная декларация* поставки. Она не должна содержать runtime secrets, пароли пользователей, произвольные адреса конкретных внутренних узлов или физические пути машины.

**Этап 2 — AppDock Studio/authoring.** Для конкретной поставки дополняются допустимые отсутствующие поля, выбирается target platform/install/Node/Data/Entry конфигурация. Объявленное source-manifest значение должно сохранять собственную authority. Не следует считать, что Studio «переписывает всё содержимое manifest»: действующий внешний owner различает source truth и authoring definition.

**Этап 3 — Release/deployment truth.** Поставка получает resolved package identities, physical bindings, доступные runtime environments и surface startup points. Это определяет, какие executable/worker/API компоненты действительно установлены и где.

**Этап 4 — Activation/runtime.** При каждом запуске Strategy Box получает типизированный, проверенный handoff: `node_id`, `role`, `endpoint`, `data_binding`, `runtime_capabilities`, `identity/session hints` по поддерживаемому контракту. Strategy Box валидирует его, выбирает local/remote application backend и проверяет реальные permission/effect условия **на момент выполнения**.

Важно: только первые три этапа определяются авторингом/сборкой; фактический `host connected`, `authenticated`, `worker healthy`, `artifact accessible` выясняются **после запуска**.

### 11.2. Матрица итоговых профилей поставки

| Профиль поставки | Компоненты | Где данные/исполнение | Что открывается | Обязательный handshake |
|---|---|---|---|---|
| Windows локальная | Qt + local authority + core | ПК пользователя | Desktop | local activation/data root |
| Windows remote client | Qt + remote client adapter | Host | Desktop | endpoint + session + capabilities |
| Web host deployment | HTTP/API app authority + core/worker + web assets | Host | HTTPS domain | server configuration + auth + node binding |
| Web only client assets | Browser JS/CSS | Host (удалённый) | HTTPS origin | session/API discovery |
| Android companion | APK/client | Host | Android | endpoint, session, node/feature discovery |
| Future Android local compute | APK + platform-specific core runtime | Телефон/host selectable | Android | local executor/profile; **не MVP** |

Эта таблица — **целевой design space**. Из текущего Connector `4.0` Windows manifest доказан лишь первый локальный desktop-путь, причём его зависимости требуют исправления. Наличие `Node`, `Data` и `surface` как слов в AppDock не доказывает наличие нужного remote lifecycle.

### 11.3. Не проектировать выдуманный AppDock API

Для незрелой платформы выбрать **Anti-Corruption Layer**: единственный `AppDockActivationAdapter` и, позднее, `AppDockNodeTransportAdapter`. В остальном продукт работает через собственные `NodeContext`, `ApplicationEndpoints`, `DataBinding`, `PlatformCapabilities` и `LaunchDiagnostics`. Отсутствующий platform feature возвращает явное `unavailable/unsupported`, а не silently emulated API. Это позволит обновлять AppDock без рефакторинга всей бизнес-логики или UI.

### 11.4. Риск противоречивых источников полномочий

Если AppDock выдал «узел host», а Strategy Box runtime ещё не поднял executor, клиент должен получить `node.ready=false` и понятный статус. Если manifest допускает remote, но release собран без API process, доступный profile считается **неподдерживаемым**. Если клиент показывает `can_cancel=true`, server command всё равно проверяет permission/status. Нельзя закреплять право на выполнение в одном только compile-time manifest.

## 12. Persistence, конкуренция и связь с другими темами

Тема 07 не должна заново разрабатывать всю БД, протокол задач или event sourcing. Однако Web/Android принципиально заставляют определить их минимальную ответственность.

**Authority boundary:** локальный Windows может хранить свои размеры панелей, выбор вкладки и draft формы, но shared `runs/jobs/messages/artifacts/assignment status/read receipts` должны жить у владельца узла. Один объект — один authoritative writer/logical owner. Не каждое состояние надо переносить на сервер.

**Минимальная база:** один узел с единым backend-writer разумно начинать с SQLite при проверенных транзакциях/locking, сохранении на **локальном** диске хоста и backup-процедуре. При нескольких API/worker процессах, разных машинах, тяжёлой конкурентной записи или горизонтальном масштабировании PostgreSQL имеет преимущества. Выбор СУБД — отдельная тема 03; здесь важен **типизированный StateStore-port** и транзакционная атомарность.

**История:** локальные пять JSON-файлов Windows могут послужить импортным источником, но не стать network database. Миграция history требует id mapping и тестов на потери/повторы. Обратная совместимость кода не требуется; сохранность реальных пользовательских данных требует отдельного migration plan.

**Конкуренция:** два пользователя запускают разные сценарии в двух чатах. Блокировка единственным desktop coordinator непригодна. Сервер должен иметь scheduler/admission с configurable concurrency; resource conflicts (тот же output file, shared directory, data cache) решаются отдельно. Можно ограничить CPU-сценарии одной тяжёлой задачей одновременно, но это **ресурсная политика host**, а не глобальная блокировка UI.

**События:** хранить durable event/cursor только для действительно значимых статусов/артефактов. Высокочастотный progress можно агрегировать, показывая клиентам последнюю актуальную проекцию. Для скачивания крупного XLSX использовать поток/контролируемые bytes, а не передавать его JSON в чат.

**Публикация:** `result computed` ≠ `artifact published`. Пока физическая запись/валидация файла и выдача прав/metadata не подтверждены, Web/Android получают промежуточный `pending/failed/unknown` status, а не активную кнопку Download.

## 13. Офлайн: что полезно оставить, а что преждевременно

Три различных «офлайна»:

1. **Offline UI:** клиент показывает last synced read-only данные, когда сеть пропала. Достаточно для будущего PWA и Android.
2. **Offline drafts:** пользователь вводит параметры/текст, которые ещё не отправлены. Их можно хранить локально при соблюдении сроков и защиты конфиденциальности.
3. **Offline execution:** телефон скачал источники/код и сам воспроизводит расчёт. Требует отдельного Android Python/toolchain/data/storage profile, которого пользователь сейчас не просит.

Для MVP принять **онлайн по умолчанию** с честным экраном `connection lost / last synced` и сохранением локальных черновиков. Кэшировать содержимое файлов только после оценки назначения/доступа. Автоматически отправлять опасную команду из автономной очереди после reconnect **не следует**: могли измениться данные, права и эффект. Использовать повторное подтверждение/новый effect plan.

MDN [Caching PWAs](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Caching) подчёркивает компромисс между freshness и offline; [Offline/background](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Offline_and_background_operation) прямо отмечает, что service worker не является бесконечно живущим process. Поэтому делать browser background worker владельцем тяжёлой банковской задачи — архитектурная ошибка.

## 14. Физическая схема репозиториев и минимальная реализация

### 14.1. Рекомендуемое разграничение ownership

```text
ForestTiger-GH/
  stratbox/                   # Python domain core, public-neutral API
  stratbox-windows/           # Qt Windows client (existing)
  stratbox-web/               # browser UI (after first real commit)
  stratbox-android/           # Android client (after toolkit spike)
  stratbox-host/              # OPTIONAL future headless authority/release
```

`stratbox-host` по смыслу вероятен; он может появиться **до Web release**, когда его lifecycle станет самостоятельным. Если требуется прямо сейчас создать только два дополнительных репозитория, можно зарезервировать `stratbox-web` и `stratbox-android`, но **не нужно копировать в каждый по версии `application/scenarios/runner.py`**. Источник общей прикладной логики должен оставаться один; его физический owner фиксируется отдельно.

### 14.2. Нужен ли `stratbox-shared` сразу

**Рекомендация: нет, пока нет реального второго потребителя общего исходного кода.** Пакет shared UI state на Python не поможет TypeScript frontend; общий протокол/fixture поможет. Начать с `contracts/` (schemas/fixtures) у фактического application owner и выдачи versioned schemas клиентам. Если позже Web и Android оба TypeScript, можно ввести отдельный `strategybox-client-contracts` TS package; если Android Kotlin, SDK генерируется из OpenAPI. Самостоятельный публичный repository design tokens также нужен только при отдельном release/owner, иначе достаточно совместимого catalog файлов.

### 14.3. Что делать непосредственно внутри `stratbox-windows`

- Убрать из `runtime/bootstrap` создание конкретного `ScenarioCoordinator`, ввести Qt-free application coordinator/interface; Qt signals пусть переводят события из application projection в виджеты.
- Выделить transport-neutral параметры, результаты, action descriptors и contract tests; реальные Python handlers остаются внутри local/host executor.
- Разделить user-local UI preferences и durable shared state; операции с артефактами и файлами, завязанные на прямые пути перенести за `WorkspaceProvider` и logical references.
- Принять корректные current `manifest/pyproject` версии и убрать устаревшие smoke expectations.
- Сохранить существующий рабочий Qt UX; переписывать весь интерфейс ради Android сейчас не нужно.

### 14.4. Вертикальный срез, который проверяет архитектуру честно

Один функциональный опыт лучше десятка пустых абстракций: **«экспорт истории эскроу»** или простой безопасный CBR collector (для самого первого среза ещё проще `system.diagnostics`, но он не тестирует артефактную границу).

Полный путь:

```text
Windows/Web/Android DTO fixture
  → scenario selection and identical semantic parameters
  → host validates and accepts Run once
  → stratbox core builds actual output
  → publishes artifact ref
  → returns events / status / download capability
  → each client renders same status and correct action
```

Нужен второй негативный срез: **потерять сеть после `POST /runs`, но до HTTP-ответа**. Клиент повторяет с тем же idempotency key; host не создаёт вторую работу; клиент находит первый Run. Третий: пользователь не имеет прав на артефакт — ссылка в чате не раскрывает байты. Четвёртый: закрытие Windows/Web процесса не останавливает host Job.

## 15. Acceptance tests и доказательства готовности

### 15.1. Контрактный gate без GUI

1. Импорт `application`/`presentations.semantic` в пустом Python environment без PySide6 успешен.
2. Import audit подтверждает, что core не импортирует clients, а portable application не импортирует Qt/system `Path.open`.
3. Python serializer ↔ TS/Kotlin generated/parser models проходят одни JSON fixtures.
4. `OperationDescriptor` содержит stable ID, typed input, side effects, output/available actions; сетевые DTO не включают Python handler refs.
5. Состояния `running`, `success`, `failed`, `cancelled`, `unknown` корректно рендерятся на каждом клиенте.

### 15.2. Multi-client behavioural tests

| Кейс | Условие приёмки |
|---|---|
| Два клиента запускают разные jobs | Обоим выданы разные Run IDs, оба job наблюдаемы; concurrency admission соблюдает ресурсные лимиты |
| Два клиента повторяют запрос с одинаковым idempotency key | Один логический Run, клиентам возвращается тот же результат admission |
| Web закрыт при `running` | Job продолжает работать, новый Web session его видит |
| Android offline при job success | Android сообщает `stale`, после reconnect получает actual terminal state |
| Смена роли участника в другом клиенте | Следующее action permission пересчитано на сервере; старое `available_actions` не даёт доступ |
| Обновление source/action descriptors | Старый form draft проходит revalidation; устаревший effect plan отклоняется/просит подтверждение |
| Перенос/удаление файла на host | Preview/download выдаёт `missing/unavailable`, но не чужой файл с похожим именем |
| Artifact не полностью опубликован | Нет ложного успешного download; статус публикации диагностируем |
| Ошибка AppDock remote capability | Явное unsupported/degraded, приложение не падает из-за отсутствующего неформализованного метода |
| Android перезапускается / экран вращается | Серверный run не теряется; local draft/selection восстанавливается по UX-политике |
| Browser user вводит путь `../` | API не выходит за разрешённый namespace, сервер не возвращает реальные system paths |
| Ошибка логина / brute-force | Rate limit и равномерное сообщение; raw credentials не появляются в shared events |

### 15.3. UX/performance/a11y spike

Измерить на имеющихся медленных рабочих ПК и среднем Android: cold load, открытие 1000+ элементов истории, рендер больших form schemas, переподключение SSE при Wi-Fi→мобильной сети, download 20/200 МБ, screen reader/keyboard, portrait/landscape/tablet. Пороги задавать после первого baseline, без произвольных обещаний. На Web отдельно проверить DOM accessibility и data table behavior; в Android проверить системные notifications/share, touch target и состояние при background/kill.

### 15.4. AppDock integration gate

В отдельном проверочном контуре платформы подтвердить: manifest/schema validation, сборку нужного target profile, exact dependency graph, правильные resolved Node/Data bindings, версию activation context, runtime endpoint discovery, запуск диагностики, отключение/восстановление соединения и безопасное обновление. **Ни один такой тест нельзя объявить прошедшим на основании только документации или текущего Windows manifest.**

## 16. Согласованный план по шагам, без преждевременных подсистем

**Этап 0 — зафиксировать Product Decisions (коротко).** Принять: Web обязателен; Android remote-first; общий semantic contract; публичный Web только с аутентификацией; default shared-node scope; local/offline heavy Android вне MVP. Определить, что именно будет доступно первому Web пользователю: Threads/Runs/Scenarios/Artifacts или урезанный диагностический режим.

**Этап 1 — исправить Windows границы, не ломая UX.** Версионирование зависимостей и manifest; Qt-free orchestration; generic `ExecutionBackend`, portable descriptors/read models; contract tests. Не копировать код на будущие платформы до этого шага.

**Этап 2 — первый независимый headless host/surface API.** Минимальное durable состояние Run и artifact refs, single node authority, submit/status/events/download, один проработанный end-to-end сценарий. Физическое размещение определить по требуемому process lifecycle; при немедленном Web-host release выделить `stratbox-host`.

**Этап 3 — Web клиент и публичная граница.** `stratbox-web` с responsive browser UI, admin-provisioned local accounts, HTTPS, sessions, allowed actions; работа через домен. Добавить PWA-установку и read-only cache только при измеренной пользе, не строить сразу сложный offline sync.

**Этап 4 — Android spike и работающий remote-client.** Реально сравнить Compose и RN/Expo на одинаковой форме+timeline, при необходимости Qt Quick/Flutter; проверить APK installation, доступность, large screen, жизненный цикл, deep links и notifications. Затем создать осмысленный `stratbox-android` (проект + базовые tests) и реализовать выбранные capabilities.

**Этап 5 — расширение, а не обязательный первый выпуск.** Полная совместная работа, rich artifact previews, локальный Android executor, cross-device drafts, advanced approvals, фоновые trigger policies, отдельный SDK/shared token package — только по подтверждённым сценариям и потребителям.

**Граница готовности:** структура папок и наличие исходных моделей не равны реализованному feature. Для каждого этапа нужны сценарии `accepted → executed → observed → recovered`, включая неуспешные и неизвестные эффекты.

## 17. Внешняя теория, стандарты и практические источники

### 17.1. Почему границы скрывают изменчивость, а не повторяют названия экранов

**D. L. Parnas (1972), “On the Criteria To Be Used in Decomposing Systems into Modules”**, *Communications of the ACM* 15(12), 1053–1058, DOI: [10.1145/361598.361623](https://doi.org/10.1145/361598.361623). В статье критерий хорошего разбиения — локализация проектных решений, вероятных к изменению. Применение: `QtScenarioCoordinator`, session cookies, AppDock activation fields и Android intents должны быть сокрыты за ports, а не объединены исходниками ради «одной платформы».

**Roy Fielding (2000), “Architectural Styles and the Design of Network-based Software Architectures”**, University of California, Irvine, [abstract](https://ics.uci.edu/~fielding/pubs/dissertation/abstract.htm), [introduction](https://ics.uci.edu/~fielding/pubs/dissertation/introduction.htm). Ценность HTTP/REST-style constraints — независимость компонентов, stateless message semantics и промежуточные границы. Для Strategy Box это аргумент за self-describing API queries/commands, а не за бесконтрольный RPC, который обнажает внутренние Python classes.

### 17.2. Контракты данных и ошибок

- [OpenAPI Specification 3.1.1](https://spec.openapis.org/oas/v3.1.1.html): языконезависимое HTTP API описание; позволяет проверять Web/Android и генерировать типы.
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/): формальное описание структур и validation; подходит для общего подмножества user parameter schemas/DTO, но не заменяет собственные предметные правила.
- [RFC 9110 HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html): статус HTTP должен сохранять смысл метода и результата, transport/application outcome следует различать.
- [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html): типизированные HTTP-ошибки без потери машинно-читаемой причины.

### 17.3. Обновление состояния, мобильная адаптация и offline

- [MDN: Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) — SSE/`id`/reconnect; полезен как начальный событийный транспорт.
- [Android Developers: Guide to app architecture](https://developer.android.com/topic/architecture) — single source of truth и unidirectional data flow; переносится в решение о каноническом shared node state.
- [Android Developers: Window size classes](https://developer.android.com/develop/adaptive-apps/guides/use-window-size-classes) — адаптация по доступной области, включая foldable/tablet/multiwindow.
- [MDN: PWA caching](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Caching) и [Offline and background operation](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Offline_and_background_operation) — caching и ограничения фоновых браузерных возможностей.
- [W3C WCAG 2.2 changes](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) — общие требования к touch, focus и доступности.

### 17.4. Технические альтернативы UI

- [Qt for Python: pyside6-android-deploy](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-android-deploy.html) — Android сборки реальны, но требуют отдельного toolchain и не гарантируют перенос Qt Widgets UX.
- [Expo: Develop websites](https://docs.expo.dev/workflow/web/) — универсальные React/RN Web приложения и смысловые ограничения этого подхода.
- [Flutter: Web accessibility](https://docs.flutter.dev/ui/accessibility/web-accessibility) и [Flutter: Web FAQ](https://docs.flutter.dev/platform-integration/web/faq) — web canvas semantics и возможные UX последствия.
- [Next.js: Authentication](https://nextjs.org/docs/app/guides/authentication) — разделение authentication, session management, authorization; при использовании именно Next.js помогает не собирать собственную session-систему с нуля.

### 17.5. Публичная security-граница

- [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) — salted adaptive hashing, Argon2id.
- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) — secure session cookies, ограничения браузерных сессий.
- [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) — cookie-based browser session threats.

**Методологическое ограничение внешних источников:** это научные работы/стандарты и документация вендоров. Они показывают доказанные свойства API и поддерживаемые механизмы, **но не содержат benchmarks конкретно Strategy Box**. Выбор toolkit, concurrency и deployment следует принимать по запущенным end-to-end probes (§15), а не по одному рекламному тезису.

## 18. Реестр противоречий, решений и открытых вопросов

| № | Противоречие или неизвестное | Оценка | Предлагаемое разрешение / следующая проверка |
|---:|---|---|---|
| Q07-01 | «Два новых репозитория» vs фактически требуется ещё authority host | **OPEN, архитектурно важно** | Репозитории Web/Android создавать при первом реальном коде; host выделить при отдельном process lifecycle |
| Q07-02 | Единые визуальные компоненты vs Qt/CSS/native Android | **Разрешено на уровне принципа** | Общие tokens + semantic components; renderer отдельно |
| Q07-03 | B-web предлагает `stratbox-host`, новый `docs/` оставляет физический owner открытым | **Не противоречие в logical ownership; physical OPEN** | Принять lifecycle-driven extraction после prototype |
| Q07-04 | Windows QThread owns execution vs mobile/web remote-independent execution | **BLOCKER** | Qt-free application authority и headless executor |
| Q07-05 | Локальная JSON history vs общие чаты и два устройства | **BLOCKER** | Durable node state; local history только migration/cache |
| Q07-06 | Browser доступ по домену vs «безопасность позже» | **BLOCKER для публичного запуска** | Admin-provisioned accounts+TLS+sessions+ACL с первого release |
| Q07-07 | Никнеймы в команде vs web identity | **Обязательно развести** | Principal отдельно от display label и session/device |
| Q07-08 | Android offline vs remote-first | **Разрешено по scope** | Online-first, limited local cache/drafts; offline compute позже |
| Q07-09 | Manifest declares host role vs реальная готовность host | **Риск несуществующей capability** | Build profile + runtime handshake + degraded status |
| Q07-10 | Windows pin core `0.2.1` vs current core `0.8.0` | **Текущий технический debt** | Обновить точный dependency graph и CI validation перед release |
| Q07-11 | SSE или WebSocket | **Decision candidate** | SSE сначала, измерить необходимость двустороннего потока |
| Q07-12 | Kotlin Compose vs RN/Expo vs Flutter/Qt Quick | **OPEN** | Два renderer spike по одной форме и timeline; a11y/build/perf tests |
| Q07-13 | Кто владеет правами/аудитом и файлом при частичном результате | **Зависит от тем 03–05, 08, 10** | Граница application authority и typed effect receipts до многоузлового Web |
| Q07-14 | Нужен ли общий language-specific source package | **OPEN; не первоочередной** | Сначала OpenAPI/schema+fixtures; пакет лишь при двух доказанных consumers |
| Q07-15 | Remote AppDock APIs, mobile release tooling | **EXTERNAL DEPENDENCY** | Точная версия SDK/manifest; проверка возможностей у AppDock owner |

### 18.1. Предлагаемые Product Decisions к принятию человеком

**PD-07-A:** Стратегия `one Strategy Box semantics — multiple native/adaptive surfaces` как неизменяемая продуктовая граница.

**PD-07-B:** Первый Web — полноценный browser client узла с общей историей, разрешённым запуском, прогрессом и результатами; публикация через HTTPS domain с подготовленными оператором учётными записями.

**PD-07-C:** Первый Android — remote-first companion/контроллер с просмотром, запуском простых операций, статусом и артефактами; full local computing и сложные offline editing исключены из первой поставки.

**PD-07-D:** Семантические модели/действия и design tokens общие; toolkit-specific widgets, navigation и filesystem адаптируются отдельно.

**PD-07-E:** AppDock определяет support/deployment/activation configuration в пределах своего версионированного интерфейса; Strategy Box остаётся authority для выполнения конкретной операции, статуса, прав в прикладном контуре и его результатов.

Эти пять решений уже имеют достаточно оснований для предметного обсуждения. **Ни одно не является утверждённым Product Decision в рамках данного исследования.**

---

## 19. Финальные выводы

1. Главный reusable asset Strategy Box — **семантика и прикладные контракты**, а не текущие Qt widgets. Нейтральная Python domain core уже существует; application/surface граница требует доработки.
2. **Web — обязательное направление, а не факультативная «когда-нибудь» оболочка.** Его появление превращает общую execution authority, сетевой контракт и server-side authentication в реальные продуктовые зависимости.
3. Android следует начинать как **управляющий клиент хоста**. Локальная аналитика и полнофункциональная файловая среда на смартфоне могут ждать. Это сохраняет пользователю главную ценность без тяжёлого APK/runtime.
4. Публичный Web имеет **минимальный непреложный security floor**. Можно отказаться от регистрации и почтового восстановления в MVP, но нельзя отказаться от защищённых сессий, проверки полномочий и хеширования паролей.
5. AppDock — **упаковка, окружение, узел и runtime handoff**, Strategy Box — **аналитика, application commands, результаты и их смысл**. Их сопряжение должно быть узким и версионированным; текущие будущие возможности AppDock нельзя выдавать за доступные.
6. Вопрос о создании двух новых репозиториев не отменяется: `stratbox-web` и `stratbox-android` логичны как самостоятельные implementation owners. Но создавать пустые репозитории или копировать application engine заранее нет пользы. Отдельный headless `stratbox-host` вероятно понадобится до работающего remote-клиента.
7. **Наиболее полезный следующий инженерный эксперимент** — один настоящий сценарий от browser/phone через host к core и обратно к статусу/артефакту, плюс негативные тесты сетевого обрыва, повторного запуска и отказа в доступе. Он даст основания принять физическую архитектуру и toolkit без искусственного усложнения.

**Итоговая формула:** **один домен → одна application authority → общий контракт возможностей и состояния → разные клиентские представления → отдельные платформенные адаптеры.**
