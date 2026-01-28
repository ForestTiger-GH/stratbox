"""
Пример: чтение Excel через классический pandas.

Назначение:
- использовать вне контура, локально
- показать "базовый" способ чтения без stratbox-инфраструктуры

Запуск:
  python scripts/pandas_read_excel_example.py --path "data/input.xlsx" --sheet 0
"""

from __future__ import annotations

import argparse

import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, help="Path to .xlsx file (local).")
    parser.add_argument("--sheet", default=0, help="Sheet name or index (default: 0).")
    args = parser.parse_args()

    df = pd.read_excel(args.path, sheet_name=args.sheet)
    print(f"INFO: read ok rows={len(df)} cols={len(df.columns)}")
    print("INFO: head:")
    print(df.head(5).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())