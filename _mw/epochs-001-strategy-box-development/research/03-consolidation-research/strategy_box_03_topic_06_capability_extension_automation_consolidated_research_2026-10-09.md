# Strategy Box — консолидирующее исследование 06: Capability, Extension & Automation Architecture

**Дата:** 2026-10-09  
**Программа:** `03-consolidation-research`, тема **06 — Capability, Extension & Automation Architecture**  
**Статус:** **Research Synthesis / Consolidation Result**. Исследовательская архитектурная модель; не Product Decision, не утверждённые Target WHAT/HOW, не спецификация уже существующего API.  
**Основной корпус:** исследования `02-base-study` за 6–8 октября 2026 года; контроль терминов и границ — результаты тем 00–04 третьей ветки.  
**Приоритет истинности:** актуальный код соответствующего owner → его документация и тесты → factual baseline → тематические исследования → консолидированная модель → новые гипотезы.  
**Изменения в репозиториях:** отсутствуют.  
**Граница публичности:** документ пригоден для открытого исследовательского корпуса. Обсуждаются исключительно универсальные интерфейсы расширений; закрытые реализации и устройство корпоративной среды не описываются.

---

## 0. Executive synthesis

### 0.1. Главный результат

**[CONSOLIDATED]** Strategy Box должен иметь **одну систему описания аналитических способностей и одну систему допущенного исполнения**, поверх которых работают человек, Windows/Web/Android, CLI/Python, планировщик, внешние интеграции и ИИ. Различия между ними должны проявляться в способе обнаружения, представления, активации, разрешениях, параметрах и месте выполнения, но **не в появлении собственной копии бизнес-логики или отдельного workflow-движка**.

Нужны две согласованные, но различные оси:

1. **Capability plane** отвечает за вопрос: *что система способна делать, каковы семантика результата, входы, выходы, применимость, эффекты, зависимости, допустимые реализации и доказательства корректности?*
2. **Execution/automation plane** отвечает за вопрос: *кто и с какими полномочиями запускает способность, через какой план, на каком worker, по какому правилу, с какими ресурсами, эффектами, историей, retry/recovery и окончательным исходом?*

Extension plane предоставляет новые **проверяемые вклады** в эти оси: реализации инфраструктурных интерфейсов, дополнительные описания предметных способностей при подходящей модели доверия, источники данных, форматы, стили артефактов, шаблоны. Он не получает неограниченного права менять продукт, данные, политику, интерфейс или обходить исполнительный контур.

```text
      Human / UI / API / CLI / Scheduler / External AI
                            │
                  intent / target / inputs
                            ▼
                  Application admission
                  identity + authorization
                            │
          ┌─────────────────┴────────────────────┐
          ▼                                      ▼
  Semantic Capability Catalog          Extension Registry
  Operation / Scheme / Scenario         installed → selected → bound
          │                                      │
          └───────── verified bindings ──────────┘
                            │
                            ▼
                  Planner → ExecutionPlan
                            │
                            ▼
                    Run / JobManager
                            │
                    ExecutionBackend
                            │
            ┌───────────────┴────────────────┐
            ▼                                ▼
       stratbox core                    approved providers
  calculations / data semantics         environment adapters
            │                                │
            └───────────────┬────────────────┘
                            ▼
            qualified Result + evidence + artifacts
                            │
                events / receipts / history
                            │
                  projections in surfaces
```

**[CURRENT]** Этой целевой системы ещё нет целиком. В `stratbox` существуют реальные доменные функции и отдельные зрелые Request/Result-контракты, FileStore/secret/style seams и Python entry-point discovery. В `stratbox-windows` есть локальный `OperationRegistry`, `ScenarioRegistry`, последовательный runner, `ScenarioRunCase`, events/logs/artifacts, Qt execution coordinator и каркасы background/AI. **Единого версионируемого semantic capability catalog, durable AutomationSpec/TriggerOccurrence и headless JobManager сегодня нет**.

### 0.2. Консолидированные решения высокой уверенности

1. **Одна предметная реализация, множество consumers.** Банковские методы, расчёты, нормализация, парсинг и проверка данных находятся в `stratbox`, а не в обработчиках конкретного UI.
2. **Capability не равна permission.** Существование способности, наличие её технической реализации, доступность в текущей среде и право конкретного субъекта её вызвать — четыре разных факта.
3. **Operation — самостоятельный доменный use case**, а не каждая Python-функция и не Qt handler. Для неё нужны стабильная идентичность и машинно-проверяемая семантика.
4. **Scenario — курируемая продуктовая возможность**, рассчитанная на понятное пользователю действие. Он может обращаться к одной Operation либо к композиции. Механическое создание отдельного Scenario для *каждой* Operation — текущий shortcut, но слабое целевое правило.
5. **Scheme — машинно-читаемая, версионированная композиция** типизированных операций/схем с проверяемыми связями, применимостью, ограничениями и эффектами. `Cascade` — прежде всего пользовательское представление крупного рабочего потока, пока самостоятельный governance не доказан.
6. **Background — способ исполнения, Automation — постоянное правило запуска.** Автоматизация порождает обычные Work/Run/Job; специальный «фоновый scenario engine» не нужен.
7. **Scheduler Strategy Box владеет предметными правилами.** AppDock управляет узлом, поставкой, средой и жизненным циклом процесса; он не становится владельцем бизнес-расписаний.
8. **Extension discovery отделена от activation, binding, authorization и readiness.** Установленное расширение автоматически не получает права работать.
9. **Machine/AI интерфейс — projection канонических capabilities.** Агенту не предоставляется обходной универсальный `execute_python`/`shell` и отдельный набор «AI-функций».
10. **Инварианты результата и эффектов сильнее удобства fallback.** При отсутствии нужной реализации, отказе backend, неизвестном исходе и незавершённой публикации сохраняются различимые failure/unknown состояния.

### 0.3. Основные новые уточнения темы 06

**[NEW CONSOLIDATION]** Предыдущие исследования часто рассматривали «реестр способностей» как один объект. Целесообразно разделить **семантический каталог**, **реестр устанавливаемых contributions**, **реестр активированных bindings**, **зависимый от контекста каталог доступности** и **projection конкретному субъекту**. Это разные представления с разными владельцами и разной изменчивостью. Иначе одна строка `enabled=True` начинает ошибочно означать одновременно «пакет установлен», «совместим», «готов», «разрешён пользователю» и «можно запускать сейчас».

**[NEW CONSOLIDATION]** Для расширений нужны **несколько контрактных классов**, но не один универсальный plugin ABI для всех сущностей: (a) инфраструктурный provider, (b) domain operation contribution, (c) source/registry contribution, (d) declarative artifact/style contribution, (e) execution backend adapter, (f) optional surface-safe metadata. У этих классов разные ownership, валидация, потребители, установка, безопасность и жизненные циклы.

**[NEW CONSOLIDATION]** Следует установить **два отдельных доверительных перехода**: активация исполняемого кода в среде и выдача полномочий на конкретный эффект конкретному актору. Подписанный/проверенный плагин способен быть технически trusted, но его операция не становится автоматически разрешённой всем пользователям и ИИ.

**[NEW CONSOLIDATION]** Capability snapshot должен входить в ExecutionPlan как **разрешённая на момент запуска комбинация definition + provider binding + contract versions + policy revision**, а не только имя операции. При изменении каталога уже запущенный Run нельзя молча перенаправлять на другую реализацию.

### 0.4. Уровни уверенности

- **CURRENT:** найдено в коде/сохранено в прямом исследовании implementation baseline; факт имеет версию и границу проверки.
- **CONSOLIDATED:** несколько независимых линий корпуса логически согласованы и не противоречат обнаруженному коду; это ещё не автоматически Product Decision.
- **TARGET-HYPOTHESIS:** проектируемое решение, которое требует product approval, implementation pilot или contract test.
- **CONFLICT:** действительно разные требования или несовместимые модели; фиксируется выбранная рабочая интерпретация и остаток.
- **SUPERSEDED:** историческое предложение, вытесненное более строгой семантикой.
- **UNKNOWN:** сведений или реализации недостаточно; гипотеза не должна выдаваться за факт.

---

# 1. Область исследования, метод и границы

## 1.1. Предмет темы 06

Программа третьей ветки ставит вопрос: **«Что в Strategy Box может расширяться, каким contract, кто это обнаруживает, кто активирует и какие эффекты расширение получает?»** В обязательный охват входят canonical operations, capability descriptors, scenario definitions, machine schemes, automation triggers, execution backends, generic plugins, style/source providers и AI tool exposure. [P01]

Исследование **не утверждает** заново модель Work/Run/Job (тема 04), сущности SourceSnapshot/Dataset/Artifact (тема 03), устойчивое состояние (тема 05) или полную модель security/reliability (тема 08). Оно **использует** уже консолидированную семантику как вход, формулирует контракты для неё и отмечает новые вопросы, передаваемые соответствующим темам.

## 1.2. Критерий, что является расширением

Под расширением понимается **дополнительный вклад в явно определённый extension point**, распознаваемый стандартным контрактом, с известным provenance, предельными эффектами и governance. Подмена произвольной Python-функции, вставка Qt-widget, изменение внутренних модулей через monkey patch или запуск произвольного скрипта по тексту из UI этим определением не покрываются.

Вместе с этим *расширяемость* шире *плагинов*: новый доменный модуль внутри core, новая SchemeDefinition, сохранённая AutomationSpec и новый external ExecutionBackend расширяют возможности Strategy Box, хотя вовсе не обязательно являются «плагинами».

## 1.3. Что изучено и что проверено повторно

Основной корпус включает factual исследования `stratbox` и `stratbox-windows`, работы об автоматизации и ИИ, операциях/сценариях/каскадах, управлении исполнением, машинных схемах, переносимости библиотечных сегментов, background jobs, реестрах источников, расширениях, настройках, стилях артефактов, web/self-hosted, многопользовательском узле, observability и внешнем machine-consumer. Контроль — Corpus Map и темы 01–04. [R01–R18; C00–C04]

**Прямо перечитаны из текущих репозиториев:** `stratbox/base/runtime.py`, `base/styles/excel/plugin.py`, `docs/plugin-integration.md`, `pyproject.toml`; в Windows — application operation/scenario catalog models и registries, scenario runner, background registry/models/store, Qt ScenarioCoordinator, runtime bootstrap, AppDock manifest и package metadata. Ссылки и проверяемые факты приведены в §3 и Source ledger. Поскольку отдельные источники были исследованы на конкретных commit 6–8 октября, результаты срезов считаются **датированными**. Сегодняшний direct-code probe указан отдельно.

Официальные PyPA entry points, JSON Schema 2020-12 и MCP Tools прочитаны как внешние справочники по отдельным кандидатам интерфейсов. **Ни один внешний стандарт сам по себе не определяет смысл Capability, Work или Authority Strategy Box**. [E01–E03]

## 1.4. Публично-приватная граница

В публичном `stratbox` разрешены: нейтральные Protocol/API, общие capability IDs, versioned discovery, activation, binding, conformance, synthetic fixtures, error/health/event contracts и документация на общую систему. В публичном `stratbox-windows`: безопасные projections, управление разрешёнными extension options и отображение готовности. **Нельзя** включать конкретные внутренние имена, реализации, сетевые адреса, среды, credential mapping, инструкции подключения закрытых расширений, private dependency identifiers и другие сведения о закрытых компонентах. [R09; C02]

Любой перенос данного исследования в Product/код должен пройти проверку публичной границы на содержимом файлов, dependency metadata, test fixtures и примерах.

---

# 2. Минимальная логическая модель и термины

| Термин | Строгий смысл | Чем не является | Статус |
|---|---|---|---|
| `CapabilityDefinition` | Семантическая способность: намерение, граница предмета и наблюдаемый контракт | конкретным Python handler, разрешением пользователя | CONSOLIDATED |
| `OperationDefinition` | Самостоятельный, типизированный, исполнимый доменный use case | внутренней utility, UI-button, transport primitive | CONSOLIDATED |
| `ScenarioDefinition` | Курируемый продуктовый путь достижения понятного пользователю результата | обязательной 1:1 обёрткой всех операций | CONSOLIDATED |
| `SchemeDefinition` | Версионированный reusable typed graph операций/схем | живым Run или произвольным AI-текстом | TARGET-HYPOTHESIS |
| `Cascade` | Вид/профиль крупной последовательной или параллельной композиции | автоматически новым executor | CONSOLIDATED |
| `Invocation` | Запрос применить definition с заданными входами | готовым планом или эффектом | CONSOLIDATED |
| `ExecutionBinding` | Однозначно выбранная исполняемая реализация и её ограничения | identity предметной способности | TARGET-HYPOTHESIS |
| `ExecutionPlan` | Зафиксированный после разрешения параметров и bindings граф с предельными эффектами | текущими изменяемыми defaults | CONSOLIDATED |
| `PluginDescriptor` | Объявление installable расширения и его contributions | доказательством доверия/доступности | TARGET-HYPOTHESIS |
| `ProviderBinding` | Выбор конкретной реализации generic capability slot | разрешением произвольных user actions | TARGET-HYPOTHESIS |
| `AutomationSpec` | Долговечное правило появления запусков | фоновым worker, активным Job | CONSOLIDATED |
| `TriggerSpec` | Условие, расписание или входное событие | самим Run | CONSOLIDATED |
| `TriggerOccurrence` | Уникальное срабатывание/результат оценки trigger | новым `AutomationSpec` | TARGET-HYPOTHESIS |
| `ExecutionBackend` | Контракт физического запуска и контроля Job | владельцем business Outcome/Work | CONSOLIDATED |
| `MachineToolProjection` | Отфильтрованное машинное представление разрешённой способности | новой бизнес-реализацией, правом на вызов | CONSOLIDATED |

Отдельно сохраняются **`Work`** (долговечная пользовательская/деловая цель), **`Run`** (конкретная траектория работы), **`Job`** (планируемая единица исполнения), **`OperationRun`** (один вызов Operation в Run), **`Attempt`** (одна физическая попытка). Расширения не должны вводить альтернативные сущности, подменяющие этот позвоночник. [C02; C04]

## 2.1. Почему Capability и Operation нельзя слить полностью

`Capability` формулирует **обещание** вида «можно собрать историю счетов эскроу с известным качеством источников». `Operation` делает обещание **запускаемым** через typed request/result, детерминированный контракт применимости и описание эффектов. Одна Capability может быть реализована несколькими Operation variants или одной Scheme; одна Operation может удовлетворять нескольким пользовательским намерениям. Связь — явный semantic mapping, а не наследование Python-классов без необходимости.

**Практическое минималистичное правило:** в первой версии достаточно `OperationDefinition` с семантическими полями Capability; самостоятельный persisted `CapabilityDefinition` материализуется тогда, когда реально появляются несколько реализаций/вариантов, отдельная capability version или самостоятельный consumer. Это сохраняет словарь, не плодя сущности преждевременно.

## 2.2. Четыре уровня бизнес-кода

```text
L0 Mechanism — byte transport, FileStore, HTTP, formats, solver
L1 Reusable building block — parser, normalizer, validator, transformer
L2 Domain service — source discovery, canonicalization, domain datasets
L3 Canonical Operation — самостоятельный Request → qualified Result
L4 Scheme — композиция L3 с typed ports и verified conditions
```

L0–L2 могут быть доступны Python users как документированные reusable APIs, но автоматически не превращаются в scheduler/agent tools. L3–L4 — основной machine capability boundary. `stratbox` не превращается в гигантский generic ETL framework ради этой модели. [R01; R04; R05]

## 2.3. Commands как локальный технический уровень

**[CONFLICT RESOLVED]** В раннем исследовании была предложена общая цепочка `Command → Scenario → Cascade`, позже возникла модель `Operation → Scenario/Scheme`. Термин `Command` оставляется для конкретного application control (`cancel_job`, `approve_plan`) либо внутренних технических primitives там, где это действительно полезно. **Обязательного публичного `CommandRegistry` как основания бизнес-архитектуры нет**. Иначе любая загрузка URL и чтение DBF необоснованно становится глобальной машинной capability. [R02; R04; C02; C04]

## 2.4. Scheme и Scenario связаны, но живут на разных уровнях

`ScenarioDefinition` — бизнесовое/пользовательское описание: «обновить статистику ЦБ», краткие параметры, ожидаемые выходы, доступность в продукте, удобный текст. `SchemeDefinition` — проверяемая machine composition: typed ports, edges, branches, read/write sets, partial/failure semantics, constraints, postconditions. Сценарий может напрямую вызвать одну Operation или привязаться к конкретной версии Scheme. Одна Scheme может обслуживать разные курируемые сценарии; пользовательский сценарий может переключать Scheme по версии/политике только с явным binding.

