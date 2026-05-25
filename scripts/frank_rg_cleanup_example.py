"""
Пример запуска зачистки каталога Frank RG.

Сценарий:
- пользователь указывает путь к папке с файлами;
- пакет готовит план операций без захода во вложенные папки;
- затем по желанию выполняет копирование/переименование и удаление.
"""

from stratbox.macrobanks.frank_rg import run_frank_rg_cleanup


ROOT_DIR = "."
DELETE_OTHERS = False
EXECUTE = False


result = run_frank_rg_cleanup(
    ROOT_DIR,
    delete_others=DELETE_OTHERS,
    execute=EXECUTE,
)

catalog_df = result["catalog"]
latest_df = result["latest"]
plan_df = result["plan"]
execution_df = result["execution"]

print("INFO: catalog rows =", len(catalog_df))
print("INFO: latest rows =", len(latest_df))
print("INFO: plan rows =", len(plan_df))
print("INFO: execution rows =", len(execution_df))
