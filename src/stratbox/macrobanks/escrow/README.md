# Escrow (`stratbox.macrobanks.escrow`)

Домен `stratbox.macrobanks.escrow` предназначен для работы с ежемесячными Excel-публикациями ЦБ по финансированию долевого строительства и счетам эскроу.

Правильный смысл домена — не просто «собрать xlsx», а пройти четыре отдельные фазы:

1. получить структурированный список источников;
2. построить нормализованный исторический набор данных;
3. построить витринные таблицы по показателям;
4. экспортировать итоговый workbook как `.xlsx` или `.zip`.

---

## Публичный API

```python
from stratbox.macrobanks.escrow import (
    EscrowHistoryBuildRequest,
    EscrowViewBuildRequest,
    EscrowWorkbookExportRequest,
    build_escrow_history,
    build_escrow_views,
    discover_escrow_sources,
    export_escrow_workbook,
    run_escrow_export,
)
```

Главные операции домена:

- `discover_escrow_sources(...)` — найти источники;
- `build_escrow_history(request)` — построить исторический dataset;
- `build_escrow_views(history_result, request)` — построить витринные таблицы;
- `export_escrow_workbook(history_result, export_request)` — сохранить итоговый workbook;
- `run_escrow_export(...)` — удобный one-shot wrapper над полным экспортным сценарием.

---

## Канонические контракты

### Источники

- `EscrowSourceLink` — найденный источник со ссылкой и именем файла;
- `EscrowSourceDownloadResult` — успешно скачанный или прочитанный из кэша файл;
- `EscrowSourceFailure` — ошибка обработки одного источника.

### Исторический слой

- `EscrowHistoryBuildRequest` — параметры построения history dataset;
- `EscrowHistoryResult` — канонический результат построения истории.

Главный результат `EscrowHistoryResult` содержит:

- `source_links` — какие источники были найдены;
- `downloaded_sources` — какие исходники реально получены;
- `failures` — какие источники не удалось скачать или распарсить;
- `parsed_files` — результаты парсинга отдельных файлов;
- `df_long` — объединённый нормализованный long-поток;
- `dates`, `indicators`, `rows_long` — служебную сводку.

### Витринный слой

- `EscrowViewBuildRequest` — параметры построения витрин;
- `EscrowPivotPack` — итоговый набор pivot-таблиц, порядок строк, порядок дат и перечень показателей.

### Export-слой

- `EscrowWorkbookExportRequest` — параметры сохранения workbook;
- `EscrowExportResult` — итог экспорта `.xlsx` или `.zip`.

---

## Почему это сильнее старой модели

Старая модель думала про домен как про один большой сценарий `run_escrow_to_xlsx(...)`.

Новая модель разделяет смысл:

- источники — отдельно;
- history dataset — отдельно;
- витринные таблицы — отдельно;
- экспорт workbook — отдельно.

Это делает домен сильнее для:

- Jupyter и Colab;
- desktop-app слоя Strategy Box;
- будущего AppDock route/job слоя;
- повторного использования в корпоративном plugin-контуре.

---

## Источники и кэш

Если задан `source_cache_dir`, каждый скачанный Excel-файл сохраняется через активный `FileStore`.

Это полезно для:

- повторных запусков;
- отладки парсера;
- хранения копии исходников;
- работы с сетевым диском без отдельной Samba-логики.

Если `refresh=False` и файл уже есть в кэше, домен читает его из кэша без повторного скачивания.

---

## Ошибки источников

Домен поддерживает `source_error_policy`:

- `fail_fast` — остановиться на первой ошибке;
- `collect_partial` — собрать всё, что удалось, и вернуть failures как данные.

По умолчанию используется `fail_fast`, потому что для аналитики безопаснее явно знать, что история построена целиком.

---

## Режимы порядка строк

Поддерживаются:

- `latest` — порядок строк берётся из последнего доступного файла;
- `custom` — используется пользовательский список строк.

Режим `registry` из публичного основного API убран, пока для него нет реальной реализации.

---

## Пример: построить history dataset

```python
from stratbox.macrobanks.escrow import EscrowHistoryBuildRequest, build_escrow_history

history = build_escrow_history(
    EscrowHistoryBuildRequest(
        index_url="https://www.cbr.ru/statistics/bank_sector/equity_const_financing/",
        source_cache_dir="cache/escrow",
        show_progress=True,
    )
)

print(history.rows_long)
print(history.dates)
print(len(history.failures))
```

---

## Пример: построить workbook-экспорт

```python
from stratbox.macrobanks.escrow import (
    EscrowHistoryBuildRequest,
    EscrowViewBuildRequest,
    EscrowWorkbookExportRequest,
    build_escrow_history,
    export_escrow_workbook,
)

history = build_escrow_history(
    EscrowHistoryBuildRequest(
        index_url="https://www.cbr.ru/statistics/bank_sector/equity_const_financing/",
        source_cache_dir="cache/escrow",
    )
)

result = export_escrow_workbook(
    history,
    EscrowWorkbookExportRequest(
        out_path="outputs/Escrow Accounts.zip",
        archive=True,
    ),
    view_request=EscrowViewBuildRequest(regions_mode="latest"),
)

print(result.output_path)
```

---

## Пример: one-shot wrapper

```python
from stratbox.macrobanks.escrow import run_escrow_export

result = run_escrow_export(
    out_path="outputs/Escrow Accounts.xlsx",
    source_cache_dir="cache/escrow",
)

print(result.output_path)
```

---

## Структура домена

```text
escrow/
  contracts.py  # доменные contracts и request/result models
  operations.py # канонические публичные операции
  sources.py    # discover links на ежемесячные файлы
  download.py   # скачивание и кэширование исходников
  parser.py     # parsing одного xlsx в нормализованный long-flow
  rows.py       # распознавание строк витрины
  columns.py    # реестр показателей и сопоставление заголовков
  pivots.py     # построение витринных pivot-таблиц
  workbook.py   # сборка openpyxl workbook
  export.py     # сохранение xlsx/zip
```
