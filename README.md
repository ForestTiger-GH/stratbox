# Strategy Box (stratbox)

## Назначение

`stratbox` — библиотека на Python для стандартизации типовых задач анализа данных и прикладного IO (чтение/запись файлов разных форматов) в Jupyter Notebook и в скриптах.

Библиотека создаётся как **единая “коробка инструментов”**: она даёт общий интерфейс и единый стиль для работы с файлами и путями.

---

## Ключевые идеи

### 1) Единый IO API поверх FileStore

Рекомендуемый импорт:

```python
from stratbox.base import ioapi as ia
```

Далее используются модули:

- `ia.excel.read_df(...)`, `ia.excel.write_df(...)`
- `ia.csv.read_df(...)`, `ia.csv.write_df(...)`
- `ia.bytes.read_bytes(...)`, `ia.bytes.write_bytes(...)`
- и т.д.

Внутри эти операции выполняются **поверх FileStore** — абстракции “файлового пространства” (локального или внешнего).

### 2) FileStore: локально по умолчанию, расширяемо через провайдеры

`FileStore` — интерфейс, который умеет:

- читать/писать файлы (bytes или потоки),
- работать с каталогами (`makedirs`, `listdir`, `rename`, `rmtree` и т.д.),
- проверять существование (`exists`, `is_dir`, `is_file`, `stat`).

В “чистой” установке `stratbox` использует **локальный** `LocalFileStore`.

Если установлен и активирован внешний провайдер, тот же код начинает работать с **локальным хранилищем** — без изменения прикладной логики.

### 3) SecretProvider: параметры подключения без “секретов в коде”

Для интеграций и провайдеров часто нужны параметры подключения (логин, пароль, хост, share, токены и т.п.).  
`stratbox` закладывает принцип: **секреты не хранятся в коде** и не “зашиваются” в репозиторий.

За получение параметров отвечает `SecretProvider` (базовые реализации — из окружения и интерактивного ввода). Корпоративные реализации добавляются через плагин.

### 4) runtime: одна точка выбора режима (local / plugin)

Модуль `stratbox.base.runtime` решает:

- использовать ли провайдеры из плагина,
- или работать в локальном режиме.

Прикладной код не импортирует плагины напрямую.

---

## Установка

### Вариант A. Установка из PyPI (если доступно)

```bash
pip install stratbox
```

### Вариант B. Установка из репозитория (для разработки)

Из корня репозитория:

```bash
pip install -e .
```

> Режим `-e` удобен для разработки: изменения применяются сразу, без переустановки.

---

## Быстрый старт (локальный режим)

### Пример 1. Excel: запись и чтение DataFrame

```python
import pandas as pd
from stratbox.base import ioapi as ia

df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

ia.excel.write_df("out.xlsx", df)
df2 = ia.excel.read_df("out.xlsx")

print(df2.head())
```

### Пример 2. CSV

```python
import pandas as pd
from stratbox.base import ioapi as ia

df = pd.DataFrame({"x": [10, 20]})
ia.csv.write_df("data/out.csv", df)

df2 = ia.csv.read_df("data/out.csv")
print(df2)
```

### Пример 3. Сырые байты (любой формат)

```python
from stratbox.base import ioapi as ia

ia.bytes.write_bytes("bin/hello.bin", b"hello")
data = ia.bytes.read_bytes("bin/hello.bin")
print(data)
```

---

## Работа с каталогами (через FileStore)

Когда требуется создавать/переименовывать/удалять каталоги (например, при подготовке выходных витрин и выгрузок), рекомендуется использовать активный FileStore:

```python
from stratbox.base.runtime import get_filestore
fs = get_filestore()

fs.makedirs("exports/2026-02")
print(fs.listdir("exports"))
```

Подробный справочник по методам файлов и каталогов вынесен в документ:

- `docs/files_catalog_methods.md`

---

## Переменные окружения (настройка поведения)

### STRATBOX_AUTO_PIP

- `STRATBOX_AUTO_PIP=0` (по умолчанию): если не хватает опциональной зависимости — будет понятная ошибка с подсказкой, что установить.
- `STRATBOX_AUTO_PIP=1`: при отсутствии зависимости `stratbox` попробует поставить пакет через `pip` автоматически.

В Jupyter:

```python
import os
os.environ["STRATBOX_AUTO_PIP"] = "1"
# затем при необходимости перезапустить kernel
```

### STRATBOX_USE_PLUGIN

- `STRATBOX_USE_PLUGIN=1`: принудительная попытка загрузить провайдеры из плагина.
- `STRATBOX_USE_PLUGIN=0`: принудительный локальный режим.

Если переменная не задана, `runtime` обычно пытается использовать плагин “если он установлен и доступен”.

### STRATBOX_DEBUG_PLUGIN

- `STRATBOX_DEBUG_PLUGIN=1`: при проблемах загрузки плагина включает подробный traceback.

---

## Что входит в библиотеку

Основные модули `ioapi` (работают поверх FileStore):

### Табличные форматы

- Excel: `ia.excel` (xlsx/xlsm/xlsb/xls — в зависимости от доступных зависимостей)
- CSV: `ia.csv`
- DBF: `ia.dbf`

### Текст и “сырые байты”

- TXT: `ia.txt`
- XML: `ia.xml`
- Bytes: `ia.bytes`

### Документы, презентации, изображения

- DOCX: `ia.docx`
- PPTX: `ia.pptx`
- Images: `ia.images`

### Архивы

- ZIP: `ia.zip`
- RAR: `ia.rar` (если доступен инструментарий)
- Archives: `ia.archives`

---

## Зависимости и совместимость

### Версия Python

Ориентир: **Python 3.10+** (точные ограничения фиксируются в `pyproject.toml`).

### Опциональные зависимости (по форматам)

Некоторые форматы требуют дополнительных пакетов. Логика:

- по умолчанию — понятная ошибка с подсказкой `pip install ...`
- при `STRATBOX_AUTO_PIP=1` — попытка авто-установки (если разрешено и доступно)

Типичные зависимости:

- Excel xlsx/xlsm: `openpyxl`
- Excel xls: `xlrd` (чтение), `xlwt` (запись)
- Excel xlsb: `pyxlsb`
- DOCX: `python-docx`
- DBF: зависит от реализации (обычно `dbfread`)

---

## Архитектура проекта (для разработчиков)

- `stratbox/base/runtime.py` — выбор провайдеров (local/plugin)
- `stratbox/base/filestore/` — интерфейс FileStore + локальная реализация
- `stratbox/base/secrets/` — базовые провайдеры секретов
- `stratbox/base/ioapi/` — форматные модули (excel/csv/xml/bytes/…)
- `stratbox/base/utils/` — утилиты (optional deps и т.п.)

---

## Примеры в репозитории

В папке `scripts/`:

- `ioapi_read_excel_example.py`
- `ioapi_write_excel_example.py`
- `pandas_read_excel_example.py`
- `pandas_write_excel_example.py`

