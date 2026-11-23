"""Measure exact signature scans and immutable reuse on representative values."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stratbox.core.execution.values import argument_identity
from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable


def measured(value, cache, *, memory=False):
    if memory:
        tracemalloc.start()
    started = time.perf_counter()
    identity = argument_identity(value, cache=cache)
    elapsed = time.perf_counter() - started
    peak = None
    if memory:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return {"seconds": round(elapsed, 6), "peak_temporary_bytes": peak,
            "identity_bytes": identity.size, "sha256": identity.sha256,
            "signature_metrics": dict(cache["signature_metrics"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--memory", action="store_true",
        help="Measure allocations with tracemalloc; its instrumentation also increases measured time.")
    options = parser.parse_args()
    if options.rows < 1:
        parser.error("rows must be positive")
    rows = options.rows
    table = TypedTable(TableSchema(DataContract("profile.values"),
        (ColumnSchema("ordinal", ScalarType.INTEGER), ColumnSchema("value", ScalarType.INTEGER))),
        tuple((number, number * 2) for number in range(rows)))
    snapshot = DatasetSnapshot.build("profile", "capture", DataContract("profile.snapshot"),
        (("values", table),), coverage=SnapshotCoverage("complete"))
    subject, metric = SubjectRef("profile", "one"), MetricRef("count", "unit", "count")
    period = PeriodRef("as_of", date(2026, 11, 23))
    batch = ObservationBatch("profile.batch", 1, "capture", tuple(
        Observation(subject, metric, period, (), "all", number, "reported", "fixture")
        for number in range(rows)), ())
    report = {"rows": rows, "snapshot_cells": rows * 2,
              "timing_includes_allocation_tracing": options.memory, "measurements": {}}
    for name, value in (("snapshot", snapshot), ("observations", batch)):
        cache = {}
        report["measurements"][name] = {"first": measured(value, cache, memory=options.memory),
                                         "repeated": measured(value, cache, memory=options.memory)}
    try:
        import pandas
    except ImportError:
        report["measurements"]["dataframe"] = {"state": "optional_dependency_unavailable"}
    else:
        frame = pandas.DataFrame({"ordinal": range(rows), "value": range(rows)})
        cache = {}
        first = measured(frame, cache, memory=options.memory)
        frame.iloc[-1, -1] += 1
        changed = measured(frame, cache, memory=options.memory)
        report["measurements"]["dataframe"] = {"first": first, "mutated": changed,
            "mutation_detected": first["sha256"] != changed["sha256"]}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
