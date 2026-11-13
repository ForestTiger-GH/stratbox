"""Run the SORS strict and crosswalk feasibility passes on selected sources."""

import argparse

from cbr_sors_restoration_colab import require_value, run, source_files
from stratbox.macrobanks import cbr_sors_restoration as sors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_paths_json")
    parser.add_argument("date")
    args = parser.parse_args()
    strict = run(source_files(args.source_paths_json), sors.SorsRunConfig(as_of_date=args.date))
    result = require_value(sors.run_crosswalk(sors.CrosswalkSorsRequest(
        strict, sors.SorsCrosswalkConfig(mode="feasibility"),
    )))
    print(result.status, result.crosswalk_run_id)


if __name__ == "__main__":
    main()
