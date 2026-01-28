"""
Пример: чтение Excel через stratbox.base.ioapi.

Плюс:
- один код для local и corp (если установлен stratbox-plugin)

Запуск:
  python scripts/ioapi_read_excel_example.py --path "data/input.xlsx" --sheet 0
"""

from __future__ import annotations

import argparse

from stratbox.base import runtime
from stratbox.base import ioapi as ia


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, help="Path to .xlsx file (local or corp).")
    parser.add_argument("--sheet", default=0, help="Sheet name or index (default: 0).")
    args = parser.parse_args()

    providers = runtime.get_providers()
    print(f"INFO: providers source = {providers.source}")

    df = ia.excel.read_df(args.path, sheet_name=args.sheet)
    print(f"INFO: read ok rows={len(df)} cols={len(df.columns)}")
    print("INFO: head:")
    print(df.head(5).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())