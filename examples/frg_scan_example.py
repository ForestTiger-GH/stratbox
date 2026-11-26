"""Scan a caller-selected directory and show recognized delivered Frank reports."""
import argparse

from stratbox.capabilities.model.targets import FeedTarget, SeriesTarget
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.frank_rg.domain import DOMAIN
from stratbox.sdk import StrategyBox


def required(result, output):
    if result.outcome != "succeeded":
        raise RuntimeError(result.diagnostics)
    return result.output(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    with StrategyBox(providers={"filestore": LocalFileStore(root=args.directory)}) as box:
        inventory = required(box.invoke("command.material.list", inputs={"location": "."}), "inventory")
        listing = required(box.invoke("command.publication.scan", inputs={"index": inventory},
            target=FeedTarget("frank_rg.delivered_reports")), "listing")
        print("Inventory qualifications:", sorted(listing.assessment.qualifications))
        for source_id in DOMAIN.series:
            selection = required(box.invoke("command.issue.select", inputs={"listing": listing},
                target=SeriesTarget(source_id)), "selection")
            print(source_id, selection.assessment.status, tuple(asset.locator for asset in selection.entries))


if __name__ == "__main__":
    main()
