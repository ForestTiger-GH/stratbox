# CBR archiver (`stratbox.macrobanks.cbr_archiver`)

Домен `stratbox.macrobanks.cbr_archiver` предназначен для скачивания и сохранения исходных статистических файлов Банка России.

Это домен архивирования исходников, а не домен парсинга. Он не читает Excel-книги, не меняет содержимое файлов, не пересчитывает показатели и не формирует аналитические таблицы. Его задача — взять заданный список ссылок, скачать файлы и сохранить их в воспроизводимом виде.

---

## Основной сценарий

Домен выполняет простой конвейер:

1. берет плоский список URL из реестра;
2. скачивает каждый файл через общий сетевой слой `stratbox.base.net`;
3. проверяет, что вместо файла не пришла HTML-страница;
4. определяет имя файла из HTTP-заголовка или URL;
5. уникализирует дублирующиеся имена;
6. сохраняет результат через `FileStore`:
   - либо как ZIP-архив;
   - либо как пачку исходных файлов в папке;
7. возвращает структурированный результат `CbrArchiverRunResult`.

---

## Главные принципы

### 1. Файлы сохраняются как есть

Домен не изменяет содержимое исходных файлов Банка России:

- не открывает Excel;
- не пересохраняет книгу;
- не меняет листы;
- не переименовывает показатели;
- не добавляет технические суффиксы к отдельным файлам.

Например, файл `obs_tabl20%D1%81.xlsx` сохраняется как `obs_tabl20с.xlsx` после обычного URL-декодирования, без добавления `_new`.

### 2. Реестр ссылок простой и плоский

Список источников намеренно сделан максимально простым, чтобы его было удобно пополнять вручную.

### 3. Сохранение идет через инфраструктуру `stratbox`

Домен не работает напрямую с Samba, локальными дисками или корпоративными путями. Он передает путь активному `FileStore`.

Это позволяет одинаково использовать домен:

- в Colab;
- локально;
- в Jupyter;
- в расширенной корпоративной среде;
- с сетевым диском через плагин.

### 4. Скачивание идет через общий сетевой слой

Каждый URL скачивается через:

```text
stratbox.base.net.download_bytes
```

Если в корпоративной среде URL должен идти через шлюз, это решается на уровне `base.net` и плагина, а не внутри домена.

---

## Реестр ссылок

Основной список находится в файле:

```text
src/stratbox/macrobanks/cbr_archiver/registry.py
```

Главная переменная:

```python
DEFAULT_CBR_ARCHIVE_URLS = (
    "https://www.cbr.ru/path/to/file_1.xlsx",
    "https://www.cbr.ru/path/to/file_2.xlsx",
)
```

Чтобы добавить новый файл Банка России, достаточно вставить новую строку URL в этот список.

Не нужно указывать:

- группу;
- код;
- описание;
- специальное имя файла;
- отдельные правила переименования.

Совместимое имя `DEFAULT_CBR_ARCHIVE_SOURCES` также присутствует, но фактически указывает на тот же плоский список URL.

---

## Имена файлов

Имя сохраняемого файла определяется так:

1. если источник задан как `CbrArchiveSource` и в нем явно указано `file_name`, используется это имя;
2. иначе имя берется из HTTP-заголовка `Content-Disposition`, если сервер его вернул;
3. иначе имя берется из последнего сегмента URL;
4. URL-encoded символы декодируются;
5. если имя пустое, используется техническое fallback-имя;
6. если в одном запуске два файла получили одинаковое имя, второй и последующие получают суффикс `_2`, `_3` и так далее.

Это защищает результат от случайного затирания файлов с одинаковыми именами.

---

## Альтернативные варианты URL

Для отдельных разделов сайта Банка России иногда встречаются отличия в регистре каталогов. Поэтому домен умеет пробовать альтернативные варианты URL для ключевых сегментов, например:

- `BankSector` / `banksector`;
- `Mortgage` / `mortgage`;
- `Loans_to_corporations` / `loans_to_corporations`.

Эта логика включена по умолчанию через параметр:

```python
try_case_variants=True
```

Сначала всегда пробуется исходный URL из реестра.

---

## Публичный API

Основной импорт:

```python
from stratbox.macrobanks.cbr_archiver import run_cbr_archiver
```

Главная функция:

```python
run_cbr_archiver(...)
```

Она возвращает `CbrArchiverRunResult`.

---

## Основные параметры

- `out_path` — папка или полный путь к ZIP-файлу;
- `output_mode` — режим сохранения: `"zip"` или `"files"`;
- `sources` — пользовательский список URL или `CbrArchiveSource` на один запуск;
- `archive_name` — явное имя ZIP-архива, если `out_path` не заканчивается на `.zip`;
- `archive_base_name` — базовое имя архива;
- `folder_name` — подпапка для режима `files`; если `None`, `out_path` считается итоговой папкой;
- `date_in_name` — добавлять дату к имени ZIP;
- `replace_existing` — разрешить перезапись существующего результата;
- `timeout`, `retries`, `backoff`, `min_bytes_ok`, `headers` — сетевые параметры;
- `plugin_only` — передается в сетевой слой для обработки URL через plugin-инфраструктуру;
- `try_case_variants` — пробовать альтернативные варианты регистра URL;
- `continue_on_error` — продолжать скачивание остальных файлов при ошибках;
- `show_progress` — показывать индикатор прогресса;
- `filestore` — явный `FileStore`, если нужно передать его вручную.

---

## Результат выполнения

`CbrArchiverRunResult` содержит:

