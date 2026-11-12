"""Collect explicitly selected official files and save an original-byte ZIP."""

import argparse

from stratbox.base.ioapi.bytes import write_verified_bytes
from stratbox.base.runtime import local_providers
from stratbox.macrobanks import cbr_file_collector as collector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    parser.add_argument("source_ids", nargs="+")
    args = parser.parse_args()
    providers = local_providers()
    result = collector.collect_raw(collector.CollectFilesRequest(tuple(args.source_ids)), transport=providers.http)
    if result.outcome != "succeeded":
        raise SystemExit(tuple(item.code for item in result.diagnostics))
    packed = collector.prepare_archive(collector.PrepareArchiveRequest(result.value.completed))
    if packed.outcome != "succeeded":
        raise SystemExit(tuple(item.code for item in packed.diagnostics))
    artifact = packed.value
    saved = write_verified_bytes(args.output, artifact.data, store=providers.filestore,
                                 expected_sha256=artifact.identity.sha256)
    print(saved.status, saved.identity.sha256)


if __name__ == "__main__":
    main()
