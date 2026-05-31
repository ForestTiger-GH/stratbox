# app

`app` — desktop-приложение Strategy Box, публикуемое как AppDock app target.

На текущем этапе AppDock:
- подготавливает node-среду;
- синхронизирует внешний репозиторий;
- валидирует `appdock-connector/connector.json`;
- выбирает активный app target;
- передаёт приложению runtime-context через `APPDOCK_HANDOFF_PATH`;
- открывает `python -m app.entrypoints.appdock`.

`app` при этом не выполняет bootstrap shell-а и не управляет install/update средой. Он читает handoff, строит собственный GUI-контекст и работает как product surface над уже подготовленным node.

## Главный принцип

AppDock отвечает за:
- `node_root`;
- runtime и trust-контур;
- handoff и session refs;
- health snapshot;
- выбор active app target;
- запуск entrypoint.

`app` отвечает за:
- GUI;
- рабочую схему поверх workspace selector;
- запуск сценариев;
- диагностику среды;
- собственный `app_state.json`;
- локальное состояние рабочей поверхности.

## Режимы запуска

### AppDock-managed

Основной пользовательский маршрут:
- AppDock готовит node;
- AppDock создаёт session surfaces и handoff;
- `python -m app.entrypoints.appdock` читает `APPDOCK_HANDOFF_PATH`;
- приложение строит контекст от `workspace`, `refs`, `target_revision` и snapshot-ов.

### Standalone developer route

Для отладки доступен явный dev-route:

```bash
python -m app --standalone-dev-root "D:/Data"
```

## Session-aware surfaces

Приложение читает AppDock surfaces через `session_env` client layer:
- `user_state.json`;
- `sessions/<session_id>/session.json`;
- `shared/active_sessions/<session_id>.json` — если опубликован;
- `health snapshot`;
- `app_state.json`.

При этом `app` не должен быть владельцем shell-level state. Основной обратный канал приложения — `app_state.json`, куда записываются:
- `active_view`;
- `workspace_state`;
- `last_scenario_*`;
- `recent_artifacts`;
- `clean_shutdown`;
- `resumable`.

## Workspace selector and workspace root

В AppDock-managed режиме приложение различает выбранный shell-ом selector и реальный рабочий каталог. Если selector указывает на корень диска, приложение использует производный каталог `Strategy Box Data` и работает через него как через writable workspace root. Для системного диска используется каталог внутри профиля пользователя, а не корень диска.

## Surface приложения

Внутри `app` основные поверхности такие:
- `Overview` — App target, revision, node/session, selector и workspace root;
- `Node and workspace` — schema, selector, status, diagnostics;
- `Scenarios` — реестр пользовательских сценариев;
- `Latest result` — итог последнего запуска;
- `Recent artifacts` — быстрый доступ к выходам и логам;
- `Execution log` — инженерный лог текущей session.

## Copy diagnostics

В интерфейсе доступна отдельная кнопка `Copy diagnostics`, которая копирует в буфер текущую сводку по node/workspace surface без отдельного JSON-экспорта.

## Структура

- `core/` — handoff, session surfaces, paths, context, GUI config, version, app state.
- `workspace/` — рабочая схема, diagnostics, FileStore.
- `scenarios/` — registry, runner, adapters, scenario context.
- `entrypoints/` — AppDock-facing точки входа.
- `gui/` — Qt GUI.
- `resources/` — scenario JSON, workspace schema, styles.
