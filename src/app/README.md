
# app

`app` — launcher-managed desktop-приложение Strategy Box.

На текущем этапе `app` больше не выбирает корень данных самостоятельно. В обычном пользовательском маршруте этот корень передает `stratbox-launcher` через session handoff. Приложение читает handoff, строит рабочий контекст и открывает GUI поверх уже выбранного business-root.

## Главный принцип

Launcher отвечает за:

- `system_root`;
- install/runtime среду;
- bootstrap и update payload;
- `data_root` как business-root;
- handoff текущей сессии.

`app` отвечает за:

- GUI;
- рабочую схему поверх business-root;
- запуск задач;
- диагностику среды;
- отображение launcher-managed состояния.

## Режимы запуска

### Launcher-managed

Основной пользовательский маршрут:

- launcher готовит среду;
- launcher передает handoff;
- `python -m app` читает `STRATBOX_LAUNCHER_HANDOFF_PATH`;
- приложение строит контекст от `system_root`, `data_root`, trusted commit и launcher mode.

### Standalone developer route

Для отладки доступен явный dev-route:

```bash
python -m app --standalone-dev-root "D:/Data"
```

Этот маршрут предназначен для разработки и локальной проверки GUI вне launcher-а.

## Рабочая схема

Внутри `app` корень данных больше не задается профилем. Вместо старой profile-model используется рабочая схема (`workspace schema`), которая описывает структуру каталогов и базовые требования поверх уже выбранного business-root.

## Change data root

В GUI есть отдельная кнопка смены `data_root`.

В launcher-managed сессии приложение обновляет:

- launcher config;
- launcher handoff текущей сессии;

затем пересобирает `AppContext` и обновляет состояние интерфейса.

## Degraded launch

Если install-среда готова, а business-root недоступен, приложение может стартовать в degraded mode.

В этом режиме:

- интерфейс открывается;
- статус среды показывает проблему с `data_root`;
- сервисные действия остаются доступны;
- задачи, которым нужен business-root, блокируются.

## Структура

- `core/` — handoff, paths, context, GUI config, version.
- `workspace/` — рабочая схема, business-root diagnostics, FileStore.
- `tasks/` — registry, runner, adapters, task context.
- `gui/` — Qt GUI.
- `resources/` — task JSON, workspace schema, styles.