Новый объект `CascadeDefinition` стоит вводить лишь если появится самостоятельное содержание — владельцы, версионирование, admission, выделенные правила публикации или отдельные потребители, которые невозможно выразить Scenario/Scheme. Пока это **UNKNOWN, а не обязательная таблица/класс**. [C02; R02; R05]

---

# 3. CURRENT: подтверждённое состояние реализации

## 3.1. `stratbox`: специализированные домены и инфраструктурные seams

**[CURRENT]** Core (`pyproject.toml`, версия пакета `0.8.0` на проверенном срезе) содержит reusable доменные подсистемы: `cbr_file_collector`, `cbr_forms`, `cbr_industries`, `cbr_sors_restoration`, `escrow`, `frg`. Часть предоставляет структурированные request/result и failures, но **единый независимый междоменный каталог операций отсутствует**. Различные домены объединены общей нижней инфраструктурой (`FileStore`, IO форматов, сетевые операции, secrets, styles). Проверены package metadata и исследования core. [R01; I01]

Примеры существующих операций и степень готовности:

| Область | Реальный предметный результат | Что нужно для канонической machine exposure |
|---|---|---|
| `cbr_file_collector` | Получение набора исходных файлов ЦБ из встроенного source catalog | единый source snapshot manifest, typed completeness/side effects, cancellation |
| `escrow` | История счетов эскроу, views, Excel/ZIP | явное separation build/result/export, input versions, style binding |
| `cbr_forms` | Форма → семантический canonical long → workbook | доведение разных форм до единых операций build/export |
| `cbr_industries` | Статистический ряд/производные/представления | версия series spec, source applicability, новые series после доказанного пилота |
| `cbr_sors_restoration` | восстановление ограниченных статистических величин с evidence/conflict trails | resource budget, строгая квалификация результата, versioned inputs; специализированная математическая семантика сохраняется |
| `frg` | scan/catalog/cleanup plan/apply/archive файловых поставок | предохранители на эффекты, отдельные typed операций scan/plan/apply, реальные parsers и tests |

Факт наличия операции в Python API **не доказывает**, что она уже готова для автоматизации/AI. Например, отсутствие tests, устойчивых failure types, cancellation/progress и artifact receipts остаётся функциональным ограничением. [R01; R04; R05]

## 3.2. Core extension selection: уже работает, но семантически слишком неявен

**[CURRENT — прямой код]** `stratbox.base.runtime` обнаруживает entry point группы `stratbox.plugin` с именем `providers` и принимает возвращённый набор FileStore/SecretProvider. По умолчанию пытается подключить найденную реализацию, при исключениях или неподходящем результате выдаёт предупреждение и переходит в local-mode. При нескольких entry points выбор происходит фактически по первому успешному результату. Существуют совместимые с прежними именами ключей варианты, а сохранённый local instance может позднее повторно искать расширение. Это **описание общих недостатков публичного selection algorithm**, без сведений о конкретных установленных расширениях. [I02]

**[CURRENT — прямой код]** `base.styles.excel.plugin` обнаруживает отдельную группу `stratbox.styles.excel` и складывает Excel addons. Общий catch-all при ошибке возвращает пустой список. Структура `ExcelStylesAddon` содержит `presets`, `fonts`, `default_preset_name`, допускает объединение вкладов. Отсутствует единая декларация identity/conflict/readiness для разных extension types. [I03]

**[CURRENT — пакетирование]** Metadata публичных пакетов ещё содержит средо-специфичные optional dependency shortcuts. Для целевой модели публичные distributions должны оставаться нейтральными и не идентифицировать закрытые поставки. Имена и детали таких зависимостей здесь сознательно опущены. [I01; I09]

**Вывод:** entry-point discovery имеет реальную библиотечную основу, но `installed`, `active`, `ready`, `required`, `authorized` сегодня не разделены. Нельзя назвать описанный runtime уже готовым versioned extension framework.

## 3.3. `stratbox-windows`: рабочий каталог и локальный исполнитель

**[CURRENT — прямой код]** `OperationRegistry` содержит **три** `OperationSpec`: две прикладные (`cbr_file_collector.collect`, `escrow.history.export`) и `system.diagnostics`. Метаданные включают handler reference `module:function`, basic form specs, visibility, preview, repeat, `dangerous`, `ai_visibility` и ожидаемые артефакты. Список создаётся вручную в `build_operation_registry(context)`. Его `enabled` — статический флаг, а не результат расчёта среды/прав/ready-state. [I04; I05]

**[CURRENT — прямой код]** Scenario registry автоматически строит `scenario.atomic.<operation_id>` для всех enabled operations и объявляет один составной `scenario.cbr.full_update` из двух последовательных steps с `params_map`. Типы scenario допускают `atomic`, `composite`, `background`, `assignment`, хотя `background` и `assignment` сами по себе не исполняют отдельный механизм. [I06; I07]

**[CURRENT — прямой код]** `run_scenario` создаёт/обновляет case и step statuses, последовательно вызывает `run_operation`, превращает строки путей в `ArtifactRecord`, публикует events и log records. Внешний status шага основан преимущественно на `OperationResult.ok`. [I08]

**[CURRENT — прямой код]** Qt `ScenarioCoordinator` создаёт `QThread` и worker для исполнения. Свойство `is_busy` и запрет запуска при активном case ограничивают процесс **одним сценарием**; отсутствует control API для cooperative cancellation и независимый долговечный scheduler. `runtime.bootstrap` импортирует этот Qt coordinator непосредственно при сборке приложения. [I10; I11]

## 3.4. Фоновые процессы — модели, но ещё не background automation

**[CURRENT — прямой код]** Реестр содержит три названия: мониторинг публикаций, проверка workspace, обновление кэша. `BackgroundProcessStore` создаёт in-memory состояния `disabled/idle/running/warning/error`, умеет переключать `enabled` и вручную отмечать результаты/ошибки, но **не содержит scheduler, trigger evaluator, persisted occurrence history, связи с JobManager и выполнения operations**. Текст `schedule_label` — UI-подпись, не исполняемое расписание. [I12–I14]

**Следствие:** видимое «Включено» нельзя в исследованиях трактовать как реально работающую службу мониторинга. Целевая модель заменяет этот семантически слишком слабый каркас парой `AutomationSpec` + `TriggerSpec`, связываемой с обычной execution pipeline.

## 3.5. AppDock boundary и deployment

**[CURRENT]** Windows Connector Manifest заявляет `contract_version: 4.0`, local Windows foreground surface, общий Python environment и диагностический entrypoint. Он не объявляет Strategy Box как работающую сейчас удалённую execution service. Исторические исследования AppDock описывают узел, managed runtime, lifecycle, health, remote/host как отдельный контур, однако его концептуальный roadmap **не превращает** все host/remote features в реализованный Strategy Box. [I15; A01]

**[CONSOLIDATED]** AppDock владеет установкой, package graph, Node/Session activation, процессным lifecycle, удалённым транспортом и платформенной диагностикой в рамках реально опубликованного контракта. Strategy Box владеет бизнес-операциями, schemes, triggers/automation, очередью предметных jobs, планами и прикладной историей. Конкретная физическая граница будущего headless процесса зависит от дальнейшей проверки внешнего host contract. [C01; C04; R12]

## 3.6. Важный version drift

**[CURRENT]** `stratbox` package metadata сообщает `0.8.0`, в то время как `stratbox-windows` package metadata и его manifest в исследованном текущем состоянии закрепляют core package `0.2.1`. Это **доказанный декларативный разрыв**, который не позволяет по одной лишь установке заключить, что current Windows/Core combination проходит современный контракт и end-to-end тесты. В этом исследовании не проводилась установка полноценного managed environment и не объявляется успешный runtime smoke. [I01; I09; I15]

Это надо устранить **до** масштабного plugin/backend admission. По архитектурному правилу проекта обратную совместимость API сохранять не требуется; нужны единый поддерживаемый текущий контракт и чётко версионируемые пакеты.

---

# 4. Capability plane: пять реестров вместо одного смешанного

## 4.1. Разложение

| Слой | Что содержит | Кто авторитетен | Изменяется когда |
|---|---|---|---|
| **Definition Catalog** | semantic `OperationDefinition`, `SchemeDefinition`, capability reference | домен `stratbox` / application owner для Scenario | при версии продукта/контракта |
| **Contribution Inventory** | обнаруженные пакеты, объявления additions/providers, дистрибутивы, версии | extension runtime / package metadata | при изменении установленной среды |
| **Activation & Binding Registry** | явно выбранные, разрешённые и проверенные providers; overrides, priorities policy | environment runtime + владелец capability slot | на managed activation/reconfiguration |
| **Availability Projection** | текущие readiness, source/credential/data constraints, backend support, operational state | application capability resolution | динамически на узле/сессии |
| **Authorized Catalog Projection** | что именно видит и может вызвать данный Principal/Actor/AI consumer | application authorization | при запросе с учётом прав и контекста |

**[TARGET-HYPOTHESIS]** Эти реестры — **логические ответственности**, а не пять обязательных сервисов, БД или новых репозиториев. На первом пилоте их можно вычислять в одном приложении из структурированных immutable snapshots. Однако нельзя объединять их поля в одно неразличимое `enabled`.

## 4.2. Строгая формула доступности

```text
invocable(operation, principal, context) =
    defined_and_compatible
    ∧ implementation_binding_resolved
    ∧ required_providers_ready
    ∧ parameters_valid
    ∧ applicability_satisfied
    ∧ source_data_constraints_satisfied
    ∧ backend_has_required_features
    ∧ principal_authorized_for_effects
    ∧ approval_requirements_addressed
    ∧ sufficient_resource_or_explicit_queue_policy
```

Результат проверки должен быть структурированным, с отдельными признаками `discoverable`, `visible`, `selectable`, `ready`, `permitted`, `requires_approval`, `executable_now`, `queueable`. **Достаточно одного ложного критического условия**, чтобы execution admission отказал либо поместил запрос в явное ожидание. UI вправе представить короткую человекочитаемую причину, но не подменяет policy собственными условными блокировками.

## 4.3. Предлагаемая модель `OperationDefinition`

Это **кандидат семантического контракта**, а не существующий Python класс или JSON API:

```yaml
# TARGET CONTRACT EXAMPLE — illustrative, schema/version pending
operation_id: cbr.files.collect
operation_version: 1
purpose: collect_authoritative_raw_sources
owner: stratbox.macrobanks.cbr_file_collector
input_schema_ref: schema:operations/cbr.files.collect/request@1
output_schema_ref: schema:operations/cbr.files.collect/result@1
input_semantics:
  source_selection: stable_source_ids
  snapshot_policy: pinned_or_declared_current
requires:
  - network.outbound
  - storage.workspace.write
applicability:
  requires_available_source_catalog: true
effects:
  - network.read
  - storage.write
  - artifact.publish
risk_class: controlled_write
idempotency: conditional_by_snapshot_and_destination
retry_policy: bounded_only
cancellation: between_source_items
resource_claims:
  - network:cbr
  - destination:exclusive
partial_result: explicit_with_missing_sources
expected_output_kinds:
  - source_bundle
  - artifact_manifest
assurance:
  completeness_check: required
  provenance: required
```

Главное: каждая графа относится к проверяемой **семантике**, а не к косметике GUI. `title`, локализованное описание, иконка, позиция в меню, форма с раскрывающимися подсказками, плотность и тема живут в presentation overlay. `handler='package:function'` живёт в отдельном `ExecutionBinding` и не становится идентичностью Operation.

## 4.4. Схемы входов и выходов

Предпочтительна **двухслойная** модель:

- Внутри Python-domain разрешены удобные typed dataclass/Pydantic-совместимые Request/Result, DataFrame, iterators, domain-specific numerical types.
- На стабильной machine/remote boundary — явно описанные переносимые структуры: JSON-compatible control envelope, ссылочные `DatasetRef`, `SourceSnapshotRef`, `ArtifactRef`, типизированные status/failure и schemas.

Для структурированного input/output подходит JSON Schema 2020-12, с оговорками: schema валидирует форму, но не доказательность статистического утверждения, не права, не ресурсы и не семантическую совместимость двух периодов. Богатые pandas/DuckDB/Arrow объекты могут передаваться как artifact/data refs, а не копироваться целиком в JSON. [E02; R05]

## 4.5. Обязательные capability dimensions

Минимальная полнота descriptor:

1. **Identity:** stable ID, owner, definition revision, deprecated policy отсутствует при чистом разрыве ABI.
2. **Purpose:** экономическая/аналитическая цель и ожидаемый qualified outcome.
3. **Input/Output:** type, units, dimensions, source selection и schema versions.
4. **Applicability:** supported period, geography, entity scope, required source/registry snapshots, explicit `UNKNOWN`.
5. **Preconditions/Postconditions:** проверяемые до/после effects условия.
6. **Effects:** read/write/destructive, network, external API, permission scope, staging/publish.
7. **Determinism/Idempotency:** условия повторного использования и безопасного повтора.
8. **Freshness/Currentness:** можно ли использовать cached result и какую публикацию он покрывает.
9. **Resources:** CPU/RAM class, quotas, locks, worker features, estimated output size.
10. **Control:** cancellation safe points, timeout policy, resumability/checkpoints, governed retry budget.
11. **Failures:** typed outcomes включая absence/partial/unavailable/unknown.
12. **Assurance:** validation, source/evidence provenance, completeness и acceptance implications.

Если поле пока невозможно обосновать, фиксируется `UNKNOWN` или `not_supported`; **нельзя** придумывать уверенное `True` только ради красивого machine catalog.

## 4.6. Версии и snapshots

Необходимо различать:

- package release version (`stratbox`/extension wheel);
- operation semantic contract version;
- scheme/ scenario definition revision;
- provider implementation version;
- plugin discovery API major;
- capability slot contract version;
- source/registry/data snapshot identity;
- environment activation profile revision;
- effective policy/grants revision;
- execution plan snapshot/digest.

Номер пакета не заменяет schema/semantic version; два бинарно совместимых пакета могут по-разному рассчитывать показатель. Для Run обязателен immutable набор действовавших ссылок/хэшей. Без него нельзя доказательно восстановить, *что именно* исполнялось при старой версии расширения.

---

# 5. Extension plane: общий контракт обнаружения, активации и привязки

## 5.1. Extension не равна Provider и не равна Operation

**[CONSOLIDATED]** Расширение — дистрибутив или интеграционная единица, способная объявить один или несколько *contributions*. Provider — реализация конкретного интерфейса, например storage или network policy. Operation contribution — новая самостоятельная предметная способность с собственным владельцем и требованиями доказательности. Style contribution — безопасный набор декларативных ресурсов оформления **артефактов**, а не разрешение на произвольные UI-изменения. Execution backend — implementation физической диспетчеризации/исполнения Job. Все они имеют разные механизмы review и могут использовать общую оболочку identity/versioning/health.

**Два независимых признака классификации:**

- **что расширяется**: data/source, analytical domain, runtime environment, artifact representation, execution delivery;
- **где работает код**: in-process trusted Python, out-of-process service, declarative data-only, external remote endpoint.

Сочетание «техническая реализация + trusted» не означает, что добавленное действие автоматически становится business operation. Например, HTTP transport — provider нижнего уровня; `collect_cbr_files` — Operation; «обновлять публикации по утрам» — AutomationSpec. Их lifecycle не следует сливать.

## 5.2. Целевой lifecycle расширения

```text
PACKAGE_AVAILABLE
       │ packaged metadata inspected
       ▼
DISCOVERED
       │ static descriptor validated
       ├────► INVALID_DESCRIPTOR
       ▼
COMPATIBLE
       │ selected by managed/user/developer profile
       ├────► NOT_SELECTED
       ▼
SELECTED
       │ trust/policy/dependency checks
       ├────► BLOCKED / NOT_ALLOWED
       ▼
ACTIVATING
       │ explicit provider creation/binding
       ├────► CONFIG_REQUIRED / AUTH_REQUIRED / ACTIVATION_FAILED
       ▼
BOUND
       │ required capabilities health/readiness
       ├────► DEGRADED / NOT_READY
       ▼
READY
       │ later runtime health or policy change
       └────► DEGRADED / REVOKED / REQUIRES_RESTART
```

Финальная библиотечная форма этих состояний **UNKNOWN**. Диаграмма фиксирует разницу смыслов. Для безопасного product UI важно показывать конкретный этап и причину, а не один `enabled`.

