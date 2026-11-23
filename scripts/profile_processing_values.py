#!/usr/bin/env python3
"""Measure synthetic value accompaniment; no publisher-layout or economic claims.

Run locally with dataframe extras. The three fixtures exercise the actual CBR
flake, Rosstat selected-flake and SORS bundle codecs without network or solver
execution. Timings and peak temporary allocations are observations, not release
thresholds. Cancellation checkpoints are counted for the semantic digest and
SORS snapshot paths; source-context inspection is measured independently.
"""
from __future__ import annotations
import argparse
from dataclasses import fields
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import sys
from time import perf_counter
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def cbr(rows):
    from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake
    from stratbox.domains.cbr.tables.statistics.snapshots import flake_snapshot
    from stratbox.shared.data.workbook_cells import SheetCells, WorkbookCell
    from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
    from stratbox.shared.identity import ByteIdentity
    cells = tuple(WorkbookCell(i + 1, 1, f"A{i+1}", i, str(i), "n") for i in range(rows))
    original = SourcePayload(b"synthetic", source_id="cbr.monetary_statistics.monetary_agg")
    value = WorkbookFlake("cbr.monetary_statistics.monetary_agg", "synthetic", original.identity,
        "cbr.tables.monetary_agg", 1, (SheetCells("Synthetic", 0, rows, 1, cells),),
        (UsedInputReceipt.for_payload(original, "source"),))
    return value, lambda checkpoint: flake_snapshot(value, checkpoint=checkpoint), {"cells": rows, "sheets": 1}


def rosstat(rows):
    from stratbox.domains.rosstat.tables.contracts import RosstatSourceFlake, SourceValue
    from stratbox.domains.rosstat.tables.snapshots import flake_snapshot
    from stratbox.shared.data.snapshots import SnapshotCoverage
    from stratbox.shared.identity import ByteIdentity
    from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
    values = tuple(SourceValue(f"fixture_{i}", "Synthetic", "absolute", "annual", date(2025,1,1), date(2025,12,31),
        date(2025,12,31), Decimal(i), "reported", str(i), "count", "count", Decimal(1), "count", "fixture", "one", f"A{i+1}") for i in range(rows))
    original = SourcePayload(b"source", source_id="rosstat.short_term_indicators")
    value = RosstatSourceFlake("rosstat.short_term_indicators", "synthetic", "main", original.identity,
        ByteIdentity.of(b"physical"), "synthetic.technical_fixture", 1, values, (), (),
        (UsedInputReceipt.for_payload(original, "source"),),
        SnapshotCoverage("unknown", "Synthetic technical profile; no publisher coverage claim."))
    return value, lambda checkpoint: flake_snapshot(value, checkpoint=checkpoint), {"source_values": rows}


def sors(rows):
    import pandas
    from dataclasses import replace
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceBundle, SorsSourceInputs
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import DEPENDENCIES, dependency_manifest, original_input, source_uses
    from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.common import source_manifest_record
    from stratbox.domains.cbr.analytics.corporate_lending.sors.snapshots import snapshot, grid_identity
    from stratbox.shared.data.datasets import ComputationReceipt, build_dataset_version, computation_identity
    from stratbox.shared.data.snapshots import SnapshotCoverage
    from stratbox.shared.evidence import SourcePayload
    frame = pandas.DataFrame({"ordinal": range(rows), "value": [Decimal(i) for i in range(rows)]})
    sources = SorsSourceInputs(**{item.input_name: SourcePayload(f"synthetic {item.source_series}".encode(),
        source_id=item.source_series) for item in DEPENDENCIES if item.required})
    lineage = tuple(original_input(getattr(sources, item.input_name), item.source_series)
                    for item in DEPENDENCIES if item.required)
    kwargs = {item.name: frame for item in fields(SorsSourceBundle) if item.name.endswith("_grid")}
    kwargs["dependency_manifest_grid"] = dependency_manifest(sources, "2026-06-01", 1.0)
    kwargs["source_manifest_grid"] = pandas.DataFrame([source_manifest_record(item.source_series,
        getattr(sources, item.input_name), rows, required=True, role=item.source_role)
        for item in DEPENDENCIES if item.required])
    value = SorsSourceBundle(**kwargs, as_of_date="2026-06-01", publication_step=1.0, lineage=lineage,
        coverage=SnapshotCoverage("partial", "Synthetic technical grids with ten source roles; no economic validation claim."),
        source_uses=tuple(replace(use, qualification="synthetic_fixture") for use in source_uses(sources)))
    output = grid_identity(value)
    version = build_dataset_version("benchmark.sors", "synthetic", "technical_fixture", lineage, output)
    value = replace(value, evidence=ComputationReceipt(version, output, lineage,
        computation_identity("benchmark.sors", "technical_fixture", lineage)))
    return value, lambda checkpoint: snapshot(value, checkpoint=checkpoint), {"grids": len(kwargs), "total_grid_rows": sum(len(frame) for frame in kwargs.values()), "required_sources": sum(item.required for item in DEPENDENCIES)}


def measure(action):
    tracemalloc.start()
    started = perf_counter()
    result = action()
    elapsed = perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, {"seconds": round(elapsed, 6), "peak_temporary_bytes": peak}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--workload", choices=("all", "cbr", "rosstat", "sors"), default="all")
    args = parser.parse_args()
    if not 1 <= args.rows <= 1_000_000 or not 1 <= args.repeat <= 20:
        parser.error("rows must be 1..1000000 and repeat 1..20")
    from stratbox.core.execution.values import argument_identity
    from stratbox.core.execution.value_context import value_context
    report = {"rows_per_fixture": args.rows, "repeat": args.repeat, "scope": "synthetic_technical_values", "workloads": {}}
    factories = {"cbr": cbr, "rosstat": rosstat, "sors": sors}
    for name, factory in factories.items():
        if args.workload not in {"all", name}:
            continue
        value, encode, dimensions = factory(args.rows)
        phases = []
        for _ in range(args.repeat):
            checkpoints = 0
            def checkpoint():
                nonlocal checkpoints
                checkpoints += 1
            identity, signature = measure(lambda: argument_identity(value, checkpoint=checkpoint))
            context, context_cost = measure(lambda: value_context(value))
            retained, snapshot_cost = measure(lambda: encode(checkpoint))
            signature["canonical_bytes"] = identity.size
            snapshot_cost["logical_bytes"] = retained.identity.size + sum(table.identity.size for _, table in retained.tables)
            snapshot_cost["components"] = len(retained.tables)
            phases.append({"dimensions": dimensions, "signature": signature, "context": context_cost, "snapshot": snapshot_cost,
                "signature_sha256": identity.sha256, "snapshot_sha256": retained.identity.sha256,
                "source_uses": len(context.uses), "checkpoints": checkpoints})
        report["workloads"][name] = phases
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
