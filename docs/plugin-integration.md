# Plugin-интеграция

`stratbox` поддерживает две модели исполнения:

- локальную;
- plugin-backed.

Ключевая точка — `stratbox.base.runtime`.

## Как это работает

`get_providers()` выбирает провайдеры файлового доступа и секретов:

- сначала пытается загрузить plugin через entry points;
- если plugin недоступен, переходит на local fallback.

## Почему это важно

Доменные модули не должны импортировать plugin напрямую. Они должны работать через:

- `stratbox.base.filestore`
- `stratbox.base.ioapi`
- `stratbox.base.secrets`
- `stratbox.base.runtime`

## Полезные переменные окружения

- `STRATBOX_USE_PLUGIN`
- `STRATBOX_LOCAL_ROOT`
- `STRATBOX_DEBUG_PLUGIN`

## Целевая модель

В банковом контуре должен загружаться именно `stratbox` как core-репозиторий без AppDock-артефактов и без desktop surface. Корпоративные особенности должны подключаться отдельно через plugin.
