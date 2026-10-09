# Current HOW — Windows application: запуск, сценарий, история и фоновые состояния

**Статус:** ограниченный, доказанный статическим исходным кодом срез. Полное исследование UI, сетевого состояния и готовности не закрыто.  
**Implementation owner:** `ForestTiger-GH/stratbox-windows`, **exact baseline** `959e9c4ce1441124af5111c1e025041714e04d3b`.  
**Evidence class:** точные файлы исходного кода и декларативного манифеста; успешный runtime execution и CI не подтверждены.

## Реально заявленная поставка

Манифест декларирует interactive `desktop` surface, стартовое представление `scenario_chat`, среду `world` для двух связанных Python distributions, локальный foreground launch на Windows, preflight через тот же entrypoint с аргументом `--diagnose`, а также две общие surface-capability декларации об артефактах и участниках. Это **декларации manifest**, не доказательство каждого поведения. [Manifest](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json); [package metadata](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/pyproject.toml).

**Версионная точность:** версия Connector Manifest = `4.0`, activation contract в `surfaces[0].activation` = `4.0`. Самостоятельную версию Activation Context нельзя выводить из этих двух полей; она принадлежит соответствующему runtime contract. `world_version` и `stratbox-windows` package = `0.1.0`, manifest version requested for core = `0.2.1`. Эти поля не подтверждают установленную версию core.

## Activation boundary

Модуль entrypoint читает Activation Context, требует `world_id == "stratbox"` и `active_surface_id == "desktop"`, проверяет наличие двух runtime package bindings с назначенными package IDs и общую `environment_id`. При `AppConfigError` выводит управляемую ошибку и возвращает exit code `2`; при успехе вызывает основной application entry. [Прямая реализация](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/adapters/appdock/entry.py).

Это граница Strategy Box как потребителя внешнего platform context. Работа платформы по подготовке окружения, конкретная install/recovery политика и будущие удалённые возможности принадлежат своему внешнему владельцу.

## Runtime composition

`build_runtime(context)` создаёт application registries, хранилища cases/events/artifacts/logs/assignments, in-memory background state, preferences, session/platform adapters; затем читает JSON history и создаёт `ScenarioCoordinator` через прямой импорт из `presentation.qt_desktop`. Следовательно, **сегодня** bootstrap не является полностью GUI-toolkit-independent: Qt desktop concrete type участвует в runtime composition. [Прямая реализация](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py).

## Сценарий как последовательность шагов

`run_scenario()` переводит case в `running`, публикует события, проходит упорядоченные step specs, преобразует параметры через `params_map` и `params_override`, вызывает `run_operation()`, преобразует output paths в artifact records и записывает log record при наличии operation log. При `error_policy == 'fail_fast'` останавливается на неуспешном step; в остальных случаях продолжает последовательность. Терминальное событие и статус фиксируются в модели case. [Прямая реализация](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py).

**Важная граница семантики:** данный runner сам по себе не реализует устойчивую очередь задач, параллельное исполнение, долговременные leases или достоверную отмену внешних эффектов. Точная политика coordinator проверяется отдельно; модель `cancelled` или UI-признак фона не подтверждает работающую отмену.

## Persistence: recent context, не транзакционная истина

`HistoryPersistenceService` разносит cases/events/artifacts/logs/assignments по пяти JSON-файлам и восстанавливает только записи, которые могут быть декодированы соответствующими моделями. При ошибке чтения/JSON сервис молча возвращает пустой список. Запись каждого файла идёт через `Path.write_text`; здесь **нет** атомарной транзакции пяти объектов, явной блокировки или строгой ошибки чтения повреждённого state. Это файловая недолговечная проекция для возобновления desktop context, а не гарантированная authoritative event database. [Прямая реализация](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py).

## Background-process state ≠ executor

`BackgroundProcessStore` создаёт состояния `idle/disabled` по реестру, позволяет менять enabled/status, фиксировать запуск/результат/ошибку и возвращать активные состояния. В этом классе **нет** scheduler loop, worker dispatch или durable trigger persistence. Следовательно, его API доказывает наличие модели и локального store, но не работающий background execution service. [Прямая реализация](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/store.py).

## Явно выявленное несоответствие: тест ↔ манифест

Checked-in smoke test ожидает `contract_version == '3.0'` и словарь `package_identity`, тогда как manifest определяет `4.0` и `package_requirement`. Эти утверждения логически несовместимы в указанном baseline. Это **статическое обнаружение гарантированного assertion mismatch**, а не отчёт о фактическом запуске pytest. [Smoke test](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/tests/smoke/test_repository_contract.py); [Manifest](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/appdock/manifest.json).

## Границы неизвестного и повторная проверка

Фактическое присутствие внешней платформы, состояние живого узла, сохранность выходных файлов, атомарность стороннего хранилища, реальные API-responses, lifecycle Qt-компонента, доступность приложения на иных ОС и полнота пользовательской панели являются отдельными evidence tasks. Пересмотр обязателен при изменении перечисленных implementation files, tests, манифеста, runtime assumptions или при новом подтверждённом execution evidence.