## 5.3. Entry points как discovery, а не доверие

PyPA entry points — подтверждённый нейтральный механизм рекламы возможностей Python distributions. Его уже использует `stratbox` в ранней реализации. [I02–I03; E01]

**[TARGET-HYPOTHESIS]** Рекомендуемая базовая форма для *trusted Python contributions*:

```toml
# EXAMPLE ONLY; not existing contract
[project.entry-points."stratbox.extensions.v1"]
"example.storage" = "example_storage.extension:get_descriptor"
```

Правила:

- группа/API major фиксирует поддерживаемый discovery contract;
- `plugin_id` стабилен и не зависит от import path;
- обнаружение metadata проводится **до импорта исполняемого provider**, насколько позволяет packaging;
- дескриптор должен иметь side-effect-free discovery mode;
- release/source hashes и allowlist проверяются при активации;
- установленная distribution **не** получает запуск только потому, что попала в `sys.path`;
- несовместимость/конфликт и ошибочная обязательная activation **не** маскируются локальным fallback;
- установка/обновление пакета происходит через управляющую среду и требует нового managed activation для v1;
- неизвестные контракты и лишние configuration keys в production являются контролируемой ошибкой.

**Уточнение:** один entry-point group для всех типов полезен как каталог дескрипторов, но **не должен стирать** типы contributions: `storage` и `domain.operation` не обладают одинаковым контрактом доверия. По мере развития может оказаться проще несколько versioned groups либо единая group с типизированным descriptor. **UNKNOWN** — это implementation choice, решаемый по 2–3 реальным extension пилотам и простоте conformance, а не по абстрактной красоте.

## 5.4. Декларация `ExtensionDescriptor`

```yaml
# TARGET EXAMPLE. Omit all private infrastructure specifics.
plugin_id: example.analytics.addon
plugin_api: 1
release:
  distribution: example-analytics-addon
  version: 1.2.0
  wheel_sha256: "<sha256>"
compatibility:
  stratbox_api: "1"
contributions:
  - contribution_id: example.analytics.source_catalog
    type: source.catalog
    contract_version: 1
    namespace: example.analytics
  - contribution_id: example.analytics.reporting_theme
    type: artifact.style_set
    contract_version: 1
    namespace: example.analytics
required_capabilities: []
effects_declared:
  - storage.read
config_schema_ref: schema:extensions/example.analytics.addon@1
health_contract: health.v1
```

Эта декларация — **заявление пакета**. Само по себе оно не подтверждает успешное тестирование, непротиворечивость эффектов, совместимость данных или доверие к коду. Runtime должен сопоставить пакет, signer/source, фиксированный hash, тип contributed capability, разрешённую среду и required conformance profile.

## 5.5. Selection, binding и cardinality

Extension runtime должен знать *где допускается один активный provider*, а где разрешено множество независимых contributions.

| Contribution slot | Типичная кардинальность | Правило при нескольких кандидатах |
|---|---|---|
| `storage.workspace` | 1 active binding на workspace/context | только явный выбор, конфликт без binding |
| `secrets.default` | 1 на activation scope | явный selection/profile |
| `network.policy` | 0..1 либо явная chain policy | никакого случайного порядка entry points |
| `artifact.style_set` | many, namespaced | устойчивый merge с проверкой коллизий |
| `source.catalog` | many, namespaced | валидируемые независимые source IDs |
| `domain.operation` | many, уникальный semantic ID+version | конфликт одинаковой identity блокирует публикацию |
| `execution.backend` | many available, один explicit binding на выбранный Job | selection по capabilities + policy; запрещён silent failover после эффекта |

Кардинальность является **политикой владельца extension point**, а не свободно объявляемым произвольным плагином правилом. Дополнительный style preset может быть предложен как default, но глобальный default выбирает пользовательская/управляемая конфигурация, а не победитель случайного обхода списка.

## 5.6. Два типа fallback

**Semantically equivalent fallback** допустим, если идентичны наблюдаемый результат, безопасность, целостность и пределы эффектов, а fallback отражён в diagnostics/provenance. **Semantically weaker fallback** является иной capability: например, атомарное перемещение нельзя автоматически подменять `copy → delete` и говорить, что гарантия осталась прежней. Для required provider production profile действует принцип **fail-closed**. [R09]

Параметр `optional=True` означает «без этой способности продукт способен выполнять определённый subset разрешённых задач», а не «ошибку обязательной операции разрешено замаскировать успешным пустым результатом».

## 5.7. Как потребитель узнаёт состояние расширения

Рекомендуемый публично-безопасный status:

```yaml
plugin_id: example.analytics.addon
lifecycle: ready
version: 1.2.0
api_compatible: true
contributions:
  source.catalog:
    state: ready
  artifact.style_set:
    state: ready
configuration_action: none
restart_required: false
safe_diagnostics:
  - code: EXTENSION_READY
```

UI показывает имя, версию, поставщика, функции, состояние, совместимость, разрешённые пользовательские настройки и ссылку на штатное управление поставкой. Он не показывает сырые переменные окружения, credentials, внутренние hostnames, endpoint URLs и служебные identifiers без явного публичного права на раскрытие.

## 5.8. Security model: trusted code ≠ sandbox

In-process Python extension имеет доступ к правам процесса. Список объявленных effects **не создаёт технической изоляции**. Поэтому:

- произвольные community extensions нельзя считать безопасными только из-за корректного descriptor;
- доверенный runtime требует install allowlist, verified artifacts, review и governed activation;
- изоляция непривилегированных third-party исполнителей — отдельный out-of-process контракт с файловыми/сетевыми/процессными ограничениями;
- возможные worker permissions и OS sandboxing выбираются owner среды и execution backend, а не одной фразой в manifest;
- данные и артефакты должны пересекать границу ограниченно и с explicit grants.

**[UNKNOWN]** Будет ли Strategy Box поддерживать недоверенные плагины вообще. Для ближайшего цикла достаточно **trusted, managed extensions** с конформностью; отдельная marketplace/sandbox модель пока не обоснована спросом.

---

# 6. Классы contributions: кто действительно владеет расширяемостью

## 6.1. Infrastructure providers

**Owner:** публичные нейтральные интерфейсы в `stratbox.base` / его будущем versioned extension layer. **Implementation owner:** соответствующий устанавливаемый provider. **Environment owner:** AppDock/другая управляемая среда, если речь об установке, activation context и секретах.

Допустимые classes: FileStore, secret resolution, outbound network policy, optional transport, health/readiness. Provider реализует *механику доступа*, а не business semantics, расчет показателей или политику принятия аналитических доказательств.

Required contract properties:

- typed `NotFound`, `PermissionDenied`, `Unavailable`, `Unsupported`, `PartialFailure`, `ConfigurationRequired`;
- честная capability matrix (read/write/stat/rename/stream/atomicity);
- validation path scope и destructive guards;
- declared concurrency (`thread_safe` / `serialized` / `process_local`);
- deterministic configuration provenance, secret redaction;
- separate `liveness` and `readiness` checks;
- никакого network/secret I/O при чистом discovery;
- timeout/retry with governed budget;
- конформные error semantics независимо от конкретного транспорта.

**Критическое ограничение:** `ready` по проверке импорта не доказывает capability write/read/rename. Нужны ступени static → connectivity → безопасный read/write roundtrip в тестовом namespace по явному разрешению.

## 6.2. Domain operation contributions

**Owner семантики:** `stratbox` для встроенных банковских и макроэкономических предметных методов. Дополнительный внешний publisher может объявить новый namespace операций только после explicit admission и conformance по domain semantics. Такой механизм **пока отсутствует** и требует более строгого review, чем обычный стиль отчёта.

**Важная развилка:** не превращать инфраструктурный provider API в разрешение произвольному плагину вливать расчётные алгоритмы. Возможны два будущих класса:

- **core-owned canonical operations** — maintained first-party source, shared Python library, стабильный definition;
- **externally contributed domain operations** — отдельный release owner, namespace, source/measurement methodology, signatures/assurance, conformance и trust tier.

Для второго класса необходимо решить, кто отвечает за экономический смысл, качество данных, release и дефектный результат. Если этого ownership нет, contribution не может быть admitted как canonical operation. **[UNKNOWN]** Полный general-purpose API для сторонних domain contributions не является доказанной потребностью v1.

## 6.3. Source providers и каталоги

**Owner:** `stratbox.sources` / доменные источники. Extension может предложить `SourceDescriptor`, discovery adapter и source-specific validation, сохраняя различие между **описанием источника** и **зафиксированным полученным SourceSnapshot**. [R06; C03]

Source contribution не должен:

- переопределять официальный identity источника другой namespace без review;
- делать полученный файл «официальным» только наличием URL;
- менять semantics метрик внутри source transport adapter;
- скрывать историческое изменение схемы;
- молча перетирать канонический registry snapshot;
- предоставлять token/credential в `SourceDescriptor` или AI projection.

Расширяемость источников требует независимых `source_id`, `schema_version`, `authority`, `cadence`, `freshness`, `validation`, `content_hash` и cause-of-change. Новые официальные источники из основного корпуса лучше добавлять controlled Git authoring/CI, а не через UI-редактор пакета в runtime.

## 6.4. Registry contributions

Доменный code registry, справочник reference data, список источников и runtime operation registry — разные реестры. Расширение справочных значений допустимо только с явным `registry_id`, source provenance, version, effective dates и conflict policy. Произвольная замена «актуального» справочника путем случайного `mtime` или выбора первого файла не соответствует воспроизводимому анализу. [R06; C03]

Следует различать:

- **authoritative registry snapshot** — опубликованная/контролируемая версия;
- **overlay** — пользовательские соответствия, aliases, предпочтения, отдельное lineage;
- **domain mapping** — доказательный перевод между классификаторами/формами;
- **operational catalog** — machine descriptions capabilities.

Объединять их одной «таблицей настроек» или одним абстрактным `RegistryPlugin` не нужно.

## 6.5. Artifact style providers

**Owner механики оформления:** `stratbox` artifact/export layer; **owner semantic choice default:** user/managed configuration; **source style data:** builtin либо валидируемый extension contribution. [R10; R11]

**Allowed:** декларативные палитры, темы таблиц, типографика создаваемых XLSX/DOCX/PPTX/MD/plot артефактов, title/source/note/block tokens, report presets, допустимые метаданные файла, versioned style set IDs.

**Not allowed as v1:** произвольные Qt widgets, QSS injection, навигационные вкладки, shell themes, Font injection в процесс UI, изменение прав/бизнес-алгоритмов, исполняемые post-processing hooks без отдельного sandbox/contract. Файловая тема и тема интерфейса — разные системы. [R10–R11]

При генерации артефакта фиксируется `style_set_id + version + effective_parameters + formatter_version`, а фактический создатель результата в provenance хранится отдельно от явно устанавливаемого поля `document_author`. UI может предоставлять компактный выбор профиля оформления, но создание Excel остаётся core operation.

## 6.6. Format adapters и converters

Форматный reader/writer относится к нейтральной IO capability (например, DBF/CSV/XLSX), а не к банковскому domain operation. Для extension формата нужны `mime/extension handling`, read/write support, maximum-size/streaming, encoding, file safety, data loss rules, progress, exception normalization и conformance. Конверсия с предметной интерпретацией (например, регуляторная форма DBF → semantic canonical long) — уже доменная операция.

Прямой generic «открыть любую библиотеку по имени» для невалидированных форматов следует исключить из machine API. [R07]

## 6.7. Execution backend contribution

Physical placement может расширяться через `ExecutionBackend` (local worker, isolated subprocess, разрешённый remote worker). Он обязан заявлять features: locality, resource envelope, supported execution package identity, cancellation, artifact staging, heartbeat, worker lease/fencing, reconciliation, security boundary и data locality. Наличие backend не делает его eligible для любого Job; планировщик проверяет compatibility и rights.

**Ключевой запрет:** удалённый backend не должен иметь собственного второго `ScenarioRegistry`, «своей истины» Work или независимого необъявленного retry поверх управляющего runtime. [C04; R12]

## 6.8. Extension types, которым сейчас лучше сказать «пока нет»

- произвольные UI plugins и runtime-изменение shell;
- arbitrary Python/PowerShell command plugins без отдельного permissioned execution model;
- auto-loaded private domain logic как implicit `stratbox` optional dependency;
- плагины, способные переписывать чужую Scheme/OperationDefinition по совпадению имени;
- сторонние «AI reasoning modules» с правом напрямую публиковать Outcome/Artifact, минуя Strategy Box admission;
- универсальный магазин расширений без цепочки доверия;
- hot reload исполняемых библиотек в фоне одновременно с running Jobs.

С точки зрения v1 **меньше extension points, но с проверяемыми контрактами — сильнее**, чем большой перечень слабых точек внедрения.

---

# 7. Scheme, Scenario и capability composition

## 7.1. `SchemeDefinition` как typed executable knowledge

**[TARGET-HYPOTHESIS]** SchemeDefinition описывает повторяемое решение задачи и состоит из узлов, портов, зависимостей и правил принятия результата. Её версию выбирают до планирования, но сама Scheme **не является Run**.

```yaml
# TARGET EXAMPLE — not an implemented DSL
scheme_id: scheme:cbr.monthly_refresh
scheme_revision: 2
inputs:
  effective_date: date
  target_scope: workspace_ref
steps:
  - id: fetch_raw
    uses: operation:cbr.files.collect@1
    inputs:
      date: inputs.effective_date
  - id: escrow_history
    uses: operation:escrow.build_history@1
    depends_on: [fetch_raw]
    inputs:
      source_snapshot: steps.fetch_raw.outputs.source_snapshot
  - id: export_xlsx
    uses: operation:escrow.export@1
    depends_on: [escrow_history]
    inputs:
      data_ref: steps.escrow_history.outputs.dataset_ref
outputs:
  workbook: steps.export_xlsx.outputs.artifact_ref
postconditions:
  - output_artifact_verified
```

Здесь `uses` — semantic reference, **не** Python import path. Связь `steps.fetch_raw.outputs.source_snapshot` должна быть типизирована. Planner вправе отказать, если операция реально не возвращает нужный тип, требование source snapshot не выполнено или версии несовместимы.

## 7.2. Условия, ветви, fan-in и parallelism

Для первой реальной реализации достаточно **последовательной** Scheme + двухветвевой DAG; затем проверять потребности:

- branch по typed validation result;
- conditional node со строго ограниченным language/expression evaluator;
- optional steps с формализованным эффектом отсутствия;
- map/foreach over bounded typed sets;
- fan-in, где политика partial/exact completeness известна;
- parallelism только при доказанной независимости read/write sets;
- checkpoints на семантически важных границах;
- bounded dynamic replanning через новую plan revision, а не изменения живого графа без истории.

Свойство `parallelizable=True` без resource/effect assessment недостаточно. Схема, у которой два шага пишут один логический артефакт, должна указать serial order либо conditional publish.

## 7.3. Definition, Invocation, Binding, Plan, Run

| Уровень | Пример | Можно изменять после старта? |
|---|---|---|
| SchemeDefinition | «обновление источников» v2 | новая revision, историческая остаётся |
| Invocation | дата, выбранные источники, output policy | до admission; позже — отдельный change request |
| Binding | concrete compatible operation providers/execution policy | фиксируется на плановый epoch |
| ExecutionPlan | graph с inputs, versions, policy snapshot, effects | immutable или только explicit revision/amendment |
| Run | фактическое выполнение этого плана | события/status, не подмена definition |

Именно это различение защищает автоматизацию от ситуации, когда «завтра обновился preset» и вчерашний запущенный расчёт задним числом получил новые параметры.

## 7.4. Applicability и capability gaps при компиляции

Planner должен различать:

```text
APPLICABLE          условия доказаны
NOT_APPLICABLE      конкретное препятствие/несовместимый domain scope
REQUIRES_INPUT      ожидаются параметры/источник
REQUIRES_APPROVAL   известное разрешимое ожидание authority
DEPENDENCY_MISSING  нет provider/backend/format/version
UNKNOWN             сведений для проверки недостаточно
```

`UNKNOWN` не равен `False`. Пример: отсутствие новой публикации по состоянию на дату проверки не доказывает нулевого объёма кредитования или отсутствия источника вообще. Если Scheme требует достоверной полноты, запуск откладывается/отказывается с объяснением, а не молча принимает пустой DataFrame.

## 7.5. Дедупликация, shared resource и reuse

Три операции планировщика принципиально разные:

