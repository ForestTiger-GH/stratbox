# CBR source collector (`stratbox.macrobanks.cbr_archiver`)

Домен `stratbox.macrobanks.cbr_archiver` предназначен для загрузки **исходных** статистических файлов Банка России по жёсткому встроенному списку.

Это домен **загрузки исходников**, а не домен парсинга или аналитики. Он:

- не открывает Excel-книги;
- не меняет содержимое файлов;
- не формирует сводные таблицы;
- не строит витрины;
- не переименовывает показатели.

Он только:

1. берёт встроенный реестр источников;
2. скачивает файлы через `stratbox.base.net`;
3. проверяет, что вместо файла не пришла HTML-страница;
4. определяет имя файла из заголовка или URL;
5. сохраняет исходники либо как ZIP, либо как каталог файлов;
6. возвращает структурированный результат загрузки.

---

## Публичный API

```python
from stratbox.macrobanks.cbr_archiver import (
    CbrSourceCollectRequest,
    collect_cbr_sources,
    list_cbr_sources,
)
```

Главная операция домена:

```python
collect_cbr_sources(request) -> CbrSourceCollectResult
```

Дополнительная read-only операция:

```python
list_cbr_sources() -> tuple[CbrRegistryItem, ...]
```

---

## Главные принципы

### 1. Жёсткий встроенный реестр

Источники лежат в `registry.py` как структурированный реестр `DEFAULT_CBR_SOURCES`.

Каждый элемент содержит:

- `source_id` — стабильный идентификатор источника;
- `url` — URL исходного файла;
- `title` — короткое пояснение для человека;
- `expected_file_name` — опциональное ожидаемое имя.

### 2. Файлы сохраняются как есть

Содержимое исходного файла не меняется. Домен не делает предобработку и не создаёт промежуточные Excel-файлы.

### 3. Сохранение идёт через `FileStore`

Один и тот же домен работает:

- в Google Colab;
- в локальном Jupyter;
- в desktop-приложении Strategy Box;
- в корпоративной среде через плагин.

### 4. Ошибки возвращаются как данные

Результат загрузки содержит не только успешные файлы, но и список `failures` с указанием:

- `source_id`;
- исходного URL;
- текста ошибки;
- HTTP-статуса, если он есть;
- числа использованных попыток;
- фактического URL, по которому шёл запрос.

Это позволяет app-слою и ноутбукам одинаково понимать, что именно не загрузилось.

---

## Request

Главный запрос:

```python
CbrSourceCollectRequest(
    target_path: str,
    save_mode: Literal["zip", "files"] = "zip",
    overwrite: bool = True,
    continue_on_error: bool = True,
    retry_attempts: int = 3,
    retry_backoff_sec: float = 0.5,
    timeout_sec: int = 60,
    min_bytes_ok: int = 512,
    try_case_variants: bool = True,
    plugin_only: bool = True,
    headers: Mapping[str, str] | None = None,
    show_progress: bool = True,
)
```

### Важное правило по `target_path`

`target_path` — это **точный итоговый путь результата**.

- Если `save_mode="zip"`, `target_path` должен оканчиваться на `.zip`.
- Если `save_mode="files"`, `target_path` должен указывать на каталог результата.

То есть домен не додумывает имя архива и не создаёт дополнительную подпапку по скрытым правилам.

---

## Result

```python
CbrSourceCollectResult(
    target_path: str,
    save_mode: Literal["zip", "files"],
    saved_paths: tuple[str, ...],
    collected_files: tuple[CbrCollectedFile, ...],
    failures: tuple[CbrSourceFailure, ...],
    requested_count: int,
    success_count: int,
    failure_count: int,
)
```

Главный смысл результата:

- `target_path` — куда сохранился итоговый результат;
- `saved_paths` — что реально записано;
- `collected_files` — какие файлы удалось собрать;
- `failures` — что не удалось скачать;
- `success_count` / `failure_count` — счётчики для app и notebook;
- `ok` — всё ли загрузилось без ошибок.

---

## Пример: ZIP-режим

```python
from stratbox.macrobanks.cbr_archiver import CbrSourceCollectRequest, collect_cbr_sources

request = CbrSourceCollectRequest(
    target_path="/content/CBR Collected Files.zip",
    save_mode="zip",
    overwrite=True,
    continue_on_error=True,
    retry_attempts=3,
)

result = collect_cbr_sources(request)
print(result.ok)
print(result.target_path)
print(result.success_count, result.failure_count)
```

---

## Пример: Files-режим

```python
from stratbox.macrobanks.cbr_archiver import CbrSourceCollectRequest, collect_cbr_sources

request = CbrSourceCollectRequest(
    target_path="/content/CBR Collected Files",
    save_mode="files",
    overwrite=True,
    continue_on_error=True,
)

result = collect_cbr_sources(request)
print(result.target_path)
print(result.saved_paths)
```

---

## Структура домена

```text
cbr_archiver/
  contracts.py   # request/result/failure contracts
  operations.py  # collect_cbr_sources, list_cbr_sources
  registry.py    # жёсткий встроенный список источников
  downloader.py  # скачивание, retry, case-variants, HTML guard
  save.py        # сохранение zip/files через FileStore
  file_names.py  # определение и уникализация имён файлов
```

---

## Практический смысл

`cbr_archiver` даёт воспроизводимый способ собрать исходные статистические файлы Банка России:

- без предобработки содержимого;
- в одинаковой форме из Colab, Jupyter, app и plugin-среды;
- с понятным итогом по успешным и неуспешным загрузкам.
