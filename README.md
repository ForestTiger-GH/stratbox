# stratbox

`stratbox` — библиотечное ядро для прикладной аналитики и обработки данных в задачах Strategy Box.

Репозиторий содержит только core-слой:

- доменную бизнес-логику;
- нейтральную инфраструктуру;
- встроенные реестры и ресурсы;
- границу подключения внешнего plugin/runtime слоя;
- примеры использования и тесты библиотеки.

Репозиторий не содержит desktop-приложение, AppDock surface и GUI-зависимости. Windows surface живёт отдельно в репозитории `stratbox-windows`.

## Состав репозитория

- `src/stratbox/` — основной пакет библиотеки;
- `examples/` — примеры использования функций библиотеки;
- `scripts/` — инженерные проверки репозитория;
- `docs/` — документация по архитектуре, разработке и plugin-интеграции;
- `tests/` — smoke/unit тесты core-слоя.

## Установка

Базовая установка:

```bash
python -m pip install -e .
```

Установка с PDF-поддержкой:

```bash
python -m pip install -e ".[pdf]"
```

Установка с тестовым контуром:

```bash
python -m pip install -e ".[test]"
```

## Что находится внутри пакета

`src/stratbox` разделён на несколько слоёв:

- `base` — файловый транспорт, IO API, сетевой слой, runtime-провайдеры, секреты и Excel-стили;
- `common` — общие утилиты без привязки к конкретному домену;
- `macrobanks` — прикладные домены для макроэкономических задач;
- `registries` — встроенные справочники и ресурсные таблицы;
- `text` — вспомогательные текстовые нормализаторы.

## Как это связано с `stratbox-windows`

`stratbox-windows` использует `stratbox` как внешнюю runtime-зависимость. В AppDock-сценарии `stratbox` должен приезжать как bundled core dependency и устанавливаться в managed environment, а не лежать внутри surface-репозитория.

## Полезные команды

Smoke-проверка репозитория:

```bash
python scripts/check_release_integrity.py
python scripts/check_internal_imports.py
pytest -q
```

## Документация

- `docs/architecture.md`
- `docs/development.md`
- `docs/plugin-integration.md`
- `docs/examples.md`