- **dedup** двух будущих invocation только при полной semantic equivalence inputs/source versions/effects/destinations/authority;
- **reuse** ранее verified Result/SourceSnapshot при актуальной freshness/currentness policy;
- **shared resource** — соединение, quota, read-only cached snapshot, pool, без фиктивной бизнес-операции `connect`.

Ни одна из них не выводится из совпадения `operation_id` и параметров наивным равенством JSON. Одни и те же вычисления в два разных destination — две разные публикации артефакта. Plan/Apply destructive operations никогда не dedup по умолчанию. [C04]

## 7.6. Как Machine Scheme видит AI

Внешний когнитивный consumer получает **описание целей, применимости, типов, эффектов, evidence, доступных schemes**, но не внутренний Python код, сетевую топологию или права на произвольные действия. Он может предложить Scheme invocation или draft новую композицию. **Admission, type checking, policy, plan binding и effect approval остаются у Strategy Box**.

Скомпилированная deterministic scheme **не должна** становиться «магическим непрозрачным ответом ИИ». Её происхождение, version, assumptions, inputs, output quality и failure/status должны быть проверяемыми. Самостоятельный «AI-Scheme Executor» приведёт к дублированию и несогласованному аудиту. [R13–R16]

## 7.7. Эпистемические рамки схем

Поскольку Strategy Box работает с внешней банковской статистикой, Scheme обязана различать:

- «файл получен» и «данные корректно прочитаны»;
- «таблица построена» и «показатель имеет правильную экономическую интерпретацию»;
- «опубликованное число» и «оценка/восстановленная величина»;
- «расчёт завершён» и «аналитический результат принят»;
- «источник свежий» и «источник соответствует используемой версии методологии».

Структурный граф исполнения не заменяет domain validation, provenance и квалификацию доказательности. ИИ получает evidence *на выходе* Scheme и не может повысить качество доказательства простой декларацией. Примером высокого доказательного стандарта внутри нынешнего core является SORS restoration; копировать весь его математический аппарат в каждый простой domain не нужно. [R01; C03]

---

# 8. Automation architecture: определения и жизненный цикл

## 8.1. AutomationSpec является долговечной product definition

**[CONSOLIDATED]** Автоматизация связывает повторяемую цель с trigger, target capability, правами, параметрами, budget и условиями оповещения. Она живёт независимо от конкретного user session, активного клиента и одной Job. Выключить автоматизацию — запретить будущие срабатывания по policy; уже работающий Job остаётся фактом и отменяется только отдельной авторизованной командой. [R03; R08; C04]

```yaml
# TARGET EXAMPLE — not current API
automation_id: automation:cbr-monthly
revision: 5
owner_principal: principal:analyst-1
status: enabled
target:
  type: scenario
  ref: scenario:cbr.monthly_update@3
params_profile:
  ref: profile:cbr-monthly@2
trigger:
  type: schedule
  timezone: Europe/Moscow
  calendar: "0 8 * * MON-FRI"
  misfire_policy: coalesce_latest
  jitter_policy: bounded
occurrence_policy:
  identity: automation+revision+scheduled_instant
  overlapping_runs: queue_one
  max_pending: 1
execution_policy:
  placement: node
  resource_class: standard
  deadline: PT2H
  retry_budget: 2
notification_policy:
  on_failure: owner
  on_meaningful_change: subscribers
approval_policy:
  write_effects: within_approved_scope
```

Здесь `timezone`, cron expression и ISO duration — **иллюстрации**. Их точная грамматика и список допустимых policy значений требуют самостоятельной схемы/тестов; это не работающая конфигурация current Windows.

## 8.2. TriggerSpec: пять разных семантик

| Trigger | Обнаруживаемое условие | Основной риск | Что хранить |
|---|---|---|---|
| `schedule` | наступил календарный момент | DST/misfire/дубли | scheduled instant, timezone, rule revision |
| `source_changed` | новая verified publication/snapshot | ложные «изменения» по mtime/URL | old/new source hashes, authority/source ID |
| `event` | произошло допустимое доменное событие | повторная доставка/порядок | event_id, causation, contract version |
| `manual` | пользователь разрешённо вызвал automation | смешение с «run now» | actor, command id, parameter snapshot |
| `condition_watch` | предикат перешёл в состояние, требующее действия | false positives, дорогое polling | evaluated evidence, predicate revision, debounce |

**Long-running listener** — иной runtime pattern (persistent subscription/connection), но его meaningful trigger occurrences должны попадать в тот же engine. Не создавать отдельную «вечную фоновую операцию» только потому, что источник умеет push updates.

## 8.3. Occurrence имеет стабильную identity и решение

При каждом trigger evaluation результатом становится не сразу Job, а `TriggerOccurrence`:

```text
observed / evaluated
    ├─ SKIPPED (disabled, duplicate, policy, no-change)
    ├─ SUPPRESSED (debounced/coalesced)
    ├─ REQUIRES_INPUT / REQUIRES_APPROVAL
    ├─ ADMITTED → WorkCandidate / existing Work → Run / Jobs
    └─ EVALUATION_FAILED / UNKNOWN
```

Для расписания identity включает automation ID, revision и intended scheduled instant; для события — source/event identity и scope; для изменения источника — stable source ID + source snapshot hash/version + rule revision. Повторная доставка должна давать тот же occurrence result, а не второй неконтролируемый эффект.

## 8.4. Schedule semantics: часы, DST, misfire и catch-up

Здесь невозможно ограничиться «время следующего запуска» в UI. Нужны конкретные решения:

- timezone привязана к определению automation, а не к timezone устройства, которое сейчас открыло карточку;
- хранится intended wall-clock rule, resolved UTC occurrence и policy при смене offset;
- несуществующий при переходе DST локальный час: `skip` или `next_valid`;
- повторяющийся час: `once_first` или `once_second`/два, в зависимости от явно утверждённой policy;
- после простоя scheduler: `skip`, `run_latest`, `coalesce`, либо bounded catch-up;
- automation revision обновляет будущие occurrences, но сохраняет историю прошедших;
- overlap policies: `skip`, `queue`, `coalesce`, `allow_parallel` только при resource safety.

**[TARGET-HYPOTHESIS]** В первом пилоте `coalesce_latest` для update/watcher задач и `skip` для малополезных повторений выглядят разумно; но дефолты надо закрепить Product Decision и проверить на реальных business cadences.

## 8.5. Source watcher не должен сравнивать только URL и имя файла

Source watcher опирается на versioned `SourceDescriptor`, проверенный `SourceSnapshot` и условия freshness. HTTP `200` и новый `ETag` ещё не гарантируют семантически новую статистическую публикацию; совпавший URL не гарантирует прежнее содержимое. Для источников, публикующих исправления задним числом, значимы content hash, declared period, schema version и change classification. [R06; C03]

Срабатывание `source_changed` должно содержать как минимум:

```text
source_id
previous_snapshot_ref
new_snapshot_ref
change_kind (new_period / revised_data / schema_change / inaccessible / unknown)
validation_result_ref
observation_time
rule_version
```

Изменение формата или недоступность источника может требовать diagnostic Work вместо автоматического пересчёта; «доступен новый файл» и «можно безопасно построить новый показатель» — разные проверки.

## 8.6. Scheduler owner и процессный lifecycle

**[CONSOLIDATED]** Единственный authoritative scheduler на scope узла/рабочего пространства принадлежит **Strategy Box application runtime**. Его состояние и history должны переживать закрытие UI. AppDock может обеспечить запуск host process, heartbeat, process health, restarted service, node identity и согласованный transport. OS scheduler может использоваться как bootstrap для самого host, но не как независимый каталог отдельных банковских автоматизаций. [C04; R08; R12; A01]

Это устраняет конфликт ранней схемы, где AppDock иногда описывался как владелец «планировщика всех сценариев». Такое делегирование лишило бы Strategy Box authoritative history, domain misfire policies и согласованной связи с Work/Run.

## 8.7. Automation не может тайно присвоить больше полномочий

При создании automation проверяются права на target и effects. Однако при каждом occurrence и непосредственно перед значимым эффектом необходимо заново проверять действующие grants/approvals и scope. Отзыв права или изменение policy может остановить новую occurrence и потребовать reapproval. Сохранённый «enabled» не означает вечный токен без срока и ограничений.

**Разделить:** кто владеет правилом, от чьего имени оно действует, кто может управлять им, какие grants действуют на момент эффекта и кто получит уведомление. Удалённая/фоновая задача не наследует неограниченный authority только из-за того, что инициатор давно отключился.

## 8.8. Действия без создания «пустых» Work

Не каждый технический poll и skip должен становиться пользовательской Work. У automation могут быть:

- технические evaluations и skipped occurrences;
- meaningful occurrence → новый Run в долговечном мониторинговом Work;
- meaningful occurrence → новая Work по отдельному бизнес-кейсу;
- diagnostic event/problem без user-facing Work;
- notification, если изменился доменно значимый факт.

Политика определяется purpose: «проверять публикации каждый час» может быть одним долгим мониторинговым Work, а «сформировать отчёт за сентябрь» — отдельным Work на каждый период. Механическое `1 cron tick = 1 Work` создаёт шум и разрушает продуктовую timeline.

---

# 9. Execution backends и runtime placement

## 9.1. Один JobManager — несколько физических исполнителей

**[CONSOLIDATED]** Capability catalog и AutomationSpec не должны сами исполнять задачи. Admission формирует одобренный `ExecutionPlan`; authoritative JobManager выделяет очереди, ресурсы и Job lease; backend выполняет контролируемые вызовы и возвращает **receipts/observations**, а не самовольно закрывает Work. [C04]

Кандидат интерфейса:

```python
# CONCEPTUAL ONLY. Neither API nor naming is implemented today.
class ExecutionBackend(Protocol):
    def describe(self) -> BackendCapabilities: ...
    def prepare(self, job: JobEnvelope) -> PreparationReceipt: ...
    def start(self, job: JobEnvelope, lease: LeaseToken) -> StartReceipt: ...
    def observe(self, job_ref: JobRef) -> JobObservation: ...
    def request_cancel(self, job_ref: JobRef, reason: str) -> CancelReceipt: ...
    def reconcile(self, job_ref: JobRef) -> ReconciliationReceipt: ...
    def collect_outputs(self, job_ref: JobRef) -> ExecutionReceipt: ...
```

`Protocol` описывает только форму сообщений. Для настоящего isolated/remote транспорта потребуются wire-compatible schemas, authentication, version handshake, consistency guarantees, idempotency/fencing и transport errors. In-process Python Protocol не равен распределённому RPC контракту.

## 9.2. Feature matching вместо «первый доступный executor»

Planner проверяет:

```text
required python/runtime packages and exact hashes
required operation/scheme contract versions
OS/architecture constraints
data residency and source access
storage/artifact staging support
network access and policy
memory/CPU/bandwidth resource classes
cancellation capability
checkpoint/restart semantics
lease/fencing guarantees
security isolation/trust level
```

Backend выбирается **до** публикации обязательств плана. Возможна полная недоступность подходящего backend: `DEPENDENCY_MISSING`, `BACKEND_UNAVAILABLE` или explicit queue/wait. Этот отказ не должен автоматически превращаться в execution на GUI Thread, который случайно оказался свободен.

## 9.3. Local worker, subprocess, remote node

| Backend | Подходит | Ограничения |
|---|---|---|
| Local in-process worker | дешёвые короткие read-only операции, interactive development | crash isolation слабая; процесс UI не должен зависнуть |
| Isolated local subprocess | тяжёлые CPU-bound/потенциально нестабильные парсеры и вычисления | нужны process lifecycle, IPC, staging и termination semantics |
| Node-local headless worker | durable jobs, multi-client, schedule, shared resources | требуется authoritative state/store и background service |
| Remote worker/node | data locality, большой расчёт, long-running host | требуется external transport boundary, authentication, compatibility, reconciliation |

**[TARGET-HYPOTHESIS]** Первым production-like этапом лучше сделать локальный headless worker/isolated subprocess. Он докажет правильность JobManager и idempotency без преждевременной разработки distributed system. Реальный remote backend вводить только после проверки контрактов AppDock и recovery на одном узле.

## 9.4. Resource claims, locks, leases

`ResourceClaim` относится к **требованию ресурса**; `ResourceLock` — к запрету конкурирующего изменения объекта; `WorkerLease` — к праву worker опубликовать результат Job. Они разные.

Например:

- два чтения разных SourceSnapshots можно выполнять параллельно при соблюдении rate limits;
- два независимых расчёта без записи общего destination можно выполнять одновременно в пределах RAM budget;
- два экспорта одного имени logical artifact требуют условного commit/serialization;
- destructive cleanup namespace требует эксклюзивного lock после validation плана;
- тяжёлой SORS-оптимизации нужна memory/CPU quota и controlled worker selection;
- историческое состояние `RUNNING` не подтверждает, что процесс по-прежнему владеет актуальным lease.

После истечения lease старый worker может ещё физически работать. Только current fencing generation/transactional commit предотвращает публикацию вторым старым исполнителем **в управляемое хранилище**. Если внешняя система не поддерживает fencing/idempotency, исход может стать `OUTCOME_UNKNOWN` и потребовать сверки.

## 9.5. Retry budgets и side-effect boundaries

Возможны вложенные уровни retry — HTTP client, parser, OperationRun, Job, remote transport. Без общего governing budget их перемножение способно создать из «3 попыток» десятки/сотни побочных действий. Следует объявлять один budget для каждого material effect boundary, а транспортный retry включать только если известны safe idempotency условия.

События `request_cancel`, `abort_inflight`, `terminate_process`, `rollback` **не синонимы**. Отмена — запрос на безопасное прекращение; rollback возможен только там, где contract действительно умеет компенсировать/откатить effects. Запрос после commit может опоздать, и terminal outcome останется `SUCCEEDED` с отдельным `cancel_too_late` control result. [C04]

## 9.6. Outcome unknown и reconciliation

Сценарий:

```text
worker successfully published artifact
   ↓
connection dropped before ACK
   ↓
controller sees timeout
   ↓
OUTCOME_UNKNOWN (not FAILED)
   ↓
reconcile artifact manifest / commit receipt / destination version
   ├─ verified committed  → record reconciliation success
   ├─ verified absent     → safe retry if policy permits
   └─ impossible to tell  → keep uncertainty / ask operator
```

Не обещать `exactly once` за пределами своих transactional/idempotent границ. **Один terminal receipt** можно гарантировать для собственного Job state transition; «один внешний эффект» зависит от idempotency протокола destination. Исторический terminal факт не следует беззвучно переписывать: результат сверки добавляет новое документированное evidence/reconciliation событие.

## 9.7. Staging, verification, artifact publication

Перед terminal success обязательна последовательность:

```text
calculation/collection
 → staged output
 → data/format completeness verification
 → domain quality check
 → artifact manifest + lineage
 → conditional/atomic publish where supported
 → effect receipt
 → terminal execution outcome
```

**Инвариант:** `100% progress` до успешного commit — только «вычислительная стадия завершена», а не утверждение о полном результате. Fail during staging сохраняет diagnostic и не публикует частичный файл как окончательный. Result/Artifact/Work acceptance остаются разными объектами. [C03; C04]

## 9.8. AppDock collaboration boundary

AppDock владеет узлом, managed process, installation/environment, health и возможностями подключения в рамках собственного интерфейса. Strategy Box владеет операциями и бизнес-запусками. Возможность AppDock рестартовать host **не значит**, что AppDock автоматически знает безопасную семантику повторного выполнения банковского расчёта. При рестарте Strategy Box восстанавливает queue/leases/receipts/attempts из собственного durable store.

Для внешней платформенной диагностики предоставляется **sanitized health/problem projection**, а не полная история защищённых источников, параметров, секретов или пользовательских файлов. Cross-node remote execution остаётся зависимостью от официально зафиксированного transport/identity contract соответствующего owner.

---

# 10. AI tool exposure и внешний machine-consumer

## 10.1. Одна операция — несколько представлений

```text
OperationDefinition (same identity, version, effects)
      ├─ Python import facade for developer
      ├─ Scenario UI form for human
      ├─ Headless Job submission API
      ├─ Automation target
      └─ AI/MCP tool projection
```

Эти представления могут разрешать **разные подмножества** параметров и действий. Различие — policy/consumer view, не переписанная бизнес-операция. Если нужная семантика существенно другая, создаётся новая Operation version или отдельная Scheme, а не потайной AI-only handler.

## 10.2. Машинный каталог всегда context-filtered

Машине следует показывать только:

- актуальные compatible и activated definitions;
- допустимые в её namespace/scopes операции и схемы;
- достаточную, но safe семантику parameters/results;
- честные annotations effects/risk/required approvals;
- applicable source/registry constraints без раскрытия чувствительных служебных данных;
- текущие readiness/limitations;
- явный `operation_id + version`, а не динамически выдуманный tool name.

