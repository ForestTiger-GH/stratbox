"""Adapter первого этапа FRG."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from stratbox.macrobanks.frg.api import run_frg_stage1

from app.scenarios.models import ScenarioContext, ScenarioResult, ScenarioSpec


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "да"}


def run(*, context: ScenarioContext, params: dict[str, Any], spec: ScenarioSpec) -> ScenarioResult:
    if context.filestore is None:
        raise RuntimeError("FileStore is not available for current workspace root")

    root_dir = str(params.get("root_dir") or spec.input_dir).strip() or spec.input_dir
    output_path = str(params.get("output_path") or f"{spec.output_dir}/frg_stage1.xlsx").strip()
    recursive = _as_bool(params.get("recursive", False))

    context.logger.info("FRG stage1 started")
    context.logger.info("Root dir: %s", root_dir)
    context.logger.info("Output path: %s", output_path)
    context.logger.info("Recursive: %s", recursive)

    tables = run_frg_stage1(root_dir, recursive=recursive, filestore=context.filestore)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, df in tables.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    context.filestore.write_bytes(output_path, buffer.getvalue())

    row_counts = {name: int(len(df)) for name, df in tables.items()}
    details = {
        "row_counts": row_counts,
        "scenario_log": str(context.scenario_log_path),
        "workspace_root_path": str(context.workspace_root_path) if context.workspace_root_path else None,
    }
    context.logger.info("FRG stage1 finished: %s", row_counts)

    return ScenarioResult(
        ok=True,
        message="FRG stage1 finished",
        outputs=(output_path, str(context.scenario_log_path)),
        details=details,
    )
