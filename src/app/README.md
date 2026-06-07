# app

`app` — desktop product surface Strategy Box.

На текущем этапе AppDock:
- подготавливает node-среду;
- синхронизирует внешний репозиторий;
- валидирует `appdock/manifest.json`;
- optional читает repo-local `appdock/preset.json` как product delivery preset;
- выбирает активную surface;
- передаёт приложению runtime-context через `APPDOCK_ACTIVATION_CONTEXT_PATH`;
- открывает `python -m app.entrypoints.appdock`.

`app` при этом не управляет install/update средой. Он читает activation context, строит собственную product surface и работает как лёгкая рабочая поверхность над уже подготовленным node.

## Главный принцип

AppDock отвечает за:
- `system_root` и install context;
- runtime и trust-контур;
- activation context и session refs;
- health snapshot;
- выбор active app surface;
- запуск entrypoint.

`app` отвечает за:
- desktop product surface;
- timeline / feed работы;
- product operations и их пользовательские формы;
- запуск операций;
- workspace и диагностику среды;
- собственный `runtime_state.json`;
- лёгкий presence участников.

## Режимы запуска

### AppDock-managed

Основной пользовательский маршрут:
- AppDock готовит node;
- AppDock создаёт session surfaces и activation context;
- `python -m app.entrypoints.appdock` читает `APPDOCK_ACTIVATION_CONTEXT_PATH`;
- app-side activation context валидируется по major-версии (`1.x`), чтобы несовместимый контракт не принимался молча;
- приложение строит контекст от `workspace`, `refs`, `source_revision` и snapshot-ов;
- все persistent operational-файлы кладутся в один app-owned system folder внутри `install_root`. По умолчанию это `install_root/stratbox-system`; если AppDock явно передал `install_root_system_dir`, приложение использует его.

### Standalone developer route

Для отладки доступен явный dev-route:

```bash
python -m app --standalone-dev-root "D:/Data"
```

В этом режиме app-owned storage (`app.json`, `logs/`, `cache/`, `runtime/`) живёт внутри `<dev-root>/.strategy_box/system/`.

## Каноническая структура

- `entrypoints/` — точки входа surface.
- `runtime/` — runtime приложения: context, paths, config, logging, session-runtime, bootstrap.
- `platform/` — boundary к AppDock и desktop platform services.
- `application/` — product-layer, workspace, presence, timeline store и system-команды.
- `presentation/` — desktop UI, chat/feed, формы операций и Qt runner.
- `resources/` — styles, images и прочие статические ресурсы.

## Внутренние оси

### `runtime/`
Тонкий runtime-контур приложения:
- `context.py`
- `paths.py`
- `config.py`
- `logging.py`
- `version.py`
- `session_runtime.py`
- `user_preferences.py`
- `bootstrap.py`

### `platform/`
Boundary к внешней платформе:
- `platform/appdock/` — AppDock runtime contracts, entry bridge;
- `platform/desktop/` — desktop platform services.

### `application/`
Смысл продукта:
- `application/product/` — product catalog, формы, execution, операции;
- `application/workspace/` — selector, workspace root, diagnostics, FileStore;
- `application/presence/` — участники и online;
- `application/timeline/` — feed-модели и store;
- `application/system/` — системные команды surface.

### `presentation/`
Desktop-представление:
- `presentation/desktop/` — главное окно, Qt runner, composition root UI;
- `presentation/chat/` — chat/feed проекция;
- `presentation/forms/` — Qt-виджеты форм product operations;
- `presentation/timeline/` — Qt-виджеты feed/timeline.

## Surface приложения

Внутри `app` основные поверхности такие:
- `Timeline` — единая лента запусков и результатов;
- `Workspace` — схема, selector, status, diagnostics;
- `Operations` — продуктовый каталог действий Strategy Box;
- `Recent artifacts` — быстрый доступ к выходам;
- `Participants` — лёгкий список пользователей и фильтры по автору;
- `System diagnostics` — инженерная сводка среды.