Пользовательский список «всё установленное» и AI tool list — разные projections. Даже read-only операция может читать чувствительные datasets, поэтому `read_only` **не эквивалент** `publicly safe`.

## 10.3. MCP — адаптер, а не онтология Strategy Box

Спецификация MCP Tools позволяет публиковать инструмент с input/output schemas и annotations; annotations из недоверенного сервера нельзя автоматически принимать за политику безопасности. [E03] Поэтому **MCP пригоден как adapter для machine capability discovery/invocation**, но:

- MCP tool name — внешняя проекция, `operation_id` — внутренняя semantic identity;
- tool annotations помогают consumer, но authoritative effect/permission policy проверяется у Strategy Box;
- opaque `tool_result` не подменяет Run/Job/Artifact/qualifications;
- MCP task semantics, если используются, привязываются к existing Run/Job IDs;
- raw storage paths, secrets и unrestricted Python не входят в базовый tool catalog;
- MCP framework/client не определяет собственную жизненную историю Work.

Разрешённый contract:

```text
AI proposes Intent / OperationRef / SchemeRef / structured arguments
   → Strategy Box validates and admits
   → plans, checks rights/effects/applicability
   → returns Work/Run/Job references
   → agent observes progress/Result/ArtifactRef
   → optional new proposal or human acceptance
```

## 10.4. Два сценария взаимодействия с ИИ

**Conversational router.** Модель интерпретирует пользовательскую фразу, выбирает существующую ScenarioDefinition, заполняет draft и просит подтвердить запуск при необходимости. Сама business execution остаётся детерминированной. Это относительно простой первый путь.

**Cognitive planner/agent.** Модель предлагает последовательность Operations/Schemes, анализирует результаты и может запросить новый план. Каждая новая существенная branch/effect требует versioned proposal → validation/admission. Агент не получает прямых прав на публикацию документа как подтверждённого результата только потому, что способен написать текст. В банковской аналитике особое значение имеют **evidence qualification** и неразличение неизведанного с нулём. [R13–R16]

## 10.5. Уровни самостоятельности AI

| Уровень | Разрешение | Обязательная рамка |
|---|---|---|
| A — inspect/explain | каталог, описание, безопасная диагностика | только разрешённая видимость |
| B — propose | WorkCandidate, draft parameters, plan proposal | проверка input/plan/authority |
| C — read/compute | допущенные read-only вычисления | квоты, доступ к данным, provenance |
| D — controlled write | export/publish в разрешённый scope | effect scopes, idempotency, verification |
| E — approval-gated destructive | plan/apply в пределах явного согласования | approval, revalidation, signed effect scope |

Уровень относится к **principal + operation + context**, а не к глобальному флагу `ai_enabled`. Один агент может иметь C для статистического расчёта и только B для удаления файлов. [R08; R14]

## 10.6. Безопасность prompt/tool-content

Недоверенные внешние материалы (HTML официального источника, Excel комментарии, OCR, описание файла, имя артефакта, текст из plugin) являются **data**, а не инструкциями для policy engine. Ни одна строка, полученная при загрузке статистического источника, не может менять permissions, выбирать provider, инициировать destructive действие или изменять active Scheme definition.

Всякому machine request требуются:

- caller identity/principal и provenance delegated authority;
- schema validation;
- authorization/resource/approval validation;
- ограничения на произвольные paths, URLs, datasets;
- trace/correlation and effect receipts;
- explicit outcome uncertainty;
- отдельная граница секретов и redaction.

## 10.7. Никакой двойной «машинной истины»

Внешняя cognitive система может сохранять историю рассуждений и предлагать гипотезы, но **не владеет** Strategy Box `SourceSnapshot`, canonical dataset, business operation semantics, Job terminal receipt, authority grant или принятым Work closure. Обновление этих объектов происходит через проверяемые API и установленную предметную политику. [R13–R16]

---

# 11. Settings, visual resources и пользовательский контроль extensions

## 11.1. Три собственника конфигурации

| Конфигурация | Владелец | Меняется где |
|---|---|---|
| Installation/deployment profile, package trust, mandatory activation | AppDock/deployment authority | managed environment, при update/restart |
| Strategy Box product policy, capability bindings, automation rules, quotas | application/runtime owner | управляемые product controls |
| User preferences: тема, акцент, artifact style default, allowed plugin options | user within policy | `stratbox-windows`/другая surface |

`RunParameters` и `ExecutionPlan` после запуска — **не настройки**; они являются immutable execution facts. «Последний открытый сценарий» и «ширина правого инспектора» — surface state, а не extension contract. [R11; C02]

## 11.2. Раздел «Плагины» — безопасная projection

Разрешённое содержимое:

```text
расширение / отображаемое имя
поставщик / installed version
compatibility / activation / readiness
contributions с user-facing описаниями
required / optional и policy-managed state
безопасная конфигурация по schema
перезапуск при изменении набора providers
диагностика/ошибки (sanitized)
ссылка на штатный установщик/управление пакетом
```

В UI допустим toggle только для user-manageable optional extensions и только через полномочия owner. Если extension требуется управляемой поставкой, UI показывает **«управляется администратором»**, а не активную кнопку, которая не может исполнить обещание. Активация новой версии библиотеки в работающем shared host требует управляемого restart/drain, а не незаметного hot reload.

## 11.3. Plugin options — не произвольный preferences dictionary

Параметры configuration имеют namespace, `type`, `required`, `sensitive`, `editable_by`, `restart_required`, `default`, bounds, validator и безопасное explanation. Runtime должен отвергать неизвестные keys в production, сохранять происхождение применённого значения, не сериализовать secret values в JSON settings/events и отделять form draft от фактически active binding.

## 11.4. Artifacts styles не перекрашивают Strategy Box shell

Один style provider может поставлять выбор оформления нового XLSX, шрифтов и цветов *в документе*. Тема Windows/Android/Web определяется общей продуктовой visual system и native UI rendering. Разрешение изменять стиль документа **не** равно разрешению подменить QSS, Qt Widgets или layout приложения.

Эта граница защищает переносимость Windows → Android и снижает потребность в отдельном UI-plugin ABI. Для реальной пользовательской потребности «сделать аналитические отчёты в корпоративном стиле» data-only artifact style provider достаточен. [R10–R11]

---

# 12. Версионирование, release governance и conformance

## 12.1. Четыре независимых version axes для расширений

1. **Distribution version** — release конкретного wheel/service/declarative package.
2. **Discovery/activation protocol version** — что runtime понимает в descriptor/lifecycle.
3. **Capability contract version** — какое поведение должен реализовать provider.
4. **Domain operation/scheme semantic version** — смысл аналитического метода и композиции.

Для воспроизводимого managed deployment фиксируются exact package versions/hashes/activation profile, даже если declared compatible ranges широки. Обратную совместимость со старыми Python API сохранять не требуется; для данных нужны доказуемые версии, backup/export при переходе. [R09; C02]

## 12.2. Что является breaking change

**Breaking semantic changes:** изменение набора измерений/единиц output, source selection policy, meaning of `partial`, side-effect set, destructive guarantees, idempotency claim, error semantics, required approvals, source authority, Scheme graph postcondition, applicability envelope. Простое переименование Python helper без изменения public binding может быть internal refactor; новый файл/модуль не обязательно semantic release.

При существенном разрыве выпускается новый definition/contract version и новый plan binding. Old Run history сохраняет старые versions. Не следует «встроить compatibility synonyms» только чтобы old clients перестали падать: проект специально допускает clean cut.

## 12.3. Conformance pyramid

| Уровень | Назначение | Пример gate |
|---|---|---|
| Descriptor/static | schema, identity, dependency graph, namespacing | duplicate ID, invalid version fail |
| Unit/domain | чистая семантика input/output, rules | malformed period refused |
| Provider contract with fakes | обязательные методы и exception taxonomy | `Unavailable` не превращается в `[]` |
| Failure injection | timeout, partial write, permission error, stale registry | no false success/destructive loss |
| Packaging/supply chain | clean wheel, lock/hashes, no runtime install | install/import in isolated env |
| Managed integration | AppDock context/health, real allowed backend | ready/authorization match |
| E2E capability/automation | same behavior via human/automation/AI | one admitted Job/receipt graph |
| Recovery/load | restarts, concurrent writers, schedule misfires | no duplicate effect/terminal |

Для SourceSnapshot/Registry/Data domains требуются также data fixtures, schema-version checks и методологическая приемка, выходящая за generic Provider conformance. Внешние опросы и громоздкие вычислительные подсистемы могут иметь отдельные full-data/performance suites. [R01; R09; C03; C04]

## 12.4. Публичный certification harness

Набор тестов должен использовать **synthetic reference providers** без реальной корпоративной среды. Test output машинно-читаем:

```yaml
# TARGET EXAMPLE
plugin_id: example.analytics.addon
certification_profile: core-contract
plugin_api: 1
result: failed
checks:
  - id: descriptor.duplicate_id
    status: passed
  - id: storage.error_not_found_vs_unavailable
    status: failed
    evidence_ref: test-report:case-214
  - id: metadata.redaction
    status: passed
package_digest: "<sha256>"
```

Существование имитатора, который прошёл tests, **не даёт** другому provider права объявить себя certified. Сертификация связывается с exact release artifact + capability contracts + environment profile + test evidence и временем проверки. Некоторые checks требуют отдельной приватной integration среды, но её подробности не входят в публичный corpus.

## 12.5. Runtime health отдельно от certification

Прошедший однажды conformance plugin может стать `DEGRADED` из-за изменения сети, источников, полномочий, повреждения данных или отсутствия required dependency. Наоборот, сегодняшний `READY` по health-check не доказывает все крайние случаи целостности. Нужны как минимум три состояния:

```text
certification verdict (release evidence)
activation compatibility (environment facts)
operational readiness (current observation)
```

## 12.6. Supply-chain и release integrity

Minimum production practices:

- wheel-first поставка и clean environment install;
- фиксированные package/artifact hashes, source revision и dependency lock;
- test/generate metadata без случайных `.tmp`, `.pyc`, credentials;
- проверяемый supplier/trust allowlist, SBOM при необходимости;
- сканирование публичного репозитория на средо-специфичные reference identifiers;
- no arbitrary runtime `pip install` from plugin execution;
- clear upgrade, restart, drain, rollback/recovery plan;
- conformance до activation in managed production.

## 12.7. Безопасный upgrade при работающих заданиях

**[TARGET-HYPOTHESIS]** В long-running host возможен порядок:

```text
new release staged
 → static compatibility/conformance check
 → stop admitting new jobs with old binding
 → drain or checkpoint old jobs
 → persist final results/receipts
 → activate new profile/version
 → rebuild capability availability projection
 → resume/admit new jobs
```

**UNKNOWN:** допустима ли одновременная side-by-side работа нескольких versions одного provider для длительных Run. Это зависит от процесса, package isolation, live resource semantics и поддержки нескольких worker environments. Для v1 безопаснее restart/drain вместо hot reload.

---

# 13. Наблюдаемость capability/extension/automation

## 13.1. Семантические события против логов

Capability execution должен порождать structured events (admission, plan, operation, artifact, failure, retry, cancel, trigger), а provider — технические diagnostics/readiness. Логи предназначены для расследования, **не являются единственным источником истины** о состоянии Job или наличии артефакта. [R17; C04]

Минимальный envelope:

```text
event_id / timestamp / kind / schema_version
node_id / run_id / job_id / operation_run_id / attempt_id
operation_id + version / plugin_contribution_ref where applicable
actor/principal_id (safe) / correlation_id / causation_id
status / progress units / effect receipt ref
problem_ref / safe_message / safe_attributes
```

Extension, которая генерирует сырой `print()` или `except: pass`, не удовлетворяет общему observability contract. Ошибка нижнего provider должна стать typed failure и затем, при необходимости, безопасным `ProblemDraft` на платформенной границе; traceback хранится как ограниченное техническое evidence. Платформенный health узла не подменяет предметный success/failure конкретного Run.

## 13.2. Automation traceability

Каждая осмысленная цепочка должна восстанавливаться:

```text
AutomationSpec@rev
  → TriggerOccurrence + evaluation evidence
  → WorkCandidate / Work
  → Run + ExecutionPlan@digest
  → Jobs / OperationRuns / Attempts
  → qualified results, receipts, artifacts
  → notification/read cursor / acceptance
```

При пропущенном запуске сохраняется `SKIPPED` или `MISFIRED` с причиной — отсутствие Result не позволяет понять, работало ли расписание. При `source_changed` нужны old/new snapshot refs, иначе после пересмотра исторических данных невозможно объяснить, почему создался новый Run.

## 13.3. UI наблюдает расширения, но не раскрывает их инфраструктуру

Surface показывает `READY`, `NEEDS_CONFIGURATION`, `REQUIRES_UPDATE`, `NOT_ALLOWED`, `DEGRADED`, `FAILED_CONFORMANCE` с кратким объяснением/действием. Полный технический debug выдаётся только по разрешённой диагностической процедуре и после redaction. Плагин не должен внедрять собственные произвольные error popups поверх продуктовой модели.

---

# 14. Сквозные проверочные сценарии: от контракта к работающей системе

Предыдущие разделы описывают семантическую архитектуру. Здесь она проверяется на конкретных ситуациях. **Все будущие цепочки ниже — TARGET-HYPOTHESIS / проверочные кейсы**, если явно не указано CURRENT. Их нельзя читать как утверждение о готовой реализации.

## 14.1. Одну операцию вызывают Python, Windows, автоматизация и AI

**Исходный capability:** подготовить историю счетов эскроу Банка России. Сегодня такой предметный pipeline уже есть в `stratbox`, а в Windows существует вызывающий его handler. Однако это пока два способа обращения к коду, а не один зафиксированный общесистемный `OperationDefinition` с полноценной контрактной проекцией. [R01; R07; I05]

Целевой путь:

```text
Canonical OperationDefinition: escrow.history.build@contract-version
                   │
        ┌──────────┼──────────┬──────────────┐
        ▼          ▼          ▼              ▼
   Python API   Windows   Automation      AI tool
        │          │          │              │
        └──────────┴──────────┴──────────────┘
                   │
      admission / authority / applicability
                   │
      effective parameters + snapshot refs
                   │
          resolved execution binding
                   │
          Run / Plan / Job / Attempt
                   │
            domain computation
                   │
      structured qualified Result + Artifact
```

*Прямой импорт в ноутбуке* остаётся допустимым потреблением headless Python-библиотеки и сам по себе не обязан создавать Work/Job на узле. Но если Python consumer **регистрирует управляемую задачу**, он идёт через тот же admission/control contract. Это важное различие между библиотечным вызовом и управляемой продуктовой работой.

**Проверка:** смысл вычисления одинаков при одинаковых snapshots и параметрах; состояние управляемого Run одинаково независимо от инициатора; side-effect policy различается только по его разрешённому контексту. Для прямого Python-вызова нужен domain test, для управляемых — дополнительно authorization/execution tests.

## 14.2. Расписание: проверка новой официальной публикации

```text
AutomationSpec: check official publication
  └─ TriggerSpec: schedule + conditional source-change
       └─ TriggerOccurrence: 2026-11-01T...@zone / occurrence key
            └─ fetch/check latest official descriptor
                 ├─ SAME verified snapshot → NO_CHANGE
                 ├─ new snapshot → WorkCandidate → admission
                 │                         └─ Plan/Job/Results
                 ├─ source temporarily unavailable → CHECK_FAILED
                 └─ validation inconclusive → NEEDS_REVIEW / UNKNOWN
```

В этом примере *проверка изменения* может быть лёгкой автономной операцией без новой пользовательской Work; Work создаётся, когда новая публикация порождает реальную задачу обновления. Проверка через ETag/Last-Modified сама по себе лишь ускорение: версию публикации подтверждают содержательные метаданные и/или checksum. Перезапись на прежнем URL не должна остаться незамеченной. [R03; R06; C03; C04]

**Пограничные случаи:** публикация изменила исторический период; сайт временно вернул HTML вместо XLSX; сервер вернул 304 при рассинхронизированном кэше; два trigger occurrences столкнулись за один источник; планировщик был выключен неделю; в локальной timezone произошёл переход DST. Для каждой ветки нужны отдельный outcome проверки, уникальный occurrence key и явная misfire policy.

## 14.3. Два пользователя, один узел, общий источник, разные назначения

