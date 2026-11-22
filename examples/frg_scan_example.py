"""Scan a selected FRG directory and show the latest recognized files."""

import argparse

from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains import frank_rg as frg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    result = frg.scan(frg.DiscoveryRequest("."), store=LocalFileStore(root=args.directory))
    if result.outcome != "succeeded":
        raise SystemExit(tuple(item.code for item in result.diagnostics))
    for selection in result.value.selections:
        paths = tuple(asset.entry.path for asset in selection.candidates)
        print(selection.source_id, selection.state, paths)


if __name__ == "__main__":
    main()
