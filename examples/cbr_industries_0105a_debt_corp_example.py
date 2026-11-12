"""Parse a caller-selected set of 01_05_A_Debt_corp workbooks."""

import argparse
from pathlib import Path

from stratbox.data import SourcePayload
from stratbox.macrobanks import cbr_industries as industries


def load(paths):
    inputs = tuple(industries.ParseIndustryRequest(SourcePayload(path.read_bytes()), path.name) for path in paths)
    result = industries.build_stream(industries.BuildIndustryStreamRequest(inputs))
    if result.outcome != "succeeded":
        raise RuntimeError(tuple(item.code for item in result.diagnostics))
    return result.value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbooks", nargs="+", type=Path)
    result = load(parser.parse_args().workbooks)
    print(result.df_stream.head())