Два пользователя запускают независимые сценарии, которым нужен один SourceSnapshot, а результирующие XLSX записываются в разные каталоги.

- Fetch и verified immutable SourceSnapshot можно совместно использовать при совпадении source identity, freshness policy, read scope и прав.
- Различные destinations порождают два самостоятельных write effects и два ArtifactPublication receipts.
- Общий connection pool — resource optimization, но **не** отдельная доменная операция, видимая пользователю.
- Наличие одной открытой Windows-формы не ограничивает очереди второго пользователя: арбитраж у node-wide JobManager, с учётом CPU, памяти, network quotas и write locks.
- Пользователь A может видеть разрешённые сведения о работе B, но не получает автоматически права читать приватные исходные данные или артефакты B. [R18; C04]

**Проверка:** одновременно выполняются два разрешённых read-only вычисления; записи не теряют данные; повторный upload одного назначения сериализован или завершается предсказуемым конфликтом; закрытие UI A не останавливает Job B; история и consent сохраняются после reconnect.

## 14.4. Расширение обнаружено, но недоступно для работы

```text
installed distribution
      ↓ discover metadata
plugin descriptor valid?
      ├─ no  → DISCOVERY_INVALID
      └─ yes
          ↓ package/version/trust verification
      selected in active profile?
      ├─ no  → DISCOVERED, INACTIVE
      └─ yes
          ↓ explicit contribution binding
      capability contract compatible?
      ├─ no  → INCOMPATIBLE
      └─ yes
          ↓ configuration and health
      ├─ config missing → NEEDS_CONFIGURATION
      ├─ policy denied → DISABLED_BY_POLICY
      ├─ runtime unavailable → NOT_READY
      └─ READY → included in applicable capability catalog
```

**Критический случай:** если операция требует обязательный provider выбранного managed-профиля и тот ошибся, действие блокируется с диагностикой. Подстановка локального другого backend допустима только после доказательства эквивалентного контракта и авторизованного fallback. Пользователь не получает ложный success и не теряет признак того, какой provider реально обслужил запрос. [R09; I02]

## 14.5. Два расширения заявили один capability slot

Если обнаружены два вклада в `storage.workspace`, их наличие само по себе не устанавливает приоритет. Для singleton slot требуется явная binding selection в managed profile. Для multi-contributor `artifact_style` действуют другие правила: допускаются несколько уникальных style IDs; коллизия IDs является ошибкой объединения, а не последним «победившим» пресетом. [R09; R10]

**Проверка:** порядок обхода Python entry points не меняет результат разрешения. Один и тот же active profile при одинаковом installed set и versions даёт один и тот же binding snapshot и hash. Любое изменение набора доступных расширений пересматривает readiness и каталог операций до следующего управляемого Run.

## 14.6. Расширение поставило профиль оформления отчётов

```text
ExtensionDescriptor → artifact_style contribution
    ↓ validated unique style ID, version and license
ArtifactStyleRegistry → available style sets
    ↓ user/default/policy selection
Operation request → effective ArtifactStyleSet@version
    ↓ export uses semantic workbook structure
XLSX + artifact metadata + provenance
```

Тема/акцент пользовательского приложения остаются независимыми от профиля XLSX. Указанный в свойствах файла `creator` или `author` не подменяет причинную цепочку фактических `Actor/Principal/OperationRun`. При повторной генерации сохраняются обе идентичности. Произвольное внедрение Qt widgets, QSS и модификация навигации через стиль следует считать другой, **не принятой** категорией расширяемости. [R10; R11; C02]

## 14.7. Опасная операция: удаление выбранного набора файлов

FRG — подходящий домен, потому что в нём уже существует фактическое разделение формирования cleanup plan и применения; полноценный единый approval/effect protocol пока относится к TARGET. [R01; R05; C04]

```text
Work / request cleanup
  → Operation: frg.cleanup.plan
  → immutable PlanRef + effect set + source revisions
  → authorized review / ApprovalRef binding
  → check still-current plan and permissions
  → Operation: frg.cleanup.apply
  → verified per-object effect receipts
  → final outcome: SUCCEEDED / PARTIAL / FAILED / UNKNOWN
```

Если между планированием и подтверждением файлы изменились, применение старого плана получает `STALE_PLAN` и останавливается. Если в ходе удаления часть объектов сохранилась, операция не вправе вернуть «успех» из-за подавленного exception. Если worker упал после внешнего эффекта, но до фиксации receipt, **неизвестный результат требует reconciliation**, а не автоматического повторного удаления. Политика отказа от backward compatibility не разрешает потерять уже созданные пользовательские данные.

## 14.8. ИИ предложил машинную схему с внешними эффектами

Когнитивный consumer предложил граф: загрузить официальный XLSX, построить таблицу, сохранить результат, опубликовать ссылку, затем очистить промежуточную рабочую директорию.

1. AI предлагает **PlanDraft**, пользуясь разрешёнными идентификаторами из machine catalog, а не подставляя `module:function` или shell-скрипт.
2. Deterministic planner проверяет typed ports и преусловия каждого узла, версии источников, эффекты и полномочия Principal.
3. Публикация и удаление требуют отдельных allowed effect sets; approval для одного эффекта не становится разрешением на другой.
4. Контент загруженной публикации трактуется как data, а не как инструкция сменить target, расширить доступ или вызвать новую функцию.
5. После выполнения AI получает разрешённые Result/Artifact refs, а Work acceptance живёт в продуктовой модели; фраза агента «готово» ничего не фиксирует сама по себе.

**Проверка:** тест на prompt injection в загруженном документе; неизвестный operation ID отвергается; forged tool result не расширяет права; прежний approval отвергается после изменения планируемого destructive target. [R08; R13–R16; C04]

## 14.9. Backend потерял связь после публикации файла

Есть две несводимые ситуации:

| Событие | Проверяемая истина | Правильное действие |
|---|---|---|
| Worker завершился до выполнения внешнего эффекта; подтверждение отсутствует | доказана граница «effect not started» | безопасно повторить по retry policy |
| Worker успел опубликовать файл, но ACK до Coordinator не дошёл | outcome эффекта неизвестен | `OUTCOME_UNKNOWN` → reconciliation по receipt/idempotency/artifact hash |

Простое «таймаут = FAIL» создаёт риск двойного side effect. Требуется отличать worker lease от физического effect receipt; после истечения lease старый worker может продолжить работу. Conditional publication/fencing применяются в тех хранилищах и API, где реально поддержаны. [C04]

---

# 15. Conflict, apparent conflict и superseded register

В таблице **«Разрешение» — исследовательская консолидация**, а не автоматически утверждённый Product Decision. Источник текущего поведения и источник целевой идеи могут иметь разную дату и scope; более поздний документ не «побеждает» без объяснения причин. [C00; C02; C04]

| ID | Коллизия / прежняя позиция | Почему возникла | Разрешение темы 06 | Класс / остаток |
|---|---|---|---|---|
| CF-01 | `Command → Scenario → Cascade` против Operation/Scheme | Раннее исследование выделяло командный низкоуровневый ABI | Стабильная предметная граница — `OperationDefinition`; `Command` остаётся внутренней технической командой лишь при реальном consumer | **CONFLICT → CONSOLIDATED**; технический Command ABI OPEN |
| CF-02 | `Scenario` автоматически создаётся для каждой операции | Практичный Windows scaffold | Целевой `Scenario` — курируемый user-facing use case; direct Operation invocation допустим по policy | **SUPERSEDED** как обязательное target-правило |
| CF-03 | `ScenarioKind=background/assignment` | В одном enum смешались режим исполнения и инициатор | Background — режим attached/detached; Automation — долговечное правило; Assignment — социальное поручение | **SUPERSEDED** taxonomy |
| CF-04 | `Cascade` как отдельная разновидность движка | User workflow вырос из списка шагов | `Scheme` задаёт исполнимую композицию, `Cascade` пока UI/product view; отдельный lifecycle потребуется доказать | **CONSOLIDATED + UNKNOWN** |
| CF-05 | `Machine Scheme` равен `Scenario` | Смешались reusable machine semantics и пользовательская формулировка | Scheme и Scenario — разные definition-объекты с versioned relationship | **CONSOLIDATED** |
| CF-06 | `Case` сам является долгоживущей Work и единицей запуска | Текущий `ScenarioRunCase` совмещает несколько ролей | Долговечная Work, её Runs/Jobs/Attempts, UI CaseView как projection | **SUPERSEDED** прежнее агрегирование |
| CF-07 | Один QThread / busy indicator как ограничитель всех работ | Локальная Qt-реализация | Authoritative node JobManager/queue, resource claims, отдельные client projections | **CURRENT vs TARGET**, не логический спор |
| CF-08 | BackgroundProcessStore уже обеспечивает планировщик | UI имеет enabled/status и schedule_label | Это in-memory model; долгоживущий AutomationSpec, TriggerOccurrence и scheduler отсутствуют | **CURRENT scaffold**, нельзя заявлять production |
| CF-09 | Предметный scheduler принадлежит AppDock | Смешались platform и product lifecycle | AppDock отвечает за узел/процесс/сессии, Strategy Box — бизнес-автоматизации и их историю | **SUPERSEDED** ранняя ownership-гипотеза |
| CF-10 | AppDock remote backend обязан существовать сразу | Future host описан на уровне платформы | Это потенциал и внешняя зависимость; первую целевую ветку доказывать локальным headless worker | **TARGET-HYPOTHESIS / EXTERNAL DEPENDENCY** |
| CF-11 | Установленный plugin автоматически активируется | Текущий discovery одновременно выбирает provider | `installed → discovered → compatible → selected → activated → bound → ready` | **CONFLICT → CONSOLIDATED** |
| CF-12 | Первый найденный provider можно использовать | При одном расширении порядок был незаметен | Singleton slot требует explicit binding; mergeable contributions — deterministic merge и collision rejection | **SUPERSEDED** selection algorithm |
| CF-13 | Ошибка выбранного provider → local fallback | Текущий best-effort runtime стремится продолжить работу | Required active binding должен fail-closed; fallback лишь при семантической эквивалентности и authorization | **CONFLICT → CONSOLIDATED** |
| CF-14 | Все plugins имеют один уровень полномочий и API | «Плагин» употреблялся слишком широко | Разделить инфраструктурные providers, доверенные domain contributions, declarative style/source addons, execution backend adapters | **CONSOLIDATED**, некоторые contribution ABIs UNKNOWN |
| CF-15 | Addon может сам установить global default стиля | Текущий Excel addon имеет default name | Допустима recommendation; effective default выбирает профиль с явным приоритетом и provenance | **CURRENT vs TARGET** |
| CF-16 | UI plugin может менять shell layout/шрифты | Ранняя идея расширяемой кастомизации | Артефактные styles — да; прямой произвольный UI injection — вне принятой области | **SUPERSEDED** как целевой механизм |
| CF-17 | `ai_visibility` равнозначно праву AI вызвать операцию | Поле spec отражает presentation hint | Authority зависит от principal, effect policy, binding, context, consent и review | **CONSOLIDATED** |
| CF-18 | Нужен отдельный AI engine операций | Наличие AI actor и tool API создаёт видимость нового executor | AI предлагает intent/plan через адаптер; исполняет единый JobManager | **SUPERSEDED** параллельная система исполнения |
| CF-19 | MCP schema является единственным внутренним типовым контрактом | Внешний протокол удобен для агентов | Canonical operation contract внутренний; JSON Schema/MCP — versioned projections; нужно сохранить Python-native API | **CONSOLIDATED** |
| CF-20 | Source Catalog и Operation Catalog можно сделать одним реестром | Оба перечисляют «что доступно» | Источник описывает публикацию/получение, Operation — управляемый use case; оба связаны, но разные owners | **APPARENT CONFLICT** |
| CF-21 | Raw файл, dataset и artifact — единая идентичность | Все иногда представлены путями в storage | Immutable SourceSnapshot, domain data и Artifact имеют разные stable IDs/lineage | **CONSOLIDATED** с темой 03 |
| CF-22 | Нужен отдельный репозиторий для каждого слоя capabilities | Диаграммы исследовательских работ выглядят как будущие деревья репозиториев | Сначала ответственность → owner → contract → физическое размещение после независимого lifecycle | **SUPERSEDED** обязательная физическая декомпозиция |
| CF-23 | Core должен требовать конкретное expansion distribution | Удобство установки прототипа | Public core и Windows декларируют только нейтральный API; supply/deployment выбирает distributions | **CONSOLIDATED** публичная граница |
| CF-24 | `success` Job означает окончательное принятие аналитики | Ранние handlers возвращают bool `ok` | Execution outcome, domain qualification, Work acceptance — независимые оси | **CONSOLIDATED** |
| CF-25 | Retry на каждом уровне лучше повышает надёжность | HTTP/operation/job имеют независимые retries | Единый governing retry budget для effect boundary; вложенные retries ограничены и учитываются | **CONSOLIDATED** |

### 15.1. Настоящие разногласия и различия масштаба

Настоящий содержательный **CONFLICT** возникает там, где два дизайна требуют одновременно несовместимых решений: например, auto-activation по порядку обхода и явная binding resolution; скрытый fail-open и обязательный fail-closed; отдельный engine AI и единый engine. Эти альтернативы нельзя совместить «путём усреднения».

**Apparent conflict** возникает при сравнении разных уровней: Python domain function и управляемая product Operation; plugin package и contribution; общая Machine Scheme и курируемая Scenario; Platform Node/Session и product Work/Job; source freshness и operation availability. В таких случаях правильный ответ — восстановить уровни модели.

### 15.2. Исторические находки и устаревшие следы

Исторические материалы `01-old-notes` дают мотивацию отделять предметный код от интерфейса и формализовать reusable operations. Они **не подтверждают** существование современных контрактов. Текущая реализация имеет первенство при описании фактов. При этом устаревшие автоматические правила (`ScenarioKind`, выбор первого provider, единый QThread, необязательная проверка версий) **сохраняются как исторические ограничения CURRENT**, а не как будущие совместимые интерфейсы. [C00; R01; R02]

---

# 16. UNKNOWN и локальные белые пятна — реестр исследовательских задач

Здесь фиксируются вопросы, которые **не решаются одним теоретическим синтезом**. Для каждого указан prospective owner, проверка и критерий принятия; имена физических пакетов остаются кандидатами, а не обязательными репозиториями.

