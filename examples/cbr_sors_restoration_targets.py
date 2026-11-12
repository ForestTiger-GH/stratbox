"""Run SORS restoration with a caller-selected optimization budget."""

import argparse

from cbr_sors_restoration_colab import run, source_files
from stratbox.macrobanks import cbr_sors_restoration as sors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_paths_json")
    parser.add_argument("date")
    parser.add_argument("--max-targets", type=int, required=True)
    args = parser.parse_args()
    config = sors.SorsRunConfig(as_of_date=args.date, optimization=sors.SorsOptimizationConfig(
        mode="priority", max_targets=args.max_targets,
    ))
    print(run(source_files(args.source_paths_json), config).summary)


if __name__ == "__main__":
    main()
