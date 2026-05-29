
"""Adapter задачи архиватора исходных файлов Банка России."""

from __future__ import annotations

from typing import Any

from stratbox.macrobanks.cbr_archiver.api import run_cbr_archiver

from app.tasks.models import TaskContext, TaskResult, TaskSpec


def _as_bool(value: Any) -> bool:
    """Приводит пользовательское значение к bool."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "да"}


def run(*, context: TaskContext, params: dict[str, Any], spec: TaskSpec) -> TaskResult:
    """Запускает доменный архиватор ЦБ через FileStore активного business-root."""
    if context.filestore is None:
        raise RuntimeError("FileStore is not available for current data_root")

    output_mode = str(params.get("output_mode") or "zip").strip().lower()
    output_dir = str(params.get("output_dir") or spec.output_dir).strip() or spec.output_dir

    context.logger.info("CBR archiver started")
    context.logger.info("Output mode: %s", output_mode)
    context.logger.info("Output dir: %s", output_dir)

    result = run_cbr_archiver(
        out_path=output_dir,
        output_mode=output_mode,  # type: ignore[arg-type]
        replace_existing=_as_bool(params.get("replace_existing", True)),
        continue_on_error=_as_bool(params.get("continue_on_error", True)),
        show_progress=False,
        filestore=context.filestore,
    )

    details = result.to_dict()
    details["task_log"] = str(context.task_log_path)
    details["data_root_path"] = str(context.data_root_path) if context.data_root_path else None

    message = (
        f"CBR archiver finished: {result.downloaded_count}/{result.total_sources} files downloaded"
    )
    outputs = tuple(result.saved_paths) + (str(context.task_log_path),)
    return TaskResult(ok=result.failed_count == 0, message=message, outputs=outputs, details=details)
