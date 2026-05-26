"""
Минимальный отладочный запуск первого этапа FRG.

Скрипт полезен как шпаргалка для ручной проверки в ноутбуке или терминале.
"""

from __future__ import annotations

from stratbox.macrobanks.frg import run_frg_stage1


if __name__ == "__main__":
    root_dir = "."
    result = run_frg_stage1(root_dir, recursive=False)

    print("INFO: catalog rows =", len(result["catalog"]))
    print("INFO: latest rows =", len(result["latest"]))
    print("INFO: dispatch rows =", len(result["dispatch"]))
