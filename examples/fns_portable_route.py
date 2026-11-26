"""Process an explicit local FNS publication through the standard SDK.

    python examples/fns_portable_route.py source.json 2026-11-10 ./fns-output --series fns.sme
    python examples/fns_portable_route.py source.zip 2026-11-01 ./fns-output --series fns.1yur

Original retention, interpretation, dataset retention, replay and file delivery
are separate visible commands. The example performs no network requests.
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
    parser.add_argument("--series", choices=("fns.sme", "fns.1yur"), required=True)
    parser.add_argument("--format", choices=("csv", "json", "jsonl"), default="csv")
    args = parser.parse_args(argv)
    fmt = args.source.suffix.lower().lstrip(".")
    allowed = {"json"} if args.series == "fns.sme" else {"xlsx", "xls", "zip", "rar"}
    if fmt not in allowed:
        raise ValueError("The file extension is not an admitted representation of the selected series")
    limit = 4_000_000 if args.series == "fns.sme" else 30_000_000
    with args.source.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("The supplied source exceeds its admitted byte limit")
    metadata = {"issue_id": args.issue.isoformat(), "as_of": args.issue.isoformat()}
    original = Material(data, "application/json" if fmt == "json" else "application/octet-stream",
        args.series, metadata=metadata)
    args.destination.mkdir(parents=True, exist_ok=True)
    files = LocalFileStore(str(args.destination.resolve()))
    with StrategyBox(providers={"filestore": files}) as box:
        source_ref = accepted(box, "command.artifact.commit", "reference",
            inputs={"material": original, "destination": "originals"})
        dataset = accepted(box, "operation.series.extract_any", "dataset", target=args.series,
            inputs={"material": original, "issue": metadata},
            parameters={"format": fmt, "as_of": args.issue.isoformat()})
        integrated = accepted(box, "command.observations.align", "dataset", target=args.series,
            inputs={"dataset": dataset})
        encoded = accepted(box, "command.value.encode", "representation", inputs={"value": integrated})
        dataset_ref = accepted(box, "command.artifact.commit", "reference",
            inputs={"material": encoded, "destination": "datasets"})
        retained = accepted(box, "command.material.read", "material", inputs={"location": dataset_ref})
        replayed = accepted(box, "command.value.decode", "value", inputs={"representation": retained})
        product_target = args.series + ".regional"
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
