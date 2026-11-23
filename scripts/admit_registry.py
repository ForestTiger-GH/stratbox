"""Admit one installed registry snapshot without executing its operations."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stratbox.operations import operation_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", choices=("metadata", "typed", "executable"), default="executable")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        admission = operation_catalog().admit(level=args.level)
        report = asdict(admission)
        report["admitted"] = admission.admitted
        encoded = json.dumps(report, sort_keys=True, indent=2) + "\n"
        if args.report is not None:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(encoded, encoding="utf-8")
        print(encoded, end="")
        return 0
    except (ValueError, OSError, ImportError, AttributeError) as error:
        print(f"Registry admission failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
