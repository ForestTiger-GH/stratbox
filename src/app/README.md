# app

`app` — desktop surface Strategy Box, публикуемая как AppDock app surface.

На текущем этапе AppDock:
- подготавливает node-среду;
- синхронизирует внешний репозиторий;
- валидирует `appdock-world/manifest.json`;
- выбирает активную app surface;
- передаёт приложению runtime-context через `APPDOCK_HANDOFF_PATH`;
- открывает `python -m app.entrypoints.appdock`.

`app` при этом не выполняет bootstrap shell-а и не управляет install/update средой. Он читает handoff, строит собственную product surface и работает как лёгкая рабочая поверхность над уже подготовленным node.

## Главный принцип

AppDock отвечает за:
- `system_root` and install context;
- runtime и trust-контур;
- handoff и session refs;
- health snapshot;
- выбор active app surface;
- запуск entrypoint.

`app` отвечает за:
- desktop shell surface;
- timeline / feed работы;
- каталог сценариев и launch composer;
- запуск сценариев;
- workspace и диагностику среды;
- собственный `app_state.json`;
- лёгкий presence участников.

## Режимы запуска

### AppDock-managed

Основной пользовательский маршрут:
- AppDock готовит node;
- AppDock создаёт session surfaces и handoff;
- `python -m app.entrypoints.appdock` читает `APPDOCK_HANDOFF_PATH`;
- приложение строит контекст от `workspace`, `refs`, `source_revision` и snapshot-ов;
- все собственные persistent operational-файлы кладутся прямо в `install_root`, без user-level каталогов и без дополнительных top-level имён Strategy Box.

### Standalone developer route

Для отладки доступен явный dev-route:

```bash
python -m app --standalone-dev-root "D:/Data"
```

## Структурные слои

- `foundation/` — маленькие базовые типы app surface.
- `bootstrap/` — сборка runtime и запуск desktop surface.
- `integrations/` — AppDock и platform adapters.
- `shell/` — каркас окна, top bar, sidebars, menus.
- `timeline/` — общая лента запусков, результатов и системных notices.
- `scenarios/` — каталог сценариев, JSON-spec, composer и launch request.
- `runs/` — lifecycle конкретных запусков.
- `presence/` — online и участники.
- `workspace/` — selector, workspace root, diagnostics, FileStore.
- `system/` — системные действия surface.
- `state/` — локальное состояние и пользовательские preferences.
- `resources/` — styles, scenario specs, workspace registry.
- `entrypoints/` — AppDock-facing точки входа.

## Surface приложения

Внутри `app` основные поверхности такие:
- `Timeline` — единая лента запусков и результатов;
- `Workspace` — схема, selector, status, diagnostics;
- `Scenarios` — реестр пользовательских сценариев;
- `Recent artifacts` — быстрый доступ к выходам;
- `Participants` — лёгкий список пользователей и фильтры по автору;
- `System diagnostics` — инженерная сводка среды.
