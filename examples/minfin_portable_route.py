"""Process an explicit local fiscal workbook through the standard SDK.

    python examples/minfin_portable_route.py budget.xlsx 2026-11-01 ./minfin-output \
        --series minfin.fedbud.annex3.monthly

The issue is publication context. Economic dates come from the workbook headers.
The example performs no network requests; document sources need separately
reviewed field geometry and are outside this workbook example.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material


def accepted(box, command, output, *, inputs, target=None, parameters=None):
    result = box.invoke(command, target=target, inputs=inputs, parameters=parameters or {})
    if result.outcome != "succeeded":
        raise RuntimeError(f"{command}: {result.diagnostics}")
    return result.output(output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("issue", type=date.fromisoformat)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--series", default="minfin.fedbud.annex3.monthly")
    parser.add_argument("--format", choices=("csv", "json", "jsonl"), default="csv")
    args = parser.parse_args(argv)
    fmt = args.source.suffix.lower().lstrip(".")
    if fmt not in {"xlsx", "xls"}:
        raise ValueError("This example requires a supplied XLS/XLSX workbook")
    with args.source.open("rb") as stream:
        data = stream.read(30_000_001)
    if len(data) > 30_000_000:
        raise ValueError("The supplied workbook exceeds the example byte limit")
    original = Material(data, "application/octet-stream", args.series,
        metadata={"issue_id": args.issue.isoformat()})
    args.destination.mkdir(parents=True, exist_ok=True)
    files = LocalFileStore(str(args.destination.resolve()))
    with StrategyBox(providers={"filestore": files}) as box:
        record = box.sources.source(args.series)
        if not args.series.startswith("minfin.") or fmt not in record.publication.formats:
            raise ValueError("Unknown Minfin source series")
        source_ref = accepted(box, "command.artifact.commit", "reference",
            inputs={"material": original, "destination": "originals"})
        source = accepted(box, "operation.series.extract_workbook", "dataset", target=args.series,
            inputs={"material": original, "issue": {"issue_id": args.issue.isoformat()}},
            parameters={"format": fmt})
        integrated = accepted(box, "command.observations.align", "dataset", target=args.series,
            inputs={"dataset": source})
        dataset_ref = accepted(box, "operation.dataset.retain", "reference",
            inputs={"dataset": integrated, "destination": "datasets"})
        retained = accepted(box, "command.material.read", "material", inputs={"location": dataset_ref})
        replayed = accepted(box, "command.value.decode", "value", inputs={"representation": retained})
        product_target = "minfin.nwf.overview" if args.series == "minfin.nwf.flows" else "minfin.budget.overview"
        prepared = accepted(box, "command.view.prepare", "view", target=product_target,
            inputs={"dataset": replayed})
        product = accepted(box, "command.product.render", "product", target=product_target,
            inputs={"view": prepared}, parameters={"format": args.format})
        product_ref = accepted(box, "command.artifact.commit", "reference",
            inputs={"material": product, "destination": "exports"})
        print("Source:", source_ref.location)
        print("Retained dataset:", dataset_ref.location)
        print("Product:", product_ref.location)
        print("Observations:", len(replayed.rows), "coverage:", replayed.assessment.status)


if __name__ == "__main__":
    main()
