# cbr_archiver

`cbr_archiver` — домен `stratbox.macrobanks` для скачивания и сохранения исходных статистических файлов Банка России.

Домен deliberately простой:

- берет плоский список URL из отдельного реестра;
- скачивает файлы через общий сетевой слой `stratbox.base.net`;
- не редактирует содержимое Excel-файлов;
- не переименовывает отдельные файлы вручную;
- сохраняет результат через `FileStore` как ZIP или как отдельные файлы;
- возвращает итог выполнения в виде `CbrArchiverRunResult`.

## Где лежит список файлов

Основной список ссылок находится в файле:

```text
src/stratbox/macrobanks/cbr_archiver/registry.py
```

Новые ссылки добавляются в `DEFAULT_CBR_ARCHIVE_URLS` обычными строками:

```python
DEFAULT_CBR_ARCHIVE_URLS = (
    "https://www.cbr.ru/path/to/file_1.xlsx",
    "https://www.cbr.ru/path/to/file_2.xlsx",
)
```

Никакие описания, группы, коды и специальные имена в реестр добавлять не нужно. Это сделано специально, чтобы список можно было быстро пополнять вручную.

Имя сохраняемого файла определяется автоматически:

1. сначала из HTTP-заголовка `Content-Disposition`, если его вернул сервер;
2. иначе из последнего сегмента URL;
3. если в одном запуске два файла получили одинаковое имя, второму добавляется безопасный суффикс `_2`, чтобы файл не затерся.

Например ссылка `obs_tabl20%D1%81.xlsx` сохраняется с исходным именем из URL после декодирования, без добавления `_new`.

## Сохранение ZIP в Colab

```python
from stratbox.macrobanks.cbr_archiver import run_cbr_archiver

result = run_cbr_archiver(
    out_path="/content",
    output_mode="zip",
)

print(result.output_path)
print(result.to_dict())
```

По умолчанию будет создан файл:

```text
/content/CBR Collected Files.zip
```

## Сохранение пачки файлов в Colab

```python
from stratbox.macrobanks.cbr_archiver import run_cbr_archiver

result = run_cbr_archiver(
    out_path="/content",
    output_mode="files",
)

print(result.output_path)
print(result.saved_paths)
```

По умолчанию будет создана папка:

```text
/content/CBR Collected Files/
```

## Сохранение на сетевой диск

Путь передается как обычный `out_path`. Домен не работает с Samba напрямую: путь обрабатывает активный `FileStore`.

```python
from stratbox.macrobanks.cbr_archiver import run_cbr_archiver

result = run_cbr_archiver(
    out_path="DSR/ЦМиРАП/CBR",
    output_mode="zip",
)

print(result.output_path)
```

При установленном `stratbox-plugin` сохранение должно идти через корпоративный файловый транспорт. Вне контура будет использоваться локальный `LocalFileStore`.

## Режимы сохранения

`output_mode="zip"` сохраняет один архив.

`output_mode="files"` сохраняет отдельные файлы в папку.

Если в режиме `zip` передать `out_path` с расширением `.zip`, он будет использован как полный путь архива:

```python
run_cbr_archiver(
    out_path="/content/my_archive.zip",
    output_mode="zip",
)
```

Если в режиме `files` нужно использовать `out_path` как точную итоговую папку без подпапки `CBR Collected Files`, передайте `folder_name=None`:

```python
run_cbr_archiver(
    out_path="/content/my_cbr_files",
    output_mode="files",
    folder_name=None,
)
```

## Свой список ссылок на один запуск

Можно не менять реестр, а передать список URL прямо в функцию:

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

## Ошибки скачивания

По умолчанию `continue_on_error=True`: если часть файлов не скачалась, домен сохранит успешно скачанные файлы и запишет проблемные URL в `result.failed_urls`.

Если нужно прерывать запуск при первой ошибке:

```python
run_cbr_archiver(
    out_path="/content",
    output_mode="zip",
    continue_on_error=False,
)
```

## Перезапись файлов

По умолчанию `replace_existing=True`, чтобы повторный запуск мог обновить архив или файлы. Для более осторожного режима передайте:

```python
run_cbr_archiver(
    out_path="/content",
    output_mode="zip",
    replace_existing=False,
)
```
