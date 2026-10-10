# 10. Границы ответственности и интеграционные контракты Strategy Box

**Дата:** 10 октября 2026 года  
**Статус:** самостоятельное исследование / архитектурный кандидат, **не Product Decision и не описание готового host-сервиса**.  
**Предмет:** ответственность аналитического ядра, application authority, Windows и будущих поверхностей, внешнего AppDock; локальный и хостовый режимы; состояния, разрешения, эффекты и контракты.  
**Ограничения работы:** исходный код и репозитории не изменялись; закрытые реализации и их детали в документ не переносились. Выводы относятся к изученным исходникам и документам, а не к подтверждённому развертыванию на устройстве.

## 0. Короткий результат

1. **Главная граница уже правильна:** `stratbox` является самостоятельной Python-библиотекой предметных операций. Он не должен становиться ни оконным приложением, ни сервером авторизации, ни планировщиком пользовательских задач. Прямой вызов core из Colab/Jupyter/Python остаётся полноценным способом его использования.
2. **Главное незавершённое распределение — application authority.** Текущий `stratbox-windows` владеет локальными сценариями, кейсами, событиями, логами и историей. Для общего хостового режима требуется один авторитетный владелец жизненного цикла этих объектов, действующий независимо от окон, вкладок и устройств. Логическая ответственность обоснована уже сейчас; отдельный процесс и репозиторий ещё требуют продуктового решения.
3. **AppDock — внешний владелец поставки, managed Node, запуска, среды, platform session, health и поддерживаемых внешних контрактов.** Он не должен решать, какой банковский показатель посчитан корректно, кто завершил аналитический Job, какие сообщения принадлежат рабочему чату Strategy Box и опубликован ли конкретный аналитический результат. В то же время Strategy Box не должен дублировать установку и контроль среды AppDock.
4. **Локальный и хостовый режимы различаются местом authority, а не семантикой интерфейса.** Если всё исполняется на устройстве, там находятся значимые данные и состояние. Если вычисляет хост, общий журнал чатов/кейсов, задания, подтверждения эффектов и рабочие данные находятся под authority хоста. На клиенте допустимы персональные настройки, курсоры просмотра, безопасные кэши и временные отображения.
5. **«Все интерфейсы общие» следует понимать как общую предметную модель, команды, статусы и правила прав.** Код Qt-виджетов, web-компонентов, Android-навигации, локального выбора файлов и OS-интеграции обязан различаться. Их насильственное объединение увеличит связность.
6. **Три подтверждения различны:** выполнение математического расчёта; фактическое совершение внешнего эффекта (запись/удаление/отправка); доведение результата до видимости пользователя. Успешный `return` Python-функции не доказывает две последующие ступени.
7. **Права проверяет исполнительный владелец непосредственно перед эффектом.** Никнейм — удобная видимая подпись человека в знакомой команде, но не доказательство полномочий удалённого клиента или агента.
8. **Минимальное решение:** один набор семантических application contracts; в локальном режиме — in-process реализация; в хостовом — единственный headless authority с теми же правилами, доступный по разрешённому API. Не вводить обязательные брокер, микросервисы, event sourcing и тяжёлый workflow engine до появления доказанного сценария.
9. **Наблюдаемая совместимость ещё не гарантирована.** Текущий manifest Windows объявляет Connector `4.0` и core package requirement `0.2.1`; README и один smoke-тест описывают старые элементы, а актуальный `stratbox` имеет версию `0.8.0`. Это отдельный интеграционный дефект, а не основание копировать версию пакета в доменную модель.
10. **Дальнейший Product Decision должен начинаться с профилей эксплуатации и уровня гарантий**, а не с выбора SQL-сервера, очереди, транспорта, протокола ИИ или имени будущего репозитория.

---

## 1. Постановка и нормативная сила исходных материалов

### 1.1. Что требует тема № 10

Исходная постановка из предоставленного `Strategy_Box_Research_Topics(2).docx`, раздел **«10. Границы ответственности и интеграционные контракты»**, требует:

- согласовать ответственность аналитического core, общего прикладного слоя, Windows-клиента, будущих интерфейсов и внешней платформы;
- отделить действующие подтверждённые контракты от будущих возможностей;
- сохранить автономность core и независимость реализации платформы;
- ответить, кто владеет состоянием выполнения, авторизацией действия и окончательным подтверждением внешнего эффекта;
- определить, какие интерфейсы общие, а какие зависят от deployment-профиля и версии AppDock.

**Дословно существенный замысел разработчика, без расширительного толкования:** если Strategy Box полностью работает на пользовательском компьютере, всё сохраняется там; если вычисление выполняет хост, **общие данные хранятся на хосте**, а персональные каталоги подключаемых клиентов пригодны для второстепенных данных, не влияющих на системную истину Strategy Box. Пользователю нужно прежде всего понимать, **чьи команды и где исполняются**. Фраза про «общие интерфейсы» названа самим разработчиком приблизительной.

Эти положения принимаются как **продуктовый ориентир исследовательской постановки**. Конкретный протокол, долговечность журнала, авторизация, консистентность и физическое размещение остаются открытыми. Нельзя автоматически превращать пожелание в реализованный контракт.

### 1.2. Межтематический контекст из того же DOCX

Уточнения в других постановках относятся к теме 10 лишь как **ограничения границ**, а не как отдельные исследования:

- № 1 и № 6: предметные команды/сценарии должны вызываться из внешней Python-среды; потенциально — через машинные и агентские интерфейсы. Поэтому нельзя связывать доменный API с Windows-процессом.
- № 2: автор предполагает простую политику завершения процесса при прерывании и явную индикацию незавершённого; фоновая работа через tray/AppDock ещё не утверждена. Следовательно, «durable resumed job» не является действующим обязательством.
- № 4: сформированные файлы живут в пространстве данных; при ручном переносе/удалении владелец проекта предпочитает простую отметку «файл не найден», а не дорогостоящую процедуру восстановления соответствия. Глобальный immutable artifact vault был бы избыточен.
- № 5 и № 8: участники общей команды видят общие чаты, никнеймы и безопасные сведения о проблемах; параллельные команды в разных чатах принципиально допустимы. Детальные физические логи локализованы на соответствующем узле/у исполнителя.
- № 7: Web и Android востребованы; мобильный профиль прежде всего подключается к хосту; сборка и роль узла должны учитывать AppDock, который ещё развивается. Общая смысловая составляющая важнее одинаковой верстки.

**Конфликт, который следует устранить решением:** простое прерывание локального исполнения при закрытии процесса и долговременный hosted run — два **разных эксплуатационных профиля**. Их удобно объединить контрактами идентичности/статуса, но нельзя заявить одну и ту же гарантию восстановления.

### 1.3. Иерархия достоверности

| Маркер | Значение | Что может утверждать этот документ |
|---|---|---|
| `CURRENT / DIRECT` | Проверено в исходнике/manifest актуального implementation owner | Текущий видимой кодом контракт или ограничение |
| `CURRENT / DOCUMENTED` | Записано в действующем техническом документе owner | Декларируемая семантика; полнота реализации требует сверки |
| `RESEARCH / SUPPORTED` | Обоснованный вывод из нескольких фактов и внешних практик | Рекомендация с аргументами, а не принятое требование |
| `TARGET / CANDIDATE` | Целевая архитектурная гипотеза | Возможный будущий контракт после Product Decision |
| `CONDITIONAL / EXTERNAL` | Зависит от будущего профиля, версии платформы или поставки | Никакого обещания готовности |
| `OPEN` | Отсутствует решение либо достаточно надёжное evidence | Явная развилка или эксперимент |

