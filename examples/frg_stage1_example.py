"""
Пример запуска первого этапа FRG.

Сценарий:
- пользователь указывает путь к папке с файлами;
- пакет строит каталог, выбирает latest и запускает заглушки.
"""

from stratbox.macrobanks.frg import run_frg_stage1


ROOT_DIR = "."


result = run_frg_stage1(ROOT_DIR, recursive=False)

catalog_df = result["catalog"]
latest_df = result["latest"]
dispatch_df = result["dispatch"]

print("INFO: catalog rows =", len(catalog_df))
print("INFO: latest rows =", len(latest_df))
print("INFO: dispatch rows =", len(dispatch_df))
