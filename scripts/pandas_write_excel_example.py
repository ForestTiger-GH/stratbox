"""
Пример: запись Excel через классический pandas.

Назначение:
- использовать вне контура, локально
- показать "базовый" способ записи без stratbox-инфраструктуры

Запуск:
  python scripts/pandas_write_excel_example.py --out "data/output.xlsx"
"""

from __future__ import annotations

import argparse

import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output path for .xlsx file (local).")
    args = parser.parse_args()

    df = pd.DataFrame(
        {
            "A": [1, 2, 3],
            "B": ["one", "two", "three"],
        }
    )

    df.to_excel(args.out, index=False)
    print(f"INFO: write ok path={args.out} rows={len(df)} cols={len(df.columns)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())