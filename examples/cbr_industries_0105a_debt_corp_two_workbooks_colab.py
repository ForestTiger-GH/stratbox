"""Produce two industry workbooks with a single verified snapshot admission."""

import argparse
from pathlib import Path

from cbr_industries_0105a_debt_corp_example import load
from stratbox.base.filestore import LocalFileStore
from stratbox.base.ioapi.bytes import write_verified_bytes
from stratbox.macrobanks import cbr_industries as industries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory")
    parser.add_argument("workbooks", type=Path, nargs="+")
    args = parser.parse_args()
    store = LocalFileStore(root=args.output_directory)
    stream = load(args.workbooks, selection=industries.IndustrySelection(("apk", "total")))
    result = industries.render_industries(
        industries.RenderIndustriesRequest(stream, ("apk", "total")),
    )
    if result.outcome != "succeeded":
        raise SystemExit(tuple(item.code for item in result.diagnostics))
    for workbook in result.value.items:
        artifact = workbook.representation
        saved = write_verified_bytes(
            f"{workbook.industry_code}.xlsx", artifact.data,
            store=store, expected_sha256=artifact.identity.sha256,
        )
        if saved.status not in {"stored", "already_present"}:
            raise OSError(saved.diagnostic_code)
        print(workbook.industry_code, saved.status, saved.identity.sha256)


if __name__ == "__main__":
    main()
