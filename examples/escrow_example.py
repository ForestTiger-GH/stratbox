"""Build escrow views from explicit workbook inputs."""

import argparse
from pathlib import Path

from stratbox.base.filestore import LocalFileStore
from stratbox.base.ioapi.bytes import write_verified_bytes
from stratbox.data import SourcePayload
from stratbox.macrobanks import escrow


def require_value(result):
    if result.outcome != "succeeded":
        raise RuntimeError(tuple(item.code for item in result.diagnostics))
    return result.value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    parser.add_argument("sources", nargs="+", type=Path)
    args = parser.parse_args()
    inputs = tuple(escrow.ParseEscrowRequest(SourcePayload(path.read_bytes()), path.name) for path in args.sources)
    history = require_value(escrow.build_history(escrow.EscrowHistoryBuildRequest(inputs)))
    views = require_value(escrow.build_views(escrow.BuildEscrowViewsRequest(history)))
    artifact = require_value(escrow.render_workbook(views))
    saved = write_verified_bytes(args.output, artifact.data, store=LocalFileStore(),
                                 expected_sha256=artifact.identity.sha256)
    print(saved.status, saved.identity.sha256)


if __name__ == "__main__":
    main()
