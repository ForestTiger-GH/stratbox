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
- рабочую схему поверх data-root selector;
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

Этот маршрут предназначен для разработки и локальной проверки GUI вне AppDock.

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
- `warnings`;
- `clean_shutdown`;
- `resumable`.

## Рабочая схема

Внутри `app` корень данных больше не задаётся profile-model. Используется рабочая схема (`workspace schema`), которая описывает структуру каталогов поверх выбранного data-root selector.

## Change data root

В GUI есть отдельная кнопка смены `data_root`.

В AppDock-managed режиме приложение обновляет только свой `app_state.json` и пересобирает локальный `AppContext`. Оно не должно напрямую владеть user/session/health state shell-а.

## Degraded launch

Если node готов, а data-root selector недоступен, приложение может стартовать в degraded mode.

В этом режиме:

- интерфейс открывается;
- статус среды показывает проблему с `data_root`;
- сервисные действия остаются доступны;
- сценарии, которым нужен рабочий каталог, блокируются.

## Структура

- `core/` — handoff, session surfaces, paths, context, GUI config, version.
- `workspace/` — рабочая схема, diagnostics, FileStore.
- `tasks/` — registry, runner, adapters, task context.
- `entrypoints/` — AppDock-facing точки входа.
- `gui/` — Qt GUI.
- `resources/` — task JSON, workspace schema, styles.

## Data root selector and workspace root

В AppDock-managed режиме приложение различает выбранный shell-ом data-root selector и реальный рабочий каталог. Если selector указывает на корень диска, приложение использует производный каталог `Strategy Box Data` и работает через него как через writable workspace root. Для системного диска используется каталог внутри профиля пользователя, а не корень диска.
