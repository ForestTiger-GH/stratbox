"""Adapter сценария загрузки исходных файлов Банка России."""

from __future__ import annotations

from typing import Any

from stratbox.macrobanks.cbr_archiver import (
    CbrSourceCollectRequest,
    DEFAULT_CBR_TARGET_ARCHIVE_NAME,
    DEFAULT_CBR_TARGET_DIRECTORY_NAME,
    collect_cbr_sources,
)

from app.scenarios.models import ScenarioContext, ScenarioResult, ScenarioSpec


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "да"}


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _build_target_path(*, output_dir: str, save_mode: str) -> str:
    base = str(output_dir).replace("\\", "/").rstrip("/")
    if save_mode == "files":
        return f"{base}/{DEFAULT_CBR_TARGET_DIRECTORY_NAME}"
    return f"{base}/{DEFAULT_CBR_TARGET_ARCHIVE_NAME}"


def run(*, context: ScenarioContext, params: dict[str, Any], spec: ScenarioSpec) -> ScenarioResult:
    if context.filestore is None:
        raise RuntimeError("FileStore is not available for current workspace root")

    save_mode = str(params.get("save_mode") or "zip").strip().lower()
    output_dir = str(params.get("output_dir") or spec.output_dir).strip() or spec.output_dir
    target_path = _build_target_path(output_dir=output_dir, save_mode=save_mode)

    context.logger.info("CBR source collector started")
    context.logger.info("Save mode: %s", save_mode)
    context.logger.info("Output dir: %s", output_dir)
    context.logger.info("Target path: %s", target_path)

    result = collect_cbr_sources(
        CbrSourceCollectRequest(
            target_path=target_path,
            save_mode=save_mode,  # type: ignore[arg-type]
            overwrite=_as_bool(params.get("overwrite", True)),
            continue_on_error=_as_bool(params.get("continue_on_error", True)),
            retry_attempts=_as_int(params.get("retry_attempts", 3), 3),
            show_progress=False,
        ),
        filestore=context.filestore,
    )

    details = result.to_dict()
    details["scenario_log"] = str(context.scenario_log_path)
    details["workspace_root_path"] = str(context.workspace_root_path) if context.workspace_root_path else None

    message = (
        f"CBR source collector finished: {result.success_count}/{result.requested_count} files downloaded "
        f"to {result.target_path}"
    )
    outputs = tuple(result.saved_paths) + (str(context.scenario_log_path),)
    return ScenarioResult(ok=result.ok, message=message, outputs=outputs, details=details)
