# Strategy Box

Strategy Box — desktop surface для управления аналитическими сценариями поверх AppDock-managed рабочей среды.

Текущая модель приложения — scenario-first:

- пользователь выбирает сценарий;
- сценарий состоит из одной или нескольких операций;
- запуск создаёт единый рабочий кейс;
- центральный чат показывает кейсы как динамические сообщения;
- правая выезжающая панель показывает детали: логи, артефакты и параметры;
- AppDock получает актуальное runtime-состояние surface.

## Запуск

```bash
PYTHONPATH=src python -m app --standalone-dev-root ./.tmp/dev-workspace
```

Диагностика:

```bash
PYTHONPATH=src python -m app --standalone-dev-root ./.tmp/dev-workspace --diagnose
```

## AppDock connector

`appdock/manifest.json` объявляет surface `stratbox.desktop` с entry view `scenario_chat` и набором declared views для сценарного чата, workspace, сценариев, фоновых процессов, участников, логов, артефактов, параметров и диагностики.
