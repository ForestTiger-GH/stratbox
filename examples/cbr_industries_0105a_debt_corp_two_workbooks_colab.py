"""Produce two industry views from a caller-selected set of local workbooks."""

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
    stream = load(args.workbooks)
    for code in ("apk", "total"):
        result = industries.render_industry(industries.RenderIndustryRequest(
            stream, industries.Cbr0105ADebtCorpIndustryWorkbookRequest(industry_code=code),
        ))
        if result.outcome != "succeeded":
            raise SystemExit(tuple(item.code for item in result.diagnostics))
        artifact = result.value.representation
        saved = write_verified_bytes(f"{code}.xlsx", artifact.data, store=store, expected_sha256=artifact.identity.sha256)
        print(code, saved.status, saved.identity.sha256)


if __name__ == "__main__":
    main()
