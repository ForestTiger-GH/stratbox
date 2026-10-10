# 06. Машинные интерфейсы и каталог возможностей Strategy Box

**Дата:** 10 октября 2026 года  
**Тип:** самостоятельное исследование / архитектурный анализ; **не** принятое Product Decision и **не** действующая техническая спецификация.  
**Область:** Strategy Box — аналитический Python-core, общий прикладной контур, Windows-клиент, будущий headless-хост, машинные потребители и AI.  
**Исходная постановка:** `Strategy_Box_Research_Topics(2).docx`, тема 06 «Машинные интерфейсы и каталог возможностей».  
**Снимки исходных репозиториев:** [`stratbox@beb3e484`](https://github.com/ForestTiger-GH/stratbox/tree/beb3e4842614b153ba0c0ccc1e33ae4d50698821), [`stratbox-windows@959e9c4c`](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b), [`AppDock@a4d87c64`](https://github.com/ForestTiger-GH/AppDock/tree/a4d87c643e620e54e04083d4d0b8d867513e7065). Указанные SHA используются для проверки состояния на дату исследования; ссылки вида `/blob/main/` в предыдущем корпусе являются плавающими.  
**Изменения в репозиториях:** отсутствуют. Исследовательский файл создан только для передачи в ChatGPT.  
**Граница публичности:** рассматриваются общие технические интерфейсы и публичные аналитические домены. Специфика непубличных корпоративных компонентов, внутренних адресов и реализаций исключена.

---

## 0. Результат в одном абзаце

Strategy Box следует строить вокруг **единого предметного каталога курируемых возможностей**, в котором независимо различаются: **обычная Python-функция**, **предметная Operation**, **семантическая Capability**, **машинное представление Tool**, **композиция Scheme/Scenario** и **конкретный ExecutionPlan**. *Исполняемая бизнес-логика существует в core один раз*, а каждый канал — Colab/Jupyter, Windows, API, MCP, A2A, встроенный агент — обращается к ней через подходящий адаптер и, когда требуется управляемая среда, единое правило допуска и исполнения. **Не надо автоматически публиковать каждую функцию как tool и не надо превращать каждую схему в универсальный JSON-словарь.** Python остаётся богатым нативным интерфейсом; наружу передаётся специально спроектированная, версионируемая граница с ограниченным набором типов, референсами крупных данных, явными эффектами, контекстом полномочий и честными исходами. AppDock может предоставить узел, поставку, runtime и в будущем сетевое подключение, но текущий код AppDock не даёт оснований считать готовыми MCP/A2A-сервисы Strategy Box. Встроенная или внешняя когнитивная система — **отдельный исполнитель роли AI**, а не обязательная зависимость core.

## 1. Точная постановка, комментарии разработчика и статус решений

### 1.1. Предмет темы 06

Исходный документ требует исследовать представление доступных аналитических возможностей **для внешних разрешённых программных потребителей и ИИ-агентов**; различить Python API, предметную операцию, машинный инструмент и план исполнения; оценить переносимость и версии. Его два проверочных вопроса:

1. Какие операции заслуживают отдельной машинно-читаемой регистрации, а какие достаточно оставить обычными вызовами core?
2. Как описать входы, ограничения, побочные эффекты и результаты без искусственной универсализации каждого доменного типа?

**Семь названных разработчиком режимов — реальные продуктовые цели, а не семь реализованных функций:**

| № | Требуемая траектория | Существенная граница |
|---|---|---|
| 1 | Запуск команды/сценария/каскада внутри Strategy Box | Собственная пользовательская поверхность → прикладное исполнение → core |
| 2 | Вызов команды из Google Colab, Jupyter и другой внешней Python-среды | Прямое использование установленного Python-пакета; без обязательной зависимости от GUI/AppDock |
| 3 | ИИ на другом устройстве вызывает исполнение на хосте Strategy Box через **MCP** | Remote Tool Client → MCP endpoint → проверенный запуск на хосте |
| 4 | ИИ на том же устройстве обращается к Strategy Box через **MCP** | Local Tool Client → локальный транспорт MCP → тот же допуск/исполнитель |
| 5 | ИИ на другом устройстве обращается через **A2A** к ИИ на хосте, который сам исполняет поручение | Внешний агент → агент на хосте → набор разрешённых операций / сценариев |
| 6 | Встроенный в Strategy Box ИИ вызывает аналитические возможности | Embedded cognition → прикладной каталог → исполнитель/core, без обязательного сетевого протокола |
| 7 | Внешний ИИ через A2A поручает работу именно встроенному агенту Strategy Box | Внешний агент → A2A-adapter встроенного агента → аналитическое исполнение |

Комментарий «**требования к оформлению команд, процедур, кода должны быть универсальны и выполнимы в рамках любого варианта**» трактуется как **требование единства предметной семантики, а не тождества протоколов**. Функция в Colab, удалённый MCP-вызов и A2A-поручение могут иметь одинаковую аналитическую цель, но отличаются стороной принятия решения, удостоверением вызывающего, обработкой тяжёлого результата, отменой и жизненным циклом.

### 1.2. Что уже задано, что желательно, что остаётся открытым

| Класс | Содержание | Статус |
|---|---|---|
| Установленная продуктовая цель | Одни и те же бизнес-возможности доступны из Strategy Box и внешнего Python | **Требование разработчика**; частично достижимо сегодня через core |
| Установленная продуктовая цель | Поддержать MCP для локального и удалённого AI и A2A для агентского делегирования | **Целевой режим**, техническая реализация в будущем |
| Установленная продуктовая цель | Возможности пригодны встроенному AI | **Целевой режим**, агентный runtime ещё не выбран |
| Пожелание | Максимально универсальное оформление всех команд/процедур | **Цель унификации**; нужно ограничить её там, где предметная семантика требует специальных типов |
| Гипотеза | MCP/A2A будет организован через AppDock | **Гипотеза о внешней платформе**, зависит от её реальных будущих контрактов |
| Открытый вопрос | Нужен ли самостоятельный общий application service или достаточно in-process composition | **Решение о deployment**, разделение логических ролей уже можно определить |
| Открытый вопрос | Какие возможности публиковать агенту, с какой автономией, где хранить state и как выдавать подтверждения | **Политика допуска**, отдельная от transport |
| Открытый вопрос | Какова модель согласования версий core/каталога/схем/протоколов | **Контрактная политика**, рекомендуется ниже |

**Существенная поправка к буквальному прочтению:** наличие возможности в библиотеке **не** означает, что её надо выводить в machine catalog, и наличие записи в catalog **не** означает право конкретного агента её запускать.

### 1.3. Метод и шкала достоверности

Использованы: холодный вход в основной репозиторий, свежий код и документы прямых implementation owners, корпус Research 01–03, текущая документация `docs/`, документация AppDock и официальные внешние стандарты/исследования. В выводах:

- **CURRENT** — наблюдаемый на указанных commit код/манифест/структура;
- **SUPPORTED** — архитектурный вывод, согласованный с наблюдаемой реализацией и несколькими источниками, но без Product admission;
- **PROPOSED** — наша целевая рекомендация, включая иллюстративные модели;
- **OPEN** — вопрос, где отсутствуют данные, политика или эксперимент;
- **CONFLICT** — реальные альтернативы, одновременно реализовать которые в одной ответственности невозможно либо слишком дорого.

Документация `stratbox/docs/` прямо обозначена как `PARTIAL / UNDER CONSOLIDATION` и различает действующий код и кандидатные решения ([docs/README.md](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/docs/README.md)); новый `docs/how/execution` имеет пометку `CANDIDATE`, а не production contract. Данные этого исследования **не являются результатом запуска тестов/серверов**.

---

## 2. Холодный вход и карта фактического состояния

### 2.1. Ownership и корпус

Проверены [core README](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/README.md), [AGENTS.md](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/AGENTS.md), [_mw/AGENTS.md](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/AGENTS.md). Они однозначно разделяют:

- `stratbox`: **бизнес-код, источники, расчёты, канонические модели, предметные результаты, нейтральные инфраструктурные контракты**;
- `stratbox-windows`: **действующий Windows surface**, локальные операции, сценарии, запуск, состояния интерфейса;
- AppDock: **внешняя** поставка, среда, активация, runtime/node; его будущие сетевые возможности требуют самостоятельного подтверждения;
- `stratbox/_mw`: общий Research/provenance workspace; **само размещение исследования не делает core владельцем всех архитектурных решений**.

Релевантные материалы второго корпуса: [команды/сценарии/каскады](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md), [автоматизация и ИИ](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md), [готовность бизнес-кода к машинным схемам](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md), [граница между ядром и внешней когнитивной системой](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_boundary_research_2026-10-07.md), [архитектура core](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_target_core_design_architecture_2026-10-07.md), [web/host](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md). Третья ветка уточняет их через [каноническую онтологию](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_02_canonical_semantic_model_2026-10-08.md), [Work → Execution](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_04_work_to_execution_consolidated_research_2026-10-09.md) и [Capability/Extension/Automation](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_06_capability_extension_automation_consolidated_research_2026-10-09.md). Исторический `01-old-notes` объясняет первоначальные намерения, но текущему коду и консолидированным определениям не противостоит как второй owner.

### 2.2. CURRENT: аналитическое Python API уже существует

Примеры реальных внешне вызываемых entry points:

| Домен и публичный вызов | Форма | Машинная зрелость и замечание |
|---|---|---|
| [`collect_cbr_files(CbrFileCollectRequest, filestore=...)`](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/cbr_file_collector/operations.py) | Типизированный request/result | Хороший кандидат **предметной** операции; в core также есть вспомогательная `list_cbr_file_sources` |
| [`build_escrow_history` / `build_escrow_views` / `export_escrow_workbook`](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/escrow/operations.py) | Несколько стадий конвейера | Разные эффекты и результаты: discovery/build/view/export нельзя слить в одну непрозрачную tool-функцию |
| [`run_frg_stage1`](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/frg/api.py) и функции cleanup | `dict[str, object]`, DataFrame, план/применение | Пример необходимости **сохранить богатый Python API**, но специально оформить внешнюю machine-projection |
| [`run_sors_restoration`](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/cbr_sors_restoration/operations.py) | Крупные типизированные структуры и DataFrame | Хороший пример тяжёлой операции с provenance/constraints: её result нельзя просто положить в строку ответа LLM |
| `FileStore`, `ioapi`, `base.net` | Библиотечная инфраструктура | Важны для бизнес-кода, но **не весь FileStore** должен становиться общедоступными AI-инструментами |

Важное достоинство: существующие доменные функции можно импортировать и вызывать в обычном Python **без `stratbox-windows`**. Ограничения зависят от нужных input files, сети, optional dependencies и окружения; наличие importable function не гарантирует доступность конкретных ресурсов.

### 2.3. CURRENT: Windows хранит отдельный локальный каталог

В [`OperationSpec`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/catalog/models.py) есть `id`, title, description, строковый `handler='module:function'`, tags, enabled, requires_workspace, параметрические specs, fixed values, `dangerous`, `visibility_policy`, `ai_visibility`, expected artifact kinds. Это существенный задел, но он **не является** проверенной независимой машинной декларацией: не содержит строгой входной/выходной JSON Schema, semantic version, условия допуска, typed effects, stable binding revision и официального availability result.

В [registry.py](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/catalog/registry.py) определены **три** спецификации: `cbr_file_collector.collect`, `escrow.history.export`, `system.diagnostics`. В [scenarios/models.py](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/models.py) — последовательные `ScenarioStepSpec` c `operation_id`, параметрическим отображением и overrides; в [scenario runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) — реальное исполнение и фиксация кейсов/событий. [Operation runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/execution/runner.py) динамически импортирует handler, проверяет workspace и возвращает `OperationResult`.

**Пробелы актуального контракта:**

- В параметрах доменного запуска могут находиться локальные файловые пути и значения, сформированные из текущего `AppContext`. Их нельзя механически переносить в удалённое API другого устройства.
- `fixed_param_values` защищает удобство UI, но не является политикой разрешений: значения должны принудительно применяться **на стороне исполнителя**, а не как доверенные поля от клиента.
- `dangerous: bool` и `ai_visibility: str` недостаточны для деления операций на read-only, network fetch, create, overwrite, delete, external write и для реального policy decision.
- Строковый обработчик безопасен как **доверенная запись установленного каталога**, но абсолютно неприемлем как параметр внешнего tool call: агенту нельзя передавать произвольные `module:function`.
- Scenario и Operation живут в Windows surface, хотя новые Web/Android/host потребители требуют общей семантики; текущее [`runtime/bootstrap.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py) всё ещё затрагивает Qt coordinator.
- Один действующий coordinator исполняет один сценарий, полноценного task service, удалённого API, сетевой авторизации и AI agent runtime нет (см. [исследование Windows](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox-windows_current_state_full_research_2026-10-06.md)).

### 2.4. CURRENT: AppDock даёт оболочку, но не готовую AI-сеть

Текущий [`appdock/manifest.json`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json) — **контракт 4.0**, один local Windows `foreground` desktop surface. Manifest декларирует внешний core как source/package requirement и Python runtime binding, но **не** MCP endpoint, A2A agent endpoint, remote `ExecutionBackend` или headless Strategy Box service. В README Windows имеются устаревшие упоминания Connector `3.0` — факт документационного drift, **не** основание считать manifest версией 3.0.

[AppDock architecture](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/overview.md), [manifest authority](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/manifest_authority.md) и [source/package/runtime binding](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/source_composition_and_surfaces.md) подтверждают зрелый подход к **точной идентичности поставки, managed environment и activation context**. Это важно для вычислительной среды и версий. Но платформенная `capabilities` в манифесте описывает возможности поверхности/поставки и **не является предметным каталогом аналитических операций**. Структура сетевого агентского gateway и его гарантии остаются внешней зависимостью.

**Следствие:** Strategy Box может уже сегодня проектировать независимый server-facing адаптер и каталожный контракт. При появлении подтверждённого AppDock gateway он подключится к адаптеру; преждевременное встраивание MCP-семантики в manifest или `stratbox.base` создаст неустойчивую зависимость.

### 2.5. Неравномерная зрелость — данные для архитектурного выбора

`stratbox` не обязан перенести одновременно все домены на одинаковый внешний контракт. У `cbr_file_collector` уже близкая к machine-ready пара Request/Result; `escrow` отчётливо разделяет build и export; `frg` возвращает сложный набор DataFrame и планирует опасные действия; SORS реализует богатые evidence/results и методологические условия. Для них разумен **тонкий adapter/projection per operation**, а не глобальная переделка всех DataFrame/регистров в JSON.

---

## 3. Онтология: шесть разных объектов вместо одного «инструмента»

| Объект | Определение и владелец семантики | Что **не** следует с ним путать |
|---|---|---|
| **Python Callable** | Любая доступная библиотечная функция, метод или helper (`stratbox`) | Автоматически публичным продуктовым действием, безопасным для удалённого вызова |
| **OperationDefinition** | Устойчивый **предметный** use case: вход, результат, метод, применимость, эффекты, ошибки (`stratbox`) | Случайной функцией парсинга, кнопкой UI, вызовом MCP |
| **CapabilityDefinition** | Семантическое обещание/умение, может иметь несколько реализаций, условий или альтернатив; logical owner домена | Установленным кодом, персональным разрешением, работающим endpoint |
| **ToolProjection** | Вид разрешённой операции для протокола конкретного caller (MCP tool, модельный function call, иногда HTTP action) | Независимой новой бизнес-реализацией |
| **Scheme/ScenarioDefinition** | Повторно используемая смысловая композиция/процедура с входами, зависимостями и результатом; машинный и пользовательский виды могут различаться | Уже выполненной задачей, гарантией применимости, A2A Task |
| **ExecutionPlan** | Зафиксированный **для конкретного запроса** разрешённый план: конкретные bindings, ресурсы, параметры, порядок, effect boundaries | Общей библиотечной функцией, текстовым планом LLM, готовым фактом выполнения |

**Ключевое дополнительное разграничение:**

- `Capability` отвечает **что вообще умеет система при выполненных условиях**;
- `Binding` отвечает **какая конкретная реализация выбрана, установлена и способна работать в данной среде**;
- `Availability` отвечает **можно ли это исполнить прямо сейчас в указанном профиле/узле**;
- `Authorization` отвечает **разрешено ли это субъекту с данным делегированием**;
- `Invocation` отвечает **что он запросил**;
- `Run/Job/Attempt` отвечает **что реально началось, где и с каким исходом**.

Подмена этих измерений флагом `enabled=True` — системная ошибка: capability может существовать и быть установленной, но ещё не иметь нужного источника, достаточной памяти, файловых прав, разрешения автора или принятого подтверждения destructive action.

### 3.1. Связь Scheme и Scenario

Для темы 06 важно **не принимать заранее** одну из конкурирующих схем:

- *Model A:* `Scenario` — отдельный user-facing definition, `Scheme` — machine-facing план, схематическая структура извлекается из сценария.
- *Model B:* `SchemeDefinition` — каноническая машинно-читаемая композиция, `Scenario` — курируемая смысловая проекция/ссылка на неё.
- *Model C:* `Scenario` и `Scheme` — разные, но связываемые, версии процедур; один сценарий может опираться на несколько схем.

**Рекомендация для машинного интерфейса:** не привязывать протокольный контракт к спору о полном lifecycle Scheme/Scenario. Экспортировать **`ExecutableDefinitionRef`** с явным `kind=operation|scenario|scheme` и версией, а разрешение definition → compiled plan оставить прикладному planner. На раннем этапе реально потребуются только `operation` и `scenario`; `scheme` добавлять по фактическому потребителю машинных композиционных знаний. История `Cascade` не должна диктовать отдельную границу MCP/A2A.

### 3.2. Не путать план с агентским reasoning

AI может предложить желаемые шаги, но системный ExecutionPlan допустим только после валидации зависимостей, capability versions, параметров, effect policy, ресурсов и возможности конкретного узла. А2А-агентская задача может в процессе порождать много внутренних plan revisions. Структура A2A Task от этого **не становится** Strategy Box ExecutionPlan.

### 3.3. Терминологическое предупреждение о «Command»

В ранних исследованиях `Command` обозначает технический шаг, `Scenario` — осмысленную рабочую единицу, `Cascade` — крупную композицию. В третьей ветке семантика пересмотрена: `OperationDefinition` признан доменным use case, а `Scheme` — кандидат для typed composition. Это реальные **конкурирующие рабочие модели**, а не утверждённое единое дерево типов. Для темы 06 достаточно гарантировать, что **идентичность вызова не зависит от того, как операция названа на экране**.

---

## 4. Что регистрировать в каталоге, а что оставлять Python-функцией

### 4.1. Публикуется не всё, что можно импортировать

**Рекомендуемый основной критерий:** самостоятельно регистрируется операция, для которой есть **устойчивое намерение внешнего потребителя и безопасная проверяемая граница вызова**. Классификация должна быть сделана явно, а не через автоматическую интроспекцию всех `__all__`.

| Класс функций | Python API | Machine catalog | Tool для агента |
|---|---|---|---|
| Мелкая нормализация строки, временных точек, helper сериализации | **Да** | Обычно **нет** | **Нет** |
| Внутренний parser конкретной верстки XLSX/DBF | Да, если public API требуется | Обычно нет; исключение — диагностический use case | По умолчанию нет |
| Получить каталог официальных источников | Да | **Да**, если это устойчивый request/result | **Да**, read-only и фильтрация результатов |
| Скачать/сохранить первичные файлы ЦБ | Да | **Да**, если есть внешний consumer | Да с ограничением output namespace и effects |
| Построить историю счетов эскроу | Да | **Да** | Да, если доступны нужные inputs и budget |
| Построить эскроу-Excel | Да | **Да** | Да, с записью артефакта и проверкой эффекта |
| Просмотреть каталог FRG | Да | Да по необходимости | Да, если публичное отображение файлов разрешено |
| Построить план удаления/очистки FRG | Да | Да | Да в read-only/proposal режиме |
| **Применить** план очистки FRG | Да | Да при принятой продуктовой политике | По умолчанию скрыто или approval-gated; нельзя совмещать с `plan` |
| Запустить SORS-восстановление | Да | Да при наличии ресурсов и формализованной input binding | Да на уровень «начать вычисление/получить статус», **не** возвращать гигантские таблицы в одном ответе |
| Универсальный `open_write/remove/rmtree` FileStore | Да для библиотечного кода | Только отдельные ограниченные прикладные операции | Нет общего raw filesystem shell |
| Произвольный `eval`, `exec`, импорт модуля или Python script | Да как возможности самого Python-окружения разработчика | **Нет** | **Нет** |

### 4.2. Пять проверок перед регистрацией

1. **Semantic:** внешняя цель описывается без UI-фразы «нажать кнопку», есть стабильный результат и владелец домена.
2. **Contract:** известны JSON-представимые входы или контролируемые References, понятны валидации, единицы, применимость, ошибки, варианты частичного результата.
3. **Effect:** заранее известны классы чтения/загрузки/файловой записи/перезаписи/удаления/внешней отправки и нужная точка подтверждения.
4. **Execution:** оценены deadline, ресурсы, preflight, отмена, политика повторов и точка перехода к asynchronous job.
5. **Consumer:** определён как минимум один реальный внешний потребитель; не обязательно, чтобы это был агент. Существуют документация, владелец версии и тест.

Если нет (1) — оставить utility в core; если нет (2)/(3)/(4) — сначала довести контракт; если нет (5) — **не материализовать каталог «на всякий случай»**.

### 4.3. Приоритетные кандидаты — примерный MVP

1. `cbr.sources.list` — список поддерживаемых публикаций, read-only.
2. `cbr.files.collect` — получить и опубликовать raw snapshots (эффект записи).
3. `escrow.history.build` — построить нормализованный результат.
4. `escrow.history.export` — сформировать XLSX/ZIP (эффект артефакта).
5. `frg.catalog.scan` — исследовать файлы в заданном workspace-scope.
6. `frg.cleanup.plan` — **только план** и предупреждения.
7. `sors.restore` — тяжёлый расчёт как asynchronous job с summary/refs.
8. `system.capabilities.list` / `system.capability.describe` — интроспекция каталога (прикладные служебные tools, не core domain).
9. `system.jobs.get` / `system.jobs.cancel` — только если реально материализован JobManager.

Это **предлагаемые стабильные IDs**; они не заменяют автоматически реальные Windows IDs и не означают реализации новых функций на текущем `main`. Выбор первого пилота должен опираться на домен с наименее спорным входом и безопасным эффектом: `cbr.sources.list` + `cbr.files.collect` предпочтительнее старта с полного SORS или destructive FRG.

---

## 5. Нейтральный контракт capability: минимальный, но содержательный

### 5.1. Архитектурное правило

Каталог должен быть **отдельным от конкретного transport и UI**, но **не отдельным миром моделей, конфликтующим с Python**. Предлагаются три слоя:

```text
Domain Python API / typed Request, Result, native DataFrame, FileStore
                  │
        explicit operation adapters
                  │
Canonical OperationDescriptor + ExecutionBinding + ResultEnvelope
                  │
   ┌──────────────┼───────────────┬──────────────────┐
   │              │               │                  │
Python wrapper  App/UI        HTTP/OpenAPI      MCP tool projection
                                  │                  │
                             A2A agent       AI local function
                             internal use      adapter
```

Стрелка от A2A к предметному каталогу условная: **A2A публикует агентское умение/делегирование, не обязательно одну Operation как один tool**. Все пути при удалённом управляемом исполнении сходятся в **едином admission/execution service**.

### 5.2. Логически обязательные поля (не означают десятки обязательных ключей в первом JSON)

| Группа | Содержимое | Чем обоснована |
|---|---|---|
| Identity | `operation_id`, `contract_version`, `domain`, `title`, semantic description | Повторяемость вызова, каталог, ссылки |
| Typed IO | `input_schema`, `result_schema`, semantic types/reference kinds | Валидация без Python-интроспекции на клиенте |
| Applicability | required source families, input formats, dependency conditions, supported profiles | Наличие кода ≠ готовность к запуску |
| Effects | read external, download, create, overwrite, delete, external publish, unknown; effect scope | Прозрачность и граница безопасного исполнения |
| Execution profile | expected duration class, sync/async eligibility, budget, resource/worker needs | Тяжёлые расчёты, remote host |
| Reliability | replay class, idempotency guarantee, partial result, cancellation points, error taxonomy | Повтор, прерывание, side effects |
| Result semantics | return value category, artifact kinds, provenance, method/status | Банковская доказательная квалификация |
| Exposure hints | user-facing/automation/AI eligibility | UX, но **не** право доступа |
| Governance | owner, documentation, implementation revision, deprecation/availability | Каталожное сопровождение и аудит |

**Минимально достаточно для первой итерации:** identity, schema, effects, result kind, availability adapter, binding, owner, version, documentation, classification risk. Оставшиеся свойства можно вводить по мере появления долгих заданий/агентской автономии. Для опасных действий **отсутствующие параметры не означают «безопасно»**: действует fail-closed.

### 5.3. Пример целевого описания одной операции (иллюстрация, не действующая schema)

```yaml
kind: operation
id: escrow.history.export
contract_version: '1.0.0'
title: Собрать историю счетов эскроу
summary: Сформировать структурированный отчёт из официальных публикаций
owner: stratbox.macrobanks.escrow
input_schema_ref: 'schema://operations/escrow.history.export/1/input'
result_schema_ref: 'schema://operations/escrow.history.export/1/result'
input_semantics:
  requested_periods: calendar-month, inclusive interval
  refresh: force acquisition of available source snapshots
  target: WorkspaceLocationRef, not an arbitrary host path
preconditions:
  requires_network: conditionally
  requires_workspace: true
  supported_execution_profiles: [local, host]
effects:
  - kind: network_read
  - kind: artifact_create
    scope: workspace.output
  - kind: overwrite
    when: explicit_overwrite_option
risk_class: controlled_write
execution:
  mode: sync_or_job
  retries: constrained_by_effects
  cancellation: cooperative_before_publish
result:
  kind: artifact_summary
  artifact_types: [xlsx, zip]
  preserve_source_failures: true
provenance:
  include_core_revision: true
  include_source_acquisition_times: true
visibility:
  human_catalog_candidate: true
  machine_catalog_candidate: true
  agent_candidate: true
```

Это **семантическое описание**. Реальные `Cbr/escrow` Request/Result-классы не обязаны наследовать новую глобальную метамодель. Binding реализует ручной перевод из внешнего сериализуемого Request в доменный тип, а обратно — только разрешённый машинный Result.

### 5.4. `OperationDefinition` против `ExecutionBinding`

Не смешивать стабильное описание предметной операции с адресом обработчика. Пример:

```text
OperationDefinition
  id = escrow.history.export
  contract = 1.0.0
  semantic request/result/effects
  owner = core

ExecutionBinding
  operation_id = escrow.history.export
  implementation = installed Python distribution revision
  callable_ref = trusted, server-controlled module:function
  input_adapter = validated JSON -> typed domain request
  output_adapter = domain result -> safe summary/artifact refs
  worker_profile = local or host
  environment_identity = exact installed package digest
```

**Binding выбирается доверенным композиционным уровнем.** Клиент присылает `operation_id` и параметры, но **не выбирает Python module, сетевой адрес, путь исполняемого файла или секретную конфигурацию**. Так один и тот же контракт работает для нескольких поставок без раскрытия инфраструктуры.

### 5.5. Capability catalog как пять логически разных проекций

Третья исследовательская ветка предлагает различать semantic catalog, installed contributions, bindings, availability и subject projection. Это верное **логическое** разграничение, но пять самостоятельных СУБД/сервисов преждевременны. Достаточно одного внутреннего реестра и нескольких чистых функций-представлений:

```text
list_definitions()           # какие операции известны продукту
resolve_bindings(node)       # чем они могут быть исполнены
assess_availability(context) # какие входы/ресурсы готовы
filter_for_subject(subject)  # что конкретному caller разрешено увидеть
project_to_protocol(client)  # какие tools/schema/refs поддерживает канал
```

**Availability должна быть объектом, а не bool**. Рекомендуемые значения: `available`, `blocked_missing_input`, `blocked_environment`, `blocked_permission`, `requires_approval`, `temporarily_unavailable`, `unsupported_transport`, `unknown`; вместе с safe reason и применимыми actions. При отказе платформы сведения могут быть устаревшими, поэтому проверка повторяется в момент запуска.

### 5.6. Важная тонкость: описание «права» в каталоге и реальное право

`visibility=agent` или `dangerous=false` — **метаданные**, а не authorization. Каноническое правило:

> Реальное разрешение на побочный эффект вычисляется **на стороне того узла/application authority, где этот эффект будет произведён**, с учётом principal, делегирования, области данных, версии политики, операции, параметров и предварительного согласия.

Каталог для конкретного AI должен быть отфильтрован. Но даже если внешний AI сохранил старую schema/tools-list, сервер на `tools/call` применяет **новую актуальную policy**. Нельзя полагаться на то, что UI/LLM «просто не покажет» опасный инструмент.

---

## 6. Переносимые типы: универсализировать транспорт, сохранить предметный смысл

### 6.1. Основа — JSON Schema 2020-12, но только на boundary

**Внешний факт:** JSON Schema 2020-12 определяет структурные ограничения JSON-документов, условные конструкции, композиции и ссылки на схемы ([официальная спецификация](https://json-schema.org/draft/2020-12/)). В MCP `2026-07-28` инструменты используют полную JSON Schema 2020-12 при object-root input, включая `oneOf` и `$ref` ([изменения протокола](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/)).

**Выбор для Strategy Box:** schemas — формат обмена на границе, а не заменитель внутренних `pandas`, `numpy`, dataclass, typed errors или методологических grids. Значение `Decimal('12.30')` в Python, дата официального периода, неизвестное наблюдение и DataFrame — **разные предметные объекты**, и их нельзя бездумно кастовать в `float`/`str`/`dict`.

### 6.2. Предлагаемый маленький словарь транспортных типов

| Семантика | Boundary-представление | Правило |
|---|---|---|
| Строка, bool, integer, идентификатор | JSON primitives | Явные constraints, enum только при стабильном закрытом множестве |
| Денежная сумма / точная десятичная величина | Decimal как **string** с regex и отдельным `unit/currency/scale` | Исключить двоичную потерю точности и путаницу единиц |
| Дата публикации / момент загрузки | `date` (`YYYY-MM-DD`) / UTC timestamp RFC 3339 | Дата среза ≠ момент загрузки; период имеет собственный тип |
| Год/квартал/месяц | `PeriodSpec` как объект `frequency`, `start`, `end`, semantics | Не угадывать квартал из неявного формата строки |
| Банковский/географический/ОКВЭД код | String ID с namespace и version/ref | Коды нельзя автоматически приводить к числу |
| Файлы и источники | `WorkspaceFileRef`, `SourceSnapshotRef`, `ArtifactRef` | **Не** пересылать пути хоста в удалённом API |
| Небольшой аналитический итог | Inline `summary` + method + provenance | Сохранять отдельно `unknown`, `not_available`, `suppressed`, `0` |
| Табличный набор | `DatasetRef` + schema/ref + row count + preview | Страницы/проекция/экспорт доступны отдельным вызовом |
| Большой бинарный файл | ArtifactRef + media type + size/hash/access method | Не помещать байты в LLM-контекст |
| Ошибка/предупреждение | Typed `Problem` + diagnostics/evidence ref | Не заменять всё строковым исключением |

Особенно для SORS нужно передавать **доказательную квалификацию** (`evidence tier`, source bounds, assumptions), а не только число. Если формальный договор доказательности ещё не утверждён, выбранная machine operation должна возвращать `result_ref` и контрольную summary, оставляя богатые grids в нативном core.

### 6.3. Контракт локального пути и удалённого файла — принципиально разный

Сейчас Windows формы содержат `path_dir/path_file`, т. е. путь относительно локального контекста. Для Python-вызова на той же машине допустим `pathlib.Path`/строка. При MCP/A2A на другом устройстве путь `C:\...` **указывает на чужую файловую систему**, может не существовать или нарушать границу безопасности.

Рекомендуется:

```json
{
  "target": {
    "kind": "workspace_location",
    "workspace_id": "primary",
    "relative_path": "output/escrow",
    "overwrite": false
  }
}
```

Сервер обязан канонизировать путь, проверить namespace, symlinks/traversal и права записи. Внешнему AI возвращается `ArtifactRef`/доступная ссылка на ресурс, а не raw absolute path. Для Python возможно удобное преобразование `Path` → `WorkspaceLocationRef` через тот же валидатор, **если выбран управляемый режим**.

### 6.4. Пример `inputSchema`, достаточно строгий для tool

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "save_mode": {"type": "string", "enum": ["zip", "files"]},
    "target": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "workspace_id": {"type": "string", "minLength": 1},
        "relative_path": {"type": "string", "minLength": 1}
      },
      "required": ["workspace_id", "relative_path"]
    },
    "overwrite": {"type": "boolean", "default": false}
  },
  "required": ["save_mode", "target"]
}
```

**Это иллюстративная будущая boundary schema, не точная схема существующего `CbrFileCollectRequest`.** Схема проверяет структуру, но **сама по себе не доказывает** допустимость папки, достаточность диска, существование источника, право overwrite или отсутствие у пути выхода через symlink. Требуются domain validation + runtime preflight + admission policy.

### 6.5. Нельзя допускать потери информации при проекции

Показательный случай: числовой показатель равен `0`, а другой скрыт публикацией/временно отсутствует. JSON `null` для обоих без `missing_reason` разрушает смысл. Должен существовать, как минимум:

```json
{
  "value": null,
  "unit": "million_rub",
  "status": "unavailable",
  "reason": "official_publication_absent",
  "source_snapshot_ref": "source:..."
}
```

Возможный `0` в другом объекте имеет `value: "0"`, `status: "observed"`; восстановленное/модельное значение получает свою квалификацию. Степень detail по доменам может отличаться; **транспортный envelope обеспечивает различимость**, но не переписывает методологию каждого домена.

### 6.6. Автоматическая генерация схем: удобный черновик, не authority

Pydantic/dataclass-typing и JSON Schema generator полезны для механического обнаружения поля и типа. Но автоматически созданная schema **не знает**: относится ли параметр к локальному пути или workspace, какие запросы опасны, допустимо ли повторить запрос, как распределяется бюджет, что значит `partial`, чем отличается отсутствие источника от сетевого отказа. Поэтому:

- генерировать структурную часть допустимо;
- semantic annotations/effects/authorization описываются и ревьюятся явно;
- публикуемый snapshot schema версионируется;
- схемы проверяются контрактными тестами против реального handler;
- **никакой runtime-интроспекции произвольного установленного Python-кода по запросу внешнего AI**.

---

## 7. Протоколы и архитектурные альтернативы: что с чем сравнивать

### 7.1. Матрица альтернатив

| Решение | Задача | Достоинства | Ограничения/риск | Роль в Strategy Box |
|---|---|---|---|---|
| **Прямой Python API** | Colab/Jupyter/локальные скрипты | Полная мощность pandas/numpy, нет сетевого overhead, привычная отладка | Потребитель сам управляет Python environment; нет встроенной remote auth и универсального long-running state | **Обязательный основной канал core** |
| **Нейтральный application callable/API** | Унифицировать UI, CLI, background, machine caller | Один admission/result/job contract | Требует явного разведения core и application authority | **Рекомендуемый внутренний каркас** |
| **HTTP API с OpenAPI** | Управляемые remote apps, web, программные интеграции | Широкая совместимость, typed error, SDK generation, независимость от ИИ | Нужно выбрать server/storage/auth, больше инфраструктуры | **Предпочтительная основа host-facing service**, когда remote нужен |
| **MCP** | Позволить ИИ обнаруживать и вызывать ограниченные tools/resources | Стандартные tools/list/call, schemas, prompts/resources, зрелые SDK | Отдельная auth/transport-политика, неодинаковые версии клиентов, агентская безопасность | **Адаптер поверх каталога**, локальный и remote |
| **A2A** | Делегирование самостоятельному AI-агенту цели с task/feedback | Agent Card, работа с контекстом, Task/Message/Artifact, streaming/async | Требует **реального AI agent runtime**; не подменяет function calling | **Опциональный адаптер агентской роли**, позже |
| **gRPC/Protobuf** | Высоконагруженное типизированное service-to-service | Хорошая генерация кода, streaming | Второй типовой язык; не нужен для малочисленных аналитических calls на первом этапе | **Отложить** |
| **Один «универсальный JSON-RPC» собственного дизайна** | Свести все вызовы в единый протокол | Полный контроль | Повторное изобретение ошибок/auth/схем, зависимость от уникального клиента | **Не рекомендовано** |
| **Все функции через произвольное выполнение Python на хосте** | Кажущаяся максимальная гибкость | Нет необходимости поддерживать каталог | Максимальные риски произвольного кода/данных, безконтрольные эффекты, отсутствие стабильного контракта | **Исключить как публичную/агентскую возможность** |

**Вывод:** выбирать между Python API и MCP — ложная дилемма; они обслуживают **разных потребителей** одного domain layer. Между MCP и A2A также нет отношения «старый/новый»: первый стандартизирует доступ к инструментам, второй — взаимодействие независимых агентов.

### 7.2. OpenAPI — полезен, но не каноническая онтология

Официальная [OpenAPI Specification](https://spec.openapis.org/oas/latest.html) описывает machine-readable HTTP-контракт, включая `operationId`, входы/выходы и security schemes. Хорошо подходит для будущих Web/Android/CLI клиентов и тестов. Однако:

- HTTP path/verb — транспортные детали, а не предметная идентичность `OperationDefinition`;
- `GET /operations`, `POST /runs`, `GET /runs/{id}`, `GET /artifacts/{id}` — разумный **кандидат**, а не уже существующий API;
- OpenAPI security scheme **не заменяет** авторизацию конкретного побочного эффекта;
- специфика JSON Schema/OpenAPI не должна заставлять SORS или FRG возвращать всю внутреннюю табличную модель как вложенный JSON.

Предпочтителен **транспорта-нейтральный каталог → OpenAPI document для HTTP**, а не генерация предметной семантики из HTTP endpoint annotations.

### 7.3. MCP: актуальная версия и практическое значение

По состоянию на 10.10.2026 существенные свойства **MCP `2026-07-28`**:

1. Спецификация перешла к **stateless core** без старого `initialize`/`initialized` и обязательных session IDs; для discovery есть `server/discover` ([официальный релиз](https://blog.modelcontextprotocol.io/posts/2026-07-28/)).
2. Tool описывает `name`, `description`, `inputSchema` и необязательную `outputSchema`, с полной JSON Schema 2020-12; сервер должен валидировать параметры/права ([официальная история и tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)).
3. Долгие запросы вынесены в **[Tasks extension](https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks)**. Протокольный `Task` — **не** долговременный `Job` Strategy Box, а ограниченное представление его жизни на одном канале.
4. Старые MCP roots/sampling/logging помечены как deprecated; диагностику Strategy Box нельзя проектировать вокруг MCP logging ([release notes](https://blog.modelcontextprotocol.io/posts/2026-07-28/)).
5. Для remote HTTP требуются доверенные transport/auth boundaries; спецификация MCP рассматривает собственные правила OAuth, токенов, discovery и audience validation ([Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)).

**Существенный риск:** некоторые клиенты и SDK продолжают использовать `2025-11-25`/старые модели Tasks и session. Нельзя обещать, что реализация «MCP вообще» поддержит все режимы. Нужна **матрица поддерживаемых protocol versions + negotiated features**, interop tests и отдельный lifecycle adapter. При разработке фиксировать конкретный SDK version. На дату исследования официальный Python SDK 2.x документирует v2 и local/in-process/stdio/Streamable HTTP транспорты ([SDK](https://py.sdk.modelcontextprotocol.io/)); выбор версии для внедрения остаётся архитектурным решением.

### 7.4. A2A: делегирование, не вызов Python-функции

Официальная [A2A specification 1.0.0](https://a2a-protocol.org/v1.0.0/specification/) описывает взаимодействие независимых агентских систем: Agent Card/skills, `Message`, `Task`, `Artifact`, поток статусов и возможность потребовать дополнительный ввод/авторизацию. Task может иметь `working`, `completed`, `failed`, `canceled`, `input_required`, `auth_required` и другие состояния; вызов `SendMessage` может возвращать результат после завершения или сразу — при `return_immediately=true`, с дальнейшим polling/subscription.

**Следствие для Strategy Box:**

- A2A endpoint обоснован только при наличии **настоящего агента на принимающей стороне**, который принимает цель, ведёт контекст, выбирает tools/сценарии, запрашивает уточнение и контролирует результат.
- Если удалённому AI достаточно запустить `escrow.history.export` с известными параметрами, **MCP** или HTTP action проще и точнее; обёртывать каждую Operation в A2A Agent не нужно.
- `AgentCard` может объявлять **агентское умение** вроде «анализировать банковские/макроэкономические публикации», но **не** должна дублировать весь domain operation catalog. Обратное связывание skill → разрешённые capabilities делается внутри приложения.
- Для встроенного агента, которого вызывает внешний A2A consumer, набор разрешённых внутренних tools всё равно фильтруется по actor/delegation/context. Внутренний агент не получает автоматически доступ ко всему локальному Python.

### 7.5. MCP tools, resources, prompts и host adapters

Для Strategy Box полезны разные MCP-сущности:

| MCP объект | Допустимая проекция | Чего избегать |
|---|---|---|
| `tools` | `list_capabilities`, `describe_capability`, `run_operation`, `get_run`, `get_artifact_metadata`, узкие доменные операции | Generic `execute_python`, raw arbitrary filesystem |
| `resources` | разрешённые summary, descriptors, методологические descriptions, небольшие previews | Приватные пути/файлы/логи без ACL, крупные XLSX «текстом» |
| `prompts` | Опциональные шаблоны аналитических пользовательских задач, если реально нужен такой UX | Перенос бизнес-методологии в свободный текст промпта как единственный source of truth |
| `Tasks extension` | Проекция долгоживущего `Run/Job`, если клиент поддерживает extension | Делать протокольную Tasks-структуру единственным durable state |

**Разница в discoverability:** человек видит понятные сценарии, машинный потребитель может получить типизированное описание операции, агент в конкретной сессии — **узкий список разрешённых** инструментов с пригодными описаниями. Это три view одного catalog, а не три источника истины.

### 7.6. Почему A2A и MCP лучше не вкладывать друг в друга насильно

Нормальная схема:

```text
        External application          External AI                 External AI
                │                          │                           │
             HTTP/Python                 MCP                         A2A
                │                          │                           │
                ▼                          ▼                           ▼
        Application API             MCP Adapter                  Agent Adapter
                │                          │                           │
                └───────────┬──────────────┘                           │
                            │                                          ▼
                     Admission API                              Hosted Agent Runtime
                            │                                   (owns reasoning/task)
                            │                                          │
                            └─────────────────┬────────────────────────┘
                                              ▼
                                  Capability / Binding / Executor
                                              ▼
                                         stratbox core
```

Агент на хосте **может** быть MCP-клиентом собственного сервера, но это лишний сетевой hop, если уже есть безопасный внутренний invocation port. Рекомендован **in-process application adapter** для доверенного локального агента, MCP — на внешних tool boundaries, A2A — на внешних agent boundaries.

---

## 8. Сквозные схемы семи путей разработчика

### Путь 1. Windows/будущие Web/Android: человек запускает готовую аналитику

```text
User action
 → semantic ScenarioRef + parameters
 → application admission (principal, current capabilities, data scope)
 → optional plan preview/approval
 → Run/Job
 → domain Python operation
 → Result / artifacts / messages / diagnostics
 → UI projection
```

**Рекомендация:** UI отображает те же фактические runs, которые могут запускать API/AI. В текущем Windows это пока case/scenario state, не общий cross-platform authority. При развитии UI не должен становиться отдельным источником правды о durable Job.

### Путь 2. Colab/Jupyter: пользователь вызывает библиотеку напрямую

Пример реального Python API (параметры и пути адаптируются к среде):

```python
from stratbox.macrobanks.cbr_file_collector import (
    CbrFileCollectRequest,
    collect_cbr_files,
)

request = CbrFileCollectRequest(target_path="./output/cbr_sources.zip", save_mode="zip")
result = collect_cbr_files(request)
print(result.success_count, result.failure_count)
```

*Пример иллюстрирует существующий API, но не проверялся запуском здесь; другие поля `CbrFileCollectRequest` могут иметь значения по умолчанию, а реальные загрузки зависят от сети.* Для natively imported Python **не нужна регистрация каждой функции в capability registry**. Можно добавить optional `stratbox.operations.invoke("cbr.files.collect", request)` как удобную программную обёртку лишь при появлении второго реального потребителя; это **не должно** ломать прямые доменные импорты.

**Важная оговорка:** при прямом Python-выполнении вне host application пользователь исполняет код со своими локальными правами и отвечает за окружение/эффекты. Этот путь **не эквивалентен управляемому удалённому вызову с централизованной авторизацией**. Поддержка обоих режимов — нормальная архитектурная асимметрия.

### Путь 3. Внешний AI → удалённый MCP → host Strategy Box

```text
External AI / MCP client
 → HTTPS MCP transport (future AppDock integration/host endpoint)
 → authentication + scope / audience validation
 → tools/list filtered to principal/delegation
 → tools/call with operation_id, JSON args, correlation/idempotency key
 → server admission + plan
 → host JobManager / worker
 → stratbox operation
 → result summary + artifact/dataset refs
 → MCP response or Tasks handle
```

Решающее отличие: **фактическая операция выполняется на хосте**, рядом с его разрешёнными ресурсами. Передавать клиенту произвольный путь хоста и доверять ему — ошибка. AppDock в этом потоке может предоставлять node connectivity, runtime identity и platform health, но **механизм его реального MCP-hosting ещё не подтверждён**.

### Путь 4. AI на устройстве хоста → локальный MCP

Тот же MCP tool schema и admission, но транспорт может быть `stdio` / loopback / in-process MCP SDK, без публикации внешнего HTTP endpoint. У local AI будет собственная delegated identity, даже если ОС-процесс работает под той же учётной записью. Не допускать упрощения «localhost значит доверено всё»: локальная интеграция способна вызвать запись/удаление важных файлов.

### Путь 5. Внешний AI → A2A → самостоятельный AI на хосте

```text
External delegating AI
 → A2A Agent Card + message/task
 → authenticated hosted agent (not necessarily embedded in UI)
 → agent interprets goal and requests allowed operations
 → application admission on each effect / plan
 → core execution, evaluate result, optionally iterate
 → A2A task state/messages/artifacts
```

Удалённому агенту видна **агентская услуга**, а не гарантированная 1:1 функция. Исполняющий агент может предложить план, запросить уточнение, выбрать сценарий или вернуть объяснение, почему задача недопустима. **Исполнение всё равно детерминированно проходит через core**. Нет оснований автоматически транслировать A2A task status в success отдельного банковского вычисления: такой Task может агрегировать несколько Jobs.

### Путь 6. Встроенный в Strategy Box агент

```text
Embedded AI runtime
 → trusted internal capability discovery
 → invoke/application admission (with delegated user authority)
 → scheme/scenario/operation
 → core
 → structured result + diagnostics/evidence
 → AI summarizes, continues or asks for confirmation
```

Интеграция прямо на application port даёт меньшую сложность, чем обратный loopback по HTTP. Встроенность в GUI **не должна** означать запуск вычисления на клиентском устройстве, если конечный профиль работает через host. Встроенный агент может находиться в headless service, а Windows/Android отображают его Work/Thread.

### Путь 7. Внешний AI → A2A → встроенный агент Strategy Box

С сетевой точки зрения это близко к пути 5. Разница — **кто владеет агентским runtime и UX**: собственный встроенный модуль Strategy Box, с его контекстом Work/Thread и полномочиями, вместо отдельно установленного агента на хосте. A2A-адаптер публикует Agent Card и принимает задания, встроенный агент делегирует доменные операции тому же admission service.

**Практический вывод по 5/7:** если внешний потребитель не должен различать происхождение принимающего агента, оба пути могут использовать **один A2A boundary contract** с разными Agent Bindings. Делать два несовместимых A2A протокола ради названий «встроенный» и «на хосте» не требуется.

### 8.1. Матрица зрелости/доступности семи путей

| Путь | Можно ли сегодня на текущем коде | Что нужно добавить |
|---|---|---|
| 1. Windows | **Да, ограниченно:** три operation specs, один composite, локальный запуск | Общий catalog/admission, concurrency/jobs, устойчивые state/permissions |
| 2. Colab/Jupyter | **Да как Python-библиотека**, если установлен core и доступны зависимости/данные | Документированные typed operations, examples, optional registry wrappers |
| 3. Remote MCP | **Нет подтверждённой реализации** | Host service, MCP adapter, auth, remote resource mapping, tests |
| 4. Local MCP | **Нет подтверждённой реализации** | Local server/stdio/in-process adapter, policy, tests |
| 5. A2A → host AI | **Нет подтверждённой реализации** | Отдельный agent runtime, Agent Card, A2A adapter, Job integration |
| 6. Embedded AI | **Нет подтверждённой реализации** | Когнитивный runtime, внутренние tools, budgets, audit |
| 7. A2A → embedded AI | **Нет подтверждённой реализации** | Всё из 6 плюс A2A boundary и delegation |

---

## 9. Что отдавать ИИ: каталог большой системы без каталожного шума

### 9.1. Две проблемы при росте функций

1. **Слишком много низкоуровневых tools:** отдельные tools для каждой арифметической операции, поля парсера, форматного действия и разновидности файлов приводят к шуму, ошибочному выбору и росту контекстного окна.
2. **Одна огромная универсальная tool `run_anything`:** короткий список функций, но модель должна помнить сотни operation IDs/param schemas без понятных границ; validation, права и outcome становятся непрозрачными.

Научные исследования демонстрируют, что у tool-use есть самостоятельная задача *поиска релевантного инструмента и выбора пути*, а не только синтаксическая генерация arguments: **Toolformer** (Schick et al., NeurIPS 2023) учит выбору времени и интерфейса API ([paper](https://papers.neurips.cc/paper_files/paper/2023/hash/d842425e4bf79ba039352da0f658a906-Abstract-Conference.html)); **ReAct** (Yao et al., ICLR 2023) показывает сочетание последовательных действий с наблюдением результатов ([paper](https://mlanthology.org/iclr/2023/yao2023iclr-react/)); **AnyTool** (Du et al., ICML 2024) исследует иерархическую маршрутизацию по большому набору инструментов ([paper](https://proceedings.mlr.press/v235/du24h.html)); **ToolLLM/ToolBench** рассматривает масштабы тысяч реальных API, включая retrieval средств вызова ([ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/28e50ee5b72e90b50e7196fde8ea260e-Abstract-Conference.html)). Эти работы **не доказывают конкретные показатели точности для Strategy Box**, но обосновывают архитектурное разделение поиска и исполнения.

### 9.2. Рекомендуемое двухуровневое discovery

**Уровень A — мета-инструменты (малый стабильный набор):**

- `strategybox.catalog.search(query, domain?, tags?)` — возвращает **короткие карточки** доступных операций/сценариев;
- `strategybox.catalog.describe(id)` — возвращает конкретную schema/constraints/risk/result contract;
- `strategybox.runs.submit(id, parameters, ...)` — инициирует только через admission;
- `strategybox.runs.get(run_ref)` — status и результат;
- `strategybox.artifacts.get_metadata(ref)` — ограниченная проекция результата;
- при фактической необходимости `preview`/`approve`/`cancel` как отдельные **policy-managed** действия.

**Уровень B — доменные tools для 5–20 наиболее частых действий:** допускается прямое `cbr.files.collect`, `escrow.history.export`, `sors.restore` с точными JSON schemas, если клиент хорошо справляется с таким discovery и scopes позволяют. Точная стратегия — **переключаемая проекция одного каталога**, а не две независимые системы. Проверить на пилоте selection accuracy, tool-count, request failure rate, число лишних calls, время до результата и долю недопустимых попыток.

### 9.3. Статическая vs динамическая экспозиция

Операции могут зависеть от установленной поставки, типа узла, лицензий/провайдеров, доступности workspace, состояния источников, политики пользователя. Каталог становится **контекстным**:

```text
Global supported definitions
 ∩ installed compatible bindings
 ∩ node resources
 ∩ current policy
 ∩ principal delegation
 ∩ transport-supported projection
 → effective tools/list
```

MCP tools/list допускает изменение каталога, но вызывающая модель может кэшировать старый список. Поэтому `tools/call` всегда проверяет admission повторно. Для удобства допустимы `catalog_revision`/ETag/TTL, **без предположения, что клиентское кеширование заменяет авторизацию**.

### 9.4. Качественные описания tools

Описание должно отвечать: *что делает; для каких источников/дат; какой результат; как долго может исполняться; создаёт/перезаписывает/удаляет ли файлы; нужно ли подтверждение; что делать с отсутствующими данными; где смотреть provenance.* Не помещать в `description` громоздкую методологическую спецификацию и не использовать его как единственный security control. Ограничения и результаты должны быть также представлены структурой.


---

## 10. Запуск, статусы, ошибки и фактические эффекты

### 10.1. Почему машинный `tools/call` не равен исполнению

Машинный запрос может завершиться с тремя принципиально различными наблюдениями:

1. **Admission rejected:** действие не принято к выполнению (нет прав, некорректный запрос, отсутствует binding, нужна санкция). Эффект не должен был начинаться.
2. **Accepted / pending:** запрос принят, создан Job/Run, но расчёт и файлы ещё не готовы. Синхронный ответ означает **только принятое поручение**.
3. **Outcome known / unknown:** исполнение уже началось; известен успех, отказ, частичный результат либо **неизвестно**, успел ли произойти внешний эффект до потери связи.

**Это нельзя сжимать в один `ok: bool`.** Последнее часто встречается в удобных ранних приложениях, но для удалённого AI создаёт опасную ложную интерпретацию: timeout с HTTP 504 не доказывает, что экспорт или удаление не произошли.

### 10.2. Рекомендуемый общий execution envelope

```json
{
  "invocation_id": "inv_01...",
  "run_ref": "run_01...",
  "operation": {
    "id": "escrow.history.export",
    "contract_version": "1.0.0"
  },
  "admission": "accepted",
  "execution_status": "running",
  "outcome": "pending",
  "attention": "none",
  "submitted_at": "2026-10-10T00:00:00Z",
  "links": {
    "status": "run:run_01...",
    "events": "events:run_01..."
  }
}
```

Здесь **схема иллюстративна**; статусные поля не отражают сегодняшние Python classes. Внутренняя модель из [кандидатного HOW — execution and effects](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/docs/how/execution/execution-and-effects.md) отдельно различает `OperationDefinition → Binding → Invocation → Run → Job → Attempt → EffectReceipt`. Для машинных API это полезнее, чем связывать идентичность только с ID чата или MCP request ID: **один и тот же run переживает сетевое переподключение, смену клиента, новую попытку и несколько UI-проекций**.

### 10.3. Успех анализа ≠ публикация файла ≠ принятие человеком

Фактическая последовательность экспорта должна различать:

```text
Domain compute succeeded
 → content staged
 → content verified
 → artifact published
 → ArtifactRef returned
 → user/AI can retrieve it
 → optional user acceptance
```

Если core закончил DataFrame-расчёт, но write/rename/verification файла сорвался, машинный ответ **не должен** сообщать «отчёт готов» только потому, что внутренний метод вернул результат. Для read-only операций `ArtifactRef` может отсутствовать. В файлах/больших данных перечислять версии результата и свойства доступности отдельно.

### 10.4. Нужна типизированная таксономия ошибок

| Класс | Пример | Может ли агент исправить аргументы и повторить? |
|---|---|---|
| `invalid_request` | Неверный период/параметр | Да, после коррекции |
| `not_authorized` | Нет права на источник/каталог | Нет, пока не изменено делегирование |
| `approval_required` | Перезапись уже существующего файла | Только после подтверждения и проверки того же плана |
| `binding_unavailable` | На узле нет нужной зависимости/профиля | Нет в текущем окружении |
| `source_unavailable` | Сайт/файл недоступен | Возможно позже; **не означает** «показатель равен нулю» |
| `data_invalid` | Схема публикации изменилась | Исправление парсера/правил, а не слепой retry |
| `resource_exhausted` | Solver не вписался в budget | Да только после изменения budget/ресурса |
| `execution_failed` | Алгоритм или worker завершились с ошибкой | Зависит от стадии и эффекта |
| `partial_result` | Некоторые источники получены, другие нет | Можно продолжить при явно разрешённой policy |
| `outcome_unknown` | Сеть потеряна после начала записи/удаления | **Автоматический повтор запрещён**, нужен reconciliation |
| `artifact_unavailable` | Ссылка есть, файл удалён/перемещён | Требуется обновление статуса ref, не фоновый поиск без согласия |

Для HTTP-представления удобно использовать [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html), добавляя `operation_id`, `run_ref`, `retryable`, `effect_status`, `correlation_id`. Для MCP отличать **ошибки JSON-RPC/protocol** от **ошибки исполнения tool**. Для A2A возвращать соответствующий **Task state** и детализацию конкретного Result/Artifact; сохранять исходную доменную причину внутри Strategy Box.

### 10.5. Idempotency и повтор — прежде всего про **эффект**, а не про HTTP

Рекомендован `invocation_key`, задаваемый вызывающей стороной либо узлом по согласованной политике. Его интерпретация:

```text
(scope of caller + logical operation + invocation_key)
  paired with canonical request digest and operation contract version
```

- Повтор с тем же ключом и тем же digest в окне дедупликации связывается с существующим logical run/receipt.
- Повтор с тем же ключом, но другим digest отклоняется как конфликт.
- Простой новый `request_id` после timeout **не делает операцию независимой** — caller обязан проверить состояние старого запуска.
- Наличие ключа **не гарантирует exactly once side effect**, если storage/backend не поддерживает соответствующую транзакционную семантику. Внешний источник может выполнить эффект, даже если ответ потерян.

Важно различать `safe_to_retry` (новая попытка допустима) и `same_result_reusable` (можно вернуть прежний результат). Для загрузки официальных файлов повтор может намеренно обновить snapshot; для вычисления с зафиксированными источниками результат потенциально переиспользуем; для очистки каталога повтор требует особенно строгого receipt/reconciliation.

### 10.6. Preflight и compiler: два разных этапа

**Preflight:** узел установлен, доступен, поддерживает версии/зависимости, Data root, сеть, память, ввод. **Plan compiler:** параметры и зависимости валидны, эффекты ограничены, достаточны rights и bindings, известны steps, сохранены versions/snapshots. Runtime может измениться между preflight и выполнением: для destructive/перезаписи нужен финальный recheck непосредственно перед эффектом (TOCTOU).

**Предлагаемый статус плана:** `draft → validated → admitted → running → terminal`, а policy/approval хранится отдельно с точной привязкой к `plan_digest`, principal, scope, version и истечению времени. Когда план изменился, ранее выданное подтверждение больше его не покрывает.

### 10.7. Concurrency и shared host

Искусственный лимит «один run на весь продукт» плохо подходит к нескольким чатам/внешним AI и крупным каскадам. Но необдуманная параллельность опасна при общих данных. Целевой executor должен поддерживать:

- bounded worker pool и budget per actor/node;
- resource claims на конкретные input/output namespaces;
- lock/lease для конфликтующих файловых эффектов;
- независимость нескольких read-only аналитических заданий;
- ограничение solver threads/memory и сетевого rate limiting;
- связь `run_id / job_id / attempt_id / step_id / artifact_id / source_ref`;
- backpressure и правдивый `queued/waiting` вместо фиктивного `running`.

Оптимизация/дедупликация одного источника между двумя запусками разрешается только при совместимых source/version/freshness, data scope, entitlement и result semantics. **Одинаковый URL или operation ID — недостаточное доказательство эквивалентности**.

---

## 11. Полномочия и угрозы при локальном, удалённом и агентском доступе

### 11.1. Минимальная модель доверия

**Две отдельные границы:**

1. **Code trust:** можно ли вообще загрузить данный подписанный/проверенный Python package/binding в рабочую среду?
2. **Action authority:** может ли конкретный user/agent выполнить конкретное действие над конкретными данными с выбранными параметрами?

Даже trusted installed code может быть опасен в неправильном контексте. `OperationSpec.dangerous` и model-visible descriptions — удобные hints, но не заменяют decision engine.

### 11.2. Что нельзя путать с Principal

- Никнейм в сценарном чате — **display identity**. Он помогает участникам команды понять, кто начал работу, но его недостаточно для удалённой авторизации.
- Идентификатор MCP client, имя user agent, поля Agent Card и self-reported AI identity — **не доказательство прав**, пока не связаны с выданным доверенным credential/делегированием.
- AppDock node/session identity — полезный контекст размещения; она не означает автоматическую власть над аналитическими операциями.
- Actor `AI` должен иметь **delegator + principal + granted scope + policy/expiry**, а не быть глобальным суперпользователем.

### 11.3. Матрица проверок на admission

| Контроль | Python напрямую | Внутренний managed application | Удалённый MCP | A2A |
|---|---|---|---|---|
| Кто запускает | Локальная Python OS-identity | Продуктовый principal | Authenticated MCP caller/delegation | Authenticated delegating agent/owner |
| Контроль доступа | ОС/права среды; пользователь отвечает за вызов | Application authority + storage | Server-side application authority | A2A boundary + host agent + application authority |
| Где проверять параметры | Domain API | App admission + domain | Transport schema + admission + domain | Agent message validation + admission каждого действия |
| Предупреждение об эффектах | Python caller | UI/approval | Confirmation/approval binding | Human approval через агентский канал, при необходимости |
| Кто видит результаты | Локальный процесс | Разрешённый app consumer | Scoped result refs | A2A task participants по policy |

**Безопасность нельзя «обойти через Colab»**, если Colab вызывает **host API**: это управляемый путь с authentication. Но обычный установленный `stratbox` на собственной машине остаётся самостоятельной библиотекой и не должен искусственно связываться с хостовой авторизацией.

### 11.4. Prompt injection через макроэкономические первоисточники

Для Strategy Box внешний контент — это файлы ЦБ/Росстата, HTML, PDF, Excel, пользовательские notes/логи. Эти данные могут содержать строки с инструкциями («отправь файл», «измени путь», «проигнорируй правила»). **Ни один источник данных не обладает command authority.** Агент может извлечь значения из таблицы, но команда исполняется только после проверки структурированного намерения, принадлежности к каталогу и policy.

OWASP отмечает для MCP-контуров угрозы связки инструментов, манипуляции контекстом и доверенных оболочек ([OWASP MCP Top 10](https://owasp.org/projects/mcp-top-10)). Практические меры: treat tool descriptions/results as untrusted across trust boundary, allowlist bindings, минимальные scopes, human approval для опасных эффектов, отдельные logs, safe previews и отсутствие универсального shell/Python execution. **Prompt injection тестировать целенаправленно в текстах внешних таблиц и HTML**, а не только в пользовательском чате.

### 11.5. Remote MCP HTTP: защита минимальна по сложности, но принципиальна

При фактическом запуске remote service обязательны:

- TLS и корректное удостоверение endpoint;
- access token для **именно этого resource server**, audience validation; отсутствие token passthrough к третьим сервисам;
- client/app identity, per-caller scope, expiry/revocation, server-side checking;
- сетевое ограничение доступа/CSRF-Origin protections там, где это относится к выбранному transport;
- ограничение частоты, bytes, CPU и memory, timeouts;
- user/data/artifact-scoped authorization;
- отказ от включённого remote listener по умолчанию, пока безопасность/config не доказаны.

Официальная [спецификация авторизации MCP `2026-07-28`](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) определяет рамку remote HTTP authorization; локальный stdio представляет другую модель владения процессом/credential и **не является поводом копировать HTTP OAuth в каждый import call**.

### 11.6. А2А-доверие и агентская ответственность

Remote A2A Task может выполнять несколько операций, передавать артефакты и обращаться за уточнениями. При каждом переходе:

```text
External agent credential
 → remote task owner / delegation
 → hosted agent identity
 → permitted domain capability subset
 → per-effect admission / approval
 → auditable local run
```

Если A2A агент попросил сделать то, чего его делегирование не разрешает, **действие отклоняется**, даже если агент на том же хосте имеет техническую возможность вызвать Python-код. Для вызовов с внешними эффектами сохранять distinct `requested_by`, `acting_as`, `approved_by`, `executed_by` и machine/audit IDs. Не публиковать пользователям все сырые логи только из-за общего чата.

---

## 12. Версионирование: шесть осей, которые нельзя сливать

### 12.1. Разделить договор и реализацию

| Ось | Пример | Для чего нужна |
|---|---|---|
| **Operation semantic ID** | `escrow.history.export` | Стабильная идентичность предметного use case |
| **Operation contract version** | `1.0.0` | Значение параметров, входов, выходов, ошибок, эффектов |
| **Implementation revision** | wheel version + commit/content digest | Точная версия исполняемого кода |
| **Capability catalog revision** | digest набора descriptors/bindings | Понимать, что увидел конкретный AI/client |
| **Source/registry/method version** | snapshot checksums, reference data, methodology IDs | Воспроизводимость банковского результата |
| **Protocol version** | MCP `2026-07-28`, A2A `1.0.0`, OpenAPI 3.x | Interoperability transport, не предметная методология |

Отдельно у `ExecutionPlan` должен быть content digest, фиксирующий действующие definition/bindings/policy/input snapshot. Можно использовать SemVer для **operation contract**, но нельзя из «патч-версия Python wheel» делать вывод о неизменности смысла аналитического показателя.

### 12.2. Примеры настоящего breaking change

- До изменения операция по умолчанию **только читала**, после стала перезаписывать существующий XLSX.
- `period=2026-06` ранее означал «конец месяца», после стал означать «месяц публикации».
- Отсутствующая банковская ячейка прежде маркировалась `missing`, после подменена `0`.
- Значение `amount` прежде выражалось в **тыс. рублей**, после — в **млн рублей**.
- Частичный набор источников прежде вызывал `failed`, после молча возвращается как `success`.
- Результатом вместо безопасного ArtifactRef стал публичный URL файлового каталога.

Эти изменения требуют **новой версии предметного контракта**, даже если аргументы Python-функции буквально не поменялись. Добавление optional metadata в output может быть совместимым, но для текущего проекта обратная совместимость не является самостоятельной целью: лучше менять контракт осознанно и пересобрать все consumers, чем тащить старые алиасы бесконечно.

### 12.3. Snapshot в момент запуска

При admission сохранять:

```text
requested operation ID + contract version
canonicalized request digest
selected binding + exact package identity
source/registry versions, если известны до старта
principal/delegation/policy revision
plan digest, affected workspace/artifact scopes
transport protocol/client metadata (для диагностики)
```

После завершения добавляются реальные source snapshots, used methodology, evidence refs, attempts, effect receipts, result/artifact digests. Если установка обновилась во время задания, старый `Run` должен завершаться согласованным binding либо честно получить interruption/unknown outcome. **Переключать executable revision посреди одного Job без фиксации — нарушение воспроизводимости.**

### 12.4. Версионный разрыв текущей сборки

[Windows `pyproject.toml`](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/pyproject.toml) и его [AppDock manifest](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json) всё ещё объявляют более старый core package `0.2.1`, тогда как исследование core 6 октября фиксировало `0.8.0`. Из этого следует **нужно заново проверить и согласовать package graph и runtime API**, но не следует утверждать, что фактическая установленная среда сегодня упала: package installation/E2E не выполнялись в рамках настоящего исследования. Формальное выпрямление версий требуется до публикации machine ABI.

---

## 13. Физическое размещение логических компонентов: сравнение

### 13.1. Три базовых варианта

| Вариант | Описание | Сильная сторона | Слабая сторона | Применимость |
|---|---|---|---|---|
| **A. Всё в `stratbox`** | core сам запускает MCP/A2A, хранит jobs и пользователей | Меньше пакетов в самом начале | Нарушает headless-library boundary, тащит UI/state/auth и transport deps в каждый Colab | **Отклонить** |
| **B. Всё в `stratbox-windows`** | Qt-приложение владеет каталогом, MCP и удалёнными jobs | Быстро вырастает из нынешнего кода | Windows-only/foreground/single coordinator; закрытие GUI убивает service; будущим Web/Android трудно переиспользовать | Только временный локальный прототип |
| **C. Core + нейтральный application authority + protocol adapters** | Core исполняет домен, прикладной уровень определяет admission/plans/runs, адаптеры публикуют HTTP/MCP/A2A | Один смысл, независимые устройства, прямой Python сохраняется | Нужно решить процессную жизнь/state/profiles | **Рекомендуемая целевая логика** |

**Вариант C — логическое разделение, а не требование немедленно создавать ещё один репозиторий/сервер/БД.** Для MVP один Python process может содержать `catalog + admission + local worker + MCP adapter`; в будущем headless-хост или shared package выделяется без копирования business logic. При прямом Colab-вызове его вообще не требуется запускать.

### 13.2. Что где должно жить по ответственности

| Объект | Логический owner | Почему |
|---|---|---|
| Domain `Request/Result`, алгоритм, единицы, evidence | `stratbox` | Независимость бизнес-семантики от UI/transport |
| `OperationDefinition` и общий каталог **доменных** операций | Domain/core contract boundary | Код и описание одной предметной функции развиваются вместе |
| UI-формы, перевод labels/basic/advanced, сценарная навигация | Shared application/presentation semantics | Не принадлежит Python core и не является MCP protocol |
| Binding установленной реализации, application readiness, permission/effect admission | Application authority, process location **OPEN** | Требует контекста узла/актора/хранилища |
| `Run/Job/Attempt`, lifecycle, cancellation/reconcile | Application execution authority | Одна история для GUI и машинных потребителей |
| HTTP/OpenAPI, MCP server | Transport adapters рядом с application authority | Не несут собственную бизнес-логику |
| A2A Agent Card/Task/agent orchestration | AI agent service/adapter, при наличии реального runtime | A2A про интеллект/делегирование, не про Python API |
| Установка пакетов, exact release identity, node activation | AppDock external contracts | Сверяем с реальными capabilities версии платформы |
| Desktop/Web/Android renderer | Их surface owners | Показывают разрешённые результаты/статусы |

### 13.3. AppDock: правильная точка соединения

AppDock является источником **deployment/run context**: world identity, package bindings, node/data roots, activation/health, если соответствующие свойства подтверждены выбранной версией. Он может в будущем предоставить transport gateway. Strategy Box при этом владеет **какие операции существуют, как они применяются, какие результаты значат успех и какие предметные эффекты допустимы**. Если AppDock реализует свою универсальную модель actions, это **вторая проекция** некоторых Strategy Box возможностей и операций самого AppDock; она не должна подменять весь domain catalog.

Критически важное отрицательное требование: удалённый AI не может «автоматически вызывать что угодно из мира AppDock» только по факту installed package. Нужно явное связывание внешнего действия с утверждённым `OperationDefinition`/Scenario, binding и scoped authority. Для неготовой платформенной функции — capability `unavailable`, а не фальшивый успех или silent fallback.

### 13.4. Когда материализовывать headless сервис

**Сигнал достаточности:** появляется реальный второй потребитель, которому нужна долговременная общая истина — remote MCP, Web, Android, двухпользовательский хост, одновременные фоновые jobs. До этого можно проектировать абстрактные ports/DTO и тестировать local service в памяти, сохраняя `stratbox-windows` как действующий UI. Если remote consumer пока только идея, запускать большой distributed stack преждевременно.

---

## 14. Приоритеты реализации: минимальный путь к рабочей универсальности

### Фаза 0 — фактические проверки и запреты (без расширения продукта)

- Зафиксировать конкретный core/Windows/AppDock commit, список public domain callables и текущие specs.
- Устранить противоречия существующих package versions, manifest/tests/docs; договориться о Python dependency policy.
- Определить ответственность за предметный `OperationDefinition`; убрать смешение навигационной spec и безопасной машинной schema.
- Зафиксировать запрет arbitrary Python/script/host-path execution в будущих external APIs.
- Не изменять API библиотечных функций только ради протокольных adapter DTO.

**Exit criterion:** core импортируется/тестируется отдельно от Qt/AppDock; известно, какие два пилотных operation contracts уже пригодны к machine exposure.

### Фаза 1 — один общий каталог и один локальный вызов

1. Выбрать `cbr.sources.list` и `cbr.files.collect` либо `escrow.history.build` как пилоты.
2. Для каждого создать explicit descriptor, input/result schema, effect classification, trusted handler binding.
3. Добавить `list/describe/invoke` *как логические функции*, in-process, без обязательного HTTP.
4. Применять общий request validator и domain request adapter; результат — typed summary с `provenance/warnings`.
5. Покрыть contract tests: Python direct call vs catalog adapter дают эквивалентную предметную семантику и одинаковые source failures.

**Exit criterion:** одна предметная реализация вызывается обычным Python и приложением без копирования бизнес-алгоритма; некорректные input/unknown operation отклоняются управляемо.

### Фаза 2 — local MCP (самый дешёвый проверочный внешний AI-путь)

1. Публиковать только `list/describe` и одну безопасную read-only аналитическую операцию.
2. Стандартная версия MCP, `stdio`/in-process transport; отдельный клиентский interop test через официальный SDK.
3. Затем добавить controlled artifact creation с temporary/staged output и receipt.
4. Обязательные negative tests: unavailable workspace, permission denial, tool poisoning, malformed input, interrupted write.

**Exit criterion:** реальный внешний MCP client вызывает единственный core-operation путь, получает структурированный результат и не может задать произвольный handler/path. Этот этап реализуем даже без готового AppDock remote transport.

### Фаза 3 — host service и remote MCP/HTTP

1. Принять минимальное решение по lifetime: headless process, state owner, node binding, restart/shutdown policy.
2. Реализовать `submit/get/cancel/describe` через один Job/Run service и bounded worker.
3. Публиковать host API с реальными auth/scopes, TLS, workspace refs, artifact access и audit.
4. MCP становится тонким transport adapter к service, а HTTP/OpenAPI — отдельным consumer contract.
5. Проверить инструментами AppDock наличие совместимого host/remote способа запуска; в случае отсутствия — явно оформить внешний blocker, не имитировать gateway.

**Exit criterion:** один запуск доступен для мониторинга из двух клиентов, закрытие отдельной UI surface не меняет правду о запуске, ошибка host возвращается как `unavailable/unknown` по типу отказа.

### Фаза 4 — agent runtime / A2A / machine schemes

1. Нужен подтверждённый реальный AI actor и отдельный runtime/control policy.
2. Определить Agent Skills/Task translation, бюджеты запросов, контекст работы, artifact access и intervention/approval.
3. Обеспечить A2A compatibility по выбранной версии, auth и streaming/polling.
4. Машинные схемы вводить только там, где есть конкретный потребитель typed composition, проверяемые pre/postconditions и plan compiler.

**Exit criterion:** A2A агент способен исполнить агрегированную аналитическую задачу из нескольких **разрешённых** операций, возвращает evidence/results, при недостатке полномочий останавливается и запрашивает разрешённое подтверждение.

### 14.1. Почему именно такой порядок

Он даёт проверяемый результат уже на первых двух фазах, не делает сетевую авторизацию условием использования core, не привязывает Business API к ещё незрелому AppDock gateway и откладывает дорогостоящую A2A-агентскую семантику до появления настоящего агента. Архитектура остаётся расширяемой: будущие Web/Android вызывают тот же application API, что и remote MCP, но с собственным client transport/UX.

---

## 15. Проверочные сценарии и тесты допуска

### 15.1. Контрактные тесты уровня Operation

| Тест | Стимул | Ожидаемая инварианта |
|---|---|---|
| T01 | `cbr.files.collect` импортирован в чистом headless Python | `stratbox-windows`, Qt и AppDock не требуются для core API |
| T02 | Machine call с extra field, неверным period/enum | Отклонение до обращения к внешнему источнику |
| T03 | Два вызова одного домена Python vs machine adapter с одинаковыми снимками | Эквивалентная предметная семантика, корректная нормализация result |
| T04 | В каталоге есть helper `normalize_path` | Helper сам по себе **не** появляется как AI tool |
| T05 | Пользователь прислал `handler='os.system:...'` | Поле отклонено/игнорируется; binding серверный |
| T06 | Запрошена запись за пределами `workspace_id/relative_path` | Отказ, включая `..`, absolute path и symlink escape |
| T07 | Операция публикует DataFrame на десятки тысяч строк | Возвращаются `DatasetRef + summary + page/preview`, а не весь объект в LLM content |
| T08 | Официальный источник отсутствует, другая публикация равна 0 | Различимые statuses и provenance |
| T09 | Нет optional solver/backend | `binding_unavailable` или `resource_unavailable`, без тихой подмены метода |
| T10 | Совпадение operation ID при разных contract versions | Catalog resolver не смешивает semantic signatures |

### 15.2. Исполнение, эффекты и безопасность

| Тест | Стимул | Ожидаемая инварианта |
|---|---|---|
| T11 | MCP `tools/list` от двух principals с разными grants | Возвращается разрешённая, детерминированно упорядоченная projection |
| T12 | `tools/call` для tool из устаревшего каталога | Повторная authorization/availability; запрет при потере разрешения |
| T13 | Network timeout после начала записи/удаления | `outcome_unknown`, отсутствие слепого auto-retry |
| T14 | Повтор того же invocation key и digest | Привязка к тому же logical run при действующей dedup policy |
| T15 | Тот же invocation key, иной digest | Конфликт, не скрытый второй эффект |
| T16 | Запрос отмены после irreversible commit | Не выдаётся ложный `cancelled_without_effect`; сохраняется receipt |
| T17 | Частично сформированный XLSX, crash до publish | Artifact недоступен как completed; staging может быть очищен отдельно |
| T18 | Агенту запрещён overwrite, описание tool «можно всё» | Серверный policy блокирует эффект |
| T19 | В PDF/XLSX найден текст, который просит вызвать иной tool | Контент трактуется как данные, командное полномочие не повышается |
| T20 | Два одновременных независимых read-only runs | Выполнение допустимо в рамках budgets; общий mutable output защищён |
| T21 | AppDock изменил activation schema | Contract failure диагностирован; машинная схема не подменяет платформенную |
| T22 | Core обновился во время длительного run | Binding revision pinned либо run явно прерван/перенесён по документированному правилу |
| T23 | A2A task потребовал input/auth | Отдельное agent/task состояние, underlying run не ошибочно объявлен успешным |
| T24 | Закрытие Windows GUI во время remote host Job | Server authority сохраняет status/record по принятой lifecycle policy |
| T25 | Клиент MCP 2025-11 и сервер MCP 2026-07 | Поддержанная compatibility ветка или чёткий `unsupported_version`; отсутствие ложного успеха |

### 15.3. Наблюдаемые критерии полезности AI-каталога

Чтобы сравнить *direct-per-operation tools* против *search/describe/submit*, взять 20–40 воспроизводимых задач на реальные данные (например «получить исходники ЦБ», «собрать эскроу за историю», «получить статус SORS», «предложить план очистки без применения»). Для каждого варианта измерить:

- **tool selection accuracy** и error-free argument rate;
- число лишних вызовов `list/describe` и средний объём метаданных/tokens;
- end-to-end latency до валидного аналитического результата;
- долю ошибочных destructive/unauthorized attempts;
- полноту evidence/provenance;
- размер ответов и нагрузку на host;
- recovery rate после контролируемого timeout;
- долю случаев, где модель выбрала неподходящий метод или пропустила важные ограничения.

Набор задач и критерии оценки должны быть **реплицируемыми**, с фиксированными source snapshots и catalog revision. Не делать продуктовый вывод только на основе демонстрации одной модели и двух красивых prompts.

---

## 16. Противоречия и остающиеся технические развилки

| ID | Вопрос / конфликт | Позиция исследования | Статус |
|---|---|---|---|
| Q06-01 | Семантический каталог живёт в core или общем application? | Domain definitions/typed contracts ближе к core; availability/binding/auth — application. Физический package можно выбрать позже | **SUPPORTED / deployment OPEN** |
| Q06-02 | Нужны ли всем функциям стабильные IDs и JSON schemas? | Нет; только курируемым внешним use cases и композициям | **PROPOSED** |
| Q06-03 | Machine scheme = Scenario? | Отдельные смысловые роли, конкретная модель 1:1/1:N требует реального потребителя | **OPEN** |
| Q06-04 | Открывать `run_operation` generic или отдельные named tools? | Тонкий универсальный invoke + targeted domain tools как две projection; проверять на AI evaluation | **PROPOSED** |
| Q06-05 | Что является authority для длительных удалённых Run/Job? | Shared application authority; процесс/СУБД не выбирать до operational profile | **SUPPORTED / OPEN** |
| Q06-06 | Кому принадлежат права и подтверждения? | Server-side application admission at effect boundary | **PROPOSED**, нужна Product Policy |
| Q06-07 | Может ли AppDock предоставить MCP/A2A endpoint уже сейчас? | Прямых доказательств текущей готовности для Strategy Box нет; интеграцию вести только по проверенному контракту | **EXTERNAL DEPENDENCY** |
| Q06-08 | Какие MCP protocol versions и tasks mode поддерживать? | Явная матрица и pinned SDK; актуальная спецификация 2026-07-28 отличается от 2025-11-25 | **OPEN** |
| Q06-09 | Где размещать embedded AI? | В application/service, отделённо от Qt; физическое размещение зависит от профиля | **PROPOSED / OPEN** |
| Q06-10 | Нужен ли A2A с самого начала? | Нет, только после появления agent runtime и случая делегирования | **PROPOSED** |
| Q06-11 | Как связывать файлы/таблицы через машины? | Typed Workspace/Source/Dataset/ArtifactRefs, scoped retrieval, large data out-of-band | **PROPOSED** |
| Q06-12 | Нужна ли собственная registry database? | Сначала программный каталог+materialized snapshots, storage только под реальные состояния и consumers | **PROPOSED** |
| Q06-13 | Как обновлять экосистему без обратной совместимости? | Разделять semantic contract и exact implementation; при breaking change пересобирать consumers | **PROPOSED** |
| Q06-14 | Может ли прямой Python быть полностью эквивалентен remote host? | Совпадает **domain semantics**, но управляемость, права, окружение и гарантия эффектов различаются | **SUPPORTED** |
| Q06-15 | Можно ли считать AI результатом любой `OperationResult(ok=True)`? | Нет; методологический результат, файл, публикация, Task и human acceptance — отдельные события | **SUPPORTED** |

### 16.1. Противоречие «максимально универсально» vs богатая аналитическая методология

**Неудачный путь:** все доменные операции обязаны принимать `dict[str, Any]`, возвращать `dict[str, Any]`, иметь поля каждого возможного источника/формата и автоматический путь `functools` → MCP. Он резко упрощает первый прототип, но теряет type-safety, доказательность и тестируемость.  
**Предпочтительный путь:** внешняя boundary ограничена сериализуемыми типами, внутренние контракты сохраняют нужные доменные различия. Явные input/output adapters остаются достаточно короткими и проверяемыми.

### 16.2. Противоречие «универсальный AI» vs безопасность

**Неудачный путь:** открыть все инструменты и попросить LLM не выполнять опасные команды.  
**Предпочтительный путь:** агент видит только разрешённую context-specific projection, при фактическом вызове происходит повторный admission и на уровне effects действуют confirm/deny/receipt.

### 16.3. Противоречие «всё организует AppDock» vs независимость Strategy Box

**Неудачный путь:** переносить доменные operation IDs, методологии, входы и Job outcomes в AppDock manifest, пока его AI gateway ещё меняется.  
**Предпочтительный путь:** AppDock предоставляет подтверждённые runtime/node/transport capabilities; Strategy Box располагает самостоятельным каталогом и адаптером, способным работать локально. Будущий gateway только связывает границы.

### 16.4. Противоречие «единая схема операций» vs разнородность длительности

**Неудачный путь:** `tools/call` всегда должен дождаться завершения SORS и вернуть DataFrame; либо всё обязано немедленно становиться background job.  
**Предпочтительный путь:** один предметный вызов с двумя допустимыми способами исполнения: bounded sync для быстрых read-only задач и managed job для длительных/эффектных. Смена режима не меняет domain definition, но протокольное представление результата явно отражает `accepted` и `pending`.

---

## 17. Конечная архитектурная рекомендация

**Рекомендуется принять для дальнейшей проектной проработки следующую ограниченную систему принципов:**

1. **Один исполняемый предметный core:** любые банковские/макроэкономические расчёты остаются в `stratbox`; Colab/Jupyter имеют прямой Python API.
2. **Каталог отобранных операций:** стабильные domain IDs, typed semantic Request/Result, effect profiles, applicability, owner и versions. Не регистрировать все helpers.
3. **Тонкие machine bindings:** внешнее JSON/JSON Schema представление переводится в реальные доменные типы, а результат — в summary и ссылки на таблицы/артефакты, без потери evidence.
4. **Независимый прикладной допуск:** availability, principal/delegation, policy, подтверждения, binding и план проверяются в момент исполнения; сериализованный tools/list не даёт права исполнения.
5. **Одна логическая исполнительная система:** Run/Job/Attempt/EffectReceipt не принадлежат MCP, A2A или Qt. Синхронный API и длительные задачи — две формы обращения к одному executor.
6. **MCP как AI tool adapter**, локально и по сети; конкретная версия спецификации и Tasks extension фиксируются интероперабельностными тестами.
7. **A2A только для реальной агентской роли**, способной принимать цель, вести Task и использовать catalog; не применять A2A как дорогой псевдоним `run_python`.
8. **AppDock — внешняя интеграция**, владельцем аналитической семантики остаётся Strategy Box. Сервис должен иметь чистый вариант работы, не требующий ещё неготового remote gateway.
9. **Семантическое единство Windows/Web/Android**, с собственными renderer adapters и общей идентичностью/историей запусков при host-профиле.
10. **Малый проверяемый MVP** — два доменных operation contracts, `list/describe/invoke`, local MCP, потом host API и только затем A2A.

Так достигается требуемая разработчиком вариативность без обязанности строить прямо сейчас отдельную распределённую платформу, универсальный движок всех схем или многоуровневую систему метаданных, большая часть которой не будет иметь потребителя.

---

## 18. Источники и проверяемые основания

### 18.1. Прямые владельцы — текущие репозитории

- Core cold entry: [README](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/README.md), [AGENTS](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/AGENTS.md), [_mw/AGENTS](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/AGENTS.md).
- Core domain API: [CBR collector](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/cbr_file_collector/operations.py), [escrow](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/escrow/operations.py), [FRG](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/frg/api.py), [SORS](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/cbr_sors_restoration/operations.py).
- Windows application: [catalog model](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/catalog/models.py), [catalog registry](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/catalog/registry.py), [operation runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/execution/runner.py), [scenario model](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/models.py), [scenario runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py), [manifest](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json).
- Current docs and conditional target: [publication status](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/docs/README.md), [responsibility allocation](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/docs/architecture/responsibility-allocation.md), [execution/effects](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/docs/how/execution/execution-and-effects.md).
- External platform: [AppDock overview](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/overview.md), [manifest authority](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/manifest_authority.md), [packages/activation](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/source_composition_and_surfaces.md).

### 18.2. Накопленный исследовательский корпус Strategy Box

- [02: Команды, сценарии, каскады](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_commands_scenarios_cascades_research_2026-10-07.md).
- [02: Автоматизация и AI](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/02-base-study/strategy_box_automation_ai_research_2026-10-06.md).
- [02: Готовность бизнес-кода к машинным схемам](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_protos_business_code_readiness_research_2026-10-07.md).
- [03: Canonical Semantic Model](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_02_canonical_semantic_model_2026-10-08.md).
- [03: Work → Execution](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_04_work_to_execution_consolidated_research_2026-10-09.md).
- [03: Capability, Extension, Automation](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_06_capability_extension_automation_consolidated_research_2026-10-09.md).
- [03: Whole System Target Architecture](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_09_whole_system_target_architecture_2026-10-09.md).

### 18.3. Внешние стандарты и технические первоисточники

1. **MCP, версия 2026-07-28:** [релиз](https://blog.modelcontextprotocol.io/posts/2026-07-28/), [server tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools), [authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization), [Tasks extension](https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks); [официальный Python SDK 2.x](https://py.sdk.modelcontextprotocol.io/).
2. **Agent2Agent (A2A):** [Specification 1.0.0](https://a2a-protocol.org/v1.0.0/specification/) — Agent Card, Message/Task/Artifact, асинхронность, interrupted states.
3. **JSON Schema:** [Draft 2020-12](https://json-schema.org/draft/2020-12/) — машинные структурные контракты.
4. **OpenAPI:** [текущие опубликованные версии](https://spec.openapis.org/oas/latest.html) — HTTP API description, operationId, request/response, security.
5. **RFC 9457:** [Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html) — типизированные ошибки на HTTP-boundary.
6. **OWASP:** [MCP Top 10](https://owasp.org/projects/mcp-top-10) — угрозы доверия и исполнения при AI tooling.

### 18.4. Научные исследования и предел их применения

- Schick et al., **Toolformer: Language Models Can Teach Themselves to Use Tools**, NeurIPS 2023 — выбор API и аргументов, [публикация](https://papers.neurips.cc/paper_files/paper/2023/hash/d842425e4bf79ba039352da0f658a906-Abstract-Conference.html).
- Yao et al., **ReAct: Synergizing Reasoning and Acting in Language Models**, ICLR 2023 — циклическое использование инструментов и наблюдений, [публикация](https://mlanthology.org/iclr/2023/yao2023iclr-react/).
- Du et al., **AnyTool: Self-Reflective, Hierarchical Agents for Large-Scale API Calls**, ICML 2024 — иерархическое обнаружение/выбор инструментов, [публикация](https://proceedings.mlr.press/v235/du24h.html).
- Qin et al., **ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs**, ICLR 2024 — API retrieval и масштаб, [публикация](https://proceedings.iclr.cc/paper_files/paper/2024/hash/28e50ee5b72e90b50e7196fde8ea260e-Abstract-Conference.html).

Исследования подтверждают значимость понятных инструментов, контекстного выбора и наблюдения результатов, **но не являются свидетельством** безопасности, фактической производительности или пригодности какой-либо модели для конкретной системы банковских данных Strategy Box. Это проверяется собственным набором кейсов §15.

---

## 19. Итоговые решения для следующего продуктового обсуждения

**Можно принять как рабочие архитектурные ограничения:** самостоятельность Python-core; curated machine catalog, независимый от протокола; explicit effects и refs; авторизация на стороне выполняющего узла; отсутствие произвольного Python/shell в AI tools; единая исполнительная правда и честный `outcome_unknown`; MCP как Tool adapter, A2A как Agent adapter.

**Нужно проверить коротким пилотом:** JSON Schema projection двух доменных операций; выбор прямых tools или hierarchical search; local MCP версии `2026-07-28` с реальным клиентом; semantics of artifacts/partial errors; контрактное преобразование Python Request/Result; параллельные задачи на локальном executor.

**Нельзя объявлять решённым до дополнительного Product Decision/проверки AppDock:** физический owner headless service, долговременное хранилище Job/Artifact, remote identity/auth, схемы approval/delegation, interop policy MCP 2025/2026, A2A agent deployment и формальное соотношение Machine Scheme с Scenario/Cascade.

**Главный принцип темы 06:** *общими должны быть предметный смысл операции, её входы, эффекты и проверяемый результат; транспорт, агентское рассуждение, пользовательское представление и размещение исполнения остаются разными адаптируемыми слоями.*