Главный вход по первичным owners: [`stratbox/README.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/README.md), [`stratbox/AGENTS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/AGENTS.md), [`stratbox/_mw/AGENTS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/AGENTS.md). Эти документы подтверждают core-only назначение, единый Research workspace и раздельные владельцы исходного кода. Исторические 01, baseline 02 и synthesis 03 имеют статус Research, а новые [`docs/`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/README.md) — частично опубликованную, ещё консолидируемую Knowledge Product с отдельно отмеченными кандидатами.

---

## 2. Что реально есть сегодня: срез по владельцам

### 2.1. `stratbox`: библиотечная и инфраструктурная authority

**CURRENT / DIRECT.** Корневой пакет `stratbox==0.8.0` (`pyproject.toml` на момент проверки) содержит `base`, `common`, `registries`, `text`, `macrobanks`. Предметные подсистемы выполняют загрузку статистики, нормализацию, анализ, формирование Excel и специализированное восстановление показателей. Код библиотеки импортируется независимо от графического клиента.

Проверяемые владельцы:

- [`src/stratbox/base/filestore/base.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/filestore/base.py) — `FileStore` Protocol: `read/write`, `stat`, `listdir`, `rename`, `remove`, `walk`, `copy` и др. **Это интерфейс транспорта, а не транзакция, не каталог опубликованных пользовательских артефактов и не ACL-сервис.**
- [`src/stratbox/base/runtime.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/runtime.py) — process-local разрешение нейтральных инфраструктурных провайдеров и `get_filestore()/get_secrets()`. **Это не общий Strategy Box Job runtime.**
- [`src/stratbox/base/net/http.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/net/http.py) — получение байтов внешнего источника с `DownloadResult`, повторами/ошибками. HTTP-загрузка не решает долговечность Work/Run.
- [`pyproject.toml`](https://github.com/ForestTiger-GH/stratbox/blob/main/pyproject.toml) — текущая версия/зависимости пакета.

**Доказанный принцип:** core может вычислять и сохранять данные при явной передаче среды исполнения. **Открытый пробел:** единого канонического `Operation` registry, envelope всех результатов, общесистемного `Run/Job` и проверки actor-level прав пока нет. Это не дефект самого headless core: перечисленное относится к другому уровню ответственности.

### 2.2. `stratbox-windows`: действующий application/surface

**CURRENT / DIRECT.** Репозиторий реализует desktop-приложение, но содержит больше одного UI:

- `application/`: операции, сценарии, последовательный runner, cases, events, logs, artifacts, assignments, presence и scaffold фоновых процессов;
- `runtime/`: `AppContext`, пути, состояние пользователя, AppDock session projection, конфигурация и bootstrap;
- `adapters/appdock/`: импорт platform activation/session contracts;
- `presentation/common/`: семантическая проекция сценарного чата;
- `presentation/qt_desktop/`: реальное Qt-представление и `QThread` coordinator.

Фактические исходники: [`scenario runner`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/scenarios/runner.py), [`runtime/context.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/context.py), [`runtime/bootstrap.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/bootstrap.py), [`history/persistence.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/history/persistence.py), [`docs/architecture.md`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/docs/architecture.md).

Проверенные ограничения:

1. Composite scenarios выполняются шаг за шагом; coordinator использует Qt worker и допускает **один активный сценарий за раз**. Значит, многопоточность нескольких чатов пока отсутствует, несмотря на требование разработчика.
2. Персистентная «история» — пять JSON-срезов. Запись по отдельности, без общей транзакции, явного locking, schema upgrade и строгого отказа при повреждении. Это **локальная projection**, а не общее хранилище истины команды.
3. BackgroundProcessStore умеет показать и поменять локальные статусы, но не имеет планировщика/диспетчера. Аналогично presence/assignments пока преимущественно локальные.
4. `runtime/bootstrap.py` импортирует `presentation.qt_desktop.scenario_coordinator` — реальное нарушение цели «application независимо от toolkit».
5. Действуют несколько операций/сценариев, а не универсальный remote Job API. Отсутствие общей host authority не следует компенсировать имитацией многопользовательских статусов на уровне UI.

Соответствующий проверенный snapshot подробно разобран в [`docs/current-how/windows-application.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/current-how/windows-application.md). Там прямо отмечено, что анализ **статический**, а не испытание GUI и сетевой установки.

### 2.3. Конкретный текущий AppDock Connector

**CURRENT / DIRECT:** [`stratbox-windows/appdock/manifest.json`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/appdock/manifest.json) объявляет:

| Поле | Значение в checked-in файле | Значение для исследования |
|---|---|---|
| `contract_version` | `4.0` | Версия **Connector manifest**, не всего AppDock |
| `identity.world_id` | `stratbox` | Identity устанавливаемого мира, не аналитического Run |
| `world_definition.data_profile` | `data_enabled` | Данные разрешены в поставке, не определена общая DB |
| `default_surface_id` | `desktop` | Одна текущая surface |
| `activation.contract_version` | `4.0` | Версия декларации surface activation |
| `activation.entrypoint.kind` | `python_module` | Управляемый запуск Python entry |
| `activation.locality` | `local` | **Host/remote execution текущим manifest не заявлены** |
| `activation.launch_mode` | `foreground` | Не daemon/tray/service |
| `platform_constraints.node_platforms` | `windows` | Только Windows-поставка |
| `package_declarations` | core `0.2.1`, desktop `0.1.0` | Отличается от нынешней версии core `0.8.0` |
| `runtime_bindings` | core → desktop, один Python environment | Подтверждённая package/runtime композиция |
| `supports_artifacts`, `supports_presence` | `true` | Декларируемая surface-capability, **не proof общей синхронизации** |

**Наблюдаемое рассогласование:** README Windows называет Connector `3.0`, а checked-in manifest — `4.0`. Отдельный smoke-тест ожидает `3.0` и старое поле `package_identity` вместо `package_requirement`. Это проверяемый drift конфигурации, документации и acceptance-теста. Пара `0.2.1` в manifest ↔ `0.8.0` в core — дополнительный release-интеграционный риск; сам по себе не доказывает немедленный сбой загрузки без исполнения установки.

В AppDock интеграционном слое версии имеют **разные семейства**: Connector manifest, surface activation, Activation Context, session state и Strategy Box runtime projection. Нельзя принимать их за одну общую «версию 4».

### 2.4. AppDock: четыре platform truth и предел обязательств

**CURRENT / DOCUMENTED.** AppDock архитектурно различает `SourceCatalog` (источники), `WorldDefinition` (конфигурационная истина), `ReleaseRecord/TransparencyManifest` (поставка) и `RuntimeTruth` (фактическая установленная среда). `DeploymentPlan` материализует layout, а `ActivationPlan` создаёт surface execution context. Ссылки: [`architecture/overview.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/overview.md), [`activation_and_launch.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/activation_and_launch.md), [`manifest_authority.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/manifest_authority.md), [`root_model.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/root_model.md).

AppDock различает install/system/Node/runtime/package/Data roots. Его managed Node — execution/storage/publication context платформенного мира; **не тождественен** исполнению предметного сценария Strategy Box. `system_root` — техническое физическое размещение; `Data root` — прикладные данные. Конкретные пути производны от deployment, не являются переносимым public API.

**Maturity gate.** В актуальном [`AppDock Observability implementation status`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/observability/IMPLEMENTATION_STATUS.md) milestone 5E source complete, но Windows certification pending; позднейшие bootstrap sink, полноценные incidents, MCP/A2A и иные звенья прямо отложены. В `TARGET_MODEL.md` сформулированы общие правила регистрации проблемы и безопасной диагностики — **это цель, а не доказательство готового Strategy Box remote adapter**. Не следует закладывать production-протокол на основании презентационного описания AppDock или будущего capabilities list.

### 2.5. Что нового дают материалы 01–03 и `docs/`

- [`01-old-notes/README.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/01-old-notes/README.md) определяет историю как материал происхождения, а не current specification.
- [`02-base-study/README.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/README.md) закрепляет прямых implementation owners.
- Исследование [`web/self-hosted`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md) аргументирует вариант `stratbox-host`, но это **Research Result**, а не созданный сервис.
- [`03 Work→Execution`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_04_work_to_execution_consolidated_research_2026-10-09.md) и [`03 Whole-System Target Architecture`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_09_whole_system_target_architecture_2026-10-09.md) сходятся в разделении domain/application/platform и признают unresolved physical topology. Их выводы **зависимы от одних и тех же первичных исходников** и не считаются независимыми тестовыми подтверждениями.
- Актуальная [`docs/architecture/responsibility-allocation.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/architecture/responsibility-allocation.md) уже содержит статус `PA-SB-2026-10-09-CANDIDATE-1`; наша работа проверяет, конкретизирует и оспаривает границы, а не объявляет этот кандидат принятым стандартом.

---

## 3. Правило декомпозиции: «кто знает истину» сильнее «в каком репозитории лежит файл»

Исследование Д. Парнаса (1972) рекомендует делить систему по решениям и изменениям, которые должны быть скрыты за интерфейсом, вместо группировки по этапам выполнения. Архитектура портов и адаптеров А. Кокберна (2005) позволяет вызывать прикладные операции через GUI, API, tests или batch без обратной зависимости ядра от канала вызова [E1, E2].

Для Strategy Box полезно одновременно различать **пять независимых осей**:

1. **Semantic owner:** кто определяет правильное значение результата и правила переходов (`stratbox` — банковские показатели; application — пользовательский запуск).
2. **Authoritative state owner:** кто имеет право записать окончательный state (`Case/Job` — application authority; `RuntimeTruth` — AppDock).
3. **Physical executor:** в каком процессе/устройстве выполняется вычисление (локальный Windows, headless host, отдельный worker).
4. **Physical custodian:** где реально лежат байты и журналы (локальное Data, хостовый Data, system roots/логи).
5. **Presentation consumer:** кто читает подтверждённое состояние и отображает его (Windows/Web/Android/CLI/agent adapter).

**Следствие:** одно устройство может совмещать все пять ролей; при работе через хост они расходятся. Смена размещения **сама по себе не меняет владельца смысла**. И наоборот, перенос кода в общий пакет без изменения процессной топологии не делает его доступным после закрытия клиента.

### 3.1. Карта semantic owner и запрещённых пересечений

| Объект или действие | Канонический owner | Кто может выполнять/показывать | Что запрещено считать доказанным |
|---|---|---|---|
| Источник ЦБ, методология показателя, нормализация | `stratbox` | Core, любой разрешённый caller | UI не пересчитывает экономическую семантику |
| Вычислительная операция `Request→Result` | `stratbox` | Python caller, application handler, agent adapter | Не обязана иметь chat/run/job ID |
| Каталог разрешённых *аналитических* операций | Core descriptor owner, `CANDIDATE` | Application registry и машины читают проекцию | Декларация доступности ≠ grant на исполнение |
| Scenario definition / step parameters | Application semantics | Desktop/local executor, host executor | Ни Windows widget, ни AppDock manifest не становятся owner сценарного плана |
| Общий чат/Thread, Case, сообщение, автор, read cursors | Application authority в соответствующем deployment | Все авторизованные поверхности | Локальный JSON одного Windows-клиента не должен объявляться командной истиной |
| Run/Job/Attempt, scheduling, claim, cancellation | Application execution authority, `CANDIDATE` | Executor с разрешением | AppDock surface startup не подтверждает Job-completed |
| Допуск опасной операции/ACL/approval | Application policy enforcement point | Клиент запрашивает, executor перепроверяет | Никнейм/UI disable/agent tool listing не есть авторизация |
| Запись файла/удаление/rename | Storage provider под ограничениями вызвавшего | Local/host storage backend | Возвращённый path не доказывает целостность и публикацию |
| Метаданные пользовательского артефакта и ссылка в чат | Application/catalog, `CANDIDATE` | Surface получает безопасные refs | Blob/file и record могут существовать независимо |
| Версия пакета, Node layout, Activation, RuntimeTruth | AppDock, версия-профиль-зависимо | Surface integration adapter читает | Strategy Box не правит platform truth |
| Платформенный сбой, ProblemRef, health | AppDock observability в доказанном контуре | Surface показывает разрешённую проекцию | Platform problem не равен DomainError/JobFailure |
| Аналитическая ошибка, `FailureResult`, evidence | Core и application каждый в своём слое | Reporter/projection adapter | Ошибка источника не маскируется «данных нет» |
| Window state, theme, локальный FilePicker | Конкретная surface | Только client runtime | Не нужно переносить это в host shared state |
| Хостовая машинная identity / user account | Host access boundary + platform context | Web/Android/Windows authenticated connection | Platform session или nickname сами по себе не дают права на команду |

### 3.2. Граница «двух runtime»

Слово runtime используется в проектах минимум в трёх значениях: `base.runtime` библиотеки выбирает FileStore/secret providers; application execution runtime управляет сценариями, заданиями, ошибками и состоянием; AppDock runtime поднимает установленную среду, Node/session и процесс. Эти роли допускают физическое совмещение, однако контракты и failure ownership должны оставаться раздельными.

При отказе AppDock-managed Python environment **платформа** вправе сообщить, что запуск невозможен. При падении выполнения очередного шага «история эскроу» **application** фиксирует failing Attempt/Case, а **core** сообщает доменный `FailureResult`. При недоступной Excel-записи **storage adapter** возвращает точную ошибку, а публикационный use case разрешает незавершённый статус.

---

## 4. Три конкурирующие физические архитектуры — и рекомендуемый переход

### Вариант A. Всё application остаётся в `stratbox-windows`

```
AppDock → Windows Qt + local cases/runner → stratbox
```

**Сильные стороны:** практически существует; одно приложение и мало операционных зависимостей; хорош для персонального Windows-first MVP, foreground-расчётов, демонстраций и разработки. **Цена:** Web и Android должны обращаться к Windows-процессу либо дублировать application code; после закрытия окна authority исчезает; синхронизация общих чатов и хостовые задания становятся трудноуправляемыми; Qt leak усиливает связность.

**Итог:** оставить как описатель текущего состояния. В качестве целевого общего режима отвергнуть, если действительно требуются Web, Android и независимый headless host.

### Вариант B. Общая application-библиотека, in-process у каждого клиента

```
Windows ─┐
Web svc  ├── shared app library → stratbox
Android ─┘
```

**Сильные стороны:** меньше переноса кода, общая модель операций и сценариев; локальная композиция без сети; легко тестировать. **Ключевой недостаток:** общий импорт библиотеки не создаёт **единой** сериализации writes, authority Job и реального межпользовательского chat feed. Разные устройства начнут держать несколько конкурирующих состояний. Android при этом не должен устанавливать тяжёлый Python-core без необходимости.

**Итог:** использовать как логический/кодовый общий слой, но обязательно **одну** runtime authority на конкретное рабочее пространство. Library-only не решает host collaboration.

### Вариант C. Headless Strategy Box application authority + clients

```
Windows UI ───────┐
Browser UI ───────┤   authorized commands / queries / events
Android companion ├────────────────────────────────────────┐
External client ──┘                                        │
                                 Strategy Box app authority
                                /        |             \
                           Chat/Job    policy         artifact index
                                \        |             /
                               scenario execution / workers
                                         │
                                     stratbox core
                                         │
                                neutral Data/FileStore ports

AppDock: installation → Node/runtime → activation/health/transport adapters
```

**Сильные стороны:** один подтверждённый владелец общих чатов и Job; UI-agnostic API; потенциальная долговечность после закрытия клиентов; простая поддержка Web/Android; место исполнения и место Data совпадают. **Цена:** отдельный lifecycle headless authority, сетевой protocol, хранение, аутентификация, concurrency и recovery. Необходимость архитектурного компонента **не означает** необходимость отдельного микросервиса на каждую функцию.

**Итог:** предпочтительный **целевой профиль для shared host**, с постепенным развёртыванием. Имя `stratbox-host` удобно, но имя/новый репозиторий — отдельное решение. Для local-only можно запускать эту же authority внутри процесса либо как локальный sidecar, если это уменьшает число реализаций. Не нужно обязательное HTTP внутри прямого Python вызова core.

### Вариант D. AppDock как owner всех Strategy Box Jobs и чатов

**Плюс:** потенциально единое управление разными продуктами и узлами. **Минусы:** предметные `Scenario`, банковские параметры, чат и результат оказываются зависимыми от чужого domain model; размывается ownership; зрелость необходимых AppDock Control/Data/remote интерфейсов не установлена; core и CLI теряют автономность. AppDock может запускать/наблюдать **процессы**, не имея права определять **смысл** пользовательской аналитической задачи.

**Итог:** отвергнуть как фундамент Strategy Box. Допустимо делегировать платформе техническую активацию, provider readiness, supervision, transport, problem projection — **по конкретному проверенному контракту**.

### 4.1. Почему достаточно монолитного headless authority

Первым target profile рационален **модульный process-monolith**, где shared state, auth, JobManager и API живут в одной headless поставке/процессе, а domain core импортируется как библиотека. Это локализует транзакционные границы, устраняет преждевременные распределённые гонки и позволяет держать один реестр команд и политик. Worker pool внутри того же host может быть позднее выделен без изменения UI contract. Обособленная внешняя очередь появляется только после реальной потребности в распределённых worker-ах, SLA или независимом масштабировании.

---

## 5. Режимы развёртывания: одна семантика, разные гарантии

| Профиль | Где работает core | Где authority Case/Job | Где значимое shared state | Что находится на клиенте | Статус |
|---|---|---|---|---|---|
| **P0: direct Python** (Colab/Jupyter/CLI) | В процессе caller | Может отсутствовать: только `Request→Result` | Подконтрольный caller storage | Python объект и файлы caller | **CURRENT** для core; без приложения |
| **P1: локальный Windows** | Windows | Локальный app/runtime | Локальная user/system+Data область этого устройства | В том же приложении | **CURRENT**, но durability ограничена |
| **P2: headless local** | Служба/процесс на устройстве | Локальная headless authority | На этом устройстве | Windows/Web client loopback | **TARGET / CANDIDATE** |
| **P3: командный host** | На хосте | Один host app authority | На хосте: чаты, исполнение, результаты и файлы | Личные предпочтения, read cursors, временный кэш | **TARGET / CANDIDATE** |
| **P4: публичный Web/remote** | На хосте | Host authority | На хосте; доступ только по идентичностям/правам | Browser session + cache/UI | **CONDITIONAL / SECURITY GATE** |
| **P5: Android companion** | На хосте | Host authority | На хосте | UI, токен сеанса, безопасные уведомления | **CONDITIONAL** |
| **P6: native mobile compute** | На телефоне | Local mobile authority | На телефоне | Там же | **OPEN / не нужен сейчас** |

**Операционный закон:** каждый общий workspace/узел имеет **ровно одного write-authoritative владельца** текущей пользовательской истории и исполнения. Можно подключать много read/write клиентов, но они отправляют изменения authority. Локальные кэши клиентов не создают вторую истину. Различие между platform `Node` и app `Workspace` требует отдельной mapping table: один Node потенциально содержит разные workspace, но пока потребность не доказана, достаточно одного активного app workspace на deployment instance.

### 5.1. Самое важное про `user`/`system`/`Data`

Комментарий разработчика приоритизирует **место реального исполнителя** и системную значимость state. Не надо механически записывать всю историю в физическую `user`-папку, потому что она так называется в AppDock. Правильная последовательность:

1. Определить семантику объекта (`shared Case`, `user preferences`, `raw stats`, `operation log`, `published file`).
2. Назначить authority (на host или local device).
3. Получить от AppDock **разрешённые** managed roots/bindings данного deployment.
4. Разместить байты через storage adapter без экспонирования физического пути в переносимом клиентском контракте.

**Host-owned:** authoritative Case/Run/Job records, shared chat index/messages, ack/unknown-effect status, user-to-case relation, managed artifact metadata, consistency revision, авторизованная история изменений. **Data-owned:** исходные статистические файлы, рабочие таблицы, выходные Excel и прочие пользовательские файлы. **Platform-owned system:** установка, package/runtime truth, platform sessions и platform problems. **Client-owned второстепенное:** тема, размеры окон, выбранная вкладка, последний просмотренный чат, сортировка, локальная безопасная кэш-проекция, временный файл скачивания.

Физическое расположение `operational logs` допускает платформенные constraints. Однако лог предметной операции должен логически относиться к **месту фактического исполнения** и ссылаться на соответствующий Run/Attempt; системный app-log и platform-log могут храниться в разных каталогах.

### 5.2. Согласованность с пользовательским чат-замыслом

Чат — основной визуальный контейнер событий и сообщений; **chat_id не должен одновременно становиться единственным ID запуска**. Один чат содержит несколько независимых Run, в том числе параллельных; один Run может включать несколько шагов, попыток, outputs и problems. Нужна следующая связь:

```
node / workspace
    └─ chat_id / thread_id
         ├─ message_id (human / system / activity)
         ├─ case_id / run_id
         │    ├─ job_id (только managed execution)
         │    ├─ attempt_id[]
         │    ├─ step_id[]
         │    ├─ effect_id[]
         │    └─ artifact_id[]
         └─ read_cursor_by_participant
```

Базовый nickname + timestamp + avatar достаточны для **представления** автора. Для принятия удалённой команды обязателен другой проверяемый идентификатор principal. UI показывает два дополнительных поля без перегруза: **«инициатор»** и **«выполняется на»**. Технический actor, вызвавший конкретный шаг (например, automation), хранится отдельно от исходного человеческого инициатора.

---

## 6. Владение исполнением, допуском и внешним эффектом

### 6.1. Кто принимает действие

Предлагаемый цикл хостового вызова:

```
client / agent intent
  → authenticate principal
  → validate command schema + resources + expected revision
  → authorize action + object + effect class
  → reserve run / request idempotency key
  → persist admitted intention (если профиль durable)
  → dispatch local/core worker
  → observe step result + effect evidence
  → finalize application state
  → project message/status to clients
```

**Application authority** принимает или отклоняет запуск; backend отвечает за реальное выполнение; core отвечает за предметную корректность результата; storage/provider подтверждает операции со своими ресурсами; UI отображает полученный ответ. В локальном P1 эти стадии могут быть в одном Python-процессе; их логическое различие позволяет позже подключить P3 без переписывания банковских процедур.

### 6.2. Кто даёт разрешение

По OWASP, модель доступа должна начинаться с `deny by default`, а права проверяться для **каждого** запроса на стороне контролирующего ресурс компонента [E4]. Поэтому:

- AppDock *может* аутентифицировать platform session и определить managed environment, но это не означает автоматического допуска к `frg.cleanup.execute` в Strategy Box.
- Windows/Browser/Android *может* скрывать кнопку или делать её disabled, но это UX, а не enforcement.
- Application authority сопоставляет доверенный principal, запрашиваемую operation/capability, action, object/workspace, risk class и необходимые подтверждения.
- Domain core, вызываемый **напрямую** из Python, работает с полномочиями и ресурсами caller. Он не обязан имитировать тот же web auth layer; FileStore backend и ОС всё равно ограничивают доступ к байтам.
- При непосредственном внешнем сетевом вызове от AI-инструмента/автоматизации действует тот же host policy gate, что и при UI. Наличие descriptor `ai_visibility` не даёт права выполнения.

Минимальная ролевая схема знакомой команды может состоять из `viewer` (видит), `runner` (запускает разрешённое), `workspace_editor` (изменяет файловую область) и `administrator` (управляет участниками/опасными настройками), но **точные роли и опасные действия ещё OPEN**. Для локального одиночного P1 достаточно OS-user context и явных подтверждений разрушительных действий. Для публичного Web/host P4 нельзя полагаться только на введённое пользователем имя, предварительно открытые URL, общий секрет или интерфейс AppDock; нужен минимальный устойчивый authentication/authorization boundary, TLS и ограничение доступа по объекту.

### 6.3. Кто имеет право сказать «файл создан»

Три отдельных свидетельства:

1. **Compute outcome:** core сгенерировал data result / байты или завершил метод вычисления.
2. **Effect outcome:** storage backend подтвердил запись/rename/delete/сетевой запрос. При потере ответа возможен `OUTCOME_UNKNOWN`.
3. **Publication outcome:** application catalog считает файл доступным для конкретных участников и показывает запись/ссылку в чате. После действий пользователя файл может исчезнуть и ссылку достаточно перевести в `missing`.

Пример: `xlsx_export()` успешно собрал workbook, но запись на host Data root оборвалась. `OperationResult.computation=SUCCESS`, `EffectOutcome=UNKNOWN/FAILED`, `ArtifactPublication=UNPUBLISHED`, общий `Case` отображает предупреждение. **Сообщение «готово» запрещено до нужной ступени подтверждения**.

**Важное ограничение минимализма:** не каждый пользовательский Excel требует вечного `artifact_id`, контент-адресного архива и отслеживания переименований. Если продуктовая цель — файл в обычном каталоге, достаточно запись с `artifact_id`/`locator` и проверку существования при действии. Для управляемых, публикуемых, воспроизводимых результатов можно позже добавить `version/hash/provenance` по профилю. Это согласует тему 10 с прямым комментарием разработчика по теме 4, не навязывая сложное asset management всем файлам.

### 6.4. Пример сбоя между write и acknowledgement

Представим, что хост создал `report.xlsx`, но соединение с Windows оборвалось раньше ответа. Windows **не знает**, появился ли файл. Запускать тот же экспорт вслепую рискованно: новая попытка может перезаписать готовый файл, создать дубликат либо удалить промежуточные данные.

Минимальное решение:

- immutable `request_id`/`idempotency_key` в области конкретного workspace и principal;
- durable либо восстановимый `effect_intent` перед рискованным действием в соответствующем профиле;
- серверная повторная проверка наличия результата по ключу, метаданным, version/size/hash, если это позволяет backend;
- при неизвестности — `OUTCOME_UNKNOWN` с явным разрешённым действием «Проверить»;
- повторное действие использует тот же key только при тех же параметрах и области; другая команда с тем же key получает conflict.

Семантика `at-least-once` сама по себе не равна `exactly-once`: документация Celery подчёркивает необходимость идемпотентности при поздних acknowledgment и retry [E8]. Для рабочего файла важнее **отсутствие тихой потери/дублирования**, чем слоган «выполняется ровно один раз».

### 6.5. Параллельность разных чатов

Прямое пожелание разработчика — команды исполняются одновременно в нескольких чатах. При этом «неограниченное всё параллельно» приведёт к конфликту записи одного набора DBF/Excel, разрушительному cleanup и гонкам в общем output. Значит, concurrency ограничивается **общими ресурсами**, а не блокировкой всего окна:

- `chat_A / independent read` и `chat_B / independent read`: допускаются вместе;
- `chat_A` пишет `output/escrow.xlsx`, `chat_B` пишет другой файл: допускаются вместе;
- две операции одновременно публикуют одну и ту же версию `output/report.xlsx`: одна допускается, другая получает conflict/wait;
- `frg.cleanup.execute` против `frg.scan` того же каталога: требует resource-guard и учёта изменяющегося набора файлов.

Для single-host достаточно небольшой локальной очереди с **resource keys** (workspace + normalized output/input affected path) и явной политикой shared/exclusive. Distributed leases/fencing tokens нужны лишь при нескольких конкурирующих worker-ах. Martin Kleppmann показывает, почему истёкший lease без fencing на стороне storage не защищает от запоздалого writer [E9]. Не нужно строить distributed lock service заранее.

---

## 7. Минимальный набор общих интеграционных контрактов

Общее означает **единое наблюдаемое правило**, а не единый класс DTO для любой задачи. Ниже — логические кандидаты API, а не уже существующие endpoint-ы.

| Contract / port | Значение | Owner | Для каких потребителей обязателен | Статус |
|---|---|---|---|---|
| `CoreOperation` / `Request→Result` | Предметный вызов и typed результат | `stratbox` | Python, app handler | Часть доменов CURRENT, общая нормализация CANDIDATE |
| `OperationDescriptor` | ID, параметры, effects, workspace constraints | Домен + application projection | UI/agent catalog | Частичные `OperationSpec` CURRENT |
| `ScenarioDefinition` | Шаги, зависимости, параметры | Application | GUI/host | CURRENT локально; shared CANDIDATE |
| `InvokeCommand` | Запросить запуск с principal/resources/idempotency | Application | Host clients | CANDIDATE |
| `RunSnapshot` / `JobStatus` | Подтверждённая state+revision+origin | Application authority | Все управляемые UI | CURRENT только локальная частичная модель |
| `CommandOutcome` | accepted/rejected/conflict/result/unknown | Application authority | UI/CLI/API | CANDIDATE |
| `PermissionDecision` | Проверка principal+action+object+effect | Application authority | Любой удалённый mutation | CANDIDATE |
| `EventFeed` / `Cursor` | Последовательность подтверждённых изменений | Application authority | Host clients | CANDIDATE |
| `ArtifactReference` | ID/locator/visibility/missing | Application/catalog | UI/agent | Локальный `ArtifactRecord` CURRENT, remote CANDIDATE |
| `StorageCapabilities` | Безопасные операции и пределы backend | `FileStore` adapter | Worker/publication | Basic FileStore CURRENT; advanced CANDIDATE |
| `ExecutionBackend` | Исполнить разрешённую операцию локально/на узле | Application adapter | Dispatcher | LOCAL CURRENT; remote CANDIDATE |
| `PlatformActivationAdapter` | Прочитать/проверить конкретную версию AppDock context | Strategy Box boundary + AppDock source owner | Managed surface | CURRENT для desktop |
| `PlatformHealthAdapter` | Проверенный health/problem reference без raw secrets | AppDock product boundary | Managed profiles | PARTIAL / версия-зависимо |
| `ClientViewModel` | Чат/форма/status/inspector без Qt | Application presentation semantics | Windows/Web/Android | `presentation/common` частично CURRENT |
| `Agent/MCP/A2A adapter` | Перевести разрешённый tool request в `InvokeCommand` | Внешний interface adapter | Agent consumers | CONDITIONAL; не core dependency |

### 7.1. DTO, без которого host-клиенты неизбежно разойдутся

Минимальное сообщение `InvokeCommand` (условный контракт v1; поля и имена требуют admission):

```json
{
  "contract_version": "1.0",
  "request_id": "request-opaque-id",
  "workspace_id": "workspace-opaque-id",
  "chat_id": "chat-opaque-id",
  "operation_id": "escrow.history.export",
  "operation_version": "domain-contract-version",
  "parameters": {"output_format": "xlsx"},
  "expected_workspace_revision": 27,
  "idempotency_key": "opaque-random-key"
}
```

**Принципиально:** `principal_id`, `actor_id` и trust level назначаются **после authentication на host**, а не принимаются из свободно редактируемого JSON клиента. Никнейм / авторское отображаемое имя является дополнительной проекцией. Текущий chat ID, выбранный в UI, ещё не означает право записи именно в этот чат.

Минимальный ответ:

```json
{
  "contract_version": "1.0",
  "request_id": "request-opaque-id",
  "disposition": "accepted",
  "run_id": "run-opaque-id",
  "state_revision": 28,
  "executor_node_id": "node-opaque-id",
  "status_url_ref": "opaque-reference"
}
```

`accepted` означает допуск и сохранение намерения в соответствии с поддерживаемым профилем; **это ещё не успешный расчёт**. `rejected` — вход/permission/validation; `conflict` — устаревшая revision, занятый ресурс или повтор key с другим payload; `unavailable` — backend/узел не готов; `outcome_unknown` — действие могло произойти, но не доказан результат. Для HTTP-представления `202 Accepted` по RFC 9110 также обозначает принятие на обработку, а не завершение [E5].

### 7.2. Версионирование: версия содержания отдельно от версии транспорта

Необходимы **независимые** версии:

- `core_distribution_version` и конкретные versions моделей/операций;
- `application_contract_version` (команды, результаты, состояние, события);
- `artifact_record_schema_version` и `workspace_state_schema_version` при их появлении;
- `platform_connector_manifest_version`, `activation_contract_version`, `activation_context_version`, `session_state_version` — только по AppDock owner;
- `client_version` Windows/Android/Web;
- `wire_api_version` у фактического host API.

Рекомендуется **не объявлять одну глобальную совместимость по одному `appdock_version`**. На старте adapter выполняет validation/negotiation конкретных required fields, features, profile и version; неизвестная требуемая capability → controlled `UNSUPPORTED_CAPABILITY` вместо молчаливой эмуляции. После изменения major-контракта нужно обновлять call sites и тесты одновременно; обратная совместимость legacy API сама по себе целью проекта не является. Уже сохранённые пользовательские данные при этом нуждаются в явной стратегии миграции/сохранности.

### 7.3. Что не должно быть общим

1. Платформенные абсолютные пути (`C:\\...`, `/var/...`) и OS process IDs.
2. Qt `QThread`, signals, event loop, Qt widgets и layout constants.
3. Browser cookie/session/CSRF и Android permissions/lifecycle.
4. Специфичные требования Windows Installer, AppDock Studio, Java/Kotlin bridge и mobile storage picker.
5. Низкоуровневый backend exception class.
6. Чисто персональные preferences (`selected_tab`, размер окна, gesture settings).
7. Тайминги UI-анимаций как часть серверного Job contract.
8. Внутренние поля AppDock `RuntimeTruth` и platform problem store.

Все они адаптируются у границы. Web API можно описывать OpenAPI 3.1 + JSON Schema, но эти форматы **проверяют структуру**, а права, порядок эффектов, fidelity и жизненный цикл требуют отдельных semantic invariants и тестов [E10, E11].

---

## 8. Contract topology и направления зависимостей

```text
                ┌────────────────────────────────┐
                │ Windows / Web / Android / CLI  │
                │ rendering + local preferences  │
                └───────────────┬────────────────┘
                                │ commands / queries / event views
                  ┌─────────────▼─────────────┐
                  │ Strategy Box Application  │
                  │ (local / headless authority)│
                  │ admission, chat, scenarios │
                  │ jobs, visibility, policy   │
                  └───────┬─────────┬─────────┘
                          │         │ platform *port*
          typed domain API│         └─────────┐
                  ┌───────▼────────┐   ┌───────▼────────────┐
                  │ stratbox core  │   │ AppDock adapter    │
                  │ Request/Result │   │ pinned contract   │
                  └───────┬────────┘   └───────┬────────────┘
                          │ neutral FileStore   │
               ┌──────────▼──────────────┐   ┌──▼───────────────┐
               │ Storage/network adapters│   │ External AppDock│
               └─────────────────────────┘   │ environment     │
                                              └─────────────────┘
```

**Допустимые зависимости:** clients → application contract; application → core contract + platform-neutral ports; AppDock adapter → explicit platform contract; FileStore/provider → OS/backend; тесты → fake implementations этих портов. **Недопустимые:** core → Windows/Qt/host HTTP; core → AppDock-owned private state; AppDock → импорт `stratbox`-доменных internals для интерпретации аналитики; UI → прямая запись shared DB; Web → системный путь host; background worker → отдельная копия authority.

### 8.1. Логическая authority ≠ отдельный репозиторий

Три последовательно возможные реализации:

1. Выделить interface/protocol и application use cases **внутри текущего Windows application layer**, убрать Qt import из bootstrap — минимальная архитектурная очистка.
2. Вынести независимую common application implementation/SDK и дать Windows адаптер поверх неё. Для local P1 authority может всё ещё быть in-process.
3. При реальной поставке P3/P4 материализовать host process со своей state DB и endpoint; его код может сначала принадлежать общей application поставке. Отдельный repo выделяется при отдельном deployment/release/security lifecycle.

Начинать с пяти новых репозиториев («common», «contracts», «host», «server», «sdk») до появления consumers нет смысла. Важно признать семантическое владение уже сейчас и обеспечить направленность импортов.

---

## 9. Как проходит право, идентичность и наблюдаемость

### 9.1. Минимальная сквозная корреляция

В каждой значимой записи желательно хранить:

```
node_id? / workspace_id
chat_id / message_id? / case_id? / run_id
job_id? / attempt_id? / step_id?
initiator_principal_id / display_author
executing_actor_kind / executor_node_id
operation_id + version
requested_at / started_at / finished_at UTC
outcome_code / problem_ref? / effect_ref? / artifact_ref?
```

`?` значит действительно optional по профилю: обычный прямой Python вызов не должен создавать фальшивый чат. `trace_id/span_id` полезны для технической корреляции через сервисы, но не заменяют устойчивые бизнес-ID. OpenTelemetry задаёт общие правила trace/span propagation [E6]; CloudEvents показывает переносимую event envelope (`id`, `source`, `type`, `specversion`) [E7]. При этом **внедрять полный OpenTelemetry collector и CloudEvents broker не обязательно**: достаточно собственных строгих DTO с возможностью последующего mapping.

### 9.2. Две разных схемы событий

**Business/application events:** `run_admitted`, `step_started`, `effect_pending`, `artifact_available`, `run_failed`, `chat_message_posted`, `permission_denied`; хранятся и разрешаются application authority. **Platform events/problems:** `activation_failed`, `runtime_missing`, `node_unavailable`, `session_failure_problem_ref`; принадлежат платформе и поступают только по поддерживаемому adapter API.

Отображение другому участнику строится на **разрешённой проекции**, а не на копии physical log. Нормальная карточка: «Иван — сценарий “История эскроу” — выполняется на узле “Отдел” — ошибка записи результата — 10:42». Подробности операции могут открываться инициатору/оператору; raw traceback, tokens, абсолютные server paths и secrets не должны размножаться по общей комнате.

AppDock observability содержит идею **одного подтверждённого ProblemOccurrence и стабильной ссылки**, но реальная матрица функций ограничена milestones: Strategy Box не должен заранее создавать `ProblemRef`, которого platform contract ещё не предоставил. При потере transport используется собственный `platform_unavailable`/`diagnostics_pending` статус с сохранением причин и без фиктивной регистрации проблемы.

### 9.3. Снимок + поток событий

Для общего чата недостаточно «обновить все JSON на всех устройствах». Host выдаёт snapshot (`workspace revision`, `chats`, `cases`, statuses) и cursor-based event feed после этой ревизии. При reconnect клиент запрашивает изменения; при большом пропуске — новый snapshot. Для browser read-heavy канала целесообразно начать с HTTP queries и Server-Sent Events, чья семантика `EventSource` и `Last-Event-ID` стандартизована WHATWG [E12]. WebSocket рационален при доказанной необходимости двунаправленной низколатентной беседы или сложной совместной редакции. **MCP и A2A являются внешними протоколами обращения к возможностям/агентам**, а не замещением canonical application state [E13, E14].

---

## 10. Сохранность, отмена и recovery: минимальные профили

### 10.1. Нельзя обещать одинаковую durability для P1 и P3

**P1 foreground:** пользователь закрывает приложение — процесс/операция может прерваться; к моменту нового запуска незавершённая карточка получает `INTERRUPTED/UNKNOWN` и предлагает проверку/повтор. Ценность — быстрая атомарная запись критичного файла и честная диагностика. Это соответствует предпочтению разработчика и не требует Temporal-подобного replay.

**P3 host:** клиент закрыт, но Job может продолжать работу на сервере. Для этого authority, worker и persisted state должны существовать независимо от клиента; отказ worker/server должен завершаться `INTERRUPTED/FAILED/UNKNOWN` в зависимости от доказанного эффекта. Если Product Decision не требует auto-resume, **не нужно** обещать его: достаточно регистрации незавершённого запуска, атомарных публикуемых файлов и явного ручного повторения.

Temporal демонстрирует сильную durable workflow модель с Event History/replay [E15], но она вводит самостоятельный orchestration server, history semantics и ограничения детерминизма. Это оправдано при длительных многошаговых задачах с automatic recovery, но **избыточно для раннего Strategy Box**, где разработчик допускает завершение при прерывании.

### 10.2. Где достаточно SQLite и где нужен сервер DB

Для одного host-процесса с умеренной командной нагрузкой SQLite часто даёт достаточную транзакционность, миграции схем и экономный footprint. WAL позволяет параллельных читателей и одного writer; SQLite прямо предупреждает, что WAL не работает как многомашинный общий DB поверх network filesystem [E16]. Поэтому файл SQLite должен оставаться на локальном диске **authority host**, а клиенты обращаться через API. При нескольких host-authority процессах, высокой конкуренции writers и отдельных требованиях HA возникает аргумент за PostgreSQL. Выбор СУБД зависит от RPO/RTO, числа конкурентных write-транзакций и топологии, а не от слова «multi-user» само по себе.

### 10.3. Когда применим «минимальный эффект»

- Для append-only записи нового отчёта в один Data-root: `temp → write → flush/verify → rename/commit → publish record`, если backend поддерживает нужную атомарность.
- Для внешнего неизвестного backend: `stage → attempt → verify → explicit unknown`, без обещания атомарного rename.
- Для удаления: `plan → preview/authorize → execute → verify`, отдельная запись частичного результата.
- Для загрузки источника: различать «нет новых данных», «источник недоступен», «получена HTML-страница ошибки» и «получена новая ревизия байтов».

Подробный **LDD-кандидат** уже опубликован в [`docs/ldd/artifacts/staged-publication.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/ldd/artifacts/staged-publication.md). Он предлагает `DRAFT→STAGED→VERIFIED→PUBLISH_PENDING→COMMITTED`, `OUTCOME_UNKNOWN` и reconciliation. Это полезная модель тестов **для действительно управляемых артефактов**, а не обязательное оформление каждого промежуточного CSV.

---

## 11. Что особенно не стоит проектировать сейчас

| Соблазнительное решение | Почему оно плохо подходит сейчас | Менее дорогой эквивалент |
|---|---|---|
| Перенести аналитику внутрь AppDock | Потеря автономности, неправильный semantic owner | Core через нейтральный operation contract |
| Копировать application runner в Windows, Web и Android | Три конкурирующих источника истины | Один authority + несколько renderer-ов |
| Настаивать на одинаковом UI toolkit | Разные lifecycle/верстка/OS APIs | Общие view-model, form specs, status semantics |
| Полный event sourcing всех действий | Высокая стоимость восстановления и эволюции схем | Transactional current state + компактная event/activity history |
| Kubernetes, Celery и Temporal «про запас» | Операционное усложнение при отсутствии SLA | Один headless процесс + локальный worker pool |
| Отправлять application JSON history в AppDock RuntimeTruth | Смешение ownership и lifecycle | Ссылочная safe projection: active job/ref/health |
| Делать nickname единственным authentication | Лёгкая подмена инициатора на сетевой границе | Verified principal + nickname display |
| Повторять любую failed operation автоматически | Дубли/удаление файлов после uncertain effects | Idempotency + effect classification + manual reconciliation |
| Гарантировать автоматический поиск перемещённых файлов | Противоречит явному пользовательскому правилу | Проверить locator при действии, показать `missing` |
| Вынести каждый port в отдельный сервис | Сетевая связность без самостоятельного lifecycle | Модульные границы внутри одного process-host |
| Требовать от core обязательного chat/job context | Ломает Jupyter/Colab/CLI reuse | Context optional, application wrapper binding |
| Ждать полной зрелости AppDock перед разработкой core | Затормозит доменную архитектуру | Изолированный platform adapter + feature gates |

---

## 12. Проверяемые сценарии — настоящие критерии контрактов

Ниже **не результаты выполненных тестов**, а минимальный предложенный acceptance suite для будущих решений.

| ID | Условие/инъекция отказа | Приемлемый наблюдаемый итог | Какие границы проверяет |
|---|---|---|---|
| T10-01 | Запустить одну операцию напрямую в Jupyter без UI/AppDock | `Request→Result`, корректный FileStore, нет обязательного chat/job | автономность core |
| T10-02 | Запустить две independent команды в разных чатах | Два Run ID, два исполнителя, независимые статусы | chat vs run, concurrency |
| T10-03 | Одновременная запись одного output path | Явный conflict/serialize, отсутствие скрытой перезаписи | resource guard |
| T10-04 | Закрыть Windows-клиент во время host-run | Run продолжает работу в P3; после reconnect клиент получает подтверждённое состояние | authority vs renderer |
| T10-05 | Завершить локальный foreground-процесс | После старта статус прерывания без фальшивого success; доступен ручной повтор | local failure contract |
| T10-06 | Сеть оборвалась после host file commit, до ACK | `outcome_unknown` → проверка по key → одна видимая публикация | effect reconciliation |
| T10-07 | Потерять запись после генерации workbook | Успех вычисления ≠ опубликованный artifact | computation/effect separation |
| T10-08 | Переименовать output в проводнике | При следующем действии «файл не найден», без автоматической индексации всего диска | bounded artifact UX |
| T10-09 | Клиент отправил другой `principal_id` в payload | Host игнорирует подложный actor, использует authenticated principal | auth boundary |
| T10-10 | Agent попытался вызвать опасную команду без разрешения | `DENIED`, нет side effect, есть безопасная запись отказа | capability vs permission |
| T10-11 | Manifest `4.0`, тест/adapter ожидает `3.0` | Контрактный тест **обнаруживает** несовместимость до запуска | version drift |
| T10-12 | AppDock отсутствует при direct core-run | Работа core сохраняется; managed surface выдаёт ясный startup contract error | external dependency |
| T10-13 | Host Data root недоступен | UI поднимается в degraded/read-only режиме, операции записи отклонены | readiness boundaries |
| T10-14 | Два клиента переименовывают один чат | Один accepted revision, второй получает conflict/reload | optimistic concurrency |
| T10-15 | Клиенту доступен чат, но запрещён raw log | Сообщение и safe error показаны, приватный traceback скрыт | audience projection |
| T10-16 | Повреждён persisted Case storage | Явный corrupt/degraded и диагностика, а не пустая «чистая» история | persistence integrity |
| T10-17 | Истёкший worker пытается финализировать файл | При multi-worker профиле устаревшая попытка отклоняется storage fencing/version | lease/effect safety |
| T10-18 | Подключение Android/Web во время run | Snapshot + cursor feed восстанавливают одинаковую семантику статусов | common contract |
| T10-19 | Попытка запуска поверх отсутствующей платформенной remote capability | Feature check отказывает с `UNSUPPORTED_CAPABILITY`; local mode работает | AppDock capability gate |
| T10-20 | Неуспешный platform activation | Platform problem и app Job status различаются; нет fictitious failed Job | platform/application ownership |
| T10-21 | Изменился library method, не обновлён operation descriptor | CI ловит schema/handler mismatch | catalog conformance |
| T10-22 | Нарушены source units/semantic result during adapter transform | Domain Result сохраняет units/evidence/unknown; UI не округляет без правила | science/domain authority |

### 12.1. Доказательство качества: пирамида тестирования

**Core tests:** независимый импорт, доменные golden fixtures, validation/errors. **Application tests:** scenario planner, permission guards, state revisions, idempotency, resource conflicts и crash reconciliation через in-memory/fake ports. **Platform adapter tests:** JSON/schema validation against exact AppDock versions, malformed/no fields, degraded startup, lifecycle/health. **Client contracts:** один fixture `RunSnapshot` рендерится Windows/Web/Android без изменения смысла. **End-to-end host:** два клиента, одна host DB, одновременные команды и fault injection. **Platform acceptance:** Windows/native и соответствующий Linux/host испытательный стенд, когда реально есть контракт. Прохождение статического теста manifest не доказывает установленную сборку.

---

## 13. Очерёдность реализации без архитектурного долга

### Этап I. Синхронизировать действующие границы (P0, можно делать без host)

1. Назначить версионный baseline `stratbox` ↔ `stratbox-windows` ↔ AppDock Connector; согласовать manifest, README и smoke/contract tests. Отдельно проверить фактический package resolution/installation; текстовый drift уже наблюдаем.
2. Убрать Qt import из `runtime.bootstrap`: заменить его на application-level `ScenarioExecutionPort` и Qt bridge; сделать headless/no-GUI tests.
3. Выделить общие `OperationSpec/ScenarioSpec`, typed failure/status семантику и `effect risk class`. Не форсировать единый большой registry до стабилизации доменов.
4. Отделить пользовательскую history projection от будущей authoritative state. Исправить fail-open при повреждённом JSON, ввести atomic writes для локальных projections и версию схемы.
5. Добавить проверяемый tracing lineage `chat_id → run/case_id → steps → outputs` без обязательного внешнего OTel server.

**Завершение:** полностью работающий Windows local P1 и direct core P0, без утверждений о новом shared host.

### Этап II. Формализовать один logical application authority (P1)

1. Определить `invoke/get_status/list_chats/events` как интерфейс; проверить его на локальной in-process реализации.
2. Перевести job/case writes и artifact records в один application owner, не позволяя Qt panels напрямую менять shared truth.
3. Явно различить initiator, executor, Node, workspace и чат; назначить локальный resource guard для конкурирующих output paths.
4. Сделать общую модель safe projections для нескольких UI, но сохранить независимые нативные renderer-ы.

**Завершение:** запуск из UI и headless harness дают одинаковое semantic Result/Status при одних входных данных и состоянии.

### Этап III. Материализовать host лишь после подтверждения P3/P4 (P1/P2)

1. Выбрать физическую authority: один headless process с API, локальной transactional state DB и adapter к фактическому AppDock Node/Data binding. Развести его lifecycle и foreground Windows.
2. Ввести минимальный auth/authz для подключения команды, per-workspace ownership, idempotency, revision, ограниченный append-only event feed, file/ArtifactRefs. Проверять effect scopes на host.
3. Добавить web/Android клиента на одном API: начать с browse/start/status/artifact; SSE/polling в зависимости от потока; не требовать mobile core installation.
4. Для public URL отдельно пройти TLS/session/CSRF/origin/permissions/network hardening. Использовать только реальные AppDock capabilities — без guessed remote APIs.

**Завершение:** два разных устройства видят общий чат, авторов и места исполнения; закрытие любого клиента не делает общий Run фиктивно завершённым.

### Этап IV. Усилять по измеренной нагрузке (P2)

- Реальный scheduler/background лишь при релизном scope;
- SQLite → PostgreSQL при выявленном bottleneck/HA требовании;
- process workers, queue/lease и fencing при multi-worker;
- более строгий artifact publication, provenance и snapshots для требующих того сценариев;
- MCP/A2A только как разрешённые adapters, когда платформа и потребители подтвердят контракт;
- полная unified observability интеграция при фактической готовности AppDock milestone.

---

## 14. Противоречия, последствия и открытые Product Decisions

### 14.1. Конфликты, которые можно разрешить уже сейчас

**C-01. «Общие интерфейсы» vs кроссплатформенные реалии.** Снять противоречие через общую *семантику*, API, формы и статусы, а не UI-code sharing. Renderer независим.

**C-02. Windows одновременно UI и authority.** Это факт нынешнего P1, полезный локально. Для P3 authority переезжает под headless host; клиент перестаёт быть canonical store. Не нужна параллельная «хостовая копия» JSON-хранилища.

**C-03. AppDock Node vs Strategy Box Job.** Названия похожи, но платформенный process status не подтверждает предметный результат. Два owners, связаны refs.

**C-04. Системная история в чате vs настоящие логи.** Чат — безопасная понятная activity projection; технические логи и доказательства эффектов остаются отдельными сущностями. Одно сообщение может ссылаться на Run/Problem, но не обязано содержать traceback.

**C-05. Никнейм vs authentication.** Для знакомого локального коллектива никнейм достаточен для отображения, но для сетевого исполнения и опасных эффектов требуется проверенный principal.

**C-06. «Файл наш» vs внешний файловый менеджер.** Принять слабый locator-first artifact contract по умолчанию: missing link при обнаружении. Строгие версии/хэши только для managed artifacts.

**C-07. Manifest говорит `supports_presence`, runtime без сети.** Capability declaration означает намерение или поддерживаемую surface-форму, но transport и authority нужно проверить отдельно.

### 14.2. Что требует реального решения владельца продукта

| Decision ID | Вопрос | Предпочтительное временное правило | Когда становится блокирующим |
|---|---|---|---|
| D10-01 | Нужен ли обязательный headless local process уже для P1? | Нет; начать с логической in-process authority | Перед Web/host release |
| D10-02 | Какая история действительно должна пережить crash/выключение питания? | Cases, результаты, факт опасных эффектов — при их принятом managed профиле; preferences best-effort | Перед выбором storage и RPO |
| D10-03 | Должен ли interrupted Job автоматически продолжаться? | Нет, статус + ручная проверка/повтор | При введении фоновых SLA |
| D10-04 | Какие операции read/write/destructive и кому разрешены? | Deny risky by default; explicit operator confirmation | Перед shared host и AI |
| D10-05 | Сколько workspace на один Node и каков isolation? | Один активный workspace как simplest profile | Перед multi-tenant/shared deployment |
| D10-06 | Кто подтверждает авторизацию пользователя Web/Android? | Host validates principal; upstream AppDock identity только после доказанного trust contract | До публичной сети |
| D10-07 | Где транзакционно хранится host state? | Один локальный authoritative DB без network WAL | Перед P3 implementation |
| D10-08 | Какой retention для cases/logs/artifacts? | Определить отдельно по классам и scope; no unbounded logs | Перед production хостом |
| D10-09 | Какой default artifact contract? | Path/reference + missing-on-use; staged publish для ценных files | Перед публикацией managed files |
| D10-10 | Какой exact AppDock remote/Node/Data contract? | Проверить upstream через versioned SDK, defer unsupported features | Перед remote activation |
| D10-11 | Нужны ли SSE/WebSocket/long polling? | HTTP snapshot + polling; SSE при необходимости live updates | Перед Web UX |
| D10-12 | Отдельный `stratbox-host` репозиторий? | Не решать по имени; сначала independent lifecycle | Перед отдельным build/release |
| D10-13 | Насколько одинаковыми должны быть Android и Windows возможности? | Shared core UI semantics; Android companion в первом релизе | Перед Android scope |
| D10-14 | Нужны ли agent tool / A2A bindings и кому принадлежит агент? | External adapter, без изменения core semantics | При появлении первого машинного consumer |

Эти вопросы соотносятся с актуальным [`PRODUCT-QUESTIONS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/consolidation/questions/PRODUCT-QUESTIONS.md), где `SB-Q-01..08` остаются открытыми по долговечности, хранению, опасным эффектам, scheduler, артефактам, AppDock и Android. Новое исследование **не вправе заочно закрыть** эти вопросы.

### 14.3. Три наиболее важные архитектурные проверки перед кодом

1. **Authority test:** можно ли спросить у единственного владельца состояние конкретного Run и получить тот же ответ из Windows, браузера и API; существует ли ответ после закрытия клиента в выбранном профиле?
2. **Effect test:** кто именно имеет право записать, перезаписать или удалить файл, и как отличить `succeeded`, `partial`, `failed` и `unknown` после разрыва?
3. **Platform test:** какая **конкретная версия** AppDock действительно гарантирует path/binding, activation, Node health и remote capability, без предположений из roadmap?

---

## 15. Внешние исследования и решения: критическое сопоставление

| Подход | Что извлечь | Чего не копировать буквально | Применимость |
|---|---|---|---|
| **Parnas, information hiding** [E1] | Модули вокруг собственных изменяемых решений/authority | Физический сервис для каждой обязанности | **Высокая:** division by ownership |
| **Cockburn, Ports & Adapters** [E2] | Core без GUI/database dependence; разные adapters | Абстрактные порты на каждую функцию заранее | **Высокая:** Python + GUI + host |
| **OWASP authorization** [E4] | Проверка каждой команды у protected resource, deny-by-default | Тяжёлая IAM для одиночного офлайн-режима | **Высокая:** shared/public/agent |
| **HTTP RFC 9110** [E5] | `accepted` отличать от `completed`, явная семантика ответов | HTTP как обязательный internal core interface | **Высокая:** host API |
| **OpenTelemetry/W3C** [E6] | Trace propagation и separation from business IDs | Полный telemetry stack до появления нужды | **Средняя:** расширение observability |
| **CloudEvents** [E7] | `source+id`, event type, version, timestamp discipline | Обязательный брокер событий | **Средняя:** projection/event feed |
| **Celery** [E8] | Caveats retry/ack/idempotency | Брокер и workers как стартовый фундамент | **Средняя:** поздние задания |
| **Distributed fencing** [E9] | Старый worker не должен переписать новую версию | Distributed locks для одиночного процесса | **Средняя позже:** multi-worker |
| **OpenAPI/JSON Schema** [E10–E11] | Машинно-читаемые контракты/validation | Считать schema определением методологии/права | **Высокая:** Web/clients |
| **WHATWG SSE** [E12] | Простое server→client обновление ленты | SSE как replacement для command API | **Высокая:** host chat events |
| **MCP/A2A** [E13–E14] | Адаптеры к разрешённым capabilities/agents | Перенос agent lifecycle в core | **Условная:** при потребителе |
| **Temporal** [E15] | Ясное различение Workflow/Activity/history/replay | Durable orchestration cluster и replay по умолчанию | **Низкая сейчас, высокая при сложных long-run SLA** |
| **SQLite WAL** [E16] | Один host DB, readers/writer, понятные пределы | Один SQLite на network filesystem между клиентами | **Высокая:** single host authority |

**Независимый исследовательский вывод:** распространённые инструменты решают *разные* задачи. Ни один не отменяет необходимости определить owner состояния и эффектов. Framework-first стратегия приведёт к техническому решению без согласованного продукта.

---

## 16. Источники: первичные материалы Strategy Box и AppDock

**Прямые действующие исходники и контракты:**

- [SB-1] [`stratbox/README.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/README.md), [`AGENTS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/AGENTS.md), [`_mw/AGENTS.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/AGENTS.md) — обязательный холодный вход, scope/owners/research authority.
- [SB-2] [`stratbox/pyproject.toml`](https://github.com/ForestTiger-GH/stratbox/blob/main/pyproject.toml), [`base/runtime.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/runtime.py), [`base/filestore/base.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/filestore/base.py), [`base/net/http.py`](https://github.com/ForestTiger-GH/stratbox/blob/main/src/stratbox/base/net/http.py).
- [SB-3] [`stratbox-windows/appdock/manifest.json`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/appdock/manifest.json), [`README.md`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/README.md), [`docs/architecture.md`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/docs/architecture.md), [`tests/smoke/test_repository_contract.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/tests/smoke/test_repository_contract.py).
- [SB-4] [`runtime/context.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/context.py), [`runtime/paths.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/paths.py), [`runtime/session_runtime.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/session_runtime.py), [`runtime/bootstrap.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/runtime/bootstrap.py).
- [SB-5] [`application/scenarios/runner.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/scenarios/runner.py), [`application/history/persistence.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/application/history/persistence.py), [`presentation/qt_desktop/scenario_coordinator.py`](https://github.com/ForestTiger-GH/stratbox-windows/blob/main/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py).
- [SB-6] [`docs/README.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/README.md), [`docs/architecture/README.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/architecture/README.md), [`responsibility-allocation.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/architecture/responsibility-allocation.md), [`dependency-direction.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/architecture/dependency-direction.md), [`system-context.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/architecture/system-context.md), [`docs/current-how/README.md`](https://github.com/ForestTiger-GH/stratbox/blob/main/docs/current-how/README.md).
- [SB-7] [`03-consolidation-research` role](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/README.md), [Work→Execution synthesis](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_04_work_to_execution_consolidated_research_2026-10-09.md), [Whole-System Target Architecture](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/03-consolidation-research/strategy_box_03_topic_09_whole_system_target_architecture_2026-10-09.md), [второе исследование Web/host](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_web_self_hosted_architecture_research_2026-10-07.md), [открытые Product questions](https://github.com/ForestTiger-GH/stratbox/blob/main/_mw/epochs-001-strategy-box-development/consolidation/questions/PRODUCT-QUESTIONS.md).
- [AD-1] [`AppDock/docs/architecture/overview.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/overview.md), [`manifest_authority.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/manifest_authority.md), [`root_model.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/root_model.md), [`activation_and_launch.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/activation_and_launch.md).
- [AD-2] [`AppDock observability TARGET_MODEL.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/observability/TARGET_MODEL.md), [`IMPLEMENTATION_STATUS.md`](https://github.com/ForestTiger-GH/AppDock/blob/main/docs/architecture/observability/IMPLEMENTATION_STATUS.md) — строго разделять целевое устройство и текущий validation gate.

**Внешние первоисточники / работы (проверены веб-поиском на дату исследования):**

- [E1] David L. Parnas (1972), *On the Criteria To Be Used in Decomposing Systems into Modules*, Communications of the ACM, 15(12), 1053–1058. DOI: https://doi.org/10.1145/361598.361623 .
- [E2] Alistair Cockburn (2005), *Hexagonal Architecture (Ports and Adapters)*: https://alistair.cockburn.us/hexagonal-architecture/ .
- [E4] OWASP Cheat Sheet Series, *Authorization Cheat Sheet*, deny by default / permissions on every request: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html ; *Authorization Patterns*: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Patterns_Cheat_Sheet.html .
- [E5] IETF RFC 9110 (2022), *HTTP Semantics*, включая § 15.3.3 `202 Accepted`: https://www.rfc-editor.org/rfc/rfc9110.html .
- [E6] OpenTelemetry Specification, *Context Propagation* / *Trace API*: https://opentelemetry.io/docs/specs/otel/context/api-propagators/ ; https://opentelemetry.io/docs/specs/otel/trace/api/ .
- [E7] CNCF CloudEvents 1.0, normative specification: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md .
- [E8] Celery, *Tasks / acknowledgements / idempotency / retry*: https://docs.celeryq.dev/en/stable/userguide/tasks.html .
- [E9] Martin Kleppmann (2016), *How to do distributed locking* (fencing token analysis): https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html .
- [E10] OpenAPI Initiative, *OpenAPI Specification v3.1.1*: https://spec.openapis.org/oas/v3.1.1.html .
- [E11] JSON Schema, *Draft 2020-12 Core*: https://json-schema.org/draft/2020-12/json-schema-core .
- [E12] WHATWG, *HTML Living Standard § 9.2 Server-sent events*: https://html.spec.whatwg.org/multipage/server-sent-events.html .
- [E13] Model Context Protocol, *Authorization 2026-07-28* (transport-scope): https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/authorization/index.mdx .
- [E14] Agent2Agent (A2A), *Protocol Specification*: https://a2a-protocol.org/latest/specification .
- [E15] Temporal, *Event History* и *Tasks*: https://docs.temporal.io/encyclopedia/event-history ; https://docs.temporal.io/tasks .
- [E16] SQLite, *Write-Ahead Logging*: https://www.sqlite.org/wal.html .

**Ограничение доказательности:** исследование выполнено по доступным исходникам и документам GitHub, предоставленной постановке DOCX, базовым исследованиям и внешним нормативным/инженерным материалам. Не запускались реальные AppDock installers, Windows GUI, multi-device host, нагрузочные испытания, fault-injection или полноценный test suite. Известные противоречия зафиксированы как статические; проектируемые контракты не претендуют на уже прошедшую сертификацию.

---

## 17. Окончательная архитектурная рекомендация

**Принять как направление дальнейшей разработки, после отдельного Product Decision:**

> Strategy Box — одна аналитическая система с независимым Python core и одной логической application authority на активное рабочее пространство. Локальное приложение может совмещать authority, вычислитель и UI в одном процессе. В hosted-профиле authoritative application state, допуск действий, исполнение и результаты принадлежат хосту, а Windows/Web/Android становятся его клиентами. AppDock остаётся внешним владельцем управляемой установки, Node, активации и платформенного health и подключается только по доказанным versioned contracts.

**Главное ближайшее действие — не создавать сервер, а выпрямить границу текущего Windows:** синхронизировать manifest/dependencies/tests, отделить application execution от Qt, определить минимальные operation/result/effect/reference contracts и показать их выполнение на headless test harness. После этого host становится естественным размещением **существующей осмысленной application authority**, а не созданием второй конкурирующей системы.

**Главный принцип экономии сложности:** один факт — один авторитетный владелец; один настоящий эффект — одно честное подтверждение или явно неизвестный исход; одна предметная способность — несколько допустимых способов вызова. Всё остальное — адаптеры и представления.
