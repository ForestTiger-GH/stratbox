"""
Минимальный отладочный запуск первого этапа Frank RG.

Скрипт полезен как шпаргалка для ручной проверки в ноутбуке или терминале.
"""

from __future__ import annotations

from stratbox.macrobanks.frank_rg import run_frank_rg_stage1


if __name__ == "__main__":
    root_dir = "."
    result = run_frank_rg_stage1(root_dir, recursive=False)

    print("INFO: catalog rows =", len(result["catalog"]))
    print("INFO: latest rows =", len(result["latest"]))
    print("INFO: dispatch rows =", len(result["dispatch"]))
