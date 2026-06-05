# app

`app` — desktop surface Strategy Box, публикуемая как AppDock app surface.

На текущем этапе AppDock:
- подготавливает node-среду;
- синхронизирует внешний репозиторий;
- валидирует `appdock/manifest.json`;
- выбирает активную app surface;
- передаёт приложению runtime-context через `APPDOCK_HANDOFF_PATH`;
- дополнительно может читать repo-local `appdock/distribution.json` как product delivery preset.
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
- app-side handoff валидируется по major-версии (`1.x`), чтобы несовместимый контракт не принимался молча;
- приложение строит контекст от `workspace`, `refs`, `source_revision` и snapshot-ов;
- все собственные persistent operational-файлы кладутся в один app-owned system folder внутри `install_root`. По умолчанию это `install_root/AppDock`; если AppDock явно передал `install_root_system_dir`, приложение использует его. Внутри этой папки лежат `app.json`, `logs/`, `cache/`, `runtime/`.

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