- `output_path` — итоговый путь к архиву или папке;
- `output_mode` — режим сохранения;
- `saved_paths` — сохраненные пути;
- `downloaded_files` — имена скачанных файлов;
- `failed_urls` — URL, которые не удалось скачать;
- `total_sources` — всего источников в запуске;
- `downloaded_count` — сколько файлов скачано;
- `failed_count` — сколько файлов не скачано;
- `archive_name` — имя архива в ZIP-режиме;
- `ok` — свойство, равное `True`, если все источники скачались успешно.

Пример:

```python
result = run_cbr_archiver(out_path="/content", output_mode="zip")

print(result.ok)
print(result.output_path)
print(result.downloaded_count, result.failed_count)
print(result.failed_urls)
```

---

## Сохранение ZIP в Colab

```python
from stratbox.macrobanks.cbr_archiver import run_cbr_archiver

result = run_cbr_archiver(
    out_path="/content",
    output_mode="zip",
    archive_base_name="CBR Collected Files",
    date_in_name=False,
    replace_existing=True,
    continue_on_error=True,
    show_progress=True,
)

print("OK:", result.ok)
print("Output path:", result.output_path)
print("Downloaded:", result.downloaded_count)
print("Failed:", result.failed_count)
```

Итоговый файл:

```text
/content/CBR Collected Files.zip
```

Скачать архив из Colab на компьютер можно отдельной ячейкой:

```python
from google.colab import files

files.download("/content/CBR Collected Files.zip")
```

---

## ZIP с датой в имени

```python
result = run_cbr_archiver(
    out_path="/content",
    output_mode="zip",
    archive_base_name="CBR Collected Files",
    date_in_name=True,
)

print(result.output_path)
```

Пример имени:

```text
/content/CBR Collected Files 2026-05-27.zip
```

---

## Сохранение пачки файлов в Colab

```python
from stratbox.macrobanks.cbr_archiver import run_cbr_archiver

result = run_cbr_archiver(
    out_path="/content",
    output_mode="files",
    folder_name="CBR Collected Files",
    replace_existing=True,
)

print(result.output_path)
print(result.saved_paths)
```

Итоговая папка:

```text
/content/CBR Collected Files/
```

Если нужно использовать `out_path` как точную итоговую папку без добавления подпапки:

```python
result = run_cbr_archiver(
    out_path="/content/my_cbr_files",
    output_mode="files",
    folder_name=None,
)
```

---

## Сохранение пачки файлов на сетевой диск

Пример для расширенной среды с активным `FileStore` из плагина:

```python
from stratbox.macrobanks.cbr_archiver import run_cbr_archiver

result = run_cbr_archiver(
    out_path="ABC/Data/CBR/CBR Collected Files",
    output_mode="files",
    folder_name=None,
    replace_existing=True,
    continue_on_error=True,
    show_progress=True,
)

print("Output folder:", result.output_path)
print("Downloaded:", result.downloaded_count)
print("Failed:", result.failed_count)

for path in result.saved_paths:
    print(path)
```

Домен не разбирает Samba-путь самостоятельно. Путь передается активному `FileStore`, который отвечает за физическую запись.

---

## Свой список ссылок на один запуск

Можно не менять реестр, а передать список URL напрямую:

```python
result = run_cbr_archiver(
    out_path="/content",
    output_mode="zip",
    sources=[
        "https://www.cbr.ru/path/to/file_1.xlsx",
        "https://www.cbr.ru/path/to/file_2.xlsx",
    ],
)
```

Для расширенных сценариев можно передать объекты `CbrArchiveSource`, где указать явное имя файла или служебные поля. При обычном ручном пополнении реестра это не требуется.

---

## Обработка ошибок

По умолчанию:

```python
continue_on_error=True
```

Это означает: если часть файлов не скачалась, домен сохранит успешно скачанные файлы и запишет проблемные ссылки в `result.failed_urls`.

Если нужно остановить запуск при первой ошибке:

```python
run_cbr_archiver(
    out_path="/content",
    output_mode="zip",
    continue_on_error=False,
)
```

Если не скачался ни один файл, функция завершится ошибкой независимо от `continue_on_error`.

---

## Перезапись результата

По умолчанию:

```python
replace_existing=True
```

Это удобно для регулярного обновления архива или папки.

Если нужно запретить перезапись:

```python
run_cbr_archiver(
    out_path="/content",
    output_mode="zip",
    replace_existing=False,
)
```

В этом случае при существующем итоговом файле или файле внутри папки будет ошибка.

---

## Структура домена

```text
cbr_archiver/
  api.py         # публичная функция run_cbr_archiver
  downloader.py  # скачивание источников через base.net
  models.py      # модели источника, файла, ошибки и результата
  naming.py      # имена файлов, Content-Disposition, URL-decoding, уникализация
  output.py      # сохранение ZIP/files через FileStore/ioapi
  registry.py    # плоский список URL Банка России
```

---

## Ограничения текущей версии

1. Домен не проверяет структуру Excel-файлов и не читает их содержимое.
2. Реестр по умолчанию — плоский список URL без описаний и группировок.
3. Качество результата зависит от доступности сайта Банка России или настроенного корпоративного шлюза.
4. Если сайт возвращает HTML-страницу вместо файла, такой ответ отбрасывается как ошибка скачивания.

---

## Практический результат

`cbr_archiver` дает простой повторяемый способ собрать пачку исходных статистических файлов Банка России:

- для локальной работы в Colab;
- для сохранения на сетевой диск;
- для дальнейшей ручной или автоматической обработки;
- без изменения исходных файлов и без привязки домена к конкретной файловой среде.