| ID / приоритет | UNKNOWN | Семантический owner | Нужная проверка / решение |
|---|---|---|---|
| U01 / P0 | Где именно живёт канонический `OperationDefinition` и как импортировать его без side effects? | `stratbox` domain core | 2 реальных операции разных доменов, их offline discovery и import smoke |
| U02 / P0 | Какой минимальный набор serializable Request/Result без вытеснения Python-native dataclass/DataFrame? | domain core + application contract | machine round-trip, строгая schema evolution, typed failure tests |
| U03 / P0 | Как совместить декларацию capability, runtime health и индивидуальные права? | application capability resolver | четыре principal × три backend states × два active profiles, сравнить каталог |
| U04 / P0 | Нужен ли отдельный trusted domain operation-extension API v1 или сперва достаточно встроенных операций core? | domain core | пилот внешнего synthetic package с реальным use case; оценить риск surface/review |
| U05 / P0 | Достаточен ли единый `PluginDescriptor` для storage, sources, styles и backend? | owners по contributions | 3 synthetic provider types + конфликтный merge, исключить giant descriptor |
| U06 / P0 | Где transactional durable truth автоматизаций, occurrences, runs и bindings? | application execution authority | перезапуск процесса, duplicate trigger, recovery после записи/до commit |
| U07 / P0 | Как соотносятся run-level approval, effect-level grants и policy revocation? | application authorization + platform principal | revoke-after-queue, stale plan approval, out-of-scope effect |
| U08 / P0 | Какая версия of `Run` binding snapshot замораживается при очереди и как действует replan? | planner + execution | change plugin version/SourceSnapshot/policy while queued; no invisible substitution |
| U09 / P0 | Какая точная семантика `OUTCOME_UNKNOWN` при разных провайдерах и external APIs? | application executor + provider owners | timeout-after-commit, partial receipt и reconciliation proof |
| U10 / P0 | Как определить conformance profiles отдельно для service provider, source connector, format, style, operation и execution backend? | contract owners | synthetic reference packs с intentional fail cases |
| U11 / P1 | Schema/IR Machine Scheme: canonical JSON AST, Python definitions или typed workflow graph? | application planner + domain producer | один branching+join, one shared fetch, один approval gate, real-data test |
| U12 / P1 | Какая granular applicability нужна: unavailable, unknown, forbidden, requires-input, stale? | capability resolver | backend missing, wrong source, hidden operation, expired registry, auth |
| U13 / P1 | Что является `CapabilityRequirement`: service dependency, feature flag или разрешённый action? | domain contracts | отделить `requires storage` от `allows write` на двух operations |
| U14 / P1 | Какой порядок разрешения default parameters и plugin config с managed policy? | application settings / extension profile | proof effective parameter snapshot без secret values |
| U15 / P1 | Формат, canonicalization и hash binding profile/ExecutionPlan? | application planner | одинаковый semantic plan/разный порядок keys → same digest, version bump → new digest |
| U16 / P1 | Идентичность source-change occurrence при retrospective revisions? | source semantics + automation | один URL, разные hashes; одна публикация, два mirror endpoints |
| U17 / P1 | DST и misfire policy: skip, run-once, bounded catch-up, manual review? | automation scheduler | повторный час, отсутствующий час, week-offline, disabled/reenabled |
| U18 / P1 | Когда watcher становится long-running listener, а когда periodic poller? | automation + platform lifecycle | latency, API limits, memory/CPU budget и pause/resume |
| U19 / P1 | Durable cursor и retention для событий после reconnect? | application persistence | two clients, missed N events, compaction, replay without duplicate actions |
| U20 / P1 | Где граница между worker lease, resource lock и remote host control? | execution + AppDock integration | stale worker, lease fencing, worker restart, host restart |
| U21 / P1 | Изоляция стороннего кода: trusted in-process или отдельный sandbox execution profile? | extension trust/deployment owner | threat model и минимальный out-of-process synthetic adapter |
| U22 / P1 | Поддерживать ли hot enable/disable после deployment, но без hot-install? | application runtime + AppDock | running jobs with old binding, new jobs with revised binding |
| U23 / P1 | Lifecycle и публикация ArtifactStyleSet: version pinning, licensing, font availability? | artifact formatting + application preferences | cross-platform XLSX render, fallback fonts, reproducible metadata |
| U24 / P1 | Как дать AI машинный provenance и стоимость вывода, не делая новый AI-core? | machine projection + application policy | propose/read/compute/write/approve matrix, token schema budget |
| U25 / P1 | Нужны ли отдельные external APIs для Tool/Resource/Prompt и какой стандартный protocol revision? | machine adapter owner | protocol contract test на текущий официальный MCP; no fork of operation ABI |
| U26 / P1 | Какая схема per-node quotas/fairness достаточна для тяжёлых расчётов и частых watchers? | JobManager | load profile CPU/RAM/network; starvation regression |
| U27 / P1 | Нужны ли capability-status notifications всем пользователям или только заинтересованным? | application collaboration + privacy | granular impact model, per-user filters, no leak |
| U28 / P2 | Как выбрать физическое размещение host/application contracts и нужны ли новые репозитории? | product architecture | proving one headless worker + two clients independent deployment |
| U29 / P2 | Нужно ли отдельное имя/definition для Cascade? | application product semantics | nested schemes and human-visible cascade governance pilot |
| U30 / P2 | Нужна ли сложная динамическая discovery/search index по сотням capabilities? | catalog owner | benchmark real catalogue 50–200 operations; пока достаточен simple immutable snapshot |
| U31 / P2 | Как реализовать offline execution при недоступной платформенной identity service? | application + AppDock | signed cached grants, expiry/revocation, deny unsafe effects |
| U32 / P2 | Policy versioning при семантической переработке без обратной совместимости? | product owners | sealed deployment contract, clean cutover, one-off export user data |

### 16.1. Что именно нельзя объявить доказанным сейчас

Ни в одной из проверенных текущих implementation surfaces не продемонстрированы полноценный долговечный scheduler, node-wide JobManager, remote execution backend, общий trusted domain extension ABI или единая machine-readable operation registry с полной policy filtering. Исследования дают сильные архитектурные аргументы, но **отсутствие доказанной реализации остаётся отдельным фактом**. [R01; I02–I15; C04]

Также нельзя считать окончательно решёнными численные пределы памяти/CPU, гарантии exactly-once для внешних побочных эффектов, выбор СУБД, конкретную версию MCP и физический процесс размещения runtime. Их следует решить тестами, ограничениями deployment и requirements, а не декларацией в Markdown.

### 16.2. Какие белые пятна критичнее самого количества плагинов

Наиболее высокорисковые провалы — **authority**, строгая достоверность эффекта, immutable execution/binding snapshot и distinction `UNKNOWN` от `FAILED`. Добавление десятков новых backend providers или style presets раньше устранения этих пробелов только увеличит площадь неконтролируемого поведения. Первые тесты должны проверять несчастливые пути, а не просто появление вкладки «Плагины».

---

# 17. Целевые системные инварианты и тесты архитектуры

Это **кандидаты обязательных system-wide acceptance gates**, а не утверждения, что текущий код их выполняет. Идентификаторы `CX-*` относятся именно к теме 06 и должны затем согласоваться с инвариантами темы 08. [C04]

| ID | Инвариант | Контрольное испытание |
|---|---|---|
| CX-01 | `OperationDefinition` не зависит от Qt, AppDock, локального пути установки и AI protocol | headless import/execution |
| CX-02 | Python-native и managed invocation используют один предметный смысл | same typed request/snapshot, equivalent domain result |
| CX-03 | `CapabilityDefinition`, `OperationDefinition`, `ProviderBinding`, `ExecutionBackend` различаются по identity | catalog snapshot schema/refs |
| CX-04 | Установленность extension не равна activation/authority | discovered-but-inactive test |
| CX-05 | Discovery сам по себе не создаёт сетевых, файловых и секретных side effects | monkeypatch network/filesystem deny during discovery |
| CX-06 | Singleton provider не выбирается по случайному порядку | reverse entry point enumeration |
| CX-07 | Конфликт одинакового contribution ID диагностируется, а не тихо переопределяется | duplicate style/source/operation IDs |
| CX-08 | Required bound provider при ошибке не превращается в unrelated local success | fault injection managed profile |
| CX-09 | Любой fallback сохраняет заявленные гарантии или явно меняет outcome/capability | atomic move vs copy/delete counterexample |
| CX-10 | Visibility каталога не выдаёт полномочий на исполнение | principal mismatch + authorization test |
| CX-11 | Каждый destructive action имеет declared effects и authorization/approval | plan/apply with stale grant |
| CX-12 | Новые backend/style/source/operation contributions соблюдают принадлежащий им conformance profile | synthetic extensions pass/fail suite |
| CX-13 | Machine API не раскрывает `module:function`, произвольный shell или сырые secrets | schema + prompt-injection tests |
| CX-14 | AI не обходит обычный admission, permission и JobManager | same request human vs AI policy check |
| CX-15 | Scenario, Scheme, Automation и Job имеют отдельные версии и identities | change definition while Job running |
| CX-16 | Foreground/background/AI/remote не создают отдельных business engines | common execution trace across origins |
| CX-17 | Scheduler хранит occurrence identity и причины `NO_CHANGE/SKIPPED/FAILED` | duplicate/misfire tests |
| CX-18 | Disabled Automation не отменяет существующий Job без отдельной команды | disable during run |
| CX-19 | Scheduled run привязан к версии source/registry и binding snapshot | changed URL/hash/profile after queue |
| CX-20 | Одно физическое действие не повторяется опасным образом из-за двойного trigger/retry | duplicate command/idempotency key test |
| CX-21 | Потеря ACK после эффекта приводит к `OUTCOME_UNKNOWN` и reconciliation | post-commit network drop |
| CX-22 | Один job имеет один committed terminal receipt | concurrent success/cancel finalization |
| CX-23 | Resource locks и worker lease не смешиваются | stale worker fencing |
| CX-24 | ArtifactStyleSet версионируется независимо от UI theme | switch OS dark mode, same XLSX style fingerprint |
| CX-25 | Artifact всегда связан с operation/run/source/provenance и effective style selection | manifest reconstruction |
| CX-26 | Изменение active plugin set требует новой проверенной binding revision, а не подмены уже идущего Run | update while running |
| CX-27 | Runtime/package contract drift блокирует несовместимое execution до эффекта | core/windows manifest mismatch |
| CX-28 | Ошибка и предупреждение extension доступны через безопасные structured diagnostics | redact faults, inspect ProblemRef |
| CX-29 | Все clients видят согласованный node-wide authoritative job state | two Windows + reconnect simulation |
| CX-30 | Неизвестность данных/эффекта не маскируется как пустая успешная выборка | timeout/auth/not-found/empty matrix |
| CX-31 | Public core и Windows содержат только нейтральные extension interfaces и synthetic examples | static boundary check/package audit |
| CX-32 | Обновление API может быть чистым без legacy aliases; фактические user data защищены отдельно | fresh-install smoke + one-off data export |

### 17.1. Тестовая пирамида

1. **Contract unit:** DTO/schema, compatibility, collision, policy, immutable snapshots.
2. **Synthetic provider tests:** mock storage/network/secrets, source connector, style addon; success и intentional failures.
3. **Domain operation tests:** reproducible CBR collector, escrow, FRG, forms, restoration, включая semantic validation.
4. **Application integration:** operation registry → planner → JobManager → artifacts, human/automation/AI admission.
5. **Fault injection:** process crash, lost ACK, stale worker, DST, disk full, incomplete write, revoked permission, corrupted event cursor.
6. **Managed AppDock integration:** package graph, activation context, health, safe diagnostics, signed package provenance, clean restart.
7. **Portability:** plain Python/Notebook; Windows headless; future Android/Web consumers через shared semantic contracts.

**Базовый принцип:** отсутствие модуля tests или присутствие тестовых функций само по себе не свидетельствует об успешном результате test run. Данный консолидирующий документ не проводил новый полный CI/integration/performance запуск; проверки остаются критериями целевой реализации.

---

# 18. Ownership map: responsibility прежде физической декомпозиции

| Ответственность | Логический owner | Где есть CURRENT | Target seam / допустимая физическая форма |
|---|---|---|---|
| Domain models, parsing, normalization, reconstruction, validation | `stratbox` | доменные пакеты core | сохранить headless и reusable |
| Canonical OperationDefinition, domain Request/Result, semantic version | `stratbox` | частичные typed contracts | curated domain operation catalog; не все функции |
| Service capability contracts (FileStore, net, secrets) | `stratbox` base | FileStore, runtime, style addons | versioned public interfaces и synthetic conformance |
| Source Catalog, source identity/freshness | `stratbox` | collector registries, доменные discovery | source contributions только через authority/validation |
| Reference registries | `stratbox` | packaged banks/OKVED/domain registries | immutable versioned snapshots + governance |
| Artifact representation / reporting semantics | producer (`stratbox`) + application artifact owner | пути и style registry | Artifact/StyleSet contracts, publication lineage |
| Scenario catalog, Work, Runs, client-independent execution state | Strategy Box application | сейчас распределено в Windows app | platform-neutral application responsibility |
| Scheme compiler / planner | Strategy Box application совместно с domain schemas | sequential scenarios; части лишь в research | typed DAG, immutable Plan, machine proposal validator |
| Automations, triggers, occurrences, scheduler business truth | Strategy Box application | UI scaffold | durable scheduler/service, one event model |
| JobManager, placement, locks, leases, effect reconciliation | Strategy Box application execution | Qt coordinator, one active scenario | headless execution authority, backend adapters |
| Installed distributions, trusted packages, runtime provisioning | deployment / AppDock | managed package graph | explicit profile bindings and lockfiles |
| Node lifecycle, health, session/remote platform transport | AppDock | documented platform boundaries, activation consumer | published neutral node/session contracts |
| OS-specific rendering, preferences, navigation | Windows/Web/Android surfaces | PySide6 Qt | common semantic projection + platform-native view |
| Machine/AI tool adaptation | external cognitive consumer + controlled Strategy Box interface | AI metadata scaffold | same capability catalog, constrained projection, one admission |
| Extension provider implementation | individual extension owner | externally installable in Python ecosystem | internal implementation behind public stable interface |

**Консолидация:** новые физические names (`stratbox-host`, `stratbox-core`, `stratbox-design`, отдельный extension SDK) остаются кандидатами. Для начального вертикального среза допустимо оставить application runtime в существующем проекте при условии **фактического разделения импорта/процесса/состояния**, которое переживёт UI и сможет обслужить второй клиент. Затем отдельный пакет или репозиторий выделяется по доказанной необходимости: независимый lifecycle, безопасность, deployment или несколько consumers. [C01; C02; R12]

### 18.1. Что делать именно в открытом `stratbox`

- Очистить публичный extension metadata/dependency surface до нейтрального перечня контрактов; исходный код, examples и tests должны использовать synthetic reference providers.
- Определить `OperationDefinition` для 2–3 реальных доменов, включая typed Request/Result, effects, readiness, resource hints и source snapshot refs.
- Стабилизировать neutral `ExtensionDescriptor`, capability slots, conformance и structured errors; избавиться от first-success/implicit fallback.
- Добавить versioned source/registry/format/style catalogs и обозначить общий provenance envelope.
- Сохранить Python API самостоятельным: direct library consumers не обязаны ставить desktop/UI и поднимать долгоживущий application host.

### 18.2. Что делать именно в открытом `stratbox-windows`

- Заменить hardcoded operation list как смысловой authority на проекцию валидированного application/core catalog; оставить поверхностные labels, icons, filters и формы как presentation metadata.
- Вынести Qt coordinator из runtime bootstrap и передать authority выполнения headless application service.
- Разделить `ScenarioSpec`, `AutomationSpec`, `ExecutionPlan`, `Run/Job`, `BackgroundProcessState`; убрать привычку создавать scenario автоматически для любой low-level operation.
- Показать пользователю статус расширения, причины отсутствия способности, разрешённые настройки, результаты и диагностику, без раскрытия implementation internals.
- Подготовить platform-neutral common models для Android и других clients; Qt widgets остаются Windows rendering detail.

### 18.3. Что находится на внешней платформенной границе

Package install/update, runtime activation context, host process lifecycle, platform health/remote transport и управление Node/Session сохраняются у внешнего владельца среды. Strategy Box получает стабильные versioned contracts и фиксирует собственный product execution/binding provenance. Признак `Node healthy` недостаточен для вывода `Job succeeded`; и наоборот, временный platform degradation не переписывает ранее verified domain Result. [A01; C01; C04]

---

# 19. Дорожная карта реализации с проверяемыми выходными воротами

Это **исследовательская последовательность**, а не утверждённый backlog. Цель — минимальный coherent vertical slice прежде масштабирования каталога и количества extensions. Каждый этап должен заканчиваться исполняемым evidence, а не только новым документом.

## Этап 0. Sanitation и зафиксированный baseline — P0

**Работы:** устранить публичные специфичные dependency/implementation следы; синхронизировать версии core/windows/manifest/test; отделить нынешние descriptions от целевых API; добавить reproducible build + import smoke + CI; явно записать supported Python/extras и capability matrix. Сохранить короткий changelog отказа от старых API с указанием необходимости разового экспорта полезной пользовательской истории. [R01; I01; I09; I15]

**Exit gate:** clean public wheels, совпадающий installation graph, passing import/release/contract checks, отсутствие private implementation hints в открытых материалах, baseline commit идентифицирован.

## Этап 1. Canonical Operation pilot — P0

Выбрать **две реальные операции** с разной семантикой: read/download (`cbr_file_collector.collect`) и materialized export (`escrow.history.export`). Дополнительно подготовить FRG plan как будущую проверку destructive policy. В core стандартизировать curated IDs/versions, typed request/result, errors, source/registry provenance, effects, resources, applicability и cancellation capabilities. Domain handlers сохраняются в core; application binding больше не считает строковый import path канонической identity.

**Exit gate:** одна операция вызывается из plain Python без Qt и из headless managed execution с одинаковой предметной семантикой; ее JSON-compatible descriptor проходит round-trip; Core tests не требуют GUI или AppDock.

## Этап 2. Verified extension API / binding resolver — P0

Разработать **минимальный generic API** для реально существующих service/provider и style contribution seams; дополнительно один synthetic source/operation contribution только для проверки границы. Зафиксировать `installed/discovered/selected/activated/bound/ready`, explicit profiles, collision semantics, no-load discovery metadata, conformance suites и строгую taxonomy. В production запретить silent fallback required bindings. [R09; I02; I03]

**Exit gate:** synthetic good/malformed/duplicate/conflicting/missing-provider packs; ошибка в любом звене не приводит к несанкционированному эффекту и не выдаётся за успешный local operation.

## Этап 3. Headless execution spine — P0

