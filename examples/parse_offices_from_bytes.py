"""Parse an original CBR HTML file using an explicit capture date."""

import argparse
from datetime import date
from pathlib import Path

from stratbox.base.filestore import LocalFileStore
from stratbox.base.ioapi.bytes import write_verified_bytes
from stratbox.data import SourcePayload
from stratbox.macrobanks.cbr_offices import ParseOfficesRequest, parse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("date", type=date.fromisoformat)
    parser.add_argument("--csv")
    args = parser.parse_args()
    payload = SourcePayload(args.html.read_bytes(), "text/html")
    result = parse(ParseOfficesRequest(payload, args.date))
    if result.outcome != "succeeded":
        raise SystemExit(", ".join(item.code for item in result.diagnostics))
    representation = result.value.representation
    if args.csv:
        stored = write_verified_bytes(
            args.csv,
            representation.data,
            store=LocalFileStore(),
            expected_sha256=representation.identity.sha256,
        )
        if stored.status not in {"stored", "already_present"}:
            raise SystemExit(stored.diagnostic_code)
    print(result.value.dataset_version.identity.sha256, representation.identity.sha256)


if __name__ == "__main__":
    main()
