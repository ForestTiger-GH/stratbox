# Методы работы с файлами и каталогами (FileStore + ioapi)

Этот документ предназначен как **справочник** по базовым операциям чтения/записи файлов и управлению каталогами в экосистеме **Strategy Box (`stratbox`)**.

Ключевая идея: прикладной код (аналитика, расчёты, отчёты) использует единые методы `ioapi` и/или `FileStore`, а конкретная среда хранения выбирается через `runtime`:

- **Локальный режим**: работает с файловой системой машины (LocalFileStore)
- **Корпоративный режим** (через `stratbox-plugin`): работает с сетевым хранилищем, при этом пользовательский код остаётся тем же

---

## 1) Быстрый старт: что импортировать

### 1.1 Рекомендуемый импорт для файловых форматов

```python
from stratbox.base import ioapi as ia
```

Далее используются форматные модули:

- `ia.excel.read_df(...)`, `ia.excel.write_df(...)`
- `ia.csv.read_df(...)`, `ia.csv.write_df(...)`
- `ia.bytes.read_bytes(...)`, `ia.bytes.write_bytes(...)`
- и т.д.

### 1.2 Импорт FileStore (если нужны каталоги/rename/rmtree)

```python
from stratbox.base.runtime import get_filestore
fs = get_filestore()
```

`fs` — активный файловый стор (локальный или корпоративный), определённый `runtime`.

---

## 2) Понятие пути: «путь внутри FileStore»

Вызовы `ioapi` и `FileStore` принимают **строку-путь**, которая трактуется как путь внутри текущего активного FileStore.

Примеры:

- `reports/monthly/report.xlsx`
- `ABC/Main/Programs/file.xlsx`

### 2.1 Что важно для корпоративного режима (SMB)

Плагин выполняет нормализацию входного пути (для удобства пользователя):

- `\` и `\` → `/`
- `file:///C:\ABC\...` (копипаста из Excel) → приводится к пути внутри шары
- URL-экранирование декодируется (`%20` → пробел)
- если в строке присутствует имя шары, префикс до неё может быть обрезан

> Практика: в прикладном коде рекомендуется использовать “чистые” пути внутри хранилища, например `ABC/...`.

---

## 3) Таблица методов: файлы и каталоги

### 3.1 Операции чтения/записи файлов

| Задача | Рекомендуемый способ | Пример |
|---|---|---|
| Прочитать Excel в DataFrame | `ia.excel.read_df` | `df = ia.excel.read_df("ABC/Reports/in.xlsx")` |
| Записать DataFrame в Excel | `ia.excel.write_df` | `ia.excel.write_df("ABC/Reports/out.xlsx", df)` |
| Прочитать CSV в DataFrame | `ia.csv.read_df` | `df = ia.csv.read_df("data/in.csv")` |
| Записать DataFrame в CSV | `ia.csv.write_df` | `ia.csv.write_df("data/out.csv", df)` |
| Прочитать любой файл как bytes | `ia.bytes.read_bytes` | `b = ia.bytes.read_bytes("bin/file.bin")` |
| Записать bytes в файл | `ia.bytes.write_bytes` | `ia.bytes.write_bytes("bin/file.bin", b"...")` |

### 3.2 Операции с каталогами (FileStore)

| Задача | Метод FileStore | Комментарий |
|---|---|---|
| Создать каталог (включая родителей) | `fs.makedirs(path)` | В корпоративном режиме создаёт каталоги внутри шары |
| Список файлов/папок | `fs.listdir(path)` | Возвращает список имён (без полного пути) |
| Проверить существование | `fs.exists(path)` | В некоторых средах использует fallback-логику |
| Проверить «это папка?» | `fs.is_dir(path)` | Может определяться по listdir/stat |
| Проверить «это файл?» | `fs.is_file(path)` | Может определяться по read/stat |
| Удалить файл | `fs.remove(path)` | Для файлов |
| Удалить пустой каталог | `fs.rmdir(path)` | Для пустых папок |
| Удалить каталог рекурсивно | `fs.rmtree(path)` | Для деревьев каталогов |
| Переименовать/переместить | `fs.rename(src, dst)` | Для файла и каталога (в плагине есть fallback copy-tree + delete) |