Перенести execution authority из QThread/UI процесса в testable application orchestration с `Run/ExecutionPlan/Job/OperationRun/Attempt`; вынести Qt signals в adapter. Реализовать typed admission, immutable params/binding snapshot, event stream, controlled cancellation, terminal receipts, artifact staging/verification и transactional persistence. Одновременность начать с bounded concurrency и понятных ресурсных классов. [C04; I10; I11]

**Exit gate:** закрытие окна не влияет на headless Job; два клиента видят одну историю; kill/restart/reconnect сохраняют identity и state; late cancel не переписывает success; failed export не публикует полный артефакт.

## Этап 4. Scheme compiler и effect safety — P1

Сделать одну типизированную композицию: общий fetch → две независимые ветви обработки → fan-in/validation → два разных артефакта. Показать dedup без смешения эффектов. Добавить preview Plan, approvals и отдельный `plan/apply` FRG cleanup. Ввести approved effect receipts, idempotency/reconciliation. Полный универсальный DSL откладывать до реального спроса.

**Exit gate:** identical fetch shared once where safe; два разных output writes остаются двумя effects; stale destructive approval rejected; lost ACK после commit не запускает безусловный repeat.

## Этап 5. Durable AutomationSpec и schedule/watchers — P1

Ввести `AutomationSpec`, `TriggerSpec`, `TriggerOccurrence`, `EvaluationResult`, dedup key, misfire/DST/catch-up, отключение без автоматической отмены старых Jobs. Начать с одного scheduled check официального source и одного condition watcher, оба используют обычные Operations/Jobs и source snapshots. AppDock управляет uptime, Strategy Box — предметным расписанием.

**Exit gate:** повторное получение одного event создаёт одну occurrence; изменение содержимого при прежнем URL обнаруживается; week-offline и DST воспроизводимы; неверные данные не превращаются в «нет обновлений».

## Этап 6. Machine/AI projection и альтернативные surfaces — P1/P2

Поверх **того же** catalog создать consent/authority-aware tool projection; обязательна детерминированная валидация предлагаемых AI схем и защита от instruction-content в источниках. Windows показывает каталог, ожидания, jobs, artifacts и расширения; Android/Web используют общие application semantics, при необходимости лёгкий platform-native rendering. Внешний MCP adapter добавлять после стабилизации внутреннего contract, а remote backend — после согласования platform transport and credentials. [R08; R13–R16; C04]

**Exit gate:** AI не вызывает скрытые или неподдерживаемые capabilities; все tool calls оставляют Run/receipt provenance; Windows и второй клиент видят одинаковый Work/Run/Artifact graph; remote-loss тест возвращает корректный `OUTCOME_UNKNOWN`.

### 19.1. Почему именно такой порядок

- Сначала **достоверность и public boundary**, потом расширение продуктовых возможностей.
- Сначала **реальная Operation**, потом красивый единый каталог.
- Сначала **headless execution state**, потом расписания, AI и remote.
- Сначала **один безопасный machine tool**, потом динамический агентный planner.
- Сначала **проверяемая схема из нескольких реальных операций**, потом полноценный Scheme DSL.
- Сначала **semantic ownership**, потом решение о новых физических репозиториях.

Старые ABI, синонимы ключей и переходные UI-модели не требуется поддерживать ради обратной совместимости. При замене необходимо отдельно обеспечить сохранность уже записанных пользовательских результатов и журналов либо явный экспорт/миграцию фактических данных.

---

# 20. Decision / Gap Register темы 06

| Решение / вопрос | Исследовательский статус | Что можно перенести в Product после gate |
|---|---|---|
| Capability/Operation/Scheme/Scenario имеют разные семантические обязанности | **CONSOLIDATED** | словарь, identity rules, contracts |
| Source Catalog, Extension Registry, Binding Registry и visible catalogue раздельны | **TARGET-HYPOTHESIS (высокая уверенность)** | design of catalog projection + validation |
| Одна Operation обслуживает Python/UI/automation/AI | **CONSOLIDATED** | portable domain contract |
| Все управляемые запуски проходят один admission/JobManager | **CONSOLIDATED** | execution-service API после пилота |
| `Command` как отдельный глобальный атом обязателен | **SUPERSEDED** | не вводить без use case |
| Каждый canonical Operation автоматически становится user Scenario | **SUPERSEDED** | selective curated scenarios |
| Background — режим исполнения, Automation — правило | **CONSOLIDATED** | separate persistence/trigger definitions |
| Product scheduler owner — Strategy Box, platform lifecycle — AppDock | **CONSOLIDATED** | published control boundary |
| Python entry points — удобный discovery mechanism | **CURRENT + TARGET** | stable generic discovery, no implicit activation |
| Auto-select first provider и silent local fallback | **CURRENT defect / SUPERSEDED** | explicit profiles and fail-closed required bindings |
| Один универсальный plugin API покрывает все contribution kinds | **CONFLICT / REJECTED как giant ABI** | common envelope + typed per-kind contracts |
| External domain operation contributions нужны прямо в v1 | **UNKNOWN** | показать спрос через real synthetic pilot |
| Произвольная модификация UI через plugins | **SUPERSEDED** | только safe declarative metadata и artifact styles |
| Artifact styles предоставляются как версии декларативных ресурсов | **CONSOLIDATED** | style IDs, selection, provenance, conformance |
| Физически отдельный headless host — обязательный отдельный репозиторий | **UNKNOWN** | разделить logical lifecycle; решить packaging экспериментом |
| Machine Scheme использует typed DAG, но не отдельный AI engine | **TARGET-HYPOTHESIS (высокая уверенность)** | scheme compiler pilot and contract test |
| MCP и JSON Schema являются projection/serialization, не semantic owner | **CONSOLIDATED** | protocol adapter после внутреннего schema contract |
| Exact schema DSL, backend selection scoring, quotas, DB choice | **UNKNOWN** | performance + fault-injection pilots |
| In-process plugin равнозначен sandbox | **REJECTED** | trust policy и отдельный sandbox contract при необходимости |
| Один Run может переживать изменение extension versions без silent replacement | **TARGET-HYPOTHESIS** | immutable binding snapshot + new plan admission |
| Reproducibility и evidence проходят через Operation → Result → Artifact | **CONSOLIDATED** | manifest/hash/effect receipt policies |

## 20.1. Самая короткая итоговая формула

**Strategy Box расширяется декларациями способности и проверяемыми реализациями; запускается через один разрешающий и исполняющий контур; автоматизируется долговечными правилами, порождающими обычные работы; предоставляет ИИ тот же ограниченный каталог; формирует результаты с доказуемыми источниками, версиями и эффектами.**

Физический plugin package, GUI button, Python import, cron schedule или MCP tool — способы доставки, обнаружения, запуска и представления. Каждый из них сам по себе **не является** ни аналитической истиной, ни достаточным разрешением на эффект, ни отдельной исполнительной системой.

---

# 21. Provenance ledger и карта источников

Ссылки на `main` служат навигацией к документам; **факт CURRENT относится к прочитанному состоянию на дату исследования**, а не к будущему содержимому ветки. Внутри одного ряда могут стоять разные уровни происхождения: implementation proof, prior research proposition и external protocol reference. В публичной части умышленно приводятся только нейтральные исследования и прямые источники открытых интерфейсов.

## 21.1. Исследовательская рамка и консолидирующие материалы

| Код | Источник | Использование |
|---|---|---|
| **P01** | [Программа 03](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/strategy_box_03_consolidation_research_program.md) | Нормативная рамка темы 06 |
| **C00** | [Corpus Map & Open Questions](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_00_corpus_map_open_questions_2026-10-08.md) | Карта 02-base-study, конфликты, пробелы и superseded |
| **C01** | [System Model](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/Strategy_Box_01_System_Model_consolidated_research_2026-10-08.md) | Логические ownership boundaries |
| **C02** | [Canonical Semantic Model](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_02_canonical_semantic_model_2026-10-08.md) | Словарь Capability/Operation/Scheme/Work/Run/Artifact |
| **C03** | [Data → Knowledge](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_03_data_to_knowledge_consolidated_research_2026-10-08.md) | SourceSnapshot, lineage, evidence и Artifact |
| **C04** | [Work → Execution](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_04_work_to_execution_consolidated_research_2026-10-09.md) | One execution spine, admission, Jobs, effects, automations |

## 21.2. Исследования основной второй ветки

| Код | Источник | Конкретная роль в синтезе |
|---|---|---|
| **R01** | [Core current-state](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_base_study_current_state_2026-10-06.md) | Предметные домены, FileStore, типизированные операции |
| **R02** | [Commands / Scenarios / Cascades](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md) | Исходная модель команд, сценариев, планирования и dedup |
| **R03** | [Background / Jobs](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/Strategy_Box_background_jobs_processes_architecture_research_2026-10-08.md) | Durable Automation, TriggerOccurrence, misfire и scheduler |
| **R04** | [Execution control](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_execution_control_user_path_research_2026-10-07.md) | Параметры, cancellation, controls, approvals |
| **R05** | [Machine Schemes](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_logic_machine_schemes_architecture_research_2026-10-07.md) | Типизированные композиции, effects, планы |
| **R06** | [Sources / Registries](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_registry_source_governance_research_2026-10-07.md) | Источник, snapshot, reference governance |
| **R07** | [Portability and reuse](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_business_segments_portability_reuse_architecture_research_2026-10-07.md) | Portable operation surface, reusable building blocks |
| **R08** | [Automation and AI](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md) | AI-tool projection, scheduler, machine consumers |
| **R09** | [Generic extension contract](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_corporate_plugin_contract_research_2026-10-07.md) | Нейтральный plugin/extension API и conformance — без частных реализаций |
| **R10** | [Artifact style sets](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_customization_artifact_style_sets_research_2026-10-07.md) | Декларативные ресурсы оформления артефактов |
| **R11** | [Settings](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_system_settings_research_2026-10-07.md) | UserSettings / managed policies / plugin projections |
| **R12** | [Web / self-hosted](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md) | Headless runtime, client/server logical boundary |
| **R13** | [Machine consumer boundary](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_boundary_research_2026-10-07.md) | Ответственность Strategy Box и внешнего когнитивного consumer |
| **R14** | [Business-code readiness](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md) | Машинная пригодность operation/scheme contracts |
| **R15** | [Machine-ready foundation](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_foundation_research_2026-10-07.md) | Policy, epistemics, machine-host interface |
| **R16** | [Chat / Work / Schemes](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_chat_work_schemes_ui_research_2026-10-07.md) | Сопоставление chat/work со schemes |
| **R17** | [Observability](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_observability_errors_logs_research_2026-10-07.md) | Structured events, typed errors, Problem boundary |
| **R18** | [Single-node multiuser](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md) | Node-wide execution state и multi-principal authorities |
| **R19** | [Windows current-state](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md) | Срез Windows, актуальность дополнительно проверена по коду |
| **R20** | [FileStore / formats](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_filestore_file_formats_research_2026-10-07.md) | Нейтральные transport/format capabilities |

## 21.3. Прямо проверенные implementation owner files

| Код | Текущий прямой источник | Суть проверки |
|---|---|---|
| **I01** | [`pyproject.toml`](https://github.com/ForestTiger-GH/stratbox/blob/main/pyproject.toml) | Core packaging/version metadata |
| **I02** | [`src/stratbox/base/runtime.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/runtime.py) | Фактическое обнаружение, выбор и fallback провайдеров |
| **I03** | [`src/stratbox/base/styles/excel/plugin.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/styles/excel/plugin.py) | Excel addon discovery и merge |
| **I16** | [`docs/plugin-integration.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/plugin-integration.md) | Current public description provider loading |
| **I04** | [`src/stratbox_windows/application/operations/catalog/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/operations/catalog/models.py) | OperationSpec и registry data structures |
| **I05** | [`src/stratbox_windows/application/operations/catalog/registry.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/operations/catalog/registry.py) | Три зарегистрированных операции и handlers |
| **I06** | [`src/stratbox_windows/application/scenarios/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/scenarios/models.py) | ScenarioKind/ScenarioStepSpec |
| **I07** | [`src/stratbox_windows/application/scenarios/registry.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/scenarios/registry.py) | Auto atomic scenarios + composite |
| **I08** | [`src/stratbox_windows/application/scenarios/runner.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/scenarios/runner.py) | Sequential scenario runner, cases/artifacts/events |
| **I09** | [`pyproject.toml`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/pyproject.toml) | Windows core dependency/version metadata |
| **I10** | [`src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) | QThread single active run |
| **I11** | [`src/stratbox_windows/runtime/bootstrap.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/bootstrap.py) | Application/Qt bootstrap import |
| **I12** | [`src/stratbox_windows/application/background/registry.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/background/registry.py) | Три фоновых каталожных процесса |
| **I13** | [`src/stratbox_windows/application/background/models.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/background/models.py) | Background state vocabulary |
| **I14** | [`src/stratbox_windows/application/background/store.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/background/store.py) | In-memory background state without scheduler |
| **I15** | [`appdock/manifest.json`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/appdock/manifest.json) | Local foreground Windows AppDock activation |

## 21.4. Внешний platform baseline и стандарты

- **[A01]** `AppDock - Базовое описание.docx` — приложенный к материалам проекта документ, прежде всего разделы 7 «Узел», 12 «Действия вместо команд», 14 «Восстановление», 19–23 (host, удалённая работа, безопасность, ИИ, кросс-платформенность). Используется как **граница внешнего платформенного продукта**, не как доказательство наличия конкретного удалённого executor в Strategy Box.
- **[E01]** [PyPA — Entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/) — стандарт объявляемых package entry points. Доказывает допустимость discovery-механизма, но не определяет activation и trust.
- **[E02]** [JSON Schema 2020-12](https://json-schema.org/specification) — вариант interoperable формального описания схем machine API. Семантическая идентичность и предметная истинность остаются внутри Strategy Box.
- **[E03]** [Model Context Protocol — Tools, protocol revision 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) — справка о внешней передаче machine tools/input-output schemas. MCP не становится владельцем domain operations и не является средством авторизации сам по себе.

## 21.5. Степень прямой проверки

- **Program scope:** текст программы найден и изучен целиком; тема № 06 установлена по оригиналу.
- **Research synthesis:** изучены ключевые исследования `02-base-study` и уже имеющиеся консолидирующие результаты третьей ветки, с опорой на смысловые конфликты и white spots.
- **Implementation:** выборочно прочитаны перечисленные исходники обоих публичных owners. Это **code inspection**, а не новый end-to-end test run; фиксируется состояние доступного `main` на дату работы.
- **Currentness caveat:** подробные factual baselines от 2026-10-06 являются датированными и не подменяют прямой код от 2026-10-09. В случае расхождения прямой implementation owner имеет приоритет.
- **Historical provenance:** `01-old-notes` использованы лишь как источник происхождения старых предложений; никакой historic proposal не назван CURRENT без подтверждения.
- **External technical sources:** стандарты использованы для проверки возможностей сериализации и discovery, не для механического проектирования всей системы.
- **Private boundary:** закрытые реализации расширений, их структура и идентификаторы сознательно отсутствуют. Не приводятся организационные метаданные чужих исследовательских репозиториев; только предметные выводы о Strategy Box.

---

# 22. Заключение: что тема 06 добавляет к архитектуре третьей ветки

Тема 02 установила терминологию, тема 03 — происхождение данных и результатов, тема 04 — жизненный цикл управляемого исполнения. **Тема 06 связывает их в архитектуру управляемой расширяемости.** Нельзя считать успешно подключённую библиотеку самостоятельным пользовательским permission; нельзя считать появившийся новый пункт каталога готовой операцией; нельзя считать `Automation.enabled` работающим scheduler; нельзя выдавать внешнему AI новую «магическую» систему действий при наличии предметных операций.

Итоговая целевая формула:

```text
Semantic Capability / Operation Contract
       + Verified Extension Contribution / Provider Binding
       + Explicit Context / Trust / Authority
       + Versioned Scenario or Machine Scheme
       + Trigger / Automation definition (optional)
       + Sealed ExecutionPlan / JobManager / ExecutionBackend
       + Structured Result / EffectReceipts / Artifact / Provenance
       = одна доступная, проверяемая и расширяемая способность Strategy Box
```

**Следующее Product Decision должно касаться в первую очередь минимального публичного capability ABI, правил activation/binding, места authoritative execution и доказуемых acceptance gates**, а не количества расширений, названий каталогов или экранов.

Остающиеся сложные развилки и проверки перечислены в §16; материал не превращает гипотезы в утверждённую архитектуру и не вносит изменений в implementation owners.
