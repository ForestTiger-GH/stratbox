# app

`app` — desktop surface Strategy Box, публикуемая как AppDock app surface.

На текущем этапе AppDock:
- подготавливает node-среду;
- синхронизирует внешний репозиторий;
- валидирует `appdock/manifest.json`;
- optional читает repo-local `appdock/preset.json` как product delivery preset;
- выбирает активную surface;
- передаёт приложению runtime-context через `APPDOCK_ACTIVATION_CONTEXT_PATH`;
- открывает `python -m app.entrypoints.appdock`.

`app` при этом не выполняет bootstrap shell-а и не управляет install/update средой. Он читает activation context, строит собственную product surface и работает как лёгкая рабочая поверхность над уже подготовленным node.

## Главный принцип

AppDock отвечает за:
- `system_root` и install context;
- runtime и trust-контур;
- activation context и session refs;
- health snapshot;
- выбор active app surface;
- запуск entrypoint.

`app` отвечает за:
- desktop shell surface;
- timeline / feed работы;
- **product operations** и их пользовательские формы;
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
- все собственные persistent operational-файлы кладутся в один app-owned system folder внутри `install_root`. По умолчанию это `install_root/stratbox-system`; если AppDock явно передал `install_root_system_dir`, приложение использует его. Внутри этой папки лежат `app.json`, `logs/`, `cache/`, `runtime/`.

### Standalone developer route

Для отладки доступен явный dev-route:

```bash
python -m app --standalone-dev-root "D:/Data"
```

В этом режиме не только selector/workspace, но и app-owned storage (`app.json`, `logs/`, `cache/`, `runtime/`) живут внутри указанного dev-root.

## Структурные слои

- `bootstrap/` — сборка runtime и запуск desktop surface.
- `core/` — тонкое ядро приложения: context, paths, config, version, logger.
- `platform/` — boundary к AppDock и desktop platform services.
- `product/` — product catalog, формы операций и execution layer.
- `runs/` — Qt-thread lifecycle для конкретных запусков.
- `shell/` — каркас окна и композиция desktop surface.
- `timeline/` — общая лента запусков, результатов и системных notices.
- `presence/` — online и участники.
- `workspace/` — selector, workspace root, diagnostics, FileStore.
- `system/` — системные действия surface.
- `state/` — runtime continuity, surface-state и пользовательские preferences.
- `resources/` — styles, workspace registry и прочие UI-ресурсы.
- `entrypoints/` — AppDock-facing точки входа.

## Surface приложения

Внутри `app` основные поверхности такие:
- `Timeline` — единая лента запусков и результатов;
- `Workspace` — схема, selector, status, diagnostics;
- `Operations` — продуктовый каталог действий Strategy Box;
- `Recent artifacts` — быстрый доступ к выходам;
- `Participants` — лёгкий список пользователей и фильтры по автору;
- `System diagnostics` — инженерная сводка среды.
