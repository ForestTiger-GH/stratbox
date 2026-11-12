"""Restore one SORS date using explicit source paths supplied in a JSON mapping."""

import argparse
from pathlib import Path
import json

from stratbox.base.filestore import LocalFileStore
from stratbox.base.ioapi.bytes import write_verified_bytes
from stratbox.macrobanks import cbr_sors_restoration as sors


def require_value(result):
    if result.outcome != "succeeded":
        raise RuntimeError(tuple(item.code for item in result.diagnostics))
    return result.value


def run(files, config):
    originals = require_value(sors.read_source_files(files, store=LocalFileStore()))
    return require_value(sors.restore(sors.RestoreSorsRequest(originals, config)))


def source_files(config_path):
    return sors.SorsSourceFiles(**json.loads(Path(config_path).read_text(encoding="utf-8")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_paths_json")
    parser.add_argument("date")
    parser.add_argument("output")
    args = parser.parse_args()
    restored = run(source_files(args.source_paths_json), sors.SorsRunConfig(as_of_date=args.date))
    workbook = require_value(sors.render_workbook(sors.RenderSorsRequest(restored))).representation
    saved = write_verified_bytes(args.output, workbook.data, store=LocalFileStore(),
                                 expected_sha256=workbook.identity.sha256)
    print(saved.status, saved.identity.sha256)


if __name__ == "__main__":
    main()
