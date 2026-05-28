"""Adapter первого этапа FRG."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from stratbox.macrobanks.frg.api import run_frg_stage1

from app.tasks.models import TaskContext, TaskResult, TaskSpec


def _as_bool(value: Any) -> bool:
    """Приводит пользовательское значение к bool."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "да"}


def run(*, context: TaskContext, params: dict[str, Any], spec: TaskSpec) -> TaskResult:
    """Запускает сканирование FRG и сохраняет результат в Excel."""
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
    details = {"row_counts": row_counts, "task_log": str(context.task_log_path)}
    context.logger.info("FRG stage1 finished: %s", row_counts)

    return TaskResult(
        ok=True,
        message="FRG stage1 finished",
        outputs=(output_path, str(context.task_log_path)),
        details=details,
    )
