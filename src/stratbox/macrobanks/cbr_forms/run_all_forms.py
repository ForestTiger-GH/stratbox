"""
CLI-сценарий запуска отчетных форм Банка России.

Пример запуска из корня репозитория:
  python -m stratbox.macrobanks.cbr_forms.run_all_forms --from 2024-01-01 --to 2024-12-01 --freq M --anchor start --banks legacy --forms all --out-dir .

Запуск только 805 формы:
  python -m stratbox.macrobanks.cbr_forms.run_all_forms --from 2024-01-01 --to 2026-01-01 --forms 805 --out-dir .
"""

from __future__ import annotations

import argparse

from stratbox.macrobanks.cbr_forms.api import run_all_forms_to_xlsx
from stratbox.macrobanks.cbr_forms.forms.registry import FORM_REGISTRY


def _parse_args() -> argparse.Namespace:
    """
    Функция разбирает параметры командной строки.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD (start)")
    parser.add_argument("--to", dest="date_to", required=False, default=None, help="YYYY-MM-DD (end). If omitted -> today")
    parser.add_argument("--freq", dest="freq", required=False, default="M", choices=["Y", "Q", "M", "W", "D"], help="Periods frequency")
    parser.add_argument("--anchor", dest="anchor", required=False, default="start", choices=["start", "end"], help="Period anchor")
    parser.add_argument("--banks", dest="banks_mode", required=False, default="legacy", choices=["legacy"], help="Bank set mode")
    parser.add_argument("--forms", dest="forms", required=False, default="all", help=f"Forms: all or comma-separated list. Available: {','.join(FORM_REGISTRY)}")
    parser.add_argument("--out-dir", dest="out_dir", required=False, default=".", help="Output directory")
    parser.add_argument("--timeout", dest="timeout", required=False, default=60, type=int, help="HTTP timeout seconds")
    parser.add_argument("--retries", dest="retries", required=False, default=2, type=int, help="HTTP retries")
    parser.add_argument("--backoff", dest="backoff", required=False, default=0.5, type=float, help="HTTP retry backoff")
    parser.add_argument("--min-bytes-ok", dest="min_bytes_ok", required=False, default=512, type=int, help="Minimal accepted archive size")
    parser.add_argument("--no-progress", dest="show_progress", action="store_false", help="Disable progress bars")
    parser.set_defaults(show_progress=True)
    return parser.parse_args()


def main() -> None:
    """
    Функция запускает обработку форм из командной строки.
    """
    args = _parse_args()
    run_all_forms_to_xlsx(
        date_from=args.date_from,
        date_to=args.date_to,
        freq=args.freq,
        anchor=args.anchor,
        banks_mode=args.banks_mode,
        out_dir=args.out_dir,
        forms=args.forms,
        timeout=args.timeout,
        retries=args.retries,
        backoff=args.backoff,
        min_bytes_ok=args.min_bytes_ok,
        show_progress=args.show_progress,
    )


if __name__ == "__main__":
    main()
