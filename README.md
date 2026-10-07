# stratbox

`stratbox` — библиотечное ядро для прикладной аналитики и обработки данных в задачах Strategy Box.

Репозиторий содержит только core-слой:

- доменную бизнес-логику;
- нейтральную инфраструктуру;
- встроенные реестры и ресурсы;
- стабильные extension/runtime-контракты;
- примеры использования и тесты библиотеки.

Application/UI surfaces Strategy Box живут в отдельных репозиториях. Windows surface находится в `stratbox-windows`. AppDock является отдельным внешним проектом и в этот репозиторий не входит.

## Состав репозитория

- `src/stratbox/` — основной пакет библиотеки;
- `examples/` — примеры использования функций библиотеки;
- `scripts/` — инженерные проверки репозитория;
- `docs/` — документация по архитектуре и разработке core;
- `tests/` — smoke/unit тесты core-слоя;
- `_mw/` — центральное инженерное рабочее пространство Strategy Box: Research, provenance и материалы развития, не входящие в продуктовый core.

## Инженерное рабочее пространство

Точка входа для инженерной работы и Research — `_mw/AGENTS.md`. Это паспорт центрального workspace Strategy Box, физически размещённого в этом репозитории.

Workspace может содержать исследования нескольких implementation owners Strategy Box. Размещение Research в `stratbox/_mw` не переносит ownership кода: текущее состояние каждого surface определяется его собственным репозиторием.

Активная первая эпоха находится в `_mw/epochs-001-strategy-box-development/`. Текущие Research-ветки:

- `01-old-notes` — исторические и исходные материалы;
- `02-base-study` — свежее базовое исследование текущего Strategy Box и тематические Research Results;
- `03-consolidation-research` — консолидирующие исследования накопленного Research corpus перед отдельным Knowledge assembly.

Материалы `_mw/` сами по себе не меняют текущую продуктовую семантику и не входят в библиотечный пакет.

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

Установка с Solver для восстановления SORS:

```bash
python -m pip install -e ".[sors-restoration]"
```

## Что находится внутри пакета

`src/stratbox` разделён на несколько слоёв:

- `base` — файловый транспорт, IO API, сетевой слой, runtime-провайдеры, секреты и Excel-стили;
- `common` — общие утилиты без привязки к конкретному домену;
- `macrobanks` — прикладные домены для макроэкономических задач;
- `registries` — встроенные справочники и ресурсные таблицы;
- `text` — вспомогательные текстовые нормализаторы.

## Как это связано с `stratbox-windows`

`stratbox-windows` использует `stratbox` как внешнюю runtime-зависимость и отвечает за Windows application/surface Strategy Box.

При запуске через внешний managed runtime core должен устанавливаться как отдельная зависимость surface, а не копироваться внутрь surface-репозитория.

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