---

## 4) Примеры: чтение/запись через ioapi

### 4.1 Excel: записать и прочитать DataFrame

```python
import pandas as pd
from stratbox.base import ioapi as ia

df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

ia.excel.write_df("ABC/Reports/out.xlsx", df)
df2 = ia.excel.read_df("ABC/Reports/out.xlsx")

print(df2.head())
```

### 4.2 CSV

```python
import pandas as pd
from stratbox.base import ioapi as ia

df = pd.DataFrame({"x": [10, 20]})

ia.csv.write_df("ABC/Exports/out.csv", df)
df2 = ia.csv.read_df("ABC/Exports/out.csv")

print(df2)
```

### 4.3 Сырые байты (универсально)

```python
from stratbox.base import ioapi as ia

ia.bytes.write_bytes("ABC/Temp/hello.bin", b"hello")
print(ia.bytes.read_bytes("ABC/Temp/hello.bin"))
```

---

## 5) Примеры: работа с каталогами (FileStore)

### 5.1 Базовый сценарий: mkdir → write/read → rename → rmtree

```python
from datetime import datetime
from stratbox.base.runtime import get_filestore
from stratbox.base import ioapi as ia

fs = get_filestore()

BASE_DIR = "ABC/Main/Programs/_stratbox_sandbox"
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

d = f"{BASE_DIR}/test_{stamp}/sub/a"
fs.makedirs(d)

# запись файла
p1 = f"{d}/hello.bin"
ia.bytes.write_bytes(p1, b"hello")

# чтение файла
print(ia.bytes.read_bytes(p1))

# rename файла
p2 = f"{d}/hello_renamed.bin"
fs.rename(p1, p2)

# rename каталога (в корпоративном плагине поддержан fallback-алгоритм)
src_dir = f"{BASE_DIR}/test_{stamp}"
dst_dir = f"{BASE_DIR}/test_{stamp}_RENAMED"
fs.rename(src_dir, dst_dir)

# удаление дерева
fs.rmtree(dst_dir)
```

### 5.2 Проверка: “существует ли папка”

```python
from stratbox.base.runtime import get_filestore
fs = get_filestore()

path = "ABC/Main/Programs"
print("exists:", fs.exists(path))
print("is_dir:", fs.is_dir(path))
print("entries:", fs.listdir(path)[:20])
```

---

## 6) Диагностика в корпоративном режиме (stratbox-plugin)

Если активирован плагин, корпоративный FileStore поддерживает диагностический вывод:

```python
from stratbox.base.runtime import get_filestore
fs = get_filestore()

if hasattr(fs, "debug_print_capabilities"):
    fs.debug_print_capabilities()
```

Диагностика показывает:

- какие методы реально доступны у корпоративного провайдера
- доступность fallback
- важные сигнатуры (mkdir/delete/upload/download/stream-методы)

Это полезно, когда в контуре часть методов урезана (например, нет `write_file`, нет `stat`, нет `rename`).

---

## 7) Практические рекомендации

1) В ноутбуках после переустановки пакета через `pip install --force-reinstall ...` рекомендуется **перезапуск kernel**, чтобы исключить импорт старой версии модулей из памяти.
2) Для корпоративного режима рекомендуется хранить параметры подключения в **приватном env-файле** (например, `~/keys/stratbox.env`).
3) Чтобы избежать интерактивных запросов, рекомендуется задавать ключи как минимум для:
   - `FILESTORE_HOST`, `FILESTORE_SHARE`, `FILESTORE_USER`, `FILESTORE_PASSWORD`
   - `FILESTORE_ROOT` (если используется)
   Допускается также использование ключей с префиксом `STRATBOX_` (в зависимости от SecretProvider).

---

## 8) Где смотреть исходные примеры

В репозитории `stratbox`:

- `scripts/ioapi_read_excel_example.py`
- `scripts/ioapi_write_excel_example.py`
- `scripts/pandas_read_excel_example.py`
- `scripts/pandas_write_excel_example.py`



