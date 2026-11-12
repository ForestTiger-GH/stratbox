"""Scan a selected FRG directory and show the latest recognized files."""

import argparse

from stratbox.base.filestore import LocalFileStore
from stratbox.macrobanks import frg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    result = frg.scan(frg.ScanRequest("."), store=LocalFileStore(root=args.directory))
    if result.outcome != "succeeded":
        raise SystemExit(tuple(item.code for item in result.diagnostics))
    print(result.value.latest)


if __name__ == "__main__":
    main()
