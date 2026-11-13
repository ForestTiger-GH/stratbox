"""Offline reproducible performance and result probe for Bank of Russia industry XLSX.

Usage:
    python benchmarks/cbr_industries_history.py --debt-dir /data/debt --issuance-dir /data/issuance --output results.json
    python benchmarks/cbr_industries_history.py --debt-dir /data/debt --full-comparison --repeat 3

No downloads, Colab hooks or hardcoded user paths. Original files stay untouched.
"""
from __future__ import annotations

import argparse
import cProfile
from hashlib import sha256
import json
from pathlib import Path
import platform
from statistics import median
import sys
from time import perf_counter

from stratbox.data import SourcePayload
from stratbox.macrobanks import cbr_industries as debt
from stratbox.macrobanks.cbr_industries import issuance_0104 as issuance


PATTERNS = {
    "debt": "01_05_A_Debt_corp_*.xlsx",
    "issuance": "01_04_A_New_loans_corp_*.xlsx",
}


def _memory_peak_mib() -> float | None:
    try:
        import resource
    except ImportError:
        return None
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(rss / (1024 * 1024 if sys.platform == "darwin" else 1024), 2)


def _require(result, step):
    if result.outcome != "succeeded" or result.value is None:
        raise RuntimeError(f"{step}: {result.outcome}: {[x.code for x in result.diagnostics]}")
    return result.value


def _measure(fn):
    start = perf_counter()
    result = fn()
    return result, round(perf_counter() - start, 5)


def _run_one(kind, paths, selection, *, profile_path=None):
    domain = debt if kind == "debt" else issuance
    requests = []
    originals = []
    started = perf_counter()
    for path in paths:
        raw = path.read_bytes()
        originals.append({"name": path.name, "sha256": sha256(raw).hexdigest(), "bytes": len(raw)})
        request = (debt.ParseIndustryRequest if kind == "debt" else issuance.ParseIssuanceRequest)
        requests.append(request(SourcePayload(raw), path.name))
    read_seconds = round(perf_counter() - started, 5)
    build = (debt.BuildIndustryStreamRequest if kind == "debt" else issuance.BuildIssuanceStreamRequest)
    req = build(tuple(requests), selection=selection)
    if profile_path is not None:
        profiler = cProfile.Profile()
        profiler.enable()
    history_result, build_seconds = _measure(lambda: domain.build_stream(req))
    if profile_path is not None:
        profiler.disable()
        profiler.dump_stats(str(profile_path))
    history = _require(history_result, f"{kind}.build_stream")
    batch_req = (debt.RenderIndustriesRequest if kind == "debt"
                 else issuance.RenderIssuanceIndustriesRequest)
    # A full 93-month debt history exceeds the renderer's per-operation
    # cell budget during APK derivation; benchmark full construction separately.
    if selection.industry_codes is None:
        render_result, render_seconds, workbooks = None, 0.0, None
    else:
        render_result, render_seconds = _measure(
            lambda: domain.render_industries(batch_req(history, ("apk", "total")))
        )
        workbooks = _require(render_result, f"{kind}.render_industries")
    return {
        "kind": kind, "source_count": len(originals), "read_seconds": read_seconds,
        "build_seconds": build_seconds, "batch_render_seconds": render_seconds,
        "total_seconds": round(read_seconds + build_seconds + render_seconds, 5),
        "rss_peak_mib": _memory_peak_mib(),
        "full_observations": None if selection.industry_codes is not None else history.rows_stream,
        "materialized_observations": history.rows_stream,
        "selection": selection.industry_codes,
        "operation_versions": {
            "build": [history_result.definition.contract_version, history_result.definition.method_version],
            "render": [render_result.definition.contract_version, render_result.definition.method_version]
            if render_result is not None else None,
        },
        "computation_ids": {
            "history": history.evidence.computation_id.sha256 if history.evidence else None,
            "workbooks": render_result.computation.computation_id.sha256
            if render_result is not None and render_result.computation else None,
        },
        "rendered": [
            {"industry": item.industry_code, "sha256": item.representation.identity.sha256,
             "bytes": item.representation.identity.size, "sheets": list(item.sheet_names)}
            for item in workbooks.items
        ] if workbooks is not None else [],
        "originals": originals,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debt-dir", type=Path)
    parser.add_argument("--issuance-dir", type=Path)
    parser.add_argument("--full-comparison", action="store_true",
                        help="Also build a full 26-industry history; costs substantial extra time and RAM.")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--max-files", type=int, default=None)
    parser.add_argument("--output", type=Path, default=Path("industries-benchmark.json"))
    parser.add_argument("--profile-dir", type=Path, help="Optional cProfile .prof files per run.")
    args = parser.parse_args()
    if not (args.debt_dir or args.issuance_dir) or args.repeat < 1:
        parser.error("Supply at least one source directory and --repeat >= 1")
    if args.max_files is not None and args.max_files < 1:
        parser.error("--max-files must be positive")
    if args.profile_dir is not None:
        args.profile_dir.mkdir(parents=True, exist_ok=True)
    import pandas
    import openpyxl
    from stratbox import __version__
    report = {
        "environment": {
            "python": sys.version, "platform": platform.platform(),
            "cpu": platform.processor(), "stratbox": __version__,
            "pandas": pandas.__version__, "openpyxl": openpyxl.__version__,
        },
        "runs": [],
    }
    for kind, directory in (("debt", args.debt_dir), ("issuance", args.issuance_dir)):
        if directory is None:
            continue
        paths = tuple(sorted(directory.glob(PATTERNS[kind])))
        if args.max_files is not None:
            paths = paths[-args.max_files:]
        if not paths:
            parser.error(f"No {kind} XLSX sources in {directory}")
        for attempt in range(args.repeat):
            for label, selection in [("selected", debt.IndustrySelection(("apk", "total")))] + (
                [("full", debt.IndustrySelection())] if args.full_comparison else []
            ):
                profile_path = (args.profile_dir / f"{kind}-{label}-{attempt}.prof"
                                if args.profile_dir else None)
                result = _run_one(kind, paths, selection, profile_path=profile_path)
                result.update(run_number=attempt + 1, mode=label)
                report["runs"].append(result)
                print(f"{kind} {label} #{attempt + 1}: read={result['read_seconds']}s "
                      f"build={result['build_seconds']}s render={result['batch_render_seconds']}s "
                      f"rows={result['materialized_observations']}")
    report["medians"] = {}
    for kind in ("debt", "issuance"):
        for mode in ("selected", "full"):
            runs = [r for r in report["runs"] if r["kind"] == kind and r["mode"] == mode]
            if runs:
                report["medians"][f"{kind}.{mode}"] = {
                    key: median(run[key] for run in runs)
                    for key in ("read_seconds", "build_seconds", "batch_render_seconds", "total_seconds")
                }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Benchmark report: {args.output}")


if __name__ == "__main__":
    main()
