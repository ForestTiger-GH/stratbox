"""
Пример: запись Excel через stratbox.base.ioapi.

Плюс:
- один код для local и corp (если установлен stratbox-plugin)

Запуск:
  python scripts/ioapi_write_excel_example.py --out "data/output.xlsx"
"""

from __future__ import annotations

import argparse

import pandas as pd

from stratbox.base import runtime
from stratbox.base import ioapi as ia


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output path for .xlsx file (local or corp).")
    args = parser.parse_args()

    providers = runtime.get_providers()
    print(f"INFO: providers source = {providers.source}")

    df = pd.DataFrame(
        {
            "A": [1, 2, 3],
            "B": ["one", "two", "three"],
        }
    )

    ia.excel.write_df(args.out, df)
    print(f"INFO: write ok path={args.out} rows={len(df)} cols={len(df.columns)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())