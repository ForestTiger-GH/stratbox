# Escrow domain

Домен `stratbox.macrobanks.escrow` обрабатывает ежемесячные Excel-файлы ЦБ РФ по финансированию долевого строительства (счета эскроу).

## Что делает домен

1. Читает страницу ЦБ со списком Excel-файлов.
2. Скачивает месячные источники через общий сетевой слой `stratbox.base.net`.
3. При необходимости сохраняет исходные Excel-файлы в `source_cache_dir` через `FileStore`.
4. Парсит каждый файл в "длинный" поток данных:
   - `Регион`
   - `Показатель`
   - `Значение`
   - `Дата`
5. Строит сводные таблицы `регионы × даты` по каждому показателю.
6. Формирует итоговый `.xlsx` либо `.zip` с `.xlsx` внутри.

## Важные архитектурные решения

- Домен не использует прямой `open()`/`os.makedirs()` для постоянных файлов.
- Все постоянные файлы пишутся и читаются через `FileStore` и `ioapi.bytes/zip`.
- Домен не знает про `INBANK`; при наличии `stratbox-plugin` URL обрабатывается на уровне `base.net.url`.
- Режим `regions_mode='registry'` пока зарезервирован под будущий реестр регионов.

## Публичный вход

```python
from stratbox.macrobanks.escrow import run_escrow_to_xlsx
```

## Минимальный пример

```python
result = run_escrow_to_xlsx(
    out_path="outputs/Escrow Accounts.xlsx",
    source_cache_dir="cache/escrow",
)
print(result.output_path)
```
