# app

`app` — launcher-managed desktop-приложение Strategy Box.

На текущем этапе `app` живёт в модели launcher-managed среды. Launcher разворачивает install-среду, выбирает `system_root`, передаёт business-root через `data_locator`, создаёт session contract и запускает `python -m app`. Приложение читает этот контракт, открывает GUI и работает как клиент launcher-managed session environment.

## Главный принцип

Launcher отвечает за:

- `system_root`;
- install/runtime среду;
- bootstrap и update payload;
- session creation;
- install metadata, user state, session state, active session projection и environment health snapshot;
- передачу handoff текущей сессии.

`app` отвечает за:

- GUI;
- рабочую схему поверх business-root;
- запуск задач;
- диагностику среды;
- перевод session в runtime-фазу (`running`);
- корректное завершение session при нормальном закрытии;
- смену `data_root` как обновление текущей session и пользовательского preferred locator.

## Режимы запуска

### Launcher-managed

Основной пользовательский маршрут:

- launcher готовит среду;
- launcher создаёт session state и handoff;
- `python -m app` читает `STRATBOX_LAUNCHER_HANDOFF_PATH`;
- приложение строит контекст от `system_root`, `data_root`, session state и environment health.

### Standalone developer route

Для отладки доступен явный dev-route:

```bash
python -m app --standalone-dev-root "D:/Data"
```

Этот маршрут предназначен для разработки и локальной проверки GUI вне launcher-а.

## Session-aware environment

Приложение теперь использует не только стартовый handoff JSON, но и связанные файлы среды:

- `user_state.json`;
- `sessions/<session_id>.json`;
- `shared/active_sessions/<session_id>.json`;
- `shared/health/environment_health.json`.

Эти файлы читаются через внутренний `session_env` client layer. Он позволяет:

- загрузить текущую session;
- увидеть preferred `data_locator` пользователя;
- прочитать актуальный snapshot здоровья среды;
- обновить current session при смене `data_root`;
- завершить session корректно при закрытии GUI.

## Рабочая схема

Внутри `app` корень данных больше не задаётся профилем. Вместо старой profile-model используется рабочая схема (`workspace schema`), которая описывает структуру каталогов и базовые требования поверх уже выбранного business-root.

## Change data root

В GUI есть отдельная кнопка смены `data_root`.

В launcher-managed сессии приложение обновляет:

- current `SessionState`;
- `UserState.preferred_data_locator`;
- active session projection;
- environment health snapshot.

После этого приложение пересобирает `AppContext` и обновляет состояние интерфейса.

Launcher config больше не является главным runtime source этой операции. Он остаётся bootstrap convenience layer.

## Degraded launch

Если install-среда готова, а business-root недоступен, приложение может стартовать в degraded mode.

В этом режиме:

- интерфейс открывается;
- статус среды показывает проблему с `data_root`;
- сервисные действия остаются доступны;
- задачи, которым нужен business-root, блокируются.

## Структура

- `core/` — handoff, session environment client, paths, context, GUI config, version.
- `workspace/` — рабочая схема, business-root diagnostics, FileStore.
- `tasks/` — registry, runner, adapters, task context.
- `gui/` — Qt GUI.
- `resources/` — task JSON, workspace schema, styles.


## Launcher-managed business root and workspace root

В launcher-managed режиме приложение различает выбранный пользователем business-root selector и реальный рабочий каталог. Если selector указывает на корень диска, приложение использует производный каталог `Strategy Box Data` и работает через него как через writable workspace root. Для системного диска используется каталог внутри профиля пользователя, а не корень диска.
